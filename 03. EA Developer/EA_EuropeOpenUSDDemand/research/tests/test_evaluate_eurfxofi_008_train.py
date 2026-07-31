from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "evaluate_eurfxofi_008_train.py"
SPEC = importlib.util.spec_from_file_location("eurfxofi008", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def population() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    blocks = []
    for year in range(2016, 2021):
        blocks.extend(pd.bdate_range(f"{year}-01-01", f"{year}-12-31")[:126])
    dates = pd.DatetimeIndex(blocks)
    assert len(dates) == 630
    local_date = dates.strftime("%Y-%m-%d")
    flow_sign = np.where(np.arange(len(dates)) % 2 == 0, 1, -1)
    pressure = np.where(np.arange(len(dates)) % 3 == 0, 20.0, -20.0)
    win = np.arange(len(dates)) % 5 != 0
    primary_gross = np.where(win, 5.0, -2.0)
    post_move = -flow_sign * primary_gross
    features = pd.DataFrame(
        {
            "local_date": local_date,
            "split": "TRAIN",
            "source_empty": False,
            "records": 20,
            "flow_signed": flow_sign * 10.0,
            "flow_imbalance": flow_sign * 0.4,
            "classified_volume": 25.0,
            "total_volume": 25.0,
            "flow_acceleration": 0.1,
            "late_flow_share": 0.3,
        }
    )
    signal = pd.DataFrame(
        {
            "local_date": local_date,
            "pre_fix_pressure_pips": pressure,
            "pressure_threshold_pips": 10.0,
            "pressure_direction": -np.sign(pressure).astype(int),
        }
    )
    targets = pd.DataFrame(
        {
            "local_date": local_date,
            "entry": 1.10,
            "exit": 1.10 + post_move * MODULE.PIP_SIZE,
            "post_fix_move_pips": post_move,
        }
    )
    return features, signal, targets


def test_build_trades_uses_only_frozen_flow_sign_and_four_arms() -> None:
    features, signal, targets = population()
    trades, funnel = MODULE.build_trades(features, signal, targets)
    assert len(trades) == 630
    assert funnel == {
        "selected_train_dates": 630,
        "source_empty_dates": 0,
        "zero_signed_flow_dates": 0,
        "missing_target_dates": 0,
        "trades": 630,
    }
    expected_primary = -np.sign(trades["flow_signed"]).astype(int)
    expected_pressure = -np.sign(trades["pre_fix_pressure_pips"]).astype(int)
    np.testing.assert_array_equal(trades["flow_reversal_primary_direction"], expected_primary)
    np.testing.assert_array_equal(trades["flow_continuation_control_direction"], -expected_primary)
    np.testing.assert_array_equal(trades["pressure_reversal_control_direction"], expected_pressure)
    np.testing.assert_allclose(
        trades["flow_reversal_primary_net_x1_pips"],
        trades["flow_reversal_primary_gross_pips"] - 1.5,
    )


def test_source_empty_and_exact_zero_flow_are_explicitly_skipped() -> None:
    features, signal, targets = population()
    features.loc[0, "source_empty"] = True
    features.loc[0, "flow_signed"] = np.nan
    features.loc[1, "flow_signed"] = 0.0
    trades, funnel = MODULE.build_trades(features, signal, targets)
    assert len(trades) == 628
    assert funnel["source_empty_dates"] == 1
    assert funnel["zero_signed_flow_dates"] == 1
    assert funnel["trades"] == 628


def test_missing_exact_target_boundary_fails_closed() -> None:
    features, signal, targets = population()
    with pytest.raises(MODULE.ContractError, match="missing exact target boundaries"):
        MODULE.build_trades(features, signal, targets.iloc[1:])


def test_predeclared_gates_and_sixteen_arm_dsr_universe() -> None:
    features, signal, targets = population()
    trades, funnel = MODULE.build_trades(features, signal, targets)
    prior = {
        f"prior_{index}": np.tile(np.array([-1.0, 2.0, 1.0, -0.5]), 150)
        for index in range(12)
    }
    dsr = SimpleNamespace(dsr=lambda *args: 0.99)
    metrics = MODULE.summarize_trades(
        trades,
        funnel,
        prior,
        dsr,
        permutations=100,
    )
    assert metrics["deflated_sharpe"]["n_trials"] == 16
    assert metrics["structural_gate_pass_count"] == metrics["structural_gate_total"]
    assert metrics["economic_gate_pass_count"] == metrics["economic_gate_total"]
    assert metrics["positive_years"] == 5
    assert metrics["arms"]["flow_reversal_primary"]["profit_factor"]["x1"] > 1.30


def test_all_five_chart_figures_construct_without_changing_population(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    features, signal, targets = population()
    trades, funnel = MODULE.build_trades(features, signal, targets)
    prior = {
        f"prior_{index}": np.tile(np.array([-1.0, 2.0, 1.0, -0.5]), 150)
        for index in range(12)
    }
    metrics = MODULE.summarize_trades(
        trades,
        funnel,
        prior,
        SimpleNamespace(dsr=lambda *args: 0.99),
        permutations=100,
    )
    rendered: list[Path] = []
    monkeypatch.setattr(MODULE, "_write_plot", lambda fig, path: rendered.append(path))
    paths = MODULE.render_charts(trades, metrics, tmp_path)
    assert paths == rendered
    assert [path.name for path in paths] == list(MODULE.CHART_NAMES)


def test_disarmed_sentinel_and_normalized_hash_are_stable() -> None:
    assert MODULE.REVIEWED_REGISTRY_ROW_SHA256 is None
    payload = SCRIPT.read_bytes()
    base = MODULE.normalized_evaluator_base_sha256(payload)
    armed = payload.replace(
        b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None",
        b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"',
        1,
    )
    assert MODULE.normalized_evaluator_base_sha256(armed) == base
