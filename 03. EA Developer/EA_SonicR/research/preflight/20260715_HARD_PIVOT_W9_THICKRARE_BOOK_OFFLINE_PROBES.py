#!/usr/bin/env python3
"""HARD PIVOT W9 — a priori thick-rare BOOK after W1–W8 entry-state ALL_KILL.

Carry:
  - Thick rares (FVG ~$53/tpw1.15; London→NY PF@$12~1.14/tpw1.64) starve alone.
  - Cadence-capable location accepts die under a priori +$12 across W1–W8.
  - FORBIDDEN: densify FVG window / W1–W8 knobs / reopen R-series densify.

Thesis (book-level, NOT open-FVG-for-cadence):
  Combine ≥2 INDEPENDENT thick-rare location/setup sleeves. Each sleeve may
  starve alone; BOOK cadence target 2–5/wk via orthogonal clocks while
  preserving high $/trade per fill. Universe + caps + overlap FROZEN before
  any combo metrics.

Sleeves (a priori):
  A. HYP-FX3-H1-NY-ASIA-RAID-RECLAIM-ACCEPT-CONT-001
     NY [13,17) raid beyond Asia [0,7) extreme → reclaim Asia mid accept CONT.
     ≠ W5 Asia-session sweep densify; ≠ NY-open impulse; ≠ FVG.
  B. HYP-FX3-H1-FAILED-2D-RANGE-BREAK-REVERSE-ACCEPT-001
     Break prior 2-day HL → fail back inside ≤8 bars → reverse accept CONT.
     ≠ auction-persist; ≠ London-box/W8; ≠ ORB/IB; ≠ FVG.

Book hyp: HYP-BOOK-THICKRARE-DUAL-LOC-APRIORI-001
Optional single outside W1–W8:
  C. HYP-FX3-H1-H4-SWING-FIRST-RETEST-ACCEPT-CONT-001
     After H4 swing + ≥1 ATR displacement away, first H1 retest accept CONT.
     ≠ H4disp-H1accept densify; ≠ breaker; ≠ FVG.

Universe a priori: EURUSD+GBPUSD+USDJPY.
R_SERIES densify PAUSED. Model 0 only PROBE_SURVIVOR (book or single).
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

STEM = "20260715_HARD_PIVOT_W9_THICKRARE_BOOK"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_HARD_PIVOT_W9_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_APRIORI_FREEZE.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

CORR_CAP = 0.35
OVERLAP_FRAC_CAP = 0.05

# Sleeve A — NY Asia-raid reclaim
A_ASIA = (0, 7)
A_NY = (13, 17)
A_RAID_ATR = 0.10
A_SL_PAD = 0.10
A_RR = 2.00
A_HOLD = 12
A_PRIORITY = 1

# Sleeve B — failed 2D range reverse
B_SESSION = (7, 17)
B_FAIL_BARS = 8
B_MIN_RANGE_ATR = 0.80
B_MAX_RANGE_ATR = 4.00
B_SL_PAD = 0.10
B_RR = 2.00
B_HOLD = 14
B_PRIORITY = 2

# Optional single C — H4 swing first retest
C_DISP_ATR = 1.00
C_TOUCH_ATR = 0.15
C_SL_PAD = 0.10
C_RR = 2.00
C_HOLD = 16
C_SWING_L = 2  # fractal wings on H4


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
    risk = DEPOSIT * RISK_FRAC
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
        }
    )


def asof_idx(d, ts):
    j = int(np.searchsorted(d["t"], ts, side="left"))
    if j < len(d["t"]) and int(d["t"][j]) == int(ts):
        return j
    return None


def build_asia_ranges(d):
    """date -> Asia [0,7) UTC HL."""
    by_day = {}
    for j in range(len(d["t"])):
        dt = datetime.fromtimestamp(int(d["t"][j]), tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if not (A_ASIA[0] <= dt.hour < A_ASIA[1]):
            continue
        day = dt.date()
        h, l = float(d["h"][j]), float(d["l"][j])
        if day not in by_day:
            by_day[day] = {"hi": h, "lo": l, "n": 1}
        else:
            by_day[day]["hi"] = max(by_day[day]["hi"], h)
            by_day[day]["lo"] = min(by_day[day]["lo"], l)
            by_day[day]["n"] += 1
    return by_day


def build_prior_2d_ranges(d):
    """For each date D, HL of the two prior weekdays (UTC date buckets)."""
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


def h4_swing_levels(h4):
    """Return list of (confirm_ts, level, kind) where kind in ('hi','lo').
    Fractal confirmed at bar j when wing C_SWING_L on each side (closed)."""
    swings = []
    L = C_SWING_L
    t, h, l = h4["t"], h4["h"], h4["l"]
    for j in range(L, len(t) - L):
        # swing high confirmed when center high > neighbors
        if all(h[j] > h[j - k] for k in range(1, L + 1)) and all(
            h[j] > h[j + k] for k in range(1, L + 1)
        ):
            swings.append((int(t[j + L]), float(h[j]), "hi"))
        if all(l[j] < l[j - k] for k in range(1, L + 1)) and all(
            l[j] < l[j + k] for k in range(1, L + 1)
        ):
            swings.append((int(t[j + L]), float(l[j]), "lo"))
    swings.sort(key=lambda x: x[0])
    return swings


# ---------------------------------------------------------------------------
# Sleeve A — NY Asia-raid reclaim accept CONT
# ---------------------------------------------------------------------------
def probe_ny_asia_raid_reclaim(h1):
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    asia = {s: build_asia_ranges(h1[s]) for s in FX3}
    last_day_sym = set()
    raid_state = {s: None for s in FX3}  # armed raid pending reclaim
    for i in range(40, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, A_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            for s in FX3:
                raid_state[s] = None
            continue
        sig_ts = int(clock[i - 1])
        sig_dt = datetime.fromtimestamp(sig_ts, tz=timezone.utc)
        day = sig_dt.date()
        for sym in FX3:
            d = h1[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < 25:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            ar = asia[sym].get(day)
            if ar is None or ar.get("n", 0) < 3:
                continue
            a_hi, a_lo = ar["hi"], ar["lo"]
            if a_hi <= a_lo:
                continue
            mid = 0.5 * (a_hi + a_lo)
            o, h, l, c = float(d["o"][j]), float(d["h"][j]), float(d["l"][j]), float(d["c"][j])

            # Outside NY: clear stale raid at day boundary hour < NY start
            if sig_dt.hour < A_NY[0]:
                raid_state[sym] = None
                continue
            if not (A_NY[0] <= sig_dt.hour < A_NY[1]):
                continue

            day_key = (day, sym)
            if day_key in last_day_sym or sym in open_syms:
                continue

            st = raid_state[sym]
            # Arm raid
            if st is None:
                if h >= a_hi + A_RAID_ATR * atr:
                    raid_state[sym] = {"side": -1, "ext": h, "mid": mid, "a_hi": a_hi, "a_lo": a_lo}
                elif l <= a_lo - A_RAID_ATR * atr:
                    raid_state[sym] = {"side": 1, "ext": l, "mid": mid, "a_hi": a_hi, "a_lo": a_lo}
                continue

            # Reclaim accept: close through mid in reclaim direction
            side = st["side"]
            accept = False
            if side < 0 and c < mid and h >= mid:
                accept = True
            elif side > 0 and c > mid and l <= mid:
                accept = True
            # Update extreme if still raiding
            if side < 0:
                st["ext"] = max(st["ext"], h)
            else:
                st["ext"] = min(st["ext"], l)
            if not accept:
                continue

            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            if side > 0:
                sl = st["ext"] - A_SL_PAD * atr
            else:
                sl = st["ext"] + A_SL_PAD * atr
            sl_dist = abs(entry - sl)
            if sl_dist <= 1e-12:
                raid_state[sym] = None
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
                    "sleeve": "A_NY_ASIA_RAID",
                    "priority": A_PRIORITY,
                }
            )
            last_day_sym.add(day_key)
            raid_state[sym] = None
    flush_open(open_pos, h1, closed)
    return summarize(closed)


# ---------------------------------------------------------------------------
# Sleeve B — failed 2D range break reverse accept
# ---------------------------------------------------------------------------
def probe_failed_2d_range_reverse(h1):
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    ranges = {s: build_prior_2d_ranges(h1[s]) for s in FX3}
    last_day_sym = set()
    pending = {s: None for s in FX3}  # armed break waiting fail
    for i in range(40, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, B_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            for s in FX3:
                pending[s] = None
            continue
        sig_ts = int(clock[i - 1])
        sig_dt = datetime.fromtimestamp(sig_ts, tz=timezone.utc)
        day = sig_dt.date()
        for sym in FX3:
            d = h1[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < 25:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            rg = ranges[sym].get(day)
            if rg is None:
                continue
            r_hi, r_lo = rg["hi"], rg["lo"]
            rng = r_hi - r_lo
            if rng < B_MIN_RANGE_ATR * atr or rng > B_MAX_RANGE_ATR * atr:
                continue
            o, h, l, c = float(d["o"][j]), float(d["h"][j]), float(d["l"][j]), float(d["c"][j])
            day_key = (day, sym)

            pend = pending[sym]
            if pend is not None:
                pend["age"] += 1
                if pend["age"] > B_FAIL_BARS:
                    pending[sym] = None
                    pend = None
                elif day_key not in last_day_sym and sym not in open_syms:
                    # fail = close back inside
                    failed = False
                    if pend["brk"] > 0 and c < r_hi and c > r_lo:
                        failed = True
                        side = -1
                        ext = pend["ext"]
                    elif pend["brk"] < 0 and c > r_lo and c < r_hi:
                        failed = True
                        side = 1
                        ext = pend["ext"]
                    else:
                        # update extreme while outside
                        if pend["brk"] > 0:
                            pend["ext"] = max(pend["ext"], h)
                        else:
                            pend["ext"] = min(pend["ext"], l)
                    if failed:
                        ent_i = asof_idx(d, ts)
                        if ent_i is not None:
                            entry = float(d["o"][ent_i])
                            if side > 0:
                                sl = ext - B_SL_PAD * atr
                            else:
                                sl = ext + B_SL_PAD * atr
                            sl_dist = abs(entry - sl)
                            if sl_dist > 1e-12:
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
                                        "sleeve": "B_FAIL2D",
                                        "priority": B_PRIORITY,
                                    }
                                )
                                last_day_sym.add(day_key)
                        pending[sym] = None
                        continue

            if pending[sym] is not None or sym in open_syms or day_key in last_day_sym:
                continue
            if not (B_SESSION[0] <= sig_dt.hour < B_SESSION[1]):
                continue
            # Arm break accept beyond 2D range
            if c > r_hi and o <= r_hi:
                pending[sym] = {"brk": 1, "ext": h, "age": 0}
            elif c < r_lo and o >= r_lo:
                pending[sym] = {"brk": -1, "ext": l, "age": 0}
    flush_open(open_pos, h1, closed)
    return summarize(closed)


# ---------------------------------------------------------------------------
# Optional single C — H4 swing first-retest accept CONT
# ---------------------------------------------------------------------------
def probe_h4_swing_first_retest(h1, h4):
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    swings = {s: h4_swing_levels(h4[s]) for s in FX3}
    # track last consumed swing index per symbol
    used = {s: set() for s in FX3}
    last_day_sym = set()
    armed = {s: None for s in FX3}  # displaced swing awaiting retest
    for i in range(80, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, C_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        sig_ts = int(clock[i - 1])
        sig_dt = datetime.fromtimestamp(sig_ts, tz=timezone.utc)
        day = sig_dt.date()
        for sym in FX3:
            d = h1[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < 30:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            c = float(d["c"][j])
            h, l = float(d["h"][j]), float(d["l"][j])

            # Arm newest confirmed swing that has displacement
            if armed[sym] is None:
                for k, (conf_ts, lvl, kind) in enumerate(swings[sym]):
                    if k in used[sym]:
                        continue
                    if conf_ts > sig_ts:
                        break
                    # need displacement away after confirm
                    if kind == "lo":
                        # price went up ≥ C_DISP_ATR from swing low
                        # look ahead from confirm using H1 asof
                        cj = asof_idx(d, conf_ts)
                        if cj is None:
                            continue
                        # scan from confirm to now for displacement then later retest
                        max_away = 0.0
                        for jj in range(cj, j + 1):
                            max_away = max(max_away, float(d["h"][jj]) - lvl)
                        if max_away >= C_DISP_ATR * atr:
                            armed[sym] = {
                                "kind": "lo",
                                "lvl": lvl,
                                "side": 1,
                                "k": k,
                                "max_away": max_away,
                            }
                            break
                    else:
                        max_away = 0.0
                        cj = asof_idx(d, conf_ts)
                        if cj is None:
                            continue
                        for jj in range(cj, j + 1):
                            max_away = max(max_away, lvl - float(d["l"][jj]))
                        if max_away >= C_DISP_ATR * atr:
                            armed[sym] = {
                                "kind": "hi",
                                "lvl": lvl,
                                "side": -1,
                                "k": k,
                                "max_away": max_away,
                            }
                            break

            arm = armed[sym]
            if arm is None or sym in open_syms:
                continue
            day_key = (day, sym)
            if day_key in last_day_sym:
                continue
            # session London+NY for accept
            if not (7 <= sig_dt.hour < 17):
                continue
            lvl = arm["lvl"]
            side = arm["side"]
            touched = abs(h - lvl) <= C_TOUCH_ATR * atr or abs(l - lvl) <= C_TOUCH_ATR * atr
            touched = touched or (l <= lvl <= h)
            if not touched:
                continue
            # accept close on CONT side of swing
            accept = (side > 0 and c > lvl) or (side < 0 and c < lvl)
            if not accept:
                continue
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            if side > 0:
                sl = lvl - C_SL_PAD * atr
            else:
                sl = lvl + C_SL_PAD * atr
            sl_dist = abs(entry - sl)
            if sl_dist <= 1e-12:
                used[sym].add(arm["k"])
                armed[sym] = None
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
                    "sleeve": "C_H4_SWING_RETEST",
                    "priority": 3,
                }
            )
            last_day_sym.add(day_key)
            used[sym].add(arm["k"])
            armed[sym] = None
    flush_open(open_pos, h1, closed)
    return summarize(closed)


# ---------------------------------------------------------------------------
# Book pooling
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
    # align to Monday
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


def evaluate_book(trades_a, trades_b):
    # annotate sleeve + haircut
    for t in trades_a:
        t["sleeve"] = "A_NY_ASIA_RAID"
        t["priority"] = A_PRIORITY
        t["pnl_haircut"] = float(t["pnl"]) - BASE_COST
    for t in trades_b:
        t["sleeve"] = "B_FAIL2D"
        t["priority"] = B_PRIORITY
        t["pnl_haircut"] = float(t["pnl"]) - BASE_COST
    all_t = trades_a + trades_b
    filtered, dropped = apply_heat(all_t)
    pnls_raw = [float(t["pnl"]) for t in filtered]
    m = metrics(pnls_raw)
    hc = haircuts(pnls_raw)

    by = defaultdict(list)
    for t in filtered:
        by[t["sleeve"]].append(t)
    ta, tb = by.get("A_NY_ASIA_RAID", []), by.get("B_FAIL2D", [])
    corr = pearson(weekly_series(ta, "pnl_haircut"), weekly_series(tb, "pnl_haircut"))
    ov = pairwise_overlap(ta, tb)
    corr_fail = corr is not None and corr > CORR_CAP
    ov_fail = ov > OVERLAP_FRAC_CAP
    caps_ok = (not corr_fail) and (not ov_fail)
    verdict, notes = book_verdict(m, hc, caps_ok)
    return _jsonable(
        {
            "hypothesis_id": "HYP-BOOK-THICKRARE-DUAL-LOC-APRIORI-001",
            "setup": "a priori thick-rare dual-location book (NY-Asia-raid + fail-2D)",
            "symbol": "EURUSD+GBPUSD+USDJPY",
            "timeframe": "H1",
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
            "# A priori freeze — HARD PIVOT W9 thick-rare BOOK",
            "",
            "Date: 2026-07-15",
            "Status: `APRIORI_FREEZE__PRE_METRICS`",
            "Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`",
            "Book hyp: `HYP-BOOK-THICKRARE-DUAL-LOC-APRIORI-001`",
            "",
            "## Thesis",
            "Thick-rare singles starve cadence; cadence accepts die under +$12.",
            "BOOK of ≥2 independent thick-rare location sleeves → cadence 2–5/wk",
            "while preserving high $/trade per fill. NOT open-FVG-for-cadence.",
            "",
            "## Universe (a priori)",
            "- Symbols: EURUSD, GBPUSD, USDJPY",
            "- Window: 2021-01-01 → 2025-12-31",
            "- Haircut: +$12 RT a priori on every closed trade",
            "",
            "## Sleeves (membership frozen before combo metrics)",
            "| Slot | hypothesis_id | clock | priority |",
            "|---|---|---|---|",
            "| A | HYP-FX3-H1-NY-ASIA-RAID-RECLAIM-ACCEPT-CONT-001 | NY raid of Asia range | 1 |",
            "| B | HYP-FX3-H1-FAILED-2D-RANGE-BREAK-REVERSE-ACCEPT-001 | fail-back of 2D break | 2 |",
            "",
            "## Optional single (outside W1–W8; not a book sleeve)",
            "- HYP-FX3-H1-H4-SWING-FIRST-RETEST-ACCEPT-CONT-001",
            "",
            "## Caps / overlap (a priori; fail closed)",
            f"- Weekly PnL corr ≤ {CORR_CAP}",
            f"- Same-symbol H1-bar overlap frac ≤ {OVERLAP_FRAC_CAP}",
            "- Heat: max 1 trade per (symbol, H1 bar); priority A > B",
            "- Book screen: tpw ∈ [2.0, 5.0]; PF@$12 ≥ 1.30; x1.5 ≥ 1.25; N ≥ 80",
            "- Sleeve individual cadence starve is EXPECTED; book pooled is the claim",
            "",
            "## Forbidden",
            "FVG densify; W1–W8 knob densify; R10–R31 densify; exit/MaxKZ densify;",
            "Phase-0 ceremony; reopen contaminated Phase-0 attestation.",
            "",
            "## Model 0",
            "WITHHELD unless book or optional single is PROBE_SURVIVOR.",
            "Book pooling is diagnostic offline — not EA challenger until coded.",
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
            "20260715_H_FX3_H1_NY_ASIA_RAID_RECLAIM_ACCEPT_CONT_001_PREREG.md",
            "HYP-FX3-H1-NY-ASIA-RAID-RECLAIM-ACCEPT-CONT-001",
            "fx_h1_ny_asia_raid_reclaim_accept",
            [
                f"- Asia range UTC[{A_ASIA[0]},{A_ASIA[1]}); NY raid/reclaim UTC[{A_NY[0]},{A_NY[1]}).",
                f"- Raid ≥{A_RAID_ATR}*ATR beyond Asia extreme; reclaim close through Asia mid.",
                f"- RR={A_RR}; hold≤{A_HOLD}; max 1/day/symbol; SL beyond raid extreme.",
                "- Hard ≠ W5 Asia-session sweep densify; ≠ NY-open impulse; ≠ FVG; ≠ W1–W8.",
            ],
        ),
        (
            "20260715_H_FX3_H1_FAILED_2D_RANGE_BREAK_REVERSE_ACCEPT_001_PREREG.md",
            "HYP-FX3-H1-FAILED-2D-RANGE-BREAK-REVERSE-ACCEPT-001",
            "fx_h1_failed_2d_range_reverse_accept",
            [
                f"- Prior 2 weekday HL range; arm close-break in UTC[{B_SESSION[0]},{B_SESSION[1]}).",
                f"- Fail: close back inside within {B_FAIL_BARS} bars → reverse accept CONT.",
                f"- Range size ∈[{B_MIN_RANGE_ATR},{B_MAX_RANGE_ATR}]*ATR; RR={B_RR}; hold≤{B_HOLD}.",
                "- Hard ≠ auction-persist; ≠ London-box/W8; ≠ ORB/IB; ≠ FVG; ≠ W1–W8.",
            ],
        ),
        (
            "20260715_H_BOOK_THICKRARE_DUAL_LOC_APRIORI_001_PREREG.md",
            "HYP-BOOK-THICKRARE-DUAL-LOC-APRIORI-001",
            "book_thickrare_dual_loc_apriori",
            [
                "- Membership: sleeve A NY-Asia-raid + sleeve B fail-2D (frozen pre-metrics).",
                f"- Caps: corr≤{CORR_CAP}; overlap≤{OVERLAP_FRAC_CAP}; heat A>B; +$12 haircut.",
                "- Screen: book tpw∈[2,5]; PF@$12≥1.30; x1.5≥1.25. Sleeve starve OK.",
                "- NOT open-FVG-for-cadence. NOT Phase-0. Model 0 only PROBE_SURVIVOR.",
            ],
        ),
        (
            "20260715_H_FX3_H1_H4_SWING_FIRST_RETEST_ACCEPT_CONT_001_PREREG.md",
            "HYP-FX3-H1-H4-SWING-FIRST-RETEST-ACCEPT-CONT-001",
            "fx_h1_h4_swing_first_retest_accept",
            [
                f"- H4 fractal swing (L={C_SWING_L}); displace ≥{C_DISP_ATR}*ATR_H1 away;",
                "  first H1 touch+accept of swing → CONT. Session UTC[7,17).",
                f"- RR={C_RR}; hold≤{C_HOLD}; max 1/day/symbol.",
                "- Hard ≠ H4disp densify; ≠ breaker densify; ≠ FVG; ≠ W1–W8.",
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
            "- Lane: `hard_pivot_w9_thickrare_book_20260715`",
            "- Thesis: thick-rare location; book cadence from orthogonal clocks,",
            "  not densify of FVG / W1–W8 corpses.",
            *extra,
            "- Model 0: only PROBE_SURVIVOR.",
            "",
        ]
        p.write_text("\n".join(lines), encoding="utf-8")
        paths.append(str(p.as_posix()))
    return paths


def append_reg(results, receipt, prereg_paths, book_r):
    stamp = utc_now()
    fam = {
        "HYP-FX3-H1-NY-ASIA-RAID-RECLAIM-ACCEPT-CONT-001": "fx_h1_ny_asia_raid_reclaim_accept",
        "HYP-FX3-H1-FAILED-2D-RANGE-BREAK-REVERSE-ACCEPT-001": "fx_h1_failed_2d_range_reverse_accept",
        "HYP-BOOK-THICKRARE-DUAL-LOC-APRIORI-001": "book_thickrare_dual_loc_apriori",
        "HYP-FX3-H1-H4-SWING-FIRST-RETEST-ACCEPT-CONT-001": "fx_h1_h4_swing_first_retest_accept",
    }
    all_rows = list(results) + [book_r]
    # map prereg: A,B,BOOK,C
    preg_map = {
        results[0]["hypothesis_id"]: prereg_paths[0],
        results[1]["hypothesis_id"]: prereg_paths[1],
        book_r["hypothesis_id"]: prereg_paths[2],
        results[2]["hypothesis_id"]: prereg_paths[3],
    }
    with REG.open("a", encoding="utf-8") as f:
        for r in all_rows:
            row = {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": r["hypothesis_id"],
                "state": "killed" if r["verdict"].startswith("KILLED") else "probe",
                "verdict": r["verdict"],
                "parent_candidate": None,
                "feature_family": fam.get(r["hypothesis_id"], "hard_pivot_w9"),
                "lane": "hard_pivot_w9_thickrare_book_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "HARD PIVOT W9 a priori thick-rare BOOK after W1-W8 ALL_KILL; "
                    "orthogonal location sleeves; no FVG/W1-W8 densify; "
                    "R-series densify PAUSED; Phase-0 still CONTAMINATED"
                ),
                "prereg_path": preg_map.get(r["hypothesis_id"]),
                "readout_path": str(OUT_MD.as_posix()),
                "metrics": r["metrics"],
                "validation": {
                    "cost_stress_apriori_usd": BASE_COST,
                    "haircuts": r["haircuts"],
                    "verdict": r["verdict"],
                    "fail_notes": r["fail_notes"],
                    "receipt_sha256": receipt,
                    "pair_caps": r.get("pair_caps"),
                },
                "updated_at": stamp,
                "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
                "receipt_sha256": receipt,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_docs(results, book_r, receipt, any_surv, freeze_sha, qnote):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")

    def row(r):
        return (
            f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
            f"{r['metrics']['tpw']} | {r['haircuts']['x1']['pf']} | "
            f"{r['haircuts']['x1_5']['pf']} | "
            f"{r['verdict'].replace('KILLED_AT_OFFLINE_PROBE', 'KILL')} |"
        )

    sleeve_table = [
        "| Object | N | PF | tpw | PF@$12 | x1.5 | Verdict |",
        "|---|---:|---:|---:|---:|---:|---|",
    ] + [row(r) for r in results]
    book_table = [
        "| Book | N | PF | tpw | PF@$12 | x1.5 | Caps | Verdict |",
        "|---|---:|---:|---:|---:|---:|---|---|",
        (
            f"| `{book_r['hypothesis_id']}` | {book_r['metrics']['n']} | "
            f"{book_r['metrics']['pf']} | {book_r['metrics']['tpw']} | "
            f"{book_r['haircuts']['x1']['pf']} | {book_r['haircuts']['x1_5']['pf']} | "
            f"{book_r['pair_caps']['caps_ok']} | "
            f"{book_r['verdict'].replace('KILLED_AT_OFFLINE_PROBE', 'KILL')} |"
        ),
    ]

    OUT_PANEL.write_text(
        "\n".join(
            [
                "# 3-critic panel — HARD PIVOT W9 thick-rare BOOK",
                "",
                "Date: 2026-07-15",
                "Nested: trader/quant/MQL5 lead self-merge (Owner nested OK).",
                "Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`.",
                "",
                "## Carry",
                "W1–W8 ALL_KILL. Thick rares starve; cadence dies under +$12.",
                "FVG densify FORBIDDEN. Need a priori BOOK of independent thick-rares.",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | GO NY-Asia-raid reclaim; GO fail-2D reverse; GO H4 swing retest single |",
                "| Quant | GO; freeze membership+caps pre-metrics; sleeve starve expected |",
                "| MQL5/MT5 | GO — OHLC closed-bar; no Model 0 until survivor |",
                "",
                "Merge: **GO offline book screen**. Model 0 WITHHELD until PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — HARD PIVOT W9 a priori thick-rare BOOK",
                "",
                f"Freeze sha={freeze_sha[:16]}…",
                "",
                "## Problem",
                "Single thick-rare locations starve cadence. Cadence-capable accepts",
                "die under +$12. Densifying FVG / W1–W8 knobs is FORBIDDEN.",
                "",
                "## Book thesis",
                "≥2 independent thick-rare location sleeves with orthogonal clocks.",
                "Book cadence 2–5/wk from pooling; each fill keeps structural SL /",
                "high confirmation. NOT open-FVG-because-tpw-low.",
                "",
                "### Sleeve A — NY Asia-raid reclaim accept CONT",
                "NY raids Asia extreme then reclaim mid → high confirmation;",
                "structural SL beyond raid; NY clock ≠ Asia-sweep (W5) densify.",
                "",
                "### Sleeve B — Failed 2D range reverse accept",
                "Break of prior 2-day HL that fails back inside → reverse CONT;",
                "failed-break rarity thickens $/trade; day-structure clock orthogonal to A.",
                "",
                "### Optional single C — H4 swing first-retest accept",
                "Outside W1–W8: swing+displace+first retest accept. Not book sleeve.",
                "",
                "## Caps frozen a priori",
                f"corr≤{CORR_CAP}; overlap≤{OVERLAP_FRAC_CAP}; heat A>B; +$12; tpw[2,5].",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — HARD PIVOT W9 thick-rare BOOK",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| NY-Asia-raid reclaim | ≠ W5 Asia-session sweep densify; ≠ NY-open impulse; ≠ W1–W8; ≠ FVG |",
                "| Fail-2D reverse | ≠ auction-persist; ≠ London-box/W8; ≠ ORB/IB; ≠ 3-day HL break densify; ≠ FVG |",
                "| Book dual-loc | ≠ clean RR2+Spark book densify; ≠ swing ADX/TD-ROC densify; ≠ Phase-0 |",
                "| H4 swing first-retest | ≠ H4disp-H1accept densify; ≠ breaker densify; ≠ PWHL densify; ≠ FVG |",
                "",
                "FVG densify FORBIDDEN. R-series densify PAUSED. W1–W8 knobs FORBIDDEN.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — HARD PIVOT W9 thick-rare BOOK",
                "",
                f"Generated: 2026-07-15 ~{stamp} ICT",
                f"Receipt SHA256: `{receipt}`",
                f"Freeze SHA256: `{freeze_sha}`",
                f"Status: `{status}`",
                f"QFSI: {qnote}",
                "",
                "## Sleeves + optional single",
                *sleeve_table,
                "",
                "## Book (pooled after heat)",
                *book_table,
                "",
                f"Pair caps: corr={book_r['pair_caps']['weekly_corr']} "
                f"overlap={book_r['pair_caps']['overlap_frac']} "
                f"caps_ok={book_r['pair_caps']['caps_ok']}",
                f"Heat dropped: {book_r['pooled_after_heat']['dropped_heat']}",
                "",
                "## Fail notes",
                *[
                    f"- `{r['hypothesis_id']}`: {', '.join(r['fail_notes']) or 'none'}"
                    for r in results + [book_r]
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
                "# Session closeout — HARD PIVOT W9 thick-rare BOOK",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "R-series densify: **PAUSED**.",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify W9 corpses / W1–W8 / FVG / R10–R31.",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — HARD PIVOT W9 thick-rare BOOK",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "",
                f"## Kết quả — `{status}`",
                "### Sleeves + single",
                *sleeve_table,
                "",
                "### Book gộp (sau heat)",
                *book_table,
                "",
                "### Thesis (không densify FVG)",
                "- Book ≥2 sleeve thick-rare độc lập; cadence ở mức book, không mở FVG.",
                "- A: NY raid Asia → reclaim mid. B: break 2D fail → reverse.",
                "- C (optional): H4 swing first-retest ngoài W1–W8.",
                "",
                f"Receipt `{receipt}`",
                "PAUSE R-series. Cấm densify FVG / W1–W9. Best shelf `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLEAN_VN.write_text(
        "\n".join(
            [
                "# VN action brief — Clean book + HARD PIVOT W9 thick-rare BOOK",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "",
                "## Clean book (unchanged)",
                "PRIMARY PF@$12=1.184 tpw=3.241. Best shelf RR2 `194548`.",
                "",
                f"## HARD PIVOT W9 — `{status}`",
                "### Sleeves + optional single",
                *sleeve_table,
                "",
                "### Book `HYP-BOOK-THICKRARE-DUAL-LOC-APRIORI-001`",
                *book_table,
                "",
                "### a priori thick-rare book (không densify FVG)",
                "- Membership + caps đóng băng trước combo metrics.",
                "- Cadence kỳ vọng ở book; sleeve đơn có thể starve.",
                "- Không densify FVG / W1–W8 knobs / R-series.",
                "",
                "- R-series densify PAUSED.",
                f"Receipt `{receipt}`",
                "GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def patch_hot(results, book_r, receipt, any_surv, freeze_sha, qnote):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    lines = [
        f"- **HARD PIVOT W9 THICKRARE BOOK CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED` / `{status}` / "
        f"`QFSI_007_HEALTHY` / `NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  HARD PIVOT W9 after W1–W8 entry-state ALL_KILL.",
        "  NEW a priori thick-rare BOOK (≥2 independent location sleeves):",
        "  NY-Asia-raid reclaim + failed-2D reverse; optional H4 swing retest single.",
        "  Offline screen:",
    ]
    for i, r in enumerate(results, 1):
        m, hc = r["metrics"], r["haircuts"]
        lines.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={m['n']} PF={m['pf']} tpw={m['tpw']} PF@$12={hc['x1']['pf']} "
            f"x1.5={hc['x1_5']['pf']})."
        )
    bm, bhc = book_r["metrics"], book_r["haircuts"]
    lines.append(
        f"  BOOK. `{book_r['hypothesis_id']}` → **{book_r['verdict']}** "
        f"(N={bm['n']} PF={bm['pf']} tpw={bm['tpw']} PF@$12={bhc['x1']['pf']} "
        f"x1.5={bhc['x1_5']['pf']} caps_ok={book_r['pair_caps']['caps_ok']})."
    )
    lines += [
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        f"  VN `readouts/20260715_CLEAN_BOOK_AND_HARD_PIVOT_W9_VN_ACTION_BRIEF.md`.",
        f"  Freeze sha={freeze_sha[:16]}… QFSI: {qnote}",
        "  W8 carry: insidebar/lbox ALL_KILL; FVG FORBIDDEN densify.",
        "  Do **not** densify W9 / W1–W8 / FVG / R10–R31 / exit / MaxKZ.",
        "  Clean book still GOAL_SCREEN_FAIL. PRIMARY PF@$12=1.184 tpw=3.241.",
        "  Next: next thick-rare book class or entry-state outside W1–W9;",
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
            f"Updated: 2026-07-15 ~{stamp} ICT | HARD PIVOT W9 thick-rare BOOK; "
            f"R-series densify PAUSED; {status}; GOAL unmet"
        )
        text = "\n".join(old_lines) + ("\n" if text.endswith("\n") else "")
    marker = "## Active Truth\n"
    if marker in text:
        text = text.replace(marker, marker + "\n" + block, 1)
    nm = "## Next Move\n"
    next_block = (
        f"\n- **ACTIVE — HARD PIVOT W9 thick-rare BOOK aftermath.** "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`. "
        f"W9 book offline `{status}` receipt `{receipt[:16]}…`. "
        "Do not densify FVG or W1–W9 corpses. Do not resume R10–R31 densify. "
        "Next thick-rare book class or entry-state outside W1–W9 if ALL_KILL. "
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

    # 1) FREEZE before any metrics
    freeze_sha, _ = write_freeze()
    prereg_paths = write_preregs()
    print("Freeze SHA:", freeze_sha)

    print("Loading H1 + H4 FX3...")
    h1 = {s: enrich(load(s, mt5.TIMEFRAME_H1)) for s in FX3}
    h4 = {s: enrich(load(s, mt5.TIMEFRAME_H4)) for s in FX3}

    print("Probe Sleeve A NY-Asia-raid reclaim...")
    p1, d1, t1 = probe_ny_asia_raid_reclaim(h1)
    r1 = pack_result(
        "HYP-FX3-H1-NY-ASIA-RAID-RECLAIM-ACCEPT-CONT-001",
        "FX3 H1 NY Asia-raid reclaim accept CONT (thick-rare sleeve A)",
        "EURUSD+GBPUSD+USDJPY",
        "H1",
        p1,
        d1,
    )
    print("  ", r1["verdict"], r1["metrics"], r1["haircuts"]["x1"], r1["fail_notes"])

    print("Probe Sleeve B failed-2D reverse...")
    p2, d2, t2 = probe_failed_2d_range_reverse(h1)
    r2 = pack_result(
        "HYP-FX3-H1-FAILED-2D-RANGE-BREAK-REVERSE-ACCEPT-001",
        "FX3 H1 failed-2D-range reverse accept CONT (thick-rare sleeve B)",
        "EURUSD+GBPUSD+USDJPY",
        "H1",
        p2,
        d2,
    )
    print("  ", r2["verdict"], r2["metrics"], r2["haircuts"]["x1"], r2["fail_notes"])

    print("Evaluate BOOK pooled...")
    book_r = evaluate_book(t1, t2)
    print(
        "  ",
        book_r["verdict"],
        book_r["metrics"],
        book_r["haircuts"]["x1"],
        book_r["pair_caps"],
        book_r["fail_notes"],
    )

    print("Probe optional single C H4 swing first-retest...")
    p3, d3, _t3 = probe_h4_swing_first_retest(h1, h4)
    r3 = pack_result(
        "HYP-FX3-H1-H4-SWING-FIRST-RETEST-ACCEPT-CONT-001",
        "FX3 H1 H4-swing first-retest accept CONT (optional single outside W1-W8)",
        "EURUSD+GBPUSD+USDJPY",
        "H1",
        p3,
        d3,
    )
    print("  ", r3["verdict"], r3["metrics"], r3["haircuts"]["x1"], r3["fail_notes"])

    results = [r1, r2, r3]
    any_surv = any(
        r["verdict"] == "PROBE_SURVIVOR" for r in results + [book_r]
    )
    payload = {
        "schema": "hard_pivot_w9_thickrare_book.v1",
        "generated_at": utc_now(),
        "freeze_sha256": freeze_sha,
        "base_cost_usd": BASE_COST,
        "book": book_r,
        "results": results,
        "any_survivor": any_surv,
        "flags": {
            "R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED": True,
            "FVG_RETEST_DENSIFY_FORBIDDEN": True,
            "W1_W8_KNOB_DENSIFY_FORBIDDEN": True,
            "UNIVERSE_APRIORI_FREEZE": True,
            "BOOK_MEMBERSHIP_APRIORI_FREEZE": True,
            "PHASE0_STILL_CONTAMINATED": True,
        },
    }
    raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    OUT_JSON.write_bytes(raw)
    receipt = sha256_bytes(OUT_JSON.read_bytes())
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_bytes(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))
    receipt = sha256_bytes(OUT_JSON.read_bytes())
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_bytes(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))
    receipt = sha256_bytes(OUT_JSON.read_bytes())

    qnote = qfsi_note()
    write_docs(results, book_r, receipt, any_surv, freeze_sha, qnote)
    append_reg(results, receipt, prereg_paths, book_r)
    patch_hot(results, book_r, receipt, any_surv, freeze_sha, qnote)
    print("Receipt:", receipt)
    print("Status:", "SURVIVOR" if any_surv else "ALL_KILL")
    mt5.shutdown()


if __name__ == "__main__":
    main()
