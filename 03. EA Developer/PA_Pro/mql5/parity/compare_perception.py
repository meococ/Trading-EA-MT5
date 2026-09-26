"""compare_perception.py - diff two per-bar perception snapshots.

Spec section 8 parity contract: the MQL5 object set per bar must match
Python within 1e-9 on prices and exactly on types/ids, on DESIGN sample
weeks, >= 99.5% of bars.

Both CSVs are perception_csv_v1 with the leading `bar_t` column (see
PA_Perception.mqh): each row is one object as seen at bar `bar_t`.
Columns: bar_t,id,type,state,role,t_birth,t1,t2,p1,p2,letter,side,why.

Join key: (bar_t).  Per bar, objects are compared as id-keyed records:
same id present on both sides, same type/state/role/side/letter, and
|t1|,|t2| equal exactly, |p1|,|p2| within tol.

Usage:
    python compare_perception.py <py_csv> <mq_csv> [tol] [--report path]
"""

import csv
import sys
from collections import defaultdict


def load(path):
    """-> {bar_t: {id: (type,state,role,t1,t2,p1,p2,letter,side)}}"""
    out = defaultdict(dict)
    with open(path, newline="", encoding="ascii") as f:
        for r in csv.DictReader(f):
            key = int(r["bar_t"])
            out[key][r["id"]] = (
                r["type"], r["state"], r["role"],
                int(r["t1"]), int(r["t2"]),
                float(r["p1"]), float(r["p2"]),
                r.get("letter", ""), r.get("side", ""))
    return out


def match_bar(py_objs, mq_objs, tol):
    if set(py_objs) != set(mq_objs):
        return False
    for oid, rec in py_objs.items():
        ty, st, ro, t1, t2, p1, p2, lt, sd = rec
        ty2, st2, ro2, u1, u2, q1, q2, lt2, sd2 = mq_objs[oid]
        if (ty, st, ro, lt, sd) != (ty2, st2, ro2, lt2, sd2):
            return False
        if t1 != u1 or t2 != u2:
            return False
        if abs(p1 - q1) > tol or abs(p2 - q2) > tol:
            return False
    return True


def main():
    py_path, mq_path = sys.argv[1], sys.argv[2]
    tol = 1e-9
    if len(sys.argv) > 3 and not sys.argv[3].startswith("--"):
        tol = float(sys.argv[3])
    report = None
    if "--report" in sys.argv:
        report = sys.argv[sys.argv.index("--report") + 1]
    py = load(py_path)
    mq = load(mq_path)
    keys = sorted(set(py) | set(mq))
    ident = miss = diff = 0
    diffs = []
    for key in keys:
        a, b = py.get(key), mq.get(key)
        if a is None or b is None:
            miss += 1
            diffs.append((key, "one-side", None, None))
            continue
        if match_bar(a, b, tol):
            ident += 1
        else:
            diff += 1
            diffs.append((key, "obj-diff", a, b))
    total = len(keys)
    pct = 100.0 * ident / total if total else 0.0
    print("bars compared : %d bar_t keys" % total)
    print("identical     : %d" % ident)
    print("object diff   : %d" % diff)
    print("missing side  : %d" % miss)
    print("identical %%   : %.4f%%  (target >= 99.5%%)" % pct)
    print("verdict       : %s" % ("PASS" if pct >= 99.5 else "FAIL"))
    if report:
        with open(report, "w", encoding="utf-8") as f:
            for key, kind, a, b in diffs:
                f.write("%s\t%s\tpy=%s\tmq=%s\n" % (key, kind, a, b))
        print("diff detail   : %s (%d rows)" % (report, len(diffs)))
    return 0 if pct >= 99.5 else 1


if __name__ == "__main__":
    sys.exit(main())
