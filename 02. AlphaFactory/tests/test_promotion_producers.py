import csv
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
sys.path.insert(0, str(ANALYSIS))

from aligned_variant_evidence import load_aligned_variant_evidence  # noqa: E402
from cscv_pbo import aligned_cscv_pbo  # noqa: E402
from robustness_suite import matched_rerun_parameter_sensitivity  # noqa: E402
from walk_forward import optimization_aware_walk_forward  # noqa: E402
from white_reality_check import aligned_white_reality_check, white_reality_check  # noqa: E402
from unified_validation import _bind_variant_artifact, _load_json, _variant_artifact_binding  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _build_manifest(tmp_path: Path) -> Path:
    source_bytes = b"// frozen EA source\n"
    source_sha = hashlib.sha256(source_bytes).hexdigest().upper()
    hypothesis_id = "HYP-TEST-PROMOTION-001"
    prereg = tmp_path / "PREREG.md"
    prereg.write_text("frozen before outcomes\n", encoding="utf-8")
    variant_ids = ["baseline", "variant_a", "variant_b"]
    variant_rows = []
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for offset, variant_id in enumerate(variant_ids):
        folder = tmp_path / variant_id
        folder.mkdir()
        source_snapshot = folder / "source.mq5"
        source_snapshot.write_bytes(source_bytes)
        ex5_snapshot = folder / "expert.ex5"
        ex5_snapshot.write_bytes(b"compiled-fixture-" + variant_id.encode("ascii"))
        report = folder / "report.html"
        report.write_text(f"<html>{variant_id}</html>\n", encoding="utf-8")
        trades = folder / "trades.csv"
        with trades.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["exit_time", "net_r"])
            writer.writeheader()
            for day in range(72):
                base = -0.02 if day % 4 == 0 else 0.01
                value = base + (offset * 0.04)
                writer.writerow(
                    {
                        "exit_time": (start + timedelta(days=day)).isoformat(),
                        "net_r": value,
                    }
                )
        run_manifest = folder / "run_manifest.json"
        run_manifest.write_text(
            json.dumps(
                {
                    "schema_version": "alphafactory_run_manifest.v2",
                    "hypothesis_id": hypothesis_id,
                    "variant_id": variant_id,
                    "model": 0,
                    "source_sha256": source_sha,
                    "source_snapshot": source_snapshot.name,
                    "ex5_snapshot": ex5_snapshot.name,
                    "ex5_sha256": _sha(ex5_snapshot),
                    "report_path": report.name,
                    "report_sha256": _sha(report),
                }
            ),
            encoding="utf-8",
        )
        variant_rows.append(
            {
                "variant_id": variant_id,
                "trades_csv": {"path": str(trades.relative_to(tmp_path)), "sha256": _sha(trades)},
                "run_manifest": {
                    "path": str(run_manifest.relative_to(tmp_path)),
                    "sha256": _sha(run_manifest),
                },
            }
        )
    manifest = tmp_path / "variant_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "alphafactory_aligned_variant_manifest.v1",
                "hypothesis_id": hypothesis_id,
                "source_sha256": source_sha,
                "frozen_pre_outcome": True,
                "full_tried_family": True,
                "selection_rule_frozen": True,
                "value_semantics": "net_r",
                "time_column": "exit_time",
                "value_column": "net_r",
                "preregistration": {"path": prereg.name, "sha256": _sha(prereg)},
                "expected_variant_ids": variant_ids,
                "baseline_variant_id": "baseline",
                "robustness_variant_ids": variant_ids,
                "minimum_trades_per_variant": 50,
                "minimum_variant_mean_net_r": -0.01,
                "minimum_robustness_pass_ratio": 0.6,
                "analysis_settings": {
                    "wfa_windows": 5,
                    "cscv_slices": 8,
                    "cscv_max_combinations": 200,
                    "white_reality_bootstrap": 300,
                    "white_reality_block_length": 5,
                    "random_seed": 1729,
                },
                "variants": variant_rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest


def test_promotion_producers_require_and_use_frozen_aligned_family(tmp_path):
    manifest = _build_manifest(tmp_path)
    evidence = load_aligned_variant_evidence(manifest)

    wfa = optimization_aware_walk_forward(manifest)
    robustness = matched_rerun_parameter_sensitivity(manifest)
    pbo = aligned_cscv_pbo(manifest)
    white = aligned_white_reality_check(manifest)

    assert wfa["analysis_kind"] == "optimization_aware_walk_forward"
    assert wfa["promotion_eligible"] is True
    assert robustness["analysis_kind"] == "matched_ea_rerun_parameter_sensitivity"
    assert robustness["promotion_eligible"] is True
    assert pbo["analysis_kind"] == "preregistered_aligned_variant_matrix_cscv"
    assert pbo["promotion_eligible"] is True
    assert pbo["combos_used"] > 0
    assert white["analysis_kind"] == "preregistered_aligned_white_reality_check"
    assert white["promotion_eligible"] is True
    assert white["bootstrap_dependence"] == "same moving-block indices across all variants"


def test_manifest_hash_tamper_fails_closed(tmp_path):
    manifest = _build_manifest(tmp_path)
    with (tmp_path / "variant_a" / "trades.csv").open("a", encoding="utf-8") as handle:
        handle.write("2026-01-01T00:00:00+00:00,99\n")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        load_aligned_variant_evidence(manifest)


def test_undeclared_variant_csv_fails_family_closure(tmp_path):
    manifest = _build_manifest(tmp_path)
    (tmp_path / "posthoc_rescue.csv").write_text("exit_time,net_r\n", encoding="utf-8")
    with pytest.raises(ValueError, match="CSV closure mismatch"):
        load_aligned_variant_evidence(manifest)


def test_legacy_variant_producers_remain_diagnostic():
    legacy = {"a": [0.1, -0.05, 0.2], "b": [0.02, -0.01, 0.03]}
    white = white_reality_check(legacy, n_boot=20, metric="expectancy", seed=42)
    assert white.get("promotion_eligible") is not True


def test_unified_binding_preserves_only_verified_promotion_output(tmp_path):
    variants_dir = tmp_path / "variants"
    variants_dir.mkdir()
    variant_manifest = _build_manifest(variants_dir)
    report_dir = tmp_path / "run"
    report_dir.mkdir()
    report = report_dir / "report.html"
    report.write_text("<html>fixture</html>\n", encoding="utf-8")
    current_manifest = {
        "run_id": "RUN-PROMOTION-001",
        "hypothesis_id": "HYP-TEST-PROMOTION-001",
        "source_sha256": json.loads(variant_manifest.read_text(encoding="utf-8"))["source_sha256"],
    }
    out_dir = tmp_path / "analysis"
    out_dir.mkdir()
    artifact = out_dir / "cscv_pbo.json"
    artifact.write_text(json.dumps(aligned_cscv_pbo(variant_manifest)), encoding="utf-8")

    _bind_variant_artifact(
        artifact,
        schema_version="alphafactory_cscv_pbo.v1",
        variants_dir=variants_dir,
        report_path=report,
        manifest=current_manifest,
    )
    payload = _load_json(artifact)
    bound, details = _variant_artifact_binding(
        payload,
        expected_schema="alphafactory_cscv_pbo.v1",
        variants_dir=variants_dir,
        report_path=report,
        manifest=current_manifest,
    )
    assert payload["promotion_eligible"] is True
    assert payload["analysis_kind"] == "preregistered_aligned_variant_matrix_cscv"
    assert bound is True, details
