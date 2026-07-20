#!/usr/bin/env python3
"""Select fixed best/worst HYP-017 trades for post-outcome chart forensics."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import analyze_hyp017_economics as economics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run.resolve()
    manifest_path = run_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    lifecycle = economics.find_sidecar(run_dir, manifest, "_LifecycleTrades_")
    context = economics.find_sidecar(run_dir, manifest, "_HumanContext_")
    clock_path, clock = economics.load_clock_module()
    trades = economics.load_trades(lifecycle, clock)
    join = economics.join_context(trades, context)
    if join["unmatched"]:
        raise ValueError(f"context join has {join['unmatched']} unmatched trades")
    for trade in trades:
        cost = 1.5 * 10.0 * trade["volume"]
        trade["cost_r"] = (trade["base_net"] - cost) / trade["risk_account"]
    selected = sorted(trades, key=lambda row: row["cost_r"])[:2]
    selected += sorted(trades, key=lambda row: row["cost_r"], reverse=True)[:2]
    case_ids = ["H17_L01", "H17_L02", "H17_W01", "H17_W02"]
    rows = []
    for case_id, trade in zip(case_ids, selected):
        direction = 1 if trade["direction"] == "LONG" else -1
        rows_for_position = []
        with lifecycle.open("r", encoding="utf-8-sig", newline="") as handle:
            rows_for_position = [
                row
                for row in csv.DictReader(handle)
                if row["position_id"] == trade["position_id"]
            ]
        opened = next(row for row in rows_for_position if row["action"] == "OPEN")
        closed = next(row for row in rows_for_position if row["action"] == "CLOSE")
        risk_price = float(opened["risk_pts"]) * 0.00001
        entry = float(opened["price"])
        rows.append(
            {
                "case_id": case_id,
                "position_id": trade["position_id"],
                "entry_time_utc": trade["entry_utc"].isoformat(),
                "exit_time_utc": trade["close_utc"].isoformat(),
                "direction": direction,
                "entry": entry,
                "sl": entry - direction * risk_price,
                "tp": entry + direction * 2.0 * risk_price,
                "exit": float(closed["price"]),
                "reason": "worst_primary_cost" if "_L" in case_id else "best_primary_cost",
                "label": (
                    f"pid={trade['position_id']}; state={trade['context_state']}; "
                    f"costR={trade['cost_r']:.3f}; hold={trade['hold_minutes']:.1f}m"
                ),
            }
        )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    cases_path = args.out_dir / "cases.csv"
    with cases_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    receipt = {
        "schema_version": "hyp017.post_outcome_casebook_selection.v1",
        "hypothesis_id": economics.HYPOTHESIS_ID,
        "run_id": run_dir.name,
        "purpose": "post-outcome visual forensics only; no filter or rerun authority",
        "selection": "two worst and two best trades by frozen additional-1.5-pip R",
        "run_manifest_sha256": economics.sha_file(manifest_path),
        "lifecycle_sha256": economics.sha_file(lifecycle),
        "human_context_sha256": economics.sha_file(context),
        "server_clock_sha256": economics.sha_file(clock_path),
        "cases_sha256": economics.sha_file(cases_path),
        "position_ids": [trade["position_id"] for trade in selected],
        "context_join": join,
    }
    receipt_path = args.out_dir / "selection_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"cases": str(cases_path), "position_ids": receipt["position_ids"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
