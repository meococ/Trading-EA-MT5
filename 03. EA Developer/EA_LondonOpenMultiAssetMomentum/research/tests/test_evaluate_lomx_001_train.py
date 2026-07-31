from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pandas as pd
import pytest


MODULE_PATH = Path(__file__).parents[1] / "evaluate_lomx_001_train.py"
SPEC = importlib.util.spec_from_file_location("lomx_eval", MODULE_PATH)
assert SPEC and SPEC.loader
lomx = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lomx
SPEC.loader.exec_module(lomx)


def _frame(days=("2018-01-02", "2018-01-03")) -> pd.DataFrame:
    rows = []
    for symbol in ("EURUSD", "GBPUSD", "EURJPY", "USDJPY", "XAUUSD"):
        base = 150.0 if "JPY" in symbol else (1300.0 if symbol == "XAUUSD" else 1.2)
        point = 0.001 if "JPY" in symbol else (0.01 if symbol == "XAUUSD" else 0.00001)
        for index, day in enumerate(days):
            up = index % 2 == 0
            open_0800 = base
            open_0830 = base + (0.01 if up else -0.01)
            direction = 1.0 if up else -1.0
            rows.append(
                {
                    "symbol": symbol,
                    "local_date": day,
                    "open_0800": open_0800,
                    "open_0830": open_0830,
                    "open_1200": open_0830 + direction * 0.02,
                    "open_1530": open_0830 + direction * 0.01,
                    "open_1600": open_0830 + direction * 0.03,
                    "open_1630": open_0830 + direction * 0.04,
                    "spread_0830_points": 1,
                    "spread_1200_points": 1,
                    "spread_1530_points": 1,
                    "spread_1600_points": 1,
                    "spread_1630_points": 1,
                    "point": point,
                }
            )
    return pd.DataFrame(rows)


def test_arm_accounting_and_scope_are_frozen():
    assert len(lomx.ARMS) == 23
    assert sum(arm.selectable for arm in lomx.ARMS) == 10
    assert sum(arm.role == "EXTERNAL_NULL" for arm in lomx.ARMS) == 3
    assert sum(arm.role == "REVERSE_CONTROL" for arm in lomx.ARMS) == 10
    assert "USDJPY_LATE_FIX_PRIMARY" not in {arm.arm_id for arm in lomx.ARMS}
    assert "USDJPY_FULL_SESSION_PRIMARY" not in {arm.arm_id for arm in lomx.ARMS}


def test_simulation_uses_formation_then_next_bar_open_and_cost():
    frame = lomx.validate_train_frame(_frame())
    arm = next(arm for arm in lomx.ARMS if arm.arm_id == "EURUSD_MIDDAY_PRIMARY")
    trades = lomx.simulate_arm(frame, arm)
    assert list(trades["formation_sign"]) == [1, -1]
    assert (trades["gross_return"] > 0).all()
    assert (trades["net_x1p0_return"] < trades["gross_return"]).all()
    assert (trades["net_x2p0_return"] < trades["net_x1p0_return"]).all()


def test_gbpusd_paper_directed_polarity_is_reversed():
    arm = next(arm for arm in lomx.ARMS if arm.arm_id == "GBPUSD_MIDDAY_PRIMARY")
    assert arm.polarity == -1
    primary_id = arm.arm_id
    reverse = next(item for item in lomx.ARMS if item.matched_primary_id == primary_id)
    assert reverse.polarity == 1


def test_holm_adjustment_counts_all_ten_selectable_arms():
    raw = {f"arm_{idx}": 0.001 * (idx + 1) for idx in range(10)}
    adjusted = lomx.holm_adjust(raw)
    ordered = [adjusted[f"arm_{idx}"] for idx in range(10)]
    assert ordered == sorted(ordered)
    assert adjusted["arm_0"] == pytest.approx(0.01)


def test_validation_rejects_2021_without_economic_computation():
    frame = _frame(days=("2021-01-04",))
    with pytest.raises(lomx.ContractError, match="forbidden non-TRAIN"):
        lomx.validate_train_frame(frame)


def test_cli_is_disarmed_without_production_flag():
    with pytest.raises(lomx.ContractError, match="production is disarmed"):
        lomx.main([])
