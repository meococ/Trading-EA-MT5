from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
RUNNER_PATH = ROOT / "03. EA Developer" / "EA_SupertrendBurstScalperTradeV5" / "research" / "run_stbs017_model0_audit.py"
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
ATTEMPT_ROOT = ROOT / "02. AlphaFactory" / "runtime" / "model0_audit_attempts" / "HYP-STBS-XAUUSD-M15-017" / "STBS017-MODEL0-AUDIT-001"


def load_runner():
    spec = importlib.util.spec_from_file_location("stbs017_runner", RUNNER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_override_map(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for token in text.split(";"):
        if not token or "=" not in token:
            raise ValueError("malformed override")
        key, value = token.split("=", 1)
        if not key or not value or key in values:
            raise ValueError("invalid or duplicate override")
        values[key] = value
    return values


def alpha_effective(text: str) -> str:
    values = parse_override_map(text)
    return ";".join(f"{key}={values[key]}" for key in sorted(values))


def test_outer_and_inner_identity_are_fresh_and_explicit() -> None:
    runner = load_runner()
    assert runner.HYPOTHESIS_ID == "HYP-STBS-XAUUSD-M15-017"
    assert runner.INNER_HYPOTHESIS_ID == "HYP-STBS-XAUUSD-M15-016"
    assert runner.ATTEMPT_ID == "STBS017-MODEL0-AUDIT-001"
    assert runner.MAGIC == 5604116
    assert not ATTEMPT_ROOT.exists()


def test_cli_normalizes_to_exact_receipt_and_manifest_value() -> None:
    runner = load_runner()
    assert runner.CLI_OVERRIDES != runner.EFFECTIVE_OVERRIDES
    assert parse_override_map(runner.CLI_OVERRIDES) == parse_override_map(runner.EFFECTIVE_OVERRIDES)
    assert alpha_effective(runner.CLI_OVERRIDES) == runner.EFFECTIVE_OVERRIDES
    assert runner.OVERRIDES == runner.EFFECTIVE_OVERRIDES


@pytest.mark.parametrize(
    "mutated",
    [
        "InpAuditOnly=true;InpAuditOnly=true",
        "InpAuditOnly=true;bare",
        "InpAuditOnly=",
        "=true",
    ],
)
def test_normalizer_mirror_rejects_ambiguous_cli(mutated: str) -> None:
    with pytest.raises(ValueError):
        alpha_effective(mutated)


def test_runner_passes_cli_but_binds_effective_override() -> None:
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert '"-Overrides", CLI_OVERRIDES' in source
    assert '"overrides": OVERRIDES' in source
    assert 'OVERRIDES = EFFECTIVE_OVERRIDES' in source
    assert 'v.get("cli_overrides") != CLI_OVERRIDES' in source
    assert 'v.get("effective_overrides") != EFFECTIVE_OVERRIDES' in source


def test_parent_terminal_is_exact_and_no_hyp016_retry() -> None:
    rows = [json.loads(line) for line in REGISTRY.read_text(encoding="utf-8").splitlines() if line.strip()]
    parent = [row for row in rows if row.get("hypothesis_id") == "HYP-STBS-XAUUSD-M15-016"][-1]
    assert parent["state"] == "killed"
    assert parent["verdict"] == "KILL_HARNESS_UNNORMALIZED_OVERRIDE_RECEIPT_PRECOMPILE_NO_MT5_NO_ECONOMIC_VERDICT"
    assert parent["metrics"]["mt5_audit_attempts_consumed"] == 1
    assert parent["metrics"]["run_compile_attempts_consumed"] == 0
    assert parent["validation"]["same_id_retry_authorized"] is False


def test_outer_runner_retains_zero_trade_no_economic_boundary() -> None:
    source = RUNNER_PATH.read_text(encoding="utf-8")
    for field in (
        "trade_api_authorized",
        "performance_metrics_authorized",
        "outcome_prices_authorized",
        "economics_authorized",
        "optimization_authorized",
        "validation_authorized",
        "holdout_authorized",
        "paper_trading_authorized",
        "live_trading_authorized",
    ):
        assert f'"{field}"' in source
