from __future__ import annotations

import json
from pathlib import Path

import pytest

import run_t2_p3_stage_instrumented_v3 as stage
from t2_dedup_mirrors import IdentityContractError, reject_outcome_fields, sha256_file


def test_rss_bytes_is_positive() -> None:
    assert stage._rss_bytes() > 0


def test_observed_sequence_preserves_values_and_reports_progress(tmp_path: Path) -> None:
    recorder = stage.HeartbeatRecorder(tmp_path / "heartbeat.jsonl", interval_seconds=60.0)
    recorder.begin_stage("unit_sequence", progress_unit="source_bar", progress_total=5)
    values = list(stage.ObservedSequence([1, 2, 3, 4, 5], recorder, stride=2))
    recorder.end_stage()
    recorder.close()
    assert values == [1, 2, 3, 4, 5]
    lines = [json.loads(line) for line in (tmp_path / "heartbeat.jsonl").read_text().splitlines()]
    assert lines[-2]["progress_index"] == 5
    assert lines[-2]["progress_total"] == 5


def test_parent_receipt_contains_no_forbidden_fields(tmp_path: Path) -> None:
    heartbeat = tmp_path / "stage_heartbeat.jsonl"
    heartbeat.write_text(json.dumps({"stage": "unit", "progress_index": 3}) + "\n", encoding="utf-8")
    receipt = stage._write_parent_receipt(
        tmp_path,
        lock_sha256="A" * 64,
        status="TIMEOUT_STAGE_LOCALIZED_ENGINEERING_ONLY",
        timed_out=True,
        child_exit_code=None,
        parent_wall_seconds=300.1,
        ephemeral_removed=True,
    )
    reject_outcome_fields(receipt)
    assert receipt["last_heartbeat"]["progress_index"] == 3
    assert receipt["full_replay_authorized"] is False
    assert receipt["v3_rerun_authorized"] is False
    assert receipt["heartbeat_sha256"] == sha256_file(heartbeat)


def test_prepare_output_dir_is_fresh_and_contained(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path.resolve()
    monkeypatch.setattr(stage, "REPO_ROOT", root)
    monkeypatch.setattr(stage, "EVIDENCE_ROOT", root)
    created = stage._prepare_output_dir(root / "fresh", "fresh")
    assert created.is_dir()
    with pytest.raises(IdentityContractError, match="fresh and absent"):
        stage._prepare_output_dir(root / "fresh", "fresh")


def test_safe_remove_ephemeral_requires_exact_locked_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path.resolve()
    monkeypatch.setattr(stage, "REPO_ROOT", root)
    monkeypatch.setattr(stage, "EVIDENCE_ROOT", root)
    target = root / "ephemeral"
    target.mkdir()
    (target / "artifact.tmp").write_text("x", encoding="utf-8")
    with pytest.raises(IdentityContractError, match="differs from lock"):
        stage._safe_remove_ephemeral(target, "other")
    assert target.exists()
    stage._safe_remove_ephemeral(target, "ephemeral")
    assert not target.exists()


def test_durable_output_contract_is_heartbeat_and_receipt_only() -> None:
    assert stage.EXPECTED_FILES == {"stage_heartbeat.jsonl", "stage_receipt.json"}
