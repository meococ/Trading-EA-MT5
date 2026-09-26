"""select_levels — V3 production-stream selection measure for LEVELS.

Same protocol as linelab/select_eval.py (EVAL-AUDIT R11 prefix-consistent
labels via funnel.cand_right/best_cand_match), restricted to
LEVEL_CARRIED + MINI_LEVEL candidates.

Derived feats added per candidate:
  age_min    : (idx - t_left) * 5      age of the level's left edge
  dist_abr   : |price - close| / abr   distance to price at proposal
  span_min   : (t1 - t0) * 5           proposed span

Run:  python -X utf8 select_levels.py [--limit N]
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
sys.path.insert(0, _PERC)
sys.path.insert(0, os.path.join(_PERC, "evalcheck"))
sys.path.insert(0, os.path.join(_PERC, "golden"))
sys.path.insert(0, os.path.join(_PERC, "linelab"))

import common as C          # noqa: E402
import eval as EV           # noqa: E402
import eval_v2 as V2        # noqa: E402
import funnel as F          # noqa: E402
import engine as ENG        # noqa: E402
from select_eval import auc, folds  # noqa: E402

FEATS = ["touches", "prom_abr", "z_near", "z_far", "depth", "score",
         "age_min", "dist_abr", "span_min"]
INV = {"age_min", "dist_abr"}


def collect(recs):
    rows = []
    for rec in recs:
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        t, m, o, h, l, c = EV.day_bars(rec["date"])
        e = EV.run_engine(ENG.PerceptionEngine, m, t, o, h, l, c, w1)
        gobjs, gmarks, gkeys, gmkeys = F.gold_with_keys(rec)
        g2 = [g for g in gobjs
              if V2.scorable(g, w0, w1)
              and g["spec_type"] in V2.LEVEL_TYPES]
        seen = set()
        for cd in e.cand_log or []:
            if cd["kind"] not in V2.LEVEL_TYPES:
                continue
            r = F.cand_as_record(cd, m, w0, w1)
            if r is None:
                continue
            key = (cd["kind"], cd.get("route"), r.get("t0"),
                   r.get("price"))
            if key in seen:
                continue
            seen.add(key)
            row = {"panel": rec["id"], "date": rec["date"],
                   "kind": cd["kind"], "route": cd.get("route"),
                   "y": F.best_cand_match(r, g2, m) is not None,
                   "outcome": cd.get("outcome")}
            for fk in FEATS:
                row[fk] = cd.get(fk)
            row["age_min"] = ((cd.get("idx") or 0) - (cd.get("t_left")
                              or cd.get("t0") or 0)) * 5
            if cd.get("price") is not None and cd.get("abr"):
                row["dist_abr"] = abs(cd["price"] - cd["close"]) / cd["abr"]
            if cd.get("t1") is not None and cd.get("t0") is not None:
                row["span_min"] = (cd["t1"] - cd["t0"]) * 5
            rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    recs = C.load_tune()
    if args.limit:
        recs = recs[:args.limit]
    rows = collect(recs)
    out = os.path.join(_HERE, "select_level_cands.jsonl")
    with open(out, "w", encoding="utf8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    for kind in V2.LEVEL_TYPES:
        sub = [r for r in rows if r["kind"] == kind]
        n_pos = sum(r["y"] for r in sub)
        print("%s candidates: %d  right: %d (%.3f)"
              % (kind, len(sub), n_pos, n_pos / max(len(sub), 1)))
        fs = folds(sub)
        print("feature      overall   " +
              "  ".join("f%d" % i for i in range(5)))
        fmt = lambda v: "  ---- " if v is None else "  %.3f" % v
        for feat in FEATS:
            ov = auc(sub, feat)
            pf = [auc([r for r in sub if r["date"] in fs[i]], feat)
                  for i in range(5)]
            print("%-12s %s%s" % (feat, fmt(ov), "".join(fmt(v)
                                                         for v in pf)))


if __name__ == "__main__":
    main()
