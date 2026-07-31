from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR_PATH = ROOT / "research" / "stage0_trendstack_002_supervisor.py"
WORKER_PATH = ROOT / "research" / "stage0_trendstack_002_worker.py"
PLAN_SHA256 = "3A6137ACEA37D1CC6BEE1700A561873AF8278AC524973054A82F92C70ED95EAF"
HYPOTHESIS_ID = "HYP-TRENDSTACK-EURUSD-H1-002"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def pretty_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def write_json(path: Path, value: object) -> bytes:
    raw = canonical_bytes(value) + b"\n"
    path.write_bytes(raw)
    return raw


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> bytes:
    raw = b"".join(canonical_bytes(row) + b"\n" for row in rows)
    path.write_bytes(raw)
    return raw


def snapshot_tree(root: Path) -> tuple[tuple[str, str, bytes | None], ...]:
    return tuple(
        (
            path.relative_to(root).as_posix(),
            "directory" if path.is_dir() else "file",
            None if path.is_dir() else path.read_bytes(),
        )
        for path in sorted(root.rglob("*"))
    )


def make_packet(
    opportunity_id: str,
    split: str,
    m252_direction: int,
    m6_direction: int,
) -> dict[str, object]:
    source_date = opportunity_id
    source_chain = {
        "prior_completed_shards_sha256": "A" * 64,
        "current_pre12_sha256": sha256(opportunity_id.encode("ascii")),
    }
    m6_eligible = m6_direction in (-1, 1)
    stack = m6_eligible and m252_direction == m6_direction
    disagree = m6_eligible and m252_direction == -m6_direction
    packet: dict[str, object] = {
        "schema_version": "trendstack_002_decision_packet.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "opportunity_id": opportunity_id,
        "split": split,
        "decision_cutoff_utc": f"{source_date}T12:00:00+00:00",
        "m252_direction": m252_direction,
        "m6_direction": m6_direction,
        "alignment": m252_direction == m6_direction if m6_eligible else None,
        "atr20": 0.001,
        "control_m252_eligible": True,
        "control_m6_eligible": m6_eligible,
        "challenger_stack_eligible": stack,
        "negative_disagree_eligible": disagree,
        "exclusion_reason": None if stack else ("M252_M6_DISAGREE" if disagree else "M6_EQUALITY"),
        "valid_prior_close_count": 253,
        "max_source_time_utc": f"{source_date}T11:00:00+00:00",
        "source_shard_chain_hashes": source_chain,
        "source_chain_sha256": sha256(canonical_bytes(source_chain)),
        "extractor_sha256": "C" * 64,
        "source_plan_sha256": PLAN_SHA256,
    }
    packet["packet_payload_sha256"] = sha256(canonical_bytes(packet))
    return packet


def build_synthetic_source_package(base: Path) -> tuple[Path, list[dict[str, object]]]:
    package = base / "source_package"
    packet_root = package / "decision_packets"
    packet_root.mkdir(parents=True)
    packet_specs = [
        ("2020-01-02", "DESIGN", 1, 1),
        ("2020-01-03", "DESIGN", 1, -1),
        ("2022-01-02", "VALIDATION_FEATURE_ONLY", -1, -1),
    ]
    manifest_rows: list[dict[str, object]] = []
    packet_files: list[tuple[str, bytes]] = []
    for opportunity_id, split, m252, m6 in packet_specs:
        packet = make_packet(opportunity_id, split, m252, m6)
        relative_path = f"{split}/{opportunity_id}.json"
        packet_path = packet_root / Path(relative_path)
        packet_path.parent.mkdir(parents=True, exist_ok=True)
        raw = pretty_bytes(packet)
        packet_path.write_bytes(raw)
        packet_files.append((relative_path, raw))
        manifest_rows.append(
            {
                "hypothesis_id": HYPOTHESIS_ID,
                "opportunity_id": opportunity_id,
                "split": split,
                "packet_path": relative_path,
                "packet_payload_sha256": packet["packet_payload_sha256"],
                "source_chain_sha256": packet["source_chain_sha256"],
                "max_source_time_utc": packet["max_source_time_utc"],
                "extractor_sha256": packet["extractor_sha256"],
                "source_plan_sha256": PLAN_SHA256,
                "forbidden_field_scan": "PASS",
                "packet_file_sha256": sha256(raw),
                "packet_bytes": len(raw),
            }
        )

    runtime_hashes = {
        "terminal_executable_sha256": "1" * 64,
        "python_executable_sha256": "2" * 64,
        "metatrader5_native_module_sha256": "3" * 64,
        "clock_tool_sha256": "4" * 64,
        "extractor_sha256": "C" * 64,
        "source_plan_sha256": PLAN_SHA256,
    }
    source_manifest_rows = [
        {
            "record_type": "request",
            "request_id": "REQ-001",
            "canonical_from_utc": "2020-01-01T00:00:00+00:00",
            "canonical_to_inclusive_utc": "2022-12-30T21:00:00+00:00",
            "source_end_exclusive_utc": "2022-12-30T21:00:01+00:00",
            "api_server_wall_from_encoded_as_utc": "2020-01-01T00:00:00",
            "api_server_wall_to_encoded_as_utc": "2022-12-30T21:00:00",
            "canonical_roundtrip_status": "PASS",
            "symbol": "EURUSD",
            "timeframe": "H1",
            "response": {
                "rows": 100,
                "first_server_time": "2020-01-01T00:00:00",
                "last_server_time": "2022-12-30T21:00:00",
                "first_utc_time": "2020-01-01T00:00:00+00:00",
                "last_utc_time": "2022-12-30T21:00:00+00:00",
                "duplicate_utc_opens": 0,
                "gap_count": 0,
                "maximum_gap_hours": 0.0,
                "gap_multiple_status": "PASS",
                "geometry_status": "PASS",
                "holdout_rows_received": 0,
            },
            "runtime_hashes": runtime_hashes,
        },
        {
            "record_type": "shard",
            "shard_path": "raw_h1/VALIDATION_FEATURE_ONLY/2022-12-30/post12.parquet",
            "split": "VALIDATION_FEATURE_ONLY",
            "date_utc": "2022-12-30",
            "segment": "post12",
            "rows": 100,
            "bytes": 1000,
            "sha256": "5" * 64,
            "canonical_row_content_sha256": "6" * 64,
            "first_utc_time": "2022-12-30T12:00:00+00:00",
            "last_utc_time": "2022-12-30T21:00:00+00:00",
            "request_ids": ["REQ-001"],
            "row_groups": 1,
            "duplicate_utc_opens": 0,
            "gap_multiple_status": "PASS",
            "geometry_status": "PASS",
            "holdout_rows_received": 0,
            "runtime_hashes": runtime_hashes,
        },
    ]
    source_manifest_raw = write_jsonl(package / "source_manifest.jsonl", source_manifest_rows)
    source_receipt = {
        "schema_version": "trendstack_002_source_validation.v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "source_plan_sha256": PLAN_SHA256,
        "source_manifest_sha256": sha256(source_manifest_raw),
        "request_count": 1,
        "shard_file_count": 1,
        "source_rows": 100,
        "maximum_utc_timestamp": "2022-12-30T21:00:00+00:00",
        "runtime_provenance": {
            "terminal_executable_label": "terminal64.exe",
            "terminal_executable_sha256": runtime_hashes["terminal_executable_sha256"],
            "terminal_build": 1,
            "python_executable_label": "python.exe",
            "python_executable_sha256": runtime_hashes["python_executable_sha256"],
            "metatrader5_version": "synthetic",
            "metatrader5_native_module_label": "_core.pyd",
            "metatrader5_native_module_sha256": runtime_hashes["metatrader5_native_module_sha256"],
            "clock_tool_label": "fivepercent_server_clock.py",
            "clock_tool_sha256": runtime_hashes["clock_tool_sha256"],
            "extractor_label": "prepare_trendstack_002_source.py",
            "extractor_sha256": runtime_hashes["extractor_sha256"],
            "source_plan_label": "HYP-TRENDSTACK-EURUSD-H1-002_SOURCE_PLAN.md",
            "source_plan_sha256": runtime_hashes["source_plan_sha256"],
            "account_guard": {
                "terminal_build": 1,
                "terminal_trade_allowed": False,
                "account_mode": "DEMO",
                "server": "FivePercentOnline-Real",
                "company": "Five Percent Online Ltd",
                "symbol": "EURUSD",
                "symbol_digits": 5,
                "symbol_point": 0.00001,
            },
            "pandas_version": "synthetic",
            "pyarrow_version": "synthetic",
        },
        "all_shard_hashes_verified": True,
        "no_2023_canonical_request": True,
        "no_2023_row": True,
        "no_2023_file": True,
        "m1_opened": False,
        "outcomes_opened": False,
        "physical_partition_status": "PASS",
    }
    source_receipt_raw = write_json(package / "source_validation_receipt.json", source_receipt)
    packet_manifest_raw = write_jsonl(package / "decision_packet_manifest.jsonl", manifest_rows)
    packet_set_hasher = hashlib.sha256()
    for relative_path, raw in sorted(packet_files):
        packet_set_hasher.update(relative_path.encode("utf-8"))
        packet_set_hasher.update(b"\0")
        packet_set_hasher.update(raw)
    packet_receipt = {
        "schema_version": "trendstack_002_decision_packet_receipt.v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "source_plan_sha256": PLAN_SHA256,
        "source_manifest_sha256": sha256(source_manifest_raw),
        "source_validation_receipt_sha256": sha256(source_receipt_raw),
        "decision_packet_manifest_sha256": sha256(packet_manifest_raw),
        "packet_set_sha256": packet_set_hasher.hexdigest().upper(),
        "packet_count": len(manifest_rows),
        "unique_opportunity_ids": True,
        "deterministic_rebuild_status": "PASS_DISK_REOPEN",
        "forbidden_field_scan": "PASS",
        "maximum_source_time_utc": "2022-01-02T11:00:00+00:00",
        "no_2023_packet": True,
        "m1_opened": False,
        "outcomes_opened": False,
        "holdout_opened": False,
        "economic_metrics_computed": False,
        "strategy_process_raw_source_access": "NOT_YET_VERIFIED_STAGE0_REQUIRED",
        "verdict": "SOURCE_READY_FOR_INDEPENDENT_STAGE0_REVIEW",
    }
    write_json(package / "decision_packet_receipt.json", packet_receipt)
    return package, manifest_rows


def load_supervisor():
    spec = importlib.util.spec_from_file_location("stage0_trendstack_002_supervisor", SUPERVISOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def refresh_packet_receipt_bindings(package: Path) -> None:
    source_manifest_raw = (package / "source_manifest.jsonl").read_bytes()
    source_receipt_raw = (package / "source_validation_receipt.json").read_bytes()
    packet_manifest_raw = (package / "decision_packet_manifest.jsonl").read_bytes()
    receipt_path = package / "decision_packet_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["source_manifest_sha256"] = sha256(source_manifest_raw)
    receipt["source_validation_receipt_sha256"] = sha256(source_receipt_raw)
    receipt["decision_packet_manifest_sha256"] = sha256(packet_manifest_raw)
    write_json(receipt_path, receipt)


def refresh_source_and_packet_receipt_bindings(package: Path) -> None:
    source_manifest_raw = (package / "source_manifest.jsonl").read_bytes()
    source_receipt_path = package / "source_validation_receipt.json"
    source_receipt = json.loads(source_receipt_path.read_text(encoding="utf-8"))
    source_receipt["source_manifest_sha256"] = sha256(source_manifest_raw)
    write_json(source_receipt_path, source_receipt)
    refresh_packet_receipt_bindings(package)


def synthetic_provenance(package: Path) -> dict[str, object]:
    source_receipt = json.loads((package / "source_validation_receipt.json").read_text(encoding="utf-8"))
    packet_receipt = json.loads((package / "decision_packet_receipt.json").read_text(encoding="utf-8"))
    packet_manifest = [
        json.loads(line)
        for line in (package / "decision_packet_manifest.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    return {
        "source_manifest_sha256": sha256((package / "source_manifest.jsonl").read_bytes()),
        "source_receipt_sha256": sha256((package / "source_validation_receipt.json").read_bytes()),
        "decision_manifest_sha256": sha256((package / "decision_packet_manifest.jsonl").read_bytes()),
        "decision_receipt_sha256": sha256((package / "decision_packet_receipt.json").read_bytes()),
        "packet_set_sha256": packet_receipt["packet_set_sha256"],
        "extractor_sha256": packet_manifest[0]["extractor_sha256"],
        "request_count": source_receipt["request_count"],
        "source_rows": source_receipt["source_rows"],
        "shard_file_count": source_receipt["shard_file_count"],
        "packet_count": packet_receipt["packet_count"],
        "maximum_utc_timestamp": source_receipt["maximum_utc_timestamp"],
        "maximum_source_time_utc": packet_receipt["maximum_source_time_utc"],
    }


def install_synthetic_provenance(supervisor, package: Path) -> None:
    supervisor.EXPECTED_PROVENANCE = synthetic_provenance(package)


def test_supervisor_validates_the_complete_synthetic_package_before_workers(tmp_path: Path) -> None:
    supervisor = load_supervisor()
    package, manifest_rows = build_synthetic_source_package(tmp_path)
    install_synthetic_provenance(supervisor, package)
    validated = supervisor.validate_source_package(package, frozen_root=package)
    assert [row["opportunity_id"] for row in validated["packet_manifest"]] == [
        row["opportunity_id"] for row in manifest_rows
    ]
    assert len(validated["packet_bytes_by_path"]) == 3


@pytest.mark.parametrize(
    ("target", "field", "value"),
    [
        ("source_validation_receipt.json", "physical_partition_status", "FAIL"),
        ("source_validation_receipt.json", "m1_opened", True),
        ("decision_packet_receipt.json", "schema_version", "wrong.v2"),
        ("decision_packet_receipt.json", "holdout_opened", True),
        ("decision_packet_receipt.json", "packet_count", 99),
        ("decision_packet_receipt.json", "source_plan_sha256", "0" * 64),
    ],
)
def test_supervisor_fails_closed_on_receipt_tamper(
    tmp_path: Path, target: str, field: str, value: object
) -> None:
    supervisor = load_supervisor()
    package, _ = build_synthetic_source_package(tmp_path)
    path = package / target
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload[field] = value
    write_json(path, payload)
    refresh_packet_receipt_bindings(package)
    install_synthetic_provenance(supervisor, package)
    with pytest.raises(supervisor.InvalidEngineering):
        supervisor.validate_source_package(package, frozen_root=package)


@pytest.mark.parametrize("bad_path", ["../escape.json", "DESIGN\\2024-01-02.json", "C:/escape.json"])
def test_supervisor_rejects_noncanonical_packet_paths(tmp_path: Path, bad_path: str) -> None:
    supervisor = load_supervisor()
    package, _ = build_synthetic_source_package(tmp_path)
    manifest_path = package / "decision_packet_manifest.jsonl"
    rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["packet_path"] = bad_path
    write_jsonl(manifest_path, rows)
    refresh_packet_receipt_bindings(package)
    install_synthetic_provenance(supervisor, package)
    with pytest.raises(supervisor.InvalidEngineering):
        supervisor.validate_source_package(package, frozen_root=package)


def test_supervisor_rejects_manifest_order_tamper(tmp_path: Path) -> None:
    supervisor = load_supervisor()
    package, _ = build_synthetic_source_package(tmp_path)
    manifest_path = package / "decision_packet_manifest.jsonl"
    rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()]
    write_jsonl(manifest_path, list(reversed(rows)))
    refresh_packet_receipt_bindings(package)
    install_synthetic_provenance(supervisor, package)
    with pytest.raises(supervisor.InvalidEngineering):
        supervisor.validate_source_package(package, frozen_root=package)


def test_supervisor_rejects_packet_set_and_file_hash_tamper(tmp_path: Path) -> None:
    supervisor = load_supervisor()
    package, _ = build_synthetic_source_package(tmp_path)
    install_synthetic_provenance(supervisor, package)
    packet_path = package / "decision_packets" / "DESIGN" / "2020-01-02.json"
    packet_path.write_bytes(packet_path.read_bytes() + b" ")
    with pytest.raises(supervisor.InvalidEngineering):
        supervisor.validate_source_package(package, frozen_root=package)


def test_supervisor_rejects_wrong_root_and_symlinked_packet(tmp_path: Path) -> None:
    supervisor = load_supervisor()
    package, _ = build_synthetic_source_package(tmp_path)
    install_synthetic_provenance(supervisor, package)
    with pytest.raises(supervisor.InvalidEngineering):
        supervisor.validate_source_package(package, frozen_root=tmp_path / "other")

    original = package / "decision_packets" / "DESIGN" / "2020-01-02.json"
    target = tmp_path / "target.json"
    target.write_bytes(original.read_bytes())
    original.unlink()
    try:
        original.symlink_to(target)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("Windows symlink privilege is unavailable (WinError 1314)")
        raise
    with pytest.raises(supervisor.InvalidEngineering):
        supervisor.validate_source_package(package, frozen_root=package)


def test_stage0_runs_one_fresh_isolated_worker_per_packet_and_reconciles_exactly_once(
    tmp_path: Path,
) -> None:
    supervisor = load_supervisor()
    package, manifest_rows = build_synthetic_source_package(tmp_path)
    install_synthetic_provenance(supervisor, package)
    output = tmp_path / "stage0_output"
    receipt = supervisor.run_stage0(
        package,
        output,
        worker_path=WORKER_PATH,
        frozen_root=package,
    )
    assert receipt["engineering_status"] == "PASS"
    assert receipt["stage0_verdict"] == "PARK"
    assert receipt["packet_count"] == len(manifest_rows)
    assert receipt["worker_process_count"] == len(manifest_rows)
    assert receipt["exact_once_reconciliation"] == "PASS"
    assert receipt["temporary_cleanup"] == "PASS"

    ledger = [json.loads(line) for line in (output / "stage0_eligibility_ledger.jsonl").read_text().splitlines()]
    trace = [json.loads(line) for line in (output / "stage0_access_trace.jsonl").read_text().splitlines()]
    assert [row["row_index"] for row in ledger] == list(range(len(manifest_rows)))
    assert [row["opportunity_id"] for row in ledger] == [row["opportunity_id"] for row in manifest_rows]
    assert all(row["staged_packet_count"] == 1 for row in trace)
    assert all(row["fresh_isolated_process"] is True for row in trace)
    assert all(row["cleanup_status"] == "PASS" for row in trace)
    assert not (output / ".stage0_work").exists()
    for path in output.iterdir():
        text = path.read_text(encoding="utf-8")
        assert str(tmp_path) not in text
        assert "timestamp" not in text.lower()
        assert "pid" not in text.lower()

    reconciled = supervisor.reconcile_outputs(output, manifest_rows)
    assert reconciled["exact_once_reconciliation"] == "PASS"
    with pytest.raises(supervisor.InvalidEngineering):
        supervisor.run_stage0(package, output, worker_path=WORKER_PATH, frozen_root=package)


def test_stage0_outputs_are_deterministic_across_distinct_roots(tmp_path: Path) -> None:
    supervisor = load_supervisor()
    package_a, _ = build_synthetic_source_package(tmp_path / "a")
    package_b, _ = build_synthetic_source_package(tmp_path / "b")
    install_synthetic_provenance(supervisor, package_a)
    output_a = tmp_path / "out_a"
    output_b = tmp_path / "out_b"
    supervisor.run_stage0(package_a, output_a, worker_path=WORKER_PATH, frozen_root=package_a)
    supervisor.run_stage0(package_b, output_b, worker_path=WORKER_PATH, frozen_root=package_b)
    assert sorted(path.name for path in output_a.iterdir()) == sorted(path.name for path in output_b.iterdir())
    for path_a in output_a.iterdir():
        assert path_a.read_bytes() == (output_b / path_a.name).read_bytes()


@pytest.mark.parametrize(
    "output_selector",
    [
        lambda package: package,
        lambda package: package / "decision_packets" / "stage0_output",
        lambda package: package.parent,
    ],
    ids=["equal-package", "inside-package", "ancestor-of-package"],
)
def test_review_attack_output_root_overlap_is_rejected_before_any_mkdir_or_mutation(
    tmp_path: Path, monkeypatch, output_selector
) -> None:
    supervisor = load_supervisor()
    package, _ = build_synthetic_source_package(tmp_path)
    install_synthetic_provenance(supervisor, package)
    output = output_selector(package)
    before = snapshot_tree(package)
    mkdir_calls: list[Path] = []
    original_mkdir = supervisor.Path.mkdir

    def recording_mkdir(path, *args, **kwargs):
        mkdir_calls.append(Path(path))
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(supervisor.Path, "mkdir", recording_mkdir)
    with pytest.raises(supervisor.InvalidEngineering, match="output root overlaps immutable input"):
        supervisor.run_stage0(package, output, worker_path=WORKER_PATH, frozen_root=package)

    assert mkdir_calls == []
    assert snapshot_tree(package) == before


def test_review_attack_package_identity_is_rechecked_before_pass_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    supervisor = load_supervisor()
    package, _ = build_synthetic_source_package(tmp_path)
    install_synthetic_provenance(supervisor, package)
    packet_path = package / "decision_packets" / "DESIGN" / "2020-01-02.json"
    original_run_worker = supervisor._run_worker
    mutated = False

    def mutate_after_first_worker(worker_source, worker_sha256, stage_dir, expected_sha256):
        nonlocal mutated
        result = original_run_worker(worker_source, worker_sha256, stage_dir, expected_sha256)
        if not mutated:
            packet_path.write_bytes(packet_path.read_bytes() + b" ")
            mutated = True
        return result

    monkeypatch.setattr(supervisor, "_run_worker", mutate_after_first_worker)
    output = tmp_path / "stage0_output"
    with pytest.raises(supervisor.InvalidEngineering, match="source package changed during Stage-0"):
        supervisor.run_stage0(package, output, worker_path=WORKER_PATH, frozen_root=package)

    assert mutated is True
    assert not (output / "stage0_receipt.json").exists()


@pytest.mark.parametrize(
    "mutation_kind",
    ["atomic-identical-file-replace", "write-restore-with-mtime-change", "identical-directory-replace"],
)
def test_review_attack_identical_bytes_cannot_hide_package_identity_replacement(
    tmp_path: Path, monkeypatch, mutation_kind: str
) -> None:
    supervisor = load_supervisor()
    package, _ = build_synthetic_source_package(tmp_path)
    install_synthetic_provenance(supervisor, package)
    packet_path = package / "decision_packets" / "DESIGN" / "2020-01-02.json"
    design_root = packet_path.parent
    original_packet_identity = supervisor._identity(os.lstat(packet_path))
    original_directory_identity = supervisor._identity(os.lstat(design_root))
    original_run_worker = supervisor._run_worker
    mutated = False

    def mutate_after_first_worker(worker_source, worker_sha256, stage_dir, expected_sha256):
        nonlocal mutated
        result = original_run_worker(worker_source, worker_sha256, stage_dir, expected_sha256)
        if mutated:
            return result
        packet_bytes = packet_path.read_bytes()
        if mutation_kind == "atomic-identical-file-replace":
            replacement = tmp_path / "identical-packet-replacement.json"
            replacement.write_bytes(packet_bytes)
            os.replace(replacement, packet_path)
            assert supervisor._identity(os.lstat(packet_path)) != original_packet_identity
        elif mutation_kind == "write-restore-with-mtime-change":
            packet_path.write_bytes(packet_bytes + b"temporary mutation")
            packet_path.write_bytes(packet_bytes)
            current = os.stat(packet_path)
            os.utime(packet_path, ns=(current.st_atime_ns, current.st_mtime_ns + 2_000_000_000))
            assert packet_path.read_bytes() == packet_bytes
            assert supervisor._identity(os.lstat(packet_path)) != original_packet_identity
        else:
            removed = tmp_path / "removed-design-directory"
            replacement = tmp_path / "identical-design-directory"
            shutil.copytree(design_root, replacement)
            design_root.rename(removed)
            replacement.rename(design_root)
            shutil.rmtree(removed)
            assert packet_path.read_bytes() == packet_bytes
            assert supervisor._identity(os.lstat(design_root)) != original_directory_identity
        mutated = True
        return result

    monkeypatch.setattr(supervisor, "_run_worker", mutate_after_first_worker)
    output = tmp_path / "stage0_output"
    with pytest.raises(supervisor.InvalidEngineering, match="source package changed during Stage-0"):
        supervisor.run_stage0(package, output, worker_path=WORKER_PATH, frozen_root=package)

    assert mutated is True
    assert not (output / "stage0_receipt.json").exists()


def test_supervisor_rejects_a_substituted_worker_before_process_launch(tmp_path: Path) -> None:
    supervisor = load_supervisor()
    package, _ = build_synthetic_source_package(tmp_path)
    install_synthetic_provenance(supervisor, package)
    substituted = tmp_path / "substituted_worker.py"
    substituted.write_bytes(WORKER_PATH.read_bytes())
    with pytest.raises(supervisor.InvalidEngineering):
        supervisor.run_stage0(
            package,
            tmp_path / "stage0_output",
            worker_path=substituted,
            frozen_root=package,
        )


def test_lifecycle_spy_proves_fsync_and_cleanup_precede_the_next_worker_open(
    tmp_path: Path, monkeypatch
) -> None:
    supervisor = load_supervisor()
    package, _ = build_synthetic_source_package(tmp_path)
    install_synthetic_provenance(supervisor, package)
    events: list[str] = []
    original_run_worker = supervisor._run_worker
    original_write_fsync = supervisor._write_fsync
    original_cleanup = supervisor._cleanup_stage

    def spy_worker(worker_source, worker_sha256, stage_dir, expected_sha256):
        events.append(f"worker:{int(Path(stage_dir).name)}")
        return original_run_worker(worker_source, worker_sha256, stage_dir, expected_sha256)

    def spy_fsync(stream, value):
        if "row_index" in value:
            kind = "ledger" if value["schema_version"] == supervisor.LEDGER_SCHEMA else "trace"
            events.append(f"fsync-{kind}:{value['row_index']}")
        return original_write_fsync(stream, value)

    def spy_cleanup(stage_dir):
        events.append(f"cleanup:{int(Path(stage_dir).name)}")
        return original_cleanup(stage_dir)

    monkeypatch.setattr(supervisor, "_run_worker", spy_worker)
    monkeypatch.setattr(supervisor, "_write_fsync", spy_fsync)
    monkeypatch.setattr(supervisor, "_cleanup_stage", spy_cleanup)
    supervisor.run_stage0(
        package,
        tmp_path / "stage0_output",
        worker_path=WORKER_PATH,
        frozen_root=package,
    )
    for index in (0, 1):
        assert events.index(f"worker:{index}") < events.index(f"fsync-ledger:{index}")
        assert events.index(f"fsync-ledger:{index}") < events.index(f"cleanup:{index}")
        assert events.index(f"cleanup:{index}") < events.index(f"fsync-trace:{index}")
        assert events.index(f"fsync-trace:{index}") < events.index(f"worker:{index + 1}")


def make_gate_rows(split: str, long_count: int, short_count: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for direction, count in ((1, long_count), (-1, short_count)):
        rows.extend(
            {
                "split": split,
                "challenger_stack_eligible": True,
                "challenger_stack_direction": direction,
            }
            for _ in range(count)
        )
    return rows


def test_frozen_count_and_direction_gates_distinguish_pass_from_park() -> None:
    supervisor = load_supervisor()
    passing_rows = make_gate_rows("DESIGN", 261, 261) + make_gate_rows(
        "VALIDATION_FEATURE_ONLY", 105, 104
    )
    result = supervisor.evaluate_count_gates(passing_rows)
    assert result["stage0_verdict"] == "PASS"
    assert result["design"] == {"total": 522, "long": 261, "short": 261, "status": "PASS"}
    assert result["validation_feature_only"] == {
        "total": 209,
        "long": 105,
        "short": 104,
        "status": "PASS",
    }

    too_few = make_gate_rows("DESIGN", 49, 473) + make_gate_rows(
        "VALIDATION_FEATURE_ONLY", 104, 104
    )
    parked = supervisor.evaluate_count_gates(too_few)
    assert parked["stage0_verdict"] == "PARK"
    assert parked["design"]["status"] == "PARK"
    assert parked["validation_feature_only"]["status"] == "PARK"


def test_reconciliation_detects_ledger_tamper(tmp_path: Path) -> None:
    supervisor = load_supervisor()
    package, manifest_rows = build_synthetic_source_package(tmp_path)
    install_synthetic_provenance(supervisor, package)
    output = tmp_path / "stage0_output"
    supervisor.run_stage0(package, output, worker_path=WORKER_PATH, frozen_root=package)
    ledger_path = output / "stage0_eligibility_ledger.jsonl"
    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["challenger_stack_eligible"] = False
    write_jsonl(ledger_path, rows)
    with pytest.raises(supervisor.InvalidEngineering):
        supervisor.reconcile_outputs(output, manifest_rows)


def test_supervisor_source_contains_fresh_process_and_fsync_lifecycle_guards() -> None:
    source = SUPERVISOR_PATH.read_text(encoding="utf-8")
    assert '"-I",' in source
    assert '"-S",' in source
    assert "os.fsync" in source
    assert '"xb"' in source
    assert "subprocess.Popen" in source
    assert "capture_output=True" not in source


def test_review_attack_production_pins_reject_arbitrary_self_attested_package(tmp_path: Path) -> None:
    supervisor = load_supervisor()
    package, _ = build_synthetic_source_package(tmp_path)
    with pytest.raises(supervisor.InvalidEngineering):
        supervisor.validate_source_package(package, frozen_root=package)


@pytest.mark.parametrize(
    ("target", "extra_field"),
    [
        ("source_validation_receipt.json", "unexpected_source_receipt_field"),
        ("decision_packet_receipt.json", "unexpected_packet_receipt_field"),
    ],
)
def test_review_attack_receipt_extra_fields_fail_even_when_all_hashes_are_rebound(
    tmp_path: Path, target: str, extra_field: str
) -> None:
    supervisor = load_supervisor()
    package, _ = build_synthetic_source_package(tmp_path)
    path = package / target
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload[extra_field] = "attacker-controlled"
    write_json(path, payload)
    refresh_packet_receipt_bindings(package)
    install_synthetic_provenance(supervisor, package)
    with pytest.raises(supervisor.InvalidEngineering):
        supervisor.validate_source_package(package, frozen_root=package)


def test_review_attack_source_manifest_extra_field_and_2099_date_fail_with_rebound_hashes(
    tmp_path: Path,
) -> None:
    supervisor = load_supervisor()
    package, _ = build_synthetic_source_package(tmp_path)
    manifest_path = package / "source_manifest.jsonl"
    rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()]
    rows[1]["attacker_extra"] = True
    rows[1]["date_utc"] = "2099-01-01"
    rows[1]["first_utc_time"] = "2099-01-01T00:00:00+00:00"
    rows[1]["last_utc_time"] = "2099-01-01T11:00:00+00:00"
    write_jsonl(manifest_path, rows)
    refresh_source_and_packet_receipt_bindings(package)
    install_synthetic_provenance(supervisor, package)
    with pytest.raises(supervisor.InvalidEngineering):
        supervisor.validate_source_package(package, frozen_root=package)


def test_review_attack_premodified_worker_fails_pinned_hash(tmp_path: Path, monkeypatch) -> None:
    supervisor = load_supervisor()
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    synthetic_supervisor = runtime / "stage0_trendstack_002_supervisor.py"
    synthetic_supervisor.write_text("# path anchor\n", encoding="utf-8")
    worker = runtime / "stage0_trendstack_002_worker.py"
    reviewed = WORKER_PATH.read_bytes()
    worker.write_bytes(reviewed + b"\n# premodified\n")
    monkeypatch.setattr(supervisor, "__file__", str(synthetic_supervisor))
    monkeypatch.setattr(supervisor, "EXPECTED_WORKER_SHA256", sha256(reviewed), raising=False)
    with pytest.raises(supervisor.InvalidEngineering):
        supervisor._load_trusted_worker(worker)


def test_review_attack_worker_swap_executes_cached_reviewed_bytes_not_mutable_path(
    tmp_path: Path, monkeypatch
) -> None:
    supervisor = load_supervisor()
    package, _ = build_synthetic_source_package(tmp_path)
    install_synthetic_provenance(supervisor, package)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    synthetic_supervisor = runtime / "stage0_trendstack_002_supervisor.py"
    synthetic_supervisor.write_text("# path anchor\n", encoding="utf-8")
    worker = runtime / "stage0_trendstack_002_worker.py"
    reviewed = WORKER_PATH.read_bytes()
    worker.write_bytes(reviewed)
    monkeypatch.setattr(supervisor, "__file__", str(synthetic_supervisor))
    monkeypatch.setattr(supervisor, "EXPECTED_WORKER_SHA256", sha256(reviewed), raising=False)
    original_load = supervisor._load_trusted_worker

    def swap_after_review(path):
        trusted = original_load(path)
        Path(path).write_text(
            "from pathlib import Path\nPath('SWAPPED_EXECUTED').write_text('yes')\nprint('{}')\n",
            encoding="utf-8",
        )
        return trusted

    monkeypatch.setattr(supervisor, "_load_trusted_worker", swap_after_review)
    receipt = supervisor.run_stage0(
        package,
        tmp_path / "stage0_output",
        worker_path=worker,
        frozen_root=package,
    )
    assert receipt["worker_sha256"] == sha256(reviewed)
    trace_rows = [
        json.loads(line)
        for line in (tmp_path / "stage0_output" / "stage0_access_trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert all(row["worker_sha256"] == sha256(reviewed) for row in trace_rows)
    assert not any(tmp_path.rglob("SWAPPED_EXECUTED"))


def test_review_attack_gate_rejects_boolean_direction() -> None:
    supervisor = load_supervisor()
    rows = [
        {
            "split": "DESIGN",
            "challenger_stack_eligible": True,
            "challenger_stack_direction": True,
        }
    ]
    with pytest.raises(supervisor.InvalidEngineering):
        supervisor.evaluate_count_gates(rows)


def test_review_attack_supervisor_rejects_packet_direction_bool_end_to_end(tmp_path: Path) -> None:
    supervisor = load_supervisor()
    package, _ = build_synthetic_source_package(tmp_path)
    packet_path = package / "decision_packets" / "DESIGN" / "2020-01-02.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["m252_direction"] = True
    packet["packet_payload_sha256"] = sha256(
        canonical_bytes({key: value for key, value in packet.items() if key != "packet_payload_sha256"})
    )
    raw = pretty_bytes(packet)
    packet_path.write_bytes(raw)
    manifest_path = package / "decision_packet_manifest.jsonl"
    rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["packet_payload_sha256"] = packet["packet_payload_sha256"]
    rows[0]["packet_file_sha256"] = sha256(raw)
    rows[0]["packet_bytes"] = len(raw)
    write_jsonl(manifest_path, rows)
    packet_receipt_path = package / "decision_packet_receipt.json"
    packet_receipt = json.loads(packet_receipt_path.read_text(encoding="utf-8"))
    packet_files = []
    for row in rows:
        packet_files.append((row["packet_path"], (package / "decision_packets" / row["packet_path"]).read_bytes()))
    digest = hashlib.sha256()
    for relative, payload in sorted(packet_files):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload)
    packet_receipt["decision_packet_manifest_sha256"] = sha256(manifest_path.read_bytes())
    packet_receipt["packet_set_sha256"] = digest.hexdigest().upper()
    write_json(packet_receipt_path, packet_receipt)
    install_synthetic_provenance(supervisor, package)
    with pytest.raises(supervisor.InvalidEngineering):
        supervisor.run_stage0(
            package,
            tmp_path / "stage0_output",
            worker_path=WORKER_PATH,
            frozen_root=package,
        )


def test_review_attack_hardlinked_packet_outside_root_is_rejected(tmp_path: Path) -> None:
    supervisor = load_supervisor()
    package, _ = build_synthetic_source_package(tmp_path)
    install_synthetic_provenance(supervisor, package)
    packet = package / "decision_packets" / "DESIGN" / "2020-01-02.json"
    os.link(packet, tmp_path / "outside-hardlink.json")
    assert packet.stat().st_nlink == 2
    with pytest.raises(supervisor.InvalidEngineering):
        supervisor.validate_source_package(package, frozen_root=package)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction semantics")
def test_review_attack_actual_windows_junction_root_is_rejected(tmp_path: Path) -> None:
    supervisor = load_supervisor()
    target, _ = build_synthetic_source_package(tmp_path / "target")
    junction = tmp_path / "package-junction"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    try:
        with pytest.raises(supervisor.InvalidEngineering):
            supervisor.validate_source_package(junction, frozen_root=junction)
    finally:
        if junction.exists():
            junction.rmdir()


@pytest.mark.parametrize(
    ("stream_name", "byte_cap"),
    [("stdout", 16384), ("stderr", 4096)],
)
def test_review_attack_worker_output_is_stream_bounded_and_terminated_before_json_parse(
    tmp_path: Path, monkeypatch, stream_name: str, byte_cap: int
) -> None:
    supervisor = load_supervisor()
    parsed = False

    def forbidden_parse(*args, **kwargs):
        nonlocal parsed
        parsed = True
        raise AssertionError("oversized output reached JSON parser")

    monkeypatch.setattr(supervisor, "_parse_json", forbidden_parse)
    worker_source = (
        "import sys\n"
        f"stream = sys.{stream_name}.buffer\n"
        f"stream.write(b'X' * {byte_cap + 65536})\n"
        "stream.flush()\n"
        "while True:\n"
        "    pass\n"
    )
    started = time.monotonic()
    with pytest.raises(supervisor.InvalidEngineering, match=f"worker {stream_name} exceeds byte bound"):
        supervisor._run_worker(worker_source, sha256(worker_source.encode("utf-8")), tmp_path, "B" * 64)

    assert time.monotonic() - started < 5.0
    assert parsed is False
    assert list(tmp_path.iterdir()) == []
