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
RUNNER = ROOT / "02. AlphaFactory/tools/run_stbs023_model0_baseline.ps1"
BASE = ROOT / "02. AlphaFactory/tools/research_loop_engine.ps1"
ALPHA = ROOT / "02. AlphaFactory/alpha.ps1"
AUDITOR = ROOT / "02. AlphaFactory/tools/audit_mql5_nonrepaint.py"
SOURCE = PACKAGE / "EA_SupertrendBurstScalperTradeV10.mq5"
STATIC_MANIFEST = PACKAGE / "HYP-STBS-XAUUSD-M15-023_NONREPAINT_MANIFEST.json"
BUILDER = PACKAGE / "research/build_stbs023_task_packet.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_builder_module():
    spec = importlib.util.spec_from_file_location("stbs023_packet_builder", BUILDER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def packet_only_probe(module) -> dict:
    return {
        "hypothesis_id": module.HYPOTHESIS_ID,
        "state": "probe",
        "source_hash": module.EXPECTED_SOURCE_SHA256,
        "prereg_sha256": module.EXPECTED_PREREG_SHA256,
        "verdict": "FROZEN_HYP023_PACKET_BUILDER_SEMANTIC_AUTHORITY",
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
            **{name: False for name in module.PROBE_FALSE_FIELDS},
        },
    }


def write_registry(path: Path, row: dict) -> None:
    path.write_text(json.dumps(row, separators=(",", ":")) + "\n", encoding="utf-8")


def test_shared_alphafactory_remains_frozen():
    assert sha256(ALPHA) == "BC570A1EA7D8788AC9483A7133565893C8B679ADE9A0ED85E2B8AF8B3A0F02FC"
    assert sha256(BASE) == "6E205874477A79EB97EE56967B81FA3675FB25AD784D00D989BBD077DA837550"


def test_runner_is_hyp023_only_and_preserves_original_run_manifest():
    text = RUNNER.read_text(encoding="utf-8")
    assert "$EaName -cne 'EA_SupertrendBurstScalperTradeV10'" in text
    assert "$HypothesisId -cne 'HYP-STBS-XAUUSD-M15-023'" in text
    assert "$From -cne '2005.01.01' -or $To -cne '2023.01.01'" in text
    assert "$Model -ne 0" in text and "$TimeoutSec -ne 900" in text
    assert "$TelemetryTier -cne 'trade-only'" in text
    assert "nonrepaint_run_manifest.json" in text
    assert "New-Hyp023NonRepaintAuditManifest $runManifestPath $runManifestShaForAudit $analysisDir" in text
    assert "--manifest $nonRepaintRunManifestPath" in text
    assert "Write-JsonAtomically $run $RunManifestPath" not in text
    assert "& $alphaPs1 backtest" in text


def test_runner_binds_exact_static_provenance_authority():
    text = RUNNER.read_text(encoding="utf-8")
    assert "2FD0CB06E4273671994A7D6B105701FC78AFAC37536E111D791519D99CF2086D" in text
    assert "7E281A579EB6DE5E90C5263BA6E5E064015A96231753C217DE592CA6AE641053" in text
    assert "4B481CE867DB8A9F9E02AB218FEA50C88FD37A48B8ECB92E2048418DB7F7769B" in text
    assert "366D70F0C6FAF02F85B4819E7305CD1BD271BA6A78B4789CF0DCDF2FB651E360" in text
    assert "$hyp023CopyTimeLine = 678" in text
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
        "hypothesis_id": "HYP-STBS-XAUUSD-M15-023",
        "run_id": "STBS023-ADAPTER-TEST",
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
        "[int]$allowedGates[0].line -ne $hyp023CopyTimeLine",
        "[string]$allowedGates[0].rule -cne 'collection_first_date_copytime'",
        "[string]$allowedGates[0].function -cne 'CopyTime'",
        "[string]$allowedGates[0].disposition -cne 'allowed_collection_provenance_read'",
        "non-repaint auditor, derivative manifest or audit artifact drifted during validation",
        "reviewed_nonrepaint_auditor_sha256",
        "hyp023_nonrepaint_auditor",
    ):
        assert needle in text


def test_runner_postclaim_validates_and_receipt_binds_packet_attempt_chain():
    text = RUNNER.read_text(encoding="utf-8")
    for needle in (
        "function Assert-Hyp023PacketBuildChain",
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
        "Assert-Hyp023PacketBuildChain $contract $packetResult $launchClaimRecord",
        "hyp023_packet_attempt_start",
        "hyp023_packet_attempt_terminal",
        "hyp023_gitignore",
    ):
        assert needle in text
    claim = text.index(
        "$economicAttemptRecord = New-Model0EconomicLaunchClaim $contract $binding $packetResult"
    )
    validate = text.index(
        "Assert-Hyp023PacketBuildChain $contract $packetResult $launchClaimRecord",
        claim,
    )
    assert claim < validate


def test_packet_builder_has_no_raw_row_self_hash_cycle():
    text = BUILDER.read_text(encoding="utf-8")
    assert "EXPECTED_REGISTRY_ROW_SHA256" not in text
    assert "PENDING_HYP023_INITIAL_ROW_SHA256" not in text
    assert 'row.get("state") != "probe"' in text
    assert 'row.get("verdict") != "FROZEN_HYP023_PACKET_BUILDER_SEMANTIC_AUTHORITY"' in text
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
        return "test-head" if args[:2] == ("rev-parse", "HEAD") else "?? reserved-control"

    monkeypatch.setattr(module, "git", fake_git)
    module.main()
    assert module.OUTPUT.exists()
    terminal = json.loads(module.PACKET_ATTEMPT_TERMINAL.read_text(encoding="utf-8"))
    assert terminal["status"] == "COMPLETE"
    assert terminal["attempt_started_sha256"] == sha256(module.PACKET_ATTEMPT_START)
    assert terminal["packet_sha256"] == sha256(module.OUTPUT)
    assert terminal["same_id_retry_authorized"] is False
    with pytest.raises(FileExistsError):
        module.main()


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
        else "?? reserved-control",
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
