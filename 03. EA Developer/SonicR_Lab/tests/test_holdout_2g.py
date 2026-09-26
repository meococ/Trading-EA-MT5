"""T11-T13 + swap hand-test (Round 2G pre-freeze).

T11: with HOLDOUT_OPEN={EURUSD,XAUUSD} and allow_holdout=True, a
holdout read still raises for GBPUSD and AUDJPY; for EURUSD it raises
when the flag is OFF and succeeds when ON.
T12: the new get_ctx_upto path, run with end=VALIDATION_END,
reproduces the 2F E0' VALIDATION trade files for EURUSD and XAUUSD
(both harnesses, FL and FR) row for row.
T13: prefix truncation - orders for the VALIDATION window generated on
a ctx ending 2022-06-30 vs one ending VALIDATION_END: every order
before 2022-06-30 is identical.
Swap: hand-computed R_adj on three synthetic trades.
"""
import datetime as dt

import numpy as np
import pandas as pd
import pytest

from src import data as dm
from src import e0
from src import runner
from src import sim as sm
from src import swap_adj
from src.variants.registry import CONFIGS

CFG = [c for c in CONFIGS if c["id"] == "F2_NH_b"][0]
SYMS = ["EURUSD", "XAUUSD"]


def _e(y, m, d, hh=0, mm=0, ss=0):
    return int(dt.datetime(y, m, d, hh, mm, ss,
                           tzinfo=dt.timezone.utc).timestamp())


@pytest.fixture(scope="module", autouse=True)
def _unlock():
    dm.open_holdout(SYMS)
    yield
    dm.open_holdout(set())


def test_t11_guard_whitelist():
    for s in ("GBPUSD", "AUDJPY"):
        with pytest.raises(PermissionError):
            dm.load_m1(s, dm.HOLDOUT_START + 60, dm.COMMON_END,
                       allow_holdout=True)
    with pytest.raises(PermissionError):
        dm.load_m1("EURUSD", dm.HOLDOUT_START + 60, dm.COMMON_END,
                   allow_holdout=False)
    m1 = dm.load_m1("EURUSD", dm.HOLDOUT_START + 60, dm.COMMON_END,
                    allow_holdout=True)
    assert len(m1["t"]) > 0


def test_t12_dryrun_reproduces_2f(tmp_path):
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                  "runs"))
    import order_cache
    from validation_2f import label_df
    lo, hi = dm.VALIDATION
    for sym in SYMS:
        ctx = runner.get_ctx_upto(sym, dm.VALIDATION_END,
                                  allow_holdout=True)
        cap = None if sym == "EURUSD" else runner.sl_cap(ctx, sym)
        orders = order_cache.load_orders(sym, "F2_NH_b_dstfix", (lo, hi))
        hour, _, _ = dm.london_parts(np.array(
            [int(ctx.tf["t"][o["t"]]) for o in orders]))
        am_orders = [o for o, hh in zip(orders, hour) if 7 <= hh < 12]
        mask = e0.second_stamp(ctx.m1)
        for e1 in (True, False):
            tr = sm.run_trades(ctx.m1, ctx.tf, orders, sym, atr=ctx.atr,
                               skip_suspect=e1, void_extra=mask)
            tr = tr[tr.fill_ctm >= lo]
            tr = label_df(tr); tr["sym"] = sym
            ref = pd.read_csv(
                f"out/trades_2fval_{sym}_X0-HOLD_e0s"
                f"{'_e1' if e1 else ''}.csv")
            pd.testing.assert_frame_equal(
                tr.reset_index(drop=True), ref.reset_index(drop=True),
                check_dtype=False, atol=1e-9, rtol=0)
            fr = sm.run_trades(ctx.m1, ctx.tf, am_orders, sym,
                               atr=ctx.atr, skip_suspect=e1,
                               void_extra=mask)
            fr = fr[fr.fill_ctm >= lo]
            fr = label_df(fr); fr["sym"] = sym
            ref2 = pd.read_csv(
                f"out/trades_2fval_{sym}_AMONLY_e0s"
                f"{'_e1' if e1 else ''}.csv")
            pd.testing.assert_frame_equal(
                fr.reset_index(drop=True), ref2.reset_index(drop=True),
                check_dtype=False, atol=1e-9, rtol=0)


def test_t13_prefix_truncation():
    cut = _e(2022, 6, 30, 23, 59)
    lo, hi = dm.VALIDATION
    for sym in SYMS:
        ctx_s = runner.get_ctx_upto(sym, cut, allow_holdout=True)
        ctx_l = runner.get_ctx_upto(sym, dm.VALIDATION_END,
                                    allow_holdout=True)
        cap = None if sym == "EURUSD" else runner.sl_cap(ctx_s, sym)
        o_s = runner.orders_for(ctx_s, CFG, lo, cut, cap)
        o_l = runner.orders_for(ctx_l, CFG, lo, hi, cap)
        # orders' t = tf index; both ctxs share the same prefix of tf
        sig_s = {o["t"]: o for o in o_s}
        early_l = {o["t"]: o for o in o_l
                   if ctx_l.tf["t"][o["t"]] < cut}
        assert len(sig_s) == len(early_l)
        for k, a in sig_s.items():
            b = early_l[k]
            for f in ("dir", "entry", "sl", "tp", "expiry_ctm"):
                assert a[f] == b[f], (sym, k, f, a[f], b[f])


def test_swap_handcheck():
    # 1) EURUSD long, fills Mon 10:00 exits Wed 18:00 -> crosses Mon
    #    and Tue rolls (Wed roll at 23:xx not crossed) = 2 nights.
    #    swap/night -7e-6, risk_px 0.002 -> R_adj = R - 2*7e-6/0.002
    # 2) XAUUSD short across Wednesday roll = 3 nights.
    # 3) EURUSD short, no roll crossed -> 0.
    rows = pd.DataFrame([
        {"sym": "EURUSD", "dir": 1, "fill_ctm": _e(2023, 3, 6, 10, 0),
         "exit_ctm": _e(2023, 3, 8, 18, 0), "risk_px": 0.002,
         "r_x1": 1.5},
        {"sym": "XAUUSD", "dir": -1, "fill_ctm": _e(2023, 3, 7, 10, 0),
         "exit_ctm": _e(2023, 3, 8, 18, 0), "risk_px": 5.0,
         "r_x1": -0.5},
        {"sym": "EURUSD", "dir": -1, "fill_ctm": _e(2023, 3, 6, 10, 0),
         "exit_ctm": _e(2023, 3, 6, 20, 0), "risk_px": 0.002,
         "r_x1": 0.8},
    ])
    adj = swap_adj.swap_adj_r(rows)
    r0 = sm.ROLL["EURUSD"][0][0]
    # nights crossed: count via the same helper to mirror the test
    n = swap_adj.n_rolls(rows.fill_ctm.to_numpy(),
                         rows.exit_ctm.to_numpy(),
                         rows.sym.to_numpy())
    assert list(n) == [2, 3, 0]
    assert abs(adj[0] - (1.5 - 2 * 0.0000070 / 0.002)) < 1e-12
    assert abs(adj[1] - (-0.5 - 3 * 0.046 / 5.0)) < 1e-12
    assert abs(adj[2] - 0.8) < 1e-12
