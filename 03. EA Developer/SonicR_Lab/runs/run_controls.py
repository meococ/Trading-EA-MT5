"""run_controls.py - negative controls + multiple-testing (D2/D3).

For each (symbol,cfg): reads the DESIGN trades file, rebuilds the
signal orders, then:
  (a) random-entry control: 100 seeds; each seed resamples the real
      signals' London-hour/dow distribution onto random London bars,
      reuses each real order's SL/TP geometry (risk px + R distance ->
      same shape), same pending model -> sim -> PF x1.
  (b) direction flip: same orders with dir inverted (entry/sl/tp
      mirrored around the signal close? no - same extreme offset, dir
      flipped: buy-stop becomes sell-stop at signal LOW - offset, SL/TP
      mirrored by the same price distances).
  (c) +20-bar time shift: order.t += 20 (same geometry).
Writes out/controls_summary.csv + out/controls_null.npz.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src import data as dm
from src import metrics as mt
from src import runner
from src.variants.registry import CONFIGS

SEEDS = 100
SEEDS_LOW = 20          # Lead backup plan: PF_R < 1.05 gets 20 seeds only
rng_master = np.random.default_rng(20260923)


def _mirror(o, tf):
    """Direction flip: same geometry, mirrored around signal extreme."""
    t = o["t"]; d = tf
    if o["dir"] == 1:
        dist_entry = o["entry"] - d["h"][t]
        dist_sl = o["entry"] - o["sl"]
        dist_tp = o["tp"] - o["entry"]
        entry = d["l"][t] - dist_entry
        return {**o, "dir": -1, "entry": entry,
                "sl": entry + dist_sl, "tp": entry - dist_tp}
    dist_entry = d["l"][t] - o["entry"]
    dist_sl = o["sl"] - o["entry"]
    dist_tp = o["entry"] - o["tp"]
    entry = d["h"][t] + dist_entry
    return {**o, "dir": 1, "entry": entry,
            "sl": entry - dist_sl, "tp": entry + dist_tp}


def _random_order(src_o, t_new, tf, rng):
    """Same geometry as src_o at a random bar t_new (dir resampled)."""
    d = tf
    dr = src_o["dir"] if rng.random() < 0.5 else -src_o["dir"]
    risk = abs(src_o["entry"] - src_o["sl"])
    rd = abs(src_o["tp"] - src_o["entry"])
    off = src_o["entry"] - (d["h"][src_o["t"]] if src_o["dir"] == 1
                          else d["l"][src_o["t"]])
    entry = (d["h"][t_new] + off) if dr == 1 else (d["l"][t_new] - off)
    sl = entry - dr * risk
    tp = entry + dr * rd
    return {"t": t_new, "dir": dr, "entry": float(entry), "sl": float(sl),
            "tp": float(tp), "expiry_ctm": int(d["t"][t_new]) +
            (src_o["expiry_ctm"] - int(d["t"][src_o["t"]])),
            "meta": dict(src_o["meta"])}


def controls_for(sym, cfg, ctx, orders, window, seeds=SEEDS):
    """Run (a)(b)(c) for one config; returns dict of percentiles."""
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
    tr_real = runner.sim.run_trades(ctx.m1, tf, orders, sym, atr=ctx.atr)
    real_pf = mt.pf_r(tr_real)              # E3: PF_R is the control metric
    # (a) random-entry null
    null_pfs = []
    by_hd = {}
    for o in orders:
        key = (hour[o["t"]], o["dir"])
        by_hd.setdefault(key, []).append(o)
    pool_by_hour = {h: pool[hour[pool] == h] for h in np.unique(hour[pool])}
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
        null_pfs.append(mt.pf_r(runner.sim.run_trades(
            ctx.m1, tf, ro, sym, atr=ctx.atr)))
    null_pfs = np.asarray(null_pfs)
    pct = float((null_pfs < real_pf).mean() * 100) if np.isfinite(real_pf) \
        else np.nan
    # (b) direction flip
    flipped = sorted((_mirror(o, tf) for o in orders), key=lambda o: o["t"])
    pf_flip = mt.pf_r(runner.sim.run_trades(
        ctx.m1, tf, flipped, sym, atr=ctx.atr))
    # (c) +20 bar shift
    shifted = []
    for o in orders:
        if o["t"] + 20 < t_hi:
            no = dict(o); no["t"] = o["t"] + 20
            d = tf
            if o["dir"] == 1:
                no["entry"] = d["h"][no["t"]] + (o["entry"] - d["h"][o["t"]])
            else:
                no["entry"] = d["l"][no["t"]] - (d["l"][o["t"]] - o["entry"])
            no["expiry_ctm"] = int(d["t"][no["t"]]) + \
                (o["expiry_ctm"] - int(d["t"][o["t"]]))
            no["sl"] = o["sl"] - o["entry"] + no["entry"]
            no["tp"] = o["tp"] - o["entry"] + no["entry"]
            shifted.append(no)
    pf_shift = mt.pf_r(runner.sim.run_trades(
        ctx.m1, tf, sorted(shifted, key=lambda o: o["t"]), sym,
        atr=ctx.atr))
    return {"real_pf": real_pf, "null_pfs": null_pfs, "pct": pct,
            "pf_flip": pf_flip, "pf_shift20": pf_shift,
            "n_signals": len(orders)}


def main():
    out_rows = []
    null_store = {}
    # Lead backup plan: seeds scale with DESIGN PF_R (100 if >=1.05 else 20)
    design_pfr = {}
    try:
        _d = pd.read_csv("out/design_summary.csv")
        design_pfr = {(r["sym"], r["cfg"]): r["pf_r_x1"]
                      for _, r in _d.iterrows()}
    except Exception:
        pass
    for sym in dm.SYMBOLS:
        ctx15 = runner.get_ctx(sym, 15)
        ctx5 = runner.get_ctx(sym, 5)
        cap = runner.xau_sl_cap(ctx15) if sym == "XAUUSD" else None
        for cfg in CONFIGS:
            t0 = time.time()
            ctx = ctx5 if cfg["family"] == "F3" else ctx15
            ctx.reset_zones()
            orders = runner.orders_for(ctx, cfg, *dm.DESIGN, xau_cap=cap)
            if not orders:
                out_rows.append({"sym": sym, "cfg": cfg["id"],
                                 "n_signals": 0})
                continue
            des = design_pfr.get((sym, cfg["id"]), 0.0)
            seeds = SEEDS if (np.isfinite(des) and des >= 1.05) \
                else SEEDS_LOW
            r = controls_for(sym, cfg, ctx, orders, dm.DESIGN, seeds)
            null_store[f"{sym}_{cfg['id']}"] = r["null_pfs"]
            out_rows.append({
                "sym": sym, "cfg": cfg["id"], "n_signals": r["n_signals"],
                "real_pf": r["real_pf"], "pct": r["pct"],
                "pf_flip": r["pf_flip"], "pf_shift20": r["pf_shift20"],
                "null_med": float(np.nanmedian(r["null_pfs"])),
                "null_p95": float(np.nanpercentile(r["null_pfs"], 95)),
            })
            print(f"[ctrl] {sym} {cfg['id']}: pf={r['real_pf']:.2f} "
                  f"pct={r['pct']:.0f} flip={r['pf_flip']:.2f} "
                  f"shift={r['pf_shift20']:.2f} ({time.time()-t0:.0f}s)",
                  flush=True)
            pd.DataFrame(out_rows).to_csv("out/controls_summary.csv",
                                          index=False)
    np.savez_compressed("out/controls_null.npz", **null_store)
    # best-of-N inflation: bootstrap max PF across configs under the null
    boots = []
    keys = list(null_store.keys())
    for b in range(2000):
        mx = 0.0
        for k in keys:
            v = null_store[k]
            if len(v):
                mx = max(mx, np.random.default_rng(b * 31 + hash(k) % 997)
                         .choice(v))
        boots.append(mx)
    boots = np.asarray(boots)
    print("max-PF null distribution: p50=%.3f p95=%.3f max=%.3f" %
          (np.nanpercentile(boots, 50), np.nanpercentile(boots, 95),
           np.nanmax(boots)))
    np.save("out/maxpf_null.npy", boots)


if __name__ == "__main__":
    main()
