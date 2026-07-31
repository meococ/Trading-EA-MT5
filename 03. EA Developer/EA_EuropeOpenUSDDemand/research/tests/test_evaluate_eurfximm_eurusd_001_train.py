from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "evaluate_eurfximm_eurusd_001_train.py"
SPEC = importlib.util.spec_from_file_location("eurfximm001", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def population() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    blocks = []
    for year in range(2016, 2021):
        blocks.extend(pd.bdate_range(f"{year}-01-01", f"{year}-12-31")[:126])
    dates = pd.DatetimeIndex(blocks)
    local_date = dates.strftime("%Y-%m-%d")
    flow_sign = np.where(np.arange(len(dates)) % 2 == 0, 1, -1)
    pressure = np.where(np.arange(len(dates)) % 3 == 0, 20.0, -20.0)
    win = np.arange(len(dates)) % 5 != 0
    primary_gross = np.where(win, 5.0, -2.0)
    move = flow_sign * primary_gross
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
            "exit": 1.10 + move * 0.0001,
            "immediate_move_pips": move,
        }
    )
    return features, signal, targets


def test_closed_bar_target_projection_uses_only_1415_and_1420() -> None:
    module = MODULE.configure()
    frame = pd.DataFrame(
        {
            "time_utc": pd.to_datetime(
                ["2020-01-02T13:15:00Z", "2020-01-02T13:20:00Z", "2020-01-02T13:21:00Z"]
            ),
            "close": [1.1000, 1.1008, 1.2000],
        }
    )
    projected = module.project_train_targets(frame)
    assert len(projected) == 1
    assert projected.loc[0, "immediate_move_pips"] == pytest.approx(8.0)


def test_build_trades_primary_is_flow_continuation_after_one_bar_lag() -> None:
    module = MODULE.configure()
    module.ALLOWED_MISSING_TARGET_DATES = ()
    features, signal, targets = population()
    trades, funnel = module.build_trades(features, signal, targets)
    assert len(trades) == 630
    assert funnel["trades"] == 630
    np.testing.assert_array_equal(
        trades["flow_continuation_primary_direction"],
        np.sign(trades["flow_signed"]).astype(int),
    )
    np.testing.assert_array_equal(
        trades["flow_reversal_control_direction"],
        -np.sign(trades["flow_signed"]).astype(int),
    )
    assert (trades["entry_local_hhmm"] == "14:15").all()
    assert (trades["exit_local_hhmm"] == "14:20").all()
    np.testing.assert_allclose(
        trades["flow_continuation_primary_net_x1_pips"],
        trades["flow_continuation_primary_gross_pips"] - 1.5,
    )


def test_source_empty_zero_flow_and_unexpected_missing_target_fail_closed() -> None:
    module = MODULE.configure()
    module.ALLOWED_MISSING_TARGET_DATES = ()
    features, signal, targets = population()
    features.loc[0, "source_empty"] = True
    features.loc[0, "flow_signed"] = np.nan
    features.loc[1, "flow_signed"] = 0.0
    trades, funnel = module.build_trades(features, signal, targets)
    assert len(trades) == 628
    assert funnel["source_empty_dates"] == 1
    assert funnel["zero_signed_flow_dates"] == 1
    with pytest.raises(module.ContractError, match="missing exact target boundaries"):
        module.build_trades(features, signal, targets.iloc[1:])


def test_twenty_arm_dsr_and_frozen_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    module = MODULE.configure()
    module.ALLOWED_MISSING_TARGET_DATES = ()
    monkeypatch.setattr(MODULE, "EXPECTED_TRADES", 630)
    features, signal, targets = population()
    trades, funnel = module.build_trades(features, signal, targets)
    prior = {
        f"prior_{index}": np.tile(np.array([-1.0, 2.0, 1.0, -0.5]), 150)
        for index in range(16)
    }
    metrics = module.summarize_trades(
        trades,
        funnel,
        prior,
        SimpleNamespace(dsr=lambda *args: 0.99),
        permutations=100,
    )
    assert metrics["deflated_sharpe"]["n_trials"] == 20
    assert set(metrics["arms"]) == set(MODULE.PUBLIC_ARMS if hasattr(MODULE, "PUBLIC_ARMS") else MODULE.ARMS)
    assert metrics["arms"]["flow_continuation_primary"]["profit_factor"]["x1"] > 1.30
    assert metrics["structural_gate_pass_count"] == metrics["structural_gate_total"]
    assert metrics["economic_gate_pass_count"] == metrics["economic_gate_total"]


def test_all_five_charts_construct_with_public_arm_names(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = MODULE.configure()
    module.ALLOWED_MISSING_TARGET_DATES = ()
    monkeypatch.setattr(MODULE, "EXPECTED_TRADES", 630)
    features, signal, targets = population()
    trades, funnel = module.build_trades(features, signal, targets)
    prior = {
        f"prior_{index}": np.tile(np.array([-1.0, 2.0, 1.0, -0.5]), 150)
        for index in range(16)
    }
    metrics = module.summarize_trades(
        trades,
        funnel,
        prior,
        SimpleNamespace(dsr=lambda *args: 0.99),
        permutations=100,
    )
    rendered: list[Path] = []
    monkeypatch.setattr(module, "_write_plot", lambda fig, path: rendered.append(path))
    paths = module.render_charts(trades, metrics, tmp_path)
    assert paths == rendered
    assert [path.name for path in paths] == list(module.CHART_NAMES)


def test_disarmed_or_armed_sentinel_normalization_is_stable() -> None:
    value = MODULE.REVIEWED_REGISTRY_ROW_SHA256
    assert value is None or (isinstance(value, str) and len(value) == 64)
    payload = SCRIPT.read_bytes()
    base = MODULE.normalized_evaluator_base_sha256(payload)
    if value is None:
        armed = payload.replace(
            b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None",
            b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"',
            1,
        )
    else:
        armed = payload.replace(value.encode("ascii"), b"A" * 64, 1)
    assert MODULE.normalized_evaluator_base_sha256(armed) == base


def test_authority_fails_closed_while_disarmed(tmp_path: Path) -> None:
    module = MODULE.configure()
    if MODULE.REVIEWED_REGISTRY_ROW_SHA256 is None:
        with pytest.raises(module.ContractError, match="not armed"):
            module.validate_authority(tmp_path)
