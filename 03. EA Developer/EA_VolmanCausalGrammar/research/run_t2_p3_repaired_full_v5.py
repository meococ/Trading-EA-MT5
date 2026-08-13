"""One cache-repaired full-ledger T2/P3 identity replay.

The worker calls the frozen v1 run_identity_comparisons and write_result_packet.
Only the ECRS emitter global is substituted by the parity-locked cache successor;
all other wrappers record stage progress and delegate to the frozen functions.
No trade or economic fields are read, and success cannot authorize an EA build.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Callable, Mapping

import run_t2_p3_dedup as v1
import run_t2_p3_stage_instrumented_v3 as stage_v3
import t2_dedup_mirrors as frozen
import t2_dedup_mirrors_ecrs_cache as cache_v4


REPO_ROOT = v1.REPO_ROOT.resolve()
LOCK_PATH = REPO_ROOT / "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P3_REPAIRED_FULL_LOCK_V5.json"
LOCK_SCHEMA = "t2_p3_repaired_full_lock.v5"
EVIDENCE_ROOT = (REPO_ROOT / "03. EA Developer/EA_VolmanCausalGrammar/research/evidence").resolve()
ALWAYS_FILES = frozenset({"stage_heartbeat.jsonl", "stage_receipt.json"})
SUCCESS_TOP_LEVEL = frozenset({"stage_heartbeat.jsonl", "stage_receipt.json", "identity_packet"})
PACKET_FILES = frozenset({
    "t2_structural_full.jsonl",
    "t2_reject_full.jsonl",
    "t2_pbp_audit_full.jsonl",
    "ecrs_v1_full.jsonl",
    "t2_pbp_identity_full.jsonl",
    "t2_pbp_break_full.jsonl",
    "t2_pbp_contact_full.jsonl",
    "scc_control_full.jsonl",
    "scc_challenger_full.jsonl",
    "t2_manifest.json",
    "ecrs_manifest.json",
    "d8_break_t2_manifest.json",
    "d8_break_scc_manifest.json",
    "d8_contact_t2_manifest.json",
    "d8_contact_scc_manifest.json",
    "result.json",
    "receipt.json",
})
WORKER_MARKER = "T2_P3_REPAIRED_FULL_WORKER_V5="


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _exact_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if set(value) != expected:
        raise frozen.IdentityContractError(f"{name} requires exact keys")


def verify_lock(path: Path = LOCK_PATH) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    _exact_keys(
        document,
        {
            "schema_version", "campaign", "generation", "phase", "status", "authority",
            "frozen_at_utc", "owner_scope", "replay", "bindings", "prohibitions",
        },
        "repaired-full lock",
    )
    if (
        document["schema_version"] != LOCK_SCHEMA
        or document["campaign"] != "PRO_TRADER_REPLACEMENT"
        or document["generation"] != "T2"
        or document["phase"] != "P3_OUTCOME_BLIND_DEDUP"
        or document["status"] != "FROZEN_PRE_REPAIRED_FULL_IDENTITY_REPLAY"
        or document["authority"] != "ENGINEERING_FULL_IDENTITY_ONLY_NO_BUILD_NO_ECONOMICS"
        or document["owner_scope"] != "XAU_FOREX_ONLY_BTC_NOT_GATING"
    ):
        raise frozen.IdentityContractError("repaired-full lock authority/scope mismatch")
    frozen_at = datetime.fromisoformat(str(document["frozen_at_utc"]).replace("Z", "+00:00"))
    if frozen_at.tzinfo is None or frozen_at.astimezone(timezone.utc) > datetime.now(timezone.utc):
        raise frozen.IdentityContractError("repaired-full lock timestamp is invalid")

    replay = document["replay"]
    _exact_keys(
        replay,
        {
            "symbol", "timeframe", "source_rows", "source_first_utc", "source_last_utc",
            "max_wall_seconds", "output_directory", "packet_directory", "expected_command",
            "always_files", "success_top_level", "packet_files",
        },
        "repaired-full replay",
    )
    if (
        replay["symbol"] != "EURUSD"
        or replay["timeframe"] != "M5"
        or replay["source_rows"] != v1.BOUND_D7_STAGE0_RECORD_COUNT
        or replay["source_first_utc"] != frozen.BOUND_D7_STAGE0_FIRST_UTC
        or replay["source_last_utc"] != frozen.BOUND_D7_STAGE0_LAST_UTC
        or replay["max_wall_seconds"] != 900
        or replay["output_directory"] != "03. EA Developer/EA_VolmanCausalGrammar/research/evidence/T2_P3_REPAIRED_FULL_V5_001"
        or replay["packet_directory"] != "identity_packet"
        or replay["expected_command"] != 'python "03. EA Developer/EA_VolmanCausalGrammar/research/run_t2_p3_repaired_full_v5.py" --run-full --output-dir "03. EA Developer/EA_VolmanCausalGrammar/research/evidence/T2_P3_REPAIRED_FULL_V5_001"'
        or set(replay["always_files"]) != ALWAYS_FILES
        or set(replay["success_top_level"]) != SUCCESS_TOP_LEVEL
        or set(replay["packet_files"]) != PACKET_FILES
        or len(replay["packet_files"]) != len(PACKET_FILES)
    ):
        raise frozen.IdentityContractError("repaired-full replay contract mismatch")

    verified: dict[str, str] = {}
    if not isinstance(document["bindings"], dict) or not document["bindings"]:
        raise frozen.IdentityContractError("repaired-full lock requires bindings")
    for name, binding in document["bindings"].items():
        _exact_keys(binding, {"path", "sha256", "role"}, f"binding {name}")
        relative = binding["path"]
        expected = binding["sha256"]
        if (
            not isinstance(relative, str)
            or re.fullmatch(r"[0-9A-F]{64}", str(expected)) is None
            or not isinstance(binding["role"], str)
            or not binding["role"]
        ):
            raise frozen.IdentityContractError(f"invalid repaired-full binding: {name}")
        candidate = (REPO_ROOT / relative).resolve()
        try:
            candidate.relative_to(REPO_ROOT)
        except ValueError as exc:
            raise frozen.IdentityContractError(f"binding escapes repository: {name}") from exc
        actual = frozen.sha256_file(candidate)
        if actual != expected:
            raise frozen.IdentityContractError(f"repaired-full binding SHA mismatch: {name}")
        verified[name] = actual

    required = {
        "NO_SECOND_FULL_REPLAY_OR_TIMEOUT_EXTENSION",
        "NO_PREFIX_OR_GENERIC_D7_COMPARATOR",
        "NO_GATE_THRESHOLD_KEY_SOURCE_SCHEDULE_GRAMMAR_OR_COMPARISON_CHANGE",
        "NO_OUTCOMES_OPTIMIZATION_EDGE_CLAIM_EA_BUILD_MT5_OR_GIT",
        "NO_PARTIAL_PACKET_ON_TIMEOUT_OR_NONZERO_EXIT",
        "NO_BUILD_LIVE_OR_ECONOMIC_AUTHORITY_FROM_SUCCESS",
    }
    if not isinstance(document["prohibitions"], list) or set(document["prohibitions"]) != required:
        raise frozen.IdentityContractError("repaired-full prohibitions mismatch")
    return {"document": document, "path": str(path), "sha256": frozen.sha256_file(path), "verified": verified}


def _resolve_output(path: Path, expected_relative: str) -> Path:
    resolved = path.resolve()
    expected = (REPO_ROOT / expected_relative).resolve()
    if resolved != expected:
        raise frozen.IdentityContractError("repaired-full output differs from lock")
    try:
        resolved.relative_to(EVIDENCE_ROOT)
    except ValueError as exc:
        raise frozen.IdentityContractError("repaired-full output escapes evidence root") from exc
    return resolved


def _remove_packet_dir(packet_dir: Path, output_dir: Path) -> None:
    resolved = packet_dir.resolve()
    expected = (output_dir / "identity_packet").resolve()
    if resolved != expected or resolved.parent != output_dir.resolve():
        raise frozen.IdentityContractError("full packet cleanup target differs from exact output child")
    if resolved.exists():
        shutil.rmtree(resolved)


def _instrument_frozen_v1(recorder: stage_v3.HeartbeatRecorder) -> dict[str, Callable[..., Any]]:
    """Wrap frozen globals for observation; substitute only cached ECRS."""
    names = (
        "load_bound_stage0_bars",
        "emit_scc_control_identities",
        "emit_scc_challenger_identities",
        "assert_scc_challenger_strict_subset",
        "emit_t2_d7_structural_identities",
        "emit_ecrs_v1_identities",
        "compare_d7_primary_full_ledgers",
        "emit_t2_pbp_like_identities",
        "_compare_d8",
        "write_result_packet",
    )
    original = {name: getattr(v1, name) for name in names}
    d8_index = 0

    def stage_call(name: str, fn: Callable[..., Any], *args: Any, total: int | None = None, **kwargs: Any) -> Any:
        recorder.begin_stage(
            name,
            progress_unit="source_bar" if total is not None else "none",
            progress_total=total,
        )
        result = fn(*args, **kwargs)
        recorder.end_stage()
        return result

    def load_bound_stage0_bars() -> Any:
        return stage_call("load_bound_stage0_bars", original["load_bound_stage0_bars"])

    def emit_scc_control(records: Any, *, source_bars: Any) -> Any:
        observed = stage_v3.ObservedSequence(source_bars, recorder)
        return stage_call(
            "scc_control_reference",
            original["emit_scc_control_identities"],
            records,
            source_bars=observed,
            total=len(source_bars),
        )

    def emit_scc_challenger(records: Any, *, source_bars: Any) -> Any:
        observed = stage_v3.ObservedSequence(source_bars, recorder)
        return stage_call(
            "scc_challenger_reference",
            original["emit_scc_challenger_identities"],
            records,
            source_bars=observed,
            total=len(source_bars),
        )

    def assert_subset(control: Any, challenger: Any) -> Any:
        return stage_call(
            "scc_strict_subset",
            original["assert_scc_challenger_strict_subset"],
            control,
            challenger,
        )

    def emit_t2(bars: Any, **kwargs: Any) -> Any:
        observed = stage_v3.ObservedSequence(bars, recorder)
        return stage_call(
            "t2_structural_full",
            original["emit_t2_d7_structural_identities"],
            observed,
            total=len(bars),
            **kwargs,
        )

    def emit_ecrs(rows: Any, **kwargs: Any) -> Any:
        observed = stage_v3.ObservedSequence(rows, recorder)
        return stage_call(
            "ecrs_cached_full",
            cache_v4.emit_ecrs_v1_identities_cached,
            observed,
            total=len(rows),
            **kwargs,
        )

    def compare_d7(*args: Any, **kwargs: Any) -> Any:
        return stage_call(
            "compare_d7_primary_full_ledgers",
            original["compare_d7_primary_full_ledgers"],
            *args,
            **kwargs,
        )

    def emit_pbp(*args: Any, **kwargs: Any) -> Any:
        return stage_call(
            "pbp_identity_projection_full",
            original["emit_t2_pbp_like_identities"],
            *args,
            **kwargs,
        )

    def compare_d8(*args: Any, **kwargs: Any) -> Any:
        nonlocal d8_index
        d8_index += 1
        return stage_call(
            f"compare_d8_full_{d8_index}",
            original["_compare_d8"],
            *args,
            **kwargs,
        )

    def write_packet(result: Any, packet_dir: Path) -> Any:
        return stage_call(
            "write_exact_v1_result_packet",
            original["write_result_packet"],
            result,
            packet_dir,
        )

    v1.load_bound_stage0_bars = load_bound_stage0_bars
    v1.emit_scc_control_identities = emit_scc_control
    v1.emit_scc_challenger_identities = emit_scc_challenger
    v1.assert_scc_challenger_strict_subset = assert_subset
    v1.emit_t2_d7_structural_identities = emit_t2
    v1.emit_ecrs_v1_identities = emit_ecrs
    v1.compare_d7_primary_full_ledgers = compare_d7
    v1.emit_t2_pbp_like_identities = emit_pbp
    v1._compare_d8 = compare_d8
    v1.write_result_packet = write_packet
    return original


def _restore_v1(original: Mapping[str, Callable[..., Any]]) -> None:
    for name, value in original.items():
        setattr(v1, name, value)


def _run_worker(output_dir: Path, packet_dir: Path) -> dict[str, Any]:
    recorder = stage_v3.HeartbeatRecorder(output_dir / "stage_heartbeat.jsonl")
    original_verify = v1.verify_execution_bindings
    original_functions: dict[str, Callable[..., Any]] = {}
    started = time.perf_counter()
    try:
        recorder.begin_stage("verify_all_bindings")
        bindings = v1.verify_execution_bindings(require_committed=False)
        cache_lock = cache_v4.verify_lock()
        full_lock = verify_lock()
        v1.verify_execution_bindings = lambda: dict(bindings)
        recorder.end_stage()

        original_functions = _instrument_frozen_v1(recorder)
        recorder.begin_stage("run_exact_v1_identity_comparisons")
        result = v1.run_identity_comparisons()
        recorder.end_stage()
        if (
            result["data"]["rows"] != v1.BOUND_D7_STAGE0_RECORD_COUNT
            or result["data"]["first_utc"] != frozen.BOUND_D7_STAGE0_FIRST_UTC
            or result["data"]["last_utc"] != frozen.BOUND_D7_STAGE0_LAST_UTC
            or result["build_authorized"] is not False
            or result["economic_authority"] != "NONE"
        ):
            raise frozen.IdentityContractError("full result authority or coverage mismatch")
        frozen.reject_outcome_fields(result)
        receipt = v1.write_result_packet(result, packet_dir)
        verified = verify_packet(packet_dir)
        recorder.close()
        return {
            "status": "WORKER_COMMITTED_EXACT_V1_FULL_IDENTITY_PACKET",
            "cache_successor_sha256": frozen.sha256_file(Path(cache_v4.__file__)),
            "cache_lock_sha256": cache_lock["sha256"],
            "full_lock_sha256": full_lock["sha256"],
            "packet_receipt_sha256": verified["receipt_sha256"],
            "packet_result_sha256": receipt["result_sha256"],
            "worker_wall_seconds": time.perf_counter() - started,
        }
    finally:
        if original_functions:
            _restore_v1(original_functions)
        v1.verify_execution_bindings = original_verify


def verify_packet(packet_dir: Path) -> dict[str, Any]:
    names = set(path.name for path in packet_dir.iterdir())
    if names != PACKET_FILES:
        raise frozen.IdentityContractError("full packet file set mismatch")
    receipt_path = packet_dir / "receipt.json"
    result_path = packet_dir / "result.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if receipt["result_sha256"] != frozen.sha256_file(result_path):
        raise frozen.IdentityContractError("full packet result SHA mismatch")
    for entry in receipt["artifacts"].values():
        artifact = Path(entry["path"]).resolve()
        try:
            artifact.relative_to(packet_dir.resolve())
        except ValueError as exc:
            raise frozen.IdentityContractError("full packet artifact escapes packet directory") from exc
        if frozen.sha256_file(artifact) != entry["sha256"]:
            raise frozen.IdentityContractError("full packet artifact SHA mismatch")
    if (
        result["schema_version"] != "t2_p3_dedup_result.v1"
        or result["authority"] != "P3_IDENTITY_ONLY_NO_BUILD_NO_ECONOMICS"
        or result["data"]["rows"] != v1.BOUND_D7_STAGE0_RECORD_COUNT
        or result["data"]["first_utc"] != frozen.BOUND_D7_STAGE0_FIRST_UTC
        or result["data"]["last_utc"] != frozen.BOUND_D7_STAGE0_LAST_UTC
        or result["build_authorized"] is not False
        or result["economic_authority"] != "NONE"
    ):
        raise frozen.IdentityContractError("full packet authority or coverage mismatch")
    frozen.reject_outcome_fields(result)
    return {
        "receipt_sha256": frozen.sha256_file(receipt_path),
        "result_sha256": frozen.sha256_file(result_path),
        "files": sorted(names),
    }


def _read_heartbeats(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _stderr_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _write_stage_receipt(
    output_dir: Path,
    *,
    lock_sha256: str,
    status: str,
    timed_out: bool,
    child_exit_code: int | None,
    child_stderr: str,
    parent_wall_seconds: float,
    packet_verified: bool,
    packet_receipt_sha256: str | None,
) -> dict[str, Any]:
    heartbeat_path = output_dir / "stage_heartbeat.jsonl"
    heartbeats = _read_heartbeats(heartbeat_path)
    receipt = {
        "schema_version": "t2_p3_repaired_full_stage_receipt.v5",
        "recorded_at_utc": _utc_now(),
        "status": status,
        "authority": "ENGINEERING_FULL_IDENTITY_ONLY_NO_BUILD_NO_ECONOMICS",
        "lock_sha256": lock_sha256,
        "cache_successor_sha256": frozen.sha256_file(Path(cache_v4.__file__)),
        "cache_lock_sha256": cache_v4.verify_lock()["sha256"],
        "source_field_contract": "IDENTITY_ONLY_NO_TRADE_RESULT_FIELDS",
        "economic_claim_authorized": False,
        "build_or_live_authorized": False,
        "rerun_authorized": False,
        "hard_timeout_seconds": 900,
        "timed_out": timed_out,
        "child_exit_code": child_exit_code,
        "child_stderr": child_stderr,
        "parent_wall_seconds": parent_wall_seconds,
        "heartbeat_file": str(heartbeat_path),
        "heartbeat_sha256": frozen.sha256_file(heartbeat_path) if heartbeats else None,
        "heartbeat_lines": len(heartbeats),
        "last_heartbeat": heartbeats[-1] if heartbeats else None,
        "packet_verified": packet_verified,
        "packet_receipt_sha256": packet_receipt_sha256,
    }
    frozen.reject_outcome_fields(receipt)
    v1._atomic_json(output_dir / "stage_receipt.json", receipt)
    return receipt


def run_bounded(output_dir: Path) -> dict[str, Any]:
    lock = verify_lock()
    replay = lock["document"]["replay"]
    output_dir = _resolve_output(output_dir, replay["output_directory"])
    if output_dir.exists():
        raise frozen.IdentityContractError("repaired-full output must be fresh and absent")
    output_dir.mkdir(parents=True, exist_ok=False)
    packet_dir = output_dir / replay["packet_directory"]
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        "--output-dir",
        str(output_dir),
        "--packet-dir",
        str(packet_dir),
    ]
    started = time.perf_counter()
    timed_out = False
    child_exit_code: int | None = None
    child_stderr = ""
    worker: dict[str, Any] | None = None
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=float(replay["max_wall_seconds"]),
            check=False,
        )
        child_exit_code = completed.returncode
        child_stderr = completed.stderr
        markers = [line for line in completed.stdout.splitlines() if line.startswith(WORKER_MARKER)]
        if child_exit_code == 0 and len(markers) == 1:
            worker = json.loads(markers[0][len(WORKER_MARKER):])
            packet = verify_packet(packet_dir)
            packet_verified = True
            status = "PASS_REPAIRED_FULL_IDENTITY_PACKET_ENGINEERING_ONLY"
            packet_receipt_sha256 = packet["receipt_sha256"]
        else:
            _remove_packet_dir(packet_dir, output_dir)
            packet_verified = False
            packet_receipt_sha256 = None
            status = "FAIL_REPAIRED_FULL_NONZERO_OR_MARKER_MISMATCH_NO_PACKET"
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        child_stderr = _stderr_text(exc.stderr)
        _remove_packet_dir(packet_dir, output_dir)
        packet_verified = False
        packet_receipt_sha256 = None
        status = "TIMEOUT_REPAIRED_FULL_NO_PACKET"

    stage_receipt = _write_stage_receipt(
        output_dir,
        lock_sha256=lock["sha256"],
        status=status,
        timed_out=timed_out,
        child_exit_code=child_exit_code,
        child_stderr=child_stderr,
        parent_wall_seconds=time.perf_counter() - started,
        packet_verified=packet_verified,
        packet_receipt_sha256=packet_receipt_sha256,
    )
    names = set(path.name for path in output_dir.iterdir())
    expected = SUCCESS_TOP_LEVEL if packet_verified else ALWAYS_FILES
    if names != expected:
        raise frozen.IdentityContractError("repaired-full top-level output set mismatch")
    if not stage_receipt["heartbeat_lines"]:
        raise frozen.IdentityContractError("repaired-full produced no flushed heartbeat")
    return {"worker": worker, **stage_receipt}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--verify-only", action="store_true")
    modes.add_argument("--run-full", action="store_true")
    modes.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--packet-dir", type=Path, help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.verify_only:
        if args.output_dir is not None or args.packet_dir is not None:
            raise SystemExit("--verify-only takes no runtime path")
        lock = verify_lock()
        bindings = v1.verify_execution_bindings(require_committed=False)
        cache_v4.verify_lock()
        print(json.dumps({
            "status": "PASS_REPAIRED_FULL_VERIFY_ONLY",
            "authority": "ENGINEERING_FULL_IDENTITY_ONLY_NO_BUILD_NO_ECONOMICS",
            "lock_sha256": lock["sha256"],
            "verified_binding_names": sorted(bindings),
        }, indent=2, sort_keys=True))
        return 0
    if args.output_dir is None:
        raise SystemExit("full execution requires --output-dir")
    if args.worker:
        if args.packet_dir is None:
            raise SystemExit("worker requires --packet-dir")
        result = _run_worker(args.output_dir.resolve(), args.packet_dir.resolve())
        print(WORKER_MARKER + json.dumps(result, sort_keys=True))
        return 0
    if args.packet_dir is not None:
        raise SystemExit("parent execution does not accept --packet-dir")
    result = run_bounded(args.output_dir.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
