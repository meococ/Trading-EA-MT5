from __future__ import annotations

import json
from pathlib import Path

import pytest

import run_t2_p3_identity_prefix_v2 as prefix
from t2_dedup_mirrors import IdentityContractError, sha256_file


def test_expected_prefix_packet_file_set_is_exact() -> None:
    assert len(prefix.EXPECTED_FILES) == 9
    assert "prefix_result.json" in prefix.EXPECTED_FILES
    assert "prefix_receipt.json" in prefix.EXPECTED_FILES
    assert "result.json" not in prefix.EXPECTED_FILES


def test_output_dir_must_match_lock_and_be_fresh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    expected = evidence / "probe"
    monkeypatch.setattr(prefix, "EVIDENCE_ROOT", evidence.resolve())
    monkeypatch.setattr(prefix, "REPO_ROOT", tmp_path.resolve())
    assert prefix._validate_output_dir(expected, "evidence/probe") == expected.resolve()
    expected.mkdir()
    with pytest.raises(IdentityContractError, match="fresh and absent"):
        prefix._validate_output_dir(expected, "evidence/probe")


def test_output_dir_rejects_different_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    monkeypatch.setattr(prefix, "EVIDENCE_ROOT", evidence.resolve())
    monkeypatch.setattr(prefix, "REPO_ROOT", tmp_path.resolve())
    with pytest.raises(IdentityContractError, match="differs from lock"):
        prefix._validate_output_dir(evidence / "other", "evidence/probe")


def test_verify_packet_rejects_missing_file(tmp_path: Path) -> None:
    (tmp_path / "prefix_result.json").write_text("{}", encoding="utf-8")
    with pytest.raises(IdentityContractError, match="exact output set"):
        prefix._verify_packet(tmp_path)


def test_verify_packet_accepts_engineering_only_minimal_packet(tmp_path: Path) -> None:
    artifact_names = prefix.EXPECTED_FILES - {"prefix_result.json", "prefix_receipt.json"}
    artifacts = {}
    for index, name in enumerate(sorted(artifact_names)):
        path = tmp_path / name
        path.write_text("", encoding="utf-8")
        artifacts[str(index)] = {"path": str(path), "sha256": sha256_file(path), "records": 0}
    result = {
        "schema_version": prefix.RESULT_SCHEMA,
        "authority": "ENGINEERING_PREFIX_IDENTITY_ONLY_NO_FULL_GATE_NO_ECONOMICS",
        "prefix_comparisons_are_fatal_gate_authority": False,
        "full_replay_authorized_by_this_packet": False,
        "source_field_contract": "IDENTITY_ONLY_NO_TRADE_RESULT_FIELDS",
        "economic_claim_authorized": False,
        "ea_build_or_mt5_authorized": False,
    }
    result_path = tmp_path / "prefix_result.json"
    result_path.write_text(json.dumps(result), encoding="utf-8")
    receipt = {
        "result_sha256": sha256_file(result_path),
        "artifacts": artifacts,
    }
    (tmp_path / "prefix_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    verified = prefix._verify_packet(tmp_path)
    assert verified["result_sha256"] == sha256_file(result_path)
