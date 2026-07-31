from __future__ import annotations

import copy
import importlib.util
import hashlib
import json
import shutil
import subprocess
import threading
import traceback
from datetime import timedelta
from pathlib import Path

import pytest


PACKAGE = Path(__file__).resolve().parents[1]
MODULE_PATH = PACKAGE / "research" / "acquire_event_cme6e_mbp10.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "acquire_event_cme6e_mbp10", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _v14_exact_registry_prefix(module) -> bytes:
    lines = module._registry_snapshot().splitlines(keepends=True)
    return b"".join(lines[: module.V14_REGISTRY_PREFIX_ROWS])


class FakeMetadata:
    def __init__(self) -> None:
        self.get_cost_calls: list[dict] = []
        self.get_billable_size_calls: list[dict] = []
        self.get_dataset_range_calls: list[dict] = []

    def get_dataset_range(self, **kwargs):
        self.get_dataset_range_calls.append(kwargs)
        return {"start": "2010-06-06T00:00:00.000000000Z", "end": "2026-07-28T00:00:00.000000000Z"}

    def get_cost(self, **kwargs):
        self.get_cost_calls.append(kwargs)
        return 0.000001

    def get_billable_size(self, **kwargs):
        self.get_billable_size_calls.append(kwargs)
        return 1024


class StrictSdkMetadata(FakeMetadata):
    def get_cost(
        self, *, dataset, schema, symbols, stype_in, start, end, mode
    ):
        call = {
            "dataset": dataset,
            "schema": schema,
            "symbols": symbols,
            "stype_in": stype_in,
            "start": start,
            "end": end,
            "mode": mode,
        }
        self.get_cost_calls.append(call)
        return 0.000001

    def get_billable_size(
        self, *, dataset, schema, symbols, stype_in, start, end
    ):
        call = {
            "dataset": dataset,
            "schema": schema,
            "symbols": symbols,
            "stype_in": stype_in,
            "start": start,
            "end": end,
        }
        self.get_billable_size_calls.append(call)
        return 1024


class FakeSymbology:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "result": {"6E.v.0": [["2019-01-01", "2023-01-01", "12345"]]},
            "partial": [],
            "not_found": [],
        }


class FakeClient:
    def __init__(self) -> None:
        self.metadata = FakeMetadata()
        self.symbology = FakeSymbology()
        self.timeseries = FakeTimeseries()


class FakeTimeseries:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def get_range(self, **kwargs):
        self.calls.append(kwargs)
        raise AssertionError("a paid time-series call was not expected")


class FakeWritingTimeseries:
    def __init__(self, *, fail_on_call: int | None = None) -> None:
        self.calls: list[dict] = []
        self.fail_on_call = fail_on_call

    def get_range(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail_on_call == len(self.calls):
            raise RuntimeError("ambiguous fake paid failure")
        output = Path(kwargs["path"])
        output.write_bytes(
            f"FAKE_DBN|{kwargs['start']}|{kwargs['end']}".encode("utf-8")
        )


class FakeHttpError(Exception):
    def __init__(self, status: int) -> None:
        super().__init__(f"HTTP {status}")
        self.http_status = status


class FakeSecretHttpError(FakeHttpError):
    def __init__(self, status: int, secret: str) -> None:
        super().__init__(status)
        self.args = (f"HTTP {status} api_key={secret}",)


@pytest.mark.parametrize(
    "error",
    [
        FakeHttpError(429),
        FakeHttpError(502),
        FakeHttpError(503),
        FakeHttpError(504),
        TimeoutError("timeout"),
        ConnectionError("connection"),
    ],
)
def test_v8_transient_error_classifier_is_exact(error: Exception) -> None:
    module = load_module()
    assert module._is_transient_free_metadata_error(error) is True


@pytest.mark.parametrize("method", ["timeseries.get_range", "batch.submit_job"])
def test_v8_retry_wrapper_rejects_paid_and_batch_methods(method: str) -> None:
    module = load_module()
    called = {"value": False}

    def operation():
        called["value"] = True

    with pytest.raises(module.AcquisitionError, match="retry is not authorized"):
        module._call_free_metadata_with_retry(method, operation)
    assert called["value"] is False


def test_bound_contract_and_hypothesis_row_are_byte_exact() -> None:
    module = load_module()
    report = module.verify_bound_contract(require_global_registry=True)

    assert report["all_match"] is True
    assert report["hypothesis_row_sha256"] == module.HYPOTHESIS_ROW_SHA256
    assert report["registry_sha256"] == hashlib.sha256(
        module._registry_snapshot()
    ).hexdigest().upper()
    assert report["registry_prefix_sha256"] == module.V14_REGISTRY_PREFIX_SHA256
    assert report["clock_sha256"] == module.CLOCK_SHA256
    assert report["task_packet_v4_sha256"] == module.TASK_PACKET_V4_SHA256
    assert report["task_packet_v5_sha256"] == module.TASK_PACKET_V5_SHA256
    assert report["task_packet_v6_sha256"] == module.TASK_PACKET_V6_SHA256
    assert report["task_packet_v7_sha256"] == module.TASK_PACKET_V7_SHA256
    assert report["task_packet_v8_sha256"] == module.TASK_PACKET_V8_SHA256
    assert report["task_packet_v9_sha256"] == module.TASK_PACKET_V9_SHA256


def test_v7_origin_and_probe_transition_remain_bound_in_v9_history() -> None:
    module = load_module()
    history = module._event_row_bindings(module._registry_snapshot())

    assert history["origin_row_sha256"] == module.ORIGIN_ROW_SHA256
    assert (
        history["probe_transition_row_sha256"]
        == module.PROBE_TRANSITION_ROW_SHA256
    )
    assert history["event_row_sha256_sequence"][:2] == [
        module.ORIGIN_ROW_SHA256,
        module.PROBE_TRANSITION_ROW_SHA256,
    ]


@pytest.mark.parametrize("mutation", ["mutated_latest", "later_event_row"])
def test_v7_mutated_or_later_event_row_is_rejected(mutation: str) -> None:
    module = load_module()
    snapshot = module._registry_snapshot()
    lines = snapshot.splitlines()
    event_rows = [
        line
        for line in lines
        if json.loads(line)["hypothesis_id"] == module.HYPOTHESIS_ID
    ]
    assert len(event_rows) == 3
    if mutation == "mutated_latest":
        changed = event_rows[1].replace(b'"state":"probe"', b'"state":"idea"')
        lines[lines.index(event_rows[1])] = changed
    else:
        lines.append(event_rows[-1])
    tampered = b"\n".join(lines) + b"\n"

    with pytest.raises(module.AcquisitionError, match="EVENT-CLOB registry history"):
        module._event_row_bindings(tampered)


def test_offline_plan_has_630_unique_identities_and_reports_overlap() -> None:
    module = load_module()
    plan = module.build_offline_plan()

    assert plan["status"] == "PLANNED_NOT_QUOTED_NOT_DOWNLOADED"
    assert len(plan["windows"]) == 630
    assert len({item["event_clock_id"] for item in plan["windows"]}) == 630
    assert plan["coverage"]["clock_identities"] == 630
    assert plan["coverage"]["overlapping_pair_count"] == 1
    assert plan["coverage"]["overlapping_pairs"] == [
        {
            "left_event_clock_id": "EVT0007",
            "right_event_clock_id": "EVT0008",
            "clock_delta_seconds": 60,
        }
    ]
    assert plan["clock"]["sha256"] == module.CLOCK_SHA256
    assert plan["paid_request_made"] is False
    assert plan["api_method_counters"]["timeseries.get_range"] == 0
    module.validate_plan(plan, require_quote=False)


def test_plan_id_is_deterministic_and_excludes_generated_timestamp() -> None:
    module = load_module()
    first = module.build_offline_plan()
    second = json.loads(json.dumps(first))
    second["generated_at_utc"] = "2099-01-01T00:00:00Z"

    assert module.plan_id(first) == module.plan_id(second) == first["plan_id"]


def test_plan_validation_fails_closed_on_duplicate_identity() -> None:
    module = load_module()
    plan = module.build_offline_plan()
    plan["windows"][1]["event_clock_id"] = plan["windows"][0]["event_clock_id"]
    plan["plan_id"] = module.plan_id(plan)

    with pytest.raises(module.AcquisitionError, match="duplicate event clock identity"):
        module.validate_plan(plan, require_quote=False)


def test_timestamp_shifted_window_is_rejected_before_any_remote_call() -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_offline_plan()
    window = plan["windows"][0]
    for field in ("event_time_utc", "start", "end"):
        shifted = module._parse_utc(window[field]) + timedelta(seconds=1)
        window[field] = module._iso_millis(shifted)
    window["filename"] = module._filename(
        window["event_clock_id"],
        module._parse_utc(window["start"]),
        module._parse_utc(window["end"]),
    )
    plan["plan_id"] = module.plan_id(plan)

    with pytest.raises(module.AcquisitionError, match="canonical frozen clock"):
        module.quote_plan(
            client=client,
            plan=plan,
            sdk_version="0.54.0",
            billable_size_authorized=True,
        )
    assert client.metadata.get_dataset_range_calls == []
    assert client.metadata.get_cost_calls == []
    assert client.metadata.get_billable_size_calls == []
    assert client.symbology.calls == []
    assert client.timeseries.calls == []


def test_v7_free_quote_records_validator_passed_append_only_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_offline_plan()
    start_binding = json.loads(json.dumps(plan["bindings"]))
    start_bytes = module.REGISTRY_PATH.read_bytes()
    end_bytes = start_bytes + b'{"record_type":"unrelated_test_append"}\n'
    end_binding = json.loads(json.dumps(start_binding))
    end_binding["registry_sha256"] = hashlib.sha256(end_bytes).hexdigest().upper()
    snapshots = iter((start_bytes, end_bytes))
    validator_results = iter(
        (
            "CANDIDATE_REGISTRY_OK rows=267 hypotheses=89",
            "CANDIDATE_REGISTRY_OK rows=268 hypotheses=90",
        )
    )

    monkeypatch.setattr(
        module,
        "verify_bound_contract",
        lambda *, require_global_registry: (
            start_binding if require_global_registry else end_binding
        ),
    )
    monkeypatch.setattr(module, "_registry_snapshot", lambda: next(snapshots))
    monkeypatch.setattr(
        module, "_validate_canonical_registry", lambda: next(validator_results)
    )
    quoted, receipt = module.quote_plan(
        client=client,
        plan=plan,
        sdk_version="0.54.0",
        billable_size_authorized=True,
    )

    boundary = quoted["registry_quote_boundary"]
    assert boundary == {
        "start_sha256": start_binding["registry_sha256"],
        "end_sha256": end_binding["registry_sha256"],
        "append_only_drift_observed": True,
    }
    assert receipt["registry_quote_boundary"] == boundary
    assert quoted["registry_validator_boundary"] == {
        "start_result": "CANDIDATE_REGISTRY_OK rows=267 hypotheses=89",
        "end_result": "CANDIDATE_REGISTRY_OK rows=268 hypotheses=90",
    }
    assert receipt["registry_validator_boundary"] == quoted["registry_validator_boundary"]
    assert receipt["timeseries_calls"] == 0
    assert receipt["paid_request_made"] is False


def test_free_quote_rejects_bound_row_drift_at_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_offline_plan()
    start_binding = json.loads(json.dumps(plan["bindings"]))

    def verify(*, require_global_registry: bool):
        if require_global_registry:
            return start_binding
        raise module.AcquisitionError("bound hypothesis row SHA mismatch")

    monkeypatch.setattr(module, "verify_bound_contract", verify)
    with pytest.raises(module.AcquisitionError, match="bound hypothesis row SHA mismatch"):
        module.quote_plan(
            client=client,
            plan=plan,
            sdk_version="0.54.0",
            billable_size_authorized=True,
        )
    assert len(client.metadata.get_cost_calls) == 630
    assert client.timeseries.calls == []


@pytest.mark.parametrize("lane", ["free_quote", "paid_download"])
def test_v7_validator_failure_stops_remote_boundary(
    lane: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()

    def fail_validator(*_args):
        raise module.AcquisitionError("canonical registry validator failed")

    monkeypatch.setattr(
        module,
        "_validate_canonical_registry",
        fail_validator,
    )
    monkeypatch.setattr(
        module,
        "_validate_canonical_registry_snapshot",
        fail_validator,
    )
    if lane == "free_quote":
        with pytest.raises(module.AcquisitionError, match="canonical registry validator failed"):
            module.build_offline_plan()
    else:
        window = {
            "event_clock_id": "EVT0001",
            "event_time_utc": "2019-01-03T15:00:00.000Z",
            "start": "2019-01-03T14:59:00.000Z",
            "end": "2019-01-03T15:01:00.000Z",
            "filename": "EVT0001_test.dbn.zst",
        }
        plan = {"plan_id": "V7_TEST_PLAN", "windows": [window]}
        monkeypatch.setattr(
            module,
            "verify_bound_contract",
            lambda *, require_global_registry: {"registry_sha256": module.REGISTRY_SHA256},
        )
        monkeypatch.setattr(module, "_require_paid_download_reopen", lambda _bindings: None)
        monkeypatch.setattr(module, "validate_plan", lambda *args, **kwargs: None)
        monkeypatch.setattr(module, "ensure_output_root", lambda root: root)
        monkeypatch.setattr(module, "build_offline_plan", lambda: {})
        monkeypatch.setattr(
            module,
            "quote_plan",
            lambda **kwargs: ({"estimated_total_usd": 0.01, "quotes": []}, {}),
        )
        monkeypatch.setattr(
            module, "validate_existing_download_manifest", lambda **kwargs: set()
        )
        with pytest.raises(module.AcquisitionError, match="canonical registry validator failed"):
            module.download_windows(
                client=client,
                metadata_client=client,
                plan=plan,
                expected_plan_id=plan["plan_id"],
                approve_max_usd=1.0,
                root=tmp_path,
                sdk_version="0.54.0",
            )
    assert client.metadata.get_dataset_range_calls == []
    assert client.metadata.get_cost_calls == []
    assert client.metadata.get_billable_size_calls == []
    assert client.symbology.calls == []
    assert client.timeseries.calls == []


def test_v8_transient_504_retries_free_billable_size_and_counts_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    client = FakeClient()
    original = client.metadata.get_billable_size
    failures = {"remaining": 1}

    def transient_once(**kwargs):
        if failures["remaining"]:
            failures["remaining"] -= 1
            client.metadata.get_billable_size_calls.append(kwargs)
            raise FakeHttpError(504)
        return original(**kwargs)

    client.metadata.get_billable_size = transient_once
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    quoted, receipt = module.quote_plan(
        client=client,
        plan=module.build_offline_plan(),
        sdk_version="0.54.0",
        billable_size_authorized=True,
    )

    assert len(quoted["quotes"]) == 630
    assert len(client.metadata.get_billable_size_calls) == 631
    assert quoted["api_method_counters"]["metadata.get_billable_size"] == 631
    assert receipt["api_method_counters"]["metadata.get_billable_size"] == 631
    assert receipt["api_method_counters"]["metadata.get_cost"] == 630
    assert client.timeseries.calls == []


def test_v8_permanent_metadata_error_fails_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    client = FakeClient()

    def permanent_auth_error(**kwargs):
        client.metadata.get_cost_calls.append(kwargs)
        raise FakeHttpError(401)

    client.metadata.get_cost = permanent_auth_error
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    with pytest.raises(module.AcquisitionError, match="metadata.get_cost failed after 1 attempt"):
        module.quote_plan(
            client=client,
            plan=module.build_offline_plan(),
            sdk_version="0.54.0",
            billable_size_authorized=True,
        )

    assert len(client.metadata.get_cost_calls) == 1
    assert client.metadata.get_billable_size_calls == []
    assert client.timeseries.calls == []


def test_v8_three_transient_failures_do_not_mutate_plan_or_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()

    def always_transient(**kwargs):
        client.metadata.get_billable_size_calls.append(kwargs)
        raise FakeHttpError(503)

    client.metadata.get_billable_size = always_transient
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    validator_result = module._validate_canonical_registry()
    monkeypatch.setattr(
        module,
        "_validate_canonical_registry",
        lambda: validator_result,
    )
    monkeypatch.setattr(module, "ensure_output_root", lambda root: root)
    monkeypatch.setattr(module, "make_client_from_local_key", lambda: (client, "fake-key"))

    class Foundation:
        @staticmethod
        def make_client(_key):
            return client

    monkeypatch.setattr(module, "_load_foundation", lambda: Foundation())
    plan = module.build_offline_plan()
    tmp_path.mkdir(parents=True, exist_ok=True)
    plan_path = tmp_path / module.PLAN_NAME
    receipt_path = tmp_path / module.QUOTE_RECEIPT_NAME
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    before = plan_path.read_bytes()

    result = module.main(
        [
            "quote",
            "--root",
            str(tmp_path),
            "--expected-plan-id",
            plan["plan_id"],
            "--quote-workers",
            "1",
        ]
    )

    assert result == 2
    assert len(client.metadata.get_cost_calls) == 1
    assert len(client.metadata.get_billable_size_calls) == 3
    assert plan_path.read_bytes() == before
    assert not receipt_path.exists()
    assert client.timeseries.calls == []


@pytest.mark.parametrize("attempts", [629, 1891])
def test_v8_free_metadata_attempt_counter_bounds_are_fail_closed(attempts: int) -> None:
    module = load_module()
    client = FakeClient()
    quoted, _ = module.quote_plan(
        client=client,
        plan=module.build_offline_plan(),
        sdk_version="0.54.0",
        billable_size_authorized=True,
    )
    quoted["api_method_counters"]["metadata.get_cost"] = attempts
    quoted["plan_id"] = module.plan_id(quoted)

    with pytest.raises(module.AcquisitionError, match="metadata.get_cost attempt counter"):
        module.validate_plan(quoted, require_quote=True)


def test_v9_exact_three_row_history_exposes_parked_latest_row() -> None:
    module = load_module()
    history = module._event_row_bindings(module._registry_snapshot())

    assert history["event_row_sha256_sequence"] == list(
        module.BOUND_EVENT_ROW_SHA256_SEQUENCE
    )
    assert history["latest_row_sha256"] == module.LATEST_ROW_SHA256
    assert history["latest_state"] == "parked"
    assert history["latest_verdict"] == "PARK_SOURCE_PAYMENT_AUTHORITY_UNMET"
    assert history["event_row_count"] == 3


@pytest.mark.parametrize("mutation", ["mutated_latest", "reordered", "later_event_row"])
def test_v9_mutated_reordered_or_later_event_history_is_rejected(mutation: str) -> None:
    module = load_module()
    lines = module._registry_snapshot().splitlines()
    indexes = [
        index
        for index, line in enumerate(lines)
        if json.loads(line)["hypothesis_id"] == module.HYPOTHESIS_ID
    ]
    assert len(indexes) == 3
    if mutation == "mutated_latest":
        lines[indexes[-1]] = lines[indexes[-1]].replace(
            b'"state":"parked"', b'"state":"probe"'
        )
    elif mutation == "reordered":
        lines[indexes[-2]], lines[indexes[-1]] = (
            lines[indexes[-1]],
            lines[indexes[-2]],
        )
    else:
        lines.append(lines[indexes[-1]])
    tampered = b"\n".join(lines) + b"\n"

    with pytest.raises(module.AcquisitionError, match="EVENT-CLOB registry history"):
        module._event_row_bindings(tampered)


def test_v9_parked_state_blocks_download_before_any_remote_call(tmp_path: Path) -> None:
    module = load_module()
    client = FakeClient()

    with pytest.raises(module.AcquisitionError, match="payment authority unmet"):
        module.download_windows(
            client=client,
            metadata_client=client,
            plan={},
            expected_plan_id="UNUSED",
            approve_max_usd=1.0,
            root=tmp_path,
            sdk_version="0.54.0",
        )

    assert client.metadata.get_dataset_range_calls == []
    assert client.metadata.get_cost_calls == []
    assert client.metadata.get_billable_size_calls == []
    assert client.symbology.calls == []
    assert client.timeseries.calls == []
    assert list(tmp_path.iterdir()) == []


def test_v9_immutable_free_quote_evidence_and_children_are_exact() -> None:
    module = load_module()
    evidence = module.verify_immutable_quote_evidence()

    assert evidence["manifest_sha256"] == module.QUOTE_EVIDENCE_MANIFEST_SHA256
    assert evidence["plan_id"] == "F8CC58697DAF05713DCD4A4D0DDF1AA3DE9684A3DF646AE9C8F424F645851BDB"
    assert evidence["child_sha256"] == module.QUOTE_EVIDENCE_CHILD_SHA256


def test_design_segments_v12_exact_successor_bindings_and_parent_controls() -> None:
    module = load_module()
    report = module.verify_design_segments_bound_contract(require_global_registry=True)

    assert report["all_match"] is True
    assert report["successor_row_sha256_sequence"] == list(
        module.DESIGN_SUCCESSOR_ROW_SHA256_SEQUENCE
    )
    assert report["latest_state"] == "parked"
    assert report["latest_verdict"] == "PARK_DESIGN_SOURCE_PAYMENT_AUTHORITY_UNMET"
    assert report["prereg_sha256"] == module.DESIGN_PREREG_SHA256
    assert report["task_packet_v10_sha256"] == module.TASK_PACKET_V10_SHA256
    assert report["clock_sha256"] == module.CLOCK_SHA256
    assert report["parent_v9"]["latest_state"] == "parked"
    assert report["parent_v9"]["immutable_quote_evidence"]["manifest_sha256"] == (
        module.QUOTE_EVIDENCE_MANIFEST_SHA256
    )


def test_design_segments_v11_binds_failure_evidence_and_exact_retry_policy() -> None:
    module = load_module()
    report = module.verify_design_segments_bound_contract(require_global_registry=True)
    plan = module.build_design_segments_plan()

    assert report["task_packet_v11_sha256"] == module.TASK_PACKET_V11_SHA256
    assert report["failure_evidence_sha256"] == module.DESIGN_FAILURE_EVIDENCE_SHA256
    assert plan["bindings"]["task_packet_v11_sha256"] == module.TASK_PACKET_V11_SHA256
    assert plan["bindings"]["failure_evidence_sha256"] == (
        module.DESIGN_FAILURE_EVIDENCE_SHA256
    )
    assert plan["free_metadata_retry_policy"] == {
        "methods": ["metadata.get_cost", "metadata.get_billable_size"],
        "transient_http_statuses": [429, 500, 502, 503, 504],
        "transient_exception_kinds": ["timeout", "connection"],
        "max_attempts_per_call": 3,
        "backoff_seconds": [0.25, 1.0],
        "dataset_range_and_symbology_single_attempt": True,
        "paid_and_batch_retry_authorized": False,
    }


def test_v12_exact_three_row_parked_bindings_and_offline_plan() -> None:
    module = load_module()
    report = module.verify_design_segments_bound_contract(require_global_registry=True)
    plan = module.build_design_segments_plan()
    rebuilt = module.build_design_segments_plan()

    assert report["successor_row_sha256_sequence"] == [
        "B352E22DE06889E3FDF139A7857CEAECB123944E42CDF1564C9CE3B54AF01F3D",
        "8B88B70C26060FF8A2A13F506990ADE3C6A27C2860C5618E51FBD77115B109CF",
        "AAE0F493502C13EB8C75C9105C83C6B6F325043D59BBB120075063401C907C45",
    ]
    assert report["successor_row_count"] == 3
    assert report["latest_state"] == "parked"
    assert report["latest_verdict"] == "PARK_DESIGN_SOURCE_PAYMENT_AUTHORITY_UNMET"
    assert report["task_packet_v12_sha256"] == module.TASK_PACKET_V12_SHA256
    assert report["immutable_design_quote_evidence"]["manifest_sha256"] == (
        module.DESIGN_QUOTE_EVIDENCE_MANIFEST_SHA256
    )
    assert plan["bindings"] == report
    assert plan["bindings"]["latest_state"] == "parked"
    assert plan["bindings"]["task_packet_v12_sha256"] == module.TASK_PACKET_V12_SHA256
    assert plan["status"] == "PLANNED_DESIGN_SEGMENTS_NOT_QUOTED_NOT_DOWNLOADED"
    assert len(plan["requests"]) == 658
    assert plan["quotes"] == []
    assert all(value == 0 for value in plan["api_method_counters"].values())
    assert plan["timeseries_calls"] == 0
    assert plan["paid_request_made"] is False
    assert plan["plan_id"] == rebuilt["plan_id"]


def test_v12_immutable_design_quote_evidence_reconciles_historical_v11() -> None:
    module = load_module()
    evidence = module.verify_immutable_design_quote_evidence()

    assert evidence["manifest_sha256"] == module.DESIGN_QUOTE_EVIDENCE_MANIFEST_SHA256
    assert evidence["plan_id"] == module.DESIGN_QUOTE_EVIDENCE_PLAN_ID
    assert evidence["child_sha256"] == module.DESIGN_QUOTE_EVIDENCE_CHILD_SHA256
    assert evidence["quote"] == {
        "requests": 658,
        "estimated_total_usd": 3.141317501659,
        "estimated_total_billable_bytes": 6745927968,
        "metadata_get_cost_attempts": 658,
        "metadata_get_billable_size_attempts": 658,
        "timeseries_calls": 0,
        "paid_request_made": False,
    }
    assert evidence["historical_tool_sha256"] == (
        "AAE2FFCFDBEEA06CB759D6F36458EF36194073D942BDA2A94342A45FC2574BDE"
    )
    assert evidence["historical_registry_sha256"] == (
        "824EA0DB704443B12D6FA52C0E3F2E1F549BEAE9BB07F98A1958AC7F72E6FDE0"
    )
    assert evidence["parent_quote_evidence_manifest_sha256"] == (
        module.QUOTE_EVIDENCE_MANIFEST_SHA256
    )
    assert evidence["historical_tool_sha256"] != module.sha256_file(
        Path(module.__file__).resolve()
    )


@pytest.mark.parametrize(
    "mutation",
    ["manifest", "child", "extra", "missing", "path_escape"],
)
def test_v12_immutable_design_quote_evidence_rejects_filesystem_drift(
    mutation: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    copied = tmp_path / "FREE_QUOTE_DEDDE7F2"
    shutil.copytree(module.DESIGN_QUOTE_EVIDENCE_ROOT, copied)
    manifest_path = copied / "manifest.json"

    if mutation == "manifest":
        manifest_path.write_bytes(manifest_path.read_bytes() + b" ")
    elif mutation == "child":
        (copied / "storage_assessment.json").write_bytes(b"mutated")
    elif mutation == "extra":
        (copied / "unexpected.bin").write_bytes(b"unexpected")
    elif mutation == "missing":
        (copied / "quote_receipt.json").unlink()
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"][0]["path"] = "../escaped-plan.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        monkeypatch.setattr(
            module,
            "DESIGN_QUOTE_EVIDENCE_MANIFEST_SHA256",
            module.sha256_file(manifest_path),
        )

    with pytest.raises(module.AcquisitionError):
        module.verify_immutable_design_quote_evidence(root=copied)


def test_v12_immutable_design_quote_evidence_rejects_parent_f8_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    parent = module.verify_immutable_quote_evidence()
    parent["manifest_sha256"] = "0" * 64
    monkeypatch.setattr(module, "verify_immutable_quote_evidence", lambda: parent)

    with pytest.raises(module.AcquisitionError, match="parent F8"):
        module.verify_immutable_design_quote_evidence()


@pytest.mark.parametrize("action", ["design-quote", "design-download"])
def test_v12_parked_cli_blocks_before_root_key_client_lock_or_remote(
    action: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    calls = {"root": 0, "client": 0, "lock": 0}

    def poison_root(_root):
        calls["root"] += 1
        raise AssertionError("active design root accessed after V12 parked state")

    def poison_client():
        calls["client"] += 1
        raise AssertionError("Databento client created after V12 parked state")

    def poison_lock(_root):
        calls["lock"] += 1
        raise AssertionError("paid lock accessed after V12 parked state")

    monkeypatch.setattr(module, "ensure_design_segments_output_root", poison_root)
    monkeypatch.setattr(module, "make_client_from_local_key", poison_client)
    monkeypatch.setattr(module, "exclusive_paid_download_lock", poison_lock)

    result = module.main([action])

    assert result == 2
    assert calls == {"root": 0, "client": 0, "lock": 0}


def test_v12_core_quote_plan_blocks_before_validator_factory_or_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_design_segments_plan()
    calls = {"validator": 0, "factory": 0}
    original_validator = module._validate_canonical_registry

    def audited_validator():
        calls["validator"] += 1
        return original_validator()

    def audited_factory():
        calls["factory"] += 1
        return client

    monkeypatch.setattr(module, "_validate_canonical_registry", audited_validator)

    with pytest.raises(module.AcquisitionError, match="payment authority unmet"):
        module.quote_plan(
            client=client,
            plan=plan,
            sdk_version="0.54.0",
            billable_size_authorized=True,
            client_factory=audited_factory,
            workers=1,
        )

    assert calls == {"validator": 0, "factory": 0}
    assert client.metadata.get_dataset_range_calls == []
    assert client.metadata.get_cost_calls == []
    assert client.metadata.get_billable_size_calls == []
    assert client.symbology.calls == []
    assert client.timeseries.calls == []


def test_v13_exact_owner_authority_is_bound() -> None:
    module = load_module()
    report = module.verify_design_segments_bound_contract(require_global_registry=True)

    assert report["task_packet_v13_sha256"] == module.TASK_PACKET_V13_SHA256
    assert report["owner_authorization"] == {
        "verbatim_sha256": "F77ECBE11D07A84E3B1A1112FC93AB7992720815EBC1B9C34ED874A86E4A89A0",
        "authorization_basis_plan_id": module.DESIGN_QUOTE_EVIDENCE_PLAN_ID,
        "approved_max_usd": 3.5,
    }
    assert report["immutable_design_quote_evidence"]["plan_id"] == (
        module.DESIGN_QUOTE_EVIDENCE_PLAN_ID
    )


def test_v14_exact_prefix_and_unrelated_append_are_validator_gated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    baseline = _v14_exact_registry_prefix(module)
    monkeypatch.setattr(
        module,
        "_validate_canonical_registry_snapshot",
        lambda _snapshot: "CANDIDATE_REGISTRY_OK rows=272 hypotheses=90",
    )
    exact = module._verify_v14_registry_authority(snapshot=baseline)
    assert exact["prefix_sha256"] == module.V14_REGISTRY_PREFIX_SHA256
    assert exact["appended_row_count"] == 0

    unrelated = {
        "record_type": "hypothesis_state",
        "hypothesis_id": "HYP-SYNTHETIC-UNRELATED-001",
        "state": "idea",
        "verdict": "UNRELATED_APPEND_TEST",
    }
    appended = baseline + (
        json.dumps(unrelated, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    monkeypatch.setattr(
        module,
        "_validate_canonical_registry_snapshot",
        lambda _snapshot: "CANDIDATE_REGISTRY_OK rows=273 hypotheses=91",
    )
    allowed = module._verify_v14_registry_authority(snapshot=appended)
    assert allowed["appended_row_count"] == 1
    assert allowed["registry_sha256"] == hashlib.sha256(appended).hexdigest().upper()


@pytest.mark.parametrize("mutation", ["truncate", "rewrite", "reorder", "newline"])
def test_v14_registry_prefix_byte_drift_fails_closed(
    mutation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    baseline = _v14_exact_registry_prefix(module)
    lines = baseline.splitlines(keepends=True)
    if mutation == "truncate":
        changed = b"".join(lines[:-1])
    elif mutation == "rewrite":
        changed = baseline.replace(b'"state":"parked"', b'"state":"idea"', 1)
    elif mutation == "reorder":
        lines[0], lines[1] = lines[1], lines[0]
        changed = b"".join(lines)
    else:
        changed = baseline.rstrip(b"\n")
    monkeypatch.setattr(
        module,
        "_validate_canonical_registry_snapshot",
        lambda _snapshot: "CANDIDATE_REGISTRY_OK rows=272 hypotheses=90",
    )

    with pytest.raises(module.AcquisitionError, match="prefix"):
        module._verify_v14_registry_authority(snapshot=changed)


@pytest.mark.parametrize(
    "token",
    [
        "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002",
        "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001",
        "EA_EventCLOBPersistence",
        "cme_6e_event_clob_design_segments",
        "DEDDE7F292738C16A200C59903F7839C85B728818805AA09D46D3E7F188E0C16",
    ],
)
def test_v14_related_append_is_rejected_even_when_validator_reports_pass(
    token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    baseline = _v14_exact_registry_prefix(module)
    appended = baseline + (
        json.dumps(
            {"hypothesis_id": "HYP-SYNTHETIC-001", "note": token},
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    monkeypatch.setattr(
        module,
        "_validate_canonical_registry_snapshot",
        lambda _snapshot: "CANDIDATE_REGISTRY_OK rows=273 hypotheses=91",
    )

    with pytest.raises(module.AcquisitionError, match="conflict token|EventCLOB"):
        module._verify_v14_registry_authority(snapshot=appended)


@pytest.mark.parametrize(
    "encoded_row",
    [
        br'{"hypothesis_id":"HYP-SYNTHETIC-ESCAPED-001","state":"idea","note":"\u0065vent\u005fclob"}',
        br'{"hypothesis_id":"HYP-SYNTHETIC-ESCAPED-001","state":"idea","\u0065vent\u005fclob":"related"}',
        br'{"hypothesis_id":"HYP-SYNTHETIC-ESCAPED-001","state":"idea","nested":{"items":["safe",{"marker":"\u0065vent\u005fclob"}]}}',
    ],
    ids=["escaped-value", "escaped-key", "nested-array-object"],
)
def test_v14_decoded_semantic_conflict_is_rejected_without_cache_or_remote(
    encoded_row: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    baseline = _v14_exact_registry_prefix(module)
    appended = baseline + encoded_row + b"\n"
    appended_sha256 = hashlib.sha256(appended).hexdigest().upper()
    module._V14_VALIDATOR_PASS_BY_REGISTRY_SHA256.clear()
    monkeypatch.setattr(
        module,
        "_validate_canonical_registry_snapshot",
        lambda _snapshot: "CANDIDATE_REGISTRY_OK rows=273 hypotheses=91",
    )

    with pytest.raises(module.AcquisitionError, match="conflict token|EventCLOB"):
        module._verify_v14_registry_authority(snapshot=appended)

    assert appended_sha256 not in module._V14_VALIDATOR_PASS_BY_REGISTRY_SHA256
    assert client.metadata.get_dataset_range_calls == []
    assert client.metadata.get_cost_calls == []
    assert client.metadata.get_billable_size_calls == []
    assert client.symbology.calls == []
    assert client.timeseries.calls == []


def test_v14_decoded_semantic_scan_allows_unrelated_nested_append(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    baseline = _v14_exact_registry_prefix(module)
    encoded_row = (
        br'{"hypothesis_id":"HYP-SYNTHETIC-ESCAPED-UNRELATED-001",'
        br'"state":"idea","\u006eested":{"items":["independent",{"tag":"safe"}]}}'
    )
    appended = baseline + encoded_row + b"\n"
    appended_sha256 = hashlib.sha256(appended).hexdigest().upper()
    module._V14_VALIDATOR_PASS_BY_REGISTRY_SHA256.clear()
    monkeypatch.setattr(
        module,
        "_validate_canonical_registry_snapshot",
        lambda _snapshot: "CANDIDATE_REGISTRY_OK rows=273 hypotheses=91",
    )

    authority = module._verify_v14_registry_authority(snapshot=appended)

    assert authority["registry_sha256"] == appended_sha256
    assert appended_sha256 in module._V14_VALIDATOR_PASS_BY_REGISTRY_SHA256


def test_v14_validator_failure_blocks_registry_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()

    def fail_validator(_snapshot):
        raise module.AcquisitionError("canonical registry validator failed")

    monkeypatch.setattr(
        module, "_validate_canonical_registry_snapshot", fail_validator
    )
    with pytest.raises(module.AcquisitionError, match="validator failed"):
        module._verify_v14_registry_authority(snapshot=module._registry_snapshot())


def test_v14_schema_invalid_snapshot_cannot_borrow_live_registry_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    client = FakeClient()
    live_valid = module.REGISTRY_PATH.read_bytes()
    baseline = _v14_exact_registry_prefix(module)
    invalid_row = {
        "hypothesis_id": "HYP-SYNTHETIC-SNAPSHOT-RACE-001",
        "state": "idea",
        "verdict": "SCHEMA_INVALID_SNAPSHOT_MUST_NOT_BORROW_LIVE_PASS",
    }
    invalid_snapshot = baseline + (
        json.dumps(invalid_row, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    assert len(invalid_snapshot.splitlines()) == len(live_valid.splitlines())
    assert len(
        {
            json.loads(raw.decode("utf-8"))["hypothesis_id"]
            for raw in invalid_snapshot.splitlines()
        }
    ) == len(
        {
            json.loads(raw.decode("utf-8"))["hypothesis_id"]
            for raw in live_valid.splitlines()
        }
    )
    monkeypatch.setattr(module, "_registry_snapshot", lambda: live_valid)
    module._V14_VALIDATOR_PASS_BY_REGISTRY_SHA256.clear()
    invalid_sha256 = hashlib.sha256(invalid_snapshot).hexdigest().upper()

    with pytest.raises(module.AcquisitionError, match="canonical registry validator failed"):
        module._verify_v14_registry_authority(snapshot=invalid_snapshot)

    assert invalid_sha256 not in module._V14_VALIDATOR_PASS_BY_REGISTRY_SHA256
    assert client.metadata.get_dataset_range_calls == []
    assert client.metadata.get_cost_calls == []
    assert client.metadata.get_billable_size_calls == []
    assert client.symbology.calls == []
    assert client.timeseries.calls == []


@pytest.mark.parametrize("related", [False, True])
def test_v14_concurrent_append_between_quote_and_paid_seam_is_rechecked(
    related: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    offline = module.build_design_segments_plan()
    baseline = module._registry_snapshot()
    row = {
        "hypothesis_id": "HYP-SYNTHETIC-UNRELATED-002",
        "state": "idea",
        "note": "event_clob" if related else "independent synthetic lane",
    }
    appended = baseline + (
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    state = {"snapshot": baseline}
    monkeypatch.setattr(module, "_registry_snapshot", lambda: state["snapshot"])

    def validator_result(snapshot: bytes) -> str:
        rows = [raw for raw in snapshot.splitlines() if raw]
        hypotheses = {
            json.loads(raw.decode("utf-8"))["hypothesis_id"] for raw in rows
        }
        return (
            f"CANDIDATE_REGISTRY_OK rows={len(rows)} "
            f"hypotheses={len(hypotheses)}"
        )

    monkeypatch.setattr(
        module,
        "_validate_canonical_registry",
        lambda: validator_result(state["snapshot"]),
    )
    monkeypatch.setattr(
        module, "_validate_canonical_registry_snapshot", validator_result
    )
    monkeypatch.setattr(
        module, "ensure_design_segments_output_root", lambda _root: tmp_path.resolve()
    )
    monkeypatch.setattr(
        module.shutil,
        "disk_usage",
        lambda _root: type("Usage", (), {"free": 10**15})(),
    )
    original_quote = module._quote_plan_after_authority_check

    def quote_then_append(**kwargs):
        result = original_quote(**kwargs)
        state["snapshot"] = appended
        return result

    monkeypatch.setattr(module, "_quote_plan_after_authority_check", quote_then_append)
    client = FakeClient()
    client.timeseries = FakeWritingTimeseries(fail_on_call=1)

    expected = "conflict token" if related else "in_flight preserved"
    with pytest.raises(module.AcquisitionError, match=expected):
        module.design_acquire(
            client=client,
            metadata_client=client,
            plan=offline,
            authorization_basis_plan_id=module.DESIGN_QUOTE_EVIDENCE_PLAN_ID,
            approve_max_usd=3.5,
            root=module.DESIGN_SEGMENTS_ROOT,
            sdk_version="0.54.0",
        )

    assert len(client.timeseries.calls) == (0 if related else 1)


def _write_v13_partial_resume_fixture(module, root: Path):
    offline = module.build_design_segments_plan()
    quote_client = FakeClient()
    old_plan, old_receipt = module._quote_plan_after_authority_check(
        client=quote_client,
        plan=offline,
        sdk_version="0.54.0",
        billable_size_authorized=True,
        workers=1,
    )
    old_plan["quotes"][0]["estimated_usd"] = 3.4
    old_plan["estimated_total_usd"] = sum(
        item["estimated_usd"] for item in old_plan["quotes"]
    )
    old_plan["plan_id"] = module.plan_id(old_plan)
    old_receipt["plan_id"] = old_plan["plan_id"]
    old_receipt["quotes"] = copy.deepcopy(old_plan["quotes"])
    old_receipt["estimated_total_usd"] = old_plan["estimated_total_usd"]
    old_receipt["receipt_id"] = module.plan_id(old_receipt)
    module.validate_quote_receipt(old_receipt, old_plan)
    root.mkdir(parents=True, exist_ok=True)
    (root / module.LIVE_REQUOTE_PLAN_NAME).write_text(
        json.dumps(old_plan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / module.LIVE_REQUOTE_RECEIPT_NAME).write_text(
        json.dumps(old_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    request = old_plan["requests"][0]
    output = root / "raw" / request["filename"]
    output.parent.mkdir()
    output.write_bytes(b"FAKE_DBN|HISTORICAL")
    manifest = {
        "schema_version": module.DOWNLOAD_SCHEMA_VERSION,
        "status": "DOWNLOADING_SERIAL",
        "profile": module.DESIGN_SEGMENTS_PROFILE,
        "hypothesis_id": module.DESIGN_HYPOTHESIS_ID,
        "authorization_basis_plan_id": module.DESIGN_QUOTE_EVIDENCE_PLAN_ID,
        "approved_max_usd": 3.5,
        "plan_id": old_plan["plan_id"],
        "live_plan_id": old_plan["plan_id"],
        "live_estimated_total_usd": old_plan["estimated_total_usd"],
        "live_estimated_total_billable_bytes": old_plan[
            "estimated_total_billable_bytes"
        ],
        "downloads": [
            {
                **request,
                "bytes": output.stat().st_size,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest().upper(),
                "records": 1,
                "source_empty": False,
                "charged_empty_evidence": None,
                "estimated_usd": old_plan["quotes"][0]["estimated_usd"],
                "billable_bytes": old_plan["quotes"][0]["billable_bytes"],
            }
        ],
        "in_flight": None,
        "paid_requests_completed": 1,
        "timeseries_calls": 1,
        "paid_request_made": True,
        "outcome_fields_used": False,
        "price_data_read": False,
        "validation_source_sealed": True,
    }
    (root / module.DOWNLOAD_MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return offline, old_plan, old_receipt, manifest


@pytest.mark.parametrize(
    "mutation",
    [
        "basis",
        "ceiling_higher",
        "ceiling_lower",
        "ceiling_nan",
        "ceiling_infinity",
        "root",
        "requests",
    ],
)
def test_v13_direct_design_acquire_rejects_authority_drift_before_client_or_root(
    mutation: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_design_segments_plan()
    basis = module.DESIGN_QUOTE_EVIDENCE_PLAN_ID
    ceiling = 3.5
    root = module.DESIGN_SEGMENTS_ROOT
    if mutation == "basis":
        basis = "0" * 64
    elif mutation == "ceiling_higher":
        ceiling = 3.5000001
    elif mutation == "ceiling_lower":
        ceiling = 3.49
    elif mutation == "ceiling_nan":
        ceiling = float("nan")
    elif mutation == "ceiling_infinity":
        ceiling = float("inf")
    elif mutation == "root":
        root = tmp_path
    else:
        plan["requests"] = list(reversed(plan["requests"]))
        plan["plan_id"] = module.plan_id(plan)

    root_calls = {"count": 0}

    def poison_root(_root):
        root_calls["count"] += 1
        raise AssertionError("root was touched before exact V13 authority")

    monkeypatch.setattr(module, "ensure_design_segments_output_root", poison_root)

    with pytest.raises(module.AcquisitionError):
        module.design_acquire(
            client=client,
            metadata_client=client,
            plan=plan,
            authorization_basis_plan_id=basis,
            approve_max_usd=ceiling,
            root=root,
            sdk_version="0.54.0",
        )

    assert root_calls["count"] == 0
    assert client.metadata.get_cost_calls == []
    assert client.metadata.get_billable_size_calls == []
    assert client.timeseries.calls == []


@pytest.mark.parametrize("mutation", ["missing_v13", "mutated_owner"])
def test_v13_packet_or_owner_drift_blocks_before_root_and_remote(
    mutation: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_design_segments_plan()
    if mutation == "missing_v13":
        monkeypatch.setattr(module, "TASK_PACKET_V13_PATH", tmp_path / "missing-v13.json")
    else:
        original_load_json = module._load_json

        def mutated_load_json(path):
            payload = original_load_json(path)
            if Path(path).resolve() == module.TASK_PACKET_V13_PATH.resolve():
                payload = copy.deepcopy(payload)
                payload["owner_authorization"]["verbatim"] += " MUTATED"
            return payload

        monkeypatch.setattr(module, "_load_json", mutated_load_json)
    root_calls = {"count": 0}

    def poison_root(_root):
        root_calls["count"] += 1
        raise AssertionError("root touched despite invalid V13 authority")

    monkeypatch.setattr(module, "ensure_design_segments_output_root", poison_root)

    with pytest.raises(module.AcquisitionError):
        module.design_acquire(
            client=client,
            metadata_client=client,
            plan=plan,
            authorization_basis_plan_id=module.DESIGN_QUOTE_EVIDENCE_PLAN_ID,
            approve_max_usd=3.5,
            root=module.DESIGN_SEGMENTS_ROOT,
            sdk_version="0.54.0",
        )

    assert root_calls["count"] == 0
    assert client.metadata.get_cost_calls == []
    assert client.metadata.get_billable_size_calls == []
    assert client.timeseries.calls == []


@pytest.mark.skipif(
    not hasattr(Path, "is_junction"),
    reason="requires pathlib junction detection",
)
def test_v13_raw_junction_is_rejected_before_manifest_metadata_or_external_touch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_design_segments_plan()
    approved_root = tmp_path / "approved"
    outside = tmp_path / "outside"
    approved_root.mkdir()
    outside.mkdir()
    sentinel = outside / "sentinel.bin"
    sentinel.write_bytes(b"DO-NOT-TOUCH")
    raw_root = approved_root / "raw"
    created = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(raw_root), str(outside)],
        check=False,
        capture_output=True,
        text=True,
    )
    if created.returncode != 0:
        pytest.skip(f"cannot create Windows junction: {created.stderr or created.stdout}")
    assert raw_root.is_junction()
    monkeypatch.setattr(
        module,
        "ensure_design_segments_output_root",
        lambda _root: approved_root.resolve(),
    )

    try:
        with pytest.raises(module.AcquisitionError, match="reparse|junction"):
            module.design_acquire(
                client=client,
                metadata_client=client,
                plan=plan,
                authorization_basis_plan_id=module.DESIGN_QUOTE_EVIDENCE_PLAN_ID,
                approve_max_usd=3.5,
                root=module.DESIGN_SEGMENTS_ROOT,
                sdk_version="0.54.0",
            )
    finally:
        if raw_root.is_junction():
            raw_root.rmdir()

    assert sentinel.read_bytes() == b"DO-NOT-TOUCH"
    assert sorted(path.name for path in outside.iterdir()) == ["sentinel.bin"]
    assert not (approved_root / module.DOWNLOAD_MANIFEST_NAME).exists()
    assert not (approved_root / module.LIVE_REQUOTE_PLAN_NAME).exists()
    assert client.metadata.get_dataset_range_calls == []
    assert client.metadata.get_cost_calls == []
    assert client.metadata.get_billable_size_calls == []
    assert client.symbology.calls == []
    assert client.timeseries.calls == []


@pytest.mark.parametrize("failure", ["ceiling", "capacity"])
def test_v13_live_requote_or_capacity_block_writes_no_paid_receipt(
    failure: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_design_segments_plan()
    if failure == "ceiling":
        def expensive_cost(**kwargs):
            client.metadata.get_cost_calls.append(kwargs)
            return 0.01

        client.metadata.get_cost = expensive_cost
    monkeypatch.setattr(
        module, "ensure_design_segments_output_root", lambda _root: tmp_path.resolve()
    )
    free_bytes = 0 if failure == "capacity" else 10**15
    monkeypatch.setattr(
        module.shutil,
        "disk_usage",
        lambda _root: type("Usage", (), {"free": free_bytes})(),
    )

    with pytest.raises(module.AcquisitionError, match=failure):
        module.design_acquire(
            client=client,
            metadata_client=client,
            plan=plan,
            authorization_basis_plan_id=module.DESIGN_QUOTE_EVIDENCE_PLAN_ID,
            approve_max_usd=3.5,
            root=module.DESIGN_SEGMENTS_ROOT,
            sdk_version="0.54.0",
        )

    blocker = json.loads(
        (tmp_path / module.ACQUISITION_AUTHORITY_RECEIPT_NAME).read_text(
            encoding="utf-8"
        )
    )
    assert blocker["status"].startswith("BLOCKED_")
    assert blocker["timeseries_calls"] == 0
    assert blocker["paid_request_made"] is False
    assert client.timeseries.calls == []


def test_v13_successful_fake_design_campaign_is_658_request_id_serial_and_strict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    client.timeseries = FakeWritingTimeseries()
    plan = module.build_design_segments_plan()
    monkeypatch.setattr(
        module, "ensure_design_segments_output_root", lambda _root: tmp_path.resolve()
    )
    monkeypatch.setattr(
        module.shutil,
        "disk_usage",
        lambda _root: type("Usage", (), {"free": 10**15})(),
    )

    class Foundation:
        @staticmethod
        def write_json_atomic(path, payload):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        @staticmethod
        def validate_dbn_file(path, allow_zero=False):
            assert allow_zero is True
            assert Path(path).read_bytes().startswith(b"FAKE_DBN|")
            return 1

    monkeypatch.setattr(module, "_load_foundation", lambda: Foundation())

    manifest = module.design_acquire(
        client=client,
        metadata_client=client,
        plan=plan,
        authorization_basis_plan_id=module.DESIGN_QUOTE_EVIDENCE_PLAN_ID,
        approve_max_usd=3.5,
        root=module.DESIGN_SEGMENTS_ROOT,
        sdk_version="0.54.0",
    )

    assert manifest["status"] == "DOWNLOADED_FULL_DBN_VALIDATION_PASS"
    assert manifest["paid_requests_completed"] == 658
    assert len(client.timeseries.calls) == 658
    assert len({item["request_id"] for item in manifest["downloads"]}) == 658
    assert len({item["event_clock_id"] for item in manifest["downloads"]}) == 329
    assert manifest["in_flight"] is None
    assert manifest["outcome_fields_used"] is False
    assert manifest["price_data_read"] is False
    live_plan = json.loads(
        (tmp_path / module.LIVE_REQUOTE_PLAN_NAME).read_text(encoding="utf-8")
    )
    validated = module.validate_existing_download_manifest(
        manifest=manifest,
        plan=live_plan,
        root=tmp_path,
        dbn_validator=Foundation.validate_dbn_file,
        require_complete=True,
    )
    assert len(validated) == 658

    duplicate = copy.deepcopy(manifest)
    duplicate["downloads"][1]["request_id"] = duplicate["downloads"][0][
        "request_id"
    ]
    with pytest.raises(module.AcquisitionError, match="duplicate canonical identity"):
        module.validate_existing_download_manifest(
            manifest=duplicate,
            plan=live_plan,
            root=tmp_path,
            dbn_validator=Foundation.validate_dbn_file,
        )

    record_drift = copy.deepcopy(manifest)
    record_drift["downloads"][0]["records"] = 2
    with pytest.raises(module.AcquisitionError, match="record count mismatch"):
        module.validate_existing_download_manifest(
            manifest=record_drift,
            plan=live_plan,
            root=tmp_path,
            dbn_validator=Foundation.validate_dbn_file,
        )

    path_escape = copy.deepcopy(manifest)
    path_escape["downloads"][0]["filename"] = "../escaped.dbn.zst"
    with pytest.raises(module.AcquisitionError):
        module.validate_existing_download_manifest(
            manifest=path_escape,
            plan=live_plan,
            root=tmp_path,
            dbn_validator=Foundation.validate_dbn_file,
        )

    first_output = tmp_path / "raw" / manifest["downloads"][0]["filename"]
    original_bytes = first_output.read_bytes()
    first_output.write_bytes(original_bytes + b"DRIFT")
    with pytest.raises(module.AcquisitionError, match="byte count mismatch"):
        module.validate_existing_download_manifest(
            manifest=manifest,
            plan=live_plan,
            root=tmp_path,
            dbn_validator=Foundation.validate_dbn_file,
        )
    first_output.write_bytes(original_bytes)

    partial = tmp_path / "raw" / "unmanifested.dbn.zst.partial"
    partial.write_bytes(b"partial")
    with pytest.raises(module.AcquisitionError, match="do not reconcile"):
        module.validate_existing_download_manifest(
            manifest=manifest,
            plan=live_plan,
            root=tmp_path,
            dbn_validator=Foundation.validate_dbn_file,
        )
    partial.unlink()

    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda path: True if path == first_output else original_is_symlink(path),
    )
    with pytest.raises(module.AcquisitionError, match="DBN file is missing|reparse point"):
        module.validate_existing_download_manifest(
            manifest=manifest,
            plan=live_plan,
            root=tmp_path,
            dbn_validator=Foundation.validate_dbn_file,
        )
    monkeypatch.setattr(Path, "is_symlink", original_is_symlink)

    authority = json.loads(
        (tmp_path / module.ACQUISITION_AUTHORITY_RECEIPT_NAME).read_text(
            encoding="utf-8"
        )
    )
    assert authority["status"] == "DESIGN_ACQUISITION_COMPLETE_AUTHORITY_RECONCILED"
    assert authority["download_manifest_sha256"] == module.sha256_file(
        tmp_path / module.DOWNLOAD_MANIFEST_NAME
    )


def test_v13_unresolved_design_in_flight_blocks_all_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    client.timeseries = FakeWritingTimeseries(fail_on_call=1)
    plan = module.build_design_segments_plan()
    monkeypatch.setattr(
        module, "ensure_design_segments_output_root", lambda _root: tmp_path.resolve()
    )
    monkeypatch.setattr(
        module.shutil,
        "disk_usage",
        lambda _root: type("Usage", (), {"free": 10**15})(),
    )

    with pytest.raises(module.AcquisitionError, match="in_flight preserved"):
        module.design_acquire(
            client=client,
            metadata_client=client,
            plan=plan,
            authorization_basis_plan_id=module.DESIGN_QUOTE_EVIDENCE_PLAN_ID,
            approve_max_usd=3.5,
            root=module.DESIGN_SEGMENTS_ROOT,
            sdk_version="0.54.0",
        )
    metadata_attempts = (
        len(client.metadata.get_cost_calls),
        len(client.metadata.get_billable_size_calls),
    )
    assert len(client.timeseries.calls) == 1

    with pytest.raises(module.AcquisitionError, match="manual reconciliation"):
        module.design_acquire(
            client=client,
            metadata_client=client,
            plan=plan,
            authorization_basis_plan_id=module.DESIGN_QUOTE_EVIDENCE_PLAN_ID,
            approve_max_usd=3.5,
            root=module.DESIGN_SEGMENTS_ROOT,
            sdk_version="0.54.0",
        )

    assert len(client.timeseries.calls) == 1
    assert (
        len(client.metadata.get_cost_calls),
        len(client.metadata.get_billable_size_calls),
    ) == metadata_attempts


def test_v13_revalidates_authority_after_quote_before_first_paid_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_design_segments_plan()
    monkeypatch.setattr(
        module, "ensure_design_segments_output_root", lambda _root: tmp_path.resolve()
    )
    checks = {"count": 0}
    original_verify = module._verify_design_acquisition_authority

    def verify(**kwargs):
        checks["count"] += 1
        if checks["count"] == 2:
            raise module.AcquisitionError("post-quote V13 authority drift")
        return original_verify(**kwargs)

    monkeypatch.setattr(module, "_verify_design_acquisition_authority", verify)

    with pytest.raises(module.AcquisitionError, match="post-quote V13 authority drift"):
        module.design_acquire(
            client=client,
            metadata_client=client,
            plan=plan,
            authorization_basis_plan_id=module.DESIGN_QUOTE_EVIDENCE_PLAN_ID,
            approve_max_usd=3.5,
            root=module.DESIGN_SEGMENTS_ROOT,
            sdk_version="0.54.0",
        )

    assert checks["count"] == 2
    assert client.timeseries.calls == []


@pytest.mark.parametrize("drift", ["authority", "capacity"])
def test_v13_revalidates_after_manifest_scan_immediately_before_first_paid_call(
    drift: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    client.timeseries = FakeWritingTimeseries(fail_on_call=1)
    plan = module.build_design_segments_plan()
    monkeypatch.setattr(
        module, "ensure_design_segments_output_root", lambda _root: tmp_path.resolve()
    )
    scan = {"complete": False}
    original_validate = module.validate_existing_download_manifest

    def validate_then_drift(**kwargs):
        result = original_validate(**kwargs)
        scan["complete"] = True
        return result

    monkeypatch.setattr(module, "validate_existing_download_manifest", validate_then_drift)
    original_verify = module._verify_design_acquisition_authority

    def verify(**kwargs):
        if drift == "authority" and scan["complete"]:
            raise module.AcquisitionError("post-manifest V13 authority drift")
        return original_verify(**kwargs)

    monkeypatch.setattr(module, "_verify_design_acquisition_authority", verify)
    monkeypatch.setattr(
        module.shutil,
        "disk_usage",
        lambda _root: type(
            "Usage", (), {"free": 0 if drift == "capacity" and scan["complete"] else 10**15}
        )(),
    )

    expected = "post-manifest V13 authority drift|capacity failure"
    with pytest.raises(module.AcquisitionError, match=expected):
        module.design_acquire(
            client=client,
            metadata_client=client,
            plan=plan,
            authorization_basis_plan_id=module.DESIGN_QUOTE_EVIDENCE_PLAN_ID,
            approve_max_usd=3.5,
            root=module.DESIGN_SEGMENTS_ROOT,
            sdk_version="0.54.0",
        )

    manifest = json.loads(
        (tmp_path / module.DOWNLOAD_MANIFEST_NAME).read_text(encoding="utf-8")
    )
    assert manifest["in_flight"] is None
    assert manifest["timeseries_calls"] == 0
    assert manifest["paid_request_made"] is False
    assert client.timeseries.calls == []


@pytest.mark.skipif(
    not hasattr(Path, "is_junction"),
    reason="requires pathlib junction detection",
)
def test_v13_raw_directory_swap_to_junction_after_manifest_scan_blocks_paid_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    client.timeseries = FakeWritingTimeseries(fail_on_call=1)
    plan = module.build_design_segments_plan()
    approved_root = tmp_path / "approved"
    outside = tmp_path / "outside"
    approved_root.mkdir()
    outside.mkdir()
    sentinel = outside / "sentinel.bin"
    sentinel.write_bytes(b"DO-NOT-TOUCH")
    monkeypatch.setattr(
        module,
        "ensure_design_segments_output_root",
        lambda _root: approved_root.resolve(),
    )
    monkeypatch.setattr(
        module.shutil,
        "disk_usage",
        lambda _root: type("Usage", (), {"free": 10**15})(),
    )
    original_validate = module.validate_existing_download_manifest
    swapped = {"done": False}

    def validate_then_swap(**kwargs):
        result = original_validate(**kwargs)
        if not swapped["done"]:
            raw_root = approved_root / "raw"
            raw_root.rmdir()
            created = subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(raw_root), str(outside)],
                check=False,
                capture_output=True,
                text=True,
            )
            if created.returncode != 0:
                pytest.skip(
                    f"cannot create Windows junction: {created.stderr or created.stdout}"
                )
            assert raw_root.is_junction()
            swapped["done"] = True
        return result

    monkeypatch.setattr(module, "validate_existing_download_manifest", validate_then_swap)
    raw_root = approved_root / "raw"
    try:
        with pytest.raises(module.AcquisitionError, match="reparse|junction"):
            module.design_acquire(
                client=client,
                metadata_client=client,
                plan=plan,
                authorization_basis_plan_id=module.DESIGN_QUOTE_EVIDENCE_PLAN_ID,
                approve_max_usd=3.5,
                root=module.DESIGN_SEGMENTS_ROOT,
                sdk_version="0.54.0",
            )
    finally:
        if raw_root.is_junction():
            raw_root.rmdir()

    manifest = json.loads(
        (approved_root / module.DOWNLOAD_MANIFEST_NAME).read_text(encoding="utf-8")
    )
    assert manifest["in_flight"] is None
    assert manifest["timeseries_calls"] == 0
    assert client.timeseries.calls == []
    assert sentinel.read_bytes() == b"DO-NOT-TOUCH"
    assert sorted(path.name for path in outside.iterdir()) == ["sentinel.bin"]


@pytest.mark.skipif(
    not hasattr(Path, "is_junction"),
    reason="requires pathlib junction detection",
)
def test_v13_raw_directory_swap_after_journal_is_rechecked_before_paid_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    client.timeseries = FakeWritingTimeseries(fail_on_call=1)
    plan = module.build_design_segments_plan()
    approved_root = tmp_path / "approved"
    outside = tmp_path / "outside"
    approved_root.mkdir()
    outside.mkdir()
    sentinel = outside / "sentinel.bin"
    sentinel.write_bytes(b"DO-NOT-TOUCH")
    monkeypatch.setattr(
        module,
        "ensure_design_segments_output_root",
        lambda _root: approved_root.resolve(),
    )
    monkeypatch.setattr(
        module.shutil,
        "disk_usage",
        lambda _root: type("Usage", (), {"free": 10**15})(),
    )
    original_write = module.write_json_atomic
    swapped = {"done": False}

    def write_then_swap(path, payload):
        original_write(path, payload)
        if (
            Path(path).name == module.DOWNLOAD_MANIFEST_NAME
            and payload.get("in_flight") is not None
            and not swapped["done"]
        ):
            raw_root = approved_root / "raw"
            raw_root.rmdir()
            created = subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(raw_root), str(outside)],
                check=False,
                capture_output=True,
                text=True,
            )
            if created.returncode != 0:
                pytest.skip(
                    f"cannot create Windows junction: {created.stderr or created.stdout}"
                )
            assert raw_root.is_junction()
            swapped["done"] = True

    monkeypatch.setattr(module, "write_json_atomic", write_then_swap)
    raw_root = approved_root / "raw"
    try:
        with pytest.raises(module.AcquisitionError, match="reparse|junction"):
            module.design_acquire(
                client=client,
                metadata_client=client,
                plan=plan,
                authorization_basis_plan_id=module.DESIGN_QUOTE_EVIDENCE_PLAN_ID,
                approve_max_usd=3.5,
                root=module.DESIGN_SEGMENTS_ROOT,
                sdk_version="0.54.0",
            )
    finally:
        if raw_root.is_junction():
            raw_root.rmdir()

    assert client.timeseries.calls == []
    assert sentinel.read_bytes() == b"DO-NOT-TOUCH"
    assert sorted(path.name for path in outside.iterdir()) == ["sentinel.bin"]


def test_v13_resume_aggregate_ceiling_counts_completed_plus_fresh_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    root = tmp_path / "approved"
    offline, old_plan, _old_receipt, _manifest = _write_v13_partial_resume_fixture(
        module, root
    )
    client = FakeClient()
    client.timeseries = FakeWritingTimeseries(fail_on_call=1)

    def fresh_cost(**kwargs):
        client.metadata.get_cost_calls.append(kwargs)
        return 0.0003

    client.metadata.get_cost = fresh_cost
    monkeypatch.setattr(
        module, "ensure_design_segments_output_root", lambda _root: root.resolve()
    )
    monkeypatch.setattr(
        module.shutil,
        "disk_usage",
        lambda _root: type("Usage", (), {"free": 10**15})(),
    )

    class Foundation:
        @staticmethod
        def write_json_atomic(path, payload):
            Path(path).write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        @staticmethod
        def validate_dbn_file(path, allow_zero=False):
            assert allow_zero is True
            return 1

    monkeypatch.setattr(module, "_load_foundation", lambda: Foundation())

    with pytest.raises(module.AcquisitionError, match="aggregate ceiling"):
        module.design_acquire(
            client=client,
            metadata_client=client,
            plan=offline,
            authorization_basis_plan_id=module.DESIGN_QUOTE_EVIDENCE_PLAN_ID,
            approve_max_usd=3.5,
            root=module.DESIGN_SEGMENTS_ROOT,
            sdk_version="0.54.0",
        )

    receipt = json.loads(
        (root / module.ACQUISITION_AUTHORITY_RECEIPT_NAME).read_text(encoding="utf-8")
    )
    assert receipt["status"].endswith("BEFORE_NEXT_PAID_CALL")
    assert receipt["timeseries_calls"] == 1
    assert receipt["paid_request_made"] is True
    assert receipt["authorized_aggregate_usd"] == pytest.approx(3.5971)
    assert client.timeseries.calls == []
    resumed_manifest = json.loads(
        (root / module.DOWNLOAD_MANIFEST_NAME).read_text(encoding="utf-8")
    )
    assert resumed_manifest["downloads"][0]["quote_basis_plan_id"] == old_plan[
        "plan_id"
    ]
    assert resumed_manifest["quote_basis_history"]


@pytest.mark.parametrize("drift", ["completed_estimate", "historical_receipt"])
def test_v13_resume_historical_quote_drift_blocks_before_fresh_metadata(
    drift: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    root = tmp_path / "approved"
    offline, _old_plan, _old_receipt, manifest = _write_v13_partial_resume_fixture(
        module, root
    )
    if drift == "completed_estimate":
        manifest["downloads"][0]["estimated_usd"] += 0.01
        (root / module.DOWNLOAD_MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    else:
        receipt_path = root / module.LIVE_REQUOTE_RECEIPT_NAME
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["quotes"][0]["estimated_usd"] += 0.01
        receipt_path.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    client = FakeClient()
    monkeypatch.setattr(
        module, "ensure_design_segments_output_root", lambda _root: root.resolve()
    )

    with pytest.raises(module.AcquisitionError, match="historical|quote evidence"):
        module.design_acquire(
            client=client,
            metadata_client=client,
            plan=offline,
            authorization_basis_plan_id=module.DESIGN_QUOTE_EVIDENCE_PLAN_ID,
            approve_max_usd=3.5,
            root=module.DESIGN_SEGMENTS_ROOT,
            sdk_version="0.54.0",
        )

    assert client.metadata.get_cost_calls == []
    assert client.metadata.get_billable_size_calls == []
    assert client.timeseries.calls == []


def _run_v13_clean_interruption(
    *, module, root: Path, offline: dict, cost: float, completed_target: int
):
    client = FakeClient()
    client.timeseries = FakeWritingTimeseries()

    def quoted_cost(**kwargs):
        client.metadata.get_cost_calls.append(kwargs)
        return cost

    client.metadata.get_cost = quoted_cost
    original_write = module.write_json_atomic

    class CleanInterruption(RuntimeError):
        pass

    def write_then_interrupt(path, payload):
        original_write(path, payload)
        if (
            Path(path).name == module.DOWNLOAD_MANIFEST_NAME
            and payload.get("in_flight") is None
            and payload.get("paid_requests_completed") == completed_target
        ):
            raise CleanInterruption(f"clean stop after {completed_target}")

    module.write_json_atomic = write_then_interrupt
    try:
        with pytest.raises(CleanInterruption, match="clean stop"):
            module.design_acquire(
                client=client,
                metadata_client=client,
                plan=offline,
                authorization_basis_plan_id=module.DESIGN_QUOTE_EVIDENCE_PLAN_ID,
                approve_max_usd=3.5,
                root=module.DESIGN_SEGMENTS_ROOT,
                sdk_version="0.54.0",
            )
    finally:
        module.write_json_atomic = original_write
    return client


def _prepare_v13_two_clean_resumes(
    module, root: Path, monkeypatch: pytest.MonkeyPatch
):
    offline = module.build_design_segments_plan()
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        module, "ensure_design_segments_output_root", lambda _root: root.resolve()
    )
    monkeypatch.setattr(
        module.shutil,
        "disk_usage",
        lambda _root: type("Usage", (), {"free": 10**15})(),
    )

    class Foundation:
        @staticmethod
        def write_json_atomic(path, payload):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        @staticmethod
        def validate_dbn_file(path, allow_zero=False):
            assert allow_zero is True
            assert Path(path).read_bytes().startswith(b"FAKE_DBN|")
            return 1

    monkeypatch.setattr(module, "_load_foundation", lambda: Foundation())
    first = _run_v13_clean_interruption(
        module=module, root=root, offline=offline, cost=0.0010, completed_target=1
    )
    first_manifest = json.loads(
        (root / module.DOWNLOAD_MANIFEST_NAME).read_text(encoding="utf-8")
    )
    basis_a = first_manifest["downloads"][0]["quote_basis_plan_id"]
    second = _run_v13_clean_interruption(
        module=module, root=root, offline=offline, cost=0.0011, completed_target=2
    )
    second_manifest = json.loads(
        (root / module.DOWNLOAD_MANIFEST_NAME).read_text(encoding="utf-8")
    )
    basis_b = second_manifest["downloads"][1]["quote_basis_plan_id"]
    return offline, first, second, second_manifest, basis_a, basis_b


def test_v13_three_invocations_preserve_a_and_b_quote_basis_across_two_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    root = tmp_path / "approved"
    offline, _first, _second, before_third, basis_a, basis_b = (
        _prepare_v13_two_clean_resumes(module, root, monkeypatch)
    )
    assert basis_a != basis_b
    frozen_downloads = copy.deepcopy(before_third["downloads"])
    client = FakeClient()
    client.timeseries = FakeWritingTimeseries(fail_on_call=1)

    def third_cost(**kwargs):
        client.metadata.get_cost_calls.append(kwargs)
        return 0.0012

    client.metadata.get_cost = third_cost
    with pytest.raises(module.AcquisitionError, match="in_flight preserved"):
        module.design_acquire(
            client=client,
            metadata_client=client,
            plan=offline,
            authorization_basis_plan_id=module.DESIGN_QUOTE_EVIDENCE_PLAN_ID,
            approve_max_usd=3.5,
            root=module.DESIGN_SEGMENTS_ROOT,
            sdk_version="0.54.0",
        )

    after_third = json.loads(
        (root / module.DOWNLOAD_MANIFEST_NAME).read_text(encoding="utf-8")
    )
    assert after_third["downloads"] == frozen_downloads
    assert after_third["downloads"][0]["quote_basis_plan_id"] == basis_a
    assert after_third["downloads"][1]["quote_basis_plan_id"] == basis_b
    history_ids = {item["plan_id"] for item in after_third["quote_basis_history"]}
    assert {basis_a, basis_b}.issubset(history_ids)
    assert module._completed_incurred_estimate(after_third) == pytest.approx(0.0021)
    assert len(client.timeseries.calls) == 1


@pytest.mark.parametrize("history_index", [0, 1])
def test_v13_multi_resume_rejects_mutated_a_or_b_quote_history(
    history_index: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    root = tmp_path / "approved"
    _offline, _first, _second, manifest, _basis_a, _basis_b = (
        _prepare_v13_two_clean_resumes(module, root, monkeypatch)
    )
    manifest["quote_basis_history"][history_index]["plan_json_utf8"] += " "

    with pytest.raises(module.AcquisitionError, match="embedded SHA mismatch"):
        module._completed_incurred_estimate(manifest)


@pytest.mark.parametrize(
    ("method", "expected_attempts"),
    [
        ("metadata.get_cost", {"metadata.get_cost": 2, "metadata.get_billable_size": 1}),
        (
            "metadata.get_billable_size",
            {"metadata.get_cost": 1, "metadata.get_billable_size": 2},
        ),
    ],
)
def test_v11_http_500_retries_only_the_failing_free_metadata_call(
    method: str,
    expected_attempts: dict[str, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    client = FakeClient()
    window = module.build_design_segments_plan()["requests"][0]
    metadata_method = method.rsplit(".", 1)[-1]
    original = getattr(client.metadata, metadata_method)
    failures = {"remaining": 1}

    def fail_once(**kwargs):
        if failures["remaining"]:
            failures["remaining"] -= 1
            getattr(client.metadata, f"{metadata_method}_calls").append(kwargs)
            raise FakeHttpError(500)
        return original(**kwargs)

    setattr(client.metadata, metadata_method, fail_once)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)

    quotes, attempts = module._quote_windows(
        client, [window], client_factory=None, workers=1
    )

    assert len(quotes) == 1
    assert attempts == expected_attempts
    assert len(client.metadata.get_cost_calls) == expected_attempts["metadata.get_cost"]
    assert len(client.metadata.get_billable_size_calls) == expected_attempts[
        "metadata.get_billable_size"
    ]
    assert client.timeseries.calls == []


@pytest.mark.parametrize(
    "method", ["metadata.get_cost", "metadata.get_billable_size"]
)
def test_v11_three_http_500_failures_report_exact_request_context_without_secret(
    method: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    client = FakeClient()
    window = module.build_design_segments_plan()["requests"][0]
    metadata_method = method.rsplit(".", 1)[-1]

    def always_500(**kwargs):
        getattr(client.metadata, f"{metadata_method}_calls").append(kwargs)
        raise FakeSecretHttpError(500, "V11_SUPER_SECRET")

    setattr(client.metadata, metadata_method, always_500)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)

    with pytest.raises(module.AcquisitionError) as captured:
        module._quote_windows(client, [window], client_factory=None, workers=1)

    message = str(captured.value)
    assert f"{method} failed after 3 attempts" in message
    assert f"method={method}" in message
    assert "request_id=EVT0001_PRE" in message
    assert "event_clock_id=EVT0001" in message
    assert "segment=PRE" in message
    assert "start=2019-01-03T14:59:00.000Z" in message
    assert "end=2019-01-03T14:59:45.000Z" in message
    assert "attempt_count=3" in message
    assert "http_status=500" in message
    assert "disposition=transient_retry_budget_exhausted" in message
    assert "V11_SUPER_SECRET" not in message
    assert "V11_SUPER_SECRET" not in "".join(
        traceback.format_exception(captured.value)
    )
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None
    assert module._exception_chain(captured.value) == [captured.value]
    assert all(
        "V11_SUPER_SECRET" not in repr(item)
        for item in module._exception_chain(captured.value)
    )
    expected_cost_attempts = 3 if method == "metadata.get_cost" else 1
    expected_size_attempts = 3 if method == "metadata.get_billable_size" else 0
    assert len(client.metadata.get_cost_calls) == expected_cost_attempts
    assert len(client.metadata.get_billable_size_calls) == expected_size_attempts
    assert client.timeseries.calls == []


@pytest.mark.parametrize(
    "method", ["metadata.get_cost", "metadata.get_billable_size"]
)
@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_v11_strict_4xx_metadata_errors_fail_fast_with_one_attempt(
    method: str, status: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    window = module.build_design_segments_plan()["requests"][0]
    metadata_method = method.rsplit(".", 1)[-1]
    secret = f"V11_{status}_{metadata_method}_SECRET"

    def permanent_error(**kwargs):
        getattr(client.metadata, f"{metadata_method}_calls").append(kwargs)
        raise FakeSecretHttpError(status, secret)

    setattr(client.metadata, metadata_method, permanent_error)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)

    with pytest.raises(module.AcquisitionError) as captured:
        module._quote_windows(client, [window], client_factory=None, workers=1)

    message = str(captured.value)
    assert module._is_transient_free_metadata_error(FakeHttpError(status)) is False
    assert f"http_status={status}" in message
    assert "attempt_count=1" in message
    assert "disposition=non_transient_fail_fast" in message
    assert secret not in message
    assert secret not in "".join(traceback.format_exception(captured.value))
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None
    assert module._exception_chain(captured.value) == [captured.value]
    assert all(secret not in repr(item) for item in module._exception_chain(captured.value))
    assert len(client.metadata.get_cost_calls) == 1
    expected_size_attempts = 1 if method == "metadata.get_billable_size" else 0
    assert len(client.metadata.get_billable_size_calls) == expected_size_attempts
    assert client.timeseries.calls == []


@pytest.mark.parametrize("mutation", ["missing_v11", "mutated_failure_evidence"])
def test_v11_binding_failure_blocks_before_client_creation_or_remote_access(
    mutation: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    plan = module.build_design_segments_plan()
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / module.PLAN_NAME).write_text(
        json.dumps(plan, indent=2) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        module, "ensure_design_segments_output_root", lambda _root: tmp_path.resolve()
    )

    if mutation == "missing_v11":
        monkeypatch.setattr(
            module, "TASK_PACKET_V11_PATH", tmp_path / "missing-v11.json", raising=False
        )
    else:
        failure_path = getattr(
            module,
            "DESIGN_FAILURE_EVIDENCE_PATH",
            PACKAGE
            / "research"
            / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_SOURCE_QUOTE_ATTEMPT_01_FAILURE.json",
        )
        original_sha256_file = module.sha256_file
        monkeypatch.setattr(
            module,
            "sha256_file",
            lambda path: (
                "0" * 64
                if Path(path).resolve() == Path(failure_path).resolve()
                else original_sha256_file(path)
            ),
        )

    client_creations = {"count": 0}

    def poison_client_creation():
        client_creations["count"] += 1
        raise AssertionError("client creation crossed a failed V11 binding")

    monkeypatch.setattr(module, "make_client_from_local_key", poison_client_creation)

    result = module.main(
        [
            "design-quote",
            "--root",
            str(tmp_path),
            "--expected-plan-id",
            plan["plan_id"],
            "--quote-workers",
            "1",
        ]
    )

    assert result == 2
    assert client_creations["count"] == 0


def test_v11_failed_design_quote_preserves_offline_plan_and_leaves_no_residue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_design_segments_plan()
    tmp_path.mkdir(parents=True, exist_ok=True)
    plan_path = tmp_path / module.PLAN_NAME
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    before = plan_path.read_bytes()

    def always_500(**kwargs):
        client.metadata.get_cost_calls.append(kwargs)
        raise FakeHttpError(500)

    client.metadata.get_cost = always_500
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    with pytest.raises(module.AcquisitionError, match="failed after 3 attempts"):
        module._quote_plan_after_authority_check(
            client=client,
            plan=plan,
            sdk_version="0.54.0",
            billable_size_authorized=True,
            workers=1,
        )

    assert len(client.metadata.get_cost_calls) == 3
    assert client.metadata.get_billable_size_calls == []
    assert plan_path.read_bytes() == before
    assert set(path.name for path in tmp_path.iterdir()) == {module.PLAN_NAME}
    assert client.timeseries.calls == []


@pytest.mark.parametrize("mutation", ["mutated", "reordered", "missing", "later"])
def test_design_segments_v12_successor_history_rejects_drift(mutation: str) -> None:
    module = load_module()
    lines = module._registry_snapshot().splitlines()
    indexes = [
        index
        for index, line in enumerate(lines)
        if json.loads(line)["hypothesis_id"] == module.DESIGN_HYPOTHESIS_ID
    ]
    assert len(indexes) == 3
    if mutation == "mutated":
        lines[indexes[-1]] = lines[indexes[-1]].replace(
            b'"state":"parked"', b'"state":"idea"'
        )
    elif mutation == "reordered":
        lines[indexes[-2]], lines[indexes[-1]] = lines[indexes[-1]], lines[indexes[-2]]
    elif mutation == "missing":
        lines.pop(indexes[-1])
    else:
        lines.append(lines[indexes[-1]])

    with pytest.raises(module.AcquisitionError, match="successor registry history"):
        module._design_successor_row_bindings(b"\n".join(lines) + b"\n")


def test_design_segments_plan_exact_population_duration_and_endpoints() -> None:
    module = load_module()
    plan = module.build_design_segments_plan()
    requests = plan["requests"]

    assert plan["profile"] == module.DESIGN_SEGMENTS_PROFILE
    assert plan["hypothesis_id"] == module.DESIGN_HYPOTHESIS_ID
    assert plan["coverage"] == {
        "design_clock_count": 329,
        "validation_clock_count": 0,
        "validation_request_count": 0,
        "request_identity_count": 658,
        "requested_duration_seconds": 19740,
        "request_overlap_count": 0,
        "parent_clock_overlap_count": 1,
    }
    assert len(requests) == 658
    assert len({item["request_id"] for item in requests}) == 658
    assert requests[0] == {
        "request_id": "EVT0001_PRE",
        "event_clock_id": "EVT0001",
        "segment": "PRE",
        "event_time_utc": "2019-01-03T15:00:00.000Z",
        "start": "2019-01-03T14:59:00.000Z",
        "end": "2019-01-03T14:59:45.000Z",
        "duration_seconds": 45,
        "filename": "EVT0001_PRE_20190103T145900_20190103T145945.dbn.zst",
    }
    assert requests[-1]["request_id"] == "EVT0329_LATE"
    assert requests[-1]["start"] == "2020-12-16T19:00:45.000Z"
    assert requests[-1]["end"] == "2020-12-16T19:01:00.000Z"
    module.validate_design_segments_plan(plan, require_quote=False)


def test_design_segments_requests_are_paired_half_open_and_nonoverlapping() -> None:
    module = load_module()
    plan = module.build_design_segments_plan()
    by_clock: dict[str, list[dict]] = {}
    intervals: list[tuple] = []
    for request in plan["requests"]:
        by_clock.setdefault(request["event_clock_id"], []).append(request)
        start = module._parse_utc(request["start"])
        end = module._parse_utc(request["end"])
        assert start < end
        assert start.year <= 2020 and end.year <= 2020
        intervals.append((start, end, request["request_id"]))
    assert len(by_clock) == 329
    assert all([item["segment"] for item in pair] == ["PRE", "LATE"] for pair in by_clock.values())
    intervals.sort()
    assert all(left[1] <= right[0] for left, right in zip(intervals, intervals[1:]))


def test_design_segments_rejects_noncanonical_bounds_and_wrong_roots() -> None:
    module = load_module()
    plan = module.build_design_segments_plan()
    plan["requests"][0]["end"] = "2019-01-03T15:00:00.000Z"
    plan["requests"][0]["duration_seconds"] = 60
    plan["plan_id"] = module.plan_id(plan)

    with pytest.raises(module.AcquisitionError, match="canonical half-open bounds"):
        module.validate_design_segments_plan(plan, require_quote=False)
    assert (
        module.ensure_design_segments_output_root(module.DESIGN_SEGMENTS_ROOT)
        == module.DESIGN_SEGMENTS_ROOT.resolve()
    )
    with pytest.raises(module.AcquisitionError, match="must be exactly"):
        module.ensure_design_segments_output_root(module.DEFAULT_ROOT)
    with pytest.raises(module.AcquisitionError, match="must be on D"):
        module.ensure_design_segments_output_root(Path("C:/FILE_COMMON/event_clob"))


def test_design_segments_free_quote_uses_only_exact_requests_and_audits_attempts() -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_design_segments_plan()
    quoted, receipt = module._quote_plan_after_authority_check(
        client=client,
        plan=plan,
        sdk_version="0.54.0",
        billable_size_authorized=True,
    )

    expected_args = [module._request_args(item) for item in plan["requests"]]
    assert expected_args[0] == {
        "dataset": "GLBX.MDP3",
        "schema": "mbp-10",
        "symbols": ["6E.v.0"],
        "stype_in": "continuous",
        "start": "2019-01-03T14:59:00.000Z",
        "end": "2019-01-03T14:59:45.000Z",
    }
    assert [
        {key: value for key, value in call.items() if key != "mode"}
        for call in client.metadata.get_cost_calls
    ] == expected_args
    assert client.metadata.get_billable_size_calls == expected_args
    assert client.metadata.get_dataset_range_calls == []
    assert client.symbology.calls == []
    assert len(quoted["quotes"]) == 658
    assert quoted["api_method_counters"]["metadata.get_cost"] == 658
    assert quoted["api_method_counters"]["metadata.get_billable_size"] == 658
    assert receipt["api_method_counters"] == quoted["api_method_counters"]
    assert client.timeseries.calls == []


def test_design_segments_download_fails_before_client_root_or_lock(tmp_path: Path) -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_design_segments_plan()

    with pytest.raises(module.AcquisitionError, match="payment authority unmet"):
        module.download_windows(
            client=client,
            metadata_client=client,
            plan=plan,
            expected_plan_id=plan["plan_id"],
            approve_max_usd=1.0,
            root=tmp_path,
            sdk_version="0.54.0",
        )

    assert client.metadata.get_dataset_range_calls == []
    assert client.metadata.get_cost_calls == []
    assert client.metadata.get_billable_size_calls == []
    assert client.symbology.calls == []
    assert client.timeseries.calls == []
    assert list(tmp_path.iterdir()) == []


def test_qc_design_metadata_args_match_sdk_054_signatures_exactly() -> None:
    module = load_module()
    client = FakeClient()
    client.metadata = StrictSdkMetadata()
    plan = module.build_design_segments_plan()

    quoted, receipt = module._quote_plan_after_authority_check(
        client=client,
        plan=plan,
        sdk_version="0.54.0",
        billable_size_authorized=True,
    )

    expected = [
        {
            "dataset": module.DATASET,
            "schema": module.SCHEMA,
            "symbols": [module.SYMBOL],
            "stype_in": module.STYPE_IN,
            "start": request["start"],
            "end": request["end"],
        }
        for request in plan["requests"]
    ]
    assert [
        {key: value for key, value in call.items() if key != "mode"}
        for call in client.metadata.get_cost_calls
    ] == expected
    assert client.metadata.get_billable_size_calls == expected
    assert quoted["api_method_counters"]["metadata.get_cost"] == 658
    assert receipt["api_method_counters"]["metadata.get_billable_size"] == 658


def _tamper_design_binding(plan: dict, mutation: str) -> None:
    if mutation == "task_hash":
        plan["bindings"]["task_packet_v10_sha256"] = "0" * 64
    elif mutation == "row_sequence":
        plan["bindings"]["successor_row_sha256_sequence"][0] = "0" * 64
    else:
        plan["bindings"]["parent_v9"]["immutable_quote_evidence"][
            "manifest_sha256"
        ] = "0" * 64


@pytest.mark.parametrize("mutation", ["task_hash", "row_sequence", "nested_parent"])
def test_qc_design_offline_plan_rejects_rehashed_binding_tamper(mutation: str) -> None:
    module = load_module()
    plan = module.build_design_segments_plan()
    _tamper_design_binding(plan, mutation)
    plan["plan_id"] = module.plan_id(plan)

    with pytest.raises(module.AcquisitionError, match="bindings"):
        module.validate_design_segments_plan(plan, require_quote=False)


@pytest.mark.parametrize("mutation", ["task_hash", "row_sequence", "nested_parent"])
def test_qc_design_quote_and_receipt_reject_rehashed_binding_tamper(
    mutation: str,
) -> None:
    module = load_module()
    client = FakeClient()
    quoted, receipt = module._quote_plan_after_authority_check(
        client=client,
        plan=module.build_design_segments_plan(),
        sdk_version="0.54.0",
        billable_size_authorized=True,
    )
    _tamper_design_binding(quoted, mutation)
    quoted["plan_id"] = module.plan_id(quoted)
    receipt["plan_id"] = quoted["plan_id"]
    receipt["bindings"] = json.loads(json.dumps(quoted["bindings"]))
    receipt["receipt_id"] = module.plan_id(receipt)

    with pytest.raises(module.AcquisitionError, match="bindings"):
        module.validate_design_segments_plan(quoted, require_quote=True)
    with pytest.raises(module.AcquisitionError, match="bindings"):
        module.validate_quote_receipt(receipt, quoted)


@pytest.mark.parametrize("mutation", ["status", "sdk_version", "unknown_counter"])
def test_qc_design_offline_state_contract_is_exact(mutation: str) -> None:
    module = load_module()
    plan = module.build_design_segments_plan()
    if mutation == "status":
        plan["status"] = "FORGED_OFFLINE_STATUS"
    elif mutation == "sdk_version":
        plan["databento_sdk_version"] = "0.54.0"
    else:
        plan["api_method_counters"]["metadata.unknown"] = 0
    plan["plan_id"] = module.plan_id(plan)

    with pytest.raises(module.AcquisitionError):
        module.validate_design_segments_plan(plan, require_quote=False)


@pytest.mark.parametrize("mutation", ["status", "sdk_version", "unknown_counter"])
def test_qc_design_self_consistent_plan_receipt_forgery_is_rejected(
    mutation: str,
) -> None:
    module = load_module()
    client = FakeClient()
    quoted, receipt = module._quote_plan_after_authority_check(
        client=client,
        plan=module.build_design_segments_plan(),
        sdk_version="0.54.0",
        billable_size_authorized=True,
    )
    if mutation == "status":
        quoted["status"] = "FORGED_QUOTED_STATUS"
        receipt["status"] = "FORGED_QUOTED_STATUS"
    elif mutation == "sdk_version":
        quoted["databento_sdk_version"] = "0.55.0"
        receipt["databento_sdk_version"] = "0.55.0"
    else:
        quoted["api_method_counters"]["metadata.unknown"] = 0
        receipt["api_method_counters"]["metadata.unknown"] = 0
    quoted["plan_id"] = module.plan_id(quoted)
    receipt["plan_id"] = quoted["plan_id"]
    receipt["receipt_id"] = module.plan_id(receipt)

    with pytest.raises(module.AcquisitionError):
        module.validate_design_segments_plan(quoted, require_quote=True)
    with pytest.raises(module.AcquisitionError):
        module.validate_quote_receipt(receipt, quoted)


def test_qc_design_quote_finalize_creates_storage_and_immutable_sibling_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    quoted, receipt = module._quote_plan_after_authority_check(
        client=client,
        plan=module.build_design_segments_plan(),
        sdk_version="0.54.0",
        billable_size_authorized=True,
    )
    parent_manifest_hash = module.sha256_file(module.QUOTE_EVIDENCE_MANIFEST_PATH)

    def local_atomic(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    monkeypatch.setattr(
        module, "ensure_design_segments_output_root", lambda root: root.resolve()
    )
    monkeypatch.setattr(module, "write_json_atomic", local_atomic)
    local_atomic(tmp_path / module.PLAN_NAME, quoted)
    local_atomic(tmp_path / module.DESIGN_QUOTE_RECEIPT_NAME, receipt)
    active_plan_hash = module.sha256_file(tmp_path / module.PLAN_NAME)
    active_receipt_hash = module.sha256_file(
        tmp_path / module.DESIGN_QUOTE_RECEIPT_NAME
    )

    result = module.finalize_design_quote_artifacts(
        root=tmp_path, quoted=quoted, receipt=receipt
    )

    storage_path = tmp_path / module.DESIGN_STORAGE_ASSESSMENT_NAME
    evidence_root = Path(result["evidence_root"])
    manifest = json.loads((evidence_root / "manifest.json").read_text(encoding="utf-8"))
    assert storage_path.is_file()
    assert evidence_root.parent == tmp_path / "evidence"
    assert evidence_root.name.startswith("FREE_QUOTE_")
    assert {item["path"] for item in manifest["files"]} == {
        module.PLAN_NAME,
        module.DESIGN_QUOTE_RECEIPT_NAME,
        module.DESIGN_STORAGE_ASSESSMENT_NAME,
    }
    for item in manifest["files"]:
        assert module.sha256_file(evidence_root / item["path"]) == item["sha256"]
    assert module.sha256_file(tmp_path / module.PLAN_NAME) == active_plan_hash
    assert (
        module.sha256_file(tmp_path / module.DESIGN_QUOTE_RECEIPT_NAME)
        == active_receipt_hash
    )
    assert module.sha256_file(module.QUOTE_EVIDENCE_MANIFEST_PATH) == parent_manifest_hash
    with pytest.raises(module.AcquisitionError, match="immutable design quote evidence exists"):
        module.finalize_design_quote_artifacts(
            root=tmp_path, quoted=quoted, receipt=receipt
        )


def test_qc_design_quote_allows_valid_unrelated_append_only_registry_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_design_segments_plan()
    start_binding = json.loads(json.dumps(plan["bindings"]))
    start_bytes = module.REGISTRY_PATH.read_bytes()
    appended_row = (
        b'{"hypothesis_id":"HYP-QC-UNRELATED-001",'
        b'"record_type":"unrelated_append_only_qc"}\n'
    )
    end_bytes = start_bytes + appended_row
    end_sha = hashlib.sha256(end_bytes).hexdigest().upper()
    end_binding = json.loads(json.dumps(start_binding))
    end_binding["registry_sha256"] = end_sha
    end_binding["parent_v9"]["registry_sha256"] = end_sha
    quote_state = {"completion_binding_started": False, "exact": 0}

    def verify(*, require_global_registry: bool):
        if not require_global_registry:
            quote_state["completion_binding_started"] = True
            return end_binding
        quote_state["exact"] += 1
        return (
            end_binding
            if quote_state["completion_binding_started"]
            else start_binding
        )

    def registry_snapshot() -> bytes:
        return (
            end_bytes
            if quote_state["completion_binding_started"]
            else start_bytes
        )

    def validator_result(snapshot: bytes | None = None) -> str:
        snapshot = registry_snapshot() if snapshot is None else snapshot
        rows = [raw for raw in snapshot.splitlines() if raw]
        hypotheses = {
            json.loads(raw.decode("utf-8"))["hypothesis_id"] for raw in rows
        }
        return (
            f"CANDIDATE_REGISTRY_OK rows={len(rows)} "
            f"hypotheses={len(hypotheses)}"
        )

    original_sha256_file = module.sha256_file
    monkeypatch.setattr(module, "verify_design_segments_bound_contract", verify)
    monkeypatch.setattr(module, "_registry_snapshot", registry_snapshot)
    monkeypatch.setattr(
        module,
        "sha256_file",
        lambda path: (
            start_binding["registry_sha256"]
            if Path(path) == module.REGISTRY_PATH
            else original_sha256_file(path)
        ),
    )
    monkeypatch.setattr(module, "_validate_canonical_registry", validator_result)
    monkeypatch.setattr(
        module, "_validate_canonical_registry_snapshot", validator_result
    )

    quoted, receipt = module._quote_plan_after_authority_check(
        client=client,
        plan=plan,
        sdk_version="0.54.0",
        billable_size_authorized=True,
    )

    assert quoted["registry_quote_boundary"] == {
        "start_sha256": start_binding["registry_sha256"],
        "end_sha256": end_sha,
        "append_only_drift_observed": True,
    }
    assert receipt["registry_quote_boundary"] == quoted["registry_quote_boundary"]
    assert len(quoted["quotes"]) == 658


def test_qc_design_finalize_rejects_resolved_evidence_parent_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    quoted, receipt = module._quote_plan_after_authority_check(
        client=client,
        plan=module.build_design_segments_plan(),
        sdk_version="0.54.0",
        billable_size_authorized=True,
    )

    def local_atomic(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    monkeypatch.setattr(
        module, "ensure_design_segments_output_root", lambda root: root.resolve()
    )
    monkeypatch.setattr(module, "write_json_atomic", local_atomic)
    local_atomic(tmp_path / module.PLAN_NAME, quoted)
    local_atomic(tmp_path / module.DESIGN_QUOTE_RECEIPT_NAME, receipt)
    evidence_parent = tmp_path / "evidence"
    evidence_parent.mkdir()
    outside = tmp_path.parent / f"outside_{tmp_path.name}"
    outside.mkdir(exist_ok=True)
    original_resolve = Path.resolve

    def escaped_resolve(path: Path, *args, **kwargs):
        if path == evidence_parent:
            return original_resolve(outside)
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", escaped_resolve)
    with pytest.raises(module.AcquisitionError, match="escapes exact design root"):
        module.finalize_design_quote_artifacts(
            root=tmp_path, quoted=quoted, receipt=receipt
        )
    assert list(outside.iterdir()) == []


def test_qc_design_finalize_lock_contention_preserves_shared_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    quoted, receipt = module._quote_plan_after_authority_check(
        client=client,
        plan=module.build_design_segments_plan(),
        sdk_version="0.54.0",
        billable_size_authorized=True,
    )

    def local_atomic(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    monkeypatch.setattr(
        module, "ensure_design_segments_output_root", lambda root: root.resolve()
    )
    monkeypatch.setattr(module, "write_json_atomic", local_atomic)
    local_atomic(tmp_path / module.PLAN_NAME, quoted)
    local_atomic(tmp_path / module.DESIGN_QUOTE_RECEIPT_NAME, receipt)
    storage_path = tmp_path / module.DESIGN_STORAGE_ASSESSMENT_NAME
    storage_path.write_bytes(b"winner-storage-sentinel")

    with module.exclusive_design_finalize_lock(tmp_path):
        with pytest.raises(module.AcquisitionError, match="finalize lock is already held"):
            module.finalize_design_quote_artifacts(
                root=tmp_path, quoted=quoted, receipt=receipt
            )
        assert storage_path.read_bytes() == b"winner-storage-sentinel"
        assert not (tmp_path / "evidence").exists()
    assert not (tmp_path / module.DESIGN_FINALIZE_LOCK_NAME).exists()


def test_metadata_quote_covers_every_window_without_paid_calls() -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_offline_plan()
    quoted, receipt = module.quote_plan(
        client=client,
        plan=plan,
        sdk_version="0.54.0",
        billable_size_authorized=True,
    )

    assert len(quoted["quotes"]) == 630
    assert quoted["quote_coverage"]["quoted_identities"] == 630
    assert quoted["estimated_total_usd"] == pytest.approx(0.000630)
    assert quoted["estimated_total_billable_bytes"] == 630 * 1024
    assert len(client.metadata.get_cost_calls) == 630
    assert len(client.metadata.get_billable_size_calls) == 630
    assert len(client.metadata.get_dataset_range_calls) == 1
    assert len(client.symbology.calls) == 1
    assert all(call["mode"] == "historical-streaming" for call in client.metadata.get_cost_calls)
    assert [
        {key: value for key, value in call.items() if key != "mode"}
        for call in client.metadata.get_cost_calls
    ] == client.metadata.get_billable_size_calls
    assert receipt["api_method_counters"]["metadata.get_cost"] == 630
    assert receipt["api_method_counters"]["metadata.get_billable_size"] == 630
    assert receipt["api_method_counters"]["timeseries.get_range"] == 0
    assert receipt["api_method_counters"]["batch.submit_job"] == 0
    assert receipt["api_method_counters"]["batch.download"] == 0
    assert receipt["paid_request_made"] is False
    assert receipt["quote_coverage"]["quoted_identities"] == 630
    module.validate_plan(quoted, require_quote=True)
    module.validate_quote_receipt(receipt, quoted)


@pytest.mark.parametrize("mutation", ["quote", "total"])
def test_quote_receipt_mutation_fails_exact_reconciliation(mutation: str) -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_offline_plan()
    quoted, receipt = module.quote_plan(
        client=client,
        plan=plan,
        sdk_version="0.54.0",
        billable_size_authorized=True,
    )
    if mutation == "quote":
        receipt["quotes"][0]["billable_bytes"] += 1
    else:
        receipt["estimated_total_usd"] += 0.01
    receipt["receipt_id"] = module.plan_id(receipt)

    with pytest.raises(module.AcquisitionError, match="exact reconciliation"):
        module.validate_quote_receipt(receipt, quoted)


def test_quote_without_billable_size_authority_records_bounded_blocker() -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_offline_plan()

    with pytest.raises(module.AcquisitionError, match="metadata.get_billable_size is not authorized"):
        module.quote_plan(
            client=client,
            plan=plan,
            sdk_version="0.54.0",
            billable_size_authorized=False,
        )
    assert client.metadata.get_cost_calls == []
    assert client.metadata.get_billable_size_calls == []


def test_download_authority_requires_exact_plan_id_and_positive_ceiling() -> None:
    module = load_module()
    plan = module.build_offline_plan()

    with pytest.raises(module.AcquisitionError, match="expected plan ID"):
        module.validate_download_authority(
            plan=plan,
            expected_plan_id="WRONG",
            approve_max_usd=1.0,
        )
    with pytest.raises(module.AcquisitionError, match="positive finite"):
        module.validate_download_authority(
            plan=plan,
            expected_plan_id=plan["plan_id"],
            approve_max_usd=0.0,
        )


def test_only_d_side_data_shelf_is_accepted() -> None:
    module = load_module()
    assert module.ensure_output_root(module.DEFAULT_ROOT) == module.DEFAULT_ROOT.resolve()

    with pytest.raises(module.AcquisitionError, match="must be on D"):
        module.ensure_output_root(Path("C:/tmp/event_clob"))


def test_download_requotes_and_stops_before_paid_call_above_ceiling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    offline = module.build_offline_plan()
    quoted, _ = module.quote_plan(
        client=client,
        plan=offline,
        sdk_version="0.54.0",
        billable_size_authorized=True,
    )
    monkeypatch.setattr(module, "ensure_output_root", lambda root: root)
    monkeypatch.setattr(module, "_require_paid_download_reopen", lambda _bindings: None)

    with pytest.raises(module.AcquisitionError, match="exceeds approved ceiling"):
        module.download_windows(
            client=client,
            metadata_client=client,
            plan=quoted,
            expected_plan_id=quoted["plan_id"],
            approve_max_usd=0.0001,
            root=tmp_path,
            sdk_version="0.54.0",
        )
    assert client.timeseries.calls == []


def test_unresolved_in_flight_is_never_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    offline = module.build_offline_plan()
    quoted, _ = module.quote_plan(
        client=client,
        plan=offline,
        sdk_version="0.54.0",
        billable_size_authorized=True,
    )
    manifest = {
        "schema_version": module.DOWNLOAD_SCHEMA_VERSION,
        "plan_id": quoted["plan_id"],
        "downloads": [],
        "in_flight": {"event_clock_id": "EVT0001"},
    }
    (tmp_path / module.DOWNLOAD_MANIFEST_NAME).write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    monkeypatch.setattr(module, "ensure_output_root", lambda root: root)
    monkeypatch.setattr(module, "_require_paid_download_reopen", lambda _bindings: None)

    with pytest.raises(module.AcquisitionError, match="manual reconciliation required, no retry"):
        module.download_windows(
            client=client,
            metadata_client=client,
            plan=quoted,
            expected_plan_id=quoted["plan_id"],
            approve_max_usd=1.0,
            root=tmp_path,
            sdk_version="0.54.0",
        )
    assert client.timeseries.calls == []


class FakeDbnFoundation:
    def __init__(self, records: int = 1, corrupt: bool = False) -> None:
        self.records = records
        self.corrupt = corrupt

    def validate_dbn_file(self, path: Path, allow_zero: bool = False) -> int:
        if self.corrupt:
            raise RuntimeError("corrupt DBN")
        return self.records


def _quoted_plan(module):
    client = FakeClient()
    offline = module.build_offline_plan()
    quoted, _ = module.quote_plan(
        client=client,
        plan=offline,
        sdk_version="0.54.0",
        billable_size_authorized=True,
    )
    return quoted


def _manifest_entry(module, plan, root: Path, *, records: int = 1):
    window = plan["windows"][0]
    raw_root = root / "raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    output = raw_root / window["filename"]
    output.write_bytes(b"validated-dbn-placeholder")
    entry = {
        **window,
        "bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest().upper(),
        "records": records,
        "source_empty": records == 0,
        "estimated_usd": plan["quotes"][0]["estimated_usd"],
        "billable_bytes": plan["quotes"][0]["billable_bytes"],
        "charged_empty_evidence": (
            {
                "paid_request_completed": True,
                "response_validated": True,
                "retry_prohibited": True,
            }
            if records == 0
            else None
        ),
    }
    return entry, output


def test_valid_resume_manifest_reconciles_file_and_plan(tmp_path: Path) -> None:
    module = load_module()
    plan = _quoted_plan(module)
    entry, _ = _manifest_entry(module, plan, tmp_path)
    manifest = {
        "schema_version": module.DOWNLOAD_SCHEMA_VERSION,
        "status": "DOWNLOADING_SERIAL",
        "plan_id": plan["plan_id"],
        "approved_max_usd": 1.0,
        "live_estimated_total_usd": plan["estimated_total_usd"],
        "downloads": [entry],
        "in_flight": None,
        "paid_requests_completed": 1,
        "outcome_fields_used": False,
    }

    validated = module.validate_existing_download_manifest(
        manifest=manifest,
        plan=plan,
        root=tmp_path,
        dbn_validator=FakeDbnFoundation().validate_dbn_file,
    )
    assert validated == {entry["event_clock_id"]}


@pytest.mark.parametrize(
    "invalid_state",
    ["wrong_plan", "duplicate", "missing_file", "corrupt_file", "hash_mismatch", "unvalidated_empty"],
)
def test_invalid_resume_manifest_fails_before_any_remote_call(
    invalid_state: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    plan = _quoted_plan(module)
    records = 0 if invalid_state == "unvalidated_empty" else 1
    entry, output = _manifest_entry(module, plan, tmp_path, records=records)
    manifest = {
        "schema_version": module.DOWNLOAD_SCHEMA_VERSION,
        "status": "DOWNLOADING_SERIAL",
        "plan_id": plan["plan_id"],
        "approved_max_usd": 1.0,
        "live_estimated_total_usd": plan["estimated_total_usd"],
        "downloads": [entry],
        "in_flight": None,
        "paid_requests_completed": 1,
        "outcome_fields_used": False,
    }
    foundation = FakeDbnFoundation(records=records)
    if invalid_state == "wrong_plan":
        manifest["plan_id"] = "WRONG"
    elif invalid_state == "duplicate":
        manifest["downloads"].append(dict(entry))
        manifest["paid_requests_completed"] = 2
    elif invalid_state == "missing_file":
        output.unlink()
    elif invalid_state == "corrupt_file":
        foundation.corrupt = True
    elif invalid_state == "hash_mismatch":
        output.write_bytes(b"changed-after-checkpoint")
        entry["bytes"] = output.stat().st_size
    else:
        entry["charged_empty_evidence"] = None

    (tmp_path / module.DOWNLOAD_MANIFEST_NAME).write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    client = FakeClient()
    monkeypatch.setattr(module, "ensure_output_root", lambda root: root)
    monkeypatch.setattr(module, "_load_foundation", lambda: foundation)
    monkeypatch.setattr(module, "_require_paid_download_reopen", lambda _bindings: None)

    with pytest.raises(module.AcquisitionError):
        module.download_windows(
            client=client,
            metadata_client=client,
            plan=plan,
            expected_plan_id=plan["plan_id"],
            approve_max_usd=1.0,
            root=tmp_path,
            sdk_version="0.54.0",
        )
    assert client.metadata.get_dataset_range_calls == []
    assert client.metadata.get_cost_calls == []
    assert client.metadata.get_billable_size_calls == []
    assert client.symbology.calls == []
    assert client.timeseries.calls == []


def test_paid_download_lock_allows_only_one_worker_and_releases(tmp_path: Path) -> None:
    module = load_module()
    owner_entered = threading.Event()
    release_owner = threading.Event()
    calls: list[str] = []
    errors: list[str] = []

    def owner() -> None:
        with module.exclusive_paid_download_lock(tmp_path):
            calls.append("owner_timeseries.get_range")
            owner_entered.set()
            assert release_owner.wait(timeout=5)

    def contender() -> None:
        assert owner_entered.wait(timeout=5)
        try:
            with module.exclusive_paid_download_lock(tmp_path):
                calls.append("contender_timeseries.get_range")
        except module.AcquisitionError as exc:
            errors.append(str(exc))
        finally:
            release_owner.set()

    first = threading.Thread(target=owner)
    second = threading.Thread(target=contender)
    first.start()
    second.start()
    first.join(timeout=5)
    second.join(timeout=5)

    assert calls == ["owner_timeseries.get_range"]
    assert len(errors) == 1 and "exclusive paid download lock" in errors[0]
    assert not (tmp_path / module.PAID_LOCK_NAME).exists()

    with pytest.raises(RuntimeError, match="exceptional exit"):
        with module.exclusive_paid_download_lock(tmp_path):
            raise RuntimeError("exceptional exit")
    assert not (tmp_path / module.PAID_LOCK_NAME).exists()


def test_download_rechecks_exact_global_registry_after_live_requote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    client = FakeClient()
    window = {
        "event_clock_id": "EVT0001",
        "event_time_utc": "2019-01-03T15:00:00.000Z",
        "start": "2019-01-03T14:59:00.000Z",
        "end": "2019-01-03T15:01:00.000Z",
        "filename": "EVT0001_test.dbn.zst",
    }
    plan = {"plan_id": "V6_TEST_PLAN", "windows": [window]}
    requoted = {
        "estimated_total_usd": 0.01,
        "quotes": [
            {
                "event_clock_id": "EVT0001",
                "start": window["start"],
                "end": window["end"],
                "estimated_usd": 0.01,
                "billable_bytes": 1,
            }
        ],
    }
    checks = {"count": 0}

    def verify(*, require_global_registry: bool):
        assert require_global_registry is True
        checks["count"] += 1
        if checks["count"] == 1:
            return {"registry_sha256": module.REGISTRY_SHA256}
        raise module.AcquisitionError("global registry SHA drift before paid boundary")

    monkeypatch.setattr(module, "verify_bound_contract", verify)
    monkeypatch.setattr(module, "_require_paid_download_reopen", lambda _bindings: None)
    monkeypatch.setattr(module, "validate_plan", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "ensure_output_root", lambda root: root)
    monkeypatch.setattr(module, "build_offline_plan", lambda: {})
    monkeypatch.setattr(module, "quote_plan", lambda **kwargs: (requoted, {}))
    monkeypatch.setattr(
        module, "validate_existing_download_manifest", lambda **kwargs: set()
    )

    with pytest.raises(module.AcquisitionError, match="global registry SHA drift before paid boundary"):
        module.download_windows(
            client=client,
            metadata_client=client,
            plan=plan,
            expected_plan_id=plan["plan_id"],
            approve_max_usd=1.0,
            root=tmp_path,
            sdk_version="0.54.0",
        )
    assert checks["count"] == 2
    assert client.timeseries.calls == []
    assert not (tmp_path / module.PAID_LOCK_NAME).exists()
