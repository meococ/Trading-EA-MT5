#!/usr/bin/env python3
"""Structural rebuild offline probes V3 — FVG cont + NYIB fail-fade.

NOT Model 0. NOT confirmed. NOT GOAL. Kill-fast offline.
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
    if rates is None or len(rates) < 100:
        raise RuntimeError(f"rates fail {symbol} {tf}: {mt5.last_error()}")
    return {k: rates[k].astype(float) if k != "time" else rates[k].astype(np.int64)
            for k in ("time", "open", "high", "low", "close")}


def mt5_dow(ts: int) -> int:
    # Sun=0..Sat=6
    return (datetime.fromtimestamp(ts, timezone.utc).weekday() + 1) % 7


def hour_u(ts: int) -> int:
    return datetime.fromtimestamp(ts, timezone.utc).hour


def sim_r(trades_spec: list[dict]) -> dict[str, Any]:
    """trades_spec entries: direction(+1/-1), entry, sl, tp, entry_i, bars"""
    # Simplified path: resolve on subsequent bars from caller-provided sequence
    # Here each trade already has exit_pnl_R computed by caller.
    if not trades_spec:
        return {"n": 0, "pf": 0.0, "tpw": 0.0, "exp": 0.0, "net": 0.0,
                "pf_x15_cost12": 0.0, "exp_x15_cost12": 0.0}
    bal = DEPOSIT
    pnls = []
    for t in trades_spec:
        risk_cash = bal * RISK
        pnl = risk_cash * t["r"]
        # optional additive cost stress in $ for diagnostic
        pnls.append(pnl)
        bal += pnl
    wins = [p for p in pnls if p > 0]
    losses = [-p for p in pnls if p < 0]
    pf = (sum(wins) / sum(losses)) if losses else (999.0 if wins else 0.0)
    net = sum(pnls)
    n = len(pnls)
    # +$12 a priori haircut per trade then x1.5 on that base cost
    pnls12 = [p - COST12 for p in pnls]
    w12 = [p for p in pnls12 if p > 0]
    l12 = [-p for p in pnls12 if p < 0]
    pf12 = (sum(w12) / sum(l12)) if l12 else 0.0
    pnls125 = [p - 1.5 * COST12 for p in pnls]
    w125 = [p for p in pnls125 if p > 0]
    l125 = [-p for p in pnls125 if p < 0]
    pf125 = (sum(w125) / sum(l125)) if l125 else 0.0
    return {
        "n": n,
        "pf": pf,
        "tpw": n / ELAPSED_WEEKS,
        "exp": net / n,
        "net": net,
        "pf_cost12": pf12,
        "pf_x15_cost12": pf125,
        "exp_x15_cost12": (sum(pnls125) / n) if n else 0.0,
    }


def gate(m: dict[str, Any]) -> tuple[str, list[str]]:
    notes = []
    if m["n"] < 80:
        notes.append("n_fail")
    if not (1.0 <= m["tpw"] <= 6.0):
        notes.append("cadence_fail")
    if m["pf"] < 1.0:
        notes.append("pf_fail")
    if m["pf_x15_cost12"] < 1.25:
        notes.append("stress_fail")
    if notes:
        return "KILLED_AT_OFFLINE_PROBE", notes
    if m["pf"] > 1.30 and 2.0 <= m["tpw"] <= 5.0:
        return "PROBE_SURVIVOR", notes
    return "PARK_OFFLINE", notes


def resolve_trade(direction, entry, sl, tp, i_entry, h, l, c, max_hold):
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    for j in range(i_entry, min(i_entry + max_hold, len(c))):
        hi, lo, cl = h[j], l[j], c[j]
        hit_sl = (direction > 0 and lo <= sl) or (direction < 0 and hi >= sl)
        hit_tp = (direction > 0 and hi >= tp) or (direction < 0 and lo <= tp)
        if hit_sl and hit_tp:
            return -1.0  # SL first
        if hit_sl:
            return -1.0
        if hit_tp:
            return RR
        # session flat Fri/weekend approx via later bars not needed if max_hold short
    # time exit at last close
    j = min(i_entry + max_hold - 1, len(c) - 1)
    return direction * (c[j] - entry) / risk


def probe_fvg(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_displace": 0, "n_fvg": 0, "n_trades": 0}
    i = 20
    while i < len(c) - 5:
        if math.isnan(atr[i]) or atr[i] <= 0:
            i += 1
            continue
        body = abs(c[i] - o[i])
        if body < 1.5 * atr[i]:
            i += 1
            continue
        bull = c[i] > o[i]
        # FVG: bullish gap between high[i-1] and low[i+1]? Classic 3-candle FVG:
        # bull FVG if low[i+1] > high[i-1]; bear if high[i+1] < low[i-1]
        if i + 1 >= len(c):
            break
        funnel["n_displace"] += 1
        if bull:
            if not (l[i + 1] > h[i - 1]):
                i += 1
                continue
            fvg_low, fvg_high = h[i - 1], l[i + 1]
        else:
            if not (h[i + 1] < l[i - 1]):
                i += 1
                continue
            fvg_low, fvg_high = h[i + 1], l[i - 1]
        funnel["n_fvg"] += 1
        fvg_mid = 0.5 * (fvg_low + fvg_high)
        # search fill within next 12 H1
        filled = False
        for j in range(i + 2, min(i + 2 + 12, len(c) - 2)):
            ts = int(t[j])
            dow = mt5_dow(ts)
            hr = hour_u(ts)
            if dow not in (1, 2, 3, 4) or hr >= 22:
                continue
            # ≤50% fill: price trades into FVG but close resumes direction
            if bull:
                touched = l[j] <= fvg_high and l[j] >= fvg_mid  # fill upper half at most
                resume = c[j] > fvg_mid and c[j] >= o[j]
                extreme = fvg_low
                direction = +1
            else:
                touched = h[j] >= fvg_low and h[j] <= fvg_mid
                resume = c[j] < fvg_mid and c[j] <= o[j]
                extreme = fvg_high
                direction = -1
            if not (touched and resume):
                continue
            entry = float(o[j + 1])
            sl = extreme - 0.1 * atr[j] if direction > 0 else extreme + 0.1 * atr[j]
            dist = abs(entry - sl)
            if dist < 100 * 0.001 or dist > 5000 * 0.001:
                continue
            tp = entry + dist * RR if direction > 0 else entry - dist * RR
            r = resolve_trade(direction, entry, sl, tp, j + 1, h, l, c, max_hold=12)
            if r is None:
                continue
            trades.append({"r": r})
            funnel["n_trades"] += 1
            filled = True
            i = j + 2
            break
        if not filled:
            i += 1
    m = sim_r(trades)
    verdict, notes = gate(m)
    return {
        "hypothesis_id": "HYP-H1-DISPLACE-FVG-CONT-001",
        "symbol": "USDJPY",
        "tf": "H1",
        "funnel": funnel,
        "metrics": m,
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD_KILL_FAST",
    }


def probe_nyib_fail(m15: dict) -> dict[str, Any]:
    o, h, l, c, t = m15["open"], m15["high"], m15["low"], m15["close"], m15["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_ib_days": 0, "n_break": 0, "n_fail": 0, "n_trades": 0}
    # group by UTC date
    by_day: dict[str, list[int]] = {}
    for i, ts in enumerate(t):
        day = datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%d")
        by_day.setdefault(day, []).append(i)

    for day, idxs in by_day.items():
        # IB = first 4 M15 of NY window hour 13-14 UTC proxy (NY open ~13/14 UTC depending DST)
        ib_idxs = [i for i in idxs if 13 <= hour_u(int(t[i])) < 14]
        if len(ib_idxs) < 4:
            continue
        ib = ib_idxs[:4]
        ib_hi = max(h[i] for i in ib)
        ib_lo = min(l[i] for i in ib)
        if ib_hi <= ib_lo:
            continue
        funnel["n_ib_days"] += 1
        post = [i for i in idxs if hour_u(int(t[i])) >= 14 and hour_u(int(t[i])) < 18]
        if not post:
            continue
        broken_up = False
        broken_dn = False
        break_i = None
        for i in post:
            if h[i] > ib_hi:
                broken_up = True
                break_i = i
                break
            if l[i] < ib_lo:
                broken_dn = True
                break_i = i
                break
        if not (broken_up or broken_dn):
            continue
        funnel["n_break"] += 1
        # fail within next 4 bars: close back inside IB
        fail_i = None
        for k in range(break_i, min(break_i + 5, post[-1] + 1)):
            if k not in idxs and k >= len(c):
                break
            if ib_lo < c[k] < ib_hi:
                fail_i = k
                break
        if fail_i is None:
            continue
        funnel["n_fail"] += 1
        ts = int(t[fail_i])
        if mt5_dow(ts) not in (1, 2, 3, 4):
            continue
        # fade back toward IB mid
        mid = 0.5 * (ib_hi + ib_lo)
        if broken_up:
            direction = -1
            entry = float(o[fail_i + 1]) if fail_i + 1 < len(c) else float(c[fail_i])
            sl = ib_hi + 0.1 * (atr[fail_i] if not math.isnan(atr[fail_i]) else (ib_hi - ib_lo))
        else:
            direction = +1
            entry = float(o[fail_i + 1]) if fail_i + 1 < len(c) else float(c[fail_i])
            sl = ib_lo - 0.1 * (atr[fail_i] if not math.isnan(atr[fail_i]) else (ib_hi - ib_lo))
        dist = abs(entry - sl)
        if dist < 100 * 0.001 or dist > 5000 * 0.001:
            continue
        tp = entry + dist * RR if direction > 0 else entry - dist * RR
        start = fail_i + 1
        r = resolve_trade(direction, entry, sl, tp, start, h, l, c, max_hold=16)
        if r is None:
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1

    m = sim_r(trades)
    verdict, notes = gate(m)
    return {
        "hypothesis_id": "HYP-M15-NYIB-FAIL-FADE-001",
        "symbol": "USDJPY",
        "tf": "M15",
        "funnel": funnel,
        "metrics": m,
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD_KILL_FAST",
    }


def main() -> int:
    if not mt5.initialize():
        raise RuntimeError(mt5.last_error())
    try:
        mt5.symbol_select("USDJPY", True)
        h1 = load("USDJPY", mt5.TIMEFRAME_H1)
        m15 = load("USDJPY", mt5.TIMEFRAME_M15)
        server = mt5.account_info().server if mt5.account_info() else None
    finally:
        mt5.shutdown()

    a = probe_fvg(h1)
    b = probe_nyib_fail(m15)
    payload = {
        "schema_version": "sonic_structural_offline_probes.v3",
        "created_at_utc": utc_now(),
        "status": "OFFLINE_FIRST_V3_COMPLETE",
        "honesty": "NOT_MODEL0_NOT_CONFIRMED_NOT_GOAL",
        "server": server,
        "dedup": "readouts/20260714_STRUCTURAL_V3_DEDUP_CLEARANCE.md",
        "probes": [a, b],
        "offline_survivors": [p["hypothesis_id"] for p in (a, b) if p["verdict"] == "PROBE_SURVIVOR"],
        "any_model0_authorized": any(p["verdict"] == "PROBE_SURVIVOR" for p in (a, b)),
        "phase0_compose": "BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW",
        "best_shelf": "RR2 20260714_194548",
    }
    out = PRE / "20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V3.json"
    write_json(out, payload)
    sha = sha256_file(out)

    md = [
        "# Structural rebuild offline probes V3",
        "",
        f"Generated: {payload['created_at_utc']}",
        "Authority: Owner R&D continue; offline-first; GPT waived",
        "Status: **offline-first**; Model 0 only if `PROBE_SURVIVOR`",
        "",
        "De-dup: `20260714_STRUCTURAL_V3_DEDUP_CLEARANCE.md`",
        "",
        "## Probe C — H1 displace + FVG continuation",
        "",
        f"- ID: `{a['hypothesis_id']}`",
        f"- Funnel: {a['funnel']}",
        f"- N={a['metrics']['n']} PF={a['metrics']['pf']:.4f} tpw={a['metrics']['tpw']:.3f} exp={a['metrics']['exp']:.2f}",
        f"- Cost x1.5 (+$12 base) PF={a['metrics']['pf_x15_cost12']:.4f}",
        f"- Kill notes: {a['kill_notes']}",
        f"- **Verdict: `{a['verdict']}`** · model0={a['model0']}",
        "",
        "## Probe D — M15 NY-IB fail-fade",
        "",
        f"- ID: `{b['hypothesis_id']}`",
        f"- Funnel: {b['funnel']}",
        f"- N={b['metrics']['n']} PF={b['metrics']['pf']:.4f} tpw={b['metrics']['tpw']:.3f} exp={b['metrics']['exp']:.2f}",
        f"- Cost x1.5 (+$12 base) PF={b['metrics']['pf_x15_cost12']:.4f}",
        f"- Kill notes: {b['kill_notes']}",
        f"- **Verdict: `{b['verdict']}`** · model0={b['model0']}",
        "",
        "## Board",
        "",
        "| Probe | Verdict | Model 0 |",
        "|---|---|---|",
        f"| C FVG cont | `{a['verdict']}` | `{a['model0']}` |",
        f"| D NYIB fail-fade | `{b['verdict']}` | `{b['model0']}` |",
        "",
        f"Offline survivors: `{payload['offline_survivors']}`",
        f"Any Model 0 authorized: `{payload['any_model0_authorized']}`",
        "",
        f"Receipt SHA: `{sha}`",
        "",
        "## Phase-0 / best shelf",
        "",
        "Phase-0 compose still blocked. Best shelf RR2 `194548` unchanged.",
        "No densify from these kills.",
    ]
    (READ / "20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V3.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8"
    )

    for p in (a, b):
        with REG.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "record_type": "candidate",
                        "schema_version": 1,
                        "hypothesis_id": p["hypothesis_id"],
                        "state": "killed" if "KILL" in p["verdict"] else "idea",
                        "verdict": p["verdict"],
                        "reason": f"offline V3 {p['metrics']}; notes={p['kill_notes']}",
                        "updated_at": "2026-07-14",
                        "lane": "structural_rebuild_v3_20260714",
                        "symbol": "USDJPY",
                        "timeframe": p["tf"],
                        "model": "offline_closed_bar_probe",
                        "metrics": p["metrics"],
                        "validation": {"model0": p["model0"]},
                        "receipt_sha256": sha,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(json.dumps({"sha": sha, "a": a["verdict"], "b": b["verdict"], "ma": a["metrics"], "mb": b["metrics"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
