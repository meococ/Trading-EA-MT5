import hashlib
import json
from datetime import datetime

import pytest

from test_project_trendstack_007_design_source import _project, _synthetic_case
from validate_trendstack_007_design_source import (
    EXPECTED_ARROW_SCHEMA,
    DecodedOutputShard,
    ValidationAuthority,
    pyarrow_output_decoder,
    validate_stage_from_paths,
    validate_stage_synthetic,
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _bundle_document():
    return _canonical({
        "contracts": [
            {"path": "authority/v4.json", "role": "base_v4", "sha256": "A" * 64},
            {"path": "authority/v5.json", "role": "output_schema_v5", "sha256": "B" * 64},
            {"path": "authority/v6.json", "role": "metadata_map_v6", "sha256": "C" * 64},
            {"path": "authority/v7.json", "role": "terminal_tree_v7", "sha256": "D" * 64},
        ],
        "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-007",
        "schema_version": "trendstack_007_active_source_contract_bundle.v2",
    }) + b"\n"


def _task_document():
    return _canonical({
        "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-007",
        "schema_version": "trendstack_007_source_implementation_task_packet.v4",
    }) + b"\n"


def _authority(case):
    return ValidationAuthority(
        projection_attempt_id=case["authority"].projection_attempt_id,
        active_contract_sha256=case["authority"].active_contract_sha256,
        task_packet_sha256=case["authority"].task_packet_sha256,
        validator_tool_sha256="C" * 64,
        public_receipt_sha256=case["authority"].public_receipt_sha256,
        public_manifest_sha256=case["authority"].public_manifest_sha256,
        selection_manifest_sha256=case["authority"].selection_manifest_sha256,
    )


def _validate(case, evidence, **overrides):
    values = {
        "stage_root": case["stage"],
        "evidence_root": evidence,
        "authority": _authority(case),
        "shape": case["shape"],
        "public_receipt": case["receipt"],
        "public_manifest": case["manifest"],
        "selection_manifest": case["selection"],
        "decode_output": lambda payload: DecodedOutputShard(
            EXPECTED_ARROW_SCHEMA,
            1,
            tuple(
                {
                    **json.loads(payload),
                    "time_server": datetime.fromisoformat(json.loads(payload)["time_server"]),
                    "time_utc": datetime.fromisoformat(json.loads(payload)["time_utc"]),
                }
                for _ in (0,)
            ),
        ),
    }
    values.update(overrides)
    return validate_stage_synthetic(**values)


def test_independent_validator_rederives_lineage_without_upstream_parquet_open(tmp_path):
    case = _synthetic_case(tmp_path)
    _project(case)
    evidence = tmp_path / "evidence"
    evidence.mkdir()

    result = _validate(case, evidence)

    assert result["verdict"] == "PASS_INDEPENDENT_STAGE_VALIDATION"
    assert result["output_shards"] == len(case["selected"])
    assert result["validator_access"]["public_shard_opens"] == 0
    assert result["validator_access"]["staged_output_shard_opens"] == len(case["selected"])
    assert result["validator_access"]["active_contract_reads"] == 0
    assert result["validator_access"]["task_packet_reads"] == 0
    assert set(result["stage_metadata_hashes"]) == {
        "projection_requests.jsonl", "projection_request_receipt.json",
        "design_1200_manifest.jsonl", "design_1200_source_trace.jsonl",
        "design_1200_reconciliation.json", "design_1200_projector_receipt.json",
    }
    assert (evidence / "validation_receipt.json").is_file()


def test_validator_path_surface_reads_metadata_but_has_no_public_shard_capability(tmp_path):
    case = _synthetic_case(tmp_path)
    _project(case)
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    paths = [metadata / name for name in ("receipt.json", "manifest.jsonl", "selection.jsonl", "bundle.json", "task.json")]
    for path, payload in zip(paths, (
        case["receipt"], case["manifest"], case["selection"],
        _bundle_document(), _task_document(),
    )):
        path.write_bytes(payload)
    evidence = tmp_path / "evidence"
    evidence.mkdir()

    result = validate_stage_from_paths(
        workspace_root=tmp_path,
        public_receipt_path=paths[0], public_manifest_path=paths[1], selection_manifest_path=paths[2],
        active_contract_bundle_path=paths[3], active_contract_bundle_sha256=_sha(paths[3].read_bytes()),
        implementation_task_packet_path=paths[4], implementation_task_packet_sha256=_sha(paths[4].read_bytes()),
        stage_root=case["stage"], evidence_root=evidence, authority=_authority(case), shape=case["shape"],
        decode_output=lambda payload: DecodedOutputShard(
            EXPECTED_ARROW_SCHEMA, 1,
            ({
                **json.loads(payload),
                "time_server": datetime.fromisoformat(json.loads(payload)["time_server"]),
                "time_utc": datetime.fromisoformat(json.loads(payload)["time_utc"]),
            },),
        ),
    )
    assert result["validator_access"]["public_shard_opens"] == 0


def test_independent_lazy_pyarrow_decoder_reports_exact_physical_schema():
    from project_trendstack_007_design_source import pyarrow_projection_codecs
    from test_project_trendstack_007_design_source import _row

    _, encode, _ = pyarrow_projection_codecs()
    decoded = pyarrow_output_decoder()(encode(_row("2016-01-04")))
    assert decoded.schema == EXPECTED_ARROW_SCHEMA
    assert decoded.row_groups == 1 and len(decoded.rows) == 1


def test_validator_rejects_lineage_self_consistency_attack(tmp_path):
    case = _synthetic_case(tmp_path)
    _project(case)
    trace_path = case["stage"] / "design_1200_source_trace.jsonl"
    trace = [json.loads(line) for line in trace_path.read_bytes().splitlines()]
    trace[0]["input_sha256"] = "F" * 64
    trace_payload = b"".join(_canonical(row) + b"\n" for row in trace)
    trace_path.write_bytes(trace_payload)

    reconciliation_path = case["stage"] / "design_1200_reconciliation.json"
    reconciliation = json.loads(reconciliation_path.read_bytes())
    reconciliation["trace_sha256"] = _sha(trace_payload)
    reconciliation_path.write_bytes(_canonical(reconciliation) + b"\n")
    receipt_path = case["stage"] / "design_1200_projector_receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    receipt["trace_sha256"] = _sha(trace_payload)
    receipt["reconciliation_sha256"] = _sha(reconciliation_path.read_bytes())
    receipt_path.write_bytes(_canonical(receipt) + b"\n")

    evidence = tmp_path / "evidence"
    evidence.mkdir()
    with pytest.raises(Exception):
        _validate(case, evidence)


def test_validator_rejects_projector_access_count_mismatch(tmp_path):
    case = _synthetic_case(tmp_path)
    _project(case)
    receipt_path = case["stage"] / "design_1200_projector_receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    receipt["projector_access"]["selected_public_shard_opens"] += 1
    receipt_path.write_bytes(_canonical(receipt) + b"\n")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    with pytest.raises(Exception):
        _validate(case, evidence)


@pytest.mark.parametrize("mutation", ["schema", "row_count", "bytes"])
def test_validator_rejects_output_schema_row_or_hash_mutation(tmp_path, mutation):
    case = _synthetic_case(tmp_path)
    _project(case)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    if mutation == "bytes":
        shard = next((case["stage"] / "DESIGN").rglob("*.parquet"))
        shard.write_bytes(shard.read_bytes() + b"drift")
        with pytest.raises(Exception):
            _validate(case, evidence)
        return

    def bad_decoder(payload):
        raw = json.loads(payload)
        raw["time_server"] = datetime.fromisoformat(raw["time_server"])
        raw["time_utc"] = datetime.fromisoformat(raw["time_utc"])
        if mutation == "schema":
            schema = (("wrong", "timestamp[ns]", True),) + EXPECTED_ARROW_SCHEMA[1:]
            return DecodedOutputShard(schema, 1, (raw,))
        return DecodedOutputShard(EXPECTED_ARROW_SCHEMA, 1, (raw, raw))

    with pytest.raises(Exception):
        _validate(case, evidence, decode_output=bad_decoder)


def test_validator_rejects_existing_receipt_and_stage_metadata_shape_drift(tmp_path):
    case = _synthetic_case(tmp_path)
    _project(case)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "validation_receipt.json").write_bytes(b"occupied")
    with pytest.raises(Exception):
        _validate(case, evidence)

    evidence2 = tmp_path / "evidence2"
    evidence2.mkdir()
    (case["stage"] / "unexpected.json").write_bytes(b"{}\n")
    with pytest.raises(Exception):
        _validate(case, evidence2)


def test_validator_source_is_independent_of_projector_module():
    import validate_trendstack_007_design_source as validator

    source = open(validator.__file__, "r", encoding="utf-8").read()
    assert "import project_trendstack_007_design_source" not in source
    assert "from project_trendstack_007_design_source" not in source


def test_path_validator_factually_reads_bound_contract_bundle_and_task_packet(tmp_path):
    case = _synthetic_case(tmp_path)
    _project(case)
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    receipt_path = metadata / "receipt.json"
    manifest_path = metadata / "manifest.jsonl"
    selection_path = metadata / "selection.jsonl"
    bundle_path = metadata / "active_contract_bundle.json"
    task_path = metadata / "implementation_task.json"
    for path, payload in (
        (receipt_path, case["receipt"]), (manifest_path, case["manifest"]),
        (selection_path, case["selection"]),
        (bundle_path, _bundle_document()), (task_path, _task_document()),
    ):
        path.write_bytes(payload)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    result = validate_stage_from_paths(
        workspace_root=tmp_path,
        public_receipt_path=receipt_path, public_manifest_path=manifest_path,
        selection_manifest_path=selection_path,
        active_contract_bundle_path=bundle_path,
        active_contract_bundle_sha256=_sha(bundle_path.read_bytes()),
        implementation_task_packet_path=task_path,
        implementation_task_packet_sha256=_sha(task_path.read_bytes()),
        stage_root=case["stage"], evidence_root=evidence, authority=_authority(case), shape=case["shape"],
        decode_output=lambda payload: DecodedOutputShard(
            EXPECTED_ARROW_SCHEMA, 1,
            ({
                **json.loads(payload),
                "time_server": datetime.fromisoformat(json.loads(payload)["time_server"]),
                "time_utc": datetime.fromisoformat(json.loads(payload)["time_utc"]),
            },),
        ),
    )
    assert result["validator_access"]["active_contract_reads"] == 1
    assert result["validator_access"]["task_packet_reads"] == 1

    task_path.write_bytes(task_path.read_bytes() + b" ")
    evidence2 = tmp_path / "evidence2"
    evidence2.mkdir()
    with pytest.raises(Exception):
        validate_stage_from_paths(
            workspace_root=tmp_path,
            public_receipt_path=receipt_path, public_manifest_path=manifest_path,
            selection_manifest_path=selection_path,
            active_contract_bundle_path=bundle_path,
            active_contract_bundle_sha256=_sha(bundle_path.read_bytes()),
            implementation_task_packet_path=task_path,
            implementation_task_packet_sha256="F" * 64,
            stage_root=case["stage"], evidence_root=evidence2, authority=_authority(case), shape=case["shape"],
            decode_output=lambda payload: (_ for _ in ()).throw(AssertionError("must fail before shard decode")),
        )


def test_prepublish_identity_digest_detects_same_metadata_shard_replacement(tmp_path):
    import validate_trendstack_007_design_source as validator

    case = _synthetic_case(tmp_path)
    _project(case)
    manifest_payload = (case["stage"] / "design_1200_manifest.jsonl").read_bytes()
    before = validator.stage_output_identity_digest_no_payload(
        case["stage"], manifest_payload, len(case["selected"])
    )
    shard = next((case["stage"] / "DESIGN").rglob("*.parquet"))
    original = shard.read_bytes()
    shard.unlink()
    shard.write_bytes(original)
    after = validator.stage_output_identity_digest_no_payload(
        case["stage"], manifest_payload, len(case["selected"])
    )
    assert before != after


@pytest.mark.parametrize("authority_kind", ["duplicate_key", "noncanonical_drift"])
def test_path_validator_rejects_duplicate_key_or_noncanonical_authority(tmp_path, authority_kind):
    import validate_trendstack_007_design_source as validator

    for name in ("receipt", "manifest", "selection"):
        (tmp_path / name).write_bytes(b"synthetic")
    canonical_bundle = _bundle_document()
    if authority_kind == "duplicate_key":
        bundle = b'{"schema_version":"bundle.v1","schema_version":"drift"}\n'
        expected = _sha(bundle)
    else:
        bundle = b' ' + canonical_bundle
        expected = _sha(canonical_bundle)
    (tmp_path / "bundle").write_bytes(bundle)
    task = _task_document()
    (tmp_path / "task").write_bytes(task)
    with pytest.raises(Exception):
        validator.validate_stage_from_paths(
            workspace_root=tmp_path,
            public_receipt_path=tmp_path / "receipt",
            public_manifest_path=tmp_path / "manifest",
            selection_manifest_path=tmp_path / "selection",
            active_contract_bundle_path=tmp_path / "bundle",
            active_contract_bundle_sha256=expected,
            implementation_task_packet_path=tmp_path / "task",
            implementation_task_packet_sha256=_sha(task),
            stage_root=tmp_path / "missing-stage", evidence_root=tmp_path / "missing-evidence",
            authority=None, shape=None, decode_output=lambda payload: None,
        )


def test_path_validator_rejects_superseded_task_v3_as_active_task(tmp_path):
    import validate_trendstack_007_design_source as validator

    for name in ("receipt", "manifest", "selection"):
        (tmp_path / name).write_bytes(b"synthetic")
    bundle = _bundle_document()
    task = _canonical({
        "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-007",
        "schema_version": "trendstack_007_source_implementation_task_packet.v3",
    }) + b"\n"
    (tmp_path / "bundle").write_bytes(bundle)
    (tmp_path / "task").write_bytes(task)
    with pytest.raises(Exception):
        validator.validate_stage_from_paths(
            workspace_root=tmp_path,
            public_receipt_path=tmp_path / "receipt",
            public_manifest_path=tmp_path / "manifest",
            selection_manifest_path=tmp_path / "selection",
            active_contract_bundle_path=tmp_path / "bundle",
            active_contract_bundle_sha256=_sha(bundle),
            implementation_task_packet_path=tmp_path / "task",
            implementation_task_packet_sha256=_sha(task),
            stage_root=tmp_path / "missing-stage", evidence_root=tmp_path / "missing-evidence",
            authority=None, shape=None, decode_output=lambda payload: None,
        )
