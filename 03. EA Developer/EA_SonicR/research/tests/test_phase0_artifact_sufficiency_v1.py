from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


RESEARCH_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
SPEC_PATH = (
    RESEARCH_ROOT
    / "preflight"
    / "20260711_PHASE0_ARTIFACT_SUFFICIENCY_SPEC_V1.json"
)
RESULT_PATH = (
    RESEARCH_ROOT / "preflight" / "20260711_PHASE0_ARTIFACT_SUFFICIENCY_V1.json"
)
ATTESTATION_PATH = (
    RESEARCH_ROOT
    / "preflight"
    / "20260711_PHASE0_COORDINATION_CONTAMINATION_ATTESTATION_V1.json"
)
BUILDER_PATH = (
    RESEARCH_ROOT / "analyzers" / "build_phase0_artifact_sufficiency_v1.py"
)


def _load_builder():
    module_spec = importlib.util.spec_from_file_location(
        "build_phase0_artifact_sufficiency_v1", BUILDER_PATH
    )
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def _load_spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


class ExplodingFileSystem:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def _explode(self, operation: str, path: Path):
        self.calls.append((operation, path.as_posix()))
        raise AssertionError("candidate filesystem touched before spec rejection")

    def is_file(self, path: Path) -> bool:
        return self._explode("is_file", path)

    def inspect_json_and_sha256(self, path: Path):
        return self._explode("inspect_json_and_sha256", path)

    def inspect_header_and_sha256(self, path: Path, max_bytes: int):
        return self._explode("inspect_header_and_sha256", path)

    def sha256(self, path: Path) -> str:
        return self._explode("sha256", path)


class RecordingFileSystem:
    def __init__(self, delegate) -> None:
        self.delegate = delegate
        self.calls: list[tuple[str, str]] = []

    def _record(self, operation: str, path: Path) -> None:
        self.calls.append((operation, path.as_posix()))

    def is_file(self, path: Path) -> bool:
        self._record("is_file", path)
        return self.delegate.is_file(path)

    def inspect_json_and_sha256(self, path: Path):
        self._record("inspect_json_and_sha256", path)
        return self.delegate.inspect_json_and_sha256(path)

    def inspect_header_and_sha256(self, path: Path, max_bytes: int):
        self._record("inspect_header_and_sha256", path)
        return self.delegate.inspect_header_and_sha256(path, max_bytes)

    def sha256(self, path: Path) -> str:
        self._record("sha256", path)
        return self.delegate.sha256(path)


def test_spec_freezes_only_the_exact_candidate_lists() -> None:
    spec = _load_spec()
    probes = {probe["probe_id"]: probe for probe in spec["probes"]}

    assert spec["policy"]["candidate_selection"] == "EXACT_LIST_ONLY"
    assert spec["policy"]["auto_discovery"] is False
    assert probes["PROBE_A"]["hypothesis_id"] == "HYP-PORTFOLIO-COMPOSE-001"
    assert probes["PROBE_A"]["candidate_runs"] == []
    assert (
        probes["PROBE_A"]["empty_candidate_reason"]
        == "BLOCKED_PROBE_A_EXACT_UNIVERSE_NOT_FROZEN"
    )
    assert probes["PROBE_B"]["hypothesis_id"] == "HYP-SB-WEEKEND-FLAT-001"
    assert probes["PROBE_B"]["candidate_runs"] == [
        "EA_SilverBullet/20260628_131343"
    ]


def test_spec_binds_a_reviewed_coordination_attestation() -> None:
    spec = _load_spec()
    attestation = spec["coordination_session_attestation"]

    assert attestation["path"].endswith(
        "20260711_PHASE0_COORDINATION_CONTAMINATION_ATTESTATION_V1.json"
    )
    assert len(attestation["sha256"]) == 64
    assert hashlib.sha256(ATTESTATION_PATH.read_bytes()).hexdigest() == attestation[
        "sha256"
    ]


def test_frozen_spec_rejects_safe_shape_redirect_before_filesystem() -> None:
    builder = _load_builder()
    spec = copy.deepcopy(_load_spec())
    spec["run_root"] = "00. Old File"
    spec["probes"][1]["donor"]["identity_manifests"][0]["path"] = (
        "analysis/logs/results.json"
    )
    spec["probes"][1]["donor"]["trade_header"]["path"] = (
        "analysis/logs/outcomes.csv"
    )
    spec["probes"][1]["donor"]["required_hash_bindings"] = spec["probes"][1][
        "donor"
    ]["required_hash_bindings"][:1]
    filesystem = ExplodingFileSystem()

    with pytest.raises(builder.SpecValidationError, match="frozen spec"):
        builder.build_result(spec, WORKSPACE_ROOT, filesystem=filesystem)

    assert filesystem.calls == []


@pytest.mark.parametrize("unsafe", ["C:/escape.json", "file.json:outcome", "//server/share"])
def test_windows_drive_unc_and_ads_paths_are_rejected(unsafe: str) -> None:
    builder = _load_builder()

    with pytest.raises(builder.SpecValidationError, match="exact relative path"):
        builder._validate_exact_relative_path(unsafe, "unsafe")


def test_atomic_snapshot_api_is_required_for_parsed_artifacts() -> None:
    builder = _load_builder()

    assert hasattr(builder.LocalFileSystem, "inspect_json_and_sha256")
    assert hasattr(builder.LocalFileSystem, "inspect_header_and_sha256")


def test_containment_rejects_resolved_reparse_escape(
    tmp_path: Path, monkeypatch
) -> None:
    builder = _load_builder()
    root = (tmp_path / "root").resolve()
    outside = (tmp_path / "outside").resolve()
    root.mkdir()
    outside.mkdir()
    lexical = root / "link" / "secret.json"
    resolved_outside = outside / "secret.json"
    original_resolve = Path.resolve

    def fake_resolve(self, strict=False):
        if builder._path_key(self) == builder._path_key(lexical):
            return resolved_outside
        return original_resolve(self, strict=strict)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    with pytest.raises(builder.ArtifactInspectionError, match="escapes"):
        builder._resolve_contained_path(root, "link/secret.json")


@pytest.mark.parametrize(
    "mutation",
    [
        {"outcome_selector": {"path": "analysis/enhanced_summary.json"}},
        {"metric_selector": "profit_factor"},
        {"row_filter": "is_final_close == 1"},
        {"best_run": "EA_SilverBullet/20260628_131343"},
        {"rank_by": "pf"},
        {"top_n": 1},
        {"minimum_trades": 30},
    ],
)
def test_outcome_selectors_are_rejected_before_candidate_filesystem(
    mutation: dict,
) -> None:
    builder = _load_builder()
    spec = copy.deepcopy(_load_spec())
    spec["probes"][1].update(mutation)
    filesystem = ExplodingFileSystem()

    with pytest.raises(builder.SpecValidationError, match="forbidden selector"):
        builder.build_result(spec, WORKSPACE_ROOT, filesystem=filesystem)

    assert filesystem.calls == []


def test_wildcard_candidate_is_rejected_before_candidate_filesystem() -> None:
    builder = _load_builder()
    spec = copy.deepcopy(_load_spec())
    spec["probes"][1]["candidate_runs"] = ["EA_SilverBullet/*"]
    filesystem = ExplodingFileSystem()

    with pytest.raises(builder.SpecValidationError, match="exact relative path"):
        builder.build_result(spec, WORKSPACE_ROOT, filesystem=filesystem)

    assert filesystem.calls == []


def test_current_result_is_blocked_for_both_probes_without_outcome_access() -> None:
    builder = _load_builder()
    result = builder.build_result(_load_spec(), WORKSPACE_ROOT)
    probes = {probe["probe_id"]: probe for probe in result["probes"]}

    assert result["status"] == "BLOCKED"
    assert result["producer_semantic_outcome_accessed"] is False
    attestation = result["coordination_session_attestation"]
    assert attestation["status"] == "BLOCKED"
    assert attestation["review_status"] == "CONTAMINATED"
    assert attestation["session_id"] == "019f515e-af25-7303-b3e0-69ee6d3a6d9f"
    assert attestation["input_sha256"] == _load_spec()[
        "coordination_session_attestation"
    ]["sha256"]
    assert attestation["producer_semantic_outcome_accessed"] is False
    assert attestation["outcome_values_used"] is False
    assert attestation["clearance_effect"] == (
        "BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW"
    )
    assert probes["PROBE_A"]["status"] == "BLOCKED"
    assert probes["PROBE_A"]["reasons"] == [
        "BLOCKED_PROBE_A_EXACT_UNIVERSE_NOT_FROZEN"
    ]
    assert probes["PROBE_A"]["producer_semantic_outcome_accessed"] is False
    assert probes["PROBE_B"]["status"] == "BLOCKED"
    assert probes["PROBE_B"]["producer_semantic_outcome_accessed"] is False
    assert set(probes["PROBE_B"]["reasons"]) == {
        "BLOCKED_PROBE_B_PRICE_PATH_MANIFEST_NOT_HASH_BOUND",
        "BLOCKED_PROBE_B_SIDE_AWARE_BID_NOT_HASH_BOUND",
        "BLOCKED_PROBE_B_SIDE_AWARE_ASK_NOT_HASH_BOUND",
        "BLOCKED_PROBE_B_TIMEZONE_NOT_HASH_BOUND",
        "BLOCKED_PROBE_B_SESSION_NOT_HASH_BOUND",
        "BLOCKED_PROBE_B_SYMBOL_CONTRACT_NOT_HASH_BOUND",
        "BLOCKED_PROBE_B_RESEARCH_COST_PROVENANCE_NOT_HASH_BOUND",
    }

    forbidden_output_keys = {
        "pf",
        "net",
        "trades",
        "cadence",
        "correlation",
        "portfolio_pnl",
        "replayed_exit",
        "best",
        "rank",
        "top_n",
    }

    def walk_keys(value):
        if isinstance(value, dict):
            for key, nested in value.items():
                yield key.lower()
                yield from walk_keys(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from walk_keys(nested)

    assert forbidden_output_keys.isdisjoint(set(walk_keys(result)))


def test_trade_artifact_is_only_hashed_and_header_inspected() -> None:
    builder = _load_builder()
    filesystem = RecordingFileSystem(builder.LocalFileSystem())

    builder.build_result(_load_spec(), WORKSPACE_ROOT, filesystem=filesystem)

    trade_suffix = (
        "EA_SilverBullet/20260628_131343/analysis/logs/"
        "USDJPY_20260325_PX6_Trades_20210101_000000_196670171.csv"
    )
    trade_operations = [
        operation
        for operation, path in filesystem.calls
        if path.endswith(trade_suffix)
    ]
    assert "inspect_json_and_sha256" not in trade_operations
    assert trade_operations == ["is_file", "inspect_header_and_sha256"]

    inspected_paths = "\n".join(path.lower() for _, path in filesystem.calls)
    assert "enhanced_summary" not in inspected_paths
    assert "report.html" not in inspected_paths
    assert "trades_summary" not in inspected_paths
    assert "runmeta" not in inspected_paths


def test_local_header_snapshot_retains_only_header_while_hashing_full_file(
    tmp_path: Path,
) -> None:
    builder = _load_builder()
    content = b"header_a,header_b\nOUTCOME_ROW_HASHED_BUT_NOT_RETAINED"
    fixture = tmp_path / "fixture.csv"
    fixture.write_bytes(content)

    header, digest = builder.LocalFileSystem().inspect_header_and_sha256(
        fixture, 4096
    )

    assert header == b"header_a,header_b"
    assert digest == hashlib.sha256(content).hexdigest()


def test_identity_manifest_is_parsed_and_hashed_from_one_snapshot() -> None:
    builder = _load_builder()
    filesystem = RecordingFileSystem(builder.LocalFileSystem())

    builder.build_result(_load_spec(), WORKSPACE_ROOT, filesystem=filesystem)

    manifest_suffix = "EA_SilverBullet/20260628_131343/run_manifest.json"
    operations = [
        operation
        for operation, path in filesystem.calls
        if path.endswith(manifest_suffix)
    ]
    assert operations == ["is_file", "inspect_json_and_sha256"]


def test_result_is_deterministic_and_matches_checked_in_artifact() -> None:
    builder = _load_builder()
    spec = _load_spec()

    first = builder.build_result(spec, WORKSPACE_ROOT)
    second = builder.build_result(spec, WORKSPACE_ROOT)

    assert first == second
    assert builder.render_result(first) == builder.render_result(second)
    assert json.loads(RESULT_PATH.read_text(encoding="utf-8")) == first
