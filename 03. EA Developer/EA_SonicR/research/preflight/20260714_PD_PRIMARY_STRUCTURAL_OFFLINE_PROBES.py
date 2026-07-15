#!/usr/bin/env python3
"""NYFed PD as PRIMARY structural sleeve (not RR2 keep/skip gate densify).

A priori frozen (do not mine / do not densify PD WoW sign rule):
  O1 HYP-USDJPY-H1-PD-GS-EXPAND-DISPLACE-001
  O2 HYP-USDJPY-H1-PD-GS-CONTRACT-DISPLACE-001
  O3 HYP-EURJPY-H1-PD-GS-EXPAND-DISPLACE-001

Killed sibling HYP-RR2-NYFED-PD-GS-NETFLOW-GATE-001 filtered RR2 trades;
these objects generate independent H1 displace entries under PD regime bias.
Displace params frozen from WTI structural exo template (not V9 expansion retune).

Joint screen: N, PF, tpw, +$12 x1.5. Model 0 only if PROBE_SURVIVOR.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
EXO = PRE / "v8_exogenous"
PD_PANEL = EXO / "panels" / "nyfed_pd_ust_net_pos_w1_v1.csv"
PD_CONTRACT = EXO / "contracts" / "20260714_NYFED_PD_UST_NET_AVAILABLE_AT_UTC_CONTRACT_V1.json"

OUT_JSON = PRE / "20260714_PD_PRIMARY_STRUCTURAL_OFFLINE_PROBES.json"
OUT_MD = READ / "20260714_PD_PRIMARY_STRUCTURAL_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260714_PD_PRIMARY_STRUCTURAL_DEDUP_CLEARANCE.md"
OUT_CLOSE = READ / "20260714_PD_PRIMARY_STRUCTURAL_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260714_PD_PRIMARY_STRUCTURAL_VN_ACTION_BRIEF.md"
OUT_COST = READ / "20260714_COST_SURFACE_TRACK_GAP_RECONFIRM.md"
OUT_COST_JSON = PRE / "20260714_COST_SURFACE_TRACK_GAP_RECONFIRM.json"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59, 59)
ELAPSED_WEEKS = (TO - FROM).total_seconds() / (7 * 24 * 3600)
DEPOSIT = 100000.0
RISK = 0.005
COST12 = 12.0

# A priori — WTI structural exo template (frozen; do not mine from V9 near-miss)
RANGE_ATR = 1.2
BODY_ATR = 0.55
CLOSE_FRAC = 0.60
SL_ATR = 1.0
RR = 2.0
MAX_HOLD = 12


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def pf_of(pnls: list[float]) -> float | None:
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def haircuts(pnls: list[float], base: float = COST12) -> dict:
    out = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [p - base * mult for p in pnls]
        out[key] = {
            "pf": None if not cut else round(pf_of(cut) or 0.0, 4),
            "net": round(sum(cut), 2) if cut else 0.0,
            "exp": round(sum(cut) / len(cut), 4) if cut else 0.0,
        }
    return out


def metrics(pnls: list[float]) -> dict:
    n = len(pnls)
    p = pf_of(pnls)
    net = sum(pnls) if pnls else 0.0
    tpw = n / ELAPSED_WEEKS if ELAPSED_WEEKS else None
    return {
        "n": n,
        "pf": None if p is None else round(p, 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(tpw, 4) if tpw is not None else None,
    }


def joint_verdict(m: dict, hc: dict) -> tuple[str, list[str]]:
    notes: list[str] = []
    n = m["n"] or 0
    pf = m["pf"] or 0.0
    tpw = m["tpw"] or 0.0
    x15 = (hc.get("x1_5") or {}).get("pf") or 0.0
    if n < 80:
        notes.append("n_fail")
    if not (1.0 <= tpw <= 6.5):
        notes.append("cadence_fail")
    if pf < 1.05:
        notes.append("pf_fail")
    if x15 < 1.10:
        notes.append("stress_fail")
    if (
        n >= 80
        and pf > 1.20
        and 1.5 <= tpw <= 6.0
        and x15 >= 1.15
    ):
        return "PROBE_SURVIVOR", notes
    if notes:
        return "KILLED_AT_OFFLINE_PROBE", notes
    return "KILLED_AT_OFFLINE_PROBE", ["joint_screen_miss"]


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


def load_h1(symbol: str) -> dict:
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, FROM, TO)
    if rates is None or len(rates) < 200:
        raise RuntimeError(f"rates fail {symbol}: {mt5.last_error()}")
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


def sim_r(trades_spec: list[dict]) -> list[float]:
    bal = DEPOSIT
    pnls = []
    for t in trades_spec:
        risk_cash = bal * RISK
        pnl = risk_cash * t["r"]
        pnls.append(pnl)
        bal += pnl
    return pnls


def build_pd_expand_lookup() -> dict[date, bool]:
    """True = expand (wow_delta_mn > 0); False = contract; missing = absent."""
    events: list[tuple[date, float]] = []
    with PD_PANEL.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            wow = (row.get("wow_delta_mn") or "").strip()
            if not wow:
                continue
            avail = date.fromisoformat(row["available_at_utc"][:10])
            events.append((avail, float(wow)))
    events.sort(key=lambda x: x[0])
    out: dict[date, bool] = {}
    last: bool | None = None
    idx = 0
    day = FROM.date()
    end = TO.date()
    while day <= end:
        while idx < len(events) and events[idx][0] <= day:
            last = events[idx][1] > 0.0
            idx += 1
        if last is not None:
            out[day] = last
        day += timedelta(days=1)
    return out


def probe_pd_displace(
    h1: dict,
    pd_expand: dict[date, bool],
    *,
    hypothesis_id: str,
    symbol: str,
    require_expand: bool,
) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades: list[dict] = []
    funnel = {
        "n_regime": 0,
        "n_displace": 0,
        "n_trades": 0,
        "days_used": 0,
        "n_no_pd": 0,
    }
    used_day: set[str] = set()
    # Expand → long-only; contract → short-only (primary PD bias)
    bias = +1 if require_expand else -1
    i = 20
    while i < len(c) - MAX_HOLD - 1:
        if math.isnan(atr[i]) or atr[i] <= 0 or not tradeable(int(t[i])):
            i += 1
            continue
        dkey = datetime.fromtimestamp(int(t[i]), timezone.utc).strftime("%Y-%m-%d")
        if dkey in used_day:
            i += 1
            continue
        d = date.fromisoformat(dkey)
        regime = pd_expand.get(d)
        if regime is None:
            funnel["n_no_pd"] += 1
            i += 1
            continue
        if require_expand and not regime:
            i += 1
            continue
        if (not require_expand) and regime:
            i += 1
            continue
        funnel["n_regime"] += 1
        rng = h[i] - l[i]
        body = abs(c[i] - o[i])
        if rng < RANGE_ATR * atr[i] or body < BODY_ATR * atr[i]:
            i += 1
            continue
        if bias > 0:
            if c[i] < l[i] + CLOSE_FRAC * rng:
                i += 1
                continue
        else:
            if c[i] > h[i] - CLOSE_FRAC * rng:
                i += 1
                continue
        funnel["n_displace"] += 1
        entry = float(c[i])
        if bias > 0:
            sl = entry - SL_ATR * atr[i]
            tp = entry + RR * (entry - sl)
        else:
            sl = entry + SL_ATR * atr[i]
            tp = entry - RR * (sl - entry)
        r = resolve_trade(bias, entry, sl, tp, i + 1, h, l, c, MAX_HOLD, RR)
        if r is None:
            i += 1
            continue
        trades.append({"r": float(r), "t": int(t[i]), "bias": bias, "expand": bool(regime)})
        used_day.add(dkey)
        funnel["n_trades"] += 1
        i += MAX_HOLD
    funnel["days_used"] = len(used_day)
    pnls = sim_r(trades)
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc)
    return {
        "hypothesis_id": hypothesis_id,
        "class": "nyfed_pd_primary_structural_displace",
        "symbol": symbol,
        "tf": "H1",
        "funnel": funnel,
        "metrics": m,
        "haircuts": hc,
        "kill_notes": notes,
        "verdict": verdict,
        "a_priori": {
            "pd_rule": "wow_delta_mn > 0 expand / <=0 contract",
            "lag": "observation+8d (frozen panel available_at)",
            "require_expand": require_expand,
            "bias": "long_only_if_expand" if require_expand else "short_only_if_contract",
            "range_atr": RANGE_ATR,
            "body_atr": BODY_ATR,
            "close_frac": CLOSE_FRAC,
            "sl_atr": SL_ATR,
            "rr": RR,
            "max_hold": MAX_HOLD,
            "fail_closed_missing_pd": True,
            "not_rr2_gate": True,
            "not_pd_wow_densify": True,
        },
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
    }


def write_cost_gap_reconfirm() -> dict[str, Any]:
    """Track A — reconfirm multi-year session×symbol cost surface still GAP."""
    partial = PRE / "20260714_BROKER_SPREAD_COST_TABLE_QFSI.json"
    w7 = PRE / "20260714_BROKER_SPREAD_COST_TABLE_QFSI_W7CONT.json"
    hour = PRE / "20260714_QFSI_TICK_HOUR_SPREAD_DIAGNOSTIC.json"
    payload = {
        "schema": "cost_surface_track_gap_reconfirm.v1",
        "created_at_utc": utc_now(),
        "verdict": "GAP",
        "sha_freeze_eligible_for_research_cost_surface": False,
        "reason": (
            "No reconstructable multi-month/year session×symbol spread/commission "
            "surface on disk. QFSI Real quote ticks = 1 calendar day 2026-07-14; "
            "EURUSD commission unique N=2; USDJPY commission 0; slip fills 0 MISSING≠0. "
            "Tester multi-year 'current' spread and M15 audit summaries are NOT broker "
            "session×hour evidence. Do not invent; do not re-stress RR2 under invented surface."
        ),
        "existing_partial_proxies": {
            "broker_spread_cost_table_qfsi": {
                "path": str(partial.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(partial) if partial.is_file() else None,
                "label": "PARTIAL_SINGLE_DAY_PROXY_NOT_RESEARCH_SURFACE",
            },
            "broker_spread_cost_table_qfsi_w7cont": {
                "path": str(w7.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(w7) if w7.is_file() else None,
                "label": "PARTIAL_SINGLE_DAY_PROXY_NOT_RESEARCH_SURFACE",
            },
            "tick_hour_diagnostic": {
                "path": str(hour.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(hour) if hour.is_file() else None,
                "label": "DIAGNOSTIC_ONLY_NOT_MULTI_YEAR_RESEARCH_COST_SURFACE",
            },
        },
        "missing_for_freeze": {
            "quote_calendar_days_have": 1,
            "quote_calendar_days_need": 90,
            "commission_eurusd_unique_have": 2,
            "commission_per_symbol_need": 30,
            "usdjpy_commission_unique_have": 0,
            "slip_fills_have": 0,
            "slip_fills_need_per_symbol": 100,
        },
        "rr2_restress_under_session_surface": "NOT_RUN_SURFACE_ABSENT",
        "prior_gap_doc": "03. EA Developer/EA_SonicR/research/readouts/20260714_BROKER_SESSION_SPREAD_TABLE_GAP.md",
    }
    write_json(OUT_COST_JSON, payload)
    OUT_COST.write_text(
        f"""# Cost surface track — GAP reconfirm (post PD/MMF/6J)

Date: 2026-07-15  
Status: `GAP / NO_SHA_FREEZE / NO_RR2_RESTRESS`  
Lane: single checkout; no-Git

## Verdict

**GAP.** No honest multi-month/year session×symbol spread/commission research cost
surface is reconstructable from local AlphaFactory / MT5 / QFSI artifacts.

## What was searched

- QFSI Real quote captures under `02. AlphaFactory/evidence/execution/FivePercentOnline-Real/`
  — **1 calendar day** (`2026-07-14`) only; accumulate `006` folder still absent.
- Deal-history imports — EURUSD commission unique **N=2**; USDJPY **0**; slip **0**.
- Partial tables `20260714_BROKER_SPREAD_COST_TABLE_QFSI*.json` — PARTIAL proxy only.
- Hour diagnostic `20260714_QFSI_TICK_HOUR_SPREAD_DIAGNOSTIC.json` — **not** research surface.
- Tester multi-year runs / M15 spread audit summaries — **not** broker session×hour evidence.

## Policy

- Do **not** invent spreads or commission.
- Do **not** SHA-freeze a research cost surface.
- Do **not** re-stress RR2 / near-miss under a fabricated session surface.
- Keep Real QFSI accumulate until ≥90 quote days + commission/slip gates clear.

## Receipt

`{sha256_file(OUT_COST_JSON)}`  
`preflight/20260714_COST_SURFACE_TRACK_GAP_RECONFIRM.json`

`COST_PROVENANCE_GAP` remains **NARROWED_NOT_CLEARED**.
""",
        encoding="utf-8",
    )
    payload["receipt_sha256"] = sha256_file(OUT_COST_JSON)
    write_json(OUT_COST_JSON, payload)
    return payload


def append_registry(objects: list[dict], receipt: str) -> None:
    lines = []
    for o in objects:
        state = "killed" if "KILL" in o["verdict"] else ("parked" if "PARK" in o["verdict"] else "probed")
        if o["verdict"] == "PROBE_SURVIVOR":
            state = "probe_survivor"
        rec = {
            "record_type": "candidate",
            "schema_version": 1,
            "hypothesis_id": o["hypothesis_id"],
            "state": state,
            "verdict": o["verdict"],
            "reason": ",".join(o.get("kill_notes") or []) or o["verdict"],
            "updated_at": "2026-07-15",
            "feature_family": o.get("class"),
            "lane": "pd_primary_structural_20260715",
            "setup_type": o["hypothesis_id"],
            "symbol": o.get("symbol") or "USDJPY",
            "timeframe": o.get("tf") or "H1",
            "window": "2021.01.01-2025.12.31",
            "model": None,
            "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_PD_PRIMARY_STRUCTURAL_OFFLINE_PROBES.md",
            "run_ids": [],
            "metrics": o.get("metrics"),
            "validation": {
                "offline_probe": o["verdict"],
                "kill_notes": o.get("kill_notes"),
                "receipt_sha256": receipt,
            },
            "cost_grade": "UNVERIFIED_OFFLINE_PROXY",
        }
        lines.append(json.dumps(rec, ensure_ascii=False))
    with REG.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def write_docs(payload: dict, objects: list[dict], cost: dict) -> None:
    o1, o2, o3 = objects
    OUT_DEDUP.write_text(
        """# De-dup clearance — NYFed PD primary structural sleeve

Status: `INTAKE_CLEARED / INDEPENDENT` (a priori)

| Object | Vs killed shelf |
|---|---|
| O1 USDJPY PD-expand displace long | ≠ `HYP-RR2-NYFED-PD-GS-NETFLOW-GATE-001` (RR2 keep/skip); ≠ V9 USDJPY expansion bidirectional; ≠ Asia/London box Wave5–7 |
| O2 USDJPY PD-contract displace short | ≠ O1; ≠ RR2 PD gate densify; ≠ WALCL/COT sign gates |
| O3 EURJPY PD-expand displace long | ≠ CHFJPY V9 displace (symbol); ≠ USDJPY O1 (cross sleeve) |

Banned densify remains: PD WoW sign threshold mine · RR2 MaxKZ/RR · Wave1–9 session boxes ·
dichotomy · COT size+|z| · WTI z · WALCL sign · MMF wow · 6J basis z.
""",
        encoding="utf-8",
    )

    rows = []
    for o in objects:
        m = o["metrics"]
        hc = o["haircuts"]
        rows.append(
            f"| `{o['hypothesis_id']}` | {m['n']} | {m['pf']} | {m['tpw']} | "
            f"{(hc.get('x1_5') or {}).get('pf')} | {o['verdict']} |"
        )

    OUT_MD.write_text(
        f"""# Offline probes — NYFed PD primary structural sleeve

Date: 2026-07-15  
Status: `{payload["campaign_status"]}`  
Panel SHA: `{payload["panel_sha256"]}`  
Receipt: `{payload["receipt_sha256"]}`

## Objects (independent sleeve — not RR2 gate)

| ID | N | PF | tpw | x1.5 | Verdict |
|---|---|---|---|---|---|
{chr(10).join(rows)}

## A priori

- PD lag: observation+8d (frozen `available_at`)
- Expand = `wow_delta_mn > 0`; contract otherwise; fail-closed if missing
- Displace: range≥1.2·ATR14, body≥0.55·ATR14, close frac 0.60, SL=1.0·ATR, RR=2, hold≤12 H1, ≤1/day
- **Do not** densify PD WoW sign or V9 expansion thresholds

## Model 0

{"Authorized for survivor only." if payload.get("any_survivor") else "Withheld (no PROBE_SURVIVOR)."}

## Cost track (parallel)

Verdict **{cost["verdict"]}** — see `readouts/20260714_COST_SURFACE_TRACK_GAP_RECONFIRM.md`.
No RR2 re-stress under session surface (surface absent).

Best shelf RR2 `194548`. GOAL unmet.
""",
        encoding="utf-8",
    )

    OUT_CLOSE.write_text(
        f"""# Session closeout — PD primary structural + cost surface track

Date: 2026-07-15  
Status: `{payload["campaign_status"]}`  
Lane: single checkout; no-Git

## Track A — Cost surface

**GAP** reconfirmed. No multi-month/year session×symbol research cost surface.
No SHA-freeze. No RR2 re-stress under invented surface.
Receipt: `{cost.get("receipt_sha256")}`  
`readouts/20260714_COST_SURFACE_TRACK_GAP_RECONFIRM.md`

## Track B — PD primary structural (not RR2 gate)

| ID | Verdict |
|---|---|
| `HYP-USDJPY-H1-PD-GS-EXPAND-DISPLACE-001` | **{o1['verdict']}** |
| `HYP-USDJPY-H1-PD-GS-CONTRACT-DISPLACE-001` | **{o2['verdict']}** |
| `HYP-EURJPY-H1-PD-GS-EXPAND-DISPLACE-001` | **{o3['verdict']}** |

Receipt: `{payload["receipt_sha256"]}`  
Artifacts: `preflight/20260714_PD_PRIMARY_STRUCTURAL_OFFLINE_PROBES.json`

## Model 0

{"Run survivor only." if payload.get("any_survivor") else "Withheld (no PROBE_SURVIVOR)."}

## Next autonomous EV

1. Do **not** densify PD WoW / displace ATR/RR / MMF / 6J.
2. Keep Real QFSI accumulate for cost frontier (still GAP).
3. Next object outside Wave1–9 / dichotomy / COT / WTI / WALCL / PD-MMF-6J gates /
   PD-primary displace killboard.

Best shelf unchanged: RR2 `20260714_194548`. Phase-0 still BLOCKED. GOAL unmet.
""",
        encoding="utf-8",
    )

    OUT_VN.write_text(
        f"""# Brief hành động (VN) — PD primary + cost GAP

## Kết quả
- Cost surface: **GAP** (không SHA-freeze; không re-stress RR2 bằng surface bịa).
- O1 USDJPY PD-expand displace: **{o1['verdict']}** (N={o1['metrics']['n']}, PF={o1['metrics']['pf']}, tpw={o1['metrics']['tpw']}, x1.5={(o1['haircuts'].get('x1_5') or {}).get('pf')})
- O2 USDJPY PD-contract displace: **{o2['verdict']}** (N={o2['metrics']['n']}, PF={o2['metrics']['pf']}, tpw={o2['metrics']['tpw']}, x1.5={(o2['haircuts'].get('x1_5') or {}).get('pf')})
- O3 EURJPY PD-expand displace: **{o3['verdict']}** (N={o3['metrics']['n']}, PF={o3['metrics']['pf']}, tpw={o3['metrics']['tpw']}, x1.5={(o3['haircuts'].get('x1_5') or {}).get('pf')})
- Model 0: {"chỉ survivor" if payload.get("any_survivor") else "**không chạy** (0 survivor)"}

## Việc làm / không làm
- Không densify PD WoW / V9 expansion / MaxKZ/RR.
- Không gate-retune RR2 bằng PD.
- Shelf tốt nhất vẫn RR2 `194548`. GOAL chưa đạt.
""",
        encoding="utf-8",
    )


def main() -> None:
    assert PD_PANEL.is_file(), f"missing PD panel {PD_PANEL}"
    cost = write_cost_gap_reconfirm()
    if not mt5.initialize():
        raise SystemExit(f"MT5_INIT_FAIL:{mt5.last_error()}")
    try:
        usdjpy = load_h1("USDJPY")
        eurjpy = load_h1("EURJPY")
        pd_expand = build_pd_expand_lookup()
        o1 = probe_pd_displace(
            usdjpy,
            pd_expand,
            hypothesis_id="HYP-USDJPY-H1-PD-GS-EXPAND-DISPLACE-001",
            symbol="USDJPY",
            require_expand=True,
        )
        o2 = probe_pd_displace(
            usdjpy,
            pd_expand,
            hypothesis_id="HYP-USDJPY-H1-PD-GS-CONTRACT-DISPLACE-001",
            symbol="USDJPY",
            require_expand=False,
        )
        o3 = probe_pd_displace(
            eurjpy,
            pd_expand,
            hypothesis_id="HYP-EURJPY-H1-PD-GS-EXPAND-DISPLACE-001",
            symbol="EURJPY",
            require_expand=True,
        )
        objects = [o1, o2, o3]
        survivors = [o for o in objects if o["verdict"] == "PROBE_SURVIVOR"]
        payload = {
            "schema": "pd_primary_structural_offline_probes.v1",
            "created_at_utc": utc_now(),
            "campaign_status": (
                "PROBE_SURVIVOR_PRESENT" if survivors else "OFFLINE_ALL_KILL / NO_MODEL0"
            ),
            "authority": (
                "post_PD_MMF_6J_gate_kill; PD as primary structural sleeve not RR2 gate densify; "
                "Model0 only on survivor"
            ),
            "panel_sha256": sha256_file(PD_PANEL),
            "panel_contract_sha256": sha256_file(PD_CONTRACT) if PD_CONTRACT.is_file() else None,
            "cost_track": {
                "verdict": cost["verdict"],
                "receipt_sha256": cost.get("receipt_sha256"),
                "path": str(OUT_COST_JSON.relative_to(ROOT)).replace("\\", "/"),
            },
            "a_priori_params": {
                "range_atr": RANGE_ATR,
                "body_atr": BODY_ATR,
                "close_frac": CLOSE_FRAC,
                "sl_atr": SL_ATR,
                "rr": RR,
                "max_hold": MAX_HOLD,
            },
            "objects": objects,
            "any_survivor": bool(survivors),
            "model0": "AUTHORIZED_IF_SURVIVOR" if survivors else "WITHHELD",
        }
        write_json(OUT_JSON, payload)
        payload["receipt_sha256"] = sha256_file(OUT_JSON)
        write_json(OUT_JSON, payload)
        write_docs(payload, objects, cost)
        append_registry(objects, payload["receipt_sha256"])
        print(json.dumps({
            "campaign_status": payload["campaign_status"],
            "receipt": payload["receipt_sha256"],
            "cost": cost["verdict"],
            "objects": [
                {
                    "id": o["hypothesis_id"],
                    "verdict": o["verdict"],
                    "n": o["metrics"]["n"],
                    "pf": o["metrics"]["pf"],
                    "tpw": o["metrics"]["tpw"],
                    "x15": (o["haircuts"].get("x1_5") or {}).get("pf"),
                }
                for o in objects
            ],
        }, indent=2))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
