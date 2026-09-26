"""other.py - F2 Nhat Hoai, F3 Lucy, F4 Bai 14 signal generators."""
from __future__ import annotations

import numpy as np

from .. import data as data_mod
from ..components import stops_targets as st
from ..components import zones as zn

STEP_S = 15 * 60


def gen_nhat_hoai(ctx, cfg: dict, t0: int, t1: int,
                  xau_sl_cap: float | None = None) -> list:
    """F2 (atlas S6 family 2): first pullback into the Dragon after the
    Dragon side changes; entry when a bar closes back OUTSIDE the band.
    SL (a) beyond pullback extreme / (b) beyond the large swing;
    TP = nearest opposing swing zone >=1R. M15, London-ext."""
    d = ctx.tf
    pip = data_mod.PIP[ctx.symbol]
    off = cfg["offset_pips"] * pip
    cap = 120.0 * pip if ctx.symbol == "EURUSD" else xau_sl_cap
    orders = []
    # track "side" of close vs dragon mid; on flip, arm pullback-waiting
    side_prev = np.sign(d["c"] - ctx.dm)
    armed_dir = 0      # direction we wait to trade (after side flip)
    arm_t = -1
    pull_i = -1        # bar index of the deepest pullback inside the band
    pull_px = 0.0
    used_flip = -1
    for t in range(max(t0, 3), t1):
        side = side_prev[t]
        if not np.isfinite(side):
            continue
        if side != side_prev[t - 1] and side != 0:
            armed_dir = int(side)
            arm_t = t
            pull_i, pull_px = -1, 0.0
            used_flip = -1
        if not ctx.in_london_ext[t] or armed_dir == 0 or used_flip == arm_t:
            continue
        in_band = ctx.dl[t] <= d["c"][t] <= ctx.dh[t]
        if in_band:
            if armed_dir == 1 and (pull_i < 0 or d["l"][t] < pull_px):
                pull_i, pull_px = t, d["l"][t]
            elif armed_dir == -1 and (pull_i < 0 or d["h"][t] > pull_px):
                pull_i, pull_px = t, d["h"][t]
            continue
        if pull_i < 0 or t - pull_i > 16:        # stale pullback
            continue
        # trigger: close back outside the band on the armed side
        if armed_dir == 1 and not (d["c"][t] > ctx.dh[t]):
            continue
        if armed_dir == -1 and not (d["c"][t] < ctx.dl[t]):
            continue
        dr = armed_dir
        entry = (d["h"][t] + off) if dr == 1 else (d["l"][t] - off)
        if cfg["sl"] == "pullback":
            sl = pull_px - 0.1 * ctx.atr[t] if dr == 1 else \
                pull_px + 0.1 * ctx.atr[t]
        else:
            s = st.sl_big_swing(d, t, ctx.atr, ctx.zig, dr, entry)
            if s is None:
                continue
            sl = s
        if abs(entry - sl) <= 0 or (cap is not None and
                                    abs(entry - sl) > cap):
            continue
        tp = st.tp_zone(entry, sl, dr, ctx.zones_at(t))
        if tp is None:
            continue
        used_flip = arm_t
        orders.append({
            "t": t, "dir": dr, "entry": float(entry), "sl": float(sl),
            "tp": float(tp),
            "expiry_ctm": int(d["t"][t]) + cfg["ttl"] * STEP_S,
            "meta": {"session": "london_ext", "cfg": cfg["id"],
                     "leg0": pull_i, "at_sr": -1, "thru": -1,
                     "pva": int(ctx.pva_cls[t]), "pv_bias": 0,
                     "pv_mode": 0},
        })
    return orders


def gen_lucy(ctx, cfg: dict, t0: int, t1: int, ctx_h1,
             xau_sl_cap: float | None = None) -> list:
    """F3 Lucy: H1 trend -> M5 rejection candle touching M5 Dragon/EMA89.
    Runs on the M5 ctx; ctx_h1 supplies H1 bars (same M1 source).
    H1 trend at decision bar t: use the last CLOSED H1 (h1.t < m5.t).
    Entry: market-style pending = stop beyond the rejection candle.
    SL beyond the wick + 0.1*ATR(m5); TP (a) 1.5R / (b) nearest zone.
    Session: NY overlap only."""
    d = ctx.tf
    h1 = ctx_h1.tf
    pip = data_mod.PIP[ctx.symbol]
    cap = 120.0 * pip if ctx.symbol == "EURUSD" else xau_sl_cap
    orders = []
    # map each m5 bar -> last closed h1 index (h1 open + 3600 <= m5 open)
    h1_close = h1["t"] + 3600
    h1_idx = np.searchsorted(h1_close, d["t"], side="right") - 1
    for t in range(max(t0, 3), t1):
        j = h1_idx[t]
        if j < 1:
            continue
        # H1 trend: close vs EMA89 AND vs dragon mid
        h1_long = h1["c"][j] > ctx_h1.ema89[j] and \
            h1["c"][j] > ctx_h1.dm[j]
        h1_short = h1["c"][j] < ctx_h1.ema89[j] and \
            h1["c"][j] < ctx_h1.dm[j]
        if not (h1_long or h1_short):
            continue
        dr = 1 if h1_long else -1
        if not ctx.in_ny_overlap[t]:
            continue
        # rejection candle on M5 touching dragon band or ema89
        rng = d["h"][t] - d["l"][t]
        body = abs(d["c"][t] - d["o"][t])
        if rng <= 0:
            continue
        up_wick = d["h"][t] - max(d["c"][t], d["o"][t])
        dn_wick = min(d["c"][t], d["o"][t]) - d["l"][t]
        pin = False
        if dr == 1 and dn_wick >= 2 * body and dn_wick >= 0.6 * rng:
            pin = True
        if dr == -1 and up_wick >= 2 * body and up_wick >= 0.6 * rng:
            pin = True
        eng = False
        if t >= 1:
            if dr == 1 and d["c"][t] > d["o"][t] and \
                    d["c"][t - 1] < d["o"][t - 1] and \
                    d["c"][t] >= d["o"][t - 1] and \
                    d["o"][t] <= d["c"][t - 1]:
                eng = True
            if dr == -1 and d["c"][t] < d["o"][t] and \
                    d["c"][t - 1] > d["o"][t - 1] and \
                    d["c"][t] <= d["o"][t - 1] and \
                    d["o"][t] >= d["c"][t - 1]:
                eng = True
        if not (pin or eng):
            continue
        touch = d["l"][t] <= ctx.dh[t] if dr == 1 else d["h"][t] >= ctx.dl[t]
        touch = touch or (d["l"][t] <= ctx.ema89[t] if dr == 1
                          else d["h"][t] >= ctx.ema89[t])
        if not touch:
            continue
        entry = d["h"][t] + 2 * pip if dr == 1 else d["l"][t] - 2 * pip
        sl = (d["l"][t] - 0.1 * ctx.atr[t]) if dr == 1 else \
            (d["h"][t] + 0.1 * ctx.atr[t])
        if abs(entry - sl) <= 0 or (cap is not None and
                                    abs(entry - sl) > cap):
            continue
        if cfg["tp"] == "r15":
            tp = entry + dr * 1.5 * abs(entry - sl)
        else:
            tp = st.tp_zone(entry, sl, dr, ctx.zones_at(t))
            if tp is None:
                continue
        orders.append({
            "t": t, "dir": dr, "entry": float(entry), "sl": float(sl),
            "tp": float(tp),
            "expiry_ctm": int(d["t"][t]) + cfg["ttl"] * 5 * 60,
            "meta": {"session": "ny_overlap", "cfg": cfg["id"],
                     "leg0": t, "at_sr": -1, "thru": -1,
                     "pva": int(ctx.pva_cls[t]), "pv_bias": 0,
                     "pv_mode": 0},
        })
    return orders


def gen_bai14(ctx, cfg: dict, t0: int, t1: int,
              xau_sl_cap: float | None = None) -> list:
    """F4 Bai 14 (atlas family 4): EMA34-band bounce in direction of
    EMA200 vs EMA610 (computed once in ctx extras). Entry = close back
    outside EMA34 band after a touch, in the slow-trend direction.
    SL across the band (far side - 0.1*ATR); TP = 2R. London-ext."""
    d = ctx.tf
    pip = data_mod.PIP[ctx.symbol]
    cap = 120.0 * pip if ctx.symbol == "EURUSD" else xau_sl_cap
    e200 = getattr(ctx, "ema200", None)
    e610 = getattr(ctx, "ema610", None)
    if e200 is None or e610 is None:
        raise RuntimeError("ctx lacks ema200/ema610")
    orders = []
    touched_long = False
    touched_short = False
    for t in range(max(t0, 3), t1):
        if not np.isfinite(e200[t]) or not np.isfinite(e610[t]):
            continue
        tr_long = e200[t] > e610[t]
        tr_short = e200[t] < e610[t]
        if not ctx.in_london_ext[t]:
            continue
        if d["l"][t] <= ctx.dh[t]:
            touched_long = True
        if d["h"][t] >= ctx.dl[t]:
            touched_short = True
        if d["c"][t] < ctx.dl[t]:
            touched_long = False          # broke through -> invalidate
        if d["c"][t] > ctx.dh[t]:
            touched_short = False
        dr = 0
        if tr_long and touched_long and d["c"][t] > ctx.dh[t] \
                and d["c"][t] > d["o"][t]:
            dr = 1
        elif tr_short and touched_short and d["c"][t] < ctx.dl[t] \
                and d["c"][t] < d["o"][t]:
            dr = -1
        if dr == 0:
            continue
        touched_long = touched_short = False
        entry = d["h"][t] + 2 * pip if dr == 1 else d["l"][t] - 2 * pip
        sl = (ctx.dl[t] - 0.1 * ctx.atr[t]) if dr == 1 else \
            (ctx.dh[t] + 0.1 * ctx.atr[t])
        if abs(entry - sl) <= 0 or (cap is not None and
                                    abs(entry - sl) > cap):
            continue
        tp = entry + dr * 2.0 * abs(entry - sl)
        orders.append({
            "t": t, "dir": dr, "entry": float(entry), "sl": float(sl),
            "tp": float(tp),
            "expiry_ctm": int(d["t"][t]) + cfg["ttl"] * STEP_S,
            "meta": {"session": "london_ext", "cfg": cfg["id"],
                     "leg0": t, "at_sr": -1, "thru": -1,
                     "pva": int(ctx.pva_cls[t]), "pv_bias": 0,
                     "pv_mode": 0},
        })
    return orders
