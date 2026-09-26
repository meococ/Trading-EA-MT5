"""pa_ledger — append-only, hash-chained trial ledger for PA-PRO.

File: ``PA_Pro/ledger/TRIALS.jsonl`` (path overridable for tests).

Line contract
------------
One JSON object per line, UTF-8, terminated by a single ``\\n``.  Required
keys (missing ones are filled with ``None`` by :func:`append`)::

    {trial_id, utc, round, family, spec_sha256, params, split, symbols, tf,
     n, key_metrics, code_sha256, prev_line_sha256, data_sha256,
     data_sha256_by_symbol}

plus ``kind`` (``"eval"``, ``"sealed_read"``, ...) and ``status``
(``"OK"`` / ``"ERROR"``).  ``data_sha256`` commits the line to the inputs it
describes (R02-C): the referee fills it from the provider slices it consumed;
the physics harness fills it from the frozen table hashes in ``FREEZE.json``.

Chain definition (exact)
------------------------
``prev_line_sha256`` of line *i* is ``SHA256`` (hex digest, lowercase) of the
RAW UTF-8 BYTES of line *i-1* **without** its trailing newline.  The genesis
line (i = 0) carries 64 zeros.  Verification re-reads the file bytes and
recomputes the chain; any edit to a line breaks the link stored in the NEXT
line.  Lines are never deleted or rewritten.

Integrity limits (R02-C/R02-F, charter section 6) — do not misread this file
---------------------------------------------------------------------------
The chain and the ``.tail`` sidecar are **checksums, not evidence**: they
contain no secret, so anyone with write access to ``ledger/`` can recompute
them (or delete the sidecar).  What actually detects a rewrite of ledger
history is the head anchor recorded in downstream artifacts
(:func:`anchor` / :func:`check_anchor`; every ``FREEZE.json`` and every round
report must carry it) plus independent re-execution of the round by a
different agent.  ``verify()`` never writes: a missing ``.tail`` on a
non-empty ledger is an error, never bootstrapped.

Anchors (R02-F)
---------------
``ANCHORS.jsonl`` next to the ledger is an append-only log of head anchors:
one JSON line per anchor, written by :func:`append_anchor` at every freeze and
round report.  :func:`verify_against_anchors` checks the ledger's prefix
against every record and reports the earliest violation.  Residual gap, stated
plainly: lines appended AFTER the last anchor are protected only by the chain
and ``.tail`` (both recomputable), and a party with write access can rewrite
``ANCHORS.jsonl`` itself.  The anchor therefore detects edits inside a covered
prefix only against a copy of the anchor that survives outside the attacker's
reach — it is not a security boundary either.

Concurrency: appends are serialised with an OS file lock on
``ledger/.ledger.lock`` so concurrent processes cannot interleave a
read-last-line / write-line pair.
"""

import hashlib
import json
import os
import time
from datetime import datetime, timezone

__all__ = [
    "GENESIS",
    "set_ledger_path",
    "ledger_path",
    "append",
    "verify",
    "read_lines",
    "count_trials",
    "code_sha256",
    "anchor",
    "check_anchor",
    "anchor_md",
    "anchors_path",
    "append_anchor",
    "verify_against_anchors",
]

GENESIS = "0" * 64
ANCHORS_NAME = "ANCHORS.jsonl"
# market Ruling 4 / REVIEW_3 N1: the one accepted chain irregularity —
# line 365 stores sha256(raw line 364 with '\r' stripped) instead of
# the raw-byte hash.  Pinned to this literal digest; see verify().
_PINNED_PREV_365 = \
    "46a823b541925f0306add03ca2722b18134a79f9293dcf53ab24e4119a0094cb"
_REQUIRED = [
    "trial_id", "utc", "round", "family", "spec_sha256", "params", "split",
    "symbols", "tf", "n", "key_metrics", "code_sha256", "prev_line_sha256",
    "data_sha256", "data_sha256_by_symbol",
]

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)                       # 03. EA Developer/PA_Pro
_LEDGER_PATH = os.path.join(_ROOT, "ledger", "TRIALS.jsonl")


def ledger_path():
    return _LEDGER_PATH


def set_ledger_path(path):
    """Redirect the ledger (tests / sandboxes).  Returns the previous path."""
    global _LEDGER_PATH
    old = _LEDGER_PATH
    _LEDGER_PATH = os.path.abspath(path)
    os.makedirs(os.path.dirname(_LEDGER_PATH), exist_ok=True)
    return old


def _lock_path(path=None):
    return os.path.join(os.path.dirname(path or _LEDGER_PATH), ".ledger.lock")


class _FileLock:
    def __init__(self, path, timeout=60.0):
        self.path = path
        self.timeout = timeout
        self.fd = None

    def __enter__(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        deadline = time.time() + self.timeout
        if os.name == "nt":
            import msvcrt

            while True:
                try:
                    msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
                    return self
                except OSError:
                    if time.time() > deadline:
                        raise TimeoutError(f"ledger lock timeout: {self.path}")
                    time.sleep(0.05)
        else:
            import fcntl

            fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(self.fd, 0, os.SEEK_SET)
                msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            os.close(self.fd)
            self.fd = None
        return False


def _raw_lines(path=None):
    """Raw lines (bytes, without trailing newline) of the ledger file."""
    path = path or _LEDGER_PATH
    if not os.path.exists(path):
        return []
    with open(path, "rb") as f:
        raw = f.read()
    if raw == b"":
        return []
    parts = raw.split(b"\n")
    if parts and parts[-1] == b"":
        parts = parts[:-1]
    return parts


def _sha256_hex(b):
    return hashlib.sha256(b).hexdigest()


def _utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tail_path(path=None):
    """Sidecar holding the SHA256 of the LAST line's raw bytes (R02-A F9).

    Tradeoff (declared): a sidecar keeps the JSONL format and the line
    numbering untouched (a terminator-line design would break line-based
    readers and ``count_trials``), at the cost of a second file that must
    travel with the ledger.  It is a checksum, not evidence; ``verify`` NEVER
    bootstraps it (R02-C: a missing sidecar on a non-empty ledger is an
    error, because blessing a missing sidecar is a laundering vector).
    """
    return (path or _LEDGER_PATH) + ".tail"


def _write_tail(raw_last, path=None):
    tmp = _tail_path(path) + ".tmp"
    with open(tmp, "wb") as f:
        f.write(_sha256_hex(raw_last).encode("ascii"))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, _tail_path(path))


def append(payload, kind="eval"):
    """Append ONE line.  Returns the assigned ``trial_id``.

    The caller supplies the measured fields; this function fills the standard
    envelope, assigns the sequential ``trial_id`` and chains the line to the
    previous raw line.  Under the file lock, so concurrent appends are safe.
    """
    body = dict(payload or {})
    with _FileLock(_lock_path()):
        lines = _raw_lines()
        prev_hash = _sha256_hex(lines[-1]) if lines else GENESIS
        trial_id = body.get("trial_id")
        if trial_id is None:
            trial_id = f"T{len(lines) + 1:06d}"
        body["trial_id"] = trial_id
        body.setdefault("kind", kind)
        body.setdefault("utc", _utc_now())
        body.setdefault("status", "OK")
        for k in _REQUIRED:
            body.setdefault(k, None)
        body["prev_line_sha256"] = prev_hash
        line = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
        os.makedirs(os.path.dirname(_LEDGER_PATH), exist_ok=True)
        line_bytes = line.encode("utf-8")
        with open(_LEDGER_PATH, "ab") as f:
            f.write(line_bytes + b"\n")
            f.flush()
            os.fsync(f.fileno())
        _write_tail(line_bytes)
    return trial_id


def verify(path=None):
    """Recompute the chain.  Returns ``(ok, first_bad_line_index)``.

    ``first_bad_line_index`` is the 0-based index of the first line that is not
    valid JSON or whose ``prev_line_sha256`` does not match the raw bytes of
    the previous line (``None`` when ``ok`` is True).  A tampered middle line
    is therefore reported at the following line index.  The LAST line has no
    successor to carry its hash, so it is checked against the sidecar tail hash
    (R02-A F9); a missing sidecar on a non-empty ledger is reported as
    ``(False, len(lines) - 1)`` and is NEVER bootstrapped (R02-C: bootstrap on
    read blessed tampered history — the red team's laundering vector L4/L5).
    An absent/empty ledger has nothing to verify and returns ``(True, None)``;
    the ledger anchor in FREEZE.json / round reports detects a truncation to
    empty (recompute :func:`check_anchor`).
    """
    path = path or _LEDGER_PATH
    if not os.path.exists(path):
        return True, None
    with open(path, "rb") as f:
        raw = f.read()
    lines = raw.split(b"\n")
    if lines and lines[-1] == b"":
        lines = lines[:-1]
    prev_hash = GENESIS
    for i, ln in enumerate(lines):
        try:
            obj = json.loads(ln.decode("utf-8"))
        except Exception:
            return False, i
        if not isinstance(obj, dict):
            return False, i
        if obj.get("prev_line_sha256") != prev_hash:
            # Pinned exception — edge 365 only (market Ruling 4 /
            # REVIEW_3 N1 / market DEVIATIONS.md D33): line 365's stored
            # prev commits to line 364 with its trailing '\r' stripped —
            # the foreign writer hashed a normalised copy.  Accept iff
            # the stored value is the pinned digest AND it recomputes
            # from the actual raw bytes; the chain forward still
            # propagates the RAW hash of line 365.  Every other edge
            # stays strict.
            stored = obj.get("prev_line_sha256")
            if not (i == 365 and i > 0 and stored == _PINNED_PREV_365
                    and stored == _sha256_hex(
                        lines[i - 1].replace(b"\r", b""))):
                return False, i
        prev_hash = _sha256_hex(ln)
    if lines:
        tp = _tail_path(path)
        try:
            with open(tp, "r", encoding="ascii") as f:
                tail = f.read().strip()
        except OSError:
            tail = None
        if tail is None:
            return False, len(lines) - 1
        if tail != _sha256_hex(lines[-1]):
            return False, len(lines) - 1
    return True, None


def _anchor_sha256(lines):
    """SHA256 over the raw bytes of ``lines`` (as stored: each + ``\\n``)."""
    h = hashlib.sha256()
    for ln in lines:
        h.update(ln + b"\n")
    return h.hexdigest()


def anchor(path=None):
    """Ledger head anchor (R02-C/R02-F): ``{"ledger", "n_lines", "sha256", "utc"}``.

    PREFIX hash: ``sha256`` covers the raw bytes of the FIRST ``n_lines``
    lines, so later appends are legal by design and do not invalidate the
    anchor, while any rewrite/truncation inside the covered prefix fails
    :func:`check_anchor`.  Every ``FREEZE.json`` and every round report MUST
    embed this (charter section 6).  Residual gap: it protects nothing after
    ``n_lines`` and nothing at all if the artifact carrying it is rewritten
    too — see the module docstring; the real defence is independent
    re-execution.
    """
    path = path or _LEDGER_PATH
    lines = _raw_lines(path)
    return {
        "ledger": os.path.basename(path),
        "n_lines": len(lines),
        "sha256": _anchor_sha256(lines),
        "utc": _utc_now(),
    }


def check_anchor(a, path=None):
    """Re-verify a stored :func:`anchor` against the ledger.  No writes.

    Returns ``(ok, reason)``; ``ok`` is True only when the ledger still holds
    at least ``n_lines`` lines and the first ``n_lines`` lines hash exactly to
    the anchored value (truncation, deletion and any edit inside the covered
    prefix raise False).
    """
    path = path or _LEDGER_PATH
    a = a or {}
    try:
        n = int(a.get("n_lines"))
    except (TypeError, ValueError):
        return False, "anchor has no n_lines"
    lines = _raw_lines(path)
    if len(lines) < n:
        return False, f"ledger holds {len(lines)} lines, anchor covers {n}"
    got = _anchor_sha256(lines[:n])
    if got != a.get("sha256"):
        return False, (f"anchor mismatch over first {n} lines: "
                       f"stored {a.get('sha256')}, recomputed {got}")
    return True, None


def anchor_md(a=None, path=None):
    """One markdown line for round reports / results artifacts."""
    a = a or anchor(path)
    return (f"Ledger anchor: `{a['ledger']}` sha256(first {a['n_lines']} lines) "
            f"= `{a['sha256']}` · n_lines = {a['n_lines']} · utc {a['utc']}")


def anchors_path(path=None):
    """``ANCHORS.jsonl`` next to the ledger (test redirection follows the
    ledger path set by :func:`set_ledger_path`)."""
    return os.path.join(os.path.dirname(path or _LEDGER_PATH), ANCHORS_NAME)


def append_anchor(note=None, path=None):
    """Append the current ledger head to ``ANCHORS.jsonl``.  Returns the record.

    Append-only; called at every freeze and every round report (charter
    section 6 item 6).  The record is the :func:`anchor` dict plus ``kind`` and
    an optional ``note``.  Taking the anchor under the ledger lock avoids
    racing a concurrent :func:`append`.
    """
    path = path or _LEDGER_PATH
    with _FileLock(_lock_path(path)):
        rec = anchor(path)
        rec["kind"] = "ledger_anchor"
        rec["note"] = note
        ap = anchors_path(path)
        os.makedirs(os.path.dirname(ap), exist_ok=True)
        line = json.dumps(rec, sort_keys=True, separators=(",", ":"), default=str)
        with open(ap, "ab") as f:
            f.write(line.encode("utf-8") + b"\n")
            f.flush()
            os.fsync(f.fileno())
    return rec


def verify_against_anchors(path=None, anchors_file=None):
    """Check the ledger against every anchor in ``ANCHORS.jsonl``.

    Returns ``(ok, violation)`` where ``violation`` is ``None`` on success and
    the EARLIEST violated anchor record (augmented with ``reason`` and
    ``index``) otherwise.  Each anchor is validated (``n_lines >= 1``, 64-hex
    ``sha256``) and its covered prefix re-hashed; append-only growth after an
    anchor is legal.  Missing anchors file -> ``(False, ...)``: a ledger with
    no anchors has no ex-post protection.
    """
    path = path or _LEDGER_PATH
    ap = anchors_file or anchors_path(path)
    if not os.path.exists(ap):
        return False, {"reason": "no anchors file: ledger has no ex-post protection",
                       "anchors_file": ap}
    recs = []
    with open(ap, "rb") as f:
        for i, ln in enumerate(f.read().split(b"\n")):
            if not ln.strip():
                continue
            try:
                obj = json.loads(ln.decode("utf-8"))
            except Exception as exc:
                return False, {"reason": f"unparseable anchor line {i}: {exc}",
                               "index": i}
            recs.append(obj)
    if not recs:
        return False, {"reason": "anchors file is empty: no ex-post protection",
                       "anchors_file": ap}
    for i, rec in enumerate(recs):
        n = rec.get("n_lines")
        sha = rec.get("sha256")
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            return False, {**rec, "reason":
                           f"invalid anchor #{i}: n_lines={n!r} protects nothing",
                           "index": i}
        if not isinstance(sha, str) or len(sha) != 64:
            return False, {**rec, "reason":
                           f"invalid anchor #{i}: sha256 is not 64 hex chars",
                           "index": i}
        ok, why = check_anchor(rec, path)
        if not ok:
            return False, {**rec, "reason": why, "index": i}
    return True, None


def read_lines(path=None):
    """Parsed ledger lines (list of dicts).  Raises on corrupt JSON."""
    path = path or _LEDGER_PATH
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "rb") as f:
        for ln in f.read().split(b"\n"):
            if ln.strip() == b"":
                continue
            out.append(json.loads(ln.decode("utf-8")))
    return out


def count_trials(kind=None, include_error=True, path=None):
    """Program-level trial count (for the Deflated Sharpe).  Counts ledger
    lines, optionally filtered by ``kind``; ERROR lines are excluded when
    ``include_error`` is False."""
    n = 0
    for obj in read_lines(path):
        if kind is not None and obj.get("kind") != kind:
            continue
        if not include_error and obj.get("status") == "ERROR":
            continue
        n += 1
    return n


def _is_scratch(name):
    """True for audit-scratch entries excluded from code-hash bundles."""
    return name.startswith("_") and name != "__init__.py"


def code_sha256(lib_dir=None):
    """SHA256 over ``lib/*.py`` (sorted by name): the code identity recorded
    in every ledger line.  Audit scratch is excluded (R02-C/D): names starting
    with ``_`` (``_scratch``, ``_diag*``, ``_review*``) never belong to a code
    bundle, so a probe dropped beside production code cannot change a frozen
    hash.  ``__init__.py`` stays.  Missing directory -> hash of empty string."""
    lib_dir = lib_dir or _HERE
    h = hashlib.sha256()
    if os.path.isdir(lib_dir):
        for name in sorted(os.listdir(lib_dir)):
            if name.endswith(".py") and not _is_scratch(name):
                h.update(name.encode("utf-8"))
                with open(os.path.join(lib_dir, name), "rb") as f:
                    h.update(f.read())
    return h.hexdigest()
