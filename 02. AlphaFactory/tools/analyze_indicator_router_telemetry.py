#!/usr/bin/env python3
"""Streaming, outcome-blind analysis for matched indicator-router telemetry.

The analyzer intentionally never reads post-entry prices or trading outcomes.  It
expects the two matched arms for each signal to be adjacent, which lets it keep
only one event in memory while processing arbitrarily large CSV exports.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import sqlite3
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterable


EXPECTED_ARMS = {"TRUE_REVERSAL", "FOLLOW_CONTROL"}
OPPOSITE_DIRECTION = {"LONG": "SHORT", "SHORT": "LONG"}
VETO_GROUP_MASKS = {
    "AIRD": 1 | 2 | 4,
    "VRC": 8 | 16 | 32 | 64,
    "MBB": 128 | 256,
    "QQE": 512 | 1024,
    "TB_SMC": 2048,
}
VETO_REMOVAL_SUBSETS = tuple(
    (
        "+".join(names),
        sum(VETO_GROUP_MASKS[name] for name in names),
    )
    for size in range(1, len(VETO_GROUP_MASKS) + 1)
    for names in itertools.combinations(VETO_GROUP_MASKS, size)
)
FORBIDDEN_OUTCOME_COLUMNS = {
    "outcome",
    "pnl",
    "profit",
    "gross_profit",
    "net_profit",
    "return",
    "forward_return",
    "mfe",
    "mae",
    "entry_price",
    "exit_price",
    "post_entry_price",
    "win",
    "loss",
    "realized_rr",
}
REQUIRED_COLUMNS = {
    "signal_id",
    "arm",
    "direction",
    "availability_research_clock",
    "research_year",
    "research_hour",
    "veto_mask",
    "veto_reasons",
    "router_pass",
    "aird_valid",
    "vrc_valid",
    "mbb_dc_valid",
    "qqe_primary",
    "qqe_secondary",
    "qqe_composite",
    "tb_closed_valid",
    "final_stop_pips",
    "cost_to_stop_ratio",
}


def sha256_stream(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_bool_flag(value: str, field: str, line_number: int) -> bool:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"line {line_number}: {field} is not numeric: {value!r}") from exc
    if parsed not in (0.0, 1.0):
        raise ValueError(f"line {line_number}: {field} is not an exact 0/1 flag: {value!r}")
    return parsed == 1.0


def finite_float(value: str, field: str, line_number: int) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"line {line_number}: {field} is not numeric: {value!r}") from exc
    if not math.isfinite(parsed) or abs(parsed) >= 1.0e100:
        raise ValueError(f"line {line_number}: {field} is not a usable finite value: {value!r}")
    return parsed


def sqlite_median(connection: sqlite3.Connection, column: str) -> float | None:
    count = connection.execute("SELECT COUNT(*) FROM pass_geometry").fetchone()[0]
    if count == 0:
        return None
    offset = (count - 1) // 2
    limit = 2 if count % 2 == 0 else 1
    values = [
        row[0]
        for row in connection.execute(
            f"SELECT {column} FROM pass_geometry ORDER BY {column} LIMIT ? OFFSET ?",
            (limit, offset),
        )
    ]
    return sum(values) / len(values)


def sorted_counter(counter: Counter[str | int]) -> list[dict[str, Any]]:
    return [
        {"key": key, "count": count}
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    ]


def analyze(
    csv_path: Path,
    *,
    analysis_from: date,
    analysis_to: date,
    min_raw_events: int = 500,
    min_pass_events: int = 150,
    min_cadence: float = 0.55,
    max_cadence: float = 4.0,
    min_pass_per_side: int = 40,
    max_year_share: float = 0.40,
    min_median_stop_pips: float = 6.0,
    max_median_cost_to_stop: float = 0.25,
) -> dict[str, Any]:
    if analysis_to <= analysis_from:
        raise ValueError("analysis_to must be after analysis_from")

    elapsed_weeks = (analysis_to - analysis_from).days / 7.0
    file_size = csv_path.stat().st_size
    source_sha256 = sha256_stream(csv_path)

    raw_events = 0
    arm_rows = 0
    pass_events = 0
    pass_long = 0
    pass_short = 0
    matched_pair_errors: list[str] = []
    pass_by_year: Counter[int] = Counter()
    pass_by_hour: Counter[int] = Counter()
    all_by_year: Counter[int] = Counter()
    all_by_hour: Counter[int] = Counter()
    veto_reason_counts: Counter[str] = Counter()
    veto_combination_counts: Counter[str] = Counter()
    veto_group_counts: Counter[str] = Counter()
    removal_only_pass_counts: Counter[str] = Counter()
    removal_subset_pass_counts: Counter[str] = Counter()
    validity_counts: Counter[str] = Counter()
    first_availability: str | None = None
    last_availability: str | None = None

    output_parent = csv_path.parent
    temp_handle = tempfile.NamedTemporaryFile(
        prefix="router-geometry-", suffix=".sqlite3", dir=output_parent, delete=False
    )
    temp_path = Path(temp_handle.name)
    temp_handle.close()
    connection = sqlite3.connect(temp_path)
    connection.execute("CREATE TABLE pass_geometry (stop_pips REAL NOT NULL, cost_ratio REAL NOT NULL)")

    def finalize_event(rows: list[tuple[int, dict[str, str]]]) -> None:
        nonlocal raw_events, pass_events, pass_long, pass_short, first_availability, last_availability
        if not rows:
            return
        raw_events += 1
        signal_id = rows[0][1]["signal_id"]
        if len(rows) != 2:
            matched_pair_errors.append(f"{signal_id}: expected 2 adjacent rows, found {len(rows)}")
            return
        arms = {row["arm"] for _, row in rows}
        if arms != EXPECTED_ARMS:
            matched_pair_errors.append(f"{signal_id}: arms={sorted(arms)!r}")
            return
        by_arm = {row["arm"]: (line, row) for line, row in rows}
        true_line, true_row = by_arm["TRUE_REVERSAL"]
        _, follow_row = by_arm["FOLLOW_CONTROL"]
        if OPPOSITE_DIRECTION.get(true_row["direction"]) != follow_row["direction"]:
            matched_pair_errors.append(
                f"{signal_id}: directions={true_row['direction']}/{follow_row['direction']}"
            )
        for field in ("veto_mask", "veto_reasons", "router_pass", "availability_research_clock"):
            if true_row[field] != follow_row[field]:
                matched_pair_errors.append(f"{signal_id}: matched-arm mismatch in {field}")

        availability = true_row["availability_research_clock"]
        first_availability = availability if first_availability is None else min(first_availability, availability)
        last_availability = availability if last_availability is None else max(last_availability, availability)
        year = int(true_row["research_year"])
        hour = int(true_row["research_hour"])
        all_by_year[year] += 1
        all_by_hour[hour] += 1

        mask = int(true_row["veto_mask"])
        passed = parse_bool_flag(true_row["router_pass"], "router_pass", true_line)
        if passed != (mask == 0):
            matched_pair_errors.append(f"{signal_id}: router_pass disagrees with veto_mask={mask}")

        validity_counts["events"] += 1
        if parse_bool_flag(true_row["aird_valid"], "aird_valid", true_line):
            validity_counts["AIRD_valid"] += 1
        if parse_bool_flag(true_row["vrc_valid"], "vrc_valid", true_line):
            validity_counts["VRC_valid"] += 1
        if parse_bool_flag(true_row["mbb_dc_valid"], "mbb_dc_valid", true_line):
            validity_counts["MBB_dc_valid"] += 1
        if not (mask & 512):
            validity_counts["QQE_valid"] += 1
        if parse_bool_flag(true_row["tb_closed_valid"], "tb_closed_valid", true_line):
            validity_counts["TB_closed_valid"] += 1

        if passed:
            pass_events += 1
            pass_by_year[year] += 1
            pass_by_hour[hour] += 1
            if true_row["direction"] == "LONG":
                pass_long += 1
            elif true_row["direction"] == "SHORT":
                pass_short += 1
            else:
                matched_pair_errors.append(f"{signal_id}: invalid TRUE_REVERSAL direction")
            stop = finite_float(true_row["final_stop_pips"], "final_stop_pips", true_line)
            ratio = finite_float(true_row["cost_to_stop_ratio"], "cost_to_stop_ratio", true_line)
            connection.execute("INSERT INTO pass_geometry VALUES (?, ?)", (stop, ratio))
            return

        reasons = [part for part in true_row["veto_reasons"].split("|") if part and part != "PASS"]
        for reason in reasons:
            veto_reason_counts[reason] += 1
        veto_combination_counts[true_row["veto_reasons"]] += 1
        for group, group_mask in VETO_GROUP_MASKS.items():
            if mask & group_mask:
                veto_group_counts[group] += 1
            if mask != 0 and (mask & ~group_mask) == 0:
                removal_only_pass_counts[group] += 1
        for subset_name, subset_mask in VETO_REMOVAL_SUBSETS:
            if mask != 0 and (mask & ~subset_mask) == 0:
                removal_subset_pass_counts[subset_name] += 1

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            missing = sorted(REQUIRED_COLUMNS - set(fieldnames))
            if missing:
                raise ValueError(f"missing required columns: {missing}")
            forbidden = sorted(FORBIDDEN_OUTCOME_COLUMNS & set(fieldnames))

            current_signal: str | None = None
            current_rows: list[tuple[int, dict[str, str]]] = []
            for line_number, row in enumerate(reader, start=2):
                arm_rows += 1
                signal_id = row["signal_id"]
                if not signal_id:
                    raise ValueError(f"line {line_number}: empty signal_id")
                if current_signal is not None and signal_id != current_signal:
                    finalize_event(current_rows)
                    current_rows = []
                current_signal = signal_id
                current_rows.append((line_number, row))
                if len(current_rows) > 2:
                    raise ValueError(f"line {line_number}: more than two adjacent rows for {signal_id}")
            finalize_event(current_rows)

        connection.commit()
        median_stop = sqlite_median(connection, "stop_pips")
        median_cost_ratio = sqlite_median(connection, "cost_ratio")
    finally:
        connection.close()
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass

    cadence = pass_events / elapsed_weeks if elapsed_weeks > 0 else 0.0
    observed_max_year_share = max(pass_by_year.values(), default=0) / max(pass_events, 1)
    gate_results = {
        "no_outcome_columns": not forbidden,
        "matched_arms": not matched_pair_errors and arm_rows == raw_events * 2,
        "raw_events": raw_events >= min_raw_events,
        "router_pass_events": pass_events >= min_pass_events,
        "cadence": min_cadence <= cadence <= max_cadence,
        "sides": pass_long >= min_pass_per_side and pass_short >= min_pass_per_side,
        "max_year_share": observed_max_year_share <= max_year_share,
        "median_stop": median_stop is not None and median_stop >= min_median_stop_pips,
        "median_cost_to_stop": median_cost_ratio is not None and median_cost_ratio <= max_median_cost_to_stop,
    }

    validity_rates = {
        key.removesuffix("_valid") + "_rate": value / max(validity_counts["events"], 1)
        for key, value in validity_counts.items()
        if key != "events"
    }
    return {
        "schema_version": "alphafactory.indicator_router_telemetry_analysis.v1",
        "evidence_class": "OUTCOME_BLIND_ROUTER_FEASIBILITY_ONLY",
        "source": {
            "path": str(csv_path.resolve()),
            "size_bytes": file_size,
            "sha256": source_sha256,
            "rows": arm_rows,
        },
        "analysis_window": {
            "from": analysis_from.isoformat(),
            "to": analysis_to.isoformat(),
            "elapsed_weeks": elapsed_weeks,
            "first_availability_research_clock": first_availability,
            "last_availability_research_clock": last_availability,
        },
        "population": {
            "raw_events": raw_events,
            "arm_rows": arm_rows,
            "router_pass_events": pass_events,
            "router_pass_rate": pass_events / max(raw_events, 1),
            "router_pass_long": pass_long,
            "router_pass_short": pass_short,
            "cadence_per_week": cadence,
            "max_year_share": observed_max_year_share,
            "median_stop_pips": median_stop,
            "median_cost_to_stop_ratio": median_cost_ratio,
        },
        "distribution": {
            "all_events_by_year": sorted_counter(all_by_year),
            "all_events_by_hour": sorted_counter(all_by_hour),
            "pass_events_by_year": sorted_counter(pass_by_year),
            "pass_events_by_hour": sorted_counter(pass_by_hour),
        },
        "router": {
            "veto_reason_counts": sorted_counter(veto_reason_counts),
            "veto_combination_counts": sorted_counter(veto_combination_counts),
            "veto_group_event_counts": sorted_counter(veto_group_counts),
            "counterfactual_pass_if_group_removed_alone": sorted_counter(removal_only_pass_counts),
            "counterfactual_total_pass_if_groups_removed": [
                {
                    "removed_groups": key,
                    "additional_pass_events": additional,
                    "total_pass_events": pass_events + additional,
                    "cadence_per_week": (pass_events + additional) / elapsed_weeks,
                }
                for key, additional in sorted(
                    removal_subset_pass_counts.items(),
                    key=lambda item: (len(item[0].split("+")), -item[1], item[0]),
                )
            ],
            "indicator_validity_rates": validity_rates,
        },
        "integrity": {
            "forbidden_outcome_columns": forbidden,
            "matched_pair_errors": matched_pair_errors[:100],
            "matched_pair_error_count": len(matched_pair_errors),
        },
        "frozen_gates": {
            "thresholds": {
                "min_raw_events": min_raw_events,
                "min_router_pass_events": min_pass_events,
                "cadence_range_per_week": [min_cadence, max_cadence],
                "min_router_pass_per_side": min_pass_per_side,
                "max_year_share": max_year_share,
                "min_median_stop_pips": min_median_stop_pips,
                "max_median_cost_to_stop_ratio": max_median_cost_to_stop,
            },
            "results": gate_results,
            "all_pass": all(gate_results.values()),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--analysis-from", required=True, type=date.fromisoformat)
    parser.add_argument("--analysis-to", required=True, type=date.fromisoformat)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = analyze(
        args.csv_path,
        analysis_from=args.analysis_from,
        analysis_to=args.analysis_to,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    args.out.write_text(payload, encoding="utf-8", newline="\n")
    print(
        "ROUTER_TELEMETRY_ANALYZED "
        f"events={result['population']['raw_events']} "
        f"passes={result['population']['router_pass_events']} "
        f"all_pass={str(result['frozen_gates']['all_pass']).lower()} "
        f"out={args.out.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
