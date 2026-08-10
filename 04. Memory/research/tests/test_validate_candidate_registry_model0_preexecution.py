from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_candidate_registry.py"
SPEC = importlib.util.spec_from_file_location(
    "candidate_registry_validator_model0_preexecution", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
SUT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUT)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write(root: Path, relative: str, payload: bytes) -> Path:
    path = root / Path(relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _fixture(monkeypatch, tmp_path: Path) -> tuple[dict, dict, str, str]:
    monkeypatch.setattr(SUT, "WORKSPACE", tmp_path)
    hypothesis_id = "HYP-STBS-XAUUSD-M15-013"
    ea_name = "EA_SupertrendBurstScalperTradeV3"
    source_path = f"03. EA Developer/{ea_name}/{ea_name}.mq5"
    prereg_path = (
        f"03. EA Developer/{ea_name}/research/"
        f"{hypothesis_id}_MODEL0_TRAIN_PREREG.md"
    )
    packet_path = (
        f"03. EA Developer/{ea_name}/research/preflight/{hypothesis_id}/V1/"
        "task_packet.control.json"
    )
    addendum_path = (
        f"03. EA Developer/{ea_name}/research/"
        f"{hypothesis_id}_PRE_EXECUTION_HARNESS_ADDENDUM.md"
    )
    runner_path = "02. AlphaFactory/tools/research_loop_engine.ps1"
    alpha_path = "02. AlphaFactory/alpha.ps1"
    cost_test_path = "02. AlphaFactory/tests/test_research_cost_proxy.py"
    golden_test_path = "02. AlphaFactory/tests/test_ea_golden_path.py"
    validator_path = "04. Memory/research/validate_candidate_registry.py"
    validator_test_path = (
        "04. Memory/research/tests/"
        "test_validate_candidate_registry_model0_preexecution.py"
    )
    packet_builder_path = (
        f"03. EA Developer/{ea_name}/research/build_stbs013_task_packet.py"
    )

    source = _write(tmp_path, source_path, b"// source\n")
    prereg = _write(tmp_path, prereg_path, b"# prereg\n")
    addendum = _write(tmp_path, addendum_path, b"# addendum\n")
    runner = _write(tmp_path, runner_path, b"# runner\n")
    alpha = _write(tmp_path, alpha_path, b"# alpha\n")
    cost_test = _write(tmp_path, cost_test_path, b"# cost test\n")
    golden_test = _write(tmp_path, golden_test_path, b"# golden test\n")
    validator = _write(tmp_path, validator_path, MODULE_PATH.read_bytes())
    validator_test = _write(tmp_path, validator_test_path, Path(__file__).read_bytes())
    packet_builder = _write(tmp_path, packet_builder_path, b"# packet builder\n")

    acceptance = {
        "min_profit_factor": 1.3,
        "min_trades_per_week": 2,
        "max_trades_per_week": 5,
        "max_drawdown_pct": 8,
        "min_cost_pf_x1_5": 1.25,
        "min_cost_pf_x2": 1,
        "max_monte_carlo_p95_dd_pct": 8,
    }
    registry_baseline = {
        "min_completed_trades": 500,
        "min_direction_share": 0.3,
        "max_year_trade_share": 0.3,
        "require_positive_mean_x1_net_r": True,
        "require_each_calendar_year_positive_x1_net_r": True,
    }
    packet_baseline = {
        "min_completed_trades": 500,
        "min_direction_share": 0.3,
        "max_year_trade_share": 0.3,
        "require_positive_cost_expectancy": True,
        "require_all_calendar_years_positive": True,
    }
    prior_registry_sha = "A" * 64
    prior_row_sha = "B" * 64
    git_status_sha = "C" * 64
    packet = {
        "schema_version": "alphafactory_research_task_packet.v1",
        "hypothesis_id": hypothesis_id,
        "run_role": "control",
        "ea_name": ea_name,
        "model": 0,
        "timeout_sec": 900,
        "attempt_id": "STBS013-MODEL0-TRAIN-001",
        "attempt_limit": 1,
        "source_path": source_path,
        "source_sha256": _sha(source),
        "registry_path": "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
        "registry_sha256": prior_registry_sha,
        "registry_row_sha256": prior_row_sha,
        "prereg_path": prereg_path,
        "prereg_sha256": _sha(prereg),
        "acceptance_contract": acceptance,
        "baseline_acceptance_contract": packet_baseline,
        "performance_metrics_authorized": True,
        "economics_authorized": True,
        "promotion_eligible": False,
        "git_status_sha256": git_status_sha,
    }
    packet_file = _write(
        tmp_path,
        packet_path,
        json.dumps(packet, separators=(",", ":")).encode("utf-8"),
    )

    validation = {
        "authority": "MODEL0_TRAIN_FALSIFICATION_ONLY",
        "probe_status": "SCREENED_STBS013_ONE_UNTUNED_MODEL0_RESEARCH_PROXY_BASELINE_AUTHORIZED",
        "mt5_attempt_id": "STBS013-MODEL0-TRAIN-001",
        "mt5_attempt_limit": 1,
        "baseline_acceptance_contract": registry_baseline,
        "reviewed_alpha_ps1_path": alpha_path,
        "reviewed_alpha_ps1_sha256": "0" * 64,
        "reviewed_research_loop_sha256": "1" * 64,
        "reviewed_cost_test_sha256": "2" * 64,
    }
    for field in SUT.MODEL0_PREEXECUTION_REQUIRED_TRUE_FIELDS:
        validation[field] = True
    for field in SUT.MODEL0_PREEXECUTION_REQUIRED_FALSE_FIELDS:
        validation[field] = False
    prior = {
        "record_type": "hypothesis_state",
        "schema_version": "alphafactory_candidate_registry.v1",
        "hypothesis_id": hypothesis_id,
        "ea_name": ea_name,
        "state": "screened",
        "parent_candidate": "HYP-STBS-XAUUSD-M15-012",
        "feature_family": "frozen-family",
        "lane": "frozen-lane",
        "symbol": "XAUUSD",
        "timeframe": "M15",
        "window": {"from": "2018.01.02", "to": "2022.12.30"},
        "model": 0,
        "source_provenance": "frozen",
        "source_path": source_path,
        "source_hash": _sha(source),
        "prereg_path": prereg_path,
        "prereg_sha256": _sha(prereg),
        "exact_overrides": "frozen",
        "evidence_contract_kind": "economic",
        "acceptance_contract": acceptance,
        "verdict": "SCREENED_INITIAL",
        "reason": "initial",
        "updated_at_utc": "2026-08-09T13:29:45Z",
        "run_ids": [],
        "metrics": {
            "mt5_attempt_limit": 1,
            "mt5_attempts_consumed": 0,
            "model0_runs": 0,
            "mt5_launches": 0,
            "orders_executed": 0,
            "trades_simulated": 0,
            "returns_computed": 0,
            "performance_trials_executed": 0,
            "economics_executed": False,
            "research_validation_opened": False,
            "research_holdout_opened": False,
        },
        "validation": validation,
    }
    row = copy.deepcopy(prior)
    row["verdict"] = "SCREENED_PACKET_BOUND"
    row["reason"] = "outcome-blind hardening"
    row["updated_at_utc"] = "2026-08-09T14:30:00Z"
    successor = row["validation"]
    successor.update(
        {
            "probe_status": SUT.MODEL0_PREEXECUTION_PROBE_STATUS,
            "one_shot_economic_harness_version": "model0-economic-one-shot-v1",
            "authorized_timeout_sec": 900,
            "task_packet_path": packet_path,
            "task_packet_sha256": _sha(packet_file),
            "authorized_packet_registry_sha256": prior_registry_sha,
            "authorized_packet_registry_row_sha256": prior_row_sha,
            "authorized_packet_git_status_sha256": git_status_sha,
            "execute_gate_prior_registry_line": 1,
            "execute_gate_prior_registry_sha256": prior_registry_sha,
            "execute_gate_prior_registry_row_sha256": prior_row_sha,
            "authorized_current_git_status_sha256": git_status_sha,
            "pre_execution_harness_addendum_path": addendum_path,
            "pre_execution_harness_addendum_sha256": _sha(addendum),
            "reviewed_research_loop_path": runner_path,
            "reviewed_research_loop_sha256": _sha(runner),
            "reviewed_alpha_ps1_sha256": _sha(alpha),
            "reviewed_cost_test_path": cost_test_path,
            "reviewed_cost_test_sha256": _sha(cost_test),
            "reviewed_ea_golden_path_test_path": golden_test_path,
            "reviewed_ea_golden_path_test_sha256": _sha(golden_test),
            "reviewed_registry_validator_path": validator_path,
            "reviewed_registry_validator_sha256": _sha(validator),
            "reviewed_registry_model0_preexecution_test_path": validator_test_path,
            "reviewed_registry_model0_preexecution_test_sha256": _sha(validator_test),
            "reviewed_task_packet_builder_path": packet_builder_path,
            "reviewed_task_packet_builder_sha256": _sha(packet_builder),
        }
    )
    return prior, row, prior_registry_sha, prior_row_sha


def _errors(
    monkeypatch,
    tmp_path: Path,
    mutate=None,
    *,
    verify_live_code_bindings: bool = True,
) -> list[str]:
    prior, row, prior_registry_sha, prior_row_sha = _fixture(monkeypatch, tmp_path)
    if mutate is not None:
        mutate(row, tmp_path)
    return SUT._model0_preexecution_authority_hardening_errors(
        1,
        prior_row_sha,
        prior_registry_sha,
        prior,
        2,
        row,
        verify_live_code_bindings=verify_live_code_bindings,
    )


def test_exact_model0_preexecution_hardening_passes(monkeypatch, tmp_path) -> None:
    assert _errors(monkeypatch, tmp_path) == []


def test_historical_row_keeps_immutable_packet_but_does_not_rehash_mutable_code(
    monkeypatch, tmp_path
) -> None:
    def mutate_code(row, root: Path) -> None:
        for path_field in (
            "reviewed_research_loop_path",
            "reviewed_alpha_ps1_path",
            "reviewed_cost_test_path",
            "reviewed_ea_golden_path_test_path",
            "reviewed_registry_validator_path",
            "reviewed_registry_model0_preexecution_test_path",
            "reviewed_task_packet_builder_path",
        ):
            (root / row["validation"][path_field]).write_bytes(b"newer lawful bytes")

    assert (
        _errors(
            monkeypatch,
            tmp_path / "historical",
            mutate_code,
            verify_live_code_bindings=False,
        )
        == []
    )

    def mutate_packet(row, root: Path) -> None:
        (root / row["validation"]["task_packet_path"]).write_bytes(b"drifted packet")

    packet_errors = _errors(
        monkeypatch,
        tmp_path / "packet",
        mutate_packet,
        verify_live_code_bindings=False,
    )
    assert any("task_packet_path: SHA256 mismatch" in error for error in packet_errors)


def test_strategy_or_attempt_mutation_fails(monkeypatch, tmp_path) -> None:
    strategy_errors = _errors(
        monkeypatch,
        tmp_path / "strategy",
        lambda row, _root: row.update(source_hash="F" * 64),
    )
    attempt_errors = _errors(
        monkeypatch,
        tmp_path / "attempt",
        lambda row, _root: row["metrics"].update(mt5_attempts_consumed=1),
    )
    permission_errors = _errors(
        monkeypatch,
        tmp_path / "permission",
        lambda row, _root: row["validation"].update(optimization_authorized=True),
    )

    assert any("prohibited root change 'source_hash'" in error for error in strategy_errors)
    assert any("mt5_attempts_consumed" in error for error in attempt_errors)
    assert any("optimization_authorized" in error for error in permission_errors)


def test_packet_threshold_or_prior_registry_mutation_fails(monkeypatch, tmp_path) -> None:
    def mutate_packet(row: dict, root: Path) -> None:
        packet_path = root / Path(row["validation"]["task_packet_path"])
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["baseline_acceptance_contract"]["min_completed_trades"] = 499
        packet_path.write_text(json.dumps(packet, separators=(",", ":")), encoding="utf-8")
        row["validation"]["task_packet_sha256"] = _sha(packet_path)

    packet_errors = _errors(monkeypatch, tmp_path / "packet", mutate_packet)
    registry_errors = _errors(
        monkeypatch,
        tmp_path / "registry",
        lambda row, _root: row["validation"].update(
            execute_gate_prior_registry_row_sha256="D" * 64
        ),
    )

    assert any("baseline mapping" in error for error in packet_errors)
    assert any("execute_gate_prior_registry_row_sha256 mismatch" in error for error in registry_errors)


def test_bound_harness_tamper_fails(monkeypatch, tmp_path) -> None:
    def tamper(row: dict, root: Path) -> None:
        runner = root / Path(row["validation"]["reviewed_research_loop_path"])
        runner.write_bytes(runner.read_bytes() + b"# drift\n")

    errors = _errors(monkeypatch, tmp_path, tamper)
    assert any("reviewed_research_loop_path: SHA256 mismatch" in error for error in errors)
