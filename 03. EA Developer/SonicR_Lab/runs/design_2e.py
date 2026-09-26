"""design_2e.py - ROUND 2E STEP 3: DESIGN run on the 7 D symbols.

Merges X0-HOLD trades with S_T labels (out/scores_2e_*.csv) on
(sym, sig_ctm, dir). Base = trades with a defined S_T (NA dropped -
same base for every statistic, X0 included).

Statistics (fixed list, cost x1 unless stated): per-bucket table, OLS
slope b of r_x1 on S_T with symbol fixed effects, Spearman, cutoff c in
{2,3}, kept/removed n + PF_R x1/x1.5 + pip PF + expectancy + sep,
cadence, regime-preserving null pct (1000 whole-week circular time
shifts, seed 20260924), positive years (kept), long/short split b,
leave-one-year-out b, swap column, per-component alone, free running.

NO C-symbol output may exist from this script.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

import managed as mg
import order_cache
from src import data as dm
from src import metrics as mt
from src import runner
from src import sim as sm
from src import trend as td

D_SET = ["AUDUSD", "USDCHF", "GBPJPY", "USDJPY", "GBPUSD",
         "EURUSD", "XAUUSD"]
BOOT_SEED = 20260924
BOOT_N = 2000
NULL_SEED = 20260924
NULL_N = 1000
BLK = 28 * 86400                    # 4-week calendar blocks
WEEK = 7 * 86400


def _pf_r(r):
    r = pd.Series(r).dropna()
    pos = r[r > 0].sum(); neg = -r[r < 0].sum()
    return pos / neg if neg > 0 else np.nan


def _slope_fe(s, r, sym):
    """OLS slope of r on s with symbol fixed effects (demeaned)."""
    s = np.asarray(s, float); r = np.asarray(r, float)
    ok = np.isfinite(s) & np.isfinite(r)
    s, r, sym = s[ok], r[ok], np.asarray(sym)[ok]
    xs = s - pd.Series(s).groupby(sym).transform("mean").to_numpy()
    ys = r - pd.Series(r).groupby(sym).transform("mean").to_numpy()
    den = (xs * xs).sum()
    return float((xs * ys).sum() / den) if den > 0 else np.nan


def _spearman(s, r):
    ok = np.isfinite(s) & np.isfinite(r)
    from scipy.stats import spearmanr
    return spearmanr(s[ok], r[ok])


def _blocks(ctm, lo):
    return ((ctm - lo) // BLK).astype(np.int64)


def boot_stat(df, lo, stat_fn, n=BOOT_N, seed=BOOT_SEED):
    """Joint 4-week-block bootstrap: same resampled blocks for every
    subset of df. Returns (stat, lo95_1sided, [ci90 lo, hi])."""
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
            float(np.quantile(stats, [0.05, 0.95])[0]),
            float(np.quantile(stats, 0.95)),
            float((stats <= 0).mean()))


def _stat_b(df):
    return _slope_fe(df["S_T"], df["r_x1"], df["sym"])


def _stat_sep(df, c):
    k = df["S_T"] >= c
    if k.sum() == 0 or (~k).sum() == 0:
        return np.nan
    return float(df.loc[k, "r_x1"].mean() - df.loc[~k, "r_x1"].mean())


def regime_null_pct(dsyms_tcs, trades, c, lo, hi, n=NULL_N,
                    seed=NULL_SEED):
    """Whole-week circular time shifts of each symbol's per-M15-bar
    trend-state series; same k for all symbols; pooled kept PF_R."""
    rng = np.random.default_rng(seed)
    W = (hi - lo) // WEEK
    real = _pf_r(trades.loc[trades["S_T"] >= c, "r_x1"])
    null = np.empty(n)
    for d in range(n):
        k = int(rng.integers(8, max(9, W - 8)))
        rs = []
        for sym in trades["sym"].unique():
            tc = dsyms_tcs[sym]
            tr = trades[trades["sym"] == sym]
            S = td.score_at_shifted(tc, tr["sig_ctm"].to_numpy(),
                                    tr["dir"].to_numpy(), lo, hi,
                                    k * WEEK)
            rs.append(tr.loc[S >= c, "r_x1"])
        r = pd.concat(rs) if rs else pd.Series(dtype=float)
        null[d] = _pf_r(r) if len(r) else np.nan
    pct = float((null < real).mean() * 100)
    return real, pct, np.nanstd(null)


def _n_rolls(fill_ctm, exit_ctm, sym_arr):
    """Rollovers crossed per trade = roll-window starts inside
    (fill, exit]; the Wednesday roll counts triple. Per-symbol phase."""
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
        idx = np.nonzero(k > 0)[0]
        for i in idx:
            j = 0
            while anchor0[i] + j * 86400 <= em[i]:
                if ((int(anchor0[i]) + j * 86400) // 86400 + 3) % 7 == 2:
                    extra[i] += 2                # triple = +2 extra
                j += 1
        out[m] = k + extra
    return out


def main():
    t00 = time.time()
    lo, hi = dm.DESIGN
    W = (hi - lo) // WEEK
    tcs, tables = {}, {}
    for e1 in (True, False):
        harness = "H1" if e1 else "H0"
        frames = []
        for sym in D_SET:
            tr = mg.load_x0(sym, e1)
            sc = pd.read_csv(f"out/scores_2e_{sym}.csv")
            m = tr.merge(sc[["sig_ctm", "dir", "S_T", "A1", "A2", "A3"]],
                         on=["sig_ctm", "dir"], how="left",
                         validate="m:1")
            assert len(m) == len(tr)
            base = m[np.isfinite(m["S_T"])].copy()
            frames.append(base)
            if sym not in tcs:
                tcs[sym] = td.build_trend_ctx(mg.light_ctx(sym)["m1"])
        df = pd.concat(frames, ignore_index=True)
        df["S_T"] = df["S_T"].astype(int)
        tables[harness] = df
        print(f"[2E {harness}] base n={len(df)} "
              f"(dropped NA={sum(len(mg.load_x0(s, e1)) for s in D_SET)-len(df)})",
              flush=True)
    # ---- CUTOFF RULE: c decided once on D using both harnesses --------
    c2 = {}
    for harness in ("H1", "H0"):
        dfh = tables[harness]
        for cc in (2, 3):
            kk = dfh["S_T"] >= cc
            c2[(harness, cc)] = {"pf": _pf_r(dfh.loc[kk, "r_x1"]),
                                 "cad": kk.sum() / W / len(D_SET)}
    c = 3 if (c2[("H1", 3)]["cad"] >= 0.5 and
              c2[("H1", 3)]["pf"] >= c2[("H1", 2)]["pf"] and
              c2[("H0", 3)]["pf"] >= c2[("H0", 2)]["pf"]) else 2
    c_h1 = c
    print(f"[2E] cutoff: c2 pf H0={c2[('H0',2)]['pf']:.4f} "
          f"H1={c2[('H1',2)]['pf']:.4f} | c3 pf H0={c2[('H0',3)]['pf']:.4f} "
          f"H1={c2[('H1',3)]['pf']:.4f} cad3H1={c2[('H1',3)]['cad']:.2f} "
          f"-> c={c}", flush=True)
    out_rows = []
    for harness in ("H1", "H0"):
        df = tables[harness]
        # bucket table
        bt = df.groupby("S_T")["r_x1"].agg(
            n="size", mean="mean").reset_index()
        bt["pf_r_x1"] = df.groupby("S_T")["r_x1"].apply(_pf_r).values
        bt["pf_r_x15"] = df.groupby("S_T")["r_x15"].apply(_pf_r).values
        print(f"[2E {harness}] buckets:\n{bt.to_string(index=False)}",
              flush=True)
        b0, lb, lo90, hi90, pb = boot_stat(df, lo, _stat_b)
        sp = _spearman(df["S_T"].to_numpy(), df["r_x1"].to_numpy())
        print(f"[2E {harness}] b={b0:.4f} lb95={lb:.4f} "
              f"ci90=[{lo90:.4f},{hi90:.4f}] p={pb:.4f} "
              f"spearman rho={sp.statistic:.4f} p={sp.pvalue:.4f}",
              flush=True)
        # kept vs removed
        k = df["S_T"] >= c
        sep0, sep_lb, sep_lo90, sep_hi90, _ = boot_stat(
            df, lo, lambda d: _stat_sep(d, c))
        kept, rem = df[k], df[~k]
        # swap column on kept (per-symbol roll phase and pip size)
        rolls = _n_rolls(kept["fill_ctm"].to_numpy(),
                         kept["exit_ctm"].to_numpy(),
                         kept["sym"].to_numpy())
        swap_px = kept["sym"].map(
            lambda s: 0.30 if s == "XAUUSD" else 0.3 * dm.PIP[s])
        r_swap = kept["r_x1"] - (rolls * swap_px) / kept["risk_px"]
        # positive years on kept
        yr = (kept["fill_ctm"] // 86400 // 365 + 1970)
        posy = (kept.groupby(yr)["r_x1"].sum() > 0).mean()
        out_rows.append({
            "harness": harness, "n_base": len(df), "b": b0,
            "b_lb95": lb, "b_lo90": lo90, "b_hi90": hi90,
            "b_p_1s": pb, "spearman": float(sp.statistic),
            "sp_p": float(sp.pvalue), "c": c,
            "n_kept": int(k.sum()), "pf_r_x1_kept": _pf_r(kept["r_x1"]),
            "pf_r_x15_kept": _pf_r(kept["r_x15"]),
            "pf_pips_kept": _pf_r(kept["pnl_px_x1"]),
            "expect_kept": float(kept["r_x1"].mean()),
            "pf_r_x1_rem": _pf_r(rem["r_x1"]),
            "expect_rem": float(rem["r_x1"].mean()),
            "sep": sep0, "sep_lb95": sep_lb,
            "sep_ci90": f"[{sep_lo90:.4f},{sep_hi90:.4f}]",
            "cadence": float(k.sum() / W / len(D_SET)),
            "pos_years_kept": float(posy),
            "pf_r_x1_kept_swap": _pf_r(r_swap),
            "pf_r_x1_x0base": _pf_r(df["r_x1"]),
        })
    # per-symbol kept/removed + b splits + LOYO + components (H1 detail)
    df = tables["H1"]
    per_rows = []
    for sym in D_SET:
        d = df[df.sym == sym]
        for c in (c_h1,):
            k = d["S_T"] >= c
            per_rows.append({
                "sym": sym, "harness": "H1", "n": len(d),
                "n_kept": int(k.sum()),
                "pf_kept": _pf_r(d.loc[k, "r_x1"]),
                "pf_rem": _pf_r(d.loc[~k, "r_x1"]),
                "b": _slope_fe(d["S_T"], d["r_x1"],
                               np.array([sym] * len(d))),
            })
    per_df = pd.DataFrame(per_rows)
    per_df.to_csv("out/design_2e_persym_e1.csv", index=False)
    # E2 splits (H1): long / short / leave-one-year-out
    e2 = {}
    e2["long"] = _slope_fe(df.loc[df.dir == 1, "S_T"],
                           df.loc[df.dir == 1, "r_x1"],
                           df.loc[df.dir == 1, "sym"])
    e2["short"] = _slope_fe(df.loc[df.dir == -1, "S_T"],
                            df.loc[df.dir == -1, "r_x1"],
                            df.loc[df.dir == -1, "sym"])
    yr_all = (df["fill_ctm"] // 86400 // 365 + 1970).astype(int)
    e2["loyo"] = {}
    for y in sorted(yr_all.unique()):
        dd = df[yr_all != y]
        e2["loyo"][int(y)] = _slope_fe(dd["S_T"], dd["r_x1"], dd["sym"])
    print("[2E H1] E2:", e2, flush=True)
    # components alone (kept vs removed), H1
    comp = {}
    for a in ("A1", "A2", "A3"):
        k = df[a] == 1
        comp[a] = {"n_kept": int(k.sum()),
                   "pf_kept": _pf_r(df.loc[k, "r_x1"]),
                   "pf_rem": _pf_r(df.loc[~k, "r_x1"]),
                   "mean_kept": float(df.loc[k, "r_x1"].mean()),
                   "mean_rem": float(df.loc[~k, "r_x1"].mean())}
    print("[2E H1] components:", comp, flush=True)
    # regime null (H1, c chosen)
    real_pf, null_pct, null_sd = regime_null_pct(tcs, df, c_h1, lo, hi)
    print(f"[2E H1] null: kept pf={real_pf:.4f} pct={null_pct:.1f} "
          f"null_sd={null_sd:.3f}", flush=True)
    # free running (secondary): filter orders by S_T>=c
    free_rows = []
    for e1 in (True, False):
        for sym in D_SET:
            ctx = runner.get_ctx(sym, 15)
            orders = order_cache.load_orders(sym, "F2_NH_b", dm.DESIGN)
            sc = pd.read_csv(f"out/scores_2e_{sym}.csv")
            smap = {(r.sig_ctm, r.dir): r.S_T for r in sc.itertuples()}
            keep = []
            for o in orders:
                sct = int(ctx.tf["t"][o["t"]])
                S = smap.get((sct, o["dir"]), np.nan)
                if np.isfinite(S) and S >= c_h1:
                    keep.append(o)
            fr = sm.run_trades(ctx.m1, ctx.tf, keep, sym, atr=ctx.atr,
                               skip_suspect=e1)
            free_rows.append({"sym": sym, "harness": "H1" if e1 else "H0",
                              "n_free": len(fr),
                              "pf_r_x1_free": _pf_r(fr["r_x1"])})
            print(f"[2E free {'H1' if e1 else 'H0'}] {sym} n={len(fr)}",
                  flush=True)
    pd.DataFrame(free_rows).to_csv("out/design_2e_free.csv", index=False)
    pd.DataFrame(out_rows).to_csv("out/design_2e_summary.csv",
                                 index=False)
    # save merged base for confirm reuse (D only)
    tables["H1"].to_csv("out/base_2d_e1.csv", index=False)
    tables["H0"].to_csv("out/base_2d.csv", index=False)
    print(f"[2E] design done {time.time()-t00:.0f}s", flush=True)


if __name__ == "__main__":
    main()
