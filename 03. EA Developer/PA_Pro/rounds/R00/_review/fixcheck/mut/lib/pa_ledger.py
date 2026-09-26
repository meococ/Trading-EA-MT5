"""pa_ledger — append-only, hash-chained trial ledger for PA-PRO.

File: ``PA_Pro/ledger/TRIALS.jsonl`` (path overridable for tests).

Line contract
-------------
One JSON object per line, UTF-8, terminated by a single ``\\n``.  Required
keys (missing ones are filled with ``None`` by :func:`append`)::

    {trial_id, utc, round, family, spec_sha256, params, split, symbols, tf,
     n, key_metrics, code_sha256, prev_line_sha256}

plus ``kind`` (``"eval"``, ``"sealed_read"``, ...) and ``status``
(``"OK"`` / ``"ERROR"``).

Chain definition (exact)
------------------------
``prev_line_sha256`` of line *i* is ``SHA256`` (hex digest, lowercase) of the
RAW UTF-8 BYTES of line *i-1* **without** its trailing newline.  The genesis
line (i = 0) carries 64 zeros.  Verification re-reads the file bytes and
recomputes the chain; any edit to a line breaks the link stored in the NEXT
line.  Lines are never deleted or rewritten.

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
]

GENESIS = "0" * 64
_REQUIRED = [
    "trial_id", "utc", "round", "family", "spec_sha256", "params", "split",
    "symbols", "tf", "n", "key_metrics", "code_sha256", "prev_line_sha256",
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


def _lock_path():
    return os.path.join(os.path.dirname(_LEDGER_PATH), ".ledger.lock")


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


def _raw_lines():
    """Raw lines (bytes, without trailing newline) of the ledger file."""
    if not os.path.exists(_LEDGER_PATH):
        return []
    with open(_LEDGER_PATH, "rb") as f:
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
        with open(_LEDGER_PATH, "ab") as f:
            f.write(line.encode("utf-8") + b"\n")
            f.flush()
            os.fsync(f.fileno())
    return trial_id


def verify(path=None):
    """Recompute the chain.  Returns ``(ok, first_bad_line_index)``.

    ``first_bad_line_index`` is the 0-based index of the first line that is not
    valid JSON or whose ``prev_line_sha256`` does not match the raw bytes of
    the previous line (``None`` when ``ok`` is True).  A tampered middle line
    is therefore reported at the following line index.
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
            return False, i
        prev_hash = _sha256_hex(ln)
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


def code_sha256(lib_dir=None):
    """SHA256 over ``lib/*.py`` (sorted by name): the code identity recorded
    in every ledger line.  Missing directory -> hash of the empty string."""
    lib_dir = lib_dir or _HERE
    h = hashlib.sha256()
    if os.path.isdir(lib_dir):
        for name in sorted(os.listdir(lib_dir)):
            if name.endswith(".py"):
                h.update(name.encode("utf-8"))
                with open(os.path.join(lib_dir, name), "rb") as f:
                    h.update(f.read())
    return h.hexdigest()
