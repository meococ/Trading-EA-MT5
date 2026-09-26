"""score_2e.py - ROUND 2E STEP 1: compute S_T labels for X0 trades.

Labels only - NO P/L, safe to run before the PREREG_V5 freeze. One
label set per symbol is shared by H0 and H1 (the harness decides which
trades exist, not what the trend state was).

T2: the X0-HOLD trade files (round 2D for D, round 2C for C) are the
    only input trades; join on (sym, sig_ctm, dir); assert zero
    unmatched rows.
T3: outcome-blind label sanity - S_T distribution per symbol, by
    direction, by year.

Writes out/scores_2e_<sym>.csv (labels) and out/score_dist_2e.csv.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

import managed as mg
from src import data as dm
from src import trend as td

ALL12 = list(dm.BASKET) + ["EURUSD", "XAUUSD"]
D_SET = ["AUDUSD", "USDCHF", "GBPJPY", "USDJPY", "GBPUSD",
         "EURUSD", "XAUUSD"]
C_SET = ["NZDUSD", "USDCAD", "EURJPY", "AUDJPY", "EURGBP"]


def main():
    t00 = time.time()
    dist_rows = []
    for sym in ALL12:
        t0 = time.time()
        lc = mg.light_ctx(sym)
        tc = td.build_trend_ctx(lc["m1"])
        # union of signal keys across both harnesses' X0 files
        trs = [mg.load_x0(sym, e1)[["sig_ctm", "dir"]].drop_duplicates()
               for e1 in (False, True)]
        keys = pd.concat(trs).drop_duplicates().reset_index(drop=True)
        S, A1, A2, A3, valid = td.score_trades(tc, keys)
        out = keys.copy()
        out["sym"] = sym
        out["A1"], out["A2"], out["A3"] = A1, A2, A3
        out["S_T"] = S
        out.to_csv(f"out/scores_2e_{sym}.csv", index=False)
        # T2: zero unmatched rows when joining each harness's trades
        for e1 in (False, True):
            tr = mg.load_x0(sym, e1)
            m = tr.merge(out[["sig_ctm", "dir", "S_T"]],
                         on=["sig_ctm", "dir"], how="left")
            assert len(m) == len(tr), (sym, e1)
            unmatched = m["S_T"].isna() & ~np.isfinite(m["S_T"])
            # every row must have joined (NaN score = valid NA, but the
            # row must exist) - verify via an indicator
            m2 = tr.merge(out[["sig_ctm", "dir"]].assign(_hit=1),
                          on=["sig_ctm", "dir"], how="left")
            assert m2["_hit"].notna().all(), f"unmatched {sym} {e1}"
        # T3: label sanity distributions
        yr = (keys["sig_ctm"] // 86400 // 365 + 1970).astype(int)
        for s in (0.0, 1.0, 2.0, 3.0, np.nan):
            mask = (S == s) if not np.isnan(s) else ~valid
            dist_rows.append({"sym": sym, "S_T": s,
                              "n": int(mask.sum()),
                              "long": int((mask & (keys["dir"] == 1)
                                           .to_numpy()).sum()),
                              "short": int((mask & (keys["dir"] == -1)
                                            .to_numpy()).sum())})
        by_year = {}
        for y in np.unique(yr):
            sm_ = S[yr == y]
            by_year[y] = {k: int((sm_ == k).sum()) for k in (0, 1, 2, 3)}
            by_year[y]["na"] = int((~np.isfinite(sm_)).sum())
        print(f"[2E] {sym}: n_keys={len(keys)} valid={int(valid.sum())} "
              f"na={int((~valid).sum())} dist="
              f"{pd.Series(S).value_counts().sort_index().to_dict()} "
              f"({time.time()-t0:.0f}s)", flush=True)
        for y, d in sorted(by_year.items()):
            dist_rows.append({"sym": sym, "S_T": f"year_{y}", **d})
    pd.DataFrame(dist_rows).to_csv("out/score_dist_2e.csv", index=False)
    print(f"[2E] scores done {time.time()-t00:.0f}s", flush=True)


if __name__ == "__main__":
    main()
