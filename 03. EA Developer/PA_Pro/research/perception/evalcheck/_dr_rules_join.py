"""EVAL-AUDIT s.77.4(b): join the pack features CSV with the sealed key
and report each rule-variant's pass-rate BY CLASS (golden / negative /
engine hit / engine fp), aggregates only.

Rule semantics are DR-RULES' own: thresholds come from
deepresearch/DR_RULES_golden.jsonl (author q95/q90) and predicates
from DR_RULES_report.make_pass + the VARIANTS list, replicated here.

Rows where a rule is not evaluable (missing stat) are excluded from
that rule's denominator.

Run: python evalcheck/_dr_rules_join.py [csv_path]
"""
import collections
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "deepresearch"))

import DR_RULES_report as R                     # noqa: E402

KEY = os.path.join(HERE, "_owner_judge_key", "m2_c3_key.json")
GOLD = os.path.join(PERC, "deepresearch", "DR_RULES_golden.jsonl")
DEF_CSV = os.path.join(HERE, "DR_RULES_pack_features.csv")

TRUTH = {"engine_hit": "engine_hit", "engine_fp": "engine_fp",
         "golden": "golden", "control": "golden", "neg": "negative",
         "negative": "negative"}

VARIANTS = []
for v in ("0.5", "1.0"):
    VARIANTS.append(("C1@" + v, ("box", "level")))
VARIANTS.append(("C1p@2", ("box", "level")))
for v in ("q95", "q90"):
    VARIANTS.append(("C2@" + v, ("box", "level", "line")))
for v in ("2.5", "3.0"):
    VARIANTS.append(("C3@" + v, ("box",)))
for v in ("3", "4"):
    VARIANTS.append(("C4@" + v, ("box",)))
for v in ("q95", "q90", "20"):
    VARIANTS.append(("C5@" + v, ("box",)))
VARIANTS.append(("C6@clu", ("box",)))
for v in ("2", "3"):
    VARIANTS.append(("C7@" + v, ("level", "line")))
    VARIANTS.append(("C7s@" + v, ("level", "line")))
VARIANTS.append(("C7f@2", ("level", "line")))
for v in ("1", "2"):
    VARIANTS.append(("C8@" + v, ("level",)))
    VARIANTS.append(("C8a@" + v, ("level",)))
for v in ("2.5", "3.0"):
    VARIANTS.append(("C3w@" + v, ("box",)))
for v in ("3", "4"):
    VARIANTS.append(("C4w@" + v, ("box",)))
for v in ("q95", "q90", "20"):
    VARIANTS.append(("C5w@" + v, ("box",)))


def cls_of(krow):
    t = (krow.get("truth") or krow.get("src") or "").lower()
    return TRUTH.get(t, t)


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else DEF_CSV
    key = json.load(open(KEY))["key"]
    gold = [json.loads(x) for x in open(GOLD, encoding="utf8")]
    g_by_fam = collections.defaultdict(list)
    for r in gold:
        g_by_fam[r["fam"]].append(r)
    thr = {}
    for f in ("box", "level", "line"):
        vs = [r.get("c2_s") for r in g_by_fam[f]]
        thr[("C2", f, "q95")] = R.q(vs, 95)
        thr[("C2", f, "q90")] = R.q(vs, 90)
    wb = [r.get("width_bars") for r in g_by_fam["box"]]
    thr[("C5", "box", "q95")] = R.q(wb, 95)
    thr[("C5", "box", "q90")] = R.q(wb, 90)
    ww = [r.get("width_win_bars") for r in g_by_fam["box"]]
    thr[("C5w", "box", "q95")] = R.q(ww, 95)
    thr[("C5w", "box", "q90")] = R.q(ww, 90)
    print("author thresholds: C2 q95 " +
          str({f: round(thr[("C2", f, "q95")], 4)
               for f in ("box", "level", "line")}) +
          " | C5 box q95=%.1f q90=%.1f | C5w q95=%.1f"
          % (thr[("C5", "box", "q95")], thr[("C5", "box", "q90")],
             thr[("C5w", "box", "q95")]))
    _p = R.make_pass(thr)

    def p_of(rv, r):
        # DR_RULES_report.main's p_of dispatch (C2/C5/C5w special);
        # everything else falls through to make_pass.
        rid = rv.split("@")[0]
        if rid == "C2":
            return (None if r.get("c2_s") is None else
                    r["c2_s"] <= thr[("C2", r["fam"], rv.split("@")[1])])
        if rid == "C5":
            v = r.get("width_bars")
            if v is None:
                return None
            var = rv.split("@")[1]
            w = thr[("C5", "box", var)] if var in ("q90", "q95") \
                else float(var)
            return v <= w
        if rid == "C5w":
            v = r.get("width_win_bars")
            if v is None:
                return None
            var = rv.split("@")[1]
            w = thr[("C5w", "box", var)] if var in ("q90", "q95") \
                else float(var)
            return v <= w
        return _p(rv, r)

    def num(r):
        out = {}
        for k, v in r.items():
            if k in ("seq", "panel", "fam", "spec_type", "c8_pol",
                     "prec", "degenerate", "state"):
                out[k] = v
            elif v in (None, "", "NA"):
                out[k] = None
            else:
                try:
                    out[k] = float(v)
                except (TypeError, ValueError):
                    out[k] = v
        return out

    rows = [num(r) for r in csv.DictReader(open(csv_path,
                                              encoding="utf8"))]
    classes = ["golden", "negative", "engine_hit", "engine_fp"]
    n_cls = collections.Counter()
    joined = []
    for r in rows:
        krow = key.get((r.get("seq") or "").strip())
        if krow is None:
            continue
        cls = cls_of(krow)
        r["_cls"] = cls
        n_cls[cls] += 1
        joined.append(r)
    print("joined seqs: %d | classes: %s" % (len(joined), dict(n_cls)))
    hdr = ["rule"] + ["%s(n)" % c for c in classes]
    print("\n" + " | ".join(hdr))
    print("-" * 96)
    for rv, fams in VARIANTS:
        cells = [rv]
        for c in classes:
            sel = [r for r in joined if r["_cls"] == c
                   and r.get("fam") in fams]
            ev = [(r, p_of(rv, r)) for r in sel]
            ev = [(r, p) for r, p in ev if p is not None]
            n = len(ev)
            p = sum(1 for _r, p in ev if p)
            cells.append("%d/%d %.2f" % (p, n, p / n if n else 0)
                         if n else "-")
        print(" | ".join(cells))


if __name__ == "__main__":
    main()
