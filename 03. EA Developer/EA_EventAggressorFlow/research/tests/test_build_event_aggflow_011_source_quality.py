
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "build_event_aggflow_011_source_quality.py"
SPEC = importlib.util.spec_from_file_location("event_aggflow_011_wrapper", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def workspace() -> Path:
    return MODULE_PATH.resolve().parents[3]


def foundation():
    return MODULE.load_foundation(workspace())


def test_plan_and_foundation_are_exact_hash_bound() -> None:
    root = workspace()
    assert MODULE.sha256_file(root / MODULE.PLAN_REL) == MODULE.PLAN_SHA256
    assert MODULE.sha256_file(root / MODULE.FOUNDATION_REL) == MODULE.FOUNDATION_SHA256


def test_foundation_overrides_exact_parent_and_output_contract() -> None:
    source = foundation()
    assert source.HYPOTHESIS_ID == "HYP-EVENT-AGGFLOW-EURUSD-TICK-011"
    assert source.ATTEMPT_ID == "EVENTAGGFLOW011-SOURCE-QUALITY-001"
    assert source.PARENT_HYPOTHESIS_ID == "HYP-EVENT-AGGFLOW-EURUSD-TICK-010"
    assert source.PARENT_ACQUISITION_ID == "EVENTAGGFLOW010-TRADES-DESIGN-SOURCE-001"
    assert source.PLAN_SHA256 == MODULE.PLAN_SHA256
    assert "HYP-EVENT-AGGFLOW-EURUSD-TICK-011" in source.OUTPUT_REL


def test_reused_transform_is_exact_b_minus_a_and_n_zero() -> None:
    source = foundation()
    records = [
        SimpleNamespace(action="T", side="B", size=8, ts_recv=101),
        SimpleNamespace(action="T", side="A", size=3, ts_recv=102),
        SimpleNamespace(action="T", side="N", size=100, ts_recv=103),
    ]
    values = source.aggregate_records(records, start_ns=100, end_ns=200)
    assert values["buy_volume"] == 8
    assert values["sell_volume"] == 3
    assert values["signed_flow"] == 5
    assert values["unclassified_record_count"] == 1


def test_reused_transform_rejects_end_boundary() -> None:
    source = foundation()
    record = SimpleNamespace(action="T", side="B", size=1, ts_recv=200)
    with pytest.raises(source.SourceQualityError, match="outside"):
        source.aggregate_records([record], start_ns=100, end_ns=200)


def test_wrapper_and_foundation_have_no_remote_data_calls() -> None:
    combined = MODULE_PATH.read_text(encoding="utf-8") + (
        workspace() / MODULE.FOUNDATION_REL
    ).read_text(encoding="utf-8")
    for forbidden in (
        "db.Historical(",
        "timeseries.get_range",
        "metadata.get_cost",
        "DATABENTO_API_KEY",
        "batch.submit_job",
    ):
        assert forbidden not in combined


def test_frozen_gates_are_not_overridden_by_wrapper() -> None:
    source = foundation()
    assert source.EXPECTED_EVENTS == 329
    assert source.MIN_DIRECT_EVENTS == 313
    assert source.MIN_NONZERO_EVENTS == 261
    assert source.MIN_DIRECTION_SHARE == 0.25


def test_parent_worst_case_ceiling_and_degraded_cells_are_frozen() -> None:
    assert MODULE.OWNER_CEILING_USD == 1.0
    plan = (workspace() / MODULE.PLAN_REL).read_text(encoding="utf-8")
    assert "worst-case estimate <= USD 1.00" in plan
    assert "EVT0198" in plan
    assert "EVT0270" in plan
    assert "cannot rescue a failing" in plan


def test_wrapper_does_not_create_outputs_during_load() -> None:
    source = foundation()
    output = workspace() / source.OUTPUT_REL
    assert not output.exists()
