#!/usr/bin/env python3
"""ONE thesis: USDJPY H1 JPY-cross catch-up (EURJPY+GBPJPY confirm, USDJPY lag).

NOT Path A AUDJPY densify. NOT GBPJPY-lead densify. NOT Model 0 unless survivor.
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
RR = 2.5
COST12 = 12.0
POINT = 0.001
HYP = "HYP-USDJPY-H1-JPY-CROSS-CATCHUP-001"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


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


def sim_r(trades_spec: list[dict]) -> dict[str, Any]:
    if not trades_spec:
        return {
            "n": 0,
            "pf": 0.0,
            "tpw": 0.0,
            "exp": 0.0,
            "net": 0.0,
            "pf_x15_cost12": 0.0,
            "exp_x15_cost12": 0.0,
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
        "pf_x15_cost12": pf125,
        "exp_x15_cost12": sum(pnls125) / n,
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
    if m["pf"] > 1.30 and 2.0 <= m["tpw"] <= 5.0 and m["pf_x15_cost12"] >= 1.25:
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


def align_by_time(*series_list):
    """Inner-join bars on exact unix time; return list of index tuples."""
    maps = []
    for s in series_list:
        m = {int(s["time"][i]): i for i in range(len(s["time"]))}
        maps.append(m)
    common = set(maps[0].keys())
    for m in maps[1:]:
        common &= set(m.keys())
    times = sorted(common)
    return [(t, tuple(m[t] for m in maps)) for t in times]


def probe_catchup(uj, ej, gj) -> dict[str, Any]:
    aligned = align_by_time(uj, ej, gj)
    atr_u = atr14(uj["high"], uj["low"], uj["close"])
    atr_e = atr14(ej["high"], ej["low"], ej["close"])
    atr_g = atr14(gj["high"], gj["low"], gj["close"])

    trades = []
    funnel = {"n_aligned": len(aligned), "n_dual_impulse": 0, "n_lag": 0, "n_trades": 0}
    last_day = None

    for k in range(20, len(aligned) - 2):
        t, (iu, ie, ig) = aligned[k]
        if not tradeable(int(t)):
            continue
        if (
            math.isnan(atr_u[iu])
            or math.isnan(atr_e[ie])
            or math.isnan(atr_g[ig])
            or atr_u[iu] <= 0
            or atr_e[ie] <= 0
            or atr_g[ig] <= 0
        ):
            continue

        body_e = ej["close"][ie] - ej["open"][ie]
        body_g = gj["close"][ig] - gj["open"][ig]
        body_u = uj["close"][iu] - uj["open"][iu]

        # dual leader impulse same direction
        if abs(body_e) < 1.0 * atr_e[ie] or abs(body_g) < 1.0 * atr_g[ig]:
            continue
        if (body_e > 0) != (body_g > 0):
            continue
        funnel["n_dual_impulse"] += 1
        direction = +1 if body_e > 0 else -1

        # follower quiet (lag)
        if abs(body_u) > 0.35 * atr_u[iu]:
            continue
        funnel["n_lag"] += 1

        day = datetime.fromtimestamp(int(t), timezone.utc).strftime("%Y-%m-%d")
        if day == last_day:
            continue

        # next bar on USDJPY
        t_next, (iu2, _, _) = aligned[k + 1]
        if iu2 != iu + 1:
            # require contiguous H1 on follower
            if int(uj["time"][iu + 1]) != int(t_next):
                continue
            iu2 = iu + 1

        entry = float(uj["open"][iu2])
        atr_e2 = atr_u[iu]  # use signal-bar ATR
        sl = entry - 1.25 * atr_e2 if direction > 0 else entry + 1.25 * atr_e2
        dist = abs(entry - sl)
        if dist < 100 * POINT or dist > 5000 * POINT:
            continue
        tp = entry + dist * RR if direction > 0 else entry - dist * RR
        r = resolve_trade(
            direction, entry, sl, tp, iu2, uj["high"], uj["low"], uj["close"], 16
        )
        if r is None:
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1
        last_day = day

    m = sim_r(trades)
    verdict, notes = gate(m)
    return {
        "hypothesis_id": HYP,
        "symbol": "USDJPY",
        "lead_confirm": ["EURJPY", "GBPJPY"],
        "tf": "H1",
        "funnel": funnel,
        "metrics": m,
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
    }


def main() -> int:
    if not mt5.initialize():
        raise SystemExit(f"MT5 init fail: {mt5.last_error()}")
    try:
        # ensure symbols selected
        for sym in ("USDJPY", "EURJPY", "GBPJPY"):
            if not mt5.symbol_select(sym, True):
                raise SystemExit(f"symbol_select fail {sym}: {mt5.last_error()}")
        uj = load("USDJPY", mt5.TIMEFRAME_H1)
        ej = load("EURJPY", mt5.TIMEFRAME_H1)
        gj = load("GBPJPY", mt5.TIMEFRAME_H1)
        result = probe_catchup(uj, ej, gj)
    finally:
        mt5.shutdown()

    out = {
        "generated_at_utc": utc_now(),
        "authority": "Owner one-thesis mandate; Path A blocked; GPT waived",
        "why_chosen": (
            "AUDJPY-lead already V1 KILL; GBPJPY-lead PARK; Real off. "
            "Single JPY-factor catch-up: dual EURJPY+GBPJPY impulse + USDJPY quiet lag."
        ),
        "dedup": "readouts/20260714_JPY_CROSS_CATCHUP_DEDUP_CLEARANCE.md",
        "path_a_status": "BLOCKED_V1_OFFLINE_KILL_HYP-AUDJPY-LEAD-USDJPY-H1-001",
        "rr": RR,
        "result": result,
        "survivors": [result["hypothesis_id"]] if result["verdict"] == "PROBE_SURVIVOR" else [],
        "any_model0_authorized": result["verdict"] == "PROBE_SURVIVOR",
        "best_shelf": "RR2 20260714_194548",
    }
    json_path = PRE / "20260714_JPY_CROSS_CATCHUP_OFFLINE_PROBE.json"
    write_json(json_path, out)
    sha = sha256_bytes(json_path.read_bytes())
    out["receipt_sha256"] = sha
    write_json(json_path, out)

    m = result["metrics"]
    md = f"""# Offline probe — {HYP}

Generated: {out['generated_at_utc']}  
Authority: Owner one-thesis; Path A blocked; GPT waived  
De-dup: `20260714_JPY_CROSS_CATCHUP_DEDUP_CLEARANCE.md`

## Why chosen

- Path A AUDJPY-lead = V1 offline **KILL** (no reopen).
- GBPJPY-lead = Wave4 **PARK** (no densify).
- Real/QFSI skipped (no terminal; no stall).
- One mechanism: **JPY-factor catch-up** (EURJPY+GBPJPY confirm, USDJPY lag).

## Result

| Metric | Value |
|---|---|
| N | {m['n']} |
| PF | {m['pf']:.3f} |
| tpw | {m['tpw']:.2f} |
| +$12×1.5 PF | {m['pf_x15_cost12']:.3f} |
| Verdict | **{result['verdict']}** |
| Model0 | `{result['model0']}` |

Funnel: `{result['funnel']}`  
Kill notes: `{result['kill_notes']}`  
Receipt SHA: `{sha}`

## Policy

Do **not** densify body/ATR/lag thresholds from this readout.
Best shelf RR2 `194548`.
"""
    (READ / "20260714_JPY_CROSS_CATCHUP_OFFLINE_PROBE.md").write_text(md, encoding="utf-8")

    state = (
        "probe_survivor"
        if result["verdict"] == "PROBE_SURVIVOR"
        else ("parked" if result["verdict"] == "PARK_OFFLINE" else "killed")
    )
    with REG.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "record_type": "candidate",
                    "schema_version": 1,
                    "hypothesis_id": HYP,
                    "state": state,
                    "parent_candidate": "ONE_THESIS_POST_V7",
                    "feature_family": "usdjpy_h1_jpy_cross_factor_catchup",
                    "lane": "one_thesis_jpy_catchup_20260714",
                    "setup_type": "EURJPY+GBPJPY dual impulse + USDJPY quiet lag catch-up",
                    "symbol": "USDJPY",
                    "timeframe": "H1",
                    "window": "2021.01.01-2025.12.31",
                    "model": None,
                    "prereg_path": None,
                    "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_JPY_CROSS_CATCHUP_OFFLINE_PROBE.md",
                    "run_ids": [],
                    "metrics": m,
                    "validation": {
                        "offline_probe": result["verdict"],
                        "kill_notes": result["kill_notes"],
                        "path_a": "blocked_v1_kill",
                    },
                    "verdict": result["verdict"],
                    "cost_grade": "UNVERIFIED_OFFLINE_PROXY",
                    "updated_at": "2026-07-14",
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    print(
        json.dumps(
            {
                "receipt_sha256": sha,
                "verdict": result["verdict"],
                "n": m["n"],
                "pf": round(m["pf"], 3),
                "tpw": round(m["tpw"], 2),
                "stress": round(m["pf_x15_cost12"], 3),
                "notes": result["kill_notes"],
                "model0": result["model0"],
                "funnel": result["funnel"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
