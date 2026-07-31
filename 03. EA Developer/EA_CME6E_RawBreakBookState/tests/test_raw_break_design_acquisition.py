from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


PACKAGE = Path(__file__).resolve().parents[1]
MODULE_PATH = PACKAGE / "research" / "acquire_cme6e_raw_break_design.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "acquire_cme6e_raw_break_design", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeMetadata:
    def __init__(self, cost: float = 0.10, size: int = 1000):
        self.cost = cost
        self.size = size
        self.cost_calls: list[dict] = []
        self.size_calls: list[dict] = []

    def get_cost(self, **kwargs):
        self.cost_calls.append(kwargs)
        return self.cost

    def get_billable_size(self, **kwargs):
        self.size_calls.append(kwargs)
        return self.size


class FakeTimeseries:
    def __init__(self):
        self.calls: list[dict] = []

    def get_range(self, **kwargs):
        self.calls.append(kwargs)
        Path(kwargs["path"]).write_bytes(b"\x28\xb5\x2f\xfddbn-zstd-test")


class CrashBeforeWriteTimeseries(FakeTimeseries):
    def get_range(self, **kwargs):
        self.calls.append(kwargs)
        raise RuntimeError("simulated crash before stream")


class FakeClient:
    def __init__(self, cost: float = 0.10, size: int = 1000):
        self.metadata = FakeMetadata(cost, size)
        self.timeseries = FakeTimeseries()


def tiny_plan(module) -> dict:
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA_VERSION,
        "candidate_identity": module.CANDIDATE_IDENTITY,
        "dataset": module.DATASET,
        "schema": module.SCHEMA,
        "symbol": module.SYMBOL,
        "stype_in": module.STYPE_IN,
        "cost_mode": module.COST_MODE,
        "window_seconds": module.WINDOW_SECONDS,
        "design_utc_years": [2019, 2020],
        "sealed_oos_utc_years": [2021, 2022],
        "sealed_oos_quoted": False,
        "input": {
            "fields_used": ["position_id", "decision_time", "direction"],
            "outcome_fields_used": False,
        },
        "requests": [
            {
                "position_id": "1",
                "direction": "BUY",
                "start": "2020-01-02T00:00:00Z",
                "end": "2020-01-02T00:02:00Z",
                "filename": "CTRL_PID000000001_20200102T000200Z.dbn.zst",
            },
            {
                "position_id": "2",
                "direction": "SELL",
                "start": "2020-01-03T00:00:00Z",
                "end": "2020-01-03T00:02:00Z",
                "filename": "CTRL_PID000000002_20200103T000200Z.dbn.zst",
            },
        ],
        "metadata_empty_windows": [],
        "live_quotes": [],
        "estimated_cost_usd": 0.20,
        "estimated_billable_bytes": 2000,
        "internal_2x_cost_ceiling_usd": 1.0,
        "recommended_owner_ceiling_usd": 1.0,
        "download_authorized": False,
        "paid_request_made": False,
        "plan_id": "UNIT_TEST_PLAN",
    }


def tiny_execution(module, plan: dict) -> dict:
    return {
        "schema_version": module.EXECUTION_SCHEMA_VERSION,
        "source_plan": {
            "plan_id": plan["plan_id"],
            "sha256": "UNIT_TEST_SOURCE_SHA",
        },
        "acquisition_tool": {"sha256": "UNIT_TEST_TOOL_SHA"},
        "approved_max_usd": 1.0,
        "prior_session_estimate_usd": 0.0,
        "combined_session_cap_usd": 1.0,
        "projected_combined_estimate_usd": 0.20,
        "outcome_fields_used": False,
        "sealed_oos_opened": False,
        "execution_id": "UNIT_TEST_EXECUTION",
    }


def patch_unit_contract(monkeypatch, module) -> None:
    monkeypatch.setattr(module, "validate_approved_source_plan", lambda plan: None)
    monkeypatch.setattr(
        module, "validate_execution_authorization", lambda packet, plan: None
    )
    monkeypatch.setattr(module, "ensure_output_root", lambda path: path)
    monkeypatch.setattr(
        module,
        "validate_dbn_file",
        lambda path, allow_zero=False: (module.validate_dbn_zstd(path) or 1),
    )


def test_real_execution_authorization_binds_approved_plan_tool_and_caps() -> None:
    module = load_module()
    plan = module.load_approved_source_plan()

    packet = module.build_execution_authorization(
        plan=plan,
        approved_max_usd=0.68,
        prior_session_estimate_usd=0.254399180414,
        combined_session_cap_usd=1.0,
    )

    assert packet["source_plan"]["plan_id"] == module.APPROVED_SOURCE_PLAN_ID
    assert packet["source_plan"]["sha256"] == module.APPROVED_SOURCE_PLAN_SHA256
    assert packet["acquisition_tool"]["sha256"] == module.sha256_file(MODULE_PATH)
    assert packet["approved_max_usd"] == 0.68
    assert packet["projected_combined_estimate_usd"] == pytest.approx(
        0.594278857113
    )
    assert packet["outcome_fields_used"] is False
    assert packet["sealed_oos_opened"] is False
    module.validate_execution_authorization(packet, plan)


def test_source_plan_mutation_is_rejected_before_any_network_call() -> None:
    module = load_module()
    plan = module.load_approved_source_plan()
    plan["requests"][0]["end"] = "2099-01-01T00:00:00Z"

    with pytest.raises(module.AcquisitionError, match="source plan"):
        module.validate_approved_source_plan(plan)


def test_requotes_every_window_and_blocks_before_paid_call(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    patch_unit_contract(monkeypatch, module)
    plan = tiny_plan(module)
    execution = tiny_execution(module, plan)
    client = FakeClient(cost=0.60)

    with pytest.raises(module.AcquisitionError, match="approved ceiling"):
        module.download_windows(
            client=client,
            plan=plan,
            execution=execution,
            root=tmp_path,
        )

    assert len(client.metadata.cost_calls) == 2
    assert len(client.metadata.size_calls) == 2
    assert client.timeseries.calls == []


def test_download_hashes_and_resume_skips_verified_files(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    patch_unit_contract(monkeypatch, module)
    plan = tiny_plan(module)
    execution = tiny_execution(module, plan)
    client = FakeClient()

    first = module.download_windows(
        client=client, plan=plan, execution=execution, root=tmp_path
    )
    second = module.download_windows(
        client=client, plan=plan, execution=execution, root=tmp_path
    )

    assert first["status"] == "DOWNLOADED_RAW_VALIDATION_REQUIRED"
    assert len(first["downloads"]) == 2
    assert second["resume_verified_files"] == 2
    assert len(client.timeseries.calls) == 2
    assert all(item["sha256"] for item in first["downloads"])


def test_zero_record_response_is_checkpointed_without_retry(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    patch_unit_contract(monkeypatch, module)

    def count(path: Path, allow_zero: bool = False) -> int:
        module.validate_dbn_zstd(path)
        return 0 if "000000001" in path.name else 3

    monkeypatch.setattr(module, "validate_dbn_file", count)
    plan = tiny_plan(module)
    execution = tiny_execution(module, plan)
    client = FakeClient()

    first = module.download_windows(
        client=client, plan=plan, execution=execution, root=tmp_path
    )
    second = module.download_windows(
        client=client, plan=plan, execution=execution, root=tmp_path
    )

    assert first["source_empty_files"] == 1
    assert second["resume_verified_files"] == 2
    assert len(client.timeseries.calls) == 2


def test_missing_in_flight_response_is_never_retried(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    patch_unit_contract(monkeypatch, module)
    plan = tiny_plan(module)
    execution = tiny_execution(module, plan)
    first_client = FakeClient()
    first_client.timeseries = CrashBeforeWriteTimeseries()

    with pytest.raises(module.AcquisitionError, match="paid request failed"):
        module.download_windows(
            client=first_client, plan=plan, execution=execution, root=tmp_path
        )

    second_client = FakeClient()
    with pytest.raises(module.AcquisitionError, match="refusing automatic retry"):
        module.download_windows(
            client=second_client, plan=plan, execution=execution, root=tmp_path
        )
    assert second_client.timeseries.calls == []


def test_manifest_tamper_fails_before_network_call(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    patch_unit_contract(monkeypatch, module)
    plan = tiny_plan(module)
    execution = tiny_execution(module, plan)
    module.download_windows(
        client=FakeClient(), plan=plan, execution=execution, root=tmp_path
    )
    manifest_path = tmp_path / module.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text("utf-8"))
    manifest["downloads"][0]["position_id"] = "999"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    resumed = FakeClient()

    with pytest.raises(module.AcquisitionError, match="identity mismatch"):
        module.download_windows(
            client=resumed, plan=plan, execution=execution, root=tmp_path
        )
    assert resumed.metadata.cost_calls == []
    assert resumed.timeseries.calls == []


def test_output_root_is_d_data_shelf_only() -> None:
    module = load_module()

    with pytest.raises(module.AcquisitionError, match="must be on D"):
        module.ensure_output_root(Path(r"C:\temp\cme6e"))
