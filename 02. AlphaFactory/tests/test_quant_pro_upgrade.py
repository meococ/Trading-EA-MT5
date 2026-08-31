from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest


ALPHA_ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, relative_path: str):
    path = ALPHA_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_optimization_csv(path: Path, selected_sharpe: float = 1.38) -> None:
    if selected_sharpe == 1.38:
        sharpe_values = [1.00, 1.10, 1.40, 1.38, 1.39, 0.70]
    else:
        sharpe_values = [
            selected_sharpe - 0.50,
            selected_sharpe - 0.40,
            selected_sharpe - 0.20,
            selected_sharpe,
            selected_sharpe - 0.30,
            selected_sharpe - 0.60,
        ]
    path.write_text(
        "Pass,Result,Profit,Profit Factor,Sharpe Ratio,Custom,Trades,Fast,Slow\n"
        f"1,1.0,100,1.20,{sharpe_values[0]:.12f},{sharpe_values[0]:.12f},100,10,50\n"
        f"2,1.1,110,1.25,{sharpe_values[1]:.12f},{sharpe_values[1]:.12f},100,10,60\n"
        f"3,1.4,140,1.40,{sharpe_values[2]:.12f},{sharpe_values[2]:.12f},100,20,50\n"
        f"4,1.38,138,1.38,{sharpe_values[3]:.12f},{sharpe_values[3]:.12f},100,20,60\n"
        f"5,1.39,139,1.39,{sharpe_values[4]:.12f},{sharpe_values[4]:.12f},100,30,50\n"
        f"6,0.7,70,0.90,{sharpe_values[5]:.12f},{sharpe_values[5]:.12f},100,30,60\n",
        encoding="utf-8",
    )


def test_optimization_import_counts_every_pass_and_uses_real_surface(tmp_path: Path) -> None:
    mod = _load_module("af_param_optimizer", "analysis/param_optimizer.py")
    report_path = tmp_path / "optimizer.csv"
    _write_optimization_csv(report_path)

    report = mod.parse_optimization_report(report_path)
    assert report.total_passes == 6
    assert [row.pass_id for row in report.rows] == ["1", "2", "3", "4", "5", "6"]

    surface = mod.build_parameter_surface(
        report.rows,
        param1="Fast",
        param2="Slow",
        metric="Sharpe Ratio",
        plateau_fraction=0.95,
    )
    assert surface["grid_shape"] == [3, 2]
    assert surface["best"]["value"] == pytest.approx(1.40)
    assert surface["matrix"] == [[1.0, 1.1], [1.4, 1.38], [1.39, 0.7]]
    assert surface["plateau"]["largest_component_cells"] == 3

    with pytest.raises(ValueError, match="other optimizer axes vary"):
        mod.build_parameter_surface(
            [*report.rows, mod.OptimizationPass("7", dict(report.rows[0].values))],
            param1="Fast",
            param2="Slow",
            metric="Sharpe Ratio",
        )

    source = (ALPHA_ROOT / "analysis/param_optimizer.py").read_text(encoding="utf-8")
    assert "random.gauss" not in source


def test_spreadsheetml_optimization_report_is_supported(tmp_path: Path) -> None:
    mod = _load_module("af_param_optimizer_xml", "analysis/param_optimizer.py")
    report_path = tmp_path / "optimizer.xml"
    report_path.write_text(
        """<?xml version="1.0"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
 <Worksheet ss:Name="Optimization Results"><Table>
  <Row><Cell><Data ss:Type="String">Pass</Data></Cell><Cell><Data ss:Type="String">Custom</Data></Cell><Cell><Data ss:Type="String">Fast</Data></Cell><Cell><Data ss:Type="String">Slow</Data></Cell></Row>
  <Row><Cell><Data ss:Type="Number">1</Data></Cell><Cell><Data ss:Type="Number">1.1</Data></Cell><Cell><Data ss:Type="Number">10</Data></Cell><Cell><Data ss:Type="Number">50</Data></Cell></Row>
  <Row><Cell><Data ss:Type="Number">2</Data></Cell><Cell><Data ss:Type="Number">1.2</Data></Cell><Cell><Data ss:Type="Number">20</Data></Cell><Cell><Data ss:Type="Number">60</Data></Cell></Row>
 </Table></Worksheet>
</Workbook>
""",
        encoding="utf-8",
    )

    report = mod.parse_optimization_report(report_path)
    assert report.format == "spreadsheetml"
    assert report.total_passes == 2
    assert report.rows[1].values["Custom"] == pytest.approx(1.2)


def test_dsr_requires_exact_trial_count_and_matching_sr_semantics(tmp_path: Path) -> None:
    mod = _load_module("af_param_optimizer_dsr", "analysis/param_optimizer.py")
    returns = [0.8, -0.2, 1.1, -0.3, 0.6, -0.1, 0.4, -0.2, 0.9, -0.4]
    selected_sr = mod.sample_sharpe(returns)
    report_path = tmp_path / "optimizer.csv"
    _write_optimization_csv(report_path, selected_sharpe=selected_sr)
    returns_path = tmp_path / "selected_returns.csv"
    returns_path.write_text(
        "net_r\n" + "\n".join(str(value) for value in returns) + "\n",
        encoding="utf-8",
    )
    report = mod.parse_optimization_report(report_path)

    unreceipted = mod.build_optimization_audit(
        report,
        expected_total_trials=6,
        selected_pass_id="4",
        selected_returns_path=returns_path,
        returns_column="net_r",
        sharpe_column="Custom",
        sr_semantics="per_trade_net_r",
        selection_frozen=True,
    )
    assert unreceipted["dsr"]["status"] == "COMPUTED"
    assert unreceipted["anti_overfit_gate_eligible"] is False

    source_path = tmp_path / "EA.mq5"
    config_path = tmp_path / "optimizer.ini"
    source_path.write_text("// frozen source\n", encoding="utf-8")
    config_path.write_text("[Tester]\nOptimization=1\n", encoding="utf-8")
    receipt_path = tmp_path / "optimization_receipt.json"
    receipt_path.write_text(
        json.dumps(
            {
                "schema_version": "alphafactory_optimization_receipt.v1",
                "frozen_pre_outcome": True,
                "selection_rule_frozen": True,
                "expected_total_trials": 6,
                "report_format": "delimited",
                "sharpe_column": "Custom",
                "sr_semantics": "per_trade_net_r",
                "source_path": str(source_path),
                "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
                "config_path": str(config_path),
                "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
                "hypothesis_id": "TEST-HYP-001",
                "run_id": "TEST-RUN-001",
                "selection_metric": "Custom",
                "selection_direction": "max",
                "selection_tie_breaker": "lowest_pass_id",
                "parameter_axes": ["Fast", "Slow"],
                "cumulative_trials_before": 0,
                "report_path": str(report_path),
                "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
                "selected_pass_id": "4",
                "selected_returns_path": str(returns_path),
                "selected_returns_sha256": hashlib.sha256(returns_path.read_bytes()).hexdigest(),
                "selected_returns_column": "net_r",
                "selected_returns_row_count": len(returns),
            }
        ),
        encoding="utf-8",
    )
    receipt = mod.load_optimization_receipt(receipt_path)
    audit = mod.build_optimization_audit(
        report,
        expected_total_trials=6,
        selected_pass_id="4",
        selected_returns_path=returns_path,
        returns_column="net_r",
        sharpe_column="Custom",
        sr_semantics="per_trade_net_r",
        selection_frozen=True,
        optimization_receipt=receipt,
    )
    assert audit["trial_inventory"]["n_trials"] == 6
    assert audit["dsr"]["status"] == "COMPUTED"
    assert 0.0 <= audit["dsr"]["probability"] <= 1.0
    assert audit["diagnostic_evidence_complete"] is True
    assert audit["anti_overfit_gate_eligible"] is False
    assert audit["anti_overfit_gate_pass"] is False
    assert audit["promotion_eligible"] is False

    returns_path.write_text(
        "net_r\n" + "\n".join(str(value) for value in [*returns, returns[-1]]) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="SHA256 changed"):
        mod.build_optimization_audit(
            report,
            expected_total_trials=6,
            selected_pass_id="4",
            selected_returns_path=returns_path,
            returns_column="net_r",
            sharpe_column="Custom",
            sr_semantics="per_trade_net_r",
            selection_frozen=True,
            optimization_receipt=receipt,
        )

    with pytest.raises(ValueError, match="expected_total_trials"):
        mod.build_optimization_audit(report, expected_total_trials=7)

    blocked = mod.build_optimization_audit(
        report,
        expected_total_trials=6,
        selected_pass_id="4",
        selected_returns_path=returns_path,
        returns_column="net_r",
        sharpe_column="Sharpe Ratio",
        sr_semantics="mt5_tester_sharpe",
        selection_frozen=True,
    )
    assert blocked["dsr"]["status"] == "BLOCKED_SR_SEMANTICS"
    assert blocked["anti_overfit_gate_eligible"] is False


def test_optimization_pass_inventory_requires_contiguous_closure(tmp_path: Path) -> None:
    mod = _load_module("af_param_optimizer_closure", "analysis/param_optimizer.py")
    report_path = tmp_path / "optimizer.csv"
    report_path.write_text(
        "Pass,Custom,Fast,Slow\n"
        "1,1.0,10,50\n2,1.1,10,60\n3,1.2,20,50\n"
        "4,1.3,20,60\n5,1.4,30,50\n7,1.5,30,60\n",
        encoding="utf-8",
    )
    report = mod.parse_optimization_report(report_path)
    with pytest.raises(ValueError, match="contiguous Pass identities"):
        mod.build_optimization_audit(report, expected_total_trials=6)


def _dt(day: int, hour: int = 0) -> datetime:
    return datetime(2025, 1, day, hour, tzinfo=timezone.utc)


def test_cpcv_purges_overlap_and_applies_embargo() -> None:
    mod = _load_module("af_purged_cpcv", "analysis/purged_cpcv.py")
    records = [
        mod.EventRecord("v1", "e1", _dt(1), _dt(3), 0.2),
        mod.EventRecord("v1", "e2", _dt(2), _dt(2, 12), 0.1),
        mod.EventRecord("v1", "e3", _dt(3), _dt(4), -0.1),
        mod.EventRecord("v1", "e4", _dt(4), _dt(4, 12), 0.3),
        mod.EventRecord("v1", "e5", _dt(5), _dt(5, 12), 0.2),
        mod.EventRecord("v1", "e6", _dt(6), _dt(6, 12), -0.2),
        mod.EventRecord("v1", "e7", _dt(7), _dt(7, 12), 0.4),
        mod.EventRecord("v1", "e8", _dt(8), _dt(8, 12), 0.1),
    ]

    splits = mod.build_cpcv_splits(
        records,
        n_groups=4,
        n_test_groups=2,
        embargo_pct=0.10,
    )
    assert len(splits) == 6
    assert any(split.purged_indices for split in splits)
    assert any(split.embargoed_indices for split in splits)
    for split in splits:
        assert set(split.train_indices).isdisjoint(split.test_indices)
        test_intervals = [(records[i].start_time, records[i].label_end) for i in split.test_indices]
        for index in split.train_indices:
            assert not mod.interval_overlaps_any(
                records[index].start_time,
                records[index].label_end,
                test_intervals,
            )


def _aligned_variant_events(mod, values_by_variant: dict[str, list[float]]):
    records = []
    for variant_id, values in values_by_variant.items():
        for index, value in enumerate(values, start=1):
            records.append(
                mod.EventRecord(
                    variant_id,
                    f"e{index}",
                    _dt(index),
                    _dt(index),
                    value,
                )
            )
    return records


def test_cpcv_requires_aligned_event_universe() -> None:
    mod = _load_module("af_purged_cpcv_alignment", "analysis/purged_cpcv.py")
    records = _aligned_variant_events(
        mod,
        {
            "a": [0.4, -0.2, 0.3, -0.1, 0.2, -0.2, 0.1, -0.1],
            "b": [0.3, -0.1, 0.2, -0.2, 0.1, -0.1, 0.2, -0.2],
        },
    )
    records[-1].event_id = "different_event"

    with pytest.raises(ValueError, match="aligned event universe"):
        mod.run_purged_cpcv(records, n_groups=4, n_test_groups=2, metric="mean")


def test_cpcv_ties_are_non_informative_and_json_is_strict() -> None:
    mod = _load_module("af_purged_cpcv_ties", "analysis/purged_cpcv.py")
    identical = [0.4, -0.2, 0.3, -0.1, 0.2, -0.2, 0.1, -0.1]
    result = mod.run_purged_cpcv(
        _aligned_variant_events(mod, {"a": identical, "b": identical}),
        n_groups=4,
        n_test_groups=2,
        metric="mean",
        frozen_pre_outcome=True,
    )

    assert result["anti_overfit_gate_eligible"] is False
    assert result["results"]["pbo"] is None
    assert result["results"]["non_informative_tie_combinations"] == 6
    json.dumps(result, allow_nan=False)


def test_cpcv_rejects_non_finite_fold_metrics() -> None:
    mod = _load_module("af_purged_cpcv_finite", "analysis/purged_cpcv.py")
    result = mod.run_purged_cpcv(
        _aligned_variant_events(
            mod,
            {
                "a": [0.4, 0.2, 0.3, 0.1, 0.2, 0.2, 0.1, 0.1],
                "b": [0.3, 0.1, 0.2, 0.2, 0.1, 0.1, 0.2, 0.2],
            },
        ),
        n_groups=4,
        n_test_groups=2,
        metric="pf",
        frozen_pre_outcome=True,
    )

    assert result["anti_overfit_gate_eligible"] is False
    assert result["results"]["invalid_metric_combinations"] == 6
    json.dumps(result, allow_nan=False)


def test_dynamic_impact_is_monotonic_and_fail_closed(tmp_path: Path) -> None:
    mod = _load_module("af_dynamic_cost", "analysis/dynamic_cost_model.py")
    base = {
        "fill_id": "f1",
        "trade_id": "t1",
        "timestamp": "2025-01-01T00:00:00Z",
        "symbol": "TEST",
        "side": "BUY",
        "quantity": 100.0,
        "quantity_unit": "base_units",
        "reference_price": 100.0,
        "spread_price": 0.02,
        "volatility_bps": 10.0,
        "liquidity_quantity": 10_000.0,
        "quote_currency": "USD",
        "quote_to_account_rate": 1.0,
        "commission_account": 1.0,
        "account_currency": "USD",
    }
    small = mod.estimate_fill_cost(base, eta=0.5)
    large = mod.estimate_fill_cost({**base, "fill_id": "f2", "quantity": 400.0}, eta=0.5)
    illiquid = mod.estimate_fill_cost(
        {**base, "fill_id": "f3", "liquidity_quantity": 2_500.0}, eta=0.5
    )
    volatile = mod.estimate_fill_cost({**base, "fill_id": "f4", "volatility_bps": 20.0}, eta=0.5)

    assert large["impact_bps"] > small["impact_bps"]
    assert illiquid["impact_bps"] > small["impact_bps"]
    assert volatile["impact_bps"] > small["impact_bps"]

    audit = mod.build_cost_audit(
        [base, {**base, "fill_id": "f5", "side": "SELL"}],
        {"t1": 100.0},
        source_kind="adv_proxy",
        eta=0.5,
        calibration=None,
        account_currency="USD",
        pnl_basis="mid_reference_before_modeled_costs",
    )
    assert audit["economic_claim_allowed"] is False
    assert audit["promotion_eligible"] is False
    assert audit["trades"][0]["adjusted_pnl_account"] < 100.0
    json.dumps(audit, allow_nan=False)

    with pytest.raises(ValueError, match="liquidity_quantity"):
        mod.estimate_fill_cost({**base, "liquidity_quantity": 0.0}, eta=0.5)

    converted = mod.estimate_fill_cost(
        {
            **base,
            "fill_id": "f6",
            "quote_currency": "JPY",
            "quote_to_account_rate": 0.01,
        },
        eta=0.5,
    )
    assert converted["estimated_total_cost_account"] < small["estimated_total_cost_account"]

    with pytest.raises(ValueError, match="quote_to_account_rate"):
        mod.estimate_fill_cost({k: v for k, v in base.items() if k != "quote_to_account_rate"}, eta=0.5)

    with pytest.raises(ValueError, match="not finite"):
        mod.estimate_fill_cost(
            {**base, "quantity": 1e308, "reference_price": 1e308}, eta=0.5
        )


def test_dynamic_cost_calibration_is_hash_bound(tmp_path: Path) -> None:
    mod = _load_module("af_dynamic_cost_cal", "analysis/dynamic_cost_model.py")
    evidence_path = tmp_path / "depth_capture.csv"
    evidence_path.write_text("timestamp,depth\n2025-01-01T00:00:00Z,10000\n", encoding="utf-8")
    digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    calibration_path = tmp_path / "calibration.json"
    calibration_path.write_text(
        json.dumps(
            {
                "schema_version": "alphafactory_impact_calibration.v1",
                "source_kind": "observed_depth",
                "symbol": "TEST",
                "quantity_unit": "base_units",
                "eta": 0.5,
                "sample_count": 1,
                "frozen_pre_outcome": True,
                "verification_status": "UNVERIFIED_DIAGNOSTIC_ONLY",
                "evidence_path": str(evidence_path),
                "evidence_sha256": digest,
            }
        ),
        encoding="utf-8",
    )

    calibration = mod.load_calibration(calibration_path)
    assert calibration["manifest_verified"] is True
    assert calibration["calibration_recomputed"] is False

    mismatched_path = tmp_path / "calibration_mismatch.json"
    mismatched_payload = json.loads(calibration_path.read_text(encoding="utf-8"))
    mismatched_payload["sample_count"] = 100
    mismatched_path.write_text(json.dumps(mismatched_payload), encoding="utf-8")
    with pytest.raises(ValueError, match="sample_count does not match"):
        mod.load_calibration(mismatched_path)

    fill = {
        "fill_id": "f1",
        "trade_id": "t1",
        "timestamp": "2025-01-01T00:00:00Z",
        "symbol": "TEST",
        "side": "BUY",
        "quantity": 100.0,
        "quantity_unit": "base_units",
        "reference_price": 100.0,
        "spread_price": 0.02,
        "volatility_bps": 10.0,
        "liquidity_quantity": 10_000.0,
        "quote_currency": "USD",
        "quote_to_account_rate": 1.0,
        "commission_account": 1.0,
        "account_currency": "USD",
    }
    audit = mod.build_cost_audit(
        [fill],
        {"t1": 100.0},
        source_kind="observed_depth",
        eta=0.5,
        calibration=calibration,
        account_currency="USD",
        pnl_basis="mid_reference_before_modeled_costs",
    )
    assert audit["impact_gate_eligible"] is False
    assert audit["economic_claim_allowed"] is False

    evidence_path.write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256"):
        mod.load_calibration(calibration_path)


def test_async_execution_kernel_contract_is_present() -> None:
    workspace_root = ALPHA_ROOT.parent
    kernel = workspace_root / "03. EA Developer/_Shared/Execution/AF_ExecutionKernel.mqh"
    tick_cursor = workspace_root / "03. EA Developer/_Shared/MarketData/AF_TickCursor.mqh"
    smoke = (
        workspace_root
        / "03. EA Developer/EA_ExecutionKernelHarness/EA_ExecutionKernelHarness.mq5"
    )
    source = kernel.read_text(encoding="utf-8")
    tick_source = tick_cursor.read_text(encoding="utf-8")
    smoke_source = smoke.read_text(encoding="utf-8")

    for token in (
        "AF_EXEC_PENDING_NEW",
        "AF_EXEC_ORDER_PLACED",
        "AF_EXEC_PARTIALLY_FILLED",
        "AF_EXEC_FILLED",
        "OrderSendAsync",
        "OnTradeTransaction",
        "request_id",
    ):
        assert token in source
    assert "#define AF_EXEC_EXPERIMENTAL_MUTATION_ENABLED 0" in source
    assert "An empty live scan cannot prove an async request's terminal outcome" in source
    assert "entry!=DEAL_ENTRY_IN" in source
    assert "check.retcode!=0" in source
    assert "check.retcode!=TRADE_RETCODE_DONE" not in source
    assert "CopyTicksRange" in tick_source
    assert "if(to_msc<(ulong)current.time_msc)" in tick_source
    assert "m_scan_from_msc=to_msc+1" in tick_source
    assert "g_execution.OnTradeTransaction" in smoke_source


def test_alpha_cli_routes_real_quant_pro_tools() -> None:
    source = (ALPHA_ROOT / "alpha.ps1").read_text(encoding="utf-8")
    assert '"cpcv"' in source
    assert '"impact"' in source
    assert "analysis\\purged_cpcv.py" in source
    assert "analysis\\dynamic_cost_model.py" in source
    assert "--expected-total-trials" in source
    assert "single-report Gaussian" in source
    assert "observed_depth requires -Calibration" in source


def test_alpha_impact_route_executes_diagnostic(tmp_path: Path) -> None:
    fills_path = tmp_path / "fills.csv"
    trades_path = tmp_path / "trades.csv"
    out_dir = tmp_path / "impact_out"
    fills_path.write_text(
        "fill_id,trade_id,timestamp,symbol,side,quantity,quantity_unit,"
        "reference_price,spread_price,volatility_bps,liquidity_quantity,"
        "quote_currency,quote_to_account_rate,commission_account,account_currency\n"
        "f1,t1,2025-01-01T00:00:00Z,TEST,BUY,100,base_units,100,0.02,"
        "10,10000,USD,1,1,USD\n",
        encoding="utf-8",
    )
    trades_path.write_text(
        "trade_id,gross_pnl,account_currency,pnl_basis\n"
        "t1,100,USD,mid_reference_before_modeled_costs\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ALPHA_ROOT / "alpha.ps1"),
            "impact",
            "-Report",
            str(fills_path),
            "-TradesCsv",
            str(trades_path),
            "-LiquiditySource",
            "adv_proxy",
            "-Output",
            str(out_dir),
        ],
        cwd=ALPHA_ROOT.parent,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads((out_dir / "dynamic_cost_analysis.json").read_text(encoding="utf-8"))
    assert payload["economic_claim_allowed"] is False
    assert payload["promotion_eligible"] is False
