from __future__ import annotations

import json
from pathlib import Path

import pytest

import run_t2_p3_repaired_prefix_v4 as repaired
from t2_dedup_mirrors import IdentityContractError, reject_outcome_fields, sha256_file


def test_output_contract_separates_timeout_from_success() -> None:
    assert repaired.ALWAYS_FILES == {"stage_heartbeat.jsonl", "stage_receipt.json"}
    assert repaired.SUCCESS_TOP_LEVEL == {
        "stage_heartbeat.jsonl",
        "stage_receipt.json",
        "identity_packet",
    }
    assert repaired.PACKET_FILES == {
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


def test_packet_cleanup_requires_exact_child(tmp_path: Path) -> None:
    output = tmp_path / "output"
    packet = output / "identity_packet"
    packet.mkdir(parents=True)
    (packet / "partial").write_text("x", encoding="utf-8")
    with pytest.raises(IdentityContractError, match="exact output child"):
        repaired._remove_packet_dir(output / "other", output)
    assert packet.exists()
    repaired._remove_packet_dir(packet, output)
    assert not packet.exists()


def test_stage_receipt_has_no_economic_or_full_replay_authority(tmp_path: Path) -> None:
    heartbeat = tmp_path / "stage_heartbeat.jsonl"
    heartbeat.write_text(json.dumps({"stage": "unit", "progress_index": 7}) + "\n", encoding="utf-8")
    receipt = repaired._write_stage_receipt(
        tmp_path,
        lock_sha256="A" * 64,
        status="TIMEOUT_REPAIRED_PREFIX_NO_PACKET",
        timed_out=True,
        child_exit_code=None,
        parent_wall_seconds=300.1,
        packet_verified=False,
        packet_receipt_sha256=None,
    )
    reject_outcome_fields(receipt)
    assert receipt["economic_claim_authorized"] is False
    assert receipt["full_replay_authorized"] is False
    assert receipt["rerun_authorized"] is False
    assert receipt["packet_verified"] is False
    assert receipt["heartbeat_sha256"] == sha256_file(heartbeat)


def test_resolve_output_is_exact_and_contained(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path.resolve()
    monkeypatch.setattr(repaired, "REPO_ROOT", root)
    monkeypatch.setattr(repaired, "EVIDENCE_ROOT", root)
    assert repaired._resolve_output(root / "expected", "expected") == root / "expected"
    with pytest.raises(IdentityContractError, match="differs from lock"):
        repaired._resolve_output(root / "other", "expected")


def test_cache_injection_boundary_is_successor_only() -> None:
    assert repaired.cache_v4.emit_ecrs_v1_identities_cached is not repaired.frozen.emit_ecrs_v1_identities
    assert repaired.frozen.emit_scc_control_identities is repaired.packet_v2.emit_scc_control_identities
    assert repaired.frozen.compare_identities is repaired.packet_v2.compare_identities
