from __future__ import annotations

import json
from pathlib import Path

import pytest

import run_t2_p3_dedup_v2 as timing
from t2_dedup_mirrors import IdentityContractError


def worker_payload(*, grammar_seconds: float = 10.0) -> dict[str, object]:
    return {
        "source_rows": timing.BOUND_D7_STAGE0_RECORD_COUNT,
        "prefix_bars": 50_000,
        "load_wall_seconds": 4.0,
        "load_cpu_seconds": 3.5,
        "grammar_wall_seconds": grammar_seconds,
        "grammar_cpu_seconds": max(0.0, grammar_seconds - 0.5),
        "total_wall_seconds": grammar_seconds + 4.0,
        "total_cpu_seconds": grammar_seconds + 3.0,
        "rss_start_bytes": 100,
        "rss_after_load_bytes": 200,
        "rss_after_grammar_bytes": 220,
    }


def probe_contract() -> dict[str, object]:
    return {
        "max_wall_seconds": 300,
        "min_bars_per_second": 500,
        "max_projected_full_wall_seconds": 1800,
    }


def test_worker_payload_accepts_timing_only_fields() -> None:
    assert timing._validate_worker_payload(worker_payload())["prefix_bars"] == 50_000


def test_worker_payload_rejects_identity_count_leak() -> None:
    payload = worker_payload()
    payload["identity_count"] = 1
    with pytest.raises(IdentityContractError, match="exact keys"):
        timing._validate_worker_payload(payload)


def test_timing_gate_passes_fast_prefix() -> None:
    result = timing._evaluate_timing(worker_payload(grammar_seconds=10.0), probe_contract())
    assert result["pass"] is True
    assert result["gates"] == {
        "worker_wall_within_limit": True,
        "bars_per_second_at_least_minimum": True,
        "projected_full_wall_within_limit": True,
    }


def test_timing_gate_fails_slow_prefix_without_threshold_rescue() -> None:
    result = timing._evaluate_timing(worker_payload(grammar_seconds=200.0), probe_contract())
    assert result["pass"] is False
    assert result["gates"]["bars_per_second_at_least_minimum"] is False
    assert result["gates"]["projected_full_wall_within_limit"] is False


def test_atomic_receipt_is_output_exclusive_and_no_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    monkeypatch.setattr(timing, "EVIDENCE_ROOT", evidence.resolve())
    output = evidence / "probe_001"
    path = timing._atomic_write_receipt(output, {"schema_version": timing.RECEIPT_SCHEMA})
    assert path.name == timing.ALLOWED_OUTPUT_NAME
    assert [item.name for item in output.iterdir()] == [timing.ALLOWED_OUTPUT_NAME]
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == timing.RECEIPT_SCHEMA
    with pytest.raises(IdentityContractError, match="fresh and absent"):
        timing._atomic_write_receipt(output, {"schema_version": timing.RECEIPT_SCHEMA})


def test_output_must_stay_under_package_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    monkeypatch.setattr(timing, "EVIDENCE_ROOT", evidence.resolve())
    with pytest.raises(IdentityContractError, match="evidence root"):
        timing._validate_output_dir(tmp_path / "outside")
