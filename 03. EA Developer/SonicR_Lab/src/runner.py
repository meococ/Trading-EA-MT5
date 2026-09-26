"""runner.py - build ctx once per symbol, run every config through sim.

Usage:
    from src import runner
    res = runner.run_symbol("EURUSD", data_mod.DESIGN)
    res[cfg_id] -> dict(orders=..., trades=DataFrame)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import context as context_mod
from . import data as data_mod
from . import sim
from .components import indicators as ind
from .components import stops_targets as st
from .variants import classic as v_classic
from .variants import other as v_other
from .variants.registry import CONFIGS

_CTXS: dict = {}
_CAPS: dict = {}


def get_ctx(symbol: str, minutes: int = 15,
            pre2010: bool = False) -> context_mod.Ctx:
    key = (symbol, minutes, pre2010)
    if key not in _CTXS:
        lo = data_mod.J_PARITY[0] if pre2010 else data_mod.COMMON_START
        ctx = context_mod.build(symbol, lo, data_mod.VALIDATION_END,
                                minutes=minutes, pre2010=pre2010)
        if minutes == 15:
            ctx.ema200 = ind.ema(ctx.tf["c"], 200)
            ctx.ema610 = ind.ema(ctx.tf["c"], 610)
        _CTXS[key] = ctx
    return _CTXS[key]


def get_ctx_upto(symbol: str, end_ctm: int, minutes: int = 15,
                 pre2010: bool = False,
                 allow_holdout: bool = False) -> context_mod.Ctx:
    """Ctx built to an arbitrary end (2G: COMMON_END with the whitelist
    unlock). Separate cache key so it can never alias the sealed ctx."""
    key = (symbol, minutes, pre2010, int(end_ctm))
    if key not in _CTXS:
        lo = data_mod.J_PARITY[0] if pre2010 else data_mod.COMMON_START
        ctx = context_mod.build(symbol, lo, int(end_ctm),
                                minutes=minutes, pre2010=pre2010,
                                allow_holdout=allow_holdout)
        if minutes == 15:
            ctx.ema200 = ind.ema(ctx.tf["c"], 200)
            ctx.ema610 = ind.ema(ctx.tf["c"], 610)
        _CTXS[key] = ctx
    return _CTXS[key]


def sl_cap(ctx15, symbol: str) -> float:
    """SL cap (price) = EUR's 120 pips expressed as the same multiple of
    median daily range, computed per symbol on DESIGN only (round-2C:
    same formula for every non-EUR symbol, XAUUSD unchanged)."""
    if symbol not in _CAPS:
        eur = get_ctx("EURUSD")
        mdr_eur = st.median_daily_range_pips(
            eur.tf, data_mod.DESIGN[0], data_mod.DESIGN[1], "EURUSD")
        mdr = st.median_daily_range_pips(
            ctx15.tf, data_mod.DESIGN[0], data_mod.DESIGN[1], symbol)
        _CAPS[symbol] = (120.0 / mdr_eur) * mdr * data_mod.PIP[symbol]
    return _CAPS[symbol]


def xau_sl_cap(ctx15) -> float:
    """XAU cap = EUR 120-pip multiple of median daily range, DESIGN only."""
    return sl_cap(ctx15, "XAUUSD")


def orders_for(ctx, cfg: dict, lo_ctm: int, hi_ctm: int,
               xau_cap: float | None = None) -> list:
    # A2F fix: SwingZones is incremental - a previous orders_for on this
    # cached ctx advanced _ptr past t, and zones_at(t) filters only on
    # t - i <= max_age (not conf <= t), so future swings leak in. Reset
    # the engine at every generation call site (run_symbol already did
    # this by hand; now it is enforced here).
    ctx.reset_zones()
    d = ctx.tf
    t0 = int(np.searchsorted(d["t"], lo_ctm))
    t1 = int(np.searchsorted(d["t"], hi_ctm))
    fam = cfg["family"]
    if fam in ("F0", "F1", "F1B", "F5"):
        return v_classic.gen_classic(ctx, cfg, t0, t1, xau_cap)
    if fam == "F2":
        return v_other.gen_nhat_hoai(ctx, cfg, t0, t1, xau_cap)
    if fam == "F3":
        ctx_h1 = get_ctx(ctx.symbol, 60)
        return v_other.gen_lucy(ctx, cfg, t0, t1, ctx_h1, xau_cap)
    if fam == "F4":
        return v_other.gen_bai14(ctx, cfg, t0, t1, xau_cap)
    raise ValueError(fam)


def run_symbol(symbol: str, window: tuple, pre2010: bool = False) -> dict:
    """Run every config on `window`; returns {cfg_id: {orders, trades}}."""
    ctx15 = get_ctx(symbol, 15, pre2010)
    ctx5 = get_ctx(symbol, 5, pre2010)
    cap = sl_cap(ctx15, symbol) if symbol != "EURUSD" else None
    out = {}
    for cfg in CONFIGS:
        ctx = ctx5 if cfg["family"] == "F3" else ctx15
        ctx.reset_zones()
        orders = orders_for(ctx, cfg, window[0], window[1], cap)
        trades = sim.run_trades(ctx.m1, ctx.tf, orders, symbol)
        out[cfg["id"]] = {"orders": orders, "trades": trades,
                          "cfg": cfg}
    return out
