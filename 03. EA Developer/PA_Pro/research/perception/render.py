"""render.py — draw engine objects in the book grammar (spec §2, §7).

Renders OUR M5 bars (black/hollow candles, EMA25, faint 00/50 grid) and
the engine's live objects at a chosen bar index.  Pure rendering; no
outcomes.  Used by the DESIGN gallery (P4) and QA overlays.

Draw styles: BOX solid rect; RANGE_OPEN two h-lines; CONTEXT_RANGE
dotted rect; PATTERN_LINE solid diagonal; CONTEXT_LINE dotted;
LEVEL_CARRIED long-dash; MINI_LEVEL short solid; SQUEEZE dashed ellipse;
BRACKET span + centred letter; LABEL_TF letter; FALSE_EXT tick.
"""

import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "golden"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "lib"))
sys.path.insert(0, HERE)

from golden.overlay import VMap, _dash_hline, _dash_vline, _dash_rect  # noqa: E402
import trade_tags as TT                            # noqa: E402

PIP = 1e-4


def render_engine(bars, engine, upto, path, title="", W=1180, H=380):
    """Draw bars[:upto+1] and the engine's objects alive at bar `upto`.

    bars: book_loader.load_m5() dict.  upto: bar index (inclusive).
    """
    srv = ((bars["t"] % 86400) // 60).astype(int)
    i1 = min(upto, len(srv) - 1)
    i0 = max(0, i1 - engine.p["window_bars"] - 12)
    t0, t1 = int(srv[i0]), int(srv[i1])
    if t1 <= t0:
        t1 = t0 + 300
    hh = bars["h"][i0:i1 + 1]; ll = bars["l"][i0:i1 + 1]
    p_lo, p_hi = float(ll.min()) - 8 * PIP, float(hh.max()) + 8 * PIP
    vm = VMap(t0, t1, p_lo, p_hi, W=W, H=H)
    im = Image.new("L", (vm.W, vm.H), 255)
    dr = ImageDraw.Draw(im)

    # faint 00/50 grid (context only, never a drawn object)
    p = int(p_lo / (50 * PIP) + 1) * 50 * PIP
    while p < p_hi:
        _dash_hline(dr, vm.x0, vm.x1, vm.y(p), 215, 2, 6)
        p += 50 * PIP

    # candles
    px_bar = vm.x(t0 + 5) - vm.x(t0)
    bw = max(2, int(px_bar * 0.55))
    closes = bars["c"]
    alpha = 2.0 / (25 + 1)
    e = None
    ema = []
    for k in range(len(closes)):
        e = closes[k] if e is None else e + alpha * (closes[k] - e)
        ema.append(e)
    for k in range(i0, i1 + 1):
        x = vm.x(int(srv[k]))
        o, h, l, c = bars["o"][k], bars["h"][k], bars["l"][k], bars["c"][k]
        dr.line([(x, vm.y(h)), (x, vm.y(l))], fill=0, width=1)
        yo, yc = vm.y(o), vm.y(c)
        top, bot = min(yo, yc), max(yo, yc)
        if c >= o:
            dr.rectangle([x - bw / 2, top, x + bw / 2, max(bot, top + 1)],
                         outline=0)
        else:
            dr.rectangle([x - bw / 2, top, x + bw / 2, max(bot, top + 1)],
                         fill=0)
    dr.line([(vm.x(int(srv[k])), vm.y(ema[k])) for k in range(i0, i1 + 1)],
            fill=0, width=1)
    dr.line([(vm.x0, vm.y1), (vm.x1, vm.y1)], fill=0)
    dr.line([(vm.x1, vm.y0), (vm.x1, vm.y1)], fill=0)

    def barx(j):
        j = max(0, min(int(j), len(srv) - 1))
        return vm.x(int(srv[j]))

    # objects in book grammar
    tt_on = bool(getattr(engine, "p", {}).get("trade_tags"))
    for o in engine.objects:
        od = o.to_dict() if not isinstance(o, dict) else o
        g = od["geometry"]
        if od["t_birth"] > i1 or \
                (od["t_right"] is not None and od["t_right"] < i0):
            continue
        # R78/R81 TT: objects carrying a TRADE_VIEW_HIDE tag render
        # thin grey (the future "trade view" hides them); lone_edge
        # stays normal ink; flag off or no facts -> identical ink.
        tt = (od.get("facts") or {}).get("trade_tags") or {}
        grey = tt_on and bool(TT.TRADE_VIEW_HIDE &
                              set(tt.get("tags") or ()))
        ink = 170 if grey else 0
        xl = barx(od["t_left"])
        xr = barx(min(od["t_right"] if od["t_right"] is not None else i1,
                      i1))
        typ = od["type"]
        dash = (od["state"] != "ACTIVE")
        if typ == "BOX":
            dr.rectangle([xl, vm.y(g["top"] * PIP), xr,
                          vm.y(g["bottom"] * PIP)], outline=ink)
        elif typ == "RANGE_OPEN":
            _dash_hline(dr, xl, vm.x1, vm.y(g["top"] * PIP), ink, 8, 4)
            _dash_hline(dr, xl, vm.x1, vm.y(g["bottom"] * PIP), ink, 8, 4)
        elif typ == "CONTEXT_RANGE":
            _dash_rect(dr, xl, vm.y(g["top"] * PIP), xr,
                       vm.y(g["bottom"] * PIP), ink if grey else 110)
        elif typ == "PATTERN_LINE":
            x_end = xr
            p_end = g["p0"] + g["slope"] * (min(od["t_right"] or i1, i1)
                                            - g["t0"])
            dr.line([(barx(g["t0"]), vm.y(g["p0"] * PIP)),
                     (x_end, vm.y(p_end * PIP))], fill=ink, width=1)
        elif typ == "CONTEXT_LINE":
            p_end = g["p0"] + g["slope"] * (i1 - g["t0"])
            x0, y0 = barx(g["t0"]), vm.y(g["p0"] * PIP)
            x1, y1 = vm.x1, vm.y(p_end * PIP)
            n = 60
            for s in range(n):
                xx = x0 + (x1 - x0) * s / n
                yy = y0 + (y1 - y0) * s / n
                if s % 2 == 0:
                    dr.point((xx, yy), fill=ink if grey else 110)
        elif typ == "LEVEL_CARRIED":
            _dash_hline(dr, xl, vm.x1, vm.y(g["price"] * PIP), ink, 10, 6)
        elif typ == "MINI_LEVEL":
            dr.line([(xl, vm.y(g["price"] * PIP)),
                     (xr, vm.y(g["price"] * PIP))], fill=ink,
                    width=1 if grey else 2)
        elif typ == "SQUEEZE":
            dr.arc([xl, vm.y(g["top"] * PIP), xr,
                    vm.y(g["bottom"] * PIP)], 0, 360, fill=ink)
        elif typ == "BRACKET":
            # R77 s.77.5: the mark hugs the formation's extreme —
            # above the tops for M-family, below the lows for
            # W-family, at ~0.5*ABR — never a fixed band of the plot.
            # Mirrors golden/qa/_render_v2.py's placement.  The span
            # uses the object's shifted indices (geometry t0/t1 stay
            # warmup-based under scale/gallery.py's _ScaledObj).
            above = g.get("letter") in ("M", "Mm", "SHS")
            s0 = max(0, min(int(od["t_left"]), len(srv) - 1))
            s1 = max(0, min(int(od["t_right"] or i1), len(srv) - 1))
            abrs = getattr(engine, "abr", None)
            abr = float(abrs[min(i1, len(abrs) - 1)]) \
                if abrs is not None and len(abrs) else 5.0
            if above:
                p = float(bars["h"][s0:s1 + 1].max()) / PIP \
                    + 0.5 * abr
            else:
                p = float(bars["l"][s0:s1 + 1].min()) / PIP \
                    - 0.5 * abr
            y = vm.y(p * PIP)
            dr.line([(xl, y), (xr, y)], fill=ink)
            dr.text(((xl + xr) / 2 - 4, y - 12 if above else y + 4),
                    g["letter"], fill=ink)
        elif typ == "LABEL_TF":
            y = vm.y(g["price"] * PIP)
            y += -16 if g["side"] == "above" else 16
            dr.text((barx(od["t_birth"]) - 3, y), g["letter"], fill=ink)
        elif typ == "FALSE_EXT":
            x = barx(od["t_birth"])
            y = vm.y(g["price"] * PIP)
            dr.line([(x - 4, y), (x + 4, y)], fill=ink,
                    width=1 if grey else 2)

    dr.text((vm.x0 + 2, 2), title, fill=0)
    im.save(path)
    return path
