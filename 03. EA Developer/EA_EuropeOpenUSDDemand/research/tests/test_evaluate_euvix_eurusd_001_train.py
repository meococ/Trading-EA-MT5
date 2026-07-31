from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd
import pytest


RESEARCH = Path(__file__).resolve().parents[1]
WORKSPACE = Path(__file__).resolve().parents[4]
MODULE_PATH = RESEARCH / "evaluate_euvix_eurusd_001_train.py"
SPEC = importlib.util.spec_from_file_location("evaluate_euvix_eurusd_001_train", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
euvix = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = euvix
SPEC.loader.exec_module(euvix)


def parent_frame(dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"local_date": dates, "trade_date": pd.to_datetime(dates), "year": pd.to_datetime(dates).year, "weekday": pd.to_datetime(dates).weekday, "direction": ["SHORT"] * len(dates), "entry_local_hhmm": ["07:59"] * len(dates), "exit_local_hhmm": ["14:14"] * len(dates), "gross_pips": np.arange(1, len(dates) + 1, dtype=float)})


def test_strict_lag_never_uses_same_date_vix_close() -> None:
    parent = parent_frame(["2020-01-06"])
    vix = pd.DataFrame({"vix_date": pd.to_datetime(["2020-01-03", "2020-01-06"]), "vix_close": [20.0, 99.0], "vix_threshold": [18.0, 18.0]})
    selected, coverage = euvix.select_high_vix(parent, vix)
    assert coverage == 1.0
    assert selected.iloc[0]["vix_date"] == pd.Timestamp("2020-01-03")
    assert selected.iloc[0]["vix_close"] == 20.0
    assert selected.iloc[0]["vix_lag_days"] == 3


def test_only_high_vix_rows_are_selected() -> None:
    parent = parent_frame(["2020-01-06", "2020-01-07"])
    vix = pd.DataFrame({"vix_date": pd.to_datetime(["2020-01-03", "2020-01-06"]), "vix_close": [17.0, 20.0], "vix_threshold": [18.0, 18.0]})
    selected, _ = euvix.select_high_vix(parent, vix)
    assert selected["local_date"].tolist() == ["2020-01-07"]


def test_missing_threshold_is_warmup_not_trade() -> None:
    parent = parent_frame(["2020-01-06"])
    vix = pd.DataFrame({"vix_date": pd.to_datetime(["2020-01-03"]), "vix_close": [20.0], "vix_threshold": [np.nan]})
    with pytest.raises(euvix.ContractError, match="selected"):
        euvix.select_high_vix(parent, vix)


def test_profit_factor_never_invents_zero_loss_infinity() -> None:
    assert euvix.profit_factor([2, -1, 3, -4]) == pytest.approx(1.0)
    assert euvix.profit_factor([1, 2]) is None


def test_sign_flip_is_seeded() -> None:
    values = np.array([3.0, -2.0, 2.0, -1.0, 4.0, -3.0])
    assert euvix.sign_flip_p_value(values, permutations=200, seed=7) == euvix.sign_flip_p_value(values, permutations=200, seed=7)


def test_normalized_hash_ignores_only_sentinel() -> None:
    base = MODULE_PATH.read_bytes()
    armed = re.sub(rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")$', b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"', base, count=1, flags=re.MULTILINE)
    assert armed != base
    assert euvix.normalized_evaluator_base_sha256(base) == euvix.normalized_evaluator_base_sha256(armed)
    with pytest.raises(euvix.ContractError, match="exactly one"):
        euvix.normalized_evaluator_base_sha256(base + b"\n" + base)


def test_parent_evaluator_dependency_is_hash_bound() -> None:
    module = euvix.load_parent_module(WORKSPACE)
    assert module.HYPOTHESIS_ID == "HYP-EUUSD-EURUSD-M1-001"


def test_dsr_contains_ten_declared_arms() -> None:
    parent_module = euvix.load_parent_module(WORKSPACE)
    dsr_module = parent_module.load_common(WORKSPACE).load_helper(WORKSPACE).load_dsr_module(WORKSPACE)
    base = np.array([-3.0, 2.0, -1.0, 1.0, -2.0, 1.0])
    prior = {f"arm_{i}": np.roll(base, i) + i * 0.01 for i in range(8)}
    current = np.array([2.0, 4.0, 3.0, 5.0, 1.0, 4.0])
    result = euvix.compute_dsr(current, -current - 3.0, prior, dsr_module)
    assert result["n_trials"] == 10
    assert len(result["arms"]) == 10


def test_summary_applies_all_frozen_gates() -> None:
    dates = pd.DatetimeIndex(np.concatenate([pd.bdate_range(f"{year}-01-01", periods=120).to_numpy() for year in range(2016, 2021)]))
    index = np.arange(len(dates)); gross = np.where(index % 10 == 0, -4.0, 50.0 + index % 3)
    selected = pd.DataFrame({"local_date": dates.strftime("%Y-%m-%d"), "year": dates.year, "weekday": dates.weekday, "gross_pips": gross})
    for label, cost in euvix.COSTS.items():
        selected[f"primary_net_{label}_pips"] = gross - cost
        selected[f"reverse_net_{label}_pips"] = -gross - cost
    weak = np.where(index % 2 == 0, 1.0, -1.0)
    prior = {f"arm_{i}": np.roll(weak, i) for i in range(8)}
    parent_module = euvix.load_parent_module(WORKSPACE)
    dsr_module = parent_module.load_common(WORKSPACE).load_helper(WORKSPACE).load_dsr_module(WORKSPACE)
    metrics = euvix.summarize(selected, mapping_coverage=1.0, prior=prior, dsr_module=dsr_module, permutations=200, seed=17)
    assert metrics["source_gate_pass_count"] == metrics["source_gate_total"] == 5
    assert metrics["economic_gate_pass_count"] == metrics["economic_gate_total"] == 8
    assert metrics["positive_years"] == 5
