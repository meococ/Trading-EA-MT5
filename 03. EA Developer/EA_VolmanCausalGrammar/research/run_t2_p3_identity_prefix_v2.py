"""Bounded identity-path prefix probe for frozen T2/P3.

Unlike the earlier grammar-only timing receipt, this probe executes the same
v1 loaders, T2/ECRS/SCC identity emitters, generic exact-key comparisons, and
atomic JSON/JSONL serialization path.  Its prefix comparisons are engineering
diagnostics only and cannot stand in for the frozen full-ledger D7/D8 gate.
It never reads trades, excursions, PnL, returns, or economic outcomes.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Mapping

import run_t2_p3_dedup as v1
from t2_dedup_mirrors import (
    ECRS_IDENTITY_FIELDS,
    NORMALIZED_OVERLAP_FIELDS,
    IdentityContractError,
    compare_identities,
    emit_ecrs_v1_identities,
    emit_scc_challenger_identities,
    emit_scc_control_identities,
    emit_t2_pbp_like_identities,
    reject_outcome_fields,
    sha256_file,
)
from t2_grammar_reference import emit_t2_d7_structural_identities


REPO_ROOT = v1.REPO_ROOT
LOCK_PATH = (
    REPO_ROOT
    / "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P3_IDENTITY_PREFIX_LOCK_V2.json"
)
LOCK_SCHEMA = "t2_p3_identity_prefix_lock.v2"
RESULT_SCHEMA = "t2_p3_identity_prefix_result.v2"
EVIDENCE_ROOT = (
    REPO_ROOT / "03. EA Developer/EA_VolmanCausalGrammar/research/evidence"
).resolve()
EXPECTED_FILES = frozenset(
    {
        "t2_structural_prefix.jsonl",
        "t2_reject_prefix.jsonl",
        "t2_pbp_audit_prefix.jsonl",
        "ecrs_v1_prefix.jsonl",
        "t2_pbp_identity_prefix.jsonl",
        "scc_control_full_reference.jsonl",
        "scc_challenger_full_reference.jsonl",
        "prefix_result.json",
        "prefix_receipt.json",
    }
)
WORKER_MARKER = "T2_P3_IDENTITY_PREFIX_WORKER_V2="


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _exact_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if set(value) != expected:
        raise IdentityContractError(f"{name} requires exact keys")


def verify_prefix_lock(path: Path = LOCK_PATH) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    _exact_keys(
        document,
        {
            "schema_version",
            "campaign",
            "generation",
            "phase",
            "status",
            "authority",
            "frozen_at_utc",
            "owner_scope",
            "probe",
            "bindings",
            "prohibitions",
        },
        "prefix lock",
    )
    if (
        document["schema_version"] != LOCK_SCHEMA
        or document["campaign"] != "PRO_TRADER_REPLACEMENT"
        or document["generation"] != "T2"
        or document["phase"] != "P3_OUTCOME_BLIND_DEDUP"
        or document["status"] != "FROZEN_PRE_IDENTITY_PREFIX_PACKET"
        or document["authority"] != "ENGINEERING_PREFIX_IDENTITY_ONLY_NO_FULL_GATE_NO_ECONOMICS"
        or document["owner_scope"] != "XAU_FOREX_ONLY_BTC_NOT_GATING"
    ):
        raise IdentityContractError("prefix lock authority/scope mismatch")
    frozen = datetime.fromisoformat(str(document["frozen_at_utc"]).replace("Z", "+00:00"))
    if frozen.tzinfo is None or frozen.astimezone(timezone.utc) > datetime.now(timezone.utc):
        raise IdentityContractError("prefix lock timestamp is invalid")

    probe = document["probe"]
    if not isinstance(probe, dict):
        raise IdentityContractError("prefix probe must be an object")
    _exact_keys(
        probe,
        {
            "scope",
            "prefix_bars",
            "source_rows",
            "max_wall_seconds",
            "output_directory",
            "expected_command",
            "expected_output_files",
        },
        "prefix probe",
    )
    if (
        probe["scope"] != "EURUSD_M5_FIRST_50000_ENGINEERING_PREFIX"
        or probe["prefix_bars"] != 50000
        or probe["source_rows"] != v1.BOUND_D7_STAGE0_RECORD_COUNT
        or probe["max_wall_seconds"] != 300
        or probe["output_directory"]
        != "03. EA Developer/EA_VolmanCausalGrammar/research/evidence/T2_P3_IDENTITY_PREFIX_V2_001"
        or probe["expected_command"]
        != 'python "03. EA Developer/EA_VolmanCausalGrammar/research/run_t2_p3_identity_prefix_v2.py" --run-prefix --output-dir "03. EA Developer/EA_VolmanCausalGrammar/research/evidence/T2_P3_IDENTITY_PREFIX_V2_001"'
        or set(probe["expected_output_files"]) != EXPECTED_FILES
        or len(probe["expected_output_files"]) != len(EXPECTED_FILES)
    ):
        raise IdentityContractError("prefix probe contract mismatch")

    bindings = document["bindings"]
    if not isinstance(bindings, dict) or not bindings:
        raise IdentityContractError("prefix lock requires bindings")
    verified: dict[str, str] = {}
    for name, binding in bindings.items():
        if not isinstance(binding, dict):
            raise IdentityContractError(f"binding schema mismatch: {name}")
        _exact_keys(binding, {"path", "sha256", "role"}, f"binding {name}")
        relative = binding["path"]
        expected = binding["sha256"]
        if (
            not isinstance(relative, str)
            or not isinstance(expected, str)
            or re.fullmatch(r"[0-9A-F]{64}", expected) is None
            or not isinstance(binding["role"], str)
            or not binding["role"]
        ):
            raise IdentityContractError(f"invalid binding: {name}")
        candidate = (REPO_ROOT / relative).resolve()
        try:
            candidate.relative_to(REPO_ROOT.resolve())
        except ValueError as exc:
            raise IdentityContractError(f"binding escapes repository: {name}") from exc
        actual = sha256_file(candidate)
        if actual != expected:
            raise IdentityContractError(f"binding SHA mismatch: {name}")
        verified[name] = actual

    required_prohibitions = {
        "NO_TRADES_EXCURSIONS_RETURNS_PNL_OR_ECONOMICS",
        "NO_FULL_LEDGER_D7_D8_GATE_AUTHORITY",
        "NO_PARAMETER_THRESHOLD_SCHEDULE_EVENT_KEY_OR_COMPARISON_CHANGE",
        "NO_EA_BUILD_COMPILE_MT5_BACKTEST_PAPER_OR_LIVE",
        "NO_GIT_DEPENDENCY",
        "NO_SECOND_PREFIX_OR_OVERWRITE",
    }
    if not isinstance(document["prohibitions"], list) or set(document["prohibitions"]) != required_prohibitions:
        raise IdentityContractError("prefix lock prohibitions mismatch")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "document": document,
        "verified_bindings": verified,
    }


def _validate_output_dir(path: Path, expected_relative: str) -> Path:
    resolved = path.resolve()
    expected = (REPO_ROOT / expected_relative).resolve()
    if resolved != expected:
        raise IdentityContractError("prefix output directory differs from lock")
    try:
        resolved.relative_to(EVIDENCE_ROOT)
    except ValueError as exc:
        raise IdentityContractError("prefix output escapes evidence root") from exc
    if resolved.exists():
        raise IdentityContractError("prefix output directory must be fresh and absent")
    return resolved


def _elapsed(stage_times: dict[str, float], name: str, started: float) -> None:
    stage_times[name] = time.perf_counter() - started


def _write_prefix_packet(
    output_dir: Path,
    result: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    *,
    stage_times: Mapping[str, float],
    started_total: float,
) -> dict[str, Any]:
    if output_dir.exists():
        raise IdentityContractError("prefix packet refuses existing output directory")
    output_dir.mkdir(parents=True, exist_ok=False)
    file_map = {
        "t2_events": "t2_structural_prefix.jsonl",
        "t2_rejects": "t2_reject_prefix.jsonl",
        "t2_pbp_audits": "t2_pbp_audit_prefix.jsonl",
        "ecrs_events": "ecrs_v1_prefix.jsonl",
        "pbp_events": "t2_pbp_identity_prefix.jsonl",
        "scc_control": "scc_control_full_reference.jsonl",
        "scc_challenger": "scc_challenger_full_reference.jsonl",
    }
    started_write = time.perf_counter()
    written: dict[str, dict[str, Any]] = {}
    for key, filename in file_map.items():
        path = output_dir / filename
        v1._atomic_jsonl(path, artifacts[key])
        written[key] = {
            "path": str(path),
            "sha256": sha256_file(path),
            "records": len(artifacts[key]),
        }
    public_result = dict(result)
    public_result["written_artifacts"] = written
    reject_outcome_fields(public_result)
    result_path = output_dir / "prefix_result.json"
    v1._atomic_json(result_path, public_result)
    packet_write_wall_seconds_excluding_receipt = time.perf_counter() - started_write
    receipt = {
        "schema_version": "t2_p3_identity_prefix_receipt.v2",
        "authority": "ENGINEERING_PREFIX_IDENTITY_ONLY_NO_FULL_GATE_NO_ECONOMICS",
        "result_path": str(result_path),
        "result_sha256": sha256_file(result_path),
        "artifacts": written,
        "expected_files": sorted(EXPECTED_FILES),
        "stage_wall_seconds_before_write": dict(stage_times),
        "packet_write_wall_seconds_excluding_receipt": packet_write_wall_seconds_excluding_receipt,
        "total_wall_seconds_before_receipt": time.perf_counter() - started_total,
    }
    v1._atomic_json(output_dir / "prefix_receipt.json", receipt)
    if set(path.name for path in output_dir.iterdir()) != EXPECTED_FILES:
        raise IdentityContractError("prefix packet output set mismatch")
    return receipt


def run_prefix_packet(output_dir: Path) -> dict[str, Any]:
    lock = verify_prefix_lock()
    probe = lock["document"]["probe"]
    output_dir = _validate_output_dir(output_dir, probe["output_directory"])
    verified = v1.verify_execution_bindings(require_committed=False)
    original_verify = v1.verify_execution_bindings
    v1.verify_execution_bindings = lambda: dict(verified)
    stage_times: dict[str, float] = {}
    started_total = time.perf_counter()
    try:
        started = time.perf_counter()
        schedule = v1.load_d7_schedule()
        structural, ecrs_bars, scc_path, metadata = v1.load_bound_stage0_bars()
        calendar = v1.load_bound_news_calendar()
        _elapsed(stage_times, "load_bound_inputs", started)
        if metadata["rows"] != v1.BOUND_D7_STAGE0_RECORD_COUNT:
            raise IdentityContractError("prefix packet source row mismatch")

        started = time.perf_counter()
        control_records = v1._load_scc_records(
            v1.SCC_CONTROL_PATH,
            v1.SCC_CONTROL_SHA256,
            challenger=False,
        )
        challenger_records = v1._load_scc_records(
            v1.SCC_CHALLENGER_PATH,
            v1.SCC_CHALLENGER_SHA256,
            challenger=True,
        )
        scc_control = emit_scc_control_identities(control_records, source_bars=scc_path)
        scc_challenger = emit_scc_challenger_identities(challenger_records, source_bars=scc_path)
        v1.assert_scc_challenger_strict_subset(scc_control, scc_challenger)
        _elapsed(stage_times, "scc_reference_replay", started)

        prefix_bars = int(probe["prefix_bars"])
        started = time.perf_counter()
        t2_result = emit_t2_d7_structural_identities(
            structural[:prefix_bars],
            symbol="EURUSD",
            tick=v1.EURUSD_TICK_SIZE,
            schedule=schedule,
        )
        t2_events = list(t2_result.events)
        _elapsed(stage_times, "t2_structural_prefix", started)

        started = time.perf_counter()
        ecrs_events = emit_ecrs_v1_identities(
            ecrs_bars[:prefix_bars],
            symbol="EURUSD",
            news_calendar=calendar,
        )
        _elapsed(stage_times, "ecrs_prefix", started)

        started = time.perf_counter()
        d7_prefix = compare_identities(
            t2_events,
            ecrs_events,
            key_fields=ECRS_IDENTITY_FIELDS,
        )
        pbp_events = emit_t2_pbp_like_identities(t2_result.pbp_audits)
        pbp_break = [row for row in pbp_events if row["subset"] == "PBP_BREAK_WINDOW"]
        pbp_contact = [row for row in pbp_events if row["subset"] == "PBP_TOMBSTONE_CONTACT"]
        d8_break_prefix = compare_identities(
            pbp_break,
            scc_control,
            key_fields=NORMALIZED_OVERLAP_FIELDS,
        )
        d8_contact_prefix = compare_identities(
            pbp_contact,
            scc_challenger,
            key_fields=NORMALIZED_OVERLAP_FIELDS,
        )
        _elapsed(stage_times, "prefix_comparisons", started)

        artifacts = {
            "t2_events": t2_events,
            "t2_rejects": [asdict(value) for value in t2_result.rejects],
            "t2_pbp_audits": [asdict(value) for value in t2_result.pbp_audits],
            "ecrs_events": ecrs_events,
            "pbp_events": pbp_events,
            "scc_control": scc_control,
            "scc_challenger": scc_challenger,
        }
        result = {
            "schema_version": RESULT_SCHEMA,
            "authority": "ENGINEERING_PREFIX_IDENTITY_ONLY_NO_FULL_GATE_NO_ECONOMICS",
            "created_at_utc": _utc_now(),
            "prefix_scope": probe["scope"],
            "prefix_bars": prefix_bars,
            "bound_source_rows": metadata["rows"],
            "bound_source_sha256": v1.STAGE0_BARS_SHA256,
            "prefix_comparisons_are_fatal_gate_authority": False,
            "d7_prefix_diagnostic": asdict(d7_prefix),
            "d8_break_prefix_diagnostic": asdict(d8_break_prefix),
            "d8_contact_prefix_diagnostic": asdict(d8_contact_prefix),
            "t2_prefix_stats": t2_result.stats,
            "stage_wall_seconds_before_write": stage_times,
            "source_field_contract": "IDENTITY_ONLY_NO_TRADE_RESULT_FIELDS",
            "economic_claim_authorized": False,
            "ea_build_or_mt5_authorized": False,
            "full_replay_authorized_by_this_packet": False,
            "lock_sha256": lock["sha256"],
        }
        reject_outcome_fields(result)
        started = time.perf_counter()
        receipt = _write_prefix_packet(
            output_dir,
            result,
            artifacts,
            stage_times=stage_times,
            started_total=started_total,
        )
        _elapsed(stage_times, "serialization", started)
        receipt["total_wall_seconds"] = time.perf_counter() - started_total
        receipt["stage_wall_seconds"] = stage_times
        return receipt
    finally:
        v1.verify_execution_bindings = original_verify


def _verify_packet(output_dir: Path) -> dict[str, Any]:
    names = set(path.name for path in output_dir.iterdir())
    if names != EXPECTED_FILES:
        raise IdentityContractError("prefix packet does not have the exact output set")
    receipt_path = output_dir / "prefix_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    result_path = output_dir / "prefix_result.json"
    if receipt["result_sha256"] != sha256_file(result_path):
        raise IdentityContractError("prefix result SHA mismatch")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    reject_outcome_fields(result)
    if (
        result["schema_version"] != RESULT_SCHEMA
        or result["authority"] != "ENGINEERING_PREFIX_IDENTITY_ONLY_NO_FULL_GATE_NO_ECONOMICS"
        or result["prefix_comparisons_are_fatal_gate_authority"] is not False
        or result["full_replay_authorized_by_this_packet"] is not False
        or result["source_field_contract"] != "IDENTITY_ONLY_NO_TRADE_RESULT_FIELDS"
        or result["economic_claim_authorized"] is not False
        or result["ea_build_or_mt5_authorized"] is not False
    ):
        raise IdentityContractError("prefix result authority mismatch")
    for entry in receipt["artifacts"].values():
        path = Path(entry["path"]).resolve()
        if sha256_file(path) != entry["sha256"]:
            raise IdentityContractError("prefix artifact SHA mismatch")
    return {
        "receipt_path": str(receipt_path),
        "receipt_sha256": sha256_file(receipt_path),
        "result_path": str(result_path),
        "result_sha256": sha256_file(result_path),
        "output_files": sorted(names),
    }


def run_bounded_prefix(output_dir: Path) -> dict[str, Any]:
    lock = verify_prefix_lock()
    probe = lock["document"]["probe"]
    _validate_output_dir(output_dir, probe["output_directory"])
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        "--output-dir",
        str(output_dir),
    ]
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
    except subprocess.TimeoutExpired as exc:
        raise IdentityContractError("identity-prefix worker exceeded frozen 300-second wall") from exc
    if completed.returncode != 0:
        raise IdentityContractError(
            f"identity-prefix worker failed rc={completed.returncode}: {completed.stderr[-2000:]}"
        )
    marker_lines = [line for line in completed.stdout.splitlines() if line.startswith(WORKER_MARKER)]
    if len(marker_lines) != 1:
        raise IdentityContractError("identity-prefix worker receipt marker mismatch")
    worker_receipt = json.loads(marker_lines[0][len(WORKER_MARKER) :])
    verified = _verify_packet(output_dir)
    return {
        "status": "PASS_IDENTITY_PREFIX_PACKET_ENGINEERING_ONLY",
        "authority": "NO_FULL_GATE_NO_ECONOMICS",
        "worker_total_wall_seconds": worker_receipt["total_wall_seconds"],
        "worker_stage_wall_seconds": worker_receipt["stage_wall_seconds"],
        **verified,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--verify-only", action="store_true")
    modes.add_argument("--run-prefix", action="store_true")
    modes.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.verify_only:
        if args.output_dir is not None:
            raise SystemExit("--verify-only takes no output directory")
        lock = verify_prefix_lock()
        bindings = v1.verify_execution_bindings(require_committed=False)
        print(
            json.dumps(
                {
                    "status": "PASS_VERIFY_ONLY",
                    "lock_sha256": lock["sha256"],
                    "verified_binding_names": sorted(bindings),
                    "source_field_contract": "IDENTITY_ONLY_NO_TRADE_RESULT_FIELDS",
                    "economic_claim_authorized": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.output_dir is None:
        raise SystemExit("prefix mode requires --output-dir")
    if args.worker:
        receipt = run_prefix_packet(args.output_dir.resolve())
        print(WORKER_MARKER + json.dumps(receipt, sort_keys=True))
        return 0
    result = run_bounded_prefix(args.output_dir.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
