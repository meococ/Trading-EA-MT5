from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "acquire_event_depth_transfer_005_continuation.py"
SPEC = importlib.util.spec_from_file_location("event_depth_transfer_005", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_parent_snapshot_freezes_complete_ambiguous_unattempted_and_unavailable() -> None:
    complete, ambiguous, unattempted, unavailable = MODULE.load_parent_snapshot(
        MODULE.workspace_from_source()
    )
    assert len(complete) == 256
    assert len(ambiguous) == 8
    assert len(unattempted) == 63
    assert len(unavailable) == 2
    assert unattempted[0]["event_clock_id"] == "EVT0267"
    assert unattempted[-1]["event_clock_id"] == "EVT0329"
    assert abs(
        sum(float(item["live_estimated_usd"]) for item in unattempted)
        - 0.434695020317
    ) < 1e-12


def test_combined_gate_preserves_original_distribution_thresholds() -> None:
    parent = []
    child = []
    for index in range(256):
        parent.append({"status": "COMPLETE", "semantic_gate_pass": index != 0,
                       "effective_classification": "CONTINUATION" if index < 121 else "REVERSAL",
                       "effective_direction": 1 if index % 2 == 0 else -1})
    for index in range(63):
        child.append({"status": "COMPLETE", "semantic_gate_pass": True,
                      "effective_classification": "CONTINUATION" if index < 31 else "REVERSAL",
                      "effective_direction": 1 if index % 2 == 0 else -1})
    result = MODULE.summarize_combined(parent, child, [{}] * 8, [{}] * 2)
    assert result["gate_pass"] is True
    child[0]["status"] = "FAILED_NO_RETRY"
    assert MODULE.summarize_combined(parent, child, [{}] * 8, [{}] * 2)["gate_pass"] is False


def test_source_has_one_paid_call_surface_and_no_retry_batch_or_subscription() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert source.count("local.client.timeseries.get_range(") == 1
    assert ".batch." not in source
    assert ".subscribe(" not in source
    assert "for attempt" not in source
    assert "FAILED_NO_RETRY" in source


def test_revoked_module_does_not_import_paid_parent_engine() -> None:
    assert MODULE.PARENT is None


def test_paid_continuation_is_revoked_before_any_runtime_or_network_access() -> None:
    with pytest.raises(MODULE.ContinuationError, match="not Owner-authorized"):
        MODULE.execute(MODULE.workspace_from_source(), 8)
