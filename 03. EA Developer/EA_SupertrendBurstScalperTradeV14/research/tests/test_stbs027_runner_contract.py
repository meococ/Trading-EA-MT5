from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "02. AlphaFactory/tools/run_stbs027_model0_baseline.ps1"
BASE = ROOT / "02. AlphaFactory/tools/research_loop_engine.ps1"
ALPHA = ROOT / "02. AlphaFactory/alpha.ps1"
AUDITOR = ROOT / "02. AlphaFactory/tools/audit_mql5_nonrepaint.py"
SOURCE = PACKAGE / "EA_SupertrendBurstScalperTradeV14.mq5"
STATIC_MANIFEST = PACKAGE / "HYP-STBS-XAUUSD-M15-027_NONREPAINT_MANIFEST.json"
BUILDER = PACKAGE / "research/build_stbs027_task_packet.py"
REGISTRY = ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"


def exact_parent_terminal_raw() -> str:
    for raw in reversed(REGISTRY.read_text(encoding="utf-8").splitlines()):
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("hypothesis_id") == "HYP-STBS-XAUUSD-M15-025":
            return raw
    raise AssertionError("HYP025 terminal row is absent")


PARENT_TERMINAL_RAW = exact_parent_terminal_raw()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_builder_module():
    spec = importlib.util.spec_from_file_location("stbs027_packet_builder", BUILDER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def packet_only_probe(module) -> dict:
    return {
        "hypothesis_id": module.HYPOTHESIS_ID,
        "parent_candidate": "HYP-STBS-XAUUSD-M15-025",
        "state": "probe",
        "source_hash": module.EXPECTED_SOURCE_SHA256,
        "prereg_sha256": module.EXPECTED_PREREG_SHA256,
        "verdict": "FROZEN_HYP027_PACKET_BUILDER_SEMANTIC_AUTHORITY",
        "run_ids": [],
        "metrics": dict(module.PROBE_ZERO_METRICS),
        "validation": {
            "authority": module.PACKET_ONLY_AUTHORITY,
            "packet_build_authorized": True,
            "packet_build_attempt_id": module.PACKET_ATTEMPT_ID,
            "packet_build_attempt_limit": 1,
            "mt5_attempt_id": module.MT5_ATTEMPT_ID,
            "mt5_attempt_limit": 1,
            "reviewed_task_packet_builder_path": module.repo_relative(BUILDER),
            "reviewed_task_packet_builder_sha256": sha256(BUILDER),
            "exact_outer_hypothesis_id": "HYP-STBS-XAUUSD-M15-027",
            "exact_inner_mql_identity": "HYP-STBS-XAUUSD-M15-027",
            "exact_ea_name": "EA_SupertrendBurstScalperTradeV14",
            "parent_hyp025_terminal_row_sha256": module.EXPECTED_PARENT_TERMINAL_ROW_SHA256,
            "parent_hyp025_terminal_verdict": module.EXPECTED_PARENT_TERMINAL_VERDICT,
            "parent_hyp025_failure_path": module.repo_relative(module.PARENT_FAILURE_PACKET),
            "parent_hyp025_failure_sha256": module.EXPECTED_PARENT_FAILURE_PACKET_SHA256,
            "parent_hyp025_post_failure_review_path": module.repo_relative(module.PARENT_POST_FAILURE_REVIEW),
            "parent_hyp025_post_failure_review_sha256": module.EXPECTED_PARENT_POST_FAILURE_REVIEW_SHA256,
            "journal_budget_tester_projection_path": module.repo_relative(module.TESTER_NO_SPAM_PROJECTION),
            "journal_budget_tester_projection_sha256": module.EXPECTED_TESTER_PROJECTION_SHA256,
            "journal_budget_tester_projection_bytes": module.EXPECTED_TESTER_PROJECTION_BYTES,
            "journal_budget_agent_projection_path": module.repo_relative(module.AGENT_NO_SPAM_PROJECTION),
            "journal_budget_agent_projection_sha256": module.EXPECTED_AGENT_PROJECTION_SHA256,
            "journal_budget_agent_projection_bytes": module.EXPECTED_AGENT_PROJECTION_BYTES,
            "journal_budget_addendum_path": module.repo_relative(module.JOURNAL_BUDGET_ADDENDUM),
            "journal_budget_addendum_sha256": module.EXPECTED_JOURNAL_BUDGET_ADDENDUM_SHA256,
            "pre_execution_harness_addendum_path": module.repo_relative(module.PRE_EXECUTION_HARNESS_ADDENDUM),
            "pre_execution_harness_addendum_sha256": module.EXPECTED_PRE_EXECUTION_HARNESS_ADDENDUM_SHA256,
            "independent_pre_run_review_path": module.repo_relative(module.INDEPENDENT_PRE_PROBE_REVIEW),
            "independent_pre_run_review_sha256": module.EXPECTED_INDEPENDENT_PRE_PROBE_REVIEW_SHA256,
            "bounded_diff_proof_path": module.repo_relative(module.BOUNDED_DIFF_PROOF),
            "bounded_diff_proof_sha256": module.EXPECTED_BOUNDED_DIFF_PROOF_SHA256,
            "source_contract_test_path": module.repo_relative(module.COMPACT_TELEMETRY_TEST),
            "source_contract_test_sha256": module.EXPECTED_COMPACT_TELEMETRY_TEST_SHA256,
            "reserved_post_packet_review_path": module.repo_relative(module.RESERVED_POST_PACKET_REVIEW),
            "reserved_post_packet_review_placeholder_sha256": module.EXPECTED_RESERVED_POST_PACKET_REVIEW_SHA256,
            **{name: False for name in module.PROBE_FALSE_FIELDS},
        },
    }


def write_registry(path: Path, row: dict) -> None:
    path.write_text(
        PARENT_TERMINAL_RAW + "\n" + json.dumps(row, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def test_shared_alphafactory_and_base_runner_are_frozen():
    assert sha256(ALPHA) == "55B3B0641BD843B1B1D9620086180CDBC180E9FA2865B08090ED89DF92043571"
    assert sha256(BASE) == "6E205874477A79EB97EE56967B81FA3675FB25AD784D00D989BBD077DA837550"


def test_runner_is_hyp027_only_and_preserves_original_run_manifest():
    text = RUNNER.read_text(encoding="utf-8")
    assert "$EaName -cne 'EA_SupertrendBurstScalperTradeV14'" in text
    assert "$HypothesisId -cne 'HYP-STBS-XAUUSD-M15-027'" in text
    assert "$From -cne '2005.01.01' -or $To -cne '2023.01.01'" in text
    assert "$Model -ne 0" in text and "$TimeoutSec -ne 900" in text
    assert "$TelemetryTier -cne 'trade-only'" in text
    assert "nonrepaint_run_manifest.json" in text
    assert "New-Hyp027NonRepaintAuditManifest $runManifestPath $runManifestShaForAudit $analysisDir" in text
    assert "--manifest $nonRepaintRunManifestPath" in text
    assert "Write-JsonAtomically $run $RunManifestPath" not in text
    assert "& $alphaPs1 backtest" in text
    assert "exact HYP027 outer/inner identity contract" in text


def test_runner_binds_exact_static_provenance_authority():
    text = RUNNER.read_text(encoding="utf-8")
    assert "958B4678772D2FFEF8DAC9A22ADCACEFCD0D868862180D02974C0C7433138E63" in text
    assert "D94C9745A0349D946C242B72B2F230B03E43F7E6334711D9ACDB2F89A00DA1E0" in text
    assert "F60A9469D1A6FE2D62F5E83DECB953862C68AF9E3D154EA0AE488C072B4A4DA4" in text
    assert "366D70F0C6FAF02F85B4819E7305CD1BD271BA6A78B4789CF0DCDF2FB651E360" in text
    assert "$hyp027CopyTimeLine = 678" in text
    assert "single exact DATA_EPOCH_D0 CopyTime first-date proof; no decision or outcome access" in text
    assert "original_run_manifest_sha256 = $RunManifestSha256" in text
    assert text.count("changed while") >= 3
    manifest = json.loads(STATIC_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["nondecision_provenance_copytime_authorized"] is True
    assert manifest["source_sha256"] == sha256(SOURCE)


def test_derived_manifest_passes_only_the_exact_copytime_provenance(tmp_path: Path):
    snapshot_root = tmp_path / "snapshot"
    snapshot_root.mkdir()
    snapshot_source = snapshot_root / SOURCE.name
    shutil.copyfile(SOURCE, snapshot_source)
    base = {
        "hypothesis_id": "HYP-STBS-XAUUSD-M15-027",
        "run_id": "STBS027-ADAPTER-TEST",
        "snapshot_root": str(snapshot_root.resolve()),
        "source_snapshot": str(snapshot_source.resolve()),
        "source_sha256": sha256(snapshot_source),
        "include_snapshots": [],
    }
    manifest = tmp_path / "manifest.json"
    out = tmp_path / "audit.json"
    manifest.write_text(json.dumps(base), encoding="utf-8")
    rejected = subprocess.run(
        [sys.executable, str(AUDITOR), "--manifest", str(manifest), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert rejected.returncode == 1
    assert json.loads(out.read_text(encoding="utf-8"))["findings"] == [
        {
            "path": str(snapshot_source.resolve()),
                "line": 678,
            "rule": "unproven_closed_bar_shift",
            "function": "CopyTime",
            "shift_expression": "copytime_from",
        }
    ]

    base["nondecision_provenance_copytime_authorized"] = True
    manifest.write_text(json.dumps(base), encoding="utf-8")
    accepted = subprocess.run(
        [sys.executable, str(AUDITOR), "--manifest", str(manifest), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    audit = json.loads(out.read_text(encoding="utf-8"))
    assert audit["status"] == "PASS"
    assert audit["manifest"] == str(manifest.resolve())
    assert audit["manifest_sha256"] == sha256(manifest)
    assert audit["collection_authority_verified"] is False
    assert audit["audited_files"] == [
        {"path": str(snapshot_source.resolve()), "sha256": sha256(snapshot_source)}
    ]
    assert audit["findings"] == []
    assert audit["allowed_new_bar_gates"] == [
        {
            "path": str(snapshot_source.resolve()),
            "line": 678,
            "rule": "collection_first_date_copytime",
            "function": "CopyTime",
            "disposition": "allowed_collection_provenance_read",
        }
    ]


def test_runner_fail_closes_the_full_runtime_nonrepaint_semantics():
    text = RUNNER.read_text(encoding="utf-8")
    for needle in (
        "manifest_sha256 -cne $nonRepaintRunManifestShaForAudit",
        "collection_authority_verified -ne $false",
        "$auditedFiles.Count -ne 1",
        "$findings.Count -ne 0",
        "$allowedGates.Count -ne 1",
        "[int]$allowedGates[0].line -ne $hyp027CopyTimeLine",
        "[string]$allowedGates[0].rule -cne 'collection_first_date_copytime'",
        "[string]$allowedGates[0].function -cne 'CopyTime'",
        "[string]$allowedGates[0].disposition -cne 'allowed_collection_provenance_read'",
        "non-repaint auditor, derivative manifest or audit artifact drifted during validation",
        "reviewed_nonrepaint_auditor_sha256",
        "hyp027_nonrepaint_auditor",
    ):
        assert needle in text


def test_runner_postclaim_validates_and_receipt_binds_packet_attempt_chain():
    text = RUNNER.read_text(encoding="utf-8")
    for needle in (
        "function Assert-Hyp027PacketBuildChain",
        "packet_build_attempts_consumed') -ne 1",
        "packet_build_attempt_start_path",
        "packet_build_attempt_start_sha256",
        "packet_build_attempt_terminal_path",
        "packet_build_attempt_terminal_sha256",
        "[string]$terminal.status -cne 'COMPLETE'",
        "$null -ne $terminal.error",
        "[string]$terminal.attempt_started_sha256 -cne $startSha",
        "[string]$terminal.packet_sha256 -cne [string]$PacketResult.PacketSha256",
        "$startAt -le $terminalAt -and $terminalAt -le $authorityAt -and $authorityAt -le $launchAt",
        "Enter-ImmutableEvidenceReadLocks $packetChainPaths $evidenceReadLocks",
        "Assert-Hyp027PacketBuildChain $contract $packetResult $launchClaimRecord",
        "hyp027_packet_attempt_start",
        "hyp027_packet_attempt_terminal",
        "hyp027_gitignore",
    ):
        assert needle in text
    claim = text.index(
        "$economicAttemptRecord = New-Model0EconomicLaunchClaim $contract $binding $packetResult"
    )
    validate = text.index(
        "Assert-Hyp027PacketBuildChain $contract $packetResult $launchClaimRecord",
        claim,
    )
    assert claim < validate


def test_reserved_review_is_same_path_claimed_then_final_and_receipt_bound():
    module = load_builder_module()
    text = RUNNER.read_text(encoding="utf-8")
    builder_text = BUILDER.read_text(encoding="utf-8")
    assert sha256(module.RESERVED_POST_PACKET_REVIEW) == (
        module.EXPECTED_RESERVED_POST_PACKET_REVIEW_SHA256
    )
    assert module.RESERVED_POST_PACKET_REVIEW.read_text(encoding="utf-8").splitlines() == [
        "schema_version: stbs027_post_packet_review.v1",
        "hypothesis_id: HYP-STBS-XAUUSD-M15-027",
        "packet_sha256: RESERVED_NOT_AUTHORITY",
        "packet_terminal_sha256: RESERVED_NOT_AUTHORITY",
        "verdict: RESERVED_NOT_AUTHORITY",
    ]
    for needle in (
        "git_status.count(RESERVED_POST_PACKET_REVIEW_STATUS_LINE) != 1",
        '"reserved_post_packet_review_path"',
        '"reserved_post_packet_review_placeholder_sha256"',
        '"reserved_post_packet_review_status_line"',
    ):
        assert needle in builder_text
    for needle in (
        "independent_post_packet_review_path",
        "independent_post_packet_review_sha256",
        "schema_version: stbs027_post_packet_review.v1",
        "packet_sha256: {0}",
        "packet_terminal_sha256: {0}",
        "verdict: PASS_SCREENED_AUTHORITY",
        "$reviewExact = $finalReviewLines.Count -eq $expectedReviewLines.Count",
        "hyp027_independent_post_packet_review",
        "Enter-ImmutableEvidenceReadLocks $packetChainPaths $evidenceReadLocks",
    ):
        assert needle in text
    claim = text.index(
        "$economicAttemptRecord = New-Model0EconomicLaunchClaim $contract $binding $packetResult"
    )
    validation_call = text.index(
        "Assert-Hyp027PacketBuildChain $contract $packetResult $launchClaimRecord",
        claim,
    )
    assert claim < validation_call


@pytest.mark.parametrize(
    "mutator",
    [
        lambda lines: lines[:-1] + ["verdict: FAIL"],
        lambda lines: lines + ["verdict: PASS_SCREENED_AUTHORITY"],
        lambda lines: lines[:-1]
        + ["verdict: FAIL - PASS_SCREENED_AUTHORITY is not granted"],
        lambda lines: lines[:2] + ["packet_sha256: " + "0" * 64] + lines[3:],
        lambda lines: lines[:3]
        + ["packet_terminal_sha256: " + "0" * 64]
        + lines[4:],
        lambda lines: ["status: PENDING", *lines],
    ],
)
def test_exact_post_packet_review_schema_rejects_contradiction_or_drift(mutator):
    packet_sha = "A" * 64
    terminal_sha = "B" * 64
    expected = [
        "schema_version: stbs027_post_packet_review.v1",
        "hypothesis_id: HYP-STBS-XAUUSD-M15-027",
        f"packet_sha256: {packet_sha}",
        f"packet_terminal_sha256: {terminal_sha}",
        "verdict: PASS_SCREENED_AUTHORITY",
    ]

    def accepted(lines: list[str]) -> bool:
        return lines == expected

    assert accepted(expected)
    assert not accepted(mutator(expected.copy()))


def test_packet_builder_rechecks_placeholder_and_pathset_before_complete():
    text = BUILDER.read_text(encoding="utf-8")
    packet_hash = text.index("packet_sha256 = sha256_file(OUTPUT)")
    placeholder_rehash = text.index(
        "if sha256_file(RESERVED_POST_PACKET_REVIEW) != EXPECTED_RESERVED_POST_PACKET_REVIEW_SHA256",
        packet_hash,
    )
    pathset_recheck = text.index("terminal_git_status = git(", placeholder_rehash)
    terminal = text.index('status="COMPLETE"', pathset_recheck)
    assert packet_hash < placeholder_rehash < pathset_recheck < terminal


def test_packet_builder_freezes_parent_and_journal_budget_evidence():
    module = load_builder_module()
    expected = {
        module.PARENT_FAILURE_PACKET: module.EXPECTED_PARENT_FAILURE_PACKET_SHA256,
        module.PARENT_POST_FAILURE_REVIEW: module.EXPECTED_PARENT_POST_FAILURE_REVIEW_SHA256,
        module.TESTER_NO_SPAM_PROJECTION: module.EXPECTED_TESTER_PROJECTION_SHA256,
        module.AGENT_NO_SPAM_PROJECTION: module.EXPECTED_AGENT_PROJECTION_SHA256,
        module.JOURNAL_BUDGET_ADDENDUM: module.EXPECTED_JOURNAL_BUDGET_ADDENDUM_SHA256,
        module.PRE_EXECUTION_HARNESS_ADDENDUM: module.EXPECTED_PRE_EXECUTION_HARNESS_ADDENDUM_SHA256,
        module.INDEPENDENT_PRE_PROBE_REVIEW: module.EXPECTED_INDEPENDENT_PRE_PROBE_REVIEW_SHA256,
        module.BOUNDED_DIFF_PROOF: module.EXPECTED_BOUNDED_DIFF_PROOF_SHA256,
        module.COMPACT_TELEMETRY_TEST: module.EXPECTED_COMPACT_TELEMETRY_TEST_SHA256,
    }
    for path, expected_sha in expected.items():
        assert sha256(path) == expected_sha
    assert module.TESTER_NO_SPAM_PROJECTION.stat().st_size == 871_692
    assert module.AGENT_NO_SPAM_PROJECTION.stat().st_size == 858_852
    text = RUNNER.read_text(encoding="utf-8")
    for needle in (
        "hyp025_parent_failure_packet",
        "hyp025_parent_failure_review",
        "hyp027_tester_no_spam_projection",
        "hyp027_agent_no_spam_projection",
        "hyp027_journal_budget_addendum",
        "hyp027_bounded_diff_proof",
        "hyp027_compact_telemetry_test",
        "current registry does not contain the exact hash-bound terminal HYP025 parent row",
        "hyp027_pre_execution_harness_addendum",
        "hyp027_independent_pre_probe_review",
    ):
        assert needle in text


def test_packet_builder_has_no_raw_row_self_hash_cycle():
    text = BUILDER.read_text(encoding="utf-8")
    assert "EXPECTED_REGISTRY_ROW_SHA256" not in text
    assert "PENDING_HYP027_INITIAL_ROW_SHA256" not in text
    assert 'row.get("state") != "probe"' in text
    assert 'row.get("verdict") != "FROZEN_HYP027_PACKET_BUILDER_SEMANTIC_AUTHORITY"' in text
    assert 'validation.get("reviewed_task_packet_builder_path") != repo_relative(BUILDER)' in text
    assert 'validation.get("reviewed_task_packet_builder_sha256") != sha256_file(BUILDER)' in text
    assert "PACKET_BUILD_ONLY_NO_EXECUTION_NO_ECONOMICS" in text
    assert 'validation.get("packet_build_authorized") is not True' in text
    assert 'validation.get("packet_build_attempt_id") != PACKET_ATTEMPT_ID' in text
    assert 'validation.get("mt5_attempt_id") != MT5_ATTEMPT_ID' in text


def test_packet_builder_accepts_only_the_exact_packet_only_probe(tmp_path: Path):
    module = load_builder_module()
    registry = tmp_path / "registry.jsonl"
    module.REGISTRY = registry
    row = packet_only_probe(module)
    write_registry(registry, row)
    registry_hash, row_hash, parsed = module.latest_registry_identity()
    assert parsed == row
    assert registry_hash == sha256(registry)
    assert row_hash == hashlib.sha256(
        json.dumps(row, separators=(",", ":")).encode("utf-8")
    ).hexdigest().upper()


def test_packet_builder_rejects_wrong_parent_or_mutated_terminal_row(tmp_path: Path):
    module = load_builder_module()
    registry = tmp_path / "registry.jsonl"
    module.REGISTRY = registry
    wrong_parent = packet_only_probe(module)
    wrong_parent["parent_candidate"] = "HYP-STBS-XAUUSD-M15-022"
    write_registry(registry, wrong_parent)
    with pytest.raises(RuntimeError, match="source/prereg binding is invalid"):
        module.latest_registry_identity()

    parent = json.loads(PARENT_TERMINAL_RAW)
    parent["verdict"] = "MUTATED"
    registry.write_text(
        json.dumps(parent, separators=(",", ":"))
        + "\n"
        + json.dumps(packet_only_probe(module), separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="exact frozen post-claim kill"):
        module.latest_registry_identity()


@pytest.mark.parametrize(
    "field",
    [
        "parent_hyp025_failure_sha256",
        "parent_hyp025_post_failure_review_sha256",
        "pre_execution_harness_addendum_sha256",
        "independent_pre_run_review_sha256",
        "journal_budget_tester_projection_sha256",
        "journal_budget_agent_projection_sha256",
        "journal_budget_addendum_sha256",
        "bounded_diff_proof_sha256",
        "source_contract_test_sha256",
        "reserved_post_packet_review_placeholder_sha256",
    ],
)
def test_packet_builder_rejects_each_governance_evidence_drift(
    tmp_path: Path, field: str
):
    module = load_builder_module()
    registry = tmp_path / "registry.jsonl"
    module.REGISTRY = registry
    row = packet_only_probe(module)
    row["validation"][field] = "0" * 64
    write_registry(registry, row)
    with pytest.raises(RuntimeError, match="not exact packet-only authority"):
        module.latest_registry_identity()


@pytest.mark.parametrize("field", [
    "mt5_train_run_authorized",
    "run_compile_authorized",
    "trade_api_authorized",
    "outcome_prices_authorized",
    "performance_metrics_authorized",
    "economics_authorized",
    "validation_authorized",
    "holdout_authorized",
    "paper_trading_authorized",
    "live_trading_authorized",
    "same_id_retry_authorized",
    "registry_mutation_allowed",
])
def test_packet_builder_rejects_each_broadened_probe_permission(
    tmp_path: Path, field: str
):
    module = load_builder_module()
    registry = tmp_path / "registry.jsonl"
    module.REGISTRY = registry
    row = packet_only_probe(module)
    row["validation"][field] = True
    write_registry(registry, row)
    with pytest.raises(RuntimeError, match="not exact packet-only authority"):
        module.latest_registry_identity()


@pytest.mark.parametrize("field", [
    "packet_build_attempts_consumed",
    "mt5_attempts_consumed",
    "run_compile_attempts_consumed",
    "model0_runs",
    "mt5_launches",
    "orders_executed",
    "trades_simulated",
    "returns_computed",
    "performance_trials_executed",
])
def test_packet_builder_rejects_each_nonzero_probe_counter(
    tmp_path: Path, field: str
):
    module = load_builder_module()
    registry = tmp_path / "registry.jsonl"
    module.REGISTRY = registry
    row = packet_only_probe(module)
    row["metrics"][field] = 1
    write_registry(registry, row)
    with pytest.raises(RuntimeError, match="counters are not pristine"):
        module.latest_registry_identity()


def test_packet_builder_rejects_missing_packet_authority_and_nonempty_run_ids(
    tmp_path: Path,
):
    module = load_builder_module()
    registry = tmp_path / "registry.jsonl"
    module.REGISTRY = registry
    base = packet_only_probe(module)
    mutations = []
    missing_packet = deepcopy(base)
    del missing_packet["validation"]["packet_build_authorized"]
    mutations.append(missing_packet)
    wrong_authority = deepcopy(base)
    wrong_authority["validation"]["authority"] = "MODEL0_TRAIN_FALSIFICATION_ONLY"
    mutations.append(wrong_authority)
    run_ids = deepcopy(base)
    run_ids["run_ids"] = [module.MT5_ATTEMPT_ID]
    mutations.append(run_ids)
    armed_harness = deepcopy(base)
    armed_harness["validation"]["one_shot_economic_harness_version"] = (
        "model0-economic-one-shot-v1"
    )
    mutations.append(armed_harness)
    for row in mutations:
        write_registry(registry, row)
        with pytest.raises(RuntimeError):
            module.latest_registry_identity()


def configure_packet_attempt_paths(module, tmp_path: Path) -> None:
    module.PACKET_ATTEMPT_ROOT = tmp_path / "evidence" / module.PACKET_ATTEMPT_ID
    module.PACKET_ATTEMPT_START = module.PACKET_ATTEMPT_ROOT / "attempt_started.json"
    module.PACKET_ATTEMPT_TERMINAL = module.PACKET_ATTEMPT_ROOT / "attempt_terminal.json"
    module.OUTPUT = tmp_path / "preflight" / "task_packet.control.json"


def test_packet_builder_claim_is_exclusive_and_crash_residue_blocks_retry(
    tmp_path: Path,
):
    module = load_builder_module()
    configure_packet_attempt_paths(module, tmp_path)
    start_sha = module.claim_packet_attempt()
    assert start_sha == sha256(module.PACKET_ATTEMPT_START)
    assert not module.PACKET_ATTEMPT_TERMINAL.exists()
    with pytest.raises(FileExistsError):
        module.claim_packet_attempt()


def test_packet_claim_hash_comes_from_serialized_bytes_without_marker_reread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_builder_module()
    configure_packet_attempt_paths(module, tmp_path)
    monkeypatch.setattr(
        module,
        "sha256_file",
        lambda _path: (_ for _ in ()).throw(AssertionError("marker reread forbidden")),
    )
    start_sha = module.claim_packet_attempt()
    assert start_sha == hashlib.sha256(module.PACKET_ATTEMPT_START.read_bytes()).hexdigest().upper()


def test_model0_claim_installs_terminalizable_record_without_marker_reread():
    text = RUNNER.read_text(encoding="utf-8")
    function = text[text.index("function New-EarlyModel0EconomicLaunchClaim") : text.index("trap {")]
    assert "Sha256 = Get-EarlySha256 $claimBytes" in function
    assert "ReadAllBytes($startPath)" not in function
    assignment = function.index("$script:earlyModel0EconomicAttemptRecord = $attemptRecord")
    returned = function.index("return $attemptRecord", assignment)
    assert assignment < returned


def test_exact_postclaim_marker_is_accepted_and_mutations_fail_executable(tmp_path: Path):
    text = RUNNER.read_text(encoding="utf-8")
    start = text.index("function Test-Hyp027EarlyModel0ClaimIdentity")
    end = text.index("function Add-Model0EconomicLaunchAuthorityBlockers", start)
    helper = text[start:end]
    marker = tmp_path / "attempt_started.json"
    marker.write_text('{"status":"STARTED"}\n', encoding="utf-8")
    packet = tmp_path / "task_packet.control.json"
    packet.write_text("{}\n", encoding="utf-8")
    wrapper = tmp_path / "verify_postclaim.ps1"
    wrapper.write_text(
        "function Get-Sha256IfExists([string]$Path) {\n"
        "  if (-not (Test-Path -LiteralPath $Path)) { return $null }\n"
        "  return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash\n"
        "}\n"
        "function Get-RepoRelativePath([string]$Path) { return [System.IO.Path]::GetFileName($Path) }\n"
        + helper
        + "\n$marker = $args[0]\n"
        + "$packetPath = $args[1]\n"
        + "$sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $marker).Hash\n"
        + "$paths = [pscustomobject]@{StartPath=$marker;TerminalPath=($marker + '.terminal')}\n"
        + "$contract = [pscustomobject]@{RegistrySha256=('A'*64);RegistryRowSha256=('B'*64)}\n"
        + "$packet = [pscustomobject]@{PacketPath=$packetPath;PacketSha256=('C'*64)}\n"
        + "$early = [pscustomobject]@{Path=$marker;TerminalPath=($marker + '.terminal');Sha256=$sha;RegistrySha256=('A'*64);RegistryRowSha256=('B'*64);TaskPacketPath=[System.IO.Path]::GetFileName($packetPath);TaskPacketSha256=('C'*64)}\n"
        + "$exact = Test-Hyp027EarlyModel0ClaimIdentity $early $paths $contract $packet\n"
        + "$early.RegistryRowSha256 = ('D'*64)\n"
        + "$mutated = Test-Hyp027EarlyModel0ClaimIdentity $early $paths $contract $packet\n"
        + "[pscustomobject]@{exact=$exact;mutated=$mutated}|ConvertTo-Json -Compress\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-File", str(wrapper), str(marker), str(packet)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    verdict = json.loads(result.stdout.strip())
    assert verdict == {"exact": True, "mutated": False}


def test_packet_builder_claim_precedes_every_bound_input_read():
    text = BUILDER.read_text(encoding="utf-8")
    main = text[text.index("def main() -> None:") :]
    claim = main.index("start_sha256 = claim_packet_attempt()")
    assert claim < main.index("frozen = {")
    assert claim < main.index("REGISTRY.read_bytes()")
    assert 'OUTPUT.open("xb")' in main
    assert "os.replace(" not in main


def test_packet_builder_writes_complete_terminal_and_blocks_second_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_builder_module()
    configure_packet_attempt_paths(module, tmp_path)
    monkeypatch.setattr(module, "repo_relative", lambda path: Path(path).name)
    registry = tmp_path / "registry.jsonl"
    module.REGISTRY = registry
    write_registry(registry, packet_only_probe(module))

    def fake_git(*args: str) -> str:
        return (
            "test-head"
            if args[:2] == ("rev-parse", "HEAD")
            else module.RESERVED_POST_PACKET_REVIEW_STATUS_LINE
        )

    monkeypatch.setattr(module, "git", fake_git)
    module.main()
    assert module.OUTPUT.exists()
    packet = json.loads(module.OUTPUT.read_text(encoding="utf-8"))
    assert packet["data_quality_contract"]["max_journal_delta_bytes"] == 4_194_304
    assert packet["journal_budget_projected_combined_bytes"] == 1_730_544
    assert packet["reserved_post_packet_review_path"] == module.repo_relative(
        module.RESERVED_POST_PACKET_REVIEW
    )
    terminal = json.loads(module.PACKET_ATTEMPT_TERMINAL.read_text(encoding="utf-8"))
    assert terminal["status"] == "COMPLETE"
    assert terminal["attempt_started_sha256"] == sha256(module.PACKET_ATTEMPT_START)
    assert terminal["packet_sha256"] == sha256(module.OUTPUT)
    assert terminal["same_id_retry_authorized"] is False
    with pytest.raises(FileExistsError):
        module.main()


def test_hyp027_runner_freezes_packet_and_manifest_to_four_mib():
    text = RUNNER.read_text(encoding="utf-8")
    assert "data_quality_contract.max_journal_delta_bytes must equal the frozen 4194304-byte raw-delta cap" in text
    assert "$packetMaxJournalDeltaBytes -ne 4194304L" in text
    assert "[int64](Get-ObjectProperty $manifestContract 'max_journal_delta_bytes') -ne $packetMaxJournalDeltaBytes" in text
    assert "journal evidence is incomplete, truncated or ambiguous" in text


def test_alpha_contract_cap_is_explicit_and_backward_compatible():
    alpha = (ROOT / "02. AlphaFactory/alpha.ps1").read_text(encoding="utf-8-sig")
    assert "[int64]$maxJournalDeltaBytes = 1048576L" in alpha
    assert "may additionally contain only max_journal_delta_bytes" in alpha
    assert "max_journal_delta_bytes must be an integer" in alpha
    assert "must be a power of two from 1048576 through 67108864" in alpha
    assert "max_journal_delta_bytes = $maxJournalDeltaBytes" in alpha


@pytest.mark.parametrize("bad_cap", [None, "4194304", 1_048_576, 2_097_152, 8_388_608, 4_194_305])
def test_packet_cap_mutations_are_not_the_frozen_hyp027_contract(bad_cap):
    module = load_builder_module()
    packet = {
        "data_quality_contract": {
            "history_quality": {"operator": "gt", "value": 97.0},
            "coverage_mode": "fixed_window",
            "availability_asof_utc": "2026-08-09T21:22:00Z",
            "requested_from": "2005.01.01",
            "requested_to": "2023.01.01",
            "require_tester_journal_bounds": True,
            "max_journal_delta_bytes": bad_cap,
        }
    }
    assert packet["data_quality_contract"]["max_journal_delta_bytes"] != 4_194_304
    assert module.MT5_ATTEMPT_ID == "STBS027-MODEL0-TRAIN-001"


def test_packet_builder_failure_after_claim_is_terminal_and_nonretryable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_builder_module()
    configure_packet_attempt_paths(module, tmp_path)
    monkeypatch.setattr(module, "repo_relative", lambda path: Path(path).name)
    registry = tmp_path / "registry.jsonl"
    module.REGISTRY = registry
    write_registry(registry, packet_only_probe(module))
    monkeypatch.setattr(module, "EXPECTED_SOURCE_SHA256", "0" * 64)
    with pytest.raises(RuntimeError, match="frozen input drift"):
        module.main()
    terminal = json.loads(module.PACKET_ATTEMPT_TERMINAL.read_text(encoding="utf-8"))
    assert terminal["status"] == "FAILED"
    assert terminal["packet_sha256"] is None
    assert terminal["error"].startswith("RuntimeError: frozen input drift")
    with pytest.raises(FileExistsError):
        module.main()


def test_packet_builder_crash_after_packet_before_terminal_cannot_be_promoted_or_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_builder_module()
    configure_packet_attempt_paths(module, tmp_path)
    monkeypatch.setattr(module, "repo_relative", lambda path: Path(path).name)
    registry = tmp_path / "registry.jsonl"
    module.REGISTRY = registry
    write_registry(registry, packet_only_probe(module))
    monkeypatch.setattr(
        module,
        "git",
        lambda *args: "test-head"
        if args[:2] == ("rev-parse", "HEAD")
        else module.RESERVED_POST_PACKET_REVIEW_STATUS_LINE,
    )

    def crash_terminal(**_kwargs):
        raise RuntimeError("simulated terminal crash")

    monkeypatch.setattr(module, "finish_packet_attempt", crash_terminal)
    with pytest.raises(RuntimeError, match="simulated terminal crash"):
        module.main()
    assert module.OUTPUT.exists()
    assert module.PACKET_ATTEMPT_START.exists()
    assert not module.PACKET_ATTEMPT_TERMINAL.exists()
    with pytest.raises(FileExistsError):
        module.main()
