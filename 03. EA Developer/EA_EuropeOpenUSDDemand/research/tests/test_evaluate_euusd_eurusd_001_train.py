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
MODULE_PATH = RESEARCH / "evaluate_euusd_eurusd_001_train.py"
SPEC = importlib.util.spec_from_file_location("evaluate_euusd_eurusd_001_train", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
eueur = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = eueur
SPEC.loader.exec_module(eueur)


def local_bar(date: str, clock: str, close: float) -> tuple[pd.Timestamp, float]:
    return pd.Timestamp(f"{date} {clock}", tz="Europe/Berlin").tz_convert("UTC"), close


def frame_for_days(days: list[tuple[str, float, float]]) -> pd.DataFrame:
    rows: list[tuple[pd.Timestamp, float]] = []
    for date, entry, exit_ in days:
        rows.extend([local_bar(date, "07:59", entry), local_bar(date, "14:14", exit_)])
    rows.sort(key=lambda item: item[0])
    return pd.DataFrame(rows, columns=["time_utc", "close"])


def test_builds_fixed_short_eurusd_trade() -> None:
    row = eueur.build_trades_from_frame(frame_for_days([("2019-01-07", 1.1500, 1.1490)])).iloc[0]
    assert row["direction"] == -1
    assert row["raw_move_pips"] == pytest.approx(-10.0)
    assert row["gross_pips"] == pytest.approx(10.0)
    assert row["primary_net_x1_pips"] == pytest.approx(8.5)
    assert row["reverse_net_x1_pips"] == pytest.approx(-11.5)


def test_price_rise_remains_short_loss() -> None:
    row = eueur.build_trades_from_frame(frame_for_days([("2019-01-08", 1.1490, 1.1500)])).iloc[0]
    assert row["direction"] == -1
    assert row["gross_pips"] == pytest.approx(-10.0)


def test_berlin_dst_preserves_exact_slots() -> None:
    trades = eueur.build_trades_from_frame(frame_for_days([("2019-03-29", 1.15, 1.149), ("2019-04-01", 1.15, 1.149)]))
    assert trades["local_date"].astype(str).tolist() == ["2019-03-29", "2019-04-01"]
    assert trades["entry_local_hhmm"].tolist() == ["07:59", "07:59"]
    assert trades["exit_local_hhmm"].tolist() == ["14:14", "14:14"]


def test_missing_boundary_drops_day() -> None:
    frame = frame_for_days([("2019-01-07", 1.15, 1.149)]).iloc[:-1]
    assert eueur.build_trades_from_frame(frame).empty


def test_weekend_is_excluded() -> None:
    assert eueur.build_trades_from_frame(frame_for_days([("2019-01-05", 1.15, 1.149)])).empty


def test_duplicate_timestamp_fails_closed() -> None:
    frame = frame_for_days([("2019-01-07", 1.15, 1.149)])
    duplicate = pd.concat([frame, frame.iloc[[0]]], ignore_index=True).sort_values("time_utc")
    with pytest.raises(eueur.ContractError, match="unique"):
        eueur.build_trades_from_frame(duplicate)


def test_profit_factor_never_invents_zero_loss_infinity() -> None:
    assert eueur.profit_factor([2, -1, 3, -4]) == pytest.approx(1.0)
    assert eueur.profit_factor([1, 2]) is None


def test_sign_flip_is_seeded() -> None:
    values = np.array([3.0, -2.0, 2.0, -1.0, 4.0, -3.0])
    assert eueur.sign_flip_p_value(values, permutations=200, seed=7) == eueur.sign_flip_p_value(values, permutations=200, seed=7)


def test_normalized_hash_ignores_only_sentinel() -> None:
    base = MODULE_PATH.read_bytes()
    armed = re.sub(
        rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")$',
        b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"',
        base,
        count=1,
        flags=re.MULTILINE,
    )
    assert armed != base
    assert eueur.normalized_evaluator_base_sha256(base) == eueur.normalized_evaluator_base_sha256(armed)
    with pytest.raises(eueur.ContractError, match="exactly one"):
        eueur.normalized_evaluator_base_sha256(base + b"\n" + base)


def test_dsr_contains_eight_declared_arms() -> None:
    common = eueur.load_common(WORKSPACE)
    module = common.load_helper(WORKSPACE).load_dsr_module(WORKSPACE)
    values = np.array([-3.0, 2.0, -1.0, 1.0, -2.0, 1.0])
    prior = {
        "lojm001_primary": values,
        "lojm001_reverse": -values,
        "lofix002_primary": values + 0.1,
        "lofix002_reverse": -values - 0.1,
        "euusd_usdjpy_001_primary": values + 0.2,
        "euusd_usdjpy_001_reverse": -values - 0.2,
    }
    current = np.array([2.0, 4.0, 3.0, 5.0, 1.0, 4.0])
    result = eueur.compute_dsr(current, -current - 3.0, prior, module)
    assert result["n_trials"] == 8
    assert len(result["arms"]) == 8


def test_summary_applies_all_frozen_gates() -> None:
    dates = pd.bdate_range("2016-01-04", "2020-12-31")
    index = np.arange(len(dates))
    gross = np.where(index % 10 == 0, -4.0, 50.0 + (index % 3))
    trades = pd.DataFrame({"local_date": dates.date, "year": dates.year, "weekday": dates.weekday, "direction": -np.ones(len(dates), dtype=int), "entry_local_hhmm": ["07:59"] * len(dates), "exit_local_hhmm": ["14:14"] * len(dates), "gross_pips": gross})
    for label, cost in eueur.COSTS.items():
        trades[f"primary_net_{label}_pips"] = gross - cost
        trades[f"reverse_net_{label}_pips"] = -gross - cost
    weak = np.where(index % 2 == 0, 1.0, -1.0)
    prior = {"lojm001_primary": weak, "lojm001_reverse": -weak, "lofix002_primary": np.roll(weak, 1), "lofix002_reverse": -np.roll(weak, 1), "euusd_usdjpy_001_primary": np.roll(weak, 2), "euusd_usdjpy_001_reverse": -np.roll(weak, 2)}
    common = eueur.load_common(WORKSPACE)
    module = common.load_helper(WORKSPACE).load_dsr_module(WORKSPACE)
    metrics = eueur.summarize_trades(trades, prior=prior, dsr_module=module, permutations=200, seed=17)
    assert metrics["source_gate_pass_count"] == metrics["source_gate_total"] == 5
    assert metrics["economic_gate_pass_count"] == metrics["economic_gate_total"] == 8
    assert metrics["positive_years"] == 5
