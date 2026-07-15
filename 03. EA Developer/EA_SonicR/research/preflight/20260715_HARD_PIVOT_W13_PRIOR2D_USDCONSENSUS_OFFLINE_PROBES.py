#!/usr/bin/env python3
"""HARD PIVOT W13 — prior-2D range-break CONT + USD-consensus impulse after W1–W12 ALL_KILL.

FORBIDDEN densify: W1–W12 / FVG / R-series / swing / Donch / Outside / VR /
absorb3 / weekday-gap / inventory / NR7 / H4-engulf / ORB/IB / closeloc.

NEW classes (outside W1–W12 densify bans):
  A. HYP-FX3-H1-PRIOR2D-RANGE-BREAK-CONT-001
     Close beyond prior 2-weekday H/L (successful break CONT).
     ≠ W9 failed-2D reverse; ≠ Outside densify; ≠ W10 prior-month HL.
  B. HYP-FX3-H1-USD-CONSENSUS-IMPULSE-CONT-001
     ≥2/3 FX3 same USD-direction impulse on closed H1 → enter agreeing pairs.
     ≠ W5 leadlag peer accept; ≠ USBILL basket; ≠ R24 RS-rank densify.
  BOOK. HYP-BOOK-PRIOR2D-USDCONSENSUS-APRIORI-001

+$12 still hard RESEARCH-GRADE screen. Model 0 only PROBE_SURVIVOR.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"
PREREG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preregs"

STEM = "20260715_HARD_PIVOT_W13_PRIOR2D_USDCONSENSUS"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_HARD_PIVOT_W13_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_APRIORI_FREEZE.md"
OUT_COMBO_VN = READ / "20260715_COST_GRADE_AND_HARD_PIVOT_W13_VN_ACTION_BRIEF.md"
COST_STATUS = PRE / "20260715_COST_GRADE_PUSH_W13_STATUS.json"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
CASH_R = DEPOSIT * RISK_FRAC
FX3 = ("EURUSD", "GBPUSD", "USDJPY")
CORR_CAP = 0.35
OVERLAP_FRAC_CAP = 0.05

A_SL_PAD = 0.15
A_SL_MIN_ATR = 1.35
A_RR = 3.00
A_HOLD = 48
A_PRIORITY = 1
A_MAX_BOOK = 2
A_ENTRY_HOURS = (0, 20)

B_IMPULSE_ATR = 0.40
B_MIN_VOTES = 2
B_SL_PAD = 0.20
B_SL_MIN_ATR = 1.20
B_RR = 2.75
B_HOLD = 32
B_PRIORITY = 2
B_MAX_BOOK = 2
B_COOLDOWN_BARS = 4


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
        cut = [float(p) - BASE_COST * mult for p in pnls]
        p = pf_of(cut)
        out[key] = {
            "pf": None if not cut else round(float(p or 0.0), 4),
            "net": round(float(sum(cut)), 2) if cut else 0.0,
            "exp": round(float(sum(cut) / len(cut)), 4) if cut else 0.0,
        }
    return out


def metrics(pnls):
    n = len(pnls)
    p = pf_of(pnls)
    net = float(sum(pnls)) if pnls else 0.0
    return {
        "n": int(n),
        "pf": None if p is None else round(float(p), 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(float(n / WEEKS), 4) if WEEKS else None,
    }


def joint_verdict(m, hc):
    notes = []
    n, pf, tpw = m["n"] or 0, m["pf"] or 0.0, m["tpw"] or 0.0
    pf12 = hc["x1"]["pf"] or 0.0
    if n < 80:
        notes.append("n_fail")
    if pf is None or pf < 1.30:
        notes.append("pf_fail")
    if tpw is None or tpw < 2.0 or tpw > 5.0:
        notes.append("cadence_fail")
    if pf12 < 1.30:
        notes.append("pf12_fail")
    if hc["x1_5"]["pf"] is None or hc["x1_5"]["pf"] < 1.25:
        notes.append("stress_fail")
    return ("PROBE_SURVIVOR", []) if not notes else ("KILLED_AT_OFFLINE_PROBE", notes)


def book_verdict(m, hc, caps_ok: bool):
    notes = []
    n, pf, tpw = m["n"] or 0, m["pf"] or 0.0, m["tpw"] or 0.0
    pf12 = hc["x1"]["pf"] or 0.0
    if n < 80:
        notes.append("n_fail")
    if pf is None or pf < 1.30:
        notes.append("pf_fail")
    if tpw is None or tpw < 2.0 or tpw > 5.0:
        notes.append("cadence_fail")
    if pf12 < 1.30:
        notes.append("pf12_fail")
    if hc["x1_5"]["pf"] is None or hc["x1_5"]["pf"] < 1.25:
        notes.append("stress_fail")
    if not caps_ok:
        notes.append("caps_fail")
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


def enrich(d):
    d["atr"] = atr_arr(d["h"], d["l"], d["c"])
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
    risk = CASH_R
    dist = abs(entry - sl)
    if dist <= 0 or info is None:
        return 0.01
    tick_val = float(info.trade_tick_value) or 1.0
    tick_size = float(info.trade_tick_size) or pip_size(symbol)
    loss = dist / tick_size * tick_val
    if loss <= 0:
        return 0.01
    step = 0.01
    if info.volume_min and info.volume_min < 0.01:
        step = float(info.volume_min)
    lots = math.floor(risk / loss / step) * step
    return min(5.0, max(float(info.volume_min or 0.01), lots))


def manage_exits(open_pos, data, ts, closed, hold_limit):
    still = []
    for pos in open_pos:
        sym = pos["sym"]
        d = data[sym]
        idx = int(np.searchsorted(d["t"], ts, side="left"))
        if idx >= len(d["t"]) or d["t"][idx] != ts:
            still.append(pos)
            continue
        exit_px = reason = None
        if pos["side"] > 0:
            if d["l"][idx] <= pos["sl"]:
                exit_px, reason = pos["sl"], "sl"
            elif d["h"][idx] >= pos["tp"]:
                exit_px, reason = pos["tp"], "tp"
        else:
            if d["h"][idx] >= pos["sl"]:
                exit_px, reason = pos["sl"], "sl"
            elif d["l"][idx] <= pos["tp"]:
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
                    "entry_ts": pos.get("entry_ts"),
                    "sleeve": pos.get("sleeve"),
                    "priority": pos.get("priority"),
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
                "pnl": cash_pnl(pos["sym"], pos["side"], pos["entry"], float(d["c"][-1]), pos["lots"]),
                "reason": "eod",
                "sym": pos["sym"],
                "entry_ts": pos.get("entry_ts"),
                "sleeve": pos.get("sleeve"),
                "priority": pos.get("priority"),
            }
        )


def summarize(closed):
    pnls = [x["pnl"] for x in closed]
    detail = {"by_reason": {}, "by_sym": {}}
    for x in closed:
        detail["by_reason"][x["reason"]] = detail["by_reason"].get(x["reason"], 0) + 1
        detail["by_sym"][x["sym"]] = detail["by_sym"].get(x["sym"], 0) + 1
    return pnls, detail, closed


def _jsonable(x):
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_jsonable(v) for v in x]
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


def pack_result(hid, setup, pnls, detail, tf="H1"):
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc)
    return _jsonable(
        {
            "hypothesis_id": hid,
            "setup": setup,
            "symbol": "EURUSD+GBPUSD+USDJPY",
            "timeframe": tf,
            "metrics": m,
            "haircuts": hc,
            "verdict": verdict,
            "fail_notes": notes,
            "detail": detail,
        }
    )


def asof_idx(d, ts):
    j = int(np.searchsorted(d["t"], ts, side="left"))
    if j < len(d["t"]) and int(d["t"][j]) == int(ts):
        return j
    return None


def build_prior_2d_ranges(d):
    day_hl = {}
    for j in range(len(d["t"])):
        dt = datetime.fromtimestamp(int(d["t"][j]), tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        day = dt.date()
        h, l = float(d["h"][j]), float(d["l"][j])
        if day not in day_hl:
            day_hl[day] = {"hi": h, "lo": l}
        else:
            day_hl[day]["hi"] = max(day_hl[day]["hi"], h)
            day_hl[day]["lo"] = min(day_hl[day]["lo"], l)
    days = sorted(day_hl.keys())
    out = {}
    for i, day in enumerate(days):
        if i < 2:
            continue
        d1, d2 = days[i - 1], days[i - 2]
        out[day] = {
            "hi": max(day_hl[d1]["hi"], day_hl[d2]["hi"]),
            "lo": min(day_hl[d1]["lo"], day_hl[d2]["lo"]),
        }
    return out


def usd_impulse(sym, o, c, atr):
    """Signed USD impulse in ATR units. + = USD stronger."""
    if atr <= 0 or not np.isfinite(atr):
        return 0.0
    body = (c - o) / atr
    if sym in ("EURUSD", "GBPUSD"):
        return -body
    if sym == "USDJPY":
        return body
    return 0.0


def fx_side_for_usd(sym, usd_sign: int) -> int:
    """usd_sign +1 = USD up. Return FX trade side (+1 long pair)."""
    if sym in ("EURUSD", "GBPUSD"):
        return -usd_sign
    if sym == "USDJPY":
        return usd_sign
    return 0


def probe_prior2d_break_cont(h1):
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    ranges = {s: build_prior_2d_ranges(h1[s]) for s in FX3}
    used = set()
    for i in range(60, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, A_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if not (A_ENTRY_HOURS[0] <= dt.hour < A_ENTRY_HOURS[1]):
            continue
        if len(open_pos) >= A_MAX_BOOK:
            continue
        sig_ts = int(clock[i - 1])
        sig_dt = datetime.fromtimestamp(sig_ts, tz=timezone.utc)
        if sig_dt.weekday() >= 5:
            continue
        day = sig_dt.date()
        for sym in FX3:
            if sym in open_syms:
                continue
            key = (day, sym)
            if key in used:
                continue
            rng = ranges[sym].get(day)
            if rng is None:
                continue
            d = h1[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < 20:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            o, h, l, c = float(d["o"][j]), float(d["h"][j]), float(d["l"][j]), float(d["c"][j])
            hi, lo = rng["hi"], rng["lo"]
            side = 0
            ext = None
            # Successful break CONT: pierce + close beyond prior 2D HL
            if c > hi and h > hi:
                side = 1
                ext = hi
            elif c < lo and l < lo:
                side = -1
                ext = lo
            if side == 0:
                continue
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            atr1 = d["atr"][ent_i] if np.isfinite(d["atr"][ent_i]) else atr
            if side > 0:
                sl = ext - A_SL_PAD * atr1
                sl = min(sl, entry - A_SL_MIN_ATR * atr1)
            else:
                sl = ext + A_SL_PAD * atr1
                sl = max(sl, entry + A_SL_MIN_ATR * atr1)
            sl_dist = abs(entry - sl)
            if sl_dist <= 1e-12:
                continue
            tp = entry + side * A_RR * sl_dist
            lots = risk_lots(sym, entry, sl)
            open_pos.append(
                {
                    "sym": sym,
                    "side": side,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "lots": lots,
                    "bars": 0,
                    "entry_ts": ts,
                    "sleeve": "A_PRIOR2D",
                    "priority": A_PRIORITY,
                }
            )
            used.add(key)
    flush_open(open_pos, h1, closed)
    return summarize(closed)


def probe_usd_consensus_impulse(h1):
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    last_entry_i = -10**9
    for i in range(80, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, B_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if len(open_pos) >= B_MAX_BOOK:
            continue
        if i - last_entry_i < B_COOLDOWN_BARS:
            continue
        sig_ts = int(clock[i - 1])
        votes = {}  # sym -> usd_impulse
        for sym in FX3:
            d = h1[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < 20:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            o, c = float(d["o"][j]), float(d["c"][j])
            imp = usd_impulse(sym, o, c, atr)
            if abs(imp) >= B_IMPULSE_ATR:
                votes[sym] = imp
        if len(votes) < B_MIN_VOTES:
            continue
        # consensus sign among voters
        pos_n = sum(1 for v in votes.values() if v > 0)
        neg_n = sum(1 for v in votes.values() if v < 0)
        if pos_n >= B_MIN_VOTES and pos_n > neg_n:
            usd_sign = 1
        elif neg_n >= B_MIN_VOTES and neg_n > pos_n:
            usd_sign = -1
        else:
            continue
        agreeing = [s for s, v in votes.items() if (v > 0 and usd_sign > 0) or (v < 0 and usd_sign < 0)]
        placed = 0
        for sym in agreeing:
            if sym in open_syms:
                continue
            if len(open_pos) + placed >= B_MAX_BOOK:
                break
            d = h1[sym]
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            j = asof_idx(d, sig_ts)
            atr = d["atr"][j] if j is not None else d["atr"][ent_i]
            if not np.isfinite(atr) or atr <= 0:
                continue
            side = fx_side_for_usd(sym, usd_sign)
            if side == 0:
                continue
            entry = float(d["o"][ent_i])
            atr1 = d["atr"][ent_i] if np.isfinite(d["atr"][ent_i]) else atr
            # SL beyond signal bar extreme opposite to trade
            if side > 0:
                ext = float(d["l"][j])
                sl = ext - B_SL_PAD * atr1
                sl = min(sl, entry - B_SL_MIN_ATR * atr1)
            else:
                ext = float(d["h"][j])
                sl = ext + B_SL_PAD * atr1
                sl = max(sl, entry + B_SL_MIN_ATR * atr1)
            sl_dist = abs(entry - sl)
            if sl_dist <= 1e-12:
                continue
            tp = entry + side * B_RR * sl_dist
            lots = risk_lots(sym, entry, sl)
            open_pos.append(
                {
                    "sym": sym,
                    "side": side,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "lots": lots,
                    "bars": 0,
                    "entry_ts": ts,
                    "sleeve": "B_USDCONS",
                    "priority": B_PRIORITY,
                }
            )
            placed += 1
        if placed:
            last_entry_i = i
    flush_open(open_pos, h1, closed)
    return summarize(closed)


def weekly_series(trades, field="pnl"):
    buckets = defaultdict(float)
    for t in trades:
        ts = t.get("entry_ts")
        if ts is None:
            continue
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        iso = dt.isocalendar()
        buckets[(iso.year, iso.week)] += float(t[field])
    cur = FROM.date() - timedelta(days=FROM.weekday())
    end = TO.date()
    series = []
    while cur <= end:
        iso = cur.isocalendar()
        series.append(buckets.get((iso.year, iso.week), 0.0))
        cur += timedelta(days=7)
    return series


def pearson(a, b):
    n = len(a)
    if n != len(b) or n < 2:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    da, db = [x - ma for x in a], [y - mb for y in b]
    num = sum(x * y for x, y in zip(da, db))
    den = math.sqrt(sum(x * x for x in da) * sum(y * y for y in db))
    return None if den == 0 else num / den


def apply_heat(trades):
    best, dropped = {}, 0
    for t in sorted(trades, key=lambda t: (t.get("priority", 99), t.get("entry_ts", 0))):
        bar = int(t["entry_ts"]) // 3600 * 3600 if t.get("entry_ts") else 0
        k = (t["sym"], bar)
        if k not in best:
            best[k] = t
        else:
            dropped += 1
    return sorted(best.values(), key=lambda t: t.get("entry_ts", 0)), dropped


def pairwise_overlap(a, b):
    if not a or not b:
        return 0.0
    sa = {int(t["entry_ts"]) // 3600 for t in a if t.get("entry_ts")}
    sb = {int(t["entry_ts"]) // 3600 for t in b if t.get("entry_ts")}
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / min(len(sa), len(sb))


def evaluate_book(ta, tb):
    for t in ta:
        t["sleeve"], t["priority"] = "A_PRIOR2D", A_PRIORITY
        t["pnl_haircut"] = float(t["pnl"]) - BASE_COST
    for t in tb:
        t["sleeve"], t["priority"] = "B_USDCONS", B_PRIORITY
        t["pnl_haircut"] = float(t["pnl"]) - BASE_COST
    filtered, dropped = apply_heat(ta + tb)
    pnls = [float(t["pnl"]) for t in filtered]
    m, hc = metrics(pnls), haircuts(pnls)
    by = defaultdict(list)
    for t in filtered:
        by[t["sleeve"]].append(t)
    a, b = by.get("A_PRIOR2D", []), by.get("B_USDCONS", [])
    corr = pearson(weekly_series(a, "pnl_haircut"), weekly_series(b, "pnl_haircut"))
    ov = pairwise_overlap(a, b)
    caps_ok = not ((corr is not None and corr > CORR_CAP) or ov > OVERLAP_FRAC_CAP)
    verdict, notes = book_verdict(m, hc, caps_ok)
    return _jsonable(
        {
            "hypothesis_id": "HYP-BOOK-PRIOR2D-USDCONSENSUS-APRIORI-001",
            "setup": "a priori book: prior-2D break CONT + USD-consensus impulse",
            "symbol": "EURUSD+GBPUSD+USDJPY",
            "timeframe": "H1",
            "metrics": m,
            "haircuts": hc,
            "verdict": verdict,
            "fail_notes": notes,
            "pooled_after_heat": {"n": len(filtered), "dropped_heat": dropped, "a": len(a), "b": len(b)},
            "pair_caps": {
                "weekly_corr": None if corr is None else round(float(corr), 4),
                "overlap_frac": round(float(ov), 4),
                "caps_ok": caps_ok,
            },
        }
    )


def write_freeze():
    body = "\n".join(
        [
            "# A priori freeze — HARD PIVOT W13 prior-2D + USD-consensus",
            "",
            "Date: 2026-07-15",
            "Status: `APRIORI_FREEZE__PRE_METRICS`",
            f"A target MFE ≈ ${A_RR * CASH_R:.0f}; B ≈ ${B_RR * CASH_R:.0f} ≫ ${BASE_COST}.",
            "",
            "## Objects",
            "- HYP-FX3-H1-PRIOR2D-RANGE-BREAK-CONT-001",
            "- HYP-FX3-H1-USD-CONSENSUS-IMPULSE-CONT-001",
            "- HYP-BOOK-PRIOR2D-USDCONSENSUS-APRIORI-001",
            "",
            "## Forbidden",
            "W1–W12 densify; FVG; R-series; swing/Donch/Outside/VR; absorb3; weekday-gap;",
            "inventory; NR7; H4-engulf; ORB/IB; closeloc densify.",
            "",
            "## Screen",
            f"+${BASE_COST} a priori RESEARCH-GRADE; tpw∈[2,5]; PF@$12≥1.30; x1.5≥1.25; N≥80.",
            "",
        ]
    )
    OUT_FREEZE.write_text(body, encoding="utf-8")
    return sha256_bytes(body.encode("utf-8"))


def write_preregs():
    PREREG.mkdir(parents=True, exist_ok=True)
    specs = [
        (
            "20260715_H_FX3_H1_PRIOR2D_RANGE_BREAK_CONT_001_PREREG.md",
            "HYP-FX3-H1-PRIOR2D-RANGE-BREAK-CONT-001",
            [
                f"- Close beyond prior 2-weekday H/L → CONT; RR={A_RR}; hold≤{A_HOLD}.",
                "- ≠ W9 failed-2D reverse; ≠ Outside densify; ≠ W10 prior-month HL.",
            ],
        ),
        (
            "20260715_H_FX3_H1_USD_CONSENSUS_IMPULSE_CONT_001_PREREG.md",
            "HYP-FX3-H1-USD-CONSENSUS-IMPULSE-CONT-001",
            [
                f"- ≥{B_MIN_VOTES}/3 FX3 same USD impulse ≥{B_IMPULSE_ATR}*ATR → agreeing pairs CONT.",
                f"- RR={B_RR}; hold≤{B_HOLD}. ≠ W5 leadlag; ≠ USBILL; ≠ R24 RS-rank.",
            ],
        ),
        (
            "20260715_H_BOOK_PRIOR2D_USDCONSENSUS_APRIORI_001_PREREG.md",
            "HYP-BOOK-PRIOR2D-USDCONSENSUS-APRIORI-001",
            [
                f"- Pool A+B; corr≤{CORR_CAP}; overlap≤{OVERLAP_FRAC_CAP}; +$12; tpw[2,5].",
            ],
        ),
    ]
    paths = []
    for fname, hid, extra in specs:
        p = PREREG / fname
        p.write_text(
            "\n".join(
                [
                    f"# Prereg — {hid}",
                    "",
                    "- State: `preregistered` (frozen pre-offline)",
                    "- Lane: `hard_pivot_w13_prior2d_usdconsensus_20260715`",
                    *extra,
                    "- Model 0: only PROBE_SURVIVOR.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        paths.append(str(p.as_posix()))
    return paths


def _table(rows):
    lines = [
        "| Object | N | PF | tpw | PF@$12 | x1.5 | Verdict |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        m, hc = r["metrics"], r["haircuts"]
        v = "KILL" if "KILL" in r["verdict"] else "SURV"
        lines.append(
            f"| `{r['hypothesis_id']}` | {m['n']} | {m['pf']} | {m['tpw']} | "
            f"{hc['x1']['pf']} | {hc['x1_5']['pf']} | {v} |"
        )
    return lines


def append_registry(results, book, receipt):
    stamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    rows = []
    for r in results + [book]:
        rows.append(
            {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": r["hypothesis_id"],
                "state": "killed" if "KILL" in r["verdict"] else "probe_survivor",
                "parent_candidate": "hard_pivot_w13_prior2d_usdconsensus",
                "feature_family": "hard_pivot_w13_prior2d_usdcons",
                "lane": "hard_pivot_w13_prior2d_usdconsensus_20260715",
                "setup_type": r.get("setup"),
                "symbol": "FX3",
                "timeframe": "H1",
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "metrics": {
                    "n": r["metrics"]["n"],
                    "pf": r["metrics"]["pf"],
                    "tpw": r["metrics"]["tpw"],
                    "pf_cost_x1": r["haircuts"]["x1"]["pf"],
                    "pf_cost_x1_5": r["haircuts"]["x1_5"]["pf"],
                },
                "validation": {
                    "offline_probe": str(OUT_JSON.as_posix()),
                    "receipt_sha256": receipt,
                    "status": r["verdict"],
                    "fail_notes": r.get("fail_notes"),
                    "model0": "WITHHELD" if "KILL" in r["verdict"] else "ELIGIBLE",
                },
                "verdict": r["verdict"],
                "updated_at": stamp,
            }
        )
    with REG.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def cost_grade_lines():
    if not COST_STATUS.exists():
        return [
            "Cost grade: status JSON missing — assume GAP (11 deals, ≪90d).",
        ]
    cs = json.loads(COST_STATUS.read_text(encoding="utf-8"))
    d = cs.get("distance_to_freeze", {})
    hb = cs.get("watcher_heartbeat", {})
    cp = cs.get("qfsi_007_capture_progress", {})
    return [
        f"- QFSI 007: watcher_alive={hb.get('watcher_alive')} cap_pid={hb.get('capture_pid')} "
        f"quotes={cp.get('quote_rows')} hb={cp.get('heartbeat_rows')} tick_err={cp.get('tick_errors')}",
        f"- quote_days={d.get('quote_days')}; raw_deals={d.get('raw_deals')}; freeze_eligible={d.get('freeze_eligible')}",
        f"- commission unique days: {d.get('commission_lifecycle_proxy_unique_days')}",
        f"- slip: {d.get('slippage')}",
        f"- verdict: `{d.get('verdict')}`",
        "- Autonomous remaining: keep QFSI alive (calendar-bound days); retry deals (still ~11=exhausted); "
        "do NOT invent cost; Owner export optional only.",
    ]


def write_docs(results, book, receipt, any_surv, freeze_sha):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    table = _table(results + [book])
    cg = cost_grade_lines()
    OUT_PANEL.write_text(
        "\n".join(
            [
                "# 3-critic — W13 prior-2D + USD-consensus",
                "",
                "| Critic | Call |",
                "|---|---|",
                "| Sonic trader | GO — 2D success CONT ≠ W9 fail-reverse; USD consensus ≠ location accept |",
                "| Quant | GO — freeze MFE≫$12 + book caps pre-metrics; honest +$12 kill |",
                "| MQL5/MT5 | GO offline closed-bar; Model0 withheld until survivor |",
                "",
                "Merge: GO offline probe. Lead self-merge closeout.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — HARD PIVOT W13 prior-2D + USD-consensus",
                "",
                f"Freeze sha={freeze_sha[:16]}…",
                "",
                "After W1–W12 ALL_KILL (location/book/high-R/gap/absorb).",
                "NEW classes outside densify bans:",
                "1) Prior 2-weekday range break CONT (success path ≠ W9 fail-reverse).",
                "2) USD-consensus impulse across FX3 (≥2 agreeing).",
                f"A priori MFE A=${A_RR*CASH_R:.0f} B=${B_RR*CASH_R:.0f} ≫ $12.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — W13",
                "",
                "| Object | ≠ |",
                "|---|---|",
                "| prior-2D break CONT | W9 failed-2D reverse; Outside densify; W10 prior-month HL |",
                "| USD-consensus impulse | W5 leadlag peer accept; USBILL basket; R24 RS-rank densify |",
                "",
                "Clearance: PASS a priori (pre-metrics).",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                f"# HARD PIVOT W13 offline probes — `{status}`",
                "",
                f"Receipt `{receipt}`",
                "QFSI: QFSI 007 parallel; cost freeze GAP; login not headline",
                "",
                *table,
                "",
                f"- Caps book: corr={book['pair_caps']['weekly_corr']} "
                f"overlap={book['pair_caps']['overlap_frac']} ok={book['pair_caps']['caps_ok']}",
                "- Model 0: WITHHELD (no survivor)" if not any_surv else "- Model 0: ELIGIBLE survivor present",
                "",
                "## Cost grade",
                *cg,
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN — HARD PIVOT W13 prior-2D + USD-consensus",
                "",
                f"`{status}`",
                "",
                *table,
                "",
                "Không densify W1–W12 / FVG / R-series / absorb3 / weekday-gap.",
                f"Receipt `{receipt}`",
                "GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLOSE.write_text(
        "\n".join(
            [
                f"# Session closeout — HARD PIVOT W13 — `{status}`",
                "",
                f"Receipt `{receipt}` freeze sha={freeze_sha[:16]}…",
                "R-series densify PAUSED. Model0 withheld if ALL_KILL.",
                "Next: next independent class outside W1–W13 if ALL_KILL;",
                "keep +$12 research screen; QFSI parallel; cost freeze GAP.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLEAN_VN.write_text(
        "\n".join(
            [
                "# VN action brief — Clean book + HARD PIVOT W13",
                "",
                f"Thời điểm: 2026-07-15 ~{datetime.now().strftime('%H:%M')} ICT",
                "",
                "## Clean book (unchanged RESEARCH-GRADE @$12)",
                "PRIMARY PF@$12=1.184 tpw=3.241. Best shelf RR2 `194548`.",
                "DIAGNOSTIC RealP50≈1.356 ≠ GOAL — không promote.",
                "",
                f"## HARD PIVOT W13 — `{status}`",
                *table,
                "",
                "- Prior-2D success CONT + USD-consensus impulse; MFE ≫ $12 a priori.",
                "- Không densify W1–W13 / FVG / R-series / swing / Donch / Outside / VR.",
                f"Receipt `{receipt}`",
                "GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_COMBO_VN.write_text(
        "\n".join(
            [
                "# VN action brief — Cost-grade push + HARD PIVOT W13",
                "",
                f"Thời điểm: 2026-07-15 ~{datetime.now().strftime('%H:%M')} ICT",
                "",
                "## Track 1 — Cost-grade push (distance to research-grade freeze)",
                *cg,
                "",
                "- Clean PRIMARY PF@$12=**1.184** tpw=3.24 vẫn binding RESEARCH-GRADE.",
                "- RealP50≈1.356 / PF@$8 đẹp hơn chỉ là DIAGNOSTIC — **không nới GOAL**.",
                "- Deal history vẫn **11** → broker history exhausted cho login này; không invent.",
                "",
                f"## Track 2 — HARD PIVOT W13 `{status}`",
                *table,
                f"Receipt W13 `{receipt}`",
                "GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def patch_hot(results, book, receipt, any_surv, freeze_sha):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    lines_tbl = []
    for r in results + [book]:
        m, hc = r["metrics"], r["haircuts"]
        lines_tbl.append(
            f"  {len(lines_tbl)+1}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={m['n']} PF={m['pf']} tpw={m['tpw']} PF@$12={hc['x1']['pf']} x1.5={hc['x1_5']['pf']})."
        )
    cg = cost_grade_lines()
    block = "\n".join(
        [
            f"- **HARD PIVOT W13 PRIOR2D/USDCONSENSUS + COST-GRADE CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
            f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED` / `{status}` / "
            f"`QFSI_007_HEALTHY` / `NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
            "  Dual-track: (1) cost-grade distance-to-freeze; (2) HARD PIVOT W13 new class.",
            "  **Cost-grade** `preflight/20260715_COST_GRADE_PUSH_W13_STATUS.json`:",
            *[f"  {ln}" for ln in cg],
            "  Clean PRIMARY PF@$12=1.184 tpw=3.241; RealP50 DIAGNOSTIC only — do NOT promote GOAL.",
            "  **W13 offline** after W1–W12 ALL_KILL — prior-2D break CONT + USD-consensus impulse:",
            *lines_tbl,
            f"  Receipt `{receipt}`",
            f"  `preflight/{OUT_JSON.name}`;",
            f"  VN `readouts/{OUT_COMBO_VN.name}`.",
            f"  Freeze sha={freeze_sha[:16]}… QFSI: QFSI 007 parallel; cost freeze GAP (11 deals); login not headline",
            "  Do **not** densify W13 / W1–W12 / FVG / absorb3 / R10–R31 / swing / Donch / Outside / VR.",
            "  Clean book still GOAL_SCREEN_FAIL. PRIMARY PF@$12=1.184 tpw=3.241.",
            "  Next: next independent class outside W1–W13; keep R-series paused; +$12 screen holds.",
            "  Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
            "",
            "",
        ]
    )
    text = HOT.read_text(encoding="utf-8")
    text = re.sub(
        r"^Updated:.*$",
        f"Updated: 2026-07-15 ~{stamp} ICT | HARD PIVOT W13 prior2d/usdconsensus + cost-grade; "
        f"R-series densify PAUSED; {status}; GOAL unmet",
        text,
        count=1,
        flags=re.M,
    )
    marker = "## Active Truth\n"
    if marker in text:
        idx = text.index(marker) + len(marker)
        text = text[:idx] + "\n" + block + text[idx:]
    else:
        text = block + text
    HOT.write_text(text, encoding="utf-8")


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 init fail: {mt5.last_error()}")
    try:
        freeze_sha = write_freeze()
        preregs = write_preregs()
        h1 = {s: enrich(load(s, mt5.TIMEFRAME_H1)) for s in FX3}
        pnls_a, detail_a, trades_a = probe_prior2d_break_cont(h1)
        pnls_b, detail_b, trades_b = probe_usd_consensus_impulse(h1)
        ra = pack_result(
            "HYP-FX3-H1-PRIOR2D-RANGE-BREAK-CONT-001",
            "Prior 2-weekday HL break CONT RR3",
            pnls_a,
            detail_a,
        )
        rb = pack_result(
            "HYP-FX3-H1-USD-CONSENSUS-IMPULSE-CONT-001",
            "USD-consensus impulse ≥2/3 FX3 CONT RR2.75",
            pnls_b,
            detail_b,
        )
        book = evaluate_book(trades_a, trades_b)
        results = [ra, rb]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results + [book])
        payload = {
            "schema_version": "hard_pivot_w13_prior2d_usdconsensus_offline.v1",
            "generated_at_utc": utc_now(),
            "freeze_sha256": freeze_sha,
            "preregs": preregs,
            "base_cost_usd": BASE_COST,
            "cost_grade_status": str(COST_STATUS.as_posix()) if COST_STATUS.exists() else None,
            "results": results,
            "book": book,
            "any_survivor": any_surv,
            "flags": {
                "R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED": True,
                "W1_W12_DENSIFY_FORBIDDEN": True,
                "FVG_DENSIFY_FORBIDDEN": True,
            },
        }
        raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        receipt = sha256_bytes(raw)
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        write_docs(results, book, receipt, any_surv, freeze_sha)
        append_registry(results, book, receipt)
        patch_hot(results, book, receipt, any_surv, freeze_sha)
        print(
            json.dumps(
                {
                    "receipt": receipt,
                    "any_survivor": any_surv,
                    "results": [
                        {
                            "id": r["hypothesis_id"],
                            "verdict": r["verdict"],
                            "n": r["metrics"]["n"],
                            "pf": r["metrics"]["pf"],
                            "pf12": r["haircuts"]["x1"]["pf"],
                            "tpw": r["metrics"]["tpw"],
                            "notes": r.get("fail_notes"),
                        }
                        for r in results + [book]
                    ],
                },
                indent=2,
            )
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
