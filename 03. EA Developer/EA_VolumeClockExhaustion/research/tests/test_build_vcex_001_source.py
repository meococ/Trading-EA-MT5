from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
import os
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "build_vcex_001_source.py"
SPEC = importlib.util.spec_from_file_location("build_vcex_001_source", SOURCE)
assert SPEC and SPEC.loader
sut = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sut)

UTC = timezone.utc
PLAN = Path(__file__).resolve().parents[1] / "HYP-VCEX-EURUSD-M15-001_SOURCE_FEASIBILITY_PLAN.md"


def utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def business_days(start: date, count: int) -> tuple[date, ...]:
    values: list[date] = []
    current = start
    while len(values) < count:
        if current.weekday() < 5:
            values.append(current)
        current += timedelta(days=1)
    return tuple(values)


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def m1_row(
    at: datetime,
    *,
    open_: float,
    high: float,
    low: float,
    close: float,
    tick_volume: float = 10.0,
) -> dict[str, object]:
    return {
        "time_utc": at,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "tick_volume": tick_volume,
    }


def flat_minutes(
    start: datetime,
    close: float = 1.1000,
    *,
    volumes: list[float] | None = None,
) -> list[dict[str, object]]:
    rows = []
    for index in range(15):
        at = start + timedelta(minutes=index)
        tv = 10.0 if volumes is None else float(volumes[index])
        rows.append(
            m1_row(
                at,
                open_=close,
                high=close + 0.00005,
                low=close - 0.00005,
                close=close,
                tick_volume=tv,
            )
        )
    return rows


def impulse_minutes(
    start: datetime,
    *,
    open_price: float,
    close_price: float,
    high: float | None = None,
    low: float | None = None,
    volumes: list[float] | None = None,
    early_close_at: int | None = None,
) -> list[dict[str, object]]:
    hi = high if high is not None else max(open_price, close_price) + 0.00010
    lo = low if low is not None else min(open_price, close_price) - 0.00010
    rows = []
    for index in range(15):
        at = start + timedelta(minutes=index)
        if early_close_at is not None and index <= early_close_at:
            # Ramp open->target by early_close_at, then hold/reverse via late path
            if early_close_at == 0:
                o = open_price
                c = close_price if index == 0 else close_price
            else:
                frac = index / float(early_close_at)
                mid = open_price + (close_price - open_price) * min(frac, 1.0)
                o = open_price if index == 0 else mid
                c = mid
        elif index == 0:
            o, c = open_price, open_price
        elif index == 14:
            o, c = open_price, close_price
        else:
            frac = index / 14.0
            mid = open_price + (close_price - open_price) * frac
            o, c = mid, mid
        tv = 10.0 if volumes is None else float(volumes[index])
        rows.append(m1_row(at, open_=o, high=hi, low=lo, close=c, tick_volume=tv))
    return rows


def early_mass_volumes(h: int, *, total: float = 100.0) -> list[float]:
    """Construct volumes so half-mass first crosses at minute h."""

    if not 0 <= h <= 14:
        raise ValueError("h out of range")
    # Put just under half before h, then enough at h to cross 0.5, rest after.
    vols = [0.0] * 15
    if h == 0:
        vols[0] = total * 0.50
        rem = total - vols[0]
        for index in range(1, 15):
            vols[index] = rem / 14.0
        return vols
    before = total * 0.49
    for index in range(h):
        vols[index] = before / float(h)
    vols[h] = total * 0.02  # crosses half-mass at h
    after = total - sum(vols)
    if h < 14:
        for index in range(h + 1, 15):
            vols[index] = after / float(14 - h)
    else:
        vols[h] += after
    return vols


def test_ast_parse_deliverables() -> None:
    for path in (SOURCE, Path(__file__), PLAN):
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".py":
            ast.parse(text)
        assert text


def test_complete_m15_exact_offsets_ohlc_and_volume() -> None:
    start = utc(2020, 1, 6, 8, 0)
    volumes = early_mass_volumes(3)
    rows = impulse_minutes(
        start,
        open_price=1.1000,
        close_price=1.1015,
        high=1.1020,
        low=1.0990,
        volumes=volumes,
    )
    bars, quality = sut.build_complete_m15(rows)
    assert quality == {"observed_bins": 1, "complete_bins": 1, "incomplete_bins": 0}
    assert len(bars) == 1
    assert bars[0]["time_utc"] == start
    assert bars[0]["availability_utc"] == start + timedelta(minutes=15)
    assert bars[0]["open"] == pytest.approx(1.1000)
    assert bars[0]["close"] == pytest.approx(1.1015)
    assert bars[0]["high"] == pytest.approx(1.1020)
    assert bars[0]["low"] == pytest.approx(1.0990)
    assert len(bars[0]["minute_tick_volume"]) == 15
    assert bars[0]["tick_volume"] == pytest.approx(sum(volumes))


def test_complete_m15_rejects_gap_duplicate_and_never_fills() -> None:
    start = utc(2020, 1, 6, 8, 0)
    complete = flat_minutes(start)
    gap = [row for row in complete if row["time_utc"] != start + timedelta(minutes=7)]
    bars, quality = sut.build_complete_m15(gap)
    assert bars == []
    assert quality["incomplete_bins"] == 1
    with pytest.raises(sut.ContractError, match="duplicated|unordered"):
        sut.build_complete_m15([complete[0], complete[0]])


def test_signal_domain_07_to_16_only() -> None:
    assert sut.in_signal_domain(utc(2020, 1, 6, 7, 0)) is True
    assert sut.in_signal_domain(utc(2020, 1, 6, 16, 45)) is True
    assert sut.in_signal_domain(utc(2020, 1, 6, 6, 45)) is False
    assert sut.in_signal_domain(utc(2020, 1, 6, 17, 0)) is False
    assert sut.in_signal_domain(utc(2020, 1, 6, 0, 0)) is False
    assert sut.in_signal_domain(utc(2020, 1, 4, 10, 0)) is False  # Saturday
    assert sut.in_signal_domain(utc(2020, 1, 5, 10, 0)) is False  # Sunday


def test_volume_clock_h_and_tau_boundaries() -> None:
    # h=0 => tau = 0.5/15 = 0.0333...
    clock0 = sut.volume_clock_features(
        minute_open=[1.1] * 15,
        minute_close=[1.1] * 15,
        minute_tick_volume=early_mass_volumes(0),
    )
    assert clock0 is not None
    assert clock0["h"] == 0
    assert clock0["tau"] == pytest.approx((0 + 0.5) / 15.0)
    # h=5 => tau = 5.5/15 ≈ 0.3667 <= 0.40
    clock5 = sut.volume_clock_features(
        minute_open=[1.1] * 15,
        minute_close=[1.1] * 15,
        minute_tick_volume=early_mass_volumes(5),
    )
    assert clock5 is not None
    assert clock5["h"] == 5
    assert clock5["tau"] == pytest.approx(5.5 / 15.0)
    assert clock5["tau"] <= 0.40
    # h=6 => tau = 6.5/15 ≈ 0.4333 > 0.40
    clock6 = sut.volume_clock_features(
        minute_open=[1.1] * 15,
        minute_close=[1.1] * 15,
        minute_tick_volume=early_mass_volumes(6),
    )
    assert clock6 is not None
    assert clock6["h"] == 6
    assert clock6["tau"] == pytest.approx(6.5 / 15.0)
    assert clock6["tau"] > 0.40
    # totalTV=0 unavailable
    assert (
        sut.volume_clock_features(
            minute_open=[1.1] * 15,
            minute_close=[1.1] * 15,
            minute_tick_volume=[0.0] * 15,
        )
        is None
    )


def test_p_early_p_late_and_exhaustion_formula() -> None:
    opens = [1.1000] + [1.1005] * 14
    closes = [1.1000] * 15
    # h=2, C_h=1.1010, O_0=1.1000 => P_early=+0.0010
    closes[2] = 1.1010
    closes[14] = 1.1002  # P_late = 1.1002-1.1010 = -0.0008 (opposite sign => exhaustion)
    vols = early_mass_volumes(2)
    clock = sut.volume_clock_features(
        minute_open=opens, minute_close=closes, minute_tick_volume=vols
    )
    assert clock is not None
    assert clock["h"] == 2
    assert clock["p_early"] == pytest.approx(0.0010)
    assert clock["p_late"] == pytest.approx(-0.0008)
    assert sut.exhaustion_holds(p_early=0.0010, p_late=-0.0008) is True
    # same-sign but small late: abs(0.0002) < 0.30*0.0010
    assert sut.exhaustion_holds(p_early=0.0010, p_late=0.0002) is True
    # same-sign large late fails
    assert sut.exhaustion_holds(p_early=0.0010, p_late=0.0005) is False
    # zero early fails
    assert sut.exhaustion_holds(p_early=0.0, p_late=-0.001) is False


def test_atr14_includes_current_closed_bar_and_resets_on_gap() -> None:
    start = utc(2020, 1, 6, 7, 0)
    m1: list[dict[str, object]] = []
    price = 1.1000
    for index in range(20):
        open_p = price
        close_p = price + 0.00030
        bar_start = start + timedelta(minutes=15 * index)
        m1.extend(
            impulse_minutes(
                bar_start,
                open_price=open_p,
                close_price=close_p,
                high=open_p + 0.00040,
                low=open_p - 0.00010,
                volumes=early_mass_volumes(2),
            )
        )
        price = close_p
    gap_start = start + timedelta(minutes=15 * 22)
    m1.extend(
        impulse_minutes(
            gap_start,
            open_price=price,
            close_price=price + 0.00030,
            volumes=early_mass_volumes(2),
        )
    )
    bars, _ = sut.build_complete_m15(m1)
    features = sut.compute_bar_features(bars)
    with_atr = [row for row in features if row["atr14"] is not None]
    assert with_atr
    first_atr_bar = with_atr[0]
    assert first_atr_bar["time_utc"] == start + timedelta(minutes=15 * 14)
    gap_feature = [row for row in features if row["time_utc"] == gap_start][0]
    assert gap_feature["atr14"] is None
    assert gap_feature["contiguous_prev"] is False


def _feature_template(
    *,
    at: datetime,
    atr: float = 0.0010,
    tau: float = 0.20,
    p_early: float = 0.0010,
    p_late: float = -0.0002,
    half_index: int = 2,
) -> dict[str, object]:
    return {
        "time_utc": at,
        "availability_utc": at + timedelta(minutes=15),
        "date": at.date(),
        "slot": 4 * at.hour + at.minute // 15,
        "atr14": atr,
        "tau": tau,
        "p_early": p_early,
        "p_late": p_late,
        "h": half_index,
        "total_tv": 100.0,
        "open": 1.1,
        "high": 1.11,
        "low": 1.09,
        "close": 1.101,
        "contiguous_prev": True,
    }


def test_gates_tau_early_atr_exhaustion_boundaries() -> None:
    at = utc(2020, 1, 6, 10, 0)
    base = _feature_template(at=at, tau=0.40, p_early=0.00045, p_late=-0.0001, atr=0.0010)
    # tau==0.40 inclusive pass, early == 0.45*ATR pass (binary64 product may exceed 0.00045)
    assert abs(0.00045) < 0.45 * 0.0010  # documents the raw binary64 trap
    assert sut.ge_inclusive(0.00045, 0.45 * 0.0010) is True
    assert len(sut.select_raw_signals([base])) == 1
    late_tau = dict(base)
    late_tau["tau"] = 0.4000001
    assert sut.select_raw_signals([late_tau]) == []
    just_above_tau = dict(base)
    just_above_tau["tau"] = 0.40 + 1e-9
    assert sut.select_raw_signals([just_above_tau]) == []
    weak_early = dict(base)
    weak_early["p_early"] = 0.00044  # just below 0.45*0.0010
    assert sut.select_raw_signals([weak_early]) == []
    exact_early = dict(base)
    exact_early["p_early"] = 0.00045
    assert len(sut.select_raw_signals([exact_early])) == 1
    zero_early = dict(base)
    zero_early["p_early"] = 0.0
    assert sut.select_raw_signals([zero_early]) == []
    # Strict exhaustion: exact 0.30 same-sign must fail; just below must pass.
    exact_exhaust = dict(base)
    exact_exhaust["p_late"] = 0.00045 * 0.30
    assert sut.exhaustion_holds(p_early=0.00045, p_late=0.00045 * 0.30) is False
    assert sut.select_raw_signals([exact_exhaust]) == []
    no_exhaust = dict(base)
    no_exhaust["p_late"] = 0.00020  # same sign, abs > 0.30*early
    assert sut.select_raw_signals([no_exhaust]) == []
    shrink = dict(base)
    shrink["p_late"] = 0.00045 * 0.299
    assert sut.exhaustion_holds(p_early=0.00045, p_late=0.00045 * 0.299) is True
    assert len(sut.select_raw_signals([shrink])) == 1


def test_first_eligible_per_day_and_matched_follow_control() -> None:
    day = date(2020, 1, 6)
    features = []
    for hour in (9, 10, 11):
        features.append(_feature_template(at=utc(2020, 1, 6, hour, 0)))
    raw = sut.select_raw_signals(features)
    assert len(raw) == 1
    assert raw[0]["time_utc"].hour == 9
    # TRUE = -sign(P_early); P_early>0 => TRUE SHORT, FOLLOW LONG
    assert raw[0]["true_direction"] == "SHORT"
    assert raw[0]["follow_control_direction"] == "LONG"
    starts = [utc(2020, 1, 6, 9, 15) + timedelta(minutes=15 * i) for i in range(8)]
    ledgers = sut.build_matched_ledgers(raw, starts)
    assert ledgers["eligible_count"] == 1
    assert ledgers["TRUE"][0]["direction"] == "SHORT"
    assert ledgers["FOLLOW_CONTROL"][0]["direction"] == "LONG"
    assert ledgers["TRUE"][0]["decision_utc"] == ledgers["FOLLOW_CONTROL"][0]["decision_utc"]
    assert ledgers["TRUE"][0]["source_signal_id"] == ledgers["FOLLOW_CONTROL"][0]["source_signal_id"]
    assert ledgers["exact_once"]["exact_once_reconciliation"] is True
    assert len(ledgers["classifications"]) == 1
    assert ledgers["classifications"][0]["status"] == "SOURCE_EXECUTABLE"


def test_next_bar_eight_bar_horizon_timestamp_only() -> None:
    entry = utc(2020, 1, 6, 10, 15)
    starts = [entry + timedelta(minutes=15 * i) for i in range(8)]
    horizon = sut.map_horizon(entry, starts)
    assert horizon["source_executable"] is True
    assert horizon["time_exit_utc"] == entry + timedelta(minutes=120)
    assert horizon["observed_horizon_bars"] == 8
    assert horizon["required_horizon_bars"] == 8
    incomplete = sut.map_horizon(entry, starts[:-1])
    assert incomplete["source_executable"] is False
    assert incomplete["reason"] == "HORIZON_INCOMPLETE"
    assert incomplete["observed_horizon_bars"] == 7
    assert incomplete["required_horizon_bars"] == 8


def test_no_post_entry_access_in_horizon_mapping() -> None:
    entry = utc(2020, 1, 6, 10, 15)
    with pytest.raises(sut.ContractError):
        sut.map_horizon(
            entry,
            [{"time_utc": entry, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}],  # type: ignore[list-item]
        )


def test_no_lookahead_features_use_closed_bar_only() -> None:
    # Contiguous chain; permute future bars must not change past ATR/tau for earlier stamps.
    start = utc(2020, 1, 6, 7, 0)
    m1: list[dict[str, object]] = []
    price = 1.1000
    for index in range(30):
        open_p = price
        close_p = price + (0.00040 if index == 20 else 0.00010)
        bar_start = start + timedelta(minutes=15 * index)
        m1.extend(
            impulse_minutes(
                bar_start,
                open_price=open_p,
                close_price=close_p,
                high=max(open_p, close_p) + 0.00020,
                low=min(open_p, close_p) - 0.00020,
                volumes=early_mass_volumes(2 if index != 20 else 3),
            )
        )
        price = close_p
    bars, _ = sut.build_complete_m15(m1)
    features_a = sut.compute_bar_features(bars)
    # reorder input bars; compute sorts internally => invariant
    features_b = sut.compute_bar_features(list(reversed(bars)))
    assert [row["time_utc"] for row in features_a] == [row["time_utc"] for row in features_b]
    assert [row["atr14"] for row in features_a] == [row["atr14"] for row in features_b]
    assert [row["tau"] for row in features_a] == [row["tau"] for row in features_b]
    assert [row["p_early"] for row in features_a] == [row["p_early"] for row in features_b]


def test_cadence_uses_elapsed_calendar_weeks_not_active() -> None:
    assert sut.ELAPSED_CALENDAR_WEEKS == pytest.approx(
        (date(2020, 12, 31) - date(2016, 1, 4)).days / 7.0
    )
    true_rows = []
    follow_rows = []
    weeks = sut.ELAPSED_CALENDAR_WEEKS
    count = int(round(3.0 * weeks))
    for index in range(count):
        year = 2016 + (index % 5)
        direction = "LONG" if index % 2 == 0 else "SHORT"
        true_rows.append(
            {
                "decision_utc": f"{year}-06-01T10:00:00Z",
                "direction": direction,
                "year": year,
                "cost_to_stop_ratio": 0.10,
                "stop_distance_pips": 10.0,
                "source_signal_id": f"SRC-{index:04d}",
            }
        )
        follow_rows.append(
            {
                "decision_utc": f"{year}-06-01T10:00:00Z",
                "direction": "SHORT" if direction == "LONG" else "LONG",
                "year": year,
                "cost_to_stop_ratio": 0.10,
                "stop_distance_pips": 10.0,
                "source_signal_id": f"SRC-{index:04d}",
            }
        )
    n = len(true_rows)
    for index, row in enumerate(true_rows):
        year = 2016 + (index * 5) // max(n, 1)
        if year > 2020:
            year = 2016 + (index % 5)
        direction = "LONG" if index < n // 2 else "SHORT"
        row["year"] = year
        row["direction"] = direction
        follow_rows[index]["year"] = year
        follow_rows[index]["direction"] = "SHORT" if direction == "LONG" else "LONG"
        follow_rows[index]["decision_utc"] = row["decision_utc"] = f"{year}-06-01T10:00:00Z"
    horizons = [{"source_executable": True} for _ in true_rows]
    stage0 = sut.evaluate_stage0_gates(
        true_signals=true_rows,
        follow_signals=follow_rows,
        raw_first_per_day_count=len(true_rows),
        horizon_records=horizons,
        domain_complete=99,
        domain_scheduled=100,
        elapsed_weeks=sut.ELAPSED_CALENDAR_WEEKS,
    )
    cadence = stage0["metrics"]["cadence_per_elapsed_week"]
    assert 2.0 <= cadence <= 5.0
    assert stage0["metrics"]["elapsed_calendar_weeks"] == pytest.approx(sut.ELAPSED_CALENDAR_WEEKS)


def _balanced_population(count: int = 200) -> tuple[list[dict], list[dict], list[dict]]:
    true_rows = []
    follow_rows = []
    years = [2016, 2017, 2018, 2019, 2020]
    for index in range(count):
        year = years[index % 5]
        direction = "LONG" if index % 2 == 0 else "SHORT"
        decision = f"{year}-06-{(index % 28) + 1:02d}T10:00:00Z"
        source_id = f"SRC-{index:04d}"
        true_rows.append(
            {
                "decision_utc": decision,
                "direction": direction,
                "year": year,
                "cost_to_stop_ratio": 0.12,
                "stop_distance_pips": 8.0,
                "source_signal_id": source_id,
            }
        )
        follow_rows.append(
            {
                "decision_utc": decision,
                "direction": "SHORT" if direction == "LONG" else "LONG",
                "year": year,
                "cost_to_stop_ratio": 0.12,
                "stop_distance_pips": 8.0,
                "source_signal_id": source_id,
            }
        )
    horizons = [{"source_executable": True} for _ in true_rows]
    return true_rows, follow_rows, horizons


def test_every_stage0_gate_passes_at_inclusive_boundaries() -> None:
    true_rows, follow_rows, horizons = _balanced_population(260)
    for row in true_rows:
        row["cost_to_stop_ratio"] = 0.25
        row["stop_distance_pips"] = 6.0
    stage0 = sut.evaluate_stage0_gates(
        true_signals=true_rows,
        follow_signals=follow_rows,
        raw_first_per_day_count=len(true_rows),
        horizon_records=horizons,
        domain_complete=99,
        domain_scheduled=100,
        elapsed_weeks=sut.ELAPSED_CALENDAR_WEEKS,
    )
    assert stage0["gates"]["signal_domain_m15_completeness_at_least_0_99"] is True
    assert stage0["gates"]["median_cost_to_stop_ratio_at_most_0_25"] is True
    assert stage0["gates"]["median_stop_distance_pips_at_least_6_0"] is True
    assert stage0["gates"]["max_calendar_year_share_at_most_0_35"] is True
    assert stage0["gates"]["follow_control_matched_true_timestamps"] is True
    assert stage0["verdict"] in {
        "SOURCE_PASS_FUTURE_ECONOMICS_PREREG_ONLY",
        "SOURCE_FAIL_NO_ECONOMICS_AUTHORITY",
    }


def test_exact_six_pip_boundary_is_inclusive() -> None:
    true_rows, follow_rows, horizons = _balanced_population(200)
    for row in true_rows:
        row["stop_distance_pips"] = 6.0
        row["cost_to_stop_ratio"] = 0.20
    stage0 = sut.evaluate_stage0_gates(
        true_signals=true_rows,
        follow_signals=follow_rows,
        raw_first_per_day_count=len(true_rows),
        horizon_records=horizons,
        domain_complete=100,
        domain_scheduled=100,
        elapsed_weeks=50.0,
    )
    assert stage0["gates"]["median_stop_distance_pips_at_least_6_0"] is True
    # MIN_STOP/PIP binary64 trap must still pass the inclusive 6.0 gate.
    min_stop_pips = sut.MIN_STOP_DISTANCE / sut.PIP
    assert min_stop_pips < 6.0  # raw binary64 is just under 6
    assert sut.ge_inclusive(min_stop_pips, 6.0) is True
    for row in true_rows:
        row["stop_distance_pips"] = min_stop_pips
    stage0_min = sut.evaluate_stage0_gates(
        true_signals=true_rows,
        follow_signals=follow_rows,
        raw_first_per_day_count=len(true_rows),
        horizon_records=horizons,
        domain_complete=100,
        domain_scheduled=100,
        elapsed_weeks=50.0,
    )
    assert stage0_min["gates"]["median_stop_distance_pips_at_least_6_0"] is True
    for row in true_rows:
        row["stop_distance_pips"] = 5.999
    stage0_fail = sut.evaluate_stage0_gates(
        true_signals=true_rows,
        follow_signals=follow_rows,
        raw_first_per_day_count=len(true_rows),
        horizon_records=horizons,
        domain_complete=100,
        domain_scheduled=100,
        elapsed_weeks=50.0,
    )
    assert stage0_fail["gates"]["median_stop_distance_pips_at_least_6_0"] is False


def test_stage0_numeric_boundaries_exact_and_just_outside() -> None:
    """Adversarial inclusive Stage-0 edges: exact pass, just-outside fail."""

    true_rows, follow_rows, horizons = _balanced_population(200)
    for row in true_rows:
        row["cost_to_stop_ratio"] = 0.25
        row["stop_distance_pips"] = 6.0
    # Completeness / horizon exact 0.99 pass
    stage0 = sut.evaluate_stage0_gates(
        true_signals=true_rows,
        follow_signals=follow_rows,
        raw_first_per_day_count=len(true_rows),
        horizon_records=horizons,
        domain_complete=99,
        domain_scheduled=100,
        elapsed_weeks=50.0,
    )
    assert stage0["gates"]["signal_domain_m15_completeness_at_least_0_99"] is True
    assert stage0["gates"]["source_executable_horizon_ratio_at_least_0_99"] is True
    assert stage0["gates"]["median_cost_to_stop_ratio_at_most_0_25"] is True
    assert stage0["gates"]["median_stop_distance_pips_at_least_6_0"] is True
    # Completeness just below 0.99 fails
    stage0_dom = sut.evaluate_stage0_gates(
        true_signals=true_rows,
        follow_signals=follow_rows,
        raw_first_per_day_count=len(true_rows),
        horizon_records=horizons,
        domain_complete=98,
        domain_scheduled=100,
        elapsed_weeks=50.0,
    )
    assert stage0_dom["gates"]["signal_domain_m15_completeness_at_least_0_99"] is False
    # Horizon just below 0.99 fails
    raw_count = len(true_rows)
    horizons_low = [
        {"source_executable": index < int(0.98 * raw_count)} for index in range(raw_count)
    ]
    stage0_hz = sut.evaluate_stage0_gates(
        true_signals=true_rows,
        follow_signals=follow_rows,
        raw_first_per_day_count=raw_count,
        horizon_records=horizons_low,
        domain_complete=100,
        domain_scheduled=100,
        elapsed_weeks=50.0,
    )
    assert stage0_hz["gates"]["source_executable_horizon_ratio_at_least_0_99"] is False
    # Cadence exact 2.0 and 5.0 inclusive; just outside fails
    n2 = 100
    rows2, follow2, hz2 = _balanced_population(n2)
    for row in rows2:
        row["cost_to_stop_ratio"] = 0.20
        row["stop_distance_pips"] = 8.0
    for row in follow2:
        row["cost_to_stop_ratio"] = 0.20
        row["stop_distance_pips"] = 8.0
    stage_cad_lo = sut.evaluate_stage0_gates(
        true_signals=rows2,
        follow_signals=follow2,
        raw_first_per_day_count=n2,
        horizon_records=hz2,
        domain_complete=100,
        domain_scheduled=100,
        elapsed_weeks=50.0,  # cadence = 2.0
    )
    assert stage_cad_lo["metrics"]["cadence_per_elapsed_week"] == pytest.approx(2.0)
    assert stage_cad_lo["gates"]["eligible_cadence_2_to_5_per_elapsed_week"] is True
    stage_cad_hi = sut.evaluate_stage0_gates(
        true_signals=rows2,
        follow_signals=follow2,
        raw_first_per_day_count=n2,
        horizon_records=hz2,
        domain_complete=100,
        domain_scheduled=100,
        elapsed_weeks=20.0,  # cadence = 5.0
    )
    assert stage_cad_hi["metrics"]["cadence_per_elapsed_week"] == pytest.approx(5.0)
    assert stage_cad_hi["gates"]["eligible_cadence_2_to_5_per_elapsed_week"] is True
    stage_cad_out = sut.evaluate_stage0_gates(
        true_signals=rows2,
        follow_signals=follow2,
        raw_first_per_day_count=n2,
        horizon_records=hz2,
        domain_complete=100,
        domain_scheduled=100,
        elapsed_weeks=19.0,  # cadence > 5
    )
    assert stage_cad_out["gates"]["eligible_cadence_2_to_5_per_elapsed_week"] is False
    # Share exact 0.25 pass; just below fails. Year share exact 0.35 pass; just above fails.
    share_rows, share_follow, share_hz = _balanced_population(200)
    for index, row in enumerate(share_rows):
        row["direction"] = "LONG" if index < 50 else "SHORT"
        share_follow[index]["direction"] = "SHORT" if row["direction"] == "LONG" else "LONG"
        row["cost_to_stop_ratio"] = 0.20
        row["stop_distance_pips"] = 8.0
    stage_share = sut.evaluate_stage0_gates(
        true_signals=share_rows,
        follow_signals=share_follow,
        raw_first_per_day_count=200,
        horizon_records=share_hz,
        domain_complete=100,
        domain_scheduled=100,
        elapsed_weeks=50.0,
    )
    assert stage_share["metrics"]["long_share"] == pytest.approx(0.25)
    assert stage_share["gates"]["true_long_share_at_least_0_25"] is True
    for index, row in enumerate(share_rows):
        row["direction"] = "LONG" if index < 49 else "SHORT"
        share_follow[index]["direction"] = "SHORT" if row["direction"] == "LONG" else "LONG"
    stage_share_fail = sut.evaluate_stage0_gates(
        true_signals=share_rows,
        follow_signals=share_follow,
        raw_first_per_day_count=200,
        horizon_records=share_hz,
        domain_complete=100,
        domain_scheduled=100,
        elapsed_weeks=50.0,
    )
    assert stage_share_fail["gates"]["true_long_share_at_least_0_25"] is False
    year_rows, year_follow, year_hz = _balanced_population(200)
    # 70/200 = 0.35 exact for one year
    years = [2016] * 70 + [2017] * 50 + [2018] * 40 + [2019] * 20 + [2020] * 20
    for index, row in enumerate(year_rows):
        row["year"] = years[index]
        year_follow[index]["year"] = years[index]
        row["cost_to_stop_ratio"] = 0.20
        row["stop_distance_pips"] = 8.0
    stage_year = sut.evaluate_stage0_gates(
        true_signals=year_rows,
        follow_signals=year_follow,
        raw_first_per_day_count=200,
        horizon_records=year_hz,
        domain_complete=100,
        domain_scheduled=100,
        elapsed_weeks=50.0,
    )
    assert stage_year["metrics"]["max_year_share"] == pytest.approx(0.35)
    assert stage_year["gates"]["max_calendar_year_share_at_most_0_35"] is True
    years_hi = [2016] * 71 + [2017] * 49 + [2018] * 40 + [2019] * 20 + [2020] * 20
    for index, row in enumerate(year_rows):
        row["year"] = years_hi[index]
        year_follow[index]["year"] = years_hi[index]
    stage_year_fail = sut.evaluate_stage0_gates(
        true_signals=year_rows,
        follow_signals=year_follow,
        raw_first_per_day_count=200,
        horizon_records=year_hz,
        domain_complete=100,
        domain_scheduled=100,
        elapsed_weeks=50.0,
    )
    assert stage_year_fail["gates"]["max_calendar_year_share_at_most_0_35"] is False
    # Cost exact 0.25 pass; just above fails
    cost_rows, cost_follow, cost_hz = _balanced_population(200)
    for row in cost_rows:
        row["cost_to_stop_ratio"] = 0.25
        row["stop_distance_pips"] = 8.0
    stage_cost = sut.evaluate_stage0_gates(
        true_signals=cost_rows,
        follow_signals=cost_follow,
        raw_first_per_day_count=200,
        horizon_records=cost_hz,
        domain_complete=100,
        domain_scheduled=100,
        elapsed_weeks=50.0,
    )
    assert stage_cost["gates"]["median_cost_to_stop_ratio_at_most_0_25"] is True
    for row in cost_rows:
        row["cost_to_stop_ratio"] = 0.250001
    stage_cost_fail = sut.evaluate_stage0_gates(
        true_signals=cost_rows,
        follow_signals=cost_follow,
        raw_first_per_day_count=200,
        horizon_records=cost_hz,
        domain_complete=100,
        domain_scheduled=100,
        elapsed_weeks=50.0,
    )
    assert stage_cost_fail["gates"]["median_cost_to_stop_ratio_at_most_0_25"] is False
    # Comparison helper unit contract (finite-only ULP scale)
    assert sut.le_inclusive(0.40, 0.40) is True
    assert sut.gt_strict(0.40 + 1e-9, 0.40) is True
    assert sut.lt_strict(0.30 * 0.001, 0.30 * 0.001) is False
    assert sut.lt_strict(0.299 * 0.001, 0.30 * 0.001) is True
    # Substantively just-below 0.30 must pass strict; equality / just-above fail.
    assert sut.lt_strict(0.299999999999, 0.30) is True
    assert sut.lt_strict(0.30, 0.30) is False
    assert sut.lt_strict(0.300000000001, 0.30) is False
    assert sut.exhaustion_holds(p_early=1.0, p_late=0.299999999999) is True
    assert sut.exhaustion_holds(p_early=1.0, p_late=0.30) is False
    assert sut.exhaustion_holds(p_early=1.0, p_late=0.300000000001) is False


@pytest.mark.parametrize(
    "mutation,failed_gate",
    [
        ("domain", "signal_domain_m15_completeness_at_least_0_99"),
        ("horizon", "source_executable_horizon_ratio_at_least_0_99"),
        ("cadence_low", "eligible_cadence_2_to_5_per_elapsed_week"),
        ("long_share", "true_long_share_at_least_0_25"),
        ("year", "max_calendar_year_share_at_most_0_35"),
        ("sides", "at_least_20_eligible_per_side"),
        ("cost", "median_cost_to_stop_ratio_at_most_0_25"),
        ("stop", "median_stop_distance_pips_at_least_6_0"),
    ],
)
def test_each_gate_can_fail_independently(mutation: str, failed_gate: str) -> None:
    true_rows, follow_rows, horizons = _balanced_population(300)
    domain_complete, domain_scheduled = 100, 100
    raw_count = len(true_rows)
    elapsed = sut.ELAPSED_CALENDAR_WEEKS
    if mutation == "domain":
        domain_complete, domain_scheduled = 98, 100
    elif mutation == "horizon":
        horizons = [{"source_executable": i < int(0.98 * raw_count)} for i in range(raw_count)]
    elif mutation == "cadence_low":
        true_rows = true_rows[:10]
        follow_rows = follow_rows[:10]
        horizons = horizons[:10]
        raw_count = 10
    elif mutation == "long_share":
        for row in true_rows:
            row["direction"] = "SHORT"
        for row in follow_rows:
            row["direction"] = "LONG"
    elif mutation == "year":
        for row in true_rows:
            row["year"] = 2016
        for row in follow_rows:
            row["year"] = 2016
    elif mutation == "sides":
        true_rows = true_rows[:30]
        follow_rows = follow_rows[:30]
        for index, row in enumerate(true_rows):
            row["direction"] = "LONG" if index < 25 else "SHORT"
            follow_rows[index]["direction"] = "SHORT" if row["direction"] == "LONG" else "LONG"
            follow_rows[index]["decision_utc"] = row["decision_utc"]
            follow_rows[index]["source_signal_id"] = row["source_signal_id"]
        horizons = horizons[:30]
        raw_count = 30
    elif mutation == "cost":
        for row in true_rows:
            row["cost_to_stop_ratio"] = 0.40
    elif mutation == "stop":
        for row in true_rows:
            row["stop_distance_pips"] = 5.0
    stage0 = sut.evaluate_stage0_gates(
        true_signals=true_rows,
        follow_signals=follow_rows,
        raw_first_per_day_count=raw_count,
        horizon_records=horizons,
        domain_complete=domain_complete,
        domain_scheduled=domain_scheduled,
        elapsed_weeks=elapsed,
    )
    assert stage0["gates"][failed_gate] is False
    assert stage0["verdict"] == "SOURCE_FAIL_NO_ECONOMICS_AUTHORITY"


def _synthetic_vcex_m1(days: tuple[date, ...], *, seed: int = 42) -> list[dict[str, object]]:
    m1: list[dict[str, object]] = []
    price = 1.1000
    rng = random.Random(seed)
    for day_index, day in enumerate(days):
        # Prehistory 05:00-06:45 UTC so ATR14 (14 contiguous TRs) is available by
        # the 10:00 domain shock. Overnight gap still resets ATR; signal domain
        # remains 07-16 only in production selectors.
        for hour in range(5, 17):
            for minute in (0, 15, 30, 45):
                start = utc(day.year, day.month, day.day, hour, minute)
                if day_index >= 16 and hour == 10 and minute == 0:
                    shock = 0.0020 if day_index % 2 == 0 else -0.0020
                    vols = early_mass_volumes(2)
                    late_hold = price + shock * 0.2
                    open_p = price
                    # Build minutes with early impulse then exhaustion
                    rows = []
                    for index in range(15):
                        at = start + timedelta(minutes=index)
                        if index <= 2:
                            frac = index / 2.0 if index > 0 else 0.0
                            c = open_p + shock * frac
                            o = open_p if index == 0 else c
                        else:
                            # fade toward late_hold
                            c = late_hold
                            o = late_hold
                        hi = max(o, c) + 0.00020
                        lo = min(o, c) - 0.00020
                        rows.append(
                            m1_row(at, open_=o, high=hi, low=lo, close=c, tick_volume=vols[index])
                        )
                    m1.extend(rows)
                    price = late_hold
                else:
                    shock = rng.uniform(-0.00005, 0.00005)
                    open_p = price
                    close_p = max(0.5, price + shock)
                    hi = max(open_p, close_p) + 0.00020
                    lo = min(open_p, close_p) - 0.00020
                    m1.extend(
                        impulse_minutes(
                            start,
                            open_price=open_p,
                            close_price=close_p,
                            high=hi,
                            low=lo,
                            volumes=early_mass_volumes(4),
                        )
                    )
                    price = close_p
    return m1


def test_scan_source_end_to_end_synthetic_outcome_blind() -> None:
    days = business_days(date(2020, 1, 6), 40)
    m1 = _synthetic_vcex_m1(days)
    report = sut.scan_source(m1, days)
    assert report["hypothesis_id"] == sut.HYPOTHESIS_ID
    assert report["economics_authorized"] is False
    assert report["post_entry_ohlc_rows_read"] == 0
    assert report["arm_counts"]["TRUE"] == report["arm_counts"]["FOLLOW_CONTROL"]
    assert report["exact_once_reconciliation"] is True
    assert report["canonical_digest_sha256"] == report["replay_canonical_digest_sha256"]
    assert "WALL_CLOCK_H7" in report["source_contract"]["rejected_trials"]
    sut.assert_outcome_blind(report)


def test_outcome_fields_and_wall_clock_h7_rejected() -> None:
    with pytest.raises(sut.ContractError, match="forbidden"):
        sut.assert_outcome_blind({"pnl": 1})
    with pytest.raises(sut.ContractError, match="forbidden"):
        sut.assert_outcome_blind({"post_entry_high": 1.0})
    with pytest.raises(sut.ContractError, match="forbidden"):
        sut.assert_outcome_blind({"wall_clock_h7_arm": True})
    with pytest.raises(sut.ContractError, match="forbidden"):
        sut.assert_outcome_blind({"entry_price": 1.1})
    with pytest.raises(sut.ContractError, match="forbidden"):
        sut.assert_outcome_blind({"arm": "WALL_CLOCK_H7"})
    with pytest.raises(sut.ContractError, match="forbidden"):
        sut.assert_outcome_blind({"arm": "FADE"})


def test_forbidden_path_parts_rejected(tmp_path: Path) -> None:
    workspace = tmp_path
    (workspace / "private").mkdir()
    target = workspace / "private" / "x.json"
    target.write_bytes(b"{}\n")
    with pytest.raises(sut.ContractError):
        sut.stable_read_regular(target, workspace)
    (workspace / "public").mkdir()
    ok = workspace / "public" / "ok.json"
    ok.write_bytes(b"abc")
    assert sut.stable_read_regular(ok, workspace) == b"abc"


def public_manifest_receipt_ok() -> tuple[bytes, bytes]:
    row = {
        "bytes": 10,
        "date": "2016-01-04",
        "relative_path": "public/DESIGN/2016-01-04/m1.parquet",
        "rows": 1,
        "sha256": "A" * 64,
    }
    manifest = canonical(row) + b"\n"
    receipt = {
        "collection_plan_sha256": "B" * 64,
        "custodian_full_corpus_decoded": True,
        "custodian_tool_sha256": "C" * 64,
        "design_dates": 1,
        "design_manifest_sha256": sha(manifest),
        "design_rows": 1,
        "exact_once_status": "PASS",
        "private_custody_digest": "D" * 64,
        "private_custody_receipt_sha256": "E" * 64,
        "research_holdout_opened": False,
        "research_validation_opened": False,
        "source_bytes": 1,
        "source_footer_length": 1,
        "source_footer_start": 1,
        "source_footer_sha256": "F" * 64,
        "source_sha256": sut.M1_SOURCE_SHA256,
        "source_attempt_id": "X",
        "stage_path": "stage",
        "stage_role": "CUSTODY",
        "supervisor_review_base_sha256": "1" * 64,
        "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
    }
    return canonical(receipt) + b"\n", manifest


def test_public_metadata_hash_mismatch_fails() -> None:
    receipt, manifest = public_manifest_receipt_ok()
    with pytest.raises(sut.ContractError, match="public metadata hash"):
        sut.validate_public_metadata(
            receipt_payload=receipt,
            manifest_payload=manifest,
            expected_receipt_sha256="0" * 64,
            expected_manifest_sha256=sha(manifest),
        )


def test_decode_allowlist_includes_tick_volume_only() -> None:
    assert "time_server" not in sut.ALLOWED_DECODE_COLUMNS
    assert "spread" not in sut.ALLOWED_DECODE_COLUMNS
    assert "real_volume" not in sut.ALLOWED_DECODE_COLUMNS
    assert sut.ALLOWED_DECODE_COLUMNS == (
        "time_utc",
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
    )


def registry_fixture(
    *,
    builder_payload: bytes | None = None,
    test_payload: bytes | None = None,
    receipt_sha: str | None = None,
) -> tuple[bytes, str, bytes, bytes]:
    builder = builder_payload if builder_payload is not None else SOURCE.read_bytes()
    tests = test_payload if test_payload is not None else Path(__file__).read_bytes()
    base_sha = sut.reviewed_base_source_sha256(builder)
    test_sha = sha(tests)
    receipt_hash = receipt_sha if receipt_sha is not None else "A" * 64
    validation = {
        "source_feasibility_only": True,
        "source_run_authorized": True,
        **{field: False for field in sut.SEALED_FALSE_FIELDS},
        "source_feasibility_attempt_limit": 1,
        "source_feasibility_attempt_id": sut.ATTEMPT_ID,
        "source_feasibility_evidence_root": sut.EVIDENCE_ROOT_REL,
        "probe_status": sut.PROBE_STATUS,
        "independent_implementation_review_status": "PASS",
        "independent_pre_run_review_status": "PASS",
        "independent_quant_prereg_review_status": "PASS",
        "reviewed_builder_path": sut.BUILDER_REL,
        "reviewed_builder_base_sha256": base_sha,
        "reviewed_test_path": sut.TEST_REL,
        "reviewed_test_sha256": test_sha,
        "independent_review_receipt_path": sut.REVIEW_RECEIPT_REL,
        "independent_review_receipt_schema": sut.REVIEW_RECEIPT_SCHEMA,
        "independent_review_receipt_sha256": receipt_hash,
        "design_m1_manifest_path": sut.M1_MANIFEST_REL,
        "design_m1_manifest_sha256": sut.M1_MANIFEST_SHA256,
        "design_m1_receipt_path": sut.M1_RECEIPT_REL,
        "design_m1_receipt_sha256": sut.M1_RECEIPT_SHA256,
        "design_m1_source_sha256": sut.M1_SOURCE_SHA256,
        "registry_validator_path": sut.REGISTRY_VALIDATOR_REL,
        "registry_validator_sha256": sut.REGISTRY_VALIDATOR_SHA256,
        "registry_schema_path": sut.REGISTRY_SCHEMA_REL,
        "registry_schema_sha256": sut.REGISTRY_SCHEMA_SHA256,
    }
    row = {
        "record_type": "hypothesis_state",
        "schema_version": "alphafactory_candidate_registry.v1",
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "ea_name": sut.EA_NAME,
        "state": "probe",
        "parent_candidate": None,
        "feature_family": sut.FAMILY,
        "lane": "source-feasibility",
        "symbol": "EURUSD",
        "timeframe": "M15",
        "window": {"from": "2016.01.04", "to": "2020.12.31"},
        "model": None,
        "source_provenance": "fivepercent_splitvault_002_public_design",
        "source_path": None,
        "source_hash": None,
        "prereg_path": sut.PLAN_REL,
        "prereg_sha256": sut.PLAN_SHA256,
        "exact_overrides": "",
        "acceptance_contract": {
            "min_profit_factor": 1.3,
            "min_trades_per_week": 2.0,
            "max_trades_per_week": 5.0,
            "max_drawdown_pct": 8.0,
            "min_cost_pf_x1_5": 1.25,
            "min_cost_pf_x2": 1.0,
            "max_monte_carlo_p95_dd_pct": 8.0,
        },
        "verdict": "AUTHORIZED_SOURCE_FEASIBILITY_ONLY",
        "reason": "frozen VCEX stage-0 package",
        "updated_at_utc": "2026-07-29T00:00:00Z",
        "run_ids": [],
        "metrics": dict(sut.SOURCE_ONLY_ZERO_METRICS),
        "validation": validation,
    }
    raw = canonical(row) + b"\n"
    return raw, sha(raw), builder, tests


def test_registry_exact_validation_whitelist_is_accepted() -> None:
    payload, row_sha, builder, tests = registry_fixture()
    row = sut.validate_registry_authority(
        payload, row_sha, builder_payload=builder, test_payload=tests
    )
    assert row["hypothesis_id"] == sut.HYPOTHESIS_ID
    assert row["validation"]["source_run_authorized"] is True
    assert row["validation"]["economics_authorized"] is False


@pytest.mark.parametrize("field", sorted(sut.SEALED_FALSE_FIELDS)[:5])
def test_registry_false_authorities_reject_true(field: str) -> None:
    payload, row_sha, builder, tests = registry_fixture()
    row = json.loads(payload.decode("utf-8"))
    row["validation"][field] = True
    bad = canonical(row) + b"\n"
    with pytest.raises(sut.ContractError):
        sut.validate_registry_authority(bad, sha(bad), builder_payload=builder, test_payload=tests)


def test_registry_rejects_nonzero_pre_run_metrics() -> None:
    payload, _, builder, tests = registry_fixture()
    row = json.loads(payload.decode("utf-8"))
    row["metrics"]["trades_simulated"] = 1
    bad = canonical(row) + b"\n"
    with pytest.raises(sut.ContractError):
        sut.validate_registry_authority(bad, sha(bad), builder_payload=builder, test_payload=tests)


def test_wrong_registry_row_sha_cannot_arm() -> None:
    payload, row_sha, builder, tests = registry_fixture()
    with pytest.raises(sut.ContractError):
        sut.validate_registry_authority(payload, "0" * 64, builder_payload=builder, test_payload=tests)


def test_latest_row_required_not_older_duplicate() -> None:
    payload, row_sha, builder, tests = registry_fixture()
    row = json.loads(payload.decode("utf-8"))
    older = dict(row)
    older["updated_at_utc"] = "2026-07-28T00:00:00Z"
    newer = dict(row)
    newer["updated_at_utc"] = "2026-07-29T12:00:00Z"
    newer_raw = canonical(newer) + b"\n"
    older_raw = canonical(older) + b"\n"
    stacked = older_raw + newer_raw
    # arming with older SHA must fail even if older SHA exists
    with pytest.raises(sut.ContractError):
        sut.validate_registry_authority(
            stacked, sha(older_raw), builder_payload=builder, test_payload=tests
        )
    ok = sut.validate_registry_authority(
        stacked, sha(newer_raw), builder_payload=builder, test_payload=tests
    )
    assert ok["updated_at_utc"] == "2026-07-29T12:00:00Z"


def test_review_receipt_binding() -> None:
    builder = SOURCE.read_bytes()
    tests = Path(__file__).read_bytes()
    receipt = {
        "schema_version": sut.REVIEW_RECEIPT_SCHEMA,
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "review_status": "PASS",
        "reviewed_builder": {
            "path": sut.BUILDER_REL,
            "base_sha256": sut.reviewed_base_source_sha256(builder),
        },
        "reviewed_tests": {"path": sut.TEST_REL, "sha256": sha(tests)},
        "v1_plan": {"path": sut.PLAN_REL, "sha256": sut.PLAN_SHA256},
        "permissions": {
            "source_feasibility_run": True,
            "performance_or_economics": False,
            "mt5_or_mql5": False,
        },
    }
    payload = canonical(receipt) + b"\n"
    assert sut.validate_review_receipt(
        payload,
        expected_sha256=sha(payload),
        builder_payload=builder,
        test_payload=tests,
    ) == receipt


def test_sentinel_is_exactly_disarmed_and_import_inert() -> None:
    assert sut.REVIEWED_REGISTRY_ROW_SHA256 is None
    text = SOURCE.read_text(encoding="utf-8")
    assert "REVIEWED_REGISTRY_ROW_SHA256: str | None = None" in text
    assert "WALL_CLOCK_H7" in text
    assert "FOLLOW_CONTROL" in text


def test_cli_dual_gate_disarmed(tmp_path: Path) -> None:
    with pytest.raises(sut.ContractError, match="disarmed"):
        sut.execute_probe(workspace_root=tmp_path, run_switch=False)
    with pytest.raises(sut.ContractError, match="disarmed"):
        sut.execute_probe(workspace_root=tmp_path, run_switch=True)


def test_plan_hash_binding_matches_exact_bytes() -> None:
    assert sha(PLAN.read_bytes()) == sut.PLAN_SHA256
    text = PLAN.read_text(encoding="utf-8")
    assert "tau0.40/early0.45ATR/exhaustion0.30/07-16UTC/max1day/8bar/1R" in text
    assert "FOLLOW_CONTROL" in text
    assert "wall-clock" in text.lower()


def test_create_new_evidence_reservation_and_hash_chain(tmp_path: Path) -> None:
    workspace = tmp_path
    builder_rel = Path(sut.BUILDER_REL)
    test_rel = Path(sut.TEST_REL)
    plan_rel = Path(sut.PLAN_REL)
    for relative, payload in (
        (builder_rel, SOURCE.read_bytes()),
        (test_rel, Path(__file__).read_bytes()),
        (plan_rel, PLAN.read_bytes()),
    ):
        path = workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    row_sha = "B" * 64
    root = sut._reserve_attempt(workspace, row_sha)
    started = json.loads((root / "attempt_started.json").read_text(encoding="utf-8"))
    assert started["attempt_id"] == sut.ATTEMPT_ID
    assert started["status"] == "STARTED"
    with pytest.raises(sut.ContractError, match="already exists"):
        sut._reserve_attempt(workspace, row_sha)
    sut._persist_engineering_failure(root, row_sha, RuntimeError("boom"))
    terminal = json.loads((root / "attempt_terminal.json").read_text(encoding="utf-8"))
    assert terminal["status"] == "ENGINEERING_INVALID_NO_MARKET_VERDICT"
    assert "attempt_started.json" in terminal["artifact_hashes"]


def test_persist_success_writes_report_ledger_receipt(tmp_path: Path) -> None:
    workspace = tmp_path
    root = workspace / "evidence"
    root.mkdir()
    row_sha = "C" * 64
    sut._write_new_canonical(
        root / "attempt_started.json",
        {
            "schema_version": "vcex_001_attempt_started.v1",
            "hypothesis_id": sut.HYPOTHESIS_ID,
            "attempt_id": sut.ATTEMPT_ID,
            "reviewed_registry_row_sha256": row_sha,
            "status": "STARTED",
            "source_only_counters": sut._executed_source_only_counters(),
            "sealed_permissions": sut._sealed_permissions(),
        },
    )
    true_rows, follow_rows, horizons = _balanced_population(100)
    classifications = []
    for index, row in enumerate(true_rows):
        source_id = f"VCEX001-SRC-{index:016d}"
        classifications.append(
            {
                "source_signal_id": source_id,
                "decision_utc": row["decision_utc"],
                "entry_open_utc": row["decision_utc"],
                "status": "SOURCE_EXECUTABLE",
                "observed_horizon_bars": 8,
                "required_horizon_bars": 8,
            }
        )
        row["source_signal_id"] = source_id
        follow_rows[index]["source_signal_id"] = source_id
    report = {
        "schema_version": "vcex_001_source_feasibility_report.v1",
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "signal_ledgers": {"TRUE": true_rows, "FOLLOW_CONTROL": follow_rows},
        "raw_signal_classifications": classifications,
        "stage0": {
            "verdict": "SOURCE_FAIL_NO_ECONOMICS_AUTHORITY",
            "gates": {},
            "metrics": {},
        },
        "economics_authorized": False,
        "post_entry_ohlc_rows_read": 0,
        "outcome_fields_emitted": 0,
        "returns_computed": 0,
        "trades_simulated": 0,
        "performance_trials_executed": 0,
    }
    for arm, rows in (("TRUE", true_rows), ("FOLLOW_CONTROL", follow_rows)):
        for index, row in enumerate(rows):
            row["candidate_id"] = f"{arm}-{index}"
            row["arm"] = arm
            row["entry_open_utc"] = row["decision_utc"]
            row["time_exit_utc"] = row["decision_utc"]
            row["h"] = 2
            row["tau"] = 0.2
            row["p_early"] = 0.001
            row["p_late"] = -0.0002
            row["atr14_pips"] = 10.0
            row["slot"] = 40
    enriched = sut._persist_success(root, report, row_sha)
    assert (root / "vcex_001_source_report.json").exists()
    assert (root / "vcex_001_source_classifications.jsonl").exists()
    assert (root / "vcex_001_source_ledger.jsonl").exists()
    assert (root / "source_feasibility_receipt.json").exists()
    assert (root / "attempt_terminal.json").exists()
    assert enriched["stage0"]["verdict"] == "SOURCE_FAIL_NO_ECONOMICS_AUTHORITY"
    receipt = json.loads((root / "source_feasibility_receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == sut.RECEIPT_NON_TERMINAL_STATUS
    assert receipt["terminal_is_sole_authoritative_completion"] is True
    assert "terminal_status" not in receipt
    assert sut.TERMINAL_PASS_STATUS not in json.dumps(receipt)
    terminal = json.loads((root / "attempt_terminal.json").read_text(encoding="utf-8"))
    assert terminal["status"] == sut.TERMINAL_FAIL_STATUS
    assert "source_feasibility_receipt.json" in terminal["artifact_hashes"]
    assert "vcex_001_source_classifications.jsonl" in terminal["artifact_hashes"]


def test_immutable_hashes_are_bound() -> None:
    assert sut.M1_MANIFEST_SHA256 == "A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7"
    assert sut.M1_RECEIPT_SHA256 == "8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8"
    assert sut.M1_SOURCE_SHA256 == "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
    assert sut.REGISTRY_VALIDATOR_SHA256 == "B04B379E11F556A0CF3E6C3264768176310FF01CF360CC3B92464C51A2996DD0"
    assert sut.REGISTRY_SCHEMA_SHA256 == "96C80D3C46A105A9754CA1325F3DD6C160D92A9D5800ECBC402DE0F40C612F5C"
    assert sut.EXPECTED_MANIFEST_DATES == 1555
    assert sut.EXPECTED_M1_DESIGN_ROWS == 1859820
    assert sut.HORIZON_BARS == 8
    assert sut.SIGNAL_HOUR_START == 7
    assert sut.SIGNAL_HOUR_END == 16
    assert sut.TAU_MAX == 0.40
    assert sut.EARLY_ATR_MULT == 0.45
    assert sut.EXHAUSTION_LATE_MULT == 0.30


def test_domain_schedule_counts_weekdays_hours_07_16_only() -> None:
    days = business_days(date(2020, 1, 6), 2)
    assert sut.signal_domain_scheduled_bins(days) == 2 * 10 * 4
    with pytest.raises(sut.ContractError):
        sut.signal_domain_scheduled_bins([date(2020, 1, 4)])


def test_parse_args_execute_probe_flag() -> None:
    args = sut.parse_args(["--execute-probe", "--workspace-root", "."])
    assert args.execute_probe is True


def test_exact_once_classification_and_arm_mapping() -> None:
    days = business_days(date(2020, 3, 2), 30)
    m1 = _synthetic_vcex_m1(days, seed=7)
    cut = utc(days[-1].year, days[-1].month, days[-1].day, 11, 0)
    m1 = [row for row in m1 if row["time_utc"] < cut]
    bars, _ = sut.build_complete_m15(m1)
    features = sut.compute_bar_features(bars)
    raw = sut.select_raw_signals(features)
    assert raw, "synthetic fixture must produce at least one raw signal"
    starts = [row["time_utc"] for row in bars]
    ledgers = sut.build_matched_ledgers(raw, starts)
    classifications = ledgers["classifications"]
    exact = ledgers["exact_once"]
    assert exact["raw_first_per_day_count"] == len(raw)
    assert exact["classification_count"] == len(classifications)
    assert exact["raw_equals_classifications"] is True
    assert exact["classifications_equal_executable_plus_excluded"] is True
    assert exact["exact_once_reconciliation"] is True
    assert (
        exact["raw_first_per_day_count"]
        == exact["classification_count"]
        == exact["executable_count"] + exact["excluded_count"]
    )
    decision_dates = [row["decision_utc"][:10] for row in classifications]
    assert len(decision_dates) == len(set(decision_dates))
    for row, signal in zip(classifications, sorted(raw, key=lambda item: item["time_utc"])):
        expected = sut.assign_source_signal_id(signal["time_utc"])
        assert row["source_signal_id"] == expected
        assert row["decision_utc"] == sut._iso_z(signal["time_utc"])
        assert row["entry_open_utc"] == sut._iso_z(signal["availability_utc"])
        assert row["status"] in {"SOURCE_EXECUTABLE", "HORIZON_INCOMPLETE"}
        assert row["required_horizon_bars"] == 8
        assert 0 <= int(row["observed_horizon_bars"]) <= 8
        assert "high" not in row and "low" not in row and "close" not in row
    executable_ids = {
        row["source_signal_id"] for row in classifications if row["status"] == "SOURCE_EXECUTABLE"
    }
    excluded_ids = {
        row["source_signal_id"] for row in classifications if row["status"] == "HORIZON_INCOMPLETE"
    }
    true_ids = {row["source_signal_id"] for row in ledgers["TRUE"]}
    follow_ids = {row["source_signal_id"] for row in ledgers["FOLLOW_CONTROL"]}
    assert true_ids == follow_ids == executable_ids
    assert excluded_ids.isdisjoint(true_ids)
    assert len(ledgers["TRUE"]) == len(executable_ids)
    assert len(ledgers["FOLLOW_CONTROL"]) == len(executable_ids)
    candidate_ids = [row["candidate_id"] for row in ledgers["TRUE"] + ledgers["FOLLOW_CONTROL"]]
    assert len(candidate_ids) == len(set(candidate_ids))
    projected = sut._arm_identity_projection(ledgers["TRUE"], ledgers["FOLLOW_CONTROL"])
    assert exact["classification_digest_sha256"] == sut.classification_canonical_digest(
        classifications, projected
    )
    if len(classifications) >= 2:
        reordered = list(classifications)
        reordered[0], reordered[1] = reordered[1], reordered[0]
        assert sut.classification_canonical_digest(reordered, projected) != exact[
            "classification_digest_sha256"
        ]


def test_independent_replay_digest_equality_and_mutation_rejection() -> None:
    days = business_days(date(2020, 1, 6), 35)
    m1 = _synthetic_vcex_m1(days, seed=99)
    primary = sut.scan_source_once(m1, days)
    replay_meta = sut.independent_replay_scan(m1, days, primary)
    assert replay_meta["primary_canonical_digest_sha256"] == replay_meta[
        "replay_canonical_digest_sha256"
    ]
    assert replay_meta["exact_once_reconciliation"] is True
    assert replay_meta["digests_equal"] is True
    wrapped = sut.scan_source(m1, days, with_independent_replay=True)
    assert wrapped["canonical_digest_sha256"] == wrapped["replay_canonical_digest_sha256"]
    assert wrapped["exact_once_reconciliation"] is True
    for mode in ("omit_classification", "reorder_classification", "mutate_ledger"):
        if mode in {"omit_classification", "reorder_classification"}:
            if len(primary.get("raw_signal_classifications") or []) < 2:
                continue
        if mode == "mutate_ledger" and not (primary.get("signal_ledgers") or {}).get("TRUE"):
            continue
        sut.assert_independent_replay_rejects_mutation(m1, days, mode=mode)
    one_pass = sut.scan_source_once(m1, days)
    assert "independent_replay" not in one_pass
    assert "canonical_digest_sha256" not in one_pass


def test_terminal_is_sole_pass_authority_and_failed_terminal_write(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    root.mkdir()
    row_sha = "D" * 64
    sut._write_new_canonical(
        root / "attempt_started.json",
        {
            "schema_version": "vcex_001_attempt_started.v1",
            "hypothesis_id": sut.HYPOTHESIS_ID,
            "attempt_id": sut.ATTEMPT_ID,
            "reviewed_registry_row_sha256": row_sha,
            "status": "STARTED",
            "source_only_counters": sut._executed_source_only_counters(),
            "sealed_permissions": sut._sealed_permissions(),
        },
    )
    true_rows, follow_rows, _ = _balanced_population(40)
    classifications = []
    for index, row in enumerate(true_rows):
        source_id = f"VCEX001-SRC-{index:016d}"
        classifications.append(
            {
                "source_signal_id": source_id,
                "decision_utc": row["decision_utc"],
                "entry_open_utc": row["decision_utc"],
                "status": "SOURCE_EXECUTABLE",
                "observed_horizon_bars": 8,
                "required_horizon_bars": 8,
            }
        )
        row["source_signal_id"] = source_id
        row["candidate_id"] = f"TRUE-{index}"
        row["arm"] = "TRUE"
        row["entry_open_utc"] = row["decision_utc"]
        row["time_exit_utc"] = row["decision_utc"]
        row["h"] = 2
        row["tau"] = 0.2
        row["p_early"] = 0.001
        row["p_late"] = -0.0002
        row["atr14_pips"] = 10.0
        row["slot"] = 40
        fade = follow_rows[index]
        fade["source_signal_id"] = source_id
        fade["candidate_id"] = f"FOLLOW_CONTROL-{index}"
        fade["arm"] = "FOLLOW_CONTROL"
        fade["entry_open_utc"] = fade["decision_utc"]
        fade["time_exit_utc"] = fade["decision_utc"]
        fade["h"] = 2
        fade["tau"] = 0.2
        fade["p_early"] = 0.001
        fade["p_late"] = -0.0002
        fade["atr14_pips"] = 10.0
        fade["slot"] = 40
    pass_report = {
        "schema_version": "vcex_001_source_feasibility_report.v1",
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "signal_ledgers": {"TRUE": true_rows, "FOLLOW_CONTROL": follow_rows},
        "raw_signal_classifications": classifications,
        "stage0": {
            "verdict": "SOURCE_PASS_FUTURE_ECONOMICS_PREREG_ONLY",
            "gates": {},
            "metrics": {},
        },
        "economics_authorized": False,
        "post_entry_ohlc_rows_read": 0,
        "outcome_fields_emitted": 0,
        "returns_computed": 0,
        "trades_simulated": 0,
        "performance_trials_executed": 0,
    }
    sut._persist_success(root, pass_report, row_sha)
    receipt = json.loads((root / "source_feasibility_receipt.json").read_text(encoding="utf-8"))
    terminal = json.loads((root / "attempt_terminal.json").read_text(encoding="utf-8"))
    assert receipt["status"] == sut.RECEIPT_NON_TERMINAL_STATUS
    assert receipt["stage0_verdict"] == "SOURCE_PASS_FUTURE_ECONOMICS_PREREG_ONLY"
    assert receipt["stage0_verdict_is_non_authoritative_calculation"] is True
    assert receipt["terminal_is_sole_authoritative_completion"] is True
    assert "terminal_status" not in receipt
    assert sut.TERMINAL_PASS_STATUS not in canonical(receipt).decode("utf-8")
    assert terminal["status"] == sut.TERMINAL_PASS_STATUS
    assert terminal["sole_authoritative_completion"] is True
    for name in (
        "attempt_started.json",
        "vcex_001_source_report.json",
        "vcex_001_source_classifications.jsonl",
        "vcex_001_source_ledger.jsonl",
        "source_feasibility_receipt.json",
    ):
        assert name in terminal["artifact_hashes"]

    root2 = tmp_path / "evidence_fault"
    root2.mkdir()
    sut._write_new_canonical(
        root2 / "attempt_started.json",
        {
            "schema_version": "vcex_001_attempt_started.v1",
            "hypothesis_id": sut.HYPOTHESIS_ID,
            "attempt_id": sut.ATTEMPT_ID,
            "reviewed_registry_row_sha256": row_sha,
            "status": "STARTED",
            "source_only_counters": sut._executed_source_only_counters(),
            "sealed_permissions": sut._sealed_permissions(),
        },
    )
    original_write = sut._write_new_canonical

    def flaky_write(path: Path, value: object) -> None:
        if path.name == "attempt_terminal.json":
            raise OSError("synthetic terminal write fault")
        return original_write(path, value)

    sut._write_new_canonical = flaky_write  # type: ignore[assignment]
    try:
        with pytest.raises(sut.ContractError, match="attempt_terminal write failed"):
            sut._persist_success(root2, pass_report, row_sha)
    finally:
        sut._write_new_canonical = original_write  # type: ignore[assignment]
    assert not (root2 / "attempt_terminal.json").exists()
    surviving = json.loads((root2 / "source_feasibility_receipt.json").read_text(encoding="utf-8"))
    assert surviving["status"] == sut.RECEIPT_NON_TERMINAL_STATUS
    assert "terminal_status" not in surviving
    assert sut.TERMINAL_PASS_STATUS not in canonical(surviving).decode("utf-8")
    sut._persist_engineering_failure(
        root2, row_sha, RuntimeError("authoritative attempt_terminal write failed")
    )
    eng = json.loads((root2 / "attempt_terminal.json").read_text(encoding="utf-8"))
    assert eng["status"] == sut.TERMINAL_ENGINEERING_INVALID
    assert eng["sole_authoritative_completion"] is True
    assert "source_feasibility_receipt.json" in eng["artifact_hashes"]
    assert "vcex_001_source_report.json" in eng["artifact_hashes"]
    for artifact_name in (
        "attempt_started.json",
        "vcex_001_source_report.json",
        "vcex_001_source_classifications.jsonl",
        "vcex_001_source_ledger.jsonl",
        "source_feasibility_receipt.json",
    ):
        payload = (root2 / artifact_name).read_bytes()
        assert sut.TERMINAL_PASS_STATUS.encode("ascii") not in payload
    assert (root / "attempt_terminal.json").read_bytes().find(
        sut.TERMINAL_PASS_STATUS.encode("ascii")
    ) >= 0


def test_receipt_never_carries_authoritative_pass_status() -> None:
    receipt = {
        "schema_version": "vcex_001_source_feasibility_receipt.v1",
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "attempt_id": sut.ATTEMPT_ID,
        "reviewed_registry_row_sha256": "E" * 64,
        "status": sut.RECEIPT_NON_TERMINAL_STATUS,
        "stage0_verdict": "SOURCE_PASS_FUTURE_ECONOMICS_PREREG_ONLY",
        "stage0_verdict_is_non_authoritative_calculation": True,
        "terminal_is_sole_authoritative_completion": True,
        "artifact_hashes": {},
        "source_only_counters": sut._executed_source_only_counters(),
        "sealed_permissions": sut._sealed_permissions(),
    }
    sut._assert_receipt_is_non_terminal(receipt)
    bad = dict(receipt)
    bad["terminal_status"] = sut.TERMINAL_PASS_STATUS
    with pytest.raises(sut.ContractError):
        sut._assert_receipt_is_non_terminal(bad)
    bad2 = dict(receipt)
    bad2["status"] = sut.TERMINAL_PASS_STATUS
    with pytest.raises(sut.ContractError):
        sut._assert_receipt_is_non_terminal(bad2)


def test_non_finite_numeric_fields_fail_closed() -> None:
    """NaN/+inf/-inf never pass signal selection, boundaries, or Stage-0 gates."""

    non_finite = (float("nan"), float("inf"), float("-inf"))
    at = utc(2020, 1, 6, 10, 0)
    base = _feature_template(at=at)
    assert len(sut.select_raw_signals([base])) == 1
    for field in ("atr14", "tau", "p_early", "p_late"):
        for bad in non_finite:
            poisoned = dict(base)
            poisoned[field] = bad
            assert sut.select_raw_signals([poisoned]) == []
    for left in (*non_finite, 1.0):
        for right in (*non_finite, 1.0):
            if math.isfinite(left) and math.isfinite(right):
                continue
            assert sut.le_inclusive(left, right) is False
            assert sut.ge_inclusive(left, right) is False
            assert sut.lt_strict(left, right) is False
            assert sut.gt_strict(left, right) is False
    # Inclusive product noise still accepted; non-finite gate operands cannot PASS.
    assert sut.ge_inclusive(0.00045, 0.45 * 0.001) is True
    assert sut.ge_inclusive(sut.MIN_STOP_DISTANCE / sut.PIP, 6.0) is True
    true_rows, follow_rows, horizons = _balanced_population(40)
    for field in ("cost_to_stop_ratio", "stop_distance_pips"):
        for bad in non_finite:
            rows = [dict(row) for row in true_rows]
            rows[0] = dict(rows[0])
            rows[0][field] = bad
            with pytest.raises(sut.ContractError, match="invalid geometry"):
                sut.evaluate_stage0_gates(
                    true_signals=rows,
                    follow_signals=follow_rows,
                    raw_first_per_day_count=len(rows),
                    horizon_records=horizons,
                    domain_complete=40,
                    domain_scheduled=40,
                    elapsed_weeks=10.0,
                )
    # Direct metric comparisons must not PASS non-finite values.
    for bad in non_finite:
        assert sut.le_inclusive(bad, 0.25) is False
        assert sut.ge_inclusive(bad, 0.99) is False
        assert sut.ge_inclusive(bad, 6.0) is False
        assert sut.le_inclusive(bad, 0.35) is False


def test_post_write_terminal_fault_recovers_without_pass(tmp_path: Path) -> None:
    """PASS bytes written then post-write raise => sole ENGINEERING_INVALID terminal."""

    root = tmp_path / "evidence_post_write"
    root.mkdir()
    row_sha = "F" * 64
    sut._write_new_canonical(
        root / "attempt_started.json",
        {
            "schema_version": "vcex_001_attempt_started.v1",
            "hypothesis_id": sut.HYPOTHESIS_ID,
            "attempt_id": sut.ATTEMPT_ID,
            "reviewed_registry_row_sha256": row_sha,
            "status": "STARTED",
            "source_only_counters": sut._executed_source_only_counters(),
            "sealed_permissions": sut._sealed_permissions(),
        },
    )
    true_rows, follow_rows, _ = _balanced_population(20)
    classifications = []
    for index, row in enumerate(true_rows):
        source_id = f"VCEX001-SRC-{index:016d}"
        classifications.append(
            {
                "source_signal_id": source_id,
                "decision_utc": row["decision_utc"],
                "entry_open_utc": row["decision_utc"],
                "status": "SOURCE_EXECUTABLE",
                "observed_horizon_bars": 8,
                "required_horizon_bars": 8,
            }
        )
        row["source_signal_id"] = source_id
        row["candidate_id"] = f"TRUE-{index}"
        row["arm"] = "TRUE"
        row["entry_open_utc"] = row["decision_utc"]
        row["time_exit_utc"] = row["decision_utc"]
        row["h"] = 2
        row["tau"] = 0.2
        row["p_early"] = 0.001
        row["p_late"] = -0.0002
        row["atr14_pips"] = 10.0
        row["slot"] = 40
        fade = follow_rows[index]
        fade["source_signal_id"] = source_id
        fade["candidate_id"] = f"FOLLOW_CONTROL-{index}"
        fade["arm"] = "FOLLOW_CONTROL"
        fade["entry_open_utc"] = fade["decision_utc"]
        fade["time_exit_utc"] = fade["decision_utc"]
        fade["h"] = 2
        fade["tau"] = 0.2
        fade["p_early"] = 0.001
        fade["p_late"] = -0.0002
        fade["atr14_pips"] = 10.0
        fade["slot"] = 40
    pass_report = {
        "schema_version": "vcex_001_source_feasibility_report.v1",
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "signal_ledgers": {"TRUE": true_rows, "FOLLOW_CONTROL": follow_rows},
        "raw_signal_classifications": classifications,
        "stage0": {
            "verdict": "SOURCE_PASS_FUTURE_ECONOMICS_PREREG_ONLY",
            "gates": {},
            "metrics": {},
        },
        "economics_authorized": False,
        "post_entry_ohlc_rows_read": 0,
        "outcome_fields_emitted": 0,
        "returns_computed": 0,
        "trades_simulated": 0,
        "performance_trials_executed": 0,
    }
    original_write = sut._write_new_canonical

    def write_pass_then_raise(path: Path, value: object) -> None:
        if path.name == "attempt_terminal.json":
            original_write(path, value)
            raise OSError("synthetic post-write identity/readback fault")
        return original_write(path, value)

    sut._write_new_canonical = write_pass_then_raise  # type: ignore[assignment]
    try:
        with pytest.raises(sut.ContractError, match="attempt_terminal write failed"):
            sut._persist_success(root, pass_report, row_sha)
    finally:
        sut._write_new_canonical = original_write  # type: ignore[assignment]

    suspect_path = root / "attempt_terminal.json"
    assert suspect_path.exists()
    suspect = json.loads(suspect_path.read_text(encoding="utf-8"))
    assert suspect["status"] == sut.TERMINAL_PASS_STATUS
    assert sut.TERMINAL_PASS_STATUS.encode("ascii") in suspect_path.read_bytes()

    sut._persist_engineering_failure(
        root, row_sha, RuntimeError("post-write identity fault after PASS bytes")
    )
    terminal_path = root / "attempt_terminal.json"
    assert terminal_path.exists()
    terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
    assert terminal["status"] == sut.TERMINAL_ENGINEERING_INVALID
    assert terminal["sole_authoritative_completion"] is True
    assert sut.TERMINAL_PASS_STATUS not in terminal_path.read_text(encoding="utf-8")
    assert sut.TERMINAL_PASS_STATUS.encode("ascii") not in terminal_path.read_bytes()
    assert "source_feasibility_receipt.json" in terminal["artifact_hashes"]
    assert "vcex_001_source_report.json" in terminal["artifact_hashes"]
    # Sole terminal file under the attempt root.
    terminal_names = [
        entry.name
        for entry in os.scandir(root)
        if entry.name == "attempt_terminal.json"
    ]
    assert terminal_names == ["attempt_terminal.json"]
    for artifact_name in (
        "attempt_started.json",
        "vcex_001_source_report.json",
        "vcex_001_source_classifications.jsonl",
        "vcex_001_source_ledger.jsonl",
        "source_feasibility_receipt.json",
        "attempt_terminal.json",
    ):
        payload = (root / artifact_name).read_bytes()
        assert sut.TERMINAL_PASS_STATUS.encode("ascii") not in payload
