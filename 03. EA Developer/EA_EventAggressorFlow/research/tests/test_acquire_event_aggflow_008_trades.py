from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "acquire_event_aggflow_008_trades.py"
SPEC = importlib.util.spec_from_file_location("event_aggflow_008_acquire", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def workspace() -> Path:
    return MODULE_PATH.resolve().parents[3]


def quote() -> dict:
    return MODULE.load_quote(workspace() / MODULE.QUOTE_REL)


def live() -> list[dict]:
    root = workspace() / MODULE.RECOVERY_PARENT_PLAN_REL
    return json.loads(root.read_text(encoding="ascii"))["windows"]


def test_plan_owner_runtime_quote_are_exact_hash_bound() -> None:
    root = workspace()
    assert MODULE.sha256_file(root / MODULE.PLAN_REL) == MODULE.PLAN_SHA256
    assert MODULE.sha256_file(root / MODULE.OWNER_REL) == MODULE.OWNER_AUTHORITY_SHA256
    assert MODULE.sha256_file(root / MODULE.RUNTIME_RECEIPT_REL) == MODULE.RUNTIME_RECEIPT_SHA256
    assert quote()["request_count"] == 329


def test_owner_authority_limits_manual_retry_and_worst_case() -> None:
    authority = MODULE.validate_owner_authority(workspace() / MODULE.OWNER_REL)
    assert authority["approved_max_usd"] == 1.0
    assert authority["recovery_unresolved_request_id"] == "EVT0081"
    assert authority["manual_retry_evt0081_authorized_once"] is True
    assert authority["worst_case_aggregate_with_one_manual_retry_usd"] == pytest.approx(
        0.880477845666, abs=1e-12
    )
    assert authority["detached_monitored_execution_required"] is True


def test_parent_stopped_campaign_contract_is_exact() -> None:
    parent = MODULE.load_recovery_parent(workspace(), quote())
    manifest = parent["manifest"]
    assert len(parent["live"]) == 329
    assert len(manifest["downloads"]) == 80
    assert manifest["in_flight"]["request_id"] == "EVT0081"
    assert sum(item["records"] for item in manifest["downloads"]) == 37_737
    assert sum(item["bytes"] for item in manifest["downloads"]) == 645_863
    assert not (parent["raw"] / "EVT0081.dbn.zst").exists()
    assert not (parent["raw"] / "EVT0081.dbn.zst.partial").exists()


def test_manual_retry_risk_stays_under_owner_ceiling() -> None:
    item = next(row for row in live() if row["request_id"] == "EVT0081")
    original_total = sum(float(row["live_estimated_usd"]) for row in live())
    assert item["live_estimated_usd"] == MODULE.RECOVERY_ESTIMATED_USD
    assert item["live_billable_bytes"] == MODULE.RECOVERY_BILLABLE_BYTES
    assert original_total + item["live_estimated_usd"] == pytest.approx(
        MODULE.RECOVERY_WORST_CASE_AGGREGATE_USD, abs=1e-12
    )
    assert MODULE.RECOVERY_WORST_CASE_AGGREGATE_USD < MODULE.OWNER_CEILING_USD


def test_parent_first_file_full_stream_dbnv3_validates() -> None:
    parent = MODULE.load_recovery_parent(workspace(), quote())
    item = parent["manifest"]["downloads"][0]
    path = parent["raw"] / item["filename"]
    assert MODULE.validate_dbn_file_v3(path, allow_zero=True) == item["records"]
    assert MODULE.sha256_file(path) == item["sha256"]


def test_inherit_parent_completed_copies_exact_80_without_remote(tmp_path: Path) -> None:
    parent = MODULE.load_recovery_parent(workspace(), quote())
    live_by_id = {item["request_id"]: item for item in parent["live"]}
    manifest_path = tmp_path / "download_manifest.json"
    manifest = {
        "downloads": [],
        "paid_timeseries_calls": 0,
        "updated_at_utc": "2026-08-12T00:00:00Z",
    }
    MODULE.write_json_atomic(manifest_path, manifest)
    MODULE.inherit_parent_completed(
        parent=parent,
        root=tmp_path,
        manifest=manifest,
        live_by_id=live_by_id,
        manifest_path=manifest_path,
    )
    assert len(manifest["downloads"]) == 80
    assert manifest["inherited_parent_paid_timeseries_calls"] == 80
    assert manifest["successor_paid_timeseries_calls"] == 0
    assert manifest["manual_retry_evt0081_calls"] == 0
    assert sum(item["records"] for item in manifest["downloads"]) == 37_737
    assert all(item["inherited_local_no_remote_call"] for item in manifest["downloads"])
    assert not (tmp_path / "raw" / "EVT0081.dbn.zst").exists()


def test_live_quote_contract_is_exact_329_and_ceiling_safe() -> None:
    total_usd, total_bytes = MODULE.validate_live_quote(live(), quote()["quotes"])
    assert total_usd == pytest.approx(0.875670075414, abs=1e-12)
    assert total_bytes == 33_580_128


def test_live_quote_rejects_identity_drift() -> None:
    changed = [dict(item) for item in live()]
    changed[0]["end"] = "2019-01-01T00:00:00.000Z"
    with pytest.raises(MODULE.AcquisitionError, match="identity/window"):
        MODULE.validate_live_quote(changed, quote()["quotes"])


def test_request_args_are_exact_source_only() -> None:
    item = live()[0]
    assert MODULE.request_args(item) == {
        "dataset": "GLBX.MDP3",
        "schema": "trades",
        "symbols": ["6E.v.0"],
        "stype_in": "continuous",
        "start": item["start"],
        "end": item["end"],
    }


def test_source_empty_entries_require_live_zero_byte_binding() -> None:
    live_by_id = {item["request_id"]: item for item in live()}
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


def test_tool_is_self_contained_and_has_no_batch_or_concurrent_paid_calls() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "EA_SweepCascadeContinuation",
        "FOUNDATION_SHA256",
        "batch.submit_job",
        "batch.download",
        "ThreadPoolExecutor(max_workers=workers) as pool:return",
    ):
        assert forbidden not in source
    assert "paid_calls_serial_only" in source


def test_exclusive_campaign_lock_rejects_second_writer(tmp_path: Path) -> None:
    with MODULE.exclusive_campaign_lock(tmp_path):
        with pytest.raises(MODULE.AcquisitionError, match="already locked"):
            with MODULE.exclusive_campaign_lock(tmp_path):
                pass


def test_atomic_writer_is_canonical_and_replaces(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    MODULE.write_json_atomic(path, {"z": 1, "a": False})
    assert path.read_bytes() == b'{"a":false,"z":1}\n'
    MODULE.write_json_atomic(path, {"z": 2})
    assert path.read_bytes() == b'{"z":2}\n'
