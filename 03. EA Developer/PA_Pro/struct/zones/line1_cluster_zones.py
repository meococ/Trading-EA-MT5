"""line1_cluster_zones.py — BASELINE zone generator (T-PAPRO-ZONE-1).

"LINE-1 swing clusters converted to zones": take exactly the confirmed +-3-bar
M5 swings that LINE-1 used as level anchors (`EA_VolmanPA/research/lines/
vpa_lines.py:436-450`, the `_confirm_swings` rule), then convert them into
horizontal ZONES per `docs/CHARTER_ADDENDUM_1.md`:

- a new confirmed swing is absorbed into the nearest live swing zone whose
  band (at the confirm bar t) is within ``link_atr`` = 0.25 x ATR14(H1) of the
  swing price and whose merged band stays <= ``max_width_atr`` = 0.6 x
  ATR14(H1);
- otherwise it creates a new zone ``[price - w/2, price + w/2]``,
  ``w`` = ``width_atr`` = 0.25 x ATR14(H1) (addendum band 0.2-0.6 ATR);
- swng highs and lows cluster together (a prior resistance that becomes
  support is ONE zone; the common state machine tracks role flips);
- the zone's quality (T_qual input) is its member count / 2 (saturates at 2);
- age is counted from the anchor swing bar, availability from the confirm bar
  (LINE-1 `_seed_levels` convention: `born_idx = j`, `created_idx = t`).

Deliberate deltas vs LINE-1 lines (documented in `research/zones/SHORTLIST.md`):
1. LINE-1's `level_dedupe_atr` = 0.30 x ATR14(M5) merges same-side lines;
   here the merge is a 0.25 x ATR14(H1) single-link around the zone band and
   mixes sides.
2. Only the SWING RULE is reused.  LINE-1's score (`0.35*touch + ...`,
   `vpa_lines.py:116-123`) is NOT used; strength v0 lives in `common.py`.
   LINE-1's `_htf_align` (:785-805) is known to be look-ahead (it is being
   fixed in the LINE-1 session) and is not used anywhere here.
3. No outcomes, no fills: this module only produces zone bands.

Interface: `Line1ClusterZones(ctx).run()` then `zones_at(t)`; see `common.py`.
"""

from common import ZoneGen

__all__ = ["Line1ClusterZones", "DEFAULTS"]

DEFAULTS = {
    "pivot_lag": 3,          # LINE-1 level_pivot_lag (:60)
    "scan_bars": 240,        # LINE-1 level_scan_bars (:62)
    "link_atr": 0.25,        # pivot joins a zone within this x ATR14(H1)
    "width_atr": 0.25,       # zone width when a single swing seeds it
    "max_width_atr": 0.60,   # merged band cap (addendum 1 item 1)
}


class Line1ClusterZones(ZoneGen):
    NAME = "line1_cluster"
    SCALE = "micro"
    QUAL_REF = 2.0
    DEFAULTS = DEFAULTS

    def __init__(self, ctx, params=None):
        super().__init__(ctx, params)
        self._piv = ctx.pivots(int(self.cfg["pivot_lag"]))
        self._next = 0

    def _on_bar(self, t):
        A = self.ctx.a(t)
        if A != A or A <= 0:
            return
        piv = self._piv
        while self._next < len(piv) and piv[self._next][3] <= t:
            j, price, _side, _conf = piv[self._next]
            self._next += 1
            if t - j > self.cfg["scan_bars"]:
                continue
            w = self.cfg["width_atr"] * A
            link = self.cfg["link_atr"] * A
            max_w = self.cfg["max_width_atr"] * A
            best = None
            for z in self._live.values():
                if z.kind != "swing":
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
                    kind="swing", scale=self.SCALE, born_idx=j, created_idx=t,
                    lo=price - w / 2.0, hi=price + w / 2.0, quality=1.0,
                    meta={"n_members": 1, "anchor": j},
                )
