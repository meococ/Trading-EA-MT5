"""Timing-only successor for the frozen T2/P3 identity replay.

This wrapper does not change the v1 producer, mirrors, thresholds, schedules,
event keys, or comparison laws.  It exists only to localize the v1 full-replay
timeout with one bounded prefix timing probe.  It never emits identity rows,
identity counts, D7/D8 scores, trades, excursions, PnL, or economics.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping

from run_t2_p3_dedup import (
    BOUND_D7_STAGE0_RECORD_COUNT,
    REPO_ROOT,
    STAGE0_BARS_PATH,
    STAGE0_BARS_SHA256,
    load_bound_stage0_bars,
    load_d7_schedule,
    verify_execution_bindings,
)
from t2_dedup_mirrors import IdentityContractError, sha256_file
from t2_grammar_reference import emit_t2_d7_structural_identities


LOCK_PATH = (
    REPO_ROOT
    / "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P3_TIMING_EXECUTION_LOCK_V2.json"
)
LOCK_SCHEMA = "t2_p3_timing_execution_lock.v2"
RECEIPT_SCHEMA = "t2_p3_timing_receipt.v2"
ALLOWED_OUTPUT_NAME = "timing_receipt.json"
EVIDENCE_ROOT = (
    REPO_ROOT / "03. EA Developer/EA_VolmanCausalGrammar/research/evidence"
).resolve()
WORKER_MARKER = "T2_P3_TIMING_WORKER_V2="
WORKER_FIELDS = frozenset(
    {
        "source_rows",
        "prefix_bars",
        "load_wall_seconds",
        "load_cpu_seconds",
        "grammar_wall_seconds",
        "grammar_cpu_seconds",
        "total_wall_seconds",
        "total_cpu_seconds",
        "rss_start_bytes",
        "rss_after_load_bytes",
        "rss_after_grammar_bytes",
    }
)
FORBIDDEN_WORKER_KEY_TOKENS = (
    "identity",
    "audit",
    "reject",
    "score",
    "trade",
    "excursion",
    "pnl",
    "profit",
    "return",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _rss_bytes() -> int | None:
    try:
        import psutil  # type: ignore[import-not-found]

        return int(psutil.Process(os.getpid()).memory_info().rss)
    except (ImportError, OSError, ValueError):
        return None


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if set(value) != expected:
        raise IdentityContractError(f"{name} requires exact keys")


def _parse_utc(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise IdentityContractError(f"{name} must be a UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IdentityContractError(f"{name} is invalid") from exc
    if parsed.tzinfo is None:
        raise IdentityContractError(f"{name} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def verify_timing_lock(path: Path = LOCK_PATH) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    _require_exact_keys(
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
            "timing_probe",
            "bindings",
            "prohibitions",
        },
        "timing lock",
    )
    if (
        document["schema_version"] != LOCK_SCHEMA
        or document["campaign"] != "PRO_TRADER_REPLACEMENT"
        or document["generation"] != "T2"
        or document["phase"] != "P3_OUTCOME_BLIND_DEDUP"
        or document["status"] != "FROZEN_PRE_TIMING_ONLY_PREFIX_SOURCE_READ"
        or document["authority"] != "ENGINEERING_TIMING_ONLY_NO_IDENTITY_OUTPUT_NO_ECONOMICS"
        or document["owner_scope"] != "XAU_FOREX_ONLY_BTC_NOT_GATING"
    ):
        raise IdentityContractError("timing lock status/authority/scope mismatch")
    frozen_at = _parse_utc(document["frozen_at_utc"], "frozen_at_utc")
    if frozen_at > datetime.now(timezone.utc):
        raise IdentityContractError("timing lock timestamp is in the future")

    probe = document["timing_probe"]
    if not isinstance(probe, dict):
        raise IdentityContractError("timing_probe must be an object")
    _require_exact_keys(
        probe,
        {
            "primary_scope",
            "prefix_bars",
            "max_wall_seconds",
            "min_bars_per_second",
            "max_projected_full_wall_seconds",
            "source_rows",
            "allowed_output_files",
            "expected_command",
        },
        "timing_probe",
    )
    if (
        probe["primary_scope"] != "EURUSD_M5_EXACT_BOUND_PREFIX"
        or type(probe["prefix_bars"]) is not int
        or not 50 <= probe["prefix_bars"] < BOUND_D7_STAGE0_RECORD_COUNT
        or type(probe["max_wall_seconds"]) not in {int, float}
        or probe["max_wall_seconds"] <= 0
        or type(probe["min_bars_per_second"]) not in {int, float}
        or probe["min_bars_per_second"] <= 0
        or type(probe["max_projected_full_wall_seconds"]) not in {int, float}
        or probe["max_projected_full_wall_seconds"] <= 0
        or probe["source_rows"] != BOUND_D7_STAGE0_RECORD_COUNT
        or probe["allowed_output_files"] != [ALLOWED_OUTPUT_NAME]
        or probe["expected_command"]
        != 'python "03. EA Developer/EA_VolmanCausalGrammar/research/run_t2_p3_dedup_v2.py" --timing-only --prefix-bars 50000 --output-dir "03. EA Developer/EA_VolmanCausalGrammar/research/evidence/T2_P3_TIMING_V2_001"'
    ):
        raise IdentityContractError("timing_probe contract mismatch")

    bindings = document["bindings"]
    if not isinstance(bindings, dict) or not bindings:
        raise IdentityContractError("timing lock requires nonempty bindings")
    verified: dict[str, str] = {}
    for name, binding in bindings.items():
        if not isinstance(name, str) or not isinstance(binding, dict):
            raise IdentityContractError("timing lock binding schema mismatch")
        _require_exact_keys(binding, {"path", "sha256", "role"}, f"binding {name}")
        relative = binding["path"]
        expected = binding["sha256"]
        if (
            not isinstance(relative, str)
            or not relative
            or not isinstance(expected, str)
            or re.fullmatch(r"[0-9A-F]{64}", expected) is None
            or not isinstance(binding["role"], str)
            or not binding["role"]
        ):
            raise IdentityContractError(f"timing lock binding is invalid: {name}")
        candidate = (REPO_ROOT / relative).resolve()
        try:
            candidate.relative_to(REPO_ROOT.resolve())
        except ValueError as exc:
            raise IdentityContractError(f"timing lock binding escapes repository: {name}") from exc
        verified[name] = sha256_file(candidate)
        if verified[name] != expected:
            raise IdentityContractError(f"timing lock SHA mismatch: {name}")

    prohibitions = document["prohibitions"]
    required = {
        "NO_MARKET_OUTCOMES_TRADES_EXCURSIONS_OR_PNL",
        "NO_IDENTITY_AUDIT_REJECT_ROWS_OR_COUNTS",
        "NO_D7_D8_SCORE_OR_RESULT_PACKET",
        "NO_THRESHOLD_SCHEDULE_EVENT_KEY_OR_COMPARISON_CHANGE",
        "NO_EA_BUILD_COMPILE_BACKTEST_OR_ECONOMICS",
        "NO_GIT_DEPENDENCY",
        "NO_OVERWRITE",
    }
    if not isinstance(prohibitions, list) or set(prohibitions) != required:
        raise IdentityContractError("timing lock prohibitions mismatch")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "document": document,
        "verified_bindings": verified,
    }


def _validate_worker_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require_exact_keys(payload, set(WORKER_FIELDS), "timing worker payload")
    for key in payload:
        lower = key.lower()
        if any(token in lower for token in FORBIDDEN_WORKER_KEY_TOKENS):
            raise IdentityContractError(f"timing worker leaked forbidden key: {key}")
    if payload["source_rows"] != BOUND_D7_STAGE0_RECORD_COUNT:
        raise IdentityContractError("timing worker source row mismatch")
    for key in (
        "load_wall_seconds",
        "load_cpu_seconds",
        "grammar_wall_seconds",
        "grammar_cpu_seconds",
        "total_wall_seconds",
        "total_cpu_seconds",
    ):
        if type(payload[key]) not in {int, float} or payload[key] < 0:
            raise IdentityContractError(f"timing worker invalid duration: {key}")
    for key in ("rss_start_bytes", "rss_after_load_bytes", "rss_after_grammar_bytes"):
        if payload[key] is not None and (type(payload[key]) is not int or payload[key] < 0):
            raise IdentityContractError(f"timing worker invalid RSS: {key}")
    if type(payload["prefix_bars"]) is not int or payload["prefix_bars"] <= 0:
        raise IdentityContractError("timing worker invalid prefix")
    return dict(payload)


def _timing_worker(prefix_bars: int) -> dict[str, Any]:
    total_wall_start = time.perf_counter()
    total_cpu_start = time.process_time()
    rss_start = _rss_bytes()

    load_wall_start = time.perf_counter()
    load_cpu_start = time.process_time()
    structural, ecrs, scc_path, metadata = load_bound_stage0_bars()
    load_wall = time.perf_counter() - load_wall_start
    load_cpu = time.process_time() - load_cpu_start
    rss_after_load = _rss_bytes()
    if metadata.get("rows") != BOUND_D7_STAGE0_RECORD_COUNT:
        raise IdentityContractError("timing worker loaded source row mismatch")
    if len(structural) != BOUND_D7_STAGE0_RECORD_COUNT or prefix_bars > len(structural):
        raise IdentityContractError("timing worker prefix/source mismatch")

    schedule = load_d7_schedule()
    grammar_wall_start = time.perf_counter()
    grammar_cpu_start = time.process_time()
    private_result = emit_t2_d7_structural_identities(
        structural[:prefix_bars],
        symbol="EURUSD",
        tick=0.00001,
        schedule=schedule,
    )
    grammar_wall = time.perf_counter() - grammar_wall_start
    grammar_cpu = time.process_time() - grammar_cpu_start
    rss_after_grammar = _rss_bytes()
    del private_result, structural, ecrs, scc_path, metadata

    return _validate_worker_payload(
        {
            "source_rows": BOUND_D7_STAGE0_RECORD_COUNT,
            "prefix_bars": prefix_bars,
            "load_wall_seconds": load_wall,
            "load_cpu_seconds": load_cpu,
            "grammar_wall_seconds": grammar_wall,
            "grammar_cpu_seconds": grammar_cpu,
            "total_wall_seconds": time.perf_counter() - total_wall_start,
            "total_cpu_seconds": time.process_time() - total_cpu_start,
            "rss_start_bytes": rss_start,
            "rss_after_load_bytes": rss_after_load,
            "rss_after_grammar_bytes": rss_after_grammar,
        }
    )


def _evaluate_timing(payload: Mapping[str, Any], probe: Mapping[str, Any]) -> dict[str, Any]:
    grammar_wall = float(payload["grammar_wall_seconds"])
    prefix_bars = int(payload["prefix_bars"])
    bars_per_second = float("inf") if grammar_wall == 0 else prefix_bars / grammar_wall
    projected = float(payload["load_wall_seconds"])
    if bars_per_second != float("inf"):
        projected += BOUND_D7_STAGE0_RECORD_COUNT / bars_per_second
    gates = {
        "worker_wall_within_limit": float(payload["total_wall_seconds"])
        <= float(probe["max_wall_seconds"]),
        "bars_per_second_at_least_minimum": bars_per_second
        >= float(probe["min_bars_per_second"]),
        "projected_full_wall_within_limit": projected
        <= float(probe["max_projected_full_wall_seconds"]),
    }
    return {
        "bars_per_second": bars_per_second,
        "projected_full_wall_seconds": projected,
        "gates": gates,
        "pass": all(gates.values()),
    }


def _validate_output_dir(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(EVIDENCE_ROOT)
    except ValueError as exc:
        raise IdentityContractError("timing output directory must stay under package evidence root") from exc
    if resolved.exists():
        raise IdentityContractError("timing output directory must be fresh and absent")
    return resolved


def _atomic_write_receipt(output_dir: Path, receipt: Mapping[str, Any]) -> Path:
    output_dir = _validate_output_dir(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    final_path = output_dir / ALLOWED_OUTPUT_NAME
    fd, temp_name = tempfile.mkstemp(prefix=".timing_receipt.", suffix=".tmp", dir=output_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(receipt, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, final_path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    if sorted(path.name for path in output_dir.iterdir()) != [ALLOWED_OUTPUT_NAME]:
        raise IdentityContractError("timing output surface contains an unauthorized file")
    return final_path


def _base_receipt(lock: Mapping[str, Any], prefix_bars: int) -> dict[str, Any]:
    return {
        "schema_version": RECEIPT_SCHEMA,
        "recorded_at_utc": _utc_now(),
        "authority": "ENGINEERING_TIMING_ONLY_NO_IDENTITY_OUTPUT_NO_ECONOMICS",
        "scope": "EURUSD_M5_EXACT_BOUND_PREFIX",
        "prefix_bars": prefix_bars,
        "source_rows": BOUND_D7_STAGE0_RECORD_COUNT,
        "source_sha256": STAGE0_BARS_SHA256,
        "source_path": str(STAGE0_BARS_PATH),
        "timing_lock_path": str(LOCK_PATH),
        "timing_lock_sha256": lock["sha256"],
        "outputs_allowed": [ALLOWED_OUTPUT_NAME],
        "market_outcomes_read": False,
        "economics_executed": False,
        "ea_build_or_mt5_authorized": False,
    }


def run_timing_probe(prefix_bars: int, output_dir: Path) -> dict[str, Any]:
    lock = verify_timing_lock()
    probe = lock["document"]["timing_probe"]
    if prefix_bars != probe["prefix_bars"]:
        raise IdentityContractError("prefix bars differ from the frozen timing lock")
    verify_execution_bindings(require_committed=False)

    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--timing-worker",
        "--prefix-bars",
        str(prefix_bars),
    ]
    receipt = _base_receipt(lock, prefix_bars)
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
    except subprocess.TimeoutExpired:
        receipt.update(
            {
                "status": "FAIL_TIMING_WORKER_MAX_WALL_TIMEOUT",
                "timing": None,
                "gates": {
                    "worker_wall_within_limit": False,
                    "bars_per_second_at_least_minimum": False,
                    "projected_full_wall_within_limit": False,
                },
                "next_action": "Localize the timed-out stage without changing market semantics.",
            }
        )
        receipt_path = _atomic_write_receipt(output_dir, receipt)
        receipt["receipt_path"] = str(receipt_path)
        receipt["receipt_sha256"] = sha256_file(receipt_path)
        return receipt

    if completed.returncode != 0:
        receipt.update(
            {
                "status": "FAIL_TIMING_WORKER_ERROR",
                "timing": None,
                "gates": None,
                "worker_returncode": completed.returncode,
                "worker_stderr_tail": completed.stderr[-2000:],
                "next_action": "Diagnose engineering failure; do not open identity or economic output.",
            }
        )
    else:
        lines = [line for line in completed.stdout.splitlines() if line.startswith(WORKER_MARKER)]
        if len(lines) != 1:
            raise IdentityContractError("timing worker did not emit exactly one private timing payload")
        payload = _validate_worker_payload(json.loads(lines[0][len(WORKER_MARKER) :]))
        evaluation = _evaluate_timing(payload, probe)
        receipt.update(
            {
                "status": (
                    "PASS_TIMING_ONLY_PREFIX_CADENCE"
                    if evaluation["pass"]
                    else "FAIL_TIMING_ONLY_PREFIX_CADENCE"
                ),
                "timing": payload,
                "derived": {
                    "bars_per_second": evaluation["bars_per_second"],
                    "projected_full_wall_seconds": evaluation["projected_full_wall_seconds"],
                },
                "gates": evaluation["gates"],
                "next_action": (
                    "Authorize one separately frozen full identity replay only after review."
                    if evaluation["pass"]
                    else "Profile the slow stage and prove a semantics-preserving repair before any full replay."
                ),
            }
        )

    receipt_path = _atomic_write_receipt(output_dir, receipt)
    receipt["receipt_path"] = str(receipt_path)
    receipt["receipt_sha256"] = sha256_file(receipt_path)
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--verify-only", action="store_true")
    modes.add_argument("--timing-only", action="store_true")
    modes.add_argument("--timing-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--prefix-bars", type=int)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.verify_only:
        if args.prefix_bars is not None or args.output_dir is not None:
            raise SystemExit("--verify-only takes no prefix or output directory")
        lock = verify_timing_lock()
        bindings = verify_execution_bindings(require_committed=False)
        print(
            json.dumps(
                {
                    "status": "PASS_VERIFY_ONLY",
                    "timing_lock_sha256": lock["sha256"],
                    "verified_binding_names": sorted(bindings),
                    "market_outcomes_read": False,
                    "economics_executed": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.timing_worker:
        if args.prefix_bars is None or args.output_dir is not None:
            raise SystemExit("timing worker requires only --prefix-bars")
        print(WORKER_MARKER + json.dumps(_timing_worker(args.prefix_bars), sort_keys=True))
        return 0
    if args.prefix_bars is None or args.output_dir is None:
        raise SystemExit("--timing-only requires --prefix-bars and --output-dir")
    receipt = run_timing_probe(args.prefix_bars, args.output_dir)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
