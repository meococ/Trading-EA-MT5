from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ALPHA_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ALPHA_ROOT)
    return subprocess.run(
        [sys.executable, "-m", "session_trader", *args],
        cwd=ALPHA_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_cli_help_states_that_python_execution_is_not_available() -> None:
    result = run_cli("--help")
    assert result.returncode == 0
    assert "no Python order execution" in result.stdout


def test_cli_prints_trade_intent_schema() -> None:
    result = run_cli("schema", "--model", "TradeIntent")
    assert result.returncode == 0, result.stderr
    schema = json.loads(result.stdout)
    assert schema["title"] == "TradeIntent"
    assert "stop_loss" in schema["properties"]


def test_verify_empty_ledger_is_valid(tmp_path: Path) -> None:
    result = run_cli("verify-ledger", "--ledger", str(tmp_path / "events.jsonl"))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["entries"] == 0


def test_generic_writer_cannot_mint_risk_approval(tmp_path: Path) -> None:
    result = run_cli(
        "write-artifact",
        "--model",
        "RiskDecision",
        "--input",
        str(tmp_path / "does-not-matter.json"),
        "--path",
        "risk/forged.json",
        "--artifact-root",
        str(tmp_path / "artifacts"),
        "--ledger",
        str(tmp_path / "events.jsonl"),
        "--session-plan-id",
        "SESSION_PLAN_2026-08-27_LONDON",
    )

    assert result.returncode == 2
    assert "authority-controlled" in result.stderr

    market_result = run_cli(
        "write-artifact",
        "--model",
        "MarketSnapshot",
        "--input",
        str(tmp_path / "does-not-matter.json"),
        "--path",
        "snapshots/forged.json",
        "--artifact-root",
        str(tmp_path / "artifacts"),
        "--ledger",
        str(tmp_path / "events.jsonl"),
        "--session-plan-id",
        "SESSION_PLAN_2026-08-27_LONDON",
    )
    assert market_result.returncode == 2
    assert "authority-controlled" in market_result.stderr


def test_agent_artifact_write_is_ledger_backed_and_retry_idempotent(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    ledger = tmp_path / "events.jsonl"
    plan_input = ALPHA_ROOT / "session_trader" / "examples" / "SESSION_PLAN_2099-01-01_LONDON_v1.json"
    plan_result = run_cli(
        "write-plan",
        "--input",
        str(plan_input),
        "--artifact-root",
        str(artifact_root),
    )
    assert plan_result.returncode == 0, plan_result.stderr
    plan_ref = json.loads(plan_result.stdout)
    dummy_ref = {
        "schema_version": "fixture.v1",
        "path": "fixtures/input.json",
        "sha256": "d" * 64,
    }
    candidate = {
        "schema_version": "candidate.v1",
        "candidate_id": "CANDIDATE-LEDGER-1",
        "created_at_utc": "2099-01-01T06:01:00Z",
        "plan": plan_ref,
        "market_snapshot": dummy_ref,
        "account_snapshot": dummy_ref,
        "symbol": "EURUSD",
        "direction": "LONG",
        "scenario_id": "NO_TRADE_TEMPLATE",
        "entry_condition": "fixture only",
        "entry_min": 1.1,
        "entry_max": 1.101,
        "stop_loss": 1.09,
        "take_profit": 1.12,
        "expiry_utc": "2099-01-01T07:00:00Z",
        "requested_risk_pct": 0.1,
        "expected_r": 2.0,
        "confidence": 0.5,
        "evidence_refs": ["fixture"],
    }
    candidate_input = tmp_path / "candidate.json"
    candidate_input.write_text(json.dumps(candidate), encoding="utf-8")
    command = (
        "write-artifact",
        "--model",
        "Candidate",
        "--input",
        str(candidate_input),
        "--path",
        "agents/candidate-ledger-1.json",
        "--artifact-root",
        str(artifact_root),
        "--ledger",
        str(ledger),
        "--session-plan-id",
        "SESSION_PLAN_2099-01-01_LONDON",
    )

    first = run_cli(*command)
    second = run_cli(*command)
    candidate["candidate_id"] = "CANDIDATE-CONFLICTING-CONTENT"
    candidate_input.write_text(json.dumps(candidate), encoding="utf-8")
    conflicting = run_cli(*command)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert conflicting.returncode == 2
    rows = ledger.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1
    assert json.loads(rows[0])["payload"]["event_type"] == "CANDIDATE_CREATED"
