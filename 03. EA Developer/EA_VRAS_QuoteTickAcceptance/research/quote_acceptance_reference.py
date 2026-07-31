"""Deterministic pure-Python reference for HYP-VRAS-EURUSD-M5-012.

Mirrors the frozen closed-bar arm and causal quote-tick acceptance FSM.
Collection-only: no orders, PnL, SL/TP or promotion logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCHEMA_VERSION = "vras_quote_acceptance.v1"
HYPOTHESIS_ID = "HYP-VRAS-EURUSD-M5-014"
SYMBOL = "EURUSD"
TIMEFRAME = "M5"

H1_EMA_PERIOD = 200
VWAP_BARS = 48
PREARM_RING = 60
PREARM_MIN = 30
AGE_MIN_MS = 30_000
AGE_MAX_MS = 120_000
MIN_QUOTE_UPDATES = 20
MIN_PRICE_CHANGES = 12
MIN_IMBALANCE = 0.60
MAX_SPREAD_RATIO = 1.50
MAX_GAP_MS = 15_000
POINT = 0.00001  # EURUSD 5-digit reference point

EVENT_ARMED = "ARMED"
EVENT_OBSERVE = "OBSERVE"
TERMINAL_ACCEPTED = "ACCEPTED_OBSERVATION"
TERMINAL_VWAP = "REJECT_VWAP_RECROSS"
TERMINAL_SPREAD = "REJECT_SPREAD_SPIKE"
TERMINAL_GAP = "REJECT_STALE_GAP"
TERMINAL_INVALID = "REJECT_INVALID_QUOTE"
TERMINAL_EXPIRE = "EXPIRE_NO_ACCEPTANCE"
TERMINAL_DEINIT = "DEINIT_ACTIVE_ARM"

TERMINAL_STATES = frozenset(
    {
        TERMINAL_ACCEPTED,
        TERMINAL_VWAP,
        TERMINAL_SPREAD,
        TERMINAL_GAP,
        TERMINAL_INVALID,
        TERMINAL_EXPIRE,
        TERMINAL_DEINIT,
    }
)

CSV_COLUMNS = [
    "schema_version",
    "hypothesis_id",
    "run_id",
    "event_time_msc",
    "event_time_utc",
    "symbol",
    "event",
    "direction",
    "arm_bar_time",
    "arm_time_msc",
    "age_ms",
    "bid",
    "ask",
    "mid",
    "spread_points",
    "prearm_median_spread_points",
    "quote_updates",
    "price_changes",
    "directional_moves",
    "opposite_moves",
    "imbalance",
    "directional_net_points",
    "max_gap_ms",
    "max_spread_ratio",
    "frozen_vwap",
    "data_source",
    "promotion_eligible",
]


def is_finite_positive(value: float) -> bool:
    return value is not None and value == value and value not in (float("inf"), float("-inf")) and value > 0.0


def quote_is_valid(time_msc: int, bid: float, ask: float, last_time_msc: Optional[int]) -> bool:
    if last_time_msc is not None and time_msc <= last_time_msc:
        return False
    if not is_finite_positive(bid) or not is_finite_positive(ask):
        return False
    if ask < bid:
        return False
    return True


def mid_price(bid: float, ask: float) -> float:
    return (bid + ask) / 2.0


def spread_price(bid: float, ask: float) -> float:
    return ask - bid


def spread_points(bid: float, ask: float, point: float = POINT) -> float:
    if point <= 0.0:
        return 0.0
    return (ask - bid) / point


def normalize_server_tick_msc(raw_time_msc: int, server_utc_offset_ms: int) -> int:
    normalized = int(raw_time_msc) - int(server_utc_offset_ms)
    if normalized <= 0:
        raise ValueError("normalized tick timestamp must be positive")
    return normalized


def compute_rolling_vwap(bars: Sequence[Dict[str, float]]) -> float:
    """bars: completed M5 shifts 1..N as dicts with high/low/close/tick_volume."""
    sum_pv = 0.0
    sum_v = 0.0
    for bar in bars:
        volume = float(bar.get("tick_volume", 0.0) or 0.0)
        if volume <= 0.0:
            continue
        typical = (float(bar["high"]) + float(bar["low"]) + float(bar["close"])) / 3.0
        sum_pv += typical * volume
        sum_v += volume
    if sum_v <= 0.0:
        return 0.0
    return sum_pv / sum_v


def evaluate_closed_bar_arm(
    h1_close: float,
    h1_ema: float,
    shift1_high: float,
    shift1_low: float,
    shift1_close: float,
    shift2_high: float,
    shift2_low: float,
    vwap: float,
) -> Optional[str]:
    """Return 'long', 'short', or None. Closed-bar only (shift-1/2 inputs)."""
    if vwap <= 0.0:
        return None
    if (
        h1_close > h1_ema
        and shift1_low <= vwap
        and shift1_close > vwap
        and shift1_close > shift2_high
    ):
        return "long"
    if (
        h1_close < h1_ema
        and shift1_high >= vwap
        and shift1_close < vwap
        and shift1_close < shift2_low
    ):
        return "short"
    return None


def prearm_median_spread(spreads: Sequence[float]) -> float:
    if not spreads:
        return 0.0
    return float(median(list(spreads)))


def imbalance_ratio(directional: int, opposite: int) -> float:
    denom = directional + opposite
    if denom <= 0:
        return 0.0
    return directional / denom


@dataclass
class TelemetryEvent:
    event: str
    direction: str
    event_time_msc: int
    arm_bar_time: int
    arm_time_msc: int
    age_ms: int
    bid: float
    ask: float
    mid: float
    spread_points: float
    prearm_median_spread_points: float
    quote_updates: int
    price_changes: int
    directional_moves: int
    opposite_moves: int
    imbalance: float
    directional_net_points: float
    max_gap_ms: int
    max_spread_ratio: float
    frozen_vwap: float
    data_source: str = "LIVE_QUOTES"
    promotion_eligible: bool = False
    hypothesis_id: str = HYPOTHESIS_ID
    schema_version: str = SCHEMA_VERSION
    symbol: str = SYMBOL
    run_id: str = "ref"

    def as_row(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "hypothesis_id": self.hypothesis_id,
            "run_id": self.run_id,
            "event_time_msc": self.event_time_msc,
            "event_time_utc": "",
            "symbol": self.symbol,
            "event": self.event,
            "direction": self.direction,
            "arm_bar_time": self.arm_bar_time,
            "arm_time_msc": self.arm_time_msc,
            "age_ms": self.age_ms,
            "bid": self.bid,
            "ask": self.ask,
            "mid": self.mid,
            "spread_points": self.spread_points,
            "prearm_median_spread_points": self.prearm_median_spread_points,
            "quote_updates": self.quote_updates,
            "price_changes": self.price_changes,
            "directional_moves": self.directional_moves,
            "opposite_moves": self.opposite_moves,
            "imbalance": self.imbalance,
            "directional_net_points": self.directional_net_points,
            "max_gap_ms": self.max_gap_ms,
            "max_spread_ratio": self.max_spread_ratio,
            "frozen_vwap": self.frozen_vwap,
            "data_source": self.data_source,
            "promotion_eligible": False,
        }


@dataclass
class QuoteAcceptanceEngine:
    """Causal pre-arm ring + one-active-arm acceptance FSM."""

    point: float = POINT
    data_source: str = "LIVE_QUOTES"
    run_id: str = "ref"
    prearm_spreads: List[float] = field(default_factory=list)
    last_quote_time_msc: Optional[int] = None
    pending_direction: Optional[str] = None
    pending_vwap: float = 0.0
    pending_arm_bar_time: int = 0
    arm_active: bool = False
    arm_terminal: Optional[str] = None
    direction: str = ""
    frozen_vwap: float = 0.0
    arm_bar_time: int = 0
    arm_time_msc: int = 0
    arm_bid: float = 0.0
    arm_ask: float = 0.0
    arm_mid: float = 0.0
    arm_spread: float = 0.0
    prearm_median: float = 0.0
    prearm_median_points: float = 0.0
    last_mid: float = 0.0
    last_obs_time_msc: int = 0
    quote_updates: int = 0
    price_changes: int = 0
    directional_moves: int = 0
    opposite_moves: int = 0
    max_gap_ms: int = 0
    max_spread_since_arm: float = 0.0
    events: List[TelemetryEvent] = field(default_factory=list)

    def _push_prearm(self, spread: float) -> None:
        self.prearm_spreads.append(spread)
        if len(self.prearm_spreads) > PREARM_RING:
            self.prearm_spreads = self.prearm_spreads[-PREARM_RING:]

    def try_arm_from_closed_bar(
        self,
        direction: Optional[str],
        vwap: float,
        arm_bar_time: int,
    ) -> bool:
        """Queue a closed-bar arm. Does not overwrite an active or pending arm."""
        if self.arm_active or self.pending_direction is not None:
            return False
        if direction not in ("long", "short"):
            return False
        if vwap <= 0.0:
            return False
        self.pending_direction = direction
        self.pending_vwap = vwap
        self.pending_arm_bar_time = arm_bar_time
        return True

    def _snapshot_event(
        self,
        event: str,
        time_msc: int,
        bid: float,
        ask: float,
    ) -> TelemetryEvent:
        mid = mid_price(bid, ask)
        spr_pts = spread_points(bid, ask, self.point)
        age = 0 if self.arm_time_msc <= 0 else int(time_msc - self.arm_time_msc)
        imb = imbalance_ratio(self.directional_moves, self.opposite_moves)
        net = 0.0
        if self.arm_active or self.arm_time_msc > 0:
            sign = 1.0 if self.direction == "long" else -1.0
            net = sign * (mid - self.arm_mid) / self.point if self.point > 0 else 0.0
        max_ratio = 0.0
        if self.prearm_median > 0.0:
            max_ratio = self.max_spread_since_arm / self.prearm_median
        return TelemetryEvent(
            event=event,
            direction=self.direction,
            event_time_msc=time_msc,
            arm_bar_time=self.arm_bar_time,
            arm_time_msc=self.arm_time_msc,
            age_ms=age,
            bid=bid,
            ask=ask,
            mid=mid,
            spread_points=spr_pts,
            prearm_median_spread_points=self.prearm_median_points,
            quote_updates=self.quote_updates,
            price_changes=self.price_changes,
            directional_moves=self.directional_moves,
            opposite_moves=self.opposite_moves,
            imbalance=imb,
            directional_net_points=net,
            max_gap_ms=self.max_gap_ms,
            max_spread_ratio=max_ratio,
            frozen_vwap=self.frozen_vwap,
            data_source=self.data_source,
            run_id=self.run_id,
        )

    def _terminate(self, terminal: str, time_msc: int, bid: float, ask: float) -> TelemetryEvent:
        assert terminal in TERMINAL_STATES
        self.arm_terminal = terminal
        self.arm_active = False
        self.pending_direction = None
        ev = self._snapshot_event(terminal, time_msc, bid, ask)
        self.events.append(ev)
        return ev

    def _freeze_arm(self, time_msc: int, bid: float, ask: float) -> Optional[TelemetryEvent]:
        if self.pending_direction is None:
            return None
        if len(self.prearm_spreads) < PREARM_MIN:
            # Fail-closed: drop pending arm, keep quote for pre-arm history.
            self.pending_direction = None
            self.pending_vwap = 0.0
            self.pending_arm_bar_time = 0
            if quote_is_valid(time_msc, bid, ask, self.last_quote_time_msc):
                self.last_quote_time_msc = time_msc
                self._push_prearm(spread_price(bid, ask))
            return None
        if not quote_is_valid(time_msc, bid, ask, self.last_quote_time_msc):
            return None

        med = prearm_median_spread(self.prearm_spreads)
        if med <= 0.0:
            self.pending_direction = None
            self.pending_vwap = 0.0
            self.pending_arm_bar_time = 0
            self.last_quote_time_msc = time_msc
            self._push_prearm(spread_price(bid, ask))
            return None
        self.direction = self.pending_direction
        self.frozen_vwap = self.pending_vwap
        self.arm_bar_time = self.pending_arm_bar_time
        self.arm_time_msc = time_msc
        self.arm_bid = bid
        self.arm_ask = ask
        self.arm_mid = mid_price(bid, ask)
        self.arm_spread = spread_price(bid, ask)
        self.prearm_median = med
        self.prearm_median_points = med / self.point if self.point > 0 else 0.0
        self.last_mid = self.arm_mid
        self.last_obs_time_msc = time_msc
        self.quote_updates = 0
        self.price_changes = 0
        self.directional_moves = 0
        self.opposite_moves = 0
        self.max_gap_ms = 0
        self.max_spread_since_arm = self.arm_spread
        self.arm_active = True
        self.arm_terminal = None
        self.pending_direction = None
        self.last_quote_time_msc = time_msc
        ev = self._snapshot_event(EVENT_ARMED, time_msc, bid, ask)
        self.events.append(ev)
        return ev

    def _vwap_violated(self, bid: float, ask: float) -> bool:
        if self.direction == "long":
            return bid <= self.frozen_vwap
        if self.direction == "short":
            return ask >= self.frozen_vwap
        return True

    def _acceptance_gates(self, bid: float, ask: float, age_ms: int) -> bool:
        if age_ms < AGE_MIN_MS or age_ms > AGE_MAX_MS:
            return False
        if self.quote_updates < MIN_QUOTE_UPDATES:
            return False
        if self.price_changes < MIN_PRICE_CHANGES:
            return False
        imb = imbalance_ratio(self.directional_moves, self.opposite_moves)
        if imb < MIN_IMBALANCE:
            return False
        sign = 1.0 if self.direction == "long" else -1.0
        net_exp = sign * (mid_price(bid, ask) - self.arm_mid)
        if net_exp < self.arm_spread:
            return False
        cur_spread = spread_price(bid, ask)
        if cur_spread > self.prearm_median:
            return False
        if self.max_spread_since_arm > MAX_SPREAD_RATIO * self.prearm_median:
            return False
        if self.max_gap_ms > MAX_GAP_MS:
            return False
        if self._vwap_violated(bid, ask):
            return False
        return True

    def on_quote(self, time_msc: int, bid: float, ask: float) -> Optional[TelemetryEvent]:
        """Process one chronological quote. Returns telemetry event if emitted."""
        # Immutable terminal: ignore further quotes for a completed arm.
        if self.arm_terminal is not None and not self.arm_active and self.pending_direction is None:
            # Allow new pre-arm accumulation after terminal for a later arm.
            if quote_is_valid(time_msc, bid, ask, self.last_quote_time_msc):
                self.last_quote_time_msc = time_msc
                self._push_prearm(spread_price(bid, ask))
            return None

        if self.arm_active:
            if not quote_is_valid(time_msc, bid, ask, self.last_quote_time_msc):
                return self._terminate(TERMINAL_INVALID, time_msc, bid, ask)

            gap = int(time_msc - self.last_obs_time_msc)
            if gap > self.max_gap_ms:
                self.max_gap_ms = gap
            cur_spread = spread_price(bid, ask)
            if cur_spread > self.max_spread_since_arm:
                self.max_spread_since_arm = cur_spread

            mid = mid_price(bid, ask)
            self.quote_updates += 1
            if mid != self.last_mid:
                self.price_changes += 1
                if self.direction == "long":
                    if mid > self.last_mid:
                        self.directional_moves += 1
                    elif mid < self.last_mid:
                        self.opposite_moves += 1
                else:
                    if mid < self.last_mid:
                        self.directional_moves += 1
                    elif mid > self.last_mid:
                        self.opposite_moves += 1
            self.last_mid = mid
            self.last_obs_time_msc = time_msc
            self.last_quote_time_msc = time_msc
            age = int(time_msc - self.arm_time_msc)

            if self._vwap_violated(bid, ask):
                return self._terminate(TERMINAL_VWAP, time_msc, bid, ask)
            if self.prearm_median > 0.0 and self.max_spread_since_arm > MAX_SPREAD_RATIO * self.prearm_median:
                return self._terminate(TERMINAL_SPREAD, time_msc, bid, ask)
            if self.max_gap_ms > MAX_GAP_MS:
                return self._terminate(TERMINAL_GAP, time_msc, bid, ask)
            if age > AGE_MAX_MS:
                return self._terminate(TERMINAL_EXPIRE, time_msc, bid, ask)
            if self._acceptance_gates(bid, ask, age):
                return self._terminate(TERMINAL_ACCEPTED, time_msc, bid, ask)

            ev = self._snapshot_event(EVENT_OBSERVE, time_msc, bid, ask)
            self.events.append(ev)
            return ev

        # Pending freeze path.
        if self.pending_direction is not None:
            return self._freeze_arm(time_msc, bid, ask)

        # Idle pre-arm ring (dedup / invalid skipped).
        if quote_is_valid(time_msc, bid, ask, self.last_quote_time_msc):
            self.last_quote_time_msc = time_msc
            self._push_prearm(spread_price(bid, ask))
        return None

    def on_deinit(self, time_msc: int, bid: float = 0.0, ask: float = 0.0) -> Optional[TelemetryEvent]:
        if not self.arm_active:
            return None
        if bid <= 0.0 or ask <= 0.0:
            bid = self.arm_bid
            ask = self.arm_ask
        return self._terminate(TERMINAL_DEINIT, time_msc, bid, ask)

    def seed_prearm_quotes(self, quotes: Sequence[Tuple[int, float, float]]) -> None:
        for time_msc, bid, ask in quotes:
            self.on_quote(time_msc, bid, ask)


def build_monotonic_prearm(
    n: int = PREARM_MIN,
    start_msc: int = 1_000_000,
    bid: float = 1.10000,
    spread: float = 0.00010,
    step_msc: int = 100,
) -> List[Tuple[int, float, float]]:
    out: List[Tuple[int, float, float]] = []
    for i in range(n):
        t = start_msc + i * step_msc
        out.append((t, bid, bid + spread))
    return out
