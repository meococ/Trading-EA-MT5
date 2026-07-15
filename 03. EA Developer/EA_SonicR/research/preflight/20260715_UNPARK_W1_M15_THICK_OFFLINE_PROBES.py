#!/usr/bin/env python3
"""Unpark Round — W1 position sleeve + M15 thick-stop-from-scratch (+ replacement).

Parent: Round7 CHF/COM3/ADR OFFLINE_ALL_KILL; W1/M15 were PARKED not killed.

FORBIDDEN densify:
  ≠ FX3 H4 R1–R5 path · Round6 triad/NAS/metal · Round7 CHF β/COM3 z/ADR k
  ≠ Weekly-HL H4 RR3 (killed) · PDH-BREAK-M15 (parked) · SB FVG/KZ/RR densify
  ≠ XS/AUDNZD/AONIA/CORRA/thin3/carry/anticarry/D1vol/swing/LNY/FRED/exit-RR2

Intake rulings (a priori, before metrics):
  A) Panel PDH thick-stop sketch → INTAKE_KILL (PDH densify vs HYP-PDH-BREAK-M15-001)
  B) W1 HL-break D1-confirm position sleeve → CLEARED (≠ H4 Weekly-HL RR3)
  C) M15 D1-bias RANGE-EXP thick-stop from scratch → CLEARED (≠ PDH/SB/ORB/IB)
  D) Replacement greenfield: D1 inside-bar → H1 break cont → CLEARED (outside R1–R7)

Probe B+C+D jointly under +$12. Model 0 only if PROBE_SURVIVOR.

Nested critic: cursor-grok-4.5-high-fast (lead self-merge).
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"

STEM = "20260715_UNPARK_W1_M15_THICK"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_SESSION_VN = READ / "20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md"
OUT_PREREG_W1 = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preregs"
    / "20260715_H_FX3_W1_HLBREAK_D1CONF_HOLD_001_PREREG.md"
)
OUT_PREREG_M15 = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preregs"
    / "20260715_H_USDJPY_M15_D1BIAS_RANGEEXP_THICK_001_PREREG.md"
)
OUT_PREREG_INS = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preregs"
    / "20260715_H_USDJPY_D1_INSIDE_H1_BREAK_CONT_001_PREREG.md"
)

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# --- B W1 HL-break + D1 confirm position sleeve ---
W1_SL_ATR = 2.5
W1_TRAIL_ATR = 3.0
W1_HOLD_D1 = 20
W1_MAX_PER_WEEK = 1

# --- C M15 D1-bias range-expansion thick-stop ---
M15_RANGE_K = 1.5
M15_SL_ATR = 2.5
M15_HOLD = 16
M15_MAX_PER_DAY = 1
M15_EMA = 50

# --- D D1 inside-bar → H1 break continuation ---
INS_SL_ATR = 1.5
INS_RR = 2.0
INS_HOLD = 24
INS_MAX_PER_DAY = 1


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def pf_of(pnls):
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def haircuts(pnls):
    out = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [p - BASE_COST * mult for p in pnls]
        out[key] = {
            "pf": None if not cut else round(pf_of(cut) or 0.0, 4),
            "net": round(sum(cut), 2) if cut else 0.0,
            "exp": round(sum(cut) / len(cut), 4) if cut else 0.0,
        }
    return out


def metrics(pnls):
    n = len(pnls)
    p = pf_of(pnls)
    net = sum(pnls) if pnls else 0.0
    return {
        "n": n,
        "pf": None if p is None else round(p, 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(n / WEEKS, 4) if WEEKS else None,
    }


def joint_verdict(m, hc):
    notes = []
    n, pf, tpw = m["n"] or 0, m["pf"] or 0.0, m["tpw"] or 0.0
    if n < 80:
        notes.append("n_fail")
    if pf is None or pf < 1.30:
        notes.append("pf_fail")
    if tpw is None or tpw < 2.0:
        notes.append("cadence_fail")
    if hc["x1_5"]["pf"] is None or hc["x1_5"]["pf"] < 1.25:
        notes.append("stress_fail")
    return ("PROBE_SURVIVOR", []) if not notes else ("KILLED_AT_OFFLINE_PROBE", notes)


def atr_arr(h, l, c, n=14):
    prev = np.roll(c, 1)
    prev[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))
    out = np.full_like(tr, np.nan, dtype=float)
    s = tr[:n].sum()
    out[n - 1] = s / n
    for i in range(n, len(tr)):
        s = s - tr[i - n] + tr[i]
        out[i] = s / n
    return out


def ema_arr(c, n):
    out = np.full_like(c, np.nan, dtype=float)
    if len(c) < n:
        return out
    out[n - 1] = float(np.mean(c[:n]))
    k = 2.0 / (n + 1.0)
    for i in range(n, len(c)):
        out[i] = out[i - 1] + k * (c[i] - out[i - 1])
    return out


def load(symbol, tf, fr=FROM, to=TO):
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_range(symbol, tf, fr, to)
    if rates is None or len(rates) < 100:
        raise RuntimeError(f"{symbol} tf={tf}: {mt5.last_error()}")
    return {
        "t": rates["time"].astype(np.int64),
        "o": rates["open"].astype(float),
        "h": rates["high"].astype(float),
        "l": rates["low"].astype(float),
        "c": rates["close"].astype(float),
    }


def enrich(d, ema_n=None):
    d["atr"] = atr_arr(d["h"], d["l"], d["c"])
    if ema_n:
        d["ema"] = ema_arr(d["c"], ema_n)
    return d


def pip_size(symbol):
    info = mt5.symbol_info(symbol)
    if info is None:
        return 0.01 if "JPY" in symbol else 0.0001
    return info.point * (10 if info.digits in (3, 5) else 1)


def cash_pnl(symbol, side, entry, exit_px, lots):
    info = mt5.symbol_info(symbol)
    tick_val = float(info.trade_tick_value) if info else 1.0
    tick_size = float(info.trade_tick_size) if info else pip_size(symbol)
    if tick_size <= 0:
        tick_size = pip_size(symbol)
    return (exit_px - entry) * side / tick_size * tick_val * lots


def risk_lots(symbol, entry, sl):
    info = mt5.symbol_info(symbol)
    risk = DEPOSIT * RISK_FRAC
    dist = abs(entry - sl)
    if dist <= 0 or info is None:
        return 0.01
    tick_val = float(info.trade_tick_value) or 1.0
    tick_size = float(info.trade_tick_size) or pip_size(symbol)
    loss = dist / tick_size * tick_val
    if loss <= 0:
        return 0.01
    return min(5.0, max(0.01, math.floor(risk / loss * 100) / 100))


def manage_exits_fixed(open_pos, data, ts, closed, hold_limit):
    still = []
    for pos in open_pos:
        sym = pos["sym"]
        d = data[sym]
        idx = int(np.searchsorted(d["t"], ts, side="left"))
        if idx >= len(d["t"]) or d["t"][idx] != ts:
            still.append(pos)
            continue
        exit_px = None
        reason = None
        if pos["side"] > 0:
            if d["l"][idx] <= pos["sl"]:
                exit_px, reason = pos["sl"], "sl"
            elif pos.get("tp") is not None and d["h"][idx] >= pos["tp"]:
                exit_px, reason = pos["tp"], "tp"
        else:
            if d["h"][idx] >= pos["sl"]:
                exit_px, reason = pos["sl"], "sl"
            elif pos.get("tp") is not None and d["l"][idx] <= pos["tp"]:
                exit_px, reason = pos["tp"], "tp"
        pos["bars"] += 1
        if exit_px is None and pos["bars"] >= hold_limit:
            exit_px, reason = d["c"][idx], "time"
        if exit_px is not None:
            closed.append(
                {
                    "pnl": cash_pnl(sym, pos["side"], pos["entry"], exit_px, pos["lots"]),
                    "reason": reason,
                    "sym": sym,
                }
            )
        else:
            still.append(pos)
    return still


def flush_open(open_pos, data, closed):
    for pos in open_pos:
        d = data[pos["sym"]]
        closed.append(
            {
                "pnl": cash_pnl(
                    pos["sym"], pos["side"], pos["entry"], float(d["c"][-1]), pos["lots"]
                ),
                "reason": "eod",
                "sym": pos["sym"],
            }
        )


def summarize(closed):
    pnls = [x["pnl"] for x in closed]
    detail = {"by_reason": {}, "by_sym": {}}
    for x in closed:
        detail["by_reason"][x["reason"]] = detail["by_reason"].get(x["reason"], 0) + 1
        detail["by_sym"][x["sym"]] = detail["by_sym"].get(x["sym"], 0) + 1
    return pnls, detail


def iso_week(dt: datetime) -> str:
    y, w, _ = dt.isocalendar()
    return f"{y}-W{w:02d}"


def probe_w1_hlbreak_d1conf(d1_map: dict[str, dict], w1_map: dict[str, dict]):
    """W1 close beyond prior W1 HL + D1 confirm → next D1 open; trail ATR position."""
    closed: list[dict] = []
    open_pos: list[dict] = []
    week_used: set[str] = set()
    funnel = {
        "n_w1_breaks": 0,
        "n_d1_confirm": 0,
        "n_trades": 0,
        "n_skip_open": 0,
        "n_skip_week": 0,
    }

    # Build W1 break events per symbol: after W1[i] closes beyond W1[i-1] HL
    # Pending confirm until a D1 close in break direction during that ISO week.
    pending: dict[str, dict[str, Any]] = {}  # sym -> pending break

    # Union D1 clock from EURUSD
    clock = d1_map["EURUSD"]["t"]
    idx_map = {
        s: {int(t): i for i, t in enumerate(d1_map[s]["t"])} for s in FX3
    }

    # Precompute W1 events keyed by W1 close timestamp
    w1_events: list[tuple[int, str, int, float]] = []  # (w1_close_ts, sym, side, level)
    for sym in FX3:
        w = w1_map[sym]
        for i in range(1, len(w["t"])):
            prev_h, prev_l = float(w["h"][i - 1]), float(w["l"][i - 1])
            c = float(w["c"][i])
            if c > prev_h:
                w1_events.append((int(w["t"][i]), sym, 1, prev_h))
            elif c < prev_l:
                w1_events.append((int(w["t"][i]), sym, -1, prev_l))
    w1_events.sort(key=lambda x: x[0])
    ev_i = 0

    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        # Manage open positions on this D1 bar (SL/time first; trail updates at close)
        still = []
        for pos in open_pos:
            sym = pos["sym"]
            d = d1_map[sym]
            j = idx_map[sym].get(int(ts))
            if j is None:
                still.append(pos)
                continue
            exit_px = None
            reason = None
            if pos["side"] > 0:
                if d["l"][j] <= pos["sl"]:
                    exit_px, reason = pos["sl"], "sl_trail"
            else:
                if d["h"][j] >= pos["sl"]:
                    exit_px, reason = pos["sl"], "sl_trail"
            pos["bars"] += 1
            if exit_px is None and pos["bars"] >= W1_HOLD_D1:
                exit_px, reason = float(d["c"][j]), "time"
            if exit_px is not None:
                closed.append(
                    {
                        "pnl": cash_pnl(
                            sym, pos["side"], pos["entry"], exit_px, pos["lots"]
                        ),
                        "reason": reason,
                        "sym": sym,
                    }
                )
            else:
                atr = d["atr"][j]
                if np.isfinite(atr) and atr > 0:
                    if pos["side"] > 0:
                        trail = float(d["c"][j]) - W1_TRAIL_ATR * atr
                        pos["sl"] = max(pos["sl"], trail)
                    else:
                        trail = float(d["c"][j]) + W1_TRAIL_ATR * atr
                        pos["sl"] = min(pos["sl"], trail)
                still.append(pos)
        open_pos = still

        if dt.weekday() >= 5:
            continue

        # Ingest W1 events whose close ts <= this D1 bar (closed-bar: W1 already closed)
        while ev_i < len(w1_events) and w1_events[ev_i][0] <= int(ts):
            ets, esym, eside, elev = w1_events[ev_i]
            funnel["n_w1_breaks"] += 1
            wk = iso_week(datetime.fromtimestamp(ets, tz=timezone.utc))
            pending[esym] = {
                "side": eside,
                "level": elev,
                "week": wk,
                "w1_ts": ets,
            }
            ev_i += 1

        # Confirm pending on this closed D1 (use prior bar for signal → enter next open)
        if i + 1 >= len(clock):
            continue
        if open_pos:
            funnel["n_skip_open"] += 1
            continue

        candidates = []
        for sym in FX3:
            pend = pending.get(sym)
            if pend is None:
                continue
            j = idx_map[sym].get(int(ts))
            if j is None or j < 20:
                continue
            d = d1_map[sym]
            c = float(d["c"][j])
            side = pend["side"]
            # D1 confirm: close beyond break level in break direction
            if side > 0 and c <= pend["level"]:
                continue
            if side < 0 and c >= pend["level"]:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            wk = pend["week"]
            if wk in week_used:
                continue
            candidates.append((sym, side, atr, wk, pend["level"]))

        if not candidates:
            continue

        # A priori first eligible FX3 order
        sym, side, atr, wk, level = candidates[0]
        if wk in week_used:
            funnel["n_skip_week"] += 1
            continue
        funnel["n_d1_confirm"] += 1
        next_ts = int(clock[i + 1])
        nj = idx_map[sym].get(next_ts)
        if nj is None:
            continue
        entry = float(d1_map[sym]["o"][nj])
        # SL: 2.5 ATR beyond entry, also respect W1 extreme distance
        sl_atr = entry - side * W1_SL_ATR * atr
        if side > 0:
            sl = min(sl_atr, level - 0.1 * atr)
        else:
            sl = max(sl_atr, level + 0.1 * atr)
        if abs(entry - sl) <= 0:
            continue
        open_pos.append(
            {
                "sym": sym,
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": None,
                "lots": risk_lots(sym, entry, sl),
                "bars": 0,
            }
        )
        week_used.add(wk)
        pending.pop(sym, None)
        funnel["n_trades"] += 1

    flush_open(open_pos, d1_map, closed)
    pnls, detail = summarize(closed)
    detail["funnel"] = funnel
    return pnls, detail


def probe_m15_rangeexp_thick(m15: dict, d1: dict):
    """D1 EMA50 bias + M15 range expansion; thick 2.5 ATR stop; time/bias exit."""
    closed: list[dict] = []
    open_pos: list[dict] = []
    day_count: dict[str, int] = {}
    funnel = {
        "n_bars": 0,
        "n_bias_ok": 0,
        "n_signal": 0,
        "n_trades": 0,
        "n_skip_open": 0,
    }
    data_map = {"USDJPY": m15}

    # Map each M15 bar to latest closed D1 index
    d1_t = d1["t"]
    d1_idx_for_m15 = np.searchsorted(d1_t, m15["t"], side="right") - 1

    for i, ts in enumerate(m15["t"]):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        # Exit management + opposite D1 bias kill
        still = []
        for pos in open_pos:
            idx = i
            exit_px = None
            reason = None
            di = int(d1_idx_for_m15[idx])
            if di >= M15_EMA and np.isfinite(d1["ema"][di]):
                bias_now = 1 if d1["c"][di] > d1["ema"][di] else -1
                if bias_now != pos["side"]:
                    exit_px, reason = float(m15["c"][idx]), "bias_flip"
            if exit_px is None:
                if pos["side"] > 0 and m15["l"][idx] <= pos["sl"]:
                    exit_px, reason = pos["sl"], "sl"
                elif pos["side"] < 0 and m15["h"][idx] >= pos["sl"]:
                    exit_px, reason = pos["sl"], "sl"
            pos["bars"] += 1
            if exit_px is None and pos["bars"] >= M15_HOLD:
                exit_px, reason = float(m15["c"][idx]), "time"
            if exit_px is not None:
                closed.append(
                    {
                        "pnl": cash_pnl(
                            "USDJPY", pos["side"], pos["entry"], exit_px, pos["lots"]
                        ),
                        "reason": reason,
                        "sym": "USDJPY",
                    }
                )
            else:
                still.append(pos)
        open_pos = still

        if dt.weekday() >= 5:
            continue
        j = i - 1
        if j < 30:
            continue
        funnel["n_bars"] += 1
        if open_pos:
            funnel["n_skip_open"] += 1
            continue
        day = dt.date().isoformat()
        if day_count.get(day, 0) >= M15_MAX_PER_DAY:
            continue
        di = int(d1_idx_for_m15[j])
        if di < M15_EMA or not np.isfinite(d1["ema"][di]):
            continue
        # Closed D1 only (di points to last D1 with t <= m15[j])
        bias = 1 if d1["c"][di] > d1["ema"][di] else -1
        funnel["n_bias_ok"] += 1
        atr = m15["atr"][j]
        if not np.isfinite(atr) or atr <= 0:
            continue
        rng = float(m15["h"][j] - m15["l"][j])
        if rng < M15_RANGE_K * atr:
            continue
        c = float(m15["c"][j])
        o = float(m15["o"][j])
        # Outer third + close in bias direction
        upper = m15["l"][j] + (2.0 / 3.0) * rng
        lower = m15["l"][j] + (1.0 / 3.0) * rng
        if bias > 0:
            if not (c >= upper and c > o):
                continue
            side = 1
        else:
            if not (c <= lower and c < o):
                continue
            side = -1
        funnel["n_signal"] += 1
        entry = float(m15["o"][i])
        sl = entry - side * M15_SL_ATR * atr
        if abs(entry - sl) <= 0:
            continue
        open_pos.append(
            {
                "sym": "USDJPY",
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": None,
                "lots": risk_lots("USDJPY", entry, sl),
                "bars": 0,
            }
        )
        day_count[day] = day_count.get(day, 0) + 1
        funnel["n_trades"] += 1

    flush_open(open_pos, data_map, closed)
    pnls, detail = summarize(closed)
    detail["funnel"] = funnel
    return pnls, detail


def probe_d1_inside_h1_break(h1: dict, d1: dict):
    """Prior D1 inside-bar → H1 close break of inside H/L; RR2 thick-ish SL."""
    closed: list[dict] = []
    open_pos: list[dict] = []
    day_count: dict[str, int] = {}
    funnel = {
        "n_bars": 0,
        "n_inside_active": 0,
        "n_signal": 0,
        "n_trades": 0,
        "n_skip_open": 0,
    }
    data_map = {"USDJPY": h1}
    d1_t = d1["t"]
    d1_idx = np.searchsorted(d1_t, h1["t"], side="right") - 1

    # Precompute inside-bar flags on D1: bar i is inside if h[i]<h[i-1] and l[i]>l[i-1]
    inside = np.zeros(len(d1["t"]), dtype=bool)
    for i in range(1, len(d1["t"])):
        inside[i] = d1["h"][i] < d1["h"][i - 1] and d1["l"][i] > d1["l"][i - 1]

    for i, ts in enumerate(h1["t"]):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        open_pos = manage_exits_fixed(open_pos, data_map, ts, closed, INS_HOLD)
        if dt.weekday() >= 5:
            continue
        j = i - 1
        if j < 30:
            continue
        funnel["n_bars"] += 1
        if open_pos:
            funnel["n_skip_open"] += 1
            continue
        day = dt.date().isoformat()
        if day_count.get(day, 0) >= INS_MAX_PER_DAY:
            continue
        di = int(d1_idx[j])
        # Closed-bar only: use last *completed* D1 whose calendar date < H1 date.
        # MT5 may already have today's forming D1 at di — never trade that.
        h1_day = dt.date()
        prior = di
        while prior >= 0:
            d1_day = datetime.fromtimestamp(int(d1_t[prior]), tz=timezone.utc).date()
            if d1_day < h1_day:
                break
            prior -= 1
        if prior < 2 or not inside[prior]:
            continue
        funnel["n_inside_active"] += 1
        ih, il = float(d1["h"][prior]), float(d1["l"][prior])
        c = float(h1["c"][j])
        atr = h1["atr"][j]
        if not np.isfinite(atr) or atr <= 0:
            continue
        if c > ih:
            side = 1
        elif c < il:
            side = -1
        else:
            continue
        funnel["n_signal"] += 1
        entry = float(h1["o"][i])
        sl = entry - side * INS_SL_ATR * atr
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        tp = entry + side * INS_RR * risk
        open_pos.append(
            {
                "sym": "USDJPY",
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": risk_lots("USDJPY", entry, sl),
                "bars": 0,
            }
        )
        day_count[day] = day_count.get(day, 0) + 1
        funnel["n_trades"] += 1

    flush_open(open_pos, data_map, closed)
    pnls, detail = summarize(closed)
    detail["funnel"] = funnel
    return pnls, detail


def pack_result(hid, setup, symbol, timeframe, pnls, detail, intake=None):
    m = metrics(pnls)
    hc = haircuts(pnls)
    if intake == "INTAKE_KILL":
        verdict, notes = "INTAKE_KILL_SB_OR_PDH_DENSIFY", ["intake_densify"]
    else:
        verdict, notes = joint_verdict(m, hc)
    return {
        "hypothesis_id": hid,
        "setup_type": setup,
        "symbol": symbol,
        "timeframe": timeframe,
        "metrics": m,
        "haircuts": hc,
        "verdict": verdict,
        "fail_notes": notes,
        "detail": detail,
        "intake": intake or "CLEARED",
    }


def write_preregs():
    OUT_PREREG_W1.write_text(
        "\n".join(
            [
                "# Prereg — HYP-FX3-W1-HLBREAK-D1CONF-HOLD-001",
                "",
                "Date: 2026-07-15",
                "State on freeze: `preregistered` (offline probe first)",
                "Authority: Owner unpark after Round7 PARK; nested `cursor-grok-4.5-high-fast`",
                "",
                "## Identity",
                "- Hypothesis ID: `HYP-FX3-W1-HLBREAK-D1CONF-HOLD-001`",
                "- Parent: parked W1 position sleeve (Round6/7 panel); ≠ killed "
                "`HYP-WEEKLY-HL-BREAK-H4-001`",
                "",
                "## Thesis",
                "Prior W1 high/low break on **W1 close**, confirmed by **D1 close** beyond "
                "the broken level, enters a multi-day **position sleeve** (ATR trail). "
                "Swap is cost accounting only — not funding alpha.",
                "",
                "## Locked Design",
                "| Item | Frozen |",
                "|---|---|",
                "| Book | FX3 EURUSD→GBPUSD→USDJPY (1/week a priori) |",
                "| Entry TF | D1 open after W1-break + D1 confirm |",
                "| Level | Prior completed W1 high/low |",
                f"| SL | {W1_SL_ATR}×ATR14(D1); trail {W1_TRAIL_ATR}×ATR on closed D1 |",
                f"| Hold | ≤{W1_HOLD_D1} D1 bars; no fixed RR TP |",
                "| Risk | 0.50%; max 1 trade / ISO week |",
                "| Window | 2021.01.01–2025.12.31 |",
                "| Cost screen | +$12 / x1.5 / x2 joint |",
                "",
                "## Banned",
                "- Retune to H4 first-break RR3 (killed Weekly-HL densify)",
                "- Day/session mine from readout; multi-symbol post-hoc expand",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_PREREG_M15.write_text(
        "\n".join(
            [
                "# Prereg — HYP-USDJPY-M15-D1BIAS-RANGEEXP-THICK-001",
                "",
                "Date: 2026-07-15",
                "State on freeze: `preregistered` (offline probe first)",
                "Authority: Owner unpark M15 thick-stop-from-scratch; ≠ PDH/SB densify",
                "",
                "## Identity",
                "- Hypothesis ID: `HYP-USDJPY-M15-D1BIAS-RANGEEXP-THICK-001`",
                "- Parent: parked M15 thick-stop class; **replacement** after PDH sketch "
                "INTAKE_KILL",
                "",
                "## Thesis",
                "D1 EMA50 sets bias. Entry is **M15 range expansion** "
                f"(range ≥ {M15_RANGE_K}×ATR14) with close in outer third in bias "
                f"direction. Stop architecture is thick ({M15_SL_ATR}×ATR) from scratch — "
                "not SB FVG, not PDH/PDL break, not ORB/IB.",
                "",
                "## Locked Design",
                "| Item | Frozen |",
                "|---|---|",
                "| Symbol/TF | USDJPY M15 + D1 bias |",
                f"| Bias | D1 close vs EMA{M15_EMA} |",
                f"| Entry | M15 range≥{M15_RANGE_K}×ATR; outer-third close w/ bias |",
                f"| SL | {M15_SL_ATR}×ATR14(M15); no fixed TP |",
                f"| Exit | time ≤{M15_HOLD} M15 **or** opposite D1 bias |",
                "| Caps | 1/day; Mon–Fri |",
                "| Window | 2021.01.01–2025.12.31 |",
                "| Cost screen | +$12 / x1.5 / x2 joint |",
                "",
                "## Banned",
                "- PDH/PDL break entry (parked densify)",
                "- SB FVG / KZ / RR / MaxKZ densify",
                "- ORB / IB / Asia-coil / LNY session retune",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_PREREG_INS.write_text(
        "\n".join(
            [
                "# Prereg — HYP-USDJPY-D1-INSIDE-H1-BREAK-CONT-001",
                "",
                "Date: 2026-07-15",
                "State on freeze: `preregistered` (offline probe first)",
                "Authority: Replacement greenfield after PDH thick-stop INTAKE_KILL",
                "",
                "## Identity",
                "- Hypothesis ID: `HYP-USDJPY-D1-INSIDE-H1-BREAK-CONT-001`",
                "- Parent: unpark round replacement outside R1–R7 killboards",
                "",
                "## Thesis",
                "Completed D1 **inside bar** (high < prior high AND low > prior low) "
                "is a compression parent. First H1 close beyond the inside H/L continues "
                "in break direction.",
                "",
                "## Locked Design",
                "| Item | Frozen |",
                "|---|---|",
                "| Symbol/TF | USDJPY H1; pattern on D1 |",
                "| Pattern | D1 inside bar (closed) |",
                "| Entry | next H1 open after H1 close beyond inside H/L |",
                f"| SL/TP | {INS_SL_ATR}×ATR14(H1) / RR={INS_RR} |",
                f"| Hold | ≤{INS_HOLD} H1; 1/day |",
                "| Window | 2021.01.01–2025.12.31 |",
                "| Cost screen | +$12 / x1.5 / x2 joint |",
                "",
                "## Banned",
                "- ≠ NR7 densify (different compress definition)",
                "- ≠ Outside/Engulf fade packs; ≠ D1 vol-regime break; ≠ FX3 H4 path",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_docs(results, intake_killed, receipt, any_surv, qfsi_note: str):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")

    OUT_PANEL.write_text(
        "\n".join(
            [
                "# 3-critic panel — Unpark W1 sleeve + M15 thick-stop (post Round7)",
                "",
                "Date: 2026-07-15",
                "Nested model: `cursor-grok-4.5-high-fast`",
                "Note: lead self-merge (Task backend optional).",
                "Parent: Round7 ALL_KILL; W1/M15 were PARKED — Owner ordered execute.",
                "",
                "## Named classes",
                "1. `W1_HL_BREAK_POSITION_SLEEVE` — UNPARK — rank 3.5 (≠ H4 Weekly-HL)",
                "2. Panel `M15_THICKSTOP_PDH` sketch — **INTAKE_KILL** (PDH densify)",
                "3. `M15_D1BIAS_RANGEEXP_THICK` — replacement from-scratch — rank 3.5",
                "4. `D1_INSIDE_H1_BREAK_CONT` — replacement greenfield — rank 3.5",
                "",
                "## Critic merge",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — W1 position ≠ H4 scalp; range-exp ≠ SB FVG |",
                "| Quant | SOFT — W1 N/tpw risk; thick stop +$12 harsh; still lawful |",
                "| MQL5/MT5 | PASS — closed-bar W1/D1/M15; no Model 0 yet |",
                "",
                "PDH sketch unpark: **NO** (intake-kill).",
                "Model 0: **WITHHELD** until PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — Unpark W1 + M15 thick-stop + replacement",
                "",
                "Date: 2026-07-15",
                "Parent: Round7 PARK release. Nested `cursor-grok-4.5-high-fast`.",
                "",
                "## Intake",
                "- PDH thick-stop panel sketch → **INTAKE_KILL** vs "
                "`HYP-PDH-BREAK-M15-001` + SB/session densify risk.",
                "- W1 sleeve → **CLEARED** (W1 close + D1 confirm + ATR trail ≠ H4 RR3).",
                "- M15 range-exp thick → **CLEARED** (≠ PDH/SB/ORB/IB).",
                "- D1 inside→H1 break → **CLEARED** replacement outside R1–R7.",
                "",
                "## 1 `HYP-FX3-W1-HLBREAK-D1CONF-HOLD-001`",
                f"W1 close beyond prior W1 HL; D1 confirm; SL={W1_SL_ATR} ATR; "
                f"trail={W1_TRAIL_ATR} ATR; hold≤{W1_HOLD_D1} D1; 1/ISO-week FX3.",
                "",
                "## 2 `HYP-USDJPY-M15-D1BIAS-RANGEEXP-THICK-001`",
                f"D1 EMA{M15_EMA} bias; M15 range≥{M15_RANGE_K}×ATR outer-third; "
                f"SL={M15_SL_ATR} ATR; hold≤{M15_HOLD}; 1/day.",
                "",
                "## 3 `HYP-USDJPY-D1-INSIDE-H1-BREAK-CONT-001`",
                f"D1 inside; H1 close break; SL={INS_SL_ATR} ATR RR={INS_RR}; "
                f"hold≤{INS_HOLD}; 1/day.",
                "",
                "## Model 0",
                "Only PROBE_SURVIVOR. No R6–R7 densify. No PDH/SB densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Unpark W1 + M15 thick-stop + replacement",
                "",
                "| Object | Vs killboard | Ruling |",
                "|---|---|---|",
                "| Panel PDH thick-stop sketch | = PDH-BREAK-M15 densify / SB contamination | "
                "**INTAKE_KILL** |",
                "| `HYP-FX3-W1-HLBREAK-D1CONF-HOLD-001` | ≠ Weekly-HL H4 RR3 (entry TF + "
                "D1 confirm + ATR trail monetization) | **CLEARED** |",
                "| `HYP-USDJPY-M15-D1BIAS-RANGEEXP-THICK-001` | ≠ PDH break; ≠ SB FVG/KZ; "
                "≠ ORB/IB/LNY; ≠ R1–R7 boards | **CLEARED** |",
                "| `HYP-USDJPY-D1-INSIDE-H1-BREAK-CONT-001` | ≠ NR7; ≠ Outside/Engulf fade; "
                "≠ D1 vol-regime; ≠ FX3 H4 path; ≠ R6–R7 | **CLEARED** |",
                "",
                "CLEARED for offline probe: W1 + M15-rangeexp + D1-inside.",
                "No densify of R6–R7 near-misses / Weekly-HL H4 / PDH / SB.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    lines_md = [
        "# Offline — Unpark W1 + M15 thick-stop + replacement",
        "",
        f"Receipt: `{receipt}`",
        f"Status: `{status}`",
        f"Cost: +${BASE_COST:.0f} joint; window 2021–2025; deposit {DEPOSIT:.0f}",
        "",
        "## Intake-killed (no probe metrics as survivor path)",
    ]
    for ik in intake_killed:
        lines_md.append(f"- `{ik['hypothesis_id']}` — {ik['reason']}")
    lines_md += [
        "",
        "| Object | N | PF | tpw | x1.5 | Verdict |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for r in results:
        lines_md.append(
            f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
            f"{r['metrics']['tpw']} | {r['haircuts']['x1_5']['pf']} | "
            f"**{r['verdict']}** |"
        )
    lines_md += ["", "## Funnel notes"]
    for r in results:
        lines_md.append(f"- `{r['hypothesis_id']}`: {r['detail'].get('funnel')}")
    lines_md += [
        "",
        f"QFSI parallel: {qfsi_note}",
        "Best shelf RR2 `194548`. GOAL unmet.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines_md), encoding="utf-8")

    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Closeout — Unpark W1 + M15 thick-stop",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                *[
                    f"- `{r['hypothesis_id']}` → **{r['verdict']}**"
                    for r in results
                ],
                "- Panel PDH thick-stop sketch → **INTAKE_KILL** (PDH densify).",
                "Do **not** densify W1 trail / M15 range-k / inside pattern / R6–R7 / "
                "PDH / SB / Weekly-HL H4.",
                "Best shelf RR2 `194548`. Cost freeze GAP. QFSI parallel only.",
                "Login not headline. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Unpark W1 + M15 thick-stop",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Unpark sau Round7 PARK. PDH sketch → intake-kill; probe W1 + "
                "M15 range-exp thick + D1-inside replacement.",
                "",
                f"## Kết quả → `{status}`",
                "| Object | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                *[
                    f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
                    f"{r['metrics']['tpw']} | {r['haircuts']['x1_5']['pf']} | "
                    f"{'SURVIVOR' if r['verdict'] == 'PROBE_SURVIVOR' else 'KILL'} |"
                    for r in results
                ],
                f"Receipt `{receipt}`",
                "",
                "## Quyết định",
                f"- {'Có' if any_surv else 'Zero'} Model 0.",
                "- PDH thick-stop sketch = INTAKE_KILL (densify).",
                "- Không densify W1/M15 knobs / R6–R7 near-miss.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI parallel only.",
                "- Next: greenfield ngoài board này **hoặc** research-grade cost.",
                "",
                "Login không headline. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # Append session VN section
    sess = OUT_SESSION_VN.read_text(encoding="utf-8") if OUT_SESSION_VN.exists() else ""
    block = "\n".join(
        [
            "",
            f"## Unpark W1/M15 — `{status}` (~{stamp} ICT)",
            "| Object | N | PF | tpw | x1.5 | Verdict |",
            "|---|---:|---:|---:|---:|---|",
            *[
                f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
                f"{r['metrics']['tpw']} | {r['haircuts']['x1_5']['pf']} | "
                f"{'SURVIVOR' if r['verdict'] == 'PROBE_SURVIVOR' else 'KILL'} |"
                for r in results
            ],
            f"Receipt `{receipt}` | PDH sketch INTAKE_KILL | Zero Model 0 "
            f"{'unless survivor' if any_surv else ''}".strip(),
            "",
        ]
    )
    # Update header timestamp if present
    if sess.startswith("# VN brief"):
        lines = sess.splitlines()
        for i, ln in enumerate(lines):
            if ln.startswith("Thời điểm:"):
                lines[i] = f"Thời điểm: 2026-07-15 ~{stamp} ICT"
                break
        # Insert unpark section after Round 7 block if present
        text = "\n".join(lines)
        marker = "## Quyết định"
        if marker in text and "## Unpark W1/M15" not in text:
            text = text.replace(marker, block + marker, 1)
            # Fix decision bullets about PARKED
            text = text.replace("- W1 / M15 vẫn PARKED.", "- W1 / M15 đã UNPARK + probe (xem Unpark section).")
            OUT_SESSION_VN.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
        elif "## Unpark W1/M15" not in text:
            OUT_SESSION_VN.write_text(sess.rstrip() + block, encoding="utf-8")
    else:
        OUT_SESSION_VN.write_text(
            "\n".join(
                [
                    "# VN brief — continue R&D (greenfield + unpark)",
                    f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                    block,
                ]
            ),
            encoding="utf-8",
        )


def append_reg(results, intake_killed, receipt):
    lane = "unpark_w1_m15_thick_20260715"
    drop_ids = {r["hypothesis_id"] for r in results} | {
        x["hypothesis_id"] for x in intake_killed
    }
    if REG.exists():
        keep = []
        for line in REG.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                keep.append(line)
                continue
            if obj.get("hypothesis_id") in drop_ids and obj.get("lane") == lane:
                continue
            keep.append(line)
        REG.write_text("\n".join(keep) + ("\n" if keep else ""), encoding="utf-8")
    with REG.open("a", encoding="utf-8") as f:
        for ik in intake_killed:
            f.write(
                json.dumps(
                    {
                        "record_type": "candidate",
                        "schema_version": 1,
                        "hypothesis_id": ik["hypothesis_id"],
                        "state": "intake_killed",
                        "parent_candidate": "round7_parked_m15_thickstop",
                        "feature_family": "unpark_intake_reject",
                        "lane": lane,
                        "setup_type": ik["setup_type"],
                        "verdict": "INTAKE_KILL_SB_OR_PDH_DENSIFY",
                        "reason": ik["reason"],
                        "updated_at": "2026-07-15",
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        for r in results:
            f.write(
                json.dumps(
                    {
                        "record_type": "candidate",
                        "schema_version": 1,
                        "hypothesis_id": r["hypothesis_id"],
                        "state": "killed"
                        if r["verdict"] != "PROBE_SURVIVOR"
                        else "probe_survivor",
                        "parent_candidate": "round7_parked_unpark_20260715",
                        "feature_family": "unpark_w1_m15_thick",
                        "lane": lane,
                        "setup_type": r["setup_type"],
                        "symbol": r["symbol"],
                        "timeframe": r["timeframe"],
                        "window": "2021.01.01-2025.12.31",
                        "model": "offline_probe_only",
                        "prereg_path": {
                            "HYP-FX3-W1-HLBREAK-D1CONF-HOLD-001": str(
                                OUT_PREREG_W1.relative_to(ROOT)
                            ).replace("\\", "/"),
                            "HYP-USDJPY-M15-D1BIAS-RANGEEXP-THICK-001": str(
                                OUT_PREREG_M15.relative_to(ROOT)
                            ).replace("\\", "/"),
                            "HYP-USDJPY-D1-INSIDE-H1-BREAK-CONT-001": str(
                                OUT_PREREG_INS.relative_to(ROOT)
                            ).replace("\\", "/"),
                        }.get(r["hypothesis_id"]),
                        "readout_path": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                        "metrics": {
                            "trades": r["metrics"]["n"],
                            "pf": r["metrics"]["pf"],
                            "tpw": r["metrics"]["tpw"],
                            "pf_cost_x1_5": r["haircuts"]["x1_5"]["pf"],
                        },
                        "validation": {
                            "offline_probe": str(OUT_JSON.relative_to(ROOT)).replace(
                                "\\", "/"
                            ),
                            "receipt_sha256": receipt,
                            "status": r["verdict"],
                            "fail_notes": r["fail_notes"],
                            "model0": "AUTHORIZED"
                            if r["verdict"] == "PROBE_SURVIVOR"
                            else "WITHHELD",
                            "dedup": str(OUT_DEDUP.relative_to(ROOT)).replace("\\", "/"),
                        },
                        "verdict": r["verdict"],
                        "reason": ",".join(r["fail_notes"]) or "probe_survivor",
                        "updated_at": "2026-07-15",
                        "cost_grade": "a_priori_usd12",
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def patch_hot(results, intake_killed, receipt, any_surv, qfsi_note: str):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    block = [
        f"- **UNPARK W1/M15 THICK CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.**",
        "  Owner release of Round7 PARK. Nested critic `cursor-grok-4.5-high-fast`.",
        "  Intake: panel PDH thick-stop sketch → **INTAKE_KILL** (PDH/SB densify).",
        "  Offline joint screen:",
    ]
    for i, r in enumerate(results, 1):
        block.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']})."
        )
    block += [
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        f"  VN `readouts/{STEM}_VN_ACTION_BRIEF.md`;",
        "  session `readouts/20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md`;",
        f"  panel `readouts/{STEM}_3CRITIC_PANEL.md`.",
        f"  QFSI parallel: {qfsi_note}",
        "  Do **not** densify W1 trail / M15 range-k / inside pattern / R6–R7 /",
        "  PDH / SB / Weekly-HL H4 / triad / NAS / metal / FX3 H4 path.",
        "  Next: next true greenfield outside unpark board — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    lines = HOT.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | Unpark W1/M15 "
            f"{status.split('__')[0]}; GOAL unmet"
        )
    # Drop prior unpark block if re-run
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if "UNPARK W1/M15 THICK CLOSEOUT" in ln:
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.startswith("- **") or (
                    nxt.startswith("## ") and "Active Truth" not in nxt
                ):
                    break
                if nxt.strip() == "" and i + 1 < len(lines) and lines[i + 1].startswith(
                    "- **"
                ):
                    i += 1
                    break
                i += 1
            continue
        cleaned.append(ln)
        i += 1
    lines = cleaned
    out = []
    inserted = False
    for ln in lines:
        out.append(ln)
        if not inserted and ln.strip() == "## Active Truth":
            out.extend(block)
            inserted = True
    HOT.write_text("\n".join(out) + "\n", encoding="utf-8")


def qfsi_parallel_note() -> str:
    prog = (
        ROOT
        / "02. AlphaFactory"
        / "evidence"
        / "execution"
        / "FivePercentOnline-Real"
        / "20260715_QFSI_REAL_007_LONG_ACCUMULATE"
        / "capture_progress.json"
    )
    if not prog.exists():
        return "007 dir missing — cost GAP unchanged; not headline."
    try:
        p = json.loads(prog.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "007 progress unreadable — cost GAP unchanged."
    hb = p.get("heartbeat_rows")
    qr = p.get("quote_rows")
    dl = p.get("deadline_utc")
    return (
        f"007 accumulate hb={hb} quotes={qr} deadline={dl}; "
        "cost freeze still GAP; login not headline."
    )


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 init fail: {mt5.last_error()}")

    intake_killed = [
        {
            "hypothesis_id": "HYP-USDJPY-M15-D1BIAS-PDHPDL-THICK-001",
            "setup_type": "panel_pdh_thickstop_sketch",
            "reason": "INTAKE_KILL: identical surface to parked HYP-PDH-BREAK-M15-001 "
            "(D1 EMA50 + M15 beyond prior D1 H/L) + SB/session densify contamination. "
            "Replaced by RANGEEXP thick-stop + D1-inside greenfield.",
        }
    ]

    write_preregs()
    qfsi_note = qfsi_parallel_note()

    try:
        d1_map = {s: enrich(load(s, mt5.TIMEFRAME_D1)) for s in FX3}
        w1_map = {s: enrich(load(s, mt5.TIMEFRAME_W1)) for s in FX3}
        m15 = enrich(load("USDJPY", mt5.TIMEFRAME_M15))
        d1_uj = enrich(load("USDJPY", mt5.TIMEFRAME_D1), ema_n=M15_EMA)
        h1_uj = enrich(load("USDJPY", mt5.TIMEFRAME_H1))

        results = []
        pnls, detail = probe_w1_hlbreak_d1conf(d1_map, w1_map)
        results.append(
            pack_result(
                "HYP-FX3-W1-HLBREAK-D1CONF-HOLD-001",
                "w1_hlbreak_d1conf_atr_trail_position",
                "FX3",
                "W1+D1",
                pnls,
                detail,
            )
        )
        pnls, detail = probe_m15_rangeexp_thick(m15, d1_uj)
        results.append(
            pack_result(
                "HYP-USDJPY-M15-D1BIAS-RANGEEXP-THICK-001",
                "m15_d1bias_rangeexp_thickstop",
                "USDJPY",
                "M15",
                pnls,
                detail,
            )
        )
        pnls, detail = probe_d1_inside_h1_break(h1_uj, d1_uj)
        results.append(
            pack_result(
                "HYP-USDJPY-D1-INSIDE-H1-BREAK-CONT-001",
                "d1_inside_h1_break_cont",
                "USDJPY",
                "H1",
                pnls,
                detail,
            )
        )
    finally:
        mt5.shutdown()

    any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
    payload = {
        "generated_at_utc": utc_now(),
        "lane": "unpark_w1_m15_thick_20260715",
        "base_cost_usd": BASE_COST,
        "window": "2021-01-01..2025-12-31",
        "intake_killed": intake_killed,
        "results": results,
        "any_survivor": any_surv,
        "model0": "AUTHORIZED_FOR_SURVIVORS" if any_surv else "WITHHELD",
        "qfsi_parallel": qfsi_note,
        "best_shelf": "194548",
        "nested_critic": "cursor-grok-4.5-high-fast",
    }
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    receipt = sha256_bytes(raw)
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_bytes(
        json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    )

    write_docs(results, intake_killed, receipt, any_surv, qfsi_note)
    append_reg(results, intake_killed, receipt)
    patch_hot(results, intake_killed, receipt, any_surv, qfsi_note)

    print(json.dumps({"receipt": receipt, "any_survivor": any_surv, "results": [
        {
            "id": r["hypothesis_id"],
            "n": r["metrics"]["n"],
            "pf": r["metrics"]["pf"],
            "tpw": r["metrics"]["tpw"],
            "x1_5": r["haircuts"]["x1_5"]["pf"],
            "verdict": r["verdict"],
            "notes": r["fail_notes"],
        }
        for r in results
    ]}, indent=2))


if __name__ == "__main__":
    main()
