#!/usr/bin/env python3
"""HARD PIVOT W12 — weekday D1 gap CONT + H1 absorb3 reverse after W1–W11 ALL_KILL.

FORBIDDEN densify: W1–W11 / FVG / R-series / swing / Donch / Outside / VR /
weekend-gap-fade / D1-inside densify / London-inventory densify.

NEW classes (outside location-accept shelf):
  A. HYP-FX3-H1-WEEKDAY-D1GAP-CONT-MULTIDAY-001
     Weekday D1 gap ≥0.30 ATR_D1 (vs prior D1 close) → first H1 CONT in gap dir;
     RR=3.0; hold≤48 H1; thick SL beyond gap extreme. ≠ weekend gap fade;
     ≠ USDJPY-only D1 gap fade; ≠ W10/W11 location.
  B. HYP-FX3-H1-ABSORB3-WICK-REVERSE-001
     3 consecutive H1 bars probing same swing extreme with declining bodies,
     final rejection wick ≥0.55 ATR → reverse CONT; RR=2.75; hold≤32.
     ≠ insidebar mother (W8); ≠ breaker retest (W2); ≠ FVG.
  BOOK. HYP-BOOK-WEEKDAYGAP-ABSORB-APRIORI-001

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

STEM = "20260715_HARD_PIVOT_W12_WEEKDAYGAP_ABSORB"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_HARD_PIVOT_W12_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_APRIORI_FREEZE.md"
COST_LADDER_MD = READ / "20260715_COST_LADDER_DIAGNOSTIC_RR2_CLEANBOOK.md"
COST_LADDER_JSON = PRE / "20260715_COST_LADDER_DIAGNOSTIC_RR2_CLEANBOOK.json"
OUT_COMBO_VN = READ / "20260715_COST_LADDER_AND_HARD_PIVOT_W12_VN_ACTION_BRIEF.md"

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

A_GAP_ATR = 0.30
A_SL_PAD = 0.15
A_SL_MIN_ATR = 1.40
A_RR = 3.00
A_HOLD = 48
A_PRIORITY = 1
A_MAX_BOOK = 2
A_ENTRY_HOURS = (0, 12)  # first H1 opportunities after D1 open

B_N = 3
B_WICK_ATR = 0.55
B_BODY_SHRINK = 0.85  # each body ≤ prior * this
B_SL_PAD = 0.20
B_SL_MIN_ATR = 1.20
B_RR = 2.75
B_HOLD = 32
B_PRIORITY = 2
B_MAX_BOOK = 2
B_SWING = 12


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


def build_d1(h1_sym):
    by = {}
    for j in range(len(h1_sym["t"])):
        dt = datetime.fromtimestamp(int(h1_sym["t"][j]), tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        day = dt.date()
        o, h, l, c = float(h1_sym["o"][j]), float(h1_sym["h"][j]), float(h1_sym["l"][j]), float(h1_sym["c"][j])
        atr = h1_sym["atr"][j]
        if day not in by:
            by[day] = {"o": o, "h": h, "l": l, "c": c, "atr": atr}
        else:
            by[day]["h"] = max(by[day]["h"], h)
            by[day]["l"] = min(by[day]["l"], l)
            by[day]["c"] = c
            if np.isfinite(atr):
                by[day]["atr"] = atr
    return sorted(by.keys()), by


def prior_weekday(day):
    d = day - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def probe_weekday_gap_cont(h1):
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    d1p = {s: build_d1(h1[s]) for s in FX3}
    used = set()
    for i in range(40, len(clock) - 1):
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
        for sym in FX3:
            if sym in open_syms:
                continue
            days, by = d1p[sym]
            day = dt.date()
            key = (day, sym)
            if key in used:
                continue
            prev = prior_weekday(day)
            if prev not in by or day not in by:
                continue
            # Skip Monday weekend gaps — weekday-only (Tue–Fri) vs prior weekday close.
            if day.weekday() == 0:
                continue
            b_prev, b_today = by[prev], by[day]
            atr = b_prev["atr"]
            if not np.isfinite(atr) or atr <= 0:
                continue
            # Gap measured at today's open vs prior close (closed-bar prior).
            gap = b_today["o"] - b_prev["c"]
            if abs(gap) < A_GAP_ATR * atr:
                continue
            # Enter only on first H1 of the day in window (hour of first available bar).
            d = h1[sym]
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            # first bar of this day for symbol in clock alignment: require entry open ≈ D1 open
            if abs(float(d["o"][ent_i]) - b_today["o"]) > 1e-8:
                # allow if this is still early and we haven't traded; require hour is first seen
                # Use: only trade when H1 open equals D1 open (true session open bar).
                continue
            side = 1 if gap > 0 else -1
            entry = float(d["o"][ent_i])
            atr1 = d["atr"][ent_i] if np.isfinite(d["atr"][ent_i]) else atr
            if side > 0:
                sl = min(b_prev["c"], entry) - A_SL_PAD * atr1
                sl = min(sl, entry - A_SL_MIN_ATR * atr1)
            else:
                sl = max(b_prev["c"], entry) + A_SL_PAD * atr1
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
                    "sleeve": "A_WEEKDAY_GAP",
                    "priority": A_PRIORITY,
                }
            )
            used.add(key)
    flush_open(open_pos, h1, closed)
    return summarize(closed)


def probe_absorb3_reverse(h1):
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    used = set()
    for i in range(80, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, B_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if len(open_pos) >= B_MAX_BOOK:
            continue
        sig_ts = int(clock[i - 1])  # closed bar decision
        for sym in FX3:
            if sym in open_syms:
                continue
            d = h1[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < B_SWING + B_N + 2:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            # last B_N closed bars ending at j
            idxs = list(range(j - B_N + 1, j + 1))
            bodies = [abs(d["c"][k] - d["o"][k]) for k in idxs]
            # declining bodies
            ok_shrink = all(
                bodies[k] <= bodies[k - 1] * B_BODY_SHRINK + 1e-12 for k in range(1, len(bodies))
            )
            if not ok_shrink:
                continue
            swing_hi = float(np.max(d["h"][j - B_SWING : j - B_N + 1]))
            swing_lo = float(np.min(d["l"][j - B_SWING : j - B_N + 1]))
            # bullish absorption at lows: bars probe near swing_lo, final lower wick reject up
            lows = [float(d["l"][k]) for k in idxs]
            highs = [float(d["h"][k]) for k in idxs]
            o0, c0 = float(d["o"][j]), float(d["c"][j])
            upper_wick = float(d["h"][j]) - max(o0, c0)
            lower_wick = min(o0, c0) - float(d["l"][j])
            near_lo = all(abs(lows[k] - swing_lo) <= 0.35 * atr for k in range(B_N))
            near_hi = all(abs(highs[k] - swing_hi) <= 0.35 * atr for k in range(B_N))
            side = 0
            ext = None
            if near_lo and lower_wick >= B_WICK_ATR * atr and c0 > o0:
                side = 1
                ext = min(lows)
            elif near_hi and upper_wick >= B_WICK_ATR * atr and c0 < o0:
                side = -1
                ext = max(highs)
            if side == 0:
                continue
            key = (int(sig_ts) // 3600, sym, side)
            if key in used:
                continue
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            atr1 = d["atr"][ent_i] if np.isfinite(d["atr"][ent_i]) else atr
            if side > 0:
                sl = ext - B_SL_PAD * atr1
                sl = min(sl, entry - B_SL_MIN_ATR * atr1)
            else:
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
                    "sleeve": "B_ABSORB3",
                    "priority": B_PRIORITY,
                }
            )
            used.add(key)
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
        t["sleeve"], t["priority"] = "A_WEEKDAY_GAP", A_PRIORITY
        t["pnl_haircut"] = float(t["pnl"]) - BASE_COST
    for t in tb:
        t["sleeve"], t["priority"] = "B_ABSORB3", B_PRIORITY
        t["pnl_haircut"] = float(t["pnl"]) - BASE_COST
    filtered, dropped = apply_heat(ta + tb)
    pnls = [float(t["pnl"]) for t in filtered]
    m, hc = metrics(pnls), haircuts(pnls)
    by = defaultdict(list)
    for t in filtered:
        by[t["sleeve"]].append(t)
    a, b = by.get("A_WEEKDAY_GAP", []), by.get("B_ABSORB3", [])
    corr = pearson(weekly_series(a, "pnl_haircut"), weekly_series(b, "pnl_haircut"))
    ov = pairwise_overlap(a, b)
    caps_ok = not ((corr is not None and corr > CORR_CAP) or ov > OVERLAP_FRAC_CAP)
    verdict, notes = book_verdict(m, hc, caps_ok)
    return _jsonable(
        {
            "hypothesis_id": "HYP-BOOK-WEEKDAYGAP-ABSORB-APRIORI-001",
            "setup": "a priori book: weekday D1 gap CONT + absorb3 wick reverse",
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
            "# A priori freeze — HARD PIVOT W12 weekday-gap + absorb3",
            "",
            "Date: 2026-07-15",
            "Status: `APRIORI_FREEZE__PRE_METRICS`",
            f"A target MFE ≈ ${A_RR * CASH_R:.0f}; B ≈ ${B_RR * CASH_R:.0f} ≫ ${BASE_COST}.",
            "",
            "## Objects",
            "- HYP-FX3-H1-WEEKDAY-D1GAP-CONT-MULTIDAY-001",
            "- HYP-FX3-H1-ABSORB3-WICK-REVERSE-001",
            "- HYP-BOOK-WEEKDAYGAP-ABSORB-APRIORI-001",
            "",
            "## Forbidden",
            "W1–W11 densify; FVG; R-series; swing/Donch/Outside/VR; weekend-gap densify;",
            "D1-inside densify; London-inventory densify.",
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
            "20260715_H_FX3_H1_WEEKDAY_D1GAP_CONT_MULTIDAY_001_PREREG.md",
            "HYP-FX3-H1-WEEKDAY-D1GAP-CONT-MULTIDAY-001",
            [
                f"- Tue–Fri D1 gap≥{A_GAP_ATR}*ATR vs prior weekday close → H1 open CONT.",
                f"- RR={A_RR}; hold≤{A_HOLD}. ≠ weekend gap fade; ≠ D1 gap fade densify; ≠ W10/W11.",
            ],
        ),
        (
            "20260715_H_FX3_H1_ABSORB3_WICK_REVERSE_001_PREREG.md",
            "HYP-FX3-H1-ABSORB3-WICK-REVERSE-001",
            [
                f"- {B_N} declining-body probes at swing + reject wick≥{B_WICK_ATR}*ATR → reverse CONT.",
                f"- RR={B_RR}; hold≤{B_HOLD}. ≠ W8 insidebar; ≠ W2 breaker; ≠ FVG.",
            ],
        ),
        (
            "20260715_H_BOOK_WEEKDAYGAP_ABSORB_APRIORI_001_PREREG.md",
            "HYP-BOOK-WEEKDAYGAP-ABSORB-APRIORI-001",
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
                    "- Lane: `hard_pivot_w12_weekdaygap_absorb_20260715`",
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
                "parent_candidate": "hard_pivot_w12_weekdaygap_absorb",
                "feature_family": "hard_pivot_w12_gap_absorb",
                "lane": "hard_pivot_w12_weekdaygap_absorb_20260715",
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


def write_docs(results, book, receipt, any_surv, freeze_sha):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    table = _table(results + [book])
    OUT_PANEL.write_text(
        "\n".join(
            [
                "# 3-critic — W12 weekday-gap + absorb3",
                "",
                "| Critic | Call |",
                "|---|---|",
                "| Sonic trader | GO — gap CONT ≠ weekend fade densify; absorb ≠ insidebar/breaker |",
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
                "# Design — HARD PIVOT W12 weekday-gap + absorb3",
                "",
                f"Freeze sha={freeze_sha[:16]}…",
                "",
                "After W1–W11 location/book + high-R inventory ALL_KILL.",
                "NEW classes outside accept-location shelf:",
                "1) Weekday D1 gap CONT multi-day (skip Mon weekend gap).",
                "2) H1 absorb3 declining-body wick reverse.",
                f"A priori MFE A=${A_RR*CASH_R:.0f} B=${B_RR*CASH_R:.0f} ≫ $12.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — W12",
                "",
                "| Object | ≠ |",
                "|---|---|",
                "| weekday-gap CONT | weekend gap fade; D1 gap fade USDJPY-only; W10/W11 inventory |",
                "| absorb3 reverse | W8 insidebar mother; W2 breaker; FVG retest; pin densify |",
                "",
                "Clearance: PASS a priori (pre-metrics).",
                "",
            ]
        ),
        encoding="utf-8",
    )
    body_md = "\n".join(
        [
            f"# HARD PIVOT W12 offline probes — `{status}`",
            "",
            f"Receipt `{receipt}`",
            "QFSI: QFSI 007 parallel; cost freeze GAP (11 deals); login not headline",
            "",
            *table,
            "",
            f"- Caps book: corr={book['pair_caps']['weekly_corr']} "
            f"overlap={book['pair_caps']['overlap_frac']} ok={book['pair_caps']['caps_ok']}",
            "- Model 0: WITHHELD (no survivor)" if not any_surv else "- Model 0: ELIGIBLE survivor present",
            "",
        ]
    )
    OUT_MD.write_text(body_md, encoding="utf-8")
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN — HARD PIVOT W12 weekday-gap + absorb3",
                "",
                f"`{status}`",
                "",
                *table,
                "",
                "Không densify W1–W11 / FVG / R-series / weekend-gap / D1-inside / inventory.",
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
                f"# Session closeout — HARD PIVOT W12 — `{status}`",
                "",
                f"Receipt `{receipt}` freeze sha={freeze_sha[:16]}…",
                "R-series densify PAUSED. Model0 withheld if ALL_KILL.",
                "Next: next independent class outside W1–W12 if ALL_KILL;",
                "keep +$12 research screen; QFSI parallel; cost freeze GAP.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    # Combined VN brief with cost-ladder pointer
    cost_note = "Cost-ladder diagnostic present." if COST_LADDER_MD.exists() else "Cost-ladder pending."
    OUT_CLEAN_VN.write_text(
        "\n".join(
            [
                "# VN action brief — Clean book + HARD PIVOT W12",
                "",
                f"Thời điểm: 2026-07-15 ~{datetime.now().strftime('%H:%M')} ICT",
                "",
                "## Clean book (unchanged RESEARCH-GRADE @$12)",
                "PRIMARY PF@$12=1.184 tpw=3.241. Best shelf RR2 `194548`.",
                "",
                f"## Cost-ladder (see `{COST_LADDER_MD.name}`)",
                cost_note,
                "DIAGNOSTIC Real/QFSI P50≈$2.62 ≠ GOAL. +$12 still binding RESEARCH-GRADE screen.",
                "",
                f"## HARD PIVOT W12 — `{status}`",
                *table,
                "",
                "- Weekday D1 gap CONT + absorb3 wick reverse; MFE ≫ $12 a priori.",
                "- Không densify W1–W12 / FVG / R-series / swing / Donch / Outside / VR.",
                f"Receipt `{receipt}`",
                "GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    if COST_LADDER_JSON.exists():
        try:
            cl = json.loads(COST_LADDER_JSON.read_text(encoding="utf-8"))
            dec = cl.get("decision", {})
            cl_receipt = cl.get("receipt_sha256", "")
        except Exception:
            dec, cl_receipt = {}, ""
    else:
        dec, cl_receipt = {}, ""
    OUT_COMBO_VN.write_text(
        "\n".join(
            [
                "# VN action brief — Cost-ladder + HARD PIVOT W12",
                "",
                f"Thời điểm: 2026-07-15 ~{datetime.now().strftime('%H:%M')} ICT",
                "",
                "## Track 1 — Cost-ladder (honest labels)",
                f"Receipt cost `{cl_receipt}`",
                f"- RR2 PF tester / RealP50 / @$8 / @$12: "
                f"{dec.get('rr2_pf_tester')} / {dec.get('rr2_pf_real_p50')} / "
                f"{dec.get('rr2_pf_apriori_8')} / {dec.get('rr2_pf_apriori_12')}",
                f"- Clean PRIMARY PF tester / RealP50 / @$8 / @$12: "
                f"{dec.get('book_pf_tester')} / {dec.get('book_pf_real_p50')} / "
                f"{dec.get('book_pf_apriori_8')} / {dec.get('book_pf_apriori_12')} "
                f"(tpw={dec.get('book_tpw')})",
                "- DIAGNOSTIC Real≈$2.62 cho thấy $12 punitive vs thin Real sample — "
                "NHƯNG freeze vẫn GAP → không nới GOAL. +$12 vẫn binding RESEARCH-GRADE.",
                "",
                f"## Track 2 — HARD PIVOT W12 `{status}`",
                *table,
                f"Receipt W12 `{receipt}`",
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
    block = "\n".join(
        [
            f"- **HARD PIVOT W12 WEEKDAYGAP/ABSORB CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
            f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED` / `{status}` / "
            f"`QFSI_007_HEALTHY` / `NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
            "  HARD PIVOT W12 after W1–W11 ALL_KILL — weekday D1 gap CONT + absorb3 reverse.",
            "  Offline screen:",
            *lines_tbl,
            f"  Receipt `{receipt}`",
            f"  `preflight/{OUT_JSON.name}`;",
            f"  VN `readouts/{OUT_CLEAN_VN.name}`;",
            f"  Cost-ladder `readouts/{COST_LADDER_MD.name}` (DIAGNOSTIC Real P50≈$2.62; +$12 binding).",
            f"  Freeze sha={freeze_sha[:16]}… QFSI: QFSI 007 parallel; cost freeze GAP (11 deals); login not headline",
            "  Do **not** densify W12 / W1–W11 / FVG / R10–R31 / swing / Donch / Outside / VR.",
            "  Clean book still GOAL_SCREEN_FAIL. PRIMARY PF@$12=1.184 tpw=3.241.",
            "  Next: next independent class outside W1–W12; keep R-series paused.",
            "  Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
            "",
            "",
        ]
    )
    text = HOT.read_text(encoding="utf-8")
    # Update header
    text = re.sub(
        r"^Updated:.*$",
        f"Updated: 2026-07-15 ~{stamp} ICT | HARD PIVOT W12 weekdaygap/absorb; "
        f"cost-ladder diagnostic; R-series densify PAUSED; {status}; GOAL unmet",
        text,
        count=1,
        flags=re.M,
    )
    # Insert after Active Truth header
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
        pnls_a, detail_a, trades_a = probe_weekday_gap_cont(h1)
        pnls_b, detail_b, trades_b = probe_absorb3_reverse(h1)
        ra = pack_result(
            "HYP-FX3-H1-WEEKDAY-D1GAP-CONT-MULTIDAY-001",
            "Tue-Fri D1 gap CONT multi-day RR3",
            pnls_a,
            detail_a,
        )
        rb = pack_result(
            "HYP-FX3-H1-ABSORB3-WICK-REVERSE-001",
            "H1 absorb3 declining-body wick reverse RR2.75",
            pnls_b,
            detail_b,
        )
        book = evaluate_book(trades_a, trades_b)
        results = [ra, rb]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results + [book])
        payload = {
            "schema_version": "hard_pivot_w12_weekdaygap_absorb_offline.v1",
            "generated_at_utc": utc_now(),
            "freeze_sha256": freeze_sha,
            "preregs": preregs,
            "base_cost_usd": BASE_COST,
            "results": results,
            "book": book,
            "any_survivor": any_surv,
            "flags": {
                "R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED": True,
                "W1_W11_DENSIFY_FORBIDDEN": True,
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
                            "pf12": r["haircuts"]["x1"]["pf"],
                            "tpw": r["metrics"]["tpw"],
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
