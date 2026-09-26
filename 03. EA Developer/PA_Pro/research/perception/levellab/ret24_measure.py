"""ret24_measure — re-measure the birth-on-return feature under the
protocol (R16 §16.3 handoff -> REQ-L2 decision).

Feature: for each production LEVEL_CARRIED/MINI_LEVEL proposal, did any
bar extreme trade back within the level's tol band within 24 bars of the
proposal (bars idx+1..idx+24)? Label right = funnel rule (price within
golden tol AND proposal minute inside golden span).

Protocol: AUC overall + per day-level 5-fold; a fold with too few
positives is inconclusive, not a pass.

Run: python -X utf8 ret24_measure.py [--limit N]
"""
import argparse
import bisect
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
import engine as ENG  # noqa: E402
from select_eval import auc  # noqa: E402

K = 24


def collect(recs):
    days = bars_cache.days()
    rows = []
    for rec in recs:
        day = days[rec["date"]]
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        e = EV.run_engine(ENG.PerceptionEngine, day["m"], day["t"],
                          day["o"], day["h"], day["l"], day["c"], w1)
        gobjs, _, _ = EV.gold_objects(rec)
        for g in gobjs:
            if g.get("t0") is None:
                g["t0"] = w0
            if g.get("t1") is None:
                g["t1"] = w1
        g2 = [g for g in gobjs if E2.scorable(g, w0, w1)
              and g["spec_type"] in E2.LEVEL_TYPES]
        seen = set()
        for cd in e.cand_log or []:
            if cd["kind"] not in E2.LEVEL_TYPES or \
                    cd.get("price") is None:
                continue
            i = min(cd["idx"], len(day["m"]) - 1)
            key = (round(cd["price"], 1), i)
            if key in seen:
                continue
            seen.add(key)
            p = cd["price"]
            ret = 0
            for j in range(i + 1, min(i + 1 + K, len(day["m"]))):
                if abs(day["h"][j] - p) <= 1.5 or \
                        abs(day["l"][j] - p) <= 1.5:
                    ret = 1
                    break
            im = day["m"][i]
            y = any(g.get("price") is not None and
                    g["t0"] <= im <= g["t1"] and
                    abs(p - g["price"] * 1e4) <= E2.tol_px(g)
                    for g in g2)
            rows.append({"panel": rec["id"], "date": rec["date"],
                         "ret24": ret, "y": y})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    recs = bars_cache.tune_records()
    if args.limit:
        recs = recs[:args.limit]
    rows = collect(recs)
    with open(os.path.join(_HERE, "ret24_cands.jsonl"), "w",
              encoding="utf8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    pos = sum(r["y"] for r in rows)
    print("cands %d  right %d (%.3f)  ret24=1 share %.3f"
          % (len(rows), pos, pos / max(len(rows), 1),
             sum(r["ret24"] for r in rows) / max(len(rows), 1)))
    dates = sorted({r["date"] for r in rows})
    folds = [set(dates[i::5]) for i in range(5)]
    print("ret_24 AUC overall: %.3f" % (auc(rows, "ret24") or float("nan")))
    for i in range(5):
        fr = [r for r in rows if r["date"] in folds[i]]
        fp = sum(r["y"] for r in fr)
        a = auc(fr, "ret24")
        print("  fold%d: AUC %s  (n=%d pos=%d%s)"
              % (i, "----" if a is None else "%.3f" % a,
                 len(fr), fp, "  INCONCLUSIVE<10pos" if fp < 10 else ""))


if __name__ == "__main__":
    main()
