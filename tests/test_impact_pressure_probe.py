from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "02. AlphaFactory"
    / "tools"
    / "impact_pressure_probe.py"
)
SPEC = importlib.util.spec_from_file_location("impact_pressure_probe", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)


def bar(bar_ms: int, *, raw_z: float | None = None, return_z: float | None = None, eligible: bool = True):
    return probe.BarFeature(
        symbol="EURUSD",
        bar_ms=bar_ms,
        point=0.00001,
        pip_size=0.0001,
        first_bid=1.10000,
        first_ask=1.10010,
        last_bid=1.10000,
        last_ask=1.10010,
        bid_min=1.10000,
        bid_max=1.10000,
        ask_min=1.10010,
        ask_max=1.10010,
        start_mid=1.10005,
        end_mid=1.10015,
        move_points=10.0,
        path_points=10.0,
        nq=30,
        netq=10,
        ipp=1.0,
        pe=1.0,
        raw=math.log(2.0),
        median_spread_points=10.0,
        base_valid=True,
        continuous_prev=True,
        return_points=10.0,
        raw_z=raw_z,
        return_z=return_z,
        spread_ratio=1.0,
        eligible=eligible,
    )


def test_impact_components_are_the_frozen_price_path_transform() -> None:
    parts = probe.impact_components([1.0, 2.0, 3.0, 2.0, 3.0], 1.0)

    assert parts["move_points"] == 2.0
    assert parts["path_points"] == 4.0
    assert parts["nq"] == 4
    assert parts["netq"] == 2
    assert parts["ipp"] == 1.0
    assert parts["pe"] == 0.5
    assert math.isclose(parts["raw"], math.log1p(0.5))


def test_robust_z_uses_only_the_supplied_prior_window() -> None:
    history = list(range(20))
    expected = (25.0 - 9.5) / 5.0

    assert math.isclose(probe.robust_z(25.0, history), expected)
    assert probe.robust_z(25.0, history[:19]) is None


def test_matched_control_threshold_matches_train_signal_count() -> None:
    rows = [
        bar(0, raw_z=3.1, return_z=4.0),
        bar(probe.BAR_MS, raw_z=-2.8, return_z=3.0),
        bar(2 * probe.BAR_MS, raw_z=1.0, return_z=2.0),
        bar(3 * probe.BAR_MS, raw_z=0.5, return_z=1.0),
    ]

    threshold, primary_count, control_count = probe.matched_control_threshold(
        {"EURUSD": rows}, 0, 4 * probe.BAR_MS, 2.7
    )

    assert threshold == 2.5
    assert primary_count == 2
    assert control_count == 2


def test_same_bar_stop_and_target_is_closed_adverse_first() -> None:
    signal = bar(0, raw_z=3.0)
    entry = bar(probe.BAR_MS, eligible=False)
    entry.bid_min = 1.10000
    entry.bid_max = 1.10030

    trades = probe.simulate_symbol([signal, entry], "PRIMARY", 2.7)

    assert len(trades) == 1
    assert trades[0].exit_reason == "both_hit_adverse_first"
    assert math.isclose(trades[0].gross_pips, -0.5)


def test_failed_data_gate_kills_the_probe() -> None:
    metrics = {
        "trades": 200,
        "trades_per_elapsed_week": 3.0,
        "pf_stress_b": 1.5,
        "expectancy_pips_stress_b": 0.3,
        "net_pips_stress_b": 60.0,
        "max_drawdown_r_stress_b": 5.0,
        "year_positive_pnl_concentration": 0.4,
        "symbol_positive_pnl_concentration": 0.6,
        "side_positive_pnl_concentration": 0.6,
    }
    primary = {"holdout": dict(metrics, trades=80), "pooled": metrics}
    control = {
        "holdout": dict(
            metrics,
            trades=80,
            pf_stress_b=1.1,
            expectancy_pips_stress_b=0.1,
            net_pips_stress_b=20.0,
        ),
        "pooled": metrics,
    }

    decision = probe.gate_decision(primary, control, data_ok=False)

    assert decision["verdict"] == "KILL_AT_OFFLINE_PROBE"
    assert "data" in decision["failed_checks"]


def test_probe_source_has_no_mt5_trading_mutation_calls() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    for forbidden in (".order_send(", ".positions_get(", ".orders_get("):
        assert forbidden not in source
