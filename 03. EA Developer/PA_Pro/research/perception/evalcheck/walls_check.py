"""walls_check — EVAL-AUDIT mandate 2, item 6: walls + ledger self-check.

Checks (mandate numbering):
  (a) No code under research/perception/ or research/market/ references
      HOLD file paths, except sealed hash/ledger code (the golden split /
      validate tooling that WRITES and hashes HOLD is exempt, and is
      listed explicitly in the report).
  (b) Perception code reads bars only via golden/book_loader.py (the
      single door) and never touches 2010-2015 bars outside the BOOK
      window.  Declared cache layers that only re-serve book_loader
      output (linelab/bars_cache.py, evalcheck/cache.py) are exempt.
  (c) No outcome imports in perception code: pa_fill, pa_eval,
      pa_random, arrival_outcome, phys_resolve, fwd_*.  Scan uses
      tokenize NAME tokens, so strings/comments/guard-sets that merely
      NAME the banned modules (book_loader's assert_clean_process, test
      wall assertions) do not false-fire.
  (d) Ledger lint: every ledger/TRIALS.jsonl line is compact JSON
      (sort_keys + tight separators round-trip) with LF endings; then
      pa_ledger.verify() must return (True, None).  Lines 364/365 are
      the KNOWN pinned defect (market Ruling 4 / REVIEW_3 N1 / D33) and
      are reported as such, not as violations.
  (e) The pinned verify() exception itself (implemented in
      lib/pa_ledger.py): edge 365 accepts stored prev 46a823b5... iff it
      equals sha256(raw line 364 with '\\r' stripped); the raw hash still
      propagates outbound; every other edge is strict.
  (f) Pin tests on byte-copies of the real ledger:
        verbatim copy            -> (True, None)
        mutate any other line    -> (False, ...)
        extra '\\r' on a clean line -> (False, ...)
        different stored prev@365 -> (False, 365)
        strip '\\r' from line 364   -> (True, None)  [exception is a
                                      superset of the strict rule]

Usage: python walls_check.py          # run all checks + tests
Read-only against the repo; ledger copies live in a temp dir.
"""

import hashlib
import io
import json
import os
import re
import sys
import tempfile
import tokenize

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
_ROOT = os.path.abspath(os.path.join(_PERC, "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "lib"))

import pa_ledger  # noqa: E402

LEDGER = os.path.join(_ROOT, "ledger", "TRIALS.jsonl")
PIN_EDGE = 365          # the one accepted irregular edge (Ruling 4)
PIN_LINES = {364, 365}  # the foreign-writer lines carrying the defect

# ---- (a) HOLD file-path references -----------------------------------------
HOLD_RE = re.compile(r"BOOK2012_HOLD|HOLD_OUT|_HOLD\b|\bHOLD\b")
# Sealed golden split/repair/validate tooling: it WRITES and hashes the
# HOLD file; that is the exemption the mandate names ("sealed
# hash/ledger code").  This checker itself and test files that assert
# the *absence* of HOLD are guards, not references.
SELF = os.path.join("evalcheck", "walls_check.py")
HOLD_EXEMPT = {
    os.path.join("golden", "split.py"),
    os.path.join("golden", "validate.py"),
    os.path.join("golden", "repair.py"),
}
HOLD_GUARD_FILES = {os.path.join("tests", "test_engine_v1.py"),
                    os.path.join("evalcheck", "test_walls.py"), SELF}

# ---- (b) bars only via book_loader — positive checks (R13 §13.7) ---
# A file that touches bar-shaped data must POSITIVELY import a door:
#   book_loader itself, evalcheck's cache module, or eval.py (which
#   reaches bars only through book_loader.day_bars).
DOOR_RE = re.compile(
    r"^\s*(import\s+(book_loader|cache|eval)\b"
    r"|from\s+(book_loader|cache|eval|evalcheck)\s+import\b"
    r"|import\s+evalcheck\.cache\b)", re.M)
# Direct bar-path access is NEVER ok outside the door itself:
PATH_RE = re.compile(
    r"\.parquet|read_parquet|read_csv|\.csv\b|EURUSD_M1|M1_20\d\d")
# npz cache io is ok only in a file that imports a door:
NP_RE = re.compile(r"np\.load|np\.savez|np\.loadtxt")
BARS_DOOR = os.path.join("golden", "book_loader.py")
# Guards that *test* the wall (assert out-of-window years are rejected).
BARS_GUARD_FILES = {os.path.join("tests", "test_book_loader.py"),
                    os.path.join("evalcheck", "test_walls.py"), SELF}
YEAR_RE = re.compile(r"\b20(10|11|13|14|15)\b")

# ---- (c) outcome identifiers ------------------------------------------------
BANNED_NAMES = {"pa_fill", "pa_eval", "pa_random",
                "arrival_outcome", "phys_resolve"}
BANNED_RE = re.compile(r"fwd_")


def _py_files(root):
    for dp, _, fns in os.walk(root):
        for fn in sorted(fns):
            if fn.endswith(".py"):
                yield os.path.join(dp, fn)


def _prose_lines(p):
    """Line numbers that are comments or inside triple-quoted strings
    (docstrings).  HOLD tokens on these lines are prose, not access."""
    safe = set()
    try:
        src = open(p, "rb").read()
        try:
            toks = tokenize.tokenize(io.BytesIO(src).readline)
        except Exception:
            toks = tokenize.generate_tokens(io.BytesIO(src).readline)
        for tok in toks:
            if tok.type == tokenize.COMMENT:
                safe.add(tok.start[0])
            elif tok.type == tokenize.STRING and \
                    tok.string.lstrip("rubfRUBF").startswith(
                        ("'''", '"""')):
                for ln in range(tok.start[0], tok.end[0] + 1):
                    safe.add(ln)
    except Exception:
        pass
    return safe


def scan_file_a(p, rel):
    """HOLD references in one file; returns (hits, violations).
    Comment/docstring occurrences are ignored (R13 §13.7)."""
    hits, viol = [], []
    safe = _prose_lines(p)
    for n, line in enumerate(open(p, encoding="utf8",
                                  errors="replace"), 1):
        if not HOLD_RE.search(line):
            continue
        if n in safe:
            kind = "doc"
        elif rel in HOLD_EXEMPT:
            kind = "sealed"
        elif rel in HOLD_GUARD_FILES:
            kind = "guard"
        else:
            kind = "VIOLATION"
        hits.append((kind, p, n, line.strip()[:100]))
        if kind == "VIOLATION":
            viol.append((p, n))
    return hits, viol


def check_a():
    """HOLD file-path references in code under perception + market."""
    hits, violations = [], []
    for root in (os.path.join(_ROOT, "research", "perception"),
                 os.path.join(_ROOT, "research", "market")):
        for p in _py_files(root):
            rel = os.path.relpath(p, root)
            if rel == SELF:
                continue
            h, v = scan_file_a(p, rel)
            hits += h
            violations += v
    return hits, violations


def scan_file_b(p, rel):
    """Bar-access rules for one file; returns (hits, violations).
    Positive check: a file that touches bar data must import a door
    (book_loader / evalcheck cache / eval).  Direct parquet/csv/M1
    paths are violations even in door-importing files (except the
    door itself)."""
    hits, viol = [], []
    src = open(p, encoding="utf8", errors="replace").read()
    has_door = bool(DOOR_RE.search(src))
    safe = _prose_lines(p)
    for n, line in enumerate(src.splitlines(), 1):
        if n in safe:
            continue
        s = line.strip()
        if PATH_RE.search(s):
            hits.append(("direct-bar-path", p, n, s[:100]))
            viol.append((p, n))
        elif NP_RE.search(s) and not has_door:
            hits.append(("np-io-no-door", p, n, s[:100]))
            viol.append((p, n))
        elif YEAR_RE.search(s) and not has_door:
            hits.append(("year-lit-no-door", p, n, s[:100]))
            viol.append((p, n))
    return hits, viol


def check_b():
    """Perception code may touch bars only through book_loader."""
    hits, violations = [], []
    root = os.path.join(_ROOT, "research", "perception")
    for p in _py_files(root):
        rel = os.path.relpath(p, root)
        if rel == BARS_DOOR or rel in BARS_GUARD_FILES:
            continue
        h, v = scan_file_b(p, rel)
        hits += h
        violations += v
    return hits, violations


def check_c():
    """Banned outcome identifiers as real NAME tokens in perception .py."""
    violations = []
    root = os.path.join(_ROOT, "research", "perception")
    for p in _py_files(root):
        src = open(p, "rb").read()
        try:
            toks = tokenize.tokenize(io.BytesIO(src).readline)
        except Exception:
            toks = tokenize.generate_tokens(
                io.BytesIO(src).readline)
        try:
            for tok in toks:
                if tok.type == tokenize.NAME and (
                        tok.string in BANNED_NAMES
                        or BANNED_RE.match(tok.string)):
                    violations.append((p, tok.start[0], tok.string))
        except tokenize.TokenError:
            pass
    return violations


def check_d():
    """Ledger lint: compact JSON, LF endings, then pa_ledger.verify()."""
    raw = open(LEDGER, "rb").read()
    lines = raw.split(b"\n")
    if lines and lines[-1] == b"":
        lines = lines[:-1]
    rows = []
    for i, ln in enumerate(lines):
        prob = []
        if b"\r" in ln:
            prob.append("CR byte")
        try:
            obj = json.loads(ln.decode("utf8"))
            compact = json.dumps(obj, sort_keys=True,
                                 separators=(",", ":"),
                                 default=str).encode("utf8")
            if compact != ln:
                prob.append("not compact")
        except Exception as exc:
            prob.append("unparseable: %s" % exc)
        if prob:
            rows.append((i, prob, i in PIN_LINES))
    ok, idx = pa_ledger.verify(LEDGER)
    return rows, ok, idx, len(lines)


# ---- (e/f) pinned-exception tests on byte-copies ----------------------------
def _write_copy(dst_lines, dst):
    """Write a ledger copy plus a correct .tail sidecar."""
    with open(dst, "wb") as f:
        for ln in dst_lines:
            f.write(ln + b"\n")
    tail = hashlib.sha256(dst_lines[-1]).hexdigest()
    with open(dst + ".tail", "w", encoding="ascii") as f:
        f.write(tail)


# ---- (g) clock stamps (R14 §14.1) -----------------------------------
# Entry stamps in the last 40 lines of every *_LOG.md under
# research/perception/, the header stamps of LEAD_NOTE*.md, and the
# "## Ruling N (time)" headers of LEAD_RULINGS.md.  A stamp FAILs when
# it is later than the file's mtime + 2 min or later than the check
# time.  "plan ~HH:MMZ" (planned, not observed) is ignored.
STAMP_RE = re.compile(
    r"(?:(\d{4}-\d{2}-\d{2})[ T,]*)?~?\s*\b(\d{1,2}):(\d{2})Z\b")
# an entry stamp sits at the START of a log line — bullet `- 22:38Z`,
# `## 2026-09-21 22:41Z —`, or bare `22:38Z`.  Mid-line times are
# deadlines, not stamps.
_ENTRY_RE = re.compile(
    r"^\s*[-*#]*\s*(?:\d{4}-\d{2}-\d{2}[ T,]*)?~?\s*"
    r"\d{1,2}:\d{2}Z\b")
LOG_TAIL = 40


def _log_files():
    root = os.path.join(_ROOT, "research", "perception")
    for dp, _, fns in os.walk(root):
        for fn in sorted(fns):
            if fn.endswith("_LOG.md"):
                yield os.path.join(dp, fn), "tail"
            elif fn.startswith("LEAD_NOTE") and fn.endswith(".md"):
                yield os.path.join(dp, fn), "head"


def check_g(now=None):
    """Returns list of (file, line_no, stamp, why) failures."""
    import datetime
    now = now or datetime.datetime.now(datetime.timezone.utc)
    fails = []
    targets = list(_log_files())
    targets.append((os.path.join(_ROOT, "research", "perception",
                                 "LEAD_RULINGS.md"), "rulings"))
    for p, mode in targets:
        if not os.path.exists(p):
            continue
        mtime = datetime.datetime.fromtimestamp(
            os.path.getmtime(p), datetime.timezone.utc)
        lines = open(p, encoding="utf8", errors="replace") \
            .read().splitlines()
        if mode == "tail":
            scan = [(len(lines) - LOG_TAIL + i, ln)
                    for i, ln in enumerate(lines[-LOG_TAIL:])]
        elif mode == "head":
            scan = [(i, ln) for i, ln in enumerate(lines[:LOG_TAIL])]
        else:                               # LEAD_RULINGS headers
            scan = [(i, ln) for i, ln in enumerate(lines)
                    if ln.startswith("## Ruling")]
        for ln_no, ln in scan:
            if "plan" in ln.lower():
                continue
            # entry stamps only: anchored at line start (bullet or
            # bare).  Mid-line time mentions are deadlines, not
            # stamps (LEVEL_LOG "till 23:50Z" etc. are plans).
            if mode == "tail":
                em = _ENTRY_RE.match(ln)
                if not em:
                    continue
                hits = [STAMP_RE.search(ln, 0, em.end())]
            else:
                hits = STAMP_RE.finditer(ln)
            for mt in hits:
                if mt is None:
                    continue
                dstr, hh, mm = mt.group(1), int(mt.group(2)), \
                    int(mt.group(3))
                if hh > 23 or mm > 59:
                    continue
                if dstr:
                    cand = [datetime.datetime.strptime(dstr, "%Y-%m-%d")
                            .replace(tzinfo=datetime.timezone.utc)
                            .date()]
                else:
                    cand = [mtime.date()]
                    if mtime.hour < 4:
                        # file written just after midnight: a late-evening
                        # stamp may honestly belong to the previous day
                        cand.append(
                            (mtime - datetime.timedelta(days=1)).date())
                dt = None
                for d in cand:
                    t = datetime.datetime(
                        d.year, d.month, d.day, hh, mm,
                        tzinfo=datetime.timezone.utc)
                    if t <= mtime + datetime.timedelta(minutes=2):
                        dt = t
                        break
                    dt = dt or t
                why = None
                if dt > mtime + datetime.timedelta(minutes=2):
                    why = "stamp later than file mtime + 2min"
                elif dt > now:
                    why = "stamp later than check time"
                if why:
                    fails.append((p, ln_no + 1, mt.group(0), why))
    return fails


def check_ef():
    """Run pa_ledger.verify() on tampered copies of the real ledger."""
    raw = open(LEDGER, "rb").read()
    lines = raw.split(b"\n")
    if lines and lines[-1] == b"":
        lines = lines[:-1]
    results = []
    with tempfile.TemporaryDirectory() as td:
        def run(name, mut):
            cp = [bytes(x) for x in lines]
            mut(cp)
            dst = os.path.join(td, name + ".jsonl")
            _write_copy(cp, dst)
            ok, idx = pa_ledger.verify(dst)
            results.append((name, ok, idx))
        run("verbatim", lambda cp: None)
        # mutate a byte inside line 100 (a digit -> different digit)
        def m100(cp):
            ln = bytearray(cp[100])
            pos = next(j for j, b in enumerate(ln)
                       if 48 <= b <= 57)
            ln[pos] = 48 + (ln[pos] - 47) % 10
            cp[100] = bytes(ln)
        run("mutate_line_100", m100)
        run("extra_CR_line_200", lambda cp: cp.__setitem__(200,
                                                         cp[200] + b"\r"))
        # different stored prev at the pinned edge
        def m365(cp):
            cp[365] = cp[365].replace(
                pa_ledger._PINNED_PREV_365.encode(),
                b"0" * 64)
        run("wrong_prev_at_365", m365)
        run("strip_CR_line_364", lambda cp: cp.__setitem__(
            364, cp[364].replace(b"\r", b"")))
    return results


def main():
    print("== walls_check ==  ledger:", LEDGER)
    allok = True

    hits, viol = check_a()
    print("\n(a) HOLD path references in code (perception+market):")
    for kind, p, n, s in hits:
        print("    [%s] %s:%d  %s" %
              (kind, os.path.relpath(p, _ROOT), n, s))
    print("    -> %d hit(s), %d violation(s) "
          "(sealed: split.py/validate.py; guard: test_engine_v1.py)"
          % (len(hits), len(viol)))
    allok &= not viol

    hits, viol = check_b()
    print("\n(b) bar-access outside book_loader (perception):")
    for kind, p, n, s in hits:
        print("    [%s] %s:%d  %s" %
              (kind, os.path.relpath(p, _ROOT), n, s))
    print("    -> %d violation(s) (door: golden/book_loader.py; "
          "declared caches: linelab/bars_cache.py, evalcheck/cache.py)"
          % len(viol))
    allok &= not viol

    viol = check_c()
    print("\n(c) outcome identifiers in perception code (NAME tokens):")
    for p, n, tok in viol:
        print("    %s:%d  %s" % (os.path.relpath(p, _ROOT), n, tok))
    print("    -> %d violation(s)" % len(viol))
    allok &= not viol

    rows, ok, idx, nlines = check_d()
    print("\n(d) ledger lint (%d lines):" % nlines)
    for i, prob, pinned in rows:
        tag = "PINNED-DEFECT (D33/Ruling 4)" if pinned else "VIOLATION"
        print("    line %d: %s  [%s]" % (i, ", ".join(prob), tag))
    unpinned = [r for r in rows if not r[2]]
    print("    -> %d unpinned defect(s); pa_ledger.verify() = (%s, %s)"
          % (len(unpinned), ok, idx))
    allok &= (not unpinned) and ok and idx is None

    print("\n(e/f) pinned-exception tests (verify on tampered copies):")
    expect = {"verbatim": (True, None),
              "mutate_line_100": (False, None),
              "extra_CR_line_200": (False, None),
              "wrong_prev_at_365": (False, PIN_EDGE),
              "strip_CR_line_364": (True, None)}
    for name, ok, idx in check_ef():
        exp_ok, exp_idx = expect[name]
        good = (ok == exp_ok) and (exp_idx is None or idx == exp_idx)
        allok &= good
        print("    %-20s -> (%s, %s)   expected (%s, %s)   %s"
              % (name, ok, idx, exp_ok, exp_idx,
                 "ok" if good else "FAIL"))

    fails = check_g()
    print("\n(g) clock stamps (R14 §14.1 — *_LOG.md tails, LEAD_* "
          "headers):")
    for p, n, stamp, why in fails:
        print("    FAIL %s:%d  %s  (%s)"
              % (os.path.relpath(p, _ROOT), n, stamp, why))
    print("    -> %d fail(s)" % len(fails))
    allok &= not fails

    print("\n== walls_check %s ==" % ("PASS" if allok else "FAIL"))
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
