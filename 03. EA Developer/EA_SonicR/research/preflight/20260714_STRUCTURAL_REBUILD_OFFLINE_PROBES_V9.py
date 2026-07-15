#!/usr/bin/env python3
"""Structural rebuild offline probes V9 — outside V1–V8 + dichotomy kills.

A priori:
  V9-1 HYP-CHFJPY-H1-DISPLACE-CONT-001
  V9-2 HYP-USDJPY-H1-EXPANSION-BAR-CONT-001
  V9-3 HYP-NZDUSD-H1-ASIA-RANGE-LONDON-FAIL-001

Model 0 withheld unless PROBE_SURVIVOR.
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


def resolve_trade(direction, entry, sl, tp, i_entry, h, l, c, max_hold, rr):
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
            return rr
    j = min(i_entry + max_hold - 1, len(c) - 1)
    return direction * (c[j] - entry) / risk


def sim_r(trades_spec: list[dict], cost: float = COST12) -> dict[str, Any]:
    if not trades_spec:
        return {
            "n": 0,
            "pf": 0.0,
            "tpw": 0.0,
            "exp": 0.0,
            "net": 0.0,
            "pf_x15_cost": 0.0,
            "pf_real_p50_haircut": 0.0,
            "real_p50_usd": 2.31,
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
    if "JPY" in symbol:
        return 0.001
    return 0.0001


def probe_chfjpy_displace(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_displace": 0, "n_trades": 0}
    pt = point_for("CHFJPY")
    rr = 2.5
    i = 20
    while i < len(c) - 8:
        if math.isnan(atr[i]) or atr[i] <= 0:
            i += 1
            continue
        rng = h[i] - l[i]
        if rng < 1.5 * atr[i]:
            i += 1
            continue
        ts = int(t[i])
        if not tradeable(ts):
            i += 1
            continue
        up = c[i] >= l[i] + 0.66 * rng
        dn = c[i] <= l[i] + 0.34 * rng
        if not (up or dn):
            i += 1
            continue
        funnel["n_displace"] += 1
        direction = 1 if up else -1
        entry = float(o[i + 1])
        sl = (l[i] - 0.1 * atr[i]) if up else (h[i] + 0.1 * atr[i])
        dist = abs(entry - sl)
        if dist < 80 * pt or dist > 5000 * pt:
            i += 1
            continue
        tp = entry + dist * rr if up else entry - dist * rr
        r = resolve_trade(direction, entry, sl, tp, i + 1, h, l, c, 16, rr)
        if r is None:
            i += 1
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1
        i += 4
    return pack("HYP-CHFJPY-H1-DISPLACE-CONT-001", "CHFJPY", "H1", funnel, trades)


def probe_usdjpy_expansion(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_exp": 0, "n_trades": 0}
    pt = point_for("USDJPY")
    rr = 2.5
    i = 20
    while i < len(c) - 8:
        if math.isnan(atr[i]) or atr[i] <= 0:
            i += 1
            continue
        rng = h[i] - l[i]
        body = abs(c[i] - o[i])
        if rng < 1.8 * atr[i] or body < 0.60 * rng:
            i += 1
            continue
        ts = int(t[i])
        if not tradeable(ts):
            i += 1
            continue
        up = c[i] >= l[i] + 0.75 * rng and c[i] > o[i]
        dn = c[i] <= l[i] + 0.25 * rng and c[i] < o[i]
        if not (up or dn):
            i += 1
            continue
        funnel["n_exp"] += 1
        direction = 1 if up else -1
        entry = float(o[i + 1])
        sl = (l[i] - 0.1 * atr[i]) if up else (h[i] + 0.1 * atr[i])
        dist = abs(entry - sl)
        if dist < 80 * pt or dist > 4000 * pt:
            i += 1
            continue
        tp = entry + dist * rr if up else entry - dist * rr
        r = resolve_trade(direction, entry, sl, tp, i + 1, h, l, c, 16, rr)
        if r is None:
            i += 1
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1
        i += 4
    return pack("HYP-USDJPY-H1-EXPANSION-BAR-CONT-001", "USDJPY", "H1", funnel, trades)


def probe_nzd_asia_fail(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_days": 0, "n_break": 0, "n_fail": 0, "n_trades": 0}
    pt = point_for("NZDUSD")
    # group by day
    by_day: dict[str, list[int]] = {}
    for i in range(len(t)):
        by_day.setdefault(day_key(int(t[i])), []).append(i)
    for dk, idxs in by_day.items():
        asia = [i for i in idxs if 0 <= hour_u(int(t[i])) < 6]
        if len(asia) < 3:
            continue
        funnel["n_days"] += 1
        a_hi = max(h[i] for i in asia)
        a_lo = min(l[i] for i in asia)
        a_mid = 0.5 * (a_hi + a_lo)
        if a_hi - a_lo < 20 * pt:
            continue
        london = [i for i in idxs if 7 <= hour_u(int(t[i])) <= 10]
        for bi in london:
            if not tradeable(int(t[bi])):
                continue
            up_brk = c[bi] > a_hi
            dn_brk = c[bi] < a_lo
            if not (up_brk or dn_brk):
                continue
            funnel["n_break"] += 1
            # fail back inside within 3 bars
            fail_i = None
            for k in range(1, 4):
                j = bi + k
                if j >= len(c):
                    break
                if up_brk and c[j] < a_hi:
                    fail_i = j
                    break
                if dn_brk and c[j] > a_lo:
                    fail_i = j
                    break
            if fail_i is None:
                continue
            funnel["n_fail"] += 1
            # fade toward mid — signal on fail bar close; enter next open
            direction = -1 if up_brk else 1
            entry_i = min(fail_i, len(c) - 2)
            if math.isnan(atr[entry_i]) or atr[entry_i] <= 0:
                continue
            entry = float(o[entry_i + 1])
            if direction < 0:
                sl = max(h[bi], h[entry_i]) + 0.1 * atr[entry_i]
                tp = a_mid
                if entry <= tp:
                    continue
            else:
                sl = min(l[bi], l[entry_i]) - 0.1 * atr[entry_i]
                tp = a_mid
                if entry >= tp:
                    continue
            dist = abs(entry - sl)
            if dist < 30 * pt or dist > 3000 * pt:
                continue
            # RR from mid distance
            rr = abs(tp - entry) / dist
            if rr < 1.2:
                continue
            r = resolve_trade(direction, entry, sl, tp, entry_i + 1, h, l, c, 12, rr)
            if r is None:
                continue
            trades.append({"r": r})
            funnel["n_trades"] += 1
            break  # one per day
    return pack(
        "HYP-NZDUSD-H1-ASIA-RANGE-LONDON-FAIL-001",
        "NZDUSD",
        "H1",
        funnel,
        trades,
        cost=12.0,
    )


def main() -> int:
    if not mt5.initialize():
        raise SystemExit(f"MT5_INIT_FAIL:{mt5.last_error()}")
    try:
        chf = load("CHFJPY", mt5.TIMEFRAME_H1)
        uj = load("USDJPY", mt5.TIMEFRAME_H1)
        nzd = load("NZDUSD", mt5.TIMEFRAME_H1)
        acc = mt5.account_info()
        server = getattr(acc, "server", None)
        login = getattr(acc, "login", None)
    finally:
        mt5.shutdown()

    probes = [
        probe_chfjpy_displace(chf),
        probe_usdjpy_expansion(uj),
        probe_nzd_asia_fail(nzd),
    ]
    survivors = [p["hypothesis_id"] for p in probes if p["verdict"] == "PROBE_SURVIVOR"]
    parks = [p["hypothesis_id"] for p in probes if p["verdict"] == "PARK_OFFLINE"]
    payload = {
        "schema_version": "sonic_structural_offline_probes.v9",
        "created_at_utc": utc_now(),
        "status": "OFFLINE_FIRST_V9_COMPLETE",
        "honesty": "NOT_MODEL0_NOT_CONFIRMED_NOT_GOAL",
        "server": server,
        "login": login,
        "dedup": "readouts/20260714_STRUCTURAL_V9_DEDUP_CLEARANCE.md",
        "prior": "dichotomy_break 3/3 KILL; V8 empty; RR2 231750 PARK_MISS",
        "probes": probes,
        "offline_survivors": survivors,
        "offline_parks": parks,
        "any_model0_authorized": bool(survivors),
        "phase0_compose": "BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW",
        "best_shelf": "RR2 20260714_194548 (historical); current Model0 231750 weaker",
        "banned": [
            "densify_rr2_maxkz_atr_spark_session",
            "retune_v1_v8",
            "retune_dichotomy_be_yield_corrcap",
            "model0_on_kill",
            "h4_outside_rerun",
        ],
    }
    out = PRE / "20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V9.json"
    write_json(out, payload)
    sha = sha256_file(out)

    lines = [
        "# Structural rebuild offline probes V9",
        "",
        f"Generated: {payload['created_at_utc']}",
        "Authority: Owner GOAL after RR2 PARK_MISS + dichotomy empty; GPT waived",
        "Status: **offline-first**; Model 0 only if `PROBE_SURVIVOR`",
        "",
        "De-dup: `20260714_STRUCTURAL_V9_DEDUP_CLEARANCE.md`",
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
        "- Dichotomy D1–D3 already KILL (BE exit / yield-z / CorrCap).",
        "- Best shelf historical RR2 `194548`; current same-ID Model0 `231750` PARK_MISS.",
        "- Do not densify V9 params. Phase-0 still BLOCKED.",
    ]
    (READ / "20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V9.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    # registry: prereg + outcome
    for p in probes:
        state = (
            "killed"
            if "KILL" in p["verdict"]
            else ("parked" if "PARK" in p["verdict"] else "preregistered")
        )
        prereg_map = {
            "HYP-CHFJPY-H1-DISPLACE-CONT-001": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_CHFJPY_H1_DISPLACE_CONT_001_PREREG.md",
            "HYP-USDJPY-H1-EXPANSION-BAR-CONT-001": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_USDJPY_H1_EXPANSION_BAR_CONT_001_PREREG.md",
            "HYP-NZDUSD-H1-ASIA-RANGE-LONDON-FAIL-001": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_NZDUSD_H1_ASIA_RANGE_LONDON_FAIL_001_PREREG.md",
        }
        with REG.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "record_type": "candidate",
                        "schema_version": 1,
                        "hypothesis_id": p["hypothesis_id"],
                        "state": state,
                        "verdict": p["verdict"],
                        "reason": f"offline V9; notes={p['kill_notes']}; metrics={ {k: (round(v,4) if isinstance(v, float) else v) for k,v in p['metrics'].items()} }",
                        "updated_at": "2026-07-14",
                        "lane": "structural_rebuild_v9_20260714",
                        "symbol": p["symbol"],
                        "timeframe": p["tf"],
                        "model": "offline_closed_bar_probe",
                        "prereg_path": prereg_map[p["hypothesis_id"]],
                        "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V9.md",
                        "metrics": {
                            k: (float(v) if hasattr(v, "item") else v)
                            for k, v in p["metrics"].items()
                        },
                        "validation": {"model0": p["model0"]},
                        "receipt_sha256": sha,
                        "dedup": "readouts/20260714_STRUCTURAL_V9_DEDUP_CLEARANCE.md",
                        "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
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
