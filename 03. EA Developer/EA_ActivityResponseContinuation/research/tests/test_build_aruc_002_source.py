from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "build_aruc_002_source.py"
SPEC = importlib.util.spec_from_file_location("build_aruc_002_source", SOURCE)
assert SPEC and SPEC.loader
sut = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sut)

UTC = timezone.utc


def utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def business_days(start: date, count: int) -> tuple[date, ...]:
    values = []
    current = start
    while len(values) < count:
        if current.weekday() < 5:
            values.append(current)
        current += timedelta(days=1)
    return tuple(values)


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def m1_row(at: datetime, close: float, tick_volume: int = 1) -> dict[str, object]:
    return {
        "time_utc": at,
        "open": close,
        "high": close + 0.0001,
        "low": close - 0.0001,
        "close": close,
        "tick_volume": tick_volume,
    }


def vector_bar(day: date, slot: tuple[int, int], sum_tv: int, *, signs=(1,) * 15):
    return {
        "date": day,
        "slot": slot,
        "sum_tv": sum_tv,
        "tick_volumes": (sum_tv,) + (0,) * 14,
        "price_signs": tuple(signs),
    }


def h1_bar(open_time: datetime, *, close: float = 10.0, true_range: float = 2.0):
    return {
        "time_utc": open_time,
        "open": close,
        "high": close + true_range / 2,
        "low": close - true_range / 2,
        "close": close,
        "tick_volume": 1,
    }


def signal(direction: str, year: int, ratio: float = 0.25) -> dict[str, object]:
    return {"direction": direction, "year": year, "cost_to_sl_ratio": ratio}


def passing_gate_inputs() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    signals = []
    year_counts = ((2016, 30), (2017, 30), (2018, 20), (2019, 20))
    remaining_long = 25
    for year, count in year_counts:
        for _ in range(count):
            direction = "LONG" if remaining_long else "SHORT"
            remaining_long = max(0, remaining_long - 1)
            signals.append(signal(direction, year))
    horizons = [{"source_executable": index < 99} for index in range(100)]
    return signals, horizons


def test_complete_m15_uses_previous_minute_and_exact_q() -> None:
    start = utc(2020, 1, 6, 7, 0)
    closes = [1.0001 if index % 2 == 0 else 1.0000 for index in range(15)]
    rows = [m1_row(start - timedelta(minutes=1), 1.0000, 99)]
    rows.extend(m1_row(start + timedelta(minutes=i), close, i + 1) for i, close in enumerate(closes))

    bars, quality = sut.build_complete_m15(rows)

    assert quality == {"observed_bins": 2, "complete_bins": 1, "incomplete_bins": 1}
    assert len(bars) == 1
    expected_q = sum((1 if i % 2 == 0 else -1) * (i + 1) for i in range(15))
    assert bars[0]["q"] == expected_q
    assert bars[0]["sum_tv"] == sum(range(1, 16))
    assert bars[0]["price_signs"] == tuple(1 if i % 2 == 0 else -1 for i in range(15))
    assert bars[0]["availability_utc"] == start + timedelta(minutes=15)


def test_complete_m15_rejects_gap_duplicate_and_missing_previous_close() -> None:
    start = utc(2020, 1, 6, 7, 0)
    complete = [m1_row(start + timedelta(minutes=i), 1.0 + i * 0.0001) for i in range(15)]
    bars, quality = sut.build_complete_m15(complete)
    assert bars == []
    assert quality["incomplete_bins"] == 1

    with pytest.raises(sut.ContractError, match="duplicated|ordered"):
        sut.build_complete_m15([complete[0], complete[0]])


def test_prior_20_activity_is_same_slot_strictly_causal() -> None:
    dates = business_days(date(2020, 1, 6), 22)
    bars = [vector_bar(day, (7, 0), index + 1) for index, day in enumerate(dates)]
    bars[-1]["sum_tv"] = 1_000_000

    value = sut.activity_ratio_for(bars[20], bars, dates, lookback=20)

    assert value == pytest.approx(21 / 10.5)
    assert sut.activity_ratio_for(bars[19], bars, dates, lookback=20) is None
    missing = [bar for bar in bars if bar["date"] != dates[3]]
    assert sut.activity_ratio_for(missing[19], missing, dates, lookback=20) is None


def test_shifted_ticks_use_current_signs_and_five_prior_date_volume() -> None:
    dates = business_days(date(2020, 1, 1), 26)
    bars = [vector_bar(day, (7, 15), index + 1) for index, day in enumerate(dates)]
    current = dict(bars[-1])
    current["price_signs"] = (1, -1) + (0,) * 13
    bars[20] = {
        **bars[20],
        "tick_volumes": (7, 2) + (0,) * 13,
        "sum_tv": 9,
    }

    shifted = sut.shifted_tick_features(current, bars, dates, shift_dates=5, lookback=20)

    assert shifted == {
        "source_date": dates[20],
        "q": 5,
        "sum_tv": 9,
        "activity": pytest.approx(9 / 10.5),
    }
    assert sut.shifted_tick_features(current, bars[:-1], dates[:-1], shift_dates=5, lookback=20) is None


def test_wilder_atr20_and_closed_h1_availability() -> None:
    bars = [h1_bar(utc(2020, 1, 1) + timedelta(hours=i)) for i in range(20)]
    bars.append(h1_bar(utc(2020, 1, 1) + timedelta(hours=20), true_range=4.0))

    assert sut.latest_wilder_atr20(bars, utc(2020, 1, 1, 19, 59)) is None
    assert sut.latest_wilder_atr20(bars, utc(2020, 1, 1, 20, 0)) == pytest.approx(2.0)
    assert sut.latest_wilder_atr20(bars, utc(2020, 1, 1, 21, 0)) == pytest.approx(2.1)


def test_primary_and_controls_apply_independent_first_per_utc_date_cap() -> None:
    rows = [
        {
            "time_utc": utc(2020, 1, 6, 7, 0), "availability_utc": utc(2020, 1, 6, 7, 15),
            "a": 1.5, "q": 60, "sum_tv": 100, "r": 0.2, "atr20": 0.001,
            "shifted_a": 1.5, "shifted_q": -60, "shifted_sum_tv": 100,
        },
        {
            "time_utc": utc(2020, 1, 6, 7, 15), "availability_utc": utc(2020, 1, 6, 7, 30),
            "a": 2.0, "q": -70, "sum_tv": 100, "r": -0.3, "atr20": 0.001,
            "shifted_a": 2.0, "shifted_q": -70, "shifted_sum_tv": 100,
        },
        {
            "time_utc": utc(2020, 1, 7, 14, 45), "availability_utc": utc(2020, 1, 7, 15, 0),
            "a": 1.6, "q": -55, "sum_tv": 100, "r": -0.15, "atr20": 0.001,
            "shifted_a": 1.6, "shifted_q": -55, "shifted_sum_tv": 100,
        },
    ]

    primary = sut.select_daily_signals(rows, arm="PRIMARY")
    price_only = sut.select_daily_signals(rows, arm="PRICE_ONLY")
    shifted = sut.select_daily_signals(rows, arm="SHIFTED_TICKS")

    assert [row["time_utc"] for row in primary] == [rows[0]["time_utc"], rows[2]["time_utc"]]
    assert [row["direction"] for row in primary] == ["LONG", "SHORT"]
    assert [row["time_utc"] for row in price_only] == [rows[0]["time_utc"], rows[2]["time_utc"]]
    assert [row["time_utc"] for row in shifted] == [rows[1]["time_utc"], rows[2]["time_utc"]]


def test_closed_bar_slot_boundaries_are_exact() -> None:
    base = {
        "a": 1.5, "q": 55, "sum_tv": 100, "r": 0.15, "atr20": 0.001,
        "shifted_a": 1.5, "shifted_q": 55, "shifted_sum_tv": 100,
    }
    candidates = []
    for index, at in enumerate((utc(2020, 1, 6, 6, 45), utc(2020, 1, 7, 7, 0), utc(2020, 1, 8, 14, 45), utc(2020, 1, 9, 15, 0))):
        candidates.append({**base, "time_utc": at, "availability_utc": at + timedelta(minutes=15)})

    selected = sut.select_daily_signals(candidates, arm="PRIMARY")

    assert [row["time_utc"].time() for row in selected] == [datetime.min.replace(hour=7).time(), datetime.min.replace(hour=14, minute=45).time()]


def test_observed_bin_horizon_uses_index_not_wall_clock_and_reads_timestamps_only() -> None:
    availability = utc(2020, 1, 6, 7, 15)
    observed = [availability, availability + timedelta(minutes=30), availability + timedelta(minutes=45), availability + timedelta(minutes=60)]

    mapped = sut.map_observed_horizon(availability, observed)

    assert mapped["entry_open_utc"] == availability
    assert mapped["entry_delay_minutes"] == 0
    assert mapped["exit_availability_utc"] == availability + timedelta(minutes=75)
    assert mapped["observed_horizon_bars"] == 4
    assert mapped["source_executable"] is True

    with pytest.raises(sut.ContractError, match="timestamps only"):
        sut.map_observed_horizon(availability, [{"time_utc": availability, "open": 1.0}])


@pytest.mark.parametrize("delay,expected", [(60, True), (61, False)])
def test_entry_delay_sixty_minute_boundary(delay: int, expected: bool) -> None:
    availability = utc(2020, 1, 6, 7, 15)
    entry = availability + timedelta(minutes=delay)
    observed = [entry + timedelta(minutes=15 * index) for index in range(4)]
    mapped = sut.map_observed_horizon(availability, observed)
    assert mapped["source_executable"] is expected
    assert mapped["reason"] == ("SOURCE_EXECUTABLE" if expected else "ENTRY_DELAY_GT_60M")


def test_right_censor_and_unavailable_funnel_are_explicit() -> None:
    availability = utc(2020, 1, 6, 7, 15)
    right = sut.map_observed_horizon(availability, [availability, availability + timedelta(minutes=15), availability + timedelta(minutes=30)])
    unavailable = sut.map_observed_horizon(availability, [])

    assert right["right_censored"] is True
    assert right["reason"] == "RIGHT_CENSORED_LT4"
    assert unavailable["unavailable"] is True
    assert unavailable["reason"] == "NO_ENTRY_OBSERVED"
    assert sut.horizon_funnel([right, unavailable]) == {
        "primary": 2,
        "source_executable": 0,
        "delayed_over_60m": 0,
        "unavailable": 1,
        "right_censored": 1,
    }


@pytest.mark.parametrize("weeks,expected", [(50.0, True), (20.0, True), (50.0001, False), (19.999, False)])
def test_cadence_gate_boundaries(weeks: float, expected: bool) -> None:
    signals, horizons = passing_gate_inputs()
    report = sut.evaluate_stage0_gates(signals, elapsed_weeks=weeks, formation_complete=99, formation_scheduled=100, horizon_records=horizons)
    assert report["gates"]["cadence_2_to_5_per_week"] is expected


def test_every_stage0_gate_passes_at_inclusive_boundaries() -> None:
    signals, horizons = passing_gate_inputs()
    report = sut.evaluate_stage0_gates(signals, elapsed_weeks=50, formation_complete=99, formation_scheduled=100, horizon_records=horizons)

    assert report["verdict"] == "SOURCE_PASS_FUTURE_ECONOMICS_PREREG_ONLY"
    assert all(report["gates"].values())
    assert report["metrics"]["long_share"] == 0.25
    assert report["metrics"]["max_year_share"] == 0.30
    assert report["metrics"]["median_cost_to_sl_ratio"] == 0.25


@pytest.mark.parametrize("long_count", [25, 75])
def test_both_direction_share_boundaries_are_inclusive(long_count: int) -> None:
    signals, horizons = passing_gate_inputs()
    for index, row in enumerate(signals):
        row["direction"] = "LONG" if index < long_count else "SHORT"
    report = sut.evaluate_stage0_gates(
        signals, elapsed_weeks=50, formation_complete=99,
        formation_scheduled=100, horizon_records=horizons,
    )
    assert report["gates"]["long_share_at_least_0_25"] is True
    assert report["gates"]["short_share_at_least_0_25"] is True


@pytest.mark.parametrize("long_count", [20, 60])
def test_twenty_per_side_boundary_is_inclusive(long_count: int) -> None:
    signals = []
    for index in range(80):
        signals.append(signal("LONG" if index < long_count else "SHORT", 2016 + index // 20))
    horizons = [{"source_executable": True} for _ in signals]
    report = sut.evaluate_stage0_gates(
        signals, elapsed_weeks=40, formation_complete=99,
        formation_scheduled=100, horizon_records=horizons,
    )
    assert report["gates"]["at_least_20_primary_per_side"] is True


@pytest.mark.parametrize(
    "mutation,failed_gate",
    [
        ("long_share", "long_share_at_least_0_25"),
        ("short_share", "short_share_at_least_0_25"),
        ("year_share", "no_year_over_0_30"),
        ("formation", "formation_ratio_at_least_0_99"),
        ("horizon", "source_executable_horizon_ratio_at_least_0_99"),
        ("cost", "median_cost_to_sl_ratio_at_most_0_25"),
        ("long_count", "at_least_20_primary_per_side"),
        ("short_count", "at_least_20_primary_per_side"),
    ],
)
def test_each_non_cadence_gate_fails_immediately_outside_boundary(mutation: str, failed_gate: str) -> None:
    signals, horizons = passing_gate_inputs()
    formation_complete = 99
    if mutation in {"long_share", "long_count"}:
        for index, row in enumerate(signals):
            row["direction"] = "LONG" if index < (24 if mutation == "long_share" else 19) else "SHORT"
    elif mutation in {"short_share", "short_count"}:
        long_count = 76 if mutation == "short_share" else 81
        for index, row in enumerate(signals):
            row["direction"] = "LONG" if index < long_count else "SHORT"
    elif mutation == "year_share":
        for index, row in enumerate(signals):
            row["year"] = 2016 if index < 31 else 2017 + (index % 3)
    elif mutation == "formation":
        formation_complete = 98
    elif mutation == "horizon":
        horizons[98]["source_executable"] = False
    elif mutation == "cost":
        for row in signals:
            row["cost_to_sl_ratio"] = 0.2500001

    report = sut.evaluate_stage0_gates(signals, elapsed_weeks=50, formation_complete=formation_complete, formation_scheduled=100, horizon_records=horizons)

    assert report["gates"][failed_gate] is False
    assert report["verdict"] == "SOURCE_FAIL_NO_ECONOMICS_AUTHORITY"


def public_metadata(kind: str):
    days = ("2016-01-04", "2016-01-05")
    if kind == "M1":
        manifest_rows = [
            {"bytes": 10, "date": day, "relative_path": f"public/DESIGN/{day}/m1.parquet", "rows": 360, "sha256": "A" * 64}
            for day in days
        ]
        manifest = b"".join(canonical(row) + b"\n" for row in manifest_rows)
        receipt = {
            "collection_plan_sha256": "B" * 64,
            "custodian_full_corpus_decoded": True,
            "custodian_tool_sha256": "C" * 64,
            "design_dates": 2,
            "design_manifest_sha256": sha(manifest),
            "design_rows": 720,
            "exact_once_status": "PASS",
            "private_custody_digest": "D" * 64,
            "private_custody_receipt_sha256": "E" * 64,
            "research_holdout_opened": False,
            "research_validation_opened": False,
            "source_bytes": 1,
            "source_footer_length": 1,
            "source_footer_start": 0,
            "source_footer_sha256": "F" * 64,
            "source_sha256": sut.M1_SOURCE_SHA256,
            "source_attempt_id": "SOURCE-ATTEMPT-1",
            "stage_path": "02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002",
            "stage_role": "canonical",
            "supervisor_review_base_sha256": "1" * 64,
            "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
        }
    else:
        manifest_rows = [
            {
                "bytes": 10, "date": day, "relative_path": f"public/DESIGN/{day}/h1.parquet", "rows": 24,
                "schema_version": sut.H1_MANIFEST_ROW_SCHEMA, "sha256": "A" * 64,
            }
            for day in days
        ]
        manifest = b"".join(canonical(row) + b"\n" for row in manifest_rows)
        receipt = {
            "collection_id": sut.H1_COLLECTION_ID,
            "design_dates": 2,
            "design_manifest_sha256": sha(manifest),
            "raw_source_opens": 1,
            "research_holdout_opened": False,
            "research_validation_opened": False,
            "schema_version": sut.H1_RECEIPT_SCHEMA,
            "source_attempt_id": "SOURCE-ATTEMPT-1",
            "source_rows": 48,
            "unselected_shard_opens": 0,
            "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
        }
    receipt_payload = canonical(receipt) + b"\n"
    return receipt_payload, manifest, manifest_rows, days


def production_manifest_days() -> tuple[str, ...]:
    current = date(2016, 1, 4)
    end = date(2020, 12, 31)
    candidates = []
    while current <= end:
        if current.weekday() < 5 or current.weekday() == 6:
            candidates.append(current)
        current += timedelta(days=1)
    weekdays = [day for day in candidates if day.weekday() < 5]
    sundays = [day for day in candidates if day.weekday() == 6]
    removed = set(weekdays[1:7]) | set(sundays[:3])
    values = tuple(day.isoformat() for day in candidates if day not in removed)
    assert len(values) == 1_555
    assert sum(date.fromisoformat(day).weekday() < 5 for day in values) == 1_298
    assert sum(date.fromisoformat(day).weekday() == 6 for day in values) == 257
    return values


def production_metadata(kind: str):
    days = production_manifest_days()
    if kind == "M1":
        row_counts = [1_197] * 40 + [1_196] * (len(days) - 40)
        assert sum(row_counts) == 1_859_820
        rows = [
            {
                "bytes": 10 + index, "date": day,
                "relative_path": f"public/DESIGN/{day}/m1.parquet",
                "rows": row_counts[index], "sha256": f"{index:064X}",
            }
            for index, day in enumerate(days)
        ]
        manifest = b"".join(canonical(row) + b"\n" for row in rows)
        receipt = {
            "collection_plan_sha256": "B" * 64,
            "custodian_full_corpus_decoded": True,
            "custodian_tool_sha256": "C" * 64,
            "design_dates": 1_555,
            "design_manifest_sha256": sha(manifest),
            "design_rows": 1_859_820,
            "exact_once_status": "PASS",
            "private_custody_digest": "D" * 64,
            "private_custody_receipt_sha256": "E" * 64,
            "research_holdout_opened": False,
            "research_validation_opened": False,
            "source_bytes": 1,
            "source_footer_length": 1,
            "source_footer_start": 0,
            "source_footer_sha256": "F" * 64,
            "source_sha256": sut.M1_SOURCE_SHA256,
            "source_attempt_id": "SOURCE-ATTEMPT-1",
            "stage_path": "02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002",
            "stage_role": "canonical",
            "supervisor_review_base_sha256": "1" * 64,
            "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
        }
    else:
        row_counts = [19] * 43 + [20] * (len(days) - 43)
        assert sum(row_counts) == 31_057
        rows = [
            {
                "bytes": 10 + index, "date": day,
                "relative_path": f"public/DESIGN/{day}/h1.parquet",
                "rows": row_counts[index], "schema_version": sut.H1_MANIFEST_ROW_SCHEMA,
                "sha256": f"{index:064X}",
            }
            for index, day in enumerate(days)
        ]
        manifest = b"".join(canonical(row) + b"\n" for row in rows)
        receipt = {
            "collection_id": sut.H1_COLLECTION_ID,
            "design_dates": 1_555,
            "design_manifest_sha256": sha(manifest),
            "raw_source_opens": 1,
            "research_holdout_opened": False,
            "research_validation_opened": False,
            "schema_version": sut.H1_RECEIPT_SCHEMA,
            "source_attempt_id": "SOURCE-ATTEMPT-1",
            "source_rows": 71_785,
            "unselected_shard_opens": 0,
            "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
        }
    receipt_payload = canonical(receipt) + b"\n"
    return receipt_payload, manifest, rows, days


@pytest.mark.parametrize("kind", ["M1", "H1"])
def test_public_manifest_receipt_paths_hashes_rows_and_schema_are_exact(kind: str) -> None:
    receipt, manifest, rows, days = production_metadata(kind)
    parsed = sut.validate_public_metadata(
        kind=kind,
        receipt_payload=receipt,
        manifest_payload=manifest,
        expected_receipt_sha256=sha(receipt),
        expected_manifest_sha256=sha(manifest),
        expected_dates=days,
    )
    assert parsed == rows


@pytest.mark.parametrize("kind", ["M1", "H1"])
def test_exact_production_metadata_shape_is_accepted_without_real_file_access(kind: str) -> None:
    receipt, manifest, rows, _ = production_metadata(kind)
    parsed = sut.validate_public_metadata(
        kind=kind,
        receipt_payload=receipt,
        manifest_payload=manifest,
        expected_receipt_sha256=sha(receipt),
        expected_manifest_sha256=sha(manifest),
    )
    assert parsed == rows


def test_h1_exact_production_shape_with_expected_dates_is_accepted() -> None:
    receipt, manifest, rows, days = production_metadata("H1")
    parsed = sut.validate_public_metadata(
        kind="H1",
        receipt_payload=receipt,
        manifest_payload=manifest,
        expected_receipt_sha256=sha(receipt),
        expected_manifest_sha256=sha(manifest),
        expected_dates=days,
    )
    assert parsed == rows


def test_h1_expected_date_sequence_mismatch_is_independent_failure() -> None:
    receipt, manifest, _, days = production_metadata("H1")
    wrong_dates = list(days)
    wrong_dates[100], wrong_dates[101] = wrong_dates[101], wrong_dates[100]
    with pytest.raises(sut.ContractError, match="dates mismatch"):
        sut.validate_public_metadata(
            kind="H1", receipt_payload=receipt, manifest_payload=manifest,
            expected_receipt_sha256=sha(receipt), expected_manifest_sha256=sha(manifest),
            expected_dates=wrong_dates,
        )


def test_h1_design_manifest_total_mismatch_is_independent_failure() -> None:
    receipt, _, rows, days = production_metadata("H1")
    changed = [dict(row) for row in rows]
    changed[0]["rows"] += 1
    manifest = b"".join(canonical(row) + b"\n" for row in changed)
    receipt_value = json.loads(receipt)
    receipt_value["design_manifest_sha256"] = sha(manifest)
    receipt = canonical(receipt_value) + b"\n"
    with pytest.raises(sut.ContractError, match="DESIGN.*row-count"):
        sut.validate_public_metadata(
            kind="H1", receipt_payload=receipt, manifest_payload=manifest,
            expected_receipt_sha256=sha(receipt), expected_manifest_sha256=sha(manifest),
            expected_dates=days,
        )


def test_h1_raw_source_total_mismatch_is_independent_failure() -> None:
    receipt, manifest, _, days = production_metadata("H1")
    receipt_value = json.loads(receipt)
    receipt_value["source_rows"] = sut.EXPECTED_H1_RAW_SOURCE_ROWS - 1
    receipt = canonical(receipt_value) + b"\n"
    with pytest.raises(sut.ContractError, match="raw-source.*row-count"):
        sut.validate_public_metadata(
            kind="H1", receipt_payload=receipt, manifest_payload=manifest,
            expected_receipt_sha256=sha(receipt), expected_manifest_sha256=sha(manifest),
            expected_dates=days,
        )


def test_h1_receipt_requires_design_capability_only_verdict() -> None:
    receipt, manifest, _, days = production_metadata("H1")
    value = json.loads(receipt)
    value["verdict"] = "WRONG"
    receipt = canonical(value) + b"\n"
    with pytest.raises(sut.ContractError, match="H1 receipt"):
        sut.validate_public_metadata(
            kind="H1", receipt_payload=receipt, manifest_payload=manifest,
            expected_receipt_sha256=sha(receipt), expected_manifest_sha256=sha(manifest),
            expected_dates=days,
        )


def test_m1_h1_manifest_date_sequences_must_match_exactly() -> None:
    _, _, m1_rows, _ = production_metadata("M1")
    _, _, h1_rows, _ = production_metadata("H1")
    sut.validate_matching_manifest_date_sequences(m1_rows, h1_rows)
    changed = [dict(row) for row in h1_rows]
    changed[10]["date"] = "2016-02-29"
    with pytest.raises(sut.ContractError, match="date sequence"):
        sut.validate_matching_manifest_date_sequences(m1_rows, changed)


def test_weekday_decision_dates_exclude_sundays_but_keep_exact_1298() -> None:
    _, _, rows, _ = production_metadata("M1")
    selected = sut.weekday_decision_dates(rows)
    assert len(selected) == 1_298
    assert all(day.weekday() < 5 for day in selected)


@pytest.mark.parametrize("kind", ["M1", "H1"])
@pytest.mark.parametrize("fault", ["receipt_hash", "manifest_hash", "path", "bytes", "rows", "sha", "schema"])
def test_public_metadata_faults_fail_closed(kind: str, fault: str) -> None:
    receipt, manifest, rows, days = production_metadata(kind)
    receipt_sha = sha(receipt)
    manifest_sha = sha(manifest)
    if fault == "receipt_hash":
        receipt_sha = "0" * 64
    elif fault == "manifest_hash":
        manifest_sha = "0" * 64
    else:
        changed = [dict(row) for row in rows]
        if fault == "path":
            changed[0]["relative_path"] = f"private/VALIDATION/{days[0]}/x.parquet"
        elif fault == "bytes":
            changed[0]["bytes"] = 0
        elif fault == "rows":
            changed[0]["rows"] = 0
        elif fault == "sha":
            changed[0]["sha256"] = "not-a-sha"
        elif fault == "schema":
            if kind == "H1":
                changed[0]["schema_version"] = "wrong"
            else:
                changed[0]["schema_version"] = "unexpected"
        manifest = b"".join(canonical(row) + b"\n" for row in changed)
        manifest_sha = sha(manifest)
        receipt_value = json.loads(receipt)
        receipt_value["design_manifest_sha256"] = manifest_sha
        if kind == "M1":
            receipt_value["design_rows"] = sum(int(row["rows"]) for row in changed)
        receipt = canonical(receipt_value) + b"\n"
        receipt_sha = sha(receipt)

    with pytest.raises(sut.ContractError):
        sut.validate_public_metadata(
            kind=kind,
            receipt_payload=receipt,
            manifest_payload=manifest,
            expected_receipt_sha256=receipt_sha,
            expected_manifest_sha256=manifest_sha,
            expected_dates=days,
        )


def decoded_row(day: str, hour: int = 7) -> dict[str, object]:
    at = datetime.fromisoformat(f"{day}T{hour:02d}:00:00")
    return {
        "time_server": at + timedelta(hours=2), "time_utc": at, "utc_offset_h": 2,
        "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0,
        "tick_volume": 1, "spread": 2, "real_volume": 0,
    }


@pytest.mark.parametrize("kind", ["M1", "H1"])
def test_decoded_shard_binds_exact_schema_row_group_and_clock(kind: str) -> None:
    row = decoded_row("2016-01-04")
    decoded = sut.DecodedShard(sut.EXPECTED_ARROW_SCHEMA, 1, (row,))
    rows = sut.validate_decoded_shard(
        decoded, kind=kind, day="2016-01-04", expected_rows=1,
        server_offset_hours=lambda _: 2,
        server_to_utc=lambda value: value - timedelta(hours=2),
    )
    assert rows == (row,)


@pytest.mark.parametrize("fault", ["schema", "row_group", "timezone", "clock", "duplicate"])
def test_decoded_shard_faults_fail_closed(fault: str) -> None:
    row = decoded_row("2016-01-04")
    schema = sut.EXPECTED_ARROW_SCHEMA
    row_groups = 1
    rows = (row,)
    offset = lambda _: 2
    to_utc = lambda value: value - timedelta(hours=2)
    if fault == "schema":
        schema = (("wrong", "timestamp[ns]", True),) + schema[1:]
    elif fault == "row_group":
        row_groups = 2
    elif fault == "timezone":
        rows = ({**row, "time_utc": row["time_utc"].replace(tzinfo=UTC)},)
    elif fault == "clock":
        to_utc = lambda value: value - timedelta(hours=3)
    elif fault == "duplicate":
        rows = (row, dict(row))

    with pytest.raises(sut.ContractError):
        sut.validate_decoded_shard(
            sut.DecodedShard(schema, row_groups, rows), kind="H1", day="2016-01-04",
            expected_rows=len(rows), server_offset_hours=offset, server_to_utc=to_utc,
        )


def test_safe_reader_rejects_hardlinks_symlinks_and_reparse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"source")
    hardlink = tmp_path / "hardlink.bin"
    os.link(source, hardlink)
    with pytest.raises(sut.ContractError, match="alias|link|reparse"):
        sut.stable_read_regular(hardlink, tmp_path)

    symlink = tmp_path / "symlink.bin"
    try:
        symlink.symlink_to(source)
    except OSError:
        symlink = None
    if symlink is not None:
        with pytest.raises(sut.ContractError, match="alias|link|reparse"):
            sut.stable_read_regular(symlink, tmp_path)

    ordinary = tmp_path / "ordinary.bin"
    ordinary.write_bytes(b"ordinary")
    original = sut._is_reparse
    monkeypatch.setattr(sut, "_is_reparse", lambda info: True if info.st_ino == ordinary.stat().st_ino else original(info))
    with pytest.raises(sut.ContractError, match="alias|link|reparse"):
        sut.stable_read_regular(ordinary, tmp_path)


def registry_fixture(
    *,
    hypothesis_id: str | None = None,
    with_noncanonical_history: bool = False,
) -> tuple[bytes, str, bytes, bytes]:
    builder = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None\n"
    tests = b"synthetic reviewed tests\n"
    validation = {
        "source_feasibility_only": True,
        "source_run_authorized": True,
        "source_feasibility_attempt_limit": 1,
        "source_feasibility_attempt_id": sut.ATTEMPT_ID,
        "source_feasibility_evidence_root": sut.EVIDENCE_ROOT_REL,
        "probe_status": sut.PROBE_STATUS,
        "independent_implementation_review_status": "PASS",
        "independent_pre_run_review_status": "PASS",
        "independent_quant_prereg_review_status": "PASS",
        "reviewed_builder_path": sut.BUILDER_REL,
        "reviewed_builder_base_sha256": sut.reviewed_base_source_sha256(builder),
        "reviewed_test_path": sut.TEST_REL,
        "reviewed_test_sha256": sha(tests),
        "independent_review_receipt_path": sut.REVIEW_RECEIPT_REL,
        "independent_review_receipt_schema": sut.REVIEW_RECEIPT_SCHEMA,
        "independent_review_receipt_sha256": "A" * 64,
        "clock_path": sut.CLOCK_REL,
        "clock_sha256": sut.CLOCK_SHA256,
        "design_m1_manifest_path": sut.M1_MANIFEST_REL,
        "design_m1_manifest_sha256": sut.M1_MANIFEST_SHA256,
        "design_m1_receipt_path": sut.M1_RECEIPT_REL,
        "design_m1_receipt_sha256": sut.M1_RECEIPT_SHA256,
        "design_m1_source_sha256": sut.M1_SOURCE_SHA256,
        "design_h1_manifest_path": sut.H1_MANIFEST_REL,
        "design_h1_manifest_sha256": sut.H1_MANIFEST_SHA256,
        "design_h1_receipt_path": sut.H1_RECEIPT_REL,
        "design_h1_receipt_sha256": sut.H1_RECEIPT_SHA256,
        "design_h1_price_side": "BID",
        "registry_validator_path": sut.REGISTRY_VALIDATOR_REL,
        "registry_validator_sha256": sut.REGISTRY_VALIDATOR_SHA256,
        "registry_schema_path": sut.REGISTRY_SCHEMA_REL,
        "registry_schema_sha256": sut.REGISTRY_SCHEMA_SHA256,
    }
    validation.update({field: False for field in sut.SEALED_FALSE_FIELDS})
    row = {
        "record_type": "hypothesis_state",
        "schema_version": "alphafactory_candidate_registry.v1",
        "hypothesis_id": hypothesis_id or sut.HYPOTHESIS_ID,
        "ea_name": sut.EA_NAME,
        "state": "probe",
        "parent_candidate": sut.PARENT_HYPOTHESIS_ID,
        "feature_family": sut.FAMILY,
        "lane": "source-feasibility",
        "symbol": "EURUSD",
        "timeframe": "M15",
        "window": {"from": "2016.01.04", "to": "2020.12.31"},
        "model": None,
        "source_provenance": "FivePercent public DESIGN M1 and H1 BID",
        "source_path": None,
        "source_hash": None,
        "prereg_path": sut.PLAN_REL,
        "prereg_sha256": sut.PLAN_SHA256,
        "exact_overrides": "Source feasibility only; no economics",
        "acceptance_contract": {
            "min_profit_factor": 1.3,
            "min_trades_per_week": 2.0,
            "max_trades_per_week": 5.0,
            "max_drawdown_pct": 8.0,
            "min_cost_pf_x1_5": 1.25,
            "min_cost_pf_x2": 1.0,
            "max_monte_carlo_p95_dd_pct": 8.0,
        },
        "verdict": "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "reason": "Fresh child repairs pre-run registry authority only",
        "updated_at_utc": "2026-07-29T00:00:00Z",
        "run_ids": [],
        "metrics": dict(sut.SOURCE_ONLY_ZERO_METRICS),
        "validation": validation,
    }
    selected = canonical(row) + b"\n"
    history = b'{ "hypothesis_id": "HYP-HISTORY-001" }\n' if with_noncanonical_history else b""
    return history + selected, sha(selected), builder, tests


def fake_registry_validator(errors: list[str] | None = None) -> bytes:
    result = [] if errors is None else errors
    return (
        "def validate_registry(registry, schema_path):\n"
        "    if not registry.is_file() or not schema_path.is_file():\n"
        "        return ['immutable adapter missing']\n"
        "    if not registry.read_bytes().endswith(b'\\n'):\n"
        "        return ['registry bytes unavailable']\n"
        "    if not schema_path.read_text(encoding='utf-8-sig'):\n"
        "        return ['schema bytes unavailable']\n"
        f"    return {result!r}\n"
    ).encode("utf-8")


def test_registry_exact_validation_whitelist_is_accepted() -> None:
    registry, reviewed_sha, builder, tests = registry_fixture()

    parsed = sut.validate_registry_authority(
        registry,
        reviewed_sha,
        builder_payload=builder,
        test_payload=tests,
    )

    assert parsed == json.loads(registry)


@pytest.mark.parametrize("alias", [0, "false", None])
def test_registry_false_authorities_reject_false_aliases(alias: object) -> None:
    registry, _, builder, tests = registry_fixture()
    row = json.loads(registry)
    row["validation"]["economics_authorized"] = alias
    mutated = canonical(row) + b"\n"
    with pytest.raises(sut.ContractError, match="authority|sealed"):
        sut.validate_registry_authority(
            mutated, sha(mutated), builder_payload=builder, test_payload=tests
        )


def test_registry_true_authority_rejects_numeric_alias() -> None:
    registry, _, builder, tests = registry_fixture()
    row = json.loads(registry)
    row["validation"]["source_run_authorized"] = 1
    mutated = canonical(row) + b"\n"
    with pytest.raises(sut.ContractError, match="authority"):
        sut.validate_registry_authority(
            mutated, sha(mutated), builder_payload=builder, test_payload=tests
        )


@pytest.mark.parametrize(
    "key,value",
    [
        ("shadow_access_authorized", True),
        ("validation_authorized", True),
        ("holdout_access_authorized", "true"),
        ("economic_permission", False),
        ("source_build_allowed", 0),
    ],
)
def test_unknown_authority_like_validation_keys_are_rejected(key: str, value: object) -> None:
    registry, _, builder, tests = registry_fixture()
    row = json.loads(registry)
    row["validation"][key] = value
    mutated = canonical(row) + b"\n"
    with pytest.raises(sut.ContractError, match="authority|validation key"):
        sut.validate_registry_authority(
            mutated, sha(mutated), builder_payload=builder, test_payload=tests
        )


@pytest.mark.parametrize(
    "key,value",
    [
        ("mt5", "true"),
        ("model0", 1),
        ("paid", "true"),
        ("live", "true"),
        ("outcome", "true"),
        ("post_entry_ohlc", "true"),
        ("validation", "true"),
        ("holdout", 1),
        ("private", "true"),
        ("sealed", "true"),
        ("promotion", "true"),
        ("note", False),
    ],
)
def test_registry_validation_rejects_every_extra_key(key: str, value: object) -> None:
    registry, _, builder, tests = registry_fixture()
    row = json.loads(registry)
    row["validation"][key] = value
    mutated = canonical(row) + b"\n"

    with pytest.raises(sut.ContractError, match="validation key|whitelist"):
        sut.validate_registry_authority(
            mutated, sha(mutated), builder_payload=builder, test_payload=tests
        )


def test_registry_noncanonical_history_passes_only_with_clean_canonical_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry, reviewed_sha, builder, tests = registry_fixture(with_noncanonical_history=True)
    validator = fake_registry_validator()
    schema = b'{"type":"object"}\n'
    with monkeypatch.context() as scoped:
        scoped.setattr(sut, "REGISTRY_VALIDATOR_SHA256", sha(validator))
        scoped.setattr(sut, "REGISTRY_SCHEMA_SHA256", sha(schema))
        sut.validate_registry_snapshot(
            registry_payload=registry,
            validator_payload=validator,
            schema_payload=schema,
            validator_path=Path("validate_candidate_registry.py"),
        )
    parsed = sut.validate_registry_authority(
        registry, reviewed_sha, builder_payload=builder, test_payload=tests
    )

    assert parsed["hypothesis_id"] == sut.HYPOTHESIS_ID


@pytest.mark.parametrize(
    "bad_history",
    [
        b'{"x":1,"x":2}\n',
        b'{"x":}\n',
        b'{"x":NaN}\n',
        b"\n",
    ],
)
def test_registry_parser_rejects_duplicate_malformed_nonfinite_and_blank_rows(
    bad_history: bytes,
) -> None:
    registry, _, _, _ = registry_fixture()
    with pytest.raises(sut.ContractError, match="registry|strict|duplicate|blank"):
        sut.parse_registry_jsonl(bad_history + registry)


def test_registry_selected_raw_line_hash_drift_fails() -> None:
    registry, reviewed_sha, builder, tests = registry_fixture(with_noncanonical_history=True)
    lines = registry.splitlines(keepends=True)
    lines[-1] = lines[-1][:-1] + b" \n"

    with pytest.raises(sut.ContractError, match="registry|binding|canonical"):
        sut.validate_registry_authority(
            b"".join(lines), reviewed_sha, builder_payload=builder, test_payload=tests
        )


@pytest.mark.parametrize("case", ["wrong_sha", "nonlatest"])
def test_wrong_or_nonlatest_registry_row_sha_cannot_arm_source(case: str) -> None:
    registry, reviewed_sha, builder, tests = registry_fixture()
    if case == "wrong_sha":
        reviewed_sha = "F" * 64
    else:
        successor = json.loads(registry)
        successor["updated_at_utc"] = "2026-07-29T00:00:01Z"
        registry += canonical(successor) + b"\n"

    with pytest.raises(sut.ContractError, match="registry|latest|authority"):
        sut.validate_registry_authority(
            registry, reviewed_sha, builder_payload=builder, test_payload=tests
        )


@pytest.mark.parametrize(
    "mutation",
    ["bool_alias", "missing", "extra"],
)
def test_registry_zero_runtime_metrics_are_exact(mutation: str) -> None:
    registry, _, builder, tests = registry_fixture()
    row = json.loads(registry)
    if mutation == "bool_alias":
        row["metrics"]["source_runs_executed"] = False
    elif mutation == "missing":
        del row["metrics"]["outcome_fields_emitted"]
    else:
        row["metrics"]["innocuous"] = 0
    mutated = canonical(row) + b"\n"

    with pytest.raises(sut.ContractError, match="zero metrics|authority"):
        sut.validate_registry_authority(
            mutated, sha(mutated), builder_payload=builder, test_payload=tests
        )


@pytest.mark.parametrize("case", ["row", "source"])
def test_parent_001_row_or_source_cannot_authorize_child_002(case: str) -> None:
    registry, reviewed_sha, builder, tests = registry_fixture(
        hypothesis_id="HYP-ARUC-EURUSD-M15-001" if case == "row" else None
    )
    if case == "source":
        builder = (
            b"# HYP-ARUC-EURUSD-M15-001\n"
            b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None\n"
        )

    with pytest.raises(sut.ContractError, match="registry|authority"):
        sut.validate_registry_authority(
            registry, reviewed_sha, builder_payload=builder, test_payload=tests
        )


@pytest.mark.parametrize("drift", ["validator", "schema"])
def test_registry_snapshot_validator_or_schema_hash_drift_fails(
    drift: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry, _, _, _ = registry_fixture(with_noncanonical_history=True)
    validator = fake_registry_validator()
    schema = b'{"type":"object"}\n'
    monkeypatch.setattr(sut, "REGISTRY_VALIDATOR_SHA256", sha(validator))
    monkeypatch.setattr(sut, "REGISTRY_SCHEMA_SHA256", sha(schema))
    if drift == "validator":
        validator += b"# drift\n"
    else:
        schema += b" \n"

    with pytest.raises(sut.ContractError, match="validator|schema|SHA"):
        sut.validate_registry_snapshot(
            registry_payload=registry,
            validator_payload=validator,
            schema_payload=schema,
            validator_path=Path("validate_candidate_registry.py"),
        )


def test_registry_snapshot_validator_errors_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    registry, _, _, _ = registry_fixture(with_noncanonical_history=True)
    validator = fake_registry_validator(["synthetic canonical validator error"])
    schema = b'{"type":"object"}\n'
    monkeypatch.setattr(sut, "REGISTRY_VALIDATOR_SHA256", sha(validator))
    monkeypatch.setattr(sut, "REGISTRY_SCHEMA_SHA256", sha(schema))

    with pytest.raises(sut.ContractError, match="canonical registry validator"):
        sut.validate_registry_snapshot(
            registry_payload=registry,
            validator_payload=validator,
            schema_payload=schema,
            validator_path=Path("validate_candidate_registry.py"),
        )


def test_all_three_arm_ledgers_are_stable_and_timestamp_only() -> None:
    first = utc(2020, 1, 6, 7, 0)
    second = utc(2020, 1, 7, 8, 0)
    primary = [
        {
            "time_utc": second, "availability_utc": second + timedelta(minutes=15),
            "direction": "SHORT", "year": 2020, "a": 1.7, "q": -60,
            "sum_tv": 100, "r": -0.2, "atr20": 0.001,
            "cost_to_sl_ratio": 0.15,
        },
        {
            "time_utc": first, "availability_utc": first + timedelta(minutes=15),
            "direction": "LONG", "year": 2020, "a": 1.6, "q": 55,
            "sum_tv": 100, "r": 0.2, "atr20": 0.001,
            "cost_to_sl_ratio": 0.15,
        },
    ]
    price_only = [{
        "time_utc": first, "availability_utc": first + timedelta(minutes=15),
        "direction": "LONG", "year": 2020, "r": 0.2, "atr20": 0.001,
        "cost_to_sl_ratio": 0.15,
    }]
    shifted = [{
        "time_utc": second, "availability_utc": second + timedelta(minutes=15),
        "direction": "SHORT", "year": 2020, "shifted_a": 1.8,
        "shifted_q": -70, "shifted_sum_tv": 100, "r": -0.2,
        "shifted_source_date": date(2019, 12, 31),
        "atr20": 0.001, "cost_to_sl_ratio": 0.15,
    }]
    observed = []
    for at in (first, second):
        availability = at + timedelta(minutes=15)
        observed.extend(availability + timedelta(minutes=15 * index) for index in range(4))
    observed.sort()

    ledgers_a = sut.build_arm_ledgers(
        {"PRIMARY": primary, "PRICE_ONLY": price_only, "SHIFTED_TICKS": shifted},
        observed,
    )
    ledgers_b = sut.build_arm_ledgers(
        {"SHIFTED_TICKS": list(reversed(shifted)), "PRICE_ONLY": price_only, "PRIMARY": list(reversed(primary))},
        observed,
    )

    assert canonical(ledgers_a) == canonical(ledgers_b)
    assert tuple(ledgers_a) == ("PRIMARY", "PRICE_ONLY", "SHIFTED_TICKS")
    assert [row["decision_utc"] for row in ledgers_a["PRIMARY"]] == sorted(
        row["decision_utc"] for row in ledgers_a["PRIMARY"]
    )
    assert len({row["signal_id"] for rows in ledgers_a.values() for row in rows}) == 4
    assert set(ledgers_a["PRIMARY"][0]["causal_features"]) == {"a", "q", "sum_tv", "r", "atr20", "cost_to_sl_ratio"}
    assert set(ledgers_a["PRICE_ONLY"][0]["causal_features"]) == {"r", "atr20", "cost_to_sl_ratio"}
    assert set(ledgers_a["SHIFTED_TICKS"][0]["causal_features"]) == {
        "shifted_a", "shifted_q", "shifted_sum_tv", "shifted_source_date",
        "r", "atr20", "cost_to_sl_ratio",
    }
    assert all(row["horizon"]["reason"] == "SOURCE_EXECUTABLE" for rows in ledgers_a.values() for row in rows)
    sut.assert_outcome_blind(ledgers_a)

    def assert_no_prices(value: object) -> None:
        if isinstance(value, dict):
            assert not ({"open", "high", "low", "close"} & set(value))
            for child in value.values():
                assert_no_prices(child)
        elif isinstance(value, list):
            for child in value:
                assert_no_prices(child)

    assert_no_prices(ledgers_a)


def test_default_disarm_blocks_before_any_real_source_access(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("real source access attempted")

    monkeypatch.setattr(sut, "stable_read_regular", forbidden)
    with pytest.raises(sut.ContractError, match="disarmed|run switch|registry"):
        sut.execute_probe(workspace_root=tmp_path, run_switch=False)
    assert calls == []


def test_registry_row_sentinel_is_exactly_disarmed() -> None:
    assert sut.REVIEWED_REGISTRY_ROW_SHA256 is None


def test_outcome_fields_are_rejected() -> None:
    for key in ("return", "pnl", "profit_factor", "dsr", "post_entry_open", "trade_count"):
        with pytest.raises(sut.ContractError, match="outcome|forbidden"):
            sut.assert_outcome_blind({key: 1})
