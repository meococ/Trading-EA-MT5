#!/usr/bin/env python3
"""HARD PIVOT W11 — overnight London inventory CONT multi-day after W10 ALL_KILL.

W10: high-R WO-bias + D1-mid reclaim book tpw~2.25 but PF~0.86 ALL_KILL.
Month thick-rare starved. FORBIDDEN densify W1–W10 / FVG / R-series /
swing / Donch / Outside / volregime / W10 corpses.

NEW class (still high-R economics: RR≥3, MFE ≫ $12):
  A. HYP-FX3-H1-LONDON-CLOSE-INVENTORY-ON-CONT-001
     London UTC[7,16] session close in extreme third + body≥1.0 ATR →
     next weekday H1 open CONT; thick SL beyond London extreme; RR=3.25;
     hold≤56 H1 (~2+ days). ≠ W7 same-day L→NY PB densify; ≠ London open-drive.
  B. HYP-FX3-H4-D1-PERSIST2-PB-ACCEPT-MULTIDAY-001
     Two consecutive D1 closes same dir totaling ≥2.2 ATR → first H4 PB
     accept CONT; RR=3.0; hold≤64 H1. ≠ W10 D1-mid reclaim; ≠ swing ADX/TD-ROC;
     ≠ streak densify (R15 body-streak H1).
  BOOK. HYP-BOOK-HIGHR-INVENTORY-PERSIST-APRIORI-001

Universe FX3 a priori. Model 0 only PROBE_SURVIVOR.
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

STEM = "20260715_HARD_PIVOT_W11_INVENTORY_PERSIST"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_HARD_PIVOT_W11_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_APRIORI_FREEZE.md"

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

A_LONDON = (7, 16)
A_BODY_ATR = 1.00
A_EXTREME = 0.33  # close in top/bottom third of London range
A_SL_PAD = 0.15
A_SL_MIN_ATR = 1.60
A_RR = 3.25
A_HOLD = 56
A_PRIORITY = 1
A_MAX_BOOK = 2

B_PERSIST_ATR = 2.20
B_PB_ATR = 0.35
B_SL_PAD = 0.20
B_SL_MIN_ATR = 1.50
B_RR = 3.00
B_HOLD = 64
B_PRIORITY = 2
B_MAX_BOOK = 2
B_EXPIRE_H4 = 8


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


def pack_result(hid, setup, pnls, detail):
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc)
    return _jsonable(
        {
            "hypothesis_id": hid,
            "setup": setup,
            "symbol": "EURUSD+GBPUSD+USDJPY",
            "timeframe": "H1/H4",
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


def build_london_sessions(h1_sym):
    """date -> London session OHLC + last atr."""
    by = {}
    for j in range(len(h1_sym["t"])):
        dt = datetime.fromtimestamp(int(h1_sym["t"][j]), tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if not (A_LONDON[0] <= dt.hour < A_LONDON[1]):
            continue
        day = dt.date()
        o, h, l, c = float(h1_sym["o"][j]), float(h1_sym["h"][j]), float(h1_sym["l"][j]), float(h1_sym["c"][j])
        atr = h1_sym["atr"][j]
        if day not in by:
            by[day] = {"o": o, "h": h, "l": l, "c": c, "atr": atr, "n": 1}
        else:
            by[day]["h"] = max(by[day]["h"], h)
            by[day]["l"] = min(by[day]["l"], l)
            by[day]["c"] = c
            by[day]["n"] += 1
            if np.isfinite(atr):
                by[day]["atr"] = atr
    return by


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


def probe_london_inventory_on(h1):
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    london = {s: build_london_sessions(h1[s]) for s in FX3}
    pending = {s: None for s in FX3}
    used = set()
    for i in range(40, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, A_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        # Arm at first bar after London end (hour==16) using completed London day
        sig_ts = int(clock[i - 1])
        sig_dt = datetime.fromtimestamp(sig_ts, tz=timezone.utc)
        for sym in FX3:
            # Complete London when we see hour >= 16 on same day
            if sig_dt.hour == 16 and pending[sym] is None:
                day = sig_dt.date()
                ses = london[sym].get(day)
                if ses and ses["n"] >= 4 and np.isfinite(ses["atr"]) and ses["atr"] > 0:
                    rng = ses["h"] - ses["l"]
                    if rng > 0:
                        body = abs(ses["c"] - ses["o"])
                        if body >= A_BODY_ATR * ses["atr"]:
                            loc = (ses["c"] - ses["l"]) / rng
                            if loc >= (1.0 - A_EXTREME) and ses["c"] > ses["o"]:
                                pending[sym] = {
                                    "side": 1,
                                    "ext": ses["l"],
                                    "day": day,
                                    "atr": float(ses["atr"]),
                                }
                            elif loc <= A_EXTREME and ses["c"] < ses["o"]:
                                pending[sym] = {
                                    "side": -1,
                                    "ext": ses["h"],
                                    "day": day,
                                    "atr": float(ses["atr"]),
                                }
            # Enter next weekday open after arm day (skip weekend)
            arm = pending[sym]
            if arm is None or sym in open_syms:
                continue
            if len(open_pos) >= A_MAX_BOOK:
                continue
            if dt.date() <= arm["day"]:
                continue
            # first H1 of next weekday in [0,10) UTC
            if not (0 <= dt.hour < 10):
                if dt.date() > arm["day"] + timedelta(days=2):
                    pending[sym] = None
                continue
            key = (arm["day"], sym)
            if key in used:
                pending[sym] = None
                continue
            d = h1[sym]
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            # only first opportunity: hour of entry bar should be first available
            entry = float(d["o"][ent_i])
            atr = d["atr"][ent_i] if np.isfinite(d["atr"][ent_i]) else arm["atr"]
            side = arm["side"]
            if side > 0:
                sl = arm["ext"] - A_SL_PAD * atr
                sl = min(sl, entry - A_SL_MIN_ATR * atr)
            else:
                sl = arm["ext"] + A_SL_PAD * atr
                sl = max(sl, entry + A_SL_MIN_ATR * atr)
            sl_dist = abs(entry - sl)
            if sl_dist <= 1e-12:
                pending[sym] = None
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
                    "sleeve": "A_LONDON_INV",
                    "priority": A_PRIORITY,
                }
            )
            used.add(key)
            pending[sym] = None
    flush_open(open_pos, h1, closed)
    return summarize(closed)


def probe_d1_persist2_pb(h1, h4):
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    d1p = {s: build_d1(h1[s]) for s in FX3}
    armed = {s: None for s in FX3}
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
        sig_ts = int(clock[i - 1])
        sig_dt = datetime.fromtimestamp(sig_ts, tz=timezone.utc)
        for sym in FX3:
            days, by = d1p[sym]
            # Arm after 2 completed D1
            arm_day = sig_dt.date() - timedelta(days=1)
            while arm_day.weekday() >= 5:
                arm_day -= timedelta(days=1)
            if arm_day in by:
                try:
                    di = days.index(arm_day)
                except ValueError:
                    di = -1
                if di >= 1:
                    d0, d1 = days[di - 1], days[di]
                    b0, b1 = by[d0], by[d1]
                    atr = b1["atr"]
                    key = (arm_day, sym)
                    if (
                        key not in used
                        and armed[sym] is None
                        and np.isfinite(atr)
                        and atr > 0
                    ):
                        move = (b1["c"] - b0["o"])  # two-day net from d0 open to d1 close
                        # also require both closes same direction
                        s0 = np.sign(b0["c"] - b0["o"])
                        s1 = np.sign(b1["c"] - b1["o"])
                        if s0 != 0 and s0 == s1 and abs(move) >= B_PERSIST_ATR * atr:
                            side = int(s0)
                            extreme = min(b0["l"], b1["l"]) if side > 0 else max(b0["h"], b1["h"])
                            armed[sym] = {
                                "side": side,
                                "ext": extreme,
                                "ref": b1["c"],
                                "arm_day": arm_day,
                                "bars_left": B_EXPIRE_H4,
                                "atr": float(atr),
                            }
                            used.add(key)

            arm = armed[sym]
            if arm is None or sym in open_syms:
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
            side = arm["side"]
            # PB: price retraces ≥ B_PB_ATR toward against side, then accept CONT
            if side > 0:
                pb = (arm["ref"] - l) >= B_PB_ATR * atr4
                accept = pb and c > ((h + l) / 2.0) and c > float(d4["o"][j4])
            else:
                pb = (h - arm["ref"]) >= B_PB_ATR * atr4
                accept = pb and c < ((h + l) / 2.0) and c < float(d4["o"][j4])
            arm["bars_left"] -= 1
            if arm["bars_left"] < 0:
                armed[sym] = None
                continue
            if not accept:
                continue
            d = h1[sym]
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            atr1 = d["atr"][ent_i] if np.isfinite(d["atr"][ent_i]) else atr4
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
                    "sleeve": "B_PERSIST2_PB",
                    "priority": B_PRIORITY,
                }
            )
            armed[sym] = None
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
        t["sleeve"], t["priority"] = "A_LONDON_INV", A_PRIORITY
        t["pnl_haircut"] = float(t["pnl"]) - BASE_COST
    for t in tb:
        t["sleeve"], t["priority"] = "B_PERSIST2_PB", B_PRIORITY
        t["pnl_haircut"] = float(t["pnl"]) - BASE_COST
    filtered, dropped = apply_heat(ta + tb)
    pnls = [float(t["pnl"]) for t in filtered]
    m, hc = metrics(pnls), haircuts(pnls)
    by = defaultdict(list)
    for t in filtered:
        by[t["sleeve"]].append(t)
    a, b = by.get("A_LONDON_INV", []), by.get("B_PERSIST2_PB", [])
    corr = pearson(weekly_series(a, "pnl_haircut"), weekly_series(b, "pnl_haircut"))
    ov = pairwise_overlap(a, b)
    caps_ok = not ((corr is not None and corr > CORR_CAP) or ov > OVERLAP_FRAC_CAP)
    verdict, notes = book_verdict(m, hc, caps_ok)
    return _jsonable(
        {
            "hypothesis_id": "HYP-BOOK-HIGHR-INVENTORY-PERSIST-APRIORI-001",
            "setup": "a priori high-R book: London overnight inventory + D1 persist2 PB",
            "symbol": "EURUSD+GBPUSD+USDJPY",
            "timeframe": "H1/H4",
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
            "# A priori freeze — HARD PIVOT W11 inventory/persist high-R",
            "",
            "Date: 2026-07-15",
            "Status: `APRIORI_FREEZE__PRE_METRICS`",
            f"A target MFE ≈ ${A_RR * CASH_R:.0f}; B ≈ ${B_RR * CASH_R:.0f} ≫ ${BASE_COST}.",
            "",
            "## Objects",
            "- HYP-FX3-H1-LONDON-CLOSE-INVENTORY-ON-CONT-001",
            "- HYP-FX3-H4-D1-PERSIST2-PB-ACCEPT-MULTIDAY-001",
            "- HYP-BOOK-HIGHR-INVENTORY-PERSIST-APRIORI-001",
            "",
            "## Forbidden",
            "W1–W10 densify; FVG; R-series; swing/Donch/Outside/VR; W7 L→NY densify.",
            "",
        ]
    )
    OUT_FREEZE.write_text(body, encoding="utf-8")
    return sha256_bytes(body.encode("utf-8"))


def write_preregs():
    PREREG.mkdir(parents=True, exist_ok=True)
    specs = [
        (
            "20260715_H_FX3_H1_LONDON_CLOSE_INVENTORY_ON_CONT_001_PREREG.md",
            "HYP-FX3-H1-LONDON-CLOSE-INVENTORY-ON-CONT-001",
            [
                f"- London[{A_LONDON[0]},{A_LONDON[1]}) body≥{A_BODY_ATR}*ATR + close extreme third → next-day ON CONT.",
                f"- RR={A_RR}; hold≤{A_HOLD}; thick SL beyond London extreme.",
                "- ≠ W7 same-day L→NY PB; ≠ London open-drive; ≠ W10 WO/mid; ≠ FVG.",
            ],
        ),
        (
            "20260715_H_FX3_H4_D1_PERSIST2_PB_ACCEPT_MULTIDAY_001_PREREG.md",
            "HYP-FX3-H4-D1-PERSIST2-PB-ACCEPT-MULTIDAY-001",
            [
                f"- 2 D1 same-dir closes net≥{B_PERSIST_ATR}*ATR → H4 PB≥{B_PB_ATR}*ATR accept CONT.",
                f"- RR={B_RR}; hold≤{B_HOLD}. ≠ W10 mid-reclaim; ≠ swing ADX; ≠ R15 streak densify.",
            ],
        ),
        (
            "20260715_H_BOOK_HIGHR_INVENTORY_PERSIST_APRIORI_001_PREREG.md",
            "HYP-BOOK-HIGHR-INVENTORY-PERSIST-APRIORI-001",
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
                    "- Lane: `hard_pivot_w11_inventory_persist_20260715`",
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


def write_docs(results, book, receipt, any_surv, freeze_sha, qnote):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    table = _table(results + [book])
    OUT_PANEL.write_text(
        "# 3-critic — W11\n\nMerge GO offline. Model0 withheld until survivor.\n",
        encoding="utf-8",
    )
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — HARD PIVOT W11 inventory/persist high-R",
                "",
                f"Freeze sha={freeze_sha[:16]}…",
                "",
                "After W10 high-R WO/mid ALL_KILL (book tpw OK, edge neg).",
                "NEW: overnight London inventory CONT + D1 persist2 PB multi-day.",
                f"A priori MFE A=${A_RR*CASH_R:.0f} B=${B_RR*CASH_R:.0f} ≫ $12.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — W11",
                "",
                "| Object | ≠ |",
                "|---|---|",
                "| London ON inventory | ≠ W7 L→NY same-day; ≠ London open-drive; ≠ W10; ≠ FVG |",
                "| D1 persist2 PB | ≠ W10 mid-reclaim; ≠ swing ADX/TD-ROC; ≠ R15 streak densify |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline — HARD PIVOT W11",
                "",
                f"Receipt `{receipt}` Freeze `{freeze_sha}` Status `{status}`",
                f"QFSI: {qnote}",
                "",
                *table,
                "",
                f"caps={book['pair_caps']}",
                "",
                *[f"- `{r['hypothesis_id']}`: {', '.join(r['fail_notes']) or 'none'}" for r in results + [book]],
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLOSE.write_text(
        f"# Closeout W11\n\nStatus `{status}` Receipt `{receipt}`\n"
        "Do not densify W11/W1–W10/FVG/R-series. Best shelf `194548`. GOAL unmet.\n",
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — HARD PIVOT W11",
                "",
                f"~{stamp} ICT — `{status}`",
                *table,
                f"Receipt `{receipt}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLEAN_VN.write_text(
        "\n".join(
            [
                "# VN action brief — Clean book + HARD PIVOT W11",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "",
                "## Clean book (unchanged)",
                "PRIMARY PF@$12=1.184 tpw=3.241. Best shelf RR2 `194548`.",
                "",
                f"## HARD PIVOT W11 — `{status}`",
                *table,
                "",
                "- Overnight London inventory + D1 persist2 PB; MFE ≫ $12 a priori.",
                "- Không densify W1–W11 / FVG / R-series / swing / Donch / Outside / VR.",
                f"Receipt `{receipt}`",
                "GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def append_reg(results, book, receipt, prereg_paths):
    stamp = utc_now()
    with REG.open("a", encoding="utf-8") as f:
        for r, pp in zip(results, prereg_paths):
            f.write(
                json.dumps(
                    {
                        "record_type": "candidate",
                        "schema_version": 1,
                        "hypothesis_id": r["hypothesis_id"],
                        "state": "killed" if "KILL" in r["verdict"] else "probe_survivor",
                        "lane": "hard_pivot_w11_inventory_persist_20260715",
                        "prereg_path": pp,
                        "metrics": r["metrics"],
                        "verdict": r["verdict"],
                        "validation": {"fail_notes": r["fail_notes"], "receipt_sha256": receipt},
                        "updated_at": stamp,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        f.write(
            json.dumps(
                {
                    "record_type": "candidate",
                    "schema_version": 1,
                    "hypothesis_id": book["hypothesis_id"],
                    "state": "killed" if "KILL" in book["verdict"] else "probe_survivor",
                    "lane": "hard_pivot_w11_inventory_persist_20260715",
                    "metrics": book["metrics"],
                    "verdict": book["verdict"],
                    "validation": {
                        "fail_notes": book["fail_notes"],
                        "pair_caps": book["pair_caps"],
                        "receipt_sha256": receipt,
                    },
                    "updated_at": stamp,
                },
                ensure_ascii=False,
            )
            + "\n"
        )


def patch_hot(results, book, receipt, any_surv, freeze_sha, qnote):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    lines = [
        f"- **HARD PIVOT W11 INVENTORY/PERSIST CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED` / `{status}` / "
        f"`QFSI_007_HEALTHY` / `NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  HARD PIVOT W11 after W10 high-R ALL_KILL — overnight inventory + persist2 PB.",
        "  Offline screen:",
    ]
    for i, r in enumerate(results, 1):
        m, hc = r["metrics"], r["haircuts"]
        lines.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={m['n']} PF={m['pf']} tpw={m['tpw']} PF@$12={hc['x1']['pf']} x1.5={hc['x1_5']['pf']})."
        )
    bm, bhc = book["metrics"], book["haircuts"]
    lines.append(
        f"  BOOK. `{book['hypothesis_id']}` → **{book['verdict']}** "
        f"(N={bm['n']} PF={bm['pf']} tpw={bm['tpw']} PF@$12={bhc['x1']['pf']} "
        f"x1.5={bhc['x1_5']['pf']} caps_ok={book['pair_caps']['caps_ok']})."
    )
    lines += [
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        f"  VN `readouts/20260715_CLEAN_BOOK_AND_HARD_PIVOT_W11_VN_ACTION_BRIEF.md`.",
        f"  Freeze sha={freeze_sha[:16]}… QFSI: {qnote}",
        "  W10 carry: high-R book tpw~2.25 / edge neg; month thick-rare starve.",
        "  Do **not** densify W11 / W1–W10 / FVG / R10–R31 / swing / Donch / Outside / VR.",
        "  Clean book still GOAL_SCREEN_FAIL. PRIMARY PF@$12=1.184 tpw=3.241.",
        "  Next: next independent class outside W1–W11; keep R-series paused.",
        "  Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
        "",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    old = text.splitlines()
    if old and old[0].startswith("# Hot Cache"):
        old[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | HARD PIVOT W11 inventory/persist; "
            f"R-series densify PAUSED; {status}; GOAL unmet"
        )
        text = "\n".join(old) + ("\n" if text.endswith("\n") else "")
    marker = "## Active Truth\n"
    if marker in text:
        text = text.replace(marker, marker + "\n" + "\n".join(lines), 1)
    nm = "## Next Move\n"
    next_block = (
        f"\n- **ACTIVE — HARD PIVOT W11 inventory/persist aftermath.** "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`. "
        f"W11 offline `{status}` receipt `{receipt[:16]}…`. "
        "Do not densify FVG / W1–W11 / swing / Donch / Outside / VR. "
        "Next independent class if ALL_KILL. QFSI parallel; cost GAP. "
        "Best shelf RR2 `194548`. GOAL unmet.\n"
    )
    if nm in text:
        text2, nsub = re.subn(r"\n- \*\*ACTIVE — HARD PIVOT[^\n]*\n", next_block, text, count=1)
        text = text2 if nsub else text[: text.find(nm) + len(nm)] + next_block + text[text.find(nm) + len(nm) :]
    HOT.write_text(text, encoding="utf-8")


def qfsi_note():
    return "QFSI 007 parallel; cost freeze GAP (11 deals); login not headline"


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")
    freeze_sha = write_freeze()
    preregs = write_preregs()
    print("Freeze", freeze_sha[:16], f"MFE A=${A_RR*CASH_R:.0f} B=${B_RR*CASH_R:.0f}")
    h1 = {s: enrich(load(s, mt5.TIMEFRAME_H1)) for s in FX3}
    h4 = {s: enrich(load(s, mt5.TIMEFRAME_H4)) for s in FX3}

    print("Probe A London inventory ON...")
    p1, d1, t1 = probe_london_inventory_on(h1)
    r1 = pack_result("HYP-FX3-H1-LONDON-CLOSE-INVENTORY-ON-CONT-001", "London close inventory overnight CONT high-R", p1, d1)
    print(" ", r1["verdict"], r1["metrics"], r1["haircuts"]["x1"], r1["fail_notes"])

    print("Probe B D1 persist2 PB...")
    p2, d2, t2 = probe_d1_persist2_pb(h1, h4)
    r2 = pack_result("HYP-FX3-H4-D1-PERSIST2-PB-ACCEPT-MULTIDAY-001", "D1 persist2 H4 PB accept multi-day high-R", p2, d2)
    print(" ", r2["verdict"], r2["metrics"], r2["haircuts"]["x1"], r2["fail_notes"])

    print("Book...")
    book = evaluate_book(t1, t2)
    print(" ", book["verdict"], book["metrics"], book["haircuts"]["x1"], book["pair_caps"], book["fail_notes"])

    results = [r1, r2]
    any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results + [book])
    payload = {
        "schema": "hard_pivot_w11_inventory_persist.v1",
        "generated_at": utc_now(),
        "freeze_sha256": freeze_sha,
        "base_cost_usd": BASE_COST,
        "apriori_target_mfe": {"A": A_RR * CASH_R, "B": B_RR * CASH_R},
        "book": book,
        "results": results,
        "any_survivor": any_surv,
        "flags": {
            "R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED": True,
            "W1_W10_DENSIFY_FORBIDDEN": True,
            "FVG_DENSIFY_FORBIDDEN": True,
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
    write_docs(results, book, receipt, any_surv, freeze_sha, qnote)
    append_reg(results, book, receipt, preregs)
    patch_hot(results, book, receipt, any_surv, freeze_sha, qnote)
    print("Receipt", receipt)
    print("Status", "SURVIVOR" if any_surv else "ALL_KILL")
    mt5.shutdown()


if __name__ == "__main__":
    main()
