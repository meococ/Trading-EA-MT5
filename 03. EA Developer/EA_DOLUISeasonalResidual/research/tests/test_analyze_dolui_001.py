from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "analyze_dolui_001.py"
SPEC = importlib.util.spec_from_file_location("analyze_dolui_001", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_profit_factor_and_drawdown() -> None:
    assert MODULE.profit_factor([3.0, -1.0, 2.0, -1.0]) == 2.5
    assert MODULE.closed_trade_drawdown([100.0, -50.0], 1000.0) > 0.0


def test_cost_formula_tolerance() -> None:
    row = {
        "event_id": "DOLUI0001",
        "lots": "1.0",
        "raw_mid_pnl_usd": "100.0",
        "executable_pnl_usd": "90.0",
        "observed_spread_fill_cost_usd": "10.0",
        "commission_usd": "4.0",
        "dynamic_slippage_usd": "6.0",
        "complete_cost_usd": "20.0",
        "entry_spread_pips": "1.0",
        "exit_spread_pips": "1.0",
        "pip_value_per_lot": "10.0",
        "net_base_usd": "80.0",
        "net_x1_5_usd": "70.0",
        "net_x2_usd": "60.0",
    }
    MODULE.validate_cost_row(row)
