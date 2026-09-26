"""_feat_auc.py — per-kind feature AUC on FUNNEL prefix labels.

Joins evalcheck labels (right-proposal = label not null) with cand_log
feature rows via (panel, cand_seq).  Reports per-fold AUC for every
numeric candidate feature plus a structure-age analog of LINE-LAB's
age_min:  age = proposal bar - structure t0 (bars).
"""
import collections
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "evalcheck"))
import common as C                    # noqa: E402
import eval as EV                     # noqa: E402
import pa_slots                       # noqa: E402
import engine as ENG1                 # noqa: E402
from _auc import auc                  # noqa: E402

LAB = os.path.join(HERE, "evalcheck",
                   "labels_v1_ef06f265ab84889f.jsonl")


def main():
    lab = {}
    for r in map(json.loads, open(LAB, encoding="utf8")):
        if r["src"] == "cand":
            lab[(r["panel"], r["cand_seq"])] = r["label"]
    recs = C.load_tune()
    rows = []
    with pa_slots.slot("feat_auc", timeout=300):
        for k, rec in enumerate(recs):
            w1 = rec["window"]["x1"] or 1439
            t, m, o, h, l, c = EV.day_bars(rec["date"])
            e = EV.run_engine(ENG1.PerceptionEngine, m, t, o, h, l, c,
                              w1)
            for seq, cd in enumerate(e.cand_log):
                lab_ = lab.get((rec["id"], seq))
                row = {"kind": cd["kind"], "date": rec["date"],
                       "panel": rec["id"], "seq": seq,
                       "idx": cd["idx"],
                       "label": 1 if lab_ else 0,
                       "outcome": cd.get("outcome")}
                # structure-age analog of LINE-LAB's age_min:
                # proposal bar minus structure start, in bars/min
                t0 = cd.get("t0")
                row["age_bars"] = (cd["idx"] - t0) \
                    if t0 is not None else None
                row["age_min"] = row["age_bars"] * 5 \
                    if row["age_bars"] is not None else None
                for fk, fv in cd.items():
                    if isinstance(fv, (int, float)) and \
                            fk not in ("idx", "t0", "t1"):
                        row.setdefault("f_" + fk, fv)
                rows.append(row)
            if (k + 1) % 50 == 0:
                print("  %d/%d" % (k + 1, len(recs)), flush=True)
    json.dump(rows, open("_feat_lab_rows.json", "w"))
    # arrival-order diagnostic: right proposals that hit a full window
    # vs lost a score race, per kind
    import collections
    panel_births = collections.defaultdict(
        lambda: collections.defaultdict(list))
    for r in rows:
        if r["outcome"] == "born":
            panel_births[r["panel"]][r["kind"]].append(r["idx"])
            panel_births[r["panel"]]["*"].append(r["idx"])
    RATE = {"BRACKET": 2, "BOX": 1, "LEVEL_CARRIED": 1}
    for kind in ("BRACKET", "BOX", "LEVEL_CARRIED"):
        sub = [r for r in rows if r["kind"] == kind]
        early_k = early_j = late = won = 0
        for r in sub:
            if not r["label"]:
                continue
            if r["outcome"] == "born":
                won += 1
                continue
            pb = panel_births[r["panel"]]
            pk = sum(1 for b in pb[kind] if r["idx"] - 72 <= b < r["idx"])
            pj = sum(1 for b in pb["*"] if r["idx"] - 72 <= b < r["idx"])
            if pk >= RATE[kind]:
                early_k += 1
            elif pj >= 5:
                early_j += 1
            else:
                late += 1
        print("%s right non-born: kind-window-full=%d joint-full=%d "
              "slot-free-on-arrival=%d (born %d)"
              % (kind, early_k, early_j, late, won))
    dates = sorted({r["date"] for r in rows})
    folds = [set(dates[i::5]) for i in range(5)]
    feats = sorted({k for r in rows for k in r
                    if k.startswith("f_") or k.startswith("age")})
    for kind in ("BOX", "BRACKET", "LEVEL_CARRIED", "PATTERN_LINE"):
        sub = [r for r in rows if r["kind"] == kind]
        pos = sum(r["label"] for r in sub)
        print("\n== %s  n=%d pos=%d ==" % (kind, len(sub), pos))
        for f in feats:
            rs = [r for r in sub if r.get(f) is not None]
            if len(rs) < 200 or sum(r["label"] for r in rs) < 10:
                continue
            all_ = auc([r[f] for r in rs], [r["label"] for r in rs])
            per = [auc([r[f] for r in rs if r["date"] in fold],
                       [r["label"] for r in rs if r["date"] in fold])
                   for fold in folds]
            ai = auc([-r[f] for r in rs], [r["label"] for r in rs])
            tag = " *" if min(per) >= 0.60 or \
                min(-x + 1 for x in per) >= 0.60 else ""
            print("  %-14s all=%.3f inv=%.3f folds=%s%s"
                  % (f, all_, ai,
                     " ".join("%.2f" % x for x in per), tag))


if __name__ == "__main__":
    main()
