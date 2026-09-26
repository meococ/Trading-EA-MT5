"""refs.py — causal reference levels (T-PAPRO-ZONE-1).

Minimal, self-contained reference book for the bake-off's v0 strength term
`T_ref` and for the `ref_zones` candidate generator.  Objects follow
`struct/PERCEPTION_SPEC.md` O3/O4/O5/O6 on the SERVER clock (pa_data bars):
PDH/PDL/PDC (previous server day), Asia high/low (UTC 00:00-05:00 window),
week high/low (previous server week, Monday start), round 00/50 grid
(50 pips, LINE-1 `round_grid_pips` :103).

Causal by construction: every value at bar `t` is computed from a completed
period or from running extremes over bars <= t; arrays are filled in one
forward pass and read at index t.  No outcomes.

NOTE for R01: this is the bake-off's local instance.  The round will build
`struct/refs.py` to PERCEPTION_SPEC O3-O6; this file is then a dedup target
(same semantics, no writes outside `struct/zones/`).
"""

import numpy as np

__all__ = ["RefBook", "ROUND_GRID_PIPS", "ASIA_UTC"]

ROUND_GRID_PIPS = 50.0
ASIA_UTC = (0, 300)          # UTC minutes-of-day [lo, hi)


class RefBook:
    """Per-bar reference levels; `confluence(lo, hi, t)` feeds strength v0."""

    def __init__(self, bars, ctx, width_atr=0.25):
        self.ctx = ctx
        self.pip = float(bars["pip"])
        self.grid = ROUND_GRID_PIPS * self.pip
        self.width_atr = float(width_atr)
        n = len(bars["t"])
        self.n = n
        t = np.asarray(bars["t"], dtype=np.int64)
        utc_min = np.asarray(bars["utc_min"], dtype=np.int64)
        h = np.asarray(bars["h"], dtype=np.float64)
        l = np.asarray(bars["l"], dtype=np.float64)
        c = np.asarray(bars["c"], dtype=np.float64)
        day = t // 86400

        self.pdh = np.full(n, np.nan)
        self.pdl = np.full(n, np.nan)
        self.pdc = np.full(n, np.nan)
        self.asia_hi = np.full(n, np.nan)
        self.asia_lo = np.full(n, np.nan)
        self.wk_hi = np.full(n, np.nan)
        self.wk_lo = np.full(n, np.nan)

        d_hi = d_lo = d_c = float("nan")          # running current day
        p_hi = p_lo = p_c = float("nan")          # previous completed day
        w_hi = w_lo = float("nan")
        a_hi = a_lo = float("nan")
        a_done_hi = a_done_lo = float("nan")
        cur_day = day[0] if n else 0
        # seed the first day with its own running values (no prior day yet)
        for i in range(n):
            if day[i] != cur_day:
                if d_hi == d_hi:
                    p_hi, p_lo, p_c = d_hi, d_lo, d_c
                d_hi = h[i]
                d_lo = l[i]
                d_c = c[i]
                cur_day = day[i]
            else:
                if d_hi != d_hi:
                    d_hi = h[i]
                    d_lo = l[i]
                    d_c = c[i]
                else:
                    if h[i] > d_hi:
                        d_hi = h[i]
                    if l[i] < d_lo:
                        d_lo = l[i]
                    d_c = c[i]
            # R02-A F3: the previous day's H/L/C are visible on EVERY bar of the
            # current day (carry-forward), exactly like wk_* and asia_* below.
            if p_hi == p_hi:
                self.pdh[i] = p_hi
                self.pdl[i] = p_lo
                self.pdc[i] = p_c
            # week: promote the completed week's extremes at a Monday rollover
            if i > 0 and day[i] != day[i - 1] and int(bars["dow"][i]) == 0:
                if w_hi == w_hi:
                    self.wk_hi[i] = w_hi
                    self.wk_lo[i] = w_lo
                w_hi, w_lo = h[i], l[i]
            else:
                if w_hi != w_hi:
                    w_hi, w_lo = h[i], l[i]
                else:
                    if h[i] > w_hi:
                        w_hi = h[i]
                    if l[i] < w_lo:
                        w_lo = l[i]
                if i > 0:
                    self.wk_hi[i] = self.wk_hi[i - 1]
                    self.wk_lo[i] = self.wk_lo[i - 1]
            # Asia window (UTC 00:00-05:00): running during, completed after
            in_asia = ASIA_UTC[0] <= int(utc_min[i]) < ASIA_UTC[1]
            if in_asia:
                if i == 0 or not (ASIA_UTC[0] <= int(utc_min[i - 1]) < ASIA_UTC[1]):
                    a_hi, a_lo = h[i], l[i]
                else:
                    if h[i] > a_hi:
                        a_hi = h[i]
                    if l[i] < a_lo:
                        a_lo = l[i]
                self.asia_hi[i] = a_hi
                self.asia_lo[i] = a_lo
            else:
                if i > 0:
                    self.asia_hi[i] = self.asia_hi[i - 1]
                    self.asia_lo[i] = self.asia_lo[i - 1]
                if i > 0 and (ASIA_UTC[0] <= int(utc_min[i - 1]) < ASIA_UTC[1]):
                    a_done_hi, a_done_lo = a_hi, a_lo
                if a_done_hi == a_done_hi:
                    self.asia_hi[i] = a_done_hi
                    self.asia_lo[i] = a_done_lo

    # ------------------------------------------------------------------ reads
    def levels_at(self, t):
        """(kind, level) list of the reference levels active at bar t."""
        out = []
        for name in ("pdh", "pdl", "pdc"):
            v = float(getattr(self, name)[t])
            if v == v:
                out.append((name, v))
        for name in ("asia_hi", "asia_lo", "wk_hi", "wk_lo"):
            v = float(getattr(self, name)[t])
            if v == v:
                out.append((name, v))
        return out

    def round_near(self, price):
        """The two nearest 00/50 grid prices (below, above) for a price."""
        g = self.grid
        if g <= 0:
            return []
        k = np.floor(price / g)
        return [float(k * g), float((k + 1) * g)]

    def confluence(self, lo, hi, t):
        """T_ref v0 = min(1, (n_ref + n_round) / 2) at bar t for band [lo, hi].

        A reference counts when its +-w/2 band intersects [lo, hi]
        (w = 0.25 x ATR14(H1)); a round number counts when either of the two
        grid prices nearest the band center intersects it.
        """
        A = self.ctx.a(t)
        if A != A or A <= 0:
            return 0.0
        half = 0.5 * self.width_atr * A
        n_ref = 0
        for _, lvl in self.levels_at(t):
            if (lvl - half) <= hi and (lvl + half) >= lo:
                n_ref += 1
        cen = 0.5 * (lo + hi)
        n_round = 0
        for g in self.round_near(cen):
            if (g - half) <= hi and (g + half) >= lo:
                n_round = 1
                break
        return min(1.0, (n_ref + n_round) / 2.0)
