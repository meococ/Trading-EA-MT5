#!/usr/bin/env python3
"""Lot-scale partial Real cost stress for A1 + Spark (+ MaxKZ2/RR2 cross-check).

Uses unit cost from latest RR2/MaxKZ2 Real reprice receipt:
  (USDJPY live spread_usd/lot P50 + EURUSD commission clue RT/lot) * book lot_p50.

Honesty: PARTIAL only. Full QFSI unmet. Slippage MISSING ≠ 0. Not confirmed.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"d:\Trading EA MT5")
ALPHA = ROOT / "02. AlphaFactory"
PRE = ROOT / "03. EA Developer/EA_SonicR/research/preflight"
PARENT = PRE / "20260714_QFSI_REAL_REPRICE_RR2_MAXKZ2_RECEIPT.json"

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


def lot_stats(ea: str, run_id: str) -> dict[str, Any]:
    report = ALPHA / "runs" / ea / run_id / "report.html"
    deals = parse_deals(report)
    trades = deals_to_trades(deals)
    lots: list[float] = []
    for deal in deals:
        if (deal.direction or "").strip().lower() != "in":
            continue
        if (deal.side or "").strip().lower() in {"", "balance"}:
            continue
        try:
            vol = abs(float(deal.volume))
        except (TypeError, ValueError):
            continue
        if vol > 0:
            lots.append(vol)
    return {
        "n_trades": len(trades),
        "lot_p50": statistics.median(lots) if lots else None,
        "lot_mean": statistics.mean(lots) if lots else None,
    }


def stress(ea: str, run_id: str, label: str, base_cost: float, note: str) -> dict[str, Any]:
    class Args:
        pass

    args = Args()
    args.run = str(ALPHA / "runs" / ea / run_id)
    args.ea = ea
    args.report = str(ALPHA / "runs" / ea / run_id / "report.html")
    out_name = f"20260714_COSTSTRESS_{label.upper()}_{run_id}_REAL_P50_LOTSCALE.json"
    out_path = PRE / out_name
    args.out = str(out_path)
    args.start_equity = 100000.0
    args.base_cost_per_trade = float(base_cost)
    args.spread_points = 0.0
    args.slippage_points = 0.0
    args.commission_round_turn = 0.0
    args.point_value_per_lot = 1.0
    args.lot_size = 0.01
    matrix = scs.build_cost_matrix(args)
    matrix["cost_assumption"]["note"] = note
    matrix["cost_assumption"]["provenance"] = "FIVEPERCENTONLINE_REAL_PARTIAL_SAMPLE_LOTSCALE"
    out_path.write_text(json.dumps(matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    smap = {s["scenario"]: s for s in matrix.get("scenarios", [])}
    x1 = smap.get("cost_x1_00", {})
    x15 = smap.get("cost_x1_50", {})
    x2 = smap.get("cost_x2_00", {})
    base = smap.get("base_report", {})
    return {
        "run_id": run_id,
        "ea": ea,
        "base_cost_per_trade": base_cost,
        "out": str(out_path.as_posix()),
        "out_sha256": sha256_file(out_path),
        "base_pf": base.get("profit_factor"),
        "x1_pf": x1.get("profit_factor"),
        "x1_5_pf": x15.get("profit_factor"),
        "x2_pf": x2.get("profit_factor"),
        "goal_cost_stress_pass": (
            (x1.get("profit_factor") or 0) > 1.30
            and (x15.get("profit_factor") or 0) >= 1.25
            and (x2.get("profit_factor") or 0) >= 1.00
        ),
    }


def main() -> int:
    parent = json.loads(PARENT.read_text(encoding="utf-8"))
    cm = parent["cost_model"]
    spread = float(cm["usdjpy_live"]["spread_usd_per_lot_p50"])
    # commission clue from parent receipt
    comm = float(cm.get("commission_rt_per_lot") or cm.get("commission_clue_rt_per_lot") or 4.0)
    if "commission_clue" in cm and isinstance(cm["commission_clue"], dict):
        if cm["commission_clue"].get("round_turn_account_per_lot_p50") is not None:
            comm = float(cm["commission_clue"]["round_turn_account_per_lot_p50"])
    unit = spread + comm
    note = (
        f"FivePercentOnline-Real PARTIAL lot-scaled: (USDJPY spread_usd/lot P50 {spread:.6f} + "
        f"EURUSD commission clue ${comm:.2f}/lot RT N=2) * book lot_p50. "
        "Slippage MISSING (not zero). Full QFSI gates unmet. Not confirmed."
    )

    books = [
        ("EA_SilverBullet", "20260714_002505", "A1"),
        ("EA_M15SparkAsian", "20260714_193358", "SPARK100K"),
        ("EA_SilverBullet", "20260714_192304", "MAXKZ2"),
        ("EA_SilverBullet", "20260714_194221", "RR2"),
    ]
    results: dict[str, Any] = {}
    for ea, run_id, label in books:
        ls = lot_stats(ea, run_id)
        lot = ls["lot_p50"]
        if lot is None:
            results[label] = {"error": "no_lots", **ls}
            continue
        base_cost = unit * float(lot)
        stressed = stress(ea, run_id, label, base_cost, note)
        stressed.update(ls)
        stressed["unit_usd_per_lot"] = unit
        results[label] = stressed

    out = {
        "schema_version": "sonic_qfsi_real_reprice_a1_spark_extension.v1",
        "created_at_utc": utc_now(),
        "status": "PARTIAL_REAL_COST_LOTSCALE_COMPLETE",
        "goal_claim": False,
        "confirmed_claim": False,
        "full_qfsi_gate": "FAIL_SAMPLE_GATES",
        "cost_unit": {
            "spread_usd_per_lot_p50": spread,
            "commission_rt_per_lot": comm,
            "unit_usd_per_lot": unit,
            "label": "REAL_LIVE_SPREAD_PLUS_EURUSD_COMMISSION_CLUE_LOTSCALE",
            "slippage": "MISSING_NOT_ZERO",
        },
        "parent_receipt": str(PARENT.as_posix()),
        "parent_receipt_sha256": sha256_file(PARENT),
        "books": results,
        "decision": {
            "maxkz2_goal_cost_stress": results.get("MAXKZ2", {}).get("goal_cost_stress_pass"),
            "rr2_goal_cost_stress": results.get("RR2", {}).get("goal_cost_stress_pass"),
            "a1_goal_cost_stress": results.get("A1", {}).get("goal_cost_stress_pass"),
            "spark100k_goal_cost_stress": results.get("SPARK100K", {}).get("goal_cost_stress_pass"),
            "confirmed": False,
        },
    }
    out_path = PRE / "20260714_QFSI_REAL_REPRICE_A1_SPARK_LOTSCALE_RECEIPT.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "OK",
                "receipt": str(out_path),
                "sha256": sha256_file(out_path),
                "unit_usd_per_lot": unit,
                "books": {
                    k: {
                        kk: vv
                        for kk, vv in v.items()
                        if kk
                        in {
                            "run_id",
                            "lot_p50",
                            "base_cost_per_trade",
                            "x1_pf",
                            "x1_5_pf",
                            "x2_pf",
                            "goal_cost_stress_pass",
                        }
                    }
                    for k, v in results.items()
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
