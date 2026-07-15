#!/usr/bin/env python3
"""PWHL reclaim + H4 balance offline probes (sibling to parallel V4 five-pack).

Collision-safe filenames (not V4/V5 shared slots).
NOT Model 0. Kill-fast offline.
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
STEM = "20260714_STRUCTURAL_PWHL_H4BAL_OFFLINE_PROBES"

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
    return {
        k: rates[k].astype(float) if k != "time" else rates[k].astype(np.int64)
        for k in ("time", "open", "high", "low", "close")
    }


def mt5_dow(ts: int) -> int:
    return (datetime.fromtimestamp(ts, timezone.utc).weekday() + 1) % 7


def hour_u(ts: int) -> int:
    return datetime.fromtimestamp(ts, timezone.utc).hour


def week_key(ts: int) -> str:
    iso = datetime.fromtimestamp(ts, timezone.utc).isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def sim_r(trades_spec: list[dict]) -> dict[str, Any]:
    if not trades_spec:
        return {
            "n": 0, "pf": 0.0, "tpw": 0.0, "exp": 0.0, "net": 0.0,
            "pf_cost12": 0.0, "pf_x15_cost12": 0.0, "exp_x15_cost12": 0.0,
        }
    bal = DEPOSIT
    pnls = []
    for t in trades_spec:
        pnl = bal * RISK * t["r"]
        pnls.append(pnl)
        bal += pnl
    wins = [p for p in pnls if p > 0]
    losses = [-p for p in pnls if p < 0]
    pf = (sum(wins) / sum(losses)) if losses else (999.0 if wins else 0.0)
    net = sum(pnls)
    n = len(pnls)
    pnls12 = [p - COST12 for p in pnls]
    w12 = [p for p in pnls12 if p > 0]
    l12 = [-p for p in pnls12 if p < 0]
    pf12 = (sum(w12) / sum(l12)) if l12 else 0.0
    pnls125 = [p - 1.5 * COST12 for p in pnls]
    w125 = [p for p in pnls125 if p > 0]
    l125 = [-p for p in pnls125 if p < 0]
    pf125 = (sum(w125) / sum(l125)) if l125 else 0.0
    return {
        "n": n, "pf": float(pf), "tpw": n / ELAPSED_WEEKS,
        "exp": float(net / n), "net": float(net),
        "pf_cost12": float(pf12), "pf_x15_cost12": float(pf125),
        "exp_x15_cost12": float(sum(pnls125) / n) if n else 0.0,
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
        hi, lo = h[j], l[j]
        hit_sl = (direction > 0 and lo <= sl) or (direction < 0 and hi >= sl)
        hit_tp = (direction > 0 and hi >= tp) or (direction < 0 and lo <= tp)
        if hit_sl or (hit_sl and hit_tp):
            return -1.0
        if hit_tp:
            return RR
    j = min(i_entry + max_hold - 1, len(c) - 1)
    return direction * (c[j] - entry) / risk


def build_prior_week_levels(h1: dict) -> dict[str, tuple[float, float]]:
    t, h, l = h1["time"], h1["high"], h1["low"]
    by_week: dict[str, list[int]] = {}
    for i, ts in enumerate(t):
        by_week.setdefault(week_key(int(ts)), []).append(i)
    weeks = sorted(by_week.keys())
    week_hl = {
        wk: (float(max(h[i] for i in idxs)), float(min(l[i] for i in idxs)))
        for wk, idxs in by_week.items()
    }
    return {weeks[i]: week_hl[weeks[i - 1]] for i in range(1, len(weeks))}


def probe_pwhl(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    prior = build_prior_week_levels(h1)
    trades, funnel = [], {"n_weeks": 0, "n_sweep": 0, "n_reclaim": 0, "n_trades": 0}
    used, last_i, seen = set(), -999, set()
    for i in range(30, len(c) - 3):
        ts = int(t[i])
        wk = week_key(ts)
        if wk not in prior:
            continue
        if wk not in seen:
            seen.add(wk)
            funnel["n_weeks"] += 1
        if wk in used or math.isnan(atr[i]) or atr[i] <= 0:
            continue
        if mt5_dow(ts) not in (1, 2, 3, 4) or hour_u(ts) >= 21 or i - last_i < 4:
            continue
        pwh, pwl = prior[wk]
        up, dn = h[i] > pwh + 0.05 * atr[i], l[i] < pwl - 0.05 * atr[i]
        if not (up or dn):
            continue
        funnel["n_sweep"] += 1
        reclaim_i = direction = None
        extreme = 0.0
        if up:
            for j in range(i, min(i + 4, len(c) - 2)):
                if pwl < c[j] < pwh:
                    reclaim_i, direction = j, -1
                    extreme = float(max(h[k] for k in range(i, j + 1)))
                    break
        else:
            for j in range(i, min(i + 4, len(c) - 2)):
                if pwl < c[j] < pwh:
                    reclaim_i, direction = j, +1
                    extreme = float(min(l[k] for k in range(i, j + 1)))
                    break
        if reclaim_i is None:
            continue
        funnel["n_reclaim"] += 1
        entry_i = reclaim_i + 1
        entry = float(o[entry_i])
        sl = extreme + 0.15 * atr[reclaim_i] if direction < 0 else extreme - 0.15 * atr[reclaim_i]
        dist = abs(entry - sl)
        if dist < 0.10 or dist > 5.0:
            continue
        tp = entry - dist * RR if direction < 0 else entry + dist * RR
        r = resolve_trade(direction, entry, sl, tp, entry_i, h, l, c, 24)
        if r is None:
            continue
        trades.append({"r": float(r)})
        funnel["n_trades"] += 1
        used.add(wk)
        last_i = entry_i
    m = sim_r(trades)
    verdict, notes = gate(m)
    return {
        "hypothesis_id": "HYP-W1-PWHL-SWEEP-RECLAIM-H1-001",
        "symbol": "USDJPY", "tf": "H1", "funnel": funnel, "metrics": m,
        "kill_notes": notes, "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD_KILL_FAST",
    }


def probe_balance(h4: dict, h1: dict) -> dict[str, Any]:
    h4h, h4l, h4c, h4t = h4["high"], h4["low"], h4["close"], h4["time"]
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr_h4, atr_h1 = atr14(h4h, h4l, h4c), atr14(h, l, c)
    trades, funnel = [], {"n_balance": 0, "n_break": 0, "n_accept": 0, "n_trades": 0}
    BAL_LEN, MULT, last_i = 6, 1.25, -999
    i_h4 = BAL_LEN
    while i_h4 < len(h4c) - 2:
        if math.isnan(atr_h4[i_h4]) or atr_h4[i_h4] <= 0:
            i_h4 += 1
            continue
        window = range(i_h4 - BAL_LEN + 1, i_h4 + 1)
        bal_hi = float(max(h4h[k] for k in window))
        bal_lo = float(min(h4l[k] for k in window))
        atr_med = float(np.nanmedian([atr_h4[k] for k in window]))
        if atr_med <= 0 or (bal_hi - bal_lo) > MULT * atr_med:
            i_h4 += 1
            continue
        funnel["n_balance"] += 1
        start = int(np.searchsorted(t, int(h4t[i_h4]) + 4 * 3600, side="left"))
        if start >= len(c) - 3:
            i_h4 += 1
            continue
        break_i = direction = None
        for i in range(start, min(start + 12, len(c) - 3)):
            ts = int(t[i])
            if mt5_dow(ts) not in (1, 2, 3, 4) or hour_u(ts) >= 21:
                continue
            if c[i] > bal_hi:
                break_i, direction = i, +1
                break
            if c[i] < bal_lo:
                break_i, direction = i, -1
                break
        if break_i is None:
            i_h4 += 1
            continue
        funnel["n_break"] += 1
        accept_i = break_i + 1
        if accept_i >= len(c) - 2:
            i_h4 += 1
            continue
        if direction > 0 and not (c[accept_i] > bal_hi):
            i_h4 += 1
            continue
        if direction < 0 and not (c[accept_i] < bal_lo):
            i_h4 += 1
            continue
        funnel["n_accept"] += 1
        if accept_i - last_i < 6:
            i_h4 += 1
            continue
        entry_i = accept_i + 1
        entry = float(o[entry_i])
        a = atr_h1[accept_i] if not math.isnan(atr_h1[accept_i]) else (bal_hi - bal_lo)
        if direction > 0:
            sl = min(bal_lo - 0.1 * a, float(l[break_i]) - 0.05 * a)
            tp = entry + abs(entry - sl) * RR
        else:
            sl = max(bal_hi + 0.1 * a, float(h[break_i]) + 0.05 * a)
            tp = entry - abs(entry - sl) * RR
        dist = abs(entry - sl)
        if dist < 0.10 or dist > 5.0:
            i_h4 += 1
            continue
        r = resolve_trade(direction, entry, sl, tp, entry_i, h, l, c, 24)
        if r is None:
            i_h4 += 1
            continue
        trades.append({"r": float(r)})
        funnel["n_trades"] += 1
        last_i = entry_i
        i_h4 = max(i_h4 + BAL_LEN, i_h4 + 1)
    m = sim_r(trades)
    verdict, notes = gate(m)
    return {
        "hypothesis_id": "HYP-H4-BALANCE-BREAK-H1-ACCEPT-001",
        "symbol": "USDJPY", "tf": "H4→H1", "funnel": funnel, "metrics": m,
        "kill_notes": notes, "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD_KILL_FAST",
    }


def main() -> int:
    if not mt5.initialize():
        raise RuntimeError(mt5.last_error())
    try:
        mt5.symbol_select("USDJPY", True)
        h1 = load("USDJPY", mt5.TIMEFRAME_H1)
        h4 = load("USDJPY", mt5.TIMEFRAME_H4)
        server = mt5.account_info().server if mt5.account_info() else None
    finally:
        mt5.shutdown()

    a, b = probe_pwhl(h1), probe_balance(h4, h1)
    payload = {
        "schema_version": "sonic_structural_offline_probes.pwhl_h4bal.v1",
        "created_at_utc": utc_now(),
        "status": "OFFLINE_PWHL_H4BAL_COMPLETE",
        "honesty": "NOT_MODEL0_NOT_CONFIRMED_NOT_GOAL",
        "server": server,
        "dedup": "readouts/20260714_STRUCTURAL_PWHL_H4BAL_DEDUP_CLEARANCE.md",
        "sibling_note": "Parallel V4 five-pack remains at STRUCTURAL_REBUILD_OFFLINE_PROBES_V4.*; this batch is independent.",
        "probes": [a, b],
        "offline_survivors": [p["hypothesis_id"] for p in (a, b) if p["verdict"] == "PROBE_SURVIVOR"],
        "any_model0_authorized": any(p["verdict"] == "PROBE_SURVIVOR" for p in (a, b)),
        "phase0_compose": "BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW",
        "best_shelf": "RR2 20260714_194548",
    }
    out = PRE / f"{STEM}.json"
    write_json(out, payload)
    sha = sha256_file(out)
    md = [
        "# Structural offline probes — PWHL reclaim + H4 balance",
        "",
        f"Generated: {payload['created_at_utc']}",
        "Sibling to parallel V4 five-pack (do not overwrite V4 paths).",
        "De-dup: `20260714_STRUCTURAL_PWHL_H4BAL_DEDUP_CLEARANCE.md`",
        "",
        f"## E `{a['hypothesis_id']}`",
        f"- Funnel {a['funnel']}",
        f"- N={a['metrics']['n']} PF={a['metrics']['pf']:.4f} tpw={a['metrics']['tpw']:.3f} exp={a['metrics']['exp']:.2f}",
        f"- x1.5@$12 PF={a['metrics']['pf_x15_cost12']:.4f} notes={a['kill_notes']}",
        f"- **{a['verdict']}** model0={a['model0']}",
        "",
        f"## F `{b['hypothesis_id']}`",
        f"- Funnel {b['funnel']}",
        f"- N={b['metrics']['n']} PF={b['metrics']['pf']:.4f} tpw={b['metrics']['tpw']:.3f} exp={b['metrics']['exp']:.2f}",
        f"- x1.5@$12 PF={b['metrics']['pf_x15_cost12']:.4f} notes={b['kill_notes']}",
        f"- **{b['verdict']}** model0={b['model0']}",
        "",
        f"Survivors: `{payload['offline_survivors']}` · Model0 authorized: `{payload['any_model0_authorized']}`",
        f"Receipt SHA: `{sha}`",
        "",
        "Best shelf RR2 `194548` unchanged. No densify.",
    ]
    (READ / f"{STEM}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    for p in (a, b):
        with REG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "record_type": "candidate", "schema_version": 1,
                "hypothesis_id": p["hypothesis_id"],
                "state": "killed" if "KILL" in p["verdict"] else "idea",
                "verdict": p["verdict"],
                "reason": (
                    f"offline PWHL_H4BAL n={p['metrics']['n']} pf={p['metrics']['pf']:.4f} "
                    f"tpw={p['metrics']['tpw']:.3f} x15={p['metrics']['pf_x15_cost12']:.4f}; "
                    f"notes={p['kill_notes']}"
                ),
                "updated_at": "2026-07-14",
                "lane": "structural_pwhl_h4bal_20260714",
                "feature_family": p["hypothesis_id"].lower().replace("-", "_"),
                "symbol": "USDJPY", "timeframe": p["tf"],
                "model": "offline_closed_bar_probe", "metrics": p["metrics"],
                "validation": {"model0": p["model0"]},
                "receipt_sha256": sha,
                "readout_path": f"03. EA Developer/EA_SonicR/research/readouts/{STEM}.md",
            }, ensure_ascii=False) + "\n")
    print(json.dumps({"sha": sha, "e": a, "f": b}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
