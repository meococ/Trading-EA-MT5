"""eval_v2.py — D9-consistent ruler (EVAL-AUDIT lane, mandate E3).

Same §6.1 metric shape as eval.py (per-type recall/precision on matched
pairs, clutter, LABEL_TF agreement), with the matching semantics fixed
per the golden audit and Lead notes R9/R9a:

  D9  — a box's drawn span runs past the break; the containment window
        is [build_start, build_end].  Lines likewise: the fitted segment
        is the pre-break anchor span; drawn extension is ink, not
        geometry.

  R9.1 — eval.py's eng_objects sent ACTIVE objects to the last bar of
        the DAY (len(m)-1) although the engine was only fed to w1; and
        never clipped t0 to w0.  The frozen conversion below uses the
        last FED bar and clips both sides to the panel window [w0, w1]
        (engine side AND golden side — golden keeps true starts, 33
        objects have t0 < w0).

  R9.2 — eval.py's iou() is overlap / max(len), not intersection /
        union.  True IoU is used here.

  R11  — BOX match = true IoU of the containment windows >= 0.5 plus
        both edges within tol; the drawn-span coverage fallback survives
        only when a side recorded NO containment window at all, and its
        use is counted.  Diagnostic "located" (overlap coeff >= 0.5 +
        edges) is reported beside recall, never a match.  Repaired-line
        price sigma = 2.0 p (LINE-LAB L1 mid-span hug p95), edges keep
        1.5 p.

  Precision-flag tolerances — every tolerance is tied to the object's
  own precision flag (common.prec_sigmas): eye +/-5p / +/-10min,
  meas +/-2p, bar-anchored repairs +/-1.5p (lines +/-2.0p).  E2 showed
  the spec's flat 2p level tol and +-5min mark tol are tighter than the
  labels support.

Per-type rules:

  BOX / RANGE_OPEN / CONTEXT_RANGE
      Match (R11): true IoU(engine containment window, golden
      containment window) >= 0.5 AND both edges within tol.  Engine
      window = meta_build_start..meta_build_end (bar idx -> minutes)
      when present, else t0 .. (break_bar or t1).  Golden window =
      build_start (fallback t0) .. build_end (fallback t1); a degenerate
      or absent window resolves to the drawn span.  Fallback (counted):
      coverage(engine drawn span clipped to panel, golden window)
      >= 0.5 — only when a side recorded no containment window at all.
      time_only / missing edges -> span criterion only.
      Diagnostic: box_located() — overlap coeff >= 0.5 + edges ok.

  PATTERN_LINE / CONTEXT_LINE
      Shared span W = clipped engine span ∩ clipped golden span must
      cover >= 25% of the golden span (>= 10 min; <= half of very short
      spans).  Both endpoints of W must agree within
      tol_l = sigma_p + |slope_g| * 10min — the anchor-time noise
      projected through the line's own slope (a +-10min read on a steep
      line is a real price displacement).  Extension excluded: nothing
      outside W is scored.  No golden endpoints -> coverage + dir.

  LEVEL_CARRIED / MINI_LEVEL
      |price diff| <= sigma_p AND clipped spans share >= 1 minute.

  LABEL_TF (marks)
      |t diff| <= 10 min (catalogue time precision) AND same side.
      t=None -> side only.

  BRACKET
      coverage(engine span, golden formation span) >= 0.3 AND same
      letter family (m/w/i stripped, as eval.py).

  SQUEEZE     coverage >= 0.3 of golden span.
  BAR_MARKER  engine stamp within +/-10 min of the golden mark window
              (a point event; span-IoU can never score it).

  Boundary: golden objects/marks lying entirely outside the panel
  window are unscorable — a causal engine fed to w1 can never produce
  them.  scorable()/scorable_mark() exclude them (counted separately).

score() is the greedy-assignment key: coverage of the golden window —
same role as eval.py's span IoU.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C                              # noqa: E402
import eval as EV                               # noqa: E402

PIP = EV.PIP

BOX_TYPES = ("BOX", "RANGE_OPEN", "CONTEXT_RANGE")
LINE_TYPES = ("PATTERN_LINE", "CONTEXT_LINE")
LEVEL_TYPES = ("LEVEL_CARRIED", "MINI_LEVEL")


# ------------------------------------------------------------------ #
# frozen engine->record conversion (R9/R9a: self-contained, clipped)
# ------------------------------------------------------------------ #

def _min(m, i):
    i = int(min(max(i, 0), len(m) - 1))
    return int(m[i])


def eng_objects(e, m, w0, w1):
    """Engine objects -> minute/pip records, clipped to [w0, w1].

    Identical field extraction to eval.eng_objects, plus:
      * ACTIVE object's t1 = last FED bar (len(e.bars)-1), then clipped
        to w1 — the pre-16:28Z eval.py used len(m)-1 = day end;
      * t0 clipped to w0 (left asymmetry, R9);
      * containment window carried through: meta_build_start /
        meta_build_end (v1 boxes) and break_bar -> minutes.
    """
    nfed = len(e.bars) - 1
    out = []
    for o in e.objects:
        t0m = _min(m, o.t_left)
        t1_src = o.geometry.get("t1_drawn") or \
            (o.t_right if o.t_right is not None else nfed)
        t1m = _min(m, t1_src)
        if t1m < w0 or t0m > w1:
            continue
        g = o.geometry
        rec = {"type": o.type, "why": o.why,
               "t0": max(t0m, w0), "t1": min(t1m, w1),
               "t0_raw": t0m, "t1_raw": t1m,
               "t_birth": _min(m, o.t_birth), "id": o.id,
               "events": o.events, "w0": w0, "w1": w1}
        if "top" in g:
            rec["lo"], rec["hi"] = g["bottom"], g["top"]
        if "price" in g:
            rec["price"], rec["side"] = g["price"], g.get("side")
        if "p0" in g:
            rec["p0"] = g["p0"]
            rec["slope"] = g["slope"]
            rec["t0_bar"] = g["t0"]
            rec["side"] = g.get("side")
            rec["dirn"] = 1 if g["slope"] > 0.05 else \
                (-1 if g["slope"] < -0.05 else 0)
        if "letter" in g:
            rec["letter"] = g["letter"]
        if o.type == "LABEL_TF":
            rec["price"] = g.get("price")
            rec["side"] = g.get("side")
            rec["letter"] = g.get("letter")
        # containment window (bar indices -> minutes), when recorded
        bs = g.get("meta_build_start", g.get("build_start"))
        be = g.get("meta_build_end", g.get("build_end"))
        if bs is not None:
            rec["bs"] = _min(m, bs)
        if be is not None:
            rec["be"] = _min(m, be)
        if g.get("break_bar") is not None:
            rec["break_bar_min"] = _min(m, g["break_bar"])
        out.append(rec)
    return out


def eng_objects_pre_r91(e, m, w0, w1):
    """The pre-16:28Z conversion: ACTIVE objects stretch to len(m)-1
    (last bar of the DAY), no clipping.  Kept for the E4 before/after
    column — replicates the old eval.py exactly."""
    out = []
    for o in e.objects:
        t0m = _min(m, o.t_left)
        t1_src = o.geometry.get("t1_drawn") or \
            (o.t_right if o.t_right is not None else len(m) - 1)
        t1m = _min(m, t1_src)
        if t1m < w0 or t0m > w1:
            continue
        g = o.geometry
        rec = {"type": o.type, "why": o.why, "t0": t0m, "t1": t1m,
               "t_birth": _min(m, o.t_birth), "id": o.id,
               "events": o.events}
        if "top" in g:
            rec["lo"], rec["hi"] = g["bottom"], g["top"]
        if "price" in g:
            rec["price"], rec["side"] = g["price"], g.get("side")
        if "p0" in g:
            rec["p0"] = g["p0"]
            rec["slope"] = g["slope"]
            rec["t0_bar"] = g["t0"]
            rec["side"] = g.get("side")
            rec["dirn"] = 1 if g["slope"] > 0.05 else \
                (-1 if g["slope"] < -0.05 else 0)
        if "letter" in g:
            rec["letter"] = g["letter"]
        if o.type == "LABEL_TF":
            rec["price"] = g.get("price")
            rec["side"] = g.get("side")
            rec["letter"] = g.get("letter")
        out.append(rec)
    return out


# ------------------------------------------------------------------ #
# matching
# ------------------------------------------------------------------ #

def tol_px(o):
    """Match tolerance = the object's own label precision."""
    return C.prec_sigmas(o)[0]


def iou_true(a0, a1, b0, b1):
    inter = max(0.0, min(a1, b1) - max(a0, b0))
    union = max(a1 - a0, 0.0) + max(b1 - b0, 0.0) - inter
    return inter / union if union > 0 else 0.0


def _clip(a0, a1, w0, w1):
    if a0 is None or a1 is None:
        return None, None
    return max(a0, w0), min(a1, w1)


def _span(o):
    t0, t1 = o.get("t0"), o.get("t1")
    if t0 is None:
        return None, None
    return t0, (t1 if t1 is not None else t0)


def _overlap(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def _coverage(e0, e1, g0, g1):
    return _overlap(e0, e1, g0, g1) / float(max(g1 - g0, 1))


def _cov_or_point(e0, e1, g0, g1):
    """Coverage, with a degenerate clipped engine span (a point at the
    panel edge) scoring 1.0 iff it sits inside the golden span."""
    if e1 <= e0:
        return 1.0 if (g0 <= e0 <= g1) else 0.0
    return _coverage(e0, e1, g0, g1)


def _gold_window(g):
    """Golden containment window (D9): build_start (fallback t0) to
    build_end (fallback t1).  A degenerate point window (build_start ==
    build_end, ~10 objects where only one side was annotated) carries
    no containment information -> fall back to the drawn span."""
    t0, t1 = _span(g)
    bs = g.get("build_start") if g.get("build_start") is not None else t0
    be = g.get("build_end") if g.get("build_end") is not None else t1
    if bs is None or be is None or be <= bs:
        return t0, t1
    return bs, be


def _eng_window(e):
    """Engine containment window: recorded build window, else drawn
    start to the break bar (D9: containment ends at the break), else
    the drawn span.  Degenerate windows fall back to the drawn span."""
    e0, e1 = _span(e)
    bs = e.get("bs") if e.get("bs") is not None else e.get("t0_raw", e0)
    be = e.get("be")
    if be is None:
        be = e.get("break_bar_min")
    if be is None:
        be = e.get("t1_raw", e1)
    if bs is None or be is None or be <= bs:
        return e.get("t0_raw", e0), e.get("t1_raw", e1)
    return bs, be


def _has_gold_window(g):
    """True iff the golden side recorded a genuine (non-degenerate)
    containment window: build_start < build_end (R11 §11.1)."""
    bs, be = g.get("build_start"), g.get("build_end")
    return bs is not None and be is not None and be > bs


def _has_eng_window(e):
    """True iff the engine record carries a genuine containment window:
    a recorded build start plus a build end or break bar strictly later
    (R11 §11.1)."""
    bs = e.get("bs")
    be = e.get("be") if e.get("be") is not None else e.get("break_bar_min")
    return bs is not None and be is not None and be > bs


def _box_edges_ok(g, e, t_only, tol):
    """Both edges within the object's own price tolerance.  When the
    golden side defines edges but the engine record gives none, the
    test FAILS (the engine side gave no edges)."""
    if t_only or g.get("price_lo") is None:
        return True                         # no edge evidence demanded
    if e.get("lo") is None:
        return False                        # engine side gave no edges
    return abs(e["lo"] - g["price_lo"] / PIP) <= tol and \
        abs(e["hi"] - g["price_hi"] / PIP) <= tol


def _ovcoef(a0, a1, b0, b1):
    """Overlap coefficient: intersection / shorter window.  A degenerate
    (point) shorter window scores 1.0 iff it sits inside the other."""
    la, lb = a1 - a0, b1 - b0
    if min(la, lb) <= 0:
        p = a0 if la <= 0 else b0
        lo, hi = (b0, b1) if la <= 0 else (a0, a1)
        return 1.0 if lo <= p <= hi else 0.0
    return _overlap(a0, a1, b0, b1) / min(la, lb)


def box_located(g, e, m):
    """R11 §11.1 diagnostic "located": right place, any extent —
    overlap coefficient >= 0.5 on the containment windows plus both
    edges within tol.  Reported next to recall; never counts as a
    match."""
    if g["spec_type"] not in BOX_TYPES:
        return False
    if EV.FAMILY.get(g["spec_type"]) != EV.FAMILY.get(e["type"]):
        return False
    wg0, wg1 = _gold_window(g)
    we0, we1 = _eng_window(e)
    if None in (wg0, wg1, we0, we1):
        return False
    tol = tol_px(g)
    return _ovcoef(we0, we1, wg0, wg1) >= 0.5 and \
        _box_edges_ok(g, e, C.is_time_only(g), tol)


def _eng_line_at(e, t_min, m):
    j = int(np.searchsorted(m, t_min))
    j = min(j, len(m) - 1)
    return e["p0"] + e["slope"] * (j - e["t0_bar"])


def _gold_line_at(g, t_min):
    t0, t1 = g["t0"], g["t1"]
    p0, p1 = g["price0"] / PIP, g["price1"] / PIP
    if t1 == t0:
        return p0
    return p0 + (p1 - p0) * (t_min - t0) / (t1 - t0)


def score(g, e):
    """Assignment key: coverage of the golden (containment) window."""
    gt = g["spec_type"]
    g0, g1 = (_gold_window(g) if gt in BOX_TYPES else _span(g))
    e0, e1 = _span(e)
    if None in (g0, g1, e0, e1):
        return 0.0
    return _coverage(e0, e1, g0, g1)


def _fam_letter(s):
    return (s or "").replace("m", "").replace("w", "").replace("i", "")


def match_detail(g, e, m):
    """(matched, route) — route labels the BOX evidence used."""
    gt = g["spec_type"]
    if EV.FAMILY.get(gt) != EV.FAMILY.get(e["type"]):
        return False, "family"
    t_only = C.is_time_only(g)
    tol = tol_px(g)
    w0, w1 = e.get("w0", -10**9), e.get("w1", 10**9)
    g0, g1 = _clip(*_span(g), w0, w1)
    e0, e1 = _clip(*_span(e), w0, w1)
    if None in (g0, g1, e0, e1):
        return False, "no_span"

    if gt in BOX_TYPES:
        wg0, wg1 = _gold_window(g)
        we0, we1 = _eng_window(e)
        edges_ok = _box_edges_ok(g, e, t_only, tol)
        # R11 §11.1: match = true IoU of the containment windows >= 0.5
        # plus both edges within tol.  The drawn-span coverage fallback
        # survives ONLY when a side recorded no containment window at
        # all (absent or degenerate); its use is counted via the route.
        if None not in (wg0, wg1, we0, we1) and \
                iou_true(we0, we1, wg0, wg1) >= 0.5:
            return edges_ok, "containment_iou"
        if not (_has_gold_window(g) and _has_eng_window(e)) and \
                wg0 is not None and wg1 is not None and \
                _cov_or_point(e0, e1, wg0, wg1) >= 0.5:
            return edges_ok, "coverage"
        return False, "box_span"

    if gt in LINE_TYPES:
        if e1 <= e0:
            # degenerate visible span: single-point anchor check
            if not (g0 <= e0 <= g1):
                return False, "line_overlap"
            if t_only:
                return True, "line_span_dir"
            p0g = g.get("price0")
            if p0g is None or e.get("p0") is None:
                return True, "line_span_dir"
            slope_g = ((g["price1"] - p0g) / PIP / max(g1 - g0, 1)
                       if g.get("price1") is not None else 0.0)
            tol_l = tol + abs(slope_g) * C.TIME_SIGMA_MIN
            ok = abs(_eng_line_at(e, e0, m)
                     - _gold_line_at(g, e0)) <= tol_l
            return ok, "line_anchors"
        ov = _overlap(e0, e1, g0, g1)
        min_ov = min(0.5 * (g1 - g0), max(10.0, 0.25 * (g1 - g0)))
        if ov < min_ov:
            return False, "line_overlap"
        p0g, p1g = g.get("price0"), g.get("price1")
        if t_only or p0g is None or p1g is None or e.get("p0") is None:
            gd = {"up": 1, "down": -1}.get(g.get("dir"))
            ok = gd is None or gd == e.get("dirn") or t_only
            return ok, "line_span_dir"
        slope_g = (p1g - p0g) / PIP / max(g1 - g0, 1)
        tol_l = tol + abs(slope_g) * C.TIME_SIGMA_MIN
        a, b = max(e0, g0), min(e1, g1)
        ok = abs(_eng_line_at(e, a, m) - _gold_line_at(g, a)) <= tol_l \
            and abs(_eng_line_at(e, b, m) - _gold_line_at(g, b)) <= tol_l
        return ok, "line_anchors"

    if gt in LEVEL_TYPES:
        ov = _overlap(e0, e1, g0, g1) > 0 or \
            (e1 <= e0 and g0 <= e0 <= g1)
        if g.get("price") is None or e.get("price") is None or t_only:
            return ov, "level_span"
        return (ov and abs(e["price"] - g["price"] / PIP) <= tol), \
            "level_zone"

    if gt == "BRACKET":
        ok = _cov_or_point(e0, e1, g0, g1) >= 0.3 and \
            _fam_letter(g.get("letter")) == _fam_letter(e.get("letter"))
        return ok, "bracket"

    if gt == "SQUEEZE":
        return _cov_or_point(e0, e1, g0, g1) >= 0.3, "squeeze"

    if gt == "BAR_MARKER":
        em = 0.5 * (e0 + e1)
        return g0 - C.TIME_SIGMA_MIN <= em <= g1 + C.TIME_SIGMA_MIN, \
            "marker_time"

    if _cov_or_point(e0, e1, g0, g1) < 0.3:
        return False, "other_span"
    if g.get("price") is not None and e.get("price") is not None:
        return abs(e["price"] - g["price"] / PIP) <= tol, "other_price"
    if g.get("price_hi") is not None and e.get("hi") is not None:
        ok = abs(e["lo"] - g["price_lo"] / PIP) <= tol and \
            abs(e["hi"] - g["price_hi"] / PIP) <= tol
        return ok, "other_edges"
    return True, "other"


def match(g, e, m):
    return match_detail(g, e, m)[0]


def match_mark(gm, em):
    """LABEL_TF: same side + time within the catalogue precision."""
    if em["type"] != "LABEL_TF":
        return False
    if gm.get("side") and em.get("side") and gm["side"] != em["side"]:
        return False
    if gm.get("t") is None or em.get("t_birth") is None:
        return True
    return abs(em["t_birth"] - gm["t"]) <= C.TIME_SIGMA_MIN


# ------------------------------------------------------------------ #
# scorability boundary (the E1-B3 fix)
# ------------------------------------------------------------------ #

def scorable(g, w0, w1):
    """A golden object is scorable only if its span intersects the
    panel window the engine was actually scored on."""
    g0, g1 = _span(g)
    if g0 is None:
        return True
    return not (g1 < w0 or g0 > w1)


def scorable_mark(gm, w0, w1):
    t = gm.get("t")
    return t is None or (w0 <= t <= w1)
