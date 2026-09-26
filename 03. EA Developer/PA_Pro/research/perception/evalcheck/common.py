"""evalcheck/common.py — shared harness for the ruler-audit lane (E1-E4).

EVAL-AUDIT lane (Ruling 8 / MANDATE_EVAL_AUDIT).  Read-only use of
eval.py, the engines, the golden yardstick and book_loader.  Nothing in
this package edits any file outside evalcheck/.

Conventions (identical to eval.py):
  * golden objects: dicts from BOOK2012_TUNE_v2.jsonl; t0/t1 are CET
    minutes-of-day, prices absolute.
  * engine records: the minute-space dicts eval.eng_objects produces
    {type,t0,t1,t_birth,lo,hi,price,p0,slope,t0_bar,side,letter,dirn}.
  * PIP distances are in pips (price * 1e4).
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)                       # research/perception
PROOT = os.path.dirname(os.path.dirname(PERC))     # PA_Pro
for _p in (PERC, os.path.join(PERC, "golden"),
           os.path.join(PROOT, "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import eval as EV                                 # noqa: E402  the ruler under audit

PIP = EV.PIP                                     # 1e-4
TUNE = EV.TUNE

USABLE = EV.USABLE
EXCLUDED = EV.EXCLUDED
TIME_ONLY = EV.TIME_ONLY
ANNOT = EV.ANNOT

# repair methods whose geometry was re-anchored on real M5 bars
# (GOLDEN_AUDIT repair-provenance table).  Bar-anchored coordinates carry
# a tighter label noise than the author's catalogue eyeball.
REFINED_METHODS = {
    "constrained_fit", "text_anchor_bars",
    "edge_from_bars", "edge_from_bars+subwindow",
    "sibling_span",
}

# Label-precision model (mandate E2): catalogue eyeball +/-5 p / +/-10 min;
# [meas] prices +/-2 p; bar-anchored repairs +/-1.5 p (TOUCH_TOL scale).
# R11 §11.3: repaired LINES carry mid-span fit noise ~2 p (LINE-LAB L1
# trusted hug4 p95 = 2.0 p) -> line types get 2.0 p; edge/level prices
# stay at 1.5 p.  Time is always a catalogue read -> +/-10 min.
PRICE_SIGMA = {"meas": 2.0, "eye": 5.0}
REFINED_PRICE_SIGMA = 1.5
REFINED_LINE_SIGMA = 2.0
LINE_SPEC_TYPES = ("PATTERN_LINE", "CONTEXT_LINE")
TIME_SIGMA_MIN = 10.0


def load_tune():
    return [json.loads(x) for x in open(TUNE, encoding="utf8")]


def prec_sigmas(o):
    """(price_sigma_pips, time_sigma_min) for one golden object."""
    if o.get("prec") == "meas":
        return 2.0, TIME_SIGMA_MIN
    if o.get("repair_method") in REFINED_METHODS:
        if o.get("spec_type") in LINE_SPEC_TYPES:
            return REFINED_LINE_SIGMA, TIME_SIGMA_MIN
        return REFINED_PRICE_SIGMA, TIME_SIGMA_MIN
    return 5.0, TIME_SIGMA_MIN


def is_time_only(o):
    return o.get("status") in TIME_ONLY or o.get("prec") == "time_only"


# ------------------------------------------------------------------ #
# golden object -> synthetic engine record (minute space)
# ------------------------------------------------------------------ #

def _bar_of(m, t_min):
    """First bar index with cet_min >= t_min (eval._line_price_at uses
    the same searchsorted convention)."""
    j = int(np.searchsorted(m, t_min))
    return min(j, len(m) - 1)


def gold_as_engine(g, m):
    """Convert one usable golden object into the record format that
    eval.eng_objects emits, so it can be fed to eval.match verbatim.

    Line records carry p0/slope in BAR-INDEX space exactly like the real
    engine output (t0_bar = first bar >= golden t0).
    """
    gt = g["spec_type"]
    t0, t1 = g.get("t0"), g.get("t1")
    rec = {"type": gt, "why": "golden_self", "t0": t0, "t1": t1,
           "t0_raw": t0, "t1_raw": t1,
           "t_birth": t0, "id": "g", "events": []}
    if gt in ("BOX", "RANGE_OPEN", "CONTEXT_RANGE"):
        if g.get("price_lo") is not None:
            rec["lo"], rec["hi"] = g["price_lo"] / PIP, g["price_hi"] / PIP
        # containment window in minutes (the engine-side counterpart of
        # meta_build_*/break_bar in the real conversion)
        if g.get("build_start") is not None:
            rec["bs"] = g["build_start"]
        if g.get("build_end") is not None:
            rec["be"] = g["build_end"]
    elif gt in ("PATTERN_LINE", "CONTEXT_LINE"):
        p0, p1 = g.get("price0"), g.get("price1")
        if p0 is not None and p1 is not None and t0 is not None \
                and t1 is not None and t1 > t0:
            j0, j1 = _bar_of(m, t0), _bar_of(m, t1)
            dj = max(j1 - j0, 1)
            rec["p0"] = p0 / PIP
            rec["slope"] = (p1 - p0) / PIP / dj      # pips per bar
            rec["t0_bar"] = j0
            rec["dirn"] = 1 if rec["slope"] > 0.05 else \
                (-1 if rec["slope"] < -0.05 else 0)
        elif p0 is not None and p1 is not None:
            rec["p0"], rec["slope"], rec["t0_bar"] = \
                p0 / PIP, 0.0, _bar_of(m, t0 or 0)
            rec["dirn"] = 0
    elif gt in ("LEVEL_CARRIED", "MINI_LEVEL"):
        if g.get("price") is not None:
            rec["price"] = g["price"] / PIP
            rec["side"] = g.get("dir")
    elif gt == "BRACKET":
        rec["letter"] = g.get("letter")
        if g.get("price") is not None:
            rec["price"] = g["price"] / PIP
    return rec


def mark_as_engine(gm, w0=0):
    """Golden LABEL_TF mark -> engine LABEL_TF record.  t_birth is a CET
    minute in both worlds (eval.eng_objects maps bar->cet_min).  A mark
    with t=None is parent-attached; a real engine always stamps a birth
    bar, so the copy carries the panel's left edge (a real time)."""
    t = gm.get("t")
    return {"type": "LABEL_TF", "why": "golden_self", "t0": t, "t1": t,
            "t_birth": t if t is not None else w0, "id": "gm",
            "events": [], "price": None, "side": gm.get("side"),
            "letter": gm.get("letter")}


# ------------------------------------------------------------------ #
# matching driver — mirrors eval.eval_panel's assignment stage exactly,
# parameterised on the match functions so eval_v2 can reuse it.
# ------------------------------------------------------------------ #

def match_panel(gobjs, eobjs, gmarks, emarks, m,
                matchfn=EV.match, markfn=EV.match_mark,
                scorefn=None):
    """Greedy assignment identical to eval.py: candidate pairs sorted by
    descending score (span IoU by default), 1:1."""
    if scorefn is None:
        scorefn = lambda g, e: EV.iou(g["t0"], g["t1"], e["t0"], e["t1"])
    cand = []
    for gi, g in enumerate(gobjs):
        for ei, eo in enumerate(eobjs):
            if matchfn(g, eo, m):
                cand.append((-scorefn(g, eo), gi, ei))
    cand.sort()
    used_g, used_e, pairs = set(), set(), []
    for _s, gi, ei in cand:
        if gi in used_g or ei in used_e:
            continue
        used_g.add(gi)
        used_e.add(ei)
        pairs.append((gi, ei))

    mpairs, used_em = [], set()
    for gm in gmarks:
        best, bs = None, 1e9
        for ei, em in enumerate(emarks):
            if ei in used_em or not markfn(gm, em):
                continue
            d = abs(em["t_birth"] - gm["t"]) if gm.get("t") is not None \
                else 0
            if d < bs:
                best, bs = ei, d
        if best is not None:
            used_em.add(best)
            mpairs.append((gm, emarks[best]))
    return pairs, mpairs


def tally(gobjs, eobjs, gmarks, pairs, mpairs):
    """Per-type counts identical to eval.aggregate's bookkeeping."""
    from collections import defaultdict
    pt = defaultdict(lambda: {"g": 0, "e": 0, "m": 0})
    mg = {gi for gi, _ in pairs}
    for gi, g in enumerate(gobjs):
        t = g["spec_type"]
        pt[t]["g"] += 1
        if gi in mg:
            pt[t]["m"] += 1
    for eo in eobjs:
        if eo["type"] in ANNOT:
            continue
        pt[eo["type"]]["e"] += 1
    pt["LABEL_TF"]["g"] += len(gmarks)
    pt["LABEL_TF"]["e"] += sum(1 for e in eobjs if e["type"] == "LABEL_TF")
    pt["LABEL_TF"]["m"] += len(mpairs)
    return pt
