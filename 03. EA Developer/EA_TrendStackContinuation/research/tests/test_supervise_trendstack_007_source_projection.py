import hashlib
import inspect
import json
from pathlib import Path

import pytest

import supervise_trendstack_007_source_projection as supervisor


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _packet():
    packet = dict(supervisor.SOURCE_RUN_PACKET_DEFAULTS)
    packet.setdefault("registry_row_index", 1)
    for field in supervisor.SOURCE_RUN_PACKET_FIELDS:
        if field.endswith("_sha256"):
            packet.setdefault(field, "A" * 64)
        elif field.endswith("_path") or field.endswith("_root"):
            packet.setdefault(field, "synthetic/" + field)
    packet["stage_root"] = (
        "02. AlphaFactory/data/fivepercent/EURUSD/.trendstack_007_design_h1_1200.attempt-"
        + packet["projection_attempt_id"]
    )
    packet["evidence_root"] = (
        "03. EA Developer/EA_TrendStackContinuation/research/evidence/"
        "HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_PROJECTION_ATTEMPTS/"
        + packet["projection_attempt_id"]
    )
    packet["reviewed_source_run_packet_sha256"] = "0" * 64
    detached = supervisor.compute_source_run_packet_sha256(packet)
    packet["reviewed_source_run_packet_sha256"] = detached
    return packet, detached


def test_packet_hash_sentinel_and_exact_shape_fail_closed(tmp_path):
    packet, detached = _packet()
    payload = supervisor.canonical_json(packet) + b"\n"
    verified = supervisor.validate_source_run_packet_document(payload, detached)
    assert verified.detached_sha256 == detached

    extra = dict(packet)
    extra["invented"] = True
    with pytest.raises(Exception):
        supervisor.validate_source_run_packet_document(supervisor.canonical_json(extra) + b"\n", detached)
    missing = dict(packet)
    missing.pop("implementation_review_receipt_sha256")
    with pytest.raises(Exception):
        supervisor.validate_source_run_packet_document(supervisor.canonical_json(missing) + b"\n", detached)
    with pytest.raises(Exception):
        supervisor.validate_source_run_packet_document(payload, "F" * 64)
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = None
    with pytest.raises(Exception):
        supervisor.supervise(tmp_path / "packet.json")


def _armed_prepacket_runtime(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    runtime = (
        workspace
        / "03. EA Developer/EA_TrendStackContinuation/research/supervise_trendstack_007_source_projection.py"
    )
    runtime.parent.mkdir(parents=True)
    reviewed = "A" * 64
    disarmed = b"REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = None"
    armed = (
        b'REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = "'
        + reviewed.encode("ascii")
        + b'"'
    )
    payload = Path(supervisor.__file__).read_bytes()
    assert payload.count(disarmed) == 1
    runtime.write_bytes(payload.replace(disarmed, armed))
    monkeypatch.setattr(supervisor, "__file__", str(runtime))
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = reviewed
    return workspace, runtime, reviewed, disarmed, armed


@pytest.mark.parametrize(
    "failure",
    [
        "missing",
        "unreadable",
        "outside_workspace",
        "ancestor_invalid",
        "malformed",
        "duplicate_key",
        "wrong_shape",
        "detached_digest_mismatch",
    ],
)
def test_armed_prepacket_failures_attempt_persistent_disarm_and_clear_global(
    tmp_path, monkeypatch, failure
):
    workspace, runtime, reviewed, disarmed, armed = _armed_prepacket_runtime(
        tmp_path, monkeypatch
    )
    packet_path = workspace / "authority/source_run_packet.json"
    packet_path.parent.mkdir(parents=True)
    packet, _ = _packet()
    packet_payload = supervisor.canonical_json(packet) + b"\n"
    packet_path.write_bytes(packet_payload)

    if failure == "missing":
        packet_path.unlink()
    elif failure == "unreadable":
        original_read = supervisor._stable_authority_read

        def unreadable(path):
            if Path(path).absolute() == packet_path.absolute():
                raise PermissionError("synthetic unreadable packet")
            return original_read(path)

        monkeypatch.setattr(supervisor, "_stable_authority_read", unreadable)
    elif failure == "outside_workspace":
        packet_path = tmp_path / "outside.json"
        packet_path.write_bytes(packet_payload)
    elif failure == "ancestor_invalid":
        original_bind = supervisor.bind_existing_ancestor_chain

        def invalid_ancestor(root, target):
            if Path(target).absolute() == packet_path.parent.absolute():
                raise ValueError("synthetic invalid packet ancestor")
            return original_bind(root, target)

        monkeypatch.setattr(supervisor, "bind_existing_ancestor_chain", invalid_ancestor)
    elif failure == "malformed":
        packet_path.write_bytes(b"{\n")
    elif failure == "duplicate_key":
        packet_path.write_bytes(b'{"schema_version":"x","schema_version":"y"}\n')
    elif failure == "wrong_shape":
        packet_path.write_bytes(b"[]\n")

    calls = []
    real_disarm = supervisor.self_disarm_runtime

    def recorded_disarm(path, digest):
        calls.append((Path(path).absolute(), digest))
        return real_disarm(path, digest)

    monkeypatch.setattr(supervisor, "self_disarm_runtime", recorded_disarm)
    with pytest.raises(supervisor.InvalidSourceProjection) as raised:
        supervisor.supervise(packet_path)

    assert str(raised.value) == "INVALID_SOURCE_PROJECTION"
    assert calls == [(runtime.absolute(), reviewed)]
    assert supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 is None
    assert runtime.read_bytes().count(disarmed) == 1
    assert armed not in runtime.read_bytes()


def test_prepacket_disarm_failure_still_clears_global_and_normalizes_error(
    tmp_path, monkeypatch
):
    workspace, runtime, reviewed, _, armed = _armed_prepacket_runtime(tmp_path, monkeypatch)
    packet_path = workspace / "authority/missing.json"
    calls = []

    def failed_disarm(path, digest):
        calls.append((Path(path).absolute(), digest))
        raise OSError("synthetic persistent disarm failure")

    monkeypatch.setattr(supervisor, "self_disarm_runtime", failed_disarm)
    with pytest.raises(supervisor.InvalidSourceProjection) as raised:
        supervisor.supervise(packet_path)

    assert str(raised.value) == "INVALID_SOURCE_PROJECTION"
    assert calls == [(runtime.absolute(), reviewed)]
    assert supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 is None
    assert armed in runtime.read_bytes()


def test_packet_binds_dynamic_positive_registry_row_without_hardcoded_row285():
    packet, _ = _packet()
    packet["registry_row_index"] = 7
    packet["registry_row_sha256"] = "F" * 64
    detached = supervisor.compute_source_run_packet_sha256(packet)
    packet["reviewed_source_run_packet_sha256"] = detached
    verified = supervisor.validate_source_run_packet_document(
        supervisor.canonical_json(packet) + b"\n", detached
    )
    assert verified.values["registry_row_index"] == 7
    assert verified.values["registry_row_sha256"] == "F" * 64


class _Operations:
    def __init__(self, *, fail_phase=None, pre_map=None, post_map=None):
        self.events = []
        self.fail_phase = fail_phase
        self.map = {name: chr(65 + index) * 64 for index, name in enumerate(supervisor.METADATA_FILES)}
        self.pre_map = pre_map or dict(self.map)
        self.post_map = post_map or dict(self.map)
        self.published = False

    def preflight(self, packet):
        self.events.append("PREFLIGHT")
        return {"packet": packet}

    def start(self, packet, context):
        self.events.append("MARKER")
        return {"attempt_state": "ATTEMPT_CONSUMED"}, "A" * 64

    def project(self, packet, marker, context):
        assert self.events[-1] == "MARKER"
        self.events.append("PROJECT_OPEN")
        if self.fail_phase == "project":
            raise ValueError("synthetic projector failure")
        return {"stage_metadata_hashes": dict(self.map), "output_shards": 2}

    def validate(self, packet, project_result, context):
        self.events.append("VALIDATE")
        if self.fail_phase == "validate":
            raise ValueError("synthetic validator failure")
        return {
            "stage_metadata_hashes": dict(self.map),
            "validation_receipt_sha256": "B" * 64,
            "output_shards": 2,
        }

    def pre_publish_metadata_hashes(self, packet, context):
        self.events.append("PRE_HASH")
        return dict(self.pre_map)

    def publish(self, packet, context):
        self.events.append("PUBLISH")
        self.published = True

    def post_publish(self, packet, context):
        self.events.append("POST_HASH")
        return {"metadata_hashes": dict(self.post_map), "output_shard_lstats": 2, "final_output_root_identity": [1, 2]}

    def disarm(self, packet, context):
        self.events.append("DISARM")
        return {"supervisor_disarm_status": "DISARMED_NONE_VERIFIED", "supervisor_disarmed_sha256": "C" * 64}

    def terminal(self, packet, marker_sha256, verdict, evidence, context):
        self.events.append("TERMINAL:" + verdict)
        return "D" * 64


def _verified_packet():
    packet, detached = _packet()
    return supervisor.VerifiedSourceRunPacket(packet, detached, supervisor.canonical_json(packet) + b"\n")


def test_registry_row_authority_hash_excludes_single_lf_delimiter():
    registry = Path(__file__).resolve().parents[4] / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    row = registry.read_bytes().splitlines(keepends=True)[284]
    expected = "6D72D93644BF6C61D3D966013348FF272F3A78D13DE7444CB245A6809EB722DA"
    assert supervisor.canonical_registry_row_sha256(row) == expected
    assert expected != _sha(row)
    assert _sha(supervisor.canonical_json(json.loads(row))) == (
        "DBEF5D612A65ABBB855D9525250FCF1808C639D35CC61AF8B4541EBA1FEF087A"
    )
    for invalid in (
        row[:-1],
        row + b"\n",
        row[:-1] + b"\r\n",
        b'{"hypothesis_id":"HYP-TRENDSTACK-EURUSD-H1-007", "registry_row_index":285}\n',
        b'{"hypothesis_id":"HYP-TRENDSTACK-EURUSD-H1-007","registry_row_index":285,"registry_row_index":285}\n',
        b'{"value":NaN}\n',
        b'{"value":Infinity}\n',
    ):
        with pytest.raises(Exception):
            supervisor.canonical_registry_row_sha256(invalid)


@pytest.mark.parametrize(
    "mutation",
    ["missing_v7_path", "wrong_v7_path", "wrong_v7_sha256"],
)
def test_run_packet_fails_closed_on_missing_or_wrong_v7_binding(mutation):
    packet, _ = _packet()
    if mutation == "missing_v7_path":
        packet.pop("contract_v7_path")
        with pytest.raises(Exception):
            supervisor.compute_source_run_packet_sha256(packet)
        return
    if mutation == "wrong_v7_path":
        packet["contract_v7_path"] = "authority/wrong_v7.json"
    else:
        packet["contract_v7_sha256"] = "F" * 64
    detached = supervisor.compute_source_run_packet_sha256(packet)
    packet["reviewed_source_run_packet_sha256"] = detached
    with pytest.raises(Exception):
        supervisor.validate_source_run_packet_document(
            supervisor.canonical_json(packet) + b"\n", detached
        )


@pytest.mark.parametrize("field", ["implementation_task_v4_path", "implementation_task_v4_sha256"])
def test_run_packet_fails_closed_on_wrong_active_task_v4_binding(field):
    packet, _ = _packet()
    packet[field] = "authority/wrong_task.json" if field.endswith("_path") else "F" * 64
    detached = supervisor.compute_source_run_packet_sha256(packet)
    packet["reviewed_source_run_packet_sha256"] = detached
    with pytest.raises(Exception):
        supervisor.validate_source_run_packet_document(
            supervisor.canonical_json(packet) + b"\n", detached
        )


@pytest.mark.parametrize(
    "field",
    [
        "authority_amendment_v2_path", "authority_amendment_v2_sha256",
        "authority_amendment_v3_path", "authority_amendment_v3_sha256",
        "implementation_task_v5_path", "implementation_task_v5_sha256",
        "authority_repair_amendment_v4_path", "authority_repair_amendment_v4_sha256",
        "implementation_task_v6_path", "implementation_task_v6_sha256",
    ],
)
def test_run_packet_fails_closed_on_wrong_v2_v3_or_task_v5_binding(field):
    packet, _ = _packet()
    packet[field] = "authority/wrong.json" if field.endswith("_path") else "F" * 64
    detached = supervisor.compute_source_run_packet_sha256(packet)
    packet["reviewed_source_run_packet_sha256"] = detached
    with pytest.raises(Exception):
        supervisor.validate_source_run_packet_document(
            supervisor.canonical_json(packet) + b"\n", detached
        )


@pytest.mark.parametrize(
    "field",
    [
        "authority_repair_amendment_v4_path",
        "authority_repair_amendment_v4_sha256",
        "implementation_task_v6_path",
        "implementation_task_v6_sha256",
    ],
)
def test_run_packet_fails_closed_on_wrong_repair_v4_or_task_v6_binding(field):
    packet, _ = _packet()
    packet[field] = "authority/wrong.json" if field.endswith("_path") else "F" * 64
    detached = supervisor.compute_source_run_packet_sha256(packet)
    packet["reviewed_source_run_packet_sha256"] = detached
    with pytest.raises(Exception):
        supervisor.validate_source_run_packet_document(
            supervisor.canonical_json(packet) + b"\n", detached
        )


def test_one_shot_marks_before_first_open_publishes_disarms_and_passes():
    packet = _verified_packet()
    operations = _Operations()
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = packet.detached_sha256
    result = supervisor.run_one_shot_for_testing(packet, operations)

    assert result["verdict"] == "ENGINEERING_VALID_SOURCE_PROJECTION"
    assert operations.events == [
        "PREFLIGHT", "MARKER", "PROJECT_OPEN", "VALIDATE", "PRE_HASH",
        "PUBLISH", "POST_HASH", "DISARM", "TERMINAL:ENGINEERING_VALID_SOURCE_PROJECTION",
    ]
    assert supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 is None


def test_supervise_entry_rejects_arbitrary_injected_lifecycle(tmp_path):
    packet_values, detached = _packet()
    packet_path = tmp_path / "packet.json"
    packet_path.write_bytes(supervisor.canonical_json(packet_values) + b"\n")
    operations = _Operations()
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = detached

    with pytest.raises(TypeError):
        supervisor.supervise(packet_path, operations)
    assert operations.events == []
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = None


@pytest.mark.parametrize("failure", ["project", "validate"])
def test_one_shot_failure_after_marker_self_disarms_and_writes_fail_terminal(failure):
    packet = _verified_packet()
    operations = _Operations(fail_phase=failure)
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = packet.detached_sha256
    with pytest.raises(Exception):
        supervisor.run_one_shot_for_testing(packet, operations)
    assert "PUBLISH" not in operations.events
    assert "DISARM" in operations.events
    assert operations.events[-1] == "TERMINAL:SOURCE_PROJECTION_FAILED_ENGINEERING_NO_MARKET_VERDICT"
    assert supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 is None


def test_metadata_mutation_before_or_after_publish_cannot_pass():
    packet = _verified_packet()
    bad = {name: "F" * 64 for name in supervisor.METADATA_FILES}
    pre = _Operations(pre_map=bad)
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = packet.detached_sha256
    with pytest.raises(Exception):
        supervisor.run_one_shot_for_testing(packet, pre)
    assert pre.published is False

    post = _Operations(post_map=bad)
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = packet.detached_sha256
    with pytest.raises(Exception):
        supervisor.run_one_shot_for_testing(packet, post)
    assert post.published is True
    assert post.events[-1] == "TERMINAL:SOURCE_PROJECTION_FAILED_ENGINEERING_NO_MARKET_VERDICT"


def test_workspace_relative_paths_existing_roots_and_no_replace_publish(tmp_path):
    stage, final, evidence = supervisor.preflight_synthetic_paths(
        tmp_path,
        "data/stage",
        "data/final",
        "evidence/attempt",
    )
    assert stage.is_absolute() and final.is_absolute() and evidence.is_absolute()
    with pytest.raises(Exception):
        supervisor.preflight_synthetic_paths(tmp_path, "../escape", "data/final", "evidence/attempt")
    stage.mkdir(parents=True)
    final.mkdir(parents=True)
    with pytest.raises(Exception):
        supervisor.publish_no_replace(stage, final)


@pytest.mark.parametrize("occupied", ["stage", "final", "evidence"])
def test_preflight_rejects_each_existing_attempt_root(tmp_path, occupied):
    paths = {
        "stage": tmp_path / "data/stage",
        "final": tmp_path / "data/final",
        "evidence": tmp_path / "evidence/attempt",
    }
    paths[occupied].mkdir(parents=True)
    with pytest.raises(Exception):
        supervisor.preflight_synthetic_paths(
            tmp_path, "data/stage", "data/final", "evidence/attempt"
        )


def test_self_disarm_rewrites_only_synthetic_runtime_copy(tmp_path):
    reviewed = "A" * 64
    runtime = tmp_path / "supervisor.py"
    runtime.write_bytes(
        b'before\nREVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = "' + reviewed.encode("ascii") + b'"\nafter\n'
    )
    result = supervisor.self_disarm_runtime(runtime, reviewed)
    assert runtime.read_bytes() == b"before\nREVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = None\nafter\n"
    assert result["supervisor_disarm_status"] == "DISARMED_NONE_VERIFIED"


def test_production_entry_has_concrete_operations_and_no_injection_surface():
    assert hasattr(supervisor, "ProductionOperations")
    assert tuple(inspect.signature(supervisor.supervise).parameters) == ("source_run_packet_path",)
    assert Path(supervisor.__file__).read_text(encoding="utf-8").count(
        "REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = None"
    ) == 1
    required = {
        "registry_path", "registry_sha256", "registry_row_index", "registry_row_sha256",
        "active_plan_path", "active_plan_sha256", "contract_v4_path", "contract_v4_sha256",
        "contract_v5_path", "contract_v5_sha256", "contract_v6_path", "contract_v6_sha256",
        "contract_v7_path", "contract_v7_sha256",
        "active_contract_bundle_path", "active_contract_bundle_sha256",
        "implementation_task_v1_path", "implementation_task_v1_sha256",
        "implementation_task_v2_path", "implementation_task_v2_sha256",
        "implementation_task_v3_path", "implementation_task_v3_sha256",
        "implementation_task_v4_path", "implementation_task_v4_sha256",
        "authority_amendment_v2_path", "authority_amendment_v2_sha256",
        "authority_amendment_v3_path", "authority_amendment_v3_sha256",
        "implementation_task_v5_path", "implementation_task_v5_sha256",
        "implementation_review_receipt_path", "implementation_review_receipt_sha256",
        "workspace_root_identity", "supervisor_review_base_sha256", "supervisor_runtime_sha256",
    }
    assert required.issubset(supervisor.SOURCE_RUN_PACKET_FIELDS)


class _EarlyFailureOperations(_Operations):
    def __init__(self, phase):
        super().__init__()
        self.phase = phase
        self.persistent_disarmed = False
        self.partial_marker = False

    def preflight(self, packet):
        self.events.append("PREFLIGHT")
        if self.phase == "preflight":
            raise ValueError("preflight failure")
        return {"packet": packet}

    def start(self, packet, context):
        self.events.append("START")
        if self.phase == "start":
            raise ValueError("before marker")
        if self.phase == "partial_marker":
            self.partial_marker = True
            raise ValueError("after marker write")
        return super().start(packet, context)

    def reconcile_marker(self, packet, context):
        self.events.append("RECONCILE")
        if self.partial_marker:
            return {"attempt_state": "ATTEMPT_CONSUMED"}, "A" * 64
        return None

    def disarm(self, packet, context):
        self.events.append("DISARM")
        self.persistent_disarmed = True
        return {"supervisor_disarm_status": "DISARMED_NONE_VERIFIED", "supervisor_disarmed_sha256": "C" * 64}


@pytest.mark.parametrize("phase,terminal", [("preflight", False), ("start", False), ("partial_marker", True)])
def test_accepted_packet_persistently_disarms_on_all_early_exits(phase, terminal):
    packet = _verified_packet()
    operations = _EarlyFailureOperations(phase)
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = packet.detached_sha256
    with pytest.raises(Exception):
        supervisor.run_one_shot_for_testing(packet, operations)
    assert operations.persistent_disarmed is True
    assert ("TERMINAL:SOURCE_PROJECTION_FAILED_ENGINEERING_NO_MARKET_VERDICT" in operations.events) is terminal
    assert supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 is None


def test_ancestor_guard_rejects_symlink_and_detects_identity_drift(tmp_path, monkeypatch):
    assert hasattr(supervisor, "bind_existing_ancestor_chain")
    assert hasattr(supervisor, "verify_existing_ancestor_chain")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    real = workspace / "real"
    real.mkdir()
    link = workspace / "link"
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError:
        pass
    else:
        with pytest.raises(Exception):
            supervisor.bind_existing_ancestor_chain(workspace, link / "stage")

    parent = workspace / "safe"
    parent.mkdir()
    anchors = supervisor.bind_existing_ancestor_chain(workspace, parent / "stage")
    original = supervisor._directory_identity
    calls = {"count": 0}

    def drift(info):
        value = original(info)
        calls["count"] += 1
        return value if calls["count"] == 1 else (value[0], value[1] + 1, *value[2:])

    monkeypatch.setattr(supervisor, "_directory_identity", drift)
    with pytest.raises(Exception):
        supervisor.verify_existing_ancestor_chain(anchors)


def test_ancestor_guard_deterministically_rejects_mocked_reparse_ancestor(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    ancestor = workspace / "ancestor"
    ancestor.mkdir(parents=True)
    target_inode = ancestor.stat().st_ino
    original = supervisor._reparse
    monkeypatch.setattr(
        supervisor, "_reparse",
        lambda info: int(info.st_ino) == int(target_inode) or original(info),
    )
    with pytest.raises(Exception):
        supervisor.bind_existing_ancestor_chain(workspace, ancestor / "stage")


def _compact_registry_row(value):
    return json.dumps(
        value, sort_keys=False, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8") + b"\n"


def _authorized_registry_row(packet, prior):
    row = json.loads(json.dumps(prior))
    row["reason"] = (
        "Authorize the unchanged synthetic source projection after the reviewed "
        "pre-packet persistent-disarm repair; economics remain closed."
    )
    row["updated_at_utc"] = "2026-07-28T23:59:59Z"
    row["verdict"] = (
        "FROZEN_SINGLE_1200_BAR_SOURCE_RUN_AUTHORIZED_AFTER_PREARM_DISARM_REPAIR"
    )
    row["validation"]["probe_status"] = (
        "FROZEN_ONE_SHOT_SOURCE_PROJECTION_AUTHORIZED_AFTER_PREARM_DISARM_REPAIR"
    )
    bindings = row["validation"]["source_run_bindings"]
    for row_key, packet_key in supervisor.SOURCE_RUN_BINDING_TO_PACKET.items():
        bindings[row_key] = packet[packet_key]
    bindings.update(supervisor.SOURCE_RUN_BINDING_CONSTANTS)
    return row


def _mutate_registry_row(row, mutation):
    if mutation is None:
        return
    if mutation == "unauthorized":
        row["validation"]["source_run_authorized"] = False
    elif mutation == "state":
        row["state"] = "idea"
    elif mutation == "verdict":
        row["verdict"] = "FROZEN_SOURCE_IMPLEMENTATION_ONLY"
    elif mutation == "prereg":
        row["prereg_sha256"] = "F" * 64
    elif mutation == "metrics":
        row["metrics"]["economics_opened"] = True
    elif mutation == "validation":
        row["validation"]["performance_metrics_authorized"] = True
    elif mutation == "source":
        row["source_path"] = "unexpected/source.parquet"
    elif mutation == "run_ids":
        row["run_ids"] = ["unexpected"]
    elif mutation == "override_missing":
        row["validation"]["source_run_bindings"].pop("source_run_packet_review_required")
    elif mutation == "override_duplicate":
        row["validation"]["source_run_bindings"]["unexpected"] = False
    elif mutation == "override_mismatch":
        row["validation"]["source_run_bindings"]["source_projection_attempt_limit"] = 2
    else:
        raise AssertionError(mutation)


def _concrete_production_case(
    tmp_path,
    monkeypatch,
    bundle_v7_mutation=None,
    registry_mutation=None,
    later_hyp007=False,
    task_v4_schema="trendstack_007_source_implementation_task_packet.v4",
):
    import pyarrow as pa
    import pyarrow.parquet as pq
    import project_trendstack_007_design_source as projector
    import validate_trendstack_007_design_source as validator
    from test_project_trendstack_007_design_source import _row

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    def write(relative, payload):
        path = workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path

    def rel(path):
        return path.relative_to(workspace).as_posix()

    schema = pa.schema([
        pa.field("time_server", pa.timestamp("ns"), nullable=True),
        pa.field("time_utc", pa.timestamp("ns"), nullable=True),
        pa.field("utc_offset_h", pa.int8(), nullable=True),
        pa.field("open", pa.float64(), nullable=True), pa.field("high", pa.float64(), nullable=True),
        pa.field("low", pa.float64(), nullable=True), pa.field("close", pa.float64(), nullable=True),
        pa.field("tick_volume", pa.uint64(), nullable=True),
        pa.field("spread", pa.int32(), nullable=True),
        pa.field("real_volume", pa.uint64(), nullable=True),
    ])
    selected = ("2016-01-04", "2016-01-05")
    extra = ("2016-01-06",)
    all_dates = selected + extra
    manifest_rows = []
    for day in all_dates:
        table = pa.Table.from_pylist([_row(day, 11), _row(day, 12)], schema=schema)
        sink = pa.BufferOutputStream()
        pq.write_table(table, sink, row_group_size=2, compression="NONE", use_dictionary=False)
        payload = sink.getvalue().to_pybytes()
        write(f"data/public/DESIGN/{day}/h1.parquet", payload)
        manifest_rows.append({
            "bytes": len(payload), "date": day,
            "relative_path": f"public/DESIGN/{day}/h1.parquet", "rows": 2,
            "schema_version": "h1_splitvault_002_public_design_shard.v1",
            "sha256": _sha(payload),
        })
    manifest_payload = b"".join(supervisor.canonical_json(row) + b"\n" for row in manifest_rows)
    manifest_path = write("data/public/design_manifest.jsonl", manifest_payload)
    receipt_payload = supervisor.canonical_json({
        "collection_id": "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002",
        "design_dates": len(all_dates), "design_manifest_sha256": _sha(manifest_payload),
        "raw_source_opens": 1, "research_holdout_opened": False,
        "research_validation_opened": False, "schema_version": "h1_splitvault_002_public_receipt.v1",
        "source_attempt_id": "HYP006-SOURCE-ATTEMPT-ABCDEF1234567890", "source_rows": 6,
        "unselected_shard_opens": 0, "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
    }) + b"\n"
    receipt_path = write("data/public/design_receipt.json", receipt_payload)
    selection_payload = b"".join(
        supervisor.canonical_json({"date": day, "schema_version": "trendstack_006_design_date_selection.v1"}) + b"\n"
        for day in selected
    )
    selection_path = write("authority/selection.jsonl", selection_payload)
    date_set_sha = _sha(
        b"trendstack_002_design_date_set.v1\n"
        + b"".join(day.encode("ascii") + b"\n" for day in selected)
    )

    simple_documents = {}
    for name in (
        "active_plan", "contract_v4", "contract_v5", "contract_v6", "contract_v7",
        "active_contract_bundle", "implementation_task_v1", "implementation_task_v2",
        "implementation_task_v3", "implementation_task_v4",
    ):
        simple_documents[name] = write(
            f"authority/{name}.json",
            supervisor.canonical_json({"schema_version": f"synthetic_{name}.v1"}) + b"\n",
        )
    repository_root = Path(__file__).resolve().parents[4]
    for name in (
        "authority_amendment_v2", "authority_amendment_v3", "implementation_task_v5",
        "authority_repair_amendment_v4", "implementation_task_v6",
    ):
        relative = supervisor.SOURCE_RUN_PACKET_DEFAULTS[name + "_path"]
        simple_documents[name] = write(relative, (repository_root / relative).read_bytes())
    receipt_binding_files = {
        name: write(relative, (repository_root / relative).read_bytes())
        for name, relative in supervisor.RECEIPT_V6_BINDING_PATHS.items()
    }
    simple_documents["implementation_review_receipt"] = write(
        "03. EA Developer/EA_TrendStackContinuation/research/"
        "HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT_V6.json",
        b"{}\n",
    )
    bundle_contracts = [
            {"path": rel(simple_documents["contract_v4"]), "role": "base_v4", "sha256": _sha(simple_documents["contract_v4"].read_bytes())},
            {"path": rel(simple_documents["contract_v5"]), "role": "output_schema_v5", "sha256": _sha(simple_documents["contract_v5"].read_bytes())},
            {"path": rel(simple_documents["contract_v6"]), "role": "metadata_map_v6", "sha256": _sha(simple_documents["contract_v6"].read_bytes())},
            {"path": rel(simple_documents["contract_v7"]), "role": "terminal_tree_v7", "sha256": _sha(simple_documents["contract_v7"].read_bytes())},
    ]
    if bundle_v7_mutation == "missing":
        bundle_contracts.pop()
    elif bundle_v7_mutation == "wrong_path":
        bundle_contracts[-1]["path"] = "authority/wrong_v7.json"
    elif bundle_v7_mutation == "wrong_hash":
        bundle_contracts[-1]["sha256"] = "F" * 64
    elif bundle_v7_mutation is not None:
        raise AssertionError(bundle_v7_mutation)
    simple_documents["active_contract_bundle"].write_bytes(supervisor.canonical_json({
        "contracts": bundle_contracts,
        "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-007",
        "schema_version": "trendstack_007_active_source_contract_bundle.v2",
    }) + b"\n")
    simple_documents["implementation_task_v1"].write_bytes(supervisor.canonical_json({
        "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-007",
        "schema_version": "trendstack_007_source_implementation_task_packet.v1",
    }) + b"\n")
    simple_documents["implementation_task_v2"].write_bytes(supervisor.canonical_json({
        "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-007",
        "schema_version": "trendstack_007_source_implementation_task_packet.v2",
    }) + b"\n")
    simple_documents["implementation_task_v3"].write_bytes(supervisor.canonical_json({
        "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-007",
        "schema_version": "trendstack_007_source_implementation_task_packet.v3",
    }) + b"\n")
    simple_documents["implementation_task_v4"].write_bytes(supervisor.canonical_json({
        "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-007",
        "schema_version": task_v4_schema,
    }) + b"\n")
    clock_path = write(
        "tools/clock.py",
        b"from datetime import timedelta\n"
        b"def server_offset_hours(value): return 2\n"
        b"def server_to_utc(value): return value - timedelta(hours=2)\n",
    )
    projector_path = write("tools/projector.py", Path(projector.__file__).read_bytes())
    validator_path = write("tools/validator.py", Path(validator.__file__).read_bytes())
    projector_test_path = write(
        "tests/test_projector.py",
        Path(__file__).with_name("test_project_trendstack_007_design_source.py").read_bytes(),
    )
    validator_test_path = write(
        "tests/test_validator.py",
        Path(__file__).with_name("test_validate_trendstack_007_design_source.py").read_bytes(),
    )
    supervisor_test_path = write("tests/test_supervisor.py", Path(__file__).read_bytes())
    runtime_path = write("tools/supervisor.py", Path(supervisor.__file__).read_bytes())
    review_base = runtime_path.read_bytes()
    simple_documents["implementation_review_receipt"].write_bytes(
        supervisor.canonical_json({
            "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-007",
            "reviewed_authority": {
                "authority_repair_amendment_v4_sha256": _sha(
                    simple_documents["authority_repair_amendment_v4"].read_bytes()
                ),
                "implementation_task_v6_sha256": _sha(
                    simple_documents["implementation_task_v6"].read_bytes()
                ),
            },
            "reviewed_snapshot": {
                "registry_schema_sha256": _sha(receipt_binding_files["registry_schema"].read_bytes()),
                "registry_validator_sha256": _sha(receipt_binding_files["registry_validator"].read_bytes()),
                "registry_integration_test_sha256": _sha(
                    receipt_binding_files["registry_integration_test"].read_bytes()
                ),
                "supervisor_review_base_sha256": _sha(review_base),
                "supervisor_test_sha256": _sha(supervisor_test_path.read_bytes()),
            },
            "schema_version": "trendstack_007_source_implementation_review_receipt.v6",
            "verdict": "PASS_FOR_PRODUCTION_SOURCE_RUN_PACKET_PREPARATION",
        }) + b"\n"
    )

    packet = dict(supervisor.SOURCE_RUN_PACKET_DEFAULTS)
    for field in supervisor.SOURCE_RUN_PACKET_FIELDS:
        if field.endswith("_sha256"):
            packet.setdefault(field, "A" * 64)
        elif field.endswith("_path") or field.endswith("_root"):
            packet.setdefault(field, "synthetic/" + field)
    packet.update({
        "workspace_root_path": ".", "workspace_root_identity": list(supervisor._directory_identity(workspace.stat())),
        "registry_row_index": 287, "expected_dates": len(selected),
        "expected_unselected_dates": len(extra), "expected_date_set_sha256": date_set_sha,
        "first_date": selected[0], "last_date": selected[-1],
        "stage_root": "output/stage", "final_output_root": "output/final",
        "evidence_root": "evidence/attempt",
    })

    def bind(prefix, path):
        packet[prefix + "_path"] = rel(path)
        packet[prefix + "_sha256"] = _sha(path.read_bytes())

    bind("active_plan", simple_documents["active_plan"])
    for name in ("contract_v4", "contract_v5", "contract_v6", "contract_v7", "active_contract_bundle"):
        bind(name, simple_documents[name])
    bind("implementation_task_v1", simple_documents["implementation_task_v1"])
    bind("implementation_task_v2", simple_documents["implementation_task_v2"])
    bind("implementation_task_v3", simple_documents["implementation_task_v3"])
    bind("implementation_task_v4", simple_documents["implementation_task_v4"])
    bind("authority_amendment_v2", simple_documents["authority_amendment_v2"])
    bind("authority_amendment_v3", simple_documents["authority_amendment_v3"])
    bind("implementation_task_v5", simple_documents["implementation_task_v5"])
    bind("authority_repair_amendment_v4", simple_documents["authority_repair_amendment_v4"])
    bind("implementation_task_v6", simple_documents["implementation_task_v6"])
    bind("implementation_review_receipt", simple_documents["implementation_review_receipt"])
    bind("projector_tool", projector_path); bind("projector_test", projector_test_path)
    bind("validator_tool", validator_path); bind("validator_test", validator_test_path)
    bind("supervisor_test", supervisor_test_path); bind("clock", clock_path)
    bind("public_receipt", receipt_path); bind("public_manifest", manifest_path)
    bind("selection_manifest", selection_path)
    packet["active_contract_path"] = packet["active_contract_bundle_path"]
    packet["active_contract_sha256"] = packet["active_contract_bundle_sha256"]
    packet["task_packet_path"] = packet["implementation_task_v4_path"]
    packet["task_packet_sha256"] = packet["implementation_task_v4_sha256"]
    packet["supervisor_tool_path"] = rel(runtime_path)
    packet["supervisor_runtime_path"] = rel(runtime_path)
    packet["supervisor_review_base_sha256"] = _sha(review_base)
    packet["supervisor_tool_sha256"] = _sha(review_base)
    packet["supervisor_runtime_sha256"] = "A" * 64
    repository_rows = (
        repository_root / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    ).read_bytes().splitlines(keepends=True)
    actual_row286 = json.loads(repository_rows[285])
    actual_prior_bindings = actual_row286["validation"]["source_run_bindings"]
    successor_bindings = {
        row_key: packet[packet_key]
        for row_key, packet_key in supervisor.SOURCE_RUN_BINDING_TO_PACKET.items()
    }
    successor_bindings.update(supervisor.SOURCE_RUN_BINDING_CONSTANTS)
    synthetic_prior = json.loads(json.dumps(actual_row286))
    synthetic_prior["validation"]["source_run_bindings"] = json.loads(
        json.dumps(successor_bindings)
    )
    for key in supervisor.HYP007_REPAIR_BINDING_CHANGES:
        synthetic_prior["validation"]["source_run_bindings"][key] = actual_prior_bindings[key]
    prior_row = _compact_registry_row(synthetic_prior)
    monkeypatch.setattr(
        supervisor, "HYP007_AUTHORIZED_ROW_SHA256", _sha(prior_row[:-1])
    )
    registry_row_value = _authorized_registry_row(packet, synthetic_prior)
    _mutate_registry_row(registry_row_value, registry_mutation)
    registry_row = _compact_registry_row(registry_row_value)
    padding = b"".join(
        _compact_registry_row({"record_type": "padding", "index": index})
        for index in range(1, 285)
    )
    row285 = repository_rows[284]
    registry_payload = padding + row285 + prior_row + registry_row
    if later_hyp007:
        registry_payload += _compact_registry_row({
            "record_type": "hypothesis_state",
            "schema_version": "alphafactory_candidate_registry.v1",
            "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-007",
        })
    registry_path = write("authority/registry.jsonl", registry_payload)
    bind("registry", registry_path)
    packet["registry_row_sha256"] = _sha(registry_row[:-1])
    packet["reviewed_source_run_packet_sha256"] = "0" * 64
    detached = supervisor.compute_source_run_packet_sha256(packet)
    armed = review_base.replace(
        b"REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = None",
        b'REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = "' + detached.encode("ascii") + b'"',
    )
    assert armed != review_base
    runtime_path.write_bytes(armed)
    packet["supervisor_runtime_sha256"] = _sha(armed)
    packet["reviewed_source_run_packet_sha256"] = detached
    assert supervisor.compute_source_run_packet_sha256(packet) == detached
    verified = supervisor.VerifiedSourceRunPacket(
        packet, detached, supervisor.canonical_json(packet) + b"\n"
    )
    return {
        "packet": verified, "runtime": runtime_path, "workspace": workspace,
        "authority": simple_documents, "registry_payload": registry_payload,
        "registry_prior": prior_row, "registry_prior_value": synthetic_prior,
        "registry_row": registry_row,
    }


def _rebind_case_after_receipt_mutation(case, mutate):
    receipt = case["authority"]["implementation_review_receipt"]
    document = json.loads(receipt.read_bytes())
    mutate(document)
    receipt.write_bytes(supervisor.canonical_json(document) + b"\n")

    values = dict(case["packet"].values)
    receipt_sha = _sha(receipt.read_bytes())
    values["implementation_review_receipt_sha256"] = receipt_sha
    row = json.loads(case["registry_row"])
    row["validation"]["source_run_bindings"][
        "implementation_review_receipt_sha256"
    ] = receipt_sha
    row_payload = _compact_registry_row(row)
    registry_payload = case["registry_payload"][: -len(case["registry_row"])] + row_payload
    registry_path = case["workspace"] / values["registry_path"]
    registry_path.write_bytes(registry_payload)
    values["registry_sha256"] = _sha(registry_payload)
    values["registry_row_sha256"] = _sha(row_payload[:-1])

    old_armed = (
        b'REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = "'
        + case["packet"].detached_sha256.encode("ascii")
        + b'"'
    )
    disarmed = b"REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = None"
    review_base = case["runtime"].read_bytes().replace(old_armed, disarmed)
    values["reviewed_source_run_packet_sha256"] = "0" * 64
    detached = supervisor.compute_source_run_packet_sha256(values)
    runtime = review_base.replace(
        disarmed,
        b'REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = "'
        + detached.encode("ascii")
        + b'"',
    )
    case["runtime"].write_bytes(runtime)
    values["supervisor_runtime_sha256"] = _sha(runtime)
    values["reviewed_source_run_packet_sha256"] = detached
    assert supervisor.compute_source_run_packet_sha256(values) == detached
    return supervisor.VerifiedSourceRunPacket(
        values, detached, supervisor.canonical_json(values) + b"\n"
    )


def test_synthetic_latest_authorized_registry_row_passes_exact_semantics_and_bindings(tmp_path, monkeypatch):
    case = _concrete_production_case(tmp_path, monkeypatch)
    selected = supervisor.validate_registry_source_run_authority(
        case["registry_payload"], case["packet"].values
    )
    assert selected["verdict"] == (
        "FROZEN_SINGLE_1200_BAR_SOURCE_RUN_AUTHORIZED_AFTER_PREARM_DISARM_REPAIR"
    )
    assert selected["validation"]["source_run_authorized"] is True


def test_actual_row286_is_hashable_but_cannot_authorize_repaired_source_run(tmp_path, monkeypatch):
    case = _concrete_production_case(tmp_path, monkeypatch)
    registry = Path(__file__).resolve().parents[4] / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    payload = registry.read_bytes()
    values = dict(case["packet"].values)
    values["registry_sha256"] = _sha(payload)
    values["registry_row_index"] = 286
    values["registry_row_sha256"] = "17512FE256454130E3EAE26D2372818631487D67EEB0F8B414D255FE2D5CA06E"
    with pytest.raises(Exception):
        supervisor.validate_registry_source_run_authority(payload, values)


def test_registry_authority_rejects_wrong_hash_stale_row_and_semantic_or_binding_drift(tmp_path, monkeypatch):
    case = _concrete_production_case(tmp_path, monkeypatch)
    base_values = dict(case["packet"].values)

    wrong_hash = dict(base_values)
    wrong_hash["registry_row_sha256"] = "F" * 64
    with pytest.raises(Exception):
        supervisor.validate_registry_source_run_authority(case["registry_payload"], wrong_hash)

    stale_payload = case["registry_payload"] + _compact_registry_row({
        "record_type": "hypothesis_state",
        "schema_version": "alphafactory_candidate_registry.v1",
        "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-007",
    })
    with pytest.raises(Exception):
        supervisor.validate_registry_source_run_authority(stale_payload, base_values)

    for mutation in (
        "unauthorized", "state", "verdict", "prereg", "metrics", "validation",
        "source", "run_ids", "override_missing", "override_duplicate", "override_mismatch",
    ):
        row = _authorized_registry_row(base_values, case["registry_prior_value"])
        _mutate_registry_row(row, mutation)
        row_payload = _compact_registry_row(row)
        payload = case["registry_payload"][: -len(case["registry_row"])] + row_payload
        values = dict(base_values)
        values["registry_sha256"] = _sha(payload)
        values["registry_row_sha256"] = _sha(row_payload[:-1])
        with pytest.raises(Exception, match="INVALID_SOURCE_PROJECTION"):
            supervisor.validate_registry_source_run_authority(payload, values)


def test_concrete_production_operations_end_to_end_on_synthetic_tmp(tmp_path, monkeypatch):
    case = _concrete_production_case(tmp_path, monkeypatch)
    operations = supervisor.ProductionOperations.for_testing(case["packet"], case["workspace"])
    original_project = operations.project

    def marker_checked_project(packet, marker, context):
        assert (case["workspace"] / "evidence/attempt/attempt_started.json").is_file()
        return original_project(packet, marker, context)

    monkeypatch.setattr(operations, "project", marker_checked_project)
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = case["packet"].detached_sha256
    result = supervisor.run_one_shot_for_testing(case["packet"], operations)

    assert result["verdict"] == "ENGINEERING_VALID_SOURCE_PROJECTION"
    assert (case["workspace"] / "output/final").is_dir()
    assert not (case["workspace"] / "output/stage").exists()
    assert (case["workspace"] / "evidence/attempt/attempt_terminal.json").is_file()
    assert b"REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = None" in case["runtime"].read_bytes()
    validation = json.loads((case["workspace"] / "evidence/attempt/validation_receipt.json").read_bytes())
    terminal = json.loads((case["workspace"] / "evidence/attempt/attempt_terminal.json").read_bytes())
    assert validation["validator_access"]["active_contract_reads"] == 1
    assert validation["validator_access"]["task_packet_reads"] == 1
    assert terminal["validated_file_identities_sha256"] == validation["validated_file_identities_sha256"]
    expected_terminal_fields = {
        "attempt_started_sha256", "completed_at_utc", "data_tree_sha256", "economics_opened",
        "final_output_root", "final_output_root_identity", "hypothesis_id", "manifest_sha256",
        "market_verdict", "post_publish_metadata_hashes", "post_publish_output_shard_lstats",
        "projection_attempt_id", "projector_receipt_sha256", "reconciliation_sha256",
        "research_holdout_opened", "research_validation_opened", "schema_version",
        "source_projection_attempts_consumed", "supervisor_disarm_status",
        "supervisor_disarmed_sha256", "trace_sha256", "validated_file_identities_sha256",
        "validation_receipt_sha256", "verdict",
    }
    assert set(terminal) == expected_terminal_fields
    assert terminal["schema_version"] == "trendstack_007_projection_attempt_terminal_pass.v2"


def test_concrete_preflight_hash_drift_persistently_disarms_runtime(tmp_path, monkeypatch):
    case = _concrete_production_case(tmp_path, monkeypatch)
    case["authority"]["active_plan"].write_bytes(b"drift")
    operations = supervisor.ProductionOperations.for_testing(case["packet"], case["workspace"])
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = case["packet"].detached_sha256
    with pytest.raises(Exception):
        supervisor.run_one_shot_for_testing(case["packet"], operations)
    assert b"REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = None" in case["runtime"].read_bytes()
    assert not (case["workspace"] / "evidence/attempt/attempt_started.json").exists()


def test_concrete_preflight_rejects_full_registry_hash_drift(tmp_path, monkeypatch):
    case = _concrete_production_case(tmp_path, monkeypatch)
    registry = case["workspace"] / case["packet"].values["registry_path"]
    registry.write_bytes(registry.read_bytes() + _compact_registry_row({"record_type": "audit"}))
    operations = supervisor.ProductionOperations.for_testing(case["packet"], case["workspace"])
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = case["packet"].detached_sha256
    with pytest.raises(Exception):
        supervisor.run_one_shot_for_testing(case["packet"], operations)
    assert b"REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = None" in case["runtime"].read_bytes()
    assert not (case["workspace"] / "evidence/attempt/attempt_started.json").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("economics_authorized", True),
        ("final_output_root", "output/other-final"),
        ("selection_manifest_sha256", "F" * 64),
        ("authority_repair_amendment_v4_sha256", "F" * 64),
        ("implementation_task_v6_sha256", "F" * 64),
        ("supervisor_tool_sha256", "F" * 64),
    ],
)
def test_row_packet_mapping_mismatch_fails_before_marker_or_parquet_open(
    tmp_path, monkeypatch, field, value
):
    case = _concrete_production_case(tmp_path, monkeypatch)
    values = dict(case["packet"].values)
    values[field] = value
    values["reviewed_source_run_packet_sha256"] = "0" * 64
    detached = supervisor.compute_source_run_packet_sha256(values)
    old_armed = (
        b'REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = "'
        + case["packet"].detached_sha256.encode("ascii") + b'"'
    )
    disarmed = b"REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = None"
    review_base = case["runtime"].read_bytes().replace(old_armed, disarmed)
    new_runtime = review_base.replace(
        disarmed,
        b'REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = "' + detached.encode("ascii") + b'"',
    )
    case["runtime"].write_bytes(new_runtime)
    values["supervisor_runtime_sha256"] = _sha(new_runtime)
    values["reviewed_source_run_packet_sha256"] = detached
    packet = supervisor.VerifiedSourceRunPacket(
        values, detached, supervisor.canonical_json(values) + b"\n"
    )
    operations = supervisor.ProductionOperations.for_testing(packet, case["workspace"])
    real_open = supervisor.os.open
    parquet_opens = []

    def reject_parquet(path, flags, *args, **kwargs):
        if str(path).lower().endswith(".parquet"):
            parquet_opens.append(str(path))
            raise AssertionError("preflight opened Parquet")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(supervisor.os, "open", reject_parquet)
    with pytest.raises(Exception):
        operations.preflight(packet)
    assert parquet_opens == []
    assert not (case["workspace"] / "evidence/attempt/attempt_started.json").exists()
    assert not (case["workspace"] / "output/stage").exists()
    assert not (case["workspace"] / "output/final").exists()


@pytest.mark.parametrize(
    "mutation",
    [
        "registry_schema",
        "registry_validator",
        "registry_integration_test",
        "supervisor_review_base",
        "supervisor_test",
        "forbidden_full_registry",
    ],
)
def test_v6_receipt_binding_or_forbidden_registry_identity_fails_pre_marker_pre_payload(
    tmp_path, monkeypatch, mutation
):
    case = _concrete_production_case(tmp_path, monkeypatch)

    def mutate(document):
        if mutation == "forbidden_full_registry":
            document["registry_sha256"] = "F" * 64
        else:
            key = {
                "registry_schema": "registry_schema_sha256",
                "registry_validator": "registry_validator_sha256",
                "registry_integration_test": "registry_integration_test_sha256",
                "supervisor_review_base": "supervisor_review_base_sha256",
                "supervisor_test": "supervisor_test_sha256",
            }[mutation]
            document["reviewed_snapshot"][key] = "F" * 64

    packet = _rebind_case_after_receipt_mutation(case, mutate)
    operations = supervisor.ProductionOperations.for_testing(packet, case["workspace"])
    real_open = supervisor.os.open
    parquet_opens = []

    def reject_parquet(path, flags, *args, **kwargs):
        if str(path).lower().endswith(".parquet"):
            parquet_opens.append(str(path))
            raise AssertionError("receipt validation opened Parquet")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(supervisor.os, "open", reject_parquet)
    with pytest.raises(Exception):
        operations.preflight(packet)
    assert parquet_opens == []
    assert not (case["workspace"] / "evidence/attempt/attempt_started.json").exists()
    assert not (case["workspace"] / "output/stage").exists()
    assert not (case["workspace"] / "output/final").exists()


@pytest.mark.parametrize(
    "authority_name",
    [
        "authority_amendment_v2", "authority_amendment_v3", "implementation_task_v5",
        "authority_repair_amendment_v4", "implementation_task_v6",
    ],
)
def test_concrete_preflight_rejects_stale_authority_or_task_file(tmp_path, monkeypatch, authority_name):
    case = _concrete_production_case(tmp_path, monkeypatch)
    case["authority"][authority_name].write_bytes(b"drift")
    operations = supervisor.ProductionOperations.for_testing(case["packet"], case["workspace"])
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = case["packet"].detached_sha256
    with pytest.raises(Exception):
        supervisor.run_one_shot_for_testing(case["packet"], operations)
    assert b"REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = None" in case["runtime"].read_bytes()
    assert not (case["workspace"] / "evidence/attempt/attempt_started.json").exists()


def test_concrete_preflight_rejects_superseded_task_v3_schema_as_active_v4(tmp_path, monkeypatch):
    case = _concrete_production_case(
        tmp_path, monkeypatch, task_v4_schema="trendstack_007_source_implementation_task_packet.v3"
    )
    operations = supervisor.ProductionOperations.for_testing(case["packet"], case["workspace"])
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = case["packet"].detached_sha256
    with pytest.raises(Exception):
        supervisor.run_one_shot_for_testing(case["packet"], operations)
    assert b"REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = None" in case["runtime"].read_bytes()
    assert not (case["workspace"] / "evidence/attempt/attempt_started.json").exists()


@pytest.mark.parametrize("mutation", ["missing", "wrong_path", "wrong_hash"])
def test_concrete_preflight_rejects_inexact_v7_bundle_binding(tmp_path, monkeypatch, mutation):
    case = _concrete_production_case(tmp_path, monkeypatch, bundle_v7_mutation=mutation)
    operations = supervisor.ProductionOperations.for_testing(case["packet"], case["workspace"])
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = case["packet"].detached_sha256
    with pytest.raises(Exception):
        supervisor.run_one_shot_for_testing(case["packet"], operations)
    assert b"REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = None" in case["runtime"].read_bytes()
    assert not (case["workspace"] / "evidence/attempt/attempt_started.json").exists()


def test_concrete_partial_marker_failure_reconciles_terminal_and_disarms(tmp_path, monkeypatch):
    case = _concrete_production_case(tmp_path, monkeypatch)
    operations = supervisor.ProductionOperations.for_testing(case["packet"], case["workspace"])
    original = operations.start

    def partial(packet, context):
        original(packet, context)
        raise ValueError("synthetic after durable marker")

    monkeypatch.setattr(operations, "start", partial)
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = case["packet"].detached_sha256
    with pytest.raises(Exception):
        supervisor.run_one_shot_for_testing(case["packet"], operations)
    terminal = json.loads((case["workspace"] / "evidence/attempt/attempt_terminal.json").read_bytes())
    assert terminal["verdict"] == "SOURCE_PROJECTION_FAILED_ENGINEERING_NO_MARKET_VERDICT"
    assert b"REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = None" in case["runtime"].read_bytes()


def test_concrete_start_before_marker_failure_persistently_disarms_without_terminal(tmp_path, monkeypatch):
    case = _concrete_production_case(tmp_path, monkeypatch)
    operations = supervisor.ProductionOperations.for_testing(case["packet"], case["workspace"])
    monkeypatch.setattr(
        operations, "start",
        lambda packet, context: (_ for _ in ()).throw(ValueError("before marker")),
    )
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = case["packet"].detached_sha256
    with pytest.raises(Exception):
        supervisor.run_one_shot_for_testing(case["packet"], operations)
    assert b"REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = None" in case["runtime"].read_bytes()
    assert not (case["workspace"] / "evidence/attempt/attempt_terminal.json").exists()


def test_concrete_prepublish_rejects_same_bytes_shard_replacement(tmp_path, monkeypatch):
    case = _concrete_production_case(tmp_path, monkeypatch)
    packet = case["packet"]
    operations = supervisor.ProductionOperations.for_testing(packet, case["workspace"])
    context = operations.preflight(packet)
    marker, _ = operations.start(packet, context)
    projected = operations.project(packet, marker, context)
    operations.validate(packet, projected, context)
    shard = next((case["workspace"] / "output/stage/DESIGN").rglob("*.parquet"))
    payload = shard.read_bytes()
    shard.unlink()
    shard.write_bytes(payload)
    with pytest.raises(Exception):
        operations.pre_publish_metadata_hashes(packet, context)
    operations.disarm(packet, context)
    assert not (case["workspace"] / "output/final").exists()


def _add_extra_tree_entry(root, mutation):
    if mutation == "root_file":
        (root / "unexpected.txt").write_bytes(b"extra")
    elif mutation == "design_entry":
        (root / "DESIGN/unexpected.txt").write_bytes(b"extra")
    elif mutation == "day_file":
        day = next(entry for entry in (root / "DESIGN").iterdir() if entry.is_dir())
        (day / "unexpected.bin").write_bytes(b"extra")
    elif mutation == "extra_directory":
        (root / "UNEXPECTED_DIR").mkdir()
    else:
        raise AssertionError(mutation)


@pytest.mark.parametrize("mutation", ["root_file", "design_entry", "day_file", "extra_directory"])
def test_concrete_prepublish_rejects_every_extra_tree_class(tmp_path, monkeypatch, mutation):
    case = _concrete_production_case(tmp_path, monkeypatch)
    packet = case["packet"]
    operations = supervisor.ProductionOperations.for_testing(packet, case["workspace"])
    context = operations.preflight(packet)
    marker, _ = operations.start(packet, context)
    projected = operations.project(packet, marker, context)
    operations.validate(packet, projected, context)
    _add_extra_tree_entry(case["workspace"] / "output/stage", mutation)
    with pytest.raises(Exception):
        operations.pre_publish_metadata_hashes(packet, context)
    operations.disarm(packet, context)
    assert not (case["workspace"] / "output/final").exists()


@pytest.mark.parametrize("mutation", ["root_file", "design_entry", "day_file", "extra_directory"])
def test_concrete_postpublish_extra_tree_writes_failure_terminal(tmp_path, monkeypatch, mutation):
    case = _concrete_production_case(tmp_path, monkeypatch)
    operations = supervisor.ProductionOperations.for_testing(case["packet"], case["workspace"])
    original_post = operations.post_publish

    def mutated_post(packet, context):
        _add_extra_tree_entry(case["workspace"] / "output/final", mutation)
        return original_post(packet, context)

    monkeypatch.setattr(operations, "post_publish", mutated_post)
    supervisor.REVIEWED_SOURCE_RUN_PACKET_SHA256 = case["packet"].detached_sha256
    with pytest.raises(Exception):
        supervisor.run_one_shot_for_testing(case["packet"], operations)
    terminal = json.loads((case["workspace"] / "evidence/attempt/attempt_terminal.json").read_bytes())
    assert terminal["verdict"] == "SOURCE_PROJECTION_FAILED_ENGINEERING_NO_MARKET_VERDICT"
    assert terminal["market_verdict"] is None


def test_exact_tree_gate_opens_zero_parquet_payloads(tmp_path, monkeypatch):
    case = _concrete_production_case(tmp_path, monkeypatch)
    packet = case["packet"]
    operations = supervisor.ProductionOperations.for_testing(packet, case["workspace"])
    context = operations.preflight(packet)
    marker, _ = operations.start(packet, context)
    projected = operations.project(packet, marker, context)
    operations.validate(packet, projected, context)
    real_open = supervisor.os.open

    def no_parquet_open(path, flags, *args, **kwargs):
        if str(path).lower().endswith(".parquet"):
            raise AssertionError("supervisor exact-tree gate opened Parquet")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(supervisor.os, "open", no_parquet_open)
    hashes = operations.pre_publish_metadata_hashes(packet, context)
    assert set(hashes) == set(supervisor.METADATA_FILES)
    monkeypatch.setattr(supervisor.os, "open", real_open)
    operations.disarm(packet, context)
