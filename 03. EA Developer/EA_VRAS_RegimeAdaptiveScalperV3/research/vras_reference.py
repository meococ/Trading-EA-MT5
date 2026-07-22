"""Small outcome-blind reference functions for VRAS contract tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
import calendar
import math


class Regime(Enum):
    RANGE = 0
    TREND = 1


@dataclass
class WeightedWelford:
    weight: float = 0.0
    mean: float = 0.0
    m2: float = 0.0
    samples: int = 0

    def add(self, value: float, weight: float) -> None:
        if not math.isfinite(value) or not math.isfinite(weight):
            raise ValueError("non-finite Welford input")
        if weight <= 0.0:
            return
        new_weight = self.weight + weight
        delta = value - self.mean
        self.mean += weight / new_weight * delta
        self.m2 += weight * delta * (value - self.mean)
        self.weight = new_weight
        self.samples += 1

    @property
    def variance(self) -> float:
        if self.weight <= 0.0:
            return math.nan
        return max(0.0, self.m2 / self.weight)

    @property
    def sd(self) -> float:
        return math.sqrt(self.variance)

    def ready(self, minimum_samples: int) -> bool:
        return self.samples >= minimum_samples and self.weight > 0.0


def update_regime(
    regime: Regime,
    bars_since_switch: int,
    adx: float,
    enter: float,
    exit_: float,
    minimum_dwell: int,
) -> tuple[Regime, int, bool]:
    """Apply the report's Schmitt trigger on one newly closed bar."""
    if not math.isfinite(adx):
        raise ValueError("ADX must be finite")
    age = bars_since_switch + 1
    if regime is Regime.RANGE and adx >= enter and age >= minimum_dwell:
        return Regime.TREND, 0, True
    if regime is Regime.TREND and adx < exit_ and age >= minimum_dwell:
        return Regime.RANGE, 0, True
    return regime, age, False


def _last_sunday(year: int, month: int) -> int:
    day = calendar.monthrange(year, month)[1]
    while datetime(year, month, day).weekday() != 6:
        day -= 1
    return day


def _nth_sunday(year: int, month: int, ordinal: int) -> int:
    day = 1
    while datetime(year, month, day).weekday() != 6:
        day += 1
    return day + 7 * (ordinal - 1)


def is_europe_dst(value_utc: datetime) -> bool:
    value_utc = value_utc.astimezone(timezone.utc)
    start = datetime(value_utc.year, 3, _last_sunday(value_utc.year, 3), 1, tzinfo=timezone.utc)
    end = datetime(value_utc.year, 10, _last_sunday(value_utc.year, 10), 1, tzinfo=timezone.utc)
    return start <= value_utc < end


def is_us_dst(value_utc: datetime) -> bool:
    value_utc = value_utc.astimezone(timezone.utc)
    start = datetime(value_utc.year, 3, _nth_sunday(value_utc.year, 3, 2), 7, tzinfo=timezone.utc)
    end = datetime(value_utc.year, 11, _nth_sunday(value_utc.year, 11, 1), 6, tzinfo=timezone.utc)
    return start <= value_utc < end


def server_to_utc(server_naive: datetime, winter_offset_hours: int, follows_us_dst: bool) -> datetime:
    if server_naive.tzinfo is not None:
        server_naive = server_naive.replace(tzinfo=None)
    winter_candidate = (server_naive - timedelta(hours=winter_offset_hours)).replace(tzinfo=timezone.utc)
    offset = winter_offset_hours + (1 if follows_us_dst and is_us_dst(winter_candidate) else 0)
    return (server_naive - timedelta(hours=offset)).replace(tzinfo=timezone.utc)


def confirmed_fractal(values: list[float], kind: str) -> int | None:
    """Return the latest strict five-bar center, or None before confirmation."""
    if len(values) < 5:
        return None
    for center in range(len(values) - 3, 1, -1):
        window = values[center - 2 : center + 3]
        pivot = window[2]
        others = window[:2] + window[3:]
        if kind == "low" and all(pivot < value for value in others):
            return center
        if kind == "high" and all(pivot > value for value in others):
            return center
    return None
