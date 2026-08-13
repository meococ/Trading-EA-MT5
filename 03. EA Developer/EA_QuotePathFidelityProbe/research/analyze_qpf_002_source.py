#!/usr/bin/env python3
"""Outcome-blind gate analyzer for HYP-QPF-EURUSD-M1-002."""

from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HYPOTHESIS_ID = "HYP-QPF-EURUSD-M1-002"
SCHEMA_VERSION = "alphafactory.quote_path_fidelity.v1"
EXPECTED_YEARS = tuple(range(2018, 2027))
FORBIDDEN_COLUMNS = {
    "return", "future_return", "pnl", "profit", "profit_factor", "pf",
    "balance", "equity", "mfe", "mae", "outcome", "label", "trade_result",
}
REQUIRED_COLUMNS = {
    "schema_version", "hypothesis_id", "run_id", "symbol", "timeframe",
    "bucket_start_server", "bucket_end_server", "total_ticks", "valid_quotes",
    "invalid_quotes", "invalid_time", "reverse_time_msc",
    "exact_duplicate_quotes", "quote_changes", "bid_only_changes",
    "ask_only_changes", "both_changes", "spread_changes", "bar_complete",
    "orders_sent", "promotion_eligible",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def ratio(num: int, den: int) -> float:
    return num / den if den else math.nan


def blank_counts() -> dict[str, int]:
    return defaultdict(int)


def parse_report(report: Path) -> dict[str, float | int | str]:
    raw = report.read_bytes()
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    text = raw.decode(encoding, errors="ignore")

    def number_after(labels: tuple[str, ...], integer: bool = False):
        for label in labels:
            pattern = re.escape(label) + r".*?<b>\s*([0-9][0-9\s.,]*)"
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                cleaned = match.group(1).replace(" ", "").replace(",", "")
                return int(float(cleaned)) if integer else float(cleaned)
        raise ValueError(f"report field not found: {labels}")

    return {
        "history_quality_pct": number_after(("History Quality:",)),
        "ticks": number_after(("Ticks:",), integer=True),
        "total_trades": number_after(("Total Trades:", "T\u1ed5ng s\u1ed1 giao d\u1ecbch:"), integer=True),
        "net_profit": number_after(("Total Net Profit:", "T\u1ed5ng l\u1ee3i nhu\u1eadn r\u00f2ng:")),
    }


def add_counts(target: dict[str, int], row: dict[str, str]) -> None:
    for key in (
        "total_ticks", "valid_quotes", "invalid_quotes", "invalid_time",
        "reverse_time_msc", "exact_duplicate_quotes", "quote_changes",
        "bid_only_changes", "ask_only_changes", "both_changes", "spread_changes",
    ):
        value = int(row[key])
        if value < 0:
            raise ValueError(f"negative {key}")
        target[key] += value
    target["buckets"] += 1
    if int(row["quote_changes"]) >= 20:
        target["buckets_ge_20_changes"] += 1


def metrics(counts: dict[str, int]) -> dict[str, float | int]:
    transitions = counts["quote_changes"] + counts["exact_duplicate_quotes"]
    return {
        **dict(counts),
        "invalid_quote_share": ratio(counts["invalid_quotes"], counts["total_ticks"]),
        "positive_timestamp_share": 1.0 - ratio(counts["invalid_time"], counts["total_ticks"]),
        "buckets_ge_20_changes_share": ratio(counts["buckets_ge_20_changes"], counts["buckets"]),
        "duplicate_transition_share": ratio(counts["exact_duplicate_quotes"], transitions),
        "one_sided_update_share": ratio(
            counts["bid_only_changes"] + counts["ask_only_changes"],
            counts["quote_changes"],
        ),
        "spread_change_share": ratio(counts["spread_changes"], transitions),
    }


def gates(m: dict[str, float | int]) -> dict[str, bool]:
    return {
        "invalid_quote_share_le_0_001": m["invalid_quote_share"] <= 0.001,
        "reverse_time_zero": m["reverse_time_msc"] == 0,
        "positive_timestamp_share_eq_1": m["positive_timestamp_share"] == 1.0,
        "active_buckets_ge_20_share_ge_0_95": m["buckets_ge_20_changes_share"] >= 0.95,
        "duplicate_transition_share_lt_0_05": m["duplicate_transition_share"] < 0.05,
        "one_sided_update_share_ge_0_05": m["one_sided_update_share"] >= 0.05,
        "spread_change_share_ge_0_01": m["spread_change_share"] >= 0.01,
    }


def analyze(csv_path: Path, report_path: Path, manifest_path: Path) -> dict:
    report = parse_report(report_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    pooled = blank_counts()
    yearly: dict[int, dict[str, int]] = {year: blank_counts() for year in EXPECTED_YEARS}
    previous_start: datetime | None = None
    run_ids: set[str] = set()
    identity_errors: list[str] = []

    expected_manifest_scalars = {
        "hypothesis_id": HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": "EA_QuotePathFidelityProbe",
        "symbol": "EURUSD",
        "period": "M1",
        "from": "2018.01.01",
        "to": "2026.08.01",
        "model": 0,
        "telemetry_tier": "off",
        "telemetry_profile": "none",
    }
    for key, expected in expected_manifest_scalars.items():
        if manifest.get(key) != expected:
            identity_errors.append(f"manifest {key}")
    if manifest.get("required_sidecars") != ["*_QuotePathFidelity_*.csv"]:
        identity_errors.append("manifest required_sidecars")
    csv_hash = sha256(csv_path)
    qpf_sidecars = [
        item for item in manifest.get("sidecars", [])
        if fnmatch.fnmatchcase(
            Path(str(item.get("path", ""))).name,
            "*_QuotePathFidelity_*.csv",
        )
    ]
    sidecars = [
        item for item in manifest.get("sidecars", [])
        if Path(str(item.get("path", ""))).name == csv_path.name
    ]
    if len(qpf_sidecars) != 1:
        identity_errors.append("manifest exact-one QPF sidecar")
    if len(sidecars) != 1 or str(sidecars[0].get("sha256", "")).upper() != csv_hash:
        identity_errors.append("manifest sidecar identity")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - columns)
        forbidden = sorted(columns & FORBIDDEN_COLUMNS)
        if missing:
            raise ValueError(f"missing columns: {missing}")
        if forbidden:
            raise ValueError(f"forbidden economic columns: {forbidden}")
        for line_no, row in enumerate(reader, start=2):
            if row["schema_version"] != SCHEMA_VERSION:
                identity_errors.append(f"line {line_no}: schema_version")
            if row["hypothesis_id"] != HYPOTHESIS_ID:
                identity_errors.append(f"line {line_no}: hypothesis_id")
            if row["symbol"] != "EURUSD" or row["timeframe"] != "M1":
                identity_errors.append(f"line {line_no}: symbol/timeframe")
            if row["bar_complete"].lower() != "true" or row["orders_sent"] != "0":
                identity_errors.append(f"line {line_no}: collection flags")
            if row["promotion_eligible"].lower() != "false":
                identity_errors.append(f"line {line_no}: promotion flag")
            start = datetime.strptime(row["bucket_start_server"], "%Y.%m.%d %H:%M:%S")
            end = datetime.strptime(row["bucket_end_server"], "%Y.%m.%d %H:%M:%S")
            if (end - start).total_seconds() != 300:
                identity_errors.append(f"line {line_no}: bucket width")
            if previous_start is not None and start <= previous_start:
                identity_errors.append(f"line {line_no}: timestamp order")
            previous_start = start
            if start.year not in yearly:
                identity_errors.append(f"line {line_no}: year {start.year}")
                continue
            run_ids.add(row["run_id"])
            add_counts(pooled, row)
            add_counts(yearly[start.year], row)

    pooled_metrics = metrics(pooled)
    yearly_metrics = {str(year): metrics(yearly[year]) for year in EXPECTED_YEARS}
    pooled_gates = gates(pooled_metrics)
    yearly_gates = {year: gates(values) for year, values in yearly_metrics.items()}
    engineering_ok = (
        report["history_quality_pct"] > 97.0
        and report["total_trades"] == 0
        and report["net_profit"] == 0.0
        and len(run_ids) == 1
        and not identity_errors
        and all(values["buckets"] > 0 for values in yearly_metrics.values())
    )
    source_gate_pass = (
        engineering_ok
        and all(pooled_gates.values())
        and all(all(group.values()) for group in yearly_gates.values())
    )
    return {
        "schema_version": "alphafactory.qpf_source_result.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "analysis_mode": "source_only_no_outcome",
        "inputs": {
            "csv": str(csv_path.resolve()), "csv_sha256": csv_hash,
            "report": str(report_path.resolve()), "report_sha256": sha256(report_path),
            "manifest": str(manifest_path.resolve()), "manifest_sha256": sha256(manifest_path),
        },
        "report": report,
        "run_ids": sorted(run_ids),
        "identity_errors": identity_errors[:100],
        "pooled": pooled_metrics,
        "pooled_gates": pooled_gates,
        "yearly": yearly_metrics,
        "yearly_gates": yearly_gates,
        "verdict": (
            "ENGINEERING_INVALID_NO_SOURCE_VERDICT"
            if not engineering_ok
            else (
                "PASS_QUOTE_PATH_FIDELITY_MAY_RESEARCH_CLOSED_M5_M15_CHILD"
                if source_gate_pass
                else "KILL_QUOTE_PATH_FIDELITY_EXACT_EURUSD_METATICKS"
            )
        ),
        "economics_authorized": False,
        "promotion_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = analyze(args.csv, args.report, args.manifest)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(result["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
