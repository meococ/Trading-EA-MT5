"""run_portfolio_2c.py - ROUND 2C portfolio view (reporting only).

All 12 symbols (10 basket + EURUSD + XAUUSD), per config x harness:
1R risk per trade, TAH account doctrine - cap 5 new trades per calendar
week (first-come by fill_ctm) and max 3 open positions. Report
trades/week/account, PF_R x1, positive-year share, MC DD P95 in R
(200 reorderings), uncapped and capped.

Reads the trades CSVs already on disk (no new sims).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src import data as dm
from src import metrics as mt

CENSUS_CFGS = ("F0_J", "F2_NH_b", "F5_S2", "F5_S3")
WEEK_CAP = 5
MAX_OPEN = 3


def _trades_for(sym, cid, e1):
    tag = "_e1" if e1 else ""
    for pat in (f"out/trades_2c_{sym}_{cid}{tag}.csv",
                f"out/trades_2b_{sym}_{cid}{tag}.csv",
                f"out/trades_{sym}_{cid}{tag}.csv"):
        if os.path.exists(pat):
            return pd.read_csv(pat)
    return None


def _cap_filter(tr):
    """First-come by fill time: <=WEEK_CAP new trades/week, <=MAX_OPEN open."""
    tr = tr.sort_values("fill_ctm").reset_index(drop=True)
    week = tr["fill_ctm"].to_numpy() // (7 * 86400)
    open_until = []          # exit_ctm of currently open positions
    wk_seen = {}
    keep = np.zeros(len(tr), bool)
    fills = tr["fill_ctm"].to_numpy(); exits = tr["exit_ctm"].to_numpy()
    for i in range(len(tr)):
        f = fills[i]
        open_until = [e for e in open_until if e > f]
        w = week[i]
        if wk_seen.get(w, 0) >= WEEK_CAP or len(open_until) >= MAX_OPEN:
            continue
        keep[i] = True
        wk_seen[w] = wk_seen.get(w, 0) + 1
        open_until.append(exits[i])
    return tr[keep]


def _mc_dd(r, n=200, seed=5):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        eq = np.cumsum(rng.permutation(r))
        out.append((np.maximum.accumulate(eq) - eq).max())
    return float(np.percentile(out, 95)) if out else np.nan


def _pos_years(tr):
    if not len(tr):
        return np.nan, np.nan
    y = (tr["exit_ctm"].to_numpy() // 86400) // 365
    py = tr.groupby(y)["r_x1"].sum()
    return float((py > 0).mean()), len(py)


def main():
    rows = []
    for e1, h in ((False, "H0"), (True, "H1")):
        for cid in CENSUS_CFGS:
            parts = []
            for sym in dm.ALL_SYMBOLS:
                t = _trades_for(sym, cid, e1)
                if t is not None and len(t):
                    parts.append(t)
            if not parts:
                continue
            all_tr = pd.concat(parts, ignore_index=True)
            for mode, tr in (("uncapped", all_tr),
                             ("capped", _cap_filter(all_tr))):
                r = tr["r_x1"].dropna().to_numpy()
                wks = (tr["exit_ctm"].max() - tr["fill_ctm"].min()) \
                    / (7 * 86400) if len(tr) else np.nan
                posy, ny = _pos_years(tr)
                rows.append({
                    "harness": h, "cfg": cid, "mode": mode,
                    "n_trades": len(tr),
                    "trades_wk": len(tr) / wks if wks else np.nan,
                    "pf_r_x1": mt.pf_r(tr, "r_x1"),
                    "pf_r_x15": mt.pf_r(tr, "r_x15"),
                    "pos_year_share": posy, "n_years": ny,
                    "mc_dd_p95_r": _mc_dd(r) if len(r) > 3 else np.nan})
            print(f"[port] {h} {cid}: uncapped n={len(all_tr)} "
                  f"capped n={rows[-1]['n_trades']}", flush=True)
            pd.DataFrame(rows).to_csv("out/portfolio_2c.csv", index=False)
    df = pd.DataFrame(rows)
    print(df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
