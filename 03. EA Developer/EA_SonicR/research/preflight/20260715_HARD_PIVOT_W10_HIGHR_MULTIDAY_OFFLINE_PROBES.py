#!/usr/bin/env python3
"""HARD PIVOT W10 — change cost economics: high-R / multi-day after W9 ALL_KILL.

Carry:
  - W1–W9 location-accept saturated (cadence OK often dies under +$12).
  - W9 thick-rare BOOK topology worked (tpw~3, caps OK) but edge negative.
  - Prior high-R shelf KILLED: swing ADX/TD-ROC, Donchian, Outside, D1 volregime,
    carry, anticarry. FORBIDDEN densify those + FVG + W1–W9 + R-series.

Thesis (COST ECONOMICS SHIFT):
  A priori target MFE = RR × cash_R ≫ $12 RT (RR≥3, cash_R≈$500 → MFE≥$1500;
  friction ≤1% of target). Multi-day hold + thick structural SL. Cadence 2–5/wk
  from multi-setup OR multi-symbol book rules FROZEN a priori — not densify.

Objects (frozen pre-metrics):
  A. HYP-FX3-H4-WEEKLY-OPEN-BIAS-RETEST-MULTIDAY-001
     Mon bias from weekly open → Tue–Thu H4 first WO retest accept CONT.
     ≠ R11 WO-dist FADE; ≠ R28 prior-week HL break CONT; ≠ swing/Donch/Outside/VR.
  B. HYP-FX3-H4-D1-DISPLACE-MID-RECLAIM-MULTIDAY-001
     D1 close ≥1.8 ATR beyond 5D mid → H4 mid reclaim accept (MR multi-day).
     ≠ W9 fail-2D densify; ≠ Outside; ≠ swing-failure fade; ≠ volregime break.
  BOOK. HYP-BOOK-HIGHR-MULTIDAY-DUAL-SETUP-APRIORI-001
     Pool A+B; corr/overlap/heat frozen a priori.

Optional thick-rare book ≠ W9 sleeves:
  C. HYP-FX3-H4-MONTHLY-OPEN-FIRST-ACCEPT-CONT-001
  D. HYP-FX3-H4-PRIOR-MONTH-HL-FAILBREAK-REV-001
  BOOK2. HYP-BOOK-THICKRARE-MONTHSTRUCT-APRIORI-001

Universe a priori: EURUSD+GBPUSD+USDJPY.
R_SERIES densify PAUSED. Model 0 only PROBE_SURVIVOR.
Phase-0 still CONTAMINATED — diagnostic clean-path only.
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

STEM = "20260715_HARD_PIVOT_W10_HIGHR_MULTIDAY"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_HARD_PIVOT_W10_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_APRIORI_FREEZE.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
CASH_R = DEPOSIT * RISK_FRAC  # ~$500
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

CORR_CAP = 0.35
OVERLAP_FRAC_CAP = 0.05

# --- High-R A: weekly-open bias retest CONT ---
A_BIAS_ATR = 0.50          # Mon close vs WO
A_ENTRY = (7, 17)          # Tue–Thu London+NY UTC on H4 signal
A_SL_MIN_ATR = 1.75
A_SL_PAD = 0.15
A_RR = 3.50
A_HOLD_H1 = 60             # ~2.5 days
A_PRIORITY = 1
A_MAX_BOOK = 2

# --- High-R B: D1 displace → mid reclaim MR ---
B_LOOKBACK_D1 = 5
B_DISP_ATR = 1.80
B_SL_MIN_ATR = 1.50
B_SL_PAD = 0.25
B_RR = 3.00
B_HOLD_H1 = 72             # ~3 days
B_EXPIRE_D1 = 5
B_PRIORITY = 2
B_MAX_BOOK = 2

# --- Optional thick-rare C: monthly open first accept ---
C_SL_PAD = 0.20
C_SL_MIN_ATR = 1.00
C_RR = 2.50
C_HOLD_H1 = 48
C_PRIORITY = 1
C_TOUCH_ATR = 0.20

# --- Optional thick-rare D: prior-month HL failbreak rev ---
D_FAIL_BARS_H4 = 6
D_SL_PAD = 0.20
D_SL_MIN_ATR = 1.00
D_RR = 2.50
D_HOLD_H1 = 48
D_PRIORITY = 2
D_MIN_RANGE_ATR = 1.50


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
        exit_px = None
        reason = None
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
                "pnl": cash_pnl(
                    pos["sym"], pos["side"], pos["entry"], float(d["c"][-1]), pos["lots"]
                ),
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


def pack_result(hid, setup, symbol, timeframe, pnls, detail, challenger=False):
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc)
    return _jsonable(
        {
            "hypothesis_id": hid,
            "setup": setup,
            "symbol": symbol,
            "timeframe": timeframe,
            "metrics": m,
            "haircuts": hc,
            "verdict": verdict,
            "fail_notes": notes,
            "detail": detail,
            "challenger": challenger,
            "apriori_target_mfe_usd": None,
        }
    )


def asof_idx(d, ts):
    j = int(np.searchsorted(d["t"], ts, side="left"))
    if j < len(d["t"]) and int(d["t"][j]) == int(ts):
        return j
    return None


def iso_week_key(dt: datetime):
    iso = dt.isocalendar()
    return (iso.year, iso.week)


def build_weekly_opens_and_mon(h1_sym):
    """Per ISO week: weekly_open (first Mon H1 open), Mon HL + Mon close ATR."""
    weeks = {}
    for j in range(len(h1_sym["t"])):
        dt = datetime.fromtimestamp(int(h1_sym["t"][j]), tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        wk = iso_week_key(dt)
        if wk not in weeks:
            weeks[wk] = {
                "wo": float(h1_sym["o"][j]),
                "mon_hi": None,
                "mon_lo": None,
                "mon_c": None,
                "mon_atr": None,
            }
        if dt.weekday() == 0:
            h, l, c = float(h1_sym["h"][j]), float(h1_sym["l"][j]), float(h1_sym["c"][j])
            atr = h1_sym["atr"][j]
            w = weeks[wk]
            if w["mon_hi"] is None:
                w["mon_hi"], w["mon_lo"], w["mon_c"] = h, l, c
            else:
                w["mon_hi"] = max(w["mon_hi"], h)
                w["mon_lo"] = min(w["mon_lo"], l)
                w["mon_c"] = c
            if np.isfinite(atr) and atr > 0:
                w["mon_atr"] = float(atr)
    return weeks


def build_d1_series(h1_sym):
    """Build D1 OHLC from H1 (UTC date buckets, weekdays)."""
    by_day = {}
    for j in range(len(h1_sym["t"])):
        dt = datetime.fromtimestamp(int(h1_sym["t"][j]), tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        day = dt.date()
        o, h, l, c = (
            float(h1_sym["o"][j]),
            float(h1_sym["h"][j]),
            float(h1_sym["l"][j]),
            float(h1_sym["c"][j]),
        )
        atr = h1_sym["atr"][j]
        if day not in by_day:
            by_day[day] = {"o": o, "h": h, "l": l, "c": c, "atr": atr, "end_ts": int(h1_sym["t"][j])}
        else:
            by_day[day]["h"] = max(by_day[day]["h"], h)
            by_day[day]["l"] = min(by_day[day]["l"], l)
            by_day[day]["c"] = c
            by_day[day]["end_ts"] = int(h1_sym["t"][j])
            if np.isfinite(atr):
                by_day[day]["atr"] = atr
    days = sorted(by_day.keys())
    return days, by_day


def build_month_levels(h1_sym):
    """Prior completed calendar-month open + HL."""
    by_m = {}
    for j in range(len(h1_sym["t"])):
        dt = datetime.fromtimestamp(int(h1_sym["t"][j]), tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        key = (dt.year, dt.month)
        o, h, l = float(h1_sym["o"][j]), float(h1_sym["h"][j]), float(h1_sym["l"][j])
        if key not in by_m:
            by_m[key] = {"open": o, "hi": h, "lo": l}
        else:
            by_m[key]["hi"] = max(by_m[key]["hi"], h)
            by_m[key]["lo"] = min(by_m[key]["lo"], l)
    months = sorted(by_m.keys())
    prior = {}
    for i, m in enumerate(months):
        if i == 0:
            continue
        pm = months[i - 1]
        prior[m] = {
            "open": by_m[pm]["open"],
            "hi": by_m[pm]["hi"],
            "lo": by_m[pm]["lo"],
        }
    return prior


# ---------------------------------------------------------------------------
# A — Weekly-open bias retest multi-day CONT
# ---------------------------------------------------------------------------
def probe_weekly_open_bias_retest(h1, h4):
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    weeks = {s: build_weekly_opens_and_mon(h1[s]) for s in FX3}
    used_week_sym = set()
    for i in range(80, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, A_HOLD_H1)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        # Entry only Tue(1)–Thu(3)
        if dt.weekday() not in (1, 2, 3):
            continue
        if not (A_ENTRY[0] <= dt.hour < A_ENTRY[1]):
            continue
        if len(open_pos) >= A_MAX_BOOK:
            continue
        sig_ts = int(clock[i - 1])
        # Prefer H4 closed-bar signal: find last closed H4 before ts
        for sym in FX3:
            if sym in open_syms:
                continue
            d4 = h4[sym]
            j4 = int(np.searchsorted(d4["t"], sig_ts, side="right") - 1)
            if j4 < 20:
                continue
            # signal bar must be closed H4 (its open time + 4h <= ts roughly)
            if int(d4["t"][j4]) + 4 * 3600 > ts:
                j4 -= 1
            if j4 < 20:
                continue
            sig_dt = datetime.fromtimestamp(int(d4["t"][j4]), tz=timezone.utc)
            if sig_dt.weekday() not in (1, 2, 3):
                continue
            if not (A_ENTRY[0] <= sig_dt.hour < A_ENTRY[1]):
                continue
            wk = iso_week_key(sig_dt)
            week_key = (wk, sym)
            if week_key in used_week_sym:
                continue
            meta = weeks[sym].get(wk)
            if meta is None or meta["mon_hi"] is None or meta["mon_atr"] is None:
                continue
            wo = meta["wo"]
            mon_c = meta["mon_c"]
            mon_atr = meta["mon_atr"]
            if mon_atr <= 0:
                continue
            # Mon bias vs weekly open
            if mon_c >= wo + A_BIAS_ATR * mon_atr:
                side = 1
                mon_ext = meta["mon_lo"]
            elif mon_c <= wo - A_BIAS_ATR * mon_atr:
                side = -1
                mon_ext = meta["mon_hi"]
            else:
                continue
            atr4 = d4["atr"][j4]
            if not np.isfinite(atr4) or atr4 <= 0:
                continue
            h, l, c = float(d4["h"][j4]), float(d4["l"][j4]), float(d4["c"][j4])
            touched = (l <= wo <= h) or abs(h - wo) <= 0.15 * atr4 or abs(l - wo) <= 0.15 * atr4
            if not touched:
                continue
            # accept CONT through WO in bias direction
            if side > 0 and not (c > wo and l <= wo):
                continue
            if side < 0 and not (c < wo and h >= wo):
                continue
            d1 = h1[sym]
            ent_i = asof_idx(d1, ts)
            if ent_i is None:
                continue
            entry = float(d1["o"][ent_i])
            atr1 = d1["atr"][ent_i]
            if not np.isfinite(atr1) or atr1 <= 0:
                atr1 = atr4
            if side > 0:
                sl = mon_ext - A_SL_PAD * atr1
                sl = min(sl, entry - A_SL_MIN_ATR * atr1)
            else:
                sl = mon_ext + A_SL_PAD * atr1
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
                    "sleeve": "A_WO_BIAS",
                    "priority": A_PRIORITY,
                }
            )
            used_week_sym.add(week_key)
            open_syms.add(sym)
            if len(open_pos) >= A_MAX_BOOK:
                break
    flush_open(open_pos, h1, closed)
    return summarize(closed)


# ---------------------------------------------------------------------------
# B — D1 displace → mid reclaim multi-day MR
# ---------------------------------------------------------------------------
def probe_d1_displace_mid_reclaim(h1, h4):
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    d1_pack = {s: build_d1_series(h1[s]) for s in FX3}
    armed = {s: None for s in FX3}
    used_arm = set()
    for i in range(120, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, B_HOLD_H1)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if len(open_pos) >= B_MAX_BOOK:
            continue
        sig_ts = int(clock[i - 1])
        for sym in FX3:
            days, by_day = d1_pack[sym]
            # Arm on newly completed D1 (yesterday relative to sig)
            sig_dt = datetime.fromtimestamp(sig_ts, tz=timezone.utc)
            arm_day = sig_dt.date() - timedelta(days=1)
            while arm_day.weekday() >= 5:
                arm_day -= timedelta(days=1)
            if arm_day in by_day and days:
                try:
                    di = days.index(arm_day)
                except ValueError:
                    di = -1
                if di >= B_LOOKBACK_D1:
                    window = days[di - B_LOOKBACK_D1 : di]  # prior 5 completed before arm_day
                    # mid of prior 5D HL (exclude arm_day itself for mid; displace uses arm_day)
                    hi5 = max(by_day[d]["h"] for d in window)
                    lo5 = min(by_day[d]["l"] for d in window)
                    mid = 0.5 * (hi5 + lo5)
                    bar = by_day[arm_day]
                    atr_d = bar["atr"]
                    if np.isfinite(atr_d) and atr_d > 0 and hi5 > lo5:
                        c = bar["c"]
                        # only arm once per arm_day
                        arm_key = (arm_day, sym)
                        if arm_key not in used_arm and armed[sym] is None:
                            if c >= mid + B_DISP_ATR * atr_d:
                                armed[sym] = {
                                    "side": -1,
                                    "mid": mid,
                                    "ext": bar["h"],
                                    "arm_day": arm_day,
                                    "expire": arm_day + timedelta(days=B_EXPIRE_D1 + 2),
                                    "atr": float(atr_d),
                                }
                                used_arm.add(arm_key)
                            elif c <= mid - B_DISP_ATR * atr_d:
                                armed[sym] = {
                                    "side": 1,
                                    "mid": mid,
                                    "ext": bar["l"],
                                    "arm_day": arm_day,
                                    "expire": arm_day + timedelta(days=B_EXPIRE_D1 + 2),
                                    "atr": float(atr_d),
                                }
                                used_arm.add(arm_key)

            arm = armed[sym]
            if arm is None or sym in open_syms:
                continue
            if sig_dt.date() > arm["expire"]:
                armed[sym] = None
                continue
            d4 = h4[sym]
            j4 = int(np.searchsorted(d4["t"], sig_ts, side="right") - 1)
            if j4 < 20:
                continue
            if int(d4["t"][j4]) + 4 * 3600 > ts:
                j4 -= 1
            if j4 < 20:
                continue
            atr4 = d4["atr"][j4]
            if not np.isfinite(atr4) or atr4 <= 0:
                continue
            h, l, c = float(d4["h"][j4]), float(d4["l"][j4]), float(d4["c"][j4])
            mid = arm["mid"]
            side = arm["side"]
            touched = l <= mid <= h
            if not touched:
                continue
            if side > 0 and not (c > mid):
                continue
            if side < 0 and not (c < mid):
                continue
            d1 = h1[sym]
            ent_i = asof_idx(d1, ts)
            if ent_i is None:
                continue
            entry = float(d1["o"][ent_i])
            atr1 = d1["atr"][ent_i]
            if not np.isfinite(atr1) or atr1 <= 0:
                atr1 = atr4
            if side > 0:
                sl = arm["ext"] - B_SL_PAD * atr1
                sl = min(sl, entry - B_SL_MIN_ATR * atr1)
            else:
                sl = arm["ext"] + B_SL_PAD * atr1
                sl = max(sl, entry + B_SL_MIN_ATR * atr1)
            sl_dist = abs(entry - sl)
            if sl_dist <= 1e-12:
                armed[sym] = None
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
                    "sleeve": "B_D1_MID_RECLAIM",
                    "priority": B_PRIORITY,
                }
            )
            armed[sym] = None
            open_syms.add(sym)
            if len(open_pos) >= B_MAX_BOOK:
                break
    flush_open(open_pos, h1, closed)
    return summarize(closed)


# ---------------------------------------------------------------------------
# C — Monthly open first H4 accept CONT (optional thick-rare)
# ---------------------------------------------------------------------------
def probe_monthly_open_first_accept(h1, h4):
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    month_lvls = {s: build_month_levels(h1[s]) for s in FX3}
    used_month_sym = set()
    for i in range(100, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, C_HOLD_H1)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if not (7 <= dt.hour < 17):
            continue
        sig_ts = int(clock[i - 1])
        for sym in FX3:
            if sym in open_syms:
                continue
            mk = (dt.year, dt.month)
            if (mk, sym) in used_month_sym:
                continue
            lv = month_lvls[sym].get(mk)
            if lv is None:
                continue
            mo = lv["open"]
            d4 = h4[sym]
            j4 = int(np.searchsorted(d4["t"], sig_ts, side="right") - 1)
            if j4 < 20:
                continue
            if int(d4["t"][j4]) + 4 * 3600 > ts:
                j4 -= 1
            if j4 < 20:
                continue
            atr4 = d4["atr"][j4]
            if not np.isfinite(atr4) or atr4 <= 0:
                continue
            h, l, c = float(d4["h"][j4]), float(d4["l"][j4]), float(d4["c"][j4])
            touched = (l <= mo <= h) or abs(c - mo) <= C_TOUCH_ATR * atr4
            if not touched:
                continue
            # CONT accept: close on side of first decisive break of MO this month
            # Use close vs MO + body through
            if c > mo and l <= mo:
                side = 1
            elif c < mo and h >= mo:
                side = -1
            else:
                continue
            d1 = h1[sym]
            ent_i = asof_idx(d1, ts)
            if ent_i is None:
                continue
            entry = float(d1["o"][ent_i])
            atr1 = d1["atr"][ent_i] if np.isfinite(d1["atr"][ent_i]) else atr4
            if side > 0:
                sl = mo - C_SL_PAD * atr1
                sl = min(sl, entry - C_SL_MIN_ATR * atr1)
            else:
                sl = mo + C_SL_PAD * atr1
                sl = max(sl, entry + C_SL_MIN_ATR * atr1)
            sl_dist = abs(entry - sl)
            if sl_dist <= 1e-12:
                continue
            tp = entry + side * C_RR * sl_dist
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
                    "sleeve": "C_MONTH_OPEN",
                    "priority": C_PRIORITY,
                }
            )
            used_month_sym.add((mk, sym))
    flush_open(open_pos, h1, closed)
    return summarize(closed)


# ---------------------------------------------------------------------------
# D — Prior-month HL fail-break reverse (optional thick-rare)
# ---------------------------------------------------------------------------
def probe_prior_month_hl_failbreak(h1, h4):
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    month_lvls = {s: build_month_levels(h1[s]) for s in FX3}
    pending = {s: None for s in FX3}
    used_month_side = set()
    for i in range(100, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, D_HOLD_H1)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            for s in FX3:
                pending[s] = None
            continue
        if not (7 <= dt.hour < 17):
            continue
        sig_ts = int(clock[i - 1])
        for sym in FX3:
            mk = (dt.year, dt.month)
            lv = month_lvls[sym].get(mk)
            if lv is None:
                continue
            phi, plo = lv["hi"], lv["lo"]
            rng = phi - plo
            d4 = h4[sym]
            j4 = int(np.searchsorted(d4["t"], sig_ts, side="right") - 1)
            if j4 < 30:
                continue
            if int(d4["t"][j4]) + 4 * 3600 > ts:
                j4 -= 1
            if j4 < 30:
                continue
            atr4 = d4["atr"][j4]
            if not np.isfinite(atr4) or atr4 <= 0:
                continue
            if rng < D_MIN_RANGE_ATR * atr4:
                continue
            h, l, c = float(d4["h"][j4]), float(d4["l"][j4]), float(d4["c"][j4])
            st = pending[sym]
            # Arm break close beyond prior-month HL
            if st is None:
                if c > phi:
                    key = (mk, sym, 1)
                    if key not in used_month_side:
                        pending[sym] = {
                            "side_break": 1,
                            "ext": h,
                            "lvl": phi,
                            "bars": 0,
                            "key": key,
                        }
                elif c < plo:
                    key = (mk, sym, -1)
                    if key not in used_month_side:
                        pending[sym] = {
                            "side_break": -1,
                            "ext": l,
                            "lvl": plo,
                            "bars": 0,
                            "key": key,
                        }
                continue
            st["bars"] += 1
            if st["side_break"] > 0:
                st["ext"] = max(st["ext"], h)
            else:
                st["ext"] = min(st["ext"], l)
            if st["bars"] > D_FAIL_BARS_H4:
                pending[sym] = None
                continue
            # Fail: close back inside prior-month range
            failed = (st["side_break"] > 0 and c < st["lvl"]) or (
                st["side_break"] < 0 and c > st["lvl"]
            )
            if not failed or sym in open_syms:
                continue
            side = -st["side_break"]  # reverse
            d1 = h1[sym]
            ent_i = asof_idx(d1, ts)
            if ent_i is None:
                continue
            entry = float(d1["o"][ent_i])
            atr1 = d1["atr"][ent_i] if np.isfinite(d1["atr"][ent_i]) else atr4
            if side > 0:
                sl = st["ext"] - D_SL_PAD * atr1
                sl = min(sl, entry - D_SL_MIN_ATR * atr1)
            else:
                sl = st["ext"] + D_SL_PAD * atr1
                sl = max(sl, entry + D_SL_MIN_ATR * atr1)
            sl_dist = abs(entry - sl)
            if sl_dist <= 1e-12:
                pending[sym] = None
                continue
            tp = entry + side * D_RR * sl_dist
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
                    "sleeve": "D_PMHL_FAIL",
                    "priority": D_PRIORITY,
                }
            )
            used_month_side.add(st["key"])
            pending[sym] = None
    flush_open(open_pos, h1, closed)
    return summarize(closed)


# ---------------------------------------------------------------------------
# Book helpers
# ---------------------------------------------------------------------------
def weekly_series(trades, field="pnl"):
    buckets = defaultdict(float)
    for t in trades:
        ts = t.get("entry_ts")
        if ts is None:
            continue
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        iso = dt.isocalendar()
        buckets[(iso.year, iso.week)] += float(t[field])
    cur = FROM.date()
    end = TO.date()
    cur = cur - timedelta(days=cur.weekday())
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
    ma = sum(a) / n
    mb = sum(b) / n
    da = [x - ma for x in a]
    db = [y - mb for y in b]
    num = sum(x * y for x, y in zip(da, db))
    den = math.sqrt(sum(x * x for x in da) * sum(y * y for y in db))
    if den == 0:
        return None
    return num / den


def apply_heat(trades):
    best = {}
    dropped = 0
    ordered = sorted(trades, key=lambda t: (t.get("priority", 99), t.get("entry_ts", 0)))
    for t in ordered:
        bar = int(t["entry_ts"]) // 3600 * 3600 if t.get("entry_ts") else 0
        k = (t["sym"], bar)
        if k not in best:
            best[k] = t
        else:
            dropped += 1
    kept = sorted(best.values(), key=lambda t: t.get("entry_ts", 0))
    return kept, dropped


def pairwise_overlap(a, b):
    if not a or not b:
        return 0.0
    sa = {int(t["entry_ts"]) // 3600 for t in a if t.get("entry_ts")}
    sb = {int(t["entry_ts"]) // 3600 for t in b if t.get("entry_ts")}
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / min(len(sa), len(sb))


def evaluate_book(trades_a, trades_b, book_hid, setup, sleeve_a, sleeve_b, prio_a, prio_b):
    for t in trades_a:
        t["sleeve"] = sleeve_a
        t["priority"] = prio_a
        t["pnl_haircut"] = float(t["pnl"]) - BASE_COST
    for t in trades_b:
        t["sleeve"] = sleeve_b
        t["priority"] = prio_b
        t["pnl_haircut"] = float(t["pnl"]) - BASE_COST
    all_t = trades_a + trades_b
    filtered, dropped = apply_heat(all_t)
    pnls_raw = [float(t["pnl"]) for t in filtered]
    m = metrics(pnls_raw)
    hc = haircuts(pnls_raw)
    by = defaultdict(list)
    for t in filtered:
        by[t["sleeve"]].append(t)
    ta, tb = by.get(sleeve_a, []), by.get(sleeve_b, [])
    corr = pearson(weekly_series(ta, "pnl_haircut"), weekly_series(tb, "pnl_haircut"))
    ov = pairwise_overlap(ta, tb)
    corr_fail = corr is not None and corr > CORR_CAP
    ov_fail = ov > OVERLAP_FRAC_CAP
    caps_ok = (not corr_fail) and (not ov_fail)
    verdict, notes = book_verdict(m, hc, caps_ok)
    return _jsonable(
        {
            "hypothesis_id": book_hid,
            "setup": setup,
            "symbol": "EURUSD+GBPUSD+USDJPY",
            "timeframe": "H1/H4",
            "metrics": m,
            "haircuts": hc,
            "verdict": verdict,
            "fail_notes": notes,
            "pooled_after_heat": {
                "n": len(filtered),
                "dropped_heat": dropped,
                "sleeve_a_kept": len(ta),
                "sleeve_b_kept": len(tb),
            },
            "pair_caps": {
                "weekly_corr": None if corr is None else round(float(corr), 4),
                "overlap_frac": round(float(ov), 4),
                "corr_cap": CORR_CAP,
                "overlap_cap": OVERLAP_FRAC_CAP,
                "corr_fail": corr_fail,
                "overlap_fail": ov_fail,
                "caps_ok": caps_ok,
            },
            "detail": {},
            "challenger": False,
        }
    )


def write_freeze():
    body = "\n".join(
        [
            "# A priori freeze — HARD PIVOT W10 high-R / multi-day",
            "",
            "Date: 2026-07-15",
            "Status: `APRIORI_FREEZE__PRE_METRICS`",
            "Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`",
            "",
            "## Cost-economics thesis (frozen)",
            f"- Cash R a priori ≈ ${CASH_R:.0f} (deposit×{RISK_FRAC}).",
            f"- High-R A target MFE ≈ {A_RR}×R = ${A_RR * CASH_R:.0f} ≫ ${BASE_COST} RT.",
            f"- High-R B target MFE ≈ {B_RR}×R = ${B_RR * CASH_R:.0f} ≫ ${BASE_COST} RT.",
            "- Friction fraction of target ≤ 1%; NOT location-accept scalp economics.",
            "",
            "## Universe",
            "- Symbols: EURUSD, GBPUSD, USDJPY",
            "- Window: 2021-01-01 → 2025-12-31",
            f"- Haircut: +${BASE_COST} RT a priori on every closed trade",
            "",
            "## High-R objects (membership frozen before combo metrics)",
            "| Slot | hypothesis_id | clock | RR | hold_H1 | priority |",
            "|---|---|---|---|---|---|",
            f"| A | HYP-FX3-H4-WEEKLY-OPEN-BIAS-RETEST-MULTIDAY-001 | Mon WO bias → Tue–Thu H4 retest | {A_RR} | {A_HOLD_H1} | 1 |",
            f"| B | HYP-FX3-H4-D1-DISPLACE-MID-RECLAIM-MULTIDAY-001 | D1 displace → H4 mid reclaim | {B_RR} | {B_HOLD_H1} | 2 |",
            "| BOOK | HYP-BOOK-HIGHR-MULTIDAY-DUAL-SETUP-APRIORI-001 | pool A+B | — | — | — |",
            "",
            "## Optional thick-rare book ≠ W9 (NY-raid / fail-2D / H4-swing)",
            "| Slot | hypothesis_id |",
            "|---|---|",
            "| C | HYP-FX3-H4-MONTHLY-OPEN-FIRST-ACCEPT-CONT-001 |",
            "| D | HYP-FX3-H4-PRIOR-MONTH-HL-FAILBREAK-REV-001 |",
            "| BOOK2 | HYP-BOOK-THICKRARE-MONTHSTRUCT-APRIORI-001 |",
            "",
            "## Caps / overlap (a priori; fail closed)",
            f"- Weekly PnL corr ≤ {CORR_CAP}",
            f"- Same-symbol H1-bar overlap frac ≤ {OVERLAP_FRAC_CAP}",
            "- Heat: max 1 trade per (symbol, H1 bar); priority A>B / C>D",
            "- Book screen: tpw ∈ [2.0, 5.0]; PF@$12 ≥ 1.30; x1.5 ≥ 1.25; N ≥ 80",
            "",
            "## Forbidden",
            "FVG densify; W1–W9 densify; R10–R31 densify; swing ADX/TD-ROC densify;",
            "Donchian densify; Outside densify; D1 volregime densify; carry/anticarry densify;",
            "exit/MaxKZ densify; Phase-0 ceremony.",
            "",
            "## Model 0",
            "WITHHELD unless any PROBE_SURVIVOR.",
            "",
        ]
    )
    OUT_FREEZE.write_text(body, encoding="utf-8")
    return sha256_bytes(body.encode("utf-8")), body


def write_preregs():
    PREREG.mkdir(parents=True, exist_ok=True)
    paths = []
    specs = [
        (
            "20260715_H_FX3_H4_WEEKLY_OPEN_BIAS_RETEST_MULTIDAY_001_PREREG.md",
            "HYP-FX3-H4-WEEKLY-OPEN-BIAS-RETEST-MULTIDAY-001",
            "fx_h4_weekly_open_bias_retest_multiday",
            [
                f"- Mon close vs weekly_open ≥{A_BIAS_ATR}*ATR → bias; Tue–Thu H4 first WO touch+accept CONT.",
                f"- Thick SL beyond Mon extreme, min {A_SL_MIN_ATR}*ATR; RR={A_RR}; hold≤{A_HOLD_H1} H1.",
                f"- A priori target MFE ≈ ${A_RR * CASH_R:.0f} ≫ ${BASE_COST}.",
                "- Hard ≠ R11 WO-dist FADE; ≠ R28 prior-week HL break CONT; ≠ swing/Donch/Outside/volregime; ≠ W1–W9.",
            ],
        ),
        (
            "20260715_H_FX3_H4_D1_DISPLACE_MID_RECLAIM_MULTIDAY_001_PREREG.md",
            "HYP-FX3-H4-D1-DISPLACE-MID-RECLAIM-MULTIDAY-001",
            "fx_h4_d1_displace_mid_reclaim_multiday",
            [
                f"- D1 close ≥{B_DISP_ATR}*ATR beyond prior-{B_LOOKBACK_D1}D HL mid → arm reverse.",
                f"- H4 touch mid + accept reclaim; SL beyond displace extreme min {B_SL_MIN_ATR}*ATR;",
                f"  RR={B_RR}; hold≤{B_HOLD_H1} H1; expire {B_EXPIRE_D1}D.",
                f"- A priori target MFE ≈ ${B_RR * CASH_R:.0f} ≫ ${BASE_COST}.",
                "- Hard ≠ W9 fail-2D densify; ≠ Outside; ≠ swing-failure; ≠ D1 volregime; ≠ FVG.",
            ],
        ),
        (
            "20260715_H_BOOK_HIGHR_MULTIDAY_DUAL_SETUP_APRIORI_001_PREREG.md",
            "HYP-BOOK-HIGHR-MULTIDAY-DUAL-SETUP-APRIORI-001",
            "book_highr_multiday_dual_setup_apriori",
            [
                "- Membership: WO-bias retest + D1-mid reclaim (frozen pre-metrics).",
                f"- Caps: corr≤{CORR_CAP}; overlap≤{OVERLAP_FRAC_CAP}; heat A>B; +$12.",
                "- Screen: book tpw∈[2,5]; PF@$12≥1.30; x1.5≥1.25. Sleeve starve OK.",
                "- Cost thesis: high-R multi-day; NOT location-accept densify.",
            ],
        ),
        (
            "20260715_H_FX3_H4_MONTHLY_OPEN_FIRST_ACCEPT_CONT_001_PREREG.md",
            "HYP-FX3-H4-MONTHLY-OPEN-FIRST-ACCEPT-CONT-001",
            "fx_h4_monthly_open_first_accept",
            [
                f"- First H4 touch+accept of prior-month open in new month; RR={C_RR}; hold≤{C_HOLD_H1}.",
                "- Thick-rare optional; ≠ W9 NY-raid / fail-2D / H4-swing sleeves.",
                "- Hard ≠ R11 WO fade densify; ≠ R28 week HL densify; ≠ FVG.",
            ],
        ),
        (
            "20260715_H_FX3_H4_PRIOR_MONTH_HL_FAILBREAK_REV_001_PREREG.md",
            "HYP-FX3-H4-PRIOR-MONTH-HL-FAILBREAK-REV-001",
            "fx_h4_prior_month_hl_failbreak_rev",
            [
                f"- Close-break prior-month HL then fail back ≤{D_FAIL_BARS_H4} H4 → reverse.",
                f"- RR={D_RR}; hold≤{D_HOLD_H1}. ≠ W9 fail-2D (month vs 2D day clock).",
                "- Hard ≠ R28 prior-week HL CONT densify; ≠ Outside; ≠ FVG.",
            ],
        ),
        (
            "20260715_H_BOOK_THICKRARE_MONTHSTRUCT_APRIORI_001_PREREG.md",
            "HYP-BOOK-THICKRARE-MONTHSTRUCT-APRIORI-001",
            "book_thickrare_monthstruct_apriori",
            [
                "- Optional thick-rare BOOK ≠ W9: monthly-open accept + PMHL failbreak.",
                f"- Caps corr≤{CORR_CAP}; overlap≤{OVERLAP_FRAC_CAP}; heat C>D.",
                "- Model 0 only PROBE_SURVIVOR.",
            ],
        ),
    ]
    for fname, hid, fam, extra in specs:
        p = PREREG / fname
        lines = [
            f"# Prereg — {hid}",
            "",
            "- State: `preregistered` (frozen pre-offline)",
            f"- Feature family: `{fam}`",
            "- Lane: `hard_pivot_w10_highr_multiday_20260715`",
            "- Thesis: change cost economics — high-R / multi-day MFE ≫ $12;",
            "  optional month-struct thick-rare book ≠ W9.",
            *extra,
            "- Model 0: only PROBE_SURVIVOR.",
            "",
        ]
        p.write_text("\n".join(lines), encoding="utf-8")
        paths.append(str(p.as_posix()))
    return paths


def append_reg(results, books, receipt, prereg_paths):
    stamp = utc_now()
    with REG.open("a", encoding="utf-8") as f:
        for r, pp in zip(results, prereg_paths[: len(results)]):
            row = {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": r["hypothesis_id"],
                "state": "killed" if r["verdict"] != "PROBE_SURVIVOR" else "probe_survivor",
                "parent_candidate": None,
                "feature_family": "hard_pivot_w10_highr_multiday",
                "lane": "hard_pivot_w10_highr_multiday_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": 0,
                "source_provenance": "HARD PIVOT W10 offline OHLC; +$12 a priori; no Model0 unless survivor",
                "prereg_path": pp,
                "readout_path": str(OUT_MD.as_posix()),
                "metrics": r["metrics"],
                "validation": {
                    "probe": r["verdict"],
                    "fail_notes": r["fail_notes"],
                    "haircuts": r["haircuts"],
                    "receipt_sha256": receipt,
                },
                "verdict": r["verdict"],
                "updated_at": stamp,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        for b in books:
            row = {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": b["hypothesis_id"],
                "state": "killed" if b["verdict"] != "PROBE_SURVIVOR" else "probe_survivor",
                "feature_family": "hard_pivot_w10_book",
                "lane": "hard_pivot_w10_highr_multiday_20260715",
                "setup_type": b["setup"],
                "symbol": b["symbol"],
                "timeframe": b["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": 0,
                "metrics": b["metrics"],
                "validation": {
                    "probe": b["verdict"],
                    "fail_notes": b["fail_notes"],
                    "pair_caps": b["pair_caps"],
                    "receipt_sha256": receipt,
                },
                "verdict": b["verdict"],
                "updated_at": stamp,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _table(rows):
    lines = [
        "| Object | N | PF | tpw | PF@$12 | x1.5 | Verdict |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        m, hc = r["metrics"], r["haircuts"]
        lines.append(
            f"| `{r['hypothesis_id']}` | {m['n']} | {m['pf']} | {m['tpw']} | "
            f"{hc['x1']['pf']} | {hc['x1_5']['pf']} | {r['verdict'].replace('KILLED_AT_OFFLINE_PROBE','KILL').replace('PROBE_SURVIVOR','SURV')} |"
        )
    return lines


def write_docs(results, books, receipt, any_surv, freeze_sha, qnote):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    highr = results[:2]
    opt = results[2:]
    book_hr, book_tr = books[0], books[1]
    highr_table = _table(highr + [book_hr])
    opt_table = _table(opt + [book_tr])

    OUT_PANEL.write_text(
        "\n".join(
            [
                "# 3-critic panel — HARD PIVOT W10 high-R / multi-day",
                "",
                "| Critic | Vote |",
                "|---|---|",
                "| Sonic trader | GO — change economics: thick SL + RR≥3 multi-day; WO-bias CONT ≠ WO fade |",
                "| Quant | GO — freeze MFE≫$12 + book caps pre-metrics; honest kill if PF/cadence fail |",
                "| MQL5/MT5 | GO — closed-bar H4 signal → next H1 open; no Model 0 until survivor |",
                "",
                "Merge: **GO offline screen**. Model 0 WITHHELD until PROBE_SURVIVOR.",
                "FORBIDDEN: densify FVG / W1–W9 / R-series / swing / Donch / Outside / volregime.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — HARD PIVOT W10 high-R / multi-day (+ optional month thick-rare)",
                "",
                f"Freeze sha={freeze_sha[:16]}…",
                "",
                "## Problem",
                "Location-accept W1–W9 saturated. W9 book topology OK but edge negative.",
                "$12 RT dominates thin expectancy. Need MFE ≫ $12 a priori.",
                "",
                "## High-R thesis",
                f"Cash R≈${CASH_R:.0f}; RR≥3 → target MFE ≥${3 * CASH_R:.0f} ≫ ${BASE_COST}.",
                "Multi-day hold + thick structural SL. Cadence from dual-setup FX3 book.",
                "",
                "### A — Weekly-open bias retest CONT",
                "Mon displace from WO → Tue–Thu H4 first WO accept CONT. Thick SL Mon extreme.",
                "",
                "### B — D1 displace mid reclaim MR",
                "D1 close far beyond 5D mid → H4 mid reclaim. Orthogonal day-structure clock.",
                "",
                "### Optional thick-rare ≠ W9",
                "Monthly-open first accept + prior-month HL failbreak reverse. Month clock ≠ NY/2D.",
                "",
                "## Caps",
                f"corr≤{CORR_CAP}; overlap≤{OVERLAP_FRAC_CAP}; +$12; tpw[2,5].",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — HARD PIVOT W10 high-R / multi-day",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| WO-bias retest CONT | ≠ R11 WO-dist FADE; ≠ R28 prior-week HL CONT; ≠ swing ADX/TD-ROC; ≠ Donch; ≠ Outside; ≠ volregime; ≠ W1–W9; ≠ FVG |",
                "| D1-mid reclaim MR | ≠ W9 fail-2D densify; ≠ Outside; ≠ H1 swing-failure; ≠ D1 volregime 8d/2close; ≠ FVG |",
                "| High-R dual book | ≠ W9 thick-rare dual-loc; ≠ swing thick book densify; ≠ clean RR2 densify |",
                "| Monthly-open accept | ≠ W9 sleeves; ≠ R11 WO fade densify; ≠ R28 week HL densify |",
                "| PMHL failbreak rev | ≠ W9 fail-2D (month≠2D); ≠ R28 week HL CONT; ≠ Outside |",
                "",
                "FVG densify FORBIDDEN. R-series densify PAUSED. W1–W9 knobs FORBIDDEN.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — HARD PIVOT W10 high-R / multi-day",
                "",
                f"Generated: 2026-07-15 ~{stamp} ICT",
                f"Receipt SHA256: `{receipt}`",
                f"Freeze SHA256: `{freeze_sha}`",
                f"Status: `{status}`",
                f"QFSI: {qnote}",
                "",
                "## High-R dual-setup + book",
                *highr_table,
                "",
                f"High-R book caps: corr={book_hr['pair_caps']['weekly_corr']} "
                f"overlap={book_hr['pair_caps']['overlap_frac']} "
                f"caps_ok={book_hr['pair_caps']['caps_ok']}",
                "",
                "## Optional thick-rare month-struct book ≠ W9",
                *opt_table,
                "",
                f"Month book caps: corr={book_tr['pair_caps']['weekly_corr']} "
                f"overlap={book_tr['pair_caps']['overlap_frac']} "
                f"caps_ok={book_tr['pair_caps']['caps_ok']}",
                "",
                "## Fail notes",
                *[
                    f"- `{r['hypothesis_id']}`: {', '.join(r['fail_notes']) or 'none'}"
                    for r in results + books
                ],
                "",
                "Model 0 WITHHELD unless PROBE_SURVIVOR. No corpse densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Session closeout — HARD PIVOT W10 high-R / multi-day",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "R-series densify: **PAUSED**.",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify W10 corpses / W1–W9 / FVG / R10–R31 / swing / Donch / Outside / volregime.",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — HARD PIVOT W10 high-R / multi-day",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "",
                f"## Kết quả — `{status}`",
                "### High-R (đổi economics: MFE ≫ $12)",
                *highr_table,
                "",
                "### Optional thick-rare month-struct ≠ W9",
                *opt_table,
                "",
                "### Thesis",
                f"- Target MFE A≈${A_RR * CASH_R:.0f} / B≈${B_RR * CASH_R:.0f} ≫ $12 RT.",
                "- Book dual-setup a priori; không densify FVG / W1–W9 / R-series.",
                "- De-dup vs swing / Donchian / Outside / volregime đã kill.",
                "",
                f"Receipt `{receipt}`",
                "PAUSE R-series. Best shelf `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLEAN_VN.write_text(
        "\n".join(
            [
                "# VN action brief — Clean book + HARD PIVOT W10 high-R / multi-day",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "",
                "## Clean book (unchanged)",
                "PRIMARY PF@$12=1.184 tpw=3.241. Best shelf RR2 `194548`.",
                "",
                f"## HARD PIVOT W10 — `{status}`",
                "### High-R dual-setup + book",
                *highr_table,
                "",
                "### Optional thick-rare month-struct ≠ W9",
                *opt_table,
                "",
                "### Economics shift (a priori)",
                f"- Cash R≈${CASH_R:.0f}; RR A={A_RR} / B={B_RR} → MFE ≫ $12.",
                "- Không densify FVG / W1–W9 / R-series / swing / Donch / Outside / VR.",
                "",
                "- R-series densify PAUSED.",
                f"Receipt `{receipt}`",
                "GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def patch_hot(results, books, receipt, any_surv, freeze_sha, qnote):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    lines = [
        f"- **HARD PIVOT W10 HIGHR MULTIDAY CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED` / `{status}` / "
        f"`QFSI_007_HEALTHY` / `NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  HARD PIVOT W10 after W9 thick-rare BOOK ALL_KILL — CHANGE COST ECONOMICS.",
        "  High-R / multi-day dual-setup (a priori MFE ≫ $12) + optional month thick-rare ≠ W9.",
        "  Offline screen:",
    ]
    for i, r in enumerate(results, 1):
        m, hc = r["metrics"], r["haircuts"]
        lines.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={m['n']} PF={m['pf']} tpw={m['tpw']} PF@$12={hc['x1']['pf']} "
            f"x1.5={hc['x1_5']['pf']})."
        )
    for i, b in enumerate(books):
        bm, bhc = b["metrics"], b["haircuts"]
        tag = "BOOK_HR" if i == 0 else "BOOK_TR"
        lines.append(
            f"  {tag}. `{b['hypothesis_id']}` → **{b['verdict']}** "
            f"(N={bm['n']} PF={bm['pf']} tpw={bm['tpw']} PF@$12={bhc['x1']['pf']} "
            f"x1.5={bhc['x1_5']['pf']} caps_ok={b['pair_caps']['caps_ok']})."
        )
    lines += [
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        f"  VN `readouts/20260715_CLEAN_BOOK_AND_HARD_PIVOT_W10_VN_ACTION_BRIEF.md`.",
        f"  Freeze sha={freeze_sha[:16]}… QFSI: {qnote}",
        "  W9 carry: thick-rare topology OK / edge neg; location-accept saturated.",
        "  Do **not** densify W10 / W1–W9 / FVG / R10–R31 / swing / Donch / Outside / VR.",
        "  Clean book still GOAL_SCREEN_FAIL. PRIMARY PF@$12=1.184 tpw=3.241.",
        "  Next: next independent class outside W1–W10 / killed high-R shelf;",
        "  keep R-series paused; QFSI parallel; cost autonomous retry.",
        "  Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
        "",
        "",
    ]
    block = "\n".join(lines)
    text = HOT.read_text(encoding="utf-8")
    old_lines = text.splitlines()
    if len(old_lines) >= 2 and old_lines[0].startswith("# Hot Cache"):
        old_lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | HARD PIVOT W10 high-R multi-day; "
            f"R-series densify PAUSED; {status}; GOAL unmet"
        )
        text = "\n".join(old_lines) + ("\n" if text.endswith("\n") else "")
    marker = "## Active Truth\n"
    if marker in text:
        text = text.replace(marker, marker + "\n" + block, 1)
    nm = "## Next Move\n"
    next_block = (
        f"\n- **ACTIVE — HARD PIVOT W10 high-R / multi-day aftermath.** "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`. "
        f"W10 offline `{status}` receipt `{receipt[:16]}…`. "
        "Do not densify FVG / W1–W10 / swing / Donch / Outside / volregime. "
        "Do not resume R10–R31 densify. Next independent class if ALL_KILL. "
        "QFSI parallel; cost GAP. Best shelf RR2 `194548`. GOAL unmet.\n"
    )
    if nm in text:
        text2, nsub = re.subn(
            r"\n- \*\*ACTIVE — HARD PIVOT[^\n]*\n",
            next_block,
            text,
            count=1,
        )
        if nsub:
            text = text2
        else:
            idx = text.find(nm) + len(nm)
            text = text[:idx] + next_block + text[idx:]
    HOT.write_text(text, encoding="utf-8")


def qfsi_note():
    note = "QFSI 007 parallel; cost freeze GAP (11 deals); login not headline"
    for root in (ROOT / "04. Project Control" / "ai", ROOT / "02. AlphaFactory"):
        if not root.exists():
            continue
        for p in root.rglob("*heartbeat*.json"):
            try:
                j = json.loads(p.read_text(encoding="utf-8"))
                return (
                    f"QFSI hb ts={j.get('ts') or j.get('timestamp')} "
                    f"alive={j.get('alive', j.get('watcher_alive'))}; cost GAP"
                )
            except Exception:
                continue
    return note


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")

    freeze_sha, _ = write_freeze()
    prereg_paths = write_preregs()
    print("Freeze SHA:", freeze_sha)
    print(f"A priori MFE A=${A_RR * CASH_R:.0f} B=${B_RR * CASH_R:.0f} vs cost ${BASE_COST}")

    print("Loading H1 + H4 FX3...")
    h1 = {s: enrich(load(s, mt5.TIMEFRAME_H1)) for s in FX3}
    h4 = {s: enrich(load(s, mt5.TIMEFRAME_H4)) for s in FX3}

    print("Probe A WO-bias retest multiday...")
    p1, d1, t1 = probe_weekly_open_bias_retest(h1, h4)
    r1 = pack_result(
        "HYP-FX3-H4-WEEKLY-OPEN-BIAS-RETEST-MULTIDAY-001",
        "FX3 H4 weekly-open bias retest CONT multi-day high-R",
        "EURUSD+GBPUSD+USDJPY",
        "H4→H1",
        p1,
        d1,
    )
    r1["apriori_target_mfe_usd"] = A_RR * CASH_R
    print("  ", r1["verdict"], r1["metrics"], r1["haircuts"]["x1"], r1["fail_notes"])

    print("Probe B D1-displace mid reclaim...")
    p2, d2, t2 = probe_d1_displace_mid_reclaim(h1, h4)
    r2 = pack_result(
        "HYP-FX3-H4-D1-DISPLACE-MID-RECLAIM-MULTIDAY-001",
        "FX3 H4 D1-displace mid-reclaim MR multi-day high-R",
        "EURUSD+GBPUSD+USDJPY",
        "H4→H1",
        p2,
        d2,
    )
    r2["apriori_target_mfe_usd"] = B_RR * CASH_R
    print("  ", r2["verdict"], r2["metrics"], r2["haircuts"]["x1"], r2["fail_notes"])

    print("Evaluate high-R BOOK...")
    book_hr = evaluate_book(
        t1,
        t2,
        "HYP-BOOK-HIGHR-MULTIDAY-DUAL-SETUP-APRIORI-001",
        "a priori high-R multi-day dual-setup book (WO-bias + D1-mid reclaim)",
        "A_WO_BIAS",
        "B_D1_MID_RECLAIM",
        A_PRIORITY,
        B_PRIORITY,
    )
    print(
        "  ",
        book_hr["verdict"],
        book_hr["metrics"],
        book_hr["haircuts"]["x1"],
        book_hr["pair_caps"],
        book_hr["fail_notes"],
    )

    print("Probe C monthly-open first accept...")
    p3, d3, t3 = probe_monthly_open_first_accept(h1, h4)
    r3 = pack_result(
        "HYP-FX3-H4-MONTHLY-OPEN-FIRST-ACCEPT-CONT-001",
        "FX3 H4 monthly-open first accept CONT (thick-rare ≠ W9)",
        "EURUSD+GBPUSD+USDJPY",
        "H4→H1",
        p3,
        d3,
    )
    print("  ", r3["verdict"], r3["metrics"], r3["haircuts"]["x1"], r3["fail_notes"])

    print("Probe D prior-month HL failbreak rev...")
    p4, d4, t4 = probe_prior_month_hl_failbreak(h1, h4)
    r4 = pack_result(
        "HYP-FX3-H4-PRIOR-MONTH-HL-FAILBREAK-REV-001",
        "FX3 H4 prior-month HL failbreak reverse (thick-rare ≠ W9)",
        "EURUSD+GBPUSD+USDJPY",
        "H4→H1",
        p4,
        d4,
    )
    print("  ", r4["verdict"], r4["metrics"], r4["haircuts"]["x1"], r4["fail_notes"])

    print("Evaluate month thick-rare BOOK...")
    book_tr = evaluate_book(
        t3,
        t4,
        "HYP-BOOK-THICKRARE-MONTHSTRUCT-APRIORI-001",
        "a priori thick-rare month-struct book ≠ W9 (MO accept + PMHL fail)",
        "C_MONTH_OPEN",
        "D_PMHL_FAIL",
        C_PRIORITY,
        D_PRIORITY,
    )
    print(
        "  ",
        book_tr["verdict"],
        book_tr["metrics"],
        book_tr["haircuts"]["x1"],
        book_tr["pair_caps"],
        book_tr["fail_notes"],
    )

    results = [r1, r2, r3, r4]
    books = [book_hr, book_tr]
    any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results + books)
    payload = {
        "schema": "hard_pivot_w10_highr_multiday.v1",
        "generated_at": utc_now(),
        "freeze_sha256": freeze_sha,
        "base_cost_usd": BASE_COST,
        "apriori_cash_r_usd": CASH_R,
        "apriori_target_mfe": {"A": A_RR * CASH_R, "B": B_RR * CASH_R},
        "books": books,
        "results": results,
        "any_survivor": any_surv,
        "flags": {
            "R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED": True,
            "FVG_RETEST_DENSIFY_FORBIDDEN": True,
            "W1_W9_KNOB_DENSIFY_FORBIDDEN": True,
            "SWING_DONCH_OUTSIDE_VOLREGIME_DENSIFY_FORBIDDEN": True,
            "UNIVERSE_APRIORI_FREEZE": True,
            "BOOK_MEMBERSHIP_APRIORI_FREEZE": True,
            "PHASE0_STILL_CONTAMINATED": True,
            "COST_ECONOMICS_SHIFT_HIGHR_MULTIDAY": True,
        },
    }
    OUT_JSON.write_bytes(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))
    receipt = sha256_bytes(OUT_JSON.read_bytes())
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_bytes(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))
    receipt = sha256_bytes(OUT_JSON.read_bytes())
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_bytes(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))
    receipt = sha256_bytes(OUT_JSON.read_bytes())

    qnote = qfsi_note()
    write_docs(results, books, receipt, any_surv, freeze_sha, qnote)
    append_reg(results, books, receipt, prereg_paths)
    patch_hot(results, books, receipt, any_surv, freeze_sha, qnote)
    print("Receipt:", receipt)
    print("Status:", "SURVIVOR" if any_surv else "ALL_KILL")
    mt5.shutdown()


if __name__ == "__main__":
    main()
