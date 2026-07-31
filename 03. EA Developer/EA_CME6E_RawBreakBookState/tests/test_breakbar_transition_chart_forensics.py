from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


PACKAGE = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    PACKAGE / "research" / "analyze_breakbar_transition_chart_forensics.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "analyze_breakbar_transition_chart_forensics", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_utc_session_is_deterministic() -> None:
    module = load_module()
    assert module.utc_session(23) == "ROLLOVER"
    assert module.utc_session(3) == "ASIA"
    assert module.utc_session(9) == "LONDON"
    assert module.utc_session(15) == "NEW_YORK"


def test_lifecycle_aggregation_includes_open_commission() -> None:
    module = load_module()
    lifecycle = pd.DataFrame(
        [
            {
                "position_id": "7",
                "action": "OPEN",
                "deal_profit": 0.0,
                "deal_commission": -0.8,
                "deal_swap": 0.0,
                "deal_fee": 0.0,
                "deal_net": -0.8,
                "is_final_close": 0,
            },
            {
                "position_id": "7",
                "action": "CLOSE",
                "deal_profit": 19.6,
                "deal_commission": 0.0,
                "deal_swap": 0.0,
                "deal_fee": 0.0,
                "deal_net": 19.6,
                "is_final_close": 1,
            },
        ]
    )

    result = module.aggregate_lifecycle(lifecycle)
    row = result.iloc[0]
    assert row["lifecycle_rows"] == 2
    assert row["lifecycle_net"] == pytest.approx(18.8)
    assert row["price_profit_before_explicit_cost"] == pytest.approx(19.6)
    assert row["explicit_cost_account"] == pytest.approx(0.8)
    assert row["final_close_rows"] == 1


def test_preentry_context_excludes_entry_and_future_bars() -> None:
    module = load_module()
    times = pd.date_range("2022-01-01 00:00:00", periods=62, freq="1min")
    bars = pd.DataFrame(
        {
            "time_utc": times,
            "open": [1.1000 + index * 0.00001 for index in range(62)],
            "high": [1.1001 + index * 0.00001 for index in range(62)],
            "low": [1.0999 + index * 0.00001 for index in range(62)],
            "close": [1.1000 + index * 0.00001 for index in range(62)],
        }
    )
    entry_time = pd.Timestamp("2022-01-01 01:00:00")
    bars.loc[bars["time_utc"] >= entry_time, ["open", "high", "low", "close"]] = 9.0

    context = module.compute_preentry_context(bars, entry_time, "BUY")

    assert pd.Timestamp(context["context_last_bar_utc"]) < entry_time
    assert context["pre60_range_pips"] < 20.0
    assert context["entry_location_prior24h"] <= 1.0
