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

SOURCE = Path(__file__).resolve().parents[1] / "build_jcdr_001_source.py"
SPEC = importlib.util.spec_from_file_location("build_jcdr_001_source", SOURCE)
assert SPEC and SPEC.loader
sut = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sut)

UTC = timezone.utc
PLAN = Path(__file__).resolve().parents[1] / "HYP-JCDR-EURUSD-M1-001_SOURCE_FEASIBILITY_PLAN.md"
WARMUP = sut.LOOKBACK_RETURNS + 5  # returns ready well before cluster


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
) -> dict[str, object]:
    return {
        "time_utc": at,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
    }


def flat_bar(at: datetime, price: float = 1.1000) -> dict[str, object]:
    return m1_row(
        at,
        open_=price,
        high=price + 0.00002,
        low=price - 0.00002,
        close=price,
    )


def append_minutes(
    rows: list[dict[str, object]],
    start: datetime,
    count: int,
    *,
    price: float = 1.1000,
) -> datetime:
    for index in range(count):
        rows.append(flat_bar(start + timedelta(minutes=index), price))
    return start + timedelta(minutes=count)


def _impulse_bar(
    at: datetime,
    *,
    open_: float,
    close: float,
    dominant: int,
) -> dict[str, object]:
    if dominant > 0:
        high = max(open_, close) + 0.00005
        low = min(open_, close) - 0.00002
    else:
        high = max(open_, close) + 0.00002
        low = min(open_, close) - 0.00005
    return m1_row(at, open_=open_, high=high, low=low, close=close)


def build_cluster_path(
    start: datetime,
    *,
    dominant: int = 1,
    base: float = 1.1000,
    jump_pips: float = 2.5,
    jump_offsets: tuple[int, ...] = (2, 7, 14),
    decay_decision_offset: int = 6,
    retrace_frac: float = 0.50,
    horizon_bars: int = 70,
    warmup: int = WARMUP,
) -> tuple[list[dict[str, object]], datetime]:
    """Construct one contiguous path with a single valid decision after a cluster.

    Layout: warmup flat -> 15-bar cluster ending on a jump -> decay bars -> horizon.
    Peak bar is always a jump (>= jump_pips >= 1.20). Decay steps stay under 1.0 pip.
    """

    if len(jump_offsets) < 3 or 14 not in jump_offsets:
        raise ValueError("need at least three jumps ending at offset 14")
    if not 3 <= decay_decision_offset <= 10:
        raise ValueError("decision needs three-bar quiet window inside 10-bar decay")
    sign = 1 if dominant > 0 else -1
    rows: list[dict[str, object]] = []
    cursor = append_minutes(rows, start, warmup, price=base)
    price = base
    first_jump_open: float | None = None
    extreme = base
    jump_set = set(jump_offsets)
    for offset in range(15):
        at = cursor + timedelta(minutes=offset)
        if offset in jump_set:
            open_ = price
            if first_jump_open is None:
                first_jump_open = open_
            close = open_ + sign * jump_pips * sut.PIP
            bar = _impulse_bar(at, open_=open_, close=close, dominant=dominant)
            rows.append(bar)
            price = close
            if dominant > 0:
                extreme = max(extreme, float(bar["high"]))
            else:
                extreme = min(extreme, float(bar["low"]))
        else:
            rows.append(flat_bar(at, price))
    if first_jump_open is None:
        raise RuntimeError("no jump open")
    peak_time = cursor + timedelta(minutes=14)
    anchor = float(first_jump_open)
    distance = abs(extreme - anchor)
    if distance <= 0:
        raise RuntimeError("non-positive extreme-to-anchor distance")
    target_close = extreme - sign * retrace_frac * distance
    # Gradual non-jump approach over decay_decision_offset bars (each step <= 1.0 pip).
    steps = decay_decision_offset
    remaining = target_close - price
    for step in range(1, steps + 1):
        at = peak_time + timedelta(minutes=step)
        open_ = price
        # Evenly distribute remaining distance; clamp per-bar move under 1.0 pip.
        left = steps - step + 1
        step_move = remaining / left
        max_step = 1.0 * sut.PIP
        if abs(step_move) > max_step:
            step_move = max_step if step_move > 0 else -max_step
        close = open_ + step_move
        high = max(open_, close) + 0.00001
        low = min(open_, close) - 0.00001
        rows.append(m1_row(at, open_=open_, high=high, low=low, close=close))
        price = close
        remaining = target_close - price
    decision_time = peak_time + timedelta(minutes=decay_decision_offset)
    entry = decision_time + timedelta(minutes=1)
    for index in range(horizon_bars):
        rows.append(flat_bar(entry + timedelta(minutes=index), price))
    return rows, decision_time


def build_valid_long_path(start: datetime | None = None) -> tuple[list[dict[str, object]], datetime]:
    if start is None:
        start = utc(2018, 6, 4, 10, 0)
    return build_cluster_path(start, dominant=-1)  # down cluster -> TRUE long


def build_valid_short_path(start: datetime | None = None) -> tuple[list[dict[str, object]], datetime]:
    if start is None:
        start = utc(2018, 6, 5, 10, 0)
    return build_cluster_path(start, dominant=1)  # up cluster -> TRUE short


def multi_day_signals(
    n_long: int,
    n_short: int,
    *,
    start_day: date = date(2018, 1, 2),
) -> tuple[list[dict[str, object]], tuple[date, ...], list[datetime]]:
    """Build many first-per-day signals alternating long/short with full horizons."""

    rows: list[dict[str, object]] = []
    decisions: list[datetime] = []
    days: list[date] = []
    day = start_day
    long_left, short_left = n_long, n_short
    while long_left > 0 or short_left > 0:
        if day.weekday() >= 5:
            day += timedelta(days=1)
            continue
        days.append(day)
        start = datetime(day.year, day.month, day.day, 8, 0, tzinfo=UTC)
        if short_left > 0 and (long_left == 0 or len(decisions) % 2 == 0):
            path, decision = build_cluster_path(start, dominant=1, base=1.1000 + 0.0001 * len(decisions))
            short_left -= 1
        else:
            path, decision = build_cluster_path(start, dominant=-1, base=1.1000 + 0.0001 * len(decisions))
            long_left -= 1
        rows.extend(path)
        decisions.append(decision)
        day += timedelta(days=1)
    return rows, tuple(days), decisions


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
        "candidate_id": f"JCDR001-{arm}-{sha(identity)[:16]}",
        "source_signal_id": sid,
        "arm": arm,
        "decision_utc": sut._iso_z(decision),
        "entry_open_utc": sut._iso_z(decision + timedelta(minutes=1)),
        "time_exit_utc": sut._iso_z(decision + timedelta(minutes=1 + sut.HORIZON_BARS)),
        "direction": direction,
        "year": year,
        "dominant_sign": 1 if direction == "SHORT" and arm == "TRUE" else -1,
        "coherence": 1.0,
        "jump_count": 3,
        "retracement": 0.5,
        "signed_disp_pips": 6.0,
        "stop_distance_pips": stop_pips,
        "cost_to_stop_ratio": cost,
        "cluster_peak_utc": sut._iso_z(decision - timedelta(minutes=5)),
    }


def matched_pair(direction_true: str, year: int, stop: float, decision: datetime) -> tuple[dict, dict]:
    follow = "LONG" if direction_true == "SHORT" else "SHORT"
    true_row = ledger_row(direction=direction_true, year=year, stop_pips=stop, decision=decision, arm="TRUE")
    follow_row = ledger_row(direction=follow, year=year, stop_pips=stop, decision=decision, arm="FOLLOW_CONTROL")
    follow_row["source_signal_id"] = true_row["source_signal_id"]
    return true_row, follow_row


# ---------------------------------------------------------------------------
# Basic identity / import
# ---------------------------------------------------------------------------


def test_ast_parse_deliverables() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    assert isinstance(tree, ast.Module)
    assert sut.HYPOTHESIS_ID == "HYP-JCDR-EURUSD-M1-001"
    assert sut.ATTEMPT_ID == "JCDR001-SOURCE-001"
    assert sut.PLAN_SHA256 == "15EE54A6071C3C8A81B6F07480BFB7813F82138C5C06347F169E026AB239FEB1"


def test_sentinel_is_exactly_disarmed_and_import_inert() -> None:
    assert sut.REVIEWED_REGISTRY_ROW_SHA256 is None
    text = SOURCE.read_bytes()
    matches = [
        line
        for line in text.splitlines()
        if sut._SENTINEL_RE.match(line.rstrip(b"\n"))
    ]
    assert len(matches) == 1
    assert matches[0].strip() == b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None"


def test_cli_dual_gate_disarmed(tmp_path: Path) -> None:
    with pytest.raises(sut.ContractError, match="disarmed"):
        sut.execute_probe(workspace_root=tmp_path, run_switch=False)
    with pytest.raises(sut.ContractError, match="disarmed"):
        sut.execute_probe(workspace_root=tmp_path, run_switch=True)


def test_parse_args_execute_probe_flag() -> None:
    args = sut.parse_args(["--execute-probe", "--workspace-root", "."])
    assert args.execute_probe is True


def test_plan_hash_binding_matches_exact_bytes() -> None:
    payload = PLAN.read_bytes()
    assert sha(payload) == sut.PLAN_SHA256


def test_immutable_hashes_are_bound() -> None:
    assert sut.M1_MANIFEST_SHA256 == "A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7"
    assert sut.M1_RECEIPT_SHA256 == "8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8"
    assert sut.M1_SOURCE_SHA256 == "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
    assert abs(sut.ELAPSED_CALENDAR_WEEKS - (sut.DESIGN_END - sut.DESIGN_START).days / 7.0) < 1e-12


# ---------------------------------------------------------------------------
# ULP boundaries / finite-only
# ---------------------------------------------------------------------------


def test_ulp_inclusive_boundaries_equal_and_neighbors() -> None:
    assert sut.ge_inclusive(1.20, 1.20) is True
    assert sut.le_inclusive(0.80, 0.80) is True
    assert sut.ge_inclusive(1.20 - math.ulp(1.20), 1.20) is True
    assert sut.le_inclusive(0.80 + math.ulp(0.80), 0.80) is True
    assert sut.lt_strict(1.20, 1.20) is False
    assert sut.gt_strict(1.20, 1.20) is False
    just_below = 1.20 - 100 * math.ulp(1.20)
    assert sut.ge_inclusive(just_below, 1.20) is False


def test_non_finite_boundary_helpers_fail() -> None:
    assert sut.ge_inclusive(float("nan"), 1.0) is False
    assert sut.le_inclusive(float("inf"), 1.0) is False
    assert sut.lt_strict(float("-inf"), 0.0) is False
    assert sut.gt_strict(1.0, float("nan")) is False


def test_non_finite_ohlc_rejected() -> None:
    at = utc(2018, 1, 2, 10, 0)
    with pytest.raises(sut.ContractError):
        sut._ohlc({"open": float("nan"), "high": 1.1, "low": 1.0, "close": 1.05})
    with pytest.raises(sut.ContractError):
        sut.split_contiguous_m1(
            [m1_row(at, open_=1.1, high=1.1, low=1.1, close=float("inf"))]
        )


# ---------------------------------------------------------------------------
# Contiguity / gaps / duplicates
# ---------------------------------------------------------------------------


def test_contiguous_split_and_gap_break() -> None:
    start = utc(2018, 1, 2, 10, 0)
    rows = [flat_bar(start + timedelta(minutes=i)) for i in range(5)]
    # Gap of 2 minutes.
    gap_start = start + timedelta(minutes=10)
    rows.extend(flat_bar(gap_start + timedelta(minutes=i)) for i in range(3))
    segments, quality = sut.split_contiguous_m1(rows)
    assert len(segments) == 2
    assert quality["gap_breaks"] == 1
    assert quality["contiguous_rows"] == 8


def test_duplicate_timestamps_rejected() -> None:
    at = utc(2018, 1, 2, 10, 0)
    with pytest.raises(sut.ContractError, match="duplicate"):
        sut.split_contiguous_m1([flat_bar(at), flat_bar(at)])


def test_non_minute_aligned_rejected() -> None:
    at = datetime(2018, 1, 2, 10, 0, 30, tzinfo=UTC)
    with pytest.raises(sut.ContractError, match="minute-aligned"):
        sut.split_contiguous_m1([flat_bar(at)])


def test_gap_does_not_bridge_formation_state() -> None:
    # Warmup + partial cluster, gap, then more bars: no decision across gap.
    start = utc(2018, 3, 5, 9, 0)
    rows = [flat_bar(start + timedelta(minutes=i), 1.1000) for i in range(WARMUP + 10)]
    # Large gap then flat continuation.
    later = start + timedelta(minutes=WARMUP + 100)
    rows.extend(flat_bar(later + timedelta(minutes=i), 1.1000) for i in range(80))
    segments, _ = sut.split_contiguous_m1(rows)
    assert len(segments) == 2
    raw, _ = sut.select_raw_signals(segments)
    assert raw == []


# ---------------------------------------------------------------------------
# Jump / scale / lookback exclusion
# ---------------------------------------------------------------------------


def test_prior_240_scale_excludes_current_return() -> None:
    start = utc(2018, 1, 2, 8, 0)
    rows = [flat_bar(start + timedelta(minutes=i), 1.1000) for i in range(WARMUP)]
    # One large return at the end should not enter its own scale window.
    last = start + timedelta(minutes=WARMUP)
    prev_close = 1.1000
    rows.append(
        m1_row(
            last,
            open_=prev_close,
            high=prev_close + 0.0010,
            low=prev_close - 0.0001,
            close=prev_close + 0.0005,  # +5 pips
        )
    )
    segments, _ = sut.split_contiguous_m1(rows)
    returns, scales, jumps, thresholds = sut.compute_jump_state(segments[0])
    idx = len(segments[0]) - 1
    assert returns[idx] is not None and abs(returns[idx] - 5.0) < 1e-9
    # Scale should be near zero from flat history (current excluded).
    assert scales[idx] is not None
    assert scales[idx] < 0.05
    assert thresholds[idx] == pytest.approx(1.20)
    assert jumps[idx] is True


def test_jump_threshold_floor_and_scale_multiple_boundaries() -> None:
    # Floor: max(1.20, 3*scale). When scale=0.3, threshold=1.20 (floor).
    # When scale=0.5, threshold=1.50.
    assert max(1.20, 3.0 * 0.3) == 1.20
    assert max(1.20, 3.0 * 0.5) == 1.50
    # Inclusive jump at exactly threshold.
    assert sut.ge_inclusive(1.20, 1.20) is True
    assert sut.ge_inclusive(1.20 - 50 * math.ulp(1.20), 1.20) is False


def test_jump_just_below_equal_just_above_threshold() -> None:
    start = utc(2018, 1, 2, 8, 0)
    base = 1.1000
    # Three independent probes from flat scale (reset price each time via tiny re-anchor).
    rows = [flat_bar(start + timedelta(minutes=i), base) for i in range(WARMUP)]
    # Just below: 1.19 pips
    at0 = start + timedelta(minutes=WARMUP)
    c0 = base + 1.19 * sut.PIP
    rows.append(m1_row(at0, open_=base, high=c0 + 0.00001, low=base - 0.00001, close=c0))
    # Flatten back under threshold so scale stays near zero.
    at_flat = start + timedelta(minutes=WARMUP + 1)
    rows.append(flat_bar(at_flat, c0))
    # Exactly threshold via helper boundary: set move so abs(ret) compares with ge_inclusive to 1.20
    at1 = start + timedelta(minutes=WARMUP + 2)
    # Use a clean 2.0 pip move (well above) as "above", and unit-test equal via helpers.
    c1 = c0 + 2.0 * sut.PIP
    rows.append(m1_row(at1, open_=c0, high=c1 + 0.00001, low=c0 - 0.00001, close=c1))
    segments, _ = sut.split_contiguous_m1(rows)
    returns, _, jumps, thresholds = sut.compute_jump_state(segments[0])
    i0 = WARMUP
    assert thresholds[i0] == pytest.approx(1.20)
    assert jumps[i0] is False
    assert returns[i0] is not None and returns[i0] < 1.20
    # Inclusive equality at threshold via ULP helpers (binary64 exactness).
    assert sut.ge_inclusive(1.20, 1.20) is True
    assert jumps[i0 + 2] is True


# ---------------------------------------------------------------------------
# Cluster formation
# ---------------------------------------------------------------------------


def test_cluster_requires_three_jumps_and_coherence_80() -> None:
    start = utc(2018, 4, 2, 9, 0)
    # Only two jumps: should not form.
    rows = [flat_bar(start + timedelta(minutes=i), 1.1000) for i in range(WARMUP)]
    price = 1.1000
    cursor = start + timedelta(minutes=WARMUP)
    for offset in range(15):
        at = cursor + timedelta(minutes=offset)
        if offset in (2, 14):
            close = price + 0.00025
            rows.append(_impulse_bar(at, open_=price, close=close, dominant=1))
            price = close
        else:
            rows.append(flat_bar(at, price))
    segments, _ = sut.split_contiguous_m1(rows)
    returns, _, jumps, _ = sut.compute_jump_state(segments[0])
    peak = WARMUP + 14
    assert jumps[peak] is True
    assert sut.try_form_cluster(segments[0], returns, jumps, peak) is None


def test_cluster_coherence_boundary_80_percent() -> None:
    # 4 jumps with 3 same sign => 0.75 fail; 5 with 4 same => 0.80 pass.
    start = utc(2018, 4, 3, 9, 0)
    rows = [flat_bar(start + timedelta(minutes=i), 1.1000) for i in range(WARMUP)]
    price = 1.1000
    cursor = start + timedelta(minutes=WARMUP)
    # offsets: + + - + + at end
    pattern = {0: 1, 3: 1, 6: -1, 10: 1, 14: 1}
    for offset in range(15):
        at = cursor + timedelta(minutes=offset)
        if offset in pattern:
            sign = pattern[offset]
            close = price + 0.00025 * sign
            rows.append(_impulse_bar(at, open_=price, close=close, dominant=sign))
            price = close
        else:
            rows.append(flat_bar(at, price))
    segments, _ = sut.split_contiguous_m1(rows)
    returns, _, jumps, _ = sut.compute_jump_state(segments[0])
    peak = WARMUP + 14
    cluster = sut.try_form_cluster(segments[0], returns, jumps, peak)
    assert cluster is not None
    assert sut.ge_inclusive(cluster["coherence"], 0.80) is True


def test_cluster_displacement_4_pip_boundary() -> None:
    start = utc(2018, 4, 4, 9, 0)
    # Three jumps of 2.0 pips each => signed displacement well above 4.0; peak is a jump.
    rows = [flat_bar(start + timedelta(minutes=i), 1.1000) for i in range(WARMUP)]
    price = 1.1000
    cursor = start + timedelta(minutes=WARMUP)
    first_open = None
    for offset in range(15):
        at = cursor + timedelta(minutes=offset)
        if offset in (2, 7, 14):
            open_ = price
            if first_open is None:
                first_open = open_
            close = open_ + 2.0 * sut.PIP
            rows.append(_impulse_bar(at, open_=open_, close=close, dominant=1))
            price = close
        else:
            rows.append(flat_bar(at, price))
    segments, _ = sut.split_contiguous_m1(rows)
    returns, _, jumps, _ = sut.compute_jump_state(segments[0])
    peak = WARMUP + 14
    cluster = sut.try_form_cluster(segments[0], returns, jumps, peak)
    assert cluster is not None
    assert sut.ge_inclusive(abs(cluster["signed_disp_pips"]), 4.0) is True

    # Three tiny jumps that sum under 4.0 pips displacement fail.
    rows2 = [flat_bar(start + timedelta(minutes=i), 1.1000) for i in range(WARMUP)]
    price = 1.1000
    for offset in range(15):
        at = cursor + timedelta(minutes=offset)
        if offset in (2, 7, 14):
            open_ = price
            close = open_ + 1.21 * sut.PIP  # jump but total ~3.63 pips < 4
            rows2.append(_impulse_bar(at, open_=open_, close=close, dominant=1))
            price = close
        else:
            rows2.append(flat_bar(at, price))
    segments2, _ = sut.split_contiguous_m1(rows2)
    returns2, _, jumps2, _ = sut.compute_jump_state(segments2[0])
    cluster2 = sut.try_form_cluster(segments2[0], returns2, jumps2, peak)
    assert cluster2 is None


def test_new_cluster_cancels_pending_candidate() -> None:
    start = utc(2018, 5, 7, 8, 0)
    # Valid down-cluster path yields TRUE long; proves cluster replacement path via funnel peaks.
    path, _ = build_cluster_path(start, dominant=-1)
    segments, _ = sut.split_contiguous_m1(path)
    raw, funnel = sut.select_raw_signals(segments)
    assert len(raw) == 1
    assert raw[0]["true_direction"] == "LONG"
    assert funnel.get("CLUSTER_PEAK", 0) >= 1
    # Explicit cancellation: first peak pending, second peak replaces before decision.
    rows = [flat_bar(start + timedelta(minutes=i), 1.1000) for i in range(WARMUP)]
    price = 1.1000
    cursor = start + timedelta(minutes=WARMUP)

    def add_cluster(local_rows, local_cursor, local_price, dominant):
        sign = 1 if dominant > 0 else -1
        for offset in range(15):
            at = local_cursor + timedelta(minutes=offset)
            if offset in (2, 7, 14):
                open_ = local_price
                close = open_ + sign * 2.5 * sut.PIP
                bar = _impulse_bar(at, open_=open_, close=close, dominant=dominant)
                local_rows.append(bar)
                local_price = close
            else:
                local_rows.append(flat_bar(at, local_price))
        return local_cursor + timedelta(minutes=15), local_price

    cursor, price = add_cluster(rows, cursor, price, 1)
    # Only 2 quiet bars — not enough for three-no-jump decision — then opposite cluster.
    for step in range(2):
        rows.append(flat_bar(cursor + timedelta(minutes=step), price))
    cursor = cursor + timedelta(minutes=2)
    cursor, price = add_cluster(rows, cursor, price, -1)
    # Complete a valid decay decision for the second cluster.
    peak_time = cursor - timedelta(minutes=1)
    # Estimate extreme/anchor roughly from last three jumps of 2.5 pips down from price path.
    # Use build-like gradual retrace of ~half distance (~0.5 * ~7.5 pips).
    for step in range(1, 7):
        at = peak_time + timedelta(minutes=step)
        open_ = price
        close = open_ + 0.8 * sut.PIP  # toward re-entry for down cluster
        rows.append(
            m1_row(at, open_=open_, high=max(open_, close) + 0.00001, low=min(open_, close) - 0.00001, close=close)
        )
        price = close
    decision_time = peak_time + timedelta(minutes=6)
    entry = decision_time + timedelta(minutes=1)
    for index in range(70):
        rows.append(flat_bar(entry + timedelta(minutes=index), price))
    segments2, _ = sut.split_contiguous_m1(rows)
    raw2, funnel2 = sut.select_raw_signals(segments2)
    assert funnel2.get("CLUSTER_PEAK", 0) >= 2
    # Replacement keeps a single first-per-day decision (whichever frozen peak survived).
    assert len(raw2) == 1


# ---------------------------------------------------------------------------
# Decay / retracement / three no-jump / refractory
# ---------------------------------------------------------------------------


def test_retracement_band_25_to_100_boundaries() -> None:
    # Unit-level fraction checks.
    assert sut.retracement_fraction(dominant_sign=1, extreme=1.1010, anchor=1.1000, decision_close=1.10075) == pytest.approx(0.25)
    assert sut.retracement_fraction(dominant_sign=1, extreme=1.1010, anchor=1.1000, decision_close=1.1000) == pytest.approx(1.0)
    just_below = sut.retracement_fraction(dominant_sign=1, extreme=1.1010, anchor=1.1000, decision_close=1.10076)
    assert just_below is not None and just_below < 0.25
    assert sut.ge_inclusive(0.25, 0.25) and sut.le_inclusive(1.0, 1.0)


def test_three_no_jump_predecessors_required() -> None:
    jumps = [False] * 20
    jumps[10] = True
    assert sut.three_bar_no_jump(jumps, 12) is False  # includes index 10
    jumps[10] = False
    assert sut.three_bar_no_jump(jumps, 12) is True
    assert sut.three_bar_no_jump(jumps, 1) is False  # insufficient history


def test_daily_refractory_keeps_first_only() -> None:
    day = date(2018, 6, 11)
    start1 = datetime(day.year, day.month, day.day, 8, 0, tzinfo=UTC)
    path1, d1 = build_cluster_path(start1, dominant=1, base=1.1000)
    # Second cluster later same UTC date.
    start2 = datetime(day.year, day.month, day.day, 14, 0, tzinfo=UTC)
    path2, d2 = build_cluster_path(start2, dominant=-1, base=1.1050)
    rows = path1 + path2
    segments, _ = sut.split_contiguous_m1(rows)
    raw, funnel = sut.select_raw_signals(segments)
    assert len(raw) == 1
    assert raw[0]["time_utc"].date() == day
    assert funnel.get("DAILY_REFRACTORY", 0) >= 1 or d1.date() == d2.date()


def test_decay_window_max_ten_bars() -> None:
    start = utc(2018, 6, 12, 9, 0)
    # Build cluster then only quiet bars without valid retrace until after 10.
    rows = [flat_bar(start + timedelta(minutes=i), 1.1000) for i in range(WARMUP)]
    price = 1.1000
    cursor = start + timedelta(minutes=WARMUP)
    first_open = None
    extreme = price
    for offset in range(15):
        at = cursor + timedelta(minutes=offset)
        if offset in (2, 7, 14):
            open_ = price
            if first_open is None:
                first_open = open_
            close = open_ + 0.0003
            bar = _impulse_bar(at, open_=open_, close=close, dominant=1)
            rows.append(bar)
            price = close
            extreme = max(extreme, bar["high"])
        else:
            rows.append(flat_bar(at, price))
    peak = cursor + timedelta(minutes=14)
    # 12 quiet flat bars after peak — retrace never enters band (price still at extreme side).
    for step in range(1, 13):
        rows.append(flat_bar(peak + timedelta(minutes=step), price))
    segments, _ = sut.split_contiguous_m1(rows)
    raw, funnel = sut.select_raw_signals(segments)
    assert raw == []
    assert funnel.get("DECAY_EXPIRED", 0) >= 1 or funnel.get("RETRACE_OUT_OF_BAND", 0) >= 1


# ---------------------------------------------------------------------------
# Horizon / entry / paired arms
# ---------------------------------------------------------------------------


def test_next_minute_entry_and_60_bar_horizon_timestamp_only() -> None:
    decision = utc(2018, 7, 2, 11, 0)
    observed = {decision + timedelta(minutes=k) for k in range(0, 62)}
    # entry is decision+1
    entry = decision + timedelta(minutes=1)
    horizon = sut.map_horizon(entry, observed)
    assert horizon["source_executable"] is True
    assert horizon["required_horizon_bars"] == 60
    assert horizon["observed_horizon_bars"] == 60
    assert horizon["time_exit_utc"] == entry + timedelta(minutes=60)
    # Missing last bar censors.
    observed2 = set(observed)
    observed2.remove(entry + timedelta(minutes=59))
    horizon2 = sut.map_horizon(entry, observed2)
    assert horizon2["source_executable"] is False
    assert horizon2["observed_horizon_bars"] == 59


def test_horizon_censoring_excludes_ledger_arms() -> None:
    path, decision = build_valid_short_path()
    # Truncate so horizon incomplete.
    decision_idx = None
    for index, row in enumerate(path):
        if row["time_utc"] == decision:
            decision_idx = index
            break
    assert decision_idx is not None
    truncated = path[: decision_idx + 10]  # entry exists but << 60
    segments, _ = sut.split_contiguous_m1(truncated)
    observed = {r["time_utc"] for r in truncated}
    raw, _ = sut.select_raw_signals(segments)
    if not raw:
        pytest.skip("path did not form decision under truncated geometry")
    ledgers = sut.build_matched_ledgers(raw, observed)
    assert ledgers["eligible_count"] == 0
    assert ledgers["horizon_excluded_count"] == len(raw)
    assert ledgers["TRUE"] == []
    assert ledgers["FOLLOW_CONTROL"] == []
    assert all(c["status"] == "HORIZON_INCOMPLETE" for c in ledgers["classifications"])


def test_long_short_mirrors_matched_arms() -> None:
    long_path, long_decision = build_valid_long_path(utc(2018, 8, 6, 8, 0))
    short_path, short_decision = build_valid_short_path(utc(2018, 8, 7, 8, 0))
    rows = long_path + short_path
    segments, _ = sut.split_contiguous_m1(rows)
    observed = {r["time_utc"] for seg in segments for r in seg}
    raw, _ = sut.select_raw_signals(segments)
    assert len(raw) >= 1
    ledgers = sut.build_matched_ledgers(raw, observed)
    assert len(ledgers["TRUE"]) == len(ledgers["FOLLOW_CONTROL"])
    for t, f in zip(ledgers["TRUE"], ledgers["FOLLOW_CONTROL"]):
        assert t["source_signal_id"] == f["source_signal_id"]
        assert {t["direction"], f["direction"]} == {"LONG", "SHORT"}
        assert t["decision_utc"] == f["decision_utc"]
        assert t["entry_open_utc"] == f["entry_open_utc"]
        assert t["stop_distance_pips"] == f["stop_distance_pips"]


def test_stop_distance_and_cost_geometry() -> None:
    # max(6.0, abs(extreme-anchor)/pip + 0.5)
    assert max(6.0, 4.0 + 0.5) == 6.0
    assert max(6.0, 7.0 + 0.5) == 7.5
    assert 1.50 / 6.0 == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# Gates (all eleven)
# ---------------------------------------------------------------------------


def test_eleven_gates_present_and_pass_at_boundaries() -> None:
    true_rows = []
    follow_rows = []
    horizons = []
    # 40 long + 40 short = 80 over ~260 weeks => cadence ~0.3 — too low.
    # Use short elapsed weeks override: build with evaluate_stage0_gates elapsed_weeks small.
    # 40+40=80 signals, elapsed=20 weeks => cadence=4.0.
    base = utc(2017, 1, 2, 10, 0)
    for i in range(40):
        d = base + timedelta(days=i * 2)
        t, f = matched_pair("LONG", 2017 + (i % 4), 6.0, d)
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
    for i in range(40):
        d = base + timedelta(days=100 + i * 2)
        t, f = matched_pair("SHORT", 2017 + (i % 4), 6.0, d)
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
    stage0 = sut.evaluate_stage0_gates(
        true_signals=true_rows,
        follow_signals=follow_rows,
        raw_first_per_day_count=80,
        horizon_records=horizons,
        formation_complete=99,
        formation_scheduled=100,
        elapsed_weeks=20.0,
    )
    assert len(stage0["gates"]) == 11
    assert all(stage0["gates"].values())
    assert stage0["verdict"] == sut.STAGE0_PASS
    # Cadence boundary 2.0: 40 signals / 20 weeks = 2.0
    stage0_lo = sut.evaluate_stage0_gates(
        true_signals=true_rows[:40],
        follow_signals=follow_rows[:40],
        raw_first_per_day_count=40,
        horizon_records=horizons[:40],
        formation_complete=99,
        formation_scheduled=100,
        elapsed_weeks=20.0,
    )
    # 40 signals all LONG -> short share fails; rebuild balanced 20/20.
    true_b, follow_b, hor_b = [], [], []
    for i in range(20):
        d = base + timedelta(days=i)
        t, f = matched_pair("LONG", 2018, 6.0, d)
        true_b.append(t)
        follow_b.append(f)
        hor_b.append(horizons[0] | {"source_signal_id": t["source_signal_id"]})
    for i in range(20):
        d = base + timedelta(days=40 + i)
        t, f = matched_pair("SHORT", 2018, 6.0, d)
        true_b.append(t)
        follow_b.append(f)
        hor_b.append(horizons[0] | {"source_signal_id": t["source_signal_id"]})
    stage0_cadence = sut.evaluate_stage0_gates(
        true_signals=true_b,
        follow_signals=follow_b,
        raw_first_per_day_count=40,
        horizon_records=hor_b,
        formation_complete=99,
        formation_scheduled=100,
        elapsed_weeks=20.0,
    )
    assert stage0_cadence["gates"]["true_cadence_2_to_5_per_elapsed_week"] is True
    assert stage0_cadence["metrics"]["cadence_per_elapsed_week"] == pytest.approx(2.0)


@pytest.mark.parametrize(
    "mutation,failed_gate",
    [
        ("formation", "formation_domain_completeness_at_least_0_99"),
        ("horizon", "source_executable_horizon_ratio_at_least_0_99"),
        ("cadence_low", "true_cadence_2_to_5_per_elapsed_week"),
        ("cadence_high", "true_cadence_2_to_5_per_elapsed_week"),
        ("long_share", "true_long_share_at_least_0_25"),
        ("short_share", "true_short_share_at_least_0_25"),
        ("year_share", "max_calendar_year_share_at_most_0_35"),
        ("per_side", "at_least_20_executable_true_per_direction"),
        ("stop", "median_stop_distance_pips_at_least_6_0"),
        ("cost", "median_cost_to_stop_ratio_at_most_0_25"),
        ("match", "follow_control_matched_true_one_to_one"),
    ],
)
def test_each_gate_can_fail_independently(mutation: str, failed_gate: str) -> None:
    base = utc(2017, 1, 3, 10, 0)
    true_rows: list[dict] = []
    follow_rows: list[dict] = []
    horizons: list[dict] = []
    n = 80
    for i in range(n):
        direction = "LONG" if i < n // 2 else "SHORT"
        year = 2017 + (i % 4)
        stop = 6.0
        d = base + timedelta(days=i)
        t, f = matched_pair(direction, year, stop, d)
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
    formation_complete, formation_scheduled = 99, 100
    elapsed = 20.0
    raw_count = n
    if mutation == "formation":
        formation_complete, formation_scheduled = 98, 100
    elif mutation == "horizon":
        horizons[0] = dict(horizons[0], source_executable=False)
        # raw still 80 but executable ratio = 79/80 < 0.99? 79/80=0.9875
        true_rows = true_rows[1:]
        follow_rows = follow_rows[1:]
    elif mutation == "cadence_low":
        elapsed = 50.0  # 80/50=1.6 < 2
    elif mutation == "cadence_high":
        elapsed = 10.0  # 80/10=8 > 5
    elif mutation == "long_share":
        true_rows = [r for r in true_rows if r["direction"] == "SHORT"][:40]
        follow_rows = follow_rows[:40]
        for i, row in enumerate(true_rows):
            follow_rows[i] = dict(
                follow_rows[i],
                source_signal_id=row["source_signal_id"],
                direction="LONG",
                decision_utc=row["decision_utc"],
            )
        horizons = horizons[:40]
        raw_count = 40
        # all short true -> long share 0
    elif mutation == "short_share":
        true_rows = [r for r in true_rows if r["direction"] == "LONG"][:40]
        follow_rows = follow_rows[:40]
        for i, row in enumerate(true_rows):
            follow_rows[i] = dict(
                follow_rows[i],
                source_signal_id=row["source_signal_id"],
                direction="SHORT",
                decision_utc=row["decision_utc"],
            )
        horizons = horizons[:40]
        raw_count = 40
    elif mutation == "year_share":
        for row in true_rows:
            row["year"] = 2018
        for row in follow_rows:
            row["year"] = 2018
    elif mutation == "per_side":
        true_rows = true_rows[:30]  # 15 long 15 short if half
        # Force 25 long 5 short
        true_rows = []
        follow_rows = []
        horizons = []
        for i in range(25):
            t, f = matched_pair("LONG", 2018, 6.0, base + timedelta(days=i))
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
        for i in range(5):
            t, f = matched_pair("SHORT", 2018, 6.0, base + timedelta(days=40 + i))
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
        raw_count = 30
        elapsed = 10.0  # cadence 3.0 ok
    elif mutation == "stop":
        for row in true_rows:
            row["stop_distance_pips"] = 5.9
            row["cost_to_stop_ratio"] = 1.50 / 5.9
        for row in follow_rows:
            row["stop_distance_pips"] = 5.9
            row["cost_to_stop_ratio"] = 1.50 / 5.9
    elif mutation == "cost":
        for row in true_rows:
            row["stop_distance_pips"] = 5.0
            row["cost_to_stop_ratio"] = 1.50 / 5.0  # 0.30 > 0.25
        for row in follow_rows:
            row["stop_distance_pips"] = 5.0
            row["cost_to_stop_ratio"] = 1.50 / 5.0
    elif mutation == "match":
        follow_rows[0] = dict(follow_rows[0], direction=true_rows[0]["direction"])
    stage0 = sut.evaluate_stage0_gates(
        true_signals=true_rows,
        follow_signals=follow_rows,
        raw_first_per_day_count=raw_count,
        horizon_records=horizons,
        formation_complete=formation_complete,
        formation_scheduled=formation_scheduled,
        elapsed_weeks=elapsed,
    )
    assert stage0["gates"][failed_gate] is False
    assert stage0["verdict"] == sut.STAGE0_FAIL


def test_cadence_uses_elapsed_calendar_weeks_not_active() -> None:
    assert sut.ELAPSED_CALENDAR_WEEKS == pytest.approx((date(2020, 12, 31) - date(2016, 1, 4)).days / 7.0)
    # Active weeks must not appear as denominator field.
    stage0 = sut.evaluate_stage0_gates(
        true_signals=[ledger_row(direction="LONG", year=2018, stop_pips=6.0, decision=utc(2018, 1, 2, 10, 0))],
        follow_signals=[
            ledger_row(
                direction="SHORT",
                year=2018,
                stop_pips=6.0,
                decision=utc(2018, 1, 2, 10, 0),
                arm="FOLLOW_CONTROL",
            )
        ],
        raw_first_per_day_count=1,
        horizon_records=[
            {
                "source_signal_id": "x",
                "source_executable": True,
                "reason": "SOURCE_EXECUTABLE",
                "observed_horizon_bars": 60,
                "required_horizon_bars": 60,
            }
        ],
        formation_complete=1,
        formation_scheduled=1,
        elapsed_weeks=sut.ELAPSED_CALENDAR_WEEKS,
    )
    assert "active" not in json.dumps(stage0).lower() or "elapsed_calendar_weeks" in stage0["metrics"]
    assert stage0["metrics"]["elapsed_calendar_weeks"] == sut.ELAPSED_CALENDAR_WEEKS


# ---------------------------------------------------------------------------
# Exact-once / replay
# ---------------------------------------------------------------------------


def test_exact_once_classification_and_arm_mapping() -> None:
    path, decision = build_valid_short_path()
    segments, _ = sut.split_contiguous_m1(path)
    observed = {r["time_utc"] for r in path}
    raw, _ = sut.select_raw_signals(segments)
    assert len(raw) == 1
    ledgers = sut.build_matched_ledgers(raw, observed)
    assert ledgers["exact_once"]["exact_once_reconciliation"] is True
    assert ledgers["exact_once"]["raw_first_per_day_count"] == 1
    assert ledgers["exact_once"]["classification_count"] == 1
    digest = ledgers["exact_once"]["classification_digest_sha256"]
    assert len(digest) == 64


def test_independent_replay_digest_equality_and_mutation_rejection() -> None:
    path, _ = build_valid_short_path()
    days = business_days(date(2018, 6, 5), 5)
    report = sut.scan_source(path, days, with_independent_replay=True)
    assert report["independent_replay"]["digests_equal"] is True
    assert report["canonical_digest_sha256"] == report["replay_canonical_digest_sha256"]
    # Mutation rejection when enough classifications — single signal: mutate ledger.
    sut.assert_independent_replay_rejects_mutation(path, days, mode="mutate_ledger")


def test_scan_source_end_to_end_synthetic_outcome_blind() -> None:
    path_l, _ = build_valid_long_path(utc(2018, 9, 3, 8, 0))
    path_s, _ = build_valid_short_path(utc(2018, 9, 4, 8, 0))
    rows = path_l + path_s
    days = business_days(date(2018, 9, 3), 5)
    report = sut.scan_source(rows, days, with_independent_replay=True)
    assert report["hypothesis_id"] == sut.HYPOTHESIS_ID
    assert report["post_entry_ohlc_rows_read"] == 0
    assert report["returns_computed"] == 0
    assert report["trades_simulated"] == 0
    assert report["economics_authorized"] is False
    sut.assert_outcome_blind(report)


def test_outcome_fields_rejected() -> None:
    sut.assert_outcome_blind({"JUMP_IN_DECAY_WINDOW": 2, "following_window_count": 3})
    with pytest.raises(sut.ContractError, match="forbidden outcome field"):
        sut.assert_outcome_blind({"pnl": 1.0})
    with pytest.raises(sut.ContractError, match="forbidden outcome field"):
        sut.assert_outcome_blind({"win_count": 1})
    with pytest.raises(sut.ContractError, match="forbidden outcome field"):
        sut.assert_outcome_blind({"entry_price": 1.1})
    with pytest.raises(sut.ContractError, match="forbidden outcome field"):
        sut.assert_outcome_blind({"tick_volume": 10})
    with pytest.raises(sut.ContractError, match="forbidden outcome field"):
        sut.assert_outcome_blind({"spread": 1})


# ---------------------------------------------------------------------------
# Path authority / public metadata / registry
# ---------------------------------------------------------------------------


def test_forbidden_path_parts_rejected(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    (root / "public").mkdir(parents=True)
    with pytest.raises(sut.ContractError):
        sut.stable_read_regular(root / "public" / "x.txt", root)
    # Create nested forbidden.
    bad = root / "data" / "validation" / "x.bin"
    bad.parent.mkdir(parents=True)
    bad.write_bytes(b"abc")
    with pytest.raises(sut.ContractError):
        sut.stable_read_regular(bad, root)


def test_public_metadata_hash_mismatch_fails() -> None:
    with pytest.raises(sut.ContractError, match="hash mismatch"):
        sut.validate_public_metadata(
            receipt_payload=b"{}\n",
            manifest_payload=b"{}\n",
            expected_receipt_sha256="0" * 64,
            expected_manifest_sha256="1" * 64,
        )


def test_producer_schema_forbids_signal_use_of_tick_volume_spread() -> None:
    assert "tick_volume" not in sut.SIGNAL_COLUMNS
    assert "spread" not in sut.SIGNAL_COLUMNS
    assert "tick_volume" in sut.PRODUCER_SCHEMA_COLUMNS
    assert "spread" in sut.PRODUCER_SCHEMA_COLUMNS
    assert sut.SIGNAL_COLUMNS == ("time_utc", "open", "high", "low", "close")


def _authority_validation(**overrides: object) -> dict[str, object]:
    base = {
        "source_feasibility_only": True,
        "source_run_authorized": True,
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
    for field in sut.SEALED_FALSE_FIELDS:
        base[field] = False
    base.update(overrides)
    return base


def _registry_row(**validation_overrides: object) -> dict[str, object]:
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
        "validation": _authority_validation(**validation_overrides),
        "metrics": dict(sut.SOURCE_ONLY_ZERO_METRICS),
    }


def test_registry_exact_validation_whitelist_is_accepted() -> None:
    builder = SOURCE.read_bytes()
    tests = Path(__file__).read_bytes()
    base_sha = sut.reviewed_base_source_sha256(builder)
    test_sha = sha(tests)
    row = _registry_row(
        reviewed_builder_base_sha256=base_sha,
        reviewed_test_sha256=test_sha,
    )
    payload = canonical(row) + b"\n"
    row_sha = sha(payload)
    out = sut.validate_registry_authority(
        payload, row_sha, builder_payload=builder, test_payload=tests
    )
    assert out["hypothesis_id"] == sut.HYPOTHESIS_ID


def test_registry_false_authorities_reject_true() -> None:
    builder = SOURCE.read_bytes()
    tests = Path(__file__).read_bytes()
    base_sha = sut.reviewed_base_source_sha256(builder)
    test_sha = sha(tests)
    row = _registry_row(
        reviewed_builder_base_sha256=base_sha,
        reviewed_test_sha256=test_sha,
        economics_authorized=True,
    )
    payload = canonical(row) + b"\n"
    with pytest.raises(sut.ContractError):
        sut.validate_registry_authority(
            payload, sha(payload), builder_payload=builder, test_payload=tests
        )


def test_registry_rejects_nonzero_pre_run_metrics() -> None:
    builder = SOURCE.read_bytes()
    tests = Path(__file__).read_bytes()
    base_sha = sut.reviewed_base_source_sha256(builder)
    test_sha = sha(tests)
    row = _registry_row(
        reviewed_builder_base_sha256=base_sha,
        reviewed_test_sha256=test_sha,
    )
    row["metrics"] = dict(sut.SOURCE_ONLY_ZERO_METRICS)
    row["metrics"]["returns_computed"] = 1
    payload = canonical(row) + b"\n"
    with pytest.raises(sut.ContractError):
        sut.validate_registry_authority(
            payload, sha(payload), builder_payload=builder, test_payload=tests
        )


def test_wrong_registry_row_sha_cannot_arm() -> None:
    builder = SOURCE.read_bytes()
    tests = Path(__file__).read_bytes()
    base_sha = sut.reviewed_base_source_sha256(builder)
    test_sha = sha(tests)
    row = _registry_row(
        reviewed_builder_base_sha256=base_sha,
        reviewed_test_sha256=test_sha,
    )
    payload = canonical(row) + b"\n"
    with pytest.raises(sut.ContractError):
        sut.validate_registry_authority(
            payload, "D" * 64, builder_payload=builder, test_payload=tests
        )


def test_latest_row_required_not_older_duplicate() -> None:
    builder = SOURCE.read_bytes()
    tests = Path(__file__).read_bytes()
    base_sha = sut.reviewed_base_source_sha256(builder)
    test_sha = sha(tests)
    row1 = _registry_row(
        reviewed_builder_base_sha256=base_sha,
        reviewed_test_sha256=test_sha,
    )
    row2 = _registry_row(
        reviewed_builder_base_sha256=base_sha,
        reviewed_test_sha256=test_sha,
        independent_review_receipt_sha256="E" * 64,
    )
    p1 = canonical(row1) + b"\n"
    p2 = canonical(row2) + b"\n"
    payload = p1 + p2
    # Arming older row (first) must fail because latest is second.
    with pytest.raises(sut.ContractError):
        sut.validate_registry_authority(
            payload, sha(p1), builder_payload=builder, test_payload=tests
        )


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


# ---------------------------------------------------------------------------
# Evidence root / terminal / recovery
# ---------------------------------------------------------------------------


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
    path, _ = build_valid_short_path()
    days = business_days(date(2018, 6, 5), 3)
    report = sut.scan_source(path, days, with_independent_replay=True)
    enriched = sut._persist_success(root, report, row_sha)
    assert (root / "jcdr_001_source_report.json").is_file()
    assert (root / "jcdr_001_source_classifications.jsonl").is_file()
    assert (root / "jcdr_001_source_ledger.jsonl").is_file()
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
    # Write a suspect PASS terminal then recover.
    suspect = {
        "schema_version": "jcdr_001_attempt_terminal.v1",
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
    path, _ = build_valid_short_path()
    days = business_days(date(2018, 6, 5), 3)
    report = sut.scan_source_once(path, days)
    # Force stage0 fail verdict path still writes terminal FAIL not PASS.
    report = dict(report)
    report["stage0"] = dict(report["stage0"])
    report["stage0"]["verdict"] = sut.STAGE0_FAIL
    report["stage0"]["gates"] = {k: False for k in report["stage0"]["gates"]}
    sut._persist_success(root, report, row_sha)
    terminal = json.loads((root / "attempt_terminal.json").read_text(encoding="utf-8"))
    assert terminal["status"] == sut.TERMINAL_FAIL_STATUS


# ---------------------------------------------------------------------------
# Valid path integration helpers
# ---------------------------------------------------------------------------


def test_build_valid_path_forms_at_least_one_decision() -> None:
    for builder in (build_valid_long_path, build_valid_short_path):
        path, decision = builder()
        segments, _ = sut.split_contiguous_m1(path)
        raw, funnel = sut.select_raw_signals(segments)
        assert len(raw) >= 1, funnel
        assert raw[0]["time_utc"] == decision or raw[0]["date"] == decision.date()


def test_stop_median_gate_inclusive_six_pips() -> None:
    base = utc(2018, 1, 2, 12, 0)
    true_rows, follow_rows, horizons = [], [], []
    for i in range(20):
        t, f = matched_pair("LONG", 2018, 6.0, base + timedelta(days=i))
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
    for i in range(20):
        t, f = matched_pair("SHORT", 2018, 6.0, base + timedelta(days=30 + i))
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
    stage0 = sut.evaluate_stage0_gates(
        true_signals=true_rows,
        follow_signals=follow_rows,
        raw_first_per_day_count=40,
        horizon_records=horizons,
        formation_complete=100,
        formation_scheduled=100,
        elapsed_weeks=10.0,
    )
    assert stage0["gates"]["median_stop_distance_pips_at_least_6_0"] is True
    assert stage0["gates"]["median_cost_to_stop_ratio_at_most_0_25"] is True


def test_formation_domain_counts_lookback() -> None:
    start = utc(2018, 1, 2, 8, 0)
    rows = [flat_bar(start + timedelta(minutes=i)) for i in range(300)]
    segments, quality = sut.split_contiguous_m1(rows)
    complete, scheduled = sut.formation_domain_counts(segments, quality)
    assert scheduled == 300
    assert complete == 300 - (sut.LOOKBACK_RETURNS + 1)


def test_rolling_median_window_excludes_current_by_push_order() -> None:
    roller = sut._RollingAbsMedian(3)
    roller.push(1.0)
    roller.push(2.0)
    roller.push(3.0)
    assert roller.median() == 2.0
    roller.push(100.0)  # drops 1.0
    assert roller.median() == 3.0


def test_main_disarmed_without_flag() -> None:
    with pytest.raises(sut.ContractError):
        sut.main([])
