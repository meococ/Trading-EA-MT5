"""b_tdlines.py — DeMark TD Lines (PA-ATLAS baseline C1).

Clean-room from public descriptions (Aspenres TD Lines doc +
TDTL.pdf summary): a level-k TD Point high is a bar whose high is
the strict maximum of the 2k+1 window centred on it (confirmed k
bars later); demand points mirrored.  The supply line connects the
two most recent confirmed level-k supply points and MUST slope down;
demand line mirrored, must slope up.  A line dies on a qualified
break: a close beyond the line by >= brk ticks (here: pips), where
the prior bar was NOT itself beyond (i.e., the break bar is the
first close through).

A re-formed pair (newer second point) replaces the old line — the
old object dies at the new pair's confirm bar (revision as new ink).

Params: k=2 (level-2 points), brk = max(1.0, 0.25*ABR) pips,
span_max=84 bars (spec window), keep both sides independently.
"""
import numpy as np


def _td_points(h, l, k):
    """Confirmed TD point indices.  pt['sup'][p] is usable at p+k."""
    n = len(h)
    sup, dem = [], []
    for j in range(k, n - k):
        w = h[j - k:j + k + 1]
        if h[j] == w.max() and (w < h[j]).sum() == 2 * k:
            sup.append(j)
        w = l[j - k:j + k + 1]
        if l[j] == w.min() and (w > l[j]).sum() == 2 * k:
            dem.append(j)
    return sup, dem


def emit(t, m, o, h, l, c, abr, k=2, brk_pips=1.0, brk_abr=0.25,
         span_max=84, min_span=5):
    n = len(h)
    sup_pts, dem_pts = _td_points(h, l, k)
    out = []

    for side, pts in (("top", sup_pts), ("bottom", dem_pts)):
        cur = None          # live line dict or None
        a = b = None        # anchor bar indices of the live line
        pi = 0              # scan position into pts
        for i in range(n):
            # absorb points confirmed by bar i (point p -> usable p+k)
            while pi < len(pts) and pts[pi] + k <= i:
                cand_b = pts[pi]
                pi += 1
                if cand_b >= i - span_max:
                    # find pa: newest earlier same-side point giving a
                    # correctly-signed slope (supply down, demand up)
                    pa = None
                    for q in reversed(pts[:pi - 1]):
                        if q >= cand_b or q < i - span_max or \
                                cand_b - q < min_span:
                            continue
                        s = ((h[cand_b] - h[q]) if side == "top"
                             else (l[cand_b] - l[q]))
                        s = s / (cand_b - q)
                        if (side == "top" and s < 0) or \
                           (side == "bottom" and s > 0):
                            pa = q
                            break
                    if pa is not None:
                        pair = (pa, cand_b)
                        if pair != (a, b):
                            if cur is not None and \
                                    cur["die"] is None:
                                cur["die"] = int(m[i])
                            a, b = pair
                            y0 = (h[a] if side == "top" else l[a])
                            y1 = (h[b] if side == "top" else l[b])
                            cur = {"type": "PATTERN_LINE",
                                   "why": "tdline_k%d" % k,
                                   "birth": int(m[i]),
                                   "birth_drawn": int(m[a]),
                                   "die": None,
                                   "score": float(m[i]),
                                   "p0": float(y0),
                                   "slope": float((y1 - y0) / (b - a)),
                                   "t0_bar": a, "side": side}
                            out.append(cur)
            # qualified-break check on the live line
            if cur is not None and cur["die"] is None and i > b:
                brk = max(brk_pips, brk_abr * abr[i])
                lv = cur["p0"] + cur["slope"] * (i - cur["t0_bar"])
                prev = cur["p0"] + cur["slope"] * (i - 1 -
                                                   cur["t0_bar"])
                if side == "top":
                    if c[i] > lv + brk and c[i - 1] <= prev + brk:
                        cur["die"] = int(m[i])
                else:
                    if c[i] < lv - brk and c[i - 1] >= prev - brk:
                        cur["die"] = int(m[i])
            # stale: right anchor too old
            if cur is not None and cur["die"] is None \
                    and i - b > span_max:
                cur["die"] = int(m[i])
    return out
