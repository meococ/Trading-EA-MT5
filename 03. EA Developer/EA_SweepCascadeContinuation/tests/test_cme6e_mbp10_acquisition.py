from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


PACKAGE = Path(__file__).resolve().parents[1]
MODULE_PATH = PACKAGE / "research" / "acquire_cme6e_mbp10_windows.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "acquire_cme6e_mbp10_windows", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_real_offline_plan_is_hash_bound_outcome_blind_and_complete() -> None:
    module = load_module()

    plan = module.build_acquisition_plan()

    assert plan["status"] == "PLANNED_NOT_QUOTED_NOT_DOWNLOADED"
    assert plan["databento_sdk_version"] == module.DATABENTO_SDK_VERSION
    assert plan["tool"]["sha256"] == module.sha256_file(module.Path(module.__file__))
    assert plan["input"]["sha256"] == module.INPUT_SHA256
    assert plan["clock"]["sha256"] == module.CLOCK_SHA256
    assert plan["fields_used"] == ["position_id", "decision_time", "direction"]
    assert plan["outcome_fields_used"] is False
    assert len(plan["all_windows"]) == 261
    assert len(plan["requests"]) == 259
    assert [item["position_id"] for item in plan["source_empty_windows"]] == [
        "26",
        "80",
    ]
    assert plan["estimated_cost_usd"] == pytest.approx(0.254399180414)
    assert plan["recommended_owner_ceiling_usd"] == 1.0
    module.validate_plan(plan)


def test_plan_hash_rejects_any_window_mutation() -> None:
    module = load_module()
    plan = module.build_acquisition_plan()
    plan["requests"][0]["end"] = "2099-01-01T00:00:00Z"

    with pytest.raises(module.AcquisitionError, match="plan hash mismatch"):
        module.validate_plan(plan)


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
        return object()


class CrashAfterCompleteWriteTimeseries:
    def __init__(self):
        self.calls: list[dict] = []

    def get_range(self, **kwargs):
        self.calls.append(kwargs)
        Path(kwargs["path"]).write_bytes(b"\x28\xb5\x2f\xfddbn-zstd-test")
        raise RuntimeError("simulated crash after complete stream")


class CrashBeforeWriteTimeseries:
    def __init__(self):
        self.calls: list[dict] = []

    def get_range(self, **kwargs):
        self.calls.append(kwargs)
        raise RuntimeError("simulated crash before stream")


class FakeClient:
    def __init__(self, cost: float = 0.10, size: int = 1000):
        self.metadata = FakeMetadata(cost=cost, size=size)
        self.timeseries = FakeTimeseries()


def tiny_plan(module) -> dict:
    plan = {
        "schema_version": module.SCHEMA_VERSION,
        "status": "PLANNED_NOT_QUOTED_NOT_DOWNLOADED",
        "candidate_identity": module.CANDIDATE_IDENTITY,
        "databento_sdk_version": module.DATABENTO_SDK_VERSION,
        "cost_mode": module.COST_MODE,
        "tool": {
            "path": str(module.Path(module.__file__)),
            "sha256": module.sha256_file(module.Path(module.__file__)),
        },
        "recommended_owner_ceiling_usd": 1.0,
        "requests": [
            {
                "position_id": "1",
                "direction": "BUY",
                "start": "2020-01-02T00:00:00Z",
                "end": "2020-01-02T00:02:00Z",
                "filename": "PID000000001_20200102T000200Z.dbn.zst",
            },
            {
                "position_id": "2",
                "direction": "SELL",
                "start": "2020-01-03T00:00:00Z",
                "end": "2020-01-03T00:02:00Z",
                "filename": "PID000000002_20200103T000200Z.dbn.zst",
            },
        ],
        "all_windows": [],
        "source_empty_windows": [],
        "outcome_fields_used": False,
    }
    plan["plan_id"] = module.plan_id(plan)
    return plan


def test_download_requotes_every_window_and_blocks_before_paid_call(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    monkeypatch.setattr(module, "ensure_output_root", lambda path: path)
    monkeypatch.setattr(
        module,
        "validate_dbn_file",
        lambda path, allow_zero=False: (module.validate_dbn_zstd(path) or 1),
    )
    plan = tiny_plan(module)
    client = FakeClient(cost=0.60)

    with pytest.raises(module.AcquisitionError, match="exceeds approved ceiling"):
        module.download_windows(
            client=client,
            plan=plan,
            approved_max_usd=1.0,
            root=tmp_path,
        )

    assert len(client.metadata.cost_calls) == 2
    assert len(client.metadata.size_calls) == 2
    assert all(call["mode"] == "historical-streaming" for call in client.metadata.cost_calls)
    assert client.timeseries.calls == []


def test_zero_size_and_two_times_cost_drift_block_before_paid_call(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    monkeypatch.setattr(module, "ensure_output_root", lambda path: path)

    zero_plan = tiny_plan(module)
    zero_client = FakeClient(cost=0.10, size=0)
    with pytest.raises(module.AcquisitionError, match="now empty"):
        module.download_windows(
            client=zero_client,
            plan=zero_plan,
            approved_max_usd=1.0,
            root=tmp_path / "zero",
        )
    assert zero_client.timeseries.calls == []

    drift_plan = tiny_plan(module)
    drift_plan["internal_2x_cost_ceiling_usd"] = 0.15
    drift_plan["plan_id"] = module.plan_id(drift_plan)
    drift_client = FakeClient(cost=0.10, size=1000)
    with pytest.raises(module.AcquisitionError, match="two-times drift ceiling"):
        module.download_windows(
            client=drift_client,
            plan=drift_plan,
            approved_max_usd=1.0,
            root=tmp_path / "drift",
        )
    assert drift_client.timeseries.calls == []


def test_download_hashes_files_and_resume_skips_verified_outputs(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    monkeypatch.setattr(module, "ensure_output_root", lambda path: path)
    monkeypatch.setattr(
        module,
        "validate_dbn_file",
        lambda path, allow_zero=False: (module.validate_dbn_zstd(path) or 1),
    )
    plan = tiny_plan(module)
    client = FakeClient(cost=0.10, size=1000)

    first = module.download_windows(
        client=client,
        plan=plan,
        approved_max_usd=1.0,
        root=tmp_path,
    )
    assert first["status"] == "DOWNLOADED_RAW_VALIDATION_REQUIRED"
    assert len(first["downloads"]) == 2
    assert len(client.timeseries.calls) == 2
    assert all(item["sha256"] for item in first["downloads"])

    second = module.download_windows(
        client=client,
        plan=plan,
        approved_max_usd=1.0,
        root=tmp_path,
    )
    assert second["status"] == "DOWNLOADED_RAW_VALIDATION_REQUIRED"
    assert len(client.timeseries.calls) == 2
    assert second["resume_verified_files"] == 2

    manifest = json.loads((tmp_path / module.MANIFEST_NAME).read_text("utf-8"))
    assert manifest["plan_id"] == plan["plan_id"]
    assert manifest["paid_requests_completed"] == 2


def test_resume_adopts_complete_in_flight_file_without_second_paid_call(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    monkeypatch.setattr(module, "ensure_output_root", lambda path: path)
    monkeypatch.setattr(
        module,
        "validate_dbn_file",
        lambda path, allow_zero=False: (module.validate_dbn_zstd(path) or 1),
    )
    plan = tiny_plan(module)
    first_client = FakeClient(cost=0.10, size=1000)
    first_client.timeseries = CrashAfterCompleteWriteTimeseries()

    with pytest.raises(module.AcquisitionError, match="paid request failed"):
        module.download_windows(
            client=first_client,
            plan=plan,
            approved_max_usd=1.0,
            root=tmp_path,
        )

    interrupted = json.loads((tmp_path / module.MANIFEST_NAME).read_text("utf-8"))
    assert interrupted["in_flight"]["position_id"] == "1"
    assert interrupted["paid_requests_completed"] == 0

    second_client = FakeClient(cost=0.10, size=1000)
    resumed = module.download_windows(
        client=second_client,
        plan=plan,
        approved_max_usd=1.0,
        root=tmp_path,
    )

    assert resumed["status"] == "DOWNLOADED_RAW_VALIDATION_REQUIRED"
    assert resumed["recovered_in_flight_files"] == 1
    assert len(second_client.timeseries.calls) == 1
    assert second_client.timeseries.calls[0]["start"] == plan["requests"][1]["start"]


def test_resume_refuses_automatic_retry_when_in_flight_file_is_missing(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    monkeypatch.setattr(module, "ensure_output_root", lambda path: path)
    plan = tiny_plan(module)
    first_client = FakeClient(cost=0.10, size=1000)
    first_client.timeseries = CrashBeforeWriteTimeseries()

    with pytest.raises(module.AcquisitionError, match="paid request failed"):
        module.download_windows(
            client=first_client,
            plan=plan,
            approved_max_usd=1.0,
            root=tmp_path,
        )

    second_client = FakeClient(cost=0.10, size=1000)
    with pytest.raises(module.AcquisitionError, match="refusing automatic retry"):
        module.download_windows(
            client=second_client,
            plan=plan,
            approved_max_usd=1.0,
            root=tmp_path,
        )
    assert second_client.timeseries.calls == []


def test_complete_zero_record_response_is_checkpointed_without_paid_retry(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    monkeypatch.setattr(module, "ensure_output_root", lambda path: path)

    def record_count(path: Path, allow_zero: bool = False) -> int:
        module.validate_dbn_zstd(path)
        return 0 if "PID000000001" in path.name else 7

    monkeypatch.setattr(module, "validate_dbn_file", record_count)
    plan = tiny_plan(module)
    client = FakeClient(cost=0.10, size=1000)

    first = module.download_windows(
        client=client,
        plan=plan,
        approved_max_usd=1.0,
        root=tmp_path,
    )

    assert len(client.timeseries.calls) == 2
    assert first["source_empty_files"] == 1
    assert first["nonempty_files"] == 1
    assert first["downloads"][0]["records"] == 0
    assert first["downloads"][0]["source_empty"] is True

    resumed = module.download_windows(
        client=client,
        plan=plan,
        approved_max_usd=1.0,
        root=tmp_path,
    )
    assert len(client.timeseries.calls) == 2
    assert resumed["resume_verified_files"] == 2
    assert resumed["source_empty_files"] == 1


def test_resume_rejects_manifest_identity_tamper(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    monkeypatch.setattr(module, "ensure_output_root", lambda path: path)
    monkeypatch.setattr(
        module,
        "validate_dbn_file",
        lambda path, allow_zero=False: (module.validate_dbn_zstd(path) or 1),
    )
    plan = tiny_plan(module)
    client = FakeClient(cost=0.10, size=1000)
    module.download_windows(
        client=client,
        plan=plan,
        approved_max_usd=1.0,
        root=tmp_path,
    )
    manifest_path = tmp_path / module.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text("utf-8"))
    manifest["downloads"][0]["position_id"] = "999"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    resumed_client = FakeClient(cost=0.10, size=1000)
    with pytest.raises(module.AcquisitionError, match="identity mismatch"):
        module.download_windows(
            client=resumed_client,
            plan=plan,
            approved_max_usd=1.0,
            root=tmp_path,
        )
    assert resumed_client.metadata.cost_calls == []
    assert resumed_client.timeseries.calls == []


def test_manifest_foreign_duplicate_and_missing_files_fail_closed(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    monkeypatch.setattr(module, "ensure_output_root", lambda path: path)
    monkeypatch.setattr(
        module,
        "validate_dbn_file",
        lambda path, allow_zero=False: (module.validate_dbn_zstd(path) or 1),
    )
    plan = tiny_plan(module)

    for scenario in ("foreign", "duplicate", "missing"):
        root = tmp_path / scenario
        module.download_windows(
            client=FakeClient(),
            plan=plan,
            approved_max_usd=1.0,
            root=root,
        )
        manifest_path = root / module.MANIFEST_NAME
        manifest = json.loads(manifest_path.read_text("utf-8"))
        expected = ""
        if scenario == "foreign":
            manifest["downloads"][0]["filename"] = "foreign.dbn.zst"
            expected = "outside the frozen plan"
        elif scenario == "duplicate":
            manifest["downloads"].append(copy.deepcopy(manifest["downloads"][0]))
            expected = "duplicate output"
        else:
            (root / "raw" / manifest["downloads"][0]["filename"]).unlink()
            expected = "missing or empty"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        resumed = FakeClient()
        with pytest.raises(module.AcquisitionError, match=expected):
            module.download_windows(
                client=resumed,
                plan=plan,
                approved_max_usd=1.0,
                root=root,
            )
        assert resumed.metadata.cost_calls == []
        assert resumed.timeseries.calls == []


def test_full_dbn_decoder_rejects_magic_only_stream(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    site_packages = (
        module.WORKSPACE
        / "02. AlphaFactory"
        / "runtime"
        / "python-databento"
        / "Lib"
        / "site-packages"
    )
    monkeypatch.syspath_prepend(str(site_packages))
    bad = tmp_path / "truncated.dbn.zst"
    bad.write_bytes(b"\x28\xb5\x2f\xfdnot-a-complete-dbn-stream")

    with pytest.raises(module.AcquisitionError, match="full-stream validation failed"):
        module.validate_dbn_file(bad)


def test_output_root_must_stay_on_d_data_shelf() -> None:
    module = load_module()

    with pytest.raises(module.AcquisitionError, match="must be on D"):
        module.ensure_output_root(Path(r"C:\\temp\\cme6e"))


def test_download_public_api_enforces_d_root(tmp_path: Path) -> None:
    module = load_module()
    client = FakeClient()

    with pytest.raises(module.AcquisitionError, match="must be on D"):
        module.download_windows(
            client=client,
            plan=tiny_plan(module),
            approved_max_usd=1.0,
            root=tmp_path,
        )

    assert client.metadata.cost_calls == []
    assert client.timeseries.calls == []
