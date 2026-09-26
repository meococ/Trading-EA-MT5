"""rerun_2f_e0s.py - A4F STEP 2: re-apply frozen 2F rules under E0'.

E0' = void_extra = second_stamp (malformed, non-minute-aligned bars).
Orders unchanged (versioned cache F2_NH_b_dstfix); only fills/exits
move. Same single VALIDATION read with a data bug fixed - provisional.

Outputs (suffix _e0s, never overwrites _dstfix / first-computation):
  trades_2f_<sym>_X0-HOLD_e0s(_e1).csv   DESIGN fixed list
  trades_2fval_<sym>_X0-HOLD_e0s(_e1).csv VALIDATION fixed list
  trades_2fval_<sym>_AMONLY_e0s(_e1).csv  VALIDATION free-running
  e0s_diff_design.csv / e0s_diff_val.csv  changed-trade audit
  confirm_2f_e0s_pooled/persym.csv        K1-K3 inputs on C
  val_2f_e0s_pooled.csv / val_2f_e0s_free.csv / val_2f_e0s_persym_*.csv
  portfolio_2f_e0s.csv
  sens_2f_pooled.csv                      V1-V3 under (iii) price-E0
  extreme_2f_audit.csv                    |r_x1|>5 under (i)+(ii)
  h0h1_residual.csv                       H0-H1 diff + roll attribution
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

from src import data as dm
from src import e0
from src import runner
from src import sim as sm
from src.variants.registry import CONFIGS
from validation_2f import (orders_once, pf, joint_boot, label_df,
                           swap_adj_r, cap_filter, mc_dd, london_week,
                           london_year)
from confirm_2f import sep_stat, joint_boot as c_boot

ALL = list(dm.ALL_SYMBOLS)
C_SET = ["NZDUSD", "USDCAD", "EURJPY", "AUDJPY", "EURGBP"]
CFG = [c for c in CONFIGS if c["id"] == "F2_NH_b"][0]
TOL = 1e-9
SS = {}   # sym -> second_stamp mask aligned to ctx.m1


def void_mask(sym, ctx):
    if sym not in SS:
        SS[sym] = e0.second_stamp(ctx.m1)
    return SS[sym]


def price_e0_mask(sym, ctx):
    """LEAD_NOTE_5 3%/15min rule - sensitivity cell only, labelled
    'voids real events - not valid'."""
    z = np.load(f"out/e0_flags_{sym}.npz")
    if len(z["t"]) == len(ctx.m1["t"]) and \
            np.array_equal(z["t"], ctx.m1["t"]):
        return z["flag"]
    return np.isin(ctx.m1["t"], z["t"][z["flag"]])


def sim_orders(sym, orders, e1, mask):
    ctx = runner.get_ctx(sym, 15)
    return sm.run_trades(ctx.m1, ctx.tf, orders, sym, atr=ctx.atr,
                         skip_suspect=e1, void_extra=mask)


def diff_audit(old, new, label):
    """Join on (sig_ctm,dir); per changed trade before/after r_x1 and
    helped/hurt (delta r_x1 sign). Not one-sided by construction."""
    m = old.merge(new[["sig_ctm", "dir", "r_x1", "exit_ctm", "sym"]],
                  on=["sig_ctm", "dir"], how="outer", indicator=True,
                  suffixes=("_old", "_new"))
    m["sym"] = m["sym_old"].fillna(m["sym_new"])
    rows = []
    for _, r in m.iterrows():
        if r["_merge"] == "left_only":
            rows.append({"sym": r["sym"], "sig_ctm": r["sig_ctm"],
                         "dir": r["dir"], "kind": "removed",
                         "r_old": r["r_x1_old"], "r_new": np.nan,
                         "delta": -r["r_x1_old"]})
        elif r["_merge"] == "right_only":
            rows.append({"sym": r["sym"], "sig_ctm": r["sig_ctm"],
                         "dir": r["dir"], "kind": "added",
                         "r_old": np.nan, "r_new": r["r_x1_new"],
                         "delta": r["r_x1_new"]})
        elif abs(r["r_x1_new"] - r["r_x1_old"]) > TOL:
            rows.append({"sym": r["sym"], "sig_ctm": r["sig_ctm"],
                         "dir": r["dir"], "kind": "changed",
                         "r_old": r["r_x1_old"], "r_new": r["r_x1_new"],
                         "delta": r["r_x1_new"] - r["r_x1_old"]})
    d = pd.DataFrame(rows)
    if len(d):
        d["window"] = label
        d["helped"] = d["delta"] > 0
    return d


def main():
    t00 = time.time()
    # ---------- 1. DESIGN _e0s rerun + audit ----------
    des_diff = []
    for sym in ALL:
        ctx = runner.get_ctx(sym, 15)
        cap = None if sym == "EURUSD" else runner.sl_cap(ctx, sym)
        orders = orders_once(sym, dm.DESIGN, cap)
        mask = void_mask(sym, ctx)
        for e1 in (True, False):
            h = "H1" if e1 else "H0"
            tr = sm.run_trades(ctx.m1, ctx.tf, orders, sym, atr=ctx.atr,
                               skip_suspect=e1, void_extra=mask)
            tr["sym"] = sym
            tr.to_csv(f"out/trades_2f_{sym}_X0-HOLD_e0s"
                      f"{'_e1' if e1 else ''}.csv", index=False)
            old = pd.read_csv(f"out/trades_2f_{sym}_X0-HOLD_dstfix"
                              f"{'_e1' if e1 else ''}.csv")
            old["sym"] = sym
            d = diff_audit(old, tr, "DESIGN")
            d["harness"] = h
            des_diff.append(d)
            print(f"[e0s D {h}] {sym} n {len(old)}->{len(tr)} "
                  f"chg={0 if d is None else len(d)} "
                  f"pf {pf(old.r_x1):.3f}->{pf(tr.r_x1):.3f}", flush=True)
    dd = pd.concat([x for x in des_diff if x is not None and len(x)],
                   ignore_index=True) if any(
                       x is not None and len(x) for x in des_diff) \
        else pd.DataFrame()
    dd.to_csv("out/e0s_diff_design.csv", index=False)
    # ---------- 2. labels on _e0s (C only needed for K1-K3) ----------
    lab = {}
    for e1 in (True, False):
        h = "H1" if e1 else "H0"
        fr = []
        for sym in C_SET:
            tr = pd.read_csv(f"out/trades_2f_{sym}_X0-HOLD_e0s"
                             f"{'_e1' if e1 else ''}.csv")
            tr["sym"] = sym
            fr.append(label_df(tr))
        lab[h] = pd.concat(fr, ignore_index=True)
        lab[h].to_csv(f"out/labels_2f_e0s_{h}.csv", index=False)
    # ---------- 3. K1-K3 on C ----------
    rows = []
    for e1 in (True, False):
        h = "H1" if e1 else "H0"
        c = lab[h]
        lo, _ = dm.DESIGN
        s0, lb, ub, sd, bs = c_boot(c, lo, sep_stat)
        am = c.am_pm == "AM"
        per = c.groupby(["sym", "am_pm"])["r_x1"].apply(pf).unstack()
        k1 = (lb > 0) if e1 else (s0 > 0)
        k2 = int((per["AM"] > per["PM"]).sum()) >= 4
        lo_s = c[c.dir == 1]; sh_s = c[c.dir == -1]
        sep_l = (lo_s.loc[lo_s.am_pm == "AM", "r_x1"].mean()
                 - lo_s.loc[lo_s.am_pm == "PM", "r_x1"].mean())
        sep_s = (sh_s.loc[sh_s.am_pm == "AM", "r_x1"].mean()
                 - sh_s.loc[sh_s.am_pm == "PM", "r_x1"].mean())
        yr = c[c.lon_year.isin(range(2010, 2020))]
        pery = yr.groupby(["lon_year", "am_pm"])["r_x1"].apply(pf)\
                 .unstack()
        n_y = int((pery["AM"] > pery["PM"]).sum())
        k3 = (sep_l > 0) and (sep_s > 0) and (n_y >= 6)
        rows.append({"harness": h, "sep": s0, "lb95": lb, "k1": bool(k1),
                     "am_gt_pm_syms": int((per["AM"] > per["PM"]).sum()),
                     "k2": bool(k2), "sep_long": float(sep_l),
                     "sep_short": float(sep_s), "am_gt_pm_years": n_y,
                     "k3": bool(k3),
                     "pf_am": pf(c.loc[am, "r_x1"]),
                     "pf_pm": pf(c.loc[~am, "r_x1"])})
        print(f"[e0s C {h}] sep={s0:.4f} lb95={lb:.4f} K1={k1} "
              f"K2={k2}({int((per['AM']>per['PM']).sum())}/5) "
              f"K3={k3}(long={sep_l:.3f} short={sep_s:.3f} y={n_y}/10)",
              flush=True)
    pd.DataFrame(rows).to_csv("out/confirm_2f_e0s_pooled.csv",
                              index=False)
    # ---------- 4. VALIDATION _e0s (same single read, bug fixed) ----
    lo, hi = dm.VALIDATION
    try:
        dm.load_m1("EURUSD", dm.HOLDOUT_START + 60, dm.COMMON_END)
        raise SystemExit("HOLDOUT READ DID NOT RAISE - STOP")
    except PermissionError as ex:
        print(f"[VAL-e0s] holdout guard OK: {ex}", flush=True)
    val_diff = []
    pooled = []
    persym_out = []
    free_rows = []
    fixed, free = {}, {}
    for e1 in (True, False):
        h = "H1" if e1 else "H0"
        for sym in ALL:
            ctx = runner.get_ctx(sym, 15)
            cap = None if sym == "EURUSD" else runner.sl_cap(ctx, sym)
            orders = orders_once(sym, (lo, hi), cap)
            mask = void_mask(sym, ctx)
            hour, _, _ = dm.london_parts(np.array(
                [int(ctx.tf["t"][o["t"]]) for o in orders]))
            am_orders = [o for o, hh in zip(orders, hour)
                         if 7 <= hh < 12]
            tr = sm.run_trades(ctx.m1, ctx.tf, orders, sym, atr=ctx.atr,
                               skip_suspect=e1, void_extra=mask)
            tr = tr[tr.fill_ctm >= lo]
            tr = label_df(tr); tr["sym"] = sym
            tr.to_csv(f"out/trades_2fval_{sym}_X0-HOLD_e0s"
                      f"{'_e1' if e1 else ''}.csv", index=False)
            fixed[(sym, h)] = tr
            fr = sm.run_trades(ctx.m1, ctx.tf, am_orders, sym,
                               atr=ctx.atr, skip_suspect=e1,
                               void_extra=mask)
            fr = fr[fr.fill_ctm >= lo]
            fr = label_df(fr); fr["sym"] = sym
            fr.to_csv(f"out/trades_2fval_{sym}_AMONLY_e0s"
                      f"{'_e1' if e1 else ''}.csv", index=False)
            free[(sym, h)] = fr
            old = pd.read_csv(f"out/trades_2fval_{sym}_X0-HOLD"
                              f"{'_e1' if e1 else ''}.csv")
            old["sym"] = sym
            d = diff_audit(old, tr, "VALIDATION")
            d["harness"] = h
            val_diff.append(d)
            print(f"[e0s V {h}] {sym} fixed n={len(tr)} "
                  f"free n={len(fr)} chg={0 if d is None else len(d)}",
                  flush=True)
    vd = pd.concat([x for x in val_diff if x is not None and len(x)],
                   ignore_index=True) if any(
                       x is not None and len(x) for x in val_diff) \
        else pd.DataFrame()
    vd.to_csv("out/e0s_diff_val.csv", index=False)
    # ---------- 5. V1-V3 on _e0s ----------
    for e1 in (True, False):
        h = "H1" if e1 else "H0"
        df = pd.concat([fixed[(s, h)] for s in ALL], ignore_index=True)
        am = df.am_pm == "AM"
        st = joint_boot(df, lo)
        sep = (df.loc[am, "r_x1"].mean() - df.loc[~am, "r_x1"].mean())
        per = df.groupby(["sym", "am_pm"])["r_x1"].apply(pf).unstack()
        pooled.append({"harness": h,
                       "pf_am_x1": pf(df.loc[am, "r_x1"]),
                       "pf_pm_x1": pf(df.loc[~am, "r_x1"]),
                       "pf_am_x15": pf(df.loc[am, "r_x15"]),
                       "exp_am": float(df.loc[am, "r_x1"].mean()),
                       "sep": float(sep),
                       "sep_lb95": float(np.quantile(st, 0.05)),
                       "n_syms_am_gt1": int((per["AM"] > 1.0).sum()),
                       "pf_am_swap": pf(swap_adj_r(df)[am]),
                       "gross_am": pf(df.loc[am, "r_gross"]),
                       "gross_pm": pf(df.loc[~am, "r_gross"])})
        per.to_csv(f"out/val_2f_e0s_persym_{h}.csv")
        yr = df.groupby(["lon_year", "am_pm"])["r_x1"].apply(pf).unstack()
        print(f"[e0s VAL {h}] per-year AM/PM:\n{yr.round(3)}", flush=True)
        fr = pd.concat([free[(s, h)] for s in ALL], ignore_index=True)
        fam = fr[fr.am_pm == "AM"]
        free_rows.append({"harness": h, "n": len(fr),
                          "am_n": len(fam), "pf_x1": pf(fam.r_x1),
                          "pf_x15": pf(fam.r_x15),
                          "exp": float(fam.r_x1.mean())})
    pd.DataFrame(pooled).to_csv("out/val_2f_e0s_pooled.csv", index=False)
    pd.DataFrame(free_rows).to_csv("out/val_2f_e0s_free.csv",
                                   index=False)
    print(pd.DataFrame(pooled).round(4).to_string(index=False),
          flush=True)
    print(pd.DataFrame(free_rows).round(4).to_string(index=False),
          flush=True)
    # ---------- 6. sensitivity cell (iii): price-E0, NOT VALID ------
    sens = []
    for e1 in (True, False):
        h = "H1" if e1 else "H0"
        fdf = []
        ffree = []
        for sym in ALL:
            ctx = runner.get_ctx(sym, 15)
            cap = None if sym == "EURUSD" else runner.sl_cap(ctx, sym)
            orders = orders_once(sym, (lo, hi), cap)
            pmask = price_e0_mask(sym, ctx)
            tr = sm.run_trades(ctx.m1, ctx.tf, orders, sym, atr=ctx.atr,
                               skip_suspect=e1, void_extra=pmask)
            tr = tr[tr.fill_ctm >= lo]
            tr = label_df(tr); tr["sym"] = sym
            fdf.append(tr)
            hour, _, _ = dm.london_parts(np.array(
                [int(ctx.tf["t"][o["t"]]) for o in orders]))
            am_orders = [o for o, hh in zip(orders, hour)
                         if 7 <= hh < 12]
            fr = sm.run_trades(ctx.m1, ctx.tf, am_orders, sym,
                               atr=ctx.atr, skip_suspect=e1,
                               void_extra=pmask)
            fr = fr[fr.fill_ctm >= lo]
            ffree.append(label_df(fr))
        df = pd.concat(fdf, ignore_index=True)
        fr = pd.concat(ffree, ignore_index=True)
        am = df.am_pm == "AM"
        st = joint_boot(df, lo)
        sep = (df.loc[am, "r_x1"].mean() - df.loc[~am, "r_x1"].mean())
        per = df.groupby(["sym", "am_pm"])["r_x1"].apply(pf).unstack()
        fam = fr[fr.am_pm == "AM"]
        sens.append({"variant": "priceE0_3pct_15m_INVALID",
                     "harness": h,
                     "pf_am_x1": pf(df.loc[am, "r_x1"]),
                     "pf_am_x15": pf(df.loc[am, "r_x15"]),
                     "exp_am": float(df.loc[am, "r_x1"].mean()),
                     "sep": float(sep),
                     "sep_lb95": float(np.quantile(st, 0.05)),
                     "n_syms_am_gt1": int((per["AM"] > 1.0).sum()),
                     "free_pf_x1": pf(fam.r_x1),
                     "free_exp": float(fam.r_x1.mean())})
        print(f"[sens priceE0 {h}] pf_am={pf(df.loc[am,'r_x1']):.4f} "
              f"exp={df.loc[am,'r_x1'].mean():.4f} "
              f"free={pf(fam.r_x1):.4f}", flush=True)
    pd.DataFrame(sens).to_csv("out/sens_2f_pooled.csv", index=False)
    # ---------- 7. extreme-trade audit (i) vs (ii) ------------------
    ext = []
    for wname, tag in (("DESIGN", "trades_2f_{s}_X0-HOLD"),
                       ("VALIDATION", "trades_2fval_{s}_X0-HOLD")):
        for e1 in (True, False):
            h = "H1" if e1 else "H0"
            for sym in ALL:
                for variant, sfx in (("noE0", "_dstfix" if wname == "DESIGN"
                                      else ""),
                                     ("e0s", "_e0s")):
                    f = (f"out/{tag.format(s=sym)}{sfx}"
                         f"{'_e1' if e1 else ''}.csv")
                    tr = pd.read_csv(f)
                    tr = tr[np.abs(tr.r_x1) > 5]
                    for _, r in tr.iterrows():
                        ext.append({"window": wname, "harness": h,
                                    "variant": variant, "sym": sym,
                                    "sig_ctm": r["sig_ctm"],
                                    "dir": r["dir"],
                                    "reason": r["reason"],
                                    "r_x1": r["r_x1"],
                                    "exit_ctm": r["exit_ctm"]})
    pd.DataFrame(ext).to_csv("out/extreme_2f_audit.csv", index=False)
    # ---------- 8. H0-H1 residual + roll attribution ----------------
    res = []
    for wname, lo_w, hi_w, tag in (
            ("DESIGN", *dm.DESIGN, "trades_2f_{s}_X0-HOLD_e0s"),
            ("VALIDATION", *dm.VALIDATION, "trades_2fval_{s}_X0-HOLD_e0s")):
        for sym in ALL:
            t0 = pd.read_csv(f"out/{tag.format(s=sym)}.csv")
            t1 = pd.read_csv(f"out/{tag.format(s=sym)}_e1.csv")
            if wname == "VALIDATION":
                t0 = t0[t0.fill_ctm >= lo_w]
                t1 = t1[t1.fill_ctm >= lo_w]
            # trades in H0 that touched suspect bars
            susp = t0[t0.suspect_fill | t0.suspect_exit]
            mod = (t0.exit_ctm.to_numpy() % 86400) // 60
            r0 = sm.ROLL[sym][0][0]; r1 = sm.ROLL[sym][0][1]
            in_roll = (mod >= r0) | (mod < r1) if r1 < r0 \
                else (mod >= r0) & (mod < r1)
            roll_tr = t0[in_roll]
            res.append({"window": wname, "sym": sym,
                        "n_h0": len(t0), "n_h1": len(t1),
                        "r_h0": float(t0.r_x1.sum()),
                        "r_h1": float(t1.r_x1.sum()),
                        "pf_h0": pf(t0.r_x1), "pf_h1": pf(t1.r_x1),
                        "n_susp_touch": len(susp),
                        "r_susp": float(susp.r_x1.sum()),
                        "n_exit_in_roll": int(in_roll.sum()),
                        "r_exit_in_roll": float(roll_tr.r_x1.sum())})
    rdf = pd.DataFrame(res)
    rdf.to_csv("out/h0h1_residual.csv", index=False)
    print(rdf.round(3).to_string(index=False), flush=True)
    # ---------- 9. portfolios on _e0s -------------------------------
    des_free = {}
    for e1 in (True, False):
        h = "H1" if e1 else "H0"
        for sym in ALL:
            ctx = runner.get_ctx(sym, 15)
            cap = None if sym == "EURUSD" else runner.sl_cap(ctx, sym)
            orders = orders_once(sym, dm.DESIGN, cap)
            hour, _, _ = dm.london_parts(np.array(
                [int(ctx.tf["t"][o["t"]]) for o in orders]))
            am_orders = [o for o, hh in zip(orders, hour)
                         if 7 <= hh < 12]
            fr = sm.run_trades(ctx.m1, ctx.tf, am_orders, sym,
                               atr=ctx.atr, skip_suspect=e1,
                               void_extra=void_mask(sym, ctx))
            fr = fr[fr.fill_ctm >= dm.DESIGN[0]]
            fr["sym"] = sym
            des_free[(sym, h)] = fr
    port_rows = []
    for e1 in (True, False):
        h = "H1" if e1 else "H0"
        for view, syms in (("eur_xau", ["EURUSD", "XAUUSD"]),
                           ("all12", ALL)):
            for wname, src in (("DESIGN", des_free),
                               ("VALIDATION", free)):
                df = pd.concat([src[(s, h)] for s in syms],
                               ignore_index=True)
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
                        yrarr = london_year(tr2["exit_ctm"].to_numpy())
                        py = tr2.groupby(yrarr)["r_use"].sum()
                        port_rows.append({
                            "harness": h, "view": view, "window": wname,
                            "mode": mode, "swap": sw, "n": len(tr),
                            "trades_wk": len(tr) / wks if wks else np.nan,
                            "pf_r": pf(r),
                            "pos_years": float((py > 0).mean())
                            if len(py) else np.nan,
                            "mc_dd_p95": mc_dd(r) if len(r) > 3
                            else np.nan})
    pd.DataFrame(port_rows).to_csv("out/portfolio_2f_e0s.csv",
                                   index=False)
    print(pd.DataFrame(port_rows).round(3).to_string(index=False),
          flush=True)
    print(f"[e0s] done {time.time()-t00:.0f}s", flush=True)


if __name__ == "__main__":
    main()
