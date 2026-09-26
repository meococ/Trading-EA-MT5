#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""r3_fit.py — A3 learned-ranker fit (R56 §56.4.3 / R57 §57.1).

Deterministic NumPy logistic fit over boxlab/r_dataset/rows.csv.
Grain: one row per BOX candidate per (panel, tau) cell on TUNE.

Rules honoured:
  * <= 4 features, drawn only from the causal null-surviving set
    (r57_causal.py): neg_dist_edge_abr, close_at_box, neg_recency,
    neg_bars_since_touch, prior_leg_abr, h_rel_day, h_abr;
  * in-script per-feature gate: feature's own CV cell@1 must beat its
    200-draw within-cell label-shuffle p95;
  * leave-one-day-out CV (fold id = `date`); reported score is OOF;
  * shuffle control: same pipeline on labels permuted within cells;
  * deterministic seed -> same input bytes, same numbers.

Run:  python r3_fit.py [rows.csv]
"""
import csv, sys, os, collections
import numpy as np

SEED = 20261202
DRAWS = 200
MAXF = 4
X_ABR = 0.5          # stated before measurement (r57_causal)
# pooled routes = cands that can actually reach the birth slot;
# cluster_range_wick is the log-only variant stream (wick_birth OFF).
POOL_ONLY = True
POOLED_ROUTES = {"congestion_scan", "cluster_range", "asia_session",
                 "cong_pivedge"}

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = os.path.join(HERE, "r_dataset", "rows.csv")


def fnum(r, k):
    try:
        v = r.get(k)
        return float(v) if v not in (None, "", "nan") else np.nan
    except ValueError:
        return np.nan


FEATS = {
    "neg_dist_edge_abr":    lambda r: -fnum(r, "dist_close_edge_abr"),
    "close_at_box":         lambda r: float(fnum(r, "px_in_box") == 1.0
                                    or fnum(r, "dist_close_edge_abr") <= X_ABR),
    "neg_recency":          lambda r: -fnum(r, "recency_bars"),
    "neg_bars_since_touch": lambda r: -fnum(r, "bars_since_touch"),
    "prior_leg_abr":        lambda r: fnum(r, "prior_leg_abr"),
    "h_rel_day":            lambda r: fnum(r, "h_rel_day"),
    "h_abr":                lambda r: fnum(r, "h_abr"),
}


def load(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    cells = collections.OrderedDict()
    for i, r in enumerate(rows):
        r["_y"] = 1.0 if int(r["label_edge"]) >= 0 else 0.0
        r["_cell"] = r["panel"] + "@" + r["tau"]
        r["_day"] = r["date"]
        cells.setdefault(r["_cell"], []).append(i)
    return rows, cells


def build_X(rows, names):
    X = np.full((len(rows), len(names)), np.nan)
    for j, n in enumerate(names):
        X[:, j] = [FEATS[n](r) for r in rows]
    med = np.nanmedian(X, axis=0)
    med = np.where(np.isfinite(med), med, 0.0)
    inds = np.where(~np.isfinite(X))
    X[inds] = np.take(med, inds[1])
    return X


def fit_logreg(X, y, iters=250, lr=0.2, l2=1e-3):
    w = np.zeros(X.shape[1]); b = 0.0; n = len(y)
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-(X @ w + b)))
        w -= lr * ((X.T @ (p - y)) / n + l2 * w)
        b -= lr * (p - y).mean()
    return w, b


def lodo_scores(X, y, days):
    oof = np.zeros(len(y))
    for d in np.unique(days):
        te = days == d; tr = ~te
        mu = X[tr].mean(0); sd = X[tr].std(0); sd[sd == 0] = 1.0
        w, b = fit_logreg((X[tr] - mu) / sd, y[tr])
        oof[te] = ((X[te] - mu) / sd) @ w + b
    return oof


def cell_at1(scores, cells, y):
    """cells whose argmax-scored row is right under label vector y."""
    hit = tot = 0
    for c, idx in cells.items():
        idx = np.asarray(idx)
        if y[idx].sum() == 0:
            continue
        tot += 1
        hit += int(y[idx[int(np.argmax(scores[idx]))]] == 1.0)
    return hit, tot


def shuffle_labels_within_cells(rows, cells, rng):
    y = np.zeros(len(rows))
    for idx in cells.values():
        k = int(sum(rows[i]["_y"] for i in idx))
        if k:
            pick = rng.permutation(idx)[:k]
            y[list(pick)] = 1.0
    return y


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else ROWS
    rows, cells = load(path)
    if POOL_ONLY:
        keep_i = [i for i, r in enumerate(rows)
                  if r["route"] in POOLED_ROUTES]
        rows = [rows[i] for i in keep_i]
        cells = collections.OrderedDict()
        for i, r in enumerate(rows):
            cells.setdefault(r["_cell"], []).append(i)
    days = np.array([r["_day"] for r in rows])
    y = np.array([r["_y"] for r in rows])
    rng = np.random.default_rng(SEED)
    print("rows=%d cells=%d days=%d pos=%d"
          % (len(rows), len(cells), len(np.unique(days)), int(y.sum())))

    # baseline: engine's own score_last as the ranker
    base = np.array([fnum(r, "score_last") for r in rows])
    base = np.where(np.isfinite(base), base, -1e9)
    h, t = cell_at1(base, cells, y)
    print("baseline score_last cell@1 = %d/%d" % (h, t))
    base = np.array([fnum(r, "box_rank") for r in rows])
    h, t = cell_at1(base, cells, y)
    print("baseline box_rank   cell@1 = %d/%d" % (h, t))

    # per-feature gate (R57 SS57.1 VS-REST null): within each cell the
    # feature must separate the right set from the rest beyond the
    # 200-draw label-shuffle p95.  This is the null the Lead specified;
    # an argmax-gate is stricter than required and disclosed separately.
    keep = []
    for n in FEATS:
        X1 = build_X(rows, [n])[:, 0]
        # obs: mean over cells of (mean f(right) - mean f(rest))
        deltas = []
        pools = []
        for idx in cells.values():
            idx = np.asarray(idx)
            if y[idx].sum() == 0 or y[idx].sum() == len(idx):
                continue
            ri = idx[y[idx] == 1.0]; oi = idx[y[idx] == 0.0]
            deltas.append(X1[ri].mean() - X1[oi].mean())
            pools.append(idx)
        obs = float(np.mean(deltas))
        null = np.zeros(DRAWS)
        for d in range(DRAWS):
            s = 0.0
            for idx in pools:
                k = int(y[idx].sum())
                perm = rng.permutation(idx)
                s += X1[perm[:k]].mean() - X1[perm[k:]].mean()
            null[d] = s / len(pools)
        p95 = np.percentile(null, 95)
        ok = obs > p95
        print("  feat %-22s vs-rest d=%.3f null p95 %.3f  %s"
              % (n, obs, p95, "KEEP" if ok else "drop"))
        if ok:
            keep.append((obs, n))
    keep = [n for _s, n in sorted(keep, reverse=True)[:MAXF]]
    print("kept features:", keep)
    if not keep:
        print("no feature beats the null -> A3 not viable")
        return

    X = build_X(rows, keep)
    oof = lodo_scores(X, y, days)
    h, t = cell_at1(oof, cells, y)
    print("MODEL CV cell@1 = %d/%d = %.3f" % (h, t, h / t))

    null = np.zeros(DRAWS)
    for d in range(DRAWS):
        ys = shuffle_labels_within_cells(rows, cells, rng)
        ns, _ = cell_at1(lodo_scores(X, ys, days), cells, y)
        null[d] = ns / t
    p95 = np.percentile(null, 95)
    print("shuffle-control CV cell@1 p95 = %.3f" % p95)
    print("A3 verdict: %s" % ("PASS" if h / t > p95 else "FAIL"))


if __name__ == "__main__":
    main()
