"""fractal_zones.py — H1 pivot S/R zone generator (T-PAPRO-ZONE-1).

"H1-scale pivot S/R zones": confirmed +-2-bar fractals on the H1 bars,
mapped into M5 index space by `common.ZoneContext.h1_pivots(k=2)`, filtered
for PAST-LEG prominence (causal at the pivot's confirm bar) and converted
into horizontal ZONES per `docs/CHARTER_ADDENDUM_1.md`:

- a pivot is usable only from its confirm bar `m5_confirm` (never from the
  pivot's own bar); a pivot whose own H1 bucket lies more than `scan_bars`
  M5 bars before the confirm bar is discarded as stale;
- prominence: at the confirm bar, `A = ATR14(H1)`; a HIGH qualifies when
  `price - min(H1 low over [j-12, j]) >= prom_atr * A`, a LOW when
  `max(H1 high over [j-12, j]) - price >= prom_atr * A`; the window uses H1
  bars up to the pivot bucket only (all closed at/before the confirm bar);
- a qualified pivot is absorbed into the nearest live `swing_h1` zone whose
  band (at the confirm bar t) is within `link_atr` x A of the price and whose
  merged band stays <= `max_width_atr` x A; otherwise it seeds a new zone
  `[price - w/2, price + w/2]`, `w` = `width_atr` x A (addendum band
  0.2-0.6 ATR14(H1));
- highs and lows cluster into the SAME zone kind (`swing_h1`); the common
  state machine tracks role flips;
- zone quality (T_qual input) is its member count (saturating at
  QUAL_REF = 2); quality only ever changes through `z.add_quality`;
- age is counted from the pivot's own H1 bucket first M5 bar
  (`born_idx = m5_anchor`), availability from the confirm bar
  (`created_idx = t`), the LINE-1 `_seed_levels` convention.

Meso scale: `SCALE = "meso"` (H1 structure, wider bands 0.30 x ATR14(H1)) and
`max_age_bars = 5760` (20 server days) — deliberately distinct from the
baseline LINE-1 M5 lag-3 micro swings (0.25 x ATR14(H1), 10 days).

Interface: `FractalZones(ctx).run()` then `zones_at(t)`; see `common.py`.
No outcomes, no fills: this module only produces zone bands.
"""

import numpy as np

from common import ZoneGen

__all__ = ["FractalZones", "DEFAULTS"]

DEFAULTS = {
    "pivot_k": 2,            # H1 +-2-bar fractals (ctx.h1_pivots)
    "prom_lookback": 12,     # H1 bars of the leg up to the pivot ([j-12, j])
    "prom_atr": 0.40,        # past-leg prominence >= this x ATR14(H1)
    "scan_bars": 480,        # stale-pivot guard (M5 bars, anchor -> confirm)
    "width_atr": 0.30,       # zone width when a single pivot seeds it
    "link_atr": 0.30,        # pivot joins a zone within this x ATR14(H1)
    "max_width_atr": 0.60,   # merged band cap (addendum 1 item 1)
    "max_age_bars": 5760,    # retire 20 server days after birth (H1 structure)
}


class FractalZones(ZoneGen):
    """H1 pivot S/R zones: confirmed +-2-bar H1 fractals -> meso zones."""

    NAME = "fractal_h1"
    SCALE = "meso"
    QUAL_REF = 2.0
    DEFAULTS = DEFAULTS

    def __init__(self, ctx, params=None):
        super().__init__(ctx, params)
        self._piv = self._qualify(ctx.h1_pivots(int(self.cfg["pivot_k"])))
        self._next = 0

    def _qualify(self, pivots):
        """Keep pivots whose PAST leg is >= prom_atr x ATR14(H1), measured at
        the pivot's confirm bar; drop stale pivots (anchor more than
        `scan_bars` M5 bars before the confirm bar).  Every input is fixed at
        or before the confirm bar, so precomputing the whole list is causal
        (consumers still gate on `m5_confirm <= t`)."""
        h1_h = np.asarray(self.ctx.h1["h"], dtype=np.float64)
        h1_l = np.asarray(self.ctx.h1["l"], dtype=np.float64)
        look = int(self.cfg["prom_lookback"])
        need = float(self.cfg["prom_atr"])
        scan = int(self.cfg["scan_bars"])
        out = []
        for (j, price, side, m5c, m5a) in pivots:
            if m5c - m5a > scan:
                continue
            A = self.ctx.a(m5c)
            if A != A or A <= 0:
                continue
            j0 = max(0, j - look)
            if side > 0:
                leg = price - float(h1_l[j0:j + 1].min())
            else:
                leg = float(h1_h[j0:j + 1].max()) - price
            if leg >= need * A:
                out.append((j, price, side, m5c, m5a))
        return out

    def _on_bar(self, t):
        A = self.ctx.a(t)
        if A != A or A <= 0:
            return
        piv = self._piv
        while self._next < len(piv) and piv[self._next][3] <= t:
            _j, price, _side, _conf, anchor = piv[self._next]
            self._next += 1
            w = self.cfg["width_atr"] * A
            link = self.cfg["link_atr"] * A
            max_w = self.cfg["max_width_atr"] * A
            best = None
            for z in self._live.values():
                if z.kind != "swing_h1":
                    continue
                lo, hi = z.band_at(t)
                nlo = min(lo, price - w / 2.0)
                nhi = max(hi, price + w / 2.0)
                if (nhi - nlo) > max_w + 1e-12:
                    continue
                if price < lo:
                    d = lo - price
                elif price > hi:
                    d = price - hi
                else:
                    d = 0.0
                if d <= link + 1e-12 and (best is None or d < best[0]):
                    best = (d, z, nlo, nhi)
            if best is not None:
                _, z, nlo, nhi = best
                z.set_band(t, nlo, nhi)
                z.add_quality(t, z.quality_at(t) + 1.0)
                self._cnt("pivot_absorbed")
            else:
                self._new_zone(
                    kind="swing_h1", scale=self.SCALE, born_idx=anchor,
                    created_idx=t, lo=price - w / 2.0, hi=price + w / 2.0,
                    quality=1.0, meta={"n_members": 1},
                )
