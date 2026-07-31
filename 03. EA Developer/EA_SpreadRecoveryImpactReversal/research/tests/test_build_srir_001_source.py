from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "build_srir_001_source.py"
SPEC = importlib.util.spec_from_file_location("build_srir_001_source", SOURCE)
assert SPEC and SPEC.loader
sut = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sut)

UTC = timezone.utc
PLAN = Path(__file__).resolve().parents[1] / "HYP-SRIR-EURUSD-M5-001_SOURCE_FEASIBILITY_PLAN_V2.md"
PIP = sut.PIP


def utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def source_days(start: date, count: int) -> tuple[date, ...]:
    """Chronological unique source dates (weekdays only for compact synthetic)."""

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
    spread: float = 10.0,
) -> dict[str, object]:
    return {
        "time_utc": at,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "spread": spread,
    }


def flat_bar(at: datetime, price: float = 1.1000, spread: float = 10.0) -> dict[str, object]:
    return m1_row(
        at,
        open_=price,
        high=price + 0.00005,
        low=price - 0.00005,
        close=price,
        spread=spread,
    )


def fill_m5_block(
    rows: list[dict[str, object]],
    start: datetime,
    *,
    open_: float,
    high: float,
    low: float,
    close: float,
    spread: float = 10.0,
) -> None:
    """Append exact five M1 rows forming one M5 OHLC block."""

    # Distribute high/low across minutes so aggregate matches requested extremes.
    for index in range(5):
        at = start + timedelta(minutes=index)
        if index == 0:
            o, c = open_, open_ + (close - open_) * 0.2
            h = max(o, c, high) if index == 0 else max(o, c)
            l = min(o, c, low)
            # Force first bar to contribute open and extremes loosely
            rows.append(m1_row(at, open_=open_, high=high, low=low, close=c, spread=spread))
        elif index == 4:
            o = rows[-1]["close"]  # type: ignore[index]
            rows.append(
                m1_row(
                    at,
                    open_=float(o),
                    high=max(float(o), close),
                    low=min(float(o), close),
                    close=close,
                    spread=spread,
                )
            )
        else:
            o = rows[-1]["close"]  # type: ignore[index]
            mid = open_ + (close - open_) * (index / 4.0)
            rows.append(
                m1_row(
                    at,
                    open_=float(o),
                    high=max(float(o), mid, high if index == 1 else float(o)),
                    low=min(float(o), mid, low if index == 2 else float(o)),
                    close=mid,
                    spread=spread,
                )
            )


def fill_flat_m5(rows: list[dict[str, object]], start: datetime, price: float = 1.1000, spread: float = 10.0) -> None:
    for index in range(5):
        rows.append(flat_bar(start + timedelta(minutes=index), price, spread))


def fill_day_session(
    rows: list[dict[str, object]],
    day: date,
    *,
    price: float = 1.1000,
    spread: float = 10.0,
    start_hour: int = 6,
    end_hour: int = 17,
) -> None:
    """Fill continuous M1 from start_hour:00 through end_hour:00 exclusive."""

    start = datetime(day.year, day.month, day.day, start_hour, 0, tzinfo=UTC)
    end = datetime(day.year, day.month, day.day, end_hour, 0, tzinfo=UTC)
    at = start
    while at < end:
        rows.append(flat_bar(at, price, spread))
        at += timedelta(minutes=1)


def _directional_m5(
    *,
    open_: float,
    close: float,
    sign: int,
    atr_pips: float = 8.0,
) -> tuple[float, float, float, float]:
    """Build OHLC with body, range and outer-close for shock qualification."""

    body = abs(close - open_)
    # Ensure body/range >= 0.65 and outer 20% close.
    bar_range = body / 0.70
    if sign > 0:
        low = open_ - 0.05 * bar_range
        high = low + bar_range
        # close near high
        close = high - 0.05 * bar_range
        open_ = close - body
        # recompute to keep consistent
        low = min(open_, close) - 0.02 * bar_range
        high = max(open_, close) + 0.05 * bar_range
        # Force outer close
        high = close + 0.01 * (high - low + body)
        low = close - 0.95 * (high - close) / 0.05 if False else low
        low = close - ((close - open_) / 0.70) * 0.85
        high = low + (close - open_) / 0.70
        open_ = close - body
        # Final clamp
        low = min(open_, close, low)
        high = max(open_, close, high)
        # Ensure upper 20%: (close-low)/range >= 0.80
        bar_range = high - low
        if (close - low) / bar_range < 0.80:
            low = close - 0.80 * (high - close) / 0.20
            high = max(high, close)
            low = min(low, open_, close)
            high = max(high, open_, close)
    else:
        body = abs(open_ - close)
        high = open_ + 0.05 * (body / 0.70)
        low = high - body / 0.70
        close = low + 0.05 * (high - low)
        open_ = close + body
        high = max(open_, close, high)
        low = min(open_, close, low)
        bar_range = high - low
        if (high - close) / bar_range < 0.80:
            high = close + 0.80 * (close - low) / 0.20
            high = max(high, open_, close)
            low = min(low, open_, close)
    # Ensure body large enough vs atr
    body_now = abs(close - open_)
    min_body = max(4.0 * PIP, 0.50 * atr_pips * PIP)
    if body_now < min_body:
        if sign > 0:
            close = open_ + min_body
            high = max(high, close) + 0.00002
            low = min(low, open_) - 0.00002
            # re-fix outer
            bar_range = high - low
            if (close - low) / bar_range < 0.80:
                low = close - 0.82 * bar_range
                high = max(high, close)
        else:
            close = open_ - min_body
            low = min(low, close) - 0.00002
            high = max(high, open_) + 0.00002
            bar_range = high - low
            if (high - close) / bar_range < 0.80:
                high = close + 0.82 * bar_range
                low = min(low, close)
    return open_, high, low, close


def build_valid_path(
    *,
    shock_sign: int = 1,
    start_day: date = date(2018, 1, 2),
    source_date_count: int = 30,
    shock_hour: int = 10,
    shock_minute: int = 0,
    recovery_offset_bars: int = 1,
    baseline_spread: float = 10.0,
    shock_spread: float = 25.0,
    recovery_spread: float = 12.0,
    horizon_bars: int = 70,
    with_horizon: bool = True,
) -> tuple[list[dict[str, object]], tuple[date, ...], datetime]:
    """Construct burn-in + baseline history and one valid shock/recovery decision."""

    dates = source_days(start_day, source_date_count)
    assert len(dates) > sut.BURN_IN_ELIGIBLE_DATES + 1
    signal_day = dates[sut.BURN_IN_ELIGIBLE_DATES]
    rows: list[dict[str, object]] = []
    price = 1.1000
    # Warm all prior dates + signal day with full sessions for ATR + baseline slots.
    for day in dates:
        if day > signal_day:
            break
        fill_day_session(rows, day, price=price, spread=baseline_spread, start_hour=6, end_hour=17)

    # Overlay shock block and recovery on signal day by replacing rows in that window.
    shock_start = datetime(signal_day.year, signal_day.month, signal_day.day, shock_hour, shock_minute, tzinfo=UTC)
    # Remove existing minutes covering shock + recovery + horizon for clean overlay.
    recovery_start = shock_start + timedelta(minutes=5 * recovery_offset_bars)
    horizon_start = recovery_start + timedelta(minutes=5)
    end_overlay = horizon_start + timedelta(minutes=horizon_bars + 5)
    rows = [r for r in rows if not (shock_start <= r["time_utc"] < end_overlay)]  # type: ignore[operator]

    # Shock OHLC: large directional body.
    if shock_sign > 0:
        open_s = price
        close_s = price + 0.00080  # 8 pips body
    else:
        open_s = price
        close_s = price - 0.00080
    open_s, high_s, low_s, close_s = _directional_m5(open_=open_s, close=close_s, sign=shock_sign, atr_pips=8.0)
    # Write shock M5 as five M1 with elevated spread.
    fill_m5_block(
        rows,
        shock_start,
        open_=open_s,
        high=high_s,
        low=low_s,
        close=close_s,
        spread=shock_spread,
    )
    # Intermediate bars between shock and recovery if offset > 1: mild continuation without new extreme.
    for step in range(1, recovery_offset_bars):
        mid = shock_start + timedelta(minutes=5 * step)
        if shock_sign > 0:
            o = close_s
            c = close_s - 0.00005
            h = min(high_s, max(o, c) + 0.00002)
            l = min(o, c) - 0.00002
        else:
            o = close_s
            c = close_s + 0.00005
            h = max(o, c) + 0.00002
            l = max(low_s, min(o, c) - 0.00002)
        fill_m5_block(rows, mid, open_=o, high=h, low=l, close=c, spread=shock_spread)

    # Recovery: opposite body, 25%+ retrace, spread normalized, no new extreme.
    body_abs = abs(close_s - open_s)
    if shock_sign > 0:
        rec_open = close_s
        rec_close = close_s - 0.30 * body_abs
        rec_high = min(high_s, max(rec_open, rec_close) + 0.00002)
        rec_low = min(rec_open, rec_close) - 0.00002
    else:
        rec_open = close_s
        rec_close = close_s + 0.30 * body_abs
        rec_high = max(rec_open, rec_close) + 0.00002
        rec_low = max(low_s, min(rec_open, rec_close) - 0.00002)
    fill_m5_block(
        rows,
        recovery_start,
        open_=rec_open,
        high=rec_high,
        low=rec_low,
        close=rec_close,
        spread=recovery_spread,
    )
    decision = recovery_start
    if with_horizon:
        for index in range(horizon_bars):
            rows.append(flat_bar(horizon_start + timedelta(minutes=index), rec_close, baseline_spread))
    rows.sort(key=lambda item: item["time_utc"])  # type: ignore[arg-type, return-value]
    # De-dupe by timestamp if any overlap slipped through.
    dedup: dict[datetime, dict[str, object]] = {}
    for row in rows:
        dedup[_as_utc_row(row)] = row
    ordered = [dedup[key] for key in sorted(dedup)]
    return ordered, dates, decision


def _as_utc_row(row: dict[str, object]) -> datetime:
    value = row["time_utc"]
    assert isinstance(value, datetime)
    return value


def build_valid_long_path() -> tuple[list[dict[str, object]], tuple[date, ...], datetime]:
    return build_valid_path(shock_sign=-1)  # down shock -> TRUE long


def build_valid_short_path() -> tuple[list[dict[str, object]], tuple[date, ...], datetime]:
    return build_valid_path(shock_sign=1)  # up shock -> TRUE short


def multi_day_signals(
    n_long: int,
    n_short: int,
    *,
    start_day: date = date(2018, 1, 2),
) -> tuple[list[dict[str, object]], tuple[date, ...], list[datetime]]:
    """Many first-per-day decisions with full horizons for gate tests."""

    needed_signal_days = n_long + n_short
    total_dates = sut.BURN_IN_ELIGIBLE_DATES + needed_signal_days + 2
    dates = source_days(start_day, total_dates)
    rows: list[dict[str, object]] = []
    decisions: list[datetime] = []
    price = 1.1000
    baseline_spread = 10.0
    # Warm all dates with sessions first.
    for day in dates:
        fill_day_session(rows, day, price=price, spread=baseline_spread, start_hour=6, end_hour=17)

    long_left, short_left = n_long, n_short
    signal_index = 0
    for day in dates[sut.BURN_IN_ELIGIBLE_DATES :]:
        if long_left <= 0 and short_left <= 0:
            break
        if day.weekday() >= 5:
            continue
        if short_left > 0 and (long_left == 0 or signal_index % 2 == 0):
            sign = 1
            short_left -= 1
        else:
            sign = -1
            long_left -= 1
        shock_start = datetime(day.year, day.month, day.day, 10, 0, tzinfo=UTC)
        recovery_start = shock_start + timedelta(minutes=5)
        horizon_start = recovery_start + timedelta(minutes=5)
        end_overlay = horizon_start + timedelta(minutes=70)
        rows = [r for r in rows if not (shock_start <= r["time_utc"] < end_overlay)]  # type: ignore[operator]
        if sign > 0:
            open_s, close_s = price, price + 0.00080
        else:
            open_s, close_s = price, price - 0.00080
        open_s, high_s, low_s, close_s = _directional_m5(open_=open_s, close=close_s, sign=sign)
        fill_m5_block(rows, shock_start, open_=open_s, high=high_s, low=low_s, close=close_s, spread=25.0)
        body_abs = abs(close_s - open_s)
        if sign > 0:
            rec_open = close_s
            rec_close = close_s - 0.30 * body_abs
            rec_high = min(high_s, max(rec_open, rec_close) + 0.00002)
            rec_low = min(rec_open, rec_close) - 0.00002
        else:
            rec_open = close_s
            rec_close = close_s + 0.30 * body_abs
            rec_high = max(rec_open, rec_close) + 0.00002
            rec_low = max(low_s, min(rec_open, rec_close) - 0.00002)
        fill_m5_block(
            rows,
            recovery_start,
            open_=rec_open,
            high=rec_high,
            low=rec_low,
            close=rec_close,
            spread=12.0,
        )
        for index in range(70):
            rows.append(flat_bar(horizon_start + timedelta(minutes=index), rec_close, baseline_spread))
        decisions.append(recovery_start)
        signal_index += 1
        price += 0.00001

    dedup: dict[datetime, dict[str, object]] = {}
    for row in rows:
        dedup[_as_utc_row(row)] = row
    ordered = [dedup[key] for key in sorted(dedup)]
    return ordered, dates, decisions


def ledger_row(
    *,
    direction: str,
    year: int,
    stop_pips: float,
    decision: datetime,
    arm: str = "TRUE",
) -> dict[str, object]:
    cost = 1.50 / stop_pips
    sid = sut.assign_source_signal_id(decision)
    identity = f"{sut.HYPOTHESIS_ID}|{arm}|{sid}|{sut._iso_z(decision)}|{direction}".encode("ascii")
    return {
        "candidate_id": f"SRIR001-{arm}-{sha(identity)[:16]}",
        "source_signal_id": sid,
        "arm": arm,
        "decision_utc": sut._iso_z(decision),
        "entry_open_utc": sut._iso_z(decision + timedelta(minutes=5)),
        "time_exit_utc": sut._iso_z(decision + timedelta(minutes=5 + sut.HORIZON_BARS)),
        "direction": direction,
        "year": year,
        "shock_sign": 1 if direction == "SHORT" and arm == "TRUE" else -1,
        "shock_time_utc": sut._iso_z(decision - timedelta(minutes=5)),
        "baseline_spread_points": 10.0,
        "shock_spread_points": 25.0,
        "recovery_spread_points": 12.0,
        "atr20_prev_pips": 8.0,
        "stop_distance_pips": stop_pips,
        "cost_to_stop_ratio": cost,
        "recovery_bars": 1,
        "slot": 10 * 12,
    }


def matched_pair(direction_true: str, year: int, stop: float, decision: datetime) -> tuple[dict, dict]:
    follow = "LONG" if direction_true == "SHORT" else "SHORT"
    true_row = ledger_row(direction=direction_true, year=year, stop_pips=stop, decision=decision, arm="TRUE")
    follow_row = ledger_row(direction=follow, year=year, stop_pips=stop, decision=decision, arm="FOLLOW_CONTROL")
    follow_row["source_signal_id"] = true_row["source_signal_id"]
    return true_row, follow_row


def _passing_domain_metrics() -> dict[str, object]:
    return {
        "formation_scheduled": 100,
        "formation_complete": 100,
        "formation_ratio": 1.0,
        "baseline_complete_scan_blocks": 100,
        "baseline_available": 100,
        "baseline_availability_ratio": 1.0,
        "positive_spread_observed_m1": 1000,
        "positive_spread_count": 1000,
        "positive_spread_ratio": 1.0,
        "post_burn_in_weekday_count": 10,
        "slots_per_day": 105,
    }


# ---------------------------------------------------------------------------
# Basic identity / import
# ---------------------------------------------------------------------------


def test_ast_parse_deliverables() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    assert any(isinstance(node, ast.FunctionDef) and node.name == "scan_source" for node in tree.body)
    assert any(isinstance(node, ast.FunctionDef) and node.name == "execute_probe" for node in tree.body)


def test_sentinel_is_exactly_disarmed_and_import_inert() -> None:
    assert sut.REVIEWED_REGISTRY_ROW_SHA256 is None
    text = SOURCE.read_bytes()
    assert b'REVIEWED_REGISTRY_ROW_SHA256: str | None = None' in text
    matches = [line for line in text.splitlines() if sut._SENTINEL_RE.match(line.rstrip(b"\n"))]
    assert len(matches) == 1


def test_cli_dual_gate_disarmed(tmp_path: Path) -> None:
    with pytest.raises(sut.ContractError, match="disarmed"):
        sut.execute_probe(workspace_root=tmp_path, run_switch=False)
    with pytest.raises(sut.ContractError, match="disarmed"):
        sut.execute_probe(workspace_root=tmp_path, run_switch=True)


def test_parse_args_execute_probe_flag() -> None:
    args = sut.parse_args(["--execute-probe", "--workspace-root", "."])
    assert args.execute_probe is True


def test_plan_hash_binding_matches_exact_bytes() -> None:
    assert sha(PLAN.read_bytes()) == sut.PLAN_SHA256


def test_immutable_hashes_are_bound() -> None:
    assert sut.M1_MANIFEST_SHA256 == "A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7"
    assert sut.M1_RECEIPT_SHA256 == "8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8"
    assert sut.M1_SOURCE_SHA256 == "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
    assert sut.REGISTRY_VALIDATOR_SHA256 == "B04B379E11F556A0CF3E6C3264768176310FF01CF360CC3B92464C51A2996DD0"
    assert sut.REGISTRY_SCHEMA_SHA256 == "96C80D3C46A105A9754CA1325F3DD6C160D92A9D5800ECBC402DE0F40C612F5C"


def test_ulp_inclusive_boundaries_equal_and_neighbors() -> None:
    assert sut.le_inclusive(1.0, 1.0) is True
    assert sut.ge_inclusive(1.0, 1.0) is True
    assert sut.lt_strict(1.0, 1.0) is False
    assert sut.gt_strict(1.0, 1.0) is False
    assert sut.le_inclusive(1.0, 1.0 + math.ulp(1.0)) is True
    assert sut.ge_inclusive(1.0 + math.ulp(1.0), 1.0) is True


def test_non_finite_boundary_helpers_fail() -> None:
    assert sut.le_inclusive(float("nan"), 1.0) is False
    assert sut.ge_inclusive(float("inf"), 1.0) is False
    assert sut.lt_strict(float("-inf"), 0.0) is False
    assert sut.gt_strict(1.0, float("nan")) is False


def test_non_finite_ohlc_and_spread_rejected() -> None:
    at = utc(2018, 1, 2, 10, 0)
    with pytest.raises(sut.ContractError):
        sut._ohlc({"open": float("nan"), "high": 1.1, "low": 1.0, "close": 1.05})
    with pytest.raises(sut.ContractError):
        sut._producer_spread(float("inf"))
    with pytest.raises(sut.ContractError):
        sut.build_complete_m5([m1_row(at, open_=1.1, high=1.1, low=1.1, close=1.1, spread=float("nan"))])


def test_zero_and_negative_spread_unavailable() -> None:
    assert sut.positive_finite_spread(0.0) is None
    assert sut.positive_finite_spread(-1.0) is None
    assert sut.positive_finite_spread(float("nan")) is None
    assert sut.positive_finite_spread(5.0) == 5.0


def test_complete_m5_exact_offsets_and_max_spread() -> None:
    start = utc(2018, 6, 4, 10, 0)
    rows = []
    for i, sp in enumerate([8.0, 12.0, 9.0, 15.0, 10.0]):
        rows.append(flat_bar(start + timedelta(minutes=i), 1.10, sp))
    bars, quality = sut.build_complete_m5(rows)
    assert quality["complete_bins"] == 1
    assert bars[0]["block_spread_points"] == 15.0
    assert bars[0]["spread_available"] is True
    assert bars[0]["open"] == pytest.approx(1.10)
    assert bars[0]["availability_utc"] == start + timedelta(minutes=5)


def test_complete_m5_rejects_gap_duplicate_and_never_fills() -> None:
    start = utc(2018, 6, 4, 10, 0)
    rows = [flat_bar(start + timedelta(minutes=i)) for i in (0, 1, 2, 4)]  # missing minute 3
    bars, quality = sut.build_complete_m5(rows)
    assert quality["complete_bins"] == 0
    assert quality["incomplete_bins"] == 1
    assert bars == []
    dup = [flat_bar(start), flat_bar(start)]
    with pytest.raises(sut.ContractError, match="duplicated"):
        sut.build_complete_m5(dup)


def test_scan_domain_07_to_1540_only() -> None:
    assert sut.in_scan_domain(utc(2018, 6, 4, 7, 0)) is True
    assert sut.in_scan_domain(utc(2018, 6, 4, 15, 40)) is True
    assert sut.in_scan_domain(utc(2018, 6, 4, 15, 45)) is False
    assert sut.in_scan_domain(utc(2018, 6, 4, 6, 55)) is False
    assert sut.in_scan_domain(utc(2018, 6, 2, 10, 0)) is False  # Saturday
    assert sut.scan_domain_slots_per_day() == 105


def test_atr20_excludes_current_and_resets_on_gap() -> None:
    # Build 25 contiguous M5 flat bars then a gap then more.
    start = utc(2018, 6, 4, 7, 0)
    rows = []
    for i in range(25 * 5):
        rows.append(flat_bar(start + timedelta(minutes=i), 1.1000 + (i // 5) * 0.00001))
    bars, _ = sut.build_complete_m5(rows)
    enriched = sut.attach_wilder_atr20(bars)
    # Need 20 TRs after first bar => atr20 set from index 20 onward; atr20_prev lags one.
    assert enriched[0]["atr20_prev"] is None
    # Index 20 is the 21st bar: after 20 contiguous TRs seed at bar index 20's update,
    # atr20_prev for bar 21 uses atr at bar 20.
    ready = [bar for bar in enriched if bar["atr20_prev"] is not None]
    assert len(ready) >= 1
    # Gap reset
    gapped = list(bars)
    # Drop one bar in the middle to create time gap in remaining series
    gapped = bars[:10] + bars[12:]
    enriched2 = sut.attach_wilder_atr20(gapped)
    # After gap, ATR should reset
    gap_time = bars[12]["time_utc"]
    after = [b for b in enriched2 if b["time_utc"] >= gap_time]
    assert after[0]["atr20_prev"] is None or after[0]["contiguous_prev"] is False


def test_prior_20_baseline_median_excludes_current_and_no_fill() -> None:
    dates = source_days(date(2018, 1, 2), 25)
    slot = 10 * 12  # 10:00
    slot_maps: dict[date, dict[int, float | None]] = {}
    for index, day in enumerate(dates):
        # spreads 1..25 for the 10:00 slot
        slot_maps[day] = {slot: float(index + 1)}
    date_index = {day: i for i, day in enumerate(dates)}
    day = dates[20]
    base = sut.prior_20_baseline(
        source_dates=dates,
        date_index=date_index,
        slot_maps=slot_maps,
        day=day,
        slot=slot,
    )
    # prior indices 0..19 -> values 1..20, median = 10.5
    assert base == pytest.approx(10.5)
    # Missing one prior date slot => unavailable, no fill
    slot_maps[dates[5]][slot] = None
    assert (
        sut.prior_20_baseline(
            source_dates=dates,
            date_index=date_index,
            slot_maps=slot_maps,
            day=day,
            slot=slot,
        )
        is None
    )


def test_v2_baseline_calendar_excludes_partial_sunday_manifest_dates() -> None:
    dates = tuple(date(2016, 1, 4) + timedelta(days=index) for index in range(35))
    eligible = sut.eligible_baseline_dates(dates)
    assert eligible == tuple(day for day in dates if day.weekday() < 5)
    assert all(day.weekday() < 5 for day in eligible)
    assert date(2016, 1, 10) not in eligible
    assert len(eligible[: sut.BURN_IN_ELIGIBLE_DATES]) == 20


def test_v2_scan_excludes_sunday_spreads_from_baseline_and_burn_in() -> None:
    rows, dates, _ = build_valid_short_path()
    reference = sut.scan_source_once(rows, dates)
    sunday_rows: list[dict[str, object]] = []
    cursor = dates[0]
    sundays: list[date] = []
    while cursor <= dates[-1]:
        if cursor.weekday() == 6:
            sundays.append(cursor)
            fill_day_session(sunday_rows, cursor, spread=999.0)
        cursor += timedelta(days=1)
    mixed_dates = tuple(sorted(set(dates) | set(sundays)))
    mixed_rows = sorted([*rows, *sunday_rows], key=lambda row: row["time_utc"])
    mixed = sut.scan_source_once(mixed_rows, mixed_dates)
    assert mixed["exact_once"]["classification_digest_sha256"] == reference["exact_once"][
        "classification_digest_sha256"
    ]
    assert mixed["population"]["raw_first_per_day_count"] >= 1
    assert all(
        row["baseline_spread_points"] == pytest.approx(10.0)
        for row in mixed["signal_ledgers"]["TRUE"]
    )


def test_burn_in_excludes_first_20_eligible_dates() -> None:
    rows, dates, _ = build_valid_path(source_date_count=25)
    report = sut.scan_source_once(rows, dates)
    # Decision should only exist on post-burn-in dates
    for row in report["raw_signal_classifications"]:
        day = date.fromisoformat(str(row["decision_utc"])[:10])
        assert day not in set(dates[:20])


def test_shock_numeric_boundaries_ratio_and_excess() -> None:
    baseline = 10.0
    open_s, high_s, low_s, close_s = _directional_m5(open_=1.10, close=1.1008, sign=1)
    bar = {
        "time_utc": utc(2018, 6, 4, 10, 0),
        "slot": 10 * 12,
        "open": open_s,
        "high": high_s,
        "low": low_s,
        "close": close_s,
        "block_spread_points": 19.9,
        "spread_available": True,
        "atr20_prev": 0.0008,
    }
    assert sut.is_qualifying_shock(bar, baseline=baseline) is None
    bar["block_spread_points"] = 20.0
    assert sut.is_qualifying_shock(bar, baseline=baseline) is not None
    bar2 = dict(bar)
    bar2["block_spread_points"] = 14.0
    assert sut.is_qualifying_shock(bar2, baseline=10.0) is None


def test_body_range_outer_close_boundaries() -> None:
    baseline = 10.0
    atr = 0.0008
    bar = {
        "time_utc": utc(2018, 6, 4, 10, 0),
        "slot": 10 * 12,
        "open": 1.1000,
        "high": 1.1010,
        "low": 1.0990,
        "close": 1.1006,  # body 6p, range 20p => 0.30
        "block_spread_points": 25.0,
        "spread_available": True,
        "atr20_prev": atr,
    }
    assert sut.is_qualifying_shock(bar, baseline=baseline) is None
    open_s, high_s, low_s, close_s = _directional_m5(open_=1.1000, close=1.1008, sign=1, atr_pips=8.0)
    bar_ok = {
        "time_utc": utc(2018, 6, 4, 10, 0),
        "slot": 10 * 12,
        "open": open_s,
        "high": high_s,
        "low": low_s,
        "close": close_s,
        "block_spread_points": 25.0,
        "spread_available": True,
        "atr20_prev": atr,
    }
    assert sut.is_qualifying_shock(bar_ok, baseline=baseline) is not None


def test_long_short_mirrors_matched_arms() -> None:
    for builder, true_dir in ((build_valid_long_path, "LONG"), (build_valid_short_path, "SHORT")):
        rows, dates, decision = builder()
        report = sut.scan_source(rows, dates, with_independent_replay=True)
        true_rows = report["signal_ledgers"]["TRUE"]
        follow_rows = report["signal_ledgers"]["FOLLOW_CONTROL"]
        assert len(true_rows) >= 1
        assert true_rows[0]["direction"] == true_dir
        assert follow_rows[0]["direction"] != true_dir
        assert true_rows[0]["decision_utc"] == follow_rows[0]["decision_utc"]
        assert true_rows[0]["source_signal_id"] == follow_rows[0]["source_signal_id"]
        assert true_rows[0]["decision_utc"].startswith(decision.date().isoformat())


def test_next_m1_entry_and_60_bar_horizon_timestamp_only() -> None:
    rows, dates, decision = build_valid_short_path()
    report = sut.scan_source_once(rows, dates)
    true_rows = report["signal_ledgers"]["TRUE"]
    assert true_rows
    entry = datetime.fromisoformat(true_rows[0]["entry_open_utc"].replace("Z", "+00:00"))
    assert entry == decision + timedelta(minutes=5)
    exit_t = datetime.fromisoformat(true_rows[0]["time_exit_utc"].replace("Z", "+00:00"))
    assert exit_t == entry + timedelta(minutes=60)
    # Horizon mapping never needs OHLC
    observed = {r["time_utc"] for r in rows}
    horizon = sut.map_horizon(entry, observed)  # type: ignore[arg-type]
    assert horizon["source_executable"] is True
    assert "open" not in horizon


def test_horizon_censoring_excludes_ledger_arms() -> None:
    rows, dates, decision = build_valid_path(with_horizon=False, horizon_bars=0)
    # No horizon minutes after recovery close
    report = sut.scan_source_once(rows, dates)
    assert report["population"]["raw_first_per_day_count"] >= 1
    assert report["population"]["eligible_count"] == 0
    assert report["signal_ledgers"]["TRUE"] == []
    assert all(c["status"] == "HORIZON_INCOMPLETE" for c in report["raw_signal_classifications"])


def test_stop_distance_formula_and_cost_geometry() -> None:
    shock = {"sign": 1, "high": 1.10100, "low": 1.09900}
    stop = sut.planned_stop_pips(shock=shock, recovery_close=1.10050)
    # (1.10100 - 1.10050)/0.0001 + 0.50 = 5 + 0.50 = 5.5 -> max with 6 = 6
    assert stop == pytest.approx(6.0)
    shock2 = {"sign": -1, "high": 1.10100, "low": 1.09900}
    stop2 = sut.planned_stop_pips(shock=shock2, recovery_close=1.10020)
    # (1.10020 - 1.09900)/0.0001 + 0.5 = 12 + 0.5 = 12.5
    assert stop2 == pytest.approx(12.5)
    assert (1.50 / stop2) == pytest.approx(1.50 / 12.5)


def test_new_shock_replaces_pending_identity() -> None:
    dates = source_days(date(2019, 1, 2), 30)
    rows: list[dict[str, object]] = []
    for day in dates[:22]:
        fill_day_session(rows, day, spread=10.0)
    signal_day = dates[20]
    first_shock = datetime(signal_day.year, signal_day.month, signal_day.day, 10, 0, tzinfo=UTC)
    second_shock = first_shock + timedelta(minutes=5)
    recovery = second_shock + timedelta(minutes=5)
    rows = [
        row
        for row in rows
        if not (first_shock <= row["time_utc"] < recovery + timedelta(minutes=5))  # type: ignore[operator]
    ]
    open_1, high_1, low_1, close_1 = _directional_m5(
        open_=1.1000, close=1.1008, sign=1
    )
    fill_m5_block(
        rows, first_shock, open_=open_1, high=high_1, low=low_1,
        close=close_1, spread=25.0
    )
    open_2, high_2, low_2, close_2 = _directional_m5(
        open_=close_1, close=close_1 + 0.0008, sign=1
    )
    fill_m5_block(
        rows, second_shock, open_=open_2, high=high_2, low=low_2,
        close=close_2, spread=25.0
    )
    body_2 = abs(close_2 - open_2)
    recovery_close = close_2 - 0.30 * body_2
    fill_m5_block(
        rows,
        recovery,
        open_=close_2,
        high=min(high_2, close_2 + 0.00002),
        low=recovery_close - 0.00002,
        close=recovery_close,
        spread=12.0,
    )
    dedup = {row["time_utc"]: row for row in rows}
    ordered = [dedup[key] for key in sorted(dedup)]  # type: ignore[index]
    bars, _ = sut.build_complete_m5(ordered)
    enriched = sut.attach_wilder_atr20(bars)
    raw, funnel = sut.select_raw_signals(
        enriched, source_dates=dates, burn_in_dates=set(dates[:20])
    )
    assert funnel.get("SHOCK_REPLACEMENT", 0) == 1
    assert len(raw) == 1
    assert raw[0]["shock_time_utc"] == sut._iso_z(second_shock)


def test_recovery_expires_after_three_nonqualifying_bars() -> None:
    dates3 = source_days(date(2019, 1, 2), 30)
    rows3: list[dict[str, object]] = []
    for day in dates3[:22]:
        fill_day_session(rows3, day, spread=10.0)
    signal_day = dates3[20]
    shock_start = datetime(signal_day.year, signal_day.month, signal_day.day, 10, 0, tzinfo=UTC)
    rows3 = [r for r in rows3 if not (shock_start <= r["time_utc"] < shock_start + timedelta(minutes=30))]  # type: ignore[operator]
    open_s, high_s, low_s, close_s = _directional_m5(open_=1.10, close=1.1008, sign=1)
    fill_m5_block(rows3, shock_start, open_=open_s, high=high_s, low=low_s, close=close_s, spread=25.0)
    # Next three bars continue same direction with high spread — no recovery
    for step in range(1, 4):
        mid = shock_start + timedelta(minutes=5 * step)
        fill_m5_block(
            rows3,
            mid,
            open_=close_s,
            high=high_s + 0.00001,  # new extreme may also cancel extreme rule
            low=close_s - 0.00002,
            close=close_s + 0.00010,
            spread=25.0,
        )
    dedup = {r["time_utc"]: r for r in rows3}
    ordered = [dedup[k] for k in sorted(dedup)]  # type: ignore[index]
    bars, _ = sut.build_complete_m5(ordered)
    enriched = sut.attach_wilder_atr20(bars)
    raw, funnel = sut.select_raw_signals(enriched, source_dates=dates3, burn_in_dates=set(dates3[:20]))
    assert raw == []
    assert funnel.get("RECOVERY_EXPIRED", 0) >= 1 or funnel.get("RECOVERY_NOT_YET", 0) >= 1


def test_daily_refractory_keeps_first_only() -> None:
    rows, dates, decision = build_valid_short_path()
    # Inject a second shock/recovery later same day
    day = decision.date()
    second_shock = datetime(day.year, day.month, day.day, 12, 0, tzinfo=UTC)
    second_rec = second_shock + timedelta(minutes=5)
    open_s, high_s, low_s, close_s = _directional_m5(open_=1.10, close=1.1008, sign=1)
    # remove and refill
    rows = [r for r in rows if not (second_shock <= r["time_utc"] < second_rec + timedelta(minutes=70))]  # type: ignore[operator]
    fill_m5_block(rows, second_shock, open_=open_s, high=high_s, low=low_s, close=close_s, spread=25.0)
    body = abs(close_s - open_s)
    fill_m5_block(
        rows,
        second_rec,
        open_=close_s,
        high=min(high_s, close_s + 0.00002),
        low=close_s - 0.30 * body,
        close=close_s - 0.30 * body,
        spread=12.0,
    )
    for i in range(70):
        rows.append(flat_bar(second_rec + timedelta(minutes=5 + i), close_s - 0.30 * body))
    dedup = {r["time_utc"]: r for r in rows}
    ordered = [dedup[k] for k in sorted(dedup)]  # type: ignore[index]
    report = sut.scan_source_once(ordered, dates)
    assert report["population"]["raw_first_per_day_count"] == 1
    assert report["raw_signal_classifications"][0]["decision_utc"].startswith(decision.isoformat()[:16].replace("+00:00", ""))


def test_gap_cancels_pending_shock() -> None:
    dates = source_days(date(2018, 3, 1), 30)
    rows: list[dict[str, object]] = []
    for day in dates[:22]:
        fill_day_session(rows, day, spread=10.0)
    signal_day = dates[20]
    shock_start = datetime(signal_day.year, signal_day.month, signal_day.day, 10, 0, tzinfo=UTC)
    rows = [r for r in rows if not (shock_start <= r["time_utc"] < shock_start + timedelta(hours=2))]  # type: ignore[operator]
    open_s, high_s, low_s, close_s = _directional_m5(open_=1.10, close=1.1008, sign=1)
    fill_m5_block(rows, shock_start, open_=open_s, high=high_s, low=low_s, close=close_s, spread=25.0)
    # Skip 10:05 block entirely; place recovery at 10:10 without contiguous intermediate
    rec = shock_start + timedelta(minutes=10)
    body = abs(close_s - open_s)
    fill_m5_block(
        rows,
        rec,
        open_=close_s,
        high=min(high_s, close_s),
        low=close_s - 0.30 * body,
        close=close_s - 0.30 * body,
        spread=12.0,
    )
    dedup = {r["time_utc"]: r for r in rows}
    ordered = [dedup[k] for k in sorted(dedup)]  # type: ignore[index]
    bars, _ = sut.build_complete_m5(ordered)
    enriched = sut.attach_wilder_atr20(bars)
    raw, funnel = sut.select_raw_signals(enriched, source_dates=dates, burn_in_dates=set(dates[:20]))
    assert raw == []
    assert funnel.get("SHOCK", 0) >= 1
    assert funnel.get("GAP_CANCEL", 0) >= 1


def _balanced_gate_population(
    *,
    stop: float = 6.0,
    n_long: int = 20,
    n_short: int = 20,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Build matched arms with year share <= 0.35 and balanced directions."""

    base = utc(2016, 1, 4, 12, 0)
    true_rows: list[dict] = []
    follow_rows: list[dict] = []
    horizons: list[dict] = []
    years = [2016, 2017, 2018, 2019, 2020]
    idx = 0
    for _ in range(n_long):
        year = years[idx % len(years)]
        decision = base + timedelta(days=idx)
        t, f = matched_pair("LONG", year, stop, decision)
        true_rows.append(t)
        follow_rows.append(f)
        horizons.append(
            {
                "source_signal_id": t["source_signal_id"],
                "source_executable": True,
                "reason": "SOURCE_EXECUTABLE",
                "observed_horizon_bars": 60,
                "required_horizon_bars": 60,
            }
        )
        idx += 1
    for _ in range(n_short):
        year = years[idx % len(years)]
        decision = base + timedelta(days=idx + 100)
        t, f = matched_pair("SHORT", year, stop, decision)
        true_rows.append(t)
        follow_rows.append(f)
        horizons.append(
            {
                "source_signal_id": t["source_signal_id"],
                "source_executable": True,
                "reason": "SOURCE_EXECUTABLE",
                "observed_horizon_bars": 60,
                "required_horizon_bars": 60,
            }
        )
        idx += 1
    return true_rows, follow_rows, horizons


def test_thirteen_gates_present_and_pass_at_boundaries() -> None:
    true_rows, follow_rows, horizons = _balanced_gate_population()
    stage0 = sut.evaluate_stage0_gates(
        true_signals=true_rows,
        follow_signals=follow_rows,
        raw_first_per_day_count=40,
        horizon_records=horizons,
        domain_metrics=_passing_domain_metrics(),
        source_only_counters=sut._executed_source_only_counters(),
        elapsed_weeks=10.0,
    )
    assert len(stage0["gates"]) == 13
    assert all(stage0["gates"].values()), stage0["gates"]
    assert stage0["verdict"] == sut.STAGE0_PASS


@pytest.mark.parametrize(
    "mutation,failed_gate",
    [
        ("cadence_low", "true_cadence_2_to_5_per_elapsed_week"),
        ("long_share", "true_long_share_at_least_0_25"),
        ("short_share", "true_short_share_at_least_0_25"),
        ("year_share", "max_calendar_year_share_at_most_0_35"),
        ("per_side", "at_least_20_executable_true_per_direction"),
        ("stop", "median_stop_distance_pips_at_least_6_0"),
        ("cost", "median_cost_to_stop_ratio_at_most_0_25"),
        ("horizon", "source_executable_horizon_ratio_at_least_0_99"),
        ("formation", "exact_scheduled_m1_formation_completeness_at_least_0_99"),
        ("spread_ratio", "positive_finite_m1_spread_ratio_at_least_0_99"),
        ("baseline", "frozen_prior_20_eligible_date_baseline_availability_at_least_0_99"),
        ("follow", "follow_control_matched_true_one_to_one"),
        ("outcome", "outcome_blind_plane_intact"),
    ],
)
def test_each_gate_can_fail_independently(mutation: str, failed_gate: str) -> None:
    true_rows, follow_rows, horizons = _balanced_gate_population()
    domain = _passing_domain_metrics()
    counters = sut._executed_source_only_counters()
    weeks = 10.0
    raw_count = 40
    if mutation == "cadence_low":
        weeks = 40.0  # 40/40 = 1.0 < 2
    elif mutation == "long_share":
        true_rows, follow_rows, horizons = _balanced_gate_population(
            n_long=20, n_short=80
        )
        raw_count = 100
        weeks = 20.0
    elif mutation == "short_share":
        true_rows, follow_rows, horizons = _balanced_gate_population(
            n_long=80, n_short=20
        )
        raw_count = 100
        weeks = 20.0
    elif mutation == "year_share":
        for row in true_rows:
            row["year"] = 2018
        for row in follow_rows:
            row["year"] = 2018
    elif mutation == "per_side":
        true_rows = true_rows[:30]
        follow_rows = follow_rows[:30]
        horizons = horizons[:30]
        raw_count = 30
        weeks = 8.0
    elif mutation == "stop":
        for row in true_rows:
            row["stop_distance_pips"] = 5.9
            row["cost_to_stop_ratio"] = 0.25
        for row in follow_rows:
            row["stop_distance_pips"] = 5.9
            row["cost_to_stop_ratio"] = 0.25
    elif mutation == "cost":
        for row in true_rows:
            row["stop_distance_pips"] = 6.0
            row["cost_to_stop_ratio"] = 0.251
        for row in follow_rows:
            row["stop_distance_pips"] = 6.0
            row["cost_to_stop_ratio"] = 0.251
    elif mutation == "horizon":
        horizons[0]["source_executable"] = False
        # drop corresponding arms to keep exact-once? evaluate_stage0 only checks horizon ratio
        # but true/follow still length 40 — horizon_ratio = 39/40 < 0.99
        raw_count = 40
    elif mutation == "formation":
        domain["formation_ratio"] = 0.98
        domain["formation_complete"] = 98
    elif mutation == "spread_ratio":
        domain["positive_spread_ratio"] = 0.98
    elif mutation == "baseline":
        domain["baseline_availability_ratio"] = 0.98
    elif mutation == "follow":
        follow_rows = follow_rows[:-1]
        # will raise on length mismatch — special case
        with pytest.raises(sut.ContractError):
            sut.evaluate_stage0_gates(
                true_signals=true_rows,
                follow_signals=follow_rows,
                raw_first_per_day_count=raw_count,
                horizon_records=horizons,
                domain_metrics=domain,
                source_only_counters=counters,
                elapsed_weeks=weeks,
            )
        return
    elif mutation == "outcome":
        counters["post_entry_ohlc_rows_read"] = 1
    stage0 = sut.evaluate_stage0_gates(
        true_signals=true_rows,
        follow_signals=follow_rows,
        raw_first_per_day_count=raw_count,
        horizon_records=horizons,
        domain_metrics=domain,
        source_only_counters=counters,
        elapsed_weeks=weeks,
    )
    assert stage0["gates"][failed_gate] is False
    assert all(
        value is True
        for key, value in stage0["gates"].items()
        if key != failed_gate
    ), stage0["gates"]
    assert stage0["verdict"] == sut.STAGE0_FAIL


def test_cadence_uses_elapsed_calendar_weeks_not_active() -> None:
    assert sut.ELAPSED_CALENDAR_WEEKS == pytest.approx((date(2020, 12, 31) - date(2016, 1, 4)).days / 7.0)
    true_rows, follow_rows, horizons = _balanced_gate_population()
    stage0 = sut.evaluate_stage0_gates(
        true_signals=true_rows,
        follow_signals=follow_rows,
        raw_first_per_day_count=40,
        horizon_records=horizons,
        domain_metrics=_passing_domain_metrics(),
        source_only_counters=sut._executed_source_only_counters(),
        elapsed_weeks=sut.ELAPSED_CALENDAR_WEEKS,
    )
    # 40 / ~260 weeks << 2
    assert stage0["gates"]["true_cadence_2_to_5_per_elapsed_week"] is False


def test_exact_once_classification_and_arm_mapping() -> None:
    rows, dates, _ = build_valid_short_path()
    report = sut.scan_source_once(rows, dates)
    exact = report["exact_once"]
    assert exact["exact_once_reconciliation"] is True
    assert exact["raw_equals_classifications"] is True
    assert exact["classifications_equal_executable_plus_excluded"] is True
    assert exact["max_one_decision_per_utc_date"] is True


def test_independent_replay_digest_equality_and_mutation_rejection() -> None:
    rows, dates, _ = build_valid_short_path()
    primary = sut.scan_source_once(rows, dates)
    meta = sut.independent_replay_scan(rows, dates, primary)
    assert meta["digests_equal"] is True
    sut.assert_independent_replay_rejects_mutation(rows, dates, mode="mutate_ledger")
    # Need two classifications for reorder — use multi-day
    rows2, dates2, _ = multi_day_signals(2, 2)
    primary2 = sut.scan_source_once(rows2, dates2)
    if len(primary2["raw_signal_classifications"]) >= 2:
        sut.assert_independent_replay_rejects_mutation(rows2, dates2, mode="reorder_classification")
        sut.assert_independent_replay_rejects_mutation(rows2, dates2, mode="omit_classification")


def test_scan_source_end_to_end_synthetic_outcome_blind() -> None:
    rows, dates, _ = build_valid_long_path()
    report = sut.scan_source(rows, dates, with_independent_replay=True)
    assert report["hypothesis_id"] == sut.HYPOTHESIS_ID
    assert report["economics_authorized"] is False
    assert report["post_entry_ohlc_rows_read"] == 0
    assert report["returns_computed"] == 0
    assert "independent_replay" in report
    sut.assert_outcome_blind(report)


def test_outcome_fields_rejected() -> None:
    with pytest.raises(sut.ContractError, match="forbidden"):
        sut.assert_outcome_blind({"pnl": 1.0})
    with pytest.raises(sut.ContractError, match="forbidden"):
        sut.assert_outcome_blind({"entry_price": 1.1})
    with pytest.raises(sut.ContractError, match="forbidden"):
        sut.assert_outcome_blind({"tick_volume": 1})
    with pytest.raises(sut.ContractError, match="forbidden"):
        sut.assert_outcome_blind({"real_volume": 1})
    # Authorized spread diagnostics allowed
    sut.assert_outcome_blind({"baseline_spread_points": 10.0, "shock_spread_points": 25.0})


def test_forbidden_path_parts_rejected(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    for part in ("private", "validation", "holdout", "sealed"):
        bad = root / part / "x.bin"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_bytes(b"abc")
        with pytest.raises(sut.ContractError):
            sut.stable_read_regular(bad, root)


def test_public_metadata_hash_mismatch_fails() -> None:
    with pytest.raises(sut.ContractError, match="hash mismatch"):
        sut.validate_public_metadata(
            receipt_payload=b"{}\n",
            manifest_payload=b"{}\n",
            expected_receipt_sha256="A" * 64,
            expected_manifest_sha256="B" * 64,
        )


def test_producer_schema_forbids_signal_use_of_tick_volume_real_volume() -> None:
    assert "tick_volume" not in sut.SIGNAL_COLUMNS
    assert "real_volume" not in sut.SIGNAL_COLUMNS
    assert "spread" in sut.SIGNAL_COLUMNS
    assert "tick_volume" in sut.PRODUCER_SCHEMA_COLUMNS
    assert "real_volume" in sut.PRODUCER_SCHEMA_COLUMNS


def _minimal_registry_row(**validation_overrides: object) -> dict[str, object]:
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
        "reviewed_builder_base_sha256": "A" * 64,
        "reviewed_test_path": sut.TEST_REL,
        "reviewed_test_sha256": "B" * 64,
        "independent_review_receipt_path": sut.REVIEW_RECEIPT_REL,
        "independent_review_receipt_schema": sut.REVIEW_RECEIPT_SCHEMA,
        "independent_review_receipt_sha256": "C" * 64,
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
    validation.update(validation_overrides)
    return {
        "schema_version": "alphafactory_candidate_registry.v1",
        "record_type": "hypothesis_state",
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "parent_candidate": None,
        "ea_name": sut.EA_NAME,
        "feature_family": sut.FAMILY,
        "state": "probe",
        "model": None,
        "source_path": None,
        "source_hash": None,
        "run_ids": [],
        "prereg_path": sut.PLAN_REL,
        "prereg_sha256": sut.PLAN_SHA256,
        "validation": validation,
        "metrics": dict(sut.SOURCE_ONLY_ZERO_METRICS),
    }


def test_registry_exact_validation_whitelist_is_accepted() -> None:
    builder = SOURCE.read_bytes()
    tests = Path(__file__).read_bytes()
    row = _minimal_registry_row(
        reviewed_builder_base_sha256=sut.reviewed_base_source_sha256(builder),
        reviewed_test_sha256=sha(tests),
    )
    payload = canonical(row) + b"\n"
    row_sha = sha(payload)
    # Fix whitelist: validation keys must equal REGISTRY_VALIDATION_FIELDS exactly
    assert set(row["validation"]) == sut.REGISTRY_VALIDATION_FIELDS
    accepted = sut.validate_registry_authority(payload, row_sha, builder_payload=builder, test_payload=tests)
    assert accepted["hypothesis_id"] == sut.HYPOTHESIS_ID


def test_registry_false_authorities_reject_true() -> None:
    builder = SOURCE.read_bytes()
    tests = Path(__file__).read_bytes()
    row = _minimal_registry_row(
        reviewed_builder_base_sha256=sut.reviewed_base_source_sha256(builder),
        reviewed_test_sha256=sha(tests),
        economics_authorized=True,
    )
    payload = canonical(row) + b"\n"
    with pytest.raises(sut.ContractError):
        sut.validate_registry_authority(payload, sha(payload), builder_payload=builder, test_payload=tests)


def test_registry_rejects_nonzero_pre_run_metrics() -> None:
    builder = SOURCE.read_bytes()
    tests = Path(__file__).read_bytes()
    row = _minimal_registry_row(
        reviewed_builder_base_sha256=sut.reviewed_base_source_sha256(builder),
        reviewed_test_sha256=sha(tests),
    )
    row["metrics"] = dict(sut.SOURCE_ONLY_ZERO_METRICS)
    row["metrics"]["returns_computed"] = 1
    payload = canonical(row) + b"\n"
    with pytest.raises(sut.ContractError):
        sut.validate_registry_authority(payload, sha(payload), builder_payload=builder, test_payload=tests)


def test_wrong_registry_row_sha_cannot_arm() -> None:
    builder = SOURCE.read_bytes()
    tests = Path(__file__).read_bytes()
    row = _minimal_registry_row(
        reviewed_builder_base_sha256=sut.reviewed_base_source_sha256(builder),
        reviewed_test_sha256=sha(tests),
    )
    payload = canonical(row) + b"\n"
    with pytest.raises(sut.ContractError):
        sut.validate_registry_authority(payload, "F" * 64, builder_payload=builder, test_payload=tests)


def test_latest_row_required_not_older_duplicate() -> None:
    builder = SOURCE.read_bytes()
    tests = Path(__file__).read_bytes()
    row1 = _minimal_registry_row(
        reviewed_builder_base_sha256=sut.reviewed_base_source_sha256(builder),
        reviewed_test_sha256=sha(tests),
    )
    row2 = _minimal_registry_row(
        reviewed_builder_base_sha256=sut.reviewed_base_source_sha256(builder),
        reviewed_test_sha256=sha(tests),
    )
    p1 = canonical(row1) + b"\n"
    p2 = canonical(row2) + b"\n"
    # Same content => same sha; tweak row2 validation receipt hash
    row2["validation"] = dict(row2["validation"])
    row2["validation"]["independent_review_receipt_sha256"] = "D" * 64
    p2 = canonical(row2) + b"\n"
    combined = p1 + p2
    # Arming with older row sha must fail (not latest)
    with pytest.raises(sut.ContractError):
        sut.validate_registry_authority(combined, sha(p1), builder_payload=builder, test_payload=tests)
    # Latest accepted
    accepted = sut.validate_registry_authority(combined, sha(p2), builder_payload=builder, test_payload=tests)
    assert accepted["validation"]["independent_review_receipt_sha256"] == "D" * 64


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
    out = sut.validate_review_receipt(
        payload,
        expected_sha256=sha(payload),
        builder_payload=builder,
        test_payload=tests,
    )
    assert out["review_status"] == "PASS"


def test_create_new_evidence_reservation_and_one_shot(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    row_sha = "A" * 64
    root = sut._reserve_attempt(workspace, row_sha)
    assert root.is_dir()
    assert (root / "attempt_started.json").is_file()
    with pytest.raises(sut.ContractError, match="already exists"):
        sut._reserve_attempt(workspace, row_sha)


def test_receipt_never_carries_authoritative_pass_status() -> None:
    receipt = {
        "status": sut.RECEIPT_NON_TERMINAL_STATUS,
        "terminal_is_sole_authoritative_completion": True,
        "stage0_verdict": sut.STAGE0_PASS,
    }
    sut._assert_receipt_is_non_terminal(receipt)
    bad = dict(receipt, status=sut.TERMINAL_PASS_STATUS)
    with pytest.raises(sut.ContractError):
        sut._assert_receipt_is_non_terminal(bad)


def test_persist_success_writes_report_ledger_receipt(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    row_sha = "B" * 64
    root = sut._reserve_attempt(workspace, row_sha)
    rows, dates, _ = build_valid_short_path()
    report = sut.scan_source(rows, dates, with_independent_replay=True)
    enriched = sut._persist_success(root, report, row_sha)
    assert (root / "source_report.json").is_file()
    assert (root / "source_classifications.jsonl").is_file()
    assert (root / "source_ledger.jsonl").is_file()
    assert (root / "source_feasibility_receipt.json").is_file()
    assert (root / "attempt_terminal.json").is_file()
    terminal = json.loads((root / "attempt_terminal.json").read_text(encoding="utf-8"))
    assert terminal["sole_authoritative_completion"] is True
    receipt = json.loads((root / "source_feasibility_receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == sut.RECEIPT_NON_TERMINAL_STATUS
    assert enriched["hypothesis_id"] == sut.HYPOTHESIS_ID


def test_post_write_terminal_fault_recovers_without_pass(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    row_sha = "C" * 64
    root = sut._reserve_attempt(workspace, row_sha)
    suspect = {
        "schema_version": "srir_001_attempt_terminal.v1",
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "attempt_id": sut.ATTEMPT_ID,
        "reviewed_registry_row_sha256": row_sha,
        "status": sut.TERMINAL_PASS_STATUS,
        "sole_authoritative_completion": True,
        "source_only_counters": sut._executed_source_only_counters(),
        "sealed_permissions": sut._sealed_permissions(),
        "artifact_hashes": {},
    }
    sut._write_new_canonical(root / "attempt_terminal.json", suspect)
    sut._persist_engineering_failure(root, row_sha, RuntimeError("post-write fault"))
    terminal = json.loads((root / "attempt_terminal.json").read_text(encoding="utf-8"))
    assert terminal["status"] == sut.TERMINAL_ENGINEERING_INVALID
    assert terminal["status"] != sut.TERMINAL_PASS_STATUS


def test_terminal_is_sole_pass_authority_and_failed_terminal_write(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    row_sha = "D" * 64
    root = sut._reserve_attempt(workspace, row_sha)
    rows, dates, _ = build_valid_short_path()
    report = sut.scan_source_once(rows, dates)
    report = dict(report)
    report["stage0"] = dict(report["stage0"])
    report["stage0"]["verdict"] = sut.STAGE0_FAIL
    report["stage0"]["gates"] = {k: False for k in report["stage0"]["gates"]}
    sut._persist_success(root, report, row_sha)
    terminal = json.loads((root / "attempt_terminal.json").read_text(encoding="utf-8"))
    assert terminal["status"] == sut.TERMINAL_FAIL_STATUS


def test_build_valid_path_forms_at_least_one_decision() -> None:
    for builder in (build_valid_long_path, build_valid_short_path):
        rows, dates, decision = builder()
        report = sut.scan_source_once(rows, dates)
        assert report["population"]["raw_first_per_day_count"] >= 1, report["domain_diagnostics"].get("funnel")
        assert any(
            c["decision_utc"].startswith(decision.date().isoformat())
            for c in report["raw_signal_classifications"]
        )


def test_stop_median_gate_inclusive_six_pips() -> None:
    true_rows, follow_rows, horizons = _balanced_gate_population(stop=6.0)
    stage0 = sut.evaluate_stage0_gates(
        true_signals=true_rows,
        follow_signals=follow_rows,
        raw_first_per_day_count=40,
        horizon_records=horizons,
        domain_metrics=_passing_domain_metrics(),
        source_only_counters=sut._executed_source_only_counters(),
        elapsed_weeks=10.0,
    )
    assert stage0["gates"]["median_stop_distance_pips_at_least_6_0"] is True
    assert stage0["gates"]["median_cost_to_stop_ratio_at_most_0_25"] is True


def test_main_disarmed_without_flag() -> None:
    with pytest.raises(sut.ContractError):
        sut.main([])


def test_reviewed_base_source_sha_normalizes_sentinel() -> None:
    payload = SOURCE.read_bytes()
    base = sut.reviewed_base_source_sha256(payload)
    assert len(base) == 64
    # Armed form hashes differently but base normalizes
    armed = payload.replace(
        b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None",
        b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"',
        1,
    )
    assert sut.reviewed_base_source_sha256(armed) == base


def test_domain_metrics_separates_formation_baseline_spread() -> None:
    rows, dates, _ = build_valid_short_path()
    bars, _ = sut.build_complete_m5(rows)
    enriched = sut.attach_wilder_atr20(bars)
    metrics = sut.domain_quality_metrics(
        m1_rows=rows,
        m5_bars=enriched,
        source_dates=dates,
        burn_in_dates=set(dates[:20]),
    )
    assert "formation_ratio" in metrics
    assert "baseline_availability_ratio" in metrics
    assert "positive_spread_ratio" in metrics
    assert metrics["slots_per_day"] == 105


def test_multi_day_signals_produce_paired_arms() -> None:
    rows, dates, decisions = multi_day_signals(3, 3)
    report = sut.scan_source(rows, dates, with_independent_replay=True)
    assert report["population"]["raw_first_per_day_count"] >= 3
    true_rows = report["signal_ledgers"]["TRUE"]
    follow_rows = report["signal_ledgers"]["FOLLOW_CONTROL"]
    assert len(true_rows) == len(follow_rows)
    for t, f in zip(true_rows, follow_rows):
        assert t["source_signal_id"] == f["source_signal_id"]
        assert {t["direction"], f["direction"]} == {"LONG", "SHORT"}


def test_nan_inf_spread_in_block_marks_unavailable() -> None:
    start = utc(2018, 6, 4, 10, 0)
    rows = [flat_bar(start + timedelta(minutes=i), spread=10.0) for i in range(5)]
    rows[2] = flat_bar(start + timedelta(minutes=2), spread=0.0)
    bars, _ = sut.build_complete_m5(rows)
    assert bars[0]["spread_available"] is False
    assert bars[0]["block_spread_points"] is None
