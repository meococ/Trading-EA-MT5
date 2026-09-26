"""_box_auc.py — BOX selection features on FUNNEL labels (R15 §15.1):
prom_abr and box height (hgt = (top-bottom)/abr, inverted per
BOX-LAB: golden boxes are short).  Per-fold AUC via _auc.auc.

Usage: python _box_auc.py <hash>
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
import cache as CA                    # noqa: E402
import engine as ENG1                 # noqa: E402
from _auc import auc                  # noqa: E402


def main():
    eng_hash = sys.argv[1]
    lab_path = os.path.join(
        HERE, "evalcheck", "labels_v1_%s.jsonl" % eng_hash)
    lab = {}
    for r in map(json.loads, open(lab_path, encoding="utf8")):
        if r["src"] == "cand":
            lab[(r["panel"], r["cand_seq"])] = r["label"]
    recs = C.load_tune()
    rows = []
    for rec in recs:
        e = CA.run(eng_hash, ENG1.PerceptionEngine, rec)
        for seq, cd in enumerate(e.cand_log):
            if cd["kind"] != "BOX":
                continue
            lab_ = lab.get((rec["id"], seq))
            hgt = (cd["top"] - cd["bottom"]) / cd["abr"] \
                if cd.get("abr") else None
            rows.append({"date": rec["date"], "panel": rec["id"],
                         "outcome": cd.get("outcome"),
                         "label": 1 if lab_ else 0,
                         "prom_abr": cd.get("prom_abr"),
                         "hgt": hgt,
                         "touches": cd.get("touches"),
                         "score": cd.get("score")})
    pos = sum(r["label"] for r in rows)
    print("BOX cands n=%d pos=%d" % (len(rows), pos))
    dates = sorted({r["date"] for r in rows})
    folds = [set(dates[i::5]) for i in range(5)]
    for f in ("prom_abr", "hgt", "touches", "score"):
        rs = [r for r in rows if r.get(f) is not None]
        if not rs:
            continue
        all_ = auc([r[f] for r in rs], [r["label"] for r in rs])
        per = [auc([r[f] for r in rs if r["date"] in fold],
                   [r["label"] for r in rs if r["date"] in fold])
               for fold in folds]
        ai = auc([-r[f] for r in rs], [r["label"] for r in rs])
        peri = [auc([-r[f] for r in rs if r["date"] in fold],
                    [r["label"] for r in rs if r["date"] in fold])
                for fold in folds]
        print("%-10s all=%.3f folds=%s | inv all=%.3f folds=%s"
              % (f, all_, " ".join("%.2f" % x for x in per),
                 ai, " ".join("%.2f" % x for x in peri)))
    # combined: low hgt AND high prom — equal-weight rank product
    rs = [r for r in rows if r["prom_abr"] is not None
          and r["hgt"] is not None]
    def rank(vals):
        order = np.argsort(vals)
        rk = np.empty(len(vals))
        rk[order] = np.arange(len(vals))
        return rk / max(1, len(vals) - 1)
    pr = rank([r["prom_abr"] for r in rs])
    hr = rank([-r["hgt"] for r in rs])
    combo = pr + hr
    lab_ = [r["label"] for r in rs]
    all_ = auc(combo, lab_)
    per = [auc([combo[k] for k in range(len(rs)) if rs[k]["date"] in fold],
               [lab_[k] for k in range(len(rs)) if rs[k]["date"] in fold])
           for fold in folds]
    print("combo prom+(−hgt) ranks: all=%.3f folds=%s"
          % (all_, " ".join("%.2f" % x for x in per)))


if __name__ == "__main__":
    main()
