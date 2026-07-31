from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "evaluate_lojm_001_train.py"
SPEC = importlib.util.spec_from_file_location("evaluate_lojm_001_train", MODULE_PATH)
assert SPEC and SPEC.loader
lojm = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lojm
SPEC.loader.exec_module(lojm)


def local_utc(day: str, hour: int, minute: int) -> pd.Timestamp:
    return pd.Timestamp(f"{day} {hour:02d}:{minute:02d}", tz="Europe/London").tz_convert("UTC")


def make_source(days: list[str], *, missing: tuple[str, str] | None = None) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    slots = {"pre": (7, 59), "entry": (8, 29), "exit": (16, 29)}
    for index, day in enumerate(days):
        positive = index % 2 == 0
        values = (
            {"pre": 150.00, "entry": 150.10, "exit": 150.15}
            if positive
            else {"pre": 150.10, "entry": 150.00, "exit": 149.95}
        )
        for slot, (hour, minute) in slots.items():
            if missing == (day, slot):
                continue
            rows.append(
                {
                    "time_utc": local_utc(day, hour, minute),
                    "close": values[slot],
                }
            )
    return pd.DataFrame(rows).sort_values("time_utc").reset_index(drop=True)


def make_summary_trades() -> pd.DataFrame:
    dates = []
    for year in range(2016, 2021):
        dates.extend(pd.date_range(f"{year}-01-04", periods=250, freq="B").date)
    count = len(dates)
    direction = np.where(np.arange(count) % 2 == 0, 1, -1)
    gross = np.where(np.arange(count) % 5 == 0, -5.0, 5.0)
    raw_move = gross / direction
    frame = pd.DataFrame(
        {
            "local_date": dates,
            "year": [day.year for day in dates],
            "direction": direction,
            "pre_close": 150.0,
            "entry_close": 150.1,
            "exit_close": 150.1 + raw_move * lojm.PIP_SIZE,
            "formation_log_return": direction * 0.001,
            "raw_move_pips": raw_move,
            "gross_pips": gross,
        }
    )
    for label, cost in lojm.COSTS.items():
        frame[f"primary_net_{label}_pips"] = gross - cost
        frame[f"reverse_net_{label}_pips"] = -gross - cost
    return frame


def test_normalized_evaluator_hash_ignores_only_sentinel_value() -> None:
    payload = MODULE_PATH.read_bytes()
    base = lojm.normalized_evaluator_base_sha256(payload)
    armed = payload.replace(
        b"\nREVIEWED_REGISTRY_ROW_SHA256: str | None = None\n",
        b'\nREVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"\n',
        1,
    )
    assert lojm.normalized_evaluator_base_sha256(armed) == base


def test_build_trades_uses_london_dst_and_locked_sign() -> None:
    source = make_source(["2019-03-29", "2019-04-01"])
    trades = lojm.build_trades_from_frame(source)
    assert list(trades["local_date"].astype(str)) == ["2019-03-29", "2019-04-01"]
    assert list(trades["direction"]) == [1, -1]
    assert trades["gross_pips"].tolist() == pytest.approx([5.0, 5.0])
    assert trades["primary_net_x1_pips"].tolist() == pytest.approx([3.5, 3.5])


def test_missing_exact_slot_drops_only_that_day() -> None:
    source = make_source(
        ["2020-01-06", "2020-01-07"],
        missing=("2020-01-06", "exit"),
    )
    trades = lojm.build_trades_from_frame(source)
    assert list(trades["local_date"].astype(str)) == ["2020-01-07"]


def test_duplicate_timestamp_is_rejected() -> None:
    source = make_source(["2020-01-06"])
    source = pd.concat([source, source.iloc[[0]]], ignore_index=True).sort_values("time_utc")
    with pytest.raises(lojm.ContractError, match="unique"):
        lojm.build_trades_from_frame(source)


def test_profit_factor_is_fail_closed() -> None:
    assert lojm.profit_factor([3.0, -2.0, 1.0, -2.0]) == pytest.approx(1.0)
    assert lojm.profit_factor([1.0, 2.0]) is None
    assert lojm.profit_factor([-1.0, -2.0]) is None


def test_permutation_is_deterministic_and_one_sided() -> None:
    directions = np.array([1, -1] * 100)
    raw_moves = directions * 4.0
    first = lojm.permutation_p_value(directions, raw_moves, permutations=999, seed=7)
    second = lojm.permutation_p_value(directions, raw_moves, permutations=999, seed=7)
    assert first == second
    assert first <= 0.01


def test_summary_survivor_requires_all_locked_gates() -> None:
    summary = lojm.summarize_trades(make_summary_trades(), permutations=999, seed=7)
    assert summary["trade_count"] == 1250
    assert summary["source_gate_pass_count"] == summary["source_gate_total"] == 5
    assert summary["economic_gate_pass_count"] == summary["economic_gate_total"] == 7
    assert summary["profit_factor"]["primary"]["x2"] == pytest.approx(1.0)
    assert summary["positive_years"] == 5


def test_summary_does_not_rescue_negative_primary() -> None:
    trades = make_summary_trades()
    trades["gross_pips"] = -5.0
    for label, cost in lojm.COSTS.items():
        trades[f"primary_net_{label}_pips"] = -5.0 - cost
        trades[f"reverse_net_{label}_pips"] = 5.0 - cost
    summary = lojm.summarize_trades(trades, permutations=99, seed=7)
    assert not summary["economic_gates"]["pf_x1_gt_1_30"]
    assert not summary["economic_gates"]["beats_reverse_x1"]
    assert summary["economic_gate_pass_count"] < summary["economic_gate_total"]


def test_real_run_is_disarmed_before_registry_freeze() -> None:
    sentinel = lojm.REVIEWED_REGISTRY_ROW_SHA256
    assert sentinel is None or (
        isinstance(sentinel, str)
        and len(sentinel) == 64
        and all(char in "0123456789ABCDEF" for char in sentinel)
    )
    if sentinel is None:
        with pytest.raises(lojm.ContractError, match="not armed"):
            lojm.validate_authority(Path("D:/Trading EA MT5"))
