#!/usr/bin/env python3
"""Stream and validate outcome-blind JCDR role-router source telemetry."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterable


EXPECTED_ARMS = {"ROLE_PRIMARY", "INVERSE_CONTROL"}
EXPECTED_ROUTES = {"TRUE_REVERSAL", "FOLLOW_CONTROL"}
OPPOSITE_DIRECTION = {"LONG": "SHORT", "SHORT": "LONG"}
FORBIDDEN_COLUMNS = {
    "availability_price",
    "entry_price",
    "exit_price",
    "post_availability_price",
    "post_entry_price",
    "target_hit",
    "stop_hit",
    "return",
    "forward_return",
    "mfe",
    "mae",
    "outcome",
    "pnl",
    "profit",
    "balance",
    "equity",
    "profit_factor",
    "drawdown",
    "expectancy",
    "win",
    "loss",
}
REQUIRED_COLUMNS = {
    "hypothesis_id",
    "variant",
    "signal_id",
    "arm",
    "direction",
    "decision_research_clock",
    "availability_research_clock",
    "research_year",
    "research_hour",
    "route",
    "invalid_mask",
    "routed",
    "planned_stop_pips",
    "corridor_pips",
    "cost_to_stop_ratio",
}


def sha256_stream(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def finite_float(value: str, field: str, line: int) -> float:
    try:
        result = float(value)
    except ValueError as exc:
        raise ValueError(f"line {line}: {field} is not numeric: {value!r}") from exc
    if not math.isfinite(result) or abs(result) >= 1.0e100:
        raise ValueError(f"line {line}: {field} is not finite: {value!r}")
    return result


def exact_flag(value: str, field: str, line: int) -> bool:
    parsed = finite_float(value, field, line)
    if parsed not in (0.0, 1.0):
        raise ValueError(f"line {line}: {field} must be exact 0/1: {value!r}")
    return parsed == 1.0


def counter_rows(counter: Counter[Any]) -> list[dict[str, Any]]:
    return [
        {"key": key, "count": count}
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    ]


def analyze(
    csv_path: Path,
    run_meta_path: Path,
    data_quality_path: Path,
    *,
    analysis_from: date,
    analysis_to: date,
) -> dict[str, Any]:
    if analysis_to <= analysis_from:
        raise ValueError("analysis_to must be after analysis_from")
    run_meta = json.loads(run_meta_path.read_text(encoding="utf-8-sig"))
    data_quality = json.loads(data_quality_path.read_text(encoding="utf-8-sig"))

    rows = 0
    events = 0
    primary_long = 0
    primary_short = 0
    routes: Counter[str] = Counter()
    by_year: Counter[int] = Counter()
    by_hour: Counter[int] = Counter()
    feature_flags: Counter[str] = Counter()
    stop_values: list[float] = []
    cost_values: list[float] = []
    corridor_values: list[float] = []
    integrity_errors: list[str] = []
    first_availability: str | None = None
    last_availability: str | None = None

    def finalize(pair: list[tuple[int, dict[str, str]]], fieldnames: list[str]) -> None:
        nonlocal events, primary_long, primary_short, first_availability, last_availability
        if not pair:
            return
        events += 1
        signal_id = pair[0][1]["signal_id"]
        if len(pair) != 2:
            integrity_errors.append(f"{signal_id}: expected 2 adjacent rows, found {len(pair)}")
            return
        arms = {row["arm"] for _, row in pair}
        if arms != EXPECTED_ARMS:
            integrity_errors.append(f"{signal_id}: arms={sorted(arms)!r}")
            return
        indexed = {row["arm"]: (line, row) for line, row in pair}
        primary_line, primary = indexed["ROLE_PRIMARY"]
        _, inverse = indexed["INVERSE_CONTROL"]
        if OPPOSITE_DIRECTION.get(primary["direction"]) != inverse["direction"]:
            integrity_errors.append(
                f"{signal_id}: directions={primary['direction']}/{inverse['direction']}"
            )
        for field in fieldnames:
            if field not in {"arm", "direction"} and primary[field] != inverse[field]:
                integrity_errors.append(f"{signal_id}: matched-arm mismatch in {field}")
        route = primary["route"]
        if route not in EXPECTED_ROUTES:
            integrity_errors.append(f"{signal_id}: unsupported route {route!r}")
        if int(primary["invalid_mask"]) != 0:
            integrity_errors.append(f"{signal_id}: exported routed row has invalid_mask")
        if not exact_flag(primary["routed"], "routed", primary_line):
            integrity_errors.append(f"{signal_id}: exported row is not routed")

        direction = primary["direction"]
        if direction == "LONG":
            primary_long += 1
        elif direction == "SHORT":
            primary_short += 1
        else:
            integrity_errors.append(f"{signal_id}: invalid primary direction {direction!r}")
        routes[route] += 1
        by_year[int(primary["research_year"])] += 1
        by_hour[int(primary["research_hour"])] += 1
        availability = primary["availability_research_clock"]
        first_availability = availability if first_availability is None else min(first_availability, availability)
        last_availability = availability if last_availability is None else max(last_availability, availability)
        for flag in (
            "aird_follow",
            "qqe_follow",
            "vrc_disorder",
            "vrc_high_or_compression",
            "unreleased_squeeze",
        ):
            if flag in primary and exact_flag(primary[flag], flag, primary_line):
                feature_flags[flag] += 1
        aird_follow = exact_flag(primary.get("aird_follow", "0"), "aird_follow", primary_line)
        qqe_follow = exact_flag(primary.get("qqe_follow", "0"), "qqe_follow", primary_line)
        continuation_energy = (
            exact_flag(primary.get("vrc_high_vol", "0"), "vrc_high_vol", primary_line)
            or finite_float(primary.get("mbb_regime", "0"), "mbb_regime", primary_line) == 1.0
            or exact_flag(primary.get("mbb_release", "0"), "mbb_release", primary_line)
        )
        if aird_follow and qqe_follow:
            feature_flags["aird_qqe_joint"] += 1
        if continuation_energy:
            feature_flags["continuation_energy"] += 1
        if aird_follow and qqe_follow and continuation_energy:
            feature_flags["frozen_follow_predicate"] += 1
        elif aird_follow and qqe_follow:
            feature_flags["joint_without_energy"] += 1
        elif continuation_energy:
            feature_flags["energy_without_joint"] += 1
        stop_values.append(finite_float(primary["planned_stop_pips"], "planned_stop_pips", primary_line))
        corridor_values.append(finite_float(primary["corridor_pips"], "corridor_pips", primary_line))
        cost_values.append(finite_float(primary["cost_to_stop_ratio"], "cost_to_stop_ratio", primary_line))

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = sorted(REQUIRED_COLUMNS - set(fieldnames))
        if missing:
            raise ValueError(f"missing required columns: {missing}")
        forbidden = sorted(FORBIDDEN_COLUMNS & set(fieldnames))
        current_id: str | None = None
        current_pair: list[tuple[int, dict[str, str]]] = []
        for line, row in enumerate(reader, start=2):
            rows += 1
            signal_id = row["signal_id"]
            if not signal_id:
                raise ValueError(f"line {line}: empty signal_id")
            if current_id is not None and signal_id != current_id:
                finalize(current_pair, fieldnames)
                current_pair = []
            current_id = signal_id
            current_pair.append((line, row))
            if len(current_pair) > 2:
                raise ValueError(f"line {line}: more than two adjacent rows for {signal_id}")
        finalize(current_pair, fieldnames)

    meta_consistency = {
        "routed_events": int(run_meta["routed_events"]) == events,
        "arm_rows": int(run_meta["arm_rows"]) == rows,
        "primary_long": int(run_meta["primary_long"]) == primary_long,
        "primary_short": int(run_meta["primary_short"]) == primary_short,
        "route_reversal": int(run_meta["route_reversal"]) == routes["TRUE_REVERSAL"],
        "route_follow": int(run_meta["route_follow"]) == routes["FOLLOW_CONTROL"],
    }
    elapsed_weeks = float(run_meta["elapsed_weeks"])
    cadence = events / elapsed_weeks
    max_year_share = max(by_year.values(), default=0) / max(events, 1)
    median_stop = statistics.median(stop_values) if stop_values else None
    median_cost = statistics.median(cost_values) if cost_values else None
    median_corridor = statistics.median(corridor_values) if corridor_values else None
    quality_gate = data_quality.get("data_quality_gate", {})
    quality_pass = (
        data_quality.get("verdict") == "PASS"
        and float(quality_gate.get("history_quality", 0.0)) > 97.0
        and quality_gate.get("journal_truncated") is False
    )
    gates = {
        "data_quality": quality_pass,
        "no_trade": bool(run_meta["gates"]["no_trade"]),
        "telemetry_integrity": bool(run_meta["gates"]["telemetry_integrity"]),
        "coverage": bool(run_meta["gates"]["coverage"]),
        "handles_contract": bool(run_meta["gates"]["handles_contract"]),
        "raw_count": int(run_meta["raw_events"]) >= 500,
        "routed_count": events >= 180,
        "cadence": 0.70 <= cadence <= 2.00,
        "sides": primary_long >= 80 and primary_short >= 80,
        "routes": routes["TRUE_REVERSAL"] >= 80 and routes["FOLLOW_CONTROL"] >= 80,
        "year_share": max_year_share <= 0.30,
        "matched_arms": not integrity_errors and rows == events * 2,
        "run_meta_consistency": all(meta_consistency.values()),
        "stop_geometry": median_stop is not None and median_stop >= 6.0,
        "cost_geometry": median_cost is not None and median_cost <= 0.25,
        "no_forbidden_outcome_fields": not forbidden,
        "no_post_availability_reads": int(run_meta["post_availability_price_reads"]) == 0,
        "no_economics": not bool(run_meta["economics_executed"]),
    }
    raw_events = int(run_meta["raw_events"])
    dispositions = {
        key: int(run_meta[key])
        for key in (
            "routed_events",
            "abstain_invalid",
            "abstain_squeeze",
            "abstain_regime_conflict",
            "abstain_corridor",
        )
    }
    return {
        "schema_version": "alphafactory.jcdr004_role_router_analysis.v1",
        "evidence_class": "OUTCOME_BLIND_SOURCE_FEASIBILITY_ONLY",
        "source": {
            "csv_path": str(csv_path.resolve()),
            "csv_sha256": sha256_stream(csv_path),
            "run_meta_path": str(run_meta_path.resolve()),
            "run_meta_sha256": sha256_stream(run_meta_path),
            "data_quality_path": str(data_quality_path.resolve()),
            "data_quality_sha256": sha256_stream(data_quality_path),
        },
        "identity": {
            "hypothesis_id": run_meta["hypothesis_id"],
            "variant": run_meta["variant"],
            "analysis_from": analysis_from.isoformat(),
            "analysis_to": analysis_to.isoformat(),
            "first_availability_research_clock": first_availability,
            "last_availability_research_clock": last_availability,
        },
        "population": {
            "raw_events": raw_events,
            "routed_events": events,
            "arm_rows": rows,
            "primary_long": primary_long,
            "primary_short": primary_short,
            "route_reversal": routes["TRUE_REVERSAL"],
            "route_follow": routes["FOLLOW_CONTROL"],
            "cadence_per_week": cadence,
            "max_year_share": max_year_share,
            "median_stop_pips": median_stop,
            "median_corridor_pips": median_corridor,
            "median_cost_to_stop": median_cost,
        },
        "dispositions": {
            "counts": dispositions,
            "shares_of_raw_events": {
                key: value / max(raw_events, 1) for key, value in dispositions.items()
            },
            "stop_too_tight": int(run_meta["stop_too_tight"]),
            "corridor_too_short": int(run_meta["corridor_too_short"]),
        },
        "distribution": {
            "routed_by_year": counter_rows(by_year),
            "routed_by_hour": counter_rows(by_hour),
            "routed_feature_true_counts": counter_rows(feature_flags),
        },
        "integrity": {
            "forbidden_columns": forbidden,
            "errors": integrity_errors[:100],
            "error_count": len(integrity_errors),
            "run_meta_consistency": meta_consistency,
        },
        "frozen_gates": {
            "results": gates,
            "failed": [name for name, passed in gates.items() if not passed],
            "all_pass": all(gates.values()),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--run-meta", required=True, type=Path)
    parser.add_argument("--data-quality", required=True, type=Path)
    parser.add_argument("--analysis-from", required=True, type=date.fromisoformat)
    parser.add_argument("--analysis-to", required=True, type=date.fromisoformat)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = analyze(
        args.csv_path,
        args.run_meta,
        args.data_quality,
        analysis_from=args.analysis_from,
        analysis_to=args.analysis_to,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        "ROLE_ROUTER_TELEMETRY_ANALYZED "
        f"raw={result['population']['raw_events']} "
        f"routed={result['population']['routed_events']} "
        f"all_pass={str(result['frozen_gates']['all_pass']).lower()} "
        f"out={args.out.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
