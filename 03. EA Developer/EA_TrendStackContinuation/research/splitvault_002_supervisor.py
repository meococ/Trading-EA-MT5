"""Hash-bound source supervisor; production remains inert until peer review."""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import secrets
import stat
import subprocess
import sys
from pathlib import Path


PUBLIC_ERROR = "INVALID_SUPERVISOR"
RUN_PACKET_SCHEMA = "trendstack_004_splitvault_source_run_packet.v1"
COLLECTION_ID = "DATASET-FIVEPERCENT-EURUSD-M1-SPLITVAULT-002"
HYPOTHESIS_ID = "HYP-TRENDSTACK-EURUSD-H1-004"
RUN_PACKET_VERDICT = "FROZEN_OUTCOME_BLIND_SOURCE_RUN_AUTHORIZED"
RUN_PACKET_FILENAME = "HYP-TRENDSTACK-EURUSD-H1-004_SOURCE_RUN_PACKET.json"
REVIEWED_RUN_PACKET_SHA256: str | None = None

COLLECTION_PLAN_SHA256 = "F4321C66548B26E867A6CDF0B4B02B3E6B5E1CCA352AC5FB022B3FCA6C320382"
COLLECTION_PLAN_FILENAME = "DATASET-FIVEPERCENT-EURUSD-M1-SPLITVAULT-002_PLAN.md"
HYPOTHESIS_PLAN_SHA256 = "2C82C993A390A56AC33C9A7956F8B3D6B70C426AD5947B36BAE48FBC90CD2F07"
HYPOTHESIS_PLAN_FILENAME = "HYP-TRENDSTACK-EURUSD-H1-004_PROBE_PLAN.md"
REGISTRY_FILENAME = "CANDIDATE_REGISTRY.jsonl"
REGISTRY_ROW_INDEX = 276
REGISTRY_ROW_SHA256 = "9D34120F20E78E90931740B09990C941128EF6E7E0A8978DCFA6249ED463D2A6"
PARENT_REGISTRY_ROW_INDEX = 274
PARENT_REGISTRY_ROW_SHA256 = "5EA4F3921A8F9FE2684249A6BE7098B36CB05408690E1B27C2F257E6E2CE864F"
PARENT_FAILURE_MANIFEST_SHA256 = "DAEDFB436BD7FC636C7F791FB24084289DA41B1CD9ABE0446A6BC6BE892127E7"
PARENT_TERMINAL_SHA256 = "00FF0F107129D535693FBE497D36A315B5891F8A44028A46F5156E956612B961"
PARENT_ATTEMPT_ID = "HYP003-SOURCE-ATTEMPT-1323330E76ED3671"
SOURCE_ATTEMPT_PREFIX = "HYP004-SOURCE-ATTEMPT-"
AUTHORITY_SENTINEL_LINE = b"REVIEWED_RUN_PACKET_SHA256: str | None = " + b"None"
ATTEMPT_EVIDENCE_PARENT = "HYP-TRENDSTACK-EURUSD-H1-004_SOURCE_ATTEMPTS"
SOURCE_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
SOURCE_BYTES = 104_965_845
SOURCE_MANIFEST_SHA256 = "2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54"
SOURCE_FOOTER_LENGTH = 10_121
SOURCE_FOOTER_START = 104_955_716
SOURCE_FOOTER_SHA256 = "691BE204EBC508FD61C925972F91482854AED46625EF7B05F330B7FDFBC9970F"
REJECTED_PARENT_FOOTER_SHA256 = "92E8403266EF971ED2F4C05523ECB6C10AE5B5723F0F7504E09694663A779727"
CLOCK_SHA256 = "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52"
PARENT_LEDGER_SHA256 = "3092A6FCFADE0DA23E4470C4BF3B1D7750190358CF6ED09A2BB942937A7CD3C7"
PARENT_RECEIPT_SHA256 = "5AEA570736361EF22BF2F090A5C05EF2974F482B5CB34A1186F27D9B43AAF5CE"
DESIGN_DATE_SET_SHA256 = "4F30B5E09C8C21C3FCB63F4D5A016EB514D689710589077427464B92CD99A06A"
EXPECTED_DESIGN_DATES = 1_297
EXPECTED_ROWS_PER_DAY = 360
EXPECTED_TOTAL_ROWS = 466_920
FIRST_DESIGN_DATE = "2016-01-04"
LAST_DESIGN_DATE = "2020-12-31"
_HEX = frozenset("0123456789ABCDEF")
_PENDING_TREE_SCHEMA = "trendstack_004_pending_tree.v1"
_PENDING_BASE_FILES = {
    "design_request_plan.jsonl",
    "design_request_plan_receipt.json",
    "design_stage0_projection.jsonl",
    "design_stage0_projection_receipt.json",
    "design_m1_manifest.jsonl",
    "design_m1_source_receipt.json",
    "design_source_access_trace.jsonl",
    "design_source_reconciliation.json",
}
_FILE_BINDINGS = {
    "collection_plan_path": "collection_plan_sha256",
    "hypothesis_plan_path": "hypothesis_plan_sha256",
    "registry_path": "registry_sha256",
    "parent_failure_manifest_path": "parent_failure_manifest_sha256",
    "parent_attempt_terminal_path": "parent_attempt_terminal_sha256",
    "source_path": "source_sha256",
    "source_manifest_path": "source_manifest_sha256",
    "clock_path": "clock_sha256",
    "parent_stage0_ledger_path": "parent_stage0_ledger_sha256",
    "parent_stage0_receipt_path": "parent_stage0_receipt_sha256",
    "custodian_tool_path": "custodian_tool_sha256",
    "supervisor_tool_path": "supervisor_review_base_sha256",
    "design_builder_tool_path": "design_builder_tool_sha256",
    "validator_tool_path": "validator_tool_sha256",
    "custodian_test_path": "custodian_test_sha256",
    "supervisor_test_path": "supervisor_test_sha256",
    "design_builder_test_path": "design_builder_test_sha256",
    "validator_test_path": "validator_test_sha256",
}
_FIELDS = {
    "schema_version",
    "collection_id",
    "hypothesis_id",
    "verdict",
    "collection_plan_path",
    "collection_plan_sha256",
    "hypothesis_plan_path",
    "hypothesis_plan_sha256",
    "registry_path",
    "registry_sha256",
    "registry_row_index",
    "registry_row_sha256",
    "parent_registry_row_index",
    "parent_registry_row_sha256",
    "parent_failure_manifest_path",
    "parent_failure_manifest_sha256",
    "parent_attempt_terminal_path",
    "parent_attempt_terminal_sha256",
    "source_attempt_id",
    "attempt_evidence_root",
    "custody_stage_path",
    "design_stage_path",
    "source_path",
    "source_sha256",
    "source_bytes",
    "source_manifest_path",
    "source_manifest_sha256",
    "source_footer_length",
    "source_footer_start",
    "source_footer_sha256",
    "clock_path",
    "clock_sha256",
    "parent_stage0_ledger_path",
    "parent_stage0_ledger_sha256",
    "parent_stage0_receipt_path",
    "parent_stage0_receipt_sha256",
    "design_date_set_sha256",
    "custodian_tool_path",
    "custodian_tool_sha256",
    "supervisor_tool_path",
    "supervisor_review_base_sha256",
    "design_builder_tool_path",
    "design_builder_tool_sha256",
    "validator_tool_path",
    "validator_tool_sha256",
    "custodian_test_path",
    "custodian_test_sha256",
    "supervisor_test_path",
    "supervisor_test_sha256",
    "design_builder_test_path",
    "design_builder_test_sha256",
    "validator_test_path",
    "validator_test_sha256",
    "splitvault_output_root",
    "design_source_output_root",
    "one_shot_custody_source_attempt_authorized",
    "performance_metrics_authorized",
    "economics_authorized",
    "mt5_authorized",
    "trading_mutation",
    "network_allowed",
    "subprocess_allowed",
    "model0_authorized",
    "validation_authorized",
    "holdout_authorized",
    "promotion_authorized",
    "paper_authorized",
    "live_authorized",
    "deploy_authorized",
}


class InvalidSupervisor(RuntimeError):
    pass


class FrozenBindings:
    def __init__(self, expected: dict[str, object], identities: dict[str, tuple[int, ...]]) -> None:
        self.expected = dict(expected)
        self.identities = dict(identities)
        self.verified_bytes: dict[str, bytes] = {}
        self.runtime_supervisor_sha256: str | None = None
        self.source_identity: tuple[int, ...] | None = None

    @classmethod
    def from_packet_for_testing(cls, packet: dict[str, object]) -> "FrozenBindings":
        try:
            if type(packet) is not dict:
                raise ValueError
            identities = {
                path_key: _identity(Path(str(packet[path_key])).absolute())
                for path_key in _FILE_BINDINGS
            }
            return cls(packet, identities)
        except Exception as exc:
            raise InvalidSupervisor(PUBLIC_ERROR) from exc


class _GenericAuthority:
    def __init__(self, **values: object) -> None:
        self.__dict__.update(values)


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _valid_sha(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(character in _HEX for character in value)


def _valid_source_attempt_id(value: object) -> bool:
    return (
        type(value) is str
        and value.isascii()
        and value.startswith(SOURCE_ATTEMPT_PREFIX)
        and len(value) == len(SOURCE_ATTEMPT_PREFIX) + 16
        and all(character in _HEX for character in value[len(SOURCE_ATTEMPT_PREFIX) :])
    )


def _verify_runtime_authority(runtime_bytes: bytes, packet_sha256: str, review_base_sha256: str) -> str:
    try:
        if type(runtime_bytes) is not bytes or not _valid_sha(packet_sha256) or not _valid_sha(review_base_sha256):
            raise ValueError
        token = b"REVIEWED_RUN_PACKET_SHA256:"
        matches: list[tuple[int, int, bytes]] = []
        offset = 0
        for line in runtime_bytes.splitlines(keepends=True):
            content = line.rstrip(b"\r\n")
            ending = line[len(content) :]
            if content.startswith(token):
                matches.append((offset, offset + len(line), ending))
            offset += len(line)
        if len(matches) != 1:
            raise ValueError
        start, end, ending = matches[0]
        expected = (
            b'REVIEWED_RUN_PACKET_SHA256: str | None = "'
            + packet_sha256.encode("ascii")
            + b'"'
            + ending
        )
        if runtime_bytes[start:end] != expected:
            raise ValueError
        normalized = runtime_bytes[:start] + AUTHORITY_SENTINEL_LINE + ending + runtime_bytes[end:]
        if _digest(normalized) != review_base_sha256:
            raise ValueError
        return _digest(runtime_bytes)
    except Exception as exc:
        if isinstance(exc, InvalidSupervisor) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


def _identity(path: Path) -> tuple[int, int, int, int, int, int, int]:
    info = os.lstat(path)
    attributes = int(getattr(info, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if not stat.S_ISREG(info.st_mode) or attributes & reparse or info.st_nlink != 1:
        raise ValueError
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_size),
        int(info.st_mtime_ns),
        int(info.st_ctime_ns),
        int(info.st_nlink),
        attributes,
    )


def _directory_chain(path: Path) -> None:
    current = path.absolute().parent
    while True:
        info = os.lstat(current)
        attributes = int(getattr(info, "st_file_attributes", 0))
        reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
        if not stat.S_ISDIR(info.st_mode) or attributes & reparse:
            raise ValueError
        if current.parent == current:
            return
        current = current.parent


def _directory_identity(path: Path) -> tuple[int, int, int, int, int, int]:
    info = os.lstat(path)
    attributes = int(getattr(info, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if not stat.S_ISDIR(info.st_mode) or attributes & reparse:
        raise ValueError
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_mode),
        int(info.st_mtime_ns),
        int(info.st_ctime_ns),
        attributes,
    )


def _directory_anchor(identity: tuple[int, ...]) -> tuple[int, int, int, int]:
    if type(identity) is not tuple or len(identity) != 6 or any(type(value) is not int for value in identity):
        raise ValueError
    return (identity[0], identity[1], identity[2], identity[5])


def _as_directory_anchor(identity: tuple[int, ...]) -> tuple[int, int, int, int]:
    if type(identity) is not tuple or any(type(value) is not int for value in identity):
        raise ValueError
    if len(identity) == 4:
        return identity
    return _directory_anchor(identity)


def _validated_directory_root(path: Path | str) -> str:
    root = Path(path).absolute()
    if root.resolve(strict=True) != root:
        raise ValueError
    _directory_chain(root / "child")
    _directory_identity(root)
    return str(root)


def _pyarrow_import_root() -> str:
    candidates = []
    for value in sys.path:
        if not value:
            continue
        candidate = Path(value).absolute()
        if (candidate / "pyarrow" / "__init__.py").is_file():
            candidates.append(_validated_directory_root(candidate))
    if len(candidates) != 1:
        raise ValueError
    return candidates[0]


def _precreate_attempt(output: Path) -> tuple[Path, tuple[int, ...]]:
    _directory_chain(output)
    if output.exists():
        raise ValueError
    for _ in range(16):
        attempt = output.parent / ("." + output.name + ".attempt-" + secrets.token_hex(16))
        try:
            attempt.mkdir(parents=False)
        except FileExistsError:
            continue
        return attempt, _directory_identity(attempt)
    raise ValueError


def _stable_read(path: Path) -> bytes:
    _directory_chain(path)
    before = _identity(path)
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (int(opened.st_dev), int(opened.st_ino)) != before[:2]:
            raise ValueError
        payload = handle.read()
        final = os.fstat(handle.fileno())
    if before != _identity(path) or int(final.st_size) != len(payload):
        raise ValueError
    return payload


def _exclusive_evidence_write(
    path: Path,
    payload: bytes,
    *,
    expected_parent_identity: tuple[int, ...] | None = None,
) -> str:
    if type(payload) is not bytes or path.exists():
        raise ValueError
    _directory_chain(path)
    if expected_parent_identity is not None and _directory_anchor(_directory_identity(path.parent)) != _as_directory_anchor(
        expected_parent_identity
    ):
        raise ValueError
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    identity = _identity(path)
    if (
        _stable_read(path) != payload
        or _identity(path) != identity
        or (
            expected_parent_identity is not None
            and _directory_anchor(_directory_identity(path.parent)) != _as_directory_anchor(expected_parent_identity)
        )
    ):
        raise ValueError
    return _digest(payload)


def _precreate_bound_stage(path: Path) -> tuple[int, ...]:
    _directory_chain(path)
    if path.exists():
        raise ValueError
    path.mkdir(parents=False)
    identity = _directory_identity(path)
    with os.scandir(path) as entries:
        if next(entries, None) is not None:
            raise ValueError
    return identity


def _create_attempt_started(
    packet: dict[str, object],
    packet_path: Path,
    packet_sha256: str,
    runtime_supervisor_sha256: str,
    source_identity: tuple[int, ...],
) -> tuple[str, dict[str, object], tuple[int, ...], tuple[int, ...], bytes]:
    root = Path(str(packet["attempt_evidence_root"])).absolute()
    _directory_chain(root)
    if root.exists():
        raise ValueError
    root.mkdir(parents=False)
    root_identity = _directory_anchor(_directory_identity(root))
    marker = {
        "attempt_evidence_root": str(root),
        "attempt_evidence_root_identity": list(root_identity),
        "collection_plan_sha256": packet["collection_plan_sha256"],
        "custodian_test_sha256": packet["custodian_test_sha256"],
        "custodian_tool_sha256": packet["custodian_tool_sha256"],
        "custody_stage_path": packet["custody_stage_path"],
        "custody_stage_role": "CUSTODY",
        "design_builder_test_sha256": packet["design_builder_test_sha256"],
        "design_builder_tool_sha256": packet["design_builder_tool_sha256"],
        "design_source_output_root": packet["design_source_output_root"],
        "design_stage_path": packet["design_stage_path"],
        "design_stage_role": "DESIGN",
        "hypothesis_id": HYPOTHESIS_ID,
        "hypothesis_plan_sha256": packet["hypothesis_plan_sha256"],
        "parent_registry_row_index": packet["parent_registry_row_index"],
        "parent_registry_row_sha256": packet["parent_registry_row_sha256"],
        "parent_failure_manifest_sha256": packet["parent_failure_manifest_sha256"],
        "parent_attempt_terminal_sha256": packet["parent_attempt_terminal_sha256"],
        "packet_path": str(packet_path),
        "packet_sha256": packet_sha256,
        "one_shot_custody_source_attempt_authorized": packet[
            "one_shot_custody_source_attempt_authorized"
        ],
        "registry_path": packet["registry_path"],
        "registry_sha256": packet["registry_sha256"],
        "registry_row_index": packet["registry_row_index"],
        "registry_row_sha256": packet["registry_row_sha256"],
        "runtime_supervisor_sha256": runtime_supervisor_sha256,
        "schema_version": "trendstack_004_source_attempt_started.v1",
        "source_attempt_id": packet["source_attempt_id"],
        "source_bytes": packet["source_bytes"],
        "source_footer_length": packet["source_footer_length"],
        "source_footer_start": packet["source_footer_start"],
        "source_footer_sha256": packet["source_footer_sha256"],
        "source_identity": list(source_identity),
        "source_path": packet["source_path"],
        "source_sha256": packet["source_sha256"],
        "splitvault_output_root": packet["splitvault_output_root"],
        "supervisor_review_base_sha256": packet["supervisor_review_base_sha256"],
        "supervisor_test_sha256": packet["supervisor_test_sha256"],
        "validator_test_sha256": packet["validator_test_sha256"],
        "validator_tool_sha256": packet["validator_tool_sha256"],
        "verdict": "ATTEMPT_CONSUMED",
    }
    payload = _canonical(marker) + b"\n"
    marker_path = root / "attempt_started.json"
    marker_sha = _exclusive_evidence_write(marker_path, payload, expected_parent_identity=root_identity)
    marker_identity = _identity(marker_path)
    if _directory_anchor(_directory_identity(root)) != root_identity:
        raise ValueError
    return marker_sha, marker, root_identity, marker_identity, payload


def _create_attempt_terminal(
    packet: dict[str, object],
    packet_sha256: str,
    runtime_supervisor_sha256: str,
    attempt_started_sha256: str,
    attempt_started_payload: bytes,
    attempt_root_identity: tuple[int, ...],
    attempt_started_identity: tuple[int, ...],
    verdict: str,
    evidence: dict[str, object],
) -> str:
    root = Path(str(packet["attempt_evidence_root"])).absolute()
    marker_path = root / "attempt_started.json"

    def verify_started() -> None:
        if (
            _directory_anchor(_directory_identity(root)) != _as_directory_anchor(attempt_root_identity)
            or _identity(marker_path) != attempt_started_identity
        ):
            raise ValueError
        observed = _stable_read(marker_path)
        if observed != attempt_started_payload or _digest(observed) != attempt_started_sha256:
            raise ValueError

    verify_started()
    terminal = {
        **evidence,
        "attempt_evidence_root_identity": list(_as_directory_anchor(attempt_root_identity)),
        "attempt_started_sha256": attempt_started_sha256,
        "packet_sha256": packet_sha256,
        "runtime_supervisor_sha256": runtime_supervisor_sha256,
        "schema_version": "trendstack_004_source_attempt_terminal.v1",
        "source_attempt_id": packet["source_attempt_id"],
        "supervisor_review_base_sha256": packet["supervisor_review_base_sha256"],
        "verdict": verdict,
    }
    terminal_sha256 = _exclusive_evidence_write(
        root / "attempt_terminal.json",
        _canonical(terminal) + b"\n",
        expected_parent_identity=attempt_root_identity,
    )
    verify_started()
    return terminal_sha256


def _canonical_object(payload: bytes) -> dict[str, object]:
    if not payload.endswith(b"\n") or payload.count(b"\n") != 1:
        raise ValueError
    value = json.loads(payload)
    if type(value) is not dict or _canonical(value) + b"\n" != payload:
        raise ValueError
    return value


def _canonical_rows(payload: bytes) -> list[dict[str, object]]:
    if not payload or not payload.endswith(b"\n"):
        raise ValueError
    rows = []
    for line in payload.splitlines():
        value = json.loads(line)
        if type(value) is not dict or _canonical(value) != line:
            raise ValueError
        rows.append(value)
    return rows


def _validate_registry_authority(payload: bytes, packet: dict[str, object]) -> None:
    if (
        type(payload) is not bytes
        or not payload.endswith(b"\n")
        or packet.get("registry_row_index") != REGISTRY_ROW_INDEX
        or packet.get("registry_row_sha256") != REGISTRY_ROW_SHA256
        or packet.get("parent_registry_row_index") != PARENT_REGISTRY_ROW_INDEX
        or packet.get("parent_registry_row_sha256") != PARENT_REGISTRY_ROW_SHA256
    ):
        raise ValueError
    lines = payload.splitlines()
    if len(lines) < REGISTRY_ROW_INDEX:
        raise ValueError
    raw_row = lines[REGISTRY_ROW_INDEX - 1]
    parent_raw_row = lines[PARENT_REGISTRY_ROW_INDEX - 1]
    if _digest(raw_row) != REGISTRY_ROW_SHA256 or _digest(parent_raw_row) != PARENT_REGISTRY_ROW_SHA256:
        raise ValueError
    parsed: list[dict[str, object]] = []
    latest_hyp004 = 0
    latest_parent = 0
    for index, line in enumerate(lines, start=1):
        value = json.loads(line)
        if type(value) is not dict:
            raise ValueError
        parsed.append(value)
        if value.get("hypothesis_id") == HYPOTHESIS_ID:
            latest_hyp004 = index
        if value.get("hypothesis_id") == "HYP-TRENDSTACK-EURUSD-H1-003":
            latest_parent = index
    if latest_hyp004 != REGISTRY_ROW_INDEX or latest_parent != PARENT_REGISTRY_ROW_INDEX:
        raise ValueError
    row = parsed[REGISTRY_ROW_INDEX - 1]
    validation = row.get("validation")
    metrics = row.get("metrics")
    reason = row.get("reason")
    if (
        row.get("hypothesis_id") != HYPOTHESIS_ID
        or row.get("state") != "probe"
        or row.get("prereg_path")
        != "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-004_PROBE_PLAN.md"
        or row.get("prereg_sha256") != HYPOTHESIS_PLAN_SHA256
        or type(reason) is not str
        or "Exactly one outcome-blind custody/DESIGN source attempt" not in reason
        or "conditional on independent review and a fresh one-shot packet" not in reason
        or type(validation) is not dict
        or type(metrics) is not dict
        or validation.get("source_run_authorized") is not False
        or validation.get("performance_metrics_authorized") is not False
        or validation.get("model0_authorized") is not False
        or validation.get("promotion_eligible") is not False
        or validation.get("research_validation_access_authorized") is not False
        or validation.get("research_holdout_access_authorized") is not False
        or metrics.get("economics_opened") is not False
        or metrics.get("research_validation_opened") is not False
        or metrics.get("research_holdout_opened") is not False
        or metrics.get("performance_trials_executed") != 0
    ):
        raise ValueError
    parent = parsed[PARENT_REGISTRY_ROW_INDEX - 1]
    parent_validation = parent.get("validation")
    parent_metrics = parent.get("metrics")
    if (
        parent.get("hypothesis_id") != "HYP-TRENDSTACK-EURUSD-H1-003"
        or parent.get("state") != "parked"
        or parent.get("verdict")
        != "PARK_ENGINEERING_INVALID_FOOTER_DIGEST_CONTRACT_MISMATCH_NO_MARKET_VERDICT"
        or type(parent_validation) is not dict
        or type(parent_metrics) is not dict
        or parent_validation.get("failure_manifest_sha256") != PARENT_FAILURE_MANIFEST_SHA256
        or parent_validation.get("attempt_terminal_sha256") != PARENT_TERMINAL_SHA256
        or parent_validation.get("source_run_authorized") is not False
        or parent_validation.get("model0_authorized") is not False
        or parent_validation.get("promotion_eligible") is not False
        or parent_validation.get("research_validation_access_authorized") is not False
        or parent_validation.get("research_holdout_access_authorized") is not False
        or parent_metrics.get("economics_opened") is not False
        or parent_metrics.get("research_price_rows_opened") != 0
        or parent_metrics.get("source_decoded") is not False
        or parent_metrics.get("source_attempts_consumed") != 1
    ):
        raise ValueError


def _validate_parent_failure_evidence(
    manifest_payload: bytes,
    terminal_payload: bytes,
    packet: dict[str, object],
) -> None:
    if (
        packet.get("parent_failure_manifest_sha256") != PARENT_FAILURE_MANIFEST_SHA256
        or packet.get("parent_attempt_terminal_sha256") != PARENT_TERMINAL_SHA256
        or _digest(manifest_payload) != PARENT_FAILURE_MANIFEST_SHA256
        or _digest(terminal_payload) != PARENT_TERMINAL_SHA256
    ):
        raise ValueError
    manifest = _canonical_object(manifest_payload)
    terminal = _canonical_object(terminal_payload)
    if (
        manifest.get("schema_version") != "trendstack_003_source_failure_manifest.v1"
        or manifest.get("hypothesis_id") != "HYP-TRENDSTACK-EURUSD-H1-003"
        or manifest.get("source_attempt_id") != PARENT_ATTEMPT_ID
        or manifest.get("attempt_terminal_sha256") != PARENT_TERMINAL_SHA256
        or manifest.get("verdict")
        != "PARK_ENGINEERING_INVALID_FOOTER_DIGEST_CONTRACT_MISMATCH_NO_MARKET_VERDICT"
        or manifest.get("expected_source_footer_sha256") != REJECTED_PARENT_FOOTER_SHA256
        or manifest.get("observed_source_footer_sha256") != SOURCE_FOOTER_SHA256
        or manifest.get("observed_footer_length_bytes") != SOURCE_FOOTER_LENGTH
        or manifest.get("observed_footer_start_offset") != SOURCE_FOOTER_START
        or manifest.get("source_decoded") is not False
        or manifest.get("research_price_rows_opened") != 0
        or manifest.get("economics_opened") is not False
        or terminal.get("schema_version") != "trendstack_003_source_attempt_terminal.v1"
        or terminal.get("source_attempt_id") != PARENT_ATTEMPT_ID
        or terminal.get("verdict") != "SOURCE_ATTEMPT_FAILED_ENGINEERING_NO_MARKET_VERDICT"
    ):
        raise ValueError


def _bind_pending_output(output_root: Path | str, result: dict[str, object]) -> dict[str, object]:
    output = Path(output_root).absolute()
    if type(result) is not dict:
        raise ValueError
    root_identity = _directory_identity(output)
    files: dict[str, bytes] = {}
    file_identities: dict[str, tuple[int, ...]] = {}
    directories: dict[str, tuple[int, ...]] = {".": root_identity}
    pending = [output]
    while pending:
        current = pending.pop()
        _directory_identity(current)
        with os.scandir(current) as entries:
            for entry in entries:
                path = Path(entry.path)
                relative = path.relative_to(output).as_posix()
                info = os.lstat(path)
                attributes = int(getattr(info, "st_file_attributes", 0))
                reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
                if attributes & reparse:
                    raise ValueError
                if stat.S_ISDIR(info.st_mode):
                    directories[relative] = _directory_identity(path)
                    pending.append(path)
                elif stat.S_ISREG(info.st_mode):
                    file_identities[relative] = _identity(path)
                    files[relative] = _stable_read(path)
                else:
                    raise ValueError
    if _directory_identity(output) != root_identity or "design_m1_manifest.jsonl" not in files:
        raise ValueError
    manifest = _canonical_rows(files["design_m1_manifest.jsonl"])
    shard_paths: set[str] = set()
    expected_directories = {".", "raw_m1", "raw_m1/DESIGN"}
    for item in manifest:
        relative = item.get("relative_path")
        day = item.get("date")
        if type(relative) is not str or type(day) is not str or relative != f"raw_m1/DESIGN/{day}/1201_1800.parquet":
            raise ValueError
        shard_paths.add(relative)
        expected_directories.add(f"raw_m1/DESIGN/{day}")
    if set(files) != _PENDING_BASE_FILES | shard_paths or set(directories) != expected_directories:
        raise ValueError
    receipt_payload = files["design_m1_source_receipt.json"]
    receipt = _canonical_object(receipt_payload)
    expected_result = {**receipt, "pending_receipt_sha256": _digest(receipt_payload)}
    if result != expected_result:
        raise ValueError
    entries = [
        {"bytes": len(files[relative]), "relative_path": relative, "sha256": _digest(files[relative])}
        for relative in sorted(set(files) - {"design_m1_source_receipt.json"})
    ]
    tree_sha = _digest(_canonical({"files": entries, "schema_version": _PENDING_TREE_SCHEMA}))
    if receipt.get("pending_tree_sha256") != tree_sha:
        raise ValueError
    if _directory_identity(output) != root_identity:
        raise ValueError
    if any(_identity(output / relative) != identity for relative, identity in file_identities.items()):
        raise ValueError
    if any(
        _directory_identity(output if relative == "." else output / relative) != identity
        for relative, identity in directories.items()
    ):
        raise ValueError
    return {
        "pending_receipt_sha256": expected_result["pending_receipt_sha256"],
        "pending_tree_sha256": tree_sha,
        "expected_root_identity": root_identity,
        "expected_directory_identities": directories,
        "expected_file_identities": file_identities,
    }


class _ExecutedModule:
    def __init__(self, namespace: dict[str, object]) -> None:
        self._namespace = namespace

    def __getattr__(self, name: str):
        try:
            return self._namespace[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def _execute_verified(payload: bytes, label: str, expected_sha256: str) -> _ExecutedModule:
    if type(payload) is not bytes or _digest(payload) != expected_sha256:
        raise ValueError
    namespace: dict[str, object] = {
        "__file__": label,
        "__name__": "_verified_" + hashlib.sha256(label.encode("utf-8")).hexdigest()[:16],
        "__verified_sha256__": expected_sha256,
    }
    exec(compile(payload, label, "exec"), namespace)
    return _ExecutedModule(namespace)


def _validate_packet_types(packet: dict[str, object]) -> None:
    if set(packet) != _FIELDS:
        raise ValueError
    if packet["schema_version"] != RUN_PACKET_SCHEMA:
        raise ValueError
    if packet["collection_id"] != COLLECTION_ID or packet["hypothesis_id"] != HYPOTHESIS_ID:
        raise ValueError
    if packet["verdict"] != RUN_PACKET_VERDICT:
        raise ValueError
    for path_key in _FILE_BINDINGS:
        value = packet[path_key]
        if type(value) is not str or not Path(value).is_absolute():
            raise ValueError
    for path_key in (
        "splitvault_output_root",
        "design_source_output_root",
        "attempt_evidence_root",
        "custody_stage_path",
        "design_stage_path",
    ):
        value = packet[path_key]
        if type(value) is not str or not Path(value).is_absolute():
            raise ValueError
    for hash_key in set(_FILE_BINDINGS.values()) | {"source_footer_sha256", "design_date_set_sha256"}:
        if not _valid_sha(packet[hash_key]):
            raise ValueError
    if not _valid_source_attempt_id(packet["source_attempt_id"]):
        raise ValueError
    if packet["registry_row_index"] != REGISTRY_ROW_INDEX or type(packet["registry_row_index"]) is not int:
        raise ValueError
    if packet["registry_row_sha256"] != REGISTRY_ROW_SHA256:
        raise ValueError
    if (
        type(packet["parent_registry_row_index"]) is not int
        or packet["parent_registry_row_index"] != PARENT_REGISTRY_ROW_INDEX
        or packet["parent_registry_row_sha256"] != PARENT_REGISTRY_ROW_SHA256
        or packet["parent_failure_manifest_sha256"] != PARENT_FAILURE_MANIFEST_SHA256
        or packet["parent_attempt_terminal_sha256"] != PARENT_TERMINAL_SHA256
    ):
        raise ValueError
    if type(packet["source_bytes"]) is not int or packet["source_bytes"] <= 0:
        raise ValueError
    if (
        type(packet["source_footer_length"]) is not int
        or packet["source_footer_length"] <= 0
        or type(packet["source_footer_start"]) is not int
        or packet["source_footer_start"] < 4
        or packet["source_footer_start"] + packet["source_footer_length"] + 8 != packet["source_bytes"]
        or packet["source_footer_sha256"] == REJECTED_PARENT_FOOTER_SHA256
    ):
        raise ValueError
    expected_flags = {
        "one_shot_custody_source_attempt_authorized": True,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "mt5_authorized": False,
        "trading_mutation": False,
        "network_allowed": False,
        "subprocess_allowed": False,
        "model0_authorized": False,
        "validation_authorized": False,
        "holdout_authorized": False,
        "promotion_authorized": False,
        "paper_authorized": False,
        "live_authorized": False,
        "deploy_authorized": False,
    }
    for key, expected in expected_flags.items():
        if type(packet[key]) is not bool or packet[key] is not expected:
            raise ValueError


def _validate_paths(packet: dict[str, object]) -> None:
    inputs: list[Path] = []
    for path_key in _FILE_BINDINGS:
        path = Path(str(packet[path_key])).absolute()
        if path.resolve(strict=True) != path:
            raise ValueError
        inputs.append(path)
    if len({str(path).lower() for path in inputs}) != len(inputs):
        raise ValueError
    if (
        Path(str(packet["collection_plan_path"])).name != COLLECTION_PLAN_FILENAME
        or Path(str(packet["hypothesis_plan_path"])).name != HYPOTHESIS_PLAN_FILENAME
        or Path(str(packet["registry_path"])).name != REGISTRY_FILENAME
        or Path(str(packet["parent_failure_manifest_path"])).name != "failure_manifest.json"
        or Path(str(packet["parent_attempt_terminal_path"])).name != "attempt_terminal.json"
    ):
        raise ValueError
    outputs = [Path(str(packet[key])).absolute() for key in ("splitvault_output_root", "design_source_output_root")]
    if outputs[0] == outputs[1] or outputs[0] in outputs[1].parents or outputs[1] in outputs[0].parents:
        raise ValueError
    for output in outputs:
        _directory_chain(output)
        if output.exists():
            raise ValueError
        normalized = output.resolve(strict=False)
        for source in inputs:
            if normalized == source or normalized in source.parents or source in normalized.parents:
                raise ValueError
    expected_attempt_paths = _expected_attempt_paths(packet)
    for key, expected in expected_attempt_paths.items():
        observed = Path(str(packet[key])).absolute()
        if observed != expected or observed.exists():
            raise ValueError
        _directory_chain(observed)


def _expected_attempt_paths(packet: dict[str, object]) -> dict[str, Path]:
    if type(packet) is not dict or not _valid_source_attempt_id(packet.get("source_attempt_id")):
        raise ValueError
    attempt_id = str(packet["source_attempt_id"])
    research = Path(str(packet["hypothesis_plan_path"])).absolute().parent
    custody_output = Path(str(packet["splitvault_output_root"])).absolute()
    design_output = Path(str(packet["design_source_output_root"])).absolute()
    return {
        "attempt_evidence_root": research / "evidence" / ATTEMPT_EVIDENCE_PARENT / attempt_id,
        "custody_stage_path": custody_output.parent / ("." + custody_output.name + ".attempt-" + attempt_id),
        "design_stage_path": design_output.parent / ("." + design_output.name + ".attempt-" + attempt_id),
    }


def read_reviewed_run_packet(
    packet_path: Path | str,
    reviewed_sha256: str,
    frozen: FrozenBindings,
) -> tuple[dict[str, object], str]:
    try:
        path = Path(packet_path).absolute()
        if path.name != RUN_PACKET_FILENAME or not _valid_sha(reviewed_sha256) or type(frozen) is not FrozenBindings:
            raise ValueError
        payload = _stable_read(path)
        observed_sha = _digest(payload)
        if observed_sha != reviewed_sha256 or not payload.endswith(b"\n") or payload.count(b"\n") != 1:
            raise ValueError
        packet = json.loads(payload)
        if type(packet) is not dict or _canonical(packet) + b"\n" != payload:
            raise ValueError
        _validate_packet_types(packet)
        if packet != frozen.expected:
            raise ValueError
        _validate_paths(packet)
        verified: dict[str, bytes] = {}
        for path_key, hash_key in _FILE_BINDINGS.items():
            if path_key == "source_path":
                continue
            target = Path(str(packet[path_key])).absolute()
            if _identity(target) != frozen.identities.get(path_key):
                raise ValueError
            data = _stable_read(target)
            if path_key == "supervisor_tool_path":
                frozen.runtime_supervisor_sha256 = _verify_runtime_authority(
                    data,
                    observed_sha,
                    str(packet["supervisor_review_base_sha256"]),
                )
            else:
                if _digest(data) != packet[hash_key]:
                    raise ValueError
                if path_key == "registry_path":
                    _validate_registry_authority(data, packet)
            verified[path_key] = data
        _validate_parent_failure_evidence(
            verified["parent_failure_manifest_path"],
            verified["parent_attempt_terminal_path"],
            packet,
        )
        source = Path(str(packet["source_path"])).absolute()
        source_identity = _identity(source)
        if source_identity != frozen.identities.get("source_path") or int(source_identity[2]) != packet["source_bytes"]:
            raise ValueError
        if frozen.runtime_supervisor_sha256 is None:
            raise ValueError
        frozen.source_identity = source_identity
        frozen.verified_bytes = verified
        return packet, observed_sha
    except Exception as exc:
        if isinstance(exc, InvalidSupervisor) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


def _production_expected_paths(source_attempt_id: str) -> dict[str, Path]:
    if not _valid_source_attempt_id(source_attempt_id):
        raise ValueError
    workspace = Path(__file__).resolve().parents[3]
    research = Path(__file__).resolve().parent
    package = research.parent
    paths = {
        "collection_plan_path": research / COLLECTION_PLAN_FILENAME,
        "hypothesis_plan_path": research / HYPOTHESIS_PLAN_FILENAME,
        "registry_path": workspace / "04. Memory" / "research" / REGISTRY_FILENAME,
        "parent_failure_manifest_path": research
        / "evidence"
        / "HYP-TRENDSTACK-EURUSD-H1-003_SOURCE_ATTEMPTS"
        / PARENT_ATTEMPT_ID
        / "failure_manifest.json",
        "parent_attempt_terminal_path": research
        / "evidence"
        / "HYP-TRENDSTACK-EURUSD-H1-003_SOURCE_ATTEMPTS"
        / PARENT_ATTEMPT_ID
        / "attempt_terminal.json",
        "source_path": workspace / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "EURUSD_M1_2015_now.parquet",
        "source_manifest_path": workspace / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "manifest.json",
        "clock_path": workspace / "02. AlphaFactory" / "tools" / "research" / "fivepercent_server_clock.py",
        "parent_stage0_ledger_path": research / "evidence" / "HYP-TRENDSTACK-EURUSD-H1-002_STAGE0" / "stage0_eligibility_ledger.jsonl",
        "parent_stage0_receipt_path": research / "evidence" / "HYP-TRENDSTACK-EURUSD-H1-002_STAGE0" / "stage0_receipt.json",
        "custodian_tool_path": research / "splitvault_002_custodian.py",
        "supervisor_tool_path": research / "splitvault_002_supervisor.py",
        "design_builder_tool_path": research / "build_trendstack_004_design_source.py",
        "validator_tool_path": research / "validate_trendstack_004_design_source.py",
        "custodian_test_path": package / "tests" / "test_splitvault_002_custodian.py",
        "supervisor_test_path": package / "tests" / "test_splitvault_002_supervisor.py",
        "design_builder_test_path": package / "tests" / "test_build_trendstack_004_design_source.py",
        "validator_test_path": package / "tests" / "test_validate_trendstack_004_design_source.py",
        "splitvault_output_root": workspace / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "splitvault_002",
        "design_source_output_root": workspace / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "trendstack_004_design_m1",
    }
    paths.update(_expected_attempt_paths({**paths, "source_attempt_id": source_attempt_id}))
    return paths


def _production_frozen(packet_path: Path) -> FrozenBindings:
    """Build immutable file identities only after the peer-reviewed packet is fixed."""
    payload = _stable_read(packet_path)
    packet = json.loads(payload)
    if type(packet) is not dict:
        raise ValueError
    if not _valid_source_attempt_id(packet.get("source_attempt_id")):
        raise ValueError
    expected_paths = _production_expected_paths(str(packet["source_attempt_id"]))
    for key, expected_path in expected_paths.items():
        if Path(str(packet.get(key))).absolute() != expected_path.absolute():
            raise ValueError
    expected_external = {
        "collection_plan_sha256": COLLECTION_PLAN_SHA256,
        "hypothesis_plan_sha256": HYPOTHESIS_PLAN_SHA256,
        "registry_row_index": REGISTRY_ROW_INDEX,
        "registry_row_sha256": REGISTRY_ROW_SHA256,
        "parent_registry_row_index": PARENT_REGISTRY_ROW_INDEX,
        "parent_registry_row_sha256": PARENT_REGISTRY_ROW_SHA256,
        "parent_failure_manifest_sha256": PARENT_FAILURE_MANIFEST_SHA256,
        "parent_attempt_terminal_sha256": PARENT_TERMINAL_SHA256,
        "source_sha256": SOURCE_SHA256,
        "source_bytes": SOURCE_BYTES,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
        "source_footer_length": SOURCE_FOOTER_LENGTH,
        "source_footer_start": SOURCE_FOOTER_START,
        "source_footer_sha256": SOURCE_FOOTER_SHA256,
        "clock_sha256": CLOCK_SHA256,
        "parent_stage0_ledger_sha256": PARENT_LEDGER_SHA256,
        "parent_stage0_receipt_sha256": PARENT_RECEIPT_SHA256,
        "design_date_set_sha256": DESIGN_DATE_SET_SHA256,
    }
    if any(packet.get(key) != value for key, value in expected_external.items()):
        raise ValueError
    identities = {key: _identity(Path(str(packet[key])).absolute()) for key in _FILE_BINDINGS}
    return FrozenBindings(packet, identities)


_WORKER_BOOTSTRAP = r'''
import base64
import __future__
import _strptime
import hashlib
import json
import math
import os
import pickle
import secrets
import stat
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

payload = pickle.loads(sys.stdin.buffer.read())
output = os.path.normcase(os.path.abspath(payload["output_root"]))
attempt = os.path.normcase(os.path.abspath(payload["attempt_root"]))
read_roots = tuple(
    os.path.normcase(os.path.abspath(value))
    for value in payload["runtime_read_roots"] + payload["trusted_import_roots"]
)
ancestors = set()
cursor = output
while True:
    ancestors.add(cursor)
    nxt = os.path.dirname(cursor)
    if nxt == cursor:
        break
    cursor = nxt

def normalized(value):
    if isinstance(value, int):
        return None
    try:
        return os.path.normcase(os.path.abspath(os.fspath(value)))
    except Exception:
        raise PermissionError("DENIED")

def within(target, root):
    return target == root or target.startswith(root + os.sep)

def allowed_data(value):
    target = normalized(value)
    if target is None:
        return True
    return within(target, output) or within(target, attempt)

def allowed_read(value):
    target = normalized(value)
    if target is None or allowed_data(target):
        return True
    return any(within(target, root) for root in read_roots)

def read_only_mode(mode):
    if isinstance(mode, str):
        return not any(flag in mode for flag in "wax+")
    if isinstance(mode, int):
        forbidden = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        return mode & forbidden == 0
    return False

def allowed_stat(value):
    target = normalized(value)
    if target is None or allowed_read(target):
        return True
    if target not in ancestors:
        return False
    frame = sys._getframe(1)
    while frame is not None:
        if (
            frame.f_globals.get("__name__") == "_sealed_design_builder"
            and frame.f_code.co_name in {"_directory_chain", "_directory_identity", "_publish_no_replace"}
        ):
            return True
        frame = frame.f_back
    return False

original_stat = os.stat
original_lstat = os.lstat
original_listdir = os.listdir
original_scandir = os.scandir

def guarded_stat(value, *args, **kwargs):
    if not allowed_stat(value):
        raise PermissionError("DENIED")
    return original_stat(value, *args, **kwargs)

def guarded_lstat(value, *args, **kwargs):
    if not allowed_stat(value):
        raise PermissionError("DENIED")
    return original_lstat(value, *args, **kwargs)

def guarded_listdir(value="."):
    if not allowed_read(value):
        raise PermissionError("DENIED")
    return original_listdir(value)

def guarded_scandir(value="."):
    if not allowed_read(value):
        raise PermissionError("DENIED")
    return original_scandir(value)

os.stat = guarded_stat
os.lstat = guarded_lstat
os.listdir = guarded_listdir
os.scandir = guarded_scandir

def audit(event, args):
    if event.startswith("socket.") or event == "subprocess.Popen" or event == "os.system" or event.startswith("os.exec") or event.startswith("os.spawn"):
        raise PermissionError("DENIED")
    if event == "open" and args:
        mode = args[1] if len(args) > 1 else "r"
        if not allowed_read(args[0]) or (not allowed_data(args[0]) and not read_only_mode(mode)):
            raise PermissionError("DENIED")
    if event in {"os.listdir", "os.scandir"} and args and not allowed_read(args[0]):
        raise PermissionError("DENIED")
    if event in {"os.remove", "os.rmdir", "os.mkdir"} and args and not allowed_data(args[0]):
        raise PermissionError("DENIED")
    if event in {"os.rename", "os.replace"}:
        for value in args[:2]:
            if not allowed_data(value):
                raise PermissionError("DENIED")

sys.addaudithook(audit)

for trusted_path in reversed(payload["trusted_import_roots"]):
    if trusted_path not in sys.path:
        sys.path.insert(0, trusted_path)

if payload["mode"] == "build":
    import pyarrow as pa
    import pyarrow.parquet as pq

if payload["mode"] == "probe":
    forbidden = payload["forbidden_paths"]
    result = {}
    try:
        open(forbidden[0], "rb").close()
        result["file_open_denied"] = False
    except Exception:
        result["file_open_denied"] = True
    try:
        os.stat(forbidden[0])
        result["file_stat_denied"] = False
    except Exception:
        result["file_stat_denied"] = True
    try:
        for directory in forbidden[1:]:
            os.listdir(directory)
        result["directory_list_denied"] = False
    except Exception:
        result["directory_list_denied"] = True
    try:
        os.stat(forbidden[-1])
        result["parent_stat_denied"] = False
    except Exception:
        result["parent_stat_denied"] = True
    try:
        os.listdir(payload["prior_attempt_path"])
        result["prior_attempt_denied"] = False
    except Exception:
        result["prior_attempt_denied"] = True
    try:
        import socket
        socket.socket()
        result["network_denied"] = False
    except Exception:
        result["network_denied"] = True
    try:
        subprocess.run([sys.executable, "-c", "pass"], check=False)
        result["subprocess_denied"] = False
    except Exception:
        result["subprocess_denied"] = True
    pickle.dump({"ok": True, "result": result}, sys.stdout.buffer)
elif payload["mode"] == "import_probe":
    module = __import__(payload["package_name"])
    result = {
        "import_read_denied": getattr(module, "IMPORT_READ_DENIED", False) is True,
        "side_effect_absent": getattr(module, "IMPORT_READ_DENIED", False) is True,
    }
    pickle.dump({"ok": True, "result": result}, sys.stdout.buffer)
else:
    source = payload["builder_bytes"]
    if hashlib.sha256(source).hexdigest().upper() != payload["builder_sha256"]:
        raise RuntimeError("INVALID_WORKER")
    namespace = {
        "__file__": payload["builder_label"],
        "__name__": "_sealed_design_builder",
        "__verified_sha256__": payload["builder_sha256"],
    }
    exec(compile(source, payload["builder_label"], "exec"), namespace)

    class PublicCapability:
        __slots__ = ("payloads", "receipt", "manifest")
        def __init__(self):
            self.payloads = payload["design_payloads"]
            self.receipt = payload["custody_receipt"]
            self.manifest = payload["custody_manifest"]
        def design_dates(self):
            return tuple(sorted(self.payloads))
        def read_design_day(self, day):
            return bytes(self.payloads[day])
        def public_receipt_bytes(self):
            return bytes(self.receipt)
        def public_manifest_bytes(self):
            return bytes(self.manifest)

    projection = namespace["ProjectionCapability"].from_bytes_for_testing(
        payload["projection_bytes"], payload["projection_receipt"]
    )
    contract = namespace["DesignSourceContract"](**payload["contract"])
    result = namespace["build_design_source"](
        PublicCapability(),
        projection,
        payload["output_root"],
        contract,
        attempt_root=payload["attempt_root"],
        expected_attempt_identity=tuple(payload["attempt_identity"]),
    )
    pickle.dump({"ok": True, "result": result}, sys.stdout.buffer)
'''


def _run_worker(payload: dict[str, object]) -> dict[str, object]:
    payload = dict(payload)
    payload["runtime_read_roots"] = [_validated_directory_root(Path(sys.base_prefix))]
    trusted = payload.pop("requested_import_roots", [])
    if type(trusted) is not list:
        raise ValueError
    payload["trusted_import_roots"] = [_validated_directory_root(value) for value in trusted]
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "WINDIR": os.environ.get("WINDIR", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
    }
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", _WORKER_BOOTSTRAP],
        input=pickle.dumps(payload, protocol=5),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,
        check=False,
        env=environment,
        cwd=str(Path(str(payload["output_root"])).absolute().parent),
    )
    if completed.returncode != 0 or completed.stderr:
        raise ValueError
    value = pickle.loads(completed.stdout)
    if type(value) is not dict or value.get("ok") is not True or type(value.get("result")) is not dict:
        raise ValueError
    return value["result"]


def run_design_containment_probe(
    output_root: Path | str,
    forbidden_paths: list[Path | str],
    *,
    prior_attempt_path: Path | str,
) -> dict[str, object]:
    try:
        output = Path(output_root).absolute()
        if output.exists() or type(forbidden_paths) is not list or len(forbidden_paths) < 2:
            raise ValueError
        attempt, attempt_identity = _precreate_attempt(output)
        return _run_worker(
            {
                "mode": "probe",
                "output_root": str(output),
                "attempt_root": str(attempt),
                "attempt_identity": attempt_identity,
                "forbidden_paths": [str(Path(path).absolute()) for path in forbidden_paths],
                "prior_attempt_path": str(Path(prior_attempt_path).absolute()),
            }
        )
    except Exception as exc:
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


def run_import_containment_probe(
    output_root: Path | str,
    trusted_import_root: Path | str,
    package_name: str,
    forbidden_path: Path | str,
    side_effect_path: Path | str,
) -> dict[str, object]:
    try:
        output = Path(output_root).absolute()
        trusted = Path(trusted_import_root).absolute()
        forbidden = Path(forbidden_path).absolute()
        side_effect = Path(side_effect_path).absolute()
        if (
            output.exists()
            or type(package_name) is not str
            or not package_name.isidentifier()
            or forbidden == side_effect
        ):
            raise ValueError
        attempt, attempt_identity = _precreate_attempt(output)
        result = _run_worker(
            {
                "mode": "import_probe",
                "output_root": str(output),
                "attempt_root": str(attempt),
                "attempt_identity": attempt_identity,
                "requested_import_roots": [str(trusted)],
                "package_name": package_name,
            }
        )
        if side_effect.exists():
            raise ValueError
        return result
    except Exception as exc:
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


def _sealed_design_build(
    builder_bytes: bytes,
    packet: dict[str, object],
    design_capability,
    projection_capability,
    contract_override: dict[str, object] | None = None,
    bound_attempt_path: Path | str | None = None,
    bound_attempt_identity: tuple[int, ...] | None = None,
) -> dict[str, object]:
    dates = tuple(design_capability.design_dates())
    design_payloads = {day: design_capability.read_design_day(day) for day in dates}
    if any(type(day) is not str or type(value) is not bytes for day, value in design_payloads.items()):
        raise ValueError
    output = Path(str(packet["design_source_output_root"])).absolute()
    if bound_attempt_path is None:
        if bound_attempt_identity is not None:
            raise ValueError
        attempt = output.parent / ("." + output.name + ".attempt-" + str(packet["source_attempt_id"]))
        attempt_identity = _precreate_bound_stage(attempt)
    else:
        attempt = Path(bound_attempt_path).absolute()
        if (
            attempt.parent != output.parent
            or type(bound_attempt_identity) is not tuple
            or _directory_identity(attempt) != bound_attempt_identity
        ):
            raise ValueError
        attempt_identity = bound_attempt_identity
    contract_values = dict(contract_override) if contract_override is not None else {
        "design_date_set_sha256": packet["design_date_set_sha256"],
        "expected_design_dates": EXPECTED_DESIGN_DATES,
        "expected_rows_per_day": EXPECTED_ROWS_PER_DAY,
        "expected_total_rows": EXPECTED_TOTAL_ROWS,
        "first_design_date": FIRST_DESIGN_DATE,
        "last_design_date": LAST_DESIGN_DATE,
    }
    if contract_values.get("builder_tool_sha256", packet["design_builder_tool_sha256"]) != packet["design_builder_tool_sha256"]:
        raise ValueError
    contract_values["builder_tool_sha256"] = packet["design_builder_tool_sha256"]
    expected_provenance = {
        "source_attempt_id": packet["source_attempt_id"],
        "design_stage_path": str(attempt),
        "stage_role": "DESIGN",
        "supervisor_review_base_sha256": packet["supervisor_review_base_sha256"],
    }
    if any(contract_values.get(key, value) != value for key, value in expected_provenance.items()):
        raise ValueError
    contract_values.update(expected_provenance)
    return _run_worker(
        {
            "mode": "build",
            "output_root": str(output),
            "attempt_root": str(attempt),
            "attempt_identity": attempt_identity,
            "requested_import_roots": [_pyarrow_import_root()],
            "builder_bytes": builder_bytes,
            "builder_sha256": packet["design_builder_tool_sha256"],
            "builder_label": packet["design_builder_tool_path"],
            "design_payloads": design_payloads,
            "custody_receipt": design_capability.public_receipt_bytes(),
            "custody_manifest": design_capability.public_manifest_bytes(),
            "projection_bytes": projection_capability.projection_bytes(),
            "projection_receipt": projection_capability.receipt_bytes(),
            "contract": contract_values,
        }
    )


def _supervise_reviewed(
    packet_path: Path | str,
    reviewed_sha256: str,
    frozen: FrozenBindings,
    *,
    custody_runner=None,
    projection_runner=None,
    design_runner=None,
    validator_runner=None,
    lifecycle_hook=None,
) -> dict[str, object]:
    packet: dict[str, object] | None = None
    packet_sha256: str | None = None
    runtime_supervisor_sha256: str | None = None
    attempt_started_sha256: str | None = None
    attempt_started_payload: bytes | None = None
    attempt_root_identity: tuple[int, ...] | None = None
    attempt_started_identity: tuple[int, ...] | None = None
    terminal_evidence: dict[str, object] = {}
    try:
        packet, packet_sha256 = read_reviewed_run_packet(packet_path, reviewed_sha256, frozen)
        runtime_supervisor_sha256 = frozen.runtime_supervisor_sha256
        if runtime_supervisor_sha256 is None or frozen.source_identity is None:
            raise ValueError
        if lifecycle_hook is not None:
            lifecycle_hook("after_tool_verification")
        custodian_module = _execute_verified(
            frozen.verified_bytes["custodian_tool_path"],
            str(packet["custodian_tool_path"]),
            str(packet["custodian_tool_sha256"]),
        )
        builder_module = _execute_verified(
            frozen.verified_bytes["design_builder_tool_path"],
            str(packet["design_builder_tool_path"]),
            str(packet["design_builder_tool_sha256"]),
        )
        validator_module = _execute_verified(
            frozen.verified_bytes["validator_tool_path"],
            str(packet["validator_tool_path"]),
            str(packet["validator_tool_sha256"]),
        )
        projection_authority = builder_module.ProjectionAuthority(
            parent_ledger_sha256=packet["parent_stage0_ledger_sha256"],
            parent_receipt_sha256=packet["parent_stage0_receipt_sha256"],
            design_date_set_sha256=packet["design_date_set_sha256"],
            expected_design_dates=EXPECTED_DESIGN_DATES,
            projector_tool_sha256=packet["design_builder_tool_sha256"],
        )
        projector = projection_runner or builder_module.project_design_stage0
        projection_capability = projector(
            Path(str(packet["parent_stage0_ledger_path"])),
            Path(str(packet["parent_stage0_receipt_path"])),
            projection_authority,
        )
        if lifecycle_hook is not None:
            lifecycle_hook("before_attempt_start")
        (
            attempt_started_sha256,
            _,
            attempt_root_identity,
            attempt_started_identity,
            attempt_started_payload,
        ) = _create_attempt_started(
            packet,
            Path(packet_path).absolute(),
            packet_sha256,
            runtime_supervisor_sha256,
            frozen.source_identity,
        )
        if lifecycle_hook is not None:
            lifecycle_hook("after_attempt_start")
        custody_stage_identity = _precreate_bound_stage(Path(str(packet["custody_stage_path"])).absolute())
        custody_authority = custodian_module.CustodyAuthority(
            collection_plan_sha256=packet["collection_plan_sha256"],
            source_sha256=packet["source_sha256"],
            source_bytes=packet["source_bytes"],
            source_manifest_sha256=packet["source_manifest_sha256"],
            source_footer_length=packet["source_footer_length"],
            source_footer_start=packet["source_footer_start"],
            source_footer_sha256=packet["source_footer_sha256"],
            clock_sha256=packet["clock_sha256"],
            custodian_tool_sha256=packet["custodian_tool_sha256"],
            supervisor_review_base_sha256=packet["supervisor_review_base_sha256"],
            source_attempt_id=packet["source_attempt_id"],
            custody_stage_path=packet["custody_stage_path"],
            custody_stage_identity=custody_stage_identity,
            stage_role="CUSTODY",
            source_identity=frozen.source_identity,
        )
        custody = custody_runner or custodian_module.run_custody
        custody_receipt, design_capability = custody(
            Path(str(packet["source_path"])),
            Path(str(packet["source_manifest_path"])),
            Path(str(packet["collection_plan_path"])),
            Path(str(packet["clock_path"])),
            Path(str(packet["splitvault_output_root"])),
            authority=custody_authority,
            lifecycle_hook=lifecycle_hook,
        )
        if (
            type(custody_receipt) is not dict
            or custody_receipt.get("verdict") != "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY"
            or custody_receipt.get("source_attempt_id") != packet["source_attempt_id"]
            or custody_receipt.get("stage_path") != packet["custody_stage_path"]
            or custody_receipt.get("stage_role") != "CUSTODY"
            or custody_receipt.get("supervisor_review_base_sha256") != packet["supervisor_review_base_sha256"]
            or custody_receipt.get("source_footer_length") != packet["source_footer_length"]
            or custody_receipt.get("source_footer_start") != packet["source_footer_start"]
            or custody_receipt.get("source_footer_sha256") != packet["source_footer_sha256"]
        ):
            raise ValueError
        terminal_evidence.update(
            {
                "custody_public_manifest_sha256": _digest(design_capability.public_manifest_bytes()),
                "custody_public_receipt_sha256": _digest(design_capability.public_receipt_bytes()),
            }
        )
        contract = builder_module.DesignSourceContract(
            design_date_set_sha256=packet["design_date_set_sha256"],
            expected_design_dates=EXPECTED_DESIGN_DATES,
            expected_rows_per_day=EXPECTED_ROWS_PER_DAY,
            expected_total_rows=EXPECTED_TOTAL_ROWS,
            first_design_date=FIRST_DESIGN_DATE,
            last_design_date=LAST_DESIGN_DATE,
            builder_tool_sha256=packet["design_builder_tool_sha256"],
            source_attempt_id=packet["source_attempt_id"],
            design_stage_path=packet["design_stage_path"],
            stage_role="DESIGN",
            supervisor_review_base_sha256=packet["supervisor_review_base_sha256"],
        )
        design_stage = Path(str(packet["design_stage_path"])).absolute()
        design_stage_identity = _precreate_bound_stage(design_stage)
        if design_runner is None:
            result = _sealed_design_build(
                frozen.verified_bytes["design_builder_tool_path"],
                packet,
                design_capability,
                projection_capability,
                bound_attempt_path=packet["design_stage_path"],
                bound_attempt_identity=design_stage_identity,
            )
            pending_binding = _bind_pending_output(packet["design_source_output_root"], result)
            if _directory_anchor(pending_binding["expected_root_identity"]) != _directory_anchor(design_stage_identity):
                raise ValueError
        else:
            result = design_runner(
                design_capability,
                projection_capability,
                Path(str(packet["design_source_output_root"])),
                contract,
                attempt_root=design_stage,
                expected_attempt_identity=design_stage_identity,
            )
            if _directory_identity(design_stage) != design_stage_identity:
                raise ValueError
            pending_binding = {
                "pending_receipt_sha256": result.get("pending_receipt_sha256", "0" * 64),
                "pending_tree_sha256": result.get("pending_tree_sha256", "0" * 64),
                "expected_root_identity": (0, 0, 0, 0, 0, 0),
                "expected_directory_identities": {".": (0, 0, 0, 0, 0, 0)},
                "expected_file_identities": {"synthetic": (0, 0, 0, 0, 0, 0, 0)},
            }
        expected_design_provenance = {
            "source_attempt_id": packet["source_attempt_id"],
            "stage_path": packet["design_stage_path"],
            "stage_role": "DESIGN",
            "supervisor_review_base_sha256": packet["supervisor_review_base_sha256"],
        }
        if (
            type(result) is not dict
            or result.get("verdict") != "PENDING_INDEPENDENT_VALIDATION"
            or any(result.get(key) != value for key, value in expected_design_provenance.items())
        ):
            raise ValueError
        terminal_evidence.update(
            {
                "design_stage_path": packet["design_stage_path"],
                "design_stage_role": "DESIGN",
                "pending_receipt_sha256": pending_binding["pending_receipt_sha256"],
                "pending_tree_sha256": pending_binding["pending_tree_sha256"],
            }
        )
        custody_manifest_rows = _canonical_rows(design_capability.public_manifest_bytes())
        custody_day_sha256: dict[str, str] = {}
        for item in custody_manifest_rows:
            day = item.get("date")
            digest = item.get("sha256")
            if type(day) is not str or not _valid_sha(digest) or day in custody_day_sha256:
                raise ValueError
            custody_day_sha256[day] = digest
        validation_authority = validator_module.ValidationAuthority(
            design_date_set_sha256=packet["design_date_set_sha256"],
            expected_design_dates=EXPECTED_DESIGN_DATES,
            expected_rows_per_day=EXPECTED_ROWS_PER_DAY,
            expected_total_rows=EXPECTED_TOTAL_ROWS,
            first_design_date=FIRST_DESIGN_DATE,
            last_design_date=LAST_DESIGN_DATE,
            validator_tool_sha256=packet["validator_tool_sha256"],
            validator_test_sha256=packet["validator_test_sha256"],
            custodian_public_receipt_sha256=_digest(design_capability.public_receipt_bytes()),
            custodian_public_manifest_sha256=_digest(design_capability.public_manifest_bytes()),
            expected_pending_receipt_sha256=pending_binding["pending_receipt_sha256"],
            expected_pending_tree_sha256=pending_binding["pending_tree_sha256"],
            parent_ledger_sha256=packet["parent_stage0_ledger_sha256"],
            parent_receipt_sha256=packet["parent_stage0_receipt_sha256"],
            projector_tool_sha256=packet["design_builder_tool_sha256"],
            builder_tool_sha256=packet["design_builder_tool_sha256"],
            source_attempt_id=packet["source_attempt_id"],
            design_stage_path=packet["design_stage_path"],
            stage_role="DESIGN",
            supervisor_review_base_sha256=packet["supervisor_review_base_sha256"],
            custody_design_day_sha256=custody_day_sha256,
            expected_root_identity=pending_binding["expected_root_identity"],
            expected_directory_identities=pending_binding["expected_directory_identities"],
            expected_file_identities=pending_binding["expected_file_identities"],
        )
        validator = validator_runner or validator_module.validate_design_source
        validation = validator(Path(str(packet["design_source_output_root"])), validation_authority)
        if (
            type(validation) is not dict
            or validation.get("verdict") != "SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET"
            or any(validation.get(key) != value for key, value in expected_design_provenance.items())
        ):
            raise ValueError
        safe_validation = {
            key: validation[key]
            for key in (
                "design_date_set_sha256",
                "source_receipt_sha256",
                "source_attempt_id",
                "stage_path",
                "stage_role",
                "supervisor_review_base_sha256",
                "validated_dates",
                "validated_m1_rows",
                "validator_test_sha256",
                "validator_tool_sha256",
                "verdict",
            )
            if key in validation
        }
        terminal_evidence["source_receipt_sha256"] = validation.get("source_receipt_sha256", "0" * 64)
        terminal_sha256 = _create_attempt_terminal(
            packet,
            packet_sha256,
            runtime_supervisor_sha256,
            attempt_started_sha256,
            attempt_started_payload,
            attempt_root_identity,
            attempt_started_identity,
            "SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET",
            terminal_evidence,
        )
        return {
            **safe_validation,
            "attempt_started_sha256": attempt_started_sha256,
            "attempt_terminal_sha256": terminal_sha256,
            "packet_sha256": packet_sha256,
            "runtime_supervisor_sha256": runtime_supervisor_sha256,
            "source_attempt_id": packet["source_attempt_id"],
            "source_verdict": safe_validation["verdict"],
            "supervisor_review_base_sha256": packet["supervisor_review_base_sha256"],
        }
    except Exception as exc:
        if (
            packet is not None
            and packet_sha256 is not None
            and runtime_supervisor_sha256 is not None
            and attempt_started_sha256 is not None
            and attempt_started_payload is not None
            and attempt_root_identity is not None
            and attempt_started_identity is not None
        ):
            try:
                _create_attempt_terminal(
                    packet,
                    packet_sha256,
                    runtime_supervisor_sha256,
                    attempt_started_sha256,
                    attempt_started_payload,
                    attempt_root_identity,
                    attempt_started_identity,
                    "SOURCE_ATTEMPT_FAILED_ENGINEERING_NO_MARKET_VERDICT",
                    terminal_evidence,
                )
            except Exception:
                pass
        if isinstance(exc, InvalidSupervisor) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


def supervise(packet_path: Path | str) -> dict[str, object]:
    try:
        if REVIEWED_RUN_PACKET_SHA256 is None:
            raise ValueError
        path = Path(packet_path).absolute()
        if path != Path(__file__).absolute().with_name(RUN_PACKET_FILENAME):
            raise ValueError
        frozen = _production_frozen(path)
        return _supervise_reviewed(path, REVIEWED_RUN_PACKET_SHA256, frozen)
    except Exception as exc:
        if isinstance(exc, InvalidSupervisor) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidSupervisor(PUBLIC_ERROR) from exc
