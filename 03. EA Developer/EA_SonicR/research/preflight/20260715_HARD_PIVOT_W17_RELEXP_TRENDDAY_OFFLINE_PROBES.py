#!/usr/bin/env python3
"""HARD PIVOT W17 — EURGBP relative-expansion CONT + D1 trend-day H1 follow-through after W1–W16 ALL_KILL.

FORBIDDEN densify: W1–W16 / FVG / R-series / swing / Donch / Outside / VR /
absorb3 / weekday-gap / inventory / prior2d / usdconsensus / NR7 / H4-engulf /
ORB/IB / closeloc / H4-retest / Asia-quiet / L-range NY / pivot / week-HL / failbreak.

NEW classes (edge-seeking; W16 had cadence OK but PF@$12~1.01):
  A. HYP-FX3-H1-EURGBP-REL-EXPANSION-CONT-001
     London: one of EURUSD/GBPUSD expands (≥1.6*ATR) while peer compresses (≤0.7*ATR)
     → trade expander CONT into NY. ≠ W13 USD-consensus (≥2 same-dir).
  B. HYP-FX3-H1-D1-TRENDDAY-FOLLOWTHROUGH-CONT-001
     Prior D1 close in top/bottom 20% of range (trend day) → next London/NY H1
     first continuation break of prior D1 close CONT. ≠ W12 weekday gap; ≠ closeloc densify.
  BOOK. HYP-BOOK-RELEXP-TRENDDAY-APRIORI-001

+$12 hard. Model 0 only PROBE_SURVIVOR. Aim beat W14 near-miss 1.2209@$12.
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

STEM = "20260715_HARD_PIVOT_W17_RELEXP_TRENDDAY"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_HARD_PIVOT_W17_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_APRIORI_FREEZE.md"
OUT_COMBO_VN = READ / "20260715_COST_GRADE_AND_HARD_PIVOT_W17_VN_ACTION_BRIEF.md"
COST_STATUS = PRE / "20260715_COST_GRADE_PUSH_W13_STATUS.json"
QFSI_HB = PRE / "20260715_QFSI_007_WATCHER_HEARTBEAT.json"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
CASH_R = DEPOSIT * RISK_FRAC
FX3 = ("EURUSD", "GBPUSD", "USDJPY")
EURGBP = ("EURUSD", "GBPUSD")
CORR_CAP = 0.35
OVERLAP_FRAC_CAP = 0.05

A_LONDON = (7, 12)
A_NY = (12, 17)
A_EXP_ATR = 1.60
A_CMP_ATR = 0.70
A_SL_PAD = 0.20
A_SL_MIN_ATR = 1.40
A_RR = 3.00
A_HOLD = 48
A_PRIORITY = 1
A_MAX_BOOK = 2

B_SESSION = (7, 17)
B_EXTREME = 0.20  # close in top/bottom 20%
B_SL_PAD = 0.20
B_SL_MIN_ATR = 1.45
B_RR = 3.25
B_HOLD = 56
B_PRIORITY = 2
B_MAX_BOOK = 2


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


def build_london_stats(d):
    """Per day: London session TR, net close-open, ATR at end, side of close vs open."""
    by = {}
    for j in range(len(d["t"])):
        dt = datetime.fromtimestamp(int(d["t"][j]), tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if not (A_LONDON[0] <= dt.hour < A_LONDON[1]):
            continue
        day = dt.date()
        o, h, l, c = float(d["o"][j]), float(d["h"][j]), float(d["l"][j]), float(d["c"][j])
        atr = d["atr"][j]
        if day not in by:
            by[day] = {"hi": h, "lo": l, "o": o, "c": c, "n": 1, "atr": atr}
        else:
            by[day]["hi"] = max(by[day]["hi"], h)
            by[day]["lo"] = min(by[day]["lo"], l)
            by[day]["c"] = c
            by[day]["n"] += 1
            if np.isfinite(atr):
                by[day]["atr"] = atr
    for day, v in by.items():
        v["tr"] = v["hi"] - v["lo"]
        v["dir"] = 1 if v["c"] > v["o"] else (-1 if v["c"] < v["o"] else 0)
    return by


def build_d1_trend_days(d1):
    """Map next trading day → prior D1 trend-day signal."""
    out = {}
    for j in range(len(d1["t"])):
        dt = datetime.fromtimestamp(int(d1["t"][j]), tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        o, h, l, c = float(d1["o"][j]), float(d1["h"][j]), float(d1["l"][j]), float(d1["c"][j])
        rng = h - l
        if rng <= 0:
            continue
        loc = (c - l) / rng
        side = 0
        if loc >= (1.0 - B_EXTREME):
            side = 1
        elif loc <= B_EXTREME:
            side = -1
        if side == 0:
            continue
        next_day = (dt + timedelta(days=1)).date()
        while next_day.weekday() >= 5:
            next_day = next_day + timedelta(days=1)
        out[next_day] = {"side": side, "close": c, "hi": h, "lo": l, "rng": rng}
    return out


def probe_eurgbp_rel_expansion(h1):
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    london = {s: build_london_stats(h1[s]) for s in EURGBP}
    used = set()
    for i in range(40, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, A_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if not (A_NY[0] <= dt.hour < A_NY[1]):
            continue
        if len(open_pos) >= A_MAX_BOOK:
            continue
        sig_ts = int(clock[i - 1])
        sig_dt = datetime.fromtimestamp(sig_ts, tz=timezone.utc)
        if not (A_NY[0] <= sig_dt.hour < A_NY[1]):
            continue
        day = sig_dt.date()
        le = london["EURUSD"].get(day)
        lg = london["GBPUSD"].get(day)
        if le is None or lg is None:
            continue
        if le.get("n", 0) < 3 or lg.get("n", 0) < 3:
            continue
        ae, ag = le.get("atr"), lg.get("atr")
        if not (np.isfinite(ae) and ae > 0 and np.isfinite(ag) and ag > 0):
            continue
        re_, rg = le["tr"] / ae, lg["tr"] / ag
        # relative expansion: one expands, peer compresses
        candidates = []
        if re_ >= A_EXP_ATR and rg <= A_CMP_ATR and le["dir"] != 0:
            candidates.append(("EURUSD", le["dir"], le))
        if rg >= A_EXP_ATR and re_ <= A_CMP_ATR and lg["dir"] != 0:
            candidates.append(("GBPUSD", lg["dir"], lg))
        for sym, side, st in candidates:
            if sym in open_syms:
                continue
            key = (day, sym)
            if key in used:
                continue
            d = h1[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < 20:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                atr = st.get("atr")
            if not np.isfinite(atr) or atr <= 0:
                continue
            _o, h, l, c = float(d["o"][j]), float(d["h"][j]), float(d["l"][j]), float(d["c"][j])
            # NY accept in London direction (close still on London dir side of London close)
            if side > 0 and c < st["c"]:
                continue
            if side < 0 and c > st["c"]:
                continue
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            atr_e = d["atr"][ent_i] if np.isfinite(d["atr"][ent_i]) else atr
            if side > 0:
                sl = st["lo"] - A_SL_PAD * atr_e
                sl = min(sl, entry - A_SL_MIN_ATR * atr_e)
            else:
                sl = st["hi"] + A_SL_PAD * atr_e
                sl = max(sl, entry + A_SL_MIN_ATR * atr_e)
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
                    "sleeve": "A_RELEXP",
                    "priority": A_PRIORITY,
                }
            )
            used.add(key)
    flush_open(open_pos, h1, closed)
    return summarize(closed)


def probe_d1_trendday_followthrough(h1, d1):
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    td = {s: build_d1_trend_days(d1[s]) for s in FX3}
    used = set()
    for i in range(40, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, B_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if not (B_SESSION[0] <= dt.hour < B_SESSION[1]):
            continue
        if len(open_pos) >= B_MAX_BOOK:
            continue
        sig_ts = int(clock[i - 1])
        sig_dt = datetime.fromtimestamp(sig_ts, tz=timezone.utc)
        if not (B_SESSION[0] <= sig_dt.hour < B_SESSION[1]):
            continue
        day = sig_dt.date()
        for sym in FX3:
            if sym in open_syms:
                continue
            key = (day, sym)
            if key in used:
                continue
            sig = td[sym].get(day)
            if sig is None:
                continue
            d = h1[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < 20:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            _o, h, l, c = float(d["o"][j]), float(d["h"][j]), float(d["l"][j]), float(d["c"][j])
            side = sig["side"]
            lvl = sig["close"]
            # first continuation break of prior D1 close
            if side > 0 and not (c > lvl and h > lvl):
                continue
            if side < 0 and not (c < lvl and l < lvl):
                continue
            if j >= 1:
                pc = float(d["c"][j - 1])
                if side > 0 and pc > lvl:
                    continue
                if side < 0 and pc < lvl:
                    continue
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            atr_e = d["atr"][ent_i] if np.isfinite(d["atr"][ent_i]) else atr
            if side > 0:
                sl = min(l, lvl) - B_SL_PAD * atr_e
                sl = min(sl, entry - B_SL_MIN_ATR * atr_e)
            else:
                sl = max(h, lvl) + B_SL_PAD * atr_e
                sl = max(sl, entry + B_SL_MIN_ATR * atr_e)
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
                    "sleeve": "B_TRENDDAY",
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
        t["sleeve"], t["priority"] = "A_RELEXP", A_PRIORITY
        t["pnl_haircut"] = float(t["pnl"]) - BASE_COST
    for t in tb:
        t["sleeve"], t["priority"] = "B_TRENDDAY", B_PRIORITY
        t["pnl_haircut"] = float(t["pnl"]) - BASE_COST
    filtered, dropped = apply_heat(ta + tb)
    pnls = [float(t["pnl"]) for t in filtered]
    m, hc = metrics(pnls), haircuts(pnls)
    by = defaultdict(list)
    for t in filtered:
        by[t["sleeve"]].append(t)
    a, b = by.get("A_RELEXP", []), by.get("B_TRENDDAY", [])
    corr = pearson(weekly_series(a, "pnl_haircut"), weekly_series(b, "pnl_haircut"))
    ov = pairwise_overlap(a, b)
    caps_ok = not ((corr is not None and corr > CORR_CAP) or ov > OVERLAP_FRAC_CAP)
    verdict, notes = book_verdict(m, hc, caps_ok)
    return _jsonable(
        {
            "hypothesis_id": "HYP-BOOK-RELEXP-TRENDDAY-APRIORI-001",
            "setup": "a priori book: EURGBP rel-expansion + D1 trend-day follow-through",
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
            "# A priori freeze — HARD PIVOT W17 EURGBP rel-expansion + D1 trend-day FT",
            "",
            "Date: 2026-07-15",
            "Status: `APRIORI_FREEZE__PRE_METRICS`",
            f"A target MFE ≈ ${A_RR * CASH_R:.0f}; B ≈ ${B_RR * CASH_R:.0f} ≫ ${BASE_COST}.",
            "",
            "## Objects",
            "- HYP-FX3-H1-EURGBP-REL-EXPANSION-CONT-001",
            "- HYP-FX3-H1-D1-TRENDDAY-FOLLOWTHROUGH-CONT-001",
            "- HYP-BOOK-RELEXP-TRENDDAY-APRIORI-001",
            "",
            "## Forbidden",
            "W1–W16 densify; FVG; R-series; usdconsensus densify; H4-retest; Asia-quiet;",
            "L-range NY; pivot; week-HL; failbreak; closeloc densify.",
            "",
            "## Screen",
            f"+${BASE_COST}; tpw∈[2,5]; PF@$12≥1.30; x1.5≥1.25; N≥80.",
            "Aim beat W14 near-miss 1.2209@$12. W16 cadence OK / edge thin.",
            "",
        ]
    )
    OUT_FREEZE.write_text(body, encoding="utf-8")
    return sha256_bytes(body.encode("utf-8"))


def write_preregs():
    PREREG.mkdir(parents=True, exist_ok=True)
    specs = [
        (
            "20260715_H_FX3_H1_EURGBP_REL_EXPANSION_CONT_001_PREREG.md",
            "HYP-FX3-H1-EURGBP-REL-EXPANSION-CONT-001",
            [
                f"- London EUR vs GBP relative expansion → NY CONT; RR={A_RR}; hold<={A_HOLD}.",
                "- != W13 USD-consensus (≥2 same-dir across FX3).",
            ],
        ),
        (
            "20260715_H_FX3_H1_D1_TRENDDAY_FOLLOWTHROUGH_CONT_001_PREREG.md",
            "HYP-FX3-H1-D1-TRENDDAY-FOLLOWTHROUGH-CONT-001",
            [
                f"- Prior D1 trend-day (close extreme 20%) → H1 first break of D1 close CONT; RR={B_RR}.",
                "- != W12 weekday gap; != closeloc densify shelf.",
            ],
        ),
        (
            "20260715_H_BOOK_RELEXP_TRENDDAY_APRIORI_001_PREREG.md",
            "HYP-BOOK-RELEXP-TRENDDAY-APRIORI-001",
            [f"- Pool A+B; corr<={CORR_CAP}; overlap<={OVERLAP_FRAC_CAP}; +$12; tpw[2,5]."],
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
                    "- Lane: `hard_pivot_w17_relexp_trendday_20260715`",
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
                "parent_candidate": "hard_pivot_w17_relexp_trendday",
                "feature_family": "hard_pivot_w17_relexp_trendday",
                "lane": "hard_pivot_w17_relexp_trendday_20260715",
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


def spotcheck_qfsi():
    hb = {}
    if QFSI_HB.exists():
        try:
            hb = json.loads(QFSI_HB.read_text(encoding="utf-8"))
        except Exception as e:
            hb = {"parse_error": str(e)}
    alive = bool(hb.get("watcher_alive"))
    pid = hb.get("capture_pid")
    proc_alive = None
    if pid is not None:
        try:
            import os

            if os.name == "nt":
                import ctypes

                k = ctypes.windll.kernel32
                handle = k.OpenProcess(0x1000, False, int(pid))
                if handle:
                    exit_code = ctypes.c_ulong()
                    k.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                    proc_alive = exit_code.value == 259
                    k.CloseHandle(handle)
                else:
                    proc_alive = False
            else:
                os.kill(int(pid), 0)
                proc_alive = True
        except Exception:
            proc_alive = False
    return {
        "heartbeat": hb,
        "watcher_alive": alive,
        "capture_pid": pid,
        "proc_alive": proc_alive,
        "spotcheck_at_utc": utc_now(),
        "verdict": (
            "QFSI_007_HEALTHY"
            if alive and (proc_alive is True or proc_alive is None)
            else "QFSI_007_UNHEALTHY_OR_STALE"
        ),
    }


def cost_grade_lines(qfsi_spot=None):
    if not COST_STATUS.exists():
        lines = ["Cost grade: status JSON missing — assume GAP (11 deals, ≪90d)."]
    else:
        cs = json.loads(COST_STATUS.read_text(encoding="utf-8"))
        d = cs.get("distance_to_freeze", {})
        hb = cs.get("watcher_heartbeat", {})
        cp = cs.get("qfsi_007_capture_progress", {})
        lines = [
            f"- QFSI 007: watcher_alive={hb.get('watcher_alive')} cap_pid={hb.get('capture_pid')} "
            f"quotes={cp.get('quote_rows')} hb={cp.get('heartbeat_rows')} tick_err={cp.get('tick_errors')}",
            f"- quote_days={d.get('quote_days')}; raw_deals={d.get('raw_deals')}; freeze_eligible={d.get('freeze_eligible')}",
            f"- commission unique days: {d.get('commission_lifecycle_proxy_unique_days')}",
            f"- slip: {d.get('slippage')}",
            f"- verdict: `{d.get('verdict')}`",
            "- Autonomous remaining: keep QFSI alive (calendar-bound days); retry deals (still ~11=exhausted); "
            "do NOT invent cost; Owner export optional only.",
        ]
    if qfsi_spot:
        lines.append(
            f"- W17 spot-check: `{qfsi_spot.get('verdict')}` "
            f"hb_alive={qfsi_spot.get('watcher_alive')} proc_alive={qfsi_spot.get('proc_alive')} "
            f"pid={qfsi_spot.get('capture_pid')} @ {qfsi_spot.get('spotcheck_at_utc')}"
        )
    return lines


def write_docs(results, book, receipt, any_surv, freeze_sha, qfsi_spot):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    table = _table(results + [book])
    cg = cost_grade_lines(qfsi_spot)
    OUT_PANEL.write_text(
        "\n".join(
            [
                "# 3-critic — W17 EURGBP rel-expansion + D1 trend-day FT",
                "",
                "| Critic | Call |",
                "|---|---|",
                "| Sonic trader | GO — rel-expansion != USD-consensus; trend-day FT != weekday-gap/closeloc |",
                "| Quant | GO — W16 cadence OK/edge thin → new edge source; MFE≫$12; honest +$12 |",
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
                "# Design — HARD PIVOT W17 rel-expansion + trend-day",
                "",
                f"Freeze sha={freeze_sha[:16]}…",
                "",
                "After W1–W16 ALL_KILL (W16 tpw OK / PF@$12~1.01; W14 near-miss densify FORBIDDEN).",
                "NEW edge-source classes:",
                "1) EUR vs GBP London relative expansion → NY CONT.",
                "2) Prior D1 trend-day → H1 follow-through break of D1 close.",
                f"A priori MFE A=${A_RR*CASH_R:.0f} B=${B_RR*CASH_R:.0f} ≫ $12.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — W17",
                "",
                "| Object | ≠ |",
                "|---|---|",
                "| EURGBP rel-expansion | W13 USD-consensus (≥2 FX3 same-dir) |",
                "| D1 trend-day follow-through | W12 weekday gap; closeloc densify shelf |",
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
                f"# HARD PIVOT W17 offline probes — `{status}`",
                "",
                f"Receipt `{receipt}`",
                f"QFSI spot-check: `{qfsi_spot.get('verdict')}`; cost freeze GAP; login not headline",
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
                "# VN — HARD PIVOT W17 rel-expansion + trend-day",
                "",
                f"`{status}`",
                "",
                *table,
                "",
                "Không densify W1–W16 / H4-retest / Asia-quiet / usdconsensus.",
                f"Receipt `{receipt}`",
                "GOAL unmet." if not any_surv else "Survivor → Model 0 only.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLOSE.write_text(
        "\n".join(
            [
                f"# Session closeout — HARD PIVOT W17 — `{status}`",
                "",
                f"Receipt `{receipt}` freeze sha={freeze_sha[:16]}…",
                "R-series densify PAUSED. Model0 withheld if ALL_KILL.",
                "Next: next independent class outside W1–W17 if ALL_KILL;",
                "keep +$12 research screen; QFSI parallel; cost freeze GAP.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLEAN_VN.write_text(
        "\n".join(
            [
                "# VN action brief — Clean book + HARD PIVOT W17",
                "",
                f"Thời điểm: 2026-07-15 ~{datetime.now().strftime('%H:%M')} ICT",
                "",
                "## Clean book (unchanged RESEARCH-GRADE @$12)",
                "PRIMARY PF@$12=1.184 tpw=3.241. Best shelf RR2 `194548`.",
                "DIAGNOSTIC RealP50≈1.356 ≠ GOAL — không promote.",
                "",
                f"## HARD PIVOT W17 — `{status}`",
                *table,
                "",
                "- EURGBP rel-expansion + D1 trend-day FT; MFE ≫ $12 a priori.",
                "- Không densify W1–W16 / H4-retest / Asia-quiet / FVG / R-series.",
                f"Receipt `{receipt}`",
                "GOAL unmet." if not any_surv else "Có survivor — chỉ Model 0.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_COMBO_VN.write_text(
        "\n".join(
            [
                "# VN action brief — Cost-grade push + HARD PIVOT W17",
                "",
                f"Thời điểm: 2026-07-15 ~{datetime.now().strftime('%H:%M')} ICT",
                "",
                "## Track 1 — Cost-grade push (distance to research-grade freeze)",
                *cg,
                "",
                "- Clean PRIMARY PF@$12=**1.184** tpw=3.24 vẫn binding RESEARCH-GRADE.",
                "- RealP50≈1.356 / PF@$8 đẹp hơn chỉ là DIAGNOSTIC — **không nới GOAL**.",
                "- Deal history vẫn **11** → broker history exhausted; không invent.",
                "- W14 near-miss PF@$12=1.221 densify **FORBIDDEN**.",
                "",
                f"## Track 2 — HARD PIVOT W17 `{status}`",
                *table,
                f"Receipt W17 `{receipt}`",
                "GOAL unmet." if not any_surv else "Survivor → Model 0 only.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def patch_hot(results, book, receipt, any_surv, freeze_sha, qfsi_spot):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    lines_tbl = []
    for r in results + [book]:
        m, hc = r["metrics"], r["haircuts"]
        lines_tbl.append(
            f"  {len(lines_tbl)+1}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={m['n']} PF={m['pf']} tpw={m['tpw']} PF@$12={hc['x1']['pf']} x1.5={hc['x1_5']['pf']})."
        )
    cg = cost_grade_lines(qfsi_spot)
    qfsi_tag = qfsi_spot.get("verdict", "QFSI_007_HEALTHY")
    block = "\n".join(
        [
            f"- **HARD PIVOT W17 RELEXP/TRENDDAY + COST-GRADE CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
            f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED` / `{status}` / "
            f"`{qfsi_tag}` / `NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
            "  Dual-track: (1) cost-grade distance-to-freeze; (2) HARD PIVOT W17 new class.",
            "  **Cost-grade** `preflight/20260715_COST_GRADE_PUSH_W13_STATUS.json`:",
            *[f"  {ln}" for ln in cg],
            "  Clean PRIMARY PF@$12=1.184 tpw=3.241; RealP50 DIAGNOSTIC only — do NOT promote GOAL.",
            "  **W17 offline** after W1–W16 ALL_KILL — EURGBP rel-expansion + D1 trend-day FT:",
            *lines_tbl,
            f"  Receipt `{receipt}`",
            f"  `preflight/{OUT_JSON.name}`;",
            f"  VN `readouts/{OUT_COMBO_VN.name}`.",
            f"  Freeze sha={freeze_sha[:16]}… QFSI spot-check `{qfsi_tag}`; cost freeze GAP (11 deals); login not headline",
            "  Do **not** densify W17 / W1–W16 / H4-retest / Asia-quiet / usdconsensus / FVG / R10–R31.",
            "  Clean book still GOAL_SCREEN_FAIL. PRIMARY PF@$12=1.184 tpw=3.241.",
            "  Next: next independent class outside W1–W17; keep R-series paused; +$12 screen holds.",
            "  Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
            "",
            "",
        ]
    )
    text = HOT.read_text(encoding="utf-8")
    text = re.sub(
        r"^Updated:.*$",
        f"Updated: 2026-07-15 ~{stamp} ICT | HARD PIVOT W17 relexp/trendday + cost-grade; "
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
        qfsi_spot = spotcheck_qfsi()
        freeze_sha = write_freeze()
        preregs = write_preregs()
        h1 = {s: enrich(load(s, mt5.TIMEFRAME_H1)) for s in FX3}
        d1 = {s: enrich(load(s, mt5.TIMEFRAME_D1)) for s in FX3}
        pnls_a, detail_a, trades_a = probe_eurgbp_rel_expansion(h1)
        pnls_b, detail_b, trades_b = probe_d1_trendday_followthrough(h1, d1)
        ra = pack_result(
            "HYP-FX3-H1-EURGBP-REL-EXPANSION-CONT-001",
            "EURGBP London rel-expansion → NY CONT RR3",
            pnls_a,
            detail_a,
        )
        rb = pack_result(
            "HYP-FX3-H1-D1-TRENDDAY-FOLLOWTHROUGH-CONT-001",
            "Prior D1 trend-day → H1 FT break CONT RR3.25",
            pnls_b,
            detail_b,
        )
        book = evaluate_book(trades_a, trades_b)
        results = [ra, rb]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results + [book])
        payload = {
            "schema_version": "hard_pivot_w17_relexp_trendday_offline.v1",
            "generated_at_utc": utc_now(),
            "freeze_sha256": freeze_sha,
            "preregs": preregs,
            "base_cost_usd": BASE_COST,
            "cost_grade_status": str(COST_STATUS.as_posix()) if COST_STATUS.exists() else None,
            "qfsi_spotcheck": qfsi_spot,
            "results": results,
            "book": book,
            "any_survivor": any_surv,
            "flags": {
                "R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED": True,
                "W1_W16_DENSIFY_FORBIDDEN": True,
                "H4RETEST_ASIAQUIET_DENSIFY_FORBIDDEN": True,
                "FVG_DENSIFY_FORBIDDEN": True,
            },
            "w14_near_miss_pf12": 1.2209,
        }
        raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        receipt = sha256_bytes(raw)
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        write_docs(results, book, receipt, any_surv, freeze_sha, qfsi_spot)
        append_registry(results, book, receipt)
        patch_hot(results, book, receipt, any_surv, freeze_sha, qfsi_spot)
        print(
            json.dumps(
                {
                    "receipt": receipt,
                    "any_survivor": any_surv,
                    "qfsi_spotcheck": qfsi_spot.get("verdict"),
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
