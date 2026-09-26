"""verify_2d.py - ROUND 2D mandatory tests T1/T4/T5 (real data).

T1 regression: X0 through the new exit layer reproduces the 2C trade
files row for row (exit_ctm, exit px, reason, r_x1 to 1e-9) for all 12
symbols, H0 and H1, BOTH modes (fixed list + free running).
T4: the X0 random-entry null through the new code path equals the old
    path for one symbol and one seed (same generator as 2C).
T5: X0-DF in free-running mode reproduces the 2C pf_r_x1_flat2350
    column for 2 D symbols, H0 and H1.
Also asserts: no X0 fill happens in [23:50, roll window end) on D, so
the daily flat never changes an entry.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

import order_cache
import managed as mg
from run_controls import _random_order
from run_controls_2c import _pool_ctx
from src import data as dm
from src import metrics as mt
from src import runner
from src import sim as sm

ALL12 = list(dm.BASKET) + ["EURUSD", "XAUUSD"]
D_SET = ["AUDUSD", "USDCHF", "GBPJPY", "USDJPY", "GBPUSD",
         "EURUSD", "XAUUSD"]


def _cmp(a, b, tol=1e-9):
    return np.allclose(np.asarray(a, float), np.asarray(b, float),
                       atol=tol, rtol=0, equal_nan=True)


def t1_symbol(sym, e1):
    tr0 = mg.load_x0(sym, e1)
    lc = mg.light_ctx(sym)
    # --- fixed list ----------------------------------------------------
    fl = mg.resim_trades(tr0, lc, sym, "X0", skip_suspect=e1)
    ok = (_cmp(fl["exit_ctm"], tr0["exit_ctm"]) and
          _cmp(fl["exit"], tr0["exit"]) and
          (fl["reason"].astype(str) == tr0["reason"].astype(str)).all() and
          _cmp(fl["r_x1"], tr0["r_x1"]) and
          _cmp(fl["r_x15"], tr0["r_x15"]) and
          _cmp(fl["r_x2"], tr0["r_x2"]))
    # --- free running ---------------------------------------------------
    ctx = runner.get_ctx(sym, 15)
    orders = order_cache.load_orders(sym, "F2_NH_b", dm.DESIGN)
    fr = sm.run_trades(ctx.m1, ctx.tf, orders, sym, atr=ctx.atr,
                       skip_suspect=e1, exit_rule="X0", tfx=lc["tfx"])
    fr = fr.reset_index(drop=True)
    ok2 = (len(fr) == len(tr0) and
           _cmp(fr["fill_ctm"], tr0["fill_ctm"]) and
           _cmp(fr["exit_ctm"], tr0["exit_ctm"]) and
           _cmp(fr["exit"], tr0["exit"]) and
           (fr["reason"].astype(str) == tr0["reason"].astype(str)).all()
           and _cmp(fr["r_x1"], tr0["r_x1"]))
    return ok, ok2, len(tr0)


def t4_null_equiv(sym="GBPUSD", seed=0):
    ctx = runner.get_ctx(sym, 15)
    lc = mg.light_ctx(sym)
    orders = order_cache.load_orders(sym, "F2_NH_b", dm.DESIGN)
    by_hd, pool, pool_by_hour = _pool_ctx(ctx, ctx.tf, orders, *dm.DESIGN)
    rng = np.random.default_rng(20_000 + seed)
    ro = []
    for (hh, dr), grp in by_hd.items():
        cand = pool_by_hour.get(hh)
        if cand is None or len(cand) == 0:
            cand = pool
        picks = rng.choice(cand, size=len(grp), replace=True)
        for src, tn in zip(grp, picks):
            ro.append(_random_order(src, int(tn), ctx.tf, rng))
    ro.sort(key=lambda o: o["t"])
    old = sm.run_trades(ctx.m1, ctx.tf, ro, sym, atr=ctx.atr)
    new = sm.run_trades(ctx.m1, ctx.tf, ro, sym, atr=ctx.atr,
                        exit_rule="X0", tfx=lc["tfx"])
    return (len(old) == len(new) and
            _cmp(old["r_x1"], new["r_x1"]) and
            _cmp(old["exit"], new["exit"]))


def t5_flat_equiv(syms=("AUDUSD", "EURUSD")):
    out = []
    for sym in syms:
        ctx = runner.get_ctx(sym, 15)
        lc = mg.light_ctx(sym)
        orders = order_cache.load_orders(sym, "F2_NH_b", dm.DESIGN)
        for e1 in (False, True):
            fr = sm.run_trades(ctx.m1, ctx.tf, orders, sym, atr=ctx.atr,
                               daily_flat_mod=1430, skip_suspect=e1,
                               exit_rule="X0", tfx=lc["tfx"])
            got = mt.pf_r(fr, "r_x1")
            fsum = ("out/design_summary_2c_e1.csv" if e1 and
                    os.path.exists("out/design_summary_2c_e1.csv")
                    else "out/design_summary_2c.csv") \
                if sym in dm.BASKET else \
                ("out/design_summary_e1.csv" if e1 and
                 os.path.exists("out/design_summary_e1.csv")
                 else "out/design_summary.csv")
            df = pd.read_csv(fsum)
            ref = float(df[(df.sym == sym) & (df.cfg == "F2_NH_b")]
                        ["pf_r_x1_flat2350"].iloc[0])
            out.append((sym, e1, got, ref, abs(got - ref) < 1e-9))
    return out


def assert_fill_window():
    """No X0 fill in [23:50, roll window end) on any D symbol/harness."""
    bad = []
    for sym in D_SET:
        (a, b), _s = sm.ROLL[sym]
        for e1 in (False, True):
            tr = mg.load_x0(sym, e1)
            mod = (tr["fill_ctm"].to_numpy() % 86400) // 60
            in_win = (mod >= 1430) | (mod < b)
            if in_win.any():
                bad.append((sym, e1, int(in_win.sum())))
    return bad


def main():
    t00 = time.time()
    print("[2D] T1 regression - all 12 symbols, H0/H1, both modes")
    fails = []
    for sym in ALL12:
        for e1 in (False, True):
            ok, ok2, n = t1_symbol(sym, e1)
            tag = "H1" if e1 else "H0"
            print(f"  {sym} {tag}: fixed={ok} free={ok2} n={n}",
                  flush=True)
            if not (ok and ok2):
                fails.append((sym, tag, ok, ok2))
    print(f"[2D] T1 done {time.time()-t00:.0f}s fails={fails}")

    print("[2D] T4 null equivalence GBPUSD seed 0:",
          t4_null_equiv(), flush=True)
    print("[2D] T5 flat2350 free-running:", flush=True)
    for row in t5_flat_equiv():
        print("  ", row, flush=True)
    print("[2D] fill-window assertion (must be []):",
          assert_fill_window(), flush=True)
    print(f"[2D] verify done {time.time()-t00:.0f}s")


if __name__ == "__main__":
    main()
