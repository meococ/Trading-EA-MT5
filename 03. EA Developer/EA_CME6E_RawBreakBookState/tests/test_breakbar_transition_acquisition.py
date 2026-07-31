from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


PACKAGE = Path(__file__).resolve().parents[1]
MODULE_PATH = PACKAGE / "research" / "acquire_cme6e_breakbar_transition_design.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "acquire_cme6e_breakbar_transition_design", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_approved_source_plan_is_clock_correct_and_hash_bound() -> None:
    module = load_module()
    plan = module.load_approved_source_plan()

    assert plan["plan_id"] == module.APPROVED_SOURCE_PLAN_ID
    assert len(plan["requests"]) == 561
    assert len(plan["metadata_empty_windows"]) == 4
    assert plan["clock_semantics"]["feature_window_start_role"] == "BREAK_BAR_OPEN"
    assert plan["clock_semantics"]["feature_window_end_role"] == "ACTUAL_NEXT_BAR_DECISION_ENTRY"
    assert plan["input"]["outcome_fields_used"] is False
    assert plan["paid_request_made"] is False


def test_execution_authorization_requires_exact_owner_ceiling() -> None:
    module = load_module()
    plan = module.load_approved_source_plan()
    packet = module.build_execution_authorization(
        plan=plan,
        approved_max_usd=1.40,
    )

    assert packet["source_plan"]["plan_id"] == module.APPROVED_SOURCE_PLAN_ID
    assert packet["approved_max_usd"] == 1.40
    assert packet["owner_authority"] == (
        "2026-07-27 explicit approval for plan C57B0AF9...64A1D1C up to USD1.40"
    )
    assert packet["outcome_fields_used"] is False
    assert packet["prior_hypothesis_oos_opened"] is False
    module.validate_execution_authorization(packet, plan)

    with pytest.raises(module.AcquisitionError, match="USD1.40"):
        module.build_execution_authorization(plan=plan, approved_max_usd=1.39)


def test_borrowed_acquisition_foundation_is_immutable() -> None:
    module = load_module()
    assert module.sha256_file(module.BASE_ACQUISITION_PATH) == module.BASE_ACQUISITION_SHA256
    assert module.base.MODULE_PATH == module.MODULE_PATH
    assert module.base.DEFAULT_ROOT == module.DEFAULT_ROOT
