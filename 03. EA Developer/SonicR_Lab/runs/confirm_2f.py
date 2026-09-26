"""confirm_2f.py - 2F STEPS 3(power)+4(confirm on C).

Order of operations (prereg): power is computed on D BEFORE touching C.

1. POWER: joint 4-week-block bootstrap of D -> P(K1-K3 pass) and
   P(V1-V3 pass) under true effect = D's and half of D's.
2. CONFIRM on C (5 syms, DESIGN window, fixed list): AM/PM n, PF_R
   x1/x1.5, PF pips, expectancy, sep + 95% LB (joint bootstrap),
   per-year AM vs PM, long/short, Friday split, gross, swap; then
   free-running AM-only (PM orders never placed).
3. Apply K1-K3; print decision.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

import order_cache
from src import data as dm
from src import runner
from src import sim as sm
from src.variants.registry import CONFIGS

D_SET = ["AUDUSD", "USDCHF", "GBPJPY", "USDJPY", "GBPUSD",
         "EURUSD", "XAUUSD"]
C_SET = ["NZDUSD", "USDCAD", "EURJPY", "AUDJPY", "EURGBP"]
FULL_YEARS = list(range(2010, 2020))
BOOT_N, SEED = 2000, 20260924
BLK = 28 * 86400
CFG = [c for c in CONFIGS if c["id"] == "F2_NH_b"][0]


def pf(r):
    r = pd.Series(r).dropna()
    neg = -r[r < 0].sum()
    return float(r[r > 0].sum() / neg) if neg > 0 else np.nan


def _blocks(ctm, lo):
    return ((ctm - lo) // BLK).astype(np.int64)


def joint_boot(df, lo, stat_fn, n=BOOT_N, seed=SEED):
    rng = np.random.default_rng(seed)
    b = _blocks(df["fill_ctm"].to_numpy(), lo)
    ub = np.unique(b)
    rows_by = [np.nonzero(b == u)[0] for u in ub]
    stats = np.empty(n)
    for i in range(n):
        sel = np.concatenate([rows_by[j] for j in
                              rng.integers(0, len(ub), len(ub))])
        stats[i] = stat_fn(df.iloc[sel])
    return (float(stat_fn(df)), float(np.quantile(stats, 0.05)),
            float(np.quantile(stats, 0.95)), float(np.std(stats)),
            stats)


def sep_stat(df):
    am = df["am_pm"] == "AM"
    if am.sum() == 0 or (~am).sum() == 0:
        return np.nan
    return float(df.loc[am, "r_x1"].mean() - df.loc[~am, "r_x1"].mean())


def _n_rolls(fill_ctm, exit_ctm, sym_arr):
    f = np.asarray(fill_ctm); e = np.asarray(exit_ctm)
    out = np.zeros(len(f), dtype=int)
    for sym in np.unique(sym_arr):
        m = sym_arr == sym
        a = sm.ROLL[sym][0][0]
        phase = a * 60
        k = (np.floor((e[m] - phase) / 86400)
             - np.floor((f[m] - phase) / 86400)).astype(int)
        extra = np.zeros(m.sum(), dtype=int)
        fm = f[m]; em = e[m]
        anchor0 = (fm + 1) * 86400 + phase
        for i in np.nonzero(k > 0)[0]:
            j = 0
            while anchor0[i] + j * 86400 <= em[i]:
                if ((int(anchor0[i]) + j * 86400) // 86400 + 3) % 7 == 2:
                    extra[i] += 2
                j += 1
        out[m] = k + extra
    return out


def swap_adj_r(df):
    rolls = _n_rolls(df["fill_ctm"].to_numpy(),
                     df["exit_ctm"].to_numpy(), df["sym"].to_numpy())
    swap_px = df["sym"].map(
        lambda s: 0.30 if s == "XAUUSD" else 0.3 * dm.PIP[s])
    return df["r_x1"] - (rolls * swap_px.to_numpy()) / df["risk_px"]


def gates_resample(df, sd_sep):
    """Evaluate K1-K3 + V approximations on one resampled df (H1 only).
    K1 approx: sep > 1.645*sd_sep (LB95>0 proxy)."""
    am = df["am_pm"] == "AM"
    sep = df.loc[am, "r_x1"].mean() - df.loc[~am, "r_x1"].mean()
    k1 = sep > 1.645 * sd_sep
    per = df.groupby(["sym", "am_pm"])["r_x1"].apply(pf).unstack()
    k2 = int((per["AM"] > per["PM"]).sum()) >= 5   # >=5/7 ~ >=4/5
    lo_s = df[df.dir == 1]; sh_s = df[df.dir == -1]
    sep_l = lo_s.loc[lo_s.am_pm == "AM", "r_x1"].mean() - \
        lo_s.loc[lo_s.am_pm == "PM", "r_x1"].mean()
    sep_s = sh_s.loc[sh_s.am_pm == "AM", "r_x1"].mean() - \
        sh_s.loc[sh_s.am_pm == "PM", "r_x1"].mean()
    yr = df[df.lon_year.isin(FULL_YEARS)]
    pery = yr.groupby(["lon_year", "am_pm"])["r_x1"].apply(pf).unstack()
    k3 = (sep_l > 0) and (sep_s > 0) and \
        int((pery["AM"] > pery["PM"]).sum()) >= 6
    # V approximations (D resample as the model)
    v1 = (pf(df.loc[am, "r_x1"]) >= 1.10) and \
        (df.loc[am, "r_x1"].mean() > 0) and \
        (pf(df.loc[am, "r_x15"]) >= 1.00)
    v2 = int((per["AM"] > 1.0).sum()) >= 5
    v3 = k1
    return k1 and k2 and k3, v1 and v2 and v3


def power_on_D():
    """Joint bootstrap of D; P(K1-K3) and P(V1-V3) at full and half
    effect (half: AM shifted -sep_D/4, PM +sep_D/4)."""
    df = pd.read_csv("out/labels_2f_H1.csv")
    d = df[df.sym.isin(D_SET)].copy()
    lo, hi = dm.DESIGN
    s0, lb, ub, sd, stats = joint_boot(d, lo, sep_stat)
    rng = np.random.default_rng(SEED + 1)
    b = _blocks(d["fill_ctm"].to_numpy(), lo)
    ub_ = np.unique(b)
    rows_by = [np.nonzero(b == u)[0] for u in ub_]
    sep_d = sep_stat(d)
    nk = np.zeros(2); nv = np.zeros(2); nres = 2000
    for i in range(nres):
        sel = np.concatenate([rows_by[j] for j in
                              rng.integers(0, len(ub_), len(ub_))])
        r = d.iloc[sel]
        for j, scale in enumerate((1.0, 0.5)):
            rr = r.copy()
            if scale < 1:
                shift = np.where(rr.am_pm == "AM",
                                 -sep_d / 4, sep_d / 4)
                rr["r_x1"] = rr["r_x1"] + shift
            kk, vv = gates_resample(rr, sd)
            nk[j] += kk; nv[j] += vv
    print(f"[power] D sep={sep_d:.4f} sd={sd:.4f} "
          f"P(K1-K3)={nk[0]/nres:.3f} P(V1-V3)={nv[0]/nres:.3f} | "
          f"half: P(K)={nk[1]/nres:.3f} P(V)={nv[1]/nres:.3f}",
          flush=True)


def confirm():
    out = []
    per_rows = []
    for e1 in (True, False):
        h = "H1" if e1 else "H0"
        df = pd.read_csv(f"out/labels_2f_{h}.csv")
        c = df[df.sym.isin(C_SET)].copy()
        lo, hi = dm.DESIGN
        s0, lb, ub, sd, bstats = joint_boot(c, lo, sep_stat)
        am = c["am_pm"] == "AM"
        r_swap = swap_adj_r(c)
        # friday split (London dow of signal bar == 4)
        _, fdow, _ = dm.london_parts(c["sig_ctm"].to_numpy())
        fri = fdow == 4
        row = {"harness": h, "n_am": int(am.sum()), "n_pm": int((~am).sum()),
               "pf_am_x1": pf(c.loc[am, "r_x1"]),
               "pf_pm_x1": pf(c.loc[~am, "r_x1"]),
               "pf_am_x15": pf(c.loc[am, "r_x15"]),
               "pf_pm_x15": pf(c.loc[~am, "r_x15"]),
               "pf_pips_am": pf(c.loc[am, "pnl_px_x1"]),
               "pf_pips_pm": pf(c.loc[~am, "pnl_px_x1"]),
               "exp_am": float(c.loc[am, "r_x1"].mean()),
               "exp_pm": float(c.loc[~am, "r_x1"].mean()),
               "sep": s0, "sep_lb95": lb, "sep_ub95": ub,
               "sep_p_1s": float((bstats <= 0).mean()),
               "gross_am": pf(c.loc[am, "r_gross"]),
               "gross_pm": pf(c.loc[~am, "r_gross"]),
               "pf_am_swap": pf(r_swap[am]),
               "sep_exfri": float(
                   c.loc[am & ~fri, "r_x1"].mean()
                   - c.loc[~am & ~fri, "r_x1"].mean()),
               "sep_fri": float(
                   c.loc[am & fri, "r_x1"].mean()
                   - c.loc[~am & fri, "r_x1"].mean()),
               }
        out.append(row)
        for sym in C_SET:
            dd = c[c.sym == sym]
            a = dd.am_pm == "AM"
            per_rows.append({"harness": h, "sym": sym, "n_am": int(a.sum()),
                             "n_pm": int((~a).sum()),
                             "pf_am": pf(dd.loc[a, "r_x1"]),
                             "pf_pm": pf(dd.loc[~a, "r_x1"]),
                             "exp_am": float(dd.loc[a, "r_x1"].mean()),
                             "exp_pm": float(dd.loc[~a, "r_x1"].mean())})
        # K3 detail on H1
        if e1:
            lo_s = c[c.dir == 1]; sh_s = c[c.dir == -1]
            sep_l = lo_s.loc[lo_s.am_pm == "AM", "r_x1"].mean() - \
                lo_s.loc[lo_s.am_pm == "PM", "r_x1"].mean()
            sep_s = sh_s.loc[sh_s.am_pm == "AM", "r_x1"].mean() - \
                sh_s.loc[sh_s.am_pm == "PM", "r_x1"].mean()
            yr = c[c.lon_year.isin(FULL_YEARS)]
            pery = yr.groupby(["lon_year", "am_pm"])["r_x1"].apply(pf).unstack()
            n_years_am = int((pery["AM"] > pery["PM"]).sum())
            pery.to_csv("out/confirm_2f_years_e1.csv")
            print(f"[C H1] sep_long={sep_l:.4f} sep_short={sep_s:.4f} "
                  f"AM>PM years={n_years_am}/10", flush=True)
    df_out = pd.DataFrame(out)
    df_out.to_csv("out/confirm_2f_pooled.csv", index=False)
    pd.DataFrame(per_rows).to_csv("out/confirm_2f_persym.csv", index=False)
    print(df_out.round(4).to_string(index=False), flush=True)
    print(pd.DataFrame(per_rows).round(4).to_string(index=False), flush=True)


def free_running():
    rows = []
    for e1 in (True, False):
        h = "H1" if e1 else "H0"
        for sym in C_SET:
            ctx = runner.get_ctx(sym, 15)
            cap = None if sym == "EURUSD" else runner.sl_cap(ctx, sym)
            orders = runner.orders_for(ctx, CFG, *dm.DESIGN, cap)
            hour, dow, _ = dm.london_parts(
                np.array([int(ctx.tf["t"][o["t"]]) for o in orders]))
            keep = [o for o, hh in zip(orders, hour) if 7 <= hh < 12]
            tr = sm.run_trades(ctx.m1, ctx.tf, keep, sym, atr=ctx.atr,
                               skip_suspect=e1)
            rows.append({"harness": h, "sym": sym, "n": len(tr),
                         "pf_r_x1": pf(tr["r_x1"]),
                         "pf_r_x15": pf(tr["r_x15"]),
                         "exp": float(tr["r_x1"].mean())})
            print(f"[free {h}] {sym} n={len(tr)} "
                  f"pf={pf(tr['r_x1']):.3f}", flush=True)
    pd.DataFrame(rows).to_csv("out/confirm_2f_free.csv", index=False)


def main():
    t00 = time.time()
    print("[2F] step: POWER on D (before touching C)", flush=True)
    power_on_D()
    print("[2F] step: CONFIRM on C", flush=True)
    confirm()
    print("[2F] step: FREE-RUNNING AM-only on C", flush=True)
    free_running()
    print(f"[2F] confirm done {time.time()-t00:.0f}s", flush=True)


if __name__ == "__main__":
    main()
