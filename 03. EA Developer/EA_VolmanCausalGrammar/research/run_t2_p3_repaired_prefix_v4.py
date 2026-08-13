"""One repaired 50k identity packet after cache-only ECRS parity.

The only computation substitution is the parity-locked cached ECRS emitter.
Every loader, T2/SCC emitter, identity comparison and atomic packet writer is
the frozen path.  The packet remains identity/de-dup engineering evidence and
has no economic or full-replay authority.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping

import run_t2_p3_dedup as v1
import run_t2_p3_identity_prefix_v2 as packet_v2
import run_t2_p3_stage_instrumented_v3 as stage_v3
import t2_dedup_mirrors as frozen
import t2_dedup_mirrors_ecrs_cache as cache_v4


REPO_ROOT = v1.REPO_ROOT.resolve()
LOCK_PATH = REPO_ROOT / "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P3_REPAIRED_PREFIX_LOCK_V4.json"
LOCK_SCHEMA = "t2_p3_repaired_prefix_lock.v4"
EVIDENCE_ROOT = (REPO_ROOT / "03. EA Developer/EA_VolmanCausalGrammar/research/evidence").resolve()
PACKET_FILES = packet_v2.EXPECTED_FILES
ALWAYS_FILES = frozenset({"stage_heartbeat.jsonl", "stage_receipt.json"})
SUCCESS_TOP_LEVEL = frozenset({"stage_heartbeat.jsonl", "stage_receipt.json", "identity_packet"})
WORKER_MARKER = "T2_P3_REPAIRED_PREFIX_WORKER_V4="


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
            "frozen_at_utc", "owner_scope", "probe", "bindings", "prohibitions",
        },
        "repaired-prefix lock",
    )
    if (
        document["schema_version"] != LOCK_SCHEMA
        or document["campaign"] != "PRO_TRADER_REPLACEMENT"
        or document["generation"] != "T2"
        or document["phase"] != "P3_OUTCOME_BLIND_DEDUP"
        or document["status"] != "FROZEN_PRE_REPAIRED_50K_PACKET"
        or document["authority"] != "ENGINEERING_REPAIRED_50K_IDENTITY_ONLY"
        or document["owner_scope"] != "XAU_FOREX_ONLY_BTC_NOT_GATING"
    ):
        raise frozen.IdentityContractError("repaired-prefix lock authority/scope mismatch")
    frozen_at = datetime.fromisoformat(str(document["frozen_at_utc"]).replace("Z", "+00:00"))
    if frozen_at.tzinfo is None or frozen_at.astimezone(timezone.utc) > datetime.now(timezone.utc):
        raise frozen.IdentityContractError("repaired-prefix lock timestamp is invalid")

    probe = document["probe"]
    _exact_keys(
        probe,
        {
            "scope", "prefix_bars", "source_rows", "max_wall_seconds", "output_directory",
            "packet_directory", "expected_command", "always_files", "success_top_level",
            "packet_files",
        },
        "repaired-prefix probe",
    )
    if (
        probe["scope"] != "EURUSD_M5_FIRST_50000_REPAIRED_IDENTITY_PACKET"
        or probe["prefix_bars"] != 50000
        or probe["source_rows"] != v1.BOUND_D7_STAGE0_RECORD_COUNT
        or probe["max_wall_seconds"] != 300
        or probe["output_directory"] != "03. EA Developer/EA_VolmanCausalGrammar/research/evidence/T2_P3_REPAIRED_PREFIX_V4_001"
        or probe["packet_directory"] != "identity_packet"
        or probe["expected_command"] != 'python "03. EA Developer/EA_VolmanCausalGrammar/research/run_t2_p3_repaired_prefix_v4.py" --run-prefix --output-dir "03. EA Developer/EA_VolmanCausalGrammar/research/evidence/T2_P3_REPAIRED_PREFIX_V4_001"'
        or set(probe["always_files"]) != ALWAYS_FILES
        or set(probe["success_top_level"]) != SUCCESS_TOP_LEVEL
        or set(probe["packet_files"]) != PACKET_FILES
        or len(probe["packet_files"]) != len(PACKET_FILES)
    ):
        raise frozen.IdentityContractError("repaired-prefix probe contract mismatch")

    verified: dict[str, str] = {}
    if not isinstance(document["bindings"], dict) or not document["bindings"]:
        raise frozen.IdentityContractError("repaired-prefix lock requires bindings")
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
            raise frozen.IdentityContractError(f"invalid repaired-prefix binding: {name}")
        candidate = (REPO_ROOT / relative).resolve()
        try:
            candidate.relative_to(REPO_ROOT)
        except ValueError as exc:
            raise frozen.IdentityContractError(f"binding escapes repository: {name}") from exc
        actual = frozen.sha256_file(candidate)
        if actual != expected:
            raise frozen.IdentityContractError(f"repaired-prefix binding SHA mismatch: {name}")
        verified[name] = actual

    required = {
        "NO_V2_V3_OR_V4_RERUN_OR_OVERWRITE",
        "NO_FULL_596141_REPLAY",
        "NO_GATE_THRESHOLD_KEY_SOURCE_SCHEDULE_OR_COMPARISON_CHANGE",
        "NO_OUTCOMES_OPTIMIZATION_EDGE_CLAIM_EA_BUILD_MT5_OR_GIT",
        "NO_PARTIAL_PACKET_ON_TIMEOUT",
        "NO_FULL_REPLAY_AUTHORITY_FROM_THIS_PACKET",
    }
    if not isinstance(document["prohibitions"], list) or set(document["prohibitions"]) != required:
        raise frozen.IdentityContractError("repaired-prefix prohibitions mismatch")
    return {"document": document, "path": str(path), "sha256": frozen.sha256_file(path), "verified": verified}


def _resolve_output(path: Path, expected_relative: str) -> Path:
    resolved = path.resolve()
    expected = (REPO_ROOT / expected_relative).resolve()
    if resolved != expected:
        raise frozen.IdentityContractError("repaired-prefix output differs from lock")
    try:
        resolved.relative_to(EVIDENCE_ROOT)
    except ValueError as exc:
        raise frozen.IdentityContractError("repaired-prefix output escapes evidence root") from exc
    return resolved


def _remove_packet_dir(packet_dir: Path, output_dir: Path) -> None:
    resolved = packet_dir.resolve()
    expected = (output_dir / "identity_packet").resolve()
    if resolved != expected or resolved.parent != output_dir.resolve():
        raise frozen.IdentityContractError("packet cleanup target differs from exact output child")
    if resolved.exists():
        shutil.rmtree(resolved)


def _run_worker(output_dir: Path, packet_dir: Path) -> dict[str, Any]:
    recorder = stage_v3.HeartbeatRecorder(output_dir / "stage_heartbeat.jsonl")
    original_verify = v1.verify_execution_bindings
    started_total = time.perf_counter()
    stage_times: dict[str, float] = {}

    def begin(name: str, *, total: int | None = None) -> float:
        recorder.begin_stage(
            name,
            progress_unit="source_bar" if total is not None else "none",
            progress_total=total,
        )
        return time.perf_counter()

    def end(name: str, started: float) -> None:
        stage_times[name] = time.perf_counter() - started
        recorder.end_stage()

    try:
        started = begin("verify_frozen_bindings")
        verified = v1.verify_execution_bindings(require_committed=False)
        cache_v4.verify_lock()
        v1.verify_execution_bindings = lambda: dict(verified)
        end("verify_frozen_bindings", started)

        started = begin("load_bound_inputs")
        schedule = v1.load_d7_schedule()
        structural, ecrs_bars, scc_path, metadata = v1.load_bound_stage0_bars()
        calendar = v1.load_bound_news_calendar()
        if metadata["rows"] != v1.BOUND_D7_STAGE0_RECORD_COUNT:
            raise frozen.IdentityContractError("repaired-prefix source row mismatch")
        control_records = v1._load_scc_records(v1.SCC_CONTROL_PATH, v1.SCC_CONTROL_SHA256, challenger=False)
        challenger_records = v1._load_scc_records(v1.SCC_CHALLENGER_PATH, v1.SCC_CHALLENGER_SHA256, challenger=True)
        end("load_bound_inputs", started)

        started = begin("scc_control_reference", total=len(scc_path))
        scc_control = frozen.emit_scc_control_identities(
            control_records,
            source_bars=stage_v3.ObservedSequence(scc_path, recorder),
        )
        end("scc_control_reference", started)

        started = begin("scc_challenger_reference", total=len(scc_path))
        scc_challenger = frozen.emit_scc_challenger_identities(
            challenger_records,
            source_bars=stage_v3.ObservedSequence(scc_path, recorder),
        )
        end("scc_challenger_reference", started)

        started = begin("scc_strict_subset")
        v1.assert_scc_challenger_strict_subset(scc_control, scc_challenger)
        end("scc_strict_subset", started)

        prefix_bars = 50000
        started = begin("t2_structural_prefix", total=prefix_bars)
        t2_result = v1.emit_t2_d7_structural_identities(
            stage_v3.ObservedSequence(structural[:prefix_bars], recorder),
            symbol="EURUSD",
            tick=v1.EURUSD_TICK_SIZE,
            schedule=schedule,
        )
        end("t2_structural_prefix", started)

        started = begin("ecrs_cached_prefix", total=prefix_bars)
        ecrs_events = cache_v4.emit_ecrs_v1_identities_cached(
            stage_v3.ObservedSequence(ecrs_bars[:prefix_bars], recorder),
            symbol="EURUSD",
            news_calendar=calendar,
        )
        end("ecrs_cached_prefix", started)

        started = begin("d7_prefix_comparison")
        d7_prefix = frozen.compare_identities(
            t2_result.events,
            ecrs_events,
            key_fields=frozen.ECRS_IDENTITY_FIELDS,
        )
        end("d7_prefix_comparison", started)

        started = begin("pbp_identity_projection")
        pbp_events = frozen.emit_t2_pbp_like_identities(t2_result.pbp_audits)
        pbp_break = [row for row in pbp_events if row["subset"] == "PBP_BREAK_WINDOW"]
        pbp_contact = [row for row in pbp_events if row["subset"] == "PBP_TOMBSTONE_CONTACT"]
        end("pbp_identity_projection", started)

        started = begin("d8_break_prefix_comparison")
        d8_break = frozen.compare_identities(
            pbp_break,
            scc_control,
            key_fields=frozen.NORMALIZED_OVERLAP_FIELDS,
        )
        end("d8_break_prefix_comparison", started)

        started = begin("d8_contact_prefix_comparison")
        d8_contact = frozen.compare_identities(
            pbp_contact,
            scc_challenger,
            key_fields=frozen.NORMALIZED_OVERLAP_FIELDS,
        )
        end("d8_contact_prefix_comparison", started)

        artifacts = {
            "t2_events": list(t2_result.events),
            "t2_rejects": [asdict(value) for value in t2_result.rejects],
            "t2_pbp_audits": [asdict(value) for value in t2_result.pbp_audits],
            "ecrs_events": ecrs_events,
            "pbp_events": pbp_events,
            "scc_control": scc_control,
            "scc_challenger": scc_challenger,
        }
        result = {
            "schema_version": packet_v2.RESULT_SCHEMA,
            "authority": "ENGINEERING_PREFIX_IDENTITY_ONLY_NO_FULL_GATE_NO_ECONOMICS",
            "created_at_utc": _utc_now(),
            "prefix_scope": "EURUSD_M5_FIRST_50000_REPAIRED_IDENTITY_PACKET",
            "prefix_bars": prefix_bars,
            "bound_source_rows": metadata["rows"],
            "bound_source_sha256": v1.STAGE0_BARS_SHA256,
            "cache_successor_sha256": frozen.sha256_file(Path(cache_v4.__file__)),
            "cache_parity_lock_sha256": cache_v4.verify_lock()["sha256"],
            "prefix_comparisons_are_fatal_gate_authority": False,
            "d7_prefix_diagnostic": asdict(d7_prefix),
            "d8_break_prefix_diagnostic": asdict(d8_break),
            "d8_contact_prefix_diagnostic": asdict(d8_contact),
            "t2_prefix_stats": t2_result.stats,
            "stage_wall_seconds_before_write": stage_times,
            "source_field_contract": "IDENTITY_ONLY_NO_TRADE_RESULT_FIELDS",
            "economic_claim_authorized": False,
            "ea_build_or_mt5_authorized": False,
            "full_replay_authorized_by_this_packet": False,
        }
        frozen.reject_outcome_fields(result)

        started = begin("atomic_identity_packet_write")
        receipt = packet_v2._write_prefix_packet(
            packet_dir,
            result,
            artifacts,
            stage_times=stage_times,
            started_total=started_total,
        )
        end("atomic_identity_packet_write", started)
        verified_packet = packet_v2._verify_packet(packet_dir)
        recorder.close()
        return {
            "status": "WORKER_COMMITTED_REPAIRED_50K_PACKET",
            "packet_receipt_sha256": verified_packet["receipt_sha256"],
            "packet_result_sha256": verified_packet["result_sha256"],
            "packet_files": verified_packet["output_files"],
            "worker_total_wall_seconds": time.perf_counter() - started_total,
        }
    finally:
        v1.verify_execution_bindings = original_verify


def _read_heartbeats(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_stage_receipt(
    output_dir: Path,
    *,
    lock_sha256: str,
    status: str,
    timed_out: bool,
    child_exit_code: int | None,
    parent_wall_seconds: float,
    packet_verified: bool,
    packet_receipt_sha256: str | None,
) -> dict[str, Any]:
    heartbeat_path = output_dir / "stage_heartbeat.jsonl"
    heartbeats = _read_heartbeats(heartbeat_path)
    receipt = {
        "schema_version": "t2_p3_repaired_prefix_stage_receipt.v4",
        "recorded_at_utc": _utc_now(),
        "status": status,
        "authority": "ENGINEERING_REPAIRED_50K_IDENTITY_ONLY",
        "lock_sha256": lock_sha256,
        "source_field_contract": "IDENTITY_ONLY_NO_TRADE_RESULT_FIELDS",
        "economic_claim_authorized": False,
        "full_replay_authorized": False,
        "rerun_authorized": False,
        "hard_timeout_seconds": 300,
        "timed_out": timed_out,
        "child_exit_code": child_exit_code,
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
    probe = lock["document"]["probe"]
    output_dir = _resolve_output(output_dir, probe["output_directory"])
    if output_dir.exists():
        raise frozen.IdentityContractError("repaired-prefix output must be fresh and absent")
    output_dir.mkdir(parents=True, exist_ok=False)
    packet_dir = output_dir / probe["packet_directory"]
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
    worker: dict[str, Any] | None = None
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=float(probe["max_wall_seconds"]),
            check=False,
        )
        child_exit_code = completed.returncode
        markers = [line for line in completed.stdout.splitlines() if line.startswith(WORKER_MARKER)]
        if child_exit_code == 0 and len(markers) == 1:
            worker = json.loads(markers[0][len(WORKER_MARKER):])
            packet_v2._verify_packet(packet_dir)
            packet_verified = True
            status = "PASS_REPAIRED_50K_IDENTITY_PACKET_ENGINEERING_ONLY"
        else:
            _remove_packet_dir(packet_dir, output_dir)
            packet_verified = False
            status = "FAIL_REPAIRED_PREFIX_WORKER_NO_PACKET"
    except subprocess.TimeoutExpired:
        timed_out = True
        _remove_packet_dir(packet_dir, output_dir)
        packet_verified = False
        status = "TIMEOUT_REPAIRED_PREFIX_NO_PACKET"

    stage_receipt = _write_stage_receipt(
        output_dir,
        lock_sha256=lock["sha256"],
        status=status,
        timed_out=timed_out,
        child_exit_code=child_exit_code,
        parent_wall_seconds=time.perf_counter() - started,
        packet_verified=packet_verified,
        packet_receipt_sha256=worker["packet_receipt_sha256"] if worker else None,
    )
    names = set(path.name for path in output_dir.iterdir())
    expected = SUCCESS_TOP_LEVEL if packet_verified else ALWAYS_FILES
    if names != expected:
        raise frozen.IdentityContractError("repaired-prefix top-level output set mismatch")
    if not stage_receipt["heartbeat_lines"]:
        raise frozen.IdentityContractError("repaired-prefix produced no flushed heartbeat")
    return {"worker": worker, **stage_receipt}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--verify-only", action="store_true")
    modes.add_argument("--run-prefix", action="store_true")
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
        v1_bindings = v1.verify_execution_bindings(require_committed=False)
        cache_v4.verify_lock()
        print(json.dumps({
            "status": "PASS_REPAIRED_PREFIX_VERIFY_ONLY",
            "authority": "ENGINEERING_REPAIRED_50K_IDENTITY_ONLY",
            "lock_sha256": lock["sha256"],
            "verified_binding_names": sorted(v1_bindings),
        }, indent=2, sort_keys=True))
        return 0
    if args.output_dir is None:
        raise SystemExit("prefix execution requires --output-dir")
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
