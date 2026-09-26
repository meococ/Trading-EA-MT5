"""render_review_set.py — G-KIT (R80 §80.6): one CLI renders the full
live chart at tau for the Gemini chart reviewer.

Per panel: one PNG 1700x620 — candles, EMA25 grey, faint 00/50 grid,
dashed vertical "now" line at tau, bars ONLY up to tau — plus every
object live at tau drawn in the book grammar (solid box, sloped line,
long-dashed level, T/F letters, BRACKET hugging the formation extreme
per R77 §77.5), all objects clipped at tau.  Corner label = panel id
only (no arm name, no scores).  A <panel>.json sidecar lists the drawn
objects for the Lead's triage.

Arms:
  --arm c3              canonical caches: run_uip2_pbbirth_8361fe85…
                        _<date>_<tau>.pkl (STABLE C-3, tree
                        1a5502129b4c1554).  Cache reads only.
  --arm <name> --flags k=v,…   live engine run with params patched
                        (dotted keys ok: salience.ev_uip=1).  An engine
                        run is HEAVY: this mode refuses unless invoked
                        under tools/heavy_run.py --lane gkit with
                        GKIT_UNDER_HEAVY=1 exported (env propagates).
  --arm <name> --override f.jsonl   offline arms (S1/H0): rows
                        {"panel","tau","objects":[…]} or one object
                        per row {"panel","tau", …object fields…}.

Review panels: --make-panels writes review/review_panels.json once
(fixed forever, seed 20260923): 12 TUNE golden-decision points —
4 box-led, 4 level-led, 4 line-led — from deepresearch/
DR_RULES_events.jsonl, distinct dates, excluding the p099-p102 panels
(owner_pack/dr_rules_item_geom.jsonl — the sealed key is never
opened) and the 10 ceiling panels (ceiling_sample.draw / ceiling_kit).

Calibration: --calib renders p099-p102 in the same style (one blue
object each, no bars after tau) as calib_1..calib_4 in random order
(seed 20260923); mapping -> review/sets/calib/_map.json.

Self-test: --selftest proves byte-determinism (same panel rendered
twice -> identical PNG) and causality (no dark pixel column right of
the "now" line inside the plot).

pa_slots: importing lib/pa_slots sets this process BelowNormal and
caps math threads (<= 1 slot, Owner rule).  TUNE only; HOLD sealed.

Usage:
  python review/render_review_set.py --make-panels
  python review/render_review_set.py --arm c3
  python review/render_review_set.py --arm s1a \
      --override deepresearch/S1_a_objects.jsonl
  set GKIT_UNDER_HEAVY=1 && python tools/heavy_run.py --lane gkit -- \
      python review/render_review_set.py --arm ttv --flags trade_tags=1
  python review/render_review_set.py --calib
  python review/render_review_set.py --arm c3 --sheet
  python review/render_review_set.py --selftest
"""
import argparse
import collections
import datetime as dt
import json
import os
import pickle
import random
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)                          # research/perception
PROOT = os.path.dirname(os.path.dirname(PERC))        # PA_Pro
for _p in (os.path.join(PERC, "evalcheck"), PERC,
           os.path.join(PERC, "boxlab"),
           os.path.join(PERC, "golden"),
           os.path.join(PERC, "golden", "qa"),
           os.path.join(PROOT, "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pa_slots  # noqa: E402,F401  (BelowNormal + thread caps on import)
import common as C                                   # noqa: E402
import eval as EV                                    # noqa: E402
import cache as CA                                   # noqa: E402
import ceiling_render as CR                          # noqa: E402
import _render_v2 as R                               # noqa: E402
import ceiling_sample as CS                         # noqa: E402
import trade_tags as TT                             # noqa: E402
# R81 s.81.5(1): --drop-tagged and the grey style hide only objects
# carrying a TRADE_VIEW_HIDE tag (lone_edge is a fact, not a hide).

PIP = 1e-4
SEED = 20260923
ARM_H = "8361fe85e73f9437"          # STABLE C-3 engine-code hash
ARM_V = "uip2_pbbirth"              #           …cache variant
STABLE = "1a5502129b4c1554"         #           …tree id (provenance)
FAM_ORDER = ("box", "level", "line")
ITEM_BLUE = (25, 65, 205)           # owner-pack item colour (R30 §30.2)
TAU_GREY = (150, 150, 150)

PANELS_JSON = os.path.join(HERE, "review_panels.json")
GEOM_JSONL = os.path.join(PERC, "owner_pack",
                          "dr_rules_item_geom.jsonl")
EVENTS_JSONL = os.path.join(PERC, "deepresearch",
                            "DR_RULES_events.jsonl")
SETS = os.path.join(HERE, "sets")
LOG = os.path.join(HERE, "GKIT_LOG.md")


def log_line(msg):
    with open(LOG, "a", encoding="utf8") as fh:
        fh.write("- %s %s\n" % (
            dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%MZ"),
            msg))


# ------------------------------------------------------------------ #
# panels file
# ------------------------------------------------------------------ #

def _pack_panels():
    """Panels of owner-pack items p099-p102 (geometry export only —
    evalcheck/_owner_judge_key/ is never opened)."""
    out = set()
    for line in open(GEOM_JSONL, encoding="utf8"):
        r = json.loads(line)
        if r["seq"] in ("p099", "p100", "p101", "p102"):
            out.add(r["panel"])
    return out


def _ceiling_panels():
    """The 10 human-ceiling panels (ceiling_sample seed 20260922)."""
    return {rec["id"] for _s, _d, rec, _ng, _t in CS.draw(20260922)}


def _c3_pkl(date, w1):
    f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                     % (ARM_V, ARM_H, date, w1))
    return f if os.path.exists(f) else None


def make_panels(seed=SEED):
    """12 fixed review panels: 4 box-led + 4 level-led + 4 line-led
    TUNE golden-decision points, distinct dates, deterministic."""
    rng = random.Random(seed)
    excluded = _pack_panels() | _ceiling_panels()
    recs = {r["id"]: r for r in C.load_tune()}
    events = []
    for line in open(EVENTS_JSONL, encoding="utf8"):
        r = json.loads(line)
        if r["kind"] != "obj" or not r["gs_fam"]:
            continue
        if r["panel"] in excluded or r["panel"] not in recs:
            continue
        if _c3_pkl(r["date"], r["tau"]) is None:
            continue
        events.append(r)
    used_dates, used_panels, panels = set(), set(), []
    for fam in FAM_ORDER:
        # prefer single-family decisions ("the golden decision IS a
        # box"); relax to fam ⊆ gs_fam only if pure runs dry
        for pred in (lambda e, f=fam: e["gs_fam"] == [f],
                     lambda e, f=fam: f in e["gs_fam"]):
            bag = [e for e in events if pred(e)]
            rng.shuffle(bag)
            for e in bag:
                if len([p for p in panels
                        if p["golden_fam"] == fam]) >= 4:
                    break
                if e["date"] in used_dates or e["panel"] in used_panels:
                    continue
                used_dates.add(e["date"])
                used_panels.add(e["panel"])
                rec = recs[e["panel"]]
                panels.append({"name": e["panel"], "panel": e["panel"],
                               "date": e["date"], "tau": e["tau"],
                               "golden_fam": fam,
                               "window": dict(rec["window"])})
            if len([p for p in panels
                    if p["golden_fam"] == fam]) >= 4:
                break
    if len(panels) != 12:
        log_line("ESCALATE make_panels picked %d/12" % len(panels))
    panels.sort(key=lambda p: (p["date"], p["tau"]))
    doc = {"seed": seed, "fixed": True, "tune_only": True,
           "hold": "sealed",
           "source": "deepresearch/DR_RULES_events.jsonl kind=obj",
           "excluded": {"p099_p102_panels": sorted(_pack_panels()),
                        "ceiling_panels": sorted(_ceiling_panels())},
           "panels": panels}
    with open(PANELS_JSON, "w", encoding="utf8") as fh:
        json.dump(doc, fh, indent=1)
    print("wrote %s (%d panels)" % (PANELS_JSON, len(panels)))
    for p in panels:
        print("  %-6s %-6s %s tau=%-4d %s" % (
            p["name"], p["date"], p["golden_fam"], p["tau"],
            p["window"]))
    return doc


def load_panels(path):
    doc = json.load(open(path, encoding="utf8"))
    return doc["panels"]


# ------------------------------------------------------------------ #
# object normalisation -> one draw-record
# ------------------------------------------------------------------ #
# draw-record: {"type","state","id","t_left","t_right","t_birth",
#               "geom"(pips / bar-idx, engine layout), "facts"}
# bar indices address the day-bars arrays (CA.bars); engine bar idx ==
# day-bar idx (run_engine feeds the day's bars in order).

def norm_engine(o):
    d = o.to_dict() if not isinstance(o, dict) else o
    return {"type": d["type"], "state": d.get("state", "ACTIVE"),
            "id": d.get("id"), "t_left": d.get("t_left"),
            "t_right": d.get("t_right"), "t_birth": d.get("t_birth"),
            "geom": d.get("geometry") or {},
            "facts": d.get("facts") or {}}


def norm_override(o):
    """Override jsonl object -> draw-record.  Two spellings:
      engine: {"type","state","t_left","t_right","t_birth",
               "geometry":{pips/bar-idx}}            (verbatim draw)
      item  : {"kind"|"type", "t0","t1" CET-min, lo/hi|price|p0/p1
               raw-price | p0+slope(pips/bar)+t0_bar, letter, side}
    Item minutes are converted to bar indices via the day's bar map
    passed to draw (kept as minutes here under *_min keys)."""
    if "geometry" in o or "t_left" in o:
        d = norm_engine(o)
        return d
    it = dict(o)
    typ = it.get("type") or it.get("kind")
    g = {}
    for k in ("letter", "side"):
        if it.get(k) is not None:
            g[k] = it[k]
    if it.get("lo") is not None and it.get("hi") is not None:
        g["bottom"], g["top"] = it["lo"] / PIP, it["hi"] / PIP
    if it.get("price") is not None:
        g["price"] = it["price"] / PIP
    if it.get("p0") is not None:
        g["p0_raw"] = it["p0"]                    # raw price at t0
    if it.get("p1") is not None:
        g["p1_raw"] = it["p1"]                    # raw price at t1
    if it.get("slope") is not None:
        # engine spelling: pips/bar, anchored at bar t0_bar
        g["p0"] = (it["p0"] / PIP) if it.get("p0") is not None else None
        g["slope"] = it["slope"]
        g["t0"] = it.get("t0_bar", 0)
    return {"type": typ, "state": it.get("state", "ACTIVE"),
            "id": it.get("id"),
            "t_left": it.get("t0"), "t_right": it.get("t1"),
            "t_birth": it.get("t_birth", it.get("t0")),
            "geom": g, "facts": it.get("facts") or {},
            "_minutes": True}      # t_left/t_right/t_birth are CET min


# ------------------------------------------------------------------ #
# the book grammar (mirror of render.py's per-type ink + R77 §77.5)
# ------------------------------------------------------------------ #

FADE_INK = 200            # R83 s83.6: faded broken-box ink (light)
FADE_DASH, FADE_GAP = 4, 4        # dashed, thin (width stays 1)


def draw_objects(dr, vm, objs, m, h, l, abr_tau, i_tau, tau_x,
                 tt_on=False, drop_tagged=False, hide_tags=None,
                 hidden_out=None, fade_broken=False, faded_out=None):
    """Draw every object live at tau, clipped at tau_x.

    m,h,l: day-bar arrays (cet_min, high, low — pips).  abr_tau: ABR at
    the last fed bar (pips).  i_tau: bar index of tau (last fed bar).
    tt_on: tagged objects render thin grey (render.py convention).
    drop_tagged: the trade view — objects carrying a
    TRADE_VIEW_HIDE tag are not drawn (lone_edge is a fact, not a
    hide — R81 §81.5(1)).  hide_tags: an explicit csv set that hides
    (TT-v1 hide subset).  hidden_out: list to collect the tag-hidden
    records for the diff.  Returns the drawn-object list
    (minute/raw-price coordinates)."""
    drawn = []
    i0 = int(np.searchsorted(m, vm.t_lo))   # left edge of the view
    for od in objs:
        geom = od["geom"]
        is_min = od.get("_minutes")
        if is_min:                       # item-style times -> bar idx
            def b2i(tmin):
                j = int(np.searchsorted(m, tmin))
                return max(0, min(j, len(m) - 1))
            tl = b2i(od["t_left"]) if od["t_left"] is not None else 0
            tr = b2i(od["t_right"]) if od["t_right"] is not None \
                else None
            tb = b2i(od["t_birth"]) if od["t_birth"] is not None \
                else tl
        else:
            tl = int(od["t_left"] or 0)
            tr = int(od["t_right"]) if od["t_right"] is not None \
                else None
            tb = int(od["t_birth"]) if od["t_birth"] is not None \
                else tl
        # render.py's window test: not yet born, or ended before the
        # view's left edge -> invisible.  Plus: left edge past tau =
        # nothing drawn yet.
        if tb > i_tau or (tr is not None and tr < i0) or tl > i_tau:
            continue
        tags = set(((od.get("facts") or {}).get("trade_tags")
                    or {}).get("tags") or ())
        hide_why = set()
        if drop_tagged:
            hide_why |= TT.TRADE_VIEW_HIDE & tags
        if hide_tags:
            hide_why |= tags & set(hide_tags)
        faded = False
        if fade_broken and "box_broken" in tags and \
                EV.FAMILY.get(od["type"]) == "box":
            # R83 s83.6: a broken box is drawn faded+truncated
            # instead of hidden; every OTHER hide tag still hides.
            hide_why -= {"box_broken"}
            faded = not hide_why
        if hide_why:
            if hidden_out is not None:
                hidden_out.append({"id": od.get("id"),
                                   "type": od["type"],
                                   "tags": sorted(tags),
                                   "hide_tags": sorted(hide_why)})
            continue                    # R81 s81.5(1): hide-set view
        tr_c = min(tr, i_tau) if tr is not None else i_tau
        exit_i = None
        if faded:
            tt_f = (od.get("facts") or {}).get("trade_tags") or {}
            eb = tt_f.get("exit_bar")
            if eb is not None:
                exit_i = int(eb)
                tr_c = min(tr_c, exit_i)        # truncate at break
            if faded_out is not None:
                faded_out.append({
                    "id": od.get("id"), "type": od["type"],
                    "exit_bar": exit_i,
                    "break_clause": tt_f.get("break_clause"),
                    "tags": sorted(tags)})

        def barx(j):
            j = max(0, min(int(j), len(m) - 1))
            return vm.x(int(m[j]))

        xl = barx(tl)
        xr = min(barx(tr_c), tau_x)
        if xr < xl:
            xr = xl
        grey = tt_on and bool(TT.TRADE_VIEW_HIDE & tags)
        ink = FADE_INK if faded else (170 if grey else 0)
        typ = od["type"]
        g = geom

        def Y(pips):
            return vm.y(pips * PIP)

        rec = {"id": od.get("id"), "type": typ, "state": od["state"],
               "t0_min": int(m[max(0, min(tl, len(m) - 1))]),
               "t1_min": int(m[max(0, min(tr_c, len(m) - 1))]),
               "tags": sorted(tags) if tags else []}
        if faded:
            rec["faded"] = True
            if exit_i is not None:
                rec["exit_bar_min"] = int(
                    m[max(0, min(exit_i, len(m) - 1))])
        if typ == "BOX":
            if faded:                   # R83 s83.6: dashed thin grey
                R._dash_rect(dr, xl, Y(g["top"]), xr, Y(g["bottom"]),
                             ink, FADE_DASH, FADE_GAP)
            else:
                dr.rectangle([xl, Y(g["top"]), xr, Y(g["bottom"])],
                             outline=ink)
            rec.update(lo_raw=g["bottom"] * PIP, hi_raw=g["top"] * PIP)
        elif typ == "RANGE_OPEN":
            R._dash_h(dr, xl, xr, Y(g["top"]), ink, 8, 4)
            R._dash_h(dr, xl, xr, Y(g["bottom"]), ink, 8, 4)
            rec.update(lo_raw=g["bottom"] * PIP, hi_raw=g["top"] * PIP)
        elif typ == "CONTEXT_RANGE":
            R._dash_rect(dr, xl, Y(g["top"]), xr, Y(g["bottom"]),
                         ink if grey else 110)
            rec.update(lo_raw=g["bottom"] * PIP, hi_raw=g["top"] * PIP)
        elif typ == "PATTERN_LINE":
            if "p0_raw" in g:            # item spelling: two endpoints
                p_a = g["p0_raw"] / PIP
                p_b = (g.get("p1_raw") or g["p0_raw"]) / PIP
                # interpolate the endpoint price at the clip bar
                span = max((od["t_right"] or od["t_left"])
                           - od["t_left"], 1) if is_min else \
                    max(tr_c - tl, 1)
                f = (tr_c - tl) / span
                dr.line([(xl, Y(p_a)), (xr, Y(p_a + (p_b - p_a) * f))],
                        fill=ink, width=1)
                rec.update(p0_raw=g["p0_raw"],
                           p1_raw=g.get("p1_raw"))
            else:
                p_end = g["p0"] + g["slope"] * (tr_c - g["t0"])
                dr.line([(barx(g["t0"]), Y(g["p0"])),
                         (xr, Y(p_end))], fill=ink, width=1)
                rec.update(p0_raw=g["p0"] * PIP, slope=g["slope"],
                           anchor_bar=g["t0"])
        elif typ == "CONTEXT_LINE":
            p_end = g["p0"] + g["slope"] * (tr_c - g["t0"])
            x0, y0 = barx(g["t0"]), Y(g["p0"])
            n = 60
            for s in range(n):
                xx = x0 + (xr - x0) * s / n
                yy = y0 + (Y(p_end) - y0) * s / n
                if s % 2 == 0:
                    dr.point((xx, yy), fill=ink if grey else 110)
            rec.update(p0_raw=g["p0"] * PIP, slope=g["slope"],
                       anchor_bar=g["t0"])
        elif typ == "LEVEL_CARRIED":
            R._dash_h(dr, xl, xr, Y(g["price"]), ink, 10, 6)
            rec.update(price_raw=g["price"] * PIP)
        elif typ == "MINI_LEVEL":
            dr.line([(xl, Y(g["price"])), (xr, Y(g["price"]))],
                    fill=ink, width=1 if grey else 2)
            rec.update(price_raw=g["price"] * PIP)
        elif typ == "SQUEEZE":
            dr.arc([xl, Y(g["top"]), xr, Y(g["bottom"])], 0, 360,
                   fill=ink)
            rec.update(lo_raw=g["bottom"] * PIP, hi_raw=g["top"] * PIP)
        elif typ == "BRACKET":
            # R77 §77.5: hug the formation's extreme — above the tops
            # for M-family, below the lows for W-family, at ~0.5*ABR.
            above = g.get("letter") in ("M", "Mm", "SHS")
            s0 = max(0, min(tl, len(m) - 1))
            s1 = max(0, min(tr_c, len(m) - 1))
            if s1 < s0:
                s1 = s0
            abr = float(abr_tau) if abr_tau else 5.0
            if above:
                p = float(h[s0:s1 + 1].max()) + 0.5 * abr
            else:
                p = float(l[s0:s1 + 1].min()) - 0.5 * abr
            y = Y(p)
            dr.line([(xl, y), (xr, y)], fill=ink)
            if g.get("letter"):
                dr.text(((xl + xr) / 2 - 4,
                         y - 12 if above else y + 4),
                        g["letter"], fill=ink)
            rec.update(price_raw=p * PIP, letter=g.get("letter"))
        elif typ == "LABEL_TF":
            y = Y(g["price"])
            y += -16 if g.get("side") == "above" else 16
            dr.text((barx(tb) - 3, y), g["letter"], fill=ink)
            rec.update(price_raw=g["price"] * PIP,
                       letter=g.get("letter"))
        elif typ == "FALSE_EXT":
            x = barx(tb)
            y = Y(g["price"])
            dr.line([(x - 4, y), (x + 4, y)], fill=ink,
                    width=1 if grey else 2)
            rec.update(price_raw=g["price"] * PIP)
        else:
            continue
        drawn.append(rec)
    return drawn


def draw_item(dr, vm, it, tau_x, m):
    """One owner-pack item, blue 3px (mirror of plausibility.draw_item;
    item clipped at tau).  Prices raw."""
    col = ITEM_BLUE
    k = it["kind"]
    t0 = it.get("t0")
    t1 = it.get("t1") if it.get("t1") is not None else t0
    if t0 is None:
        return False
    x0 = vm.x(t0)
    x1 = min(vm.x(t1), tau_x)
    drew = True
    if k in ("BOX", "CONTEXT_RANGE", "RANGE_OPEN"):
        if it.get("lo") is None or it.get("hi") is None:
            return False
        dr.rectangle([x0, vm.y(it["hi"]), x1, vm.y(it["lo"])],
                     outline=col, width=3)
    elif k in ("PATTERN_LINE", "CONTEXT_LINE"):
        if it.get("p0") is not None and it.get("p1") is not None:
            dr.line([(x0, vm.y(it["p0"])), (x1, vm.y(it["p1"]))],
                    fill=col, width=3)
        elif it.get("p0") is not None and it.get("slope") is not None:
            def y_at(tmin):
                j = int(np.searchsorted(m, tmin))
                j = min(j, len(m) - 1)
                return vm.y(it["p0"] + it["slope"]
                            * (j - it.get("t0_bar", 0)))
            dr.line([(x0, y_at(t0)), (x1, y_at(t1))], fill=col,
                    width=3)
        else:
            drew = False
    elif it.get("price") is not None:
        y = vm.y(it["price"])
        if k == "BAR_MARKER" or it.get("marker"):
            dr.polygon([(x0, y - 9), (x0 - 6, y - 1),
                        (x0 + 6, y - 1)], fill=col)
            dr.line([(x0, y - 1), (x0, y + 9)], fill=col, width=3)
        else:
            dr.line([(x0, y), (x1, y)], fill=col, width=3)
            if it.get("letter"):
                dr.text(((x0 + x1) / 2 - 6, y + 5), it["letter"],
                        fill=col)
    else:
        drew = False
    if k == "LABEL_TF" and it.get("letter"):
        y = vm.y(it["price"]) if it.get("price") else vm.y0 + 20
        dr.text((x0 + 2, y - 14), it["letter"], fill=col)
        drew = True
    return drew


# ------------------------------------------------------------------ #
# object sources
# ------------------------------------------------------------------ #

def engine_at_tau_cached(date, tau):
    """STABLE C-3 canonical cache: the tau-clipped pickled run."""
    f = _c3_pkl(date, tau)
    if f is None:
        return None
    try:
        with open(f, "rb") as fh:
            return pickle.load(fh)
    except Exception:
        return None                 # R26 §26.4: refuse, never serve


def engine_at_tau_flags(rec, tau, flags):
    """Live run with patched params — HEAVY: caller must be under
    tools/heavy_run.py --lane gkit (GKIT_UNDER_HEAVY=1)."""
    if os.environ.get("GKIT_UNDER_HEAVY") != "1":
        raise SystemExit(
            "--flags is an engine run: wrap it --\n"
            "  set GKIT_UNDER_HEAVY=1 && python "
            "tools/heavy_run.py --lane gkit -- python "
            "review/render_review_set.py --arm <name> --flags ...")
    import copy
    import engine as ENG
    params = copy.deepcopy(ENG.load_params())
    for kv in flags.split(","):
        k, _, v = kv.partition("=")
        k = k.strip()
        try:
            val = json.loads(v)
        except ValueError:
            val = v.strip()
        node = params
        parts = k.split(".")
        for p_ in parts[:-1]:
            node = node.setdefault(p_, {})
        node[parts[-1]] = val
    t, m, o, h, l, c = CA.bars(rec["date"])
    rec_t = dict(rec, window=dict(rec["window"], x1=tau))
    cls = lambda: ENG.PerceptionEngine(copy.deepcopy(params))  # noqa: E731
    return EV.run_engine(cls, m, t, o, h, l, c,
                         rec_t["window"]["x1"],
                         w0=rec["window"]["x0"])


def objects_from_engine(e):
    """Objects live at tau: born objects not DELETED (snapshot.py)."""
    return [norm_engine(o) for o in e.objects if o.state != "DELETED"]


def objects_from_override(path, panel_id, tau):
    """Rows {"panel","tau","objects":[…]} or one object per row."""
    objs = []
    for line in open(path, encoding="utf8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if r.get("panel") != panel_id or int(r.get("tau", -1)) != \
                int(tau):
            continue
        if isinstance(r.get("objects"), list):
            objs += [norm_override(o) for o in r["objects"]]
        else:
            objs.append(norm_override(r))
    return objs


S1_CAP_MIN = 375.0        # R78 s78.4(2): S1-b = 75-bar cap (minutes)
S1_STATS_KEYS = ("id", "panel", "tau", "j0", "j1", "a_j0", "b_j0")


def is_s1_stats(path):
    """DR_RULES_S1_objects.jsonl is a STATISTICS file (one row per
    live box holding both arms' indices), not a drawable override.
    Detect that spelling so --override adapts it."""
    try:
        with open(path, encoding="utf8") as fh:
            r = json.loads(fh.readline())
    except Exception:
        return False
    return all(k in r for k in S1_STATS_KEYS)


def objects_from_s1(path, panel_id, tau, arm_letter, e, m, i_tau):
    """Adapt the S1 stats rows into the c3 live set (R78 s78.4(2)).

    S1 touches BOX-family objects only.  For every live box-family
    object the transformed left edge is computed locally with the
    measure's formula; where a stats row exists for (panel,tau,id)
    the file's value must agree (mismatch -> ESCALATE, file wins).
    Live box-family objects WITHOUT a row (not in the measure's
    ranked set — e.g. ended before the window) get the same
    transform applied anyway; they are outside the view so the
    rendered ink is unchanged either way.  Non-box objects are
    returned untouched — write_diff asserts they are identical to
    the c3 set per panel.  Returns (objs, info)."""
    rows = {}
    for line in open(path, encoding="utf8"):
        r = json.loads(line)
        if r.get("panel") == panel_id and int(r.get("tau", -1)) == \
                int(tau):
            rows[r["id"]] = r
    objs = [norm_engine(o) for o in e.objects if o.state != "DELETED"]
    out, dropped, x_row, x_norow, mismatched = [], 0, 0, 0, []
    cap = int(np.searchsorted(m, tau - S1_CAP_MIN))       # M.jge
    for od in objs:
        fam = EV.FAMILY.get(od["type"])
        if fam != "box" or "top" not in od["geom"]:
            out.append(od)
            continue
        t1_src = od["geom"].get("t1_drawn") or \
            (od["t_right"] if od["t_right"] is not None else i_tau)
        j1 = min(int(t1_src), i_tau)
        j0 = min(int(od["t_left"]), j1)
        row = rows.get(od["id"])
        if arm_letter == "a":
            if row is not None and row.get("a_dropped"):
                dropped += 1
                continue
            new_j0 = int(row["a_j0"]) if row is not None else j0
        else:                                   # arm b: never drops
            new_j0 = max(j0, min(cap, j1))
            if row is not None and int(row["b_j0"]) != new_j0:
                mismatched.append(od["id"])
                new_j0 = int(row["b_j0"])
        if new_j0 != j0:
            if row is not None:
                x_row += 1
            else:
                x_norow += 1
            od = dict(od, t_left=new_j0)
        out.append(od)
    info = {"rows": len(rows), "xformed": x_row, "x_norow": x_norow,
            "dropped": dropped,
            "no_row_boxes": sorted(
                od["id"] for od in out
                if EV.FAMILY.get(od["type"]) == "box"
                and od["id"] not in rows),
            "mismatched": sorted(mismatched)}
    for bad in mismatched:
        log_line("ESCALATE s1 %s %s: file b_j0 != computed for %s"
                 % (panel_id, tau, bad))
    return out, info


# ------------------------------------------------------------------ #
# render one panel
# ------------------------------------------------------------------ #

def clip_now(dr, vm, tau_x, fill=255):
    """Hard edge at 'now': white out every plot column right of the
    dashed line (the tau bar straddles it by ~bw/2 — clipped too, so
    literally no candle ink exists right of now).  The frame borders
    (x1, y1) are kept."""
    dr.rectangle([int(tau_x) + 2, vm.y0 + 1, vm.x1 - 1, vm.y1 - 1],
                 fill=fill)


def render_panel(panel, rec, objs, abr_tau, i_tau, outdir,
                 source_desc, tt_on=False, drop_tagged=False,
                 hide_tags=None, hidden_out=None,
                 fade_broken=False, faded_out=None):
    """Base sheet via ceiling_render (bars<=tau + dashed now line +
    axis json), then objects + label on top."""
    os.makedirs(outdir, exist_ok=True)
    tau = int(panel["tau"])
    png = os.path.join(outdir, "%s.png" % panel["name"])
    js = os.path.join(outdir, "%s.json" % panel["name"])
    axis = CR.render_sheet(rec, tau, png, js)
    if axis is None:
        log_line("ESCALATE render_sheet empty: %s" % panel["name"])
        return None
    ax = json.load(open(js, encoding="utf8"))
    tm, pm, pr = ax["time_map"], ax["price_map"], ax["plot_rect_px"]
    vm = R.VMap(tm["t_lo"], tm["t_hi"], pm["p_lo"], pm["p_hi"])
    tau_x = ax["tau_x"]
    _t, m, _o, h, l, _c = CA.bars(panel["date"])

    im = Image.open(png).convert("L")
    dr = ImageDraw.Draw(im)
    drawn = draw_objects(dr, vm, objs, m, h, l, abr_tau, i_tau, tau_x,
                         tt_on=tt_on, drop_tagged=drop_tagged,
                         hide_tags=hide_tags, hidden_out=hidden_out,
                         fade_broken=fade_broken, faded_out=faded_out)
    clip_now(dr, vm, tau_x)
    # "now" line on top of the objects (same style as the sheet's)
    R._dash_v(dr, tau_x, vm.y0, vm.y1, 0, 6, 4)
    dr.text((6, 4), str(panel["name"]), fill=0)      # corner label
    im.save(png)

    doc = {"panel": panel["name"], "date": panel["date"], "tau": tau,
           "arm_source": source_desc, "axis": ax, "objects": drawn}
    with open(js, "w", encoding="utf8") as fh:
        json.dump(doc, fh, indent=1)
    return {"png": png, "json": js, "n_obj": len(drawn),
            "tau_x": tau_x, "vm": vm}


def run_arm(arm, flags, override, panels_path, outdir,
            drop_tagged=False, hide_tags=None, fade_broken=False):
    panels = load_panels(panels_path)
    recs = {r["id"]: r for r in C.load_tune()}
    os.makedirs(outdir, exist_ok=True)
    tt_on = bool(flags and "trade_tags" in flags
                 and json.loads(flags.split("trade_tags=")[1]
                                .split(",")[0] or "0"))
    s1_mode = bool(override and is_s1_stats(override))
    s1_arm = "a" if arm.rstrip("abc").endswith("s1a") or \
        arm.endswith("s1a") else "b"
    results, s1_infos, hidden, faded = [], {}, {}, {}
    for p in panels:
        rec = recs[p["panel"]]
        if s1_mode:
            epar = engine_at_tau_cached(p["date"], p["tau"])
            if epar is None:
                log_line("ESCALATE s1 base c3 cache %s %s"
                         % (p["date"], p["tau"]))
                continue
            _t, m, _o, _h, _l, _c = CA.bars(p["date"])
            i_tau = len(epar.bars) - 1
            objs, s1_infos[p["name"]] = objects_from_s1(
                override, p["panel"], p["tau"], s1_arm, epar, m,
                i_tau)
            abr_tau = float(np.asarray(epar.abr)[-1]) if len(
                epar.abr) else 5.0
            src = "s1%s:%s (c3 + %s_transform)"
            src = src % (s1_arm, os.path.basename(override), s1_arm)
        elif override:
            objs = objects_from_override(override, p["panel"], p["tau"])
            _t, m, _o, _h, _l, _c = CA.bars(p["date"])
            i_tau = int(np.searchsorted(m, p["tau"], "right")) - 1
            epar = engine_at_tau_cached(p["date"], p["tau"])
            abr_tau = float(np.asarray(epar.abr)[-1]) if epar is not \
                None else float(CA.abr(p["date"])[min(i_tau,
                                                     len(m) - 1)])
            src = "override:%s" % os.path.basename(override)
        elif flags:
            e = engine_at_tau_flags(rec, p["tau"], flags)
            objs = objects_from_engine(e)
            i_tau = len(e.bars) - 1
            abr_tau = float(np.asarray(e.abr)[-1]) if len(e.abr) \
                else 5.0
            src = "flags:%s" % flags
        else:
            e = engine_at_tau_cached(p["date"], p["tau"])
            if e is None:
                log_line("ESCALATE missing c3 cache %s %s"
                         % (p["date"], p["tau"]))
                continue
            objs = objects_from_engine(e)
            i_tau = len(e.bars) - 1
            abr_tau = float(np.asarray(e.abr)[-1]) if len(e.abr) \
                else 5.0
            src = "c3:%s@%s (STABLE %s)" % (ARM_V, ARM_H, STABLE)
        hid, fad = [], []
        r = render_panel(p, rec, objs, abr_tau, i_tau, outdir, src,
                         tt_on=tt_on, drop_tagged=drop_tagged,
                         hide_tags=hide_tags, hidden_out=hid,
                         fade_broken=fade_broken, faded_out=fad)
        if r:
            results.append((p, r))
            hidden[p["name"]] = hid
            faded[p["name"]] = fad
            print("  %-8s tau=%-4d objects=%d -> %s"
                  % (p["name"], p["tau"], r["n_obj"], r["png"]))
    return results, s1_infos, hidden, faded


# ------------------------------------------------------------------ #
# per-panel diff vs sets/c3 (R81 s81.5(3))
# ------------------------------------------------------------------ #

GEOM_FIELDS = ("type", "state", "t0_min", "t1_min", "lo_raw",
               "hi_raw", "p0_raw", "p1_raw", "slope_pip_per_bar",
               "price_raw", "letter")


def _panel_delta(name, adir, bdir):
    """(added, removed, changed) of adir's <name>.json vs bdir's."""
    a = json.load(open(os.path.join(adir, "%s.json" % name),
                       encoding="utf8"))
    b = json.load(open(os.path.join(bdir, "%s.json" % name),
                       encoding="utf8"))
    ao = {o["id"]: o for o in a["objects"]}
    bo = {o["id"]: o for o in b["objects"]}
    added = [ao[i] for i in sorted(set(ao) - set(bo))]
    removed = [bo[i] for i in sorted(set(bo) - set(ao))]
    changed = []
    for i in sorted(set(ao) & set(bo)):
        diffs = {f: (bo[i].get(f), ao[i].get(f))
                 for f in GEOM_FIELDS
                 if bo[i].get(f) != ao[i].get(f)}
        if diffs:
            changed.append((i, ao[i]["type"], diffs))
    return a, b, ao, bo, added, removed, changed


def write_diff(arm, outdir, panels, s1_infos=None, hidden=None,
               faded=None, vs2=None):
    """<arm>/_diff.md — objects added/removed/changed vs sets/c3,
    from the per-panel jsons (never pixels).  For the s1b arm also
    asserts the non-box objects are exactly the c3 set per panel.
    hidden: {panel_name: [tag-hidden records]} annotates removals
    with the tags that hid them.  vs2: a second set dir name for a
    follow-on delta table (R81: tt_view_v2 vs tt_view_v1 = what the
    three TT-2 tags removed)."""
    c3dir = os.path.join(SETS, "c3")
    lines = ["# %s vs c3 — per-panel object diff" % arm, ""]
    if arm == "s1b":
        lines.append("S1-b touches BOX-family only; non-box objects "
                     "must equal the c3 set — asserted per panel "
                     "below (PASS/FAIL).")
        lines.append("")
    for p in panels:
        name = p["name"]
        a, b, ao, bo, added, removed, changed = _panel_delta(
            name, outdir, c3dir)
        hid = {h["id"]: h for h in (hidden or {}).get(name, [])}
        lines.append("## %s (tau=%d)" % (name, p["tau"]))
        lines.append("- added (%d): %s" % (len(added), ", ".join(
            "%s(%s)" % (o["id"], o["type"]) for o in added) or "—"))
        lines.append("- removed (%d): %s" % (len(removed),
            ", ".join("%s(%s%s)" % (
                o["id"], o["type"],
                " hide=" + "+".join(hid[o["id"]]["hide_tags"])
                + " [tags: " + "+".join(hid[o["id"]]["tags"]) + "]"
                if o["id"] in hid else "")
                for o in removed) or "—"))
        lines.append("- changed (%d):" % len(changed))
        for i, typ, diffs in changed:
            pretty = "; ".join("%s %s->%s" % (f, a_, b_)
                               for f, (a_, b_) in diffs.items())
            lines.append("  - %s(%s): %s" % (i, typ, pretty))
        if faded is not None:
            fad = {f_["id"]: f_ for f_ in faded.get(name, [])}
            fs = [o for o in a["objects"] if o.get("faded")]
            lines.append("- faded (%d): %s" % (len(fs), ", ".join(
                "%s(%s exit_bar=%smin clause=%s)" % (
                    o["id"], o["type"], o.get("exit_bar_min"),
                    (fad.get(o["id"]) or {}).get("break_clause"))
                for o in fs) or "—"))
        if s1_infos is not None and name in s1_infos:
            inf = s1_infos[name]
            lines.append("- s1 stats: rows=%d transformed=%d "
                         "(+%d unlisted) dropped=%d; boxes without "
                         "row: %s"
                         % (inf["rows"], inf["xformed"],
                            inf["x_norow"], inf["dropped"],
                            ", ".join(inf["no_row_boxes"]) or "—"))
            strip = lambda o: {k: v for k, v in o.items()
                               if k != "tags"}
            nb_a = {o["id"]: strip(o) for o in a["objects"]
                    if EV.FAMILY.get(o["type"]) != "box"}
            nb_b = {o["id"]: strip(o) for o in b["objects"]
                    if EV.FAMILY.get(o["type"]) != "box"}
            same = nb_a == nb_b
            lines.append("- non-box == c3: %s"
                         % ("PASS" if same else "FAIL"))
            if not same:
                log_line("ESCALATE s1b non-box mismatch %s" % name)
        lines.append("")
    if vs2:
        vs2dir = os.path.join(SETS, vs2)
        lines.append("# %s vs %s — per-panel delta" % (arm, vs2))
        lines.append("")
        for p in panels:
            name = p["name"]
            a2, b2, ao2, bo2, added2, removed2, changed2 = \
                _panel_delta(name, outdir, vs2dir)
            hid = {h["id"]: h for h in (hidden or {}).get(name, [])}
            lines.append("## %s (tau=%d)" % (name, p["tau"]))
            lines.append("- added vs %s (%d): %s" % (
                vs2, len(added2), ", ".join(
                    "%s(%s)" % (o["id"], o["type"])
                    for o in added2) or "—"))
            lines.append("- removed vs %s (%d): %s" % (
                vs2, len(removed2), ", ".join(
                    "%s(%s%s)" % (
                        o["id"], o["type"],
                        " hide=" + "+".join(hid[o["id"]]["hide_tags"])
                        if o["id"] in hid else "")
                    for o in removed2) or "—"))
            lines.append("- changed vs %s (%d): %s" % (
                vs2, len(changed2), "; ".join(
                    "%s(%s)" % (i, t) for i, t, _d in changed2)
                    or "—"))
            if faded is not None:
                fad = {f_["id"]: f_ for f_ in faded.get(name, [])}
                fs = [o for o in a2["objects"] if o.get("faded")]
                lines.append("- faded (%d): %s" % (len(fs), ", ".join(
                    "%s(%s exit_bar=%smin clause=%s)" % (
                        o["id"], o["type"], o.get("exit_bar_min"),
                        (fad.get(o["id"]) or {}).get("break_clause"))
                    for o in fs) or "—"))
            lines.append("")
    out = os.path.join(outdir, "_diff.md")
    with open(out, "w", encoding="utf8") as fh:
        fh.write("\n".join(lines))
    print("wrote %s" % out)


# ------------------------------------------------------------------ #
# calibration set (p099-p102, once — R80 §80.6)
# ------------------------------------------------------------------ #

def run_calib(outdir):
    os.makedirs(outdir, exist_ok=True)
    rows = {}
    for line in open(GEOM_JSONL, encoding="utf8"):
        r = json.loads(line)
        if r["seq"] in ("p099", "p100", "p101", "p102"):
            rows[r["seq"]] = r
    recs = {r["id"]: r for r in C.load_tune()}
    order = sorted(rows)
    rng = random.Random(SEED)
    rng.shuffle(order)
    mapping = {}
    for n, seq in enumerate(order, 1):
        row = rows[seq]
        name = "calib_%d" % n
        rec = recs[row["panel"]]
        tau = int(row["tau"])
        png = os.path.join(outdir, "%s.png" % name)
        js = os.path.join(outdir, "%s.json" % name)
        axis = CR.render_sheet(rec, tau, png, js)
        if axis is None:
            log_line("ESCALATE calib sheet empty: %s" % seq)
            continue
        ax = json.load(open(js, encoding="utf8"))
        tm, pm = ax["time_map"], ax["price_map"]
        vm = R.VMap(tm["t_lo"], tm["t_hi"], pm["p_lo"], pm["p_hi"])
        tau_x = ax["tau_x"]
        _t, m, _o, _h, _l, _c = CA.bars(row["date"] if
                                      "date" in row else rec["date"])
        im = Image.open(png).convert("RGB")
        dr = ImageDraw.Draw(im)
        drew = draw_item(dr, vm, row, tau_x, m)
        clip_now(dr, vm, tau_x, fill=(255, 255, 255))
        # grey "now" line on top (same as the sheet's divider look)
        for y in range(int(vm.y0), int(vm.y1), 8):
            dr.line([(tau_x, y), (tau_x, min(y + 4, vm.y1))],
                    fill=TAU_GREY)
        dr.text((6, 4), name, fill=(0, 0, 0))
        im.save(png)
        item = {k: row.get(k) for k in
                ("seq", "kind", "t0", "t1", "lo", "hi", "price",
                 "p0", "p1", "slope") if row.get(k) is not None}
        with open(js, "w", encoding="utf8") as fh:
            json.dump({"calib": name, "seq": seq,
                       "panel": row["panel"], "tau": tau,
                       "axis": ax, "object": item, "drew": bool(drew)},
                      fh, indent=1)
        mapping[name] = {"seq": seq, "panel": row["panel"],
                         "tau": tau, "kind": row["kind"]}
        print("  %s <- %s (%s %s tau=%d) drew=%s"
              % (name, seq, row["panel"], row["kind"], tau, drew))
    with open(os.path.join(outdir, "_map.json"), "w",
              encoding="utf8") as fh:
        json.dump({"seed": SEED,
                   "note": "p099-p102 re-rendered blind for G-REVIEW "
                           "calibration (R80 s80.6); truth stays in "
                           "the sealed key, never here.",
                   "mapping": mapping}, fh, indent=1)
    print("wrote %s" % os.path.join(outdir, "_map.json"))


# ------------------------------------------------------------------ #
# contact sheet + self-test
# ------------------------------------------------------------------ #

def contact_sheet(setdir, cols=4, tw=560):
    pngs = sorted(f for f in os.listdir(setdir)
                  if f.endswith(".png") and not f.startswith("_"))
    if not pngs:
        print("no pngs in", setdir)
        return
    ims = [Image.open(os.path.join(setdir, f)) for f in pngs]
    th = int(ims[0].height * tw / ims[0].width)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("L", (cols * tw, rows * th), 255)
    for i, im in enumerate(ims):
        t = im.convert("L").resize((tw, th), Image.LANCZOS)
        sheet.paste(t, ((i % cols) * tw, (i // cols) * th))
    out = os.path.join(setdir, "_sheet.png")
    sheet.save(out)
    print("wrote %s (%dx%d, %d panels)" % (out, sheet.width,
                                           sheet.height, len(ims)))


def selftest(panels_path):
    """(1) render one panel twice -> identical bytes; (2) no dark
    pixel column right of the now line inside the plot."""
    panels = load_panels(panels_path)
    p = panels[0]
    rec = {r["id"]: r for r in C.load_tune()}[p["panel"]]
    e = engine_at_tau_cached(p["date"], p["tau"])
    assert e is not None, "no c3 cache for selftest panel"
    objs = objects_from_engine(e)
    i_tau = len(e.bars) - 1
    abr_tau = float(np.asarray(e.abr)[-1])
    import io
    outs = []
    for _ in range(2):
        tmp = os.path.join(HERE, "_scratch_st")
        os.makedirs(tmp, exist_ok=True)
        png = os.path.join(tmp, "st.png")
        js = os.path.join(tmp, "st.json")
        ax = CR.render_sheet(rec, p["tau"], png, js)
        a = json.load(open(js))
        vm = R.VMap(a["time_map"]["t_lo"], a["time_map"]["t_hi"],
                    a["price_map"]["p_lo"], a["price_map"]["p_hi"])
        _t, m, _o, h, l, _c = CA.bars(p["date"])
        im = Image.open(png).convert("L")
        dr = ImageDraw.Draw(im)
        draw_objects(dr, vm, objs, m, h, l, abr_tau, i_tau,
                     ax["tau_x"])
        clip_now(dr, vm, ax["tau_x"])
        R._dash_v(dr, ax["tau_x"], vm.y0, vm.y1, 0, 6, 4)
        dr.text((6, 4), str(p["name"]), fill=0)
        buf = io.BytesIO()
        im.save(buf, "PNG")
        outs.append((buf.getvalue(), ax, vm))
    b0, ax, vm = outs[0]
    ok_bytes = outs[0][0] == outs[1][0]
    print("selftest bytes-identical:", "PASS" if ok_bytes else "FAIL")
    im = Image.open(io.BytesIO(b0)).convert("L")
    px = np.asarray(im)
    x_from = int(ax["tau_x"]) + 2
    region = px[int(vm.y0) + 1:int(vm.y1),
                x_from:int(vm.x1)]
    n_dark = int((region < 150).sum())
    print("selftest no-ink-right-of-now:", "PASS" if n_dark == 0
          else "FAIL (%d dark px)" % n_dark)
    return ok_bytes and n_dark == 0


# ------------------------------------------------------------------ #

def main():
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", default="c3")
    ap.add_argument("--flags", default=None,
                    help="k=v,k2=v2 engine params (live run; HEAVY — "
                         "wrap in tools/heavy_run.py --lane gkit and "
                         "export GKIT_UNDER_HEAVY=1)")
    ap.add_argument("--override", default=None,
                    help="jsonl of objects per panel/tau (offline arms)")
    ap.add_argument("--panels", default=PANELS_JSON)
    ap.add_argument("--out", default=None)
    ap.add_argument("--make-panels", action="store_true")
    ap.add_argument("--drop-tagged", action="store_true",
                    help="trade view: objects carrying a "
                         "TRADE_VIEW_HIDE tag are not drawn "
                         "(lone_edge stays — R81 s81.5(1))")
    ap.add_argument("--hide", default=None,
                    help="csv of tags that hide (R81 s81.5(1) "
                         "explicit hide set, e.g. the TT-v1 subset)")
    ap.add_argument("--diff-vs", default=None,
                    help="second set name for an extra delta table "
                         "in _diff.md (e.g. tt_view_v1)")
    ap.add_argument("--fade-broken", action="store_true",
                    help="R83 s83.6: box_broken box-family objects "
                         "are drawn truncated at exit_bar, light "
                         "grey dashed thin, instead of hidden")
    ap.add_argument("--calib", action="store_true")
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.make_panels:
        make_panels()
        return
    if args.calib:
        run_calib(os.path.join(SETS, "calib"))
        return
    if args.selftest:
        ok = selftest(args.panels)
        sys.exit(0 if ok else 1)
    outdir = args.out or os.path.join(SETS, args.arm)
    hide_tags = args.hide.split(",") if args.hide else None
    res, s1_infos, hidden, faded = run_arm(
        args.arm, args.flags, args.override, args.panels, outdir,
        drop_tagged=args.drop_tagged, hide_tags=hide_tags,
        fade_broken=args.fade_broken)
    print("rendered %d panels -> %s" % (len(res), outdir))
    if args.arm != "c3" and res:
        write_diff(args.arm, outdir, [p for p, _r in res],
                   s1_infos=s1_infos or None, hidden=hidden,
                   faded=faded or None, vs2=args.diff_vs)
    if args.sheet or args.arm == "c3":
        contact_sheet(outdir)


if __name__ == "__main__":
    main()
