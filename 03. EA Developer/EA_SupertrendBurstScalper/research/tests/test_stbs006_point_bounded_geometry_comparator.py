from __future__ import annotations

import hashlib
import importlib.util
import math
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WRAPPER_PATH = RESEARCH / "compare_stbs006_point_bounded_geometry.py"
BASE_PATH = RESEARCH / "compare_stbs005_exact_orders_heading.py"


def load_module():
    spec = importlib.util.spec_from_file_location("stbs006_wrapper_test", WRAPPER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_fresh_identity_and_single_capture_base() -> None:
    wrapper = load_module()
    text = WRAPPER_PATH.read_text(encoding="utf-8")
    assert wrapper.HYPOTHESIS_ID == "HYP-STBS-XAUUSD-M15-006"
    assert wrapper.ATTEMPT_ID == "STBS006-COMPARATOR-001"
    assert wrapper.HYP005_TERMINAL_ROW_SHA256 == "179BD0163632218A026E433FC68E416CF49EEE9BE8613593A1AF40ABA6261942"
    assert wrapper.BASE_SHA256 == file_sha(BASE_PATH)
    assert text.count("BASE_PATH.read_bytes()") == 1
    assert "compile(BASE_RAW" in text
    assert 'captured["hyp005_comparator"] = BASE_RAW' in text


def test_consumed_event10_passes_observable_contract() -> None:
    wrapper = load_module()
    checks = wrapper.point_bounded_geometry_contract_checks(
        "SHORT", 2.04, 1337.68, 1339.73, 1334.60
    )
    assert all(checks.values())


def test_both_directions_pass() -> None:
    wrapper = load_module()
    assert all(wrapper.point_bounded_geometry_contract_checks("SHORT", 2.00, 100.00, 102.01, 96.98).values())
    assert all(wrapper.point_bounded_geometry_contract_checks("LONG", 2.00, 100.00, 97.99, 103.02).values())


def test_alignment_sidedness_and_nonfinite_fail() -> None:
    wrapper = load_module()
    assert not wrapper.point_bounded_geometry_contract_checks("LONG", 2.0, 100.005, 98.00, 103.00)["point_aligned"]
    assert not wrapper.point_bounded_geometry_contract_checks("LONG", 2.0, 100.00, 101.00, 103.00)["sided"]
    assert not wrapper.point_bounded_geometry_contract_checks("SHORT", 2.0, 100.00, 98.00, 103.00)["sided"]
    for bad in (math.nan, math.inf, -math.inf):
        assert not all(wrapper.point_bounded_geometry_contract_checks("LONG", bad, 100.0, 98.0, 103.0).values())


def test_stop_interval_lower_and_upper_violations_fail() -> None:
    wrapper = load_module()
    tol = wrapper.TOL
    lower = wrapper.point_bounded_geometry_contract_checks("SHORT", 2.0, 100.0, 102.0 - 2 * tol, 97.0)
    upper = wrapper.point_bounded_geometry_contract_checks("SHORT", 2.0, 100.0, 102.01 + 2 * tol, 96.98)
    assert not lower["stop_interval"]
    assert not upper["stop_interval"]


def test_target_interval_lower_and_upper_violations_fail() -> None:
    wrapper = load_module()
    tol = wrapper.TOL
    lower = wrapper.point_bounded_geometry_contract_checks("SHORT", 2.0, 100.0, 102.0, 97.0 + 2 * tol)
    upper = wrapper.point_bounded_geometry_contract_checks("SHORT", 2.0, 100.0, 102.0, 96.99 - 2 * tol)
    assert not lower["target_interval"]
    assert not upper["target_interval"]


def test_fresh_report_schema_and_flags() -> None:
    wrapper = load_module()
    base = {"schema_version": "stbs004_existing_run_comparator_report.v1"}
    report = wrapper.revise_report(base)
    assert report["schema_version"] == "stbs006_point_bounded_geometry_comparator_report.v1"
    assert report["point_bounded_telemetry_consistency"] is True
    assert report["geometry_point"] == 0.01
    assert report["geometry_tolerance"] == wrapper.TOL
    assert report["exact_raw_double_geometry_proven"] is False
    assert report["runtime_tick_size_proven"] is False
    assert report["exact_position_sizing_proven"] is False


def test_claim_order_inherited_gates_and_zero_authority() -> None:
    text = WRAPPER_PATH.read_text(encoding="utf-8")
    assert text.index("OUTPUT_DIR.mkdir") < text.index("for label, (path, expected) in BASE.BASE.STATIC_BINDINGS.items()")
    assert "BASE.orders_section_is_empty" in text
    assert "BASE.BASE.event_identity_checks" in text
    assert "FALSE_AUTHORITIES" in text
    assert "economics_evaluated\": False" in text
    assert "subprocess" not in text


def test_hyp005_failure_chain_is_postclaim_bound() -> None:
    text = WRAPPER_PATH.read_text(encoding="utf-8")
    for label in ("hyp005_start", "hyp005_terminal", "hyp005_failure", "hyp005_review"):
        assert f'"{label}"' in text
