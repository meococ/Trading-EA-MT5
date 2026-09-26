"""b_donchian.py — Donchian-alternating swing levels (baseline C2).

Clean-room from the public description of LuxAlgo's "Donchian
(Alternating)" detector in the S&R Pro Toolkit: an alternating state
machine — a new swing high is confirmed the moment price reverses by
`d` from the running high, which simultaneously confirms the previous
swing low.  No fixed right-side lag; the confirmation lag is whatever
time the reversal takes (fully causal, non-repainting).

Each confirmed swing extreme births a horizontal LEVEL at the extreme
price (side above for highs, below for lows).  A level dies when a
close exceeds it by `tol` (broken) — role of the level then ends; we
keep at most `keep` live levels per side (freshest retained).

Params: d = max(1.0, 0.5*ABR) reversal threshold; tol = max(1.0,
0.25*ABR) break tolerance; keep=3 per side.
"""
import numpy as np


def emit(t, m, o, h, l, c, abr, d_pips=1.0, d_abr=1.0,
         tol_pips=1.0, tol_abr=0.25, keep=3, dedupe_abr=0.5):
    n = len(h)
    out = []
    # state: tracking a run-high to be confirmed by a d-reversal down,
    # or a run-low to be confirmed by a d-reversal up.
    run_hi, run_hi_at = -np.inf, -1
    run_lo, run_lo_at = np.inf, -1
    live_hi, live_lo = [], []

    def birth(side, price, j_swing, i):
        rec = {"type": "LEVEL_CARRIED", "why": "donchian_alt",
               "birth": int(m[i]),
               "birth_drawn": int(m[j_swing]),
               "die": None, "score": float(m[i]),
               "price": float(price),
               "side": "above" if side == 1 else "below"}
        out.append(rec)
        return rec

    for i in range(n):
        d = max(d_pips, d_abr * abr[i])
        tol = max(tol_pips, tol_abr * abr[i])
        if h[i] >= run_hi:
            run_hi, run_hi_at = h[i], i
        if l[i] <= run_lo:
            run_lo, run_lo_at = l[i], i
        # reversal by d from the running high confirms a swing HIGH;
        # skip if a live same-side level already covers the price
        dd = dedupe_abr * abr[i]
        if run_hi_at >= 0 and c[i] < run_hi - d:
            if not any(abs(x["price"] - run_hi) <= dd
                       for x in live_hi):
                live_hi.append(birth(1, run_hi, run_hi_at, i))
            run_hi, run_hi_at = -np.inf, -1
        if run_lo_at >= 0 and c[i] > run_lo + d:
            if not any(abs(x["price"] - run_lo) <= dd
                       for x in live_lo):
                live_lo.append(birth(-1, run_lo, run_lo_at, i))
            run_lo, run_lo_at = np.inf, -1
        # break-death + live cap (freshest kept)
        for lv in live_hi:
            if lv["die"] is None and c[i] > lv["price"] + tol:
                lv["die"] = int(m[i])
        for lv in live_lo:
            if lv["die"] is None and c[i] < lv["price"] - tol:
                lv["die"] = int(m[i])
        live_hi = [x for x in live_hi if x["die"] is None]
        live_lo = [x for x in live_lo if x["die"] is None]
        for old in live_hi[:-keep]:
            if old["die"] is None:
                old["die"] = int(m[i])
        live_hi = live_hi[-keep:]
        for old in live_lo[:-keep]:
            if old["die"] is None:
                old["die"] = int(m[i])
        live_lo = live_lo[-keep:]
    return out
