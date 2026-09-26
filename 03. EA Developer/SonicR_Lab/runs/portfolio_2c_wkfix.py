"""portfolio_2c_wkfix.py - A2F STEP B: rerun the 2C portfolio view with
the London-calendar-week cap (Monday 00:00 London) and the true London
calendar year. New file out/portfolio_2c_wkfix.csv - never overwrites
the 2C original. Same inputs (2C trade files, read-only).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

from validation_2f import london_week, london_year, pf, mc_dd, cap_filter
from src import data as dm
from src import metrics as mt

CENSUS_CFGS = ("F0_J", "F2_NH_b", "F5_S2", "F5_S3")


def _trades_for(sym, cid, e1):
    tag = "_e1" if e1 else ""
    for pat in (f"out/trades_2c_{sym}_{cid}{tag}.csv",
                f"out/trades_2b_{sym}_{cid}{tag}.csv",
                f"out/trades_{sym}_{cid}{tag}.csv"):
        if os.path.exists(pat):
            return pd.read_csv(pat)
    return None


def main():
    rows = []
    for e1, h in ((True, "H1"), (False, "H0")):
        for cid in CENSUS_CFGS:
            parts = [t for sym in dm.ALL_SYMBOLS
                     if (t := _trades_for(sym, cid, e1)) is not None
                     and len(t)]
            if not parts:
                continue
            all_tr = pd.concat(parts, ignore_index=True)
            for mode, tr in (("uncapped", all_tr),
                             ("capped", cap_filter(all_tr))):
                r = tr["r_x1"].dropna().to_numpy()
                wks = (tr["exit_ctm"].max() - tr["fill_ctm"].min()) \
                    / (7 * 86400) if len(tr) else np.nan
                yr = london_year(tr["exit_ctm"].to_numpy())
                py = pd.Series(r).groupby(yr[:len(r)]).sum() \
                    if len(r) == len(tr) else tr.groupby(
                        pd.Series(yr))["r_x1"].sum()
                rows.append({
                    "harness": h, "cfg": cid, "mode": mode,
                    "n_trades": len(tr),
                    "trades_wk": len(tr) / wks if wks else np.nan,
                    "pf_r_x1": pf(tr["r_x1"]),
                    "pf_r_x15": pf(tr["r_x15"]),
                    "pos_year_share": float((py > 0).mean()),
                    "n_years": len(py),
                    "mc_dd_p95_r": mc_dd(r) if len(r) > 3 else np.nan})
            print(f"[2c-wkfix] {h} {cid} uncapped n={len(all_tr)}",
                  flush=True)
    df = pd.DataFrame(rows)
    df.to_csv("out/portfolio_2c_wkfix.csv", index=False)
    print(df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
