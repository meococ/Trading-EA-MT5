from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest


ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "research" / "build_trendstack_004_design_source.py"
VALIDATOR_PATH = ROOT / "research" / "validate_trendstack_004_design_source.py"
SUPERVISOR_PATH = ROOT / "research" / "splitvault_002_supervisor.py"
SOURCE_ATTEMPT_ID = "HYP004-SOURCE-ATTEMPT-0123456789ABCDEF"
SUPERVISOR_REVIEW_BASE_SHA256 = "A" * 64


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def source_schema() -> pa.Schema:
    return pa.schema(
        [
            ("time_server", pa.timestamp("ns")),
            ("time_utc", pa.timestamp("ns")),
            ("utc_offset_h", pa.int8()),
            ("open", pa.float64()),
            ("high", pa.float64()),
            ("low", pa.float64()),
            ("close", pa.float64()),
            ("tick_volume", pa.uint64()),
            ("spread", pa.int32()),
            ("real_volume", pa.uint64()),
        ]
    )


def minute_payload(tmp_path: Path, day: str) -> bytes:
    start = datetime.fromisoformat(day + "T12:01:00")
    rows = []
    for index in range(360):
        stamp = start + timedelta(minutes=index)
        price = 1.1 + index * 0.000001
        rows.append(
            {
                "time_server": stamp,
                "time_utc": stamp,
                "utc_offset_h": 0,
                "open": price,
                "high": price + 0.0001,
                "low": price - 0.0001,
                "close": price,
                "tick_volume": 1,
                "spread": 7,
                "real_volume": 0,
            }
        )
    path = tmp_path / (day + ".parquet")
    pq.write_table(pa.Table.from_pylist(rows, schema=source_schema()), path, row_group_size=360)
    return path.read_bytes()


def parent_row(builder, day: str, index: int) -> dict[str, object]:
    return {
        "challenger_stack_direction": 1,
        "challenger_stack_eligible": True,
        "control_m252_only_direction": 1,
        "control_m252_only_eligible": True,
        "control_m6_only_direction": 1,
        "control_m6_only_eligible": True,
        "exclusion_reason": None,
        "feature_complete": True,
        "hypothesis_id": builder.PARENT_HYPOTHESIS_ID,
        "max_source_time_utc": day + "T11:00:00",
        "negative_disagree_direction": None,
        "negative_disagree_eligible": False,
        "next_prefix_sha256": f"{index + 10:064X}",
        "opportunity_id": day,
        "packet_file_sha256": f"{index + 20:064X}",
        "packet_path": "DESIGN/" + day + ".json",
        "packet_payload_sha256": f"{index + 30:064X}",
        "prior_prefix_sha256": f"{index + 40:064X}",
        "row_index": index,
        "row_payload_sha256": f"{index + 50:064X}",
        "schema_version": builder.PARENT_LEDGER_SCHEMA,
        "source_chain_sha256": f"{index + 60:064X}",
        "split": "DESIGN",
    }


class PublicDesignCapability:
    __slots__ = ("payloads", "receipt", "manifest")

    def __init__(self, payloads: dict[str, bytes]):
        self.payloads = payloads
        self.receipt = canonical(
            {
                "source_attempt_id": SOURCE_ATTEMPT_ID,
                "stage_role": "CUSTODY",
                "supervisor_review_base_sha256": SUPERVISOR_REVIEW_BASE_SHA256,
                "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
            }
        ) + b"\n"
        self.manifest = b"".join(
            canonical({"date": day, "sha256": sha256(payload)}) + b"\n"
            for day, payload in sorted(payloads.items())
        )

    def design_dates(self):
        return tuple(sorted(self.payloads))

    def read_design_day(self, day: str):
        return self.payloads[day]

    def public_receipt_bytes(self):
        return self.receipt

    def public_manifest_bytes(self):
        return self.manifest


def built_fixture(tmp_path: Path, dates: list[str] | None = None):
    dates = dates or ["2016-01-04", "2016-01-05"]
    builder = load(BUILDER_PATH, "validator_builder_fixture")
    validator = load(VALIDATOR_PATH, "validator_under_test")
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_bytes(b"".join(canonical(parent_row(builder, day, index)) + b"\n" for index, day in enumerate(dates)))
    parent_receipt = tmp_path / "parent_receipt.json"
    parent_receipt.write_bytes(b'{"stage0_verdict":"PASS"}\n')
    date_sha = builder.sha256_bytes(builder.canonical_design_date_set_bytes(dates))
    projection = builder.project_design_stage0(
        ledger,
        parent_receipt,
        builder.ProjectionAuthority(
            parent_ledger_sha256=sha256(ledger.read_bytes()),
            parent_receipt_sha256=sha256(parent_receipt.read_bytes()),
            design_date_set_sha256=date_sha,
            expected_design_dates=len(dates),
            projector_tool_sha256=sha256(BUILDER_PATH.read_bytes()),
        ),
    )
    output = tmp_path / "output"
    stage = output.parent / ("." + output.name + ".attempt-" + SOURCE_ATTEMPT_ID)
    stage.mkdir()
    contract = builder.DesignSourceContract(
        design_date_set_sha256=date_sha,
        expected_design_dates=len(dates),
        expected_rows_per_day=360,
        expected_total_rows=len(dates) * 360,
        first_design_date=dates[0],
        last_design_date=dates[-1],
        builder_tool_sha256=sha256(BUILDER_PATH.read_bytes()),
        source_attempt_id=SOURCE_ATTEMPT_ID,
        design_stage_path=str(stage.resolve()),
        stage_role="DESIGN",
        supervisor_review_base_sha256=SUPERVISOR_REVIEW_BASE_SHA256,
    )
    payloads = {day: minute_payload(tmp_path, day) for day in dates}
    build_result = builder.build_design_source(
        PublicDesignCapability(payloads),
        projection,
        output,
        contract,
        attempt_root=stage,
        expected_attempt_identity=builder._directory_identity(stage),
    )
    source_receipt = json.loads((output / "design_m1_source_receipt.json").read_bytes())
    root_identity, file_identities, directory_identities = validator._inventory(output)
    authority = validator.ValidationAuthority(
        design_date_set_sha256=date_sha,
        expected_design_dates=len(dates),
        expected_rows_per_day=360,
        expected_total_rows=len(dates) * 360,
        first_design_date=dates[0],
        last_design_date=dates[-1],
        validator_tool_sha256=sha256(VALIDATOR_PATH.read_bytes()),
        validator_test_sha256=sha256(Path(__file__).read_bytes()),
        custodian_public_receipt_sha256=source_receipt["custodian_public_receipt_sha256"],
        custodian_public_manifest_sha256=source_receipt["custodian_public_manifest_sha256"],
        expected_pending_receipt_sha256=build_result["pending_receipt_sha256"],
        expected_pending_tree_sha256=build_result["pending_tree_sha256"],
        parent_ledger_sha256=sha256(ledger.read_bytes()),
        parent_receipt_sha256=sha256(parent_receipt.read_bytes()),
        projector_tool_sha256=sha256(BUILDER_PATH.read_bytes()),
        builder_tool_sha256=sha256(BUILDER_PATH.read_bytes()),
        source_attempt_id=SOURCE_ATTEMPT_ID,
        design_stage_path=str(stage.resolve()),
        stage_role="DESIGN",
        supervisor_review_base_sha256=SUPERVISOR_REVIEW_BASE_SHA256,
        custody_design_day_sha256={day: sha256(payload) for day, payload in payloads.items()},
        expected_root_identity=root_identity,
        expected_directory_identities=directory_identities,
        expected_file_identities=file_identities,
    )
    return validator, output, authority


def refresh_pending_bindings(validator, output: Path, authority) -> None:
    receipt_path = output / "design_m1_source_receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    entries = []
    for path in sorted(item for item in output.rglob("*") if item.is_file() and item != receipt_path):
        payload = path.read_bytes()
        entries.append(
            {
                "bytes": len(payload),
                "relative_path": path.relative_to(output).as_posix(),
                "sha256": sha256(payload),
            }
        )
    receipt["pending_tree_sha256"] = sha256(
        canonical({"files": entries, "schema_version": validator.PENDING_TREE_SCHEMA})
    )
    receipt_path.write_bytes(canonical(receipt) + b"\n")
    root_identity, file_identities, directory_identities = validator._inventory(output)
    authority.expected_pending_tree_sha256 = receipt["pending_tree_sha256"]
    authority.expected_pending_receipt_sha256 = sha256(receipt_path.read_bytes())
    authority.expected_root_identity = root_identity
    authority.expected_file_identities = file_identities
    authority.expected_directory_identities = directory_identities


def test_independent_validator_is_only_component_that_emits_source_ready(tmp_path: Path) -> None:
    validator, output, authority = built_fixture(tmp_path)
    result = validator.validate_design_source(output, authority)
    assert result["verdict"] == "SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET"
    assert result["validated_dates"] == 2
    assert result["validated_m1_rows"] == 720
    assert result["source_receipt_sha256"] == sha256((output / "design_m1_source_receipt.json").read_bytes())
    assert result["source_attempt_id"] == SOURCE_ATTEMPT_ID
    assert result["stage_path"] == authority.design_stage_path
    assert result["stage_role"] == "DESIGN"
    assert result["supervisor_review_base_sha256"] == SUPERVISOR_REVIEW_BASE_SHA256
    assert json.loads((output / "design_m1_source_receipt.json").read_bytes())["schema_version"] == (
        "trendstack_004_design_source_receipt.v1"
    )
    assert b"HYP003::" not in (output / "design_request_plan.jsonl").read_bytes()


def test_actual_supervisor_pending_binding_is_accepted_by_actual_validator(tmp_path: Path) -> None:
    validator, output, fixture_authority = built_fixture(tmp_path)
    supervisor = load(SUPERVISOR_PATH, "validator_supervisor_integration")
    receipt_payload = (output / "design_m1_source_receipt.json").read_bytes()
    builder_result = {
        **json.loads(receipt_payload),
        "pending_receipt_sha256": sha256(receipt_payload),
    }
    binding = supervisor._bind_pending_output(output, builder_result)
    assert len(binding["expected_root_identity"]) == 6
    assert all(type(value) is int for value in binding["expected_root_identity"])
    assert all(
        len(identity) == 6 and all(type(value) is int for value in identity)
        for identity in binding["expected_directory_identities"].values()
    )
    values = dict(fixture_authority.__dict__)
    values.update(
        {
            "expected_pending_receipt_sha256": binding["pending_receipt_sha256"],
            "expected_pending_tree_sha256": binding["pending_tree_sha256"],
            "expected_root_identity": binding["expected_root_identity"],
            "expected_directory_identities": binding["expected_directory_identities"],
            "expected_file_identities": binding["expected_file_identities"],
        }
    )
    authority = validator.ValidationAuthority(**values)
    result = validator.validate_design_source(output, authority)
    assert result["verdict"] == validator.READY_VERDICT


@pytest.mark.parametrize(
    "attack",
    ["tamper", "extra", "missing", "row_groups", "mixed_projection", "hardlink", "upstream_binding"],
)
def test_validator_rejects_tree_tamper_extra_missing_alias_and_mixed_projection(tmp_path: Path, attack: str) -> None:
    validator, output, authority = built_fixture(tmp_path)
    shard = output / "raw_m1" / "DESIGN" / "2016-01-04" / "1201_1800.parquet"
    if attack == "tamper":
        target = output / "design_request_plan_receipt.json"
        target.write_bytes(target.read_bytes() + b" ")
    elif attack == "extra":
        (output / "unexpected.txt").write_text("sentinel", encoding="utf-8")
    elif attack == "missing":
        shard.unlink()
    elif attack == "row_groups":
        table = pq.read_table(shard)
        shard.unlink()
        pq.write_table(table, shard, row_group_size=180)
    elif attack == "mixed_projection":
        target = output / "design_stage0_projection.jsonl"
        target.write_bytes(target.read_bytes().replace(b'"split":"DESIGN"', b'"split":"VALIDATION_FEATURE_ONLY"'))
    elif attack == "upstream_binding":
        target = output / "design_m1_source_receipt.json"
        value = json.loads(target.read_bytes())
        value["custodian_public_receipt_sha256"] = "F" * 64
        target.write_bytes(canonical(value) + b"\n")
    else:
        external = tmp_path / "external.parquet"
        external.write_bytes(shard.read_bytes())
        shard.unlink()
        os.link(external, shard)
    with pytest.raises(validator.InvalidDesignValidation, match="^INVALID_DESIGN_VALIDATION$"):
        validator.validate_design_source(output, authority)


def test_validator_detects_identity_swap_after_inventory(tmp_path: Path) -> None:
    validator, output, authority = built_fixture(tmp_path)
    target = output / "design_m1_manifest.jsonl"

    def swap(event: str) -> None:
        if event == "after_inventory":
            payload = target.read_bytes()
            target.unlink()
            target.write_bytes(payload)

    with pytest.raises(validator.InvalidDesignValidation, match="^INVALID_DESIGN_VALIDATION$"):
        validator.validate_design_source(output, authority, lifecycle_hook=swap)


def test_validator_rejects_root_replacement_reusing_expected_file_identities(tmp_path: Path) -> None:
    validator, output, authority = built_fixture(tmp_path)
    old_root = tmp_path / "old_tree"

    def replace_tree(event: str) -> None:
        if event != "after_inventory":
            return
        output.rename(old_root)
        output.mkdir()
        for source in sorted(old_root.rglob("*"), key=lambda item: len(item.parts)):
            relative = source.relative_to(old_root)
            target = output / relative
            if source.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                source.replace(target)
        (output / "VALIDATION_SENTINEL.txt").write_text("future", encoding="utf-8")

    with pytest.raises(validator.InvalidDesignValidation, match="^INVALID_DESIGN_VALIDATION$"):
        validator.validate_design_source(output, authority, lifecycle_hook=replace_tree)


def test_validator_rechecks_full_tree_immediately_before_ready(tmp_path: Path) -> None:
    validator, output, authority = built_fixture(tmp_path)
    called = {"value": False}

    def add_late_extra(event: str) -> None:
        if event == "before_final_inventory":
            called["value"] = True
            (output / "VALIDATION_LATE.txt").write_text("future", encoding="utf-8")

    with pytest.raises(validator.InvalidDesignValidation, match="^INVALID_DESIGN_VALIDATION$"):
        validator.validate_design_source(output, authority, lifecycle_hook=add_late_extra)
    assert called["value"] is True


def test_validator_rejects_whole_byte_consistent_tree_replacement_before_inventory(tmp_path: Path) -> None:
    validator, output, authority = built_fixture(tmp_path)
    old_root = tmp_path / "old_tree_before_validation"
    output.rename(old_root)
    output.mkdir()
    for source in sorted(old_root.rglob("*"), key=lambda item: len(item.parts)):
        relative = source.relative_to(old_root)
        target = output / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            source.replace(target)
    with pytest.raises(validator.InvalidDesignValidation, match="^INVALID_DESIGN_VALIDATION$"):
        validator.validate_design_source(output, authority)


def test_validator_binds_trace_input_hash_to_custody_day_mapping(tmp_path: Path) -> None:
    validator, output, authority = built_fixture(tmp_path)
    trace_path = output / "design_source_access_trace.jsonl"
    trace = [json.loads(line) for line in trace_path.read_bytes().splitlines()]
    trace[0]["input_day_sha256"] = "B" * 64
    trace_path.write_bytes(b"".join(canonical(row) + b"\n" for row in trace))
    receipt_path = output / "design_m1_source_receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    receipt["trace_sha256"] = sha256(trace_path.read_bytes())
    receipt_path.write_bytes(canonical(receipt) + b"\n")
    refresh_pending_bindings(validator, output, authority)
    with pytest.raises(validator.InvalidDesignValidation, match="^INVALID_DESIGN_VALIDATION$"):
        validator.validate_design_source(output, authority)


def test_validator_binds_projection_receipt_to_frozen_parent_authority(tmp_path: Path) -> None:
    validator, output, authority = built_fixture(tmp_path)
    projection_receipt_path = output / "design_stage0_projection_receipt.json"
    projection_receipt = json.loads(projection_receipt_path.read_bytes())
    projection_receipt["parent_ledger_sha256"] = "E" * 64
    projection_receipt_path.write_bytes(canonical(projection_receipt) + b"\n")
    receipt_path = output / "design_m1_source_receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    receipt["projection_receipt_sha256"] = sha256(projection_receipt_path.read_bytes())
    receipt_path.write_bytes(canonical(receipt) + b"\n")
    refresh_pending_bindings(validator, output, authority)
    with pytest.raises(validator.InvalidDesignValidation, match="^INVALID_DESIGN_VALIDATION$"):
        validator.validate_design_source(output, authority)


@pytest.mark.parametrize("field", ["source_attempt_id", "stage_path", "stage_role", "supervisor_review_base_sha256"])
def test_validator_never_promotes_mismatched_design_attempt_provenance(tmp_path: Path, field: str) -> None:
    validator, output, authority = built_fixture(tmp_path)
    receipt_path = output / "design_m1_source_receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    receipt[field] = "MISMATCH"
    receipt_path.write_bytes(canonical(receipt) + b"\n")
    refresh_pending_bindings(validator, output, authority)
    with pytest.raises(validator.InvalidDesignValidation, match="^INVALID_DESIGN_VALIDATION$"):
        validator.validate_design_source(output, authority)
