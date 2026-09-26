"""classic.py - F0 parity + F1 TAH ladder signal generators.

One generator; cfg selects the elements. Every flag maps to a Phase-B
element id; the census decomposes removals element-by-element.
"""
from __future__ import annotations

import numpy as np

from .. import data as data_mod
from ..components import pva as pva_mod
from ..components import pvsra as pvsra_mod
from ..components import stops_targets as st
from ..components import wave as wave_mod
from ..components import whq as whq_mod
from ..components import zones as zn

STEP_S = 15 * 60


def _week_key(ctm: int) -> int:
    return int(ctm // (7 * 86400))


def _element_flags(ctx, t: int, w: dict, dr: int) -> dict:
    """Round-2B element flags at decision bar t (LEAD_NOTE_4 spec).
    All inputs are bars <= t. leg2 is a confirmed swing by construction
    (the wave parser only uses conf <= t swings)."""
    d = ctx.tf
    origin_px = d["l"][w["leg0"]] if dr == 1 else d["h"][w["leg0"]]
    w2whq = zn.whq_zone(origin_px, ctx.symbol, ctx.atr[t]) is not None
    w2sw = zn.price_in_zone(origin_px, ctx.zones_at(t))
    w2any = w2whq or w2sw
    a20 = np.nan
    if t >= 20:
        a = ctx.atr[t]
        if np.isfinite(a) and a > 0:
            a20 = (ctx.dm[t] - ctx.dm[t - 20]) / (20.0 * a)
    w4c = bool(t >= 20 and dr * (ctx.dm[t] - ctx.dm[t - 20]) > 0)
    cls = ctx.pva_cls
    leg2 = int(w["leg2"])
    lo_j = max(0, leg2 - 1)
    hi_j = min(ctx.n, leg2 + 2)
    pv2a = bool(any(cls[j] in (1, 2) for j in range(lo_j, hi_j)))
    pv2b = bool(cls[t] in (1, 2))
    s = int(w2any) + int(w["thru"]) + int(w4c) + int(pv2a)
    return {"w2any": w2any, "w3": bool(w["thru"]), "w4c": w4c,
            "pv2a": pv2a, "pv2b": pv2b, "a20": float(a20), "S": s}


def gen_classic(ctx, cfg: dict, t0: int, t1: int,
                xau_sl_cap: float | None = None) -> list:
    """Produce pending orders for J / ladder / composite configs.

    cfg keys:
      swing: 'fractal2' | 'zigzag'      session: 'london_j'|'london_ext'
      w2: None|'whq'|'swing'            w3: bool
      w4_atr: 0.0|0.05|0.10             sl: 'leg0'|'bigswing'
      tp: 'j'|'zone'|'whq'              pv: bool
      offset_pips, ttl, weekly_cap, reentry: as spec
    """
    d = ctx.tf
    sw = ctx.frac if cfg["swing"] == "fractal2" else ctx.zig
    sess_mask = {"london_j": ctx.in_london_j,
                 "london_ext": ctx.in_london_ext}[cfg["session"]]
    pip = data_mod.PIP[ctx.symbol]
    off = cfg["offset_pips"] * pip
    cap = 120.0 * pip if ctx.symbol == "EURUSD" else xau_sl_cap
    orders = []
    week = -1
    week_n = 0
    reentry_used = False          # composite+reentry: at most one per wave
    last_wave_key = None
    tracker = wave_mod.WaveTracker(sw)
    for t in range(max(t0, 3), t1):
        if not sess_mask[t]:
            continue
        wk = _week_key(int(d["t"][t]))
        if wk != week:
            week, week_n, reentry_used, last_wave_key = wk, 0, False, None
        # ---- base J conditions ------------------------------------------
        long_ok = ctx.long_side[t] and ctx.dragon_up[t]
        short_ok = ctx.short_side[t] and ctx.dragon_dn[t]
        if not (long_ok or short_ok):
            continue
        w = None
        for dr_try in (1, -1):
            ok_side = long_ok if dr_try == 1 else short_ok
            ok_trig = (d["c"][t] > ctx.dh[t] and d["c"][t] > d["o"][t]) \
                if dr_try == 1 else \
                (d["c"][t] < ctx.dl[t] and d["c"][t] < d["o"][t])
            if not (ok_side and ok_trig):
                continue
            cand = tracker.shape(t, dr_try, ctx.dl, ctx.dh, d["l"],
                                 d["h"], d["c"], cfg.get("lookback", 40))
            if cand and not cand["prior_break"]:
                w = cand
                break
        reentry = False
        if w is None and cfg.get("reentry") and last_wave_key is not None \
                and not reentry_used:
            # Re-entry (atlas S3.2): prior Classic in profit -> re-enter
            # when price clears the recent extreme. Approximation: same
            # wave key, bar closes beyond the outer band again.
            lw = last_wave_key
            if long_ok and d["c"][t] > ctx.dh[t] and d["c"][t] > d["o"][t] \
                    and t - lw["leg2"] <= 20:
                w = lw; reentry = True
            elif short_ok and d["c"][t] < ctx.dl[t] \
                    and d["c"][t] < d["o"][t] and t - lw["leg2"] <= 20:
                w = lw; reentry = True
        if w is None:
            continue
        dr = w["dir"]
        # ---- round-2B element flags (computed when needed) --------------
        need_el = (cfg.get("essence") or cfg.get("score_min", 0) > 0
                   or cfg.get("w4c") or cfg.get("w4d")
                   or cfg.get("pv2a") or cfg.get("pv2b"))
        el = _element_flags(ctx, t, w, dr) if need_el else None
        # ---- ladder gates ------------------------------------------------
        if cfg["w3"] and not w["thru"]:
            continue
        if cfg.get("w4c") and not el["w4c"]:
            continue
        if cfg.get("w4d"):
            q = cfg.get("w4d_q", 0.0)
            if not (np.isfinite(el["a20"]) and dr * el["a20"] >= q):
                continue
        if cfg.get("pv2a") and not el["pv2a"]:
            continue
        if cfg.get("pv2b") and not el["pv2b"]:
            continue
        if cfg.get("score_min", 0) > 0 and el["S"] < cfg["score_min"]:
            continue
        if cfg["w4_atr"] > 0:
            a = ctx.angle5[t]
            if not np.isfinite(a) or (dr == 1 and a < cfg["w4_atr"]) \
                    or (dr == -1 and a > -cfg["w4_atr"]):
                continue
        origin_px = d["l"][w["leg0"]] if dr == 1 else d["h"][w["leg0"]]
        at_sr = False
        if cfg["w2"] == "whq":
            at_sr = zn.whq_zone(origin_px, ctx.symbol, ctx.atr[t]) is not None
            if not at_sr:
                continue
        elif cfg["w2"] == "swing":
            zlist = ctx.zones_at(t)
            at_sr = zn.price_in_zone(origin_px, zlist)
            if not at_sr:
                continue
        # ---- entry / SL / TP ----------------------------------------------
        entry = (d["h"][t] + off) if dr == 1 else (d["l"][t] - off)
        if cfg["sl"] == "leg0":
            sl = st.sl_leg0(w, d, t, ctx.atr)
        else:
            s = st.sl_big_swing(d, t, ctx.atr, ctx.zig, dr, entry)
            if s is None:
                continue
            sl = s
        if cap is not None and abs(entry - sl) > cap:
            continue                       # stop too wide -> no trade
        if abs(entry - sl) <= 0:
            continue
        if cfg["tp"] == "j":
            tp = st.tp_j(entry, sl, dr, ctx.symbol)
        elif cfg["tp"] == "zone":
            tp = st.tp_zone(entry, sl, dr, ctx.zones_at(t))
            if tp is None:
                continue
        else:
            tp = st.tp_whq(entry, sl, dr, ctx.symbol)
            if tp is None:
                continue
        # ---- PVSRA agreement ---------------------------------------------
        pv_bias = pv_mode = 0
        if cfg["pv"]:
            pv_bias, pv_mode = pvsra_mod.pvsra_label(
                t, ctx.pva_cls, d["c"], d["tv"], ctx.dm, ctx.zones_at)
            if not pvsra_mod.pv_agrees(pv_bias, pv_mode, dr):
                continue
        # ---- weekly cap ----------------------------------------------------
        if cfg["weekly_cap"] and week_n >= cfg["weekly_cap"]:
            continue
        week_n += 1
        if reentry:
            reentry_used = True
        else:
            last_wave_key = w
        meta = {"session": cfg["session"], "cfg": cfg["id"],
                "leg0": int(w["leg0"]), "at_sr": int(at_sr),
                "thru": int(w["thru"]),
                "pva": int(ctx.pva_cls[t]),
                "pv_bias": pv_bias, "pv_mode": pv_mode}
        if el is not None:
            meta.update({"S": int(el["S"]), "w2any": int(el["w2any"]),
                         "w3": int(el["w3"]), "w4c": int(el["w4c"]),
                         "pv2a": int(el["pv2a"]), "pv2b": int(el["pv2b"]),
                         "a20": float(el["a20"])})
        orders.append({
            "t": t, "dir": dr, "entry": float(entry), "sl": float(sl),
            "tp": float(tp),
            "expiry_ctm": int(d["t"][t]) + cfg["ttl"] * STEP_S,
            "meta": meta,
        })
    return orders
