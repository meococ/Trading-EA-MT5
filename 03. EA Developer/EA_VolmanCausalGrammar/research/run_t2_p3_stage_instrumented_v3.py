"""One-shot stage instrumentation for the frozen T2/P3 identity prefix.

This revision exists only to localize the v2 300-second engineering timeout.
It preserves every frozen loader, emitter, comparison and serialization call.
The durable output is restricted to flushed stage heartbeats and one parent
receipt; identity rows and comparison metrics are never published.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Any, Iterable, Iterator, Mapping, Sequence, TypeVar, overload

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


T = TypeVar("T")
REPO_ROOT = v1.REPO_ROOT.resolve()
LOCK_PATH = REPO_ROOT / "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P3_STAGE_INSTRUMENTATION_LOCK_V3.json"
LOCK_SCHEMA = "t2_p3_stage_instrumentation_lock.v3"
EVIDENCE_ROOT = (REPO_ROOT / "03. EA Developer/EA_VolmanCausalGrammar/research/evidence").resolve()
EXPECTED_FILES = frozenset({"stage_heartbeat.jsonl", "stage_receipt.json"})
WORKER_MARKER = "T2_P3_STAGE_INSTRUMENTATION_WORKER_V3="
PULSE_INTERVAL_SECONDS = 2.0
PROGRESS_STRIDE = 1000


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class _ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def _rss_bytes() -> int:
    counters = _ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    get_current_process = ctypes.windll.kernel32.GetCurrentProcess
    get_current_process.argtypes = []
    get_current_process.restype = wintypes.HANDLE
    get_process_memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
    get_process_memory_info.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_ProcessMemoryCounters),
        wintypes.DWORD,
    ]
    get_process_memory_info.restype = wintypes.BOOL
    handle = get_current_process()
    ok = get_process_memory_info(
        handle,
        ctypes.byref(counters),
        counters.cb,
    )
    if not ok:
        raise OSError("GetProcessMemoryInfo failed")
    return int(counters.WorkingSetSize)


def _append_jsonl_fsync(path: Path, value: Mapping[str, Any]) -> None:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


class HeartbeatRecorder:
    """Flush stage state while frozen functions run without editing them."""

    def __init__(self, path: Path, *, interval_seconds: float = PULSE_INTERVAL_SECONDS) -> None:
        self.path = path
        self.interval_seconds = interval_seconds
        self.started_wall = time.perf_counter()
        self.started_cpu = time.process_time()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._stage = "worker_start"
        self._progress_index: int | None = None
        self._progress_total: int | None = None
        self._progress_unit = "none"
        self._pulse_sequence = 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._emit("worker_start")
        self._thread = threading.Thread(target=self._pulse_loop, name="t2-p3-v3-heartbeat", daemon=True)
        self._thread.start()

    def _snapshot(self, pulse_kind: str) -> dict[str, Any]:
        with self._lock:
            self._pulse_sequence += 1
            return {
                "schema_version": "t2_p3_stage_heartbeat.v3",
                "recorded_at_utc": _utc_now(),
                "pulse_kind": pulse_kind,
                "pulse_sequence": self._pulse_sequence,
                "stage": self._stage,
                "progress_unit": self._progress_unit,
                "progress_index": self._progress_index,
                "progress_total": self._progress_total,
                "wall_seconds": time.perf_counter() - self.started_wall,
                "cpu_seconds": time.process_time() - self.started_cpu,
                "rss_bytes": _rss_bytes(),
            }

    def _emit(self, pulse_kind: str) -> None:
        _append_jsonl_fsync(self.path, self._snapshot(pulse_kind))

    def _pulse_loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self._emit("pulse")

    def begin_stage(
        self,
        stage: str,
        *,
        progress_unit: str = "none",
        progress_total: int | None = None,
    ) -> None:
        with self._lock:
            self._stage = stage
            self._progress_unit = progress_unit
            self._progress_index = 0 if progress_total is not None else None
            self._progress_total = progress_total
        self._emit("stage_start")

    def advance(self, index: int) -> None:
        with self._lock:
            if self._progress_index is None or index > self._progress_index:
                self._progress_index = index

    def end_stage(self) -> None:
        self._emit("stage_end")

    def close(self) -> None:
        self._emit("worker_end")
        self._stop.set()
        self._thread.join(timeout=max(1.0, self.interval_seconds * 2.0))


class ObservedSequence(Sequence[T]):
    """Read-only value-preserving sequence that exposes source-index progress."""

    def __init__(self, values: Sequence[T], recorder: HeartbeatRecorder, *, stride: int = PROGRESS_STRIDE) -> None:
        self._values = values
        self._recorder = recorder
        self._stride = stride

    def __len__(self) -> int:
        return len(self._values)

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[T]: ...

    def __getitem__(self, index: int | slice) -> T | Sequence[T]:
        value = self._values[index]
        if isinstance(index, int):
            normalized = index if index >= 0 else len(self._values) + index
            if normalized % self._stride == 0 or normalized + 1 == len(self._values):
                self._recorder.advance(normalized + 1)
        return value

    def __iter__(self) -> Iterator[T]:
        total = len(self._values)
        for index, value in enumerate(self._values, start=1):
            if index % self._stride == 0 or index == total:
                self._recorder.advance(index)
            yield value


def _exact_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if set(value) != expected:
        raise IdentityContractError(f"{name} requires exact keys")


def verify_lock(path: Path = LOCK_PATH) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    _exact_keys(
        document,
        {
            "schema_version", "campaign", "generation", "phase", "status", "authority",
            "frozen_at_utc", "owner_scope", "probe", "bindings", "prohibitions",
        },
        "v3 lock",
    )
    if (
        document["schema_version"] != LOCK_SCHEMA
        or document["campaign"] != "PRO_TRADER_REPLACEMENT"
        or document["generation"] != "T2"
        or document["phase"] != "P3_OUTCOME_BLIND_DEDUP"
        or document["status"] != "FROZEN_PRE_STAGE_INSTRUMENTATION"
        or document["authority"] != "ENGINEERING_STAGE_INSTRUMENTATION_ONLY"
        or document["owner_scope"] != "XAU_FOREX_ONLY_BTC_NOT_GATING"
    ):
        raise IdentityContractError("v3 lock authority/scope mismatch")
    frozen = datetime.fromisoformat(str(document["frozen_at_utc"]).replace("Z", "+00:00"))
    if frozen.tzinfo is None or frozen.astimezone(timezone.utc) > datetime.now(timezone.utc):
        raise IdentityContractError("v3 lock timestamp is invalid")

    probe = document["probe"]
    _exact_keys(
        probe,
        {
            "scope", "prefix_bars", "source_rows", "max_wall_seconds", "pulse_interval_seconds",
            "progress_stride", "output_directory", "ephemeral_directory", "expected_command",
            "expected_output_files",
        },
        "v3 probe",
    )
    if (
        probe["scope"] != "EURUSD_M5_FIRST_50000_STAGE_INSTRUMENTATION"
        or probe["prefix_bars"] != 50000
        or probe["source_rows"] != v1.BOUND_D7_STAGE0_RECORD_COUNT
        or probe["max_wall_seconds"] != 300
        or probe["pulse_interval_seconds"] != PULSE_INTERVAL_SECONDS
        or probe["progress_stride"] != PROGRESS_STRIDE
        or probe["output_directory"] != "03. EA Developer/EA_VolmanCausalGrammar/research/evidence/T2_P3_STAGE_INSTRUMENTATION_V3_001"
        or probe["ephemeral_directory"] != "03. EA Developer/EA_VolmanCausalGrammar/research/evidence/.T2_P3_STAGE_INSTRUMENTATION_V3_001_EPHEMERAL"
        or probe["expected_command"] != 'python "03. EA Developer/EA_VolmanCausalGrammar/research/run_t2_p3_stage_instrumented_v3.py" --run-stage-probe --output-dir "03. EA Developer/EA_VolmanCausalGrammar/research/evidence/T2_P3_STAGE_INSTRUMENTATION_V3_001"'
        or set(probe["expected_output_files"]) != EXPECTED_FILES
        or len(probe["expected_output_files"]) != len(EXPECTED_FILES)
    ):
        raise IdentityContractError("v3 probe contract mismatch")

    verified: dict[str, str] = {}
    if not isinstance(document["bindings"], dict) or not document["bindings"]:
        raise IdentityContractError("v3 lock requires bindings")
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
            raise IdentityContractError(f"invalid binding: {name}")
        candidate = (REPO_ROOT / relative).resolve()
        try:
            candidate.relative_to(REPO_ROOT)
        except ValueError as exc:
            raise IdentityContractError(f"binding escapes repository: {name}") from exc
        actual = sha256_file(candidate)
        if actual != expected:
            raise IdentityContractError(f"binding SHA mismatch: {name}")
        verified[name] = actual

    required = {
        "NO_IDENTITY_AUDIT_REJECT_ROWS_OR_COMPARISON_METRICS_IN_DURABLE_OUTPUT",
        "NO_MARKET_RULE_THRESHOLD_SCHEDULE_SOURCE_EVENT_KEY_OR_COMPARISON_CHANGE",
        "NO_FULL_REPLAY_OR_SECOND_V2_PREFIX",
        "NO_EA_BUILD_COMPILE_MT5_BACKTEST_PAPER_OR_LIVE",
        "NO_GIT_DEPENDENCY",
        "NO_V3_RERUN_OR_OVERWRITE",
    }
    if not isinstance(document["prohibitions"], list) or set(document["prohibitions"]) != required:
        raise IdentityContractError("v3 prohibitions mismatch")
    return {"document": document, "path": str(path), "sha256": sha256_file(path), "verified": verified}


def _resolve_locked_path(relative: str) -> Path:
    value = (REPO_ROOT / relative).resolve()
    try:
        value.relative_to(EVIDENCE_ROOT)
    except ValueError as exc:
        raise IdentityContractError("v3 runtime path escapes evidence root") from exc
    return value


def _prepare_output_dir(path: Path, expected_relative: str) -> Path:
    resolved = path.resolve()
    expected = _resolve_locked_path(expected_relative)
    if resolved != expected:
        raise IdentityContractError("v3 output directory differs from lock")
    if resolved.exists():
        raise IdentityContractError("v3 output directory must be fresh and absent")
    resolved.mkdir(parents=True, exist_ok=False)
    return resolved


def _safe_remove_ephemeral(path: Path, expected_relative: str) -> None:
    expected = _resolve_locked_path(expected_relative)
    resolved = path.resolve()
    if resolved != expected:
        raise IdentityContractError("ephemeral cleanup target differs from lock")
    if resolved.exists():
        shutil.rmtree(resolved)


def _run_frozen_stages(output_dir: Path, ephemeral_dir: Path) -> dict[str, Any]:
    recorder = HeartbeatRecorder(output_dir / "stage_heartbeat.jsonl")
    original_verify = v1.verify_execution_bindings
    try:
        recorder.begin_stage("verify_frozen_bindings")
        verified = v1.verify_execution_bindings(require_committed=False)
        v1.verify_execution_bindings = lambda: dict(verified)
        recorder.end_stage()

        recorder.begin_stage("load_bound_inputs")
        schedule = v1.load_d7_schedule()
        structural, ecrs_bars, scc_path, metadata = v1.load_bound_stage0_bars()
        calendar = v1.load_bound_news_calendar()
        if metadata["rows"] != v1.BOUND_D7_STAGE0_RECORD_COUNT:
            raise IdentityContractError("v3 source row mismatch")
        control_records = v1._load_scc_records(v1.SCC_CONTROL_PATH, v1.SCC_CONTROL_SHA256, challenger=False)
        challenger_records = v1._load_scc_records(v1.SCC_CHALLENGER_PATH, v1.SCC_CHALLENGER_SHA256, challenger=True)
        recorder.end_stage()

        recorder.begin_stage("scc_control_reference", progress_unit="source_bar", progress_total=len(scc_path))
        scc_control = emit_scc_control_identities(
            control_records,
            source_bars=ObservedSequence(scc_path, recorder),
        )
        recorder.end_stage()

        recorder.begin_stage("scc_challenger_reference", progress_unit="source_bar", progress_total=len(scc_path))
        scc_challenger = emit_scc_challenger_identities(
            challenger_records,
            source_bars=ObservedSequence(scc_path, recorder),
        )
        recorder.end_stage()

        recorder.begin_stage("scc_strict_subset")
        v1.assert_scc_challenger_strict_subset(scc_control, scc_challenger)
        recorder.end_stage()

        prefix_bars = 50000
        recorder.begin_stage("t2_structural_prefix", progress_unit="source_bar", progress_total=prefix_bars)
        t2_result = emit_t2_d7_structural_identities(
            ObservedSequence(structural[:prefix_bars], recorder),
            symbol="EURUSD",
            tick=v1.EURUSD_TICK_SIZE,
            schedule=schedule,
        )
        recorder.end_stage()

        recorder.begin_stage("ecrs_prefix", progress_unit="source_bar", progress_total=prefix_bars)
        ecrs_events = emit_ecrs_v1_identities(
            ObservedSequence(ecrs_bars[:prefix_bars], recorder),
            symbol="EURUSD",
            news_calendar=calendar,
        )
        recorder.end_stage()

        recorder.begin_stage("d7_prefix_comparison")
        d7_prefix = compare_identities(t2_result.events, ecrs_events, key_fields=ECRS_IDENTITY_FIELDS)
        recorder.end_stage()

        recorder.begin_stage("pbp_identity_projection")
        pbp_events = emit_t2_pbp_like_identities(t2_result.pbp_audits)
        pbp_break = [row for row in pbp_events if row["subset"] == "PBP_BREAK_WINDOW"]
        pbp_contact = [row for row in pbp_events if row["subset"] == "PBP_TOMBSTONE_CONTACT"]
        recorder.end_stage()

        recorder.begin_stage("d8_break_prefix_comparison")
        d8_break_prefix = compare_identities(pbp_break, scc_control, key_fields=NORMALIZED_OVERLAP_FIELDS)
        recorder.end_stage()

        recorder.begin_stage("d8_contact_prefix_comparison")
        d8_contact_prefix = compare_identities(pbp_contact, scc_challenger, key_fields=NORMALIZED_OVERLAP_FIELDS)
        recorder.end_stage()

        recorder.begin_stage("ephemeral_serialization")
        if ephemeral_dir.exists():
            raise IdentityContractError("v3 ephemeral directory must be absent")
        ephemeral_dir.mkdir(parents=True, exist_ok=False)
        artifacts: dict[str, Iterable[Any]] = {
            "t2_structural_prefix.jsonl": t2_result.events,
            "t2_reject_prefix.jsonl": [asdict(value) for value in t2_result.rejects],
            "t2_pbp_audit_prefix.jsonl": [asdict(value) for value in t2_result.pbp_audits],
            "ecrs_v1_prefix.jsonl": ecrs_events,
            "t2_pbp_identity_prefix.jsonl": pbp_events,
            "scc_control_full_reference.jsonl": scc_control,
            "scc_challenger_full_reference.jsonl": scc_challenger,
        }
        for filename, rows in artifacts.items():
            v1._atomic_jsonl(ephemeral_dir / filename, rows)
        ephemeral_result = {
            "authority": "EPHEMERAL_ENGINEERING_ONLY",
            "d7_prefix_diagnostic": asdict(d7_prefix),
            "d8_break_prefix_diagnostic": asdict(d8_break_prefix),
            "d8_contact_prefix_diagnostic": asdict(d8_contact_prefix),
            "source_field_contract": "IDENTITY_ONLY_NO_TRADE_RESULT_FIELDS",
        }
        reject_outcome_fields(ephemeral_result)
        v1._atomic_json(ephemeral_dir / "prefix_result.json", ephemeral_result)
        recorder.end_stage()

        recorder.begin_stage("ephemeral_cleanup")
        _safe_remove_ephemeral(ephemeral_dir, str(ephemeral_dir.relative_to(REPO_ROOT)).replace("\\", "/"))
        recorder.end_stage()
        recorder.close()
        return {"status": "WORKER_COMPLETED_ALL_FROZEN_STAGES", "source_field_contract": "IDENTITY_ONLY_NO_TRADE_RESULT_FIELDS"}
    finally:
        v1.verify_execution_bindings = original_verify


def _read_heartbeats(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


def _write_parent_receipt(
    output_dir: Path,
    *,
    lock_sha256: str,
    status: str,
    timed_out: bool,
    child_exit_code: int | None,
    parent_wall_seconds: float,
    ephemeral_removed: bool,
) -> dict[str, Any]:
    heartbeat_path = output_dir / "stage_heartbeat.jsonl"
    heartbeats = _read_heartbeats(heartbeat_path)
    receipt = {
        "schema_version": "t2_p3_stage_receipt.v3",
        "recorded_at_utc": _utc_now(),
        "status": status,
        "authority": "ENGINEERING_STAGE_INSTRUMENTATION_ONLY",
        "lock_sha256": lock_sha256,
        "source_field_contract": "IDENTITY_ONLY_NO_TRADE_RESULT_FIELDS",
        "economic_claim_authorized": False,
        "full_replay_authorized": False,
        "v3_rerun_authorized": False,
        "hard_timeout_seconds": 300,
        "timed_out": timed_out,
        "child_exit_code": child_exit_code,
        "parent_wall_seconds": parent_wall_seconds,
        "heartbeat_file": str(heartbeat_path),
        "heartbeat_sha256": sha256_file(heartbeat_path) if heartbeats else None,
        "heartbeat_lines": len(heartbeats),
        "last_heartbeat": heartbeats[-1] if heartbeats else None,
        "ephemeral_removed": ephemeral_removed,
        "durable_output_files": sorted(EXPECTED_FILES),
    }
    reject_outcome_fields(receipt)
    v1._atomic_json(output_dir / "stage_receipt.json", receipt)
    return receipt


def run_bounded_stage_probe(output_dir: Path) -> dict[str, Any]:
    lock = verify_lock()
    probe = lock["document"]["probe"]
    output_dir = _prepare_output_dir(output_dir, probe["output_directory"])
    ephemeral_dir = _resolve_locked_path(probe["ephemeral_directory"])
    _safe_remove_ephemeral(ephemeral_dir, probe["ephemeral_directory"])
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        "--output-dir",
        str(output_dir),
        "--ephemeral-dir",
        str(ephemeral_dir),
    ]
    started = time.perf_counter()
    timed_out = False
    returncode: int | None = None
    worker_status = ""
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
        returncode = completed.returncode
        markers = [line for line in completed.stdout.splitlines() if line.startswith(WORKER_MARKER)]
        if returncode == 0 and len(markers) == 1:
            worker_status = json.loads(markers[0][len(WORKER_MARKER):])["status"]
            status = "PASS_STAGE_PATH_COMPLETED_ENGINEERING_ONLY"
        else:
            status = "FAIL_STAGE_WORKER_NO_VALID_COMPLETION_MARKER"
    except subprocess.TimeoutExpired:
        timed_out = True
        status = "TIMEOUT_STAGE_LOCALIZED_ENGINEERING_ONLY"
    finally:
        _safe_remove_ephemeral(ephemeral_dir, probe["ephemeral_directory"])
    receipt = _write_parent_receipt(
        output_dir,
        lock_sha256=lock["sha256"],
        status=status,
        timed_out=timed_out,
        child_exit_code=returncode,
        parent_wall_seconds=time.perf_counter() - started,
        ephemeral_removed=not ephemeral_dir.exists(),
    )
    if set(path.name for path in output_dir.iterdir()) != EXPECTED_FILES:
        raise IdentityContractError("v3 durable output set mismatch")
    if not receipt["heartbeat_lines"]:
        raise IdentityContractError("v3 stage probe produced no flushed heartbeat")
    return {"worker_status": worker_status or None, **receipt}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--verify-only", action="store_true")
    modes.add_argument("--run-stage-probe", action="store_true")
    modes.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--ephemeral-dir", type=Path, help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.verify_only:
        if args.output_dir is not None or args.ephemeral_dir is not None:
            raise SystemExit("--verify-only takes no runtime directory")
        lock = verify_lock()
        bindings = v1.verify_execution_bindings(require_committed=False)
        print(json.dumps({
            "status": "PASS_VERIFY_ONLY",
            "authority": "ENGINEERING_STAGE_INSTRUMENTATION_ONLY",
            "lock_sha256": lock["sha256"],
            "source_field_contract": "IDENTITY_ONLY_NO_TRADE_RESULT_FIELDS",
            "verified_binding_names": sorted(bindings),
        }, indent=2, sort_keys=True))
        return 0
    if args.output_dir is None:
        raise SystemExit("stage probe requires --output-dir")
    if args.worker:
        if args.ephemeral_dir is None:
            raise SystemExit("worker requires --ephemeral-dir")
        result = _run_frozen_stages(args.output_dir.resolve(), args.ephemeral_dir.resolve())
        print(WORKER_MARKER + json.dumps(result, sort_keys=True))
        return 0
    if args.ephemeral_dir is not None:
        raise SystemExit("parent stage probe does not accept --ephemeral-dir")
    result = run_bounded_stage_probe(args.output_dir.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
