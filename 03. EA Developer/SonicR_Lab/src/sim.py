"""sim.py - causal execution simulator (E1/E1b/E2/E3 harness).

Model (Phase A5 spec + Lead errata 19:02Z):
  signal on a CLOSED tf bar t -> pending STOP order active from the first
  M1 bar with ctm >= tf.t[t] + step, valid until expiry (ttl tf bars).
  fills: first CLEAN M1 where bid extreme crosses the stop price;
         fill price = max(stop, open) long / min(stop, open) short.
  SL/TP resolved on CLEAN M1 bars from the fill bar onward; if both SL
  and TP are inside one M1 bar -> SL first (conservative).
  Friday flatten: forced exit at the OPEN of the first CLEAN M1 bar
  at/after Friday 20:00 London. Optional daily flat at 23:50 server
  (secondary column mode, daily_flat_mod=1430).
  One pending + one position at a time per (symbol, config).

E1 - fabricated bars cannot trigger or price anything:
  bars with suspect=True are skipped for pending fills and SL/TP hits.
  At the first clean bar after a suspect run: SL beyond its open ->
  exit at that open (worse than SL); TP beyond its open -> exit at the
  TP price (no gap bonus). MFE/MAE measured over clean bars only.

E1b - rollover spread stress (Lead assumptions, round-3 to measure):
  transaction price worsens by S_roll when the resolving bar is inside
  the roll window: EURUSD 23:55-00:15 server -> 2.0 pips;
  XAUUSD 00:55-01:20 server -> 20 pips ($2.00). Applied to the ask side
  of every fill/exit (buy +S_roll, sell -S_roll).

E2 - executability floor at order admission:
  (entry - sl)*dir < max(3 * round_trip_cost, 0.15 * ATR14[signal t])
  -> order skipped, counted in df.attrs["rejected"].

E3 - report R: rows carry r_x1/r_x15/r_x2 = (dir*(exit-entry) - m*cost)/risk.
  pending_px = the stop-order price; entry = the actual fill.

Costs: cost_x1 = spread + slip_entry + slip_exit + commission per DATA.md;
x1.5/x2 scale the whole. Reported entry/exit are raw fill levels.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data as data_mod
from .components import sessions as sess_mod

STOP_LONG = 1
STOP_SHORT = -1

# E1b roll-spread windows (server minute-of-day) and stress in price.
# ctm is server-naive epoch -> ctm % 86400 / 60 IS the server minute.
ROLL = {"EURUSD": ((1435, 15), 2.0 * 1e-4),     # 23:55-00:15 srv, 2 pips
        "XAUUSD": ((55, 80), 20.0 * 0.1)}       # 00:55-01:20 srv, $2.00
# Round-2C basket: windows discovered outcome-blind from suspect-flag
# clustering (runs/basket_check.py, out/basket_checks.csv); stress
# +2.0 pips ask side, GBPJPY +3.0 pips (Lead assumption).
ROLL.update({
    "GBPUSD": ((1439, 28), 2.0e-4), "USDJPY": ((1439, 30), 2.0 * 0.01),
    "AUDUSD": ((1439, 29), 2.0e-4), "NZDUSD": ((1439, 30), 2.0e-4),
    "USDCAD": ((1439, 29), 2.0e-4), "USDCHF": ((1439, 27), 2.0e-4),
    "EURJPY": ((1439, 33), 2.0 * 0.01), "GBPJPY": ((0, 16), 3.0 * 0.01),
    "EURGBP": ((1439, 26), 2.0e-4), "AUDJPY": ((0, 17), 2.0 * 0.01)})


def _in_roll(symbol: str, ctm: int) -> bool:
    (a, b), _s = ROLL[symbol]
    mod = (ctm % 86400) // 60
    return mod >= a or mod < b if a > b else a <= mod < b


def _roll_px(symbol: str) -> float:
    return ROLL[symbol][1]


def round_trip_cost(symbol: str) -> float:
    c = data_mod.COST[symbol]
    return c["spread"] + c["slip_side"] * 2 + c["comm"]


def e2_rejects(orders: list, atr: np.ndarray, symbol: str) -> int:
    """Count orders that E2 removes: |pending_px - SL| below
    max(3 x round-trip cost, 0.15 x ATR14 at the signal bar)."""
    floor_cost = 3.0 * round_trip_cost(symbol)
    n = 0
    for o in orders:
        floor = max(floor_cost, 0.15 * atr[o["t"]])
        if (o["entry"] - o["sl"]) * o["dir"] < floor:
            n += 1                        # matches run_trades admission
    return n


def run_trades(m1: dict, tf: dict, orders: list, symbol: str,
               atr: np.ndarray | None = None,
               daily_flat_mod: int | None = None,
               skip_suspect: bool = False,
               exit_rule: str | None = None,
               tfx: dict | None = None,
               pessimistic: bool = False,
               void_extra: np.ndarray | None = None) -> pd.DataFrame:
    """orders: dicts {t, dir, entry(stop px), sl, tp, expiry_ctm, meta}.
    atr: ATR14 array on tf bars (E2 floor); None -> floor = 3*cost only.
    daily_flat_mod: server minute-of-day for an extra daily flat
    (secondary-column mode). df.attrs["rejected"] = E2 skips.
    skip_suspect: E1 gate - the Lead's diagnostic rule (DATA.md roll
    window table) measured ratio < 2 -> E1 SKIPPED this round, so the
    default keeps suspect bars tradable; the machinery stays for audit.
    void_extra (A3F/E0): bars voided in EVERY harness (impossible
    prints); skipped exactly like E1 suspect skips - no fill, no SL/TP,
    no flatten, excluded from MFE/MAE, and they arm the post-suspect
    no-gap-bonus rule for the next clean bar."""
    mt = m1["t"]; mo = m1["o"]; mh = m1["h"]; ml = m1["l"]
    msus = m1.get("suspect", np.zeros(len(mt), bool))
    eff_void = (msus if skip_suspect else np.zeros(len(mt), bool))
    if void_extra is not None:
        eff_void = eff_void | void_extra
    step = tf["minutes"] * 60
    cost = data_mod.COST[symbol]
    cost_x1 = (cost["spread"] + cost["slip_side"] * 2 + cost["comm"])
    floor_cost = 3.0 * cost_x1                      # E2 leg A
    roll = _roll_px(symbol)
    mod_arr = (mt % 86400) // 60
    rows = []
    n_rejected = 0
    busy_until_m1 = -1
    for od in orders:
        t = od["t"]
        risk_dir = (od["entry"] - od["sl"]) * od["dir"]
        floor_atr = (0.15 * atr[t]
                     if atr is not None and np.isfinite(atr[t]) else 0.0)
        if risk_dir < max(floor_cost, floor_atr):
            n_rejected += 1     # E2 floor / wrong-side stop
            continue
        sig_close = tf["t"][t] + step
        start = int(np.searchsorted(mt, sig_close))
        if start <= busy_until_m1:
            continue            # a pending/position still occupies the book
        expiry = od["expiry_ctm"]
        end_idx = int(np.searchsorted(mt, expiry))
        if end_idx <= start:
            continue
        # --- pending fill (clean bars only; E1) ------------------------
        stop = od["entry"]; dr = od["dir"]
        fill_i = -1
        for i in range(start, end_idx):
            if eff_void[i]:
                continue
            if (dr == 1 and mh[i] >= stop) or (dr == -1 and ml[i] <= stop):
                fill_i = i
                break
        if fill_i < 0:
            busy_until_m1 = end_idx - 1
            continue
        roll_in = _in_roll(symbol, int(mt[fill_i]))
        fill = (max(stop, mo[fill_i]) if dr == 1
                else min(stop, mo[fill_i]))
        fill += dr * roll if roll_in else 0.0       # E1b: buy +S / sell -S
        sl = od["sl"]; tp = od["tp"]
        # --- exit resolution --------------------------------------------
        flat_ctm = sess_mod.friday_flatten_ctm(
            np.asarray([mt[fill_i]]))[0]
        dflat = None
        if daily_flat_mod is not None:
            day0 = mt[fill_i] - mod_arr[fill_i] * 60
            dflat = day0 + daily_flat_mod * 60
            if mt[fill_i] >= dflat:
                dflat += 86400
            flat_ctm = min(flat_ctm, dflat)
        if exit_rule is not None:
            from . import exits as _ex
            res = _ex.resolve_exit(
                m1, tfx, symbol, dr, fill_i, fill, sl, tp,
                flat_ctm, exit_rule, skip_suspect=skip_suspect,
                daily_flat_ctm=dflat, pessimistic=pessimistic)
            exit_i = res["exit_i"]; exit_px = res["exit_px"]
            reason = res["reason"]; seg = res["seg"]
            part_i = res["part_i"]; part_px = res["part_px"]
        else:
            part_i = -1; part_px = np.nan
            last_i = int(np.searchsorted(mt, flat_ctm))
            if last_i <= fill_i:
                last_i = fill_i + 1 if fill_i + 1 < len(mt) else fill_i
            scan_end = min(last_i, len(mt))
            exit_i = -1; exit_px = np.nan; reason = ""
            prev_suspect = False
            for i in range(fill_i, scan_end):
                if eff_void[i]:
                    prev_suspect = True
                    continue                # E1/E0: voided bars skipped
                roll_i = _in_roll(symbol, int(mt[i]))
                sgn = roll if roll_i else 0.0
                if dr == 1:
                    sl_hit = ml[i] <= sl
                    tp_hit = mh[i] >= tp
                    if sl_hit:
                        exit_i = i
                        exit_px = min(sl, mo[i]) if mo[i] < sl else sl
                        exit_px -= sgn       # exit sell: -S_roll
                        reason = "sl" if i != fill_i or not tp_hit \
                            else "sl_same"
                        break
                    if tp_hit:
                        exit_i = i
                        if prev_suspect and mo[i] >= tp:
                            exit_px = tp     # E1: no gap bonus post-suspect
                        else:
                            exit_px = max(tp, mo[i]) if mo[i] > tp else tp
                        exit_px -= sgn
                        reason = "tp"
                        break
                else:
                    sl_hit = mh[i] >= sl
                    tp_hit = ml[i] <= tp
                    if sl_hit:
                        exit_i = i
                        exit_px = max(sl, mo[i]) if mo[i] > sl else sl
                        exit_px += sgn       # exit buy: +S_roll
                        reason = "sl" if i != fill_i or not tp_hit \
                            else "sl_same"
                        break
                    if tp_hit:
                        exit_i = i
                        if prev_suspect and mo[i] <= tp:
                            exit_px = tp
                        else:
                            exit_px = min(tp, mo[i]) if mo[i] < tp else tp
                        exit_px += sgn
                        reason = "tp"
                        break
                prev_suspect = False
            if exit_i < 0:                    # friday/daily flatten
                i = min(last_i, len(mt) - 1)
                while (i < len(mt) - 1 and eff_void[i]):
                    i += 1                    # first clean bar open
                exit_i = i; exit_px = mo[i]
                reason = "flat" if last_i < len(mt) else "window_end"
            seg = np.arange(fill_i, exit_i + 1)
            seg = seg[~eff_void[seg]]
            if len(seg) == 0:
                seg = np.array([fill_i])
        # --- MFE / MAE over clean bars in [fill_i, exit_i] (E1) ----------
        if dr == 1:
            mfe_p = float(mh[seg].max() - fill)
            mae_p = float(ml[seg].min() - fill)
        else:
            mfe_p = float(fill - ml[seg].min())
            mae_p = float(fill - mh[seg].max())
        risk = abs(fill - sl)
        gross = dr * (exit_px - fill)
        if part_i >= 0:                      # X2: two half-legs
            gross = 0.5 * dr * (part_px - fill) + \
                0.5 * dr * (exit_px - fill)
        rows.append({
            "sym": symbol, "dir": dr,
            "sig_ctm": int(tf["t"][t]),
            "fill_ctm": int(mt[fill_i]), "exit_ctm": int(mt[exit_i]),
            "pending_px": float(stop),
            "entry": float(fill), "sl": float(sl), "tp": float(tp),
            "exit": float(exit_px), "reason": reason,
            "part_ctm": int(mt[part_i]) if part_i >= 0 else 0,
            "part_px": float(part_px) if part_i >= 0 else np.nan,
            "risk_px": float(risk),
            "r_gross": gross / risk if risk > 0 else np.nan,
            "cost_x1_px": float(cost_x1),
            "pnl_px_x1": gross - cost_x1,
            "pnl_px_x15": gross - 1.5 * cost_x1,
            "pnl_px_x2": gross - 2.0 * cost_x1,
            "r_x1": (gross - cost_x1) / risk if risk > 0 else np.nan,
            "r_x15": (gross - 1.5 * cost_x1) / risk
            if risk > 0 else np.nan,
            "r_x2": (gross - 2.0 * cost_x1) / risk
            if risk > 0 else np.nan,
            "mfe_r": mfe_p / risk if risk > 0 else np.nan,
            "mae_r": mae_p / risk if risk > 0 else np.nan,
            "suspect_fill": bool(msus[fill_i]),
            "suspect_exit": bool(msus[exit_i]),
            "session": od["meta"].get("session", ""),
            "cfg": od["meta"].get("cfg", ""),
            "leg0": od["meta"].get("leg0", -1),
            "at_sr": od["meta"].get("at_sr", -1),
            "thru": od["meta"].get("thru", -1),
            "pva": od["meta"].get("pva", -1),
            "pv_bias": od["meta"].get("pv_bias", 0),
            "pv_mode": od["meta"].get("pv_mode", 0),
        })
        busy_until_m1 = exit_i
    df = pd.DataFrame(rows)
    df.attrs["rejected"] = n_rejected
    return df
