from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "acquire_event_aggflow_003_trades.py"
SPEC = importlib.util.spec_from_file_location("event_aggflow_003_acquire", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def workspace() -> Path:
    return MODULE_PATH.resolve().parents[3]


def quote() -> dict:
    return MODULE.load_quote(workspace() / MODULE.QUOTE_REL)


def live_windows() -> list[dict]:
    result = []
    for item in quote()["quotes"]:
        result.append(
            {
                "request_id": item["request_id"],
                "event_clock_id": item["event_clock_id"],
                "split": item["split"],
                "event_time_utc": item["event_time_utc"],
                "start": item["start"],
                "end": item["end"],
                "live_estimated_usd": item["estimated_usd"],
                "live_billable_bytes": item["billable_bytes"],
                "metadata_attempt": 1,
            }
        )
    return result


def test_bound_free_quote_receipt_passes() -> None:
    payload = quote()
    assert payload["request_count"] == 329
    assert payload["nonzero_billable_request_count"] == 327
    assert payload["paid_request_made"] is False


def test_bound_owner_authority_passes_and_keeps_later_stages_closed() -> None:
    authority = MODULE.validate_owner_authority(workspace() / MODULE.OWNER_REL)
    assert authority["approved_max_usd"] == 1.0
    assert authority["request_count"] == 329
    assert authority["validation_source_authorized"] is False
    assert authority["outcome_prices_authorized"] is False
    assert authority["mql5_authorized"] is False


def test_normalized_tool_hash_ignores_only_registry_sentinel_value() -> None:
    source = MODULE_PATH.read_bytes()
    base = MODULE.normalized_tool_base_sha256(source)
    lines = source.splitlines(keepends=True)
    matches = [
        index
        for index, line in enumerate(lines)
        if MODULE._SENTINEL_RE.match(line.rstrip(b"\n"))
    ]
    assert len(matches) == 1
    index = matches[0]
    newline = b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = (
        b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "'
        + b"A" * 64
        + b'"'
        + newline
    )
    armed = b"".join(lines)
    assert MODULE.normalized_tool_base_sha256(armed) == base


def test_live_quote_contract_passes_for_exact_frozen_population() -> None:
    source = quote()["quotes"]
    total_usd, total_bytes = MODULE.validate_live_quote(live_windows(), source)
    assert total_usd == pytest.approx(0.875670075414, abs=1e-12)
    assert total_bytes == 33_580_128


def test_live_quote_rejects_aggregate_above_owner_ceiling() -> None:
    live = live_windows()
    live[0]["live_estimated_usd"] = 1.01
    with pytest.raises(MODULE.AcquisitionError, match="Owner ceiling"):
        MODULE.validate_live_quote(live, quote()["quotes"])


def test_live_quote_rejects_identity_or_window_drift() -> None:
    live = live_windows()
    live[0]["end"] = "2020-01-01T00:00:00.000Z"
    with pytest.raises(MODULE.AcquisitionError, match="identity/window drift"):
        MODULE.validate_live_quote(live, quote()["quotes"])


def test_request_args_are_exact_and_source_only() -> None:
    item = quote()["quotes"][0]
    args = MODULE.request_args(item)
    assert args == {
        "dataset": "GLBX.MDP3",
        "schema": "trades",
        "symbols": ["6E.v.0"],
        "stype_in": "continuous",
        "start": item["start"],
        "end": item["end"],
    }
    assert "EURUSD" not in json.dumps(args)


def test_zero_byte_identity_remains_coverage_without_paid_filename_change() -> None:
    zeros = [item for item in live_windows() if item["live_billable_bytes"] == 0]
    assert [item["request_id"] for item in zeros] == ["EVT0206", "EVT0228"]
    assert MODULE.filename(zeros[0]) == "EVT0206.dbn.zst"


def test_source_empty_manifest_requires_exact_live_zero_byte_binding() -> None:
    live = live_windows()
    live_by_id = {item["request_id"]: item for item in live}
    zero = live_by_id["EVT0206"]
    entry = {
        "request_id": zero["request_id"],
        "event_clock_id": zero["event_clock_id"],
        "start": zero["start"],
        "end": zero["end"],
        "live_estimated_usd": zero["live_estimated_usd"],
        "live_billable_bytes": 0,
        "reason": "LIVE_METADATA_ZERO_BILLABLE_BYTES_NO_TIMESERIES_CALL",
    }
    assert MODULE.validate_source_empty_entries([entry], live_by_id) == {"EVT0206"}
    bad = dict(entry, end="2020-01-01T00:00:00.000Z")
    with pytest.raises(MODULE.AcquisitionError, match="source-empty"):
        MODULE.validate_source_empty_entries([bad], live_by_id)


def test_exclusive_campaign_lock_rejects_second_writer(tmp_path: Path) -> None:
    with MODULE.exclusive_campaign_lock(tmp_path):
        with pytest.raises(MODULE.AcquisitionError, match="already locked"):
            with MODULE.exclusive_campaign_lock(tmp_path):
                pass
    assert not (tmp_path / ".paid_acquisition.lock").exists()


def test_atomic_json_writer_is_canonical_and_replaces(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    MODULE.write_json_atomic(path, {"z": 1, "a": False})
    assert path.read_bytes() == b'{"a":false,"z":1}\n'
    MODULE.write_json_atomic(path, {"z": 2})
    assert path.read_bytes() == b'{"z":2}\n'
    assert not path.with_suffix(".json.tmp").exists()

