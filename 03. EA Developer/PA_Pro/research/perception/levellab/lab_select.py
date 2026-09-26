"""lab_select — AUC of the lab proposer's candidate features on ITS OWN
stream (the §15.3 separator test, but on the lab proposal distribution
rather than the production stream).

A lab candidate is 'right' when its price is within the golden level's
tol AND the proposal bar lies inside the golden span (the funnel R11
level rule).

Run: python -X utf8 lab_select.py [--limit N]
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
sys.path.insert(0, _PERC)
sys.path.insert(0, os.path.join(_PERC, "golden"))
sys.path.insert(0, os.path.join(_PERC, "evalcheck"))
sys.path.insert(0, os.path.join(_PERC, "linelab"))

import bars_cache  # noqa: E402
import eval as EV  # noqa: E402
import eval_v2 as E2  # noqa: E402
import levels_lab  # noqa: E402
from select_eval import auc, folds  # noqa: E402

FEATS = ["n_def", "n_piv", "age_min", "dist_abr", "score"]
INV = {"age_min", "dist_abr"}


def collect(recs):
    rows = []
    for rec in recs:
        day = bars_cache.days()[rec["date"]]
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        e = levels_lab.LevelLabEngine(
            params={"sess_grace_bars": 48})
        e.cand_log = []
        for i in range(len(day["m"])):
            if day["m"][i] > w1:
                break
            e.update(day["t"][i], day["o"][i] / 1e4, day["h"][i] / 1e4,
                     day["l"][i] / 1e4, day["c"][i] / 1e4,
                     cet_min=int(day["m"][i]))
        gobjs, _, _ = EV.gold_objects(rec)
        for g in gobjs:
            if g.get("t0") is None:
                g["t0"] = w0
            if g.get("t1") is None:
                g["t1"] = w1
        g2 = [g for g in gobjs if E2.scorable(g, w0, w1)
              and g["spec_type"] in E2.LEVEL_TYPES]
        for cd in e.cand_log or []:
            im = day["m"][min(cd["idx"], len(day["m"]) - 1)]
            y = any(g.get("price") is not None and
                    g["t0"] <= im <= g["t1"] and
                    abs(cd["price"] - g["price"] * 1e4) <= E2.tol_px(g)
                    for g in g2)
            row = {"panel": rec["id"], "date": rec["date"], "y": y}
            for fk in FEATS:
                row[fk] = cd.get(fk)
            rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    recs = bars_cache.tune_records()
    if args.limit:
        recs = recs[:args.limit]
    rows = collect(recs)
    with open(os.path.join(_HERE, "lab_level_cands.jsonl"), "w",
              encoding="utf8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    n_pos = sum(r["y"] for r in rows)
    print("lab candidates: %d  right: %d (%.3f)"
          % (len(rows), n_pos, n_pos / max(len(rows), 1)))
    fs = folds(rows)
    print("feature      overall   " +
          "  ".join("f%d" % i for i in range(5)))
    fmt = lambda v: "  ---- " if v is None else "  %.3f" % v
    ok = []
    for feat in FEATS:
        ov = auc(rows, feat)
        pf = [auc([r for r in rows if r["date"] in fs[i]], feat)
              for i in range(5)]
        print("%-12s %s%s" % (feat, fmt(ov), "".join(fmt(v)
                                                     for v in pf)))
        if all(v is not None and v >= 0.60 for v in pf):
            ok.append(feat)
    print("\nfeatures >=0.60 all folds:", ok or "NONE")


if __name__ == "__main__":
    main()
