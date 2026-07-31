from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


RESEARCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH_DIR))

import build_round_cascade_002_source as sut


UTC = timezone.utc


def m1(at: datetime, *, close: float = 1.1000, high: float | None = None, low: float | None = None) -> dict:
    return {
        "time_utc": at,
        "open": close,
        "high": close if high is None else high,
        "low": close if low is None else low,
        "close": close,
    }


def minute_block(start: datetime, count: int, *, close: float = 1.1000) -> list[dict]:
    return [m1(start + timedelta(minutes=i), close=close) for i in range(count)]


def reviewed_authority_material() -> tuple[dict, bytes, bytes, bytes, bytes]:
    builder_payload = Path(sut.__file__).read_bytes()
    test_payload = Path(__file__).read_bytes()
    builder_base_sha = sut.reviewed_base_source_sha256(builder_payload)
    test_sha = sut.sha256_bytes(test_payload)
    review = {
        "schema_version": sut.INDEPENDENT_REVIEW_SCHEMA,
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "review_status": "PASS",
        "reviewed_builder": {"path": sut.BUILDER_REL, "base_sha256": builder_base_sha},
        "reviewed_tests": {"path": sut.TEST_REL, "sha256": test_sha},
        "v1_plan": {"path": sut.PLAN_REL, "sha256": sut.FROZEN_PLAN_SHA256},
        "permissions": {
            "source_feasibility_run": True,
            "performance_or_economics": False,
            "mt5_or_mql5": False,
        },
    }
    review_payload = sut.canonical_json_bytes(review)
    validation = {
        "source_build_authorized": False,
        "source_run_authorized": True,
        "source_feasibility_only": True,
        "source_feasibility_attempt_limit": 1,
        "design_manifest_sha256": sut.DESIGN_MANIFEST_SHA256,
        "design_receipt_sha256": sut.DESIGN_RECEIPT_SHA256,
        "public_m1_source_sha256": sut.PUBLIC_M1_SOURCE_SHA256,
        "source_feasibility_attempt_id": sut.ATTEMPT_ID,
        "source_feasibility_evidence_root": sut.EVIDENCE_ROOT_REL,
        "reviewed_builder_path": sut.BUILDER_REL,
        "reviewed_builder_base_sha256": builder_base_sha,
        "reviewed_test_path": sut.TEST_REL,
        "reviewed_test_sha256": test_sha,
        "independent_review_receipt_path": sut.INDEPENDENT_REVIEW_RECEIPT_REL,
        "independent_review_receipt_sha256": sut.sha256_bytes(review_payload),
    }
    validation.update({field: False for field in sut.SEALED_FALSE_FIELDS})
    row = {
        "record_type": "hypothesis_state",
        "schema_version": "alphafactory_candidate_registry.v1",
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "ea_name": sut.PACKAGE_NAME,
        "state": "probe",
        "model": None,
        "source_path": None,
        "source_hash": None,
        "prereg_path": sut.PLAN_REL,
        "prereg_sha256": sut.FROZEN_PLAN_SHA256,
        "run_ids": [],
        "validation": validation,
    }
    row_payload = sut.canonical_json_bytes(row)
    return row, row_payload, builder_payload, test_payload, review_payload


@pytest.mark.parametrize("current", [1.1001, 1.1010])
def test_true_lattice_long_boundaries_are_inclusive(current: float) -> None:
    hit = sut.classify_lattice_cross(1.0999, current, arm="TRUE_0050")
    assert hit == {"direction": "LONG", "level_pips": 11000}


@pytest.mark.parametrize("previous,current", [(1.1000, 1.1001), (1.0999, 1.1000), (1.0999, 1.1011)])
def test_true_lattice_rejects_non_cross_and_outside_long_band(previous: float, current: float) -> None:
    assert sut.classify_lattice_cross(previous, current, arm="TRUE_0050") is None


@pytest.mark.parametrize(
    "current,expected",
    [(1.10009, None), (1.10010, "LONG"), (1.10100, "LONG"), (1.10101, None)],
)
def test_fractional_pip_quotes_do_not_round_across_frozen_boundaries(current: float, expected: str | None) -> None:
    hit = sut.classify_lattice_cross(1.09999, current, arm="TRUE_0050")
    assert (hit or {}).get("direction") == expected


def test_sub_quote_point_price_is_rejected_instead_of_rounded_into_long() -> None:
    with pytest.raises(sut.ContractError, match="quote-point grid"):
        sut.classify_lattice_cross(1.09999, 1.100095, arm="TRUE_0050")


def test_binary_float_noise_on_legal_five_digit_quote_is_normalized() -> None:
    assert sut.price_to_points(1.0818699999999999) == 108187
    assert sut.price_to_points(1.0818700000000001) == 108187
    with pytest.raises(sut.ContractError, match="quote-point grid"):
        sut.price_to_points(1.081875)


@pytest.mark.parametrize("current", [1.0990, 1.0999])
def test_true_lattice_short_is_exact_mirror(current: float) -> None:
    hit = sut.classify_lattice_cross(1.1001, current, arm="TRUE_0050")
    assert hit == {"direction": "SHORT", "level_pips": 11000}


def test_shifted_placebo_uses_25_plus_50_pip_lattice() -> None:
    assert sut.classify_lattice_cross(1.1024, 1.1026, arm="SHIFTED_0025") == {
        "direction": "LONG",
        "level_pips": 11025,
    }
    assert sut.classify_lattice_cross(1.1026, 1.1024, arm="SHIFTED_0025") == {
        "direction": "SHORT",
        "level_pips": 11025,
    }
    assert sut.classify_lattice_cross(1.0999, 1.1001, arm="SHIFTED_0025") is None


def test_m5_aggregation_requires_exact_utc_offsets_zero_through_four() -> None:
    start = datetime(2019, 1, 2, 10, 0, tzinfo=UTC)
    complete, quality = sut.aggregate_complete_m5(minute_block(start, 5))
    assert len(complete) == 1
    assert complete[0]["time_utc"] == start
    assert quality == {"observed_bins": 1, "complete_bins": 1, "incomplete_bins": 0}

    missing = minute_block(start, 5)
    del missing[2]
    complete, quality = sut.aggregate_complete_m5(missing)
    assert complete == []
    assert quality["incomplete_bins"] == 1


def test_scanner_requires_previous_and_current_m5_exactly_five_minutes_apart() -> None:
    at = datetime(2019, 1, 2, 10, 0, tzinfo=UTC)
    bars = [
        {"time_utc": at, "close": 1.0999},
        {"time_utc": at + timedelta(minutes=10), "close": 1.1001},
    ]
    assert sut.scan_arm_signals(bars, {}, arm="TRUE_0050") == []


def _h1_bar(at: datetime, close: float, *, high: float | None = None, low: float | None = None) -> dict:
    return {
        "time_utc": at,
        "open": close,
        "high": close if high is None else high,
        "low": close if low is None else low,
        "close": close,
    }


def test_h1_atr20_uses_last_21_complete_trading_bars_across_weekend() -> None:
    friday = datetime(2019, 1, 4, 3, 0, tzinfo=UTC)
    hours = [friday + timedelta(hours=i) for i in range(21)]
    decision = datetime(2019, 1, 7, 1, 5, tzinfo=UTC)
    bars = [_h1_bar(at, 1.1000, high=1.1005, low=1.0995) for at in hours]
    assert sut.atr20_shift1(bars, decision) == pytest.approx(0.0010)


def test_h1_aggregation_requires_all_sixty_minutes_and_atr_shift1_ignores_decision_hour() -> None:
    start = datetime(2019, 1, 2, 0, 0, tzinfo=UTC)
    rows = minute_block(start, 21 * 60, close=1.1000)
    rows += minute_block(start + timedelta(hours=21), 60, close=1.5000)
    h1, quality = sut.aggregate_complete_h1(rows)
    assert quality["complete_bins"] == 22
    decision = start + timedelta(hours=21, minutes=5)
    assert sut.atr20_shift1(h1, decision) == pytest.approx(0.0)

    broken = rows[:-1]
    h1, quality = sut.aggregate_complete_h1(broken)
    assert quality["incomplete_bins"] == 1


def test_indexed_atr_lookup_matches_reference_without_per_m5_full_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    friday = datetime(2019, 1, 4, 0, 0, tzinfo=UTC)
    times = [friday + timedelta(hours=i) for i in range(18)]
    monday = datetime(2019, 1, 7, 0, 0, tzinfo=UTC)
    times += [monday + timedelta(hours=i) for i in range(12)]
    h1 = []
    for i, at in enumerate(times):
        close = 1.1000 + i * 0.0001
        h1.append(_h1_bar(at, close, high=close + 0.0004, low=close - 0.0003))
    # A very wide in-progress decision-hour bar must be excluded at shift 1.
    h1[-1] = _h1_bar(times[-1], 1.4000, high=1.9000, low=0.9000)
    decisions = [
        {"time_utc": monday + timedelta(hours=hour, minutes=5), "close": 1.1000}
        for hour in (4, 7, 10, 11)
    ]
    reference = {
        row["time_utc"]: sut.atr20_shift1(h1, row["time_utc"])
        for row in decisions
        if sut.atr20_shift1(h1, row["time_utc"]) is not None
    }

    def forbidden_full_scan(*_args, **_kwargs):
        raise AssertionError("build_atr_lookup must not call the per-decision full scanner")

    monkeypatch.setattr(sut, "atr20_shift1", forbidden_full_scan)
    actual = sut.build_atr_lookup(decisions, h1)
    assert actual == pytest.approx(reference)


def test_first_eligible_per_utc_date_is_independent_per_arm() -> None:
    day = datetime(2019, 1, 2, 10, 0, tzinfo=UTC)
    bars = [
        {"time_utc": day, "close": 1.0999},
        {"time_utc": day + timedelta(minutes=5), "close": 1.1001},
        {"time_utc": day + timedelta(minutes=10), "close": 1.1024},
        {"time_utc": day + timedelta(minutes=15), "close": 1.1026},
        {"time_utc": day + timedelta(minutes=20), "close": 1.1049},
        {"time_utc": day + timedelta(minutes=25), "close": 1.1051},
    ]
    atr = {bar["time_utc"]: 0.0010 for bar in bars}
    true_signals = sut.scan_arm_signals(bars, atr, arm="TRUE_0050")
    shifted_signals = sut.scan_arm_signals(bars, atr, arm="SHIFTED_0025")
    assert len(true_signals) == 1
    assert true_signals[0]["decision_bar_start_utc"] == "2019-01-02T10:05:00Z"
    assert true_signals[0]["decision_time_utc"] == "2019-01-02T10:10:00Z"
    assert true_signals[0]["planned_entry_time_utc"] == "2019-01-02T10:10:00Z"
    assert len(shifted_signals) == 1
    assert shifted_signals[0]["decision_time_utc"] == "2019-01-02T10:20:00Z"


def test_2355_bar_is_throttled_on_next_utc_availability_date() -> None:
    at = datetime(2019, 1, 2, 23, 50, tzinfo=UTC)
    bars = [
        {"time_utc": at, "close": 1.0999},
        {"time_utc": at + timedelta(minutes=5), "close": 1.1001},
        {"time_utc": at + timedelta(minutes=10), "close": 1.0999},
        {"time_utc": at + timedelta(minutes=15), "close": 1.1001},
    ]
    atr = {bar["time_utc"]: 0.0010 for bar in bars}
    signals = sut.scan_arm_signals(bars, atr, arm="TRUE_0050")
    assert len(signals) == 1
    assert signals[0]["decision_bar_start_utc"] == "2019-01-02T23:55:00Z"
    assert signals[0]["decision_time_utc"] == "2019-01-03T00:00:00Z"


def _gate_signals(count: int, years: list[int] | None = None) -> list[dict]:
    years = years or [2016, 2017, 2018, 2019, 2020]
    out: list[dict] = []
    for i in range(count):
        year = years[i % len(years)]
        out.append(
            {
                "direction": "LONG" if i % 2 == 0 else "SHORT",
                "decision_time_utc": f"{year}-01-02T10:05:00Z",
                "atr20_pips": 10.0,
                "cost_to_stop_ratio_1p5": 0.15,
            }
        )
    return out


def test_stage0_gates_enforce_cadence_quality_balance_year_and_geometry_bounds() -> None:
    arms = {"TRUE_0050": _gate_signals(522), "SHIFTED_0025": _gate_signals(1302)}
    report = sut.evaluate_source_gates(
        arms,
        m5_complete_ratio=0.99,
        signal_atr_complete_ratio={"TRUE_0050": 1.0, "SHIFTED_0025": 0.99},
    )
    assert report["verdict"] == "PASS_SOURCE_FEASIBILITY"
    assert all(gate["passed"] for gate in report["gates"])
    assert all(not gate["name"].endswith("_count") for gate in report["gates"])

    report = sut.evaluate_source_gates(
        {"TRUE_0050": _gate_signals(521), "SHIFTED_0025": _gate_signals(1303)},
        m5_complete_ratio=0.989,
        signal_atr_complete_ratio={"TRUE_0050": 0.989, "SHIFTED_0025": 1.0},
    )
    assert report["verdict"] == "PARK_SOURCE_FEASIBILITY_FAILED"


def test_zero_signal_source_failure_is_strict_json_not_infinity() -> None:
    report = sut.evaluate_source_gates(
        {"TRUE_0050": [], "SHIFTED_0025": []},
        m5_complete_ratio=1.0,
        signal_atr_complete_ratio={"TRUE_0050": 0.0, "SHIFTED_0025": 0.0},
    )
    assert report["verdict"] == "PARK_SOURCE_FEASIBILITY_FAILED"
    assert report["arm_metrics"]["TRUE_0050"]["median_cost_to_stop_ratio_1p5"] is None
    assert b"Infinity" not in sut.canonical_json_bytes(report)


def test_forbidden_outcome_surface_is_rejected() -> None:
    sut.assert_outcome_blind([{"decision_time_utc": "2019-01-01T00:00:00Z", "atr20_pips": 10.0}])
    for key in ("next_open", "future_close", "return", "pnl", "trade", "profit_factor"):
        with pytest.raises(sut.ContractError, match="forbidden outcome"):
            sut.assert_outcome_blind([{key: 0}])


def test_reviewed_registry_placeholder_and_explicit_run_switch_fail_closed() -> None:
    assert sut.REVIEWED_REGISTRY_ROW_SHA256 is None or len(sut.REVIEWED_REGISTRY_ROW_SHA256) == 64
    with pytest.raises(sut.ContractError, match="reviewed registry"):
        sut.guard_production_run(
            run_switch=True,
            reviewed_registry_sha256=sut.REVIEWED_REGISTRY_ROW_SHA256,
            registry_payload=b"{}\n",
        )
    with pytest.raises(sut.ContractError, match="explicit run switch"):
        sut.guard_production_run(run_switch=False, reviewed_registry_sha256="A" * 64, registry_payload=b"{}\n")


def test_exact_reviewed_registry_row_must_bind_plan_and_keep_economics_sealed() -> None:
    row, payload, builder, tests, review = reviewed_authority_material()
    reviewed = sut.sha256_bytes(payload)
    assert sut.guard_production_run(
        run_switch=True,
        reviewed_registry_sha256=reviewed,
        registry_payload=payload,
        builder_payload=builder,
        test_payload=tests,
        review_receipt_payload=review,
    ) == row
    row["validation"]["mt5_authorized"] = True
    payload = sut.canonical_json_bytes(row)
    with pytest.raises(sut.ContractError, match="runtime/private access sealed"):
        sut.guard_production_run(
            run_switch=True,
            reviewed_registry_sha256=sut.sha256_bytes(payload),
            registry_payload=payload,
        )


def test_create_new_terminal_guard_refuses_existing_artifact(tmp_path: Path) -> None:
    target = tmp_path / "terminal.json"
    sut.write_new_json(target, {"verdict": "PARK_SOURCE_FEASIBILITY_FAILED"}, exact_root=tmp_path)
    with pytest.raises(sut.ContractError, match="already exists"):
        sut.write_new_json(target, {"verdict": "PASS_SOURCE_FEASIBILITY"}, exact_root=tmp_path)


def test_path_containment_and_hash_verification_are_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    source = root / "authority.json"
    source.write_bytes(b"{}\n")
    expected = hashlib.sha256(b"{}\n").hexdigest().upper()
    assert sut.read_verified_bytes_once(source, expected, exact_root=root) == b"{}\n"
    with pytest.raises(sut.ContractError, match="SHA256 mismatch"):
        sut.read_verified_bytes_once(source, "0" * 64, exact_root=root)
    with pytest.raises(sut.ContractError, match="outside exact root"):
        sut.read_verified_bytes_once(tmp_path / "elsewhere", expected, exact_root=root)


def test_import_is_inert(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["build_round_cascade_002_source.py", "--run-reviewed-stage0"])
    spec = importlib.util.spec_from_file_location("round_cascade_inert_copy", RESEARCH_DIR / "build_round_cascade_002_source.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.REVIEWED_REGISTRY_ROW_SHA256 is None or len(module.REVIEWED_REGISTRY_ROW_SHA256) == 64


def test_reviewed_base_hash_normalizes_only_the_sentinel() -> None:
    payload = Path(sut.__file__).read_bytes()
    base = sut.reviewed_base_source_sha256(payload)
    armed = payload.replace(
        b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None",
        b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"',
        1,
    )
    assert armed != payload
    assert sut.reviewed_base_source_sha256(armed) == base
    with pytest.raises(sut.ContractError, match="exactly one"):
        sut.reviewed_base_source_sha256(payload + b"\nREVIEWED_REGISTRY_ROW_SHA256: str | None = None\n")


def test_attempt_failure_writes_terminal_and_refuses_rerun(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence" / "attempt"
    started = {"hypothesis_id": sut.HYPOTHESIS_ID, "attempt_id": sut.ATTEMPT_ID, "state": "STARTED"}

    def fail(root: Path, started_sha: str) -> dict:
        assert (root / "attempt_started.json").is_file()
        assert len(started_sha) == 64
        raise sut.ContractError("synthetic source failure")

    with pytest.raises(sut.ContractError, match="synthetic source failure"):
        sut.execute_with_terminal_guard(
            evidence, workspace_root=tmp_path, started_payload=started, work=fail
        )
    terminal = json.loads((evidence / "attempt_terminal.json").read_text(encoding="utf-8"))
    assert terminal["state"] == "FAILED"
    assert terminal["verdict"] == "ENGINEERING_ABORTED_NO_ECONOMIC_VERDICT"
    with pytest.raises(sut.ContractError, match="already exists"):
        sut.execute_with_terminal_guard(
            evidence, workspace_root=tmp_path, started_payload=started, work=fail
        )


def test_success_artifacts_are_create_new_and_hash_chained(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence" / "attempt"
    started = {"hypothesis_id": sut.HYPOTHESIS_ID, "attempt_id": sut.ATTEMPT_ID, "state": "STARTED"}
    signals = {
        arm: [
            {
                "hypothesis_id": sut.HYPOTHESIS_ID,
                "arm": arm,
                "direction": "LONG",
                "decision_bar_start_utc": "2019-01-02T10:00:00Z",
                "decision_time_utc": "2019-01-02T10:05:00Z",
                "planned_entry_time_utc": "2019-01-02T10:05:00Z",
                "atr20_pips": 10.0,
                "cost_to_stop_ratio_1p5": 0.15,
            }
        ]
        for arm in sut.ARMS
    }
    report = {
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "verdict": "PASS_SOURCE_FEASIBILITY",
        "zero_counters": {
            "post_decision_ohlc_rows_read": 0,
            "outcome_fields_emitted": 0,
            "performance_trials_executed": 0,
            "economic_simulation_executed": False,
            "mt5_launches": 0,
            "mql5_files_created": 0,
            "research_validation_opened": False,
            "research_holdout_opened": False,
            "network_calls": 0,
        },
    }

    def succeed(root: Path, started_sha: str) -> dict:
        return sut.write_success_artifacts(
            root,
            report=report,
            signals_by_arm=signals,
            attempt_started_sha256=started_sha,
            registry_row_sha256="B" * 64,
            review_binding={"builder_base_sha256": "C" * 64},
        )

    result = sut.execute_with_terminal_guard(
        evidence, workspace_root=tmp_path, started_payload=started, work=succeed
    )
    assert set(path.name for path in evidence.iterdir()) == {
        "attempt_started.json",
        "round_cascade_source_report.json",
        "round_cascade_source_ledger.jsonl",
        "source_feasibility_receipt.json",
        "attempt_terminal.json",
    }
    for name, expected in result["artifact_hashes"].items():
        assert hashlib.sha256((evidence / name).read_bytes()).hexdigest().upper() == expected
    terminal = json.loads((evidence / "attempt_terminal.json").read_text(encoding="utf-8"))
    receipt = json.loads((evidence / "source_feasibility_receipt.json").read_text(encoding="utf-8"))
    assert terminal["source_feasibility_receipt_sha256"] == result["artifact_hashes"]["source_feasibility_receipt.json"]
    assert receipt["artifacts"]["attempt_started.json"] == result["artifact_hashes"]["attempt_started.json"]
