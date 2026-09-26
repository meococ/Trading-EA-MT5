"""sd_base_zones.py — supply/demand base zones (T-PAPRO-ZONE-1).

"Supply/demand base zones": the base+impulse detector family from the survey.
A tight consolidation (the BASE) followed by a price displacement (the
IMPULSE) leaves a zone at the base band; the impulse only qualifies the
structure (no PnL, no returns, no signals, no stops/targets anywhere here).

Scan rule (per bar t with valid ``A = ATR14(H1)``; every input is <= t):
- base length ``nb`` in ``1..base_max_bars`` (3) and impulse length ``k`` in
  ``1..imp_max_bars`` (6); ``base_end = t - k`` and the base bars are
  ``[base_end - nb + 1 .. base_end]`` (all indices must be >= 0);
- the base is TIGHT when ``max(h[base]) - min(l[base]) <= base_range_atr * A``
  (0.35); the IMPULSE is the displacement of the close:
  DEMAND ``c[t] - max(h[base]) >= imp_min_atr * A`` (1.2) and SUPPLY
  ``min(l[base]) - c[t] >= imp_min_atr * A`` (both cannot hold at once);
- at most ONE zone per bar: among the valid structures prefer the largest
  ``delta`` (the displacement) and on ties the smallest ``k`` then the
  smallest ``nb``; the first structure in that order that also passes the
  dedupe below is emitted (structures of one bar are never all emitted);
- zone band ``[min(l[base]) - pad, max(h[base]) + pad]`` with
  ``pad = pad_atr * A`` (0.05), widened around its center to at least
  ``min_width_atr * A`` (0.20) and clipped around its center to at most
  ``max_width_atr * A`` (0.60) — the addendum 1 band;
- dedupe (declared): a structure is SKIPPED when
  1. a live zone of the SAME kind has a band center within ``dedupe_atr * A``
     (0.25) of the candidate band center, or
  2. a zone of the same kind was already created from a base whose last bar
     is within +-1 bar of this ``base_end`` (tracked in a set);
- ``born_idx = base_end`` (the structure is dated from the base), ``created_idx
  = t`` (it is known only when the impulse bar closes); quality = ``delta / A``
  with ``QUAL_REF = 2.0``, so T_qual saturates at a 2.0 x ATR14(H1) impulse;
- ``NAME = "sd_base"``, micro scale, ``max_age_bars = 1440`` (5 server days).

Causality: every input at bar t is <= t; the dedupe set and the live-zone
scan only see zones created at bars <= t; geometry and quality are fixed
through the Zone constructor (no ``set_band`` / ``add_quality``), so
``zones_at`` is prefix-invariant (tested in ``tests/test_sd_base_zones.py``).
Touch/response/break/strength/arming come from `common.py` unchanged;
``z.meta`` is never mutated and quality only enters via the constructor.

Interface: ``SdBaseZones(ctx).run()`` then ``zones_at(t)``; see `common.py`.
No outcomes, no fills: this module only produces zone bands.
"""

import numpy as np

from common import ZoneGen

__all__ = ["SdBaseZones", "DEFAULTS"]

DEFAULTS = {
    "base_max_bars": 3,      # nb: longest base in bars
    "imp_max_bars": 6,       # k: longest impulse in bars
    "base_range_atr": 0.35,  # base tightness: max(h) - min(l) <= this x A
    "imp_min_atr": 1.2,      # impulse displacement >= this x ATR14(H1)
    "pad_atr": 0.05,         # band padding around the base, x ATR14(H1)
    "min_width_atr": 0.20,   # band floor, x ATR14(H1) (addendum 1 item 1)
    "max_width_atr": 0.60,   # band cap, x ATR14(H1)   (addendum 1 item 1)
    "dedupe_atr": 0.25,      # same-kind live-zone center distance, x ATR14(H1)
    "max_age_bars": 1440,    # retire 5 server days after birth
}


class SdBaseZones(ZoneGen):
    """Base+impulse supply/demand zones: tight base, displacement close."""

    NAME = "sd_base"
    SCALE = "micro"
    QUAL_REF = 2.0
    DEFAULTS = DEFAULTS

    def __init__(self, ctx, params=None):
        super().__init__(ctx, params)
        self._bases = set()                     # (kind, base_end) already used
        self._rmax = self._roll(self.bars["h"], np.maximum)
        self._rmin = self._roll(self.bars["l"], np.minimum)

    def _roll(self, arr, ufunc):
        """Base-window extrema for every length 1..base_max_bars, as plain
        Python lists (fast scalar indexing in the per-bar scan)."""
        v = np.asarray(arr, dtype=np.float64)
        n = len(v)
        out = [v.tolist()]
        for w in range(2, int(self.cfg["base_max_bars"]) + 1):
            cur = np.full(n, np.nan)
            cur[w - 1:] = v[w - 1:]
            for j in range(1, w):
                cur[w - 1:] = ufunc(cur[w - 1:], v[w - 1 - j:n - j])
            out.append(cur.tolist())
        return out

    def _on_bar(self, t):
        A = self.ctx.a(t)
        if A != A or A <= 0:
            return
        c_t = float(self.bars["c"][t])
        base_range = float(self.cfg["base_range_atr"]) * A
        need = float(self.cfg["imp_min_atr"]) * A
        cand = []
        for k in range(1, int(self.cfg["imp_max_bars"]) + 1):
            be = t - k
            if be < 0:
                break
            for nb in range(1, int(self.cfg["base_max_bars"]) + 1):
                if be - nb + 1 < 0:
                    continue
                hb = self._rmax[nb - 1][be]
                lb = self._rmin[nb - 1][be]
                if hb - lb > base_range:
                    continue
                d = c_t - hb
                if d >= need:
                    cand.append((d, k, nb, lb, hb, "demand"))
                    continue
                d = lb - c_t
                if d >= need:
                    cand.append((d, k, nb, lb, hb, "supply"))
        if not cand:
            return
        cand.sort(key=lambda x: (-x[0], x[1], x[2]))
        pad = float(self.cfg["pad_atr"]) * A
        min_w = float(self.cfg["min_width_atr"]) * A
        max_w = float(self.cfg["max_width_atr"]) * A
        dedupe = float(self.cfg["dedupe_atr"]) * A
        for (delta, k, nb, lb, hb, kind) in cand:
            be = t - k
            if ((kind, be - 1) in self._bases or (kind, be) in self._bases
                    or (kind, be + 1) in self._bases):
                continue
            lo, hi = lb - pad, hb + pad
            cen = 0.5 * (lo + hi)
            if (hi - lo) < min_w:
                lo, hi = cen - 0.5 * min_w, cen + 0.5 * min_w
            elif (hi - lo) > max_w:
                lo, hi = cen - 0.5 * max_w, cen + 0.5 * max_w
            if self._center_blocked(kind, cen, t, dedupe):
                continue
            self._new_zone(
                kind=kind, scale=self.SCALE, born_idx=be, created_idx=t,
                lo=lo, hi=hi, quality=delta / A,
                meta={"base_end": be, "nb": nb, "k": k},
            )
            self._bases.add((kind, be))
            return

    def _center_blocked(self, kind, cen, t, dedupe):
        """True when a same-kind zone that is still live at t has a band
        center within ``dedupe`` of the candidate center (declared rule 1)."""
        for z in self._live.values():
            if z.kind != kind or t > z.end_idx:
                continue
            zlo, zhi = z.band_at(t)
            if abs(0.5 * (zlo + zhi) - cen) <= dedupe + 1e-12:
                return True
        return False
