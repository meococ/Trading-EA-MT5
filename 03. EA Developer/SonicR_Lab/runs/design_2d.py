"""design_2d.py - ROUND 2D STEP 4: DESIGN run on the 7 D symbols only.

10 configs = {X0,X1,X2,X3,X4} x {HOLD,DF}; X0-HOLD is the reference.
Modes: fixed list (primary; every selection statistic) + free running
(secondary). Plus the pessimistic same-bar column for each candidate.
NO C-symbol output may exist from this script.

Writes per-symbol fixed-list files out/trades_2d_<sym>_<CFG><tag>.csv
(D symbols only), summary out/design_2d_summary<tag>.csv, and the
reporting-only weekday / hours-held table out/design_2d_slices.csv.
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

D_SET = ["AUDUSD", "USDCHF", "GBPJPY", "USDJPY", "GBPUSD",
         "EURUSD", "XAUUSD"]
RULES = ["X0", "X1", "X2", "X3", "X4"]
CFGS = [f"{r}-{h}" for r in RULES for h in ("HOLD", "DF")]
BOOT_SEED = 20260924
BOOT_N = 2000


def _pf_r(r):
    r = pd.Series(r).dropna()
    pos = r[r > 0].sum(); neg = -r[r < 0].sum()
    return pos / neg if neg > 0 else np.nan


def _pip_pf(p):
    p = pd.Series(p).dropna()
    pos = p[p > 0].sum(); neg = -p[p < 0].sum()
    return pos / neg if neg > 0 else np.nan


def _week_ids(ctm):
    """ISO calendar-week id per trade (bootstrap cluster)."""
    return (ctm // (7 * 86400)).astype(np.int64)


def boot_mean_ci(d, weeks, level=0.90, n=BOOT_N, seed=BOOT_SEED):
    """Cluster bootstrap on calendar weeks -> (mean, lo, hi)."""
    rng = np.random.default_rng(seed)
    d = np.asarray(d, float); w = np.asarray(weeks)
    uw = np.unique(w)
    sums = np.array([d[w == u].sum() for u in uw])
    cnts = np.array([(w == u).sum() for u in uw])
    idx = rng.integers(0, len(uw), size=(n, len(uw)))
    means = sums[idx].sum(1) / cnts[idx].sum(1)
    a = (1 - level) / 2
    return float(d.mean()), float(np.quantile(means, a)), \
        float(np.quantile(means, 1 - a))


def boot_lb(d, weeks, n=BOOT_N, seed=BOOT_SEED):
    """One-sided 95% lower bound of the mean (K1)."""
    rng = np.random.default_rng(seed)
    d = np.asarray(d, float); w = np.asarray(weeks)
    uw = np.unique(w)
    sums = np.array([d[w == u].sum() for u in uw])
    cnts = np.array([(w == u).sum() for u in uw])
    idx = rng.integers(0, len(uw), size=(n, len(uw)))
    means = sums[idx].sum(1) / cnts[idx].sum(1)
    return float(np.quantile(means, 0.05))


def _decomp(x0, va):
    """Paired decomposition vs X0: losers saved / winners cut."""
    sl0 = x0["reason"].isin(["sl", "sl_same"])
    tp0 = x0["reason"] == "tp"
    d = va["r_x1"].to_numpy() - x0["r_x1"].to_numpy()
    saved = float((d[sl0] > 0).mean()) if sl0.any() else np.nan
    cut = float((d[tp0] < 0).mean()) if tp0.any() else np.nan
    return saved, cut, float(d[d > 0].sum()), float(-d[d < 0].sum())


def _mix(tr):
    return tr["reason"].value_counts().to_dict()


def _slices(tr):
    """Reporting-only: mean R / PF_R by fill weekday and hours held."""
    wd = ((tr["fill_ctm"] // 86400 + 3) % 7).astype(int)  # 0=Mon
    hrs = (tr["exit_ctm"] - tr["fill_ctm"]) / 3600.0
    bucket = pd.cut(hrs, [-1, 4, 12, 24, 1e9],
                    labels=["<4h", "4-12h", "12-24h", ">24h"])
    out = {}
    for k in range(7):
        r = tr.loc[wd == k, "r_x1"]
        out[f"wd{k}"] = (float(r.mean()), _pf_r(r), int(len(r)))
    for b in ["<4h", "4-12h", "12-24h", ">24h"]:
        r = tr.loc[bucket == b, "r_x1"]
        out[f"h{b}"] = (float(r.mean()), _pf_r(r), int(len(r)))
    return out


def run_side(e1):
    tag = "_e1" if e1 else ""
    harness = "H1" if e1 else "H0"
    rows, pooled, slices = [], {}, {}
    pess_rows = []
    fl_all = {c: [] for c in CFGS}
    for sym in D_SET:
        tr0 = mg.load_x0(sym, e1)
        lc = mg.light_ctx(sym)
        weeks = _week_ids(tr0["fill_ctm"].to_numpy())
        res = {}
        for cfg in CFGS:
            rule, hold = cfg.split("-")
            t0 = time.time()
            fl = mg.resim_trades(tr0, lc, sym, rule, skip_suspect=e1,
                                 daily_flat=(hold == "DF"))
            fl.to_csv(f"out/trades_2d_{sym}_{cfg}{tag}.csv", index=False)
            res[cfg] = fl
            fl_all[cfg].append(fl)
            print(f"[2D {harness}] {sym} {cfg} n={len(fl)} "
                  f"({time.time()-t0:.0f}s)", flush=True)
        # pessimistic column for candidates (same-bar BE on trigger bar)
        pes = {}
        for cfg in CFGS:
            if cfg == "X0-HOLD":
                continue
            rule, hold = cfg.split("-")
            pes[cfg] = mg.resim_trades(tr0, lc, sym, rule,
                                       skip_suspect=e1,
                                       daily_flat=(hold == "DF"),
                                       pessimistic=True)
            pess_rows.append({"sym": sym, "harness": harness, "cfg": cfg,
                              "mean_dR_pess": float(
                                  (pes[cfg]["r_x1"] - tr0["r_x1"]).mean()),
                              "pf_r_x1_pess": _pf_r(pes[cfg]["r_x1"])})
        # free running (secondary)
        ctx = runner.get_ctx(sym, 15)
        orders = order_cache.load_orders(sym, "F2_NH_b", dm.DESIGN)
        free = {}
        for cfg in CFGS:
            rule, hold = cfg.split("-")
            fr = sm.run_trades(ctx.m1, ctx.tf, orders, sym, atr=ctx.atr,
                               skip_suspect=e1, exit_rule=rule,
                               daily_flat_mod=1430 if hold == "DF" else None,
                               tfx=lc["tfx"])
            free[cfg] = fr
        for cfg in CFGS:
            fl = res[cfg]
            x0 = res["X0-HOLD"]
            d = (fl["r_x1"] - x0["r_x1"]).to_numpy()
            m, lo, hi = boot_mean_ci(d, weeks)
            pd_ = pes.get(cfg)
            mp = (float((pd_["r_x1"] - x0["r_x1"]).mean())
                  if pd_ is not None else np.nan)
            saved, cut, gain, loss = _decomp(x0, fl)
            rows.append({
                "sym": sym, "harness": harness, "cfg": cfg, "n": len(fl),
                "pf_r_x1": _pf_r(fl["r_x1"]),
                "pf_r_x15": _pf_r(fl["r_x15"]),
                "pf_pips": _pip_pf(fl["pnl_x1"]),
                "expectancy": float(fl["r_x1"].mean()),
                "mean_dR": m, "dR_lo90": lo, "dR_hi90": hi,
                "mean_dR_pess": mp,
                "sl_saved": saved, "tp_cut": cut,
                "r_gained": gain, "r_lost": loss,
                "mix": str(_mix(fl)),
                "pf_r_x1_free": _pf_r(free[cfg]["r_x1"]),
                "n_free": len(free[cfg]),
            })
        slices[sym] = {c: _slices(res[c])
                       for c in ("X0-HOLD", "X0-DF", "X1-HOLD", "X2-HOLD",
                                 "X3-HOLD", "X4-HOLD")}
        pooled[sym] = res
    # --- pooled-D stats -------------------------------------------------
    pool_rows = []
    x0p = pd.concat(fl_all["X0-HOLD"])
    wp = _week_ids(x0p["fill_ctm"].to_numpy())
    for cfg in CFGS:
        fl = pd.concat(fl_all[cfg])
        d = (fl["r_x1"] - x0p["r_x1"]).to_numpy()
        m, lo, hi = boot_mean_ci(d, wp)
        saved, cut, gain, loss = _decomp(x0p, fl)
        pool_rows.append({
            "sym": "POOLED", "harness": harness, "cfg": cfg,
            "n": len(fl), "pf_r_x1": _pf_r(fl["r_x1"]),
            "pf_r_x15": _pf_r(fl["r_x15"]),
            "pf_pips": _pip_pf(fl["pnl_x1"]),
            "expectancy": float(fl["r_x1"].mean()),
            "mean_dR": m, "dR_lo90": lo, "dR_hi90": hi,
            "mean_dR_pess": np.nan,
            "sl_saved": saved, "tp_cut": cut,
            "r_gained": gain, "r_lost": loss,
            "mix": str(_mix(fl)),
            "pf_r_x1_free": np.nan, "n_free": 0,
        })
    df = pd.DataFrame(rows + pool_rows)
    df.to_csv(f"out/design_2d_summary{tag}.csv", index=False)
    pd.DataFrame(pess_rows).to_csv(f"out/design_2d_pess{tag}.csv",
                                   index=False)
    # slices -> flat csv
    srows = []
    for sym, per in slices.items():
        for cfg, dd in per.items():
            for k, v in dd.items():
                srows.append({"sym": sym, "harness": harness, "cfg": cfg,
                              "bucket": k, "mean_r": v[0], "pf_r": v[1],
                              "n": v[2]})
    pd.DataFrame(srows).to_csv(f"out/design_2d_slices{tag}.csv",
                               index=False)
    print(f"[2D {harness}] design side done", flush=True)


def main():
    t0 = time.time()
    run_side(True)                          # H1 first (backup plan)
    run_side(False)
    print(f"[2D] total {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
