"""Model-fade probe: OOS purged-CV probabilities -> trade the model's
high-conviction errors. Prior finding: conv_acc 0.26-0.42 means the
model's confident calls systematically revert. Fading them is a real
signal ONLY if it survives path simulation at recorded-spread cost.

Out-of-sample discipline: probabilities come strictly from purged+
embargoed walk-forward folds; a bar's score never sees its own window
in training. Events subsampled (every `step`-th candidate bar) to keep
independence sane.
"""
import sys
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

import data_plane
import labels
import model


def oos_probs(sym, horizon=60, n_splits=5, embargo=240, step=1):
    """Return per-bar OOS probability of fwd-up, aligned to df index
    (NaN where no OOS prediction exists)."""
    df = data_plane.load(sym)
    X, y = model.build_matrix(sym, horizon)
    n = len(X)
    fold = n // (n_splits + 1)
    proba = pd.Series(np.nan, index=X.index)
    for i in range(n_splits):
        te0, te1 = fold * (i + 1), fold * (i + 2)
        tr_end = te0 - embargo
        if tr_end < fold:
            continue
        clf = HistGradientBoostingClassifier(
            max_iter=150, max_depth=4, learning_rate=0.07,
            early_stopping=True, random_state=7)
        clf.fit(X.iloc[:tr_end], y.iloc[:tr_end])
        proba.iloc[te0:te1] = clf.predict_proba(X.iloc[te0:te1])[:, 1]
        print(f"  fold{i} done", flush=True)
    return df, proba


def main():
    syms = sys.argv[1:] or ["EURUSD"]
    for sym in syms:
        pip = data_plane.pip_size(sym)
        df, proba = oos_probs(sym)
        ev = labels.Evaluator(df, pip)
        cost = labels.spread_cost_arr(df)
        edge = proba.reindex(df.index).to_numpy() - 0.5
        edge = np.where(np.isfinite(edge), edge, 0.0)
        # restrict to every 15th bar to thin overlapping events
        step_mask = np.zeros(len(df), dtype=bool)
        step_mask[::15] = True
        for th in (0.04, 0.06, 0.08, 0.10):
            hi = np.abs(edge) > th
            for mode in ("fade", "follow"):
                for side_val, sgn in ((1, -1), (-1, -1)):
                    pass
                # fade: side = -sign(edge); follow: side = +sign(edge)
                sgn = -1 if mode == "fade" else 1
                m_up = hi & (np.sign(edge) * sgn > 0) & step_mask
                m_dn = hi & (np.sign(edge) * sgn < 0) & step_mask
                for hold in (30, 60, 120):
                    for sl in (12, 20, 30):
                        for m, s in ((m_up, 1), (m_dn, -1)):
                            r = ev.eval(m, s, sl, 0, hold, cost_arr=cost)
                            ret = r["ret"]
                            if len(ret) >= 300 and labels.pf(ret) > 1.15:
                                print(f"{sym} {mode} th={th} hold={hold} "
                                      f"sl={sl} side={s}: n={len(ret)} "
                                      f"net={ret.mean():+.2f} "
                                      f"PF={labels.pf(ret):.2f}",
                                      flush=True)
        print(f"=== {sym} done ===", flush=True)


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"total {time.time()-t0:.0f}s")
