from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


SOURCE = Path(__file__).resolve().parents[1] / "evaluate_eurfxmom_eurusd_001_validation.py"
SPEC = importlib.util.spec_from_file_location("eurfxmom001_validation", SOURCE)
assert SPEC is not None and SPEC.loader is not None
mom = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mom
SPEC.loader.exec_module(mom)


def signal_and_targets() -> tuple[pd.DataFrame, pd.DataFrame]:
    population = pd.bdate_range("2021-01-04", "2024-12-27")
    dates = population[np.linspace(0, len(population) - 1, mom.EXPECTED_DATES, dtype=int)]
    pressure = np.where(np.arange(len(dates)) % 2 == 0, 30.0, -30.0)
    continuation_move = np.where(np.arange(len(dates)) % 5 == 0, -5.0, 10.0)
    signal = pd.DataFrame(
        {
            "local_date": dates.strftime("%Y-%m-%d"),
            "pre_fix_pressure_pips": pressure,
            "pressure_threshold_pips": 20.0,
            "ledger_reversal_direction": -np.sign(pressure).astype(int),
        }
    )
    targets = pd.DataFrame(
        {
            "local_date": dates.strftime("%Y-%m-%d"),
            "entry": 1.10,
            "exit": 1.10 + np.sign(pressure) * continuation_move * mom.PIP_SIZE,
        }
    )
    targets["post_fix_move_pips"] = (targets["exit"] - targets["entry"]) / mom.PIP_SIZE
    return signal, targets


def test_review_sentinel_shape_is_fail_closed() -> None:
    sentinel = mom.REVIEWED_REGISTRY_ROW_SHA256
    assert sentinel is None or (
        isinstance(sentinel, str)
        and len(sentinel) == 64
        and set(sentinel).issubset(set("0123456789ABCDEF"))
    )


def test_normalized_hash_ignores_only_sentinel_value() -> None:
    payload = SOURCE.read_bytes()
    base = mom.normalized_evaluator_base_sha256(payload)
    armed = payload.replace(
        b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None",
        b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"',
        1,
    )
    assert mom.normalized_evaluator_base_sha256(armed) == base


def test_build_trades_uses_pressure_continuation_and_fixed_costs() -> None:
    signal, targets = signal_and_targets()
    trades, funnel = mom.build_trades(signal, targets)
    expected = np.sign(trades["pre_fix_pressure_pips"]).astype(int)
    np.testing.assert_array_equal(trades["pressure_continuation_primary_direction"], expected)
    np.testing.assert_array_equal(trades["pressure_reversal_control_direction"], -expected)
    assert trades.iloc[0]["pressure_continuation_primary_gross_pips"] == pytest.approx(-5.0)
    assert trades.iloc[1]["pressure_continuation_primary_gross_pips"] == pytest.approx(10.0)
    assert trades.iloc[1]["primary_net_x1_pips"] == pytest.approx(8.5)
    assert trades.iloc[1]["primary_net_x1_5_pips"] == pytest.approx(7.75)
    assert trades.iloc[1]["primary_net_x2_pips"] == pytest.approx(7.0)
    assert funnel == {"selected_validation_dates": 526, "exact_target_dates": 526, "trades": 526}


def test_build_trades_fails_on_missing_target() -> None:
    signal, targets = signal_and_targets()
    with pytest.raises(mom.ContractError, match="missing target boundaries"):
        mom.build_trades(signal, targets.iloc[:-1])


def test_project_exact_targets_honors_berlin_dst() -> None:
    times = pd.to_datetime(
        [
            "2021-01-04T13:14:00Z",
            "2021-01-04T14:59:00Z",
            "2021-07-05T12:14:00Z",
            "2021-07-05T13:59:00Z",
        ],
        utc=True,
    )
    frame = pd.DataFrame({"time_utc": times, "close": [1.10, 1.11, 1.20, 1.19]})
    projected = mom.project_exact_targets(frame).set_index("local_date")
    assert projected.loc["2021-01-04", "post_fix_move_pips"] == pytest.approx(100.0)
    assert projected.loc["2021-07-05", "post_fix_move_pips"] == pytest.approx(-100.0)


def test_sign_flip_is_deterministic() -> None:
    values = np.repeat(5.0, 50)
    first = mom.sign_flip_p_value(values)
    second = mom.sign_flip_p_value(values)
    assert first == second
    assert first <= 0.05


def test_summarize_passes_frozen_gates_for_stable_continuation() -> None:
    signal, targets = signal_and_targets()
    trades, funnel = mom.build_trades(signal, targets)

    class DsrStub:
        @staticmethod
        def dsr(*_args: object) -> float:
            return 0.999

    metrics = mom.summarize_trades(trades, funnel, DsrStub())
    assert metrics["trade_count"] == 526
    assert metrics["structural_gate_pass_count"] == metrics["structural_gate_total"]
    assert metrics["economic_gate_pass_count"] == metrics["economic_gate_total"]
    assert metrics["arms"]["pressure_continuation_primary"]["profit_factor"]["x1"] > 1.3
    assert metrics["arms"]["pressure_reversal_control"]["profit_factor"]["x1"] < 1.0


def test_plan_hash_is_bound_to_current_file() -> None:
    plan = SOURCE.parent / "HYP-EURFXMOM-EURUSD-M1-001_VALIDATION_PROBE_PLAN.md"
    assert mom.sha256_file(plan) == mom.PLAN_SHA256
