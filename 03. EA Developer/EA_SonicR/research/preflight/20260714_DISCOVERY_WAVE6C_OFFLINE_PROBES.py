#!/usr/bin/env python3
"""Wave6C — a priori FX3 portfolio of three-day HL break (promote path from PARK).

Same frozen rule as HYP-H1-THREE-DAY-HIGHLOW-BREAK-001 on EURUSD+USDJPY+GBPUSD.
NOT densify of lookback/RR/body. New ID for multi-symbol cadence lift.
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
COST12 = 12.0
RR = 3.0
HID = "HYP-FX3-H1-THREE-DAY-HL-BREAK-PORTFOLIO-001"


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


def day_key(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def tradeable(ts: int) -> bool:
    return mt5_dow(ts) in (1, 2, 3, 4) and hour_u(ts) < 22


def min_dist(symbol: str) -> float:
    return 0.03 if "JPY" in symbol else 0.0003


def max_dist(symbol: str) -> float:
    return 2.0 if "JPY" in symbol else 0.02


def resolve(direction, entry, sl, tp, i0, h, l, c, max_hold):
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    for j in range(i0, min(i0 + max_hold, len(c))):
        hi, lo = h[j], l[j]
        if (direction > 0 and lo <= sl) or (direction < 0 and hi >= sl):
            return -1.0
        if (direction > 0 and hi >= tp) or (direction < 0 and lo <= tp):
            return float(RR)
    j = min(i0 + max_hold - 1, len(c) - 1)
    return direction * (c[j] - entry) / risk


def sim_r(trades: list[dict]) -> dict[str, Any]:
    if not trades:
        return {
            "n": 0,
            "pf": 0.0,
            "tpw": 0.0,
            "exp": 0.0,
            "net": 0.0,
            "pf_x15_cost12": 0.0,
            "pf_x2_cost12": 0.0,
        }
    bal = DEPOSIT
    pnls = []
    for t in trades:
        pnl = bal * RISK * t["r"]
        pnls.append(pnl)
        bal += pnl
    wins = [p for p in pnls if p > 0]
    losses = [-p for p in pnls if p < 0]
    pf = (sum(wins) / sum(losses)) if losses else (999.0 if wins else 0.0)
    n = len(pnls)

    def pf_at(mult: float) -> float:
        adj = [p - mult * COST12 for p in pnls]
        w = [p for p in adj if p > 0]
        l = [-p for p in adj if p < 0]
        return (sum(w) / sum(l)) if l else (999.0 if w else 0.0)

    return {
        "n": n,
        "pf": float(pf),
        "tpw": n / ELAPSED_WEEKS,
        "exp": sum(pnls) / n,
        "net": sum(pnls),
        "pf_x15_cost12": float(pf_at(1.5)),
        "pf_x2_cost12": float(pf_at(2.0)),
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
    if (
        m["pf"] > 1.30
        and 2.0 <= m["tpw"] <= 5.0
        and m["pf_x15_cost12"] >= 1.25
        and m["pf_x2_cost12"] >= 1.00
    ):
        return "PROBE_SURVIVOR", notes
    return "PARK_OFFLINE", notes


def trades_for_symbol(symbol: str, h1: dict, d1: dict) -> list[dict]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    dmap = {}
    for i in range(len(d1["time"])):
        dmap[day_key(int(d1["time"][i]))] = (float(d1["high"][i]), float(d1["low"][i]))
    days_sorted = sorted(dmap.keys())
    day_to_idx = {d: i for i, d in enumerate(days_sorted)}
    out = []
    taken = set()
    for i in range(40, len(c) - 3):
        if not tradeable(int(t[i])):
            continue
        dk = day_key(int(t[i]))
        if dk in taken:
            continue
        if dk not in day_to_idx or day_to_idx[dk] < 3:
            continue
        di = day_to_idx[dk]
        prior = days_sorted[di - 3 : di]
        if len(prior) < 3:
            continue
        phi = max(dmap[d][0] for d in prior)
        plo = min(dmap[d][1] for d in prior)
        if math.isnan(atr[i]) or atr[i] <= 0:
            continue
        body = abs(c[i] - o[i])
        if body < 0.5 * atr[i]:
            continue
        up = c[i] > phi
        dn = c[i] < plo
        if not (up or dn):
            continue
        if i + 1 >= len(c) - 1 or not tradeable(int(t[i + 1])):
            continue
        direction = 1 if up else -1
        entry = float(o[i + 1])
        extreme = plo if up else phi
        sl = extreme - 0.1 * atr[i] if up else extreme + 0.1 * atr[i]
        dist = abs(entry - sl)
        if dist < min_dist(symbol) or dist > max_dist(symbol):
            continue
        tp = entry + dist * RR if up else entry - dist * RR
        r = resolve(direction, entry, sl, tp, i + 1, h, l, c, 24)
        if r is None:
            continue
        out.append({"r": r, "ts": int(t[i + 1]), "symbol": symbol})
        taken.add(dk)
    return out


def main() -> int:
    if not mt5.initialize():
        raise SystemExit(f"MT5 init fail: {mt5.last_error()}")
    try:
        acc = mt5.account_info()
        syms = ("EURUSD", "USDJPY", "GBPUSD")
        raw = []
        per = {}
        for s in syms:
            tlist = trades_for_symbol(s, load(s, mt5.TIMEFRAME_H1), load(s, mt5.TIMEFRAME_D1))
            per[s] = len(tlist)
            raw.extend(tlist)
    finally:
        mt5.shutdown()

    raw.sort(key=lambda x: x["ts"])
    # a priori: max 1 trade per symbol-day already; pool all
    kept = [{"r": t["r"]} for t in raw]
    m = sim_r(kept)
    verdict, notes = gate(m)
    probe = {
        "hypothesis_id": HID,
        "symbol": "EURUSD+USDJPY+GBPUSD",
        "tf": "H1",
        "funnel": {"per_symbol": per, "n_pooled": len(kept)},
        "metrics": m,
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
        "parent_note": "a priori multi-symbol promote path from PARK HYP-H1-THREE-DAY-HIGHLOW-BREAK-001; same frozen rule",
    }
    out = {
        "schema_version": "sonic_discovery_wave6c_offline_probes.v1",
        "created_at_utc": utc_now(),
        "status": "OFFLINE_WAVE6C_COMPLETE",
        "honesty": "NOT_MODEL0_NOT_CONFIRMED_NOT_GOAL",
        "dedup": "readouts/20260714_DISCOVERY_WAVE6B_DEDUP_CLEARANCE.md",
        "server": getattr(acc, "server", None) if acc else None,
        "login": getattr(acc, "login", None) if acc else None,
        "probes": [probe],
        "survivors": [HID] if verdict == "PROBE_SURVIVOR" else [],
        "model0_authorized": verdict == "PROBE_SURVIVOR",
    }
    jp = PRE / "20260714_DISCOVERY_WAVE6C_OFFLINE_PROBES.json"
    write_json(jp, out)
    sha = sha256_file(jp)
    out["receipt_sha256"] = sha
    write_json(jp, out)

    md = f"""# Discovery Wave6C — FX3 three-day HL portfolio

Generated: {out['created_at_utc']}
Receipt SHA: `{sha}`

| ID | N | PF | tpw | x1.5 | x2 | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `{HID}` | {m['n']} | {m['pf']:.3f} | {m['tpw']:.2f} | {m['pf_x15_cost12']:.3f} | {m['pf_x2_cost12']:.3f} | **{verdict}** |

Funnel: {probe['funnel']} notes={notes}
Parent PARK: `HYP-H1-THREE-DAY-HIGHLOW-BREAK-001` (USDJPY-only tpw~1.02).
Same frozen 3-day HL + body≥0.5ATR + RR3 — **no param densify**.
"""
    (READ / "20260714_DISCOVERY_WAVE6C_OFFLINE_PROBES.md").write_text(md, encoding="utf-8")

    # prereg stub freeze
    (READ.parent / "preregs" / "20260714_H_FX3_H1_THREE_DAY_HL_BREAK_PORTFOLIO_001_PREREG.md").write_text(
        f"""# Prereg — {HID}

Date: 2026-07-14 · Wave6C · FROZEN · GPT waived

Equal a priori pool EURUSD+USDJPY+GBPUSD of frozen three-day HL break rule
(parent PARK `HYP-H1-THREE-DAY-HIGHLOW-BREAK-001`). Not body/RR/lookback densify.
Gates: joint Wave6 screen. Model0 iff PROBE_SURVIVOR.
""",
        encoding="utf-8",
    )

    with REG.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "record_type": "candidate",
                    "schema_version": 1,
                    "hypothesis_id": HID,
                    "state": "killed"
                    if "KILL" in verdict
                    else ("parked" if "PARK" in verdict else "probe"),
                    "parent_candidate": "HYP-H1-THREE-DAY-HIGHLOW-BREAK-001",
                    "feature_family": "fx3_h1_three_day_hl_break_portfolio",
                    "lane": "discovery_wave6_20260714",
                    "setup_type": HID,
                    "symbol": "EURUSD+USDJPY+GBPUSD",
                    "timeframe": "H1",
                    "window": "2021.01.01-2025.12.31",
                    "metrics": m,
                    "validation": {
                        "offline_probe": verdict,
                        "kill_notes": notes,
                        "model0": probe["model0"],
                    },
                    "verdict": verdict,
                    "cost_grade": "UNVERIFIED_OFFLINE_PROXY",
                    "updated_at": "2026-07-14",
                    "receipt_sha256": sha,
                    "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_DISCOVERY_WAVE6C_OFFLINE_PROBES.md",
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    print(json.dumps({"sha": sha, "verdict": verdict, "m": {
        "n": m["n"], "pf": round(m["pf"], 3), "tpw": round(m["tpw"], 2),
        "x15": round(m["pf_x15_cost12"], 3), "x2": round(m["pf_x2_cost12"], 3),
        "notes": notes,
    }}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
