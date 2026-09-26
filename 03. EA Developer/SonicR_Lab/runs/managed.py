"""managed.py - ROUND 2D fixed-list re-simulation helpers.

light_ctx: minimal per-symbol context for the exit layer (m1, M15
resample, EMA34 High/Low, server-minute array) - the heavy signal
context (zones/waves) is not needed to re-simulate exits.

resim_orders: take X0's filled trades AS IN THE TRADE FILES (same fill
bar, fill price, SL, TP) and re-run only the exit under a variant rule.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src import data as dm
from src import exits as ex
from src import sim as sim_mod
from src.components import indicators as ind
from src.components import sessions as sess_mod

_LCTX: dict = {}


def light_ctx(symbol: str, lo=None, hi=None) -> dict:
    key = (symbol, lo, hi)
    if key not in _LCTX:
        lo = dm.COMMON_START if lo is None else lo
        hi = dm.VALIDATION_END if hi is None else hi
        m1 = dm.load_m1(symbol, lo, hi)
        tf = dm.resample(m1, 15)
        e34h, _e34c, e34l = ind.dragon(tf)
        _LCTX[key] = {"m1": m1, "tf": tf, "e34h": e34h, "e34l": e34l,
                      "tfx": {"t": tf["t"], "c": tf["c"], "e34h": e34h,
                              "e34l": e34l, "m1_hi": tf["m1_hi"]}}
    return _LCTX[key]


def daily_flat_ctm(fill_ctm: int, flat_mod: int = 1430) -> int:
    day0 = fill_ctm - ((fill_ctm % 86400) // 60) * 60
    d = day0 + flat_mod * 60
    return d + 86400 if fill_ctm >= d else d


def resim_row(row, lc, sym, rule, skip_suspect, daily_flat=False,
              pessimistic=False):
    """Re-run ONE trade's exit. row = the X0 CSV row (its own fill)."""
    m1 = lc["m1"]; mt = m1["t"]
    dr = int(row["dir"]); fill = float(row["entry"])
    sl = float(row["sl"]); tp = float(row["tp"])
    fill_i = int(np.searchsorted(mt, int(row["fill_ctm"])))
    flat = sess_mod.friday_flatten_ctm(np.asarray([mt[fill_i]]))[0]
    dflat = daily_flat_ctm(int(mt[fill_i])) if daily_flat else None
    res = ex.resolve_exit(m1, lc["tfx"], sym, dr, fill_i, fill, sl, tp,
                          flat, rule, skip_suspect=skip_suspect,
                          daily_flat_ctm=dflat, pessimistic=pessimistic)
    risk = abs(fill - sl)
    gross = dr * (res["exit_px"] - fill)
    if res["part_i"] >= 0:
        gross = 0.5 * dr * (res["part_px"] - fill) + \
            0.5 * dr * (res["exit_px"] - fill)
    cost = sim_mod.round_trip_cost(sym)
    mh, ml = m1["h"], m1["l"]
    seg = res["seg"]
    mfe = (mh[seg].max() - fill) if dr == 1 else (fill - ml[seg].min())
    mae = (ml[seg].min() - fill) if dr == 1 else (fill - mh[seg].max())
    return {"exit_i": res["exit_i"], "exit_ctm": int(mt[res["exit_i"]]),
            "exit": res["exit_px"], "reason": res["reason"],
            "part_ctm": int(mt[res["part_i"]]) if res["part_i"] >= 0 else 0,
            "part_px": res["part_px"], "r_gross": gross / risk,
            "pnl_x1": gross - cost, "r_x1": (gross - cost) / risk,
            "r_x15": (gross - 1.5 * cost) / risk,
            "r_x2": (gross - 2.0 * cost) / risk,
            "mfe_r": mfe / risk, "mae_r": mae / risk}


def resim_trades(tr, lc, sym, rule, skip_suspect, daily_flat=False,
                 pessimistic=False):
    """Fixed-list re-sim of a whole trade CSV -> DataFrame."""
    rows = [resim_row(r, lc, sym, rule, skip_suspect, daily_flat,
                      pessimistic) for _, r in tr.iterrows()]
    out = tr[["sym", "dir", "sig_ctm", "fill_ctm", "entry", "sl", "tp",
              "risk_px"]].copy().reset_index(drop=True)
    for k in ("exit_ctm", "exit", "reason", "part_ctm", "part_px",
              "r_gross", "pnl_x1", "r_x1", "r_x15", "r_x2",
              "mfe_r", "mae_r"):
        out[k] = [r[k] for r in rows]
    return out


def load_x0(sym, e1):
    """X0 F2_NH_b trade file for a symbol on the given harness."""
    tag = "_e1" if e1 else ""
    for pat in (f"out/trades_2c_{sym}_F2_NH_b{tag}.csv",
                f"out/trades_{sym}_F2_NH_b{tag}.csv"):
        if os.path.exists(pat):
            return pd.read_csv(pat)
    raise FileNotFoundError(sym + tag)
