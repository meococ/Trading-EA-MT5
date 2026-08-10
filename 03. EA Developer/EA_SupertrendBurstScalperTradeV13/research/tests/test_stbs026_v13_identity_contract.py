from __future__ import annotations

import hashlib
import csv
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[2]
PARENT_V12 = ROOT / "03. EA Developer/EA_SupertrendBurstScalperTradeV12/EA_SupertrendBurstScalperTradeV12.mq5"
CURRENT_V13 = PACKAGE / "EA_SupertrendBurstScalperTradeV13.mq5"
FAILURE_ARCHIVE = (
    ROOT
    / "03. EA Developer/EA_SupertrendBurstScalperTradeV10/research/evidence"
    / "HYP-STBS-XAUUSD-M15-023/STBS023-FAILURE-CLOSE-001"
)
TESTER_PROJECTION = FAILURE_ARCHIVE / "tester_hyp023_no_spam_projection.utf16le.log"
AGENT_PROJECTION = FAILURE_ARCHIVE / "agent_hyp023_no_spam_projection.utf16le.log"
FROZEN_CAP = 4_194_304
RUNNER = ROOT / "02. AlphaFactory/tools/run_stbs026_model0_baseline.ps1"
COST_BUILDER = ROOT / "02. AlphaFactory/tools/build_verified_cost_artifact.py"
COST_MANIFEST = PACKAGE / "research/HYP-STBS-XAUUSD-M15-026_RESEARCH_COST_SOURCE_MANIFEST.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def normalize_v12_to_v13(text: str) -> str:
    replacements = {
        '#property version   "12.00"': '#property version   "13.00"',
        '#property description "H1 Supertrend V12 identity clone with unchanged bounded telemetry and execution."':
            '#property description "H1 Supertrend V13 identity clone with post-claim reconciliation harness."',
        "HYP-STBS-XAUUSD-M15-025": "HYP-STBS-XAUUSD-M15-026",
        "STBS_H1_FLIP_M15_BURST_TRADE_V12_IDENTITY_CLONE":
            "STBS_H1_FLIP_M15_BURST_TRADE_V13_POSTCLAIM_RECONCILE",
        "5604125": "5604126",
        "EA_SupertrendBurstScalperTradeV12": "EA_SupertrendBurstScalperTradeV13",
    }
    for old, new in replacements.items():
        assert old in text
        text = text.replace(old, new)
    return text


def test_v13_is_exact_v12_identity_only_clone():
    assert normalize_v12_to_v13(PARENT_V12.read_text(encoding="utf-8")) == CURRENT_V13.read_text(encoding="utf-8")
    assert sha256(PARENT_V12) == "D96F55A26F277CFC3FDC4E23A11A84C74598C111639E629CEC1877AC3F7704C5"
    assert sha256(CURRENT_V13) == "F60A9469D1A6FE2D62F5E83DECB953862C68AF9E3D154EA0AE488C072B4A4DA4"


def test_v13_identity_is_fail_closed():
    text = CURRENT_V13.read_text(encoding="utf-8")
    for needle in (
        '#property version   "13.00"',
        'InpHypothesisId        = "HYP-STBS-XAUUSD-M15-026"',
        'InpVariantTag          = "STBS_H1_FLIP_M15_BURST_TRADE_V13_POSTCLAIM_RECONCILE"',
        "InpMagic               = 5604126",
        'EA_NAME              = "EA_SupertrendBurstScalperTradeV13"',
        'InpHypothesisId!="HYP-STBS-XAUUSD-M15-026"',
        'InpVariantTag!="STBS_H1_FLIP_M15_BURST_TRADE_V13_POSTCLAIM_RECONCILE"',
        "InpAuditOnly || !InpEnableTelemetry || InpMagic!=5604126",
    ):
        assert needle in text


def test_four_mib_budget_still_dominates_exact_no_spam_projection():
    assert sha256(TESTER_PROJECTION) == "DDE409FE80DE6687DD0A520D0B4EAD2F20817142C212CD40E9E7FAFB2CC4EC7B"
    assert sha256(AGENT_PROJECTION) == "2F08B3860EB6247BF168331914754650548155FFC93513FD51FA539369BCE7AF"
    combined = TESTER_PROJECTION.stat().st_size + AGENT_PROJECTION.stat().st_size
    assert combined == 1_730_544
    assert combined > 1_048_576
    assert combined < FROZEN_CAP


def test_nondecision_spam_remains_absent():
    assert "STBS_MARGIN_STRESS_UNSAFE" not in CURRENT_V13.read_text(encoding="utf-8")


def test_generic_cost_builder_accepts_same_outer_inner_identity_and_rejects_adapter(tmp_path: Path):
    spec = importlib.util.spec_from_file_location("stbs026_cost_builder", COST_BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    contract = json.loads(COST_MANIFEST.read_text(encoding="utf-8"))["run_meta_contract"]
    lifecycle = tmp_path / "LifecycleTrades.csv"
    with lifecycle.open("w", newline="", encoding="utf-8") as handle:
        fields = sorted(module.REQUIRED_LIFECYCLE_COLUMNS)
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({field: "0" for field in fields})
    run_id = "STBS026-GOLDEN-001"
    run_meta = tmp_path / f"EA_RunMeta_{run_id}.json"
    payload = {
        "schema_version": "alphafactory_run_meta.v1",
        "run_id": run_id,
        "ea_name": "EA_SupertrendBurstScalperTradeV13",
        "symbol": "XAUUSD",
        "telemetry_profile": "lifecycle-v3",
        "hypothesis_id": "HYP-STBS-XAUUSD-M15-026",
        "variant_tag": "STBS_H1_FLIP_M15_BURST_TRADE_V13_POSTCLAIM_RECONCILE",
        "magic": 5604126,
        "audit_only": False,
        "promotion_eligible": False,
        "diagnostic": {"runtime_failed": False, "lifecycle_rows": 1},
    }
    run_meta.write_text(json.dumps(payload), encoding="utf-8")
    manifest = {
        "hypothesis_id": "HYP-STBS-XAUUSD-M15-026",
        "ea_name": "EA_SupertrendBurstScalperTradeV13",
        "symbol": "XAUUSD",
    }
    result = module.validate_run_meta(run_meta, sha256(run_meta), lifecycle, manifest, contract)
    assert result["semantic_validation"]["row_count_reconciled"] is True
    bad_contract = dict(contract, hypothesis_id="HYP-STBS-XAUUSD-M15-025")
    with pytest.raises(ValueError, match="hypothesis_id"):
        module.validate_run_meta(run_meta, sha256(run_meta), lifecycle, manifest, bad_contract)


def test_execute_claim_precedes_first_bound_helper_read_and_failure_is_terminal(tmp_path: Path):
    isolated = tmp_path / "isolated"
    tools = isolated / "02. AlphaFactory/tools"
    registry_dir = isolated / "04. Memory/research"
    tools.mkdir(parents=True)
    registry_dir.mkdir(parents=True)
    copied_runner = tools / RUNNER.name
    copied_runner.write_bytes(RUNNER.read_bytes())
    packet_relative = (
        "03. EA Developer/EA_SupertrendBurstScalperTradeV13/research/preflight/"
        "HYP-STBS-XAUUSD-M15-026/V1/task_packet.control.json"
    )
    row = {
        "hypothesis_id": "HYP-STBS-XAUUSD-M15-026",
        "state": "screened",
        "metrics": {"mt5_attempts_consumed": 0},
        "validation": {
            "authority": "MODEL0_TRAIN_FALSIFICATION_ONLY",
            "one_shot_economic_harness_version": "model0-economic-one-shot-v1",
            "mt5_attempt_id": "STBS026-MODEL0-TRAIN-001",
            "mt5_attempt_limit": 1,
            "same_id_retry_authorized": False,
            "task_packet_path": packet_relative,
            "task_packet_sha256": "A" * 64,
        },
    }
    (registry_dir / "CANDIDATE_REGISTRY.jsonl").write_text(
        json.dumps(row, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    command = [
        "powershell", "-NoProfile", "-File", str(copied_runner),
        "-EaName", "EA_SupertrendBurstScalperTradeV13",
        "-HypothesisId", "HYP-STBS-XAUUSD-M15-026",
        "-TaskPacket", packet_relative,
        "-RunRole", "control", "-Symbol", "XAUUSD", "-Period", "M15",
        "-From", "2005.01.01", "-To", "2023.01.01", "-Model", "0",
        "-ExecutionMode", "0", "-FixedDelayMs", "0", "-TimeoutSec", "900",
        "-TelemetryTier", "trade-only", "-Deposit", "100000", "-Leverage", "100",
        "-Execute",
    ]
    result = subprocess.run(command, cwd=isolated, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    attempt = isolated / (
        "02. AlphaFactory/runtime/model0_economic_attempts/"
        "HYP-STBS-XAUUSD-M15-026/STBS026-MODEL0-TRAIN-001"
    )
    assert (attempt / "attempt_started.json").is_file()
    terminal = json.loads((attempt / "attempt_terminal.json").read_text(encoding="utf-8"))
    assert terminal["status"] == "FAILED"
    assert "EA source contract resolver is missing" in terminal["error"]
