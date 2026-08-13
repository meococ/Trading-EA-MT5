from __future__ import annotations

import importlib.util
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest


PACKAGE = Path(__file__).resolve().parents[2]
TOOL = PACKAGE / "research" / "tools" / "analyze_xbtmm_fills.py"
SPEC = importlib.util.spec_from_file_location("analyze_xbtmm_fills", TOOL)
assert SPEC and SPEC.loader
sut = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sut
SPEC.loader.exec_module(sut)


def test_pf_and_stress_math() -> None:
    assert sut.pf([2.0, -1.0, 0.0]) == 2.0
    assert sut.pf([0.0]) == 0.0


def test_economics_require_explicit_authority(tmp_path: Path) -> None:
    task = tmp_path / "task.json"
    task.write_text(
        '{"hypothesis_id":"HYP-XBT-MM-TRADETHROUGH-004",'
        '"economics_authorized":false,"performance_metrics_authorized":false,'
        '"holdout_access_authorized":false}',
        encoding="utf-8",
    )
    with pytest.raises(PermissionError):
        sut.load_authority(task)


def test_economics_require_frozen_capital_contract(tmp_path: Path) -> None:
    task = tmp_path / "task.json"
    task.write_text(
        '{"hypothesis_id":"HYP-XBT-MM-TRADETHROUGH-004",'
        '"economics_authorized":true,"performance_metrics_authorized":true,'
        '"holdout_access_authorized":false,"authority":"DESIGN"}',
        encoding="utf-8",
    )
    with pytest.raises(PermissionError, match="capital contract"):
        sut.load_authority(task)


def test_capital_nav_drawdown_and_recovery() -> None:
    days = [date(2018, 1, 1) + timedelta(days=offset) for offset in range(3)]
    metrics = sut.nav_metrics(days, [40.0, -80.0, 80.0], 400.0)
    assert metrics["max_dd_pct"] == pytest.approx(100.0 * 80.0 / 440.0)
    assert metrics["recovery_days"] == 1
    assert metrics["final_nav"] == 440.0


def test_realized_xbt_is_converted_to_usd_at_execution_price() -> None:
    realized_xbt = 100.0 * (1.0 / 10_000.0 - 1.0 / 10_100.0)
    rows = [
        {
            "time_us": "1514764800000000",
            "type": "MAKER_FILL",
            "side": "BUY",
            "quantity": "100",
            "price": "10000.0",
            "inventory": "100",
            "realized_delta_xbt": "0.0",
            "fee_xbt": "0.0",
        },
        {
            "time_us": "1514764801000000",
            "type": "MAKER_FILL",
            "side": "SELL",
            "quantity": "100",
            "price": "10100.0",
            "inventory": "0",
            "realized_delta_xbt": str(realized_xbt),
            "fee_xbt": "0.0",
        },
    ]
    result = sut.analyze_engine(
        rows,
        [date(2018, 1, 1)],
        {"max_dd_xbt_pct": "0.0", "inventory": "0", "engineering_gate_pass": "true"},
    )
    assert result["net_pnl_usd"] == pytest.approx(realized_xbt * 10_100.0)
    assert result["reference_risk_capital_usd"] == 400.0


def test_gate_requires_all_years_not_aggregate() -> None:
    candidate = {
        "engineering_gate_pass": True,
        "by_year": {
            "2018": {"maker_fills": 5000, "filled_day_ratio": 0.9},
            "2019": {"maker_fills": 100, "filled_day_ratio": 0.1},
        },
        "pf": 2.0,
        "average_pnl_per_maker_contract_usd": 1.0,
        "net_pnl_usd": 1.0,
        "annualized_return_on_risk_capital": 0.20,
        "annualized_return_on_risk_capital_x2": 0.01,
        "pf_x1_5": 1.5,
        "pf_x2": 1.2,
        "daily_capital_max_dd_pct": 5.0,
        "recovery_days": 10,
        "top_5pct_days_positive_pnl_share": 0.2,
        "average_holding_minutes": 5.0,
        "average_daily_pnl_usd": 1.0,
    }
    null = {"engineering_gate_pass": True, "pf": 1.0, "average_daily_pnl_usd": 0.0}
    gates = sut.evaluate(candidate, null)
    assert gates["year_power_and_coverage"] is False
