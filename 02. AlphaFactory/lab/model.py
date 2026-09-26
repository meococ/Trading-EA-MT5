"""Model layer: learn direction weights on the feature stack.

HistGradientBoosting classifier predicting sign of forward 60-min return,
with PURGED + EMBARGOED time-series CV (no leakage across the boundary).
Outputs per-fold IC/AUC + per-year stability — a model is only interesting
if it is positive in BOTH halves and most years, like any other mechanism.
"""
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

import data_plane
import features


def build_matrix(sym, horizon=60):
    """Feature matrix X + label y (sign of fwd return over horizon bars)."""
    df = data_plane.load(sym)
    pip = data_plane.pip_size(sym)
    c = df["c"]
    fwd = (c.shift(-horizon) - c) / pip
    y = np.sign(fwd)
    X = pd.DataFrame(index=df.index)
    for k in (5, 15, 30, 60, 120, 240):
        X[f"ret{k}"] = features.ret_k(df, k) / pip
    X["vol_z60"] = features.vol_z(df, 60)
    X["vol_z240"] = features.vol_z(df, 240)
    X["gap"] = features.day_open_gap(df, pip).fillna(0)
    X["rng1"] = (df["h"] - df["l"]) / pip
    X["rng15"] = ((df["h"] - df["l"]).rolling(15).sum()) / pip
    X["mod"] = df["mod"]
    X["dow"] = df["dow"]
    X["consec5"] = features.consec_bars(df, 5)
    ok = (~df["suspect"]) & y.notna() & X.notna().all(axis=1) & (y != 0)
    # label window must also be clean: count suspect bars in (t, t+horizon]
    sus_cum = df["suspect"].astype(np.int8).cumsum()
    fwd_sus = sus_cum.shift(-horizon) - sus_cum
    ok &= (fwd_sus.fillna(1) == 0)
    return X[ok], y[ok].astype(int)


def purged_cv_eval(sym, horizon=60, n_splits=5, embargo=240):
    """Walk-forward folds with embargo between train and test."""
    X, y = build_matrix(sym, horizon)
    n = len(X)
    fold = n // (n_splits + 1)
    rows = []
    for i in range(n_splits):
        te0 = fold * (i + 1)
        te1 = te0 + fold
        tr_end = te0 - embargo
        if tr_end < fold:
            continue
        clf = HistGradientBoostingClassifier(
            max_iter=200, max_depth=4, learning_rate=0.06,
            early_stopping=True, random_state=7)
        clf.fit(X.iloc[:tr_end], y.iloc[:tr_end])
        p = clf.predict_proba(X.iloc[te0:te1])[:, 1]
        yt = y.iloc[te0:te1]
        auc = roc_auc_score(yt, p)
        # IC: correlation of prob edge with realized sign
        ic = np.corrcoef(p - 0.5, yt * 2 - 1)[0, 1]
        # economic: trade only when |p-0.5| > 0.06 -> next-bar fwd sign acc
        conv = np.abs(p - 0.5) > 0.06
        acc = (np.sign(p[conv] - 0.5) == (yt[conv] * 2 - 1)).mean() \
            if conv.sum() > 30 else np.nan
        rows.append({"fold": i, "auc": auc, "ic": ic,
                     "conv_acc": acc, "conv_n": int(conv.sum())})
        print(f"  {sym} fold{i}: AUC={auc:.3f} IC={ic:.4f} "
              f"conv_acc={acc:.3f} n={conv.sum()}", flush=True)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    syms = sys.argv[1:] or ["EURUSD", "USDCHF"]
    for s in syms:
        print(f"=== {s} ===")
        r = purged_cv_eval(s)
        print(r.describe().loc[["mean", "min", "max"]].to_string())
