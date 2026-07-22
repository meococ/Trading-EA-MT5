from __future__ import annotations

from datetime import datetime, timezone
import math

from vras_reference import (
    Regime,
    WeightedWelford,
    confirmed_fractal,
    is_europe_dst,
    is_us_dst,
    server_to_utc,
    update_regime,
)


def test_weighted_welford_hand_fixture() -> None:
    state = WeightedWelford()
    for price, weight in ((100.0, 1.0), (101.0, 2.0), (103.0, 1.0)):
        state.add(price, weight)
    assert state.samples == 3
    assert state.mean == 101.25
    assert math.isclose(state.variance, 1.1875)
    assert math.isclose(state.sd, 1.0897247358851685)


def test_zero_weight_is_skipped_and_all_zero_is_not_ready() -> None:
    state = WeightedWelford()
    state.add(100.0, 0.0)
    assert state.samples == 0
    assert not state.ready(1)
    state.add(101.0, 2.0)
    assert state.samples == 1
    assert state.mean == 101.0


def test_adx_hysteresis_dwell_and_gray_zone() -> None:
    regime, age = Regime.RANGE, 99
    for adx in (21.0, 23.0, 21.0, 23.0):
        regime, age, switched = update_regime(regime, age, adx, 25.0, 19.0, 6)
        assert regime is Regime.RANGE
        assert not switched
    regime, age, switched = update_regime(regime, age, 25.0, 25.0, 19.0, 6)
    assert regime is Regime.TREND and switched and age == 0
    for _ in range(5):
        regime, age, switched = update_regime(regime, age, 18.0, 25.0, 19.0, 6)
        assert regime is Regime.TREND
    regime, age, switched = update_regime(regime, age, 18.0, 25.0, 19.0, 6)
    assert regime is Regime.RANGE and switched


def test_eu_and_us_dst_boundaries_2026() -> None:
    utc = timezone.utc
    assert not is_europe_dst(datetime(2026, 3, 29, 0, 59, tzinfo=utc))
    assert is_europe_dst(datetime(2026, 3, 29, 1, 0, tzinfo=utc))
    assert is_europe_dst(datetime(2026, 10, 25, 0, 59, tzinfo=utc))
    assert not is_europe_dst(datetime(2026, 10, 25, 1, 0, tzinfo=utc))
    assert not is_us_dst(datetime(2026, 3, 8, 6, 59, tzinfo=utc))
    assert is_us_dst(datetime(2026, 3, 8, 7, 0, tzinfo=utc))
    assert is_us_dst(datetime(2026, 11, 1, 5, 59, tzinfo=utc))
    assert not is_us_dst(datetime(2026, 11, 1, 6, 0, tzinfo=utc))


def test_server_to_utc_uses_us_dst_following_offset() -> None:
    winter = datetime(2026, 1, 15, 9, 0)
    summer = datetime(2026, 7, 15, 10, 0)
    assert server_to_utc(winter, 2, True).hour == 7
    assert server_to_utc(summer, 2, True).hour == 7


def test_five_bar_fractal_requires_two_newer_closed_bars() -> None:
    lows = [1.4, 1.3, 1.0, 1.2, 1.5]
    highs = [2.0, 2.1, 2.2, 2.1, 2.0]
    assert confirmed_fractal(lows[:4], "low") is None
    assert confirmed_fractal(lows, "low") == 2
    assert confirmed_fractal(highs, "high") == 2
