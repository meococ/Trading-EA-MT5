"""detect — drawn-object pixel detection inside a calibrated panel.

Builds ``drawn_ink`` = scan ink minus candles (envelope runs), minus
caption boxes, minus axes/labels.  On that mask:
  - hsegments: long horizontal runs (solid or dashed) -> box edges,
    carried levels, mini levels, range-open lines, bracket baselines.
  - vsegments: vertical runs -> box sides, range sides.
  - corridor_fit: ink pixels in a corridor around a predicted sloped
    segment -> least-squares line (pattern/context lines).
  - blob_near: small text blob near a bar extreme -> T/F letters, arrows.

No OCR, no ML.  All coordinates are raw pixels; the caller maps them
through the panel's x/y calibration.
"""

import numpy as np

from calibrate import runs1d, mask_boxes


def drawn_ink(im, xr, yb, ytop, x_left=40):
    """Boolean mask of non-candle, non-caption, non-axis ink."""
    ink = (im < 150).copy()
    mask_boxes(ink, ytop, yb, x_left, xr)
    # remove candle runs: dominant contiguous run per column (same rule
    # as calibrate.envelope but returns the mask, not the extremes)
    for x in range(x_left, xr):
        rs = runs1d(ink[ytop:yb, x])
        if not rs:
            continue
        # candle run = the longest one; keep it OUT of drawn ink
        s, e = max(rs, key=lambda r: r[1] - r[0])
        if e - s >= 3:
            ink[ytop + s:ytop + e, x] = False
    # remove axes and the label bands
    ink[yb - 2:yb + 30, :] = False
    ink[:, xr - 2:xr + 55] = False
    ink[ytop - 2:ytop + 1, :] = False
    return ink


def hsegments(ink, y0, y1, x0, x1, min_len=14):
    """Horizontal segments: [(row, x_start, x_end, solidity)]."""
    out = []
    for y in range(max(0, y0), y1 + 1):
        for s, e in runs1d(ink[y, x0:x1], gap=2):
            if e - s >= min_len:
                # solidity = ink fraction inside the span
                frac = ink[y, x0 + s:x0 + e].mean()
                out.append((y, x0 + s, x0 + e, float(frac)))
    return out


def vsegments(ink, x0, x1, y0, y1, min_len=12):
    out = []
    for x in range(max(0, x0), x1 + 1):
        for s, e in runs1d(ink[y0:y1, x], gap=2):
            if e - s >= min_len:
                frac = ink[y0 + s:y0 + e, x].mean()
                out.append((x, y0 + s, y0 + e, float(frac)))
    return out


def best_hline(ink, y_c, x0, x1, dy=6, min_len=20, gap=2):
    """Strongest horizontal segment near row y_c -> (row, xs, xe, frac).
    gap bridges dash holes (dotted ~2-4, long-dashed ~8-10)."""
    best = None
    for y in range(int(y_c - dy), int(y_c + dy) + 1):
        if y < 0 or y >= ink.shape[0]:
            continue
        for s, e in runs1d(ink[y, x0:x1], gap=gap):
            if e - s >= min_len:
                frac = ink[y, x0 + s:x0 + e].mean()
                key = (e - s, frac)
                if best is None or key > best[0]:
                    best = (key, y, x0 + s, x0 + e, frac)
    if best:
        _, y, s, e, f = best
        return (y, s, e, f)
    return None


def corridor_fit(ink, x0, y0, x1, y1, dy_px=18):
    """Least-squares line through ink pixels in a corridor around the
    predicted segment (x0,y0)-(x1,y1).  Returns ((a,b), n, rms) for
    y = a*x + b, or None."""
    if x1 <= x0:
        return None
    m = (y1 - y0) / (x1 - x0)
    xs, ys = [], []
    for x in range(int(x0), int(x1) + 1):
        yc = y0 + m * (x - x0)
        lo, hi = int(yc - dy_px), int(yc + dy_px) + 1
        for yy in range(max(0, lo), min(ink.shape[0], hi)):
            if ink[yy, x]:
                xs.append(x)
                ys.append(yy)
    if len(xs) < max(10, int(0.25 * (x1 - x0))):
        return None
    xs = np.array(xs); ys = np.array(ys)
    # two-pass: fit, drop outliers, refit
    a, b = np.polyfit(xs, ys, 1)
    r = ys - (a * xs + b)
    ok = np.abs(r) <= 2.5
    if ok.sum() >= max(10, int(0.2 * (x1 - x0))):
        a, b = np.polyfit(xs[ok], ys[ok], 1)
        r = ys[ok] - (a * xs[ok] + b)
    rms = float(np.sqrt((r ** 2).mean()))
    return (float(a), float(b), int(len(xs)), rms)


def blob_near(ink, cx, y_ref, dx=14, dy_up=45, dy_dn=45,
              min_w=4, max_w=22, min_h=5, max_h=22):
    """Small text/arrow blob near (cx, y_ref).  Searches above and below.
    Returns (x_center, y_center, side) or None."""
    x0, x1 = max(0, int(cx - dx)), min(ink.shape[1], int(cx + dx))
    cands = []
    for side, (ya, yb_) in (("above", (int(y_ref - dy_up), int(y_ref - 3))),
                          ("below", (int(y_ref + 3), int(y_ref + dy_dn)))):
        if yb_ <= ya or ya < 0:
            continue
        band = ink[ya:yb_, x0:x1]
        colink = band.sum(0) > 0
        for s, e in runs1d(colink, gap=1):
            w = e - s
            if not (min_w <= w <= max_w):
                continue
            sub = band[:, s:e]
            rows = np.where(sub.any(1))[0]
            h = rows[-1] - rows[0] + 1 if len(rows) else 0
            if min_h <= h <= max_h:
                cands.append((x0 + (s + e) / 2.0,
                              ya + rows[0] + h / 2.0, side))
    if not cands:
        return None
    cands.sort(key=lambda c: abs(c[0] - cx) + abs(c[1] - y_ref) * 0.2)
    return cands[0]
