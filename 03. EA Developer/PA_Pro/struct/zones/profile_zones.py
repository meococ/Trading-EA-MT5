"""profile_zones.py — time-at-price value-area zone generator (T-PAPRO-ZONE-1).

"Market-profile / TPO value area" candidate from the survey: at every server
day rollover, build a trailing time-at-price histogram over the last
`window_bars` = 1440 complete M5 bars (5 server days), find the POC (argmax
bin) and the 70% value area around it, and publish ONE macro zone per
rollover:

- trigger: the first bar t > 0 whose ``t // 86400`` differs from bar t-1's;
  the rollover is skipped when ``A = ATR14(H1)`` is NaN or <= 0 at that bar;
- window: bars ``[max(0, t - window_bars + 1) .. t]`` (the rollover bar is
  inclusive; the window is clipped at index 0, never at the right edge);
- bins: nominal width ``bin_atr`` = 0.10 x A over
  ``[min(l) - bin/2, max(h) + bin/2]``; ``nbins = ceil(span/bin)``, capped at
  ``max_bins`` = 800 by extending the bin to ``span / 800``;
- weight: every bar spreads its range uniformly over the bins its ``[l, h]``
  covers, ``hist[b0:b1+1] += 1 / (b1 - b0 + 1)`` (a bar with ``h == l`` puts
  all its weight in one bin);
- POC = argmax bin; the value area grows from the POC by repeatedly absorbing
  the larger of its two neighboring bins until the accumulated weight is
  >= ``va_frac`` = 0.70 of the total window weight; VAL/VAH are the outer
  bin edges of the included run;
- band = ``[VAL, VAH]``; when shorter than ``min_width_atr`` = 0.20 x A or
  longer than ``max_width_atr`` = 0.60 x A (addendum 1 item 1) it is
  re-centered on the POC bin center with the bound width;
- quality (T_qual input) = ``hist[POC] / mean(hist of the VA bins)``,
  saturating at ``QUAL_REF`` = 3.0; quality is set once through the
  constructor and never updated later;
- ``max_age_bars`` = 2880 (10 server days), so profiles from consecutive
  days coexist and retire through the common machinery.

Causality: the profile at rollover bar t uses bars <= t only and bin geometry
is a pure function of that window, so ``zones_at`` is prefix-invariant
(tested in ``tests/test_profile_zones.py``).  No outcomes, no fills, no PnL,
no signals: this module only produces zone bands and their metadata.

Interface: ``ProfileZones(ctx).run()`` then ``zones_at(t)``; see `common.py`.
"""

import math

import numpy as np

from common import ZoneGen

__all__ = ["ProfileZones", "DEFAULTS"]

DEFAULTS = {
    "window_bars": 1440,     # trailing complete M5 bars (5 server days)
    "bin_atr": 0.10,         # nominal time-at-price bin width, x ATR14(H1)
    "max_bins": 800,         # hard bin cap (bin width extended when capped)
    "va_frac": 0.70,         # value-area fraction of the total window weight
    "min_width_atr": 0.20,   # enforced zone band floor, x ATR14(H1)
    "max_width_atr": 0.60,   # enforced zone band cap (addendum 1 item 1)
    "max_age_bars": 2880,    # retire 10 server days after birth
}


class ProfileZones(ZoneGen):
    """One time-at-price POC / value-area macro zone per server day."""

    NAME = "profile_va"
    SCALE = "macro"
    QUAL_REF = 3.0
    DEFAULTS = DEFAULTS

    def _on_bar(self, t):
        if t <= 0:
            return
        b = self.bars
        if (b["t"][t] // 86400) == (b["t"][t - 1] // 86400):
            return
        A = self.ctx.a(t)
        if A != A or A <= 0:
            return
        w = min(int(self.cfg["window_bars"]), t + 1)
        i0 = t - w + 1
        lw = np.asarray(b["l"][i0:t + 1], dtype=np.float64)
        hw = np.asarray(b["h"][i0:t + 1], dtype=np.float64)
        bin0 = float(self.cfg["bin_atr"]) * A
        win_lo = float(lw.min()) - 0.5 * bin0
        win_hi = float(hw.max()) + 0.5 * bin0
        span = win_hi - win_lo
        nbins = int(math.ceil(span / bin0))
        binw = bin0
        if nbins > int(self.cfg["max_bins"]):
            nbins = int(self.cfg["max_bins"])
            binw = span / nbins
        hist = np.zeros(nbins, dtype=np.float64)
        for j in range(w):
            b0 = int((lw[j] - win_lo) / binw)
            b1 = int((hw[j] - win_lo) / binw)
            hist[b0:b1 + 1] += 1.0 / (b1 - b0 + 1)
        poc = int(np.argmax(hist))
        va_lo = va_hi = poc
        acc = float(hist[poc])
        need = float(self.cfg["va_frac"]) * float(hist.sum())
        while acc < need:
            has_l = va_lo > 0
            has_r = va_hi < nbins - 1
            if not has_l and not has_r:
                break
            lv = hist[va_lo - 1] if has_l else -1.0
            rv = hist[va_hi + 1] if has_r else -1.0
            if lv >= rv:
                va_lo -= 1
                acc += lv
            else:
                va_hi += 1
                acc += rv
        val = win_lo + va_lo * binw
        vah = win_lo + (va_hi + 1) * binw
        poc_price = win_lo + (poc + 0.5) * binw
        min_w = float(self.cfg["min_width_atr"]) * A
        max_w = float(self.cfg["max_width_atr"]) * A
        lo, hi = val, vah
        if (hi - lo) < min_w:
            lo = poc_price - 0.5 * min_w
            hi = poc_price + 0.5 * min_w
        elif (hi - lo) > max_w:
            lo = poc_price - 0.5 * max_w
            hi = poc_price + 0.5 * max_w
        q = float(hist[poc]) / float(hist[va_lo:va_hi + 1].mean())
        self._new_zone(
            kind="profile_poc", scale=self.SCALE, born_idx=t, created_idx=t,
            lo=lo, hi=hi, quality=q,
            meta={"poc": poc_price, "val": val, "vah": vah,
                  "nbins": nbins, "window_bars": w},
        )
