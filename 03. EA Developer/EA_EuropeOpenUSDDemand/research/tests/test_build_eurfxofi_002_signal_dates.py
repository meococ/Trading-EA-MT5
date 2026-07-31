from __future__ import annotations

from datetime import date, datetime, timedelta
import importlib.util
from pathlib import Path
import sys

import pandas as pd


RESEARCH = Path(__file__).resolve().parents[1]
PATH = RESEARCH / "build_eurfxofi_002_signal_dates.py"
SPEC = importlib.util.spec_from_file_location("build_eurfxofi_002_signal_dates", PATH)
assert SPEC is not None and SPEC.loader is not None
sut = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sut
SPEC.loader.exec_module(sut)


def test_target_map_uses_berlin_dst_and_exact_two_slots() -> None:
    targets = sut.target_timestamp_map(date(2016, 1, 4))
    winter = {stamp: value for stamp, value in targets.items() if value[0] == date(2016, 1, 4)}
    assert winter[datetime(2016, 1, 4, 6, 59)] == (date(2016, 1, 4), "open")
    assert winter[datetime(2016, 1, 4, 13, 14)] == (date(2016, 1, 4), "entry")
    summer_targets = sut.target_timestamp_map(date(2016, 7, 4))
    summer = {stamp: value for stamp, value in summer_targets.items() if value[0] == date(2016, 7, 4)}
    assert summer[datetime(2016, 7, 4, 5, 59)] == (date(2016, 7, 4), "open")
    assert summer[datetime(2016, 7, 4, 12, 14)] == (date(2016, 7, 4), "entry")


def test_clock_inverse_is_exact_for_both_offsets() -> None:
    class Clock:
        @staticmethod
        def server_to_utc(value: datetime) -> datetime:
            offset = 3 if value.month == 7 else 2
            return value - timedelta(hours=offset)

    assert sut.utc_to_server_naive(datetime(2020, 1, 6, 13, 14), Clock) == datetime(2020, 1, 6, 15, 14)
    assert sut.utc_to_server_naive(datetime(2020, 7, 6, 12, 14), Clock) == datetime(2020, 7, 6, 15, 14)


def test_build_selection_is_strict_lag_and_never_needs_exit() -> None:
    rows = []
    day = date(2015, 10, 1)
    made = 0
    while made < 70:
        if day.weekday() < 5:
            pressure = 10.0 if made < 40 else 20.0
            rows.extend(
                [
                    {"local_date": day, "slot": "open", "close": 1.1000, "source": "test"},
                    {"local_date": day, "slot": "entry", "close": 1.1000 + pressure * sut.PIP_SIZE, "source": "test"},
                ]
            )
            made += 1
        day += timedelta(days=1)
    frame = pd.DataFrame(rows)
    result = sut.build_selection(frame, cutoff=max(frame["local_date"]))
    assert not result.empty
    assert set(result.columns) == {
        "request_id",
        "local_date",
        "split",
        "direction_from_pressure",
        "pre_fix_pressure_pips",
        "pressure_threshold_pips",
    }
    assert "exit" not in frame.columns
    assert (result["pre_fix_pressure_pips"].abs() >= result["pressure_threshold_pips"]).all()


def test_partitions_are_frozen_by_year() -> None:
    assert sut.split_for_day(date(2016, 1, 1)) == "TRAIN"
    assert sut.split_for_day(date(2020, 12, 31)) == "TRAIN"
    assert sut.split_for_day(date(2021, 1, 1)) == "VALIDATION"
    assert sut.split_for_day(date(2024, 12, 31)) == "VALIDATION"
    assert sut.split_for_day(date(2025, 1, 1)) == "HOLDOUT"


def test_source_projection_is_minimal() -> None:
    assert sut.ALLOWED_SOURCE_COLUMNS == ("time_utc", "close")
    assert set(sut.SLOTS) == {"open", "entry"}
    assert sut.SLOTS["entry"].hour == 14 and sut.SLOTS["entry"].minute == 14
