#!/usr/bin/env python3
"""Freeze a deterministic outcome-agnostic random sample of 100 HYP-004 trades."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path


HYPOTHESIS_ID = "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004"
RUN_ID = "20260725_210811"
SEED = 20260725
SAMPLE_SIZE = 100
TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
WORKSPACE = Path(__file__).resolve().parents[3]
CLOCK_TOOLS = WORKSPACE / "02. AlphaFactory" / "tools" / "research"
if str(CLOCK_TOOLS) not in sys.path:
    sys.path.insert(0, str(CLOCK_TOOLS))

from fivepercent_server_clock import server_to_utc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def iso_server_to_utc(value: str) -> str:
    server_time = datetime.strptime(value, TIME_FORMAT)
    return server_to_utc(server_time).strftime("%Y-%m-%dT%H:%M:%S")


def classify_exit(row: dict[str, str]) -> str:
    direction = 1 if row["direction"] == "BUY" else -1
    exit_price = float(row["exit"])
    stop = float(row["planned_stop"])
    target = float(row["planned_target"])
    tolerance = 2e-5
    if direction * (exit_price - target) >= -tolerance:
        return "TP_LIKE"
    if direction * (exit_price - stop) <= tolerance:
        return "SL_LIKE"
    return "TIMEOUT_OR_OTHER"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional corrected-casebook root; defaults to the original random100_forensics root.",
    )
    args = parser.parse_args()
    workspace = WORKSPACE
    evidence = (
        workspace
        / "03. EA Developer"
        / "EA_SweepCascadeContinuation"
        / "research"
        / "evidence"
        / "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS"
    )
    source = evidence / "challenger_trades.csv"
    output_dir = (
        args.output_dir.resolve()
        if args.output_dir is not None
        else evidence / "random100_forensics"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    sample_csv = output_dir / "random100_cases.csv"
    manifest_path = output_dir / "random100_sample_manifest.json"

    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_position = {int(row["position_id"]): row for row in rows}
    if len(rows) != 261 or len(by_position) != 261:
        raise SystemExit(
            f"Expected 261 unique challenger positions, got rows={len(rows)} "
            f"unique={len(by_position)}"
        )

    # The draw uses position identity only. Outcome fields are joined after the
    # 100 IDs are frozen, so selection cannot depend on win/loss or R.
    population_ids = sorted(by_position)
    selected_ids = random.Random(SEED).sample(population_ids, SAMPLE_SIZE)
    selected_rows: list[dict[str, object]] = []
    for rank, position_id in enumerate(selected_ids, start=1):
        row = by_position[position_id]
        entry_dt = datetime.strptime(row["open_time"], TIME_FORMAT)
        exit_dt = datetime.strptime(row["close_time"], TIME_FORMAT)
        net = float(row["net"])
        realized_r = float(row["realized_r"])
        direction = 1 if row["direction"] == "BUY" else -1
        outcome = "WIN" if net > 0 else "LOSS"
        selected_rows.append(
            {
                "case_id": f"R100_{rank:03d}_PID{position_id:09d}",
                "sample_rank": rank,
                "position_id": position_id,
                "entry_time_utc": iso_server_to_utc(row["open_time"]),
                "decision_time_utc": iso_server_to_utc(row["decision_time"]),
                "direction": direction,
                "direction_label": row["direction"],
                "entry": row["entry"],
                "sl": row["planned_stop"],
                "tp": row["planned_target"],
                "exit_time_utc": iso_server_to_utc(row["close_time"]),
                "exit": row["exit"],
                "reason": classify_exit(row),
                "label": f"{outcome}_NET_{'POSITIVE' if net > 0 else 'NONPOSITIVE'}",
                "net_account": f"{net:.8f}",
                "net_R": f"{realized_r:.10f}",
                "volume": row["volume"],
                "risk_points": row["risk_points"],
                "initial_risk_account": row["initial_risk_account"],
                "hold_minutes": f"{(exit_dt - entry_dt).total_seconds() / 60.0:.4f}",
                "entry_year": entry_dt.year,
            }
        )

    fieldnames = list(selected_rows[0])
    with sample_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected_rows)

    sample_nets = [float(row["net_account"]) for row in selected_rows]
    sample_rs = [float(row["net_R"]) for row in selected_rows]
    gross_profit = sum(value for value in sample_nets if value > 0)
    gross_loss = -sum(value for value in sample_nets if value < 0)
    wins = sum(value > 0 for value in sample_nets)
    sample_metrics = {
        "trades": SAMPLE_SIZE,
        "wins": wins,
        "losses": SAMPLE_SIZE - wins,
        "win_rate_pct": wins / SAMPLE_SIZE * 100.0,
        "net_account": sum(sample_nets),
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else None,
        "mean_realized_r": sum(sample_rs) / SAMPLE_SIZE,
        "median_realized_r": sorted(sample_rs)[SAMPLE_SIZE // 2 - 1 : SAMPLE_SIZE // 2 + 1],
        "finite_r_rows": sum(math.isfinite(value) for value in sample_rs),
    }
    manifest = {
        "schema_version": "scc_random_trade_sample.v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_id": HYPOTHESIS_ID,
        "run_id": RUN_ID,
        "sampling_contract": {
            "population": "all unique challenger position_id values",
            "population_size": len(population_ids),
            "sample_size": SAMPLE_SIZE,
            "seed": SEED,
            "algorithm": "Python random.Random(seed).sample(sorted(position_ids), 100)",
            "outcome_agnostic_selection": True,
            "replacement": False,
            "selection_order_preserved": True,
        },
        "time_contract": {
            "source_lifecycle_clock": "FivePercent broker server time",
            "casebook_clock": "UTC",
            "converter": "02. AlphaFactory/tools/research/fivepercent_server_clock.py",
            "raw_server_time_relabel_forbidden": True,
        },
        "source": {
            "path": source.relative_to(workspace).as_posix(),
            "bytes": source.stat().st_size,
            "sha256": sha256(source),
        },
        "sample": {
            "path": sample_csv.relative_to(workspace).as_posix(),
            "bytes": sample_csv.stat().st_size,
            "sha256": sha256(sample_csv),
            "position_ids_in_draw_order": selected_ids,
            "metrics_after_selection": sample_metrics,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(
        "SCC_RANDOM100_SAMPLE_OK "
        f"population={len(population_ids)} sample={SAMPLE_SIZE} seed={SEED} "
        f"wins={wins} losses={SAMPLE_SIZE - wins} "
        f"manifest_sha256={sha256(manifest_path)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
