#!/usr/bin/env python3
"""Structural rebuild offline probes V8 — outside V1–V7 kill shelf.

A priori (frozen before ranking; GPT waived; no densify):
  H1 HYP-H1-MONO-CONTRACT-BREAK-001     — 3 shrinking ranges → coil break cont
  H2 HYP-M15-BROKEN-LEVEL-RETEST-001    — M15 pivot break → retest hold cont
  H3 HYP-H1-FORMING-DAY-EXT-FADE-001    — late forming-day extension fade
  H4 HYP-EURGBP-H1-LEAD-EURUSD-H1-001   — EURGBP displace lead → EURUSD cont
  H5 HYP-AUDUSD-H1-OVERLAP-FAIL-FADE-001 — AUDUSD London-overlap fail-fade

Stem V8 is collision-safe vs multi-sym board on V7.* and USDJPY V6.
Probe-only. Model 0 withheld unless PROBE_SURVIVOR.
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
PRE = ROOT / "03. EA Developer/EA_SonicR/research/preflight"
READ = ROOT / "03. EA Developer/EA_SonicR/research/readouts"
REG = ROOT / "03. EA Developer/EA_SonicR/research/CANDIDATE_REGISTRY.jsonl"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59, 59)
ELAPSED_WEEKS = (TO - FROM).total_seconds() / (7 * 24 * 3600)
DEPOSIT = 100000.0
RISK = 0.005
RR = 3.0
COST12 = 12.0
POINT = 0.001  # USDJPY / EURJPY-ish; FX majors use 0.0001 override per symbol


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def atr14(h, l, c):
    n = len(c)
    tr = np.zeros(n)
    tr[0] = h[0] - l[0]
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    out = np.full(n, np.nan)
    if n < 14:
        return out
    out[13] = tr[:14].mean()
    for i in range(14, n):
        out[i] = (out[i - 1] * 13 + tr[i]) / 14
    return out


def load(symbol, tf):
    rates = mt5.copy_rates_range(symbol, tf, FROM, TO)
    if rates is None or len(rates) < 200:
        raise RuntimeError(f"rates fail {symbol} {tf}: {mt5.last_error()}")
    return {
        k: rates[k].astype(float) if k != "time" else rates[k].astype(np.int64)
        for k in ("time", "open", "high", "low", "close")
    }


def mt5_dow(ts: int) -> int:
    return (datetime.fromtimestamp(ts, timezone.utc).weekday() + 1) % 7


def hour_u(ts: int) -> int:
    return datetime.fromtimestamp(ts, timezone.utc).hour


def tradeable(ts: int) -> bool:
    return mt5_dow(ts) in (1, 2, 3, 4) and hour_u(ts) < 22


def day_key(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def sim_r(trades_spec: list[dict], cost: float = COST12) -> dict[str, Any]:
    if not trades_spec:
        return {
            "n": 0,
            "pf": 0.0,
            "tpw": 0.0,
            "exp": 0.0,
            "net": 0.0,
            "pf_x15_cost": 0.0,
            "exp_x15_cost": 0.0,
            "cost_per_trade": cost,
        }
    bal = DEPOSIT
    pnls = []
    for t in trades_spec:
        risk_cash = bal * RISK
        pnl = risk_cash * t["r"]
        pnls.append(pnl)
        bal += pnl
    wins = [p for p in pnls if p > 0]
    losses = [-p for p in pnls if p < 0]
    pf = (sum(wins) / sum(losses)) if losses else (999.0 if wins else 0.0)
    net = sum(pnls)
    n = len(pnls)
    pnls125 = [p - 1.5 * cost for p in pnls]
    w125 = [p for p in pnls125 if p > 0]
    l125 = [-p for p in pnls125 if p < 0]
    pf125 = (sum(w125) / sum(l125)) if l125 else 0.0
    # Real partial P50 haircut ~$2.31 (diagnostic only; not verified QFSI)
    real_p50 = 2.31
    pnls_real = [p - real_p50 for p in pnls]
    wr = [p for p in pnls_real if p > 0]
    lr = [-p for p in pnls_real if p < 0]
    pf_real = (sum(wr) / sum(lr)) if lr else 0.0
    return {
        "n": n,
        "pf": pf,
        "tpw": n / ELAPSED_WEEKS,
        "exp": net / n,
        "net": net,
        "pf_x15_cost": pf125,
        "exp_x15_cost": sum(pnls125) / n,
        "cost_per_trade": cost,
        "pf_real_p50_haircut": pf_real,
        "real_p50_usd": real_p50,
    }


def gate(m: dict[str, Any]) -> tuple[str, list[str]]:
    notes = []
    if m["n"] < 80:
        notes.append("n_fail")
    if not (1.0 <= m["tpw"] <= 6.0):
        notes.append("cadence_fail")
    if m["pf"] < 1.0:
        notes.append("pf_fail")
    if m["pf_x15_cost"] < 1.25:
        notes.append("stress_fail")
    if notes:
        return "KILLED_AT_OFFLINE_PROBE", notes
    if m["pf"] > 1.30 and 2.0 <= m["tpw"] <= 5.0 and m["pf_x15_cost"] >= 1.25:
        return "PROBE_SURVIVOR", notes
    return "PARK_OFFLINE", notes


def resolve_trade(direction, entry, sl, tp, i_entry, h, l, c, max_hold):
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    for j in range(i_entry, min(i_entry + max_hold, len(c))):
        hi, lo = h[j], l[j]
        hit_sl = (direction > 0 and lo <= sl) or (direction < 0 and hi >= sl)
        hit_tp = (direction > 0 and hi >= tp) or (direction < 0 and lo <= tp)
        if hit_sl:
            return -1.0
        if hit_tp:
            return RR
    j = min(i_entry + max_hold - 1, len(c) - 1)
    return direction * (c[j] - entry) / risk


def pack(hid, symbol, tf, funnel, trades, cost=COST12) -> dict[str, Any]:
    m = sim_r(trades, cost=cost)
    verdict, notes = gate(m)
    return {
        "hypothesis_id": hid,
        "symbol": symbol,
        "tf": tf,
        "funnel": funnel,
        "metrics": m,
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
    }


def point_for(symbol: str) -> float:
    if symbol.startswith("XAU") or "JPY" in symbol:
        return 0.001
    return 0.0001


# ---------------------------------------------------------------------------
# H1 — mono-contract: 3 consecutive shrinking ranges → break of coil
# ---------------------------------------------------------------------------
def probe_mono_contract(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_coil": 0, "n_break": 0, "n_trades": 0}
    pt = point_for("USDJPY")
    i = 20
    while i < len(c) - 6:
        r0 = h[i] - l[i]
        r1 = h[i - 1] - l[i - 1]
        r2 = h[i - 2] - l[i - 2]
        if not (r0 < r1 < r2 and r0 > 0):
            i += 1
            continue
        if math.isnan(atr[i]) or atr[i] <= 0 or r0 > 0.8 * atr[i]:
            i += 1
            continue
        coil_hi = max(h[i - 2], h[i - 1], h[i])
        coil_lo = min(l[i - 2], l[i - 1], l[i])
        funnel["n_coil"] += 1
        broke = False
        for j in range(i + 1, min(i + 1 + 8, len(c) - 2)):
            ts = int(t[j])
            if not tradeable(ts):
                continue
            up = c[j] > coil_hi
            dn = c[j] < coil_lo
            if not (up or dn):
                continue
            funnel["n_break"] += 1
            direction = +1 if up else -1
            entry = float(o[j + 1])
            extreme = coil_lo if up else coil_hi
            sl = extreme - 0.1 * atr[j] if up else extreme + 0.1 * atr[j]
            dist = abs(entry - sl)
            if dist < 80 * pt or dist > 4000 * pt:
                continue
            tp = entry + dist * RR if up else entry - dist * RR
            r = resolve_trade(direction, entry, sl, tp, j + 1, h, l, c, 12)
            if r is None:
                continue
            trades.append({"r": r})
            funnel["n_trades"] += 1
            i = j + 2
            broke = True
            break
        if not broke:
            i += 1
    return pack("HYP-H1-MONO-CONTRACT-BREAK-001", "USDJPY", "H1", funnel, trades)


# ---------------------------------------------------------------------------
# H2 — M15 swing break → retest hold → continuation
# ---------------------------------------------------------------------------
def probe_broken_level_retest(m15: dict) -> dict[str, Any]:
    o, h, l, c, t = m15["open"], m15["high"], m15["low"], m15["close"], m15["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_pivot": 0, "n_break": 0, "n_retest": 0, "n_trades": 0}
    pt = point_for("USDJPY")
    L = 3
    i = 40
    while i < len(c) - 20:
        # pivot high / low at i-L
        pi = i - L
        is_ph = all(h[pi] >= h[pi - k] and h[pi] > h[pi + k] for k in range(1, L + 1))
        is_pl = all(l[pi] <= l[pi - k] and l[pi] < l[pi + k] for k in range(1, L + 1))
        if not (is_ph or is_pl):
            i += 1
            continue
        funnel["n_pivot"] += 1
        level = float(h[pi]) if is_ph else float(l[pi])
        # find break within next 16 bars
        br = None
        for j in range(i, min(i + 16, len(c) - 12)):
            if is_ph and c[j] > level:
                br = (j, +1)
                break
            if is_pl and c[j] < level:
                br = (j, -1)
                break
        if br is None:
            i += 1
            continue
        funnel["n_break"] += 1
        bj, direction = br
        # retest within 8 bars after break
        for k in range(bj + 1, min(bj + 1 + 8, len(c) - 3)):
            ts = int(t[k])
            if not tradeable(ts):
                continue
            if math.isnan(atr[k]) or atr[k] <= 0:
                continue
            if direction > 0:
                touch = l[k] <= level + 0.15 * atr[k] and l[k] >= level - 0.35 * atr[k]
                hold = c[k] > level
            else:
                touch = h[k] >= level - 0.15 * atr[k] and h[k] <= level + 0.35 * atr[k]
                hold = c[k] < level
            if not (touch and hold):
                continue
            funnel["n_retest"] += 1
            entry = float(o[k + 1])
            sl = level - 0.25 * atr[k] if direction > 0 else level + 0.25 * atr[k]
            dist = abs(entry - sl)
            if dist < 60 * pt or dist > 3500 * pt:
                continue
            tp = entry + dist * RR if direction > 0 else entry - dist * RR
            r = resolve_trade(direction, entry, sl, tp, k + 1, h, l, c, 16)
            if r is None:
                continue
            trades.append({"r": r})
            funnel["n_trades"] += 1
            i = k + 4
            break
        else:
            i += 1
    return pack("HYP-M15-BROKEN-LEVEL-RETEST-001", "USDJPY", "M15", funnel, trades)


# ---------------------------------------------------------------------------
# H3 — forming day extension fade
# ---------------------------------------------------------------------------
def probe_forming_day_ext_fade(h1: dict, d1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    hd, ld, cd, td = d1["high"], d1["low"], d1["close"], d1["time"]
    atr_d = atr14(hd, ld, cd)
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_eligible_days": 0, "n_ext": 0, "n_trades": 0}
    pt = point_for("USDJPY")
    # index H1 by day
    by_day: dict[str, list[int]] = {}
    for i in range(len(c)):
        by_day.setdefault(day_key(int(t[i])), []).append(i)

    for dkey, idxs in by_day.items():
        if len(idxs) < 12:
            continue
        # prior completed D1 ATR
        d_idx = np.searchsorted(td, int(t[idxs[0]]), side="left") - 1
        if d_idx < 14 or math.isnan(atr_d[d_idx]) or atr_d[d_idx] <= 0:
            continue
        # after >=10 bars of day, check forming range
        for pos in range(10, len(idxs) - 2):
            i = idxs[pos]
            ts = int(t[i])
            if not tradeable(ts):
                continue
            day_idxs = idxs[: pos + 1]
            f_hi = max(h[j] for j in day_idxs)
            f_lo = min(l[j] for j in day_idxs)
            f_rng = f_hi - f_lo
            if f_rng < 0.80 * atr_d[d_idx]:
                continue
            funnel["n_eligible_days"] += 1
            mid = 0.5 * (f_hi + f_lo)
            # pierce beyond 0.90 of forming day range
            up_ext = h[i] >= f_lo + 0.90 * f_rng and c[i] < h[i] - 0.2 * (h[i] - l[i])
            dn_ext = l[i] <= f_hi - 0.90 * f_rng and c[i] > l[i] + 0.2 * (h[i] - l[i])
            if not (up_ext or dn_ext):
                continue
            funnel["n_ext"] += 1
            if math.isnan(atr[i]) or atr[i] <= 0:
                continue
            direction = -1 if up_ext else +1
            entry = float(o[i + 1]) if i + 1 < len(c) else float(c[i])
            extreme = h[i] if up_ext else l[i]
            sl = extreme + 0.1 * atr[i] if up_ext else extreme - 0.1 * atr[i]
            dist = abs(entry - sl)
            if dist < 80 * pt or dist > 4000 * pt:
                continue
            # TP toward day mid (cap at RR)
            tp_mid = mid
            tp_rr = entry + dist * RR if direction > 0 else entry - dist * RR
            if direction < 0:
                tp = max(tp_rr, tp_mid) if tp_mid < entry else tp_rr
                tp = min(tp, entry - 0.8 * dist)  # at least ~0.8R
            else:
                tp = min(tp_rr, tp_mid) if tp_mid > entry else tp_rr
                tp = max(tp, entry + 0.8 * dist)
            # custom resolve with mid-aware TP
            r = None
            risk = abs(entry - sl)
            for j in range(i + 1, min(i + 1 + 10, len(c))):
                hi, lo = h[j], l[j]
                hit_sl = (direction > 0 and lo <= sl) or (direction < 0 and hi >= sl)
                hit_tp = (direction > 0 and hi >= tp) or (direction < 0 and lo <= tp)
                if hit_sl:
                    r = -1.0
                    break
                if hit_tp:
                    r = abs(tp - entry) / risk
                    break
            if r is None:
                j = min(i + 10, len(c) - 1)
                r = direction * (c[j] - entry) / risk
            trades.append({"r": r})
            funnel["n_trades"] += 1
            break  # one trade per day
    return pack("HYP-H1-FORMING-DAY-EXT-FADE-001", "USDJPY", "H1", funnel, trades)


# ---------------------------------------------------------------------------
# H4 — EURGBP H1 displace lead → EURUSD same-bar continuation
# ---------------------------------------------------------------------------
def probe_eurgbp_lead(eg: dict, eu: dict) -> dict[str, Any]:
    eg_o, eg_h, eg_l, eg_c, eg_t = eg["open"], eg["high"], eg["low"], eg["close"], eg["time"]
    eu_o, eu_h, eu_l, eu_c, eu_t = eu["open"], eu["high"], eu["low"], eu["close"], eu["time"]
    atr_eg = atr14(eg_h, eg_l, eg_c)
    atr_eu = atr14(eu_h, eu_l, eu_c)
    trades = []
    funnel = {"n_lead": 0, "n_align": 0, "n_trades": 0}
    pt = point_for("EURUSD")
    # align by time
    eu_map = {int(eu_t[i]): i for i in range(len(eu_t))}
    for i in range(20, len(eg_c) - 4):
        ts = int(eg_t[i])
        if not tradeable(ts):
            continue
        if math.isnan(atr_eg[i]) or atr_eg[i] <= 0:
            continue
        body = abs(eg_c[i] - eg_o[i])
        prior_hi = max(eg_h[i - 8 : i])
        prior_lo = min(eg_l[i - 8 : i])
        up = eg_c[i] > prior_hi and body >= 0.8 * atr_eg[i]
        dn = eg_c[i] < prior_lo and body >= 0.8 * atr_eg[i]
        if not (up or dn):
            continue
        funnel["n_lead"] += 1
        j = eu_map.get(ts)
        if j is None or j + 2 >= len(eu_c):
            continue
        # EURUSD same-bar direction confirm
        if up and not (eu_c[j] > eu_o[j]):
            continue
        if dn and not (eu_c[j] < eu_o[j]):
            continue
        funnel["n_align"] += 1
        if math.isnan(atr_eu[j]) or atr_eu[j] <= 0:
            continue
        direction = +1 if up else -1
        entry = float(eu_o[j + 1])
        sl = min(eu_l[j], eu_l[j - 1]) - 0.1 * atr_eu[j] if up else max(eu_h[j], eu_h[j - 1]) + 0.1 * atr_eu[j]
        dist = abs(entry - sl)
        if dist < 40 * pt or dist > 2500 * pt:
            continue
        tp = entry + dist * RR if up else entry - dist * RR
        r = resolve_trade(direction, entry, sl, tp, j + 1, eu_h, eu_l, eu_c, 12)
        if r is None:
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1
    return pack("HYP-EURGBP-H1-LEAD-EURUSD-H1-001", "EURUSD", "H1", funnel, trades)


# ---------------------------------------------------------------------------
# H5 — AUDUSD London-overlap range → fail-fade (not continue-break)
# ---------------------------------------------------------------------------
def probe_audusd_overlap_fail(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_days": 0, "n_break": 0, "n_fail": 0, "n_trades": 0}
    pt = point_for("AUDUSD")
    by_day: dict[str, list[int]] = {}
    for i in range(len(c)):
        by_day.setdefault(day_key(int(t[i])), []).append(i)

    for dkey, idxs in by_day.items():
        ov = [i for i in idxs if 7 <= hour_u(int(t[i])) < 10]
        if len(ov) < 2:
            continue
        funnel["n_days"] += 1
        a_hi = max(h[i] for i in ov)
        a_lo = min(l[i] for i in ov)
        if a_hi <= a_lo:
            continue
        # post-overlap bars
        post = [i for i in idxs if hour_u(int(t[i])) >= 10]
        if not post:
            continue
        br = None
        for i in post[:6]:
            if c[i] > a_hi:
                br = (i, +1)
                break
            if c[i] < a_lo:
                br = (i, -1)
                break
        if br is None:
            continue
        funnel["n_break"] += 1
        bi, br_dir = br
        # fail: within 3 bars close back inside range
        fail_i = None
        for k in range(bi + 1, min(bi + 1 + 3, len(c) - 2)):
            if br_dir > 0 and c[k] < a_hi and c[k] > a_lo:
                fail_i = k
                break
            if br_dir < 0 and c[k] > a_lo and c[k] < a_hi:
                fail_i = k
                break
        if fail_i is None:
            continue
        funnel["n_fail"] += 1
        ts = int(t[fail_i])
        if not tradeable(ts):
            continue
        if math.isnan(atr[fail_i]) or atr[fail_i] <= 0:
            continue
        direction = -1 if br_dir > 0 else +1
        entry = float(o[fail_i + 1])
        extreme = a_hi if br_dir > 0 else a_lo
        sl = extreme + 0.15 * atr[fail_i] if br_dir > 0 else extreme - 0.15 * atr[fail_i]
        dist = abs(entry - sl)
        if dist < 40 * pt or dist > 2500 * pt:
            continue
        mid = 0.5 * (a_hi + a_lo)
        tp_rr = entry + dist * RR if direction > 0 else entry - dist * RR
        tp = mid if (direction < 0 and mid < entry) or (direction > 0 and mid > entry) else tp_rr
        risk = abs(entry - sl)
        r = None
        for j in range(fail_i + 1, min(fail_i + 1 + 12, len(c))):
            hi, lo = h[j], l[j]
            hit_sl = (direction > 0 and lo <= sl) or (direction < 0 and hi >= sl)
            hit_tp = (direction > 0 and hi >= tp) or (direction < 0 and lo <= tp)
            if hit_sl:
                r = -1.0
                break
            if hit_tp:
                r = abs(tp - entry) / risk
                break
        if r is None:
            j = min(fail_i + 12, len(c) - 1)
            r = direction * (c[j] - entry) / risk
        trades.append({"r": r})
        funnel["n_trades"] += 1
    return pack("HYP-AUDUSD-H1-OVERLAP-FAIL-FADE-001", "AUDUSD", "H1", funnel, trades)


def main() -> int:
    if not mt5.initialize():
        raise RuntimeError(mt5.last_error())
    try:
        for s in ("USDJPY", "EURUSD", "EURGBP", "AUDUSD"):
            mt5.symbol_select(s, True)
        h1 = load("USDJPY", mt5.TIMEFRAME_H1)
        m15 = load("USDJPY", mt5.TIMEFRAME_M15)
        d1 = load("USDJPY", mt5.TIMEFRAME_D1)
        eg = load("EURGBP", mt5.TIMEFRAME_H1)
        eu = load("EURUSD", mt5.TIMEFRAME_H1)
        au = load("AUDUSD", mt5.TIMEFRAME_H1)
        acc = mt5.account_info()
        server = getattr(acc, "server", None)
        login = getattr(acc, "login", None)
    finally:
        mt5.shutdown()

    probes = [
        probe_mono_contract(h1),
        probe_broken_level_retest(m15),
        probe_forming_day_ext_fade(h1, d1),
        probe_eurgbp_lead(eg, eu),
        probe_audusd_overlap_fail(au),
    ]
    survivors = [p["hypothesis_id"] for p in probes if p["verdict"] == "PROBE_SURVIVOR"]
    parks = [p["hypothesis_id"] for p in probes if p["verdict"] == "PARK_OFFLINE"]
    payload = {
        "schema_version": "sonic_structural_offline_probes.v8",
        "created_at_utc": utc_now(),
        "status": "OFFLINE_FIRST_V8_COMPLETE",
        "honesty": "NOT_MODEL0_NOT_CONFIRMED_NOT_GOAL",
        "server": server,
        "login": login,
        "dedup": "readouts/20260714_STRUCTURAL_V8_DEDUP_CLEARANCE.md",
        "prior_clearance": "readouts/20260714_STRUCTURAL_V7_DEDUP_CLEARANCE.md",
        "probes": probes,
        "offline_survivors": survivors,
        "offline_parks": parks,
        "any_model0_authorized": bool(survivors),
        "phase0_compose": "NOT_WAITED_DISCOVERY_CONTINUES",
        "best_shelf": "RR2 20260714_194548",
        "banned": [
            "densify_maxkz_rr_sb_spark_itsm",
            "retune_v1_v7",
            "retune_wave3_5",
            "model0_on_kill",
            "phase0_wait_stall",
            "sofr_sonia_twin",
            "exogenous_riskoff_twin",
        ],
    }
    out = PRE / "20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V8.json"
    write_json(out, payload)
    sha = sha256_file(out)

    lines = [
        "# Structural rebuild offline probes V8",
        "",
        f"Generated: {payload['created_at_utc']}",
        "Authority: Owner GOAL push; offline-first; GPT waived; outside V1–V7",
        "Status: **offline-first**; Model 0 only if `PROBE_SURVIVOR`",
        "",
        "De-dup: `20260714_STRUCTURAL_V8_DEDUP_CLEARANCE.md`",
        "H1–H3 a priori: `20260714_STRUCTURAL_V7_DEDUP_CLEARANCE.md`",
        "",
        "| ID | Sym | N | PF | tpw | +$12 x1.5 | Real~$2.31 PF | Verdict |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for p in probes:
        m = p["metrics"]
        lines.append(
            f"| `{p['hypothesis_id']}` | {p['symbol']} | {m['n']} | {m['pf']:.3f} | "
            f"{m['tpw']:.2f} | {m['pf_x15_cost']:.3f} | "
            f"{m.get('pf_real_p50_haircut', 0):.3f} | **{p['verdict']}** |"
        )
    lines += [
        "",
        f"Offline survivors: `{survivors}`",
        f"Offline parks: `{parks}`",
        f"Any Model 0 authorized: `{payload['any_model0_authorized']}`",
        f"Receipt SHA: `{sha}`",
        "",
        "## Funnels",
        "",
    ]
    for p in probes:
        lines.append(f"- `{p['hypothesis_id']}`: {p['funnel']} notes={p['kill_notes']}")
    lines += [
        "",
        "## Notes",
        "",
        "- +$12 x1.5 is conservative Demo friction proxy (legacy screen).",
        "- Real P50 ~$2.31 is partial live-tick haircut — **not** full QFSI / not confirmed.",
        "- Best shelf RR2 `194548` unchanged. Do not densify V8 kill params.",
    ]
    (READ / "20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V8.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    for p in probes:
        state = (
            "killed"
            if "KILL" in p["verdict"]
            else ("parked" if "PARK" in p["verdict"] else "idea")
        )
        with REG.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "record_type": "candidate",
                        "schema_version": 1,
                        "hypothesis_id": p["hypothesis_id"],
                        "state": state,
                        "verdict": p["verdict"],
                        "reason": f"offline V8 { {k: (round(v,4) if isinstance(v,float) else v) for k,v in p['metrics'].items()} }; notes={p['kill_notes']}",
                        "updated_at": "2026-07-14",
                        "lane": "structural_rebuild_v8_20260714",
                        "symbol": p["symbol"],
                        "timeframe": p["tf"],
                        "model": "offline_closed_bar_probe",
                        "metrics": {
                            k: (float(v) if hasattr(v, "item") else v)
                            for k, v in p["metrics"].items()
                        },
                        "validation": {"model0": p["model0"]},
                        "receipt_sha256": sha,
                        "dedup": "readouts/20260714_STRUCTURAL_V8_DEDUP_CLEARANCE.md",
                    },
                    ensure_ascii=False,
                    default=float,
                )
                + "\n"
            )

    print(
        json.dumps(
            {
                "sha": sha,
                "board": [
                    {
                        "id": p["hypothesis_id"],
                        "verdict": p["verdict"],
                        "n": p["metrics"]["n"],
                        "pf": round(float(p["metrics"]["pf"]), 3),
                        "tpw": round(float(p["metrics"]["tpw"]), 3),
                        "x15": round(float(p["metrics"]["pf_x15_cost"]), 3),
                        "real231": round(float(p["metrics"].get("pf_real_p50_haircut", 0)), 3),
                    }
                    for p in probes
                ],
                "survivors": survivors,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
