"""c1_ranker_cv.py — §40.4.5: a ranker trained on the ENGINE's live
set (not the lab stream).  Question: among the live BOXes at each
covered golden's tau, can a <=4-feature score put the match on top
more often than the engine's own `score`?

Data: livedump_<variant>_<hash>.json — per scorable golden, the live
boxes at tau with features and the match flag.  Positives are only the
coverable goldens (9 under bxsup_on) — the ruling's "119 goldens are
few" caveat is sharper here: LODO trains on <=8 positives.

Protocol (R9a / R23 §23.3):
- features: touches, log(age+1), prom_abr, height  (4, all present on
  every live box; box_rank only covers ~half the routes so excluded)
- logistic regression, standardised on the TRAIN fold, plain GD
- leave-one-DAY-out over the golden's panel date
- shuffle control: 150 permutations of the match flag inside each
  panel's box list, whole pipeline rerun
- baselines: engine `score` rank, `box_rank` (fallback score)

Usage: python c1_ranker_cv.py [variant hash]
       default bxsup_on cfb862d4
"""
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)

import numpy as np                     # noqa: E402
import common as C                      # noqa: E402

FEATS = ("touches", "age", "prom_abr", "height")


def _X(boxes):
    return [[b["touches"], math.log1p(b["age"]), b["prom_abr"],
             b["height"]] for b in boxes]


def _fit(X, y, it=400, lr=0.5, l2=1.0):
    """tiny standardising logistic, numpy GD; returns (mu, sd, w, b)."""
    X = np.asarray(X, float); y = np.asarray(y, float)
    mu = X.mean(0); sd = X.std(0) + 1e-9
    Xs = (X - mu) / sd
    w = np.zeros(X.shape[1]); b = 0.0
    n = len(Xs)
    for _ in range(it):
        p = 1.0 / (1.0 + np.exp(-np.clip(Xs @ w + b, -30, 30)))
        e = p - y
        w -= lr * (Xs.T @ e / n + l2 * w / n)
        b -= lr * e.mean()
    return mu, sd, w, b


def _score(mu, sd, w, b, box):
    r = np.array([box["touches"], math.log1p(box["age"]),
                  box["prom_abr"], box["height"]])
    return float(b + w @ ((r - mu) / sd))


def _lodo_hits(rows, dates, shuffle=None):
    """rows: coverable golden rows.  Returns hits / total."""
    hits = 0; tot = 0
    dayset = sorted(set(dates.values()))
    for hold in dayset:
        trX, trY = [], []
        for r in rows:
            if dates[r["panel"]] == hold:
                continue
            for i, bx in enumerate(r["boxes"]):
                trX.append([bx["touches"], math.log1p(bx["age"]),
                            bx["prom_abr"], bx["height"]])
                trY.append(1 if bx["match"] else 0)
        if not trX or not any(trY):
            continue
        mu, sd, w, b = _fit(trX, trY)
        for r in rows:
            if dates[r["panel"]] != hold:
                continue
            boxes = r["boxes"]
            if shuffle is not None:
                mflag = [bx["match"] for bx in boxes]
                shuffle.shuffle(mflag)
            scs = [_score(mu, sd, w, b, bx) for bx in boxes]
            top = max(range(len(boxes)), key=lambda i: scs[i])
            m = [bx["match"] for bx in boxes]
            if shuffle is not None:
                m = mflag
            tot += 1
            hits += 1 if m[top] else 0
    return hits, tot


def main():
    var = sys.argv[1] if len(sys.argv) > 1 else "bxsup_on"
    h8 = sys.argv[2] if len(sys.argv) > 2 else "cfb862d4"
    d = json.load(open(os.path.join(
        HERE, "c1_runs", "livedump_%s_%s.json" % (var, h8))))
    rows = [r for r in d["rows"] if r.get("match_rank") is not None]
    recs = C.load_tune()
    dates = {r["id"]: r["date"] for r in recs}
    print("coverable goldens: %d  live boxes: %d  days: %d" % (
        len(rows), sum(r["n_live_box"] for r in rows),
        len(set(dates[r["panel"]] for r in rows))))

    # baselines
    eng = sum(1 for r in rows
              if max(range(len(r["boxes"])),
                     key=lambda i: r["boxes"][i]["score"])
              in [i for i, b in enumerate(r["boxes"]) if b["match"]])
    brk = sum(1 for r in rows
              if max(range(len(r["boxes"])),
                     key=lambda i: (r["boxes"][i]["box_rank"]
                                    if r["boxes"][i]["box_rank"] is not None
                                    else r["boxes"][i]["score"]))
              in [i for i, b in enumerate(r["boxes"]) if b["match"]])
    print("engine score hit@1:  %d/%d" % (eng, len(rows)))
    print("box_rank   hit@1:  %d/%d" % (brk, len(rows)))

    hits, tot = _lodo_hits(rows, dates)
    print("LODO logistic hit@1: %d/%d  (feats %s)" % (hits, tot, FEATS))

    rng = random.Random(7)
    dist = []
    for _ in range(150):
        h, t = _lodo_hits(rows, dates, shuffle=rng)
        dist.append(h / max(1, t))
    dist.sort()
    p = sum(1 for x in dist if x >= hits / max(1, tot)) / len(dist)
    print("shuffle hit@1: med %.3f  p95 %.3f  max %.3f | P(rand>=obs)=%.3f"
          % (dist[len(dist) // 2], dist[int(.95 * len(dist))],
             dist[-1], p))


if __name__ == "__main__":
    main()
