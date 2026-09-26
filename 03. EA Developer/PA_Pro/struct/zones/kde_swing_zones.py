"""kde_swing_zones.py — kernel-density swing zones (T-PAPRO-ZONE-1).

"KDE swing zones": the quant-density method from the survey.  Confirmed M5
lag-3 and H1 lag-2 swings become weighted samples; a Gaussian kernel mixture
over price turns them into a density whose local maxima ("peaks") become
adaptive-width horizontal zones per `docs/CHARTER_ADDENDUM_1.md`.

- sample: `ctx.pivots(3)` (M5) and `ctx.h1_pivots(2)` (H1), both gated on
  their causal confirm index; each pivot's weight is
  ``clip(prom / A_confirm, 0.2, 1.5)`` with `prom` the PAST-leg prominence
  (M5 high: ``price - min(l[j-6..j])``, M5 low: ``max(h[j-6..j]) - price``;
  H1 over ``[j-12, j]``) and ``A_confirm = ctx.a(confirm)`` (ATR14(H1) known
  at the confirm bar); pivots with A NaN are skipped;
- refresh: at t with ``t % 24 == 0`` and A(t) valid, the density is rebuilt
  from pivots whose ``confirm <= t`` and ``t - confirm <= 1440`` (5 server
  days);
- density: price grid ``[min_sample - 0.5A, max_sample + 0.5A]`` x 160
  points, Gaussian kernel ``h = 0.20 x A``,
  ``density[i] = sum_k w_k * exp(-0.5*((x_i - p_k)/h)^2)`` — one vectorized
  numpy product, no per-kernel Python loop;
- peaks: local maxima (>= both neighbours) with ``density >= 0.5 x max``;
  the contiguous half-max run around a peak is the tentative band, clipped /
  widened centered on the peak price into ``[0.20, 0.60] x A``; peaks are
  processed strongest first (a weaker peak can link to a zone a stronger
  peak just created in the same refresh);
- zone update: a peak links to the nearest live `density` zone whose center
  is within ``0.25 x A`` — ``z.set_band(t, lo, hi)`` + ``z.add_quality(t, q)``
  — otherwise it seeds a new zone at the refresh bar; quality is
  ``q = pd / (pd + median_peak_density_of_this_refresh)`` in (0, 1) and feeds
  the common T_qual term with ``QUAL_REF = 1.0``;
- scale: `"meso"` when the H1-pivot weight share inside the half-max region
  is >= 0.5, else `"micro"`.

Causality: every refresh at bar t uses pivots with ``confirm <= t`` and bars
<= t only; geometry and quality are step histories on the `Zone` object, so
`zones_at(t)` replays exactly the state the pass built (prefix invariance is
tested in `tests/test_kde_swing_zones.py`).  Touch/response/break/strength/
arming come from `common.py` unchanged; `z.meta` is never mutated for
strength.

Interface: `KdeSwingZones(ctx).run()` then `zones_at(t)`; see `common.py`.
No outcomes, no fills: this module only produces zone bands.
"""

import numpy as np

from common import ZoneGen

__all__ = ["KdeSwingZones", "DEFAULTS"]

DEFAULTS = {
    "pivot_lag_m5": 3,        # M5 +-3-bar fractals (ctx.pivots)
    "pivot_lag_h1": 2,        # H1 +-2-bar fractals (ctx.h1_pivots)
    "prom_m5_look": 6,        # M5 bars of the past leg ([j-6, j])
    "prom_h1_look": 12,       # H1 bars of the past leg ([j-12, j])
    "w_clip_lo": 0.20,        # sample weight floor: prom / A_confirm
    "w_clip_hi": 1.50,        # sample weight cap
    "refresh_bars": 24,       # recompute the density every 24 M5 bars
    "window_bars": 1440,      # sample window: confirm within 5 server days
    "grid_n": 160,            # price-grid points
    "bandwidth_atr": 0.20,    # Gaussian kernel h = 0.20 x ATR14(H1)
    "peak_frac": 0.50,        # peak must reach 0.50 x density.max()
    "min_width_atr": 0.20,    # band floor (addendum 1 item 1)
    "max_width_atr": 0.60,    # band cap  (addendum 1 item 1)
    "link_atr": 0.25,         # peak joins a live zone within this x ATR14(H1)
    "max_age_bars": 2880,     # retire 10 server days after birth
}


class KdeSwingZones(ZoneGen):
    """KDE swing-density zones: weighted confirmed M5 + H1 swings -> Gaussian
    mixture peaks -> adaptive-width bands."""

    NAME = "kde_swing"
    SCALE = "micro"
    QUAL_REF = 1.0
    DEFAULTS = DEFAULTS

    def __init__(self, ctx, params=None):
        super().__init__(ctx, params)
        self._m5_conf, self._m5_price, self._m5_w = self._qualify_m5(
            ctx.pivots(int(self.cfg["pivot_lag_m5"])))
        self._h1_conf, self._h1_price, self._h1_w = self._qualify_h1(
            ctx.h1_pivots(int(self.cfg["pivot_lag_h1"])))
        self._m5_lo = self._m5_hi = 0
        self._h1_lo = self._h1_hi = 0

    # -------------------------------------------------------------- sampling
    def _qualify_m5(self, pivots):
        """(confirm, price, weight) arrays for confirmed M5 swings.  The
        prominence window ends at the pivot bar; the weight is fixed at the
        confirm bar's ATR14(H1), so precomputing the stream is causal
        (consumers still gate on ``confirm <= t``)."""
        h = np.asarray(self.ctx.bars["h"], dtype=np.float64)
        l = np.asarray(self.ctx.bars["l"], dtype=np.float64)
        look = int(self.cfg["prom_m5_look"])
        w_lo = float(self.cfg["w_clip_lo"])
        w_hi = float(self.cfg["w_clip_hi"])
        conf, price, weight = [], [], []
        for (j, p, side, c) in pivots:
            A = self.ctx.a(c)
            if A != A or A <= 0:
                continue
            j0 = max(0, j - look)
            if side > 0:
                prom = p - float(l[j0:j + 1].min())
            else:
                prom = float(h[j0:j + 1].max()) - p
            conf.append(int(c))
            price.append(float(p))
            weight.append(min(w_hi, max(w_lo, prom / A)))
        return (np.asarray(conf, dtype=np.int64),
                np.asarray(price, dtype=np.float64),
                np.asarray(weight, dtype=np.float64))

    def _qualify_h1(self, pivots):
        """Same for H1 swings: past-leg prominence over ``[j-12, j]`` H1 bars,
        weight fixed at the M5 confirm bar's ATR14(H1)."""
        h = np.asarray(self.ctx.h1["h"], dtype=np.float64)
        l = np.asarray(self.ctx.h1["l"], dtype=np.float64)
        look = int(self.cfg["prom_h1_look"])
        w_lo = float(self.cfg["w_clip_lo"])
        w_hi = float(self.cfg["w_clip_hi"])
        conf, price, weight = [], [], []
        for (j, p, side, m5c, _m5a) in pivots:
            A = self.ctx.a(m5c)
            if A != A or A <= 0:
                continue
            j0 = max(0, j - look)
            if side > 0:
                prom = p - float(l[j0:j + 1].min())
            else:
                prom = float(h[j0:j + 1].max()) - p
            conf.append(int(m5c))
            price.append(float(p))
            weight.append(min(w_hi, max(w_lo, prom / A)))
        return (np.asarray(conf, dtype=np.int64),
                np.asarray(price, dtype=np.float64),
                np.asarray(weight, dtype=np.float64))

    def _window(self, conf, lo, hi, t):
        """Advance a monotone cursor to the sample window at refresh bar t:
        ``confirm <= t`` and ``t - confirm <= window_bars``."""
        win = int(self.cfg["window_bars"])
        n = len(conf)
        while hi < n and conf[hi] <= t:
            hi += 1
        while lo < hi and conf[lo] < t - win:
            lo += 1
        return lo, hi

    # ------------------------------------------------------------- generator
    def _on_bar(self, t):
        if t % int(self.cfg["refresh_bars"]) != 0:
            return
        A = self.ctx.a(t)
        if A != A or A <= 0:
            return
        self._m5_lo, self._m5_hi = self._window(
            self._m5_conf, self._m5_lo, self._m5_hi, t)
        self._h1_lo, self._h1_hi = self._window(
            self._h1_conf, self._h1_lo, self._h1_hi, t)
        mp = self._m5_price[self._m5_lo:self._m5_hi]
        hpp = self._h1_price[self._h1_lo:self._h1_hi]
        prices = np.concatenate([mp, hpp])
        if prices.size == 0:
            return
        weights = np.concatenate([self._m5_w[self._m5_lo:self._m5_hi],
                                  self._h1_w[self._h1_lo:self._h1_hi]])
        is_h1 = np.concatenate([np.zeros(mp.size, dtype=bool),
                                np.ones(hpp.size, dtype=bool)])
        density, grid = self._density(prices, weights, A)
        peaks = self._peaks(density)
        if peaks.size == 0:
            return
        med = float(np.median(density[peaks]))
        live = []
        for z in self._live.values():
            if z.kind != "density":
                continue
            zlo, zhi = z.band_at(t)
            live.append((0.5 * (zlo + zhi), z))
        link = float(self.cfg["link_atr"]) * A
        order = peaks[np.argsort(-density[peaks], kind="stable")]
        for ip in order:
            ip = int(ip)
            pd = float(density[ip])
            i0, i1 = self._half_max(density, ip)
            peak_price = float(grid[ip])
            lo, hi = self._band(float(grid[i0]), float(grid[i1]), peak_price, A)
            q = pd / (pd + med) if (pd + med) > 0 else 0.5
            # scale: H1-pivot weight share inside the half-max region
            in_reg = (prices >= grid[i0]) & (prices <= grid[i1])
            w_tot = float(weights[in_reg].sum())
            w_h1 = float(weights[in_reg & is_h1].sum())
            scale = "meso" if (w_tot > 0.0 and w_h1 / w_tot >= 0.5) else "micro"
            best = None
            for k, (cen, z) in enumerate(live):
                d = abs(cen - peak_price)
                if d <= link + 1e-12 and (best is None or d < best[0]):
                    best = (d, k, z)
            if best is not None:
                _, k, z = best
                z.set_band(t, lo, hi)
                z.add_quality(t, q)
                live[k] = (0.5 * (lo + hi), z)
                self._cnt("peak_linked")
            else:
                z = self._new_zone("density", scale, t, t, lo, hi,
                                   quality=q, meta={"poc_peak": peak_price})
                live.append((0.5 * (lo + hi), z))
                self._cnt("peak_new")

    # ------------------------------------------------------------ density
    def _density(self, prices, weights, A):
        """Vectorized Gaussian kernel density on the price grid."""
        g0 = float(prices.min()) - 0.5 * A
        g1 = float(prices.max()) + 0.5 * A
        grid = np.linspace(g0, g1, int(self.cfg["grid_n"]))
        h = float(self.cfg["bandwidth_atr"]) * A
        z = (grid[:, None] - prices[None, :]) / h
        density = np.exp(-0.5 * z * z) @ weights
        return density, grid

    def _peaks(self, density):
        """Grid indices of local maxima (>= both neighbours) reaching
        ``peak_frac`` x density.max(); grid endpoints are never peaks."""
        thr = float(self.cfg["peak_frac"]) * float(density.max())
        mask = ((density[1:-1] >= density[:-2])
                & (density[1:-1] >= density[2:])
                & (density[1:-1] >= thr))
        return np.nonzero(mask)[0] + 1

    @staticmethod
    def _half_max(density, ip):
        """Contiguous run around the peak with density >= 0.5*peak_density."""
        half = 0.5 * float(density[ip])
        i0 = ip
        while i0 > 0 and density[i0 - 1] >= half:
            i0 -= 1
        i1 = ip
        n = len(density)
        while i1 < n - 1 and density[i1 + 1] >= half:
            i1 += 1
        return i0, i1

    def _band(self, lo, hi, peak, A):
        """Clip / widen the tentative band, centered on the peak price, into
        ``[min_width_atr, max_width_atr] x A``."""
        w = hi - lo
        min_w = float(self.cfg["min_width_atr"]) * A
        max_w = float(self.cfg["max_width_atr"]) * A
        if w < min_w:
            return peak - 0.5 * min_w, peak + 0.5 * min_w
        if w > max_w:
            return peak - 0.5 * max_w, peak + 0.5 * max_w
        return lo, hi
