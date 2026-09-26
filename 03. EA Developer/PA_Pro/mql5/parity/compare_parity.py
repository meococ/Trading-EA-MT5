"""compare_parity.py — diff the EA's zone export against the Python export.

Contract (mandate): >= 99.5% of bars with identical zone bounds at a
tolerance of 0.1 pip.

Both CSVs share the schema of PA_Export.mqh / export_zones.py.  Rows are
joined on (t_epoch, gen) — the EA's t_idx indexes its own loaded window,
so bar indices are NOT comparable; the server epoch is.

Per (t_epoch, gen) the armed-zone sets are compared as unordered
(kind, lo, hi) triples: a Python zone matches an MQL5 zone when kind is
equal and |lo| and |hi| differ by <= tol (default 0.1 pip).  A bar counts
as identical only if the set cardinalities are equal AND every zone
matches.

Usage:
    python compare_parity.py <py_csv> <mq_csv> [tol_price]
                             [--e0 epoch] [--e1 epoch] [--report path]

--e0/--e1 bound the compared epoch range on BOTH sides.  Use them when
the two exports cover different loaded windows: zone state accumulates
from each side's own history start, so an epoch is only fairly
comparable once both sides have >= ~30 days of prior bars (the longest
zone lifetime).  Rule: e0 = max(first epochs) + 30d, e1 = min(lasts).
"""

import csv
import sys
from collections import defaultdict


def load(path, e0=0, e1=0):
    """-> {(t_epoch, gen): [(kind, lo, hi, strength, zid), ...]}"""
    out = defaultdict(list)
    with open(path, newline="", encoding="ascii") as f:
        for r in csv.DictReader(f):
            te = int(r["t_epoch"])
            if (e0 and te < e0) or (e1 and te > e1):
                continue
            out[(te, r["gen"])].append((r["kind"], float(r["lo"]),
                                        float(r["hi"]),
                                        float(r["strength"]),
                                        int(r["zid"])))
    return out


def match_zone(zones_py, zones_mq, tol):
    """Every py zone must find an unused mq zone within tol (and vice
    versa through equal cardinality).  Greedy nearest-first is fine at
    these set sizes (<= 6 armed zones per gen per bar)."""
    if len(zones_py) != len(zones_mq):
        return False
    used = [False] * len(zones_mq)
    for k, lo, hi, _s, _z in zones_py:
        best, best_d = -1, tol
        for i, (k2, lo2, hi2, _s2, _z2) in enumerate(zones_mq):
            if used[i] or k2 != k:
                continue
            d = max(abs(lo - lo2), abs(hi - hi2))
            if d <= best_d:
                best, best_d = i, d
        if best < 0:
            return False
        used[best] = True
    return True


def main():
    py_path, mq_path = sys.argv[1], sys.argv[2]
    tol = 1e-5  # 0.1 pip @5dp
    if len(sys.argv) > 3 and not sys.argv[3].startswith("--"):
        tol = float(sys.argv[3])
    report = None
    if "--report" in sys.argv:
        report = sys.argv[sys.argv.index("--report") + 1]
    e0 = int(sys.argv[sys.argv.index("--e0") + 1]) if "--e0" in sys.argv else 0
    e1 = int(sys.argv[sys.argv.index("--e1") + 1]) if "--e1" in sys.argv else 0
    py = load(py_path, e0, e1)
    mq = load(mq_path, e0, e1)
    for tag, d in (("py", py), ("mq", mq)):
        if d:
            es = [k[0] for k in d]
            print("%s epochs       : %d keys, %d .. %d"
                  % (tag, len(d), min(es), max(es)))
    keys = sorted(set(py) | set(mq))
    ident, miss_py, miss_mq, diff = 0, 0, 0, 0
    diffs = []
    for key in keys:
        a, b = py.get(key), mq.get(key)
        if a is None:
            miss_py += 1
            diffs.append((key, "MQL5-only", None, None))
            continue
        if b is None:
            miss_mq += 1
            diffs.append((key, "PY-only", None, None))
            continue
        if match_zone(a, b, tol):
            ident += 1
        else:
            diff += 1
            diffs.append((key, "bounds", a, b))
    total = len(keys)
    shared = ident + diff
    pct = 100.0 * ident / total if total else 0.0
    pct_shared = 100.0 * ident / shared if shared else 0.0
    print("bars compared : %d (epoch,gen) keys" % total)
    print("shared bars   : %d (present in both files)" % shared)
    print("identical     : %d" % ident)
    print("bounds diff   : %d" % diff)
    print("missing in py : %d" % miss_py)
    print("missing in mq : %d" % miss_mq)
    print("identical %%   : %.4f%%  of union (target >= 99.5%%)" % pct)
    print("overlap %%     : %.4f%%  of shared keys (diagnostic)" % pct_shared)
    print("verdict       : %s" % ("PASS" if pct >= 99.5 else "FAIL"))
    if report:
        with open(report, "w", encoding="utf-8") as f:
            for key, kind, a, b in diffs:
                f.write("%s\t%s\tpy=%s\tmq=%s\n" % (key, kind, a, b))
        print("diff detail   : %s (%d rows)" % (report, len(diffs)))
    return 0 if pct >= 99.5 else 1


if __name__ == "__main__":
    sys.exit(main())
