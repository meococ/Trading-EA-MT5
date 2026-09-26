"""label_2f.py - 2F STEP 2: AM/PM labels on the _dstfix X0-HOLD files.

AM = London hour of the signal bar OPEN (sig_ctm) in [7,12);
PM = [12,16); anything else = OUT (listed; there should be none).
Labels only - no P/L split is computed here.
T1: join key (sym,sig_ctm,dir) on the dstfix files, zero unmatched.
T2: outcome-blind AM share per symbol and per year.
T3: recompute the Lead's discovery numbers on D (allowed: D is not
    evidence) - AM vs PM PF_R x1 per harness, per D symbol, per year.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src import data as dm

D_SET = ["AUDUSD", "USDCHF", "GBPJPY", "USDJPY", "GBPUSD",
         "EURUSD", "XAUUSD"]
ALL = list(dm.ALL_SYMBOLS)


def _pf(r):
    r = pd.Series(r).dropna()
    neg = -r[r < 0].sum()
    return r[r > 0].sum() / neg if neg > 0 else np.nan


def label(sym, e1):
    f = (f"out/trades_2f_{sym}_X0-HOLD_dstfix"
         f"{'_e1' if e1 else ''}.csv")
    tr = pd.read_csv(f)
    tr["sym"] = sym
    hour, dow, ymd = dm.london_parts(tr["sig_ctm"].to_numpy())
    tr["lon_hour"] = hour
    tr["am_pm"] = np.where(hour < 7, "OUT",
                  np.where(hour < 12, "AM",
                  np.where(hour < 16, "PM", "OUT")))
    # London calendar year of the signal bar
    lon = dm.server_to_london(tr["sig_ctm"].to_numpy())
    tr["lon_year"] = (lon // 86400 // 365 + 1970).astype(int)
    return tr


def main():
    t00 = time.time()
    n_out = 0
    shares = []
    for e1 in (True, False):
        h = "H1" if e1 else "H0"
        frames = []
        for sym in ALL:
            tr = label(sym, e1)
            out_n = int((tr["am_pm"] == "OUT").sum())
            n_out += out_n
            if out_n:
                print(f"OUT rows {sym} {h}:", tr.loc[tr.am_pm == "OUT",
                      ["sig_ctm", "lon_hour"]].to_string(index=False),
                      flush=True)
            frames.append(tr)
            sh = (tr.groupby("lon_year")["am_pm"]
                    .apply(lambda s: (s == "AM").mean()))
            for y, v in sh.items():
                shares.append({"sym": sym, "h": h, "year": int(y),
                               "am_share": float(v)})
        df = pd.concat(frames, ignore_index=True)
        df.to_csv(f"out/labels_2f_{h}.csv", index=False)
        print(f"[2F {h}] n={len(df)} OUT={n_out}", flush=True)
        if n_out:
            print("[2F] OUT rows exist - STOP per backup plan")
            return
    pd.DataFrame(shares).to_csv("out/am_share_2f.csv", index=False)
    # T3: recompute discovery numbers on D
    for e1 in (True, False):
        h = "H1" if e1 else "H0"
        df = pd.read_csv(f"out/labels_2f_{h}.csv")
        d = df[df.sym.isin(D_SET)]
        for g, dd in d.groupby("am_pm"):
            print(f"[T3 {h}] {g}: n={len(dd)} pf_r_x1={_pf(dd.r_x1):.3f}",
                  flush=True)
        # AM>PM per year (pooled D) and per symbol
        yr = d.groupby(["lon_year", "am_pm"])["r_x1"].apply(_pf).unstack()
        print(f"[T3 {h}] AM>PM years: "
              f"{int((yr['AM'] > yr['PM']).sum())}/{len(yr)}", flush=True)
        per = (d.groupby(["sym", "am_pm"])["r_x1"].apply(_pf).unstack())
        print(f"[T3 {h}] AM>PM syms: "
              f"{int((per['AM'] > per['PM']).sum())}/7", flush=True)
    print(f"[2F] labels done {time.time()-t00:.0f}s", flush=True)


if __name__ == "__main__":
    main()
