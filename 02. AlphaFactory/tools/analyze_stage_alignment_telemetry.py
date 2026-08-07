#!/usr/bin/env python3
"""Stream and validate outcome-blind JCDR005 stage-alignment telemetry.

This analyzer deliberately has no outcome or price-forward interface.  It
summarizes semantic indicator roles, causal age buckets, structural geometry,
year/hour representativeness, and the preregistered HYP005 role funnel.  Raw
rows are never retained.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


EXPECTED_HYPOTHESIS = "HYP-JCDR-EURUSD-M5-005"
EXPECTED_VARIANT = "JCDR_STAGE_ALIGNMENT_V1"
EXPECTED_FIELDS = 114
MAX_DEFAULT_BYTES = 64 * 1024 * 1024
MAX_DEFAULT_ROWS = 2_000_000

FORBIDDEN_HEADERS = {
    "availability_price",
    "entry",
    "entry_price",
    "selected_direction",
    "selected_route",
    "route",
    "outcome",
    "win",
    "loss",
    "pnl",
    "profit",
    "mfe",
    "mae",
    "target_hit",
    "stop_hit",
    "future_open",
    "future_high",
    "future_low",
    "future_close",
}

PERCENT_01_FIELDS = {
    "aird_raw_probability_01",
    "aird_vol_percentile_01",
}

PERCENT_100_FIELDS = {
    "aird_held_confidence_pct",
    "aird_p_bull_pct",
    "aird_p_bear_pct",
    "aird_p_range_pct",
    "aird_p_highvol_pct",
    "aird_aligned_probability_pct",
    "aird_opposite_probability_pct",
    "vrc_vol_percentile_pct",
    "mbb_ker_percentile_pct",
    "mbb_squeeze_score_pct",
}

BINARY_FIELDS = {
    "aird_valid",
    "aird_changed",
    "vrc_valid",
    "vrc_changed",
    "vrc_high_vol",
    "vrc_low_vol",
    "mbb_dc_valid",
    "mbb_squeeze_state",
    "mbb_release",
    "tb_closed_valid",
    "tb_sweep_high",
    "tb_sweep_low",
    "tb_void_bull",
    "tb_void_bear",
    "tb_displacement_bull",
    "tb_displacement_bear",
    "tb_has_liquidity_high",
    "tb_has_liquidity_low",
}

AGE_CAPS = {
    "vrc_change_age": 12,
    "mbb_squeeze_age": 20,
    "mbb_release_age": 20,
    "qqe_composite_change_age": 12,
    "qqe_zero_cross_age": 12,
    "tb_structure_age": 20,
    "tb_sweep_high_age": 20,
    "tb_sweep_low_age": 20,
}

QUANTILE_FIELDS = {
    "aird_held_confidence_pct",
    "aird_aligned_probability_pct",
    "aird_opposite_probability_pct",
    "aird_trend_corr",
    "aird_momentum",
    "aird_drift",
    "vrc_hurst",
    "vrc_adx",
    "vrc_chop",
    "vrc_vol_percentile_pct",
    "vrc_composite",
    "vrc_cluster_alignment",
    "mbb_ker",
    "mbb_ker_percentile_pct",
    "mbb_bandwidth",
    "mbb_squeeze_score_pct",
    "mbb_signal_alignment",
    "qqe_primary_alignment",
    "qqe_secondary_alignment",
    "long_stop_pips",
    "long_corridor_pips",
    "short_stop_pips",
    "short_corridor_pips",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def as_float(row: dict[str, str], key: str) -> float:
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError(f"{key} is not finite")
    return value


def as_int(row: dict[str, str], key: str) -> int:
    value = as_float(row, key)
    rounded = round(value)
    if abs(value - rounded) > 1e-9:
        raise ValueError(f"{key} is not integral: {value}")
    return int(rounded)


def age_bucket(value: int) -> str:
    if value < 0:
        return "missing"
    if value == 0:
        return "0"
    if value <= 2:
        return "1-2"
    if value <= 5:
        return "3-5"
    if value <= 10:
        return "6-10"
    return "11-20"


def quantiles(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "min": None, "p10": None, "p25": None, "median": None, "p75": None, "p90": None, "max": None}
    ordered = sorted(values)

    def pick(p: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        position = (len(ordered) - 1) * p
        lo = math.floor(position)
        hi = math.ceil(position)
        if lo == hi:
            return ordered[lo]
        weight = position - lo
        return ordered[lo] * (1.0 - weight) + ordered[hi] * weight

    return {
        "n": len(ordered),
        "min": ordered[0],
        "p10": pick(0.10),
        "p25": pick(0.25),
        "median": pick(0.50),
        "p75": pick(0.75),
        "p90": pick(0.90),
        "max": ordered[-1],
    }


def sorted_counts(counter: Counter[Any]) -> dict[str, int]:
    return {str(key): int(counter[key]) for key in sorted(counter, key=lambda item: str(item))}


def check_range(value: float, lo: float, hi: float, field: str, line: int) -> None:
    if value < lo - 1e-9 or value > hi + 1e-9:
        raise ValueError(f"line {line}: {field}={value} outside [{lo},{hi}]")


def stage_modes(row: dict[str, str]) -> dict[str, bool | str]:
    sign = as_int(row, "cluster_sign")
    held_regime = as_int(row, "aird_held_regime")
    held_conf = as_float(row, "aird_held_confidence_pct")
    aligned_regime = (sign == 1 and held_regime == 0) or (sign == -1 and held_regime == 1)
    opposite_regime = (sign == 1 and held_regime == 1) or (sign == -1 and held_regime == 0)

    qqe_composite = as_int(row, "qqe_composite")
    qqe_current_aligned = sign * qqe_composite > 0
    qqe_primary_aligned = as_float(row, "qqe_primary_alignment") > 0
    qqe_secondary_aligned = as_float(row, "qqe_secondary_alignment") > 0

    vrc_high = as_int(row, "vrc_high_vol") == 1
    vrc_low = as_int(row, "vrc_low_vol") == 1
    mbb_trend = as_int(row, "mbb_regime") == 1
    mbb_squeeze = as_int(row, "mbb_squeeze_state") == 1
    mbb_release = as_int(row, "mbb_release") == 1
    energy_expansion = vrc_high or mbb_trend or mbb_release
    energy_compression = vrc_low or mbb_squeeze

    cluster_geometry = as_int(row, "long_geometry_pass" if sign == 1 else "short_geometry_pass") == 1
    opposite_geometry = as_int(row, "short_geometry_pass" if sign == 1 else "long_geometry_pass") == 1
    both_geometry_valid = as_int(row, "long_geometry_pass") >= 0 and as_int(row, "short_geometry_pass") >= 0
    vrc_direction_aligned = as_float(row, "vrc_cluster_alignment") > 0
    tb_bias_aligned = sign * as_int(row, "tb_bias") > 0
    tb_bias_reversal = sign * as_int(row, "tb_bias") < 0
    tb_continuation_sweep = (sign == 1 and as_int(row, "tb_sweep_low") == 1) or (sign == -1 and as_int(row, "tb_sweep_high") == 1)
    tb_reversal_sweep = (sign == 1 and as_int(row, "tb_sweep_high") == 1) or (sign == -1 and as_int(row, "tb_sweep_low") == 1)
    tb_displacement_aligned = (sign == 1 and as_int(row, "tb_displacement_bull") == 1) or (sign == -1 and as_int(row, "tb_displacement_bear") == 1)
    tb_displacement_reversal = (sign == 1 and as_int(row, "tb_displacement_bear") == 1) or (sign == -1 and as_int(row, "tb_displacement_bull") == 1)
    tb_void_aligned = (sign == 1 and as_int(row, "tb_void_bull") == 1) or (sign == -1 and as_int(row, "tb_void_bear") == 1)
    tb_void_reversal = (sign == 1 and as_int(row, "tb_void_bear") == 1) or (sign == -1 and as_int(row, "tb_void_bull") == 1)

    return {
        "core_valid": as_int(row, "invalid_mask") == 0,
        "aird_aligned": aligned_regime,
        "aird_aligned_conf80": aligned_regime and held_conf >= 80.0,
        "aird_opposite": opposite_regime,
        "aird_range": held_regime == 2,
        "aird_highvol": held_regime == 3,
        "qqe_current_aligned": qqe_current_aligned,
        "qqe_primary_aligned": qqe_primary_aligned,
        "qqe_secondary_aligned": qqe_secondary_aligned,
        "qqe_both_aligned": qqe_primary_aligned and qqe_secondary_aligned,
        "energy_expansion": energy_expansion,
        "energy_compression": energy_compression,
        "unreleased_squeeze": mbb_squeeze and not mbb_release,
        "cluster_geometry": cluster_geometry,
        "opposite_geometry": opposite_geometry,
        "both_geometry_valid": both_geometry_valid,
        "vrc_direction_aligned": vrc_direction_aligned,
        "tb_bias_aligned": tb_bias_aligned,
        "tb_bias_reversal": tb_bias_reversal,
        "tb_continuation_sweep": tb_continuation_sweep,
        "tb_reversal_sweep": tb_reversal_sweep,
        "tb_displacement_aligned": tb_displacement_aligned,
        "tb_displacement_reversal": tb_displacement_reversal,
        "tb_void_aligned": tb_void_aligned,
        "tb_void_reversal": tb_void_reversal,
        "aird_mode": "aligned" if aligned_regime else "opposite" if opposite_regime else "range" if held_regime == 2 else "highvol",
        "qqe_mode": "aligned" if qqe_current_aligned else "opposite" if sign * qqe_composite < 0 else "neutral",
        "energy_mode": "compression" if energy_compression and not energy_expansion else "expansion" if energy_expansion and not energy_compression else "mixed" if energy_expansion and energy_compression else "neutral",
    }


def analyze(csv_path: Path, run_meta_path: Path, manifest_path: Path, max_bytes: int, max_rows: int) -> dict[str, Any]:
    size = csv_path.stat().st_size
    if size > max_bytes:
        raise ValueError(f"telemetry size {size} exceeds max-bytes {max_bytes}")

    run_meta = json.loads(run_meta_path.read_text(encoding="utf-8-sig"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))

    counts: dict[str, Counter[Any]] = defaultdict(Counter)
    pairs: dict[str, Counter[Any]] = defaultdict(Counter)
    ages: dict[str, Counter[Any]] = defaultdict(Counter)
    numeric: dict[str, list[float]] = {field: [] for field in QUANTILE_FIELDS}
    event_ids: set[str] = set()
    duplicate_ids: list[str] = []
    row_count = 0
    malformed_rows = 0
    first_date: int | None = None
    last_date: int | None = None

    funnel_names = [
        "raw",
        "core_valid",
        "not_unreleased_squeeze",
        "aird_aligned_conf80",
        "qqe_current_aligned",
        "energy_expansion",
        "cluster_geometry",
    ]
    funnel = Counter({name: 0 for name in funnel_names})
    independent = Counter()
    scenario_counts = Counter()

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header")
        headers = list(reader.fieldnames)
        if len(headers) != EXPECTED_FIELDS:
            raise ValueError(f"expected {EXPECTED_FIELDS} fields, found {len(headers)}")
        forbidden_present = sorted(set(headers) & FORBIDDEN_HEADERS)
        if forbidden_present:
            raise ValueError(f"forbidden outcome/route headers: {forbidden_present}")

        for line_no, row in enumerate(reader, start=2):
            row_count += 1
            if row_count > max_rows:
                raise ValueError(f"row count exceeds max-rows {max_rows}")
            if None in row or len(row) != EXPECTED_FIELDS:
                malformed_rows += 1
                continue
            if row["record_type"] != "EVENT_DIAGNOSTIC":
                raise ValueError(f"line {line_no}: unexpected record_type")
            if row["hypothesis_id"] != EXPECTED_HYPOTHESIS or row["variant"] != EXPECTED_VARIANT:
                raise ValueError(f"line {line_no}: identity mismatch")
            event_id = row["event_id"]
            if event_id in event_ids:
                if len(duplicate_ids) < 20:
                    duplicate_ids.append(event_id)
            event_ids.add(event_id)

            sign = as_int(row, "cluster_sign")
            if sign not in {-1, 1}:
                raise ValueError(f"line {line_no}: cluster_sign outside -1/+1")
            date = as_int(row, "research_date")
            year = as_int(row, "research_year")
            hour = as_int(row, "research_hour")
            check_range(hour, 0, 23, "research_hour", line_no)
            first_date = date if first_date is None else min(first_date, date)
            last_date = date if last_date is None else max(last_date, date)

            for field in PERCENT_01_FIELDS:
                check_range(as_float(row, field), 0.0, 1.0, field, line_no)
            for field in PERCENT_100_FIELDS:
                check_range(as_float(row, field), 0.0, 100.0, field, line_no)
            for field in BINARY_FIELDS:
                if as_int(row, field) not in {0, 1}:
                    raise ValueError(f"line {line_no}: {field} outside binary domain")
            if as_int(row, "qqe_zero_cross") not in {-1, 0, 1}:
                raise ValueError(f"line {line_no}: qqe_zero_cross outside ternary domain")
            if as_int(row, "tb_structure_event") not in {-2, -1, 0, 1, 2}:
                raise ValueError(f"line {line_no}: tb_structure_event outside TB event domain")
            for field in ("long_geometry_pass", "short_geometry_pass"):
                if as_int(row, field) not in {-1, 0, 1}:
                    raise ValueError(f"line {line_no}: {field} outside invalid/pass domain")
            for field, cap in AGE_CAPS.items():
                age = as_int(row, field)
                if age < -1 or age > cap:
                    raise ValueError(f"line {line_no}: {field}={age} outside [-1,{cap}]")
                ages[field][age_bucket(age)] += 1

            for field in QUANTILE_FIELDS:
                if row[field] == "":
                    # Optional continuous geometry/indicator diagnostics remain
                    # explicitly missing; their validity/pass fields carry the
                    # reason and missing values must never become numeric zero.
                    continue
                value = as_float(row, field)
                # Invalid TB geometry is explicit; do not pollute price-distance distributions.
                if field.startswith("long_") and as_int(row, "long_geometry_pass") == -1:
                    continue
                if field.startswith("short_") and as_int(row, "short_geometry_pass") == -1:
                    continue
                numeric[field].append(value)

            modes = stage_modes(row)
            counts["year"][year] += 1
            counts["hour"][hour] += 1
            counts["cluster_sign"][sign] += 1
            counts["invalid_mask"][as_int(row, "invalid_mask")] += 1
            counts["invalid_reasons"][row["invalid_reasons"]] += 1
            counts["aird_held_regime"][as_int(row, "aird_held_regime")] += 1
            counts["aird_raw_regime"][as_int(row, "aird_raw_regime")] += 1
            counts["vrc_regime"][as_int(row, "vrc_regime")] += 1
            counts["mbb_regime"][as_int(row, "mbb_regime")] += 1
            counts["mbb_priority_signal"][as_int(row, "mbb_priority_signal")] += 1
            counts["qqe_composite"][as_int(row, "qqe_composite")] += 1
            counts["qqe_zero_cross"][as_int(row, "qqe_zero_cross")] += 1
            counts["tb_bias"][as_int(row, "tb_bias")] += 1
            counts["tb_structure_event"][as_int(row, "tb_structure_event")] += 1
            counts["tb_ready_mask"][as_int(row, "tb_ready_mask")] += 1
            counts["long_geometry_pass"][as_int(row, "long_geometry_pass")] += 1
            counts["short_geometry_pass"][as_int(row, "short_geometry_pass")] += 1

            pairs["aird_x_qqe"][(modes["aird_mode"], modes["qqe_mode"])] += 1
            pairs["aird_x_energy"][(modes["aird_mode"], modes["energy_mode"])] += 1
            pairs["qqe_x_energy"][(modes["qqe_mode"], modes["energy_mode"])] += 1
            pairs["tb_structure_x_cluster_geometry"][(as_int(row, "tb_structure_event"), int(bool(modes["cluster_geometry"])))] += 1
            pairs["tb_structure_age_x_cluster_geometry"][(age_bucket(as_int(row, "tb_structure_age")), int(bool(modes["cluster_geometry"])))] += 1
            pairs["tb_structure_age_x_opposite_geometry"][(age_bucket(as_int(row, "tb_structure_age")), int(bool(modes["opposite_geometry"])))] += 1
            pairs["aird_x_cluster_geometry"][(modes["aird_mode"], int(bool(modes["cluster_geometry"])))] += 1
            pairs["aird_x_opposite_geometry"][(modes["aird_mode"], int(bool(modes["opposite_geometry"])))] += 1
            pairs["qqe_x_cluster_geometry"][(modes["qqe_mode"], int(bool(modes["cluster_geometry"])))] += 1
            pairs["qqe_x_opposite_geometry"][(modes["qqe_mode"], int(bool(modes["opposite_geometry"])))] += 1
            pairs["energy_x_cluster_geometry"][(modes["energy_mode"], int(bool(modes["cluster_geometry"])))] += 1
            pairs["energy_x_opposite_geometry"][(modes["energy_mode"], int(bool(modes["opposite_geometry"])))] += 1
            pairs["hour_x_cluster_sign"][(hour, sign)] += 1

            for name in (
                "core_valid",
                "aird_aligned",
                "aird_aligned_conf80",
                "aird_opposite",
                "aird_range",
                "aird_highvol",
                "qqe_current_aligned",
                "qqe_primary_aligned",
                "qqe_secondary_aligned",
                "qqe_both_aligned",
                "energy_expansion",
                "energy_compression",
                "unreleased_squeeze",
                "cluster_geometry",
                "opposite_geometry",
                "both_geometry_valid",
                "vrc_direction_aligned",
                "tb_bias_aligned",
                "tb_bias_reversal",
                "tb_continuation_sweep",
                "tb_reversal_sweep",
                "tb_displacement_aligned",
                "tb_displacement_reversal",
                "tb_void_aligned",
                "tb_void_reversal",
            ):
                independent[name] += int(bool(modes[name]))

            structure_recent_10 = 0 <= as_int(row, "tb_structure_age") <= 10
            not_continuation_aird = bool(modes["aird_opposite"]) or bool(modes["aird_range"])
            continuation_surface = (
                bool(modes["core_valid"])
                and bool(modes["cluster_geometry"])
                and bool(modes["aird_aligned"])
                and bool(modes["qqe_primary_aligned"])
                and bool(modes["energy_expansion"])
            )
            reversal_surface = (
                bool(modes["core_valid"])
                and bool(modes["opposite_geometry"])
                and not_continuation_aird
                and not bool(modes["qqe_current_aligned"])
                and bool(modes["energy_compression"])
            )
            transition_reversal_surface = (
                bool(modes["core_valid"])
                and bool(modes["opposite_geometry"])
                and not bool(modes["aird_aligned"])
                and not bool(modes["qqe_current_aligned"])
            )
            scenario_counts["continuation_geometry_only"] += int(bool(modes["core_valid"]) and bool(modes["cluster_geometry"]))
            scenario_counts["opposite_geometry_only"] += int(bool(modes["core_valid"]) and bool(modes["opposite_geometry"]))
            scenario_counts["continuation_semantic_surface"] += int(continuation_surface)
            scenario_counts["continuation_plus_tb_bias"] += int(continuation_surface and bool(modes["tb_bias_aligned"]))
            scenario_counts["continuation_plus_recent_structure_10"] += int(continuation_surface and structure_recent_10)
            scenario_counts["reversal_semantic_surface"] += int(reversal_surface)
            scenario_counts["reversal_plus_tb_bias"] += int(reversal_surface and bool(modes["tb_bias_reversal"]))
            scenario_counts["reversal_plus_current_exhausted_side_sweep"] += int(reversal_surface and bool(modes["tb_reversal_sweep"]))
            scenario_counts["transition_reversal_surface"] += int(transition_reversal_surface)
            scenario_counts["transition_reversal_plus_tb_bias"] += int(transition_reversal_surface and bool(modes["tb_bias_reversal"]))

            funnel["raw"] += 1
            cumulative = bool(modes["core_valid"])
            funnel["core_valid"] += int(cumulative)
            cumulative = cumulative and not bool(modes["unreleased_squeeze"])
            funnel["not_unreleased_squeeze"] += int(cumulative)
            cumulative = cumulative and bool(modes["aird_aligned_conf80"])
            funnel["aird_aligned_conf80"] += int(cumulative)
            cumulative = cumulative and bool(modes["qqe_current_aligned"])
            funnel["qqe_current_aligned"] += int(cumulative)
            cumulative = cumulative and bool(modes["energy_expansion"])
            funnel["energy_expansion"] += int(cumulative)
            cumulative = cumulative and bool(modes["cluster_geometry"])
            funnel["cluster_geometry"] += int(cumulative)

    if malformed_rows:
        raise ValueError(f"malformed row count: {malformed_rows}")
    if duplicate_ids:
        raise ValueError(f"duplicate event ids: {duplicate_ids}")

    if manifest.get("run_id") != "20260807_180115" or manifest.get("hypothesis_id") != EXPECTED_HYPOTHESIS:
        raise ValueError("run manifest identity mismatch")
    if run_meta.get("hypothesis_id") != EXPECTED_HYPOTHESIS or run_meta.get("variant") != EXPECTED_VARIANT:
        raise ValueError("RunMeta identity mismatch")
    if int(run_meta.get("raw_events", -1)) != row_count or int(run_meta.get("diagnostic_rows", -1)) != row_count:
        raise ValueError("RunMeta row counts do not match telemetry")
    if run_meta.get("outcomes_observed") is not False or run_meta.get("economics_executed") is not False:
        raise ValueError("RunMeta violates outcome-blind authority")

    duration_days = (datetime(2020, 12, 31) - datetime(2016, 1, 4)).days + 1
    weeks = duration_days / 7.0
    year_counts = counts["year"]
    max_year_share = max(year_counts.values()) / row_count if row_count else 0.0

    pair_output: dict[str, dict[str, int]] = {}
    for name, counter in pairs.items():
        pair_output[name] = {"|".join(map(str, key)): int(value) for key, value in sorted(counter.items(), key=lambda item: str(item[0]))}

    return {
        "schema_version": "jcdr005.stage_alignment_analysis.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority": "OUTCOME_BLIND_DESCRIPTIVE_ONLY_NO_ECONOMIC_CLAIM",
        "source": {
            "path": str(csv_path.resolve()),
            "sha256": sha256_file(csv_path),
            "bytes": size,
            "rows": row_count,
            "fields": EXPECTED_FIELDS,
        },
        "bindings": {
            "run_meta_path": str(run_meta_path.resolve()),
            "run_meta_sha256": sha256_file(run_meta_path),
            "manifest_path": str(manifest_path.resolve()),
            "manifest_sha256": sha256_file(manifest_path),
            "hypothesis_id": EXPECTED_HYPOTHESIS,
            "variant": EXPECTED_VARIANT,
            "run_id": manifest["run_id"],
        },
        "integrity": {
            "status": "PASS",
            "unique_event_ids": len(event_ids),
            "duplicate_event_ids": 0,
            "malformed_rows": 0,
            "forbidden_headers": [],
            "first_analysis_date": first_date,
            "last_analysis_date": last_date,
            "runtime_all_pass": bool(run_meta.get("runtime_all_pass")),
            "outcomes_observed": False,
            "economics_executed": False,
        },
        "population": {
            "raw_events": row_count,
            "weeks": weeks,
            "events_per_week": row_count / weeks if weeks else 0.0,
            "max_year_share": max_year_share,
            "by_year": sorted_counts(counts["year"]),
            "by_broker_hour": sorted_counts(counts["hour"]),
            "by_cluster_sign": sorted_counts(counts["cluster_sign"]),
            "invalid_mask": sorted_counts(counts["invalid_mask"]),
            "invalid_reasons": sorted_counts(counts["invalid_reasons"]),
        },
        "semantic_occurrence": {
            "independent_role_counts": sorted_counts(independent),
            "fixed_descriptive_scenario_counts": sorted_counts(scenario_counts),
            "categorical": {name: sorted_counts(counter) for name, counter in sorted(counts.items()) if name not in {"year", "hour", "cluster_sign", "invalid_mask", "invalid_reasons"}},
            "joint_tables": pair_output,
            "causal_age_buckets": {name: sorted_counts(counter) for name, counter in sorted(ages.items())},
        },
        "role_funnel": {
            "definition": "HYP004 same-bar semantic funnel reproduced descriptively; no route or outcome is selected",
            "cumulative_counts": {name: int(funnel[name]) for name in funnel_names},
            "cumulative_share_of_raw": {name: (funnel[name] / row_count if row_count else 0.0) for name in funnel_names},
        },
        "continuous_distributions": {field: quantiles(values) for field, values in sorted(numeric.items())},
        "verdict": "PASS_OUTCOME_BLIND_STAGE_ALIGNMENT_DATASET",
        "permissions": {
            "derive_fresh_causal_hypothesis": True,
            "select_threshold_from_outcomes": False,
            "claim_edge": False,
            "optimize": False,
            "paper_or_live": False,
        },
    }


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--run-meta", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-bytes", type=int, default=MAX_DEFAULT_BYTES)
    parser.add_argument("--max-rows", type=int, default=MAX_DEFAULT_ROWS)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    result = analyze(args.csv, args.run_meta, args.manifest, args.max_bytes, args.max_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, indent=2, sort_keys=False) + "\n"
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(
        "JCDR005_STAGE_ANALYSIS_OK "
        f"rows={result['source']['rows']} "
        f"sha256={result['source']['sha256']} "
        f"output={args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
