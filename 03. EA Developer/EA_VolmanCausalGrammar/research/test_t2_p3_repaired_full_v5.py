from __future__ import annotations

import json
from pathlib import Path

import pytest

import run_t2_p3_repaired_full_v5 as full
from t2_dedup_mirrors import IdentityContractError, reject_outcome_fields, sha256_file


def test_full_contract_has_exact_v1_packet_files() -> None:
    assert full.ALWAYS_FILES == {"stage_heartbeat.jsonl", "stage_receipt.json"}
    assert full.SUCCESS_TOP_LEVEL == {"stage_heartbeat.jsonl", "stage_receipt.json", "identity_packet"}
    assert len(full.PACKET_FILES) == 17
    assert {"result.json", "receipt.json", "t2_manifest.json", "ecrs_manifest.json"} <= full.PACKET_FILES


def test_full_packet_cleanup_requires_exact_child(tmp_path: Path) -> None:
    output = tmp_path / "output"
    packet = output / "identity_packet"
    packet.mkdir(parents=True)
    (packet / "partial").write_text("x", encoding="utf-8")
    with pytest.raises(IdentityContractError, match="exact output child"):
        full._remove_packet_dir(output / "other", output)
    assert packet.exists()
    full._remove_packet_dir(packet, output)
    assert not packet.exists()


def test_full_stage_receipt_keeps_stderr_and_denies_authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    heartbeat = tmp_path / "stage_heartbeat.jsonl"
    heartbeat.write_text(json.dumps({"stage": "unit", "progress_index": 11}) + "\n", encoding="utf-8")
    monkeypatch.setattr(full.cache_v4, "verify_lock", lambda: {"sha256": "B" * 64})
    receipt = full._write_stage_receipt(
        tmp_path,
        lock_sha256="A" * 64,
        status="FAIL_REPAIRED_FULL_NONZERO_OR_MARKER_MISMATCH_NO_PACKET",
        timed_out=False,
        child_exit_code=1,
        child_stderr="exact child error",
        parent_wall_seconds=12.3,
        packet_verified=False,
        packet_receipt_sha256=None,
    )
    reject_outcome_fields(receipt)
    assert receipt["child_stderr"] == "exact child error"
    assert receipt["economic_claim_authorized"] is False
    assert receipt["build_or_live_authorized"] is False
    assert receipt["rerun_authorized"] is False
    assert receipt["heartbeat_sha256"] == sha256_file(heartbeat)


def test_resolve_full_output_is_exact_and_contained(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path.resolve()
    monkeypatch.setattr(full, "REPO_ROOT", root)
    monkeypatch.setattr(full, "EVIDENCE_ROOT", root)
    assert full._resolve_output(root / "expected", "expected") == root / "expected"
    with pytest.raises(IdentityContractError, match="differs from lock"):
        full._resolve_output(root / "other", "expected")


def test_instrumentation_substitutes_only_ecrs_and_restores(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    recorder = full.stage_v3.HeartbeatRecorder(tmp_path / "heartbeat.jsonl", interval_seconds=60.0)
    original_ecrs = full.v1.emit_ecrs_v1_identities
    original_d7 = full.v1.compare_d7_primary_full_ledgers
    originals = full._instrument_frozen_v1(recorder)
    try:
        assert full.v1.emit_ecrs_v1_identities is not original_ecrs
        assert originals["emit_ecrs_v1_identities"] is original_ecrs
        assert originals["compare_d7_primary_full_ledgers"] is original_d7
    finally:
        full._restore_v1(originals)
        recorder.close()
    assert full.v1.emit_ecrs_v1_identities is original_ecrs
    assert full.v1.compare_d7_primary_full_ledgers is original_d7


def test_stderr_text_preserves_text_and_decodes_bytes() -> None:
    assert full._stderr_text("hello") == "hello"
    assert full._stderr_text(b"hello") == "hello"
    assert full._stderr_text(None) == ""
