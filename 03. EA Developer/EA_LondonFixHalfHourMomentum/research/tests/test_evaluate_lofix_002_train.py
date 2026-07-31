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
MODULE_PATH = RESEARCH / "evaluate_lofix_002_train.py"
SPEC = importlib.util.spec_from_file_location("evaluate_lofix_002_train", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
lofix = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lofix
SPEC.loader.exec_module(lofix)


def local_bar(local_date: str, clock: str, close: float) -> tuple[pd.Timestamp, float]:
    stamp = pd.Timestamp(f"{local_date} {clock}", tz="Europe/London").tz_convert("UTC")
    return stamp, close


def frame_for_days(days: list[tuple[str, float, float, float, float]]) -> pd.DataFrame:
    rows: list[tuple[pd.Timestamp, float]] = []
    for local_date, pre, signal, entry, exit_ in days:
        rows.extend(
            [
                local_bar(local_date, "07:59", pre),
                local_bar(local_date, "08:29", signal),
                local_bar(local_date, "15:29", entry),
                local_bar(local_date, "15:59", exit_),
            ]
        )
    rows.sort(key=lambda item: item[0])
    return pd.DataFrame(rows, columns=["time_utc", "close"])


def test_builds_pre_fix_half_hour_trade_in_signal_direction() -> None:
    frame = frame_for_days([("2019-01-07", 110.00, 110.10, 110.20, 110.25)])
    trades = lofix.build_trades_from_frame(frame)
    assert len(trades) == 1
    row = trades.iloc[0]
    assert row["direction"] == 1
    assert row["raw_move_pips"] == pytest.approx(5.0)
    assert row["gross_pips"] == pytest.approx(5.0)
    assert row["primary_net_x1_pips"] == pytest.approx(3.5)
    assert row["reverse_net_x1_pips"] == pytest.approx(-6.5)


def test_negative_signal_shorts_same_pre_fix_price_rise() -> None:
    frame = frame_for_days([("2019-01-08", 110.10, 110.00, 110.20, 110.25)])
    row = lofix.build_trades_from_frame(frame).iloc[0]
    assert row["direction"] == -1
    assert row["raw_move_pips"] == pytest.approx(5.0)
    assert row["gross_pips"] == pytest.approx(-5.0)


def test_london_dst_conversion_preserves_local_slots() -> None:
    frame = frame_for_days(
        [
            ("2019-03-29", 110.00, 110.10, 110.20, 110.25),
            ("2019-04-01", 110.00, 109.90, 110.20, 110.15),
        ]
    )
    trades = lofix.build_trades_from_frame(frame)
    assert trades["local_date"].astype(str).tolist() == ["2019-03-29", "2019-04-01"]
    assert trades["direction"].tolist() == [1, -1]


def test_missing_exact_slot_drops_date_without_nearest_match() -> None:
    frame = frame_for_days([("2019-01-07", 110.00, 110.10, 110.20, 110.25)])
    frame = frame.iloc[:-1].copy()
    assert lofix.build_trades_from_frame(frame).empty


def test_zero_formation_is_the_only_signal_skip() -> None:
    frame = frame_for_days([("2019-01-07", 110.00, 110.00, 110.20, 110.25)])
    assert lofix.build_trades_from_frame(frame).empty


def test_duplicate_timestamp_fails_closed() -> None:
    frame = frame_for_days([("2019-01-07", 110.00, 110.10, 110.20, 110.25)])
    duplicate = pd.concat([frame, frame.iloc[[0]]], ignore_index=True).sort_values("time_utc")
    with pytest.raises(lofix.ContractError, match="unique"):
        lofix.build_trades_from_frame(duplicate)


def test_profit_factor_does_not_turn_zero_loss_into_infinity() -> None:
    assert lofix.profit_factor([2.0, -1.0, 3.0, -4.0]) == pytest.approx(1.0)
    assert lofix.profit_factor([1.0, 2.0]) is None
    assert lofix.profit_factor([-1.0, -2.0]) is None


def test_permutation_is_seeded_and_one_sided() -> None:
    directions = np.array([1, -1, 1, -1, 1, -1])
    moves = np.array([3.0, -2.0, 2.0, -1.0, 4.0, -3.0])
    first = lofix.permutation_p_value(directions, moves, permutations=200, seed=7)
    second = lofix.permutation_p_value(directions, moves, permutations=200, seed=7)
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
    assert lofix.normalized_evaluator_base_sha256(base) == lofix.normalized_evaluator_base_sha256(armed)
    with pytest.raises(lofix.ContractError, match="exactly one"):
        lofix.normalized_evaluator_base_sha256(base + b"\n" + base)


def test_declared_dsr_trial_universe_contains_four_x1_arms() -> None:
    module = lofix.load_dsr_module(WORKSPACE)
    prior_primary = np.array([-4.0, 1.0, -2.0, 1.0, -1.0, 1.0])
    prior_reverse = -prior_primary - 3.0
    current_primary = np.array([2.0, 4.0, 3.0, 5.0, 1.0, 4.0])
    current_reverse = -current_primary - 3.0
    result = lofix.compute_dsr(
        current_primary,
        current_reverse,
        prior_primary,
        prior_reverse,
        module,
    )
    assert result["n_trials"] == 4
    assert set(result["arms"]) == {
        "lojm001_primary",
        "lojm001_reverse",
        "lofix002_primary",
        "lofix002_reverse",
    }
    assert 0.0 <= result["primary_dsr"] <= 1.0


def test_summary_applies_all_frozen_survivor_gates() -> None:
    dates = pd.bdate_range("2016-01-04", "2020-12-31")
    direction = np.where(np.arange(len(dates)) % 2 == 0, 1, -1)
    index = np.arange(len(dates))
    gross = np.where(index % 10 == 0, -4.0, 50.0 + (index % 3))
    raw_move = direction * gross
    trades = pd.DataFrame(
        {
            "local_date": dates.date,
            "year": dates.year,
            "direction": direction,
            "raw_move_pips": raw_move,
            "gross_pips": gross,
        }
    )
    for label, cost in lofix.COSTS.items():
        trades[f"primary_net_{label}_pips"] = gross - cost
        trades[f"reverse_net_{label}_pips"] = -gross - cost
    module = lofix.load_dsr_module(WORKSPACE)
    prior_primary = np.where(index % 2 == 0, 1.0, -1.0)
    prior_reverse = np.where(index % 2 == 0, -1.0, 1.0)
    metrics = lofix.summarize_trades(
        trades,
        prior_primary=prior_primary,
        prior_reverse=prior_reverse,
        dsr_module=module,
        permutations=200,
        seed=17,
    )
    assert metrics["source_gate_pass_count"] == metrics["source_gate_total"] == 5
    assert metrics["economic_gate_pass_count"] == metrics["economic_gate_total"] == 8
    assert metrics["trades_per_elapsed_week"] <= 5.0
    assert metrics["positive_years"] == 5
