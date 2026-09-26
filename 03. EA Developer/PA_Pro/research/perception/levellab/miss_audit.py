"""miss_audit — for every golden LEVEL_CARRIED the lab misses under
eval_v2, report the price gap to the closest candidate/born object and
what alternative price choices would have scored.

Run: python -X utf8 miss_audit.py [--limit N]
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
import common as C  # noqa: E402
import levels_lab  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    recs = bars_cache.tune_records()
    if args.limit:
        recs = recs[:args.limit]
    days = bars_cache.days()
    near = []   # misses with a candidate inside the golden span
    for rec in recs:
        day = days[rec["date"]]
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        e = levels_lab.LevelLabEngine(params={"sess_grace_bars": 48})
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
              and g["spec_type"] == "LEVEL_CARRIED"]
        eo2 = E2.eng_objects(e, day["m"], w0, w1)
        p2, _ = C.match_panel(g2, eo2, [], [], day["m"],
                              E2.match, E2.match_mark, E2.score)
        mg = {gi for gi, _ in p2}
        for gi, g in enumerate(g2):
            if gi in mg or g.get("price") is None:
                continue
            gp = g["price"] * 1e4
            tol = E2.tol_px(g)
            # closest born object (any level type) overlapping golden span
            bo = [eo for eo in eo2 if eo["type"] in E2.LEVEL_TYPES]
            born_gap = min(
                (abs(eo.get("price", -9e9) - gp) for eo in bo),
                default=None)
            # born objects within 5p, with their live spans
            bn = sorted(
                ((abs(eo["price"] - gp), eo["price"],
                  eo.get("t_birth"), eo.get("t1"), eo["type"])
                 for eo in bo if abs(eo.get("price", -9e9) - gp) <= 5),
                key=lambda x: x[0])[:3]
            # candidates inside the golden span, sorted by |price gap|
            cs = []
            for cd in e.cand_log or []:
                im = day["m"][min(cd["idx"], len(day["m"]) - 1)]
                if not (g["t0"] <= im <= g["t1"]):
                    continue
                cs.append((abs(cd["price"] - gp), cd["price"], im,
                           cd.get("n_def"), cd.get("n_piv"),
                           cd.get("outcome")))
            cs.sort()
            near.append({"id": rec["id"], "gp": round(gp, 1),
                         "tol": tol, "gspan": [g["t0"], g["t1"]],
                         "born_gap":
                         round(born_gap, 2) if born_gap is not None
                         else None,
                         "born": [(round(d, 1), round(p, 1), tb, t1, ty)
                                  for d, p, tb, t1, ty in bn],
                         "cands": [(round(d, 2), round(p, 1), t, nd, npv,
                                    oc)
                                   for d, p, t, nd, npv, oc in cs[:4]]})
    print("missed LEVEL_CARRIED:", len(near))
    for n in near:
        print(json.dumps(n, default=str))


if __name__ == "__main__":
    main()
