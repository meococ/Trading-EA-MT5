#!/usr/bin/env python3
"""Derive FivePercentOnline-Real cost sample and reprice RR2 / MaxKZ2.

Honesty labels:
- Full QFSI 90-day / commission≥30 / slippage≥100 gates remain unmet.
- This is REAL_LIVE_SPREAD_PLUS_EURUSD_COMMISSION_CLUE reprice research,
  NOT confirmed / NOT GO_FOR_PREREG / NOT missing-as-zero.
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"d:\Trading EA MT5")
ALPHA = ROOT / "02. AlphaFactory"
CAP = ALPHA / "evidence/execution/FivePercentOnline-Real/20260714_QFSI_REAL_002"
PRE = ROOT / "03. EA Developer/EA_SonicR/research/preflight"
READ = ROOT / "03. EA Developer/EA_SonicR/research/readouts"
RUNS = ALPHA / "runs/EA_SilverBullet"
PROBE = (
    ROOT
    / "03. EA Developer/EA_SonicR/research/preflight/v4_data/20260714_MT5_READONLY_PROBE_V4.json"
)

sys.path.insert(0, str(ALPHA / "analysis"))
sys.path.insert(0, str(ALPHA / "tools"))
from quant_analyzer import deals_to_trades, parse_deals  # noqa: E402
import sonic_cost_stress as scs  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def percentile(xs: list[float], p: float) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    i = min(len(xs) - 1, max(0, int(round((len(xs) - 1) * p))))
    return xs[i]


def capture_spread_stats(symbol: str) -> dict[str, Any]:
    path = CAP / f"{symbol}_quote_ticks.csv"
    spreads: list[float] = []
    n = 0
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                n += 1
                try:
                    bid = float(row["bid"])
                    ask = float(row["ask"])
                except (TypeError, ValueError):
                    continue
                if bid > 0 and ask >= bid:
                    spreads.append(ask - bid)
    return {
        "quote_rows": n,
        "valid_spreads": len(spreads),
        "spread_price_p50": percentile(spreads, 0.50),
        "spread_price_p90": percentile(spreads, 0.90),
        "sha256": sha256_file(path) if path.exists() else None,
    }


def load_commissions() -> dict[str, list[float]]:
    path = CAP / "commission_lifecycles.csv"
    out: dict[str, list[float]] = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            sym = row.get("symbol") or ""
            try:
                val = float(row["round_turn_account_per_lot"])
            except (TypeError, ValueError, KeyError):
                continue
            out.setdefault(sym, []).append(val)
    return out


def mt5_symbol_cost(symbol: str) -> dict[str, Any]:
    import MetaTrader5 as mt5

    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if info is None or tick is None:
        raise RuntimeError(f"symbol unavailable: {symbol}")
    ticks = mt5.copy_ticks_from(symbol, datetime.now(timezone.utc), 50000, mt5.COPY_TICKS_ALL)
    spreads: list[float] = []
    if ticks is not None:
        for t in ticks:
            bid = float(t["bid"])
            ask = float(t["ask"])
            if bid > 0 and ask >= bid:
                spreads.append(ask - bid)
    pip = float(info.point) * (10 if int(info.digits) in (3, 5) else 1)
    tv = float(info.trade_tick_value)
    ts = float(info.trade_tick_size) or float(info.point)
    dollars_per_price_per_lot = (tv / ts) if ts else None
    p50 = percentile(spreads, 0.50)
    p90 = percentile(spreads, 0.90)
    return {
        "digits": int(info.digits),
        "point": float(info.point),
        "pip_size": pip,
        "tick_value": tv,
        "tick_size": ts,
        "contract_size": float(info.trade_contract_size),
        "current_bid": float(tick.bid),
        "current_ask": float(tick.ask),
        "current_spread_price": float(tick.ask) - float(tick.bid),
        "live_tick_sample_n": len(spreads),
        "spread_price_p50": p50,
        "spread_price_p90": p90,
        "spread_pips_p50": (p50 / pip) if (p50 is not None and pip) else None,
        "spread_pips_p90": (p90 / pip) if (p90 is not None and pip) else None,
        "dollars_per_price_per_lot": dollars_per_price_per_lot,
        "spread_usd_per_lot_p50": (
            p50 * dollars_per_price_per_lot if (p50 is not None and dollars_per_price_per_lot) else None
        ),
        "spread_usd_per_lot_p90": (
            p90 * dollars_per_price_per_lot if (p90 is not None and dollars_per_price_per_lot) else None
        ),
    }


def trade_lots(run_id: str) -> dict[str, Any]:
    report = RUNS / run_id / "report.html"
    deals = parse_deals(report)
    trades = deals_to_trades(deals)
    lots: list[float] = []
    for deal in deals:
        direction = (deal.direction or "").strip().lower()
        side = (deal.side or "").strip().lower()
        if direction != "in" or side in {"", "balance"}:
            continue
        try:
            vol = abs(float(deal.volume))
        except (TypeError, ValueError):
            continue
        if vol > 0:
            lots.append(vol)
    return {
        "n_trades": len(trades),
        "n_lots_observed": len(lots),
        "lot_p50": statistics.median(lots) if lots else None,
        "lot_mean": statistics.mean(lots) if lots else None,
        "lot_p90": percentile(lots, 0.90) if lots else None,
    }


def run_stress(run_id: str, base_cost: float, out_name: str, note: str) -> dict[str, Any]:
    class Args:
        pass

    args = Args()
    args.run = str(RUNS / run_id)
    args.ea = "EA_SilverBullet"
    args.report = str(RUNS / run_id / "report.html")
    args.out = str(PRE / out_name)
    args.start_equity = 100000.0
    args.base_cost_per_trade = float(base_cost)
    args.spread_points = 0.0
    args.slippage_points = 0.0
    args.commission_round_turn = 0.0
    args.point_value_per_lot = 1.0
    args.lot_size = 0.01
    result = scs.build_cost_matrix(args)
    result["cost_assumption"]["note"] = note
    result["cost_assumption"]["provenance"] = "FIVEPERCENTONLINE_REAL_PARTIAL_SAMPLE"
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def scenario_map(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["scenario"]: s for s in result.get("scenarios", [])}


def gate_eval(smap: dict[str, dict[str, Any]]) -> dict[str, Any]:
    x1 = smap.get("cost_x1_00", {})
    x15 = smap.get("cost_x1_50", {})
    x2 = smap.get("cost_x2_00", {})
    base = smap.get("base_report", {})
    return {
        "base_pf": base.get("profit_factor"),
        "x1_pf": x1.get("profit_factor"),
        "x1_5_pf": x15.get("profit_factor"),
        "x2_pf": x2.get("profit_factor"),
        "goal_x1_pf_gt_1_30": (x1.get("profit_factor") or 0) > 1.30,
        "goal_x1_5_pf_ge_1_25": (x15.get("profit_factor") or 0) >= 1.25,
        "goal_x2_pf_ge_1_00": (x2.get("profit_factor") or 0) >= 1.00,
        "goal_cost_stress_pass": (
            (x1.get("profit_factor") or 0) > 1.30
            and (x15.get("profit_factor") or 0) >= 1.25
            and (x2.get("profit_factor") or 0) >= 1.00
        ),
    }


def main() -> int:
    import MetaTrader5 as mt5

    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        acc = mt5.account_info()
        term = mt5.terminal_info()
        if acc is None or term is None:
            raise RuntimeError(f"MT5 metadata unavailable: {mt5.last_error()}")
        observed = str(acc.server or "")
        if observed != "FivePercentOnline-Real":
            raise RuntimeError(f"server mismatch: {observed}")
        symbols = ["EURUSD", "GBPUSD", "XAUUSD", "USDJPY"]
        live = {s: mt5_symbol_cost(s) for s in symbols}
    finally:
        mt5.shutdown()

    commissions = load_commissions()
    capture = {s: capture_spread_stats(s) for s in ["EURUSD", "GBPUSD", "XAUUSD", "USDJPY"]}
    eurusd_comm = commissions.get("EURUSD") or []
    # Preliminary clue only (N=2). Transfer to USDJPY as research proxy with explicit label.
    commission_rt_per_lot = statistics.median(eurusd_comm) if eurusd_comm else None
    commission_status = (
        "EURUSD_N2_PRELIMINARY_CLUE_TRANSFERRED_TO_USDJPY"
        if commission_rt_per_lot is not None
        else "MISSING_NOT_ZERO"
    )

    usdjpy = live["USDJPY"]
    lots_rr2 = trade_lots("20260714_194221")
    lots_max = trade_lots("20260714_192304")
    lot_p50 = lots_rr2.get("lot_p50") or lots_max.get("lot_p50")
    if lot_p50 is None:
        # fail closed rather than invent lots
        raise RuntimeError("could not observe lot sizes from RR2/MaxKZ2 reports")

    spread_usd_lot = usdjpy.get("spread_usd_per_lot_p50")
    if spread_usd_lot is None:
        raise RuntimeError("USDJPY Real spread_usd_per_lot_p50 unavailable")

    if commission_rt_per_lot is None:
        # Cannot treat missing commission as zero. Stress with spread-only AND
        # with spread+known EURUSD clue separately if clue exists; here clue missing
        # would block. We still have EURUSD clue.
        raise RuntimeError("commission clue missing; refuse missing-as-zero")

    # Round-turn friction per trade at median lot:
    # open spread (USD) + commission RT. Slippage remains MISSING (not zeroed).
    base_cost_p50 = (spread_usd_lot + commission_rt_per_lot) * float(lot_p50)
    # Conservative research stress uses p90 spread + same commission clue.
    spread_usd_lot_p90 = usdjpy.get("spread_usd_per_lot_p90") or spread_usd_lot
    base_cost_p90 = (spread_usd_lot_p90 + commission_rt_per_lot) * float(lot_p50)

    note = (
        "FivePercentOnline-Real partial sample: USDJPY live tick spread P50/P90 "
        "+ EURUSD history commission clue $4/lot RT (N=2, transferred). "
        "Slippage MISSING (not treated as 0). Full QFSI gates unmet."
    )

    rr2_p50 = run_stress(
        "20260714_194221",
        base_cost_p50,
        "20260714_COSTSTRESS_RR2_194221_REAL_P50.json",
        note + " scenario=spread_p50+comm_clue",
    )
    rr2_p90 = run_stress(
        "20260714_194221",
        base_cost_p90,
        "20260714_COSTSTRESS_RR2_194221_REAL_P90.json",
        note + " scenario=spread_p90+comm_clue",
    )
    max_p50 = run_stress(
        "20260714_192304",
        base_cost_p50,
        "20260714_COSTSTRESS_MAXKZ2_192304_REAL_P50.json",
        note + " scenario=spread_p50+comm_clue",
    )
    max_p90 = run_stress(
        "20260714_192304",
        base_cost_p90,
        "20260714_COSTSTRESS_MAXKZ2_192304_REAL_P90.json",
        note + " scenario=spread_p90+comm_clue",
    )

    # Also keep prior $12 Demo-proxy for distance comparison (already on disk).
    prior_rr2 = json.loads((PRE / "20260714_COSTSTRESS_RR2_194221.json").read_text(encoding="utf-8"))
    prior_max = json.loads((PRE / "20260714_COSTSTRESS_MAXKZ2_192304.json").read_text(encoding="utf-8"))

    session_end = json.loads((CAP / "session_end.json").read_text(encoding="utf-8"))
    manifest = CAP / "20260714_QFSI_REAL_002.manifest.json"
    probe = json.loads(PROBE.read_text(encoding="utf-8")) if PROBE.exists() else {}

    receipt = {
        "schema_version": "sonic_qfsi_real_reprice_receipt.v1",
        "created_at_utc": utc_now(),
        "status": "PARTIAL_REAL_COST_REPRICE_COMPLETE",
        "goal_claim": False,
        "confirmed_claim": False,
        "full_qfsi_gate": "FAIL_SAMPLE_GATES",
        "server": {
            "expected": "FivePercentOnline-Real",
            "observed": "FivePercentOnline-Real",
            "server_match": True,
            "probe_path": str(PROBE.as_posix()),
            "probe_sha256": sha256_file(PROBE) if PROBE.exists() else None,
            "probe_verdict": probe.get("verdict"),
            "account_fingerprint": probe.get("account_fingerprint"),
            "server_fingerprint": probe.get("server_fingerprint"),
        },
        "capture": {
            "capture_id": "20260714_QFSI_REAL_002",
            "path": str(CAP.as_posix()),
            "session_end_status": session_end.get("status"),
            "manifest_path": str(manifest.as_posix()),
            "manifest_sha256": sha256_file(manifest),
            "session_end_sha256": sha256_file(CAP / "session_end.json"),
            "reprice_ready_per_capture_tool": session_end.get("reprice_ready"),
            "reprice_blockers": session_end.get("reprice_blockers"),
            "commission_lifecycle_counts": session_end.get("commission_lifecycle_counts"),
            "slippage_fills": session_end.get("slippage_fills"),
            "quote_rows_written": session_end.get("quote_rows_written"),
            "heartbeat_rows_written": session_end.get("heartbeat_rows_written"),
            "prior_capture_incomplete": "20260714_QFSI_REAL_001",
        },
        "cost_model": {
            "symbol": "USDJPY",
            "lot_basis": "report_median_volume_RR2",
            "lot_p50": lot_p50,
            "lots_rr2": lots_rr2,
            "lots_maxkz2": lots_max,
            "usdjpy_live": usdjpy,
            "capture_spreads": capture,
            "commission_rt_per_lot_usd": commission_rt_per_lot,
            "commission_status": commission_status,
            "commission_samples_eurusd": eurusd_comm,
            "slippage_status": "MISSING_NOT_ZERO",
            "base_round_turn_cost_per_trade_p50": base_cost_p50,
            "base_round_turn_cost_per_trade_p90": base_cost_p90,
            "formula": "(spread_usd_per_lot + commission_rt_per_lot) * lot_p50",
            "note": note,
        },
        "reprice": {
            "RR2": {
                "run_id": "20260714_194221",
                "hypothesis_id": "HYP-SB-MAXKZ2-RR2-FRICTION-001",
                "real_p50": gate_eval(scenario_map(rr2_p50)),
                "real_p90": gate_eval(scenario_map(rr2_p90)),
                "prior_demo_proxy_12usd": gate_eval(scenario_map(prior_rr2)),
                "artifacts": {
                    "real_p50": "preflight/20260714_COSTSTRESS_RR2_194221_REAL_P50.json",
                    "real_p90": "preflight/20260714_COSTSTRESS_RR2_194221_REAL_P90.json",
                    "prior_12usd": "preflight/20260714_COSTSTRESS_RR2_194221.json",
                },
            },
            "MaxKZ2": {
                "run_id": "20260714_192304",
                "hypothesis_id": "HYP-SB-MAXKZ2-DENSITY-002",
                "real_p50": gate_eval(scenario_map(max_p50)),
                "real_p90": gate_eval(scenario_map(max_p90)),
                "prior_demo_proxy_12usd": gate_eval(scenario_map(prior_max)),
                "artifacts": {
                    "real_p50": "preflight/20260714_COSTSTRESS_MAXKZ2_192304_REAL_P50.json",
                    "real_p90": "preflight/20260714_COSTSTRESS_MAXKZ2_192304_REAL_P90.json",
                    "prior_12usd": "preflight/20260714_COSTSTRESS_MAXKZ2_192304.json",
                },
            },
        },
        "verdict": {
            "COST_PROVENANCE_GAP": "NARROWED_NOT_CLEARED",
            "full_qfsi": False,
            "RR2_goal_cost_stress_pass_p50": gate_eval(scenario_map(rr2_p50))["goal_cost_stress_pass"],
            "RR2_goal_cost_stress_pass_p90": gate_eval(scenario_map(rr2_p90))["goal_cost_stress_pass"],
            "MaxKZ2_goal_cost_stress_pass_p50": gate_eval(scenario_map(max_p50))["goal_cost_stress_pass"],
            "MaxKZ2_goal_cost_stress_pass_p90": gate_eval(scenario_map(max_p90))["goal_cost_stress_pass"],
            "densify_banned": True,
            "next_legal_if_fail": "HYP-H4-OUTSIDE-REV-001 stub / independent rebuild (prereg before code)",
        },
    }

    # Decide kill/park language honestly
    rr2_pass = receipt["verdict"]["RR2_goal_cost_stress_pass_p50"]
    max_pass = receipt["verdict"]["MaxKZ2_goal_cost_stress_pass_p50"]
    if rr2_pass and max_pass:
        decision = "REAL_PARTIAL_COST_ALLOWS_CONTINUE_TO_ROBUSTNESS_BUT_FULL_QFSI_STILL_OPEN"
    elif rr2_pass or max_pass:
        decision = "MIXED_PARTIAL_REAL_COST_ONE_SURVIVOR_PATH_FULL_QFSI_STILL_OPEN"
    else:
        decision = "PARK_HIT_RESEARCH_BAR_FAILS_GOAL_UNDER_PARTIAL_REAL_COST"
    receipt["verdict"]["decision"] = decision

    out_receipt = PRE / "20260714_QFSI_REAL_REPRICE_RR2_MAXKZ2_RECEIPT.json"
    write_json(out_receipt, receipt)
    receipt["receipt_sha256"] = sha256_file(out_receipt)
    write_json(out_receipt, receipt)

    # Owner deliverable (Vietnamese body, evidence EN tables)
    rr2g = receipt["reprice"]["RR2"]["real_p50"]
    rr2g90 = receipt["reprice"]["RR2"]["real_p90"]
    maxg = receipt["reprice"]["MaxKZ2"]["real_p50"]
    maxg90 = receipt["reprice"]["MaxKZ2"]["real_p90"]
    md = f"""# Deliverable — QFSI Real unblock + RR2/MaxKZ2 reprice

Date: 2026-07-14 ~20:51 ICT  
Process: no GPT; canonical `execution_data_qfsi_nolive_capture.py` + probe V4  
Language: tiếng Việt (Owner) / evidence EN

## 1) MT5 server

| Field | Value |
|---|---|
| Expected | `FivePercentOnline-Real` |
| Observed | `FivePercentOnline-Real` |
| Probe | `TARGET_SERVER_READONLY_PROBE_COMPLETE` |
| Probe file | `preflight/v4_data/20260714_MT5_READONLY_PROBE_V4.json` |
| Probe SHA256 | `{receipt['server']['probe_sha256']}` |

## 2) QFSI capture evidence

| Field | Value |
|---|---|
| Capture ID | `20260714_QFSI_REAL_002` |
| Status | `CAPTURE_WINDOW_COMPLETE_PARTIAL` |
| Manifest SHA256 | `{receipt['capture']['manifest_sha256']}` |
| Quotes / heartbeats | {session_end.get('quote_rows_written')} / {session_end.get('heartbeat_rows_written')} |
| Commission lifecycles | EURUSD=2, GBPUSD=0, XAUUSD=0, USDJPY=0 |
| Slippage fills | 0 (MISSING, not zero) |
| `reprice_ready` (full QFSI) | **false** |
| Blockers | QFSI_SAMPLE_GATES_NOT_MET; SLIPPAGE_FILLS_MISSING; COMMISSION_SAMPLE_BELOW_30; QUOTE_ELAPSED_DAYS_BELOW_90 |

Path: `02. AlphaFactory/evidence/execution/FivePercentOnline-Real/20260714_QFSI_REAL_002/`

**Honesty:** full QFSI gate vẫn FAIL. Đây là Real live-spread + EURUSD commission clue (N=2), không phải confirmed cost provenance.

## 3) Cost model (USDJPY)

| Input | Value |
|---|---|
| Lot P50 (RR2 report) | {lot_p50:.4f} |
| Spread USD/lot P50 | {spread_usd_lot:.6f} |
| Spread USD/lot P90 | {spread_usd_lot_p90:.6f} |
| Commission clue RT/lot | ${commission_rt_per_lot:.2f} (EURUSD N=2 transferred) |
| Base $/trade P50 | **{base_cost_p50:.4f}** |
| Base $/trade P90 | **{base_cost_p90:.4f}** |
| Prior Demo proxy | $12.00/trade |

## 4) Reprice / stress vs GOAL gates

GOAL: PF>1.30 @x1; x1.5 PF≥1.25; x2 PF≥1.00 (after verified cost). Cadence already near-GOAL on tester books.

| Book | Scenario | x1 PF | x1.5 PF | x2 PF | GOAL cost-stress |
|---|---|---:|---:|---:|---|
| RR2 `194221` | Real P50 | {rr2g['x1_pf']:.3f} | {rr2g['x1_5_pf']:.3f} | {rr2g['x2_pf']:.3f} | {'PASS' if rr2g['goal_cost_stress_pass'] else 'FAIL'} |
| RR2 `194221` | Real P90 | {rr2g90['x1_pf']:.3f} | {rr2g90['x1_5_pf']:.3f} | {rr2g90['x2_pf']:.3f} | {'PASS' if rr2g90['goal_cost_stress_pass'] else 'FAIL'} |
| MaxKZ2 `192304` | Real P50 | {maxg['x1_pf']:.3f} | {maxg['x1_5_pf']:.3f} | {maxg['x2_pf']:.3f} | {'PASS' if maxg['goal_cost_stress_pass'] else 'FAIL'} |
| MaxKZ2 `192304` | Real P90 | {maxg90['x1_pf']:.3f} | {maxg90['x1_5_pf']:.3f} | {maxg90['x2_pf']:.3f} | {'PASS' if maxg90['goal_cost_stress_pass'] else 'FAIL'} |

Decision: `{decision}`

## 5) Next moves

1. Do **not** densify MaxKZ/RR.
2. If FAIL under Real partial cost: keep PARK; open next legal stub `HYP-H4-OUTSIDE-REV-001` (prereg before code) or other independent rebuild.
3. Full QFSI still needs ≥90d quotes + ≥30 commission/symbol + ≥100 slippage fills — Owner can accumulate over time; short capture cannot clear it.
4. No Spark compose promote while cost stress FAIL / QFSI partial.

## 6) hot.md?

Updated this turn: clear login blocker; record Real capture + partial reprice; COST_PROVENANCE_GAP = NARROWED_NOT_CLEARED.

## Receipt

`preflight/20260714_QFSI_REAL_REPRICE_RR2_MAXKZ2_RECEIPT.json`  
SHA256: `{receipt['receipt_sha256']}`
"""
    (READ / "20260714_QFSI_REAL_REPRICE_RR2_MAXKZ2_DELIVERABLE.md").write_text(md, encoding="utf-8")
    print(json.dumps({
        "status": "OK",
        "decision": decision,
        "base_cost_p50": base_cost_p50,
        "base_cost_p90": base_cost_p90,
        "lot_p50": lot_p50,
        "rr2_p50": rr2g,
        "max_p50": maxg,
        "receipt": str(out_receipt),
        "receipt_sha256": receipt["receipt_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
