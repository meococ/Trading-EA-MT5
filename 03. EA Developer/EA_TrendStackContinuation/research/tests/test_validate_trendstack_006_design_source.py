import json
import sys
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_trendstack_006_design_source import (
    EXPECTED_SCHEMA,
    BuildShape,
    DesignSourceContract,
    build_design_source_for_testing,
    canonical_design_date_set_bytes,
    canonical_json,
    sha256_bytes,
)
from validate_trendstack_006_design_source import (
    InvalidDesignValidation,
    ValidationAuthority,
    ValidationShape,
    _canonical,
    _digest,
    _tree_sha,
    _validate_shard,
    validate_design_source,
    validate_design_source_for_testing,
)


ATTEMPT_ID = "HYP006-SOURCE-ATTEMPT-ABCDEF1234567890"


def _payload(day):
    rows = []
    for hour in range(12, 19):
        utc = datetime.fromisoformat(f"{day}T{hour:02d}:00:00")
        rows.append(
            {
                "time_server": utc,
                "time_utc": utc,
                "utc_offset_h": 0,
                "open": 1.1,
                "high": 1.2,
                "low": 1.0,
                "close": 1.15,
                "tick_volume": 10,
                "spread": 1,
                "real_volume": 0,
            }
        )
    sink = pa.BufferOutputStream()
    pq.write_table(pa.Table.from_pylist(rows, schema=EXPECTED_SCHEMA), sink)
    return sink.getvalue().to_pybytes()


class Capability:
    def __init__(self, payloads):
        self.payloads = dict(payloads)
        self.reads = {day: 0 for day in payloads}
        dates = tuple(sorted(payloads))
        self.selection = b"".join(
            canonical_json({"date": day, "schema_version": "trendstack_006_design_date_selection.v1"}) + b"\n"
            for day in dates
        )
        mapping = []
        public = []
        for day in dates:
            row = {
                "bytes": len(payloads[day]),
                "date": day,
                "relative_path": f"public/DESIGN/{day}/h1.parquet",
                "schema_version": "trendstack_006_selected_design_shard.v1",
                "sha256": sha256_bytes(payloads[day]),
            }
            mapping.append(row)
            public.append({**row, "rows": 7, "schema_version": "h1_splitvault_002_public_design_shard.v1"})
        self.mapping = b"".join(canonical_json(row) + b"\n" for row in mapping)
        self.public_manifest = b"".join(canonical_json(row) + b"\n" for row in public)
        self.public_receipt = canonical_json(
            {
                "collection_id": "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002",
                "design_dates": len(dates),
                "design_manifest_sha256": sha256_bytes(self.public_manifest),
                "raw_source_opens": 1,
                "research_holdout_opened": False,
                "research_validation_opened": False,
                "schema_version": "h1_splitvault_002_public_receipt.v1",
                "source_attempt_id": ATTEMPT_ID,
                "source_rows": sum(len(pq.read_table(pa.BufferReader(payload))) for payload in payloads.values()),
                "unselected_shard_opens": 0,
                "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
            }
        ) + b"\n"

    def design_dates(self):
        return tuple(sorted(self.payloads))

    def read_design_day(self, day):
        self.reads[day] += 1
        return self.payloads[day]

    def selection_manifest_bytes(self): return self.selection
    def selection_mapping_bytes(self): return self.mapping
    def public_receipt_bytes(self): return self.public_receipt
    def public_manifest_bytes(self): return self.public_manifest

    def open_count_summary(self):
        return {"raw_source_opens": 1, "selected_shard_opens": sum(self.reads.values()), "unselected_shard_opens": 0}


def _shapes(dates):
    values = (
        sha256_bytes(canonical_design_date_set_bytes(tuple(dates))),
        len(dates), 7, len(dates) * 7, dates[0], dates[-1],
    )
    return BuildShape(*values), ValidationShape(*values)


def _contract(tmp_path, cap):
    return DesignSourceContract(
        builder_tool_sha256="A" * 64,
        custodian_tool_sha256="B" * 64,
        validator_tool_sha256="C" * 64,
        custodian_test_sha256="D" * 64,
        supervisor_test_sha256="E" * 64,
        builder_test_sha256="F" * 64,
        validator_test_sha256="A" * 64,
        collection_plan_v1_sha256="B" * 64,
        collection_plan_v2_sha256="C" * 64,
        probe_plan_v1_sha256="D" * 64,
        probe_plan_v2_sha256="E" * 64,
        registry_sha256="F" * 64,
        registry_row_index=282,
        registry_row_sha256="5251227378A4192AB58364591603B2C1B1EED306DCC3BD4976DB943FDFDC8A1E",
        packet_sha256="B" * 64,
        source_attempt_id=ATTEMPT_ID,
        design_stage_path=str(tmp_path / f".trendstack_006_design_h1.attempt-{ATTEMPT_ID}"),
        stage_role="DESIGN",
        supervisor_review_base_sha256="C" * 64,
        custodian_public_receipt_sha256=sha256_bytes(cap.public_receipt),
        custodian_public_manifest_sha256=sha256_bytes(cap.public_manifest),
        selection_manifest_sha256=sha256_bytes(cap.selection),
        selection_mapping_sha256=sha256_bytes(cap.mapping),
    )


def _build(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    dates = ["2016-01-04", "2016-01-05"]
    cap = Capability({day: _payload(day) for day in dates})
    contract = _contract(tmp_path, cap)
    build_shape, validation_shape = _shapes(dates)
    output = tmp_path / "trendstack_006_design_h1"
    result = build_design_source_for_testing(cap, output, contract, shape=build_shape)
    authority = ValidationAuthority(
        validator_tool_sha256=contract.validator_tool_sha256,
        validator_test_sha256=contract.validator_test_sha256,
        builder_tool_sha256=contract.builder_tool_sha256,
        builder_test_sha256=contract.builder_test_sha256,
        custodian_tool_sha256=contract.custodian_tool_sha256,
        custodian_test_sha256=contract.custodian_test_sha256,
        supervisor_test_sha256=contract.supervisor_test_sha256,
        collection_plan_v1_sha256=contract.collection_plan_v1_sha256,
        collection_plan_v2_sha256=contract.collection_plan_v2_sha256,
        probe_plan_v1_sha256=contract.probe_plan_v1_sha256,
        probe_plan_v2_sha256=contract.probe_plan_v2_sha256,
        registry_sha256=contract.registry_sha256,
        registry_row_index=contract.registry_row_index,
        registry_row_sha256=contract.registry_row_sha256,
        packet_sha256=contract.packet_sha256,
        source_attempt_id=contract.source_attempt_id,
        stage_path=contract.design_stage_path,
        stage_role=contract.stage_role,
        supervisor_review_base_sha256=contract.supervisor_review_base_sha256,
        custodian_public_receipt_sha256=contract.custodian_public_receipt_sha256,
        custodian_public_manifest_sha256=contract.custodian_public_manifest_sha256,
        selection_manifest_sha256=contract.selection_manifest_sha256,
        selection_mapping_sha256=contract.selection_mapping_sha256,
        expected_receipt_sha256=result["pending_receipt_sha256"],
        expected_tree_sha256=result["pending_tree_sha256"],
    )
    return output, authority, validation_shape


def _validate(output, authority, shape):
    return validate_design_source_for_testing(output, authority, shape=shape)


def test_v7_authority_uses_only_canonical_registry_row(tmp_path):
    _output, authority, _shape = _build(tmp_path)
    assert "source_run_registry_row_index" not in authority.__dataclass_fields__
    assert "source_run_registry_row_sha256" not in authority.__dataclass_fields__
    assert authority.registry_row_index == 282
    assert authority.registry_row_sha256 == "5251227378A4192AB58364591603B2C1B1EED306DCC3BD4976DB943FDFDC8A1E"
    receipt = json.loads((_output / "design_h1_source_receipt.json").read_bytes())
    assert receipt["registry_row_index"] == 282
    assert receipt["registry_row_sha256"] == authority.registry_row_sha256
    assert not {"source_run_registry_row_index", "source_run_registry_row_sha256"} & set(receipt)


@pytest.mark.parametrize(
    "changes",
    [
        {"registry_row_index": 283},
        {"registry_row_index": 999999},
        {"registry_row_sha256": "F" * 64},
    ],
)
def test_v7_validator_rejects_noncanonical_registry_authority(tmp_path, changes):
    output, authority, shape = _build(tmp_path)
    with pytest.raises(InvalidDesignValidation):
        _validate(output, replace(authority, **changes), shape)


def test_validator_accepts_hash_bound_design_tree(tmp_path):
    output, authority, shape = _build(tmp_path)
    result = _validate(output, authority, shape)
    assert result["verdict"] == "SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET"
    assert result["validated_dates"] == 2
    assert result["validated_h1_rows"] == 14


def test_production_validator_cannot_accept_fixture_shape(tmp_path):
    output, authority, _shape = _build(tmp_path)
    with pytest.raises(InvalidDesignValidation):
        validate_design_source(output, authority)


def test_validator_fails_closed_on_manifest_or_receipt_hash_drift(tmp_path):
    output, authority, shape = _build(tmp_path)
    receipt = output / "design_h1_source_receipt.json"
    data = json.loads(receipt.read_text())
    data["h1_rows"] = 13
    receipt.write_bytes(_canonical(data) + b"\n")
    with pytest.raises(InvalidDesignValidation):
        _validate(output, authority, shape)


def test_validator_rejects_missing_or_leaking_containment_flags(tmp_path):
    output, authority, shape = _build(tmp_path)
    receipt = output / "design_h1_source_receipt.json"
    data = json.loads(receipt.read_text())
    data["research_holdout_opened"] = True
    receipt.write_bytes(_canonical(data) + b"\n")
    with pytest.raises(InvalidDesignValidation):
        _validate(output, authority, shape)


def test_validator_rejects_extra_tree_file(tmp_path):
    output, authority, shape = _build(tmp_path)
    leak = output / "raw_h1" / "VALIDATION" / "sealed-leak.parquet"
    leak.parent.mkdir(parents=True)
    leak.write_bytes(b"not parquet")
    with pytest.raises(InvalidDesignValidation):
        _validate(output, authority, shape)


def test_validator_rejects_extra_empty_directory_and_hardlinked_expected_shard(tmp_path):
    output, authority, shape = _build(tmp_path)
    (output / "economic_leak").mkdir()
    with pytest.raises(InvalidDesignValidation):
        _validate(output, authority, shape)
    (output / "economic_leak").rmdir()
    shard = output / "raw_h1" / "DESIGN" / "2016-01-04" / "1200_1800.parquet"
    outside_link = tmp_path / "outside-hardlink.parquet"
    try:
        outside_link.hardlink_to(shard)
    except OSError:
        pytest.skip("hardlinks unavailable on this filesystem")
    with pytest.raises(InvalidDesignValidation):
        _validate(output, authority, shape)


def test_validator_independently_rejects_three_row_groups_and_auxiliary_null():
    day = "2016-01-04"
    base = pq.read_table(pa.BufferReader(_payload(day)))
    sink = pa.BufferOutputStream()
    pq.write_table(base, sink, row_group_size=3)
    with pytest.raises(InvalidDesignValidation):
        _validate_shard(sink.getvalue().to_pybytes(), day, 7)

    clock_rows = base.to_pylist()
    clock_rows[0]["time_server"] = clock_rows[0]["time_server"] + timedelta(hours=1)
    sink = pa.BufferOutputStream()
    pq.write_table(pa.Table.from_pylist(clock_rows, schema=EXPECTED_SCHEMA), sink)
    with pytest.raises(InvalidDesignValidation):
        _validate_shard(sink.getvalue().to_pybytes(), day, 7)
    arrays = [
        pa.array([0, 0, 0, None, 0, 0, 0], type=pa.uint64()) if name == "real_volume" else base[name]
        for name in EXPECTED_SCHEMA.names
    ]
    sink = pa.BufferOutputStream()
    pq.write_table(pa.Table.from_arrays(arrays, schema=EXPECTED_SCHEMA), sink)
    with pytest.raises(InvalidDesignValidation):
        _validate_shard(sink.getvalue().to_pybytes(), day, 7)


def test_validator_rejects_bad_input_day_hash_and_nested_economic_key_after_rebind(tmp_path):
    output, authority, shape = _build(tmp_path)
    mapping_path = output / "design_shard_mapping.jsonl"
    mapping = [json.loads(line) for line in mapping_path.read_text().splitlines()]
    mapping[0]["sha256"] = "F" * 64
    mapping_path.write_bytes(b"".join(_canonical(row) + b"\n" for row in mapping))
    with pytest.raises(InvalidDesignValidation):
        _validate(output, replace(authority, selection_mapping_sha256=_digest(mapping_path.read_bytes())), shape)

    output, authority, shape = _build(tmp_path / "nested")
    request_path = output / "design_request_plan.jsonl"
    requests = [json.loads(line) for line in request_path.read_text().splitlines()]
    requests[0]["nested"] = {"economic_leak": False}
    request_path.write_bytes(b"".join(_canonical(row) + b"\n" for row in requests))
    request_receipt_path = output / "design_request_plan_receipt.json"
    request_receipt = json.loads(request_receipt_path.read_text())
    request_receipt["request_plan_sha256"] = _digest(request_path.read_bytes())
    request_receipt_path.write_bytes(_canonical(request_receipt) + b"\n")
    receipt_path = output / "design_h1_source_receipt.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["request_plan_sha256"] = _digest(request_path.read_bytes())
    receipt["request_receipt_sha256"] = _digest(request_receipt_path.read_bytes())
    pending = {
        path.relative_to(output).as_posix(): path.read_bytes()
        for path in output.rglob("*")
        if path.is_file() and path != receipt_path
    }
    receipt["pending_tree_sha256"] = _tree_sha(pending)
    receipt_path.write_bytes(_canonical(receipt) + b"\n")
    rebound = replace(
        authority,
        expected_tree_sha256=receipt["pending_tree_sha256"],
        expected_receipt_sha256=_digest(receipt_path.read_bytes()),
    )
    with pytest.raises(InvalidDesignValidation):
        _validate(output, rebound, shape)

    output, authority, shape = _build(tmp_path / "wrong-type")
    receipt_path = output / "design_h1_source_receipt.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["performance_trials_executed"] = False
    receipt_path.write_bytes(_canonical(receipt) + b"\n")
    rebound = replace(authority, expected_receipt_sha256=_digest(receipt_path.read_bytes()))
    with pytest.raises(InvalidDesignValidation):
        _validate(output, rebound, shape)
