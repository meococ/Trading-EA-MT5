"""overlay — P1.5 QA: render OUR candles + golden objects, book grammar.

Never copies the scan: renders real M5 bars (black/white candles, EMA25,
faint 00/50 grid) and draws golden objects:
  BOX solid rect, RANGE_OPEN two h-lines, CONTEXT_RANGE dotted rect,
  PATTERN_LINE solid, CONTEXT_LINE dotted, LEVEL_CARRIED long-dash,
  MINI_LEVEL short solid, SQUEEZE dashed ellipse, BRACKET h-segment +
  letter, T/F labels, setup arrows.
"""

import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, ".."),
           os.path.join(HERE, "..", "..", "lib")):
    _p = os.path.abspath(_p)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import book_loader  # noqa: E402
import cet  # noqa: E402

DRAFT = os.path.join(HERE, "draft")
QA = os.path.join(HERE, "qa")
PIP = 1e-4


class VMap:
    """Data->pixel for the rendered view (server-minute x-axis)."""

    def __init__(self, t_lo, t_hi, p_lo, p_hi, W=1180, H=380,
                 x_left=44, x_right_pad=70, y_top=14, y_bot_pad=26):
        self.W, self.H = W, H
        self.x0 = x_left
        self.x1 = W - x_right_pad
        self.y0 = y_top
        self.y1 = H - y_bot_pad
        self.t_lo, self.t_hi = t_lo, t_hi
        self.p_lo, self.p_hi = p_lo, p_hi

    def x(self, srv_min):
        return self.x0 + (srv_min - self.t_lo) / (self.t_hi - self.t_lo) \
            * (self.x1 - self.x0)

    def y(self, price):
        return self.y1 - (price - self.p_lo) / (self.p_hi - self.p_lo) \
            * (self.y1 - self.y0)


def _dash_hline(dr, x0, x1, y, fill, dash, gap):
    x = x0
    while x < x1:
        dr.line([(x, y), (min(x + dash, x1), y)], fill=fill, width=1)
        x += dash + gap


def _dash_vline(dr, x, y0, y1, fill, dash, gap):
    y = y0
    while y < y1:
        dr.line([(x, y), (x, min(y + dash, y1))], fill=fill, width=1)
        y += dash + gap


def _dash_rect(dr, x0, y0, x1, y1, fill, dash=3, gap=3):
    _dash_hline(dr, x0, x1, y0, fill, dash, gap)
    _dash_hline(dr, x0, x1, y1, fill, dash, gap)
    _dash_vline(dr, x0, y0, y1, fill, dash, gap)
    _dash_vline(dr, x1, y0, y1, fill, dash, gap)


def _dash_ellipse(dr, box, fill, seg=14):
    dr.arc(box, 0, 360, fill=fill, width=1)


def render_panel(rec, bars, path):
    """rec = golden record; bars = M5 dict of that server day."""
    import datetime as _dt
    srv = ((bars["t"] % 86400) // 60).astype(int)
    t0 = hhmm(rec["x0"]) - 150      # pad ~2.5h left of first label
    t1 = hhmm(rec["x1"]) + 40
    vis = (srv >= t0) & (srv <= t1)
    if not vis.any():
        return False
    hh = bars["h"][vis]; ll = bars["l"][vis]
    p_lo, p_hi = float(ll.min()) - 8 * PIP, float(hh.max()) + 8 * PIP
    vm = VMap(t0, t1, p_lo, p_hi)
    im = Image.new("L", (vm.W, vm.H), 255)
    dr = ImageDraw.Draw(im)
    K = (0,)  # black
    G = 150   # gray for context
    # faint 00/50 grid
    p = int(p_lo / (50 * PIP) + 1) * 50 * PIP
    while p < p_hi:
        _dash_hline(dr, vm.x0, vm.x1, vm.y(p), 215, 2, 6)
        p += 50 * PIP
    # candles (M5): wick thin, body filled(black down / hollow up)
    px_bar = vm.x(t0 + 5) - vm.x(t0)
    bw = max(2, int(px_bar * 0.55))
    idx = np.where(vis)[0]
    ema = []
    closes = bars["c"]
    alpha = 2.0 / (25 + 1)
    e = None
    for k in range(len(closes)):
        e = closes[k] if e is None else e + alpha * (closes[k] - e)
        ema.append(e)
    for k in idx:
        x = vm.x(int(srv[k]))
        o, h, l, c = (bars["o"][k], bars["h"][k], bars["l"][k],
                      bars["c"][k])
        dr.line([(x, vm.y(h)), (x, vm.y(l))], fill=0, width=1)
        yo, yc = vm.y(o), vm.y(c)
        top, bot = min(yo, yc), max(yo, yc)
        if c >= o:
            dr.rectangle([x - bw / 2, top, x + bw / 2, max(bot, top + 1)],
                         outline=0)
        else:
            dr.rectangle([x - bw / 2, top, x + bw / 2, max(bot, top + 1)],
                         fill=0)
    # EMA25
    pts = [(vm.x(int(srv[k])), vm.y(ema[k])) for k in idx]
    dr.line(pts, fill=0, width=1)
    # axes
    dr.line([(vm.x0, vm.y1), (vm.x1, vm.y1)], fill=0)
    dr.line([(vm.x1, vm.y0), (vm.x1, vm.y1)], fill=0)
    # golden objects
    for o in rec.get("objects", []):
        draw_object(dr, vm, o)
    for m in rec.get("marks", []):
        draw_mark(dr, vm, m)
    dr.text((vm.x0 + 2, 2), "%s %s  %s" % (rec["id"], rec["date"],
                                          rec["fig"]), fill=0)
    im.save(path)
    return True


def draw_object(dr, vm, o):
    ty = o["spec_type"]
    t0, t1 = hhmm(o.get("t0")), hhmm(o.get("t1"))
    if t0 is None or t1 is None:
        return
    x0, x1 = vm.x(t0), vm.x(t1)
    if ty in ("BOX",):
        phi = o.get("price_hi") or o.get("price")
        plo = o.get("price_lo") or o.get("price2")
        if phi is None or plo is None:
            return
        if plo > phi:
            phi, plo = plo, phi
        dr.rectangle([x0, vm.y(phi), x1, vm.y(plo)], outline=0, width=2)
    elif ty == "CONTEXT_RANGE":
        phi = o.get("price_hi") or o.get("price")
        plo = o.get("price_lo") or o.get("price2")
        if phi is None or plo is None:
            return
        if plo > phi:
            phi, plo = plo, phi
        _dash_rect(dr, x0, vm.y(phi), x1, vm.y(plo), 0, 2, 4)
    elif ty == "RANGE_OPEN":
        for p in (o.get("price"), o.get("price2"),
                  o.get("price_hi"), o.get("price_lo")):
            if p:
                dr.line([(x0, vm.y(p)), (x1, vm.y(p))], fill=0, width=1)
    elif ty in ("PATTERN_LINE", "CONTEXT_LINE"):
        p0 = o.get("price0") or o.get("price")
        p1 = o.get("price1") or o.get("price2") or p0
        if p0 is None:
            return
        if o.get("style") == "dotted" or ty == "CONTEXT_LINE":
            x = x0
            while x < x1:
                y = vm.y(p0 + (p1 - p0) * (x - x0) / (x1 - x0))
                dr.point([(x, y), (x + 1, y)], fill=0)
                x += 3
        else:
            dr.line([(x0, vm.y(p0)), (x1, vm.y(p1))], fill=0, width=1)
    elif ty == "LEVEL_CARRIED":
        p = o.get("price")
        if p is None:
            return
        _dash_hline(dr, x0, x1, vm.y(p), 0, 10, 7)
    elif ty == "MINI_LEVEL":
        p = o.get("price")
        if p is None:
            return
        dr.line([(x0, vm.y(p)), (x1, vm.y(p))], fill=0, width=1)
    elif ty == "SQUEEZE":
        p0 = o.get("price") or 0
        p1 = o.get("price2") or p0
        y0, y1 = vm.y(max(p0, p1)), vm.y(min(p0, p1))
        if y1 - y0 < 6:
            y0, y1 = y0 - 10, y1 + 10
        _dash_ellipse(dr, [x0, y0, x1, y1], 0)
    elif ty == "BRACKET":
        p = o.get("price")
        if p is None:
            # default: just beyond span extreme is unknown -> skip price
            return
        dr.line([(x0, vm.y(p)), (x1, vm.y(p))], fill=0, width=2)
        if o.get("letter"):
            dr.text(((x0 + x1) / 2 - 3, vm.y(p) - 12
                     if o.get("side") == "above" else vm.y(p) + 4),
                    o["letter"], fill=0)


def draw_mark(dr, vm, m):
    t = hhmm(m.get("t"))
    if t is None:
        return
    p = m.get("price")
    x = vm.x(t)
    if m.get("kind") == "LABEL_TF":
        if p is None:
            return
        y = vm.y(p)
        dr.text((x - 3, y - 6), m.get("letter", "?"), fill=0)
    elif m.get("kind") == "ARROW" and p is not None:
        y = vm.y(p)
        if m.get("dir") == "down":
            dr.line([(x, y - 14), (x, y)], fill=0, width=1)
            dr.polygon([(x - 3, y - 5), (x + 3, y - 5), (x, y)], fill=0)
        else:
            dr.line([(x, y + 14), (x, y)], fill=0, width=1)
            dr.polygon([(x - 3, y + 5), (x + 3, y + 5), (x, y)], fill=0)


def hhmm(t):
    if t is None:
        return None
    if isinstance(t, (int, float)):
        return int(t)
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def main():
    os.makedirs(QA, exist_ok=True)
    recs = [json.loads(l) for l in open(
        os.path.join(HERE, "BOOK2012.jsonl"), encoding="utf8")]
    # 4 per catalogue part: pick well-calibrated panels spread over pages
    calib = {json.loads(l)["id"]: json.loads(l)
             for l in open(os.path.join(DRAFT, "calib.jsonl"))}
    picks = []
    for lo, hi in ((271, 314), (315, 358), (359, 402)):
        band = [r for r in recs
                if lo <= r["page"] <= hi and
                calib.get(r["id"], {}).get("res_med_inl", 9) < 2.0]
        step = max(1, len(band) // 4)
        picks.extend(band[::step][:4])
    day_bars = {}
    n = 0
    for rec in picks:
        day = rec["date"]
        if day not in day_bars:
            day_bars[day] = book_loader.load_m5(
                day + " 00:00", _next_day(day))
        bars = _same_day(day_bars[day], day)
        out = os.path.join(QA, "%s_overlay.png" % rec["id"])
        if render_panel(rec, bars, out):
            n += 1
            print("rendered", rec["id"])
    print("total", n)


def _same_day(bars, day):
    import datetime as _dt
    dd = np.array([_dt.datetime.utcfromtimestamp(e).date().isoformat()
                   for e in bars["t"]])
    keep = dd == day
    return {k: (v[keep] if hasattr(v, "__len__") and len(v) == len(keep)
                else v) for k, v in bars.items()}


def _next_day(day):
    import datetime as dt
    d = dt.date.fromisoformat(day) + dt.timedelta(days=1)
    return d.isoformat() + " 00:00"


if __name__ == "__main__":
    main()
