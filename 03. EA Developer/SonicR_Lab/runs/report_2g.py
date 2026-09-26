"""report_2g.py - assemble every reported table for RESULTS_v7 from
the already-written out/trades_2g_*.csv files (no re-read of bars)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

from src import swap_adj
from holdout_2g import pf, mc_dd, realized_dd

SYMS = ["EURUSD", "XAUUSD"]
WEEKS_H = 174


def load(sym, mode, h):
    e1 = "_e1" if h == "H1" else ""
    return pd.read_csv(f"out/trades_2g_{sym}_{mode}_e0s{e1}.csv")


def pooled(mode, h):
    return pd.concat([load(s, mode, h) for s in SYMS], ignore_index=True)


def am(df):
    return df[df.am_pm == "AM"] if "am_pm" in df.columns else df


def yr_of(df):
    return pd.to_datetime(df.fill_ctm, unit="s").dt.year


def main():
    fr1 = pooled("FR", "H1"); fr0 = pooled("FR", "H0")
    fl1 = am(pooled("FL", "H1")); fl0 = am(pooled("FL", "H0"))
    print("== portfolio (AM, x1) ==")
    for tag, df in (("FR H1", fr1), ("FL H1", fl1),
                    ("FR H0", fr0), ("FL H0", fl0)):
        yr = yr_of(df)
        nets = df.groupby(yr).r_x1.sum()
        print(f"{tag}: n={len(df)} t/w/acct={len(df)/WEEKS_H:.2f} "
              f"PF={pf(df.r_x1):.3f} exp={df.r_x1.mean():.3f} "
              f"net={df.r_x1.sum():.1f}R mcDD95={mc_dd(df.r_x1.to_numpy()):.1f} "
              f"realDD={realized_dd(df.r_x1):.1f} posyr={int((nets>0).sum())}/4")
        print("   per-year net_R:",
              " ".join(f"{y}:{v:+.1f}" for y, v in nets.items()))
    print("\n== per symbol (FR H1, x1) ==")
    for s in SYMS:
        d = load(s, "FR", "H1")
        lo_, hi_ = d.r_x1.clip(upper=0).sum(), d.r_x1.clip(lower=0).sum()
        print(f"{s}: n={len(d)} PF={pf(d.r_x1):.3f} net={d.r_x1.sum():+.1f} "
              f"long n={int((d['dir']==1).sum())} PF={pf(d.r_x1[d['dir']==1]):.3f} | "
              f"short n={int((d['dir']==-1).sum())} PF={pf(d.r_x1[d['dir']==-1]):.3f}")
        yr = yr_of(d)
        print("   per-year:", " ".join(
            f"{y}:{g.r_x1.sum():+.1f}(PF{pf(g.r_x1):.2f})"
            for y, g in d.groupby(yr)))
    print("\n== Friday split (FR H1) ==")
    dow = pd.to_datetime(fr1.fill_ctm, unit="s").dt.dayofweek
    for k, m in (("Fri", dow == 4), ("non-Fri", dow != 4)):
        d = fr1[m]
        print(f"{k}: n={len(d)} PF={pf(d.r_x1):.3f} net={d.r_x1.sum():+.1f}")
    print("\n== swap / cost realism (pooled AM FR) ==")
    for tag, df in (("H1", fr1), ("H0", fr0)):
        print(f"{tag}: x1={pf(df.r_x1):.3f} swap_x1="
              f"{pf(swap_adj.swap_adj_r(df,1.0)):.3f} x1.5={pf(df.r_x15):.3f} "
              f"x2={pf(df.r_x2):.3f} swap2+x1.5="
              f"{pf(swap_adj.swap_adj_r(df,2.0,'r_x15')):.3f}")
        sa = swap_adj.swap_adj_r(df, 1.0)
        print(f"     net R: x1={df.r_x1.sum():+.1f} "
              f"swap_adj={sa.sum():+.1f} (swap cost "
              f"{df.r_x1.sum()-sa.sum():.1f}R)")
    print("\n== relative-cap arm (XAUUSD FR, not gated) ==")
    for h in ("H1", "H0"):
        f = load("XAUUSD", "RELFR", h)
        dd = mc_dd(f.r_x1.to_numpy())
        yr = yr_of(f); pos = int((f.groupby(yr).r_x1.sum() > 0).sum())
        g1b_keep = np.ones(len(f), bool)
        g1b_keep[int(np.argmax(f.r_x1.to_numpy()))] = False
        print(f"{h}: FR n={len(f)} PF={pf(f.r_x1):.3f} "
              f"G1b={pf(f.r_x1[g1b_keep]):.3f} "
              f"G2={pf(swap_adj.swap_adj_r(f,2.0,'r_x15')):.3f} "
              f"mcDD={dd:.1f} posyr={pos}/4 net={f.r_x1.sum():+.1f}")
    print("\n== D/V/H pooled AM FR H1 comparison ==")
    for tag, pat in (("DESIGN", "out/trades_2f_{s}_X0-HOLD_e0s_e1.csv"),
                     ("VALIDATION",
                      "out/trades_2fval_{s}_AMONLY_e0s_e1.csv")):
        dd = pd.concat([pd.read_csv(pat.format(s=s)) for s in SYMS],
                       ignore_index=True)
        if "am_pm" in dd.columns:
            dd = dd[dd.am_pm == "AM"]
        wk = ((dd.fill_ctm.max() - dd.fill_ctm.min()) / (7 * 86400))
        print(f"{tag}: n={len(dd)} PF={pf(dd.r_x1):.3f} "
              f"net={dd.r_x1.sum():+.1f} t/w={len(dd)/wk:.2f} "
              f"mcDD95={mc_dd(dd.r_x1.to_numpy()):.1f} "
              f"realDD={realized_dd(dd.r_x1):.1f}")
    print(f"HOLDOUT: n={len(fr1)} PF={pf(fr1.r_x1):.3f} "
          f"net={fr1.r_x1.sum():+.1f} t/w={len(fr1)/WEEKS_H:.2f} "
          f"mcDD95={mc_dd(fr1.r_x1.to_numpy()):.1f} "
          f"realDD={realized_dd(fr1.r_x1):.1f}")


if __name__ == "__main__":
    main()
