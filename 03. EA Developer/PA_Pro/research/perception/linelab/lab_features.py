"""lab_features — per-feature AUC on the candidate dump, day-level
5-fold over TUNE dates.  Keeps only features with AUC >= 0.60 on
EVERY fold (Ruling-9a protocol: no fitted weights, equal-rank combine).
"""

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
DUMP = os.path.join(_HERE, "cand_dump.jsonl")

FEATS = ["nt", "over_p", "wick_over", "span", "slope_abr_hr", "fresh",
         "recent_touches", "nt_per_span", "struct_first", "ema_side",
         "dist_to_last_p", "anch_bar_ext", "prox_abr", "age_min",
         "score", "rel_nt", "rel_score", "rel_span", "is_best"]

# feature direction: '-' means lower-is-better (invert before AUC)
INV = {"over_p", "wick_over", "prox_abr", "age_min", "slope_abr_hr",
       "dist_to_last_p"}


def auc(pos, neg):
    """Rank-based AUC of feature values (higher = more positive)."""
    if not len(pos) or not len(neg):
        return float("nan")
    v = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(v))          # ranks 0..n-1
    rp = r[:len(pos)]
    return float((rp.sum() - len(pos) * (len(pos) - 1) / 2)
                 / (len(pos) * len(neg)))


def main():
    rows = [json.loads(x) for x in open(DUMP, encoding="utf8")]
    # first-match labeling: only the earliest candidate matching each
    # golden line counts as positive (the draw moment); later dupes and
    # never-matched candidates are negatives.  --mode any keeps all
    # matches positive (geometry ranking).
    mode = sys.argv[1] if len(sys.argv) > 1 else "first"
    if mode == "first":
        first = {}
        for r in rows:
            if r["label"]:
                k = r["label"]
                if k not in first or r["i"] < first[k]:
                    first[k] = r["i"]
        for r in rows:
            r["pos"] = bool(r["label"]) and r["i"] == first[r["label"]]
    else:
        for r in rows:
            r["pos"] = bool(r["label"])
    print("mode=%s cands %d, positives %d"
          % (mode, len(rows), sum(r["pos"] for r in rows)))
    # relative features: candidate's standing within its own trigger
    # event (panel, bar i) — causal: all competitors share the same i.
    by_ev = {}
    for r in rows:
        by_ev.setdefault((r["panel"], r["i"]), []).append(r)
    for ev, grp in by_ev.items():
        mx_nt = max(g["nt"] for g in grp)
        mx_sc = max(g["score"] for g in grp)
        mx_sp = max(g["span"] for g in grp)
        for g in grp:
            g["rel_nt"] = g["nt"] - mx_nt      # 0 = best in event
            g["rel_score"] = g["score"] - mx_sc
            g["rel_span"] = g["span"] - mx_sp
            g["is_best"] = float(g["score"] >= mx_sc)

    dates = sorted({r["date"] for r in rows})
    folds = [set(dates[k::5]) for k in range(5)]
    for fname in FEATS:
        per = []
        inv = fname in INV

        def fv(r):
            v = r.get(fname)
            if v is None:
                return 0.0
            if isinstance(v, bool):
                v = float(v)
            return -v if inv else v

        for fd in folds:
            sub = [r for r in rows if r["date"] in fd]
            pos = np.array([fv(r) for r in sub if r["pos"]])
            neg = np.array([fv(r) for r in sub if not r["pos"]])
            per.append(auc(pos, neg))
        pos = np.array([fv(r) for r in rows if r["pos"]])
        neg = np.array([fv(r) for r in rows if not r["pos"]])
        overall = auc(pos, neg)
        tag = "-" if inv else "+"
        print("%-14s %s folds=%s overall=%.3f %s"
              % (fname, tag, ["%.2f" % x for x in per],
                 overall,
                 "KEEP" if min(per) >= 0.60 else "drop"))


if __name__ == "__main__":
    main()
