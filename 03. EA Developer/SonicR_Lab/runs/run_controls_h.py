"""run_controls_h.py - negative controls on BOTH harnesses (addendum A1).

All 25 configs x 2 symbols. For each cell: real PF_R on H0 and H1,
then one permuted-order null per seed is evaluated on BOTH harnesses.
Seeds: 100 if max(PF_R_H0, PF_R_H1) >= 1.05 else 20 (Lead tier rule).
Writes out/controls_summary_h.csv (one row per cell x harness) and
out/controls_null_h.npz. Also direction-flip and +20-bar shift per
harness.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import order_cache
from run_controls import _mirror, _random_order
from src import data as dm
from src import metrics as mt
from src import runner
from src.variants.registry import CONFIGS
from src.variants.registry_2b import CONFIGS_2B

ALL = list(CONFIGS) + list(CONFIGS_2B)
SEEDS = 100
SEEDS_LOW = 20


def controls_dual(sym, ctx, orders, window, seeds):
    """Real + null on H0 and H1 for one cell."""
    tf = ctx.tf
    lo, hi = window
    t_lo = int(np.searchsorted(tf["t"], lo))
    t_hi = int(np.searchsorted(tf["t"], hi))
    hour = ctx.hour
    sess_mask = {"london_j": ctx.in_london_j, "london_ext": ctx.in_london_ext,
                 "ny_overlap": ctx.in_ny_overlap}.get(
                     orders[0]["meta"].get("session", "london_j")
                     if orders else "london_j", ctx.in_london_j)
    pool = np.nonzero(sess_mask & (np.arange(len(tf["t"])) >= t_lo)
                      & (np.arange(len(tf["t"])) < t_hi))[0]

    def real(skip):
        tr = runner.sim.run_trades(ctx.m1, tf, orders, sym, atr=ctx.atr,
                                   skip_suspect=skip)
        return mt.pf_r(tr)

    real_h0, real_h1 = real(False), real(True)
    # (a) random-entry null, same seeds on both harnesses
    by_hd = {}
    for o in orders:
        by_hd.setdefault((hour[o["t"]], o["dir"]), []).append(o)
    pool_by_hour = {h: pool[hour[pool] == h] for h in np.unique(hour[pool])}
    n0, n1 = [], []
    for s in range(seeds):
        rng = np.random.default_rng(10_000 + s)
        ro = []
        for (h, dr), grp in by_hd.items():
            cand = pool_by_hour.get(h)
            if cand is None or len(cand) == 0:
                cand = pool
            picks = rng.choice(cand, size=len(grp), replace=True)
            for src, tn in zip(grp, picks):
                ro.append(_random_order(src, int(tn), tf, rng))
        ro.sort(key=lambda o: o["t"])
        n0.append(mt.pf_r(runner.sim.run_trades(
            ctx.m1, tf, ro, sym, atr=ctx.atr, skip_suspect=False)))
        n1.append(mt.pf_r(runner.sim.run_trades(
            ctx.m1, tf, ro, sym, atr=ctx.atr, skip_suspect=True)))
    n0, n1 = np.asarray(n0), np.asarray(n1)

    def pct(nulls, rp):
        return float((nulls < rp).mean() * 100) if np.isfinite(rp) else np.nan

    # (b) flip + (c) +20b shift, both harnesses
    flipped = sorted((_mirror(o, tf) for o in orders), key=lambda o: o["t"])
    shifted = []
    for o in orders:
        if o["t"] + 20 < t_hi:
            no = dict(o); no["t"] = o["t"] + 20
            if o["dir"] == 1:
                no["entry"] = tf["h"][no["t"]] + (o["entry"] - tf["h"][o["t"]])
            else:
                no["entry"] = tf["l"][no["t"]] - (tf["l"][o["t"]] - o["entry"])
            no["expiry_ctm"] = int(tf["t"][no["t"]]) + \
                (o["expiry_ctm"] - int(tf["t"][o["t"]]))
            no["sl"] = o["sl"] - o["entry"] + no["entry"]
            no["tp"] = o["tp"] - o["entry"] + no["entry"]
            shifted.append(no)
    shifted = sorted(shifted, key=lambda o: o["t"])
    out = {"real_h0": real_h0, "real_h1": real_h1,
           "n0": n0, "n1": n1,
           "pct_h0": pct(n0, real_h0), "pct_h1": pct(n1, real_h1)}
    for lab, oo in (("flip", flipped), ("shift20", shifted)):
        out[f"pf_{lab}_h0"] = mt.pf_r(runner.sim.run_trades(
            ctx.m1, tf, oo, sym, atr=ctx.atr, skip_suspect=False))
        out[f"pf_{lab}_h1"] = mt.pf_r(runner.sim.run_trades(
            ctx.m1, tf, oo, sym, atr=ctx.atr, skip_suspect=True))
    out["n_signals"] = len(orders)
    return out


def main():
    rows = []
    null_store = {}
    # tier seeds on max PF_R across harnesses from the design summaries
    pfr = {}
    for f in ("out/design_summary.csv", "out/design_summary_e1.csv",
              "out/design_summary_2b.csv", "out/design_summary_2b_e1.csv"):
        try:
            d = pd.read_csv(f)
            h = "H1" if "_e1" in f else "H0"
            for _, r in d.iterrows():
                pfr[(r["sym"], r["cfg"], h)] = r["pf_r_x1"]
        except Exception:
            pass
    for sym in dm.SYMBOLS:
        ctx15 = runner.get_ctx(sym, 15)
        ctx5 = runner.get_ctx(sym, 5)
        for cfg in ALL:
            cid = cfg["id"]
            if cid in {c["id"] for c in CONFIGS_2B} and \
                    cid in {c["id"] for c in CONFIGS}:
                continue
            ctx = ctx5 if cfg["family"] == "F3" else ctx15
            orders = order_cache.load_orders(sym, cid, dm.DESIGN)
            if not orders:
                rows.append({"sym": sym, "cfg": cid, "harness": "H0",
                             "n_signals": len(orders or [])})
                rows.append({"sym": sym, "cfg": cid, "harness": "H1",
                             "n_signals": len(orders or [])})
                continue
            t0 = time.time()
            vals = [v for v in (pfr.get((sym, cid, "H0")),
                                pfr.get((sym, cid, "H1")))
                    if v is not None and np.isfinite(v)]
            seeds = SEEDS if (vals and max(vals) >= 1.05) else SEEDS_LOW
            r = controls_dual(sym, ctx, orders, dm.DESIGN, seeds)
            null_store[f"{sym}_{cid}_h0"] = r["n0"]
            null_store[f"{sym}_{cid}_h1"] = r["n1"]
            for h, rp, pc, nn in (("H0", r["real_h0"], r["pct_h0"], r["n0"]),
                                  ("H1", r["real_h1"], r["pct_h1"], r["n1"])):
                rows.append({"sym": sym, "cfg": cid, "harness": h,
                             "n_signals": r["n_signals"],
                             "real_pf_r": rp, "pct": pc,
                             "pf_flip": r[f"pf_flip_{h.lower()}"],
                             "pf_shift20": r[f"pf_shift20_{h.lower()}"],
                             "null_med": float(np.nanmedian(nn)),
                             "null_p95": float(np.nanpercentile(nn, 95)),
                             "seeds": seeds})
            print(f"[ctrl-h] {sym} {cid}: H0={r['real_h0']:.2f}"
                  f"({r['pct_h0']:.0f}%) H1={r['real_h1']:.2f}"
                  f"({r['pct_h1']:.0f}%) seeds={seeds} "
                  f"({time.time()-t0:.0f}s)", flush=True)
            pd.DataFrame(rows).to_csv("out/controls_summary_h.csv",
                                      index=False)
    np.savez_compressed("out/controls_null_h.npz", **null_store)


if __name__ == "__main__":
    main()
