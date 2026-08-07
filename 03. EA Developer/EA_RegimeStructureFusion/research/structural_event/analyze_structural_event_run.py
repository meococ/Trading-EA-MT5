#!/usr/bin/env python3
"""Hash-bound, streaming postmortem for one RSF structural-event lifecycle log.

The script reads only AlphaFactory-imported lifecycle and RunMeta sidecars.  It
does not tune, filter, or select a profitable subset; route/year/session tables
are diagnostic and must not be used to rescue a killed hypothesis.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def number(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {"trades": 0}
    net = [float(row["net_profit"]) for row in rows]
    achieved_r = [float(row["achieved_r"]) for row in rows]
    holds = [float(row["hold_minutes"]) for row in rows if row["hold_minutes"] is not None]
    gross_profit = sum(value for value in net if value > 0)
    gross_loss = -sum(value for value in net if value < 0)
    r_profit = sum(value for value in achieved_r if value > 0)
    r_loss = -sum(value for value in achieved_r if value < 0)
    risks = [float(row["initial_risk_account"]) for row in rows]
    min_lot = sum(float(row["volume"]) <= 0.0100001 for row in rows)
    collapsed = sum(value < 10.0 for value in risks)
    return {
        "trades": len(rows),
        "wins": sum(value > 0 for value in net),
        "win_rate_pct": 100.0 * sum(value > 0 for value in net) / len(rows),
        "net_profit": sum(net),
        "net_profit_factor": gross_profit / gross_loss if gross_loss else None,
        "mean_achieved_r": statistics.fmean(achieved_r),
        "median_achieved_r": statistics.median(achieved_r),
        "r_profit_factor": r_profit / r_loss if r_loss else None,
        "tp_rate_pct": 100.0 * sum(row["exit_reason"] == "DEAL_REASON_TP" for row in rows) / len(rows),
        "sl_rate_pct": 100.0 * sum(row["exit_reason"] == "DEAL_REASON_SL" for row in rows) / len(rows),
        "average_hold_minutes": statistics.fmean(holds) if holds else None,
        "average_initial_risk_account": statistics.fmean(risks),
        "minimum_lot_share_pct": 100.0 * min_lot / len(rows),
        "risk_below_10_share_pct": 100.0 * collapsed / len(rows),
    }


def grouped(rows: list[dict[str, object]], key: str) -> dict[str, object]:
    buckets: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        buckets[str(row[key])].append(row)
    return {name: summarize(bucket) for name, bucket in sorted(buckets.items())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    log_dir = args.run / "analysis" / "logs"
    lifecycle = next(log_dir.glob("*_LifecycleTrades_*.csv"))
    runmeta_path = next(log_dir.glob("*_RunMeta_*.json"))
    runmeta = json.loads(runmeta_path.read_text(encoding="utf-8"))

    opened: dict[str, dict[str, str]] = {}
    trades: list[dict[str, object]] = []
    with lifecycle.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            position_id = row["position_id"]
            if row["action"] == "OPEN":
                opened[position_id] = row
                continue
            if row["action"] != "CLOSE" or row["is_final_close"] != "1":
                continue
            entry = opened.get(position_id)
            opened_at = datetime.strptime(entry["utc_time"], "%Y.%m.%d %H:%M:%S") if entry else None
            closed_at = datetime.strptime(row["utc_time"], "%Y.%m.%d %H:%M:%S")
            trades.append(
                {
                    "position_id": position_id,
                    "utc_time": row["utc_time"],
                    "entry_event_time": entry["event_time"] if entry else None,
                    "exit_event_time": row["event_time"],
                    "entry_price": number(row["entry_price"]),
                    "exit_price": number(row["price"]),
                    "initial_sl": number(row["initial_sl"]),
                    "initial_tp": number(row["initial_tp"]),
                    "year": closed_at.year,
                    "month": closed_at.strftime("%Y-%m"),
                    "utc_hour": closed_at.hour,
                    "engine": row["engine_name"],
                    "direction": "LONG" if row["engine_name"].endswith("_LONG") else "SHORT",
                    "exit_reason": row["reason"],
                    "volume": number(row["volume"]),
                    "initial_risk_account": number(row["initial_risk_account"]),
                    "achieved_r": number(row["achievedr"]),
                    "net_profit": number(row["net_profit"]),
                    "hold_minutes": (closed_at - opened_at).total_seconds() / 60.0 if opened_at else None,
                }
            )

    first_risk_collapse = next(
        (row["utc_time"] for row in trades if float(row["initial_risk_account"]) < 10.0),
        None,
    )
    funnel = runmeta.get("funnel", {})
    armed = int(funnel.get("structural_armed", 0))
    retested = int(funnel.get("structural_retested", 0))
    confirmed = int(funnel.get("structural_confirmed", 0))
    # Outcome is used only to choose symmetric best/worst diagnostic examples.
    # Selection is frozen before any chart is viewed and never changes the
    # economic verdict or authorizes pruning.
    paired_visual_selection: list[dict[str, object]] = []
    case_no = 1
    for engine in sorted({str(row["engine"]) for row in trades}):
        eligible = [
            row for row in trades
            if row["engine"] == engine and float(row["initial_risk_account"]) >= 10.0
        ]
        for label, selected in (
            ("LOSS", min(eligible, key=lambda item: float(item["achieved_r"]))),
            ("WIN", max(eligible, key=lambda item: float(item["achieved_r"]))),
        ):
            entry_time = datetime.strptime(str(selected["entry_event_time"]), "%Y.%m.%d %H:%M:%S")
            exit_time = datetime.strptime(str(selected["exit_event_time"]), "%Y.%m.%d %H:%M:%S")
            paired_visual_selection.append(
                {
                    "case_id": f"SE004-C{case_no:02d}-{engine}-{label}",
                    "selection_rule": f"{label.lower()} achieved-R within {engine}, excluding initial risk below 10 account currency",
                    "position_id": selected["position_id"],
                    "engine": engine,
                    "direction": selected["direction"],
                    "entry_event_time": selected["entry_event_time"],
                    "exit_event_time": selected["exit_event_time"],
                    "entry_price": selected["entry_price"],
                    "exit_price": selected["exit_price"],
                    "initial_sl": selected["initial_sl"],
                    "initial_tp": selected["initial_tp"],
                    "achieved_r": selected["achieved_r"],
                    "net_profit": selected["net_profit"],
                    "visual_from": (entry_time - timedelta(days=10)).strftime("%Y.%m.%d"),
                    "visual_to": (exit_time + timedelta(days=2)).strftime("%Y.%m.%d"),
                }
            )
            case_no += 1

    result = {
        "schema_version": "rsf_structural_event_postmortem.v1",
        "run_id": args.run.name,
        "hypothesis_id": runmeta.get("hypothesis_id"),
        "source_evidence": {
            "lifecycle_path": str(lifecycle.resolve()),
            "lifecycle_sha256": sha256(lifecycle),
            "lifecycle_bytes": lifecycle.stat().st_size,
            "runmeta_path": str(runmeta_path.resolve()),
            "runmeta_sha256": sha256(runmeta_path),
        },
        "overall": summarize(trades),
        "by_engine": grouped(trades, "engine"),
        "by_direction": grouped(trades, "direction"),
        "by_year": grouped(trades, "year"),
        "by_utc_hour": grouped(trades, "utc_hour"),
        "exit_reason": grouped(trades, "exit_reason"),
        "paired_visual_selection": paired_visual_selection,
        "risk_floor_diagnostic": {
            "first_initial_risk_below_10_utc": first_risk_collapse,
            "note": "Diagnostic only. Broker money-mode stop-out plus the frozen equity buffer can reduce volume before rejecting new entries.",
        },
        "funnel": {
            "structural_armed": armed,
            "structural_retested": retested,
            "structural_confirmed": confirmed,
            "entries_opened": int(funnel.get("entries_opened", 0)),
            "arm_to_retest_pct": 100.0 * retested / armed if armed else None,
            "retest_to_confirm_pct": 100.0 * confirmed / retested if retested else None,
            "confirm_to_entry_pct": 100.0 * int(funnel.get("entries_opened", 0)) / confirmed if confirmed else None,
            "structural_expired": int(funnel.get("structural_expired", 0)),
            "structural_canceled": int(funnel.get("structural_canceled", 0)),
            "structural_reject_context": int(funnel.get("structural_reject_context", 0)),
            "structural_reject_runway": int(funnel.get("structural_reject_runway", 0)),
            "reject_risk": int(funnel.get("reject_risk", 0)),
        },
        "decision": {
            "verdict": "KILL_NEGATIVE_EXPECTANCY",
            "same_id_parameter_rescue_allowed": False,
            "post_hoc_route_session_year_pruning_allowed": False,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"STRUCTURAL_POSTMORTEM_OK out={args.out} trades={len(trades)} sha256={sha256(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
