"""holdout_2g.py - 2G STEP 3: THE ONE HOLDOUT READ.

Run ONLY after PREREG_V7's sha256 is in LAB_LOG. Order (3c):
unlock -> census -> per symbol H1 FR -> H1 FL -> H0 FR -> H0 FL ->
relative-cap arm -> reported items.

Frozen candidate: F2_NH_b generator (DST fix + reset_zones), AM-only
entries [07:00,12:00) London on the M15 signal open, X0-HOLD exits,
costs as coded, E0' second-stamp void in every harness, SL caps
(EURUSD 120p fixed; XAUUSD runner.sl_cap from DESIGN medians).
NO-FIX RULE applies after unlock.
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
from src import e0
from src import runner
from src import sim as sm
from src import spike
from src import swap_adj
from src.components import stops_targets as st
from src.variants.registry import CONFIGS
from census_2g import run_census

SYMS = ["EURUSD", "XAUUSD"]
CFG = [c for c in CONFIGS if c["id"] == "F2_NH_b"][0]
WEEKS_174 = 174


def pf(r):
    r = pd.Series(r).dropna()
    neg = -r[r < 0].sum()
    return float(r[r > 0].sum() / neg) if neg > 0 else np.nan


def mc_dd(r, n=200, seed=5):
    rng = np.random.default_rng(seed)
    r = np.asarray(r)
    out = [(np.maximum.accumulate(np.cumsum(p)) - np.cumsum(p)).max()
           for p in (rng.permutation(r) for _ in range(n))]
    return float(np.percentile(out, 95))


def realized_dd(r):
    eq = np.cumsum(np.asarray(r))
    return float((np.maximum.accumulate(eq) - eq).max()) if len(eq) else 0.0


def audit_rows(df, m1, sym, mode, h, void=None):
    """A1G AUDIT RULE A: spike/gap flags on TP-winning trades +
    |R|>5 any exit. Returns de-duplicated list rows."""
    if void is None:
        void = e0.second_stamp(m1)
    med = spike.day_med_range(m1, void)
    out = {}
    w = df[(df.reason == "tp") & (df.r_x1 > 0)]
    for _, tr in w.iterrows():
        r = spike.spike_flag(m1, void, int(tr["dir"]),
                             float(tr["exit"]), int(tr["exit_ctm"]),
                             med)
        if r["flag"]:
            key = (int(tr["sig_ctm"]), int(tr["fill_ctm"]))
            out.setdefault(key, {"flag": set()})
            out[key].update(
                {"sym": sym, "mode": mode, "h": h,
                 "dir": int(tr["dir"]), "sig_ctm": int(tr["sig_ctm"]),
                 "fill_ctm": int(tr["fill_ctm"]),
                 "entry": float(tr["entry"]),
                 "exit_ctm": int(tr["exit_ctm"]),
                 "exit": float(tr["exit"]), "reason": tr["reason"],
                 "r_x1": float(tr["r_x1"])})
            out[key]["flag"].add(r["reason"])
            out[key]["jump"] = r["jump"]
            out[key]["n_neigh"] = r["n_neigh"]
    for _, tr in df[np.abs(df.r_x1) > 5].iterrows():
        key = (int(tr["sig_ctm"]), int(tr["fill_ctm"]))
        out.setdefault(key, {"flag": set()})
        out[key].update(
            {"sym": sym, "mode": mode, "h": h,
             "dir": int(tr["dir"]), "sig_ctm": int(tr["sig_ctm"]),
             "fill_ctm": int(tr["fill_ctm"]),
             "entry": float(tr["entry"]),
             "exit_ctm": int(tr["exit_ctm"]),
             "exit": float(tr["exit"]), "reason": tr["reason"],
             "r_x1": float(tr["r_x1"])})
        out[key]["flag"].add("|R|>5")
    rows = list(out.values())
    for r in rows:
        r["flag"] = "+".join(sorted(r["flag"]))
    return rows


def spike_counts(df, m1, void, tag):
    """A1G reporting: flag count + flagged R among TP winners."""
    med = spike.day_med_range(m1, void)
    w = df[(df.reason == "tp") & (df.r_x1 > 0)]
    n, rf = 0, 0.0
    for _, tr in w.iterrows():
        r = spike.spike_flag(m1, void, int(tr["dir"]),
                             float(tr["exit"]), int(tr["exit_ctm"]),
                             med)
        if r["flag"]:
            n += 1; rf += float(tr["r_x1"])
    print(f"[audit {tag}] tp_winners={len(w)} flagged={n} "
          f"flagged_R={rf:.1f}", flush=True)
    return {"window": tag, "tp_winners": len(w), "flagged": n,
            "flagged_R": rf}


def concentration(df, tag):
    r = df.r_x1.to_numpy()
    net = r.sum()
    for q in (0.01, 0.05):
        k = max(1, int(np.ceil(len(r) * q)))
        top = np.sort(r)[-k:].sum()
        print(f"[conc {tag}] top{q:.0%}={top:.1f}R/net{net:.1f}R="
              f"{top/net:.3f}", flush=True)


def mdr250_xau(ctx):
    """Trailing-250-trading-day median daily range (price), known at
    the signal day (shifted: completed days only)."""
    day = ctx.m1["t"] // 86400
    rng_px = ctx.m1["h"] - ctx.m1["l"]
    dr = pd.Series(rng_px).groupby(day).agg(lambda x: np.nan)
    # daily range = day max high - min low
    hi = pd.Series(ctx.m1["h"]).groupby(day).max()
    lo = pd.Series(ctx.m1["l"]).groupby(day).min()
    dr = hi - lo
    return dr.rolling(250, min_periods=60).median().shift(1)


def main():
    import datetime
    t00 = time.time()
    lo, hi = dm.HOLDOUT
    # ---------- 3a unlock ----------
    dm.open_holdout(SYMS)
    ts = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    with open("LAB_LOG.md", "a") as f:
        f.write(f"\n[{ts}] HOLDOUT UNLOCKED for {SYMS} only (round 2G, "
                f"once, after PREREG_V7 frozen). Window ({lo},{hi}]. "
                f"All other symbols remain sealed (whitelist).\n")
    print(f"[2G] unlock {ts} window=({lo},{hi})", flush=True)
    # ---------- 3b census ----------
    cens = []
    detail = {}
    m1h = {}
    ctxs = {}
    voids = {}
    for sym in SYMS:
        m1 = dm.load_m1(sym, lo, hi, allow_holdout=True)
        m1h[sym] = m1
        r, d = run_census(sym, m1)
        cens.append(r); detail[sym] = d
        print(f"[2G census] {sym} bars={r['m1_bars']} "
              f"wk={r['weeks_with_data']}/{r['weeks_span']} "
              f"gaps={r['weekday_gaps_gt60m']} dup={r['dup_ts']} "
              f"e0s={r['e0s_bars']} >20%={r['gt20pct_bars']} "
              f"r10x={r['range10x_bars']}", flush=True)
    pd.DataFrame(cens).to_csv("out/census_2g.csv", index=False)
    import json
    with open("out/census_2g_detail.json", "w") as f:
        json.dump(detail, f)
    # ---------- 3c the read ----------
    frames = {}          # (sym, mode, h) -> df
    cap_rows = []
    eur_ctx = runner.get_ctx("EURUSD")          # sealed ctx (DESIGN mdr)
    mdr_eur = st.median_daily_range_pips(
        eur_ctx.tf, dm.DESIGN[0], dm.DESIGN[1], "EURUSD")
    mult = 120.0 / mdr_eur
    for sym in SYMS:
        ctx = runner.get_ctx_upto(sym, dm.COMMON_END, allow_holdout=True)
        ctxs[sym] = ctx
        cap = None if sym == "EURUSD" else runner.sl_cap(ctx, sym)
        # orders: uncapped once, then derive fixed/relative subsets
        o_all = runner.orders_for(ctx, CFG, lo, hi, None)
        o_cap = runner.orders_for(ctx, CFG, lo, hi, cap)
        sig_day = np.array([int(ctx.tf["t"][o["t"]] // 86400)
                            for o in o_all])
        risk = np.array([abs(o["entry"] - o["sl"]) for o in o_all])
        # frozen candidate = capped GENERATION (cap skip inside the
        # generator precedes used_flip, so it is not a post-hoc filter
        # on o_all; verified 2026-09-24 - o_filt != o_cap by design).
        orders_fixed = o_cap if cap is not None else o_all
        hour, _, _ = dm.london_parts(np.array(
            [int(ctx.tf["t"][o["t"]]) for o in orders_fixed]))
        am_ix = np.array([7 <= hh < 12 for hh in hour])
        am_all = np.array([7 <= hh < 12 for hh in dm.london_parts(
            np.array([int(ctx.tf["t"][o["t"]]) for o in o_all]))[0]])
        # cap binding per calendar year over D+V+H (uncapped stream)
        if sym == "XAUUSD":
            mdr250_full = mdr250_xau(ctx)
            streams = []   # (window, order, sig_ctm, risk, day, am)
            ctx_v = runner.get_ctx(sym, 15)   # sealed ctx for D+V
            for wlo, whi, wname in ((dm.DESIGN[0], dm.DESIGN[1],
                                     "DESIGN"),
                                    (dm.VALIDATION[0], dm.VALIDATION[1],
                                     "VALIDATION")):
                oo = runner.orders_for(ctx_v, CFG, wlo, whi, None)
                sigs = np.array([int(ctx_v.tf["t"][o["t"]])
                                 for o in oo])
                hh = dm.london_parts(sigs)[0]
                for o, sc, h_ in zip(oo, sigs, hh):
                    streams.append((wname, sc,
                                    abs(o["entry"] - o["sl"]),
                                    int(sc // 86400), 7 <= h_ < 12))
            for o, rk, dy, a_ in zip(o_all, risk, sig_day, am_all):
                streams.append(("HOLDOUT",
                                int(ctx.tf["t"][o["t"]]), rk, dy, a_))
            sdf = pd.DataFrame(streams, columns=[
                "window", "sig_ctm", "risk", "day", "am"])
            sdf["yr"] = pd.to_datetime(
                sdf["sig_ctm"], unit="s").dt.year
            for (wname, y), g2 in sdf.groupby(["window", "yr"]):
                rc = g2["day"].map(
                    lambda d: mult * mdr250_full.get(d, np.nan))
                cap_rows.append({
                    "sym": sym, "window": wname, "year": int(y),
                    "n_sig": len(g2),
                    "rej_fixed": int((g2.risk > cap).sum()),
                    "rej_rel": int((g2.risk > rc).sum()),
                    "am_fixed": int((g2.am & (g2.risk <= cap)).sum()),
                    "am_rel": int((g2.am & (g2.risk <= rc)).sum())})
        mask = e0.second_stamp(ctx.m1)
        voids[sym] = mask
        for e1 in (True, False):
            h = "H1" if e1 else "H0"
            am_orders = [o for o, a in zip(orders_fixed, am_ix) if a]
            fr = sm.run_trades(ctx.m1, ctx.tf, am_orders, sym,
                               atr=ctx.atr, skip_suspect=e1,
                               void_extra=mask)
            fr = fr[fr.fill_ctm >= lo]
            fr["sym"] = sym
            fr.to_csv(f"out/trades_2g_{sym}_FR_e0s"
                      f"{'_e1' if e1 else ''}.csv", index=False)
            frames[(sym, "FR", h)] = fr
            print(f"[2G {h} FR] {sym} n={len(fr)} "
                  f"pf={pf(fr.r_x1):.3f}", flush=True)
            fl = sm.run_trades(ctx.m1, ctx.tf, orders_fixed, sym,
                               atr=ctx.atr, skip_suspect=e1,
                               void_extra=mask)
            fl = fl[fl.fill_ctm >= lo]
            fl["sym"] = sym
            hh_fl, _, _ = dm.london_parts(fl["sig_ctm"].to_numpy())
            fl["am_pm"] = np.where(hh_fl < 7, "OUT",
                          np.where(hh_fl < 12, "AM",
                          np.where(hh_fl < 16, "PM", "OUT")))
            fl.to_csv(f"out/trades_2g_{sym}_FL_e0s"
                      f"{'_e1' if e1 else ''}.csv", index=False)
            frames[(sym, "FL", h)] = fl
            print(f"[2G {h} FL] {sym} n={len(fl)} "
                  f"am={int((fl.am_pm=='AM').sum())}", flush=True)
        # ----- relative-cap arm (reported only) -----
        if sym == "XAUUSD":
            mdr250 = mdr250_xau(ctx)
            o_rel = [o for o, rk, dy in zip(o_all, risk, sig_day)
                     if rk <= mult * mdr250.get(dy, np.nan)]
            hour_r, _, _ = dm.london_parts(np.array(
                [int(ctx.tf["t"][o["t"]]) for o in o_rel]))
            am_rel = np.array([7 <= hh < 12 for hh in hour_r])
            for e1 in (True, False):
                h = "H1" if e1 else "H0"
                fr = sm.run_trades(ctx.m1, ctx.tf,
                                   [o for o, a in zip(o_rel, am_rel)
                                    if a], sym, atr=ctx.atr,
                                   skip_suspect=e1, void_extra=mask)
                fr = fr[fr.fill_ctm >= lo]
                fr["sym"] = sym
                fr.to_csv(f"out/trades_2g_{sym}_RELFR_e0s"
                          f"{'_e1' if e1 else ''}.csv", index=False)
                frames[(sym, "RELFR", h)] = fr
                fl = sm.run_trades(ctx.m1, ctx.tf, o_rel, sym,
                                   atr=ctx.atr, skip_suspect=e1,
                                   void_extra=mask)
                fl = fl[fl.fill_ctm >= lo]
                fl["sym"] = sym
                hh_fl, _, _ = dm.london_parts(fl["sig_ctm"].to_numpy())
                fl["am_pm"] = np.where(hh_fl < 7, "OUT",
                              np.where(hh_fl < 12, "AM",
                              np.where(hh_fl < 16, "PM", "OUT")))
                frames[(sym, "RELFL", h)] = fl
                print(f"[2G {h} REL] {sym} fr={len(fr)} fl={len(fl)}",
                      flush=True)
            # cap binding per year over all windows
            yr = pd.to_datetime(pd.Series(
                [ctx.tf["t"][o["t"]] for o in o_all]),
                unit="s").dt.year
            am_all = np.array([7 <= hh < 12 for hh in
                               dm.london_parts(np.array(
                                   [int(ctx.tf["t"][o["t"]])
                                    for o in o_all]))[0]])
            for y, g in pd.DataFrame(
                    {"yr": yr, "risk": risk, "day": sig_day,
                     "am": am_all}).groupby("yr"):
                rc = g["day"].map(lambda d: mult * mdr250.get(d, np.nan))
                cap_rows.append({
                    "sym": sym, "year": int(y), "window": "HOLDOUT",
                    "n_sig": len(g),
                    "rej_fixed": int((g.risk > cap).sum()),
                    "rej_rel": int((g.risk > rc).sum()),
                    "am_fixed": int((g.am & (g.risk <= cap)).sum()),
                    "am_rel": int((g.am & (g.risk <= rc)).sum())})
    pd.DataFrame(cap_rows).to_csv("out/cap_binding_2g.csv", index=False)
    print("[2G] read done, gates next", flush=True)
    # ---------- gates ----------
    pooled = {}
    for mode in ("FR", "FL", "RELFR", "RELFL"):
        for h in ("H1", "H0"):
            ks = [(s, mode, h) for s in SYMS if (s, mode, h) in frames]
            if ks:
                pooled[(mode, h)] = pd.concat(
                    [frames[k] for k in ks], ignore_index=True)
    g = []
    def cell(gate, mode, h, value, thresh, passed):
        g.append({"gate": gate, "mode": mode, "h": h,
                  "value": value, "thresh": thresh, "pass": passed})
    inconclusive = []
    for h in ("H1", "H0"):
        for mode in ("FR", "FL"):
            df = pooled[(mode, h)]
            am = df[df.am_pm == "AM"] if mode == "FL" else df
            cell("G1", mode, h, pf(am.r_x1), ">=1.10",
                 pf(am.r_x1) >= 1.10 and am.r_x1.mean() > 0)
    frh1 = pooled[("FR", "H1")]
    # A1G: G1b gate - pooled AM PF_R x1 H1 FR after removing the
    # single largest winner of EACH symbol (2 trades) >= 1.05.
    keep = np.ones(len(frh1), dtype=bool)
    rr = frh1.r_x1.to_numpy()
    for s in SYMS:
        pos = np.nonzero((frh1.sym == s).to_numpy())[0]
        keep[pos[np.argmax(rr[pos])]] = False
    g1b_pf = pf(frh1.r_x1[keep])
    cell("G1b", "FR", "H1", g1b_pf, ">=1.05", g1b_pf >= 1.05)
    big = frh1[np.abs(frh1.r_x1) <= 5]
    cell("G1r(reported)", "FR", "H1", pf(big.r_x1), ">=1.05",
         pf(big.r_x1) >= 1.05)
    for mode in ("FR", "FL"):
        df = pooled[(mode, "H1")]
        am = df[df.am_pm == "AM"] if mode == "FL" else df
        r_g2 = swap_adj.swap_adj_r(am, mult=2.0, rcol="r_x15")
        cell("G2", mode, "H1", pf(r_g2), ">=1.00", pf(r_g2) >= 1.00)
    for sym in SYMS:
        df = frames[(sym, "FR", "H1")]
        wk_cov = cens[SYMS.index(sym)]["coverage"]
        ok = len(df) >= 150 and wk_cov >= 0.90
        if not ok:
            inconclusive.append(f"G3/{sym}")
        cell("G3", "FR", "H1", pf(df.r_x1), ">1.00",
             (pf(df.r_x1) > 1.00) if ok else None)
        if not ok:
            g[-1]["pass"] = "INCONCLUSIVE"
    flh1 = pooled[("FL", "H1")]
    am = flh1.am_pm == "AM"
    sep = float(flh1.loc[am, "r_x1"].mean()
                - flh1.loc[~am, "r_x1"].mean())
    cell("G4", "FL", "H1", sep, ">0", sep > 0)
    dd = mc_dd(frh1.r_x1.to_numpy())
    yr = pd.to_datetime(pd.Series(frh1.fill_ctm.to_numpy()),
                        unit="s").dt.year.to_numpy()
    nets = pd.Series(frh1.r_x1.to_numpy()).groupby(yr).sum()
    pos_yrs = int((nets > 0).sum())
    cell("G5a", "FR", "H1", dd, "<=50", dd <= 50)
    cell("G5b", "FR", "H1", pos_yrs, ">=3/4", pos_yrs >= 3)
    gdf = pd.DataFrame(g)
    gdf.to_csv("out/gates_2g.csv", index=False)
    gated = gdf[~gdf.gate.str.contains("reported")]
    n_fail = int((gated["pass"] == False).sum())
    verdict = ("FAIL" if n_fail else
               "INCONCLUSIVE" if inconclusive else "PASS")
    print(f"[2G] VERDICT={verdict} fails={n_fail} "
          f"inconclusive={inconclusive}", flush=True)
    print(gdf.to_string(index=False), flush=True)
    # ---------- reported items ----------
    rep = {}
    for h in ("H1", "H0"):
        df = pooled[("FR", h)]
        yr2 = pd.to_datetime(pd.Series(df.fill_ctm.to_numpy()),
                             unit="s").dt.year.to_numpy()
        rep[f"peryear_{h}"] = pd.DataFrame(
            {"net_R": df.r_x1.groupby(yr2).sum(),
             "pf": df.groupby(yr2)["r_x1"].apply(pf)})
    for k, v in rep.items():
        v.to_csv(f"out/report_2g_{k}.csv")
    # +/-5R list both harnesses
    ext = []
    for (sym, mode, h), df in frames.items():
        for _, r in df[np.abs(df.r_x1) > 5].iterrows():
            ext.append({"sym": sym, "mode": mode, "h": h,
                        "sig_ctm": r["sig_ctm"], "dir": r["dir"],
                        "fill_ctm": r["fill_ctm"],
                        "exit_ctm": r["exit_ctm"], "reason": r["reason"],
                        "r_x1": r["r_x1"]})
    pd.DataFrame(ext).to_csv("out/extreme_2g.csv", index=False)
    # H0-H1 residual
    res = []
    for sym in SYMS:
        for mode in ("FR", "FL"):
            t0 = frames[(sym, mode, "H0")]
            t1 = frames[(sym, mode, "H1")]
            susp = t0[t0.suspect_fill | t0.suspect_exit]
            mod = (t0.exit_ctm.to_numpy() % 86400) // 60
            r0_, r1_ = sm.ROLL[sym][0][0], sm.ROLL[sym][0][1]
            in_roll = (mod >= r0_) | (mod < r1_) if r1_ < r0_ \
                else (mod >= r0_) & (mod < r1_)
            res.append({"sym": sym, "mode": mode, "n_h0": len(t0),
                        "n_h1": len(t1), "pf_h0": pf(t0.r_x1),
                        "pf_h1": pf(t1.r_x1),
                        "n_susp": len(susp),
                        "r_susp": float(susp.r_x1.sum()),
                        "n_roll_exit": int(in_roll.sum()),
                        "r_roll_exit": float(
                            t0[in_roll].r_x1.sum())})
    pd.DataFrame(res).to_csv("out/h0h1_residual_2g.csv", index=False)
    # swap x1 + cost x2 columns
    for h in ("H1", "H0"):
        df = pooled[("FR", h)]
        am = df
        print(f"[2G {h} FR] swap_x1_pf="
              f"{pf(swap_adj.swap_adj_r(am, 1.0)):.3f} "
              f"cost_x2_pf={pf(am.r_x2):.3f}", flush=True)
    # ---------- A1G AUDIT RULE A ----------
    audit = []
    for (sym, mode, h), df in frames.items():
        if mode not in ("FR", "FL"):
            continue
        audit += audit_rows(df, ctxs[sym].m1, sym, mode, h,
                            voids[sym])
    adf = pd.DataFrame(audit).sort_values(
        ["sym", "h", "mode", "fill_ctm"])
    adf.to_csv("out/audit_list_2g.csv", index=False)
    print(f"[audit] HOLDOUT audit list: {len(adf)} trades", flush=True)
    # spike counts + flagged R for DESIGN, VALIDATION, HOLDOUT
    sc = []
    for sym in SYMS:
        ctx_v = runner.get_ctx(sym, 15)
        vv = e0.second_stamp(ctx_v.m1)
        for wname, pat in (("DESIGN", "out/trades_2f_{s}_X0-HOLD_e0s"),
                           ("VALIDATION",
                            "out/trades_2fval_{s}_X0-HOLD_e0s")):
            for e1 in (True, False):
                f = pat.format(s=sym) + ("_e1" if e1 else "") + ".csv"
                if not os.path.exists(f):
                    continue
                d = pd.read_csv(f)
                sc.append(spike_counts(
                    d, ctx_v.m1, vv,
                    f"{wname}/{sym}/{'H1' if e1 else 'H0'}/FL"))
        for e1 in (True, False):
            for mode in ("FR", "FL"):
                df = frames[(sym, mode, "H1" if e1 else "H0")]
                sc.append(spike_counts(
                    df, ctxs[sym].m1, voids[sym],
                    f"HOLDOUT/{sym}/{'H1' if e1 else 'H0'}/{mode}"))
    pd.DataFrame(sc).to_csv("out/spike_counts_2g.csv", index=False)
    # payoff concentration D/V/H (pooled AM FR-equivalent)
    for wname, df in (("DESIGN", None), ("VALIDATION", None),
                      ("HOLDOUT", pooled[("FR", "H1")])):
        if df is None:
            f = [f"out/trades_2f_{s}_X0-HOLD_e0s_e1.csv"
                 for s in SYMS]
            d = pd.concat([pd.read_csv(x) for x in f
                           if os.path.exists(x)], ignore_index=True)
            if "am_pm" in d.columns:
                d = d[d.am_pm == "AM"]
            elif wname == "DESIGN":
                hh_, _, _ = dm.london_parts(d.sig_ctm.to_numpy())
                d = d[(hh_ >= 7) & (hh_ < 12)]
            if wname == "VALIDATION":
                f2 = [f"out/trades_2fval_{s}_AMONLY_e0s_e1.csv"
                      for s in SYMS]
                d = pd.concat([pd.read_csv(x) for x in f2
                               if os.path.exists(x)],
                              ignore_index=True)
            df = d
        concentration(df, wname)
    print(f"[2G] done {time.time()-t00:.0f}s", flush=True)


if __name__ == "__main__":
    main()
