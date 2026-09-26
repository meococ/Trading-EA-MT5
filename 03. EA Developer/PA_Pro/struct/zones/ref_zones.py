"""ref_zones.py — reference-level zones (T-PAPRO-ZONE-1).

"NON-SWING reference levels": the causal reference book (`refs.py`) converted
into horizontal ZONES per `docs/CHARTER_ADDENDUM_1.md` — PDH/PDL/PDC, Asia
high/low, previous-week high/low and the nearest 00/50 round grid prices, each
published as a `0.25 x ATR14(H1)` band at the first bar the level is known:

- SERVER-DAY ROLLOVER (first bar of a new ``t // 86400`` day, ``t > 0``):
  publish one zone for each finite `ctx.refs.pdh/pdl/pdc` (kind = the level
  name, scale "meso") and one for each of the two nearest 00/50 grid prices
  from `ctx.refs.round_near(close)` (kind "round", scale "meso"); retire the
  previous day's pdh/pdl/pdc/round zones at the rollover bar;
- ASIA PUBLISH (first bar with ``prev utc_min < 300 <= utc_min``): publish
  `asia_hi`/`asia_lo` (scale "meso"); retire the previous Asia zones;
- WEEK ROLLOVER (a day rollover whose ``dow == 0``, Monday): publish
  `wk_hi`/`wk_lo` (scale "macro"); retire the previous week zones.
- band: `[level - w/2, level + w/2]`, `w = width_atr * ATR14(H1)`; for every
  reference zone `born_idx = created_idx = t` (the level is knowable only at
  that bar, never before);
- dedupe: a new zone is skipped when a live zone of the SAME kind has a center
  within `dedupe_atr x ATR14(H1)` (coincident references, e.g. yesterday's
  upper round number is today's lower one); the live zone is carried over into
  the new slot so a later rollover still retires it;
- quality: every reference zone gets `quality = 1.0` (`QUAL_REF = 1.0`):
  reference levels are declared inherently strong, quality never changes;
- retirement: the explicit rollover retire is primary, `max_age_bars = 2880`
  (10 server days) is the backstop handled by the common machinery;
- `self._prev` maps a retirement slot to the newest zone of that slot, so at
  most one zone per slot is alive: pdh/pdl/pdc/asia_hi/asia_lo/wk_hi/wk_lo
  occupy one slot each, and round numbers occupy two ("round_lo"/"round_hi")
  because two grid levels publish per server day (the nearest grid price below
  and above the rollover close).

Causality: every level is read from a `ctx.refs` array at the first bar it is
complete (all refs values are built from completed periods or running extremes
over bars <= t, `refs.py`); bands and quality are fixed at `created_idx`, so
`zones_at(t)` is prefix-invariant (tested in `tests/test_ref_zones.py`).
Touch/response/break/strength/arming come from `common.py` unchanged; `z.meta`
carries provenance only and is never mutated for strength.

Interface: `RefZones(ctx).run()` then `zones_at(t)`; see `common.py`.
No outcomes, no fills, no PnL, no signals: this module only produces bands.
"""

import math

from common import ZoneGen

__all__ = ["RefZones", "DEFAULTS"]

DEFAULTS = {
    "width_atr": 0.25,       # band width around the reference level
    "dedupe_atr": 0.25,      # skip a same-kind zone whose center is closer
    "max_age_bars": 2880,    # backstop: retire 10 server days after birth
}

_DAY = 86400
_ASIA_PUBLISH_MIN = 300      # UTC minutes-of-day; Asia window close (refs.py)
_ROUND_SLOTS = ("round_lo", "round_hi")


class RefZones(ZoneGen):
    """PDH/PDL/PDC + Asia + previous-week + nearest 00/50 round zones."""

    NAME = "ref_levels"
    SCALE = "meso"
    QUAL_REF = 1.0
    DEFAULTS = DEFAULTS

    def __init__(self, ctx, params=None):
        super().__init__(ctx, params)
        self._prev = {}          # retirement slot -> newest Zone of that slot

    # ------------------------------------------------------------ publishing
    def _publish(self, slot, kind, level, t, A, scale, src):
        """Retire the slot's previous zone, then create the new band.

        The new zone is skipped when a live zone of the same kind already has
        a center within `dedupe_atr x ATR14(H1)` (coincident references); the
        slot's previous zone is retired either way (the old level is stale)."""
        prev = self._prev.pop(slot, None)
        if prev is not None:
            self._retire(prev, t)
        if not math.isfinite(level):
            return None
        w = self.cfg["width_atr"] * A
        dedupe = self.cfg["dedupe_atr"] * A
        matched = None
        for z in self._live.values():
            if z.kind != kind:
                continue
            lo, hi = z.band_at(t)
            if abs(0.5 * (lo + hi) - level) <= dedupe:
                matched = z
                break
        if matched is not None:
            # the level is already live (e.g. yesterday's upper round number is
            # today's lower one): carry that zone over into this slot so the
            # next rollover retires it at the right time instead of orphaning
            # it until `max_age_bars`.
            for s in [s for s, owned in self._prev.items()
                      if owned is matched]:
                del self._prev[s]
            self._prev[slot] = matched
            self._cnt("zone_deduped")
            return None
        z = self._new_zone(
            kind=kind, scale=scale, born_idx=t, created_idx=t,
            lo=level - 0.5 * w, hi=level + 0.5 * w, quality=1.0,
            meta={"src": src, "level": float(level)},
        )
        self._prev[slot] = z
        return z

    # --------------------------------------------------------------- triggers
    def _on_bar(self, t):
        A = self.ctx.a(t)
        if A != A or A <= 0:
            return
        b = self.bars
        refs = self.ctx.refs
        if t > 0 and (int(b["t"][t]) // _DAY) != (int(b["t"][t - 1]) // _DAY):
            close = float(b["c"][t])
            self._publish("pdh", "pdh", float(refs.pdh[t]), t, A,
                          self.SCALE, "prev_day")
            self._publish("pdl", "pdl", float(refs.pdl[t]), t, A,
                          self.SCALE, "prev_day")
            self._publish("pdc", "pdc", float(refs.pdc[t]), t, A,
                          self.SCALE, "prev_day")
            for slot, level in zip(_ROUND_SLOTS, refs.round_near(close)):
                self._publish(slot, "round", float(level), t, A,
                              self.SCALE, "round")
            if int(b["dow"][t]) == 0:
                self._publish("wk_hi", "wk_hi", float(refs.wk_hi[t]), t, A,
                              "macro", "prev_week")
                self._publish("wk_lo", "wk_lo", float(refs.wk_lo[t]), t, A,
                              "macro", "prev_week")
        if (t > 0 and int(b["utc_min"][t - 1]) < _ASIA_PUBLISH_MIN
                <= int(b["utc_min"][t])):
            self._publish("asia_hi", "asia_hi", float(refs.asia_hi[t]), t, A,
                          self.SCALE, "asia")
            self._publish("asia_lo", "asia_lo", float(refs.asia_lo[t]), t, A,
                          self.SCALE, "asia")
