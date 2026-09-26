"""render_audit — draw audited golden BOXes for X1 (seed 20260921).

Own renderer (overlay.py conventions: B/W candles, EMA25, faint grid) plus
the audited box: solid rect over drawn span, vertical markers at
build_start / build_end, and a gray band for the containment window.
Writes boxlab/audit_png/<panel>_<idx>.png.
"""
import json
import os
import sys
import random

import numpy as np
from PIL import Image, ImageDraw

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
for _p in (_HERE, os.path.join(_PERC, "golden")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bars_cache as BC            # noqa: E402

TUNE_JSONL = os.path.join(_PERC, "golden", "draft", "BOOK2012_TUNE_v2.jsonl")
OUT_DIR = os.path.join(_HERE, "audit_png")
SEED = 20260921


class VMap:
    def __init__(self, t_lo, t_hi, p_lo, p_hi, W=1180, H=380,
                 x_left=44, x_right_pad=70, y_top=14, y_bot_pad=26):
        self.W, self.H = W, H
        self.x0, self.x1 = x_left, W - x_right_pad
        self.y0, self.y1 = y_top, H - y_bot_pad
        self.t_lo, self.t_hi = t_lo, t_hi
        self.p_lo, self.p_hi = p_lo, p_hi

    def x(self, m):
        return self.x0 + (m - self.t_lo) / (self.t_hi - self.t_lo) \
            * (self.x1 - self.x0)

    def y(self, p):
        return self.y1 - (p - self.p_lo) / (self.p_hi - self.p_lo) \
            * (self.y1 - self.y0)


def render_audit(rec, o, day, abr, path):
    m = day["m"]
    w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
    t0 = max(0, (o.get("t0") or w0) - 120)
    t1 = min(1439, (o.get("t1") or w1) + 60)
    vis = (m >= t0) & (m <= t1)
    if not vis.any():
        return False
    hh, ll = day["h"][vis], day["l"][vis]
    p_lo, p_hi = float(ll.min()) - 8.0, float(hh.max()) + 8.0
    vm = VMap(t0, t1, p_lo, p_hi)
    im = Image.new("L", (vm.W, vm.H), 255)
    dr = ImageDraw.Draw(im)

    p = int(p_lo / 50 + 1) * 50.0
    while p < p_hi:
        y = vm.y(p)
        x = vm.x0
        while x < vm.x1:
            dr.line([(x, y), (min(x + 2, vm.x1), y)], fill=215)
            x += 8
        p += 50.0

    px_bar = vm.x(t0 + 5) - vm.x(t0)
    bw = max(2, int(px_bar * 0.55))
    idx = np.where(vis)[0]
    ema = np.zeros(len(day["c"]))
    e = None
    a = 2.0 / 26.0
    for k in range(len(day["c"])):
        e = day["c"][k] if e is None else e + a * (day["c"][k] - e)
        ema[k] = e
    for k in idx:
        x = vm.x(int(m[k]))
        dr.line([(x, vm.y(day["h"][k])), (x, vm.y(day["l"][k]))], fill=0)
        yo, yc = vm.y(day["o"][k]), vm.y(day["c"][k])
        top, bot = min(yo, yc), max(yo, yc)
        if day["c"][k] >= day["o"][k]:
            dr.rectangle([x - bw / 2, top, x + bw / 2, max(bot, top + 1)],
                         outline=0)
        else:
            dr.rectangle([x - bw / 2, top, x + bw / 2, max(bot, top + 1)],
                         fill=0)
    dr.line([(vm.x(int(m[k])), vm.y(ema[k])) for k in idx], fill=0)
    dr.line([(vm.x0, vm.y1), (vm.x1, vm.y1)], fill=0)
    dr.line([(vm.x1, vm.y0), (vm.x1, vm.y1)], fill=0)

    lo = o.get("price_lo"); hi = o.get("price_hi")
    if lo is None or hi is None:
        a2, b2 = o.get("price"), o.get("price2")
        if a2 is None or b2 is None:
            return False
        lo, hi = min(a2, b2), max(a2, b2)
    lo_p, hi_p = lo * 1e4, hi * 1e4
    ot0, ot1 = o.get("t0"), o.get("t1")
    bs = o.get("build_start") if o.get("build_start") is not None else ot0
    be = o.get("build_end") if o.get("build_end") is not None else ot1

    # containment window band
    if bs is not None and be is not None and be > bs:
        x0, x1 = vm.x(bs), vm.x(be)
        for x in np.arange(x0, x1, 3.0):
            dr.line([(x, vm.y(hi_p)), (x, vm.y(lo_p))], fill=225)
    # drawn box
    if ot0 is not None and ot1 is not None:
        dr.rectangle([vm.x(ot0), vm.y(hi_p), vm.x(ot1), vm.y(lo_p)],
                     outline=0, width=2)
    # build window edges
    for t, fill in ((bs, 0), (be, 90)):
        if t is not None:
            x = vm.x(t)
            dr.line([(x, vm.y0), (x, vm.y1)], fill=fill)
    dr.text((vm.x0 + 2, 2),
            "%s  %s  box@%s  h=%.1fp  bs=%s be=%s" % (
                rec["id"], rec["date"], o.get("idx", "?"),
                hi_p - lo_p, bs, be), fill=0)
    im.save(path)
    return True


def main():
    recs = [json.loads(x) for x in open(TUNE_JSONL, encoding="utf8")]
    dates, bars = BC.load_all()
    picks = []
    for rec in recs:
        for i, o in enumerate(rec.get("objects", [])):
            if o.get("spec_type") == "BOX" and \
                    o.get("status") in ("ok", "repaired"):
                o2 = dict(o); o2["idx"] = i
                picks.append((rec, o2))
    random.Random(SEED).shuffle(picks)
    os.makedirs(OUT_DIR, exist_ok=True)
    n = 0
    for rec, o in picks:
        if n >= 20:
            break
        day = bars.get(rec["date"])
        if day is None:
            continue
        abr = BC.abr50(day["h"], day["l"], day["c"])
        out = os.path.join(OUT_DIR, "%s_box%d.png" % (rec["id"], o["idx"]))
        if render_audit(rec, o, day, abr, out):
            print("rendered", rec["id"], "obj", o["idx"])
            n += 1
    print("total", n)


if __name__ == "__main__":
    main()
