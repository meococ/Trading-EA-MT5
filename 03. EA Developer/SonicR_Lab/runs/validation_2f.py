"""validation_2f.py - 2F STEP 5: the ONE validation read.

Run ONLY after confirm K1-K3 all pass. Flow:
 1. HOLDOUT guard test: a holdout read must raise PermissionError.
 2. Log the unlock time (LAB_LOG.md appended inside this script).
 3. Rerun frozen F2_NH_b generator + sim (with the step-1 DST fix) on
    the VALIDATION window for all 12 symbols, H0/H1:
    - fixed list: all X0-HOLD trades, then AM filter applied;
    - free-running AM-only: PM orders never placed.
    Window = (DESIGN_END, VALIDATION_END] per PREREG.md. Indicators warm
    up on DESIGN prices (ctx built from COMMON_START); signals only
    inside the window; book starts empty; trades open at the window end
    close at the last loaded bar (reason "window_end").
 4. Coverage: a symbol with <90% of VALIDATION weeks is dropped+named.
 5. V1-V3; per symbol/year, long/short, Friday split, swap column.
 6. Portfolio views (reporting): (a) EURUSD+XAUUSD, (b) all 12;
    AM-only free-running, DESIGN + VALIDATION; 1R/trade; trades/week
    per account; PF_R; positive years; MC DD P95 (200 reorderings);
    with/without swap; (b) also capped 5/week first-come, max 3 open.
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

ALL = list(dm.ALL_SYMBOLS)
CFG = [c for c in CONFIGS if c["id"] == "F2_NH_b"][0]
BLK = 28 * 86400
BOOT_N, SEED = 2000, 20260924
UNLOCK_VALIDATION = True          # explicit flag, logged below

WEEK_CAP, MAX_OPEN = 5, 3


def pf(r):
    r = pd.Series(r).dropna()
    neg = -r[r < 0].sum()
    return float(r[r > 0].sum() / neg) if neg > 0 else np.nan


def _blocks(ctm, lo):
    return ((ctm - lo) // BLK).astype(np.int64)


def joint_boot(df, lo, n=BOOT_N, seed=SEED):
    rng = np.random.default_rng(seed)
    b = _blocks(df["fill_ctm"].to_numpy(), lo)
    ub = np.unique(b)
    rows_by = [np.nonzero(b == u)[0] for u in ub]
    stats = np.empty(n)
    for i in range(n):
        sel = np.concatenate([rows_by[j] for j in
                              rng.integers(0, len(ub), len(ub))])
        r = df.iloc[sel]
        am = r["am_pm"] == "AM"
        stats[i] = (r.loc[am, "r_x1"].mean()
                    - r.loc[~am, "r_x1"].mean())
    return stats


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


def london_week(ctm):
    """London calendar week starting Monday 00:00 (epoch day0=Thursday,
    Monday = day index 4 mod 7)."""
    lon = dm.server_to_london(np.asarray(ctm))
    return (lon // 86400 - 4) // 7


def london_year(ctm):
    lon = dm.server_to_london(np.asarray(ctm))
    return pd.to_datetime(pd.Series(lon), unit="s", utc=True).dt.year.to_numpy()


def orders_once(sym, window, cap):
    """Orders generated once per (sym,window); cached under a versioned
    key so the pre-A2F (buggy-mapping, no-reset) entries can never be
    picked up."""
    cid = "F2_NH_b_dstfix"
    orders = order_cache.load_orders(sym, cid, window)
    if orders is None:
        ctx = runner.get_ctx(sym, 15)
        orders = runner.orders_for(ctx, CFG, *window, cap)
        order_cache.save_orders(sym, cid, window, orders)
    return orders


def cap_filter(tr):
    tr = tr.sort_values("fill_ctm").reset_index(drop=True)
    week = london_week(tr["fill_ctm"].to_numpy())
    open_until = []
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


def mc_dd(r, n=200, seed=5):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        eq = np.cumsum(rng.permutation(r))
        out.append((np.maximum.accumulate(eq) - eq).max())
    return float(np.percentile(out, 95)) if out else np.nan


def label_df(tr):
    hour, dow, _ = dm.london_parts(tr["sig_ctm"].to_numpy())
    tr = tr.copy()
    tr["am_pm"] = np.where(hour < 7, "OUT",
                  np.where(hour < 12, "AM",
                  np.where(hour < 16, "PM", "OUT")))
    tr["lon_year"] = london_year(tr["sig_ctm"].to_numpy())
    tr["lon_dow"] = dow
    return tr


def main():
    import datetime
    t00 = time.time()
    lo, hi = dm.VALIDATION
    print(f"[VAL] window bounds (PREREG.md): DESIGN_END={lo} "
          f"VALIDATION_END={hi}", flush=True)
    # 1. holdout guard test
    try:
        dm.load_m1("EURUSD", dm.HOLDOUT_START + 60, dm.COMMON_END)
        raise SystemExit("HOLDOUT READ DID NOT RAISE - STOP")
    except PermissionError as ex:
        print(f"[VAL] holdout guard OK: {ex}", flush=True)
    # 2. unlock log
    ts = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    with open("LAB_LOG.md", "a") as f:
        f.write(f"\n[{ts}] VALIDATION UNLOCKED (round 2F, once, after "
                f"K1-K3 pass). Window ({lo},{hi}]. HOLDOUT stays "
                f"sealed; guard test passed.\n")
    print(f"[VAL] unlock logged {ts}", flush=True)
    # 3-4. rerun + label + coverage
    fixed, free = {}, {}
    dropped = []
    total_wk = (hi - lo) // (7 * 86400)
    for sym in ALL:
        ctx = runner.get_ctx(sym, 15)
        cap = None if sym == "EURUSD" else runner.sl_cap(ctx, sym)
        orders = orders_once(sym, (lo, hi), cap)
        # coverage: distinct weeks with tf bars inside window
        tw = ctx.tf["t"]
        wk = np.unique(((tw[(tw >= lo) & (tw <= hi)] - lo)
                        // (7 * 86400)))
        cov = len(wk) / total_wk
        if cov < 0.90:
            dropped.append(sym)
            print(f"[VAL] DROP {sym}: coverage {cov:.2%}", flush=True)
            continue
        hour, dow, _ = dm.london_parts(
            np.array([int(ctx.tf["t"][o["t"]]) for o in orders]))
        am_orders = [o for o, hh in zip(orders, hour) if 7 <= hh < 12]
        for e1 in (True, False):
            h = "H1" if e1 else "H0"
            tr = sm.run_trades(ctx.m1, ctx.tf, orders, sym, atr=ctx.atr,
                               skip_suspect=e1)
            tr = tr[tr.fill_ctm >= lo]          # window-only fills
            tr = label_df(tr)
            tr["sym"] = sym
            tr.to_csv(f"out/trades_2fval_{sym}_X0-HOLD"
                      f"{'_e1' if e1 else ''}.csv", index=False)
            fixed[(sym, h)] = tr
            fr = sm.run_trades(ctx.m1, ctx.tf, am_orders, sym,
                               atr=ctx.atr, skip_suspect=e1)
            fr = fr[fr.fill_ctm >= lo]
            fr = label_df(fr)
            fr["sym"] = sym
            fr.to_csv(f"out/trades_2fval_{sym}_AMONLY"
                      f"{'_e1' if e1 else ''}.csv", index=False)
            free[(sym, h)] = fr
            n_out = int((tr.am_pm == "OUT").sum())
            if n_out:
                print(f"[VAL] {sym} {h}: {n_out} OUT rows!", flush=True)
            print(f"[VAL {h}] {sym} fixed n={len(tr)} free n={len(fr)}",
                  flush=True)
    print(f"[VAL] dropped={dropped}", flush=True)
    # 5. V1-V3 on fixed list
    rep = []
    for e1 in (True, False):
        h = "H1" if e1 else "H0"
        df = pd.concat([fixed[(s, h)] for s in ALL
                        if (s, h) in fixed], ignore_index=True)
        am = df.am_pm == "AM"
        st = joint_boot(df, lo)
        sep = (df.loc[am, "r_x1"].mean() - df.loc[~am, "r_x1"].mean())
        lb = float(np.quantile(st, 0.05))
        per = df.groupby(["sym", "am_pm"])["r_x1"].apply(pf).unstack()
        n_am_gt1 = int((per["AM"] > 1.0).sum())
        rep.append({"harness": h, "n_am": int(am.sum()),
                    "n_pm": int((~am).sum()),
                    "pf_am_x1": pf(df.loc[am, "r_x1"]),
                    "pf_pm_x1": pf(df.loc[~am, "r_x1"]),
                    "pf_am_x15": pf(df.loc[am, "r_x15"]),
                    "exp_am": float(df.loc[am, "r_x1"].mean()),
                    "sep": float(sep), "sep_lb95": lb,
                    "n_syms_am_gt1": n_am_gt1,
                    "pf_am_swap": pf(swap_adj_r(df)[am]),
                    "gross_am": pf(df.loc[am, "r_gross"]),
                    "gross_pm": pf(df.loc[~am, "r_gross"]),
                    "sep_exfri": float(
                        df.loc[am & (df.lon_dow != 4), "r_x1"].mean()
                        - df.loc[~am & (df.lon_dow != 4), "r_x1"].mean()),
                    "sep_fri": float(
                        df.loc[am & (df.lon_dow == 4), "r_x1"].mean()
                        - df.loc[~am & (df.lon_dow == 4), "r_x1"].mean())})
        yr = df.groupby(["lon_year", "am_pm"])["r_x1"].apply(pf).unstack()
        print(f"[VAL {h}] per-year AM/PM:\n{yr.round(3)}", flush=True)
        los = df[df.dir == 1]; shs = df[df.dir == -1]
        print(f"[VAL {h}] sep_long="
              f"{los.loc[los.am_pm=='AM','r_x1'].mean()-los.loc[los.am_pm=='PM','r_x1'].mean():.4f} "
              f"sep_short="
              f"{shs.loc[shs.am_pm=='AM','r_x1'].mean()-shs.loc[shs.am_pm=='PM','r_x1'].mean():.4f}",
              flush=True)
        df.groupby(["sym", "am_pm"])["r_x1"].apply(pf).unstack().to_csv(
            f"out/val_2f_persym_{h}.csv")
    repdf = pd.DataFrame(rep)
    repdf.to_csv("out/val_2f_pooled.csv", index=False)
    print(repdf.round(4).to_string(index=False), flush=True)
    # free-running pooled for V1 second mode
    for e1 in (True, False):
        h = "H1" if e1 else "H0"
        fr = pd.concat([free[(s, h)] for s in ALL
                        if (s, h) in free], ignore_index=True)
        fam = fr[fr.am_pm == "AM"]
        print(f"[VAL free {h}] n={len(fr)} am n={len(fam)} "
              f"pf_x1={pf(fam.r_x1):.4f} pf_x15={pf(fam.r_x15):.4f} "
              f"exp={fam.r_x1.mean():.4f}", flush=True)
    # 6. portfolio views: AM-only free-running, DESIGN + VALIDATION
    port_rows = []
    des_free = {}
    for e1 in (True, False):
        h = "H1" if e1 else "H0"
        for sym in ALL:
            ctx = runner.get_ctx(sym, 15)
            cap = None if sym == "EURUSD" else runner.sl_cap(ctx, sym)
            orders = orders_once(sym, dm.DESIGN, cap)
            hour, _, _ = dm.london_parts(
                np.array([int(ctx.tf["t"][o["t"]]) for o in orders]))
            am_orders = [o for o, hh in zip(orders, hour)
                         if 7 <= hh < 12]
            fr = sm.run_trades(ctx.m1, ctx.tf, am_orders, sym,
                               atr=ctx.atr, skip_suspect=e1)
            fr = fr[fr.fill_ctm >= dm.DESIGN[0]]
            fr["sym"] = sym
            des_free[(sym, h)] = fr
    for e1 in (True, False):
        h = "H1" if e1 else "H0"
        for view, syms in (("eur_xau", ["EURUSD", "XAUUSD"]),
                           ("all12", [s for s in ALL
                                      if (s, h) in free])):
            for wname, (wlo, whi), src in (
                    ("DESIGN", dm.DESIGN, des_free),
                    ("VALIDATION", dm.VALIDATION, free)):
                df = pd.concat([src[(s, h)] for s in syms
                                if (s, h) in src], ignore_index=True)
                for mode, tr in (("uncapped", df),
                                 ("capped", cap_filter(df)
                                  if view == "all12" else None)):
                    if tr is None:
                        continue
                    for sw in (False, True):
                        tr2 = tr.assign(
                            r_use=swap_adj_r(tr) if sw else tr["r_x1"])
                        tr2 = tr2[np.isfinite(tr2["r_use"])]
                        r = tr2["r_use"].to_numpy()
                        wks = ((tr2["exit_ctm"].max()
                                - tr2["fill_ctm"].min()) / (7 * 86400)
                               if len(tr2) else np.nan)
                        y = (tr2["exit_ctm"].to_numpy() // 86400) // 365
                        py = tr2.groupby(y)["r_use"].sum()
                        port_rows.append({
                            "harness": h, "view": view, "window": wname,
                            "mode": mode, "swap": sw,
                            "n": len(tr), "trades_wk": len(tr) / wks
                            if wks else np.nan,
                            "pf_r": pf(r),
                            "pos_years": float((py > 0).mean())
                            if len(py) else np.nan,
                            "mc_dd_p95": mc_dd(r) if len(r) > 3 else np.nan})
    pd.DataFrame(port_rows).to_csv("out/portfolio_2f.csv", index=False)
    print(pd.DataFrame(port_rows).round(3).to_string(index=False),
          flush=True)
    print(f"[VAL] done {time.time()-t00:.0f}s", flush=True)


if __name__ == "__main__":
    if not UNLOCK_VALIDATION:
        raise SystemExit("UNLOCK_VALIDATION flag not set")
    main()
