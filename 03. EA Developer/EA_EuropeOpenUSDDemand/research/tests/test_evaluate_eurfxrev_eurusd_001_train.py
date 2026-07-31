from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd
import pytest


RESEARCH = Path(__file__).resolve().parents[1]
MODULE_PATH = RESEARCH / "evaluate_eurfxrev_eurusd_001_train.py"
SPEC = importlib.util.spec_from_file_location("evaluate_eurfxrev_eurusd_001_train", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
rev = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = rev
SPEC.loader.exec_module(rev)


def local(date: str, clock: str, close: float) -> tuple[pd.Timestamp, float]:
    return pd.Timestamp(f"{date} {clock}", tz="Europe/Berlin").tz_convert("UTC"), close


def frame(days: list[tuple[str, float, float, float]]) -> pd.DataFrame:
    rows = []
    for date, open_, entry, exit_ in days:
        rows.extend([local(date, "07:59", open_), local(date, "14:14", entry), local(date, "15:59", exit_)])
    rows.sort(key=lambda x: x[0])
    return pd.DataFrame(rows, columns=["time_utc", "close"])


def history(current_pressure: float, post_move: float) -> pd.DataFrame:
    dates = pd.bdate_range("2019-01-02", periods=41)
    days = []
    for i, date in enumerate(dates):
        pressure = 0.0010 if i < 40 else current_pressure
        entry = 1.10 + pressure
        days.append((date.date().isoformat(), 1.10, entry, entry + (post_move if i == 40 else 0.0)))
    return frame(days)


def test_reverses_negative_pressure_long() -> None:
    trades = rev.build_trades_from_frame(history(-0.0020, 0.0010))
    row = trades.iloc[-1]
    assert row["direction"] == 1
    assert row["gross_pips"] == pytest.approx(10.0)
    assert row["primary_net_x1_pips"] == pytest.approx(8.5)


def test_reverses_positive_pressure_short() -> None:
    trades = rev.build_trades_from_frame(history(0.0020, -0.0010))
    row = trades.iloc[-1]
    assert row["direction"] == -1
    assert row["gross_pips"] == pytest.approx(10.0)


def test_strict_lag_median_excludes_current() -> None:
    row = rev.build_trades_from_frame(history(0.0050, -0.0010)).iloc[-1]
    assert row["pressure_threshold_pips"] == pytest.approx(10.0)
    assert row["pre_fix_pressure_pips"] == pytest.approx(50.0)


def test_below_threshold_is_rejected() -> None:
    trades = rev.build_trades_from_frame(history(0.0005, -0.0010))
    assert trades.empty


def test_missing_exit_rejects_current_day() -> None:
    data = history(0.0020, -0.0010).iloc[:-1]
    assert rev.build_trades_from_frame(data).empty


def test_dst_preserves_local_slots() -> None:
    dates = pd.bdate_range("2019-02-01", periods=40).append(pd.DatetimeIndex([pd.Timestamp("2019-04-01")]))
    days = [(d.date().isoformat(), 1.10, 1.101, 1.100) for d in dates]
    row = rev.build_trades_from_frame(frame(days)).iloc[-1]
    assert row["local_date"].isoformat() == "2019-04-01"
    assert row["entry_local_hhmm"] == "14:14"
    assert row["exit_local_hhmm"] == "15:59"


def test_duplicate_timestamp_fails_closed() -> None:
    data = history(0.0020, -0.0010)
    duplicate = pd.concat([data, data.iloc[[0]]], ignore_index=True).sort_values("time_utc")
    with pytest.raises(rev.ContractError, match="integrity"):
        rev.build_trades_from_frame(duplicate)


def test_profit_factor_no_invented_infinity() -> None:
    assert rev.profit_factor([2, -1, 3, -4]) == pytest.approx(1.0)
    assert rev.profit_factor([1, 2]) is None


def test_sign_flip_seeded() -> None:
    values = np.array([3.0, -2.0, 2.0, -1.0, 4.0, -3.0])
    assert rev.sign_flip_p_value(values, permutations=200, seed=7) == rev.sign_flip_p_value(values, permutations=200, seed=7)


def test_normalized_hash_ignores_only_sentinel() -> None:
    base = MODULE_PATH.read_bytes()
    armed = re.sub(rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")$', b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"', base, count=1, flags=re.MULTILINE)
    assert armed != base
    assert rev.normalized_evaluator_base_sha256(base) == rev.normalized_evaluator_base_sha256(armed)


def test_dsr_declares_twelve_arms() -> None:
    dsr_path = RESEARCH.parents[2] / "02. AlphaFactory/tools/research/dsr.py"
    dsr = rev.load_module(dsr_path, rev.DSR_SHA256, "test_rev_dsr")
    weak = np.array([1.0, -1.0, 2.0, -2.0, 1.5, -0.5])
    prior = {f"arm_{i}": np.roll(weak, i) for i in range(10)}
    result = rev.compute_dsr(weak + .2, -weak - 1.7, prior, dsr)
    assert result["n_trials"] == 12
