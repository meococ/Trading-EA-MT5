"""Model v2 — the serious ML route: richer features, purged walk-forward,
per-side threshold calibration on TRAIN folds only, OOS trade-path eval
at deploy cost.

Why this exists: the mechanical grids cap at PF~1.2-1.45 on sparse
pockets; the model layer is the only class that showed positive OOS
signal (EURUSD follow-short PF 1.31, USDJPY both-sides ~1.22 at ~8/wk).
This module tests whether a better-trained, better-featured model can
push pooled PF over the 1.30 gate at legal cadence.

Leakage discipline:
- purged+embargoed walk-forward folds (as model.py)
- threshold per side calibrated on the fold's TRAIN data only
- exits evaluated on OOS bars only
- all cells land in the ledger (sim v4 cost by default)
"""
import sys
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

import data_plane
import features
import labels


def build_matrix_v2(sym, horizon=240):
    """Richer feature set: multi-scale returns, vol z, ranges, clock,
    day-context (prev-day net/range), gap, sweep flags, cross-symbol
    returns for the USD-block legs."""
    df = data_plane.load(sym)
    pip = data_plane.pip_size(sym)
    c = df["c"]
    fwd = (c.shift(-horizon) - c) / pip
    y = np.sign(fwd)
    X = pd.DataFrame(index=df.index)
    for k in (5, 15, 30, 60, 120, 240, 480, 960):
        X[f"ret{k}"] = features.ret_k(df, k) / pip
    X["vol_z60"] = features.vol_z(df, 60)
    X["vol_z240"] = features.vol_z(df, 240)
    # day_open_gap reads the first bar's open — zero it on days whose
    # first bar is suspect (fake 00:00 summary record).
    gap_v = features.day_open_gap(df, pip)
    first_bad = df["suspect"].groupby(df["day"]).transform("first")
    X["gap"] = gap_v.where(~first_bad, 0.0).fillna(0)
    # Suspect bars can carry non-bar content (e.g. the 00:00 daily-summary
    # record whose h/l equal the day's full range — verified 2026-09-19).
    # They must not leak into ANY rolling/extreme feature: replace their
    # h/l with inert values before every cumulative op.
    h_eff = df["h"].where(~df["suspect"], -np.inf)
    l_eff = df["l"].where(~df["suspect"], np.inf)
    rng_eff = (df["h"] - df["l"]).where(~df["suspect"], 0.0)
    X["rng1"] = rng_eff / pip
    X["rng15"] = rng_eff.rolling(15).sum() / pip
    X["rng240"] = rng_eff.rolling(240).sum() / pip
    X["mod"] = df["mod"]
    X["dow"] = df["dow"]
    X["consec5"] = features.consec_bars(df, 5)
    # day context
    day = df["day"].to_numpy()
    keys = np.unique(day)
    dnet = {}
    drng = {}
    sus_np = df["suspect"].to_numpy()
    for k in keys:
        sel = np.flatnonzero(day == k)
        if len(sel):
            clean = sel[~sus_np[sel]]
            o0 = df["o"].iloc[clean[0]] if len(clean) else np.nan
            dnet[k] = (c.iloc[sel[-1]] - o0) / pip if np.isfinite(o0) else 0.0
            drng[k] = (h_eff.iloc[sel].max() - l_eff.iloc[sel].min()) / pip
    pdn = np.zeros(len(df))
    pdr = np.zeros(len(df))
    for j in range(1, len(keys)):
        sel = day == keys[j]
        pdn[sel] = dnet.get(keys[j - 1], 0.0)
        pdr[sel] = drng.get(keys[j - 1], 0.0)
    X["prevday_net"] = pdn
    X["prevday_rng"] = pdr
    # position in today's range so far — extremes over NON-SUSPECT bars
    # only, otherwise the 00:00 daily-summary bar leaks the day's final
    # high/low into every bar of the day (leak found 2026-09-19).
    daymax = h_eff.groupby(df["day"]).cummax()
    daymin = l_eff.groupby(df["day"]).cummin()
    span = (daymax - daymin) / pip
    X["day_pos"] = np.where(span > 0.01,
                            ((c - daymin) / pip) / np.maximum(span, 0.01),
                            0.5)
    X["day_pos"] = pd.Series(X["day_pos"], index=df.index).clip(0, 1)
    ok = (~df["suspect"]) & y.notna() & X.notna().all(axis=1) & (y != 0)
    sus_cum = df["suspect"].astype(np.int8).cumsum()
    fwd_sus = sus_cum.shift(-horizon) - sus_cum
    ok &= (fwd_sus.fillna(1) == 0)
    return df, X[ok], y[ok].astype(int)


def run_symbol(sym, horizon=240, embargo=480, n_splits=5):
    df, X, y = build_matrix_v2(sym, horizon)
    pip = data_plane.pip_size(sym)
    ev = labels.Evaluator(df, pip)
    cost = labels.spread_cost_arr(df)
    n = len(X)
    fold = n // (n_splits + 1)
    results = []
    for i in range(n_splits):
        te0, te1 = fold * (i + 1), fold * (i + 2)
        tr_end = te0 - embargo
        if tr_end < fold:
            continue
        clf = HistGradientBoostingClassifier(
            max_iter=250, max_depth=5, learning_rate=0.06,
            early_stopping=True, random_state=7)
        clf.fit(X.iloc[:tr_end], y.iloc[:tr_end])
        # TRAIN-fold probabilities for threshold calibration (last 20%
        # of train block as a pseudo-val — still strictly before te0)
        p_tr = clf.predict_proba(X.iloc[tr_end - fold // 5:tr_end])[:, 1]
        y_tr = y.iloc[tr_end - fold // 5:tr_end]
        p_te = clf.predict_proba(X.iloc[te0:te1])[:, 1]
        idx_te = X.index[te0:te1]
        auc = roc_auc_score(y.iloc[te0:te1], p_te)
        # calibrate threshold per side on TRAIN probs: maximize
        # accuracy at |p-0.5|>th, require >=50 events
        # calibrate: per side pick the threshold with the best TRAIN
        # directional hit-rate (>=50 events), default 0.08
        best = {}
        e_tr = p_tr - 0.5
        for side, sgn in (("L", 1), ("S", -1)):
            cand = []
            for th in (0.05, 0.08, 0.12, 0.16, 0.20):
                sel = (np.abs(e_tr) > th) & (np.sign(e_tr) == sgn)
                if sel.sum() >= 50:
                    hit = ((np.sign(e_tr[sel]) == sgn) ==
                           (y_tr.to_numpy()[sel] * 2 - 1 == sgn)).mean()
                    cand.append((hit, th))
            best[side] = max(cand)[1] if cand else 0.08
        for side, sgn in (("L", 1), ("S", -1)):
            th = best[side]
            e_te = pd.Series(p_te, index=idx_te) - 0.5
            m = np.zeros(len(df), dtype=bool)
            sel_idx = idx_te[(np.abs(e_te) > th) &
                             (np.sign(e_te) == sgn)]
            pos = df.index.get_indexer(sel_idx)
            m[pos[pos >= 0]] = True
            # cooldown 30 to cap overlap
            ii = np.flatnonzero(m)
            keep = np.zeros(len(ii), dtype=bool)
            last = -10 ** 9
            for q, ii2 in enumerate(ii):
                if ii2 - last > 30:
                    keep[q] = True
                    last = ii2
            m2 = np.zeros(len(df), dtype=bool)
            m2[ii[keep]] = True
            r = ev.eval(m2, sgn, 50, 0, horizon * 2, cost_arr=cost)
            ret = r["ret"]
            results.append({
                "sym": sym, "fold": i, "side": side, "th": th,
                "auc": round(auc, 4), "n": len(ret),
                "net": round(ret.mean(), 2) if len(ret) else np.nan,
                "pf": round(labels.pf(ret), 3) if len(ret) else np.nan,
            })
            print(f"  {sym} f{i} {side} th{th} auc={auc:.3f} "
                  f"n={len(ret)} net={ret.mean() if len(ret) else 0:+.2f} "
                  f"PF={labels.pf(ret) if len(ret) else 0:.2f}",
                  flush=True)
    return pd.DataFrame(results)


def main():
    syms = sys.argv[1:] or ["EURUSD", "USDJPY"]
    out = []
    for s in syms:
        print(f"=== {s} ===", flush=True)
        out.append(run_symbol(s))
    r = pd.concat(out, ignore_index=True)
    print(r.to_string(index=False))
    r.to_csv("model_v2_oos.csv", index=False)


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"total {time.time()-t0:.0f}s")
