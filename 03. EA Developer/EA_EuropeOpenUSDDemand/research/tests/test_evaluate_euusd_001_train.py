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
MODULE_PATH = RESEARCH / "evaluate_euusd_001_train.py"
SPEC = importlib.util.spec_from_file_location("evaluate_euusd_001_train", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
euusd = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = euusd
SPEC.loader.exec_module(euusd)


def local_bar(local_date: str, clock: str, close: float) -> tuple[pd.Timestamp, float]:
    stamp = pd.Timestamp(f"{local_date} {clock}", tz="Europe/Berlin").tz_convert("UTC")
    return stamp, close


def frame_for_days(days: list[tuple[str, float, float]]) -> pd.DataFrame:
    rows: list[tuple[pd.Timestamp, float]] = []
    for local_date, entry, exit_ in days:
        rows.extend(
            [
                local_bar(local_date, "07:59", entry),
                local_bar(local_date, "14:14", exit_),
            ]
        )
    rows.sort(key=lambda item: item[0])
    return pd.DataFrame(rows, columns=["time_utc", "close"])


def test_builds_fixed_long_europe_open_to_ecb_fix_trade() -> None:
    frame = frame_for_days([("2019-01-07", 110.20, 110.25)])
    row = euusd.build_trades_from_frame(frame).iloc[0]
    assert row["direction"] == 1
    assert row["entry_local_hhmm"] == "07:59"
    assert row["exit_local_hhmm"] == "14:14"
    assert row["raw_move_pips"] == pytest.approx(5.0)
    assert row["primary_net_x1_pips"] == pytest.approx(3.5)
    assert row["reverse_net_x1_pips"] == pytest.approx(-6.5)


def test_negative_price_move_remains_long_loss() -> None:
    frame = frame_for_days([("2019-01-08", 110.25, 110.20)])
    row = euusd.build_trades_from_frame(frame).iloc[0]
    assert row["direction"] == 1
    assert row["gross_pips"] == pytest.approx(-5.0)
    assert row["primary_net_x1_pips"] == pytest.approx(-6.5)


def test_berlin_dst_conversion_preserves_exact_local_slots() -> None:
    frame = frame_for_days(
        [("2019-03-29", 110.20, 110.25), ("2019-04-01", 110.30, 110.35)]
    )
    trades = euusd.build_trades_from_frame(frame)
    assert trades["local_date"].astype(str).tolist() == ["2019-03-29", "2019-04-01"]
    assert trades["entry_local_hhmm"].tolist() == ["07:59", "07:59"]
    assert trades["exit_local_hhmm"].tolist() == ["14:14", "14:14"]


def test_missing_exact_slot_drops_date_without_nearest_match() -> None:
    frame = frame_for_days([("2019-01-07", 110.20, 110.25)]).iloc[:-1].copy()
    assert euusd.build_trades_from_frame(frame).empty


def test_weekend_is_not_eligible() -> None:
    frame = frame_for_days([("2019-01-05", 110.20, 110.25)])
    assert euusd.build_trades_from_frame(frame).empty


def test_duplicate_timestamp_fails_closed() -> None:
    frame = frame_for_days([("2019-01-07", 110.20, 110.25)])
    duplicate = pd.concat([frame, frame.iloc[[0]]], ignore_index=True).sort_values("time_utc")
    with pytest.raises(euusd.ContractError, match="unique"):
        euusd.build_trades_from_frame(duplicate)


def test_profit_factor_does_not_turn_zero_loss_into_infinity() -> None:
    assert euusd.profit_factor([2.0, -1.0, 3.0, -4.0]) == pytest.approx(1.0)
    assert euusd.profit_factor([1.0, 2.0]) is None
    assert euusd.profit_factor([-1.0, -2.0]) is None


def test_sign_flip_test_is_seeded_and_one_sided() -> None:
    moves = np.array([3.0, -2.0, 2.0, -1.0, 4.0, -3.0])
    first = euusd.sign_flip_p_value(moves, permutations=200, seed=7)
    second = euusd.sign_flip_p_value(moves, permutations=200, seed=7)
    assert first == second
    assert 0.0 < first <= 1.0


def test_normalized_hash_ignores_only_the_registry_sentinel() -> None:
    base = MODULE_PATH.read_bytes()
    armed = re.sub(
        rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")$',
        b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"',
        base,
        count=1,
        flags=re.MULTILINE,
    )
    assert armed != base
    assert euusd.normalized_evaluator_base_sha256(base) == euusd.normalized_evaluator_base_sha256(armed)
    with pytest.raises(euusd.ContractError, match="exactly one"):
        euusd.normalized_evaluator_base_sha256(base + b"\n" + base)


def test_declared_dsr_trial_universe_contains_six_x1_arms() -> None:
    helper = euusd.load_helper(WORKSPACE)
    module = helper.load_dsr_module(WORKSPACE)
    prior = {
        "lojm001_primary": np.array([-4.0, 1.0, -2.0, 1.0, -1.0, 1.0]),
        "lojm001_reverse": np.array([1.0, -4.0, 1.0, -2.0, 1.0, -1.0]),
        "lofix002_primary": np.array([-3.0, 2.0, -1.0, 1.0, -2.0, 1.0]),
        "lofix002_reverse": np.array([1.0, -3.0, 2.0, -1.0, 1.0, -2.0]),
    }
    current_primary = np.array([2.0, 4.0, 3.0, 5.0, 1.0, 4.0])
    current_reverse = -current_primary - 3.0
    result = euusd.compute_dsr(current_primary, current_reverse, prior, module)
    assert result["n_trials"] == 6
    assert set(result["arms"]) == set(prior) | {"euusd001_primary", "euusd001_reverse"}
    assert 0.0 <= result["primary_dsr"] <= 1.0


def test_summary_applies_all_frozen_survivor_gates() -> None:
    dates = pd.bdate_range("2016-01-04", "2020-12-31")
    index = np.arange(len(dates))
    gross = np.where(index % 10 == 0, -4.0, 50.0 + (index % 3))
    trades = pd.DataFrame(
        {
            "local_date": dates.date,
            "year": dates.year,
            "weekday": dates.weekday,
            "direction": np.ones(len(dates), dtype=int),
            "entry_local_hhmm": ["07:59"] * len(dates),
            "exit_local_hhmm": ["14:14"] * len(dates),
            "raw_move_pips": gross,
            "gross_pips": gross,
        }
    )
    for label, cost in euusd.COSTS.items():
        trades[f"primary_net_{label}_pips"] = gross - cost
        trades[f"reverse_net_{label}_pips"] = -gross - cost
    prior = {
        "lojm001_primary": np.where(index % 2 == 0, 1.0, -1.0),
        "lojm001_reverse": np.where(index % 2 == 0, -1.0, 1.0),
        "lofix002_primary": np.where(index % 3 == 0, 1.0, -1.0),
        "lofix002_reverse": np.where(index % 3 == 0, -1.0, 1.0),
    }
    helper = euusd.load_helper(WORKSPACE)
    module = helper.load_dsr_module(WORKSPACE)
    metrics = euusd.summarize_trades(
        trades,
        prior_arms=prior,
        dsr_module=module,
        permutations=200,
        seed=17,
    )
    assert metrics["source_gate_pass_count"] == metrics["source_gate_total"] == 5
    assert metrics["economic_gate_pass_count"] == metrics["economic_gate_total"] == 8
    assert metrics["trades_per_elapsed_week"] <= 5.0
    assert metrics["positive_years"] == 5
