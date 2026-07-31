"""T2 Volman-inspired causal grammar reference.

Synthetic/reference implementation only.  It intentionally has no MT5, PnL,
market-data or MQL5 authority.  The code follows the frozen P2 spec:
CB1DDA2B678D2F450BB2DDE05327D2734E2A430BBBC4809BB08C71110FA0BA7D.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from math import ceil, exp, floor, isfinite, log, log10
import re
from statistics import mean, median
from typing import Literal, Sequence


Side = Literal["LONG", "SHORT"]
CAPABILITY_STATUS = {
    "status": "PARTIAL_PRE_BUILD_REFERENCE",
    "implemented": [
        "P2 §§1-8 core closed-bar structural grammar",
        "P2 §9 deterministic weighted logistic fitting and sigmoid calibration",
        "P2 §§10-11 daily/schedule lifecycle guards",
        "synthetic parity-vector export surface",
    ],
    "not_implemented": [
        "MQL5 parity execution",
    ],
    "build_gate": "BLOCKED_UNTIL_MQL5_PARITY_IS_ADDED",
}
PRODUCER_SPEC_SHA256 = "CB1DDA2B678D2F450BB2DDE05327D2734E2A430BBBC4809BB08C71110FA0BA7D"
ARM_MASKS: dict[str, tuple[int, ...]] = {
    "A0_LOCKED_BARRIER_BREAK": (1, 2, 3, 13, 14),
    "A1_PATTERN_BREAK": tuple(list(range(1, 15)) + [23]),
    "A2_PATTERN_BREAK_COMBI": tuple(list(range(1, 17)) + [23]),
    "A3_PULLBACK_REVERSAL": (4, 5, 11, 12, 13, 14, 17, 18, 19, 20, 21, 22, 23),
    "A4_CAUSAL_GRAMMAR_POLICY": tuple(range(1, 27)),
}


@dataclass(frozen=True)
class Bar:
    utc_open: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class Indicators:
    atr14: list[float | None]
    ema25: list[float | None]
    clv: list[float]
    tr: list[float]


@dataclass(frozen=True)
class Barrier:
    symbol: str
    side: Side
    price: float
    lock_index: int
    lock_utc: datetime
    touch_indices: tuple[int, ...]
    lock_atr: float
    barrier_id: str
    expires_after_index: int
    consumed: bool = False
    consumed_index: int | None = None
    expire_index: int | None = None


@dataclass(frozen=True)
class Candidate:
    arm: str
    side: Side
    trigger_index: int
    barrier: Barrier | None
    features: dict[str, float]
    reject_reason: str | None = None


@dataclass(frozen=True)
class CostInputs:
    observed_spread: float
    train_p90_nonzero_spread: float
    roundtrip_commission_cash: float
    tick_size: float
    tick_value: float


@dataclass(frozen=True)
class EntryDecision:
    accepted: bool
    reason: str
    entry_index: int | None
    entry_reference: float | None
    geometry: dict[str, float]
    consumed_date: bool = True


@dataclass(frozen=True)
class CloseLabel:
    label: int
    exit_reason: str
    exit_index: int
    gross_r: float
    net_r: float


@dataclass(frozen=True)
class PbpAuditEvent:
    event_type: str
    symbol: str
    timeframe: str
    side: Side
    decision_index: int
    decision_utc: datetime
    trigger_index: int
    trigger_utc: datetime
    k_index: int
    barrier_side: Side | None
    barrier_price: float | None
    barrier_price_ticks: int | None
    barrier_id: str | None
    lock_utc: datetime | None
    break_index: int | None
    break_utc: datetime | None
    contact_index: int | None
    contact_utc: datetime | None
    consumed_index: int | None
    consumed_utc: datetime | None
    producer_spec_sha256: str = PRODUCER_SPEC_SHA256


@dataclass(frozen=True)
class ModelContext:
    room_r: float
    round_grid_room_r: float
    grid_feature_missing: int
    rho: float
    r_cash_atr: float


@dataclass(frozen=True)
class BrokerSchedule:
    symbol: str
    timezone: str
    schedule_sha256: str
    scheduled_closed_indices: frozenset[int] = frozenset()
    weekend_coverage_only: bool = False
    remap_indices: frozenset[int] = frozenset()

    def __post_init__(self) -> None:
        if not self.symbol or not self.timezone:
            raise ValueError("BrokerSchedule requires nonempty symbol/timezone")
        if not re.fullmatch(r"[0-9A-Fa-f]{64}", self.schedule_sha256):
            raise ValueError("BrokerSchedule requires valid 64-hex schedule_sha256")
        if not isinstance(self.scheduled_closed_indices, frozenset) or not isinstance(self.remap_indices, frozenset):
            raise ValueError("BrokerSchedule index sets must be immutable frozensets")
        if any((not isinstance(i, int)) or i < 0 for i in self.scheduled_closed_indices | self.remap_indices):
            raise ValueError("BrokerSchedule index sets must contain nonnegative integers")

    @classmethod
    def from_bytes(cls, symbol: str, timezone_name: str, payload: bytes, **kwargs: object) -> "BrokerSchedule":
        return cls(symbol, timezone_name, sha256(payload).hexdigest().upper(), **kwargs)


@dataclass(frozen=True)
class ScheduleStep:
    state: str
    warmup_remaining: int
    engineering_invalid: bool = False


@dataclass(frozen=True)
class NormalizationFit:
    medians: list[float]
    mads: list[float]
    constant_features: tuple[int, ...]


@dataclass(frozen=True)
class LogisticFit:
    beta: list[float]
    converged: bool
    iterations: int
    grad_inf: float
    objective: float


@dataclass(frozen=True)
class CalibrationFit:
    a: float
    b: float
    converged: bool
    iterations: int
    grad_inf: float
    objective: float


def direction(side: Side) -> int:
    return 1 if side == "LONG" else -1


def _tick_eq(a: float, b: float, tick: float) -> bool:
    return abs(a - b) <= 0.5 * tick


def compute_indicators(bars: Sequence[Bar]) -> Indicators:
    tr: list[float] = []
    clv: list[float] = []
    for i, bar in enumerate(bars):
        if i == 0:
            true_range = bar.high - bar.low
        else:
            prev_close = bars[i - 1].close
            true_range = max(
                bar.high - bar.low,
                abs(bar.high - prev_close),
                abs(bar.low - prev_close),
            )
        tr.append(true_range)
        rng = bar.high - bar.low
        clv.append(0.0 if rng <= 0 else (2 * bar.close - bar.high - bar.low) / rng)

    atr: list[float | None] = [None] * len(bars)
    if len(bars) >= 14:
        atr[13] = mean(tr[:14])
        for i in range(14, len(bars)):
            atr[i] = (13 * atr[i - 1] + tr[i]) / 14  # type: ignore[operator]

    ema: list[float | None] = [None] * len(bars)
    if len(bars) >= 25:
        ema[24] = mean([b.close for b in bars[:25]])
        alpha = 2 / 26
        for i in range(25, len(bars)):
            ema[i] = alpha * bars[i].close + (1 - alpha) * ema[i - 1]  # type: ignore[operator]

    return Indicators(atr14=atr, ema25=ema, clv=clv, tr=tr)


def contiguous_m5(bars: Sequence[Bar], start: int, end: int) -> bool:
    return all(
        bars[i].utc_open - bars[i - 1].utc_open == timedelta(minutes=5)
        for i in range(start + 1, end + 1)
    )


def barrier_id(symbol: str, side: Side, lock_utc: datetime, touches: Sequence[int] | Sequence[datetime], price: float, tick: float, bars: Sequence[Bar] | None = None) -> str:
    price_ticks = round(price / tick)
    if bars is not None:
        touch_utc = sorted(bars[int(i)].utc_open.isoformat() for i in touches)  # type: ignore[arg-type]
    else:
        touch_utc = sorted(t.isoformat() if isinstance(t, datetime) else str(t) for t in touches)
    raw = f"{symbol}|{side}|{lock_utc.isoformat()}|{','.join(touch_utc)}|{price_ticks}"
    return sha256(raw.encode("utf-8")).hexdigest().upper()


def lock_barrier(
    bars: Sequence[Bar],
    ind: Indicators,
    symbol: str,
    lock_index: int,
    side: Side,
    tick: float,
    active: Sequence[Barrier] = (),
) -> Barrier | None:
    atr = ind.atr14[lock_index]
    if atr is None or lock_index < 17 or not contiguous_m5(bars, lock_index - 17, lock_index):
        return None

    d = direction(side)
    level_at = (lambda i: bars[i].high) if side == "LONG" else (lambda i: bars[i].low)
    candidate_price = level_at(lock_index)
    eps = 0.10 * atr
    touches = [lock_index]
    for i in range(lock_index - 2, lock_index - 18, -1):
        if abs(level_at(i) - candidate_price) <= eps and all(abs(i - j) >= 2 for j in touches):
            touches.append(i)
    if len(touches) < 3:
        return None
    price = median([level_at(i) for i in touches])
    if d * (bars[lock_index].close - price) > 0.05 * atr:
        return None

    for old in active:
        if old.side != side or old.consumed:
            continue
        if abs(price - old.price) <= max(0.10 * atr, 0.10 * old.lock_atr):
            return None
        if len(set(touches).intersection(old.touch_indices)) >= 2:
            return None

    return Barrier(
        symbol=symbol,
        side=side,
        price=price,
        lock_index=lock_index,
        lock_utc=bars[lock_index].utc_open,
        touch_indices=tuple(sorted(touches)),
        lock_atr=atr,
        barrier_id=barrier_id(symbol, side, bars[lock_index].utc_open, touches, price, tick, bars),
        expires_after_index=lock_index + 12,
    )


def close_break(bars: Sequence[Bar], ind: Indicators, barrier: Barrier, t: int) -> bool:
    atr = ind.atr14[t]
    if atr is None or t <= barrier.lock_index or t > barrier.expires_after_index:
        return False
    d = direction(barrier.side)
    return d * (bars[t - 1].close - barrier.price) <= 0 and d * (bars[t].close - barrier.price) >= 0.05 * atr


def pressure_components(bars: Sequence[Bar], ind: Indicators, u: int, side: Side) -> dict[str, float] | None:
    if u < 24 or u < 5 or ind.atr14[u] is None or ind.ema25[u] is None or ind.ema25[u - 5] is None:
        return None
    denom = sum(abs(bars[k].close - bars[k - 1].close) for k in range(u - 4, u + 1))
    if denom <= 0:
        return None
    d = direction(side)
    atr = ind.atr14[u]  # type: ignore[assignment]
    return {
        "disp": d * (bars[u].close - bars[u - 5].close) / atr,
        "er": d * (bars[u].close - bars[u - 5].close) / denom,
        "mean_clv": d * mean(ind.clv[u - 5 : u + 1]),
        "ema_slope": d * (ind.ema25[u] - ind.ema25[u - 5]) / atr,  # type: ignore[operator]
    }


def pressure_true(bars: Sequence[Bar], ind: Indicators, u: int, side: Side) -> bool:
    c = pressure_components(bars, ind, u, side)
    return bool(c and c["disp"] >= 0.60 and c["er"] >= 0.55 and c["mean_clv"] >= 0.20 and c["ema_slope"] >= 0.10)


def pressure_duration(bars: Sequence[Bar], ind: Indicators, u: int, side: Side) -> int:
    n = 0
    for j in range(u, max(-1, u - 12), -1):
        if pressure_true(bars, ind, j, side):
            n += 1
        else:
            break
    return n


def buildup_features(bars: Sequence[Bar], ind: Indicators, barrier: Barrier, t: int, tick: float = 1e-12) -> dict[str, float] | None:
    if not close_break(bars, ind, barrier, t):
        return None
    d = direction(barrier.side)
    b = barrier.price
    a = barrier.lock_atr
    for n in range(8, 2, -1):
        start = t - n
        if start - 13 < 0 or barrier.lock_index > start - 1:
            continue
        if not pressure_true(bars, ind, start - 1, barrier.side) or pressure_duration(bars, ind, start - 1, barrier.side) < 2:
            continue
        seg = bars[start:t]
        if any(not (-0.05 * a <= d * (b - x.close) <= 0.35 * a) for x in seg):
            continue
        near = sum(1 for x in seg if (abs(x.high - b) if barrier.side == "LONG" else abs(x.low - b)) <= 0.10 * a)
        if near < 2:
            continue
        contraction = median(ind.tr[start:t]) / max(median(ind.tr[start - 12 : start]), tick)
        if contraction > 0.75:
            continue
        overlaps = []
        for i in range(start + 1, t):
            hi = min(bars[i].high, bars[i - 1].high)
            lo = max(bars[i].low, bars[i - 1].low)
            denom = max(min(bars[i].high - bars[i].low, bars[i - 1].high - bars[i - 1].low), tick)
            overlaps.append(max(0.0, hi - lo) / denom)
        overlap_mean = mean([min(1.0, max(0.0, x)) for x in overlaps])
        if overlap_mean < 0.50:
            continue
        support = [x.low if barrier.side == "LONG" else x.high for x in seg]
        progression = sum(1 for i in range(1, len(support)) if d * (support[i] - support[i - 1]) >= -0.05 * a) / (n - 1)
        if progression < 2 / 3:
            continue
        x = [d * (b - s) for s in support]
        counter_ratio = mean(x[-2:]) / max(mean(x[:2]), tick)
        if counter_ratio > 0.80:
            continue
        return {
            "buildup_n": float(n),
            "contraction": contraction,
            "overlap_mean": overlap_mean,
            "progression": progression,
            "counter_ratio": counter_ratio,
        }
    return None


def a1_candidate(bars: Sequence[Bar], ind: Indicators, barrier: Barrier, t: int, tick: float = 1e-12) -> Candidate | None:
    f = buildup_features(bars, ind, barrier, t, tick)
    if f is None:
        return None
    pressure_index = t - int(f["buildup_n"]) - 1
    pc = pressure_components(bars, ind, pressure_index, barrier.side) or {}
    enriched = f | {
        "touch_count": float(len(barrier.touch_indices)),
        "barrier_age": float(t - barrier.lock_index),
        "break_margin_atr": direction(barrier.side) * (bars[t].close - barrier.price) / ind.atr14[t],  # type: ignore[operator]
        "pressure_disp": pc.get("disp", 0.0),
        "pressure_er": pc.get("er", 0.0),
        "pressure_mean_clv": pc.get("mean_clv", 0.0),
        "pressure_ema_slope": pc.get("ema_slope", 0.0),
        "pressure_duration": float(pressure_duration(bars, ind, pressure_index, barrier.side)),
    }
    return Candidate("A1_PATTERN_BREAK", barrier.side, t, barrier, enriched)


def a0_candidate(bars: Sequence[Bar], ind: Indicators, barrier: Barrier, t: int) -> Candidate | None:
    if not close_break(bars, ind, barrier, t):
        return None
    atr = ind.atr14[t]
    return Candidate(
        "A0_LOCKED_BARRIER_BREAK",
        barrier.side,
        t,
        barrier,
        {
            "touch_count": float(len(barrier.touch_indices)),
            "barrier_age": float(t - barrier.lock_index),
            "break_margin_atr": direction(barrier.side) * (bars[t].close - barrier.price) / atr,  # type: ignore[operator]
        },
    )


def a2_candidate(bars: Sequence[Bar], ind: Indicators, barrier: Barrier, t: int, tick: float = 1e-12) -> Candidate | None:
    base = buildup_features(bars, ind, barrier, t, tick)
    if base is None or t < 2:
        return None
    d = direction(barrier.side)
    p, q = bars[t - 2], bars[t - 1]
    if d * (p.close - p.open) < 0.35 * ind.atr14[t - 2]:  # type: ignore[operator]
        return None
    if d * ind.clv[t - 2] < 0.50:
        return None
    mother = p.high - p.low
    if mother <= 0 or q.high > p.high + 0.5 * tick or q.low < p.low - 0.5 * tick or (q.high - q.low) / mother > 0.75:
        return None
    if d * (p.close - barrier.price) > 0 or d * (q.close - barrier.price) > 0:
        return None
    pressure_index = t - int(base["buildup_n"]) - 1
    pc = pressure_components(bars, ind, pressure_index, barrier.side) or {}
    enriched = base | {
        "touch_count": float(len(barrier.touch_indices)),
        "barrier_age": float(t - barrier.lock_index),
        "break_margin_atr": direction(barrier.side) * (bars[t].close - barrier.price) / ind.atr14[t],  # type: ignore[operator]
        "pressure_disp": pc.get("disp", 0.0),
        "pressure_er": pc.get("er", 0.0),
        "pressure_mean_clv": pc.get("mean_clv", 0.0),
        "pressure_ema_slope": pc.get("ema_slope", 0.0),
        "pressure_duration": float(pressure_duration(bars, ind, pressure_index, barrier.side)),
        "inside_ratio": (q.high - q.low) / mother,
    }
    return Candidate("A2_PATTERN_BREAK_COMBI", barrier.side, t, barrier, enriched)


def a3_candidate(
    bars: Sequence[Bar],
    ind: Indicators,
    t: int,
    side: Side,
    active_barriers: Sequence[Barrier],
    broken_tombstones: Sequence[Barrier] = (),
) -> Candidate | None:
    if broken_tombstones:
        candidate, _audit = a3_candidate_with_audit(bars, ind, t, side, active_barriers, broken_tombstones)
        return candidate
    d = direction(side)
    for m in range(2, 7):
        k = t - m - 1
        if k - 7 < 0 or ind.atr14[k] is None or ind.atr14[t] is None:
            continue
        if pressure_duration(bars, ind, k, side) < 2:
            continue
        leg_amp = d * (bars[k].close - bars[k - 7].close)
        if leg_amp < 1.20 * ind.atr14[k]:  # type: ignore[operator]
            continue
        correction = bars[k + 1 : t]
        x_c = min(x.low for x in correction) if side == "LONG" else max(x.high for x in correction)
        depth = d * (bars[k].close - x_c) / leg_amp
        if not (0.40 <= depth <= 0.60):
            continue
        denom = sum(abs(bars[i].close - bars[i - 1].close) for i in range(k + 1, t))
        corr_er = 0.0 if denom <= 0 else -d * (bars[t - 1].close - bars[k].close) / denom
        if not (0 <= corr_er <= 0.55):
            continue
        if d * (bars[t - 1].close - bars[t - 2].close) < -0.10 * ind.atr14[k]:  # type: ignore[operator]
            continue
        if d * ind.clv[t - 1] < -0.10:
            continue
        if any(
            x.side == side
            and x.consumed_index is not None
            and k - 7 <= x.consumed_index <= t - 1
            for x in broken_tombstones
        ):
            return Candidate("A3_PULLBACK_REVERSAL", side, t, None, {}, "SKIP_PBP_EXCLUDED")
        if any(close_break(bars, ind, b, j) and b.side == side for b in active_barriers for j in range(k - 7, t)):
            return Candidate("A3_PULLBACK_REVERSAL", side, t, None, {}, "SKIP_PBP_EXCLUDED")
        contact_index = min(range(k + 1, t), key=lambda i: bars[i].low if side == "LONG" else -bars[i].high)
        structure = any(
            b.side != side
            and b.lock_index < k - 7
            and b.lock_index < contact_index <= b.expires_after_index
            and abs(x_c - b.price) <= 0.10 * ind.atr14[k]  # type: ignore[operator]
            for b in active_barriers
        )
        tombstone_contact = any(
            b.side == side
            and b.consumed_index is not None
            and 0 <= contact_index - b.consumed_index <= 48
            and abs(x_c - b.price) <= 0.10 * ind.atr14[k]  # type: ignore[operator]
            for b in broken_tombstones
        )
        if tombstone_contact:
            return Candidate("A3_PULLBACK_REVERSAL", side, t, None, {}, "SKIP_PBP_EXCLUDED")
        ema = any(
            ind.ema25[i] is not None and bars[i].low <= ind.ema25[i] + 0.10 * ind.atr14[i] and bars[i].high >= ind.ema25[i] - 0.10 * ind.atr14[i]  # type: ignore[operator]
            for i in range(k + 1, t)
        )
        if not (structure or ema):
            continue
        if side == "LONG":
            release = bars[t].close >= bars[t - 1].high + 0.05 * ind.atr14[t]  # type: ignore[operator]
        else:
            release = bars[t].close <= bars[t - 1].low - 0.05 * ind.atr14[t]  # type: ignore[operator]
        if release and d * (bars[t].close - bars[t].open) > 0 and d * ind.clv[t] >= 0.50:
            pc = pressure_components(bars, ind, k, side) or {}
            return Candidate(
                "A3_PULLBACK_REVERSAL",
                side,
                t,
                None,
                {
                    "pressure_disp": pc.get("disp", 0.0),
                    "pressure_er": pc.get("er", 0.0),
                    "pressure_mean_clv": pc.get("mean_clv", 0.0),
                    "pressure_ema_slope": pc.get("ema_slope", 0.0),
                    "pressure_duration": float(pressure_duration(bars, ind, k, side)),
                    "leg_amp_atr": leg_amp / ind.atr14[k],  # type: ignore[operator]
                    "depth": depth,
                    "correction_duration": float(m),
                    "corr_er": corr_er,
                    "structure_anchor": float(structure),
                    "ema_anchor": float(ema),
                },
            )
    return None


@dataclass(frozen=True)
class A3StructuralState:
    candidate: Candidate
    k: int
    contact_index: int
    contact_price: float


def _a3_structural_state(
    bars: Sequence[Bar],
    ind: Indicators,
    t: int,
    side: Side,
    active_barriers: Sequence[Barrier],
) -> A3StructuralState | None:
    d = direction(side)
    for m in range(2, 7):
        k = t - m - 1
        if k - 7 < 0 or ind.atr14[k] is None or ind.atr14[t] is None:
            continue
        if pressure_duration(bars, ind, k, side) < 2:
            continue
        leg_amp = d * (bars[k].close - bars[k - 7].close)
        if leg_amp < 1.20 * ind.atr14[k]:  # type: ignore[operator]
            continue
        correction = bars[k + 1 : t]
        x_c = min(x.low for x in correction) if side == "LONG" else max(x.high for x in correction)
        depth = d * (bars[k].close - x_c) / leg_amp
        if not (0.40 <= depth <= 0.60):
            continue
        denom = sum(abs(bars[i].close - bars[i - 1].close) for i in range(k + 1, t))
        corr_er = 0.0 if denom <= 0 else -d * (bars[t - 1].close - bars[k].close) / denom
        if not (0 <= corr_er <= 0.55):
            continue
        if d * (bars[t - 1].close - bars[t - 2].close) < -0.10 * ind.atr14[k]:  # type: ignore[operator]
            continue
        if d * ind.clv[t - 1] < -0.10:
            continue
        contact_index = min(range(k + 1, t), key=lambda i: bars[i].low if side == "LONG" else -bars[i].high)
        structure = any(
            b.side != side
            and b.lock_index < k - 7
            and b.lock_index < contact_index <= b.expires_after_index
            and bars[contact_index].low <= b.price <= bars[contact_index].high
            and abs(x_c - b.price) <= 0.10 * ind.atr14[k]  # type: ignore[operator]
            for b in active_barriers
        )
        ema = any(
            ind.ema25[i] is not None and bars[i].low <= ind.ema25[i] + 0.10 * ind.atr14[i] and bars[i].high >= ind.ema25[i] - 0.10 * ind.atr14[i]  # type: ignore[operator]
            for i in range(k + 1, t)
        )
        if not (structure or ema):
            continue
        if side == "LONG":
            release = bars[t].close >= bars[t - 1].high + 0.05 * ind.atr14[t]  # type: ignore[operator]
        else:
            release = bars[t].close <= bars[t - 1].low - 0.05 * ind.atr14[t]  # type: ignore[operator]
        if not (release and d * (bars[t].close - bars[t].open) > 0 and d * ind.clv[t] >= 0.50):
            continue
        pc = pressure_components(bars, ind, k, side) or {}
        candidate = Candidate(
            "A3_PULLBACK_REVERSAL",
            side,
            t,
            None,
            {
                "pressure_disp": pc.get("disp", 0.0),
                "pressure_er": pc.get("er", 0.0),
                "pressure_mean_clv": pc.get("mean_clv", 0.0),
                "pressure_ema_slope": pc.get("ema_slope", 0.0),
                "pressure_duration": float(pressure_duration(bars, ind, k, side)),
                "leg_amp_atr": leg_amp / ind.atr14[k],  # type: ignore[operator]
                "depth": depth,
                "correction_duration": float(m),
                "corr_er": corr_er,
                "structure_anchor": float(structure),
                "ema_anchor": float(ema),
            },
        )
        return A3StructuralState(candidate, k, contact_index, x_c)
    return None


def a3_candidate_with_audit(
    bars: Sequence[Bar],
    ind: Indicators,
    t: int,
    side: Side,
    active_barriers: Sequence[Barrier],
    broken_tombstones: Sequence[Barrier] = (),
    tick: float = 1e-5,
) -> tuple[Candidate | None, tuple[PbpAuditEvent, ...]]:
    audits: list[PbpAuditEvent] = []
    state = _a3_structural_state(bars, ind, t, side, active_barriers)
    if state is None:
        return None, tuple(audits)
    for b in active_barriers:
        for j in range(state.k - 7, t):
            if b.side == side and close_break(bars, ind, b, j):
                audits.append(PbpAuditEvent(
                    "PBP_BREAK_WINDOW", b.symbol, "M5", side, j, bars[j].utc_open,
                    t, bars[t].utc_open, state.k, b.side, b.price, round(b.price / tick),
                    b.barrier_id, b.lock_utc, j, bars[j].utc_open, None, None,
                    b.consumed_index,
                    bars[b.consumed_index].utc_open if b.consumed_index is not None and b.consumed_index < len(bars) else None,
                ))
                return replace(state.candidate, reject_reason="SKIP_PBP_EXCLUDED"), tuple(audits)
    for b in broken_tombstones:
        if b.side != side or b.consumed_index is None:
            continue
        for ci in range(state.k + 1, t):
            if 0 <= ci - b.consumed_index <= 48 and bars[ci].low <= b.price <= bars[ci].high:
                audits.append(PbpAuditEvent(
                    "PBP_TOMBSTONE_CONTACT", b.symbol, "M5", side, ci, bars[ci].utc_open,
                    t, bars[t].utc_open, state.k, b.side, b.price, round(b.price / tick),
                    b.barrier_id, b.lock_utc, None, None, ci, bars[ci].utc_open,
                    b.consumed_index, bars[b.consumed_index].utc_open,
                ))
                return replace(state.candidate, reject_reason="SKIP_PBP_EXCLUDED"), tuple(audits)
    return state.candidate, tuple(audits)


def cost_geometry(entry: float, invalidation: float, atr: float, cost: CostInputs) -> dict[str, float]:
    if min(cost.observed_spread, cost.train_p90_nonzero_spread, cost.roundtrip_commission_cash, cost.tick_size, cost.tick_value) <= 0:
        raise ValueError("invalid non-positive cost contract")
    commission_price = cost.roundtrip_commission_cash / cost.tick_value * cost.tick_size
    c = max(cost.observed_spread, cost.train_p90_nonzero_spread) + commission_price + 2 * cost.tick_size
    r = abs(entry - invalidation)
    if r <= 0 or not all(isfinite(x) for x in [c, r, atr]):
        raise ValueError("invalid risk geometry")
    rho = c / r
    r_cash = r + c
    accepted = 0.60 * atr <= r_cash <= 1.40 * atr and rho <= 0.20
    return {"cost": c, "r": r, "rho": rho, "R_cash": r_cash, "p_BE": (1 + rho) / 3, "tau": (1 + rho) / 3 + 0.05, "accepted": float(accepted)}


def round_grid_room(entry: float, side: Side, risk: float, median_train_atr: float, tick: float) -> tuple[float, int]:
    if median_train_atr <= 0 or risk <= 0 or tick <= 0:
        return 0.0, 1
    grid = round((10 ** round(log10(10 * median_train_atr))) / tick) * tick
    if grid <= 0 or not isfinite(grid):
        return 0.0, 1
    g = grid * (floor(entry / grid) + 1) if side == "LONG" else grid * (ceil(entry / grid) - 1)
    return direction(side) * (g - entry) / risk, 0


def nearest_opposing_room(entry: float, side: Side, risk: float, active_barriers: Sequence[Barrier], trigger_barrier_id: str | None = None) -> float:
    d = direction(side)
    candidates = [
        d * (b.price - entry)
        for b in active_barriers
        if not b.consumed and b.side == side and b.barrier_id != trigger_barrier_id and d * (b.price - entry) > 0
    ]
    if risk <= 0:
        raise ValueError("non-positive risk")
    return float("inf") if not candidates else min(candidates) / risk


def derived_invalidation(bars: Sequence[Bar], ind: Indicators, candidate: Candidate) -> float:
    atr = ind.atr14[candidate.trigger_index]
    if atr is None:
        raise ValueError("ATR unavailable for invalidation")
    d = direction(candidate.side)
    if candidate.arm in {"A0_LOCKED_BARRIER_BREAK", "A1_PATTERN_BREAK", "A2_PATTERN_BREAK_COMBI"}:
        if candidate.barrier is None:
            raise ValueError("barrier required for A0-A2 invalidation")
        segment = bars[candidate.barrier.lock_index : candidate.trigger_index + 1]
        extreme = min(b.low for b in segment) if candidate.side == "LONG" else max(b.high for b in segment)
    elif candidate.arm == "A3_PULLBACK_REVERSAL":
        if "correction_extreme" not in candidate.features:
            raise ValueError("A3 correction_extreme required for invalidation")
        extreme = candidate.features["correction_extreme"]
    else:
        raise ValueError(f"unknown arm for invalidation: {candidate.arm}")
    return extreme - 0.10 * atr if d == 1 else extreme + 0.10 * atr


def finalize_candidate_context(
    bars: Sequence[Bar],
    ind: Indicators,
    candidate: Candidate,
    active_barriers: Sequence[Barrier],
    cost: CostInputs,
    *,
    tick: float,
    median_train_atr: float,
) -> Candidate:
    entry_index = candidate.trigger_index + 1
    if entry_index >= len(bars):
        raise ValueError("next-open entry unavailable")
    entry = bars[entry_index].open
    invalidation = derived_invalidation(bars, ind, candidate)
    atr = ind.atr14[candidate.trigger_index]
    if atr is None:
        raise ValueError("ATR unavailable for model context")
    geom = cost_geometry(entry, invalidation, atr, cost)
    grid_room, grid_missing = round_grid_room(entry, candidate.side, geom["r"], median_train_atr, tick)
    room = nearest_opposing_room(entry, candidate.side, geom["r"], active_barriers, candidate.barrier.barrier_id if candidate.barrier else None)
    context = ModelContext(room, grid_room, grid_missing, geom["rho"], geom["R_cash"] / atr)
    finalized = attach_model_context(candidate, context)
    finalized = replace(finalized, features=finalized.features | {
        "derived_invalidation": invalidation,
        "entry_reference": entry,
        "entry_index": float(entry_index),
        "cost": geom["cost"],
        "r": geom["r"],
        "p_BE": geom["p_BE"],
        "tau": geom["tau"],
    })
    if candidate.arm in {"A1_PATTERN_BREAK", "A2_PATTERN_BREAK_COMBI"} and room < 2.0:
        return replace(finalized, reject_reason="SKIP_INSUFFICIENT_ROOM")
    return finalized


def a4_select(candidates: Sequence[Candidate]) -> Candidate | None:
    live = [c for c in candidates if c.reject_reason is None]
    if not live:
        return None
    if {c.side for c in live} == {"LONG", "SHORT"}:
        return Candidate("A4_CAUSAL_GRAMMAR_POLICY", "LONG", min(c.trigger_index for c in live), None, {}, "SKIP_DIRECTION_CONFLICT")
    priority = {"A2_PATTERN_BREAK_COMBI": 0, "A1_PATTERN_BREAK": 1, "A3_PULLBACK_REVERSAL": 2}
    return sorted(live, key=lambda c: priority.get(c.arm, 99))[0]


def first_margin_crossing(prev_margin: float, margin: float) -> bool:
    return prev_margin <= 0 and margin > 0


def daily_entry_decision(
    bars: Sequence[Bar],
    candidate: Candidate,
    prev_margin: float,
    margin: float,
    invalidation: float,
    cost: CostInputs,
    horizon_bars: int = 12,
    scheduled_closed_indices: frozenset[int] = frozenset(),
) -> EntryDecision:
    if not first_margin_crossing(prev_margin, margin):
        return EntryDecision(False, "SKIP_NO_UPWARD_MARGIN_CROSS", None, None, {}, False)
    entry_index = candidate.trigger_index + 1
    if entry_index >= len(bars):
        return EntryDecision(False, "SKIP_NO_NEXT_OPEN", None, None, {}, True)
    required_exit_open_index = entry_index + horizon_bars + 1
    if required_exit_open_index >= len(bars):
        return EntryDecision(False, "SKIP_INSUFFICIENT_HORIZON_BARS", None, None, {}, True)
    if any(i in scheduled_closed_indices for i in range(entry_index, required_exit_open_index + 1)):
        return EntryDecision(False, "SKIP_HORIZON_CROSSES_SCHEDULED_CLOSE", None, None, {}, True)
    flat_t = datetime(2000, 1, 1, 23, 55).time()
    if any(bars[i].utc_open.weekday() == 4 and bars[i].utc_open.time() >= flat_t for i in range(entry_index, required_exit_open_index + 1)):
        return EntryDecision(False, "SKIP_FRIDAY_FLAT_HORIZON", None, None, {}, True)
    ind = compute_indicators(bars)
    derived = derived_invalidation(bars, ind, candidate)
    if abs(invalidation - derived) > 1e-9:
        raise ValueError("caller invalidation mismatch")
    if "derived_invalidation" in candidate.features and abs(candidate.features["derived_invalidation"] - derived) > 1e-9:
        raise ValueError("finalized candidate context mismatch: derived_invalidation")
    atr = ind.atr14[candidate.trigger_index]
    if atr is None:
        return EntryDecision(False, "SKIP_ATR_UNAVAILABLE", None, None, {}, True)
    entry = bars[entry_index].open
    geom = cost_geometry(entry, derived, atr, cost)
    if not geom["accepted"]:
        return EntryDecision(False, "SKIP_ENTRY_GAP_RECHECK", entry_index, entry, geom, True)
    return EntryDecision(True, "ENTER", entry_index, entry, geom, True)


def daily_entry_decision_from_finalized(
    bars: Sequence[Bar],
    ind: Indicators,
    candidate: Candidate,
    prev_margin: float,
    margin: float,
    cost: CostInputs,
    ledger: DailyArmLedger,
    *,
    active_barriers: Sequence[Barrier],
    tick: float,
    median_train_atr: float,
    horizon_bars: int = 12,
    scheduled_closed_indices: frozenset[int] = frozenset(),
) -> EntryDecision:
    if not first_margin_crossing(prev_margin, margin):
        return EntryDecision(False, "SKIP_NO_UPWARD_MARGIN_CROSS", None, None, {}, False)
    recomputed = finalize_candidate_context(bars, ind, candidate, active_barriers, cost, tick=tick, median_train_atr=median_train_atr)
    for key in ("derived_invalidation", "entry_reference", "cost", "r", "rho", "R_cash_atr"):
        if key in candidate.features and abs(candidate.features[key] - recomputed.features[key]) > 1e-9:
            raise ValueError(f"finalized candidate context mismatch: {key}")
    decision_date = bars[candidate.trigger_index].utc_open
    if not ledger.try_consume(candidate.arm, decision_date):
        return EntryDecision(False, "SKIP_UTC_DATE_ARM_ALREADY_CONSUMED", None, None, {}, False)
    if recomputed.reject_reason is not None:
        return EntryDecision(False, recomputed.reject_reason, None, None, {}, True)
    return daily_entry_decision(
        bars,
        recomputed,
        prev_margin,
        margin,
        recomputed.features["derived_invalidation"],
        cost,
        horizon_bars=horizon_bars,
        scheduled_closed_indices=scheduled_closed_indices,
    )


def close_only_label(bars: Sequence[Bar], entry_index: int, side: Side, entry_reference: float, risk: float, cost: float, horizon_bars: int = 12, scheduled_exit_index: int | None = None) -> CloseLabel:
    if risk <= 0 or not isfinite(risk) or not isfinite(cost):
        raise ValueError("invalid label risk/cost")
    if scheduled_exit_index is None and entry_index + horizon_bars + 1 >= len(bars):
        raise ValueError("ENGINEERING_INVALID_INSUFFICIENT_CLOSE_ONLY_HORIZON")
    d = direction(side)
    last = min(len(bars) - 1, entry_index + horizon_bars if scheduled_exit_index is None else scheduled_exit_index - 1)
    for j in range(entry_index + 1, last + 1):
        x = d * (bars[j].close - entry_reference)
        if x <= -risk:
            return CloseLabel(0, "CLOSE_STOP", min(j + 1, len(bars) - 1), -1.0, (-risk - cost) / risk)
        if x >= 2 * risk:
            return CloseLabel(1, "CLOSE_TARGET", min(j + 1, len(bars) - 1), 2.0, (2 * risk - cost) / risk)
    exit_index = scheduled_exit_index if scheduled_exit_index is not None else last + 1
    if exit_index >= len(bars):
        raise ValueError("ENGINEERING_INVALID_MISSING_EXIT_OPEN")
    return CloseLabel(0, "TIME_EXIT", exit_index, 0.0, -cost / risk)


def select_nearest_break_and_consume(bars: Sequence[Bar], ind: Indicators, barriers: Sequence[Barrier], t: int, side: Side) -> tuple[Barrier | None, list[Barrier]]:
    broken = [b for b in barriers if b.side == side and close_break(bars, ind, b, t)]
    if not broken:
        return None, list(barriers)
    prev_close = bars[t - 1].close
    candidate_broken = [b for b in broken if (b.price > prev_close if side == "LONG" else b.price < prev_close)]
    if side == "LONG":
        selected = sorted(candidate_broken, key=lambda b: (b.price, b.lock_utc, b.barrier_id))[0] if candidate_broken else None
    else:
        selected = sorted(candidate_broken, key=lambda b: (-b.price, b.lock_utc, b.barrier_id))[0] if candidate_broken else None
    updated = [replace(b, consumed=True, consumed_index=t) if b in broken else b for b in barriers]
    return selected, updated


def append_prefix_invariant(events_before: Sequence[object], events_after_prefix: Sequence[object]) -> bool:
    return list(events_before) == list(events_after_prefix[: len(events_before)])


def generated_engine_events(bars: Sequence[Bar], barrier: Barrier, tick: float = 1e-5) -> list[tuple[str, str, int]]:
    ind = compute_indicators(bars)
    events: list[tuple[str, str, int]] = []
    current = barrier
    for t in range(barrier.lock_index + 1, min(len(bars), barrier.expires_after_index + 1)):
        if current.consumed:
            break
        selected, updated = select_nearest_break_and_consume(bars, ind, [current], t, current.side)
        current = updated[0]
        if selected is not None:
            events.append(("A0", current.barrier_id, t))
            preconsume = replace(current, consumed=False, consumed_index=None)
            if a1_candidate(bars, ind, preconsume, t, tick):
                events.append(("A1", current.barrier_id, t))
            if a2_candidate(bars, ind, preconsume, t, tick):
                events.append(("A2", current.barrier_id, t))
    return events


def parity_vector(candidate: Candidate, bars: Sequence[Bar], ind: Indicators) -> dict[str, object]:
    return {
        "capability_status": CAPABILITY_STATUS["status"],
        "arm": candidate.arm,
        "side": candidate.side,
        "trigger_index": candidate.trigger_index,
        "trigger_utc": bars[candidate.trigger_index].utc_open.isoformat(),
        "barrier_id": candidate.barrier.barrier_id if candidate.barrier else None,
        "features": dict(sorted(candidate.features.items())),
        "atr14": ind.atr14[candidate.trigger_index],
        "ema25": ind.ema25[candidate.trigger_index],
        "reject_reason": candidate.reject_reason,
    }


REQUIRED_COMMON_FIELDS: dict[str, tuple[str, ...]] = {
    "A0_LOCKED_BARRIER_BREAK": ("touch_count", "barrier_age", "break_margin_atr", "rho", "R_cash_atr"),
    "A1_PATTERN_BREAK": ("touch_count", "barrier_age", "break_margin_atr", "pressure_disp", "pressure_er", "pressure_mean_clv", "pressure_ema_slope", "pressure_duration", "buildup_n", "contraction", "overlap_mean", "progression", "counter_ratio", "room_r", "round_grid_room_r", "grid_feature_missing", "rho", "R_cash_atr"),
    "A2_PATTERN_BREAK_COMBI": ("touch_count", "barrier_age", "break_margin_atr", "pressure_disp", "pressure_er", "pressure_mean_clv", "pressure_ema_slope", "pressure_duration", "buildup_n", "contraction", "overlap_mean", "progression", "counter_ratio", "room_r", "round_grid_room_r", "grid_feature_missing", "rho", "R_cash_atr", "inside_ratio"),
    "A3_PULLBACK_REVERSAL": ("pressure_disp", "pressure_er", "pressure_mean_clv", "pressure_ema_slope", "pressure_duration", "room_r", "round_grid_room_r", "grid_feature_missing", "rho", "R_cash_atr", "leg_amp_atr", "depth", "correction_duration", "corr_er", "structure_anchor", "ema_anchor"),
}


def clip_value(x: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, x))


def attach_model_context(candidate: Candidate, context: ModelContext) -> Candidate:
    return replace(candidate, features=candidate.features | {
        "room_r": context.room_r,
        "round_grid_room_r": context.round_grid_room_r,
        "grid_feature_missing": float(context.grid_feature_missing),
        "rho": context.rho,
        "R_cash_atr": context.r_cash_atr,
    })


def _required(candidate: Candidate, key: str) -> float:
    if key not in candidate.features:
        raise ValueError(f"missing required feature {key} for {candidate.arm}")
    value = candidate.features[key]
    if not isfinite(value):
        raise ValueError(f"nonfinite required feature {key} for {candidate.arm}")
    return value


def common_feature_vector(candidate: Candidate) -> list[float]:
    f = candidate.features
    for key in REQUIRED_COMMON_FIELDS.get(candidate.arm, ()):
        _required(candidate, key)
    values = [0.0] * 26
    values[0] = clip_value((f.get("touch_count", 0.0) - 3.0) / 3.0, 0.0, 1.0)
    values[1] = f.get("barrier_age_scaled", f.get("barrier_age", 0.0) / 12.0)
    values[2] = clip_value(f.get("break_margin_atr", 0.0), 0.0, 1.0)
    pressure_parts = [
        f.get("pressure_disp", 0.0) / 0.60,
        f.get("pressure_er", 0.0) / 0.55,
        f.get("pressure_mean_clv", 0.0) / 0.20,
        f.get("pressure_ema_slope", 0.0) / 0.10,
    ]
    values[3] = clip_value(mean(pressure_parts), 0.0, 2.0)
    values[4] = clip_value(f.get("pressure_duration", 0.0) / 12.0, 0.0, 1.0)
    values[5] = f.get("buildup_n", 0.0) / 8.0
    values[6] = 1.0 - f.get("contraction", 1.0)
    values[7] = f.get("overlap_mean", 0.0)
    values[8] = f.get("progression", 0.0)
    values[9] = 1.0 - f.get("counter_ratio", 1.0)
    values[10] = min(max(f.get("room_r", 0.0), 0.0), 4.0) / 4.0
    values[11] = min(max(f.get("round_grid_room_r", 0.0), 0.0), 4.0) / 4.0
    values[12] = f.get("rho", 0.0)
    values[13] = f.get("R_cash_atr", 0.0)
    values[14] = 1.0 if candidate.arm == "A2_PATTERN_BREAK_COMBI" else 0.0
    values[15] = f.get("inside_ratio", 0.0)
    values[16] = f.get("leg_amp_atr", 0.0)
    values[17] = f.get("depth", 0.0)
    values[18] = f.get("correction_duration", 0.0) / 6.0
    values[19] = 1.0 - f.get("corr_er", 1.0)
    values[20] = f.get("structure_anchor", 0.0)
    values[21] = f.get("ema_anchor", 0.0)
    values[22] = f.get("grid_feature_missing", 0.0)
    values[23] = 1.0 if candidate.arm == "A1_PATTERN_BREAK" else 0.0
    values[24] = 1.0 if candidate.arm == "A2_PATTERN_BREAK_COMBI" else 0.0
    values[25] = 1.0 if candidate.arm == "A3_PULLBACK_REVERSAL" else 0.0
    return values


def masked_features(candidate: Candidate, arm: str | None = None) -> list[float]:
    arm_name = arm or candidate.arm
    if arm_name != candidate.arm:
        for key in REQUIRED_COMMON_FIELDS.get(arm_name, ()):
            if key not in candidate.features:
                raise ValueError(f"missing required feature {key} for mask {arm_name}")
    raw = common_feature_vector(candidate)
    mask = set(ARM_MASKS[arm_name])
    return [raw[i - 1] if i in mask else 0.0 for i in range(1, 27)]


def fit_train_normalization(rows: Sequence[Sequence[float]]) -> NormalizationFit:
    if not rows:
        raise ValueError("empty training features")
    width = len(rows[0])
    if width != 26:
        raise ValueError("normalization requires exactly 26 raw dimensions")
    if any(len(row) != width for row in rows):
        raise ValueError("normalization row length mismatch")
    if any(not isfinite(x) for row in rows for x in row):
        raise ValueError("normalization requires finite values")
    cols = list(zip(*rows))
    medians: list[float] = []
    mads: list[float] = []
    constants: list[int] = []
    for idx, col in enumerate(cols):
        med = median(col)
        mad = median([abs(x - med) for x in col])
        medians.append(float(med))
        mads.append(float(mad))
        if mad == 0:
            constants.append(idx)
    return NormalizationFit(medians, mads, tuple(constants))


def apply_normalization(row: Sequence[float], fit: NormalizationFit) -> list[float]:
    if len(row) != len(fit.medians) or len(row) != len(fit.mads):
        raise ValueError("normalization dimension mismatch")
    if any(not isfinite(x) for x in row):
        raise ValueError("normalization input must be finite")
    out: list[float] = []
    for i, x in enumerate(row):
        if i in fit.constant_features:
            out.append(0.0)
        else:
            z = (x - fit.medians[i]) / (1.4826 * fit.mads[i])
            out.append(min(5.0, max(-5.0, z)))
    return out


def equal_year_weights(times: Sequence[datetime]) -> list[float]:
    if not times:
        raise ValueError("empty times")
    years = sorted({t.year for t in times})
    return [1.0 / len(years) / sum(1 for x in times if x.year == t.year) for t in times]


def _sigmoid(z: float) -> float:
    if z >= 0:
        e = exp(-z)
        return 1 / (1 + e)
    e = exp(z)
    return e / (1 + e)


def _weighted_logistic_objective_grad(beta: Sequence[float], x_rows: Sequence[Sequence[float]], y: Sequence[int], weights: Sequence[float], penalize_slope: bool = True) -> tuple[float, list[float]]:
    obj = 0.0
    grad = [0.0] * len(beta)
    for row, yi, wi in zip(x_rows, y, weights):
        z = beta[0] + sum(b * x for b, x in zip(beta[1:], row))
        p = _sigmoid(z)
        obj += wi * (-(yi * log(max(p, 1e-300)) + (1 - yi) * log(max(1 - p, 1e-300))))
        diff = wi * (p - yi)
        grad[0] += diff
        for j, x in enumerate(row, start=1):
            grad[j] += diff * x
    if penalize_slope:
        for j in range(1, len(beta)):
            obj += 0.5 * beta[j] * beta[j]
            grad[j] += beta[j]
    return obj, grad


def fit_weighted_logistic(x_rows: Sequence[Sequence[float]], y: Sequence[int], times: Sequence[datetime], constant_features: Sequence[int] = ()) -> LogisticFit:
    if not x_rows:
        raise ValueError("empty logistic design matrix")
    width = len(x_rows[0])
    if any(len(row) != width for row in x_rows):
        raise ValueError("logistic row length mismatch")
    if len(y) != len(x_rows) or len(times) != len(x_rows):
        raise ValueError("logistic x/y/times length mismatch")
    if any(yi not in (0, 1) for yi in y):
        raise ValueError("logistic labels must be 0/1")
    if any(not isfinite(x) for row in x_rows for x in row):
        raise ValueError("logistic design values must be finite")
    if len(set(y)) != 2:
        raise ValueError("single-class train set is fatal")
    weights = equal_year_weights(times)
    import numpy as np
    from scipy.optimize import minimize

    n = len(x_rows[0]) + 1
    beta0 = np.zeros(n)

    def fun(beta):
        obj, grad = _weighted_logistic_objective_grad(beta.tolist(), x_rows, y, weights)
        for idx in constant_features:
            grad[idx + 1] = beta[idx + 1]
        return obj, np.array(grad)

    res = minimize(fun, beta0, jac=True, method="L-BFGS-B", options={"maxiter": 1000, "ftol": 0.0, "gtol": 1e-12, "maxls": 50})
    beta = res.x.tolist()
    for idx in constant_features:
        beta[idx + 1] = 0.0
    obj, grad = _weighted_logistic_objective_grad(beta, x_rows, y, weights)
    for idx in constant_features:
        grad[idx + 1] = 0.0
    grad_inf = max(abs(g) for g in grad)
    if (not res.success) or res.nit > 1000 or grad_inf > 1e-10:
        raise ValueError(f"logistic optimizer failure success={res.success} nit={res.nit} grad_inf={grad_inf}")
    return LogisticFit(beta, True, int(res.nit), float(grad_inf), float(obj))


def predict_logistic(beta: Sequence[float], row: Sequence[float]) -> float:
    if len(beta) != len(row) + 1:
        raise ValueError("logistic prediction dimension mismatch")
    return _sigmoid(beta[0] + sum(b * x for b, x in zip(beta[1:], row)))


def fit_sigmoid_calibration(p_raw: Sequence[float], y: Sequence[int]) -> CalibrationFit:
    if len(p_raw) != len(y) or not p_raw:
        raise ValueError("calibration p/y length mismatch")
    if any(yi not in (0, 1) for yi in y):
        raise ValueError("calibration labels must be 0/1")
    if any((not isfinite(p)) or p <= 0 or p >= 1 for p in p_raw):
        raise ValueError("calibration probabilities must be finite and inside (0,1)")
    if len(set(y)) != 2:
        raise ValueError("single-class calibration set is fatal")
    import numpy as np
    from scipy.optimize import minimize

    logits = [log(min(1 - 1e-12, max(1e-12, p)) / (1 - min(1 - 1e-12, max(1e-12, p)))) for p in p_raw]
    weights = [1.0 / len(y)] * len(y)

    def fun(theta):
        a, b = theta.tolist()
        obj = 0.0
        ga = 0.0
        gb = 0.0
        for lgt, yi, wi in zip(logits, y, weights):
            p = _sigmoid(a * lgt + b)
            obj += wi * (-(yi * log(max(p, 1e-300)) + (1 - yi) * log(max(1 - p, 1e-300))))
            diff = wi * (p - yi)
            ga += diff * lgt
            gb += diff
        return obj, np.array([ga, gb])

    res = minimize(fun, np.array([1.0, 0.0]), jac=True, method="L-BFGS-B", options={"maxiter": 1000, "ftol": 0.0, "gtol": 1e-12, "maxls": 50})
    obj, grad = fun(res.x)
    grad_inf = float(max(abs(x) for x in grad.tolist()))
    if (not res.success) or res.nit > 1000 or grad_inf > 1e-10:
        raise ValueError(f"calibration optimizer failure success={res.success} nit={res.nit} grad_inf={grad_inf}")
    return CalibrationFit(float(res.x[0]), float(res.x[1]), True, int(res.nit), grad_inf, float(obj))


def apply_sigmoid_calibration(p_raw: float, fit: CalibrationFit) -> float:
    p = min(1 - 1e-12, max(1e-12, p_raw))
    return _sigmoid(fit.a * log(p / (1 - p)) + fit.b)


def schedule_state(prev: Bar, current: Bar, scheduled_closed: bool = False, in_position: bool = False) -> str:
    delta = current.utc_open - prev.utc_open
    if delta <= timedelta(0):
        return "INVALID_DATA"
    if delta == timedelta(minutes=5):
        return "CONTIGUOUS"
    if scheduled_closed:
        return "SCHEDULED_RESET"
    return "DATA_GAP_EXIT" if in_position else "UNEXPECTED_GAP_RESET_WARMUP_50"


def schedule_step(prev: Bar, current: Bar, schedule: BrokerSchedule, *, index: int, warmup_remaining: int, in_position: bool = False, setup_active: bool = False) -> ScheduleStep:
    if index in schedule.scheduled_closed_indices:
        return ScheduleStep("SKIP_GAP_CONTEXT" if setup_active else "SCHEDULED_RESET", 50)
    if index in schedule.remap_indices:
        return ScheduleStep("SKIP_GAP_CONTEXT" if setup_active else "SYMBOL_REMAP_RESET", 50)
    if schedule.weekend_coverage_only and current.utc_open.weekday() >= 5:
        return ScheduleStep("SKIP_GAP_CONTEXT" if setup_active else "WEEKEND_COVERAGE_ONLY_RESET", 50)
    if current.utc_open <= prev.utc_open:
        return ScheduleStep("INVALID_DATA", 50, True)
    raw = schedule_state(prev, current, scheduled_closed=index in schedule.scheduled_closed_indices, in_position=in_position)
    if raw == "CONTIGUOUS":
        return ScheduleStep("WARMING_UP" if warmup_remaining > 1 else "READY", max(0, warmup_remaining - 1))
    if raw == "DATA_GAP_EXIT":
        return ScheduleStep("DATA_GAP_EXIT", 50, True)
    if setup_active:
        return ScheduleStep("SKIP_GAP_CONTEXT", 50)
    return ScheduleStep(raw, 50)


@dataclass
class DailyArmLedger:
    consumed: set[tuple[str, datetime]]

    @classmethod
    def empty(cls) -> "DailyArmLedger":
        return cls(set())

    def try_consume(self, arm: str, when_utc: datetime) -> bool:
        key = (arm, when_utc.date())
        if key in self.consumed:
            return False
        self.consumed.add(key)
        return True
