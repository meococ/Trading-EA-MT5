from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_NYOpeningDriveContinuation.mq5"
PREREG = ROOT / "research" / "HYP-NYOD-XAUUSD-M15-001_FROZEN_PREREG.md"
CONTRACT = ROOT / "ALPHAFACTORY_EA_CONTRACT.json"


def _second_sunday_march(year: int) -> datetime:
    day = 1
    first = datetime(year, 3, day, tzinfo=timezone.utc)
    day += (6 - first.weekday()) % 7
    return datetime(year, 3, day + 7, 7, tzinfo=timezone.utc)


def _first_sunday_november(year: int) -> datetime:
    first = datetime(year, 11, 1, tzinfo=timezone.utc)
    day = 1 + (6 - first.weekday()) % 7
    return datetime(year, 11, day, 6, tzinfo=timezone.utc)


def utc_to_new_york(utc: datetime) -> datetime:
    dst = _second_sunday_march(utc.year) <= utc < _first_sunday_november(utc.year)
    return utc - timedelta(hours=4 if dst else 5)


@dataclass(frozen=True)
class Bar:
    open: float
    high: float
    low: float
    close: float


def classify(drive: Bar, previous_close: float, atr: float, prior_high: float, prior_low: float) -> int:
    true_range = max(
        drive.high - drive.low,
        abs(drive.high - previous_close),
        abs(drive.low - previous_close),
    )
    bar_range = drive.high - drive.low
    if atr <= 0 or true_range <= 0 or bar_range <= 0:
        return 0
    body = abs(drive.close - drive.open)
    common = true_range >= atr and body >= 0.60 * bar_range
    long_location = (drive.close - drive.low) / bar_range
    short_location = (drive.high - drive.close) / bar_range
    long_signal = (
        common
        and drive.close > drive.open
        and long_location >= 0.75
        and drive.close > prior_high
    )
    short_signal = (
        common
        and drive.close < drive.open
        and short_location >= 0.75
        and drive.close < prior_low
    )
    if long_signal == short_signal:
        return 0
    return 1 if long_signal else -1


def test_exact_closed_bar_and_prior_atr_contract() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert "CopyRates(_Symbol,PERIOD_M15,1,REQUIRED_RATES,rates)" in source
    assert "CopyBuffer(g_atr_handle,0,2,1,values)" in source
    assert "DATA_EPOCH_D0_SERIES_PROOF" in source
    assert "if(!EmitD0SeriesProof())" in source
    assert "availability_time-decision_time)!=900" in source
    assert "rates[drive].close>prior_high" in source
    assert "rates[drive].close<prior_low" in source
    assert "TARGET_R=1.50" in source
    assert "MAX_HOLD_BARS=6" in source
    assert "CopyRates(_Symbol,PERIOD_M15,0" not in source
    assert "CopyBuffer(g_atr_handle,0,0" not in source


def test_authority_identity_is_consistent() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    prereg = PREREG.read_text(encoding="utf-8")
    contract = CONTRACT.read_text(encoding="utf-8")
    for content in (source, prereg, contract):
        assert "HYP-NYOD-XAUUSD-M15-001" in content
    assert '"telemetry_profile": "none"' in contract
    assert '"expected_symbol": "XAUUSD"' in contract


def test_new_york_dst_boundaries() -> None:
    assert utc_to_new_york(datetime(2019, 3, 8, 13, 15, tzinfo=timezone.utc)).hour == 8
    assert utc_to_new_york(datetime(2019, 3, 11, 12, 15, tzinfo=timezone.utc)).hour == 8
    assert utc_to_new_york(datetime(2019, 11, 1, 12, 15, tzinfo=timezone.utc)).hour == 8
    assert utc_to_new_york(datetime(2019, 11, 4, 13, 15, tzinfo=timezone.utc)).hour == 8


def test_long_short_and_inside_range_boundaries() -> None:
    assert classify(Bar(100.0, 102.2, 99.9, 102.0), 100.0, 2.0, 101.8, 98.0) == 1
    assert classify(Bar(100.0, 100.1, 97.8, 98.0), 100.0, 2.0, 102.0, 98.2) == -1
    assert classify(Bar(100.0, 102.0, 99.9, 101.7), 100.0, 2.0, 101.8, 98.0) == 0
    assert classify(Bar(100.0, 102.2, 99.9, 101.2), 100.0, 2.0, 101.0, 98.0) == 0


def test_gap_does_not_fake_close_location() -> None:
    # True range may pass from a gap, but the close must still sit in the bar's
    # own outer quartile and the body must occupy at least 60% of that bar.
    assert classify(Bar(104.0, 104.3, 103.7, 104.1), 100.0, 2.0, 103.9, 98.0) == 0
