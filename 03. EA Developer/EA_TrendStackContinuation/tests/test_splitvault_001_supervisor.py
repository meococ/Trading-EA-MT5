from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "research" / "splitvault_001_supervisor.py"
CUSTODIAN_PATH = ROOT / "research" / "splitvault_001_custodian.py"
BUILDER_PATH = ROOT / "research" / "build_trendstack_003_design_source.py"
VALIDATOR_PATH = ROOT / "research" / "validate_trendstack_003_design_source.py"
VALIDATOR_TEST_PATH = ROOT / "tests" / "test_validate_trendstack_003_design_source.py"
FROZEN_V2_NAME = "HYP-TRENDSTACK-EURUSD-H1-003_PROBE_PLAN_V2.md"
FROZEN_V3_NAME = "HYP-TRENDSTACK-EURUSD-H1-003_PROBE_PLAN_V3.md"
FROZEN_V4_NAME = "HYP-TRENDSTACK-EURUSD-H1-003_PROBE_PLAN_V4.md"
REGISTRY_NAME = "CANDIDATE_REGISTRY.jsonl"
REGISTRY_ROW_INDEX = 273
REGISTRY_ROW_SHA256 = "63EB8F7A618DCF9179D6BE558F91E264146BA5B4629A73FBB911AD8F4B5B5920"
ACTIVE_REGISTRY_PATH = ROOT.parents[1] / "04. Memory" / "research" / REGISTRY_NAME
SOURCE_ATTEMPT_ID = "HYP003-SOURCE-ATTEMPT-0123456789ABCDEF"
AUTHORITY_SENTINEL = b"REVIEWED_RUN_PACKET_SHA256: str | None = None"


def load_tool():
    spec = importlib.util.spec_from_file_location("splitvault_001_supervisor_test", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_path(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def bound_file(tmp_path: Path, name: str, payload: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(payload)
    return path


def armed_supervisor(review_base: bytes, packet_sha256: str) -> bytes:
    assert review_base.count(AUTHORITY_SENTINEL) == 1
    return review_base.replace(
        AUTHORITY_SENTINEL,
        f'REVIEWED_RUN_PACKET_SHA256: str | None = "{packet_sha256}"'.encode("ascii"),
    )


def frozen_registry_payload() -> bytes:
    lines = ACTIVE_REGISTRY_PATH.read_bytes().splitlines()
    assert sha256(lines[REGISTRY_ROW_INDEX - 1]) == REGISTRY_ROW_SHA256
    return b"\n".join(lines[:REGISTRY_ROW_INDEX]) + b"\n"


def refreeze_packet(tool, files, packet, packet_path):
    packet_path.write_bytes(canonical(packet) + b"\n")
    review_base = TOOL_PATH.read_bytes()
    files["supervisor_tool"].write_bytes(armed_supervisor(review_base, sha256(packet_path.read_bytes())))
    return tool.FrozenBindings.from_packet_for_testing(packet)


class DummyDesignCapability:
    def public_receipt_bytes(self):
        return b'{"verdict":"COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY"}\n'

    def public_manifest_bytes(self):
        return b'{"date":"2016-01-04","sha256":"' + b"A" * 64 + b'"}\n'


def design_provenance(packet: dict[str, object]) -> dict[str, object]:
    return {
        "source_attempt_id": packet["source_attempt_id"],
        "stage_path": packet["design_stage_path"],
        "stage_role": "DESIGN",
        "supervisor_review_base_sha256": packet["supervisor_review_base_sha256"],
    }


def custody_result(packet: dict[str, object]) -> dict[str, object]:
    return {
        "source_attempt_id": packet["source_attempt_id"],
        "stage_path": packet["custody_stage_path"],
        "stage_role": "CUSTODY",
        "supervisor_review_base_sha256": packet["supervisor_review_base_sha256"],
        "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
    }


def pending_result(packet: dict[str, object]) -> dict[str, object]:
    return {**design_provenance(packet), "verdict": "PENDING_INDEPENDENT_VALIDATION"}


def ready_result(packet: dict[str, object], **extra: object) -> dict[str, object]:
    return {
        **design_provenance(packet),
        **extra,
        "verdict": "SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET",
    }


def packet_fixture(tmp_path: Path, *, copied_tools: bool = False):
    tool = load_tool()
    review_base = TOOL_PATH.read_bytes()
    copied_supervisor = bound_file(tmp_path, "supervisor.py", review_base)
    if copied_tools:
        copied_custodian = bound_file(tmp_path, "custodian.py", CUSTODIAN_PATH.read_bytes())
        copied_builder = bound_file(tmp_path, "builder.py", BUILDER_PATH.read_bytes())
        copied_validator = bound_file(tmp_path, "validator.py", VALIDATOR_PATH.read_bytes())
    else:
        copied_custodian = CUSTODIAN_PATH
        copied_builder = BUILDER_PATH
        copied_validator = VALIDATOR_PATH
    evidence_parent = tmp_path / "evidence" / "HYP-TRENDSTACK-EURUSD-H1-003_SOURCE_ATTEMPTS"
    evidence_parent.mkdir(parents=True, exist_ok=True)
    files = {
        "collection_plan": bound_file(tmp_path, "collection.md", b"collection\n"),
        "hypothesis_plan": bound_file(tmp_path, "hypothesis.md", b"hypothesis\n"),
        "hypothesis_plan_v2": bound_file(tmp_path, FROZEN_V2_NAME, b"frozen v2\n"),
        "hypothesis_plan_v3": bound_file(tmp_path, FROZEN_V3_NAME, b"frozen v3\n"),
        "hypothesis_plan_v4": bound_file(tmp_path, FROZEN_V4_NAME, b"frozen v4\n"),
        "registry": bound_file(tmp_path, REGISTRY_NAME, frozen_registry_payload()),
        "source": bound_file(tmp_path, "source.parquet", b"PAR1synthetic-footerPAR1"),
        "source_manifest": bound_file(tmp_path, "manifest.json", b"{}\n"),
        "clock": bound_file(tmp_path, "clock.py", b"def server_to_utc(value): return value\n"),
        "parent_ledger": bound_file(tmp_path, "ledger.jsonl", b"{}\n"),
        "parent_receipt": bound_file(tmp_path, "receipt.json", b"{}\n"),
        "custodian_tool": copied_custodian,
        "supervisor_tool": copied_supervisor,
        "design_builder_tool": copied_builder,
        "validator_tool": copied_validator,
        "custodian_test": bound_file(tmp_path, "test_custodian.py", (ROOT / "tests" / "test_splitvault_001_custodian.py").read_bytes()),
        "supervisor_test": bound_file(tmp_path, "test_supervisor.py", (ROOT / "tests" / "test_splitvault_001_supervisor.py").read_bytes()),
        "design_builder_test": bound_file(tmp_path, "test_builder.py", (ROOT / "tests" / "test_build_trendstack_003_design_source.py").read_bytes()),
        "validator_test": bound_file(tmp_path, "test_validator.py", VALIDATOR_TEST_PATH.read_bytes()),
    }
    packet = {
        "schema_version": tool.RUN_PACKET_SCHEMA,
        "collection_id": tool.COLLECTION_ID,
        "hypothesis_id": tool.HYPOTHESIS_ID,
        "verdict": tool.RUN_PACKET_VERDICT,
        "collection_plan_path": str(files["collection_plan"].resolve()),
        "collection_plan_sha256": sha256(files["collection_plan"].read_bytes()),
        "hypothesis_plan_path": str(files["hypothesis_plan"].resolve()),
        "hypothesis_plan_sha256": sha256(files["hypothesis_plan"].read_bytes()),
        "hypothesis_plan_v2_path": str(files["hypothesis_plan_v2"].resolve()),
        "hypothesis_plan_v2_sha256": sha256(files["hypothesis_plan_v2"].read_bytes()),
        "hypothesis_plan_v3_path": str(files["hypothesis_plan_v3"].resolve()),
        "hypothesis_plan_v3_sha256": sha256(files["hypothesis_plan_v3"].read_bytes()),
        "hypothesis_plan_v4_path": str(files["hypothesis_plan_v4"].resolve()),
        "hypothesis_plan_v4_sha256": sha256(files["hypothesis_plan_v4"].read_bytes()),
        "registry_path": str(files["registry"].resolve()),
        "registry_sha256": sha256(files["registry"].read_bytes()),
        "registry_row_index": REGISTRY_ROW_INDEX,
        "registry_row_sha256": REGISTRY_ROW_SHA256,
        "source_attempt_id": SOURCE_ATTEMPT_ID,
        "attempt_evidence_root": str((evidence_parent / SOURCE_ATTEMPT_ID).resolve()),
        "custody_stage_path": str((tmp_path / (".vault.attempt-" + SOURCE_ATTEMPT_ID)).resolve()),
        "design_stage_path": str((tmp_path / (".design.attempt-" + SOURCE_ATTEMPT_ID)).resolve()),
        "source_path": str(files["source"].resolve()),
        "source_sha256": sha256(files["source"].read_bytes()),
        "source_bytes": files["source"].stat().st_size,
        "source_manifest_path": str(files["source_manifest"].resolve()),
        "source_manifest_sha256": sha256(files["source_manifest"].read_bytes()),
        "source_footer_sha256": "F" * 64,
        "clock_path": str(files["clock"].resolve()),
        "clock_sha256": sha256(files["clock"].read_bytes()),
        "parent_stage0_ledger_path": str(files["parent_ledger"].resolve()),
        "parent_stage0_ledger_sha256": sha256(files["parent_ledger"].read_bytes()),
        "parent_stage0_receipt_path": str(files["parent_receipt"].resolve()),
        "parent_stage0_receipt_sha256": sha256(files["parent_receipt"].read_bytes()),
        "design_date_set_sha256": "D" * 64,
        "custodian_tool_path": str(files["custodian_tool"].resolve()),
        "custodian_tool_sha256": sha256(files["custodian_tool"].read_bytes()),
        "supervisor_tool_path": str(files["supervisor_tool"].resolve()),
        "supervisor_review_base_sha256": sha256(review_base),
        "design_builder_tool_path": str(files["design_builder_tool"].resolve()),
        "design_builder_tool_sha256": sha256(files["design_builder_tool"].read_bytes()),
        "validator_tool_path": str(files["validator_tool"].resolve()),
        "validator_tool_sha256": sha256(files["validator_tool"].read_bytes()),
        "custodian_test_path": str(files["custodian_test"].resolve()),
        "custodian_test_sha256": sha256(files["custodian_test"].read_bytes()),
        "supervisor_test_path": str(files["supervisor_test"].resolve()),
        "supervisor_test_sha256": sha256(files["supervisor_test"].read_bytes()),
        "design_builder_test_path": str(files["design_builder_test"].resolve()),
        "design_builder_test_sha256": sha256(files["design_builder_test"].read_bytes()),
        "validator_test_path": str(files["validator_test"].resolve()),
        "validator_test_sha256": sha256(files["validator_test"].read_bytes()),
        "splitvault_output_root": str((tmp_path / "vault").resolve()),
        "design_source_output_root": str((tmp_path / "design").resolve()),
        "one_shot_custody_source_attempt_authorized": True,
        "performance_metrics_authorized": False,
        "trading_mutation": False,
        "network_allowed": False,
        "subprocess_allowed": False,
        "model0_authorized": False,
    }
    packet_path = tmp_path / tool.RUN_PACKET_FILENAME
    frozen = refreeze_packet(tool, files, packet, packet_path)
    return tool, files, packet, packet_path, frozen


def test_exact_canonical_packet_and_bound_files_are_accepted_for_reviewed_core(tmp_path: Path) -> None:
    tool, files, packet, packet_path, frozen = packet_fixture(tmp_path)
    reviewed_sha = sha256(packet_path.read_bytes())
    observed, observed_sha = tool.read_reviewed_run_packet(packet_path, reviewed_sha, frozen)
    assert observed == packet and observed_sha == reviewed_sha


def test_generic_packet_verification_never_reads_raw_source_content(tmp_path: Path) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)
    source = Path(str(packet["source_path"])).absolute()
    stable_read = tool._stable_read
    opens = {"source": 0}

    def tracked(path: Path) -> bytes:
        if Path(path).absolute() == source:
            opens["source"] += 1
            raise AssertionError("generic verifier must not read raw source")
        return stable_read(path)

    tool._stable_read = tracked
    observed, _ = tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)
    assert observed == packet
    assert opens["source"] == 0


def test_exact_authority_line_normalization_binds_review_base_and_runtime_sha() -> None:
    tool = load_tool()
    review_base = TOOL_PATH.read_bytes()
    packet_sha = "A" * 64
    runtime = armed_supervisor(review_base, packet_sha)
    observed = tool._verify_runtime_authority(
        runtime,
        packet_sha,
        sha256(review_base),
    )
    assert observed == sha256(runtime)
    for drift in (
        runtime.replace(b'"' + b"A" * 64 + b'"', b'"' + b"B" * 64 + b'"'),
        runtime + b"\n" + AUTHORITY_SENTINEL + b"\n",
        runtime.replace(b": str | None = ", b":str | None = "),
        runtime.replace(b"\n", b" \n", 1),
    ):
        with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
            tool._verify_runtime_authority(drift, packet_sha, sha256(review_base))


@pytest.mark.parametrize(
    "missing",
    [
        "hypothesis_plan_v2_path",
        "hypothesis_plan_v2_sha256",
        "registry_path",
        "registry_sha256",
        "source_attempt_id",
    ],
)
def test_v6_packet_requires_every_new_authority_field(tmp_path: Path, missing: str) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)
    packet.pop(missing)
    packet_path.write_bytes(canonical(packet) + b"\n")
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)


@pytest.mark.parametrize(
    "missing",
    [
        "hypothesis_plan_v3_path",
        "hypothesis_plan_v3_sha256",
        "attempt_evidence_root",
        "custody_stage_path",
        "design_stage_path",
        "supervisor_review_base_sha256",
    ],
)
def test_v7_packet_requires_every_create_new_authority_field(tmp_path: Path, missing: str) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)
    packet.pop(missing)
    packet_path.write_bytes(canonical(packet) + b"\n")
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)


@pytest.mark.parametrize(
    "missing",
    [
        "hypothesis_plan_v4_path",
        "hypothesis_plan_v4_sha256",
        "registry_row_index",
        "registry_row_sha256",
        "one_shot_custody_source_attempt_authorized",
    ],
)
def test_v8_packet_requires_every_registry_authority_field(tmp_path: Path, missing: str) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)
    packet.pop(missing)
    packet_path.write_bytes(canonical(packet) + b"\n")
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)


def test_legacy_exact_supervisor_hash_field_is_rejected_as_extra(tmp_path: Path) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)
    packet["supervisor_tool_sha256"] = packet["supervisor_review_base_sha256"]
    packet_path.write_bytes(canonical(packet) + b"\n")
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)


@pytest.mark.parametrize(
    "attempt_id",
    [
        "",
        "HYP003-SOURCE-ATTEMPT-0123456789ABCDE",
        "HYP003-SOURCE-ATTEMPT-0123456789ABCDEG",
        "hyp003-source-attempt-0123456789abcdef",
        "HYP003-SOURCE-ATTEMPT-../123456789ABC",
        "HYP003-SOURCE-ATTEMPT-0123456789ABC\nEF",
        123,
    ],
)
def test_source_attempt_id_has_one_strict_frozen_format(tmp_path: Path, attempt_id: object) -> None:
    tool, _, packet, packet_path, _ = packet_fixture(tmp_path)
    packet["source_attempt_id"] = attempt_id
    packet_path.write_bytes(canonical(packet) + b"\n")
    frozen = tool.FrozenBindings.from_packet_for_testing(packet)
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)


@pytest.mark.parametrize(
    "attack",
    [
        "v2_hash",
        "v2_path",
        "v3_hash",
        "v3_path",
        "v4_hash",
        "v4_path",
        "registry_hash",
        "registry_path",
        "registry_identity",
    ],
)
def test_frozen_plan_and_registry_drift_fail_before_source_open(tmp_path: Path, attack: str) -> None:
    tool, files, packet, packet_path, _ = packet_fixture(tmp_path)
    if attack == "v2_hash":
        packet["hypothesis_plan_v2_sha256"] = "A" * 64
    elif attack == "v2_path":
        wrong = bound_file(tmp_path, "wrong_v2.md", files["hypothesis_plan_v2"].read_bytes())
        packet["hypothesis_plan_v2_path"] = str(wrong.resolve())
        packet["hypothesis_plan_v2_sha256"] = sha256(wrong.read_bytes())
    elif attack == "v3_hash":
        packet["hypothesis_plan_v3_sha256"] = "C" * 64
    elif attack == "v3_path":
        wrong = bound_file(tmp_path, "wrong_v3.md", files["hypothesis_plan_v3"].read_bytes())
        packet["hypothesis_plan_v3_path"] = str(wrong.resolve())
        packet["hypothesis_plan_v3_sha256"] = sha256(wrong.read_bytes())
    elif attack == "v4_hash":
        packet["hypothesis_plan_v4_sha256"] = "D" * 64
    elif attack == "v4_path":
        wrong = bound_file(tmp_path, "wrong_v4.md", files["hypothesis_plan_v4"].read_bytes())
        packet["hypothesis_plan_v4_path"] = str(wrong.resolve())
        packet["hypothesis_plan_v4_sha256"] = sha256(wrong.read_bytes())
    elif attack == "registry_hash":
        packet["registry_sha256"] = "B" * 64
    elif attack == "registry_path":
        wrong = bound_file(tmp_path, "copied_registry.jsonl", files["registry"].read_bytes())
        packet["registry_path"] = str(wrong.resolve())
        packet["registry_sha256"] = sha256(wrong.read_bytes())
    frozen = tool.FrozenBindings.from_packet_for_testing(packet)
    if attack == "registry_identity":
        original = files["registry"].read_bytes()
        files["registry"].unlink()
        files["registry"].write_bytes(original)
    packet_path.write_bytes(canonical(packet) + b"\n")
    opened: list[Path] = []
    stable_read = tool._stable_read

    def tracked(path: Path) -> bytes:
        opened.append(Path(path).absolute())
        return stable_read(path)

    tool._stable_read = tracked
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)
    assert Path(str(packet["source_path"])).absolute() not in opened


@pytest.mark.parametrize("attack", ["wrong_index", "wrong_row_hash", "changed_row", "later_hyp003"])
def test_v4_registry_row_authority_fails_before_marker_and_source(tmp_path: Path, attack: str) -> None:
    tool, files, packet, packet_path, _ = packet_fixture(tmp_path)
    if attack == "wrong_index":
        packet["registry_row_index"] = REGISTRY_ROW_INDEX - 1
    elif attack == "wrong_row_hash":
        packet["registry_row_sha256"] = "E" * 64
    elif attack == "changed_row":
        payload = files["registry"].read_bytes()
        assert b'"state":"probe"' in payload.splitlines()[REGISTRY_ROW_INDEX - 1]
        files["registry"].write_bytes(payload.replace(b'"state":"probe"', b'"state":"idea"', 1))
        packet["registry_sha256"] = sha256(files["registry"].read_bytes())
    else:
        later = canonical({"hypothesis_id": tool.HYPOTHESIS_ID, "state": "probe"}) + b"\n"
        files["registry"].write_bytes(files["registry"].read_bytes() + later)
        packet["registry_sha256"] = sha256(files["registry"].read_bytes())
    frozen = refreeze_packet(tool, files, packet, packet_path)
    source = Path(str(packet["source_path"])).absolute()
    source_opens = {"count": 0}
    stable_read = tool._stable_read

    def tracked(path: Path) -> bytes:
        if Path(path).absolute() == source:
            source_opens["count"] += 1
        return stable_read(path)

    tool._stable_read = tracked
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool._supervise_reviewed(packet_path, sha256(packet_path.read_bytes()), frozen)
    assert source_opens["count"] == 0
    assert not Path(str(packet["attempt_evidence_root"])).exists()


def test_unrelated_registry_append_passes_only_when_whole_file_binding_is_refrozen(tmp_path: Path) -> None:
    tool, files, packet, packet_path, frozen = packet_fixture(tmp_path)
    unrelated = canonical({"hypothesis_id": "HYP-SYNTHETIC-UNRELATED", "state": "idea"}) + b"\n"
    files["registry"].write_bytes(files["registry"].read_bytes() + unrelated)
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)
    packet["registry_sha256"] = sha256(files["registry"].read_bytes())
    frozen = refreeze_packet(tool, files, packet, packet_path)
    observed, _ = tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)
    assert observed == packet


def test_registry_whole_file_digest_is_checked_before_row_parser(tmp_path: Path) -> None:
    tool, files, packet, packet_path, _ = packet_fixture(tmp_path)
    files["registry"].write_bytes(files["registry"].read_bytes() + b'{"state":"unbound"}\n')
    frozen = refreeze_packet(tool, files, packet, packet_path)
    called = {"row": False}

    def forbidden_row_parser(*args, **kwargs):
        called["row"] = True
        raise AssertionError("row parser must not run before whole-file SHA passes")

    tool._validate_registry_authority = forbidden_row_parser
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)
    assert called["row"] is False


@pytest.mark.parametrize(
    "path_key,file_key",
    [
        ("collection_plan_path", "collection_plan"),
        ("hypothesis_plan_path", "hypothesis_plan"),
        ("hypothesis_plan_v2_path", "hypothesis_plan_v2"),
        ("hypothesis_plan_v3_path", "hypothesis_plan_v3"),
        ("hypothesis_plan_v4_path", "hypothesis_plan_v4"),
        ("registry_path", "registry"),
        ("source_manifest_path", "source_manifest"),
        ("clock_path", "clock"),
        ("parent_stage0_ledger_path", "parent_ledger"),
        ("parent_stage0_receipt_path", "parent_receipt"),
        ("custodian_tool_path", "custodian_tool"),
        ("supervisor_tool_path", "supervisor_tool"),
        ("design_builder_tool_path", "design_builder_tool"),
        ("validator_tool_path", "validator_tool"),
        ("custodian_test_path", "custodian_test"),
        ("supervisor_test_path", "supervisor_test"),
        ("design_builder_test_path", "design_builder_test"),
        ("validator_test_path", "validator_test"),
    ],
)
def test_every_non_source_identity_drift_fails_before_source_open_or_marker(
    tmp_path: Path, path_key: str, file_key: str
) -> None:
    tool, files, packet, packet_path, frozen = packet_fixture(tmp_path, copied_tools=True)
    target = files[file_key]
    payload = target.read_bytes()
    target.unlink()
    target.write_bytes(payload)
    source = Path(str(packet["source_path"])).absolute()
    opened = {"count": 0}
    stable_read = tool._stable_read

    def tracked(path: Path) -> bytes:
        if Path(path).absolute() == source:
            opened["count"] += 1
        return stable_read(path)

    tool._stable_read = tracked
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool._supervise_reviewed(packet_path, sha256(packet_path.read_bytes()), frozen)
    assert opened["count"] == 0
    assert not Path(str(packet["attempt_evidence_root"])).exists()


@pytest.mark.parametrize(
    "existing",
    [
        "attempt_evidence_root",
        "custody_stage_path",
        "design_stage_path",
        "splitvault_output_root",
        "design_source_output_root",
    ],
)
def test_existing_attempt_stage_or_output_blocks_before_marker_and_source(tmp_path: Path, existing: str) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)
    Path(str(packet[existing])).mkdir()
    source = Path(str(packet["source_path"])).absolute()
    opened = {"count": 0}
    stable_read = tool._stable_read

    def tracked(path: Path) -> bytes:
        if Path(path).absolute() == source:
            opened["count"] += 1
        return stable_read(path)

    tool._stable_read = tracked
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)
    assert opened["count"] == 0
    if existing != "attempt_evidence_root":
        assert not Path(str(packet["attempt_evidence_root"])).exists()


def test_attempt_paths_are_deterministic_and_alternate_id_cannot_reuse_them(tmp_path: Path) -> None:
    tool, files, packet, packet_path, _ = packet_fixture(tmp_path)
    assert tool._expected_attempt_paths(packet) == {
        key: Path(str(packet[key]))
        for key in ("attempt_evidence_root", "custody_stage_path", "design_stage_path")
    }
    packet["source_attempt_id"] = "HYP003-SOURCE-ATTEMPT-FEDCBA9876543210"
    packet_path.write_bytes(canonical(packet) + b"\n")
    review_base = TOOL_PATH.read_bytes()
    files["supervisor_tool"].write_bytes(armed_supervisor(review_base, sha256(packet_path.read_bytes())))
    frozen = tool.FrozenBindings.from_packet_for_testing(packet)
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)


@pytest.mark.parametrize("path_key", ["attempt_evidence_root", "custody_stage_path", "design_stage_path"])
def test_attempt_path_drift_fails_before_source_open_or_marker(tmp_path: Path, path_key: str) -> None:
    tool, files, packet, packet_path, _ = packet_fixture(tmp_path)
    packet[path_key] = str((tmp_path / (path_key + "-wrong")).resolve())
    packet_path.write_bytes(canonical(packet) + b"\n")
    review_base = TOOL_PATH.read_bytes()
    files["supervisor_tool"].write_bytes(armed_supervisor(review_base, sha256(packet_path.read_bytes())))
    frozen = tool.FrozenBindings.from_packet_for_testing(packet)
    source = Path(str(packet["source_path"])).absolute()
    opened = {"count": 0}
    stable_read = tool._stable_read

    def tracked(path: Path) -> bytes:
        if Path(path).absolute() == source:
            opened["count"] += 1
        return stable_read(path)

    tool._stable_read = tracked
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)
    assert opened["count"] == 0
    assert not Path(str(packet["attempt_evidence_root"])).exists()


def test_production_paths_pin_v2_v3_v4_and_active_registry() -> None:
    tool = load_tool()
    paths = tool._production_expected_paths(SOURCE_ATTEMPT_ID)
    assert tool.HYPOTHESIS_PLAN_V2_SHA256 == "13BCD3AEB5AB08EC060EAF5107A384FEE8A2CAF581506B50C5F0D8C5A5830840"
    assert tool.HYPOTHESIS_PLAN_V3_SHA256 == "1323330E76ED3671D5B57A367A4A84A6944B01634A4E90EC1B53128DFBB68649"
    assert tool.HYPOTHESIS_PLAN_V4_SHA256 == "7CB8B477C261451E9EA27F16959C0C6B416D8DF4354598BFFCB98C952B34E7F8"
    assert tool.REGISTRY_ROW_INDEX == REGISTRY_ROW_INDEX
    assert tool.REGISTRY_ROW_SHA256 == REGISTRY_ROW_SHA256
    assert paths["hypothesis_plan_v2_path"] == ROOT / "research" / FROZEN_V2_NAME
    assert paths["hypothesis_plan_v3_path"] == ROOT / "research" / FROZEN_V3_NAME
    assert paths["hypothesis_plan_v4_path"] == ROOT / "research" / FROZEN_V4_NAME
    assert paths["registry_path"] == ROOT.parents[1] / "04. Memory" / "research" / REGISTRY_NAME
    assert paths["attempt_evidence_root"].name == SOURCE_ATTEMPT_ID
    assert paths["custody_stage_path"].name == ".splitvault_001.attempt-" + SOURCE_ATTEMPT_ID
    assert paths["design_stage_path"].name == ".trendstack_003_design_m1.attempt-" + SOURCE_ATTEMPT_ID


def test_production_rejects_self_authored_packet_until_independent_hash_is_pinned(tmp_path: Path) -> None:
    tool, _, _, packet_path, _ = packet_fixture(tmp_path)
    assert tool.REVIEWED_RUN_PACKET_SHA256 is None
    assert TOOL_PATH.read_text(encoding="utf-8").splitlines().count(
        "REVIEWED_RUN_PACKET_SHA256: str | None = None"
    ) == 1
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool.supervise(packet_path)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: {**p, "extra": True},
        lambda p: {**p, "one_shot_custody_source_attempt_authorized": 1},
        lambda p: {**p, "one_shot_custody_source_attempt_authorized": False},
        lambda p: {**p, "source_run_authorized": True},
        lambda p: {**p, "network_allowed": "false"},
        lambda p: {**p, "model0_authorized": True},
        lambda p: {**p, "verdict": "SELF_AUTHORED"},
    ],
)
def test_schema_type_and_authority_confusion_fail_closed(tmp_path: Path, mutation) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)
    packet = mutation(packet)
    packet_path.write_bytes(canonical(packet) + b"\n")
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)


def test_noncanonical_bytes_and_filename_are_rejected(tmp_path: Path) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)
    wrong = tmp_path / "packet.json"
    wrong.write_bytes(canonical(packet) + b"\n")
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool.read_reviewed_run_packet(wrong, sha256(wrong.read_bytes()), frozen)


def test_path_overlap_escape_and_identity_replacement_fail_before_runner(tmp_path: Path) -> None:
    tool, files, packet, packet_path, frozen = packet_fixture(tmp_path)
    packet["splitvault_output_root"] = str(files["source"].parent.resolve())
    packet_path.write_bytes(canonical(packet) + b"\n")
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)

    tool, files, packet, packet_path, frozen = packet_fixture(tmp_path / "next") if False else packet_fixture(tmp_path)
    old = files["source_manifest"].read_bytes()
    files["source_manifest"].unlink()
    files["source_manifest"].write_bytes(old)
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)


def test_reviewed_orchestration_never_passes_strategy_fields_to_custodian(tmp_path: Path) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)
    seen = {}

    def custody_runner(*args, authority, **kwargs):
        seen.update(authority.__dict__)
        return custody_result(packet), DummyDesignCapability()

    def design_runner(*args, **kwargs):
        return pending_result(packet)

    def validator_runner(*args, **kwargs):
        return ready_result(packet)

    result = tool._supervise_reviewed(
        packet_path,
        sha256(packet_path.read_bytes()),
        frozen,
        custody_runner=custody_runner,
        projection_runner=lambda *args, **kwargs: object(),
        design_runner=design_runner,
        validator_runner=validator_runner,
    )
    assert result["verdict"].startswith("SOURCE_READY")
    assert result["source_attempt_id"] == SOURCE_ATTEMPT_ID
    forbidden = {"hypothesis_id", "ledger", "atr", "direction", "economics", "strategy"}
    assert not any(any(token in key.lower() for token in forbidden) for key in seen)


def test_start_marker_precedes_stages_and_success_terminal_reconciles(tmp_path: Path) -> None:
    tool, files, packet, packet_path, frozen = packet_fixture(tmp_path)
    observations: list[str] = []

    def custody_runner(*args, authority, **kwargs):
        start = Path(str(packet["attempt_evidence_root"])) / "attempt_started.json"
        assert start.is_file()
        assert Path(authority.custody_stage_path).is_dir()
        observations.append("custody_after_marker")
        return custody_result(packet), DummyDesignCapability()

    def design_runner(*args, **kwargs):
        assert Path(str(packet["design_stage_path"])).is_dir()
        assert kwargs["attempt_root"] == Path(str(packet["design_stage_path"]))
        assert tuple(kwargs["expected_attempt_identity"]) == tool._directory_identity(kwargs["attempt_root"])
        observations.append("design_bound_stage")
        return pending_result(packet)

    result = tool._supervise_reviewed(
        packet_path,
        sha256(packet_path.read_bytes()),
        frozen,
        custody_runner=custody_runner,
        projection_runner=lambda *args, **kwargs: object(),
        design_runner=design_runner,
        validator_runner=lambda *args, **kwargs: ready_result(packet, source_receipt_sha256="C" * 64),
    )
    root = Path(str(packet["attempt_evidence_root"]))
    started_payload = (root / "attempt_started.json").read_bytes()
    terminal_payload = (root / "attempt_terminal.json").read_bytes()
    started = json.loads(started_payload)
    terminal = json.loads(terminal_payload)
    assert observations == ["custody_after_marker", "design_bound_stage"]
    assert started["verdict"] == "ATTEMPT_CONSUMED"
    assert started["source_attempt_id"] == SOURCE_ATTEMPT_ID
    assert started["attempt_evidence_root_identity"] == terminal["attempt_evidence_root_identity"]
    assert started["hypothesis_plan_v4_sha256"] == packet["hypothesis_plan_v4_sha256"]
    assert started["registry_row_index"] == REGISTRY_ROW_INDEX
    assert started["registry_row_sha256"] == REGISTRY_ROW_SHA256
    assert terminal["verdict"] == "SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET"
    assert terminal["attempt_started_sha256"] == sha256(started_payload)
    assert result["attempt_started_sha256"] == sha256(started_payload)
    assert result["attempt_terminal_sha256"] == sha256(terminal_payload)
    assert result["packet_sha256"] == sha256(packet_path.read_bytes())
    assert result["runtime_supervisor_sha256"] == sha256(files["supervisor_tool"].read_bytes())
    assert result["supervisor_review_base_sha256"] == sha256(TOOL_PATH.read_bytes())
    assert result["source_attempt_id"] == SOURCE_ATTEMPT_ID
    assert result["source_verdict"] == "SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET"
    forbidden = {"profit", "expectancy", "win_rate", "validation_outcome", "holdout_outcome"}
    assert not forbidden.intersection(result)
    assert not forbidden.intersection(terminal)


@pytest.mark.parametrize(
    "attack",
    ["bare", "attempt", "path", "role", "review_base"],
)
def test_supervisor_rejects_bare_or_mismatched_pending_design_result(tmp_path: Path, attack: str) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)
    pending = pending_result(packet)
    if attack == "bare":
        pending = {"verdict": pending["verdict"]}
    elif attack == "attempt":
        pending["source_attempt_id"] = "HYP003-SOURCE-ATTEMPT-FEDCBA9876543210"
    elif attack == "path":
        pending["stage_path"] = str((tmp_path / "alternate-stage").resolve())
    elif attack == "role":
        pending["stage_role"] = "CUSTODY"
    else:
        pending["supervisor_review_base_sha256"] = "F" * 64
    validator_called = {"value": False}

    def forbidden_validator(*args, **kwargs):
        validator_called["value"] = True
        return ready_result(packet)

    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool._supervise_reviewed(
            packet_path,
            sha256(packet_path.read_bytes()),
            frozen,
            custody_runner=lambda *args, **kwargs: (
                custody_result(packet),
                DummyDesignCapability(),
            ),
            projection_runner=lambda *args, **kwargs: object(),
            design_runner=lambda *args, **kwargs: pending,
            validator_runner=forbidden_validator,
        )
    assert validator_called["value"] is False


@pytest.mark.parametrize("field", ["source_attempt_id", "stage_path", "stage_role", "supervisor_review_base_sha256"])
def test_supervisor_rejects_validator_provenance_mismatch(tmp_path: Path, field: str) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)
    invalid = ready_result(packet)
    invalid[field] = "MISMATCH"
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool._supervise_reviewed(
            packet_path,
            sha256(packet_path.read_bytes()),
            frozen,
            custody_runner=lambda *args, **kwargs: (
                custody_result(packet),
                DummyDesignCapability(),
            ),
            projection_runner=lambda *args, **kwargs: object(),
            design_runner=lambda *args, **kwargs: pending_result(packet),
            validator_runner=lambda *args, **kwargs: invalid,
        )


def test_supervisor_retains_exact_precreated_stage_identities(tmp_path: Path) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)
    observed: dict[str, tuple[int, ...]] = {}

    def custody_runner(*args, authority, **kwargs):
        observed["custody"] = tuple(authority.custody_stage_identity)
        assert observed["custody"] == tool._directory_identity(Path(authority.custody_stage_path))
        return custody_result(packet), DummyDesignCapability()

    def design_runner(*args, attempt_root, expected_attempt_identity, **kwargs):
        observed["design"] = tuple(expected_attempt_identity)
        assert observed["design"] == tool._directory_identity(attempt_root)
        return pending_result(packet)

    tool._supervise_reviewed(
        packet_path,
        sha256(packet_path.read_bytes()),
        frozen,
        custody_runner=custody_runner,
        projection_runner=lambda *args, **kwargs: object(),
        design_runner=design_runner,
        validator_runner=lambda *args, **kwargs: ready_result(packet),
    )
    assert len(observed["custody"]) == len(observed["design"]) == 6


def test_design_stage_same_path_recreation_is_rejected(tmp_path: Path) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)

    def replace_stage(*args, attempt_root, expected_attempt_identity, **kwargs):
        old = attempt_root.with_name(attempt_root.name + ".old")
        attempt_root.rename(old)
        attempt_root.mkdir()
        assert tool._directory_identity(attempt_root) != tuple(expected_attempt_identity)
        return pending_result(packet)

    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool._supervise_reviewed(
            packet_path,
            sha256(packet_path.read_bytes()),
            frozen,
            custody_runner=lambda *args, **kwargs: (
                custody_result(packet),
                DummyDesignCapability(),
            ),
            projection_runner=lambda *args, **kwargs: object(),
            design_runner=replace_stage,
            validator_runner=lambda *args, **kwargs: ready_result(packet),
        )


def test_post_marker_failure_is_terminal_and_same_attempt_cannot_retry(tmp_path: Path) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)
    calls = {"custody": 0}

    def fail_custody(*args, **kwargs):
        calls["custody"] += 1
        assert (Path(str(packet["attempt_evidence_root"])) / "attempt_started.json").is_file()
        raise RuntimeError("synthetic source-open failure")

    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool._supervise_reviewed(
            packet_path,
            sha256(packet_path.read_bytes()),
            frozen,
            custody_runner=fail_custody,
            projection_runner=lambda *args, **kwargs: object(),
        )
    root = Path(str(packet["attempt_evidence_root"]))
    terminal = json.loads((root / "attempt_terminal.json").read_bytes())
    assert terminal["verdict"] == "SOURCE_ATTEMPT_FAILED_ENGINEERING_NO_MARKET_VERDICT"
    assert calls["custody"] == 1
    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool._supervise_reviewed(
            packet_path,
            sha256(packet_path.read_bytes()),
            frozen,
            custody_runner=fail_custody,
            projection_runner=lambda *args, **kwargs: object(),
        )
    assert calls["custody"] == 1


@pytest.mark.parametrize("attack", ["root_recreate", "marker_recreate"])
def test_terminal_cannot_land_after_evidence_binding_recreation(tmp_path: Path, attack: str) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)
    packet, packet_sha = tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)
    started_sha, _, root_identity, marker_identity, started_payload = tool._create_attempt_started(
        packet,
        packet_path,
        packet_sha,
        frozen.runtime_supervisor_sha256,
        frozen.source_identity,
    )
    root = Path(str(packet["attempt_evidence_root"]))
    marker = root / "attempt_started.json"
    if attack == "root_recreate":
        root.rename(root.with_name(root.name + ".old"))
        root.mkdir()
    else:
        original = marker.read_bytes()
        marker.unlink()
        marker.write_bytes(original)
    with pytest.raises(ValueError):
        tool._create_attempt_terminal(
            packet,
            packet_sha,
            frozen.runtime_supervisor_sha256,
            started_sha,
            started_payload,
            root_identity,
            marker_identity,
            "SOURCE_ATTEMPT_FAILED_ENGINEERING_NO_MARKET_VERDICT",
            {},
        )
    assert not (root / "attempt_terminal.json").exists()


def test_terminal_rechecks_original_marker_immediately_after_create(tmp_path: Path) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)
    packet, packet_sha = tool.read_reviewed_run_packet(packet_path, sha256(packet_path.read_bytes()), frozen)
    started_sha, _, root_identity, marker_identity, started_payload = tool._create_attempt_started(
        packet,
        packet_path,
        packet_sha,
        frozen.runtime_supervisor_sha256,
        frozen.source_identity,
    )
    root = Path(str(packet["attempt_evidence_root"]))
    original_write = tool._exclusive_evidence_write

    def tamper_after_write(path: Path, payload: bytes, *, expected_parent_identity=None):
        observed = original_write(path, payload, expected_parent_identity=expected_parent_identity)
        if Path(path).name == "attempt_terminal.json":
            (root / "attempt_started.json").write_bytes(started_payload + b" ")
        return observed

    tool._exclusive_evidence_write = tamper_after_write
    with pytest.raises(ValueError):
        tool._create_attempt_terminal(
            packet,
            packet_sha,
            frozen.runtime_supervisor_sha256,
            started_sha,
            started_payload,
            root_identity,
            marker_identity,
            "SOURCE_ATTEMPT_FAILED_ENGINEERING_NO_MARKET_VERDICT",
            {},
        )


@pytest.mark.parametrize("crash_event,consumed", [("before_attempt_start", False), ("after_attempt_start", True)])
def test_attempt_consumption_boundary_is_exact(tmp_path: Path, crash_event: str, consumed: bool) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)

    def crash(event: str) -> None:
        if event == crash_event:
            raise RuntimeError("synthetic boundary crash")

    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool._supervise_reviewed(
            packet_path,
            sha256(packet_path.read_bytes()),
            frozen,
            custody_runner=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not reach custody")),
            projection_runner=lambda *args, **kwargs: object(),
            lifecycle_hook=crash,
        )
    root = Path(str(packet["attempt_evidence_root"]))
    assert (root / "attempt_started.json").exists() is consumed
    assert (root / "attempt_terminal.json").exists() is consumed


def test_source_has_no_network_subprocess_or_dynamic_shell_surface() -> None:
    source = TOOL_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not imports.intersection({"socket", "requests", "urllib", "MetaTrader5"})


def test_supervisor_rejects_builder_self_promotion_without_validator(tmp_path: Path) -> None:
    tool, _, packet, packet_path, frozen = packet_fixture(tmp_path)

    with pytest.raises(tool.InvalidSupervisor, match="^INVALID_SUPERVISOR$"):
        tool._supervise_reviewed(
            packet_path,
            sha256(packet_path.read_bytes()),
            frozen,
            custody_runner=lambda *args, **kwargs: (
                custody_result(packet),
                DummyDesignCapability(),
            ),
            projection_runner=lambda *args, **kwargs: object(),
            design_runner=lambda *args, **kwargs: {
                "verdict": "SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET"
            },
            validator_runner=lambda *args, **kwargs: {
                "verdict": "SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET"
            },
        )


def test_verified_tool_bytes_survive_swap_restore_between_verify_and_execute(tmp_path: Path) -> None:
    tool, files, packet, packet_path, frozen = packet_fixture(tmp_path, copied_tools=True)
    original = files["design_builder_tool"].read_bytes()

    def swap_restore(event: str) -> None:
        if event == "after_tool_verification":
            files["design_builder_tool"].unlink()
            files["design_builder_tool"].write_bytes(b"raise RuntimeError('swapped tool executed')\n")
            files["design_builder_tool"].unlink()
            files["design_builder_tool"].write_bytes(original)

    result = tool._supervise_reviewed(
        packet_path,
        sha256(packet_path.read_bytes()),
        frozen,
        custody_runner=lambda *args, **kwargs: (
            custody_result(packet),
            DummyDesignCapability(),
        ),
        projection_runner=lambda *args, **kwargs: object(),
        design_runner=lambda *args, **kwargs: pending_result(packet),
        validator_runner=lambda *args, **kwargs: ready_result(packet),
        lifecycle_hook=swap_restore,
    )
    assert result["verdict"].startswith("SOURCE_READY")


def test_child_boundary_denies_known_paths_enumeration_network_and_subprocess(tmp_path: Path) -> None:
    tool = load_tool()
    forbidden_file = bound_file(tmp_path, "raw.parquet", b"future sentinel")
    forbidden_dir = tmp_path / "private"
    forbidden_dir.mkdir()
    (forbidden_dir / "future.txt").write_text("future", encoding="utf-8")
    prior_attempt = tmp_path / ".allowed_output.attempt-prior"
    prior_attempt.mkdir()
    (prior_attempt / "prior.txt").write_text("prior", encoding="utf-8")
    result = tool.run_design_containment_probe(
        tmp_path / "allowed_output",
        [forbidden_file, forbidden_dir, tmp_path],
        prior_attempt_path=prior_attempt,
    )
    assert result == {
        "file_open_denied": True,
        "file_stat_denied": True,
        "directory_list_denied": True,
        "network_denied": True,
        "parent_stat_denied": True,
        "prior_attempt_denied": True,
        "subprocess_denied": True,
    }


def test_third_party_import_policy_is_active_before_synthetic_package_code(tmp_path: Path) -> None:
    tool = load_tool()
    assert "import pandas" not in TOOL_PATH.read_text(encoding="utf-8")
    sentinel = bound_file(tmp_path, "forbidden.txt", b"IMPORT_SENTINEL_SECRET")
    side_effect = tmp_path / "escaped.txt"
    trusted = tmp_path / "trusted_site"
    package = trusted / "sentinelpkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        "from pathlib import Path\n"
        f"sentinel = Path({str(sentinel)!r})\n"
        f"side_effect = Path({str(side_effect)!r})\n"
        "try:\n"
        "    leaked = sentinel.read_text(encoding='utf-8')\n"
        "except Exception:\n"
        "    IMPORT_READ_DENIED = True\n"
        "else:\n"
        "    IMPORT_READ_DENIED = False\n"
        "    side_effect.write_text(leaked, encoding='utf-8')\n",
        encoding="utf-8",
    )
    result = tool.run_import_containment_probe(
        tmp_path / "import_output",
        trusted,
        "sentinelpkg",
        sentinel,
        side_effect,
    )
    assert result["import_read_denied"] is True
    assert result["side_effect_absent"] is True
    assert not side_effect.exists()


def test_verified_builder_executes_inside_child_boundary_on_public_bytes_only(tmp_path: Path) -> None:
    tool = load_tool()
    fixtures = load_path(ROOT / "tests" / "test_build_trendstack_003_design_source.py", "sealed_builder_fixtures")
    day = "2016-01-04"
    builder, _, projection, date_hash = fixtures.write_mixed_projection_fixture(tmp_path, [day])
    payload = fixtures.payload_for(fixtures.minute_rows(day), tmp_path, "day.parquet")
    capability = fixtures.SyntheticDesignCapability({day: payload})
    output = tmp_path / "sealed_output"
    result = tool._sealed_design_build(
        BUILDER_PATH.read_bytes(),
        {
            "design_builder_tool_sha256": sha256(BUILDER_PATH.read_bytes()),
            "design_builder_tool_path": str(BUILDER_PATH.resolve()),
            "design_source_output_root": str(output.resolve()),
            "design_date_set_sha256": date_hash,
            "source_attempt_id": SOURCE_ATTEMPT_ID,
            "supervisor_review_base_sha256": "A" * 64,
        },
        capability,
        projection,
        {
            "design_date_set_sha256": date_hash,
            "expected_design_dates": 1,
            "expected_rows_per_day": 360,
            "expected_total_rows": 360,
            "first_design_date": day,
            "last_design_date": day,
            "source_attempt_id": SOURCE_ATTEMPT_ID,
            "stage_role": "DESIGN",
            "supervisor_review_base_sha256": "A" * 64,
        },
    )
    assert result["verdict"] == "PENDING_INDEPENDENT_VALIDATION"
    assert result["source_attempt_id"] == SOURCE_ATTEMPT_ID
    assert result["stage_role"] == "DESIGN"
    assert result["supervisor_review_base_sha256"] == "A" * 64
    assert Path(result["stage_path"]).name.startswith(".sealed_output.attempt-")
    assert len(result["pending_receipt_sha256"]) == 64
    assert len(result["pending_tree_sha256"]) == 64
    bound = tool._bind_pending_output(output, result)
    assert bound["pending_receipt_sha256"] == result["pending_receipt_sha256"]
    assert bound["pending_tree_sha256"] == result["pending_tree_sha256"]
    assert (output / "raw_m1" / "DESIGN" / day / "1201_1800.parquet").is_file()
