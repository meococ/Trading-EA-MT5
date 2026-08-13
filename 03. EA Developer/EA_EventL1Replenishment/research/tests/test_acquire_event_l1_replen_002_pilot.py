from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys
from types import SimpleNamespace

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "acquire_event_l1_replen_002_pilot.py"
SPEC = importlib.util.spec_from_file_location("event_l1_replen_002_pilot", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def msg(ts: int, action: str, side: str, bid: int, ask: int, bid_sz: int, ask_sz: int):
    level = SimpleNamespace(
        bid_px=bid, ask_px=ask, bid_sz=bid_sz, ask_sz=ask_sz,
        bid_ct=2, ask_ct=3,
    )
    return SimpleNamespace(
        ts_recv=ts, ts_event=ts - 100, action=action, side=side,
        price=bid, size=1, flags=0, depth=0, sequence=ts,
        levels=[level],
    )


def test_request_args_are_exact_single_pilot() -> None:
    assert MODULE.request_args() == {
        "dataset": "GLBX.MDP3", "schema": "mbp-1", "symbols": ["6E.v.0"],
        "stype_in": "continuous", "start": "2019-01-03T15:00:00.000Z",
        "end": "2019-01-03T15:02:00.000Z",
    }


def test_semantics_pass_with_trade_and_bbo_size_update() -> None:
    start = 1_000_000_000
    records = [
        msg(start, "A", "B", 1_100_000_000, 1_100_050_000, 10, 12),
        msg(start + 1_000_000, "T", "B", 1_100_000_000, 1_100_050_000, 9, 12),
        msg(start + 2_000_000, "M", "A", 1_100_000_000, 1_100_050_000, 9, 14),
    ]
    result = MODULE.analyze_records(records, start, start + 10_000_000)
    assert result["verdict"] == "PASS_SEMANTICS"
    assert result["trade_action_count"] == 1
    assert result["bbo_size_update_count"] == 2
    assert result["bbo_size_change_unchanged_price_count"] == 2


def test_semantics_parks_on_nonmonotone_or_outside_window() -> None:
    start = 1_000_000_000
    records = [
        msg(start + 2, "T", "B", 100, 101, 2, 3),
        msg(start - 1, "M", "A", 100, 101, 3, 3),
    ]
    result = MODULE.analyze_records(records, start, start + 100)
    assert result["verdict"] == "PARK_SOURCE_SEMANTICS"
    assert result["containment_violation_count"] == 1
    assert result["monotonicity_violation_count"] == 1


def test_event_driven_gap_is_diagnostic_not_a_gate() -> None:
    start = 1_000_000_000
    records = [
        msg(start, "T", "B", 100, 101, 2, 3),
        msg(start + 8_000_000_000, "M", "A", 100, 101, 4, 3),
    ]
    result = MODULE.analyze_records(records, start, start + 9_000_000_000)
    assert result["max_inter_message_gap_ms"] == 8000.0
    assert result["semantic_gates"].get("max_gap") is None
    assert result["verdict"] == "PASS_SEMANTICS"


def test_parent_quote_is_hash_bound_and_contains_exact_pilot() -> None:
    workspace = MODULE.workspace_from_source()
    item = MODULE.load_parent_quote(workspace / MODULE.QUOTE_REL)
    assert item["request_id"] == "EVT0001"
    assert item["estimated_usd"] == MODULE.PARENT_ESTIMATED_USD
    assert item["billable_bytes"] == MODULE.PARENT_BILLABLE_BYTES


def test_owner_authority_is_exact_and_excludes_live() -> None:
    workspace = MODULE.workspace_from_source()
    authority = MODULE.validate_owner_authority(workspace / MODULE.AUTHORITY_REL)
    assert authority["pilot"]["approved_max_usd"] == 0.01
    assert authority["standing_research_acquisition_policy"]["live_trading_capital_authorized"] is False


def test_normalized_hash_ignores_only_registry_sentinel() -> None:
    raw = MODULE_PATH.read_bytes()
    base = MODULE.normalized_tool_base_sha256(raw)
    unarmed = re.sub(
        rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")$',
        b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None", raw,
        count=1, flags=re.MULTILINE,
    )
    assert MODULE.normalized_tool_base_sha256(unarmed) == base


def test_registry_authority_fails_closed_when_unarmed(monkeypatch) -> None:
    monkeypatch.setattr(MODULE, "REVIEWED_REGISTRY_ROW_SHA256", None)
    with pytest.raises(MODULE.AcquisitionError, match="sentinel"):
        MODULE.validate_registry_authority(MODULE.workspace_from_source())


def test_source_has_one_serial_paid_call_surface_and_no_batch() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert source.count("client.timeseries.get_range(") == 1
    assert ".batch." not in source
    assert "automatic retry forbidden" in source


def test_api_key_is_not_embedded() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "DATABENTO_API_KEY" in source
    assert not any(token.startswith("db-") and len(token) > 24
                   for token in source.replace('"', " ").replace("'", " ").split())

