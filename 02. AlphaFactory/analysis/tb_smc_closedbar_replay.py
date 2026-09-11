"""
TB-2026 closed-bar replay twin for TB_Smart_Money_Concept_2026.mq5.

Dialect lock: TB names only. Origin Cell is not an Order Block.
No MetaTrader5 import. No live attach. No ICT-OB / CHoCH / PD / EQH / MTF.

Port of ProcessClosedEngineBar + Wilder ATR(14) + pivots, close enough
to prove the fixtures. Buffer numbers match the MQ5 contract.

Contract version: 2.3 (2.2 lockout + live-swing sweeps + no orphan CE).
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

# MT5 EMPTY_VALUE is DBL_MAX; any non-finite / sentinel is "no value".
EMPTY = float("inf")
TB_ATR_LENGTH = 14
TB_ORIGIN_LOOKBACK = 8
TB_CONTRACT_VERSION = 2.3


def is_value(value: float) -> bool:
    return value != EMPTY and math.isfinite(value)


@dataclass
class OriginCell:
    start_index: int
    event_index: int
    top: float
    bottom: float
    side: int


@dataclass
class PriceVoid:
    start_index: int
    event_index: int
    top: float
    bottom: float
    ce: float
    side: int
    upper_active: bool = True
    lower_active: bool = True


@dataclass
class VoidMidline:
    start_index: int
    event_index: int
    ce: float
    side: int


@dataclass
class EngineConfig:
    swing_length: int = 5
    displacement_atr: float = 0.45
    cells_kept: int = 3
    voids_kept: int = 4
    sweep_reclaim_atr: float = 0.05
    minimum_void_atr: float = 0.0
    minimum_cell_atr: float = 0.0
    maximum_cell_age_bars: int = 0
    maximum_void_age_bars: int = 0
    # Honest default: no sweep on a swing already consumed by BOS.
    # false restores the old TV dead-sweep paint.
    sweeps_require_live_swing: bool = True
    require_both_swings: bool = True
    enable_structure: bool = True
    enable_cells: bool = True
    enable_voids: bool = True
    enable_sweeps: bool = True
    void_whole_zone: bool = False
    # Display toggles — TV profile must NEVER gate calculation.
    show_structure: bool = True
    show_cells: bool = True
    show_voids: bool = True
    show_sweeps: bool = True
    tv_profile: bool = True


@dataclass
class BarOut:
    index: int
    closed: bool
    bos_up: float = 0.0
    mss_up: float = 0.0
    bos_down: float = 0.0
    mss_down: float = 0.0
    sweep_high: float = 0.0
    sweep_low: float = 0.0
    bull_void: float = 0.0
    bear_void: float = 0.0
    impulse_up: float = 0.0
    impulse_down: float = 0.0
    swing_high: float = EMPTY
    swing_low: float = EMPTY
    swing_high_live: float = 0.0
    swing_low_live: float = 0.0
    bias: float = 0.0
    cell_top: float = EMPTY
    cell_bottom: float = EMPTY
    cell_side: float = 0.0
    void_top: float = EMPTY
    void_bottom: float = EMPTY
    void_ce: float = EMPTY
    void_side: float = 0.0
    void_upper_active: float = 0.0
    void_lower_active: float = 0.0
    void_active_top: float = EMPTY
    void_active_bottom: float = EMPTY
    closed_bar_valid: float = 0.0
    structure_event: float = 0.0
    atr: float = EMPTY
    break_level: float = EMPTY
    break_origin: int = -1
    cell_origin: int = -1
    void_start: int = -1
    displacement_ratio: float = EMPTY
    contract_version: float = TB_CONTRACT_VERSION
    cell_count: int = 0
    void_count: int = 0
    living_ce_count: int = 0
    pending_high: float = 0.0
    pending_low: float = 0.0
    pending_high_level: float = EMPTY
    pending_low_level: float = EMPTY
    pending_high_origin: int = -1
    pending_low_origin: int = -1


def _blank_bar(index: int, closed: bool) -> BarOut:
    return BarOut(index=index, closed=closed)


class TbClosedBarEngine:
    """1:1-enough port of the TB-2026 closed-bar engine (contract 2.3)."""

    def __init__(self, config: Optional[EngineConfig] = None) -> None:
        self.cfg = config or EngineConfig()
        self.cells: List[OriginCell] = []
        self.voids: List[PriceVoid] = []
        self.void_mids: List[VoidMidline] = []
        self.swing_high = EMPTY
        self.swing_low = EMPTY
        self.previous_swing_high = EMPTY
        self.previous_swing_low = EMPTY
        self.swing_high_live = False
        self.swing_low_live = False
        self.swing_high_index = -1
        self.swing_low_index = -1
        self.bias = 0
        self.trail_high = EMPTY
        self.trail_low = EMPTY
        self.trail_high_index = -1
        self.trail_low_index = -1
        # BROKEN_UNCONFIRMED: not an Order Block.
        self.pending_high_active = False
        self.pending_high_level = EMPTY
        self.pending_high_origin = -1
        self.pending_low_active = False
        self.pending_low_level = EMPTY
        self.pending_low_origin = -1

    def reset(self) -> None:
        self.__init__(self.cfg)

    def _atr_at(self, index: int, true_range: Sequence[float], atr: Sequence[float]) -> float:
        if index < TB_ATR_LENGTH - 1:
            return EMPTY
        if index == TB_ATR_LENGTH - 1:
            return sum(true_range[i] for i in range(TB_ATR_LENGTH)) / TB_ATR_LENGTH
        if not is_value(atr[index - 1]):
            return EMPTY
        return (atr[index - 1] * (TB_ATR_LENGTH - 1) + true_range[index]) / TB_ATR_LENGTH

    def is_pivot_high(
        self, index: int, high: Sequence[float]
    ) -> Tuple[bool, float, int]:
        pivot_index = index - self.cfg.swing_length
        # Invariant: this call IS the pivot's confirmation bar — the pivot at
        # pivot_index is only knowable once bars pivot_index+1 ..
        # pivot_index+swing_length have closed, i.e. exactly at `index`.
        # (The old `index < pivot_index + swing_length` guard could never
        # fire; it was dead code.)
        assert pivot_index + self.cfg.swing_length == index
        if pivot_index < self.cfg.swing_length:
            return False, EMPTY, -1
        value = high[pivot_index]
        length = self.cfg.swing_length
        for offset in range(1, length + 1):
            if high[pivot_index - offset] > value or high[pivot_index + offset] > value:
                return False, EMPTY, -1
        return True, value, pivot_index

    def is_pivot_low(
        self, index: int, low: Sequence[float]
    ) -> Tuple[bool, float, int]:
        pivot_index = index - self.cfg.swing_length
        # Same invariant as is_pivot_high: `index` is the confirmation bar.
        assert pivot_index + self.cfg.swing_length == index
        if pivot_index < self.cfg.swing_length:
            return False, EMPTY, -1
        value = low[pivot_index]
        length = self.cfg.swing_length
        for offset in range(1, length + 1):
            if low[pivot_index - offset] < value or low[pivot_index + offset] < value:
                return False, EMPTY, -1
        return True, value, pivot_index

    def _push_cell(self, cell: OriginCell) -> None:
        self.cells.insert(0, cell)
        while len(self.cells) > self.cfg.cells_kept:
            self.cells.pop()

    def _remove_cell(self, index: int) -> None:
        if 0 <= index < len(self.cells):
            del self.cells[index]

    def _remove_void_mid_by_event(self, event_index: int) -> None:
        self.void_mids = [m for m in self.void_mids if m.event_index != event_index]

    def _push_void_mid(self, zone: PriceVoid) -> None:
        self.void_mids.insert(
            0,
            VoidMidline(
                start_index=zone.start_index,
                event_index=zone.event_index,
                ce=zone.ce,
                side=zone.side,
            ),
        )
        while len(self.void_mids) > self.cfg.voids_kept:
            self.void_mids.pop()

    def _drop_void(self, index: int) -> None:
        if 0 <= index < len(self.voids):
            event_index = self.voids[index].event_index
            del self.voids[index]
            self._remove_void_mid_by_event(event_index)

    def _push_void(self, zone: PriceVoid) -> None:
        self.voids.insert(0, zone)
        self._push_void_mid(zone)
        if self.cfg.void_whole_zone:
            while len(self.voids) > self.cfg.voids_kept:
                self._drop_void(len(self.voids) - 1)
        else:
            limit = self.cfg.voids_kept * 2
            while self._active_void_halves() > limit:
                removed = False
                for i in range(len(self.voids) - 1, -1, -1):
                    if self.voids[i].upper_active:
                        self.voids[i].upper_active = False
                        removed = True
                    elif self.voids[i].lower_active:
                        self.voids[i].lower_active = False
                        removed = True
                    if removed:
                        if not self.voids[i].upper_active and not self.voids[i].lower_active:
                            self._drop_void(i)
                        break
                if not removed:
                    break

    def _active_void_halves(self) -> int:
        return sum(int(v.upper_active) + int(v.lower_active) for v in self.voids)

    def _living_ce_count(self) -> int:
        living = 0
        for mid in self.void_mids:
            for zone in self.voids:
                if zone.event_index == mid.event_index and (zone.upper_active or zone.lower_active):
                    living += 1
                    break
        return living

    def _publish(self, index: int, closed: bool, atr: float) -> BarOut:
        out = _blank_bar(index, closed)
        atr_valid = is_value(atr) and atr > 0.0
        out.atr = atr
        out.bias = float(self.bias)
        out.swing_high = self.swing_high
        out.swing_low = self.swing_low
        # Live=0 after any close-through. Pending BROKEN_UNCONFIRMED is not an OB.
        out.swing_high_live = 1.0 if self.swing_high_live else 0.0
        out.swing_low_live = 1.0 if self.swing_low_live else 0.0
        out.pending_high = 1.0 if self.pending_high_active else 0.0
        out.pending_low = 1.0 if self.pending_low_active else 0.0
        out.pending_high_level = self.pending_high_level
        out.pending_low_level = self.pending_low_level
        out.pending_high_origin = self.pending_high_origin
        out.pending_low_origin = self.pending_low_origin
        out.contract_version = TB_CONTRACT_VERSION
        out.cell_count = len(self.cells)
        out.void_count = len(self.voids)
        out.living_ce_count = self._living_ce_count()
        swing_ready = (
            (is_value(self.swing_high) and is_value(self.swing_low))
            if self.cfg.require_both_swings
            else (is_value(self.swing_high) or is_value(self.swing_low))
        )
        out.closed_bar_valid = 1.0 if (closed and atr_valid and swing_ready) else 0.0
        if self.cells:
            newest = self.cells[0]
            out.cell_top = newest.top
            out.cell_bottom = newest.bottom
            out.cell_side = float(newest.side)
            out.cell_origin = newest.start_index
        if self.voids:
            newest_v = self.voids[0]
            out.void_top = newest_v.top
            out.void_bottom = newest_v.bottom
            out.void_ce = newest_v.ce
            out.void_side = float(newest_v.side)
            out.void_upper_active = 1.0 if newest_v.upper_active else 0.0
            out.void_lower_active = 1.0 if newest_v.lower_active else 0.0
            out.void_active_top = newest_v.top if newest_v.upper_active else newest_v.ce
            out.void_active_bottom = newest_v.bottom if newest_v.lower_active else newest_v.ce
            out.void_start = newest_v.start_index
        return out

    def process_closed_engine_bar(
        self,
        index: int,
        open_: Sequence[float],
        high: Sequence[float],
        low: Sequence[float],
        close: Sequence[float],
        atr: float,
    ) -> BarOut:
        # Snapshot at the start. Break / sweep / cells use this, then pivots update.
        snap_high = self.swing_high
        snap_low = self.swing_low
        snap_high_live = self.swing_high_live
        snap_low_live = self.swing_low_live
        snap_high_index = self.swing_high_index
        snap_low_index = self.swing_low_index
        self.previous_swing_high = snap_high
        self.previous_swing_low = snap_low

        out = _blank_bar(index, True)
        out.atr = atr
        out.contract_version = TB_CONTRACT_VERSION

        atr_valid = is_value(atr) and atr > 0.0
        body = abs(close[index] - open_[index])
        if atr_valid:
            out.displacement_ratio = body / atr
        impulse_up = atr_valid and close[index] > open_[index] and body >= atr * self.cfg.displacement_atr
        impulse_down = atr_valid and close[index] < open_[index] and body >= atr * self.cfg.displacement_atr
        # Buffer 11/12 = every impulse candle, not "displacement of the BOS bar only".
        out.impulse_up = 1.0 if impulse_up else 0.0
        out.impulse_down = 1.0 if impulse_down else 0.0

        # InpShow* never gates calculation (TV or EA). enable_* is the only switch.
        _ = (
            self.cfg.show_structure,
            self.cfg.show_cells,
            self.cfg.show_voids,
            self.cfg.show_sweeps,
            self.cfg.tv_profile,
        )
        calculate_structure = self.cfg.enable_structure
        calculate_cells = self.cfg.enable_cells
        calculate_voids = self.cfg.enable_voids
        calculate_sweeps = self.cfg.enable_sweeps

        cross_up = (
            index > 0
            and is_value(snap_high)
            and close[index] > snap_high
            and close[index - 1] <= snap_high
        )
        cross_down = (
            index > 0
            and is_value(snap_low)
            and close[index] < snap_low
            and close[index - 1] >= snap_low
        )
        # Immediate: live + fresh close-through + impulse (unchanged).
        # Deferred: pending BROKEN_UNCONFIRMED + same-direction impulse still
        # beyond the original level. Do not require a new close[i-1] cross.
        bull_break = False
        bull_break_level = snap_high
        bull_break_origin = snap_high_index
        bear_break = False
        bear_break_level = snap_low
        bear_break_origin = snap_low_index

        if calculate_structure:
            if snap_high_live and cross_up and impulse_up:
                bull_break = True
            elif (
                self.pending_high_active
                and impulse_up
                and is_value(self.pending_high_level)
                and close[index] > self.pending_high_level
            ):
                bull_break = True
                bull_break_level = self.pending_high_level
                bull_break_origin = self.pending_high_origin
            elif snap_high_live and cross_up:
                self.swing_high_live = False
                self.pending_high_active = True
                self.pending_high_level = snap_high
                self.pending_high_origin = snap_high_index
            elif (
                self.pending_high_active
                and is_value(self.pending_high_level)
                and close[index] <= self.pending_high_level
            ):
                self.pending_high_active = False
                self.pending_high_level = EMPTY
                self.pending_high_origin = -1
                self.swing_high_live = True

            if snap_low_live and cross_down and impulse_down:
                bear_break = True
            elif (
                self.pending_low_active
                and impulse_down
                and is_value(self.pending_low_level)
                and close[index] < self.pending_low_level
            ):
                bear_break = True
                bear_break_level = self.pending_low_level
                bear_break_origin = self.pending_low_origin
            elif snap_low_live and cross_down:
                self.swing_low_live = False
                self.pending_low_active = True
                self.pending_low_level = snap_low
                self.pending_low_origin = snap_low_index
            elif (
                self.pending_low_active
                and is_value(self.pending_low_level)
                and close[index] >= self.pending_low_level
            ):
                self.pending_low_active = False
                self.pending_low_level = EMPTY
                self.pending_low_origin = -1
                self.swing_low_live = True

        if bull_break:
            is_mss = self.bias < 0  # FLAT first break is BOS, never MSS.
            out.mss_up = 1.0 if is_mss else 0.0
            out.bos_up = 0.0 if is_mss else 1.0
            out.structure_event = 2.0 if is_mss else 1.0
            out.break_level = bull_break_level
            out.break_origin = bull_break_origin
            self.bias = 1
            self.swing_high_live = False
            self.pending_high_active = False
            self.pending_high_level = EMPTY
            self.pending_high_origin = -1
            if calculate_cells:
                cell = OriginCell(
                    start_index=index,
                    event_index=index,
                    top=high[index],
                    bottom=low[index],
                    side=1,
                )
                lookback = min(TB_ORIGIN_LOOKBACK, index)
                for k in range(1, lookback + 1):
                    if low[index - k] <= cell.bottom:
                        cell.bottom = low[index - k]
                        cell.top = high[index - k]
                        cell.start_index = index - k
                cell_atr = (cell.top - cell.bottom) / atr if atr_valid else 0.0
                if self.cfg.minimum_cell_atr <= 0.0 or cell_atr >= self.cfg.minimum_cell_atr:
                    self._push_cell(cell)

        if bear_break:
            is_mss = self.bias > 0
            out.mss_down = 1.0 if is_mss else 0.0
            out.bos_down = 0.0 if is_mss else 1.0
            out.structure_event = -2.0 if is_mss else -1.0
            out.break_level = bear_break_level
            out.break_origin = bear_break_origin
            self.bias = -1
            self.swing_low_live = False
            self.pending_low_active = False
            self.pending_low_level = EMPTY
            self.pending_low_origin = -1
            if calculate_cells:
                cell = OriginCell(
                    start_index=index,
                    event_index=index,
                    top=high[index],
                    bottom=low[index],
                    side=-1,
                )
                lookback = min(TB_ORIGIN_LOOKBACK, index)
                for k in range(1, lookback + 1):
                    if high[index - k] >= cell.top:
                        cell.top = high[index - k]
                        cell.bottom = low[index - k]
                        cell.start_index = index - k
                cell_atr = (cell.top - cell.bottom) / atr if atr_valid else 0.0
                if self.cfg.minimum_cell_atr <= 0.0 or cell_atr >= self.cfg.minimum_cell_atr:
                    self._push_cell(cell)

        for i in range(len(self.cells) - 1, -1, -1):
            invalid = (
                (self.cells[i].side > 0 and low[index] < self.cells[i].bottom)
                or (self.cells[i].side < 0 and high[index] > self.cells[i].top)
            )
            expired = (
                self.cfg.maximum_cell_age_bars > 0
                and index - self.cells[i].event_index > self.cfg.maximum_cell_age_bars
            )
            if invalid or expired:
                self._remove_cell(i)

        bull_void_geometry = (
            calculate_voids
            and index >= 2
            and low[index] > high[index - 2]
            and close[index - 1] > high[index - 2]
        )
        bear_void_geometry = (
            calculate_voids
            and index >= 2
            and high[index] < low[index - 2]
            and close[index - 1] < low[index - 2]
        )
        bull_gap = (low[index] - high[index - 2]) if bull_void_geometry else 0.0
        bear_gap = (low[index - 2] - high[index]) if bear_void_geometry else 0.0
        bull_void = bull_void_geometry and (
            self.cfg.minimum_void_atr <= 0.0
            or (atr_valid and bull_gap / atr >= self.cfg.minimum_void_atr)
        )
        bear_void = bear_void_geometry and (
            self.cfg.minimum_void_atr <= 0.0
            or (atr_valid and bear_gap / atr >= self.cfg.minimum_void_atr)
        )
        out.bull_void = 1.0 if bull_void else 0.0
        out.bear_void = 1.0 if bear_void else 0.0

        if bull_void:
            zone = PriceVoid(
                start_index=index - 2,
                event_index=index,
                top=low[index],
                bottom=high[index - 2],
                ce=0.5 * (low[index] + high[index - 2]),
                side=1,
            )
            self._push_void(zone)
        if bear_void:
            zone = PriceVoid(
                start_index=index - 2,
                event_index=index,
                top=low[index - 2],
                bottom=high[index],
                ce=0.5 * (low[index - 2] + high[index]),
                side=-1,
            )
            self._push_void(zone)

        # Fill = one candle spans the entire half. Touching CE is not a fill.
        # Birth bar cannot self-fill. Both halves dead → delete CE with the zone.
        for i in range(len(self.voids) - 1, -1, -1):
            if self.voids[i].event_index == index:
                continue
            if self.voids[i].upper_active and low[index] < self.voids[i].ce and high[index] > self.voids[i].top:
                self.voids[i].upper_active = False
            if self.voids[i].lower_active and low[index] < self.voids[i].bottom and high[index] > self.voids[i].ce:
                self.voids[i].lower_active = False
            expired = (
                self.cfg.maximum_void_age_bars > 0
                and index - self.voids[i].event_index > self.cfg.maximum_void_age_bars
            )
            if expired:
                self._drop_void(i)
            elif not self.voids[i].upper_active and not self.voids[i].lower_active:
                self._drop_void(i)

        high_sweep_state = (not self.cfg.sweeps_require_live_swing) or snap_high_live
        low_sweep_state = (not self.cfg.sweeps_require_live_swing) or snap_low_live
        sweep_high = (
            calculate_sweeps
            and is_value(snap_high)
            and atr_valid
            and high_sweep_state
            and high[index] > snap_high
            and close[index] < snap_high - atr * self.cfg.sweep_reclaim_atr
        )
        sweep_low = (
            calculate_sweeps
            and is_value(snap_low)
            and atr_valid
            and low_sweep_state
            and low[index] < snap_low
            and close[index] > snap_low + atr * self.cfg.sweep_reclaim_atr
        )
        out.sweep_high = 1.0 if sweep_high else 0.0
        out.sweep_low = 1.0 if sweep_low else 0.0

        # Pivots AFTER snapshot-based events.
        found, value, pivot_index = self.is_pivot_high(index, high)
        if found:
            self.swing_high = value
            self.swing_high_index = pivot_index
            self.swing_high_live = True
            self.trail_high = value
            self.trail_high_index = pivot_index
            self.pending_high_active = False
            self.pending_high_level = EMPTY
            self.pending_high_origin = -1
        found, value, pivot_index = self.is_pivot_low(index, low)
        if found:
            self.swing_low = value
            self.swing_low_index = pivot_index
            self.swing_low_live = True
            self.trail_low = value
            self.trail_low_index = pivot_index
            self.pending_low_active = False
            self.pending_low_level = EMPTY
            self.pending_low_origin = -1

        if not is_value(self.trail_high) or high[index] >= self.trail_high:
            self.trail_high = high[index]
            self.trail_high_index = index
        if not is_value(self.trail_low) or low[index] <= self.trail_low:
            self.trail_low = low[index]
            self.trail_low_index = index

        published = self._publish(index, True, atr)
        published.bos_up = out.bos_up
        published.mss_up = out.mss_up
        published.bos_down = out.bos_down
        published.mss_down = out.mss_down
        published.sweep_high = out.sweep_high
        published.sweep_low = out.sweep_low
        published.bull_void = out.bull_void
        published.bear_void = out.bear_void
        published.impulse_up = out.impulse_up
        published.impulse_down = out.impulse_down
        published.structure_event = out.structure_event
        published.break_level = out.break_level
        published.break_origin = out.break_origin
        published.displacement_ratio = out.displacement_ratio
        return published

    def publish_forming(self, index: int, atr: float) -> BarOut:
        # Forming bar: event flags stay 0; ClosedBarValid=0; contract 2.3.
        return self._publish(index, False, atr)


def true_range_at(index: int, high: Sequence[float], low: Sequence[float], close: Sequence[float]) -> float:
    if index == 0:
        return high[0] - low[0]
    return max(
        high[index] - low[index],
        abs(high[index] - close[index - 1]),
        abs(low[index] - close[index - 1]),
    )


def replay(
    open_: Sequence[float],
    high: Sequence[float],
    low: Sequence[float],
    close: Sequence[float],
    config: Optional[EngineConfig] = None,
    forming: bool = False,
) -> Tuple[List[BarOut], Optional[BarOut]]:
    n = len(open_)
    if n == 0:
        return [], None
    engine = TbClosedBarEngine(config)
    last_closed = n - 2 if forming else n - 1
    if last_closed < 0:
        atr0 = EMPTY
        return [], engine.publish_forming(0, atr0)

    atr = [EMPTY] * n
    tr = [0.0] * n
    closed_out: List[BarOut] = []
    for index in range(0, last_closed + 1):
        tr[index] = true_range_at(index, high, low, close)
        atr[index] = engine._atr_at(index, tr, atr)
        closed_out.append(
            engine.process_closed_engine_bar(index, open_, high, low, close, atr[index])
        )

    forming_out: Optional[BarOut] = None
    if forming:
        forming_index = n - 1
        tr[forming_index] = true_range_at(forming_index, high, low, close)
        atr[forming_index] = engine._atr_at(forming_index, tr, atr)
        forming_out = engine.publish_forming(forming_index, atr[forming_index])
    return closed_out, forming_out


# ---------------------------------------------------------------------------
# Synthetic OHLC helpers
# ---------------------------------------------------------------------------

@dataclass
class Ohlc:
    o: List[float] = field(default_factory=list)
    h: List[float] = field(default_factory=list)
    l: List[float] = field(default_factory=list)
    c: List[float] = field(default_factory=list)

    @classmethod
    def background(cls, n: int, mid: float = 100.0) -> "Ohlc":
        """Doji background: decreasing highs / increasing lows so no accidental pivots."""
        series = cls()
        for i in range(n):
            high = mid + 1.0 - i * 0.001
            low = mid - 1.0 + i * 0.001
            series.o.append(mid)
            series.h.append(high)
            series.l.append(low)
            series.c.append(mid)
        return series

    def set(self, index: int, o: float, h: float, l: float, c: float) -> None:
        if not (l <= min(o, c) <= max(o, c) <= h):
            raise ValueError(f"invalid OHLC at {index}: {o},{h},{l},{c}")
        self.o[index] = float(o)
        self.h[index] = float(h)
        self.l[index] = float(l)
        self.c[index] = float(c)

    def arrays(self) -> Tuple[List[float], List[float], List[float], List[float]]:
        return self.o, self.h, self.l, self.c


def _assert(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)


# ---------------------------------------------------------------------------
# Fixtures (a)–(i) plus acceptance extras
# ---------------------------------------------------------------------------

def fixture_a_pivot_confirm_at_t_plus_l() -> None:
    """(a) pivot confirm at T+L."""
    length = 5
    pivot = 20
    confirm = pivot + length
    bars = Ohlc.background(40)
    bars.set(pivot, 100.0, 105.0, 99.0, 100.0)
    closed, _ = replay(*bars.arrays())
    out = closed[confirm]
    _assert(out.swing_high == 105.0, f"(a) swing high at T+L should be 105, got {out.swing_high}")
    _assert(out.swing_high_live == 1.0, "(a) confirmed swing must be live")
    prev = closed[confirm - 1]
    _assert(prev.swing_high != 105.0, "(a) swing must not confirm before T+L")


def fixture_b_snapshot_hh_confirm() -> None:
    """(b) HH-confirm bar does NOT BOS the new pivot; DOES BOS the old swing."""
    length = 5
    old_pivot = 20
    old_confirm = old_pivot + length
    new_pivot = 30
    new_confirm = new_pivot + length
    bars = Ohlc.background(50)
    bars.set(old_pivot, 100.0, 105.0, 99.0, 100.0)
    bars.set(18, 100.0, 101.0, 94.0, 100.0)  # swing low, confirm at 23
    # New HH: long wick, close stays at or below old swing so it is not a BOS.
    bars.set(new_pivot, 104.0, 110.0, 103.5, 104.8)
    # Bar before confirm: close still <= old swing 105.
    bars.set(new_confirm - 1, 104.0, 104.8, 103.2, 104.0)
    # Confirm bar: close through OLD 105, not through NEW 110, with displacement.
    bars.set(new_confirm, 104.0, 108.0, 103.5, 107.5)
    closed, _ = replay(*bars.arrays())
    confirm_bar = closed[new_confirm]
    _assert(closed[old_confirm].swing_high == 105.0, "(b) old swing must confirm first")
    _assert(confirm_bar.bos_up == 1.0, f"(b) expected BOS of old swing, event={confirm_bar.structure_event}")
    _assert(confirm_bar.mss_up == 0.0, "(b) FLAT/continuation must not be MSS")
    _assert(confirm_bar.break_level == 105.0, f"(b) break level must be old swing 105, got {confirm_bar.break_level}")
    _assert(confirm_bar.break_origin == old_pivot, f"(b) break origin must be {old_pivot}")
    _assert(confirm_bar.structure_event == 1.0, "(b) structure event +1 BOS up")
    _assert(confirm_bar.swing_high == 110.0, f"(b) after events, new pivot 110 is installed, got {confirm_bar.swing_high}")
    _assert(confirm_bar.break_level != 110.0, "(b) must not BOS the newly confirmed 110")


def fixture_c_flat_to_up_is_bos() -> None:
    """(c) FLAT → up = BOS, never MSS."""
    bars = Ohlc.background(45)
    bars.set(20, 100.0, 105.0, 99.0, 100.0)
    bars.set(18, 100.0, 101.0, 94.0, 100.0)
    event = 32
    bars.set(event - 1, 100.0, 104.5, 99.0, 104.0)
    bars.set(event, 104.2, 108.5, 104.0, 108.0)
    closed, _ = replay(*bars.arrays())
    _assert(closed[event].bos_up == 1.0, f"(c) FLAT first break must be BOS, got event={closed[event].structure_event}")
    _assert(closed[event].mss_up == 0.0, "(c) FLAT must never emit MSS")
    _assert(closed[event].structure_event == 1.0, "(c) +1 BOS up")
    _assert(closed[event].break_level == 105.0, "(c) broke the snapshot swing high")


def fixture_d_reversal_is_mss() -> None:
    """(d) reversal against prior bias = MSS."""
    bars = Ohlc.background(50)
    bars.set(20, 100.0, 105.0, 99.0, 100.0)
    bars.set(18, 100.0, 101.0, 94.0, 100.0)
    bos = 32
    bars.set(bos - 1, 100.0, 104.5, 99.8, 104.0)
    bars.set(bos, 104.2, 108.5, 104.0, 108.0)
    mss = 38
    bars.set(mss - 1, 100.0, 102.0, 96.0, 96.5)
    bars.set(mss, 95.0, 95.4, 90.0, 90.5)
    closed, _ = replay(*bars.arrays())
    _assert(closed[bos].bos_up == 1.0, "(d) setup BOS up required")
    _assert(closed[bos].bias == 1.0, "(d) bias must be bull before reversal")
    _assert(closed[mss].mss_down == 1.0, f"(d) expected MSS down, event={closed[mss].structure_event}")
    _assert(closed[mss].bos_down == 0.0, "(d) reversal must not be labelled BOS")
    _assert(closed[mss].structure_event == -2.0, "(d) -2 MSS down")
    _assert(closed[mss].break_level == 94.0, f"(d) broke snapshot swing low 94, got {closed[mss].break_level}")


def fixture_e_doji_no_bos() -> None:
    """(e) doji / tiny body: close-through without displacement is not BOS/MSS."""
    bars = Ohlc.background(45)
    bars.set(20, 100.0, 105.0, 99.0, 100.0)
    bars.set(18, 100.0, 101.0, 94.0, 100.0)
    event = 32
    bars.set(event - 1, 100.0, 104.5, 99.0, 104.0)
    # Close through 105 but body is a doji.
    bars.set(event, 105.4, 105.8, 105.2, 105.5)
    closed, _ = replay(*bars.arrays())
    _assert(closed[event].impulse_up == 0.0, "(e) doji must not count as impulse")
    _assert(closed[event].bos_up == 0.0, "(e) no BOS without displacement")
    _assert(closed[event].mss_up == 0.0, "(e) no MSS without displacement")
    _assert(closed[event].structure_event == 0.0, "(e) structure event stays 0")
    _assert(closed[event].bos_down == 0.0 and closed[event].mss_down == 0.0, "(e) no down event")


def fixture_f_void_midclose_no_selffill() -> None:
    """(f) void + mid-close filter + no self-fill at birth."""
    bars = Ohlc.background(30)
    i = 20
    # Valid bull void: 3-candle gap, mid close through left edge.
    bars.set(i - 2, 99.0, 100.0, 98.0, 99.5)
    bars.set(i - 1, 100.2, 102.0, 100.1, 101.5)
    bars.set(i, 102.0, 103.0, 101.5, 102.5)
    closed, _ = replay(*bars.arrays())
    born = closed[i]
    _assert(born.bull_void == 1.0, "(f) valid geometry must birth a bull void")
    _assert(born.void_bottom == 100.0, f"(f) void bottom = high[i-2], got {born.void_bottom}")
    _assert(born.void_top == 101.5, f"(f) void top = low[i], got {born.void_top}")
    _assert(born.void_start == i - 2, "(f) void left edge is the first of the 3 candles")
    _assert(born.void_upper_active == 1.0 and born.void_lower_active == 1.0, "(f) no self-fill at birth")
    _assert(abs(born.void_ce - 100.75) < 1e-9, f"(f) CE is mid-gap, got {born.void_ce}")

    # Mid-close filter: gap exists but mid candle did not close through the edge.
    fail = Ohlc.background(30)
    fail.set(i - 2, 99.0, 100.0, 98.0, 99.5)
    fail.set(i - 1, 99.0, 102.0, 98.5, 99.5)  # close 99.5 <= high[i-2]=100
    fail.set(i, 102.0, 103.0, 101.5, 102.5)
    closed_fail, _ = replay(*fail.arrays())
    _assert(closed_fail[i].bull_void == 0.0, "(f) mid-close filter must reject the void")


def fixture_g_half_span_fill() -> None:
    """(g) fill requires a candle that spans the entire half, not a touch."""
    bars = Ohlc.background(32)
    i = 20
    bars.set(i - 2, 99.0, 100.0, 98.0, 99.5)
    bars.set(i - 1, 100.2, 102.0, 100.1, 101.5)
    bars.set(i, 102.0, 103.0, 101.5, 102.5)
    # Upper half only: high > top (101.5), low < CE (100.75), low >= bottom (100).
    bars.set(i + 1, 101.0, 102.2, 100.5, 101.6)
    # Touch-only candle must NOT fill the remaining lower half.
    bars.set(i + 2, 100.4, 100.8, 100.0, 100.3)
    closed, _ = replay(*bars.arrays())
    after_upper = closed[i + 1]
    _assert(after_upper.void_upper_active == 0.0, "(g) upper half must fill when fully spanned")
    _assert(after_upper.void_lower_active == 1.0, "(g) lower half must survive an upper-only span")
    after_touch = closed[i + 2]
    _assert(after_touch.void_lower_active == 1.0, "(g) touching the lower edge is not a fill")
    _assert(after_touch.void_count == 1, "(g) zone remains while a half is active")


def fixture_h_sweep_bos_mutex() -> None:
    """(h) sweep vs BOS mutually exclusive on the same snapshot swing."""
    bars = Ohlc.background(45)
    bars.set(20, 100.0, 105.0, 99.0, 100.0)
    bars.set(18, 100.0, 101.0, 94.0, 100.0)
    sweep = 32
    # Wick beyond snapshot high, close reclaims — sweep, not BOS.
    bars.set(sweep - 1, 100.0, 104.5, 99.0, 104.0)
    bars.set(sweep, 106.0, 107.5, 103.0, 104.0)
    closed, _ = replay(*bars.arrays())
    s = closed[sweep]
    _assert(s.sweep_high == 1.0, "(h) wick + reclaim must be a high sweep")
    _assert(s.bos_up == 0.0 and s.mss_up == 0.0, "(h) sweep bar must not also be BOS/MSS")
    _assert(s.structure_event == 0.0, "(h) structure event stays 0 on a sweep")

    bos_bars = Ohlc.background(45)
    bos_bars.set(20, 100.0, 105.0, 99.0, 100.0)
    bos_bars.set(18, 100.0, 101.0, 94.0, 100.0)
    bos = 32
    bos_bars.set(bos - 1, 100.0, 104.5, 99.0, 104.0)
    bos_bars.set(bos, 104.2, 108.5, 104.0, 108.0)
    closed_b, _ = replay(*bos_bars.arrays())
    b = closed_b[bos]
    _assert(b.bos_up == 1.0, "(h) close-through + displacement is BOS")
    _assert(b.sweep_high == 0.0, "(h) BOS bar must not also be a sweep on the same swing")


def fixture_i_cell_lookback_wick_invalidate() -> None:
    """(i) cell lookback before+inclusive of break; wick through invalidates."""
    bars = Ohlc.background(50)
    bars.set(20, 100.0, 105.0, 99.0, 100.0)
    bars.set(18, 100.0, 101.0, 94.0, 100.0)
    event = 40
    # Two equal lowest lows in the 8-bar window; older wins via <=.
    bars.set(34, 98.0, 99.2, 90.0, 98.2)
    bars.set(37, 98.0, 99.0, 90.0, 98.1)
    bars.set(event - 1, 100.0, 104.5, 99.0, 104.0)
    bars.set(event, 104.2, 108.5, 103.8, 108.0)
    closed, _ = replay(*bars.arrays())
    born = closed[event]
    _assert(born.bos_up == 1.0, "(i) need a BOS to birth a cell")
    _assert(born.cell_side == 1.0, "(i) bull cell")
    _assert(born.cell_origin == 34, f"(i) older equal-low candle wins, got origin {born.cell_origin}")
    _assert(born.cell_bottom == 90.0, f"(i) cell bottom is origin low, got {born.cell_bottom}")
    _assert(born.cell_top == 99.2, f"(i) cell top is origin high, got {born.cell_top}")
    _assert(born.cell_count == 1, "(i) one surviving cell at birth")

    # Wick through the origin low invalidates. Equal-low is not enough.
    bars.set(event + 1, 100.0, 101.0, 90.0, 100.0)
    closed_eq, _ = replay(*bars.arrays())
    _assert(closed_eq[event + 1].cell_count == 1, "(i) wick equal to bottom does not invalidate")
    bars.set(event + 2, 100.0, 101.0, 89.5, 100.0)
    closed_inv, _ = replay(*bars.arrays())
    _assert(closed_inv[event + 2].cell_count == 0, "(i) wick through origin low must drop the cell")
    _assert(closed_inv[event + 2].cell_side == 0.0, "(i) published newest cell is empty after invalidate")


def fixture_show_structure_does_not_gate() -> None:
    """TV InpShowStructure=false still produces buffers 3-6 when geometry holds."""
    bars = Ohlc.background(45)
    bars.set(20, 100.0, 105.0, 99.0, 100.0)
    bars.set(18, 100.0, 101.0, 94.0, 100.0)
    event = 32
    bars.set(event - 1, 100.0, 104.5, 99.0, 104.0)
    bars.set(event, 104.2, 108.5, 104.0, 108.0)
    cfg = EngineConfig(tv_profile=True, show_structure=False, enable_structure=True)
    closed, _ = replay(*bars.arrays(), config=cfg)
    _assert(closed[event].bos_up == 1.0, "InpShowStructure=false must still set BOS Up (buf 3)")
    _assert(closed[event].structure_event == 1.0, "InpShowStructure=false must still set buf 27")
    _assert(closed[event].impulse_up == 1.0, "impulse buf 11 is independent of display")


def fixture_forming_bar_silent() -> None:
    """Forming bar: 3-12, 7-10, 26, 27 = 0; 43 = 2.3."""
    bars = Ohlc.background(45)
    bars.set(20, 100.0, 105.0, 99.0, 100.0)
    bars.set(18, 100.0, 101.0, 94.0, 100.0)
    event = 32
    bars.set(event - 1, 100.0, 104.5, 99.0, 104.0)
    bars.set(event, 104.2, 108.5, 104.0, 108.0)
    # Extra forming bar that would look like another impulse if it were closed.
    bars.set(event + 1, 108.0, 112.0, 107.5, 111.5)
    closed, forming = replay(*bars.arrays(), forming=True)
    _assert(forming is not None, "forming bar required")
    assert forming is not None
    _assert(closed[event].bos_up == 1.0, "setup: last closed bar is a real BOS")
    _assert(forming.bos_up == 0.0, "forming bos_up (3) must be 0")
    _assert(forming.mss_up == 0.0, "forming mss_up (4) must be 0")
    _assert(forming.bos_down == 0.0, "forming bos_down (5) must be 0")
    _assert(forming.mss_down == 0.0, "forming mss_down (6) must be 0")
    _assert(forming.sweep_high == 0.0, "forming sweep_high (7) must be 0")
    _assert(forming.sweep_low == 0.0, "forming sweep_low (8) must be 0")
    _assert(forming.bull_void == 0.0, "forming bull_void (9) must be 0")
    _assert(forming.bear_void == 0.0, "forming bear_void (10) must be 0")
    _assert(forming.impulse_up == 0.0, "forming impulse_up (11) must be 0")
    _assert(forming.impulse_down == 0.0, "forming impulse_down (12) must be 0")
    _assert(forming.structure_event == 0.0, "forming structure_event (27) must be 0")
    _assert(forming.closed_bar_valid == 0.0, "forming ClosedBarValid (26) must be 0")
    _assert(forming.contract_version == 2.3, f"forming contract (43) must be 2.3, got {forming.contract_version}")


def _wilder_atr(high: Sequence[float], low: Sequence[float], close: Sequence[float]) -> List[float]:
    n = len(high)
    tr = [0.0] * n
    atr = [EMPTY] * n
    engine = TbClosedBarEngine()
    for i in range(n):
        tr[i] = true_range_at(i, high, low, close)
        atr[i] = engine._atr_at(i, tr, atr)
    return atr


def _plant_standard_swings(bars: Ohlc) -> None:
    bars.set(20, 100.0, 105.0, 99.0, 100.0)
    bars.set(18, 100.0, 101.0, 94.0, 100.0)


def _plant_weak_up_through_105(bars: Ohlc, event: int) -> None:
    bars.set(event - 1, 100.0, 104.5, 99.0, 104.0)
    bars.set(event, 105.4, 105.8, 105.2, 105.5)


def _set_ratio_beyond(
    bars: Ohlc,
    index: int,
    ratio: float,
    *,
    beyond: float,
    bullish: bool,
) -> None:
    """Plant body/ATR[index] == ratio with close still beyond `beyond` (TR ≈ ATR[i-1])."""
    atrs = _wilder_atr(bars.h, bars.l, bars.c)
    atr_prev = atrs[index - 1]
    _assert(is_value(atr_prev) and atr_prev > 0.0, f"ATR[{index - 1}] required to plant ratio bar")
    body = ratio * atr_prev
    prev_c = bars.c[index - 1]
    if bullish:
        o = prev_c if prev_c > beyond else beyond + 0.01
        c = o + body
        if c <= beyond:
            c = beyond + max(body, 0.02)
            o = c - body
        extra = max(atr_prev - body, 1e-9)
        high = max(o, c) + extra * 0.5
        low = min(o, c) - extra * 0.5
    else:
        o = prev_c if prev_c < beyond else beyond - 0.01
        c = o - body
        if c >= beyond:
            c = beyond - max(body, 0.02)
            o = c + body
        extra = max(atr_prev - body, 1e-9)
        high = max(o, c) + extra * 0.5
        low = min(o, c) - extra * 0.5
    bars.set(index, o, high, low, c)


def fixture_lockout_fixed() -> None:
    """Weak close-through: no BOS/MSS, Live=0, pending BROKEN_UNCONFIRMED."""
    bars = Ohlc.background(45)
    _plant_standard_swings(bars)
    event = 32
    _plant_weak_up_through_105(bars, event)
    closed, _ = replay(*bars.arrays())
    bar = closed[event]
    _assert(bar.impulse_up == 0.0, "lockout-fixed: doji is not impulse")
    _assert(bar.bos_up == 0.0 and bar.mss_up == 0.0, "lockout-fixed: no BOS/MSS on weak bar")
    _assert(bar.structure_event == 0.0, "lockout-fixed: structure event stays 0")
    _assert(bar.swing_high_live == 0.0, "lockout-fixed: Live must be 0 after close-through")
    _assert(bar.pending_high == 1.0, "lockout-fixed: pending BROKEN_UNCONFIRMED")
    _assert(bar.pending_high_level == 105.0, f"lockout-fixed: pending level 105, got {bar.pending_high_level}")
    _assert(bar.pending_high_origin == 20, f"lockout-fixed: origin 20, got {bar.pending_high_origin}")
    _assert(bar.swing_high == 105.0, "lockout-fixed: published swing stays the broken level")


def fixture_deferred_bos() -> None:
    """Later impulse still beyond pending level prints BOS at the original swing."""
    bars = Ohlc.background(45)
    _plant_standard_swings(bars)
    weak = 32
    later = 33
    _plant_weak_up_through_105(bars, weak)
    _set_ratio_beyond(bars, later, 0.45, beyond=105.0, bullish=True)
    closed, _ = replay(*bars.arrays())
    _assert(closed[weak].bos_up == 0.0, "deferred: weak bar has no BOS")
    _assert(closed[weak].pending_high == 1.0, "deferred: pending armed on weak bar")
    later_bar = closed[later]
    _assert(later_bar.displacement_ratio + 1e-12 >= 0.45, f"deferred: need impulse, ratio={later_bar.displacement_ratio}")
    _assert(later_bar.bos_up == 1.0, f"deferred: expected BOS, event={later_bar.structure_event}")
    _assert(later_bar.mss_up == 0.0, "deferred: FLAT first break is BOS, not MSS")
    _assert(later_bar.break_level == 105.0, f"deferred: must use old level 105, got {later_bar.break_level}")
    _assert(later_bar.break_origin == 20, f"deferred: origin must stay 20, got {later_bar.break_origin}")
    _assert(later_bar.structure_event == 1.0, "deferred: +1 BOS up")
    _assert(later_bar.pending_high == 0.0, "deferred: pending cleared after confirm")
    _assert(later_bar.swing_high_live == 0.0, "deferred: Live stays 0 after confirmed break")
    _assert(later_bar.bias == 1.0, "deferred: bias becomes bull")


def fixture_deferred_mss() -> None:
    """Deferred confirm against prior opposite bias is MSS at the original level."""
    bars = Ohlc.background(50)
    _plant_standard_swings(bars)
    bos = 32
    bars.set(bos - 1, 100.0, 104.5, 99.8, 104.0)
    bars.set(bos, 104.2, 108.5, 104.0, 108.0)
    weak = 38
    later = 39
    bars.set(weak - 1, 100.0, 102.0, 96.0, 96.5)
    bars.set(weak, 93.8, 94.2, 93.6, 93.7)
    _set_ratio_beyond(bars, later, 0.45, beyond=94.0, bullish=False)
    closed, _ = replay(*bars.arrays())
    _assert(closed[bos].bos_up == 1.0, "deferred-MSS: setup BOS up required")
    _assert(closed[bos].bias == 1.0, "deferred-MSS: bias bull before reversal")
    _assert(closed[weak].mss_down == 0.0 and closed[weak].bos_down == 0.0, "deferred-MSS: weak bar silent")
    _assert(closed[weak].pending_low == 1.0, "deferred-MSS: pending low armed")
    _assert(closed[weak].swing_low_live == 0.0, "deferred-MSS: Live=0 after weak down")
    later_bar = closed[later]
    _assert(later_bar.mss_down == 1.0, f"deferred-MSS: expected MSS down, event={later_bar.structure_event}")
    _assert(later_bar.bos_down == 0.0, "deferred-MSS: reversal must not be labelled BOS")
    _assert(later_bar.break_level == 94.0, f"deferred-MSS: old low 94, got {later_bar.break_level}")
    _assert(later_bar.break_origin == 18, f"deferred-MSS: origin 18, got {later_bar.break_origin}")
    _assert(later_bar.structure_event == -2.0, "deferred-MSS: -2 MSS down")
    _assert(later_bar.pending_low == 0.0, "deferred-MSS: pending cleared")


def fixture_reclaim_cancel() -> None:
    """Close back through pending level cancels pending; later move needs a new cross."""
    bars = Ohlc.background(45)
    _plant_standard_swings(bars)
    weak = 32
    reclaim = 33
    later = 34
    _plant_weak_up_through_105(bars, weak)
    bars.set(reclaim, 105.0, 105.4, 103.5, 104.0)
    # Impulse that does not close through 105 — not a new cross, must not BOS.
    bars.set(later, 100.8, 104.95, 100.5, 104.8)
    closed, _ = replay(*bars.arrays())
    _assert(closed[weak].pending_high == 1.0, "reclaim: pending armed first")
    _assert(closed[reclaim].pending_high == 0.0, "reclaim: pending gone after close back")
    _assert(closed[reclaim].swing_high_live == 1.0, "reclaim: swing intact again (new cross can BOS as today)")
    _assert(closed[reclaim].bos_up == 0.0, "reclaim: cancel bar is not BOS")
    later_bar = closed[later]
    _assert(later_bar.impulse_up == 1.0, f"reclaim: later bar must be impulse, ratio={later_bar.displacement_ratio}")
    _assert(later_bar.bos_up == 0.0 and later_bar.mss_up == 0.0, "reclaim: no BOS without a new close-through")
    _assert(later_bar.pending_high == 0.0, "reclaim: leftover pending must not re-arm")
    _assert(later_bar.structure_event == 0.0, "reclaim: no structure event")


def fixture_new_pivot_cancel() -> None:
    """New pivot on that side replaces the level and cancels old pending."""
    bars = Ohlc.background(50)
    _plant_standard_swings(bars)
    weak = 32
    new_pivot = 33
    confirm = new_pivot + 5
    later = confirm + 1
    _plant_weak_up_through_105(bars, weak)
    bars.set(new_pivot, 106.0, 108.0, 105.6, 106.2)
    for i in range(new_pivot + 1, confirm):
        bars.set(i, 106.0, 106.5, 105.6, 106.0)
    bars.set(confirm, 106.0, 106.8, 105.7, 106.1)
    bars.set(later, 106.1, 107.8, 106.0, 107.5)
    closed, _ = replay(*bars.arrays())
    _assert(closed[weak].pending_high == 1.0, "new-pivot: pending armed after weak cross")
    _assert(closed[weak].swing_high_live == 0.0, "new-pivot: Live=0 before replacement")
    confirm_bar = closed[confirm]
    _assert(confirm_bar.swing_high == 108.0, f"new-pivot: new swing 108, got {confirm_bar.swing_high}")
    _assert(confirm_bar.swing_high_live == 1.0, "new-pivot: new swing starts clean/live")
    _assert(confirm_bar.pending_high == 0.0, "new-pivot: old pending cancelled")
    _assert(confirm_bar.bos_up == 0.0, "new-pivot: confirm bar itself is not BOS of 108")
    later_bar = closed[later]
    _assert(later_bar.bos_up == 0.0 and later_bar.mss_up == 0.0, "new-pivot: later move must not BOS the cancelled level")
    _assert(later_bar.pending_high == 0.0, "new-pivot: pending stays gone")
    _assert(later_bar.swing_high == 108.0, "new-pivot: published swing remains the new pivot")


def fixture_same_bar_strong_break() -> None:
    """Same-bar close-through + impulse still prints immediate BOS (regression)."""
    bars = Ohlc.background(45)
    _plant_standard_swings(bars)
    event = 32
    bars.set(event - 1, 100.0, 104.5, 99.0, 104.0)
    bars.set(event, 104.2, 108.5, 104.0, 108.0)
    closed, _ = replay(*bars.arrays())
    bar = closed[event]
    _assert(bar.impulse_up == 1.0, "same-bar: impulse required")
    _assert(bar.bos_up == 1.0, "same-bar: immediate BOS")
    _assert(bar.mss_up == 0.0, "same-bar: FLAT is BOS")
    _assert(bar.break_level == 105.0, "same-bar: broke snapshot 105")
    _assert(bar.pending_high == 0.0, "same-bar: no leftover pending")
    _assert(bar.swing_high_live == 0.0, "same-bar: Live consumed")


def fixture_threshold_044_045() -> None:
    """0.44*ATR after weak cross does not BOS; 0.45*ATR later does at the old level."""
    bars = Ohlc.background(45)
    _plant_standard_swings(bars)
    weak = 32
    fail = 33
    passed = 34
    _plant_weak_up_through_105(bars, weak)
    _set_ratio_beyond(bars, fail, 0.44, beyond=105.0, bullish=True)
    _set_ratio_beyond(bars, passed, 0.45, beyond=105.0, bullish=True)
    closed, _ = replay(*bars.arrays())
    _assert(closed[weak].bos_up == 0.0, "threshold: weak bar silent")
    fail_bar = closed[fail]
    _assert(fail_bar.displacement_ratio < 0.45 - 1e-12, f"threshold: 0.44 bar ratio={fail_bar.displacement_ratio}")
    _assert(fail_bar.bos_up == 0.0 and fail_bar.mss_up == 0.0, "threshold: 0.44*ATR must not BOS")
    _assert(fail_bar.pending_high == 1.0, "threshold: pending survives the 0.44 bar")
    pass_bar = closed[passed]
    _assert(pass_bar.displacement_ratio + 1e-12 >= 0.45, f"threshold: 0.45 bar ratio={pass_bar.displacement_ratio}")
    _assert(pass_bar.bos_up == 1.0, "threshold: 0.45*ATR later bar must BOS")
    _assert(pass_bar.break_level == 105.0, "threshold: BOS at original 105")
    _assert(pass_bar.pending_high == 0.0, "threshold: pending cleared on confirm")


def fixture_dead_sweep_after_bos() -> None:
    """After BOS, wick back to the consumed swing is not a real sweep."""
    bars = Ohlc.background(45)
    _plant_standard_swings(bars)
    bos = 32
    bars.set(bos - 1, 100.0, 104.5, 99.0, 104.0)
    bars.set(bos, 104.2, 108.5, 104.0, 108.0)
    dead = 33
    # Wick through the old 105, close reclaims — old TV would paint a sweep.
    bars.set(dead, 104.0, 106.5, 103.0, 104.0)
    closed, _ = replay(*bars.arrays())
    _assert(closed[bos].bos_up == 1.0, "dead-sweep: setup BOS")
    _assert(closed[bos].swing_high_live == 0.0, "dead-sweep: Live=0 after BOS")
    _assert(closed[dead].sweep_high == 0.0, "dead-sweep: no real sweep on a consumed swing")
    _assert(closed[dead].bos_up == 0.0, "dead-sweep: reclaim bar is not BOS")

    old_tv = EngineConfig(sweeps_require_live_swing=False)
    closed_old, _ = replay(*bars.arrays(), config=old_tv)
    _assert(closed_old[dead].sweep_high == 1.0, "dead-sweep: live-gate off still paints old TV sweep")


def fixture_touch_ce_void_remains() -> None:
    """Touch CE without spanning a half: void and CE stay active."""
    bars = Ohlc.background(32)
    i = 20
    bars.set(i - 2, 99.0, 100.0, 98.0, 99.5)
    bars.set(i - 1, 100.2, 102.0, 100.1, 101.5)
    bars.set(i, 102.0, 103.0, 101.5, 102.5)
    # CE = 100.75; touch only, no half-span.
    bars.set(i + 1, 100.7, 100.85, 100.65, 100.75)
    closed, _ = replay(*bars.arrays())
    bar = closed[i + 1]
    _assert(bar.void_count == 1, "touch-CE: void still present")
    _assert(bar.void_upper_active == 1.0 and bar.void_lower_active == 1.0, "touch-CE: both halves live")
    _assert(abs(bar.void_ce - 100.75) < 1e-9, "touch-CE: CE still published")
    _assert(bar.living_ce_count == 1, "touch-CE: living CE remains")


def fixture_both_halves_no_orphan_ce() -> None:
    """Both halves filled → no living void and no orphan active CE."""
    bars = Ohlc.background(34)
    i = 20
    bars.set(i - 2, 99.0, 100.0, 98.0, 99.5)
    bars.set(i - 1, 100.2, 102.0, 100.1, 101.5)
    bars.set(i, 102.0, 103.0, 101.5, 102.5)
    # Upper half: high>101.5, low<100.75
    bars.set(i + 1, 101.0, 102.2, 100.5, 101.6)
    # Lower half: high>100.75, low<100.0
    bars.set(i + 2, 100.5, 101.0, 99.5, 100.2)
    closed, _ = replay(*bars.arrays())
    _assert(closed[i + 1].void_upper_active == 0.0, "orphan-CE: upper filled")
    _assert(closed[i + 1].void_lower_active == 1.0, "orphan-CE: lower still live")
    _assert(closed[i + 1].living_ce_count == 1, "orphan-CE: CE lives while a half lives")
    done = closed[i + 2]
    _assert(done.void_count == 0, "orphan-CE: no living void after both halves")
    _assert(done.void_upper_active == 0.0 and done.void_lower_active == 0.0, "orphan-CE: halves gone")
    _assert(not is_value(done.void_ce), "orphan-CE: CE buffer empty")
    _assert(done.living_ce_count == 0, "orphan-CE: no leftover active CE")


FIXTURES = [
    ("a_pivot_confirm_at_T+L", fixture_a_pivot_confirm_at_t_plus_l),
    ("b_snapshot_hh_confirm", fixture_b_snapshot_hh_confirm),
    ("c_flat_to_up_is_bos", fixture_c_flat_to_up_is_bos),
    ("d_reversal_is_mss", fixture_d_reversal_is_mss),
    ("e_doji_no_bos", fixture_e_doji_no_bos),
    ("f_void_midclose_no_selffill", fixture_f_void_midclose_no_selffill),
    ("g_half_span_fill", fixture_g_half_span_fill),
    ("h_sweep_bos_mutex", fixture_h_sweep_bos_mutex),
    ("i_cell_lookback_wick_invalidate", fixture_i_cell_lookback_wick_invalidate),
    ("show_structure_does_not_gate", fixture_show_structure_does_not_gate),
    ("forming_bar_silent", fixture_forming_bar_silent),
    ("lockout_fixed", fixture_lockout_fixed),
    ("deferred_bos", fixture_deferred_bos),
    ("deferred_mss", fixture_deferred_mss),
    ("reclaim_cancel", fixture_reclaim_cancel),
    ("new_pivot_cancel", fixture_new_pivot_cancel),
    ("same_bar_strong_break", fixture_same_bar_strong_break),
    ("threshold_044_045", fixture_threshold_044_045),
    ("dead_sweep_after_bos", fixture_dead_sweep_after_bos),
    ("touch_ce_void_remains", fixture_touch_ce_void_remains),
    ("both_halves_no_orphan_ce", fixture_both_halves_no_orphan_ce),
]


def run_fixtures() -> int:
    passed = 0
    failed = 0
    print("TB-2026 closed-bar replay fixtures (no MetaTrader5)")
    print(f"contract {TB_CONTRACT_VERSION}")
    for name, fn in FIXTURES:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as exc:
            print(f"  FAIL  {name}: {exc}")
            failed += 1
        except Exception as exc:  # noqa: BLE001 — runner must surface fixture crashes
            print(f"  FAIL  {name}: {type(exc).__name__}: {exc}")
            failed += 1
    print(f"{passed} passed, {failed} failed, {len(FIXTURES)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_fixtures())
