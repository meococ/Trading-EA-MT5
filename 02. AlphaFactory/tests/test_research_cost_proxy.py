from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import pytest


ALPHA_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ALPHA_ROOT / "tools" / "build_verified_cost_artifact.py"
UNIFIED_PATH = ALPHA_ROOT / "analysis" / "unified_validation.py"
RUNNER_PATH = ALPHA_ROOT / "tools" / "research_loop_engine.ps1"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


def _load_builder():
    spec = importlib.util.spec_from_file_location("research_cost_proxy_builder", BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_unified():
    spec = importlib.util.spec_from_file_location("research_cost_proxy_unified", UNIFIED_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _run_model0_one_shot_harness(
    tmp_path: Path,
    *,
    packet_mutation: dict[str, object] | None = None,
    validation_mutation: dict[str, object] | None = None,
    metrics_mutation: dict[str, object] | None = None,
    create_claim: bool = False,
) -> dict:
    if POWERSHELL is None:
        pytest.skip("PowerShell is required for the Model0 one-shot harness")
    fake_root = tmp_path / "repo"
    runtime = fake_root / "02. AlphaFactory" / "runtime"
    runtime.mkdir(parents=True)
    alpha = fake_root / "02. AlphaFactory" / "alpha.ps1"
    alpha.write_text("# frozen alpha\n", encoding="utf-8")
    bound_controls = {
        "pre_execution_harness_addendum": fake_root / "addendum.md",
        "reviewed_task_packet_builder": fake_root / "packet_builder.py",
        "reviewed_registry_validator": fake_root / "registry_validator.py",
        "reviewed_registry_model0_preexecution_test": fake_root / "registry_test.py",
        "reviewed_cost_test": fake_root / "cost_test.py",
        "reviewed_ea_golden_path_test": fake_root / "golden_test.py",
    }
    for label, path in bound_controls.items():
        path.write_text(f"# {label}\n", encoding="utf-8")
    packet_path = fake_root / "packet.json"
    baseline = {
        "min_completed_trades": 500,
        "min_direction_share": 0.30,
        "max_year_trade_share": 0.30,
        "require_positive_cost_expectancy": True,
        "require_all_calendar_years_positive": True,
    }
    packet = {
        "attempt_id": "STBS013-MODEL0-TRAIN-001",
        "attempt_limit": 1,
        "timeout_sec": 900,
        "registry_sha256": "A" * 64,
        "registry_row_sha256": "B" * 64,
        "git_status_sha256": "C" * 64,
        "baseline_acceptance_contract": baseline,
        "performance_metrics_authorized": True,
        "economics_authorized": True,
        "promotion_eligible": False,
    }
    packet.update(packet_mutation or {})
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    registry_baseline = {
        "min_completed_trades": baseline["min_completed_trades"],
        "min_direction_share": baseline["min_direction_share"],
        "max_year_trade_share": baseline["max_year_trade_share"],
        "require_positive_mean_x1_net_r": baseline["require_positive_cost_expectancy"],
        "require_each_calendar_year_positive_x1_net_r": baseline[
            "require_all_calendar_years_positive"
        ],
    }
    validation = {
        "authority": "MODEL0_TRAIN_FALSIFICATION_ONLY",
        "one_shot_economic_harness_version": "model0-economic-one-shot-v1",
        "probe_status": "SCREENED_STBS013_ONE_SHOT_PACKET_BOUND_MODEL0_BASELINE_AUTHORIZED",
        "mt5_train_run_authorized": True,
        "mt5_attempt_id": "STBS013-MODEL0-TRAIN-001",
        "mt5_attempt_limit": 1,
        "same_id_retry_authorized": False,
        "authorized_timeout_sec": 900,
        "task_packet_path": "packet.json",
        "task_packet_sha256": _sha(packet_path),
        "authorized_packet_registry_sha256": "A" * 64,
        "authorized_packet_registry_row_sha256": "B" * 64,
        "authorized_packet_git_status_sha256": "C" * 64,
        "execute_gate_prior_registry_line": 1,
        "execute_gate_prior_registry_sha256": "D" * 64,
        "execute_gate_prior_registry_row_sha256": "E" * 64,
        "authorized_current_git_status_sha256": "C" * 64,
        "reviewed_research_loop_sha256": _sha(RUNNER_PATH),
        "reviewed_alpha_ps1_sha256": _sha(alpha),
        "baseline_acceptance_contract": registry_baseline,
    }
    for label, path in bound_controls.items():
        validation[f"{label}_path"] = path.relative_to(fake_root).as_posix()
        validation[f"{label}_sha256"] = _sha(path)
    for field in (
        "mt5_authorized",
        "model0_authorized",
        "model0_data_acquisition_authorized",
        "model0_performance_authorized",
        "source_run_authorized",
        "run_compile_authorized",
        "mql5_compile_authorized",
        "trade_api_authorized",
        "performance_metrics_authorized",
        "outcome_prices_authorized",
        "post_event_ohlc_authorized",
        "artifact_collection_authorized",
        "economics_authorized",
        "research_falsification_authorized",
    ):
        validation[field] = True
    for field in (
        "packet_build_authorized",
        "model0_audit_run_authorized",
        "model4_authorized",
        "model4_data_acquisition_authorized",
        "model4_performance_authorized",
        "compile_authorized",
        "standalone_compile_authorized",
        "comparator_execution_authorized",
        "visual_mode_authorized",
        "network_authorized",
        "paid_requests_authorized",
        "optimization_authorized",
        "validation_authorized",
        "holdout_authorized",
        "research_validation_access_authorized",
        "research_holdout_access_authorized",
        "validation_access_authorized",
        "holdout_access_authorized",
        "economic_validity_authorized",
        "promotion_eligible",
        "paper_trading_authorized",
        "live_trading_authorized",
        "market_edge_claim_authorized",
        "registry_mutation_allowed",
    ):
        validation[field] = False
    validation.update(validation_mutation or {})
    metrics = {"mt5_attempts_consumed": 0}
    metrics.update(metrics_mutation or {})
    validation_path = fake_root / "validation.json"
    validation_path.write_text(json.dumps(validation), encoding="utf-8")
    metrics_path = fake_root / "metrics.json"
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
    harness = fake_root / "harness.ps1"
    harness.write_text(
        r'''
param([string]$Engine,[string]$Root,[string]$PacketPath,[string]$ValidationPath,[string]$MetricsPath,[string]$AlphaPath)
$ErrorActionPreference='Stop'; $repoRoot=$Root; $runtimeRoot=Join-Path $Root '02. AlphaFactory\runtime'; $alphaPs1=$AlphaPath
$tokens=$null; $parseErrors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($Engine,[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count){throw ($parseErrors|ForEach-Object{$_.Message}|Out-String)}
$needed=@('Get-Sha256IfExists','Test-Sha256Text','Test-ProvenanceObject','Get-ObjectProperty','Get-RepoRelativePath','Test-ScopedModel0EconomicPriorRegistryPacket','Get-Model0EconomicAttemptPaths','Add-Model0EconomicLaunchAuthorityBlockers','New-Model0EconomicLaunchClaim','Write-Model0EconomicAttemptTerminal')
foreach($name in $needed){$fn=$ast.Find({param($n)$n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true);if($null -eq $fn){throw "Missing $name"};Invoke-Expression $fn.Extent.Text}
$packet=Get-Content -Raw -LiteralPath $PacketPath|ConvertFrom-Json; $validation=Get-Content -Raw -LiteralPath $ValidationPath|ConvertFrom-Json; $metrics=Get-Content -Raw -LiteralPath $MetricsPath|ConvertFrom-Json
$contract=[pscustomobject]@{HypothesisId='HYP-STBS-XAUUSD-M15-013';RegistryState='screened';RegistryLine=2;RegistryRowSha256=[string]::new('F',64);LatestRow=[pscustomobject]@{validation=$validation;metrics=$metrics}}
$binding=[pscustomobject]@{Model=0;RunRole='control';TimeoutSec=900;GitStatusSha256=[string]::new('C',64)}
$packetResult=[pscustomobject]@{Packet=$packet;PacketPath=$PacketPath;PacketSha256=Get-Sha256IfExists $PacketPath;BaselineAcceptanceContract=$packet.baseline_acceptance_contract}
$blockers=New-Object System.Collections.Generic.List[string]
Add-Model0EconomicLaunchAuthorityBlockers $contract $binding $packetResult $Engine $blockers
$created=$false;$duplicateRejected=$false;$terminalCreated=$false
if($env:CREATE_MODEL0_CLAIM -ceq '1' -and $blockers.Count -eq 0){$claim=New-Model0EconomicLaunchClaim $contract $binding $packetResult;$created=Test-Path -LiteralPath $claim.Path;try{[void](New-Model0EconomicLaunchClaim $contract $binding $packetResult)}catch{$duplicateRejected=$true};$terminal=Write-Model0EconomicAttemptTerminal $claim 'COMPLETE' 'RUN1' 'RUN_DIR';$terminalCreated=Test-Path -LiteralPath $terminal.Path}
[pscustomobject]@{scoped=Test-ScopedModel0EconomicPriorRegistryPacket $packet $contract $binding $PacketPath;blockers=@($blockers);created=$created;duplicate_rejected=$duplicateRejected;terminal_created=$terminalCreated}|ConvertTo-Json -Depth 6
''',
        encoding="utf-8",
    )
    env = {**os.environ, "CREATE_MODEL0_CLAIM": "1" if create_claim else "0"}
    result = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(harness), "-Engine", str(RUNNER_PATH), "-Root", str(fake_root), "-PacketPath", str(packet_path), "-ValidationPath", str(validation_path), "-MetricsPath", str(metrics_path), "-AlphaPath", str(alpha)],
        cwd=ALPHA_ROOT.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def _proxy_fixture(tmp_path: Path) -> tuple[dict, Path, dict]:
    spread_path = tmp_path / "spread.csv"
    _write_csv(
        spread_path,
        ["timestamp", "symbol", "bid", "ask"],
        [
            {"timestamp": "2024-01-02 08:00:00", "symbol": "XAUUSD", "bid": 2040.00, "ask": 2040.20},
            {"timestamp": "2025-12-24 08:00:00", "symbol": "XAUUSD", "bid": 2600.00, "ask": 2600.25},
        ],
    )

    commission_path = tmp_path / "commission.csv"
    _write_csv(
        commission_path,
        [
            "position_id",
            "symbol",
            "account_currency",
            "round_turn_account_per_lot",
            "source_kind",
        ],
        [
            {
                "position_id": str(index + 1),
                "symbol": "XAUUSD",
                "account_currency": "USD",
                "round_turn_account_per_lot": 4.4 if index == 29 else 2.0,
                "source_kind": "strategy_tester_simulation",
            }
            for index in range(30)
        ],
    )

    quote_path = tmp_path / "quote_latency.csv"
    quote_rows: list[dict[str, object]] = []
    start = datetime(2026, 7, 14, 8, 0, 0)
    for index in range(50):
        reference = 2400.0 + index * 0.01
        adverse_pips = index % 5
        reference_time = start + timedelta(seconds=index * 2)
        future_time = reference_time + timedelta(seconds=1)
        quote_rows.append(
            {
                "sample_id": f"BUY-{index}",
                "reference_timestamp": reference_time.isoformat(),
                "future_timestamp": future_time.isoformat(),
                "symbol": "XAUUSD",
                "side": "BUY",
                "reference_side": "ask",
                "reference_price": reference,
                "future_quote_price": reference + adverse_pips * 0.01,
                "pip_size": 0.01,
                "latency_ms": 1000,
                "actual_delay_ms": 1000,
            }
        )
        quote_rows.append(
            {
                "sample_id": f"SELL-{index}",
                "reference_timestamp": reference_time.isoformat(),
                "future_timestamp": future_time.isoformat(),
                "symbol": "XAUUSD",
                "side": "SELL",
                "reference_side": "bid",
                "reference_price": reference,
                "future_quote_price": reference - adverse_pips * 0.01,
                "pip_size": 0.01,
                "latency_ms": 1000,
                "actual_delay_ms": 1000,
            }
        )
    quote_fields = list(quote_rows[0])
    _write_csv(quote_path, quote_fields, quote_rows)

    manifest = {
        "broker_fingerprint": "A" * 64,
        "server_fingerprint": "B" * 64,
        "account_fingerprint": "C" * 64,
        "data_fingerprint": "D" * 64,
        "symbol": "XAUUSD",
        "from": "2024.01.01",
        "to": "2025.12.25",
        "fingerprint_basis": {
            "broker": "Five Percent Online Ltd",
            "server": "FivePercentOnline-Real (Build 6006)",
            "currency": "USD",
            "digits": 2,
            "point": 0.01,
            "pip_size": 0.01,
        },
    }
    payload = {
        "schema_version": "alphafactory_cost_source_manifest.v1",
        "evidence_tier": "RESEARCH_PROXY",
        "provenance_status": "VERIFIED_RESEARCH_PROXY",
        "audit_status": "PASS_RESEARCH_ONLY",
        "verdict": "PASS_RESEARCH_ONLY",
        "promotion_eligible": False,
        "broker": manifest["fingerprint_basis"]["broker"],
        "server": manifest["fingerprint_basis"]["server"],
        "account_currency": "USD",
        "broker_fingerprint": manifest["broker_fingerprint"],
        "server_fingerprint": manifest["server_fingerprint"],
        "account_fingerprint": manifest["account_fingerprint"],
        "data_fingerprint": manifest["data_fingerprint"],
        "symbol": "XAUUSD",
        "from": manifest["from"],
        "to": manifest["to"],
        "symbol_geometry": {"digits": 2, "point": 0.01, "pip_size": 0.01},
        "historical_spread_provenance": {
            "verification_status": "VERIFIED",
            "symbol": "XAUUSD",
            "source": spread_path.name,
            "source_sha256": _sha(spread_path),
            "coverage": {
                "from": manifest["from"],
                "to": manifest["to"],
                "sample_count": 2,
                "total_count": 2,
                "coverage_ratio": 1.0,
            },
        },
        "commission_provenance": {
            "verification_status": "VERIFIED_RESEARCH_PROXY",
            "symbol": "XAUUSD",
            "value": 4.4,
            "statistic": "maximum",
            "sample_count": 30,
            "same_symbol_lifecycles": True,
            "source_kind": "strategy_tester_simulation",
            "method": "maximum tester-observed round-turn commission per lot",
            "source": commission_path.name,
            "source_sha256": _sha(commission_path),
        },
        "slippage_provenance": {
            "verification_status": "VERIFIED_RESEARCH_PROXY",
            "symbol": "XAUUSD",
            "source": quote_path.name,
            "source_sha256": _sha(quote_path),
            "sample_count": 100,
            "buy_count": 50,
            "sell_count": 50,
            "independent_reference": False,
            "independent_quote_reference": True,
            "fill_observed": False,
            "buy_reference_side": "ask",
            "sell_reference_side": "bid",
            "slippage_unit": "pips",
            "fixed_latency_ms": 1000,
            "max_quote_wait_ms": 500,
            "method": "non-overlapping fixed-latency future executable quote proxy",
            "p90_buy": 4.0,
            "p90_sell": 4.0,
            "p90_roundturn": 8.0,
        },
        "direction_aware_methodology": {
            "verification_status": "VERIFIED_RESEARCH_PROXY",
            "direction_aware": True,
            "long_cost_treatment": "ask-to-future-ask adverse move",
            "short_cost_treatment": "bid-to-future-bid adverse move",
        },
    }
    source_path = tmp_path / "cost_source_manifest.json"
    source_path.write_text(json.dumps(payload), encoding="utf-8")
    return payload, source_path, manifest


def test_research_proxy_cost_source_is_explicitly_non_promotable(tmp_path: Path) -> None:
    builder = _load_builder()
    payload, source_path, manifest = _proxy_fixture(tmp_path)

    result = builder.validate_cost_source(payload, source_path, manifest)

    assert result["evidence_tier"] == "RESEARCH_PROXY"
    assert result["promotion_eligible"] is False
    assert result["commission_value"] == pytest.approx(4.4)
    assert result["slippage_p90_roundturn"] == pytest.approx(8.0)
    assert result["slippage"]["fill_observed"] is False


def test_research_proxy_root_cannot_claim_promotion_eligibility(tmp_path: Path) -> None:
    builder = _load_builder()
    payload, source_path, manifest = _proxy_fixture(tmp_path)
    payload["promotion_eligible"] = True

    with pytest.raises(ValueError, match="promotion_eligible"):
        builder.validate_cost_source(payload, source_path, manifest)


def test_unified_validator_requires_explicit_proxy_opt_in() -> None:
    unified = _load_unified()
    payload = {
        "schema_version": "research_execution_cost_proxy.v1",
        "provenance_status": "VERIFIED_RESEARCH_PROXY",
        "stress_mode": "run_bound_research_cost_proxy_repricing",
        "promotion_eligible": False,
        "execution_provenance": {
            "evidence_tier": "RESEARCH_PROXY",
            "promotion_eligible": False,
        },
    }

    with pytest.raises(ValueError, match="explicit opt-in"):
        unified._cost_evidence_scope(payload, allow_research_cost_proxy=False)

    scope = unified._cost_evidence_scope(payload, allow_research_cost_proxy=True)
    assert scope == {
        "evidence_tier": "RESEARCH_PROXY",
        "research_falsification_eligible": True,
        "promotion_eligible": False,
    }


def test_runner_exposes_fail_closed_research_proxy_switch() -> None:
    text = RUNNER_PATH.read_text(encoding="utf-8-sig")
    assert "[switch]$AllowResearchCostProxy" in text
    assert "cost_evidence_tier" in text
    assert "RESEARCH_PROXY requires RunRole=control" in text
    assert '"--allow-research-cost-proxy"' in text
    assert "$backtestParameters = @{" in text
    assert "& $alphaPs1 backtest $EaName @backtestParameters" in text


def test_report_trade_window_is_distinct_from_tester_preload() -> None:
    builder = _load_builder()
    inside = builder.Deal(
        datetime(2018, 1, 2, 7), 1, "XAUUSD", "buy", "in", 0.1, 1300.0,
        11, 0.0, 0.0, 0.0, 10000.0, "entry",
    )
    boundary = builder.Deal(
        datetime(2022, 12, 30, 20), 2, "XAUUSD", "sell", "out", 0.1, 1800.0,
        12, -1.0, 0.0, 10.0, 10009.0, "exit",
    )

    result = builder.validate_report_trade_window(
        [inside, boundary], "XAUUSD", "2018.01.02", "2022.12.30"
    )
    assert result["trade_deal_count"] == 2
    assert result["boundary"] == "inclusive_calendar_dates"

    outside = builder.Deal(
        datetime(2017, 12, 31, 23), 3, "XAUUSD", "buy", "in", 0.1, 1299.0,
        13, 0.0, 0.0, 0.0, 10000.0, "preload leak",
    )
    with pytest.raises(ValueError, match="outside the frozen economic cost window"):
        builder.validate_report_trade_window(
            [outside, boundary], "XAUUSD", "2018.01.02", "2022.12.30"
        )


def _baseline_fixture(unified):
    trades = []
    repricing = []
    for offset, year in enumerate(range(2018, 2023)):
        for side in ("buy", "sell"):
            entry = datetime(year, 6, 1, 8 + offset)
            exit_time = entry + timedelta(hours=2)
            trades.append(unified.Trade(entry, exit_time, side, 10.0, 1, "", ""))
            repricing.append(
                {
                    "exit_time": exit_time.strftime("%Y.%m.%d %H:%M:%S"),
                    "direction": side.upper(),
                    "gross_r": 0.50,
                    "swap_r": 0.0,
                    "commission_r": 0.05,
                    "slippage_r": 0.05,
                }
            )
    contract = {
        "min_completed_trades": 10,
        "min_direction_share": 0.30,
        "max_year_trade_share": 0.30,
        "require_positive_cost_expectancy": True,
        "require_all_calendar_years_positive": True,
    }
    return trades, {
        "economic_window": {
            "from": "2018.01.02",
            "to": "2022.12.30",
            "boundary": "inclusive_calendar_dates",
        },
        "trade_repricing": repricing,
    }, contract


def test_baseline_falsification_gates_pass_and_fail_closed() -> None:
    unified = _load_unified()
    trades, cost, contract = _baseline_fixture(unified)
    gates = unified._baseline_falsification_gates(
        trades, cost, "2018.01.02", "2022.12.30", contract, "cost.json"
    )
    assert gates
    assert {gate["status"] for gate in gates.values()} == {"PASS"}

    imbalanced = [
        unified.Trade(t.entry_time, t.exit_time, "buy", t.profit, t.n_out_deals, t.exit_comment, t.entry_comment)
        for t in trades
    ]
    imbalance_gates = unified._baseline_falsification_gates(
        imbalanced, cost, "2018.01.02", "2022.12.30", contract, "cost.json"
    )
    assert imbalance_gates["direction_balance_baseline"]["status"] == "FAIL"

    negative_year_cost = json.loads(json.dumps(cost))
    negative_year_cost["trade_repricing"][0]["gross_r"] = -5.0
    negative_year_cost["trade_repricing"][1]["gross_r"] = -5.0
    negative_gates = unified._baseline_falsification_gates(
        trades, negative_year_cost, "2018.01.02", "2022.12.30", contract, "cost.json"
    )
    assert negative_gates["all_calendar_years_positive_baseline"]["status"] == "FAIL"

    invalid_contract = dict(contract)
    invalid_contract["require_positive_cost_expectancy"] = False
    blocked = unified._baseline_falsification_gates(
        trades, cost, "2018.01.02", "2022.12.30", invalid_contract, "cost.json"
    )
    assert blocked["economic_window_coverage"]["status"] == "BLOCKED"

    wrong_window_cost = json.loads(json.dumps(cost))
    wrong_window_cost["economic_window"]["from"] = "2018.01.03"
    wrong_window = unified._baseline_falsification_gates(
        trades, wrong_window_cost, "2018.01.02", "2022.12.30", contract, "cost.json"
    )
    assert wrong_window["economic_window_coverage"]["status"] == "FAIL"


def test_runner_freezes_economic_window_and_baseline_verdict() -> None:
    text = RUNNER_PATH.read_text(encoding="utf-8-sig")
    assert "function Resolve-EconomicWindow" in text
    assert "function Resolve-BaselineAcceptanceContract" in text
    assert '"--economic-from", $packetResult.EconomicFrom' in text
    assert "baseline_falsification_verdict" in text
    assert "Research-proxy validation summary lacks the frozen baseline falsification verdict" in text


def test_inclusive_economic_cadence_counts_both_boundary_days() -> None:
    unified = _load_unified()
    start = datetime(2018, 1, 2).date()
    end = datetime(2022, 12, 30).date()
    assert unified._elapsed_window_days(start, end, inclusive=True) == (end - start).days + 1
    assert unified._elapsed_window_days(start, start, inclusive=True) == 1
    assert unified._elapsed_window_days(start, end, inclusive=False) == (end - start).days
    assert unified._elapsed_window_days(end, start, inclusive=True) is None


def test_run_meta_contract_rejects_runtime_identity_and_row_count_drift(tmp_path: Path) -> None:
    builder = _load_builder()
    lifecycle_path = tmp_path / "XAUUSD_LifecycleTrades_HYP013_RUN.csv"
    fields = sorted(builder.REQUIRED_LIFECYCLE_COLUMNS)
    _write_csv(lifecycle_path, fields, [{field: "0" for field in fields}])
    meta_path = tmp_path / "XAUUSD_RunMeta_HYP013_RUN.json"
    contract = {
        "schema_version": "alphafactory_run_meta.v1",
        "hypothesis_id": "HYP-STBS-XAUUSD-M15-013",
        "variant_tag": "STBS_H1_FLIP_M15_BURST_TRADE_FSM_V3_TELEMETRY",
        "magic": 5604113,
        "audit_only": False,
        "promotion_eligible": False,
        "runtime_failed": False,
        "reconcile_lifecycle_rows": True,
    }
    manifest = {
        "ea_name": "EA_SupertrendBurstScalperTradeV3",
        "symbol": "XAUUSD",
        "hypothesis_id": contract["hypothesis_id"],
    }
    payload = {
        "schema_version": contract["schema_version"],
        "run_id": "HYP013_RUN",
        "ea_name": manifest["ea_name"],
        "symbol": manifest["symbol"],
        "telemetry_profile": "lifecycle-v3",
        "hypothesis_id": contract["hypothesis_id"],
        "variant_tag": contract["variant_tag"],
        "magic": contract["magic"],
        "audit_only": False,
        "promotion_eligible": False,
        "diagnostic": {"runtime_failed": False, "lifecycle_rows": 1},
    }

    def validate(current: dict):
        meta_path.write_text(json.dumps(current), encoding="utf-8")
        return builder.validate_run_meta(
            meta_path, _sha(meta_path), lifecycle_path, manifest, contract
        )

    evidence = validate(payload)
    assert evidence["semantic_validation"] == {
        "runtime_failed": False,
        "declared_lifecycle_rows": 1,
        "actual_lifecycle_rows": 1,
        "row_count_reconciled": True,
    }

    runtime_failed = json.loads(json.dumps(payload))
    runtime_failed["diagnostic"]["runtime_failed"] = True
    with pytest.raises(ValueError, match="runtime_failed"):
        validate(runtime_failed)

    wrong_identity = json.loads(json.dumps(payload))
    wrong_identity["variant_tag"] = "OTHER"
    with pytest.raises(ValueError, match="variant_tag"):
        validate(wrong_identity)

    audit_enabled = json.loads(json.dumps(payload))
    audit_enabled["audit_only"] = True
    with pytest.raises(ValueError, match="audit_only"):
        validate(audit_enabled)

    wrong_count = json.loads(json.dumps(payload))
    wrong_count["diagnostic"]["lifecycle_rows"] = 2
    with pytest.raises(ValueError, match="data-row count"):
        validate(wrong_count)


def test_model0_economic_attempt_is_packet_bound_durable_and_one_shot(tmp_path: Path) -> None:
    result = _run_model0_one_shot_harness(tmp_path, create_claim=True)
    assert result["scoped"] is True
    assert result["blockers"] == []
    assert result["created"] is True
    assert result["duplicate_rejected"] is True
    assert result["terminal_created"] is True


@pytest.mark.parametrize(
    ("packet_mutation", "validation_mutation", "metrics_mutation", "needle"),
    [
        ({"timeout_sec": 901}, None, None, "one-shot screened authority"),
        ({"baseline_acceptance_contract": {
            "min_completed_trades": 501,
            "min_direction_share": 0.30,
            "max_year_trade_share": 0.30,
            "require_positive_cost_expectancy": True,
            "require_all_calendar_years_positive": True,
        }}, None, None, "min_completed_trades"),
        ({"performance_metrics_authorized": False}, None, None, "performance_metrics_authorized"),
        (None, {"same_id_retry_authorized": True}, None, "one-shot screened authority"),
        (None, {"reviewed_registry_validator_sha256": "D" * 64}, None, "candidate-registry validator bytes"),
        (None, None, {"mt5_attempts_consumed": 1}, "one-shot screened authority"),
    ],
)
def test_model0_economic_authority_mutations_fail_closed(
    tmp_path: Path,
    packet_mutation: dict[str, object] | None,
    validation_mutation: dict[str, object] | None,
    metrics_mutation: dict[str, object] | None,
    needle: str,
) -> None:
    result = _run_model0_one_shot_harness(
        tmp_path,
        packet_mutation=packet_mutation,
        validation_mutation=validation_mutation,
        metrics_mutation=metrics_mutation,
    )
    assert result["scoped"] is False or result["blockers"]
    assert needle in "\n".join(result["blockers"])
