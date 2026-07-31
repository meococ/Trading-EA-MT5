#!/usr/bin/env python3
"""Freeze the complete VRAS 100-image forensic corpus.

The Model-0 run contains only 93 executed positions.  The corpus therefore
uses the full trade census plus seven mechanically selected cost-distance
rejections.  Rejected candidates are explicitly labelled and never counted as
economic observations.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from build_vras_grok_chart_forensics_10 import LOGS, ROOT, load_position_truth


RESEARCH = Path(__file__).resolve().parent
EVIDENCE = RESEARCH / "evidence" / "HYP-VRAS-EURUSD-M5-003_GROK_CHART_FORENSICS_100"
CASES = EVIDENCE / "cases_all_100.csv"
SELECTION = EVIDENCE / "selection_manifest.json"
TELEMETRY = next(LOGS.glob("*DecisionTelemetry*.csv"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def select_rejections(telemetry: pd.DataFrame) -> pd.DataFrame:
    rejected = telemetry[telemetry["status"].eq("COST_DISTANCE_REJECT")].copy()
    rejected = rejected.sort_values("server_time").reset_index().rename(columns={"index": "telemetry_row"})
    rejected["risk_pips"] = (rejected["entry"] - rejected["stop"]).abs() / 0.0001
    rejected["cost_risk_fraction"] = rejected["estimated_cost_pips"] / rejected["risk_pips"].replace(0.0, np.nan)
    if len(rejected) != 455:
        raise RuntimeError(f"Expected 455 cost-distance rejects, found {len(rejected)}")

    chosen: list[pd.Series] = []
    used: set[int] = set()

    def add(row: pd.Series, reason: str) -> None:
        source_row = int(row["telemetry_row"])
        if source_row in used:
            return
        used.add(source_row)
        item = row.copy()
        item["selection_reason"] = reason
        chosen.append(item)

    for event in ("TREND_LONG", "TREND_SHORT", "RANGE_LONG", "RANGE_SHORT"):
        group = rejected[rejected["event"].eq(event)]
        if group.empty:
            raise RuntimeError(f"No cost-distance reject rows for {event}")
        median = float(group["cost_risk_fraction"].median())
        row = group.loc[(group["cost_risk_fraction"] - median).abs().idxmin()]
        add(row, f"{event} candidate nearest its event-level median estimated-cost/risk fraction")

    remaining = rejected[~rejected["telemetry_row"].isin(used)]
    add(remaining.loc[remaining["cost_risk_fraction"].idxmin()], "Global minimum estimated-cost/risk fraction among unused rejects")
    remaining = rejected[~rejected["telemetry_row"].isin(used)]
    global_median = float(remaining["cost_risk_fraction"].median())
    add(remaining.loc[(remaining["cost_risk_fraction"] - global_median).abs().idxmin()], "Global median estimated-cost/risk fraction among unused rejects")
    remaining = rejected[~rejected["telemetry_row"].isin(used)]
    add(remaining.loc[remaining["cost_risk_fraction"].idxmax()], "Global maximum estimated-cost/risk fraction among unused rejects")

    selected = pd.DataFrame(chosen)
    if len(selected) != 7 or selected["telemetry_row"].nunique() != 7:
        raise RuntimeError("Rejected-candidate selection must contain seven unique telemetry rows")
    return selected


def main() -> None:
    positions = load_position_truth().copy()
    positions["case_id"] = [
        f"VRAS-003-T{number:03d}-P{int(position_id)}"
        for number, position_id in enumerate(positions["position_id"], start=1)
    ]
    positions["case_kind"] = "TRADE"
    positions["telemetry_status"] = "ORDER_ACCEPTED"
    positions["stratum"] = "complete_trade_census"
    positions["context_reason"] = "One member of the complete 93-position Model-0 trade census; no trade sampling"

    telemetry = pd.read_csv(TELEMETRY)
    telemetry["server_time"] = pd.to_datetime(telemetry["server_time"])
    telemetry["utc_time"] = pd.to_datetime(telemetry["utc_time"])
    numeric = [
        "regime", "adx", "atr", "rsi", "session_vwap", "session_sd", "shadow_vwap",
        "shadow_sd", "anchored_vwap", "m15_close", "m15_vwap", "entry", "stop",
        "target", "estimated_cost_pips", "spread_pips",
    ]
    for column in numeric:
        telemetry[column] = pd.to_numeric(telemetry[column], errors="raise")
    rejected = select_rejections(telemetry)

    reject_rows: list[dict] = []
    for number, (_, row) in enumerate(rejected.iterrows(), start=1):
        reject_rows.append(
            {
                "case_id": f"VRAS-003-R{number:02d}-CR{int(row['telemetry_row'])}",
                "case_kind": "REJECTED_CANDIDATE",
                "telemetry_status": "COST_DISTANCE_REJECT",
                "position_id": -number,
                "stratum": "cost_distance_reject_diagnostic",
                "context_reason": row["selection_reason"],
                "event": row["event"],
                "direction": 1 if str(row["event"]).endswith("LONG") else -1,
                "entry_time_server": row["server_time"],
                "entry_time_utc": row["utc_time"],
                "exit_time_server": row["server_time"] + pd.Timedelta(hours=3),
                "exit_time_utc": row["utc_time"] + pd.Timedelta(hours=3),
                "entry_price": float(row["entry"]),
                "exit_price": np.nan,
                "stop_price": float(row["stop"]),
                "target_price": float(row["target"]),
                "net_R": np.nan,
                "net_usd": np.nan,
                "exit_class": "NOT_TRADED_COST_DISTANCE_REJECT",
                "estimated_cost_pips": float(row["estimated_cost_pips"]),
                "spread_pips": float(row["spread_pips"]),
                "cost_risk_fraction": float(row["cost_risk_fraction"]),
                "telemetry_row": int(row["telemetry_row"]),
            }
        )
    rejects_frame = pd.DataFrame(reject_rows)

    cases = pd.concat([positions, rejects_frame], ignore_index=True, sort=False)
    if len(cases) != 100 or cases["case_id"].nunique() != 100:
        raise RuntimeError("The forensic corpus must contain exactly 100 unique cases")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    cases.to_csv(CASES, index=False)

    manifest = {
        "schema_version": "vras_grok_indicator_rich_selection.v2",
        "hypothesis_id": "HYP-VRAS-EURUSD-M5-003",
        "run_id": "20260722_103759",
        "frozen_at_utc": utc_now(),
        "image_target": 100,
        "executed_trade_population": 93,
        "trade_case_count": 93,
        "non_trade_diagnostic_count": 7,
        "economic_sample_size": 93,
        "anti_inflation_rule": "The seven rejected candidates are not trades and must never be included in WR, PF, expectancy, cadence, or outcome frequencies.",
        "trade_sampling": "Complete census of all reconciled positions",
        "reject_sampling": [item["context_reason"] for item in reject_rows],
        "case_ids": cases["case_id"].tolist(),
        "trade_case_ids": positions["case_id"].tolist(),
        "rejected_candidate_case_ids": rejects_frame["case_id"].tolist(),
        "source_telemetry": str(TELEMETRY.relative_to(ROOT)).replace("\\", "/"),
    }
    SELECTION.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "VRAS_100_IMAGE_CORPUS_FROZEN",
                "cases": str(CASES),
                "selection": str(SELECTION),
                "trade_cases": 93,
                "rejected_candidates": 7,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
