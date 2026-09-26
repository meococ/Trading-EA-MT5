"""render_compare.py — golden-vs-engine overlay renders (mandate item 3).

Base image: golden/qa/_render_v2.render() output (our M5 candles, EMA25,
axes, golden v2 objects in solid black — the QA look, unmodified).
Overlay (RGB): engine objects dashed —
  * blue   = matched under eval_v2 (the panel's greedy assignment)
  * red    = false positive (born, unmatched)
Golden objects get a status tag:
  * green `ok`   = matched
  * red   `MISS` = golden never matched

Output: evalcheck/renders/<enginehash>/<panel>.png for the 12 QA panels.

Usage: python evalcheck/render_compare.py [--engine v0|v1|both]
"""
import argparse
import collections
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "golden", "qa"))
sys.path.insert(0, os.path.join(PERC, "golden"))

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import _render_v2 as R                          # noqa: E402
from funnel import code_hash, V0_FILES, V1_FILES  # noqa: E402

PIP = EV.PIP
PANELS = ["9.1a", "9.13c", "9.23c", "9.33b", "9.45b", "9.54a",
          "9.63c", "9.29a", "9.29b", "9.38a", "9.39a", "9.41b"]

BLUE = (30, 80, 220)      # engine matched
RED = (220, 40, 40)       # engine false positive / golden MISS
GREEN = (0, 140, 60)      # golden matched

TSHORT = {"BOX": "BOX", "BRACKET": "BRK", "PATTERN_LINE": "PL",
          "CONTEXT_LINE": "CL", "LEVEL_CARRIED": "LC",
          "RANGE_OPEN": "RO", "MINI_LEVEL": "ML", "SQUEEZE": "SQ",
          "BAR_MARKER": "BM"}


def _dash_seg(dr, p0, p1, fill, dash=5, gap=4):
    """Dashed segment between two pixel points."""
    x0, y0 = p0
    x1, y1 = p1
    n = max(int(abs(x1 - x0) + abs(y1 - y0)), 1)
    for i in range(0, n, dash + gap):
        f0, f1 = i / n, min(i + dash, n) / n
        dr.line([(x0 + (x1 - x0) * f0, y0 + (y1 - y0) * f0),
                 (x0 + (x1 - x0) * f1, y0 + (y1 - y0) * f1)],
                fill=fill, width=2)


def _dash_rect_c(dr, x0, y0, x1, y1, fill):
    _dash_seg(dr, (x0, y0), (x1, y0), fill)
    _dash_seg(dr, (x0, y1), (x1, y1), fill)
    _dash_seg(dr, (x0, y0), (x0, y1), fill, 4, 3)
    _dash_seg(dr, (x1, y0), (x1, y1), fill, 4, 3)


def draw_engine(dr, vm, e, m, color, geom=None, bars=None):
    """One eval_v2 engine record, dashed, coloured by status.
    `geom` = the source object's geometry (render-only fields like
    bracket level that the frozen conversion does not carry).
    Returns an (x, y) anchor for the type/id tag, or None."""
    geom = geom or {}
    t0, t1 = e.get("t0"), e.get("t1")
    if t0 is None:
        return None
    if t1 is None:
        t1 = t0 + 5
    x0, x1 = vm.x(t0), vm.x(t1)
    ty = e["type"]
    if ty in V2.BOX_TYPES:
        if e.get("lo") is None:
            return None
        y_hi, y_lo = vm.y(e["hi"] * PIP), vm.y(e["lo"] * PIP)
        _dash_rect_c(dr, x0, y_hi, x1, y_lo, color)
        return (x0, y_hi)
    elif ty in V2.LINE_TYPES:
        if e.get("p0") is None:
            return None
        def y_at(tmin):
            j = int(np.searchsorted(m, tmin))
            j = min(j, len(m) - 1)
            return vm.y((e["p0"] + e["slope"] * (j - e["t0_bar"])) * PIP)
        _dash_seg(dr, (x0, y_at(t0)), (x1, y_at(t1)), color)
        return (x0, y_at(t0))
    elif ty in V2.LEVEL_TYPES:
        if e.get("price") is None:
            return None
        _dash_seg(dr, (x0, vm.y(e["price"] * PIP)),
                  (x1, vm.y(e["price"] * PIP)), color)
        return (x0, vm.y(e["price"] * PIP))
    elif ty == "BRACKET":
        # mirror golden/qa/_render_v2.py: mark hugs the formation
        # extreme over the drawn span, above for M-family letters,
        # below otherwise — never the level midline.
        letter = e.get("letter") or geom.get("letter")
        side = e.get("side") or geom.get("side")
        above = side == "above" or (
            side is None
            and (letter or "M") in ("M", "Mm", "SHS"))
        p = geom.get("price")
        if p is None and bars is not None:
            srv = bars["cet_min"].astype(int)
            sm = (srv >= t0) & (srv <= t1)
            if sm.any():
                p = (float(bars["h"][sm].max()) if above
                     else float(bars["l"][sm].min()))
                p = p / PIP + (4.0 if above else -4.0)
        if p is None:
            lp = geom.get("level", geom.get("mid"))
            if lp is None:
                return None
            p = lp
        y = vm.y(p * PIP)
        _dash_seg(dr, (x0, y), (x1, y), color)
        if letter:
            dr.text(((x0 + x1) / 2 - 6, y - 14 if above else y + 5),
                    letter, fill=color)
        return (x0, y)
    elif ty == "SQUEEZE":
        lp = geom.get("top", geom.get("mid"))
        yc = vm.y(lp * PIP) if lp is not None else vm.y0 + 16
        dr.arc([x0, yc - 10, x1, yc + 10], 0, 360, fill=color)
        return (x0, yc - 10)
    elif ty == "BAR_MARKER":
        y = vm.y(e["price"] * PIP) if e.get("price") else vm.y0 + 30
        dr.line([(x0 - 5, y), (x0 + 5, y)], fill=color, width=2)
        return (x0, y)
    elif ty == "LABEL_TF":
        pass                                    # marks handled separately
    return None


def render_panel(rec, cls, out_path, tmp_png, eng_hash=None):
    w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
    t, m, o, h, l, c = CA.bars(rec["date"])
    if eng_hash is not None:
        e = CA.run(eng_hash, cls, rec)
    else:
        e = EV.run_engine(cls, m, t, o, h, l, c, w1)

    gobjs, _u, _to = EV.gold_objects(rec)
    for g in gobjs:
        if g.get("t0") is None:
            g["t0"] = w0
        if g.get("t1") is None:
            g["t1"] = w1
    gmarks = EV.gold_marks(rec)
    g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
    gm2 = [gm for gm in gmarks if V2.scorable_mark(gm, w0, w1)]

    eobjs = V2.eng_objects(e, m, w0, w1)
    eboxes = [r for r in eobjs if r["type"] != "LABEL_TF"]
    emarks = [r for r in eobjs if r["type"] == "LABEL_TF"]
    pairs, mpairs = C.match_panel(g2, eboxes, gm2, emarks, m,
                                  V2.match, V2.match_mark, V2.score)
    hit_g = {gi for gi, _ in pairs}
    hit_e = {ei for _, ei in pairs}
    hit_gm = {id(gm) for gm, _ in mpairs}
    hit_em = {id(em) for _, em in mpairs}

    if not R.render(rec, tmp_png):
        return False
    im = Image.open(tmp_png).convert("RGB")
    dr = ImageDraw.Draw(im)
    # same view window as _render_v2
    srv_pad0 = int(rec["window"]["x0"]) - 150
    srv_pad1 = int(rec["window"]["x1"]) + 40
    vm = R.VMap(srv_pad0, srv_pad1, 0, 1)
    # recompute p_lo/p_hi exactly as _render_v2 does
    import datetime as dt
    import book_loader
    day = rec["date"]
    d0 = dt.date.fromisoformat(day)
    bars = book_loader.load_m5(day + " 00:00",
                               (d0 + dt.timedelta(days=1)).isoformat()
                               + " 00:00")
    srv = bars["cet_min"].astype(int)
    vis = (srv >= srv_pad0) & (srv <= srv_pad1)
    idx = np.where(vis)[0]
    vm.p_lo = float(bars["l"][idx].min()) - 8 * PIP
    vm.p_hi = float(bars["h"][idx].max()) + 8 * PIP

    # engine objects, dashed (geometry from source objects for fields
    # the frozen record does not carry, e.g. bracket level); every
    # object is tagged <TYPE>#<short-id>
    src_geom = {o.id: o.geometry for o in e.objects}
    for ei, er in enumerate(eboxes):
        col = BLUE if ei in hit_e else RED
        a = draw_engine(dr, vm, er, m, col,
                        geom=src_geom.get(er.get("id")), bars=bars)
        if a is not None:
            sid = str(er.get("id") or ei)
            dr.text((a[0] + 2, a[1] - 13),
                    "%s#%s" % (TSHORT.get(er["type"], er["type"]),
                               sid[-6:]), fill=col)
    for em in emarks:
        x = vm.x(em["t_birth"])
        col = BLUE if id(em) in hit_em else RED
        p = em.get("price")
        if p is not None:
            y = vm.y(p * PIP)
            dr.text((x + 3, y - 16), em.get("letter") or "?", fill=col)
        else:
            dr.text((x + 3, vm.y0 + 4), em.get("letter") or "?",
                    fill=col)

    # golden status tags
    for gi, g in enumerate(g2):
        t0g = g.get("t0", w0)
        x = vm.x(t0g)
        yp = None
        for key in ("price_hi", "price1", "price0", "price"):
            if g.get(key) is not None:
                yp = vm.y(g[key])
                break
        y = (yp - 12) if yp is not None else vm.y0 + 14
        if gi in hit_g:
            dr.text((x, y), "ok", fill=GREEN)
        else:
            dr.text((x, y), "MISS", fill=RED)
    for gm in gm2:
        if gm.get("t") is None:
            continue
        x = vm.x(gm["t"])
        if id(gm) in hit_gm:
            dr.text((x, vm.y1 - 12), "ok", fill=GREEN)
        else:
            dr.text((x, vm.y1 - 12), "MISS", fill=RED)

    # legend (mandate Z3): colour key + type abbreviations
    lx, ly = vm.x0 + 300, 6
    dr.rectangle([lx - 6, ly - 3, lx + 640, ly + 26],
                 fill=(255, 255, 255), outline=(180, 180, 180))
    dr.text((lx, ly), "engine (dashed):", fill=(90, 90, 90))
    _dash_seg(dr, (lx + 105, ly + 5), (lx + 125, ly + 5), BLUE)
    dr.text((lx + 130, ly), "=matched", fill=BLUE)
    _dash_seg(dr, (lx + 195, ly + 5), (lx + 215, ly + 5), RED)
    dr.text((lx + 220, ly), "=false-pos", fill=RED)
    dr.text((lx + 300, ly), "golden tag:", fill=(90, 90, 90))
    dr.text((lx + 365, ly), "ok", fill=GREEN)
    dr.text((lx + 382, ly), "/", fill=(90, 90, 90))
    dr.text((lx + 390, ly), "MISS", fill=RED)
    dr.text((lx, ly + 12),
            "types: BOX BRK=bracket PL=pattern_line CL=context_line "
            "LC=level_carried RO=range_open ML=mini_level SQ=squeeze "
            "BM=bar_marker", fill=(90, 90, 90))
    im.save(out_path)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="both")
    ap.add_argument("--v1-hash", default=None,
                    help="pin a cached v1 hash (pickle-only run)")
    args = ap.parse_args()
    import engine_v0 as ENG_V0
    recs = {r["id"]: r for r in C.load_tune()}
    rvdir = os.path.join(HERE, "rv")
    os.makedirs(rvdir, exist_ok=True)
    engines = [("v0", ENG_V0.PerceptionEngine, code_hash(V0_FILES))]
    if args.v1_hash:
        engines.append(("v1", None, args.v1_hash))
    else:
        import engine as ENG_V1
        engines.append(("v1", ENG_V1.PerceptionEngine,
                        code_hash(V1_FILES)))
    for tag, cls, h in engines:
        if args.engine != "both" and args.engine != tag:
            continue
        outdir = os.path.join(HERE, "renders", "%s_%s" % (tag, h))
        os.makedirs(outdir, exist_ok=True)
        tmp = os.path.join(outdir, "_tmp.png")
        for pid in PANELS:
            if pid not in recs:
                print("missing panel", pid)
                continue
            out = os.path.join(outdir, "%s.png" % pid)
            ok = render_panel(recs[pid], cls, out, tmp, eng_hash=h)
            if ok:          # flat copy: rv/<hash8>_<panel>.png (Z3)
                import shutil
                shutil.copy(out, os.path.join(
                    rvdir, "%s_%s.png" % (h[:8], pid)))
            print("%s %s -> %s" % (tag, pid, "ok" if ok else "FAIL"))
        # _tmp.png is left in place (no deletes, R12 §12.5)


if __name__ == "__main__":
    main()
