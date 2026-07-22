"""Static parser/contract tests for research/run_frozen_hyp_once.ps1.

No MT5 / backtest / research-loop execution.
"""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "research" / "run_frozen_hyp_once.ps1"


def runner_text() -> str:
    return RUNNER.read_text(encoding="utf-8-sig")


def test_runner_exists():
    assert RUNNER.is_file()


def test_allow_list_only_008_009_010():
    text = runner_text()
    assert "HYP-MZMS-XAU-M5-008" in text
    assert "HYP-MZMS-XAU-M5-009" in text
    assert "HYP-MZMS-XAU-M5-010" in text
    # HYP-007 must not be executable through this runner (already bound lesson).
    assert not re.search(
        r'ValidateSet\([\s\S]*HYP-MZMS-XAU-M5-007[\s\S]*\)',
        text,
    )
    assert "HYP-MZMS-XAU-M5-007" not in re.findall(
        r'ValidateSet\(([\s\S]*?)\)',
        text,
    )[0]
    # Only the three IDs appear inside ValidateSet.
    block = re.search(r"ValidateSet\(([\s\S]*?)\)", text)
    assert block, "ValidateSet allow-list missing"
    ids = re.findall(r'HYP-MZMS-XAU-M5-\d{3}', block.group(1))
    assert ids == [
        "HYP-MZMS-XAU-M5-008",
        "HYP-MZMS-XAU-M5-009",
        "HYP-MZMS-XAU-M5-010",
    ]


def test_exact_campaign_flags_and_paths():
    text = runner_text()
    required_flags = [
        '"-RunRole", "control"',
        '"-Symbol", "XAUUSD"',
        '"-Period", "M5"',
        '"-From", "2018.01.01"',
        '"-To", "2026.07.22"',
        '"-Model", "0"',
        '"-ExecutionMode", "0"',
        '"-FixedDelayMs", "0"',
        '"-TelemetryTier", "trade-only"',
        '"-Deposit", "100000"',
        '"-Leverage", "100"',
        '"-ValidationStage", "challenger"',
        '"-HoldingContract", "scalp"',
        '"-AllowResearchCostProxy"',
        '"-TaskPacket", $packetRel',
        '"-CostSourceManifest", $costRel',
        '"-Overrides", $overrides',
    ]
    for flag in required_flags:
        assert flag in text, f"missing flag/path wiring: {flag}"

    # Forward-slash relative packet path template.
    assert (
        '03. EA Developer/EA_MZMS_Scalper/research/preflight/{0}/task_packet.control.json'
        in text
    )
    # spread=current => omit -Spread
    assert "omit -Spread" in text
    assert not re.search(r'"-Spread"', text)


def test_no_self_retry_loop_on_execute():
    text = runner_text()
    # Exactly one WithExecute / -Execute economic invocation site.
    assert text.count("-WithExecute") == 1
    assert "never self-retry" in text.lower() or "never self-retries" in text.lower() or "No retry" in text
    # No while/do retry wrappers around execute.
    assert not re.search(r"while\s*\([^)]*Execute", text, re.I)
    assert not re.search(r"for\s*\([^)]*retry", text, re.I)
    assert "self-retry" in text or "No retry" in text
    # Single assignment of execute_attempted = $true at the economic call site.
    assert text.count("execute_attempted = $true") == 1
    assert text.count("Invoke-ResearchLoopOnce") >= 2  # dry-run + optional execute


def test_manifest_guard_and_process_guards():
    text = runner_text()
    assert "Find-BoundHypothesisRunDirs" in text
    assert "run_manifest.json" in text
    assert "second economic outcome forbidden" in text
    assert "ea_research_loop.lock" in text
    assert "Active research-loop lock exists" in text
    assert 'Get-Process -Name "terminal64"' in text
    assert "Unrelated terminal64 process exists" in text


def test_receipt_schema_has_no_outcome_fields():
    text = runner_text()
    assert "mzms_frozen_hyp_once_receipt.v1" in text
    assert "execute_attempted" in text
    assert "discovered_run_dirs" in text
    assert "dry_run_status" in text
    # Must not write outcome metrics into the operator receipt.
    for banned in (
        "profit_factor",
        "expectancy",
        "max_drawdown",
        "trades_per_week",
        "net_profit",
    ):
        assert banned not in text


def test_does_not_mutate_source_packets_registry_or_harness():
    text = runner_text()
    # Operator is read-only against sealed surfaces.
    for banned in (
        "CANDIDATE_REGISTRY.jsonl",
        "Set-Content -LiteralPath $packetAbs",
        "EA_MZMS_Scalper.mq5",
        "alpha.ps1",
    ):
        # Mentions of mq5 only allowed in comments would still be risky; require absence.
        if banned == "EA_MZMS_Scalper.mq5":
            assert banned not in text
        elif banned == "alpha.ps1":
            assert banned not in text
        elif banned == "CANDIDATE_REGISTRY.jsonl":
            assert banned not in text
        else:
            assert banned not in text

    # Only writes the caller-provided receipt path.
    assert "Write-OperatorReceipt" in text
    assert "Set-Content -LiteralPath $Path" in text
