from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "acquire_event_depth_transfer_004_design.py"
SPEC = importlib.util.spec_from_file_location("event_depth_transfer_004", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_quote_population_freezes_327_positive_and_two_unavailable() -> None:
    workspace = MODULE.workspace_from_source()
    positive, unavailable = MODULE.load_quote(workspace / MODULE.QUOTE_REL)
    assert len(positive) == 327
    assert {item["event_clock_id"] for item in unavailable} == {"EVT0206", "EVT0228"}
    assert max(float(item["estimated_usd"]) for item in positive) == 0.025940984488
    assert sum(float(item["estimated_usd"]) for item in positive) == 2.094538114962


def test_raw_filename_uses_actual_dynamic_window() -> None:
    name = MODULE.raw_filename({
        "event_clock_id": "EVT0001", "start": "2019-01-03T15:00:00.000Z",
        "end": "2019-01-03T15:01:00.000Z",
    })
    assert name == "EVT0001_20190103T150000Z_20190103T150100Z_mbp-10.dbn.zst"


def test_request_contract_is_exact_mbp10_sixty_second_window() -> None:
    positive, _ = MODULE.load_quote(MODULE.workspace_from_source() / MODULE.QUOTE_REL)
    args = MODULE.request_args(positive[0])
    assert args == {
        "dataset": "GLBX.MDP3", "schema": "mbp-10", "symbols": ["6E.v.0"],
        "stype_in": "continuous", "start": "2019-01-03T15:00:00.000Z",
        "end": "2019-01-03T15:01:00.000Z",
    }


def make_entries(continuation: int, reversal: int, invalid: int = 0):
    entries = []
    for index in range(continuation):
        entries.append({"status": "COMPLETE", "semantic_gate_pass": True,
                        "effective_classification": "CONTINUATION",
                        "effective_direction": 1 if index % 2 == 0 else -1})
    for index in range(reversal):
        entries.append({"status": "COMPLETE", "semantic_gate_pass": True,
                        "effective_classification": "REVERSAL",
                        "effective_direction": -1 if index % 2 == 0 else 1})
    for _ in range(invalid):
        entries.append({"status": "COMPLETE", "semantic_gate_pass": False,
                        "effective_classification": "SOURCE_INVALID_FLAT",
                        "effective_direction": 0})
    return entries


def test_source_census_gate_pass_and_failure_are_deterministic() -> None:
    unavailable = [{}, {}]
    passing = MODULE.summarize(make_entries(190, 130, 7), unavailable)
    assert passing["gate_pass"] is True
    degenerate = MODULE.summarize(make_entries(310, 10, 7), unavailable)
    assert degenerate["gate_pass"] is False
    assert degenerate["gates"]["reversal_share_at_least_10pct"] is False


def test_source_has_one_paid_call_surface_and_no_retry_batch_or_subscription() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert source.count("local.client.timeseries.get_range(") == 1
    assert ".batch." not in source
    assert ".subscribe(" not in source
    assert "for attempt" not in source
    assert "FAILED_NO_RETRY" in source


def test_reviewed_semantics_engine_remains_hash_bound() -> None:
    engine = MODULE_PATH.with_name("acquire_event_depth_transfer_001_pilot.py")
    assert MODULE.sha256_file(engine) == MODULE.ENGINE_SHA256


def test_paid_execute_is_revoked_before_any_runtime_or_api_access() -> None:
    try:
        MODULE.execute(MODULE.workspace_from_source(), 1)
    except MODULE.AcquisitionError as exc:
        assert "is revoked" in str(exc)
        assert "not Owner-authorized" in str(exc)
    else:
        raise AssertionError("revoked HYP004 execute unexpectedly returned")
