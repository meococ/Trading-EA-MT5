"""ceiling_render.py -- F-B3 human-ceiling drawing sheets.

One blind base render per sampled panel: candles + EMA25 + faint 00/50
grid, bars STOP at the panel tau, dashed tau divider, no engine ink, no
author ink, no titles (HUMAN_CEILING_PROTOCOL s.Drawing sheet).

Per panel writes:
  ceiling_kit/<id>.png   -- the sheet
  ceiling_kit/<id>.json  -- axis map: plot rect px, px<->bar open time,
                            px<->price, the tau bar's time
  _ceiling_key/<id>.json -- panel -> scorable goldens (kept OUT of kit)

Usage: python ceiling_render.py <seed>
"""
import sys, os, json, datetime as dt
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "evalcheck"))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "golden", "qa"))
sys.path.insert(0, os.path.join(HERE, "golden"))

import book_loader            # noqa: E402
import _render_v2 as R        # noqa: E402
import common as C           # noqa: E402
import eval as EV            # noqa: E402
import eval_v2 as V2         # noqa: E402
from ceiling_sample import draw, panel_stats   # noqa: E402

PIP = C.PIP
KIT = os.path.join(HERE, "ceiling_kit")
KEY = os.path.join(HERE, "_ceiling_key")


def render_sheet(rec, tau, png_path, axis_path):
    day = rec["date"]
    d0 = dt.date.fromisoformat(day)
    bars = book_loader.load_m5(day + " 00:00",
                               (d0 + dt.timedelta(days=1)).isoformat()
                               + " 00:00")
    srv = bars["cet_min"].astype(int)
    t0 = int(rec["window"]["x0"]) - 150
    t1 = min(int(rec["window"]["x1"]), int(tau)) + 30
    vis = (srv >= t0) & (srv <= t1)
    if not vis.any():
        return None
    idx = np.where(vis)[0]
    draw_idx = idx[srv[idx] <= tau]          # bars stop at tau
    p_lo = float(bars["l"][idx].min()) - 8 * PIP
    p_hi = float(bars["h"][idx].max()) + 8 * PIP
    vm = R.VMap(t0, t1, p_lo, p_hi)
    im = Image.new("L", (R.W, R.H), 255)
    dr = ImageDraw.Draw(im)

    p = int(p_lo / (50 * PIP) + 1) * 50 * PIP
    while p < p_hi:
        y = vm.y(p)
        R._dash_h(dr, vm.x0, vm.x1, y, 215, 2, 6)
        dr.text((vm.x1 + 8, y - 5), "%.4f" % p, fill=0)
        p += 50 * PIP
    p = int(p_lo / (25 * PIP) + 1) * 25 * PIP
    while p < p_hi:
        if abs(round(p / PIP) % 50) > 1e-6:
            y = vm.y(p)
            dr.line([(vm.x1, y), (vm.x1 + 4, y)], fill=0)
            dr.text((vm.x1 + 8, y - 5), "%.4f" % p, fill=110)
        p += 25 * PIP

    closes = bars["c"]
    alpha = 2.0 / 26
    e, ema = None, []
    for k in range(len(closes)):
        e = closes[k] if e is None else e + alpha * (closes[k] - e)
        ema.append(e)
    px_bar = vm.x(t0 + 5) - vm.x(t0)
    bw = max(2, int(px_bar * 0.55))
    for k in draw_idx:
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
    ema_pts = [(vm.x(int(srv[k])), vm.y(ema[k])) for k in draw_idx]
    if len(ema_pts) > 1:
        dr.line(ema_pts, fill=80, width=1)

    # tau divider (dashed vertical at the decision bar)
    R._dash_v(dr, vm.x(int(tau)), vm.y0, vm.y1, 0, 6, 4)

    dr.line([(vm.x0, vm.y1), (vm.x1, vm.y1)], fill=0)
    dr.line([(vm.x1, vm.y0), (vm.x1, vm.y1)], fill=0)
    m = (t0 // 60) * 60
    while m <= t1:
        if m >= t0:
            x = vm.x(m)
            dr.line([(x, vm.y1), (x, vm.y1 + 4)], fill=0)
            dr.text((x - 12, vm.y1 + 8), R.hm(m % 1440), fill=0)
        m += 60
    m = (t0 // 30) * 30
    while m <= t1:
        if m >= t0 and m % 60:
            dr.line([(vm.x(m), vm.y1), (vm.x(m), vm.y1 + 3)], fill=120)
        m += 30

    im.save(png_path)
    axis = {"panel": rec["id"], "date": day, "tau": int(tau),
            "tau_x": vm.x(int(tau)),
            "plot_rect_px": {"x0": vm.x0, "x1": vm.x1,
                             "y0": vm.y0, "y1": vm.y1},
            "time_map": {"t_lo": vm.t_lo, "t_hi": vm.t_hi,
                         "x_lo": vm.x0, "x_hi": vm.x1},
            "price_map": {"p_lo": vm.p_lo, "p_hi": vm.p_hi,
                          "y_lo": vm.y0, "y_hi": vm.y1},
            "bar_open_times": [int(v) for v in srv[draw_idx]]}
    with open(axis_path, "w") as f:
        json.dump(axis, f, indent=1)
    return axis


def main(seed=20260922):
    os.makedirs(KIT, exist_ok=True)
    os.makedirs(KEY, exist_ok=True)
    for sess, dens, rec, ng, tau in draw(seed):
        png = os.path.join(KIT, "%s.png" % rec["id"])
        ax = os.path.join(KIT, "%s.json" % rec["id"])
        out = render_sheet(rec, tau, png, ax)
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        g2 = [g for g in EV.gold_objects(rec)[0]
              if V2.scorable(g, w0, w1)]
        with open(os.path.join(KEY, "%s.json" % rec["id"]), "w") as f:
            json.dump({"panel": rec["id"], "date": rec["date"],
                       "session": sess, "density": dens,
                       "tau": int(tau), "n_goldens": ng,
                       "goldens": g2}, f, indent=1, default=str)
        print("%-8s %-5s %-6s ng=%d tau=%s -> %s" %
              (rec["id"], sess, dens, ng, tau,
               "OK" if out else "FAIL"))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20260922)
