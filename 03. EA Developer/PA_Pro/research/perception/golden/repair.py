"""repair — G-AUDIT (b)(c)(d): repair, price recovery, BOOK2012_v2.

Merges the two sources of truth per object:
- `draft/BOOK2012_draft.jsonl`  — the catalogue of record (author's stated
  times, prices, note).  NEVER modified.
- `BOOK2012_{SPLIT}.jsonl`      — the pixel-refined overlay (geometry only;
  known to be corrupted by corridor_fit candle-ink contamination, D8).

Repair precedence (Ruling 2 RESUME 3 §3):
  1. text_anchor_bars — rebuild the object from the bars the text names
     (anchor extremes, stated spans, stated prices);
  2. constrained_fit  — choose geometry maximising bar touches under the
     text's slope/side constraints.  Scan ink may confirm or break a tie;
     it never sets a line's slope sign against the text;
  3. text_price       — the catalogue's own prices override refined edges;
  4. time_only        — times kept, no recoverable price;
  5. unusable         — geometry cannot be reconciled with the text.

Every repaired object is re-validated with the SAME validator, so a repair
is only kept if it passes the hard checks.

Usage:  python repair.py TUNE|HOLD|ALL
Writes: golden/draft/BOOK2012_{SPLIT}_v2.jsonl  +  repair_{SPLIT}.jsonl log
"""

import collections
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "..")):
    _p = os.path.abspath(_p)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import textfeat as TF                                       # noqa: E402
import validate as V                                        # noqa: E402

DRAFT = os.path.join(HERE, "draft")


# ------------------------------------------------------------------ #
# small helpers
# ------------------------------------------------------------------ #

def _hhmm(v):
    """'HH:MM' or int -> int CET minutes; None passthrough."""
    if v is None:
        return None
    if isinstance(v, str):
        if ":" not in v:
            return None
        h, m = v.split(":")[:2]
        return int(h) * 60 + int(m)
    return int(v)


def touch_candidates(day, mask, kind):
    """Bar indices worth anchoring a line through: local extremes,
    running extremes, and the span's first/last bars.  kind 'low'/'high'/
    'any'."""
    idx = np.where(mask)[0]
    if not len(idx):
        return idx
    keep = set()
    ext = day.l if kind == "low" else day.h if kind == "high" else None
    for i in idx:
        lo, hi = max(idx[0], i - 3), min(idx[-1] + 1, i + 4)
        if kind == "any":
            keep.add(i)
            continue
        if ext[i] == (np.min(ext[lo:hi]) if kind == "low"
                      else np.max(ext[lo:hi])):
            keep.add(i)
    keep.add(int(idx[0]))
    keep.add(int(idx[-1]))
    return np.array(sorted(keep))


def anchor_price(day, tm, kind, tol_bars=2):
    """Extreme price of the named bar: (price, bar_minute) or (None,None)."""
    j = day.idx(tm, tol_bars)
    if j is None:
        return None, None
    lo, hi = max(0, j - tol_bars), min(len(day), j + tol_bars + 1)
    if kind == "high":
        i = lo + int(np.argmax(day.h[lo:hi]))
        return float(day.h[i]), int(day.m[i])
    if kind == "low":
        i = lo + int(np.argmin(day.l[lo:hi]))
        return float(day.l[i]), int(day.m[i])
    # unspecified: nearer of the two extremes to nothing known -> return
    # both candidates, caller picks
    return None, None


def line_value(p_a, t_a, p_b, t_b, t):
    return p_a + (p_b - p_a) * (t - t_a) / float(t_b - t_a)


def score_line(day, mask, p_a, t_a, p_b, t_b, side):
    """(touches, violations) of the candidate line over the span."""
    ts = day.m[mask].astype(float)
    vals = p_a + (p_b - p_a) * (ts - t_a) / float(t_b - t_a)
    if side == "under":
        ext = day.l[mask]
        touches = int((np.abs(ext - vals) <= V.TOUCH_TOL).sum())
        viol = int((day.c[mask] < vals - V.TOUCH_TOL).sum())
    elif side == "over":
        ext = day.h[mask]
        touches = int((np.abs(ext - vals) <= V.TOUCH_TOL).sum())
        viol = int((day.c[mask] > vals + V.TOUCH_TOL).sum())
    else:
        e_lo, e_hi = day.l[mask], day.h[mask]
        d = np.minimum(np.abs(e_lo - vals), np.abs(e_hi - vals))
        touches = int((d <= V.TOUCH_TOL).sum())
        viol = int(((day.c[mask] < vals - V.TOUCH_TOL) |
                    (day.c[mask] > vals + V.TOUCH_TOL)).sum())
    return touches, viol


def _search_lines(day, mask, t0, t1, f, bounds, cands, anchors, kinds):
    """One slope-bound set: extreme pairs, then the anchor-ray sweep.
    Returns the best (score, touches, t_a, p_a, t_b, p_b)."""
    lo_b, hi_b = bounds or (None, None)
    side = f["side"]
    best = None
    for k in kinds:
        ii = cands[k]
        ext = day.l if k == "low" else day.h
        # horizontal candidates ("horizontal neckline"): allowed when the
        # bounds admit ~0 drift
        flat_ok = ((lo_b is None or lo_b - 0.75 <= 0.0)
                   and (hi_b is None or 0.0 <= hi_b + 0.75))
        for a in range(len(ii)):
            i = int(ii[a])
            t_a, p_a = int(day.m[i]), float(ext[i])
            if flat_ok and (not anchors or all(
                    abs(line_value(p_a, t_a, p_a, t_a + 5, at) - ap)
                    <= 2.0 for at, ap in anchors)):
                tch, viol = score_line(day, mask, p_a, t_a, p_a, t_a + 5,
                                       side)
                sc = tch - 1.5 * viol
                if best is None or sc > best[0]:
                    best = (sc, tch, t_a, p_a, t_a + 5, p_a)
            for b in range(a + 1, len(ii)):
                j = int(ii[b])
                t_b, p_b = int(day.m[j]), float(ext[j])
                d = p_b - p_a
                if lo_b is not None and d < lo_b - 0.75:
                    continue
                if hi_b is not None and d > hi_b + 0.75:
                    continue
                if anchors and not all(
                        abs(line_value(p_a, t_a, p_b, t_b, at) - ap)
                        <= 2.0 for at, ap in anchors):
                    continue
                tch, viol = score_line(day, mask, p_a, t_a, p_b, t_b, side)
                sc = tch - 1.5 * viol
                if best is None or sc > best[0]:
                    best = (sc, tch, t_a, p_a, t_b, p_b)
    # Volman draws FROM the named bar: if no extreme-pair satisfies the
    # anchor, hold the anchor fixed and sweep the free end.
    if (best is None or best[1] < V.MIN_TOUCHES) and anchors:
        at, ap = anchors[0]
        idx = np.where(mask)[0]
        for k in kinds:
            ext = day.l if k == "low" else day.h
            for i in idx:
                t_b = int(day.m[i])
                if abs(t_b - at) < 10:
                    continue
                for dp in np.arange(-6.0, 6.01, 0.5):
                    p_b = float(ext[i]) + dp
                    d = (line_value(ap, at, p_b, t_b, t1)
                         - line_value(ap, at, p_b, t_b, t0))
                    if lo_b is not None and d < lo_b - 0.75:
                        continue
                    if hi_b is not None and d > hi_b + 0.75:
                        continue
                    if t_b > at:
                        tch, viol = score_line(day, mask, ap, at, p_b,
                                               t_b, side)
                        sc = tch - 1.5 * viol
                        if best is None or sc > best[0]:
                            best = (sc, tch, at, ap, t_b, p_b)
                    else:
                        tch, viol = score_line(day, mask, p_b, t_b, ap,
                                               at, side)
                        sc = tch - 1.5 * viol
                        if best is None or sc > best[0]:
                            best = (sc, tch, t_b, p_b, at, ap)
    return best


def fit_line(day, t0, t1, f):
    """Constrained line fit over [t0,t1] honouring every slope cue the
    text permits, its side and its anchors.  Returns (p0, p1, n_touches)
    or None."""
    mask = day.span(t0, t1)
    if int(mask.sum()) < 3:
        return None
    side = f["side"]
    kinds = (["low"] if side == "under" else ["high"] if side == "over"
             else ["low", "high"])
    cands = {k: touch_candidates(day, mask, k) for k in kinds}
    anchors = []
    for (tm, kind) in f["anchors"]:
        for k in (kinds if kind in (None, "bar", "wick") else [kind]):
            p, mt = anchor_price(day, tm, k)
            if p is not None:
                anchors.append((mt, p))
                break
    # a compound note names anchors for sibling objects too ("a rising
    # line from the ~08:35 low and a falling line from the ~09:30 high"):
    # only an anchor at THIS object's own endpoints constrains its fit
    own = [(tm, p) for tm, p in anchors
           if abs(tm - t0) <= 15 or abs(tm - t1) <= 15]
    if own:
        anchors = own
    best = None
    for bounds in (f.get("slope_cues") or [None]):
        cand = _search_lines(day, mask, t0, t1, f, bounds, cands,
                             anchors, kinds)
        if cand and (best is None or cand[0] > best[0]):
            best = cand
    if best is None:
        return None
    # a line the text calls broken/pierced/teased is only required to
    # hold until the break: refit on the pre-break prefix (drawn span
    # unchanged — same D9 semantics as boxes)
    if f["broken"] or f["pierced"] or f["teased"]:
        _, _, t_a, p_a, t_b, p_b = best
        idx = np.where(mask)[0]
        if f.get("break_at"):
            # the text names the break bar outright — refit on the
            # prefix before it without scanning for the first breach
            pidx = day.span(t0, f["break_at"] - 5)
            if int(pidx.sum()) >= 3:
                c2 = {k: touch_candidates(day, pidx, k)
                      for k in kinds}
                cand2 = None
                for bounds in (f.get("slope_cues") or [None]):
                    cc = _search_lines(day, pidx, t0, t1, f, bounds,
                                       c2, anchors, kinds)
                    if cc and (cand2 is None or cc[0] > cand2[0]):
                        cand2 = cc
                if cand2 is not None:
                    best = cand2
            else:
                f["break_at"] = None
        if not f.get("break_at"):
            for j in idx:
                v = line_value(p_a, t_a, p_b, t_b, int(day.m[j]))
                if (f["side"] == "over" and day.c[j] < v - V.TOUCH_TOL) or \
                   (f["side"] != "over" and day.c[j] > v + V.TOUCH_TOL):
                    pidx = day.span(t0, int(day.m[j]) - 5)
                    if int(pidx.sum()) >= 3:
                        cand2 = None
                        c2 = {k: touch_candidates(day, pidx, k)
                              for k in kinds}
                        for bounds in (f.get("slope_cues") or [None]):
                            cc = _search_lines(day, pidx, t0, t1, f,
                                               bounds, c2, anchors,
                                               kinds)
                            if cc and (cand2 is None
                                       or cc[0] > cand2[0]):
                                cand2 = cc
                        if cand2 is not None:
                            best = cand2
                    break
    _, tch, t_a, p_a, t_b, p_b = best
    if f["side"] and tch < V.MIN_TOUCHES:
        return None
    p0 = line_value(p_a, t_a, p_b, t_b, t0)
    p1 = line_value(p_a, t_a, p_b, t_b, t1)
    return p0, p1, tch


def edge_pins(day, idx, f):
    """Text-named box edges: 'bottom = the 10:25 spike low', 'its top
    sits on the 07:00 wick'.  Ambiguous kinds pin the farther outlier
    relative to the span median.  Returns (pin_lo, pin_hi)."""
    if not len(idx):
        return None, None
    med = float(np.median(day.c[idx]))
    pin_lo = pin_hi = None
    for (tm, kind) in (f.get("anchors") or []):
        jj = day.idx(tm, 2)
        if jj is None:
            continue
        wlo, whi = max(0, jj - 2), min(len(day), jj + 3)
        p_lo = float(np.min(day.l[wlo:whi]))
        p_hi = float(np.max(day.h[wlo:whi]))
        if kind == "low":
            pin_lo = p_lo
        elif kind == "high":
            pin_hi = p_hi
        elif pin_lo is None and pin_hi is None:
            if abs(p_hi - med) >= abs(med - p_lo):
                pin_hi = p_hi
            else:
                pin_lo = p_lo
    return pin_lo, pin_hi


def fit_box_edges(day, t0, t1, f, marks, span_pips=None):
    """Barrier edges from bars.
    Returns (lo, hi, build_end, nt, nb, pin_lo, pin_hi).

    Semantics (confirmed on 9.54a/9.50b/9.56c, D9): a box's drawn right
    edge is how long it was DRAWN, not how long it held — the stated
    height matches the pre-break range.  So:
      - the edge is the most extreme level that still has company
        (>= MIN_TOUCHES bars printing it); a lone spike is a poke;
      - build_end = the first close decisively beyond an edge, i.e. the
        break; containment is only meaningful over [t0, build_end];
      - when the text states a height ("~22 pips"), the break is where
        the running range first outgrows it, and edges are searched under
        the height constraint.
    """
    mask = day.span(t0, t1)
    idx = np.where(mask)[0]
    if len(idx) < 3:
        return None
    poke_up, poke_dn = set(), set()
    for m in marks:
        mt = _hhmm(m.get("t"))
        if mt is None:
            continue
        j = day.idx(mt, 2)
        if j is None or not mask[j]:
            continue
        (poke_up if m.get("side") == "above" else poke_dn).add(j)

    def break_at(sp):
        """First bar where the running range outgrows the stated height,
        or where a close escapes the current cluster.  Returns a bar
        count into idx, or len(idx)."""
        if sp:
            for k in range(4, len(idx) + 1):
                seg = idx[:k]
                if (np.max(day.h[seg]) - np.min(day.l[seg])
                        > sp * 1.3 + 1.0):
                    return max(k - 1, int(0.45 * len(idx)))
        return len(idx)

    # a named edge anchor pins that edge: "bottom = the 10:25 spike low",
    # "its top sits on the 07:00 wick"
    pin_lo, pin_hi = edge_pins(day, idx, f)

    n_pref = break_at(span_pips)
    pref = idx[:n_pref]

    def edge(vals, pokes_abs, is_top, base):
        """Most extreme value that still has company: the highest high
        (or lowest low) printed by >= MIN_TOUCHES bars.  A lone spike is
        a poke through the barrier, not the barrier.  pokes_abs/base are
        absolute bar indices; vals is indexed positionally vs base."""
        order = np.argsort(-vals if is_top else vals)
        fallback = None
        for pos in order:
            if int(base[pos]) in pokes_abs:
                continue
            if fallback is None:
                fallback = pos
            c = vals[pos]
            tch = int((np.abs(vals - c) <= V.TOUCH_TOL).sum())
            if tch >= V.MIN_TOUCHES:
                return float(c), tch
        if fallback is not None:
            c = vals[fallback]
            return float(c), int((np.abs(vals - c) <= V.TOUCH_TOL).sum())
        return float(np.max(vals) if is_top else np.min(vals)), 1

    hi, nt = edge(day.h[pref], poke_up, True, pref)
    lo, nb = edge(day.l[pref], poke_dn, False, pref)
    if lo > hi:
        lo, hi = hi, lo

    # Refine the break against the fitted edges: first close decisively
    # beyond either edge ends the buildup.
    beyond = np.where(((day.c[idx] > hi + V.TOUCH_TOL) |
                       (day.c[idx] < lo - V.TOUCH_TOL)))[0]
    if len(beyond):
        n2 = int(beyond[0])
        if n2 >= max(3, int(0.45 * len(idx))):
            n_pref = n2
            pref = idx[:n_pref]
            hi, nt = edge(day.h[pref], poke_up, True, pref)
            lo, nb = edge(day.l[pref], poke_dn, False, pref)
            if lo > hi:
                lo, hi = hi, lo

    # the text's named edge wins over the fitted cluster edge; with a
    # stated height the free edge sits at pin +/- height
    if pin_lo is not None:
        lo = pin_lo
        nb = int((np.abs(day.l[pref] - lo) <= V.TOUCH_TOL).sum())
        if span_pips:
            tgt = lo + span_pips
            cands_t = np.sort(day.h[pref])[::-1]
            cands_t = [c for c in cands_t if abs(c - tgt) <= 6.0]
            if cands_t:
                hi = min(cands_t,
                         key=lambda c: (abs(c - tgt),
                                        -int((np.abs(day.h[pref] - c)
                                              <= 2.5).sum())))
            else:
                hi = tgt
            nt = int((np.abs(day.h[pref] - hi) <= V.TOUCH_TOL).sum())
    if pin_hi is not None:
        hi = pin_hi
        nt = int((np.abs(day.h[pref] - hi) <= V.TOUCH_TOL).sum())
        if span_pips:
            tgt = hi - span_pips
            cands_b = np.sort(day.l[pref])
            cands_b = [c for c in cands_b if abs(c - tgt) <= 6.0]
            if cands_b:
                lo = min(cands_b,
                         key=lambda c: (abs(c - tgt),
                                        -int((np.abs(day.l[pref] - c)
                                              <= 2.5).sum())))
            else:
                lo = tgt
            nb = int((np.abs(day.l[pref] - lo) <= V.TOUCH_TOL).sum())
    if lo > hi:
        lo, hi = hi, lo

    # a big-figure reference is a price anchor: "under the 1.30" puts
    # the lid on 1.3000.  "Straddling 1.26" means the figure lies INSIDE
    # the box — a constraint on the edge search below, not a centre.
    rr = (f["round_refs"][0] / V.PIP) if f.get("round_refs") else None
    strad = bool(f.get("straddle")) and rr is not None
    if rr is not None and not strad:
        if f["side"] == "under":
            hi = rr
            if span_pips:
                lo = rr - span_pips
        elif f["side"] == "over":
            lo = rr
            if span_pips:
                hi = rr + span_pips
        elif span_pips and abs(rr - (lo + hi) / 2) < span_pips:
            mid = (lo + hi) / 2
            lo, hi = lo + (rr - mid), hi + (rr - mid)
        nb = int((np.abs(day.l[pref] - lo) <= V.TOUCH_TOL).sum())
        nt = int((np.abs(day.h[pref] - hi) <= V.TOUCH_TOL).sum())

    # If the text states a height and the fit disagrees — or the box must
    # straddle a figure it currently doesn't — slide a fixed-height window
    # over candidate lower edges.  A straddle searches the whole drawn
    # span (the containing run is defined by the fitted edges, D9), a
    # height-only fix searches the pre-break prefix.
    need_h = span_pips and (hi - lo) > span_pips + max(3.0, 0.25 * span_pips)
    need_s = strad and span_pips and not (lo < rr < hi)
    build_start = build_end = None
    if span_pips and (need_h or need_s):
        src = idx if need_s else pref
        cands_b = np.sort(np.unique(day.l[src]))[:14]
        best = None
        for c_b in cands_b:
            c_t = float(c_b) + span_pips
            if need_s and not (c_b < rr < c_t):
                continue
            nt2 = int((np.abs(day.h[src] - c_t) <= 2.5).sum())
            nb2 = int((np.abs(day.l[src] - c_b) <= 2.5).sum())
            if nt2 < 1 or nb2 < 1:
                continue
            # containment over the window's own buildup era
            inb = ((day.c[src] <= c_t + V.TOUCH_TOL)
                   & (day.c[src] >= c_b - V.TOUCH_TOL))
            if not inb.any():
                continue
            first = int(np.argmax(inb))
            end = len(src)
            for k in range(first + 1, len(src)):
                if not inb[k]:
                    end = k
                    break
            inside = (float(inb[first:end].mean()) if end > first
                      else 0.0)
            if inside < 0.80:
                continue
            sc = min(nt2, nb2) + 0.2 * (nt2 + nb2) + inside
            if best is None or sc > best[0]:
                best = (sc, float(c_b), float(c_t), nt2, nb2,
                        int(day.m[src[first]]),
                        int(day.m[src[end - 1]]))
        if best is not None:
            _, lo, hi, nt, nb, build_start, build_end = best
    if build_end is None:
        build_end = (int(day.m[pref[-1]]) if n_pref < len(idx)
                     else int(t1))
    return lo, hi, build_end, build_start, nt, nb, pin_lo, pin_hi


def subwindow_run(day, idx, sp):
    """Longest run of consecutive bars whose closes fit inside SOME band
    of height <= 1.35*sp — the box may bound only part of the stated
    span ('around the low base').  Returns (s, e) positions into idx."""
    best = None
    for s in range(len(idx)):
        lo_r, hi_r = np.inf, -np.inf
        for e in range(s, len(idx)):
            c = day.c[idx[e]]
            nlo, nhi = min(lo_r, c), max(hi_r, c)
            if nhi - nlo > sp * 1.35:
                break
            lo_r, hi_r = nlo, nhi
            if best is None or e - s > best[1] - best[0]:
                best = (s, e)
    return best


# ------------------------------------------------------------------ #
# per-object repair
# ------------------------------------------------------------------ #

def base_v2(d, r):
    """Normalised v2 skeleton: draft fields are the catalogue truth."""
    return {
        "spec_type": d.get("spec_type") or r.get("spec_type"),
        "style": d.get("style") or r.get("style"),
        "dir": d.get("dir"), "letter": d.get("letter") or r.get("letter"),
        "prec": d.get("prec"), "meas": d.get("meas"),
        "approx_time": d.get("approx_time"),
        "approx_price": d.get("approx_price"),
        "raw_note": d.get("note") or r.get("raw_note") or "",
        "text_t0": _hhmm(d.get("t0")), "text_t1": _hhmm(d.get("t1")),
        "text_price": d.get("price"), "text_price2": d.get("price2"),
        "text_span_pips": d.get("span_pips"),
        "clause": d.get("_clause"),
        "t0": _hhmm(r.get("t0")) if r.get("t0") is not None
        else _hhmm(d.get("t0")),
        "t1": _hhmm(r.get("t1")) if r.get("t1") is not None
        else _hhmm(d.get("t1")),
        "price": None, "price0": None, "price1": None,
        "price_lo": None, "price_hi": None, "build_end": None,
        "build_start": None,
        "pin_lo": False, "pin_hi": False,
        "status": "ok", "repair_method": "none",
        "fails": [],
    }


def revalidate(rec_ctx, v2o, day):
    """Run the same validator on the v2 geometry; returns hard-fail codes."""
    shim = dict(v2o)
    res = V.Result(rec_ctx["id"], -1, v2o["spec_type"])
    f = TF.parse(v2o.get("clause") or v2o["raw_note"], v2o["spec_type"])
    V.check_window(res, rec_ctx, shim, f)
    fn = V.CHECKERS.get(v2o["spec_type"])
    if fn:
        fn(res, rec_ctx, shim, f, day)
    return [c[0] for c in res.hard_fails]


def repair_line(rec, d, r, f, day, marks):
    o = base_v2(d, r)
    p0, p1 = V.line_pts(r)
    o["price0"], o["price1"] = (p0 * V.PIP if p0 is not None else None,
                                p1 * V.PIP if p1 is not None else None)
    if o["t0"] is None:
        o["t0"], o["t1"] = o["text_t0"], o["text_t1"]
    if o["t0"] is None and f["spans"]:
        o["t0"], o["t1"] = f["spans"][0]
    if o["t0"] is None and f["anchors"]:
        # "from the ~03:55 low to the right edge": the named bar is the
        # start even though it was not parsed as a span endpoint
        o["t0"] = f["anchors"][0][0]
    if o["t1"] is None and o["t0"] is not None:
        w1 = _hhmm(rec.get("x1"))
        o["t1"] = w1                       # "to the right edge"
    if o["t0"] is not None and o["t1"] is not None and o["t1"] < o["t0"]:
        if f["broken"]:
            # "rising support extended to ~17:30, broken by the 16:00
            # bar": the parser read the DRAWN end as t0 and the BREAK
            # bar as t1.  The line lives before the break; drawn end =
            # the larger time, fit over [window start, break).
            f["break_at"] = o["t1"]
            o["t1"] = o["t0"]
            o["t0"] = _hhmm(rec.get("x0"))
        else:
            o["t0"], o["t1"] = o["t1"], o["t0"]
    if o["t0"] is None:
        o["status"], o["repair_method"] = "unusable", "unusable"
        return o
    # "a converging triangle: ... both to ~11:55" — the trailing time is
    # the shared drawn end of the legs, not the second anchor's bar
    if f["times"] and o["t1"] is not None:
        last = max(f["times"])
        if last > o["t1"] + 10 and re.search(
                r"both to|converging|triangle|extend", o["raw_note"].lower()):
            o["t1"] = last

    # explicit anchor-bar repair: the text names a bar, snap to it
    if f["anchors"]:
        for (tm, kind) in f["anchors"]:
            for k in ([kind] if kind not in (None, "bar", "wick")
                      else ["low", "high"]):
                p, mt = anchor_price(day, tm, k)
                if p is None:
                    continue
                # anchor sits at the named bar; rebuild the other end by
                # constrained fit through it
                fit = fit_line(day, o["t0"], o["t1"], f)
                if fit is not None:
                    o["price0"], o["price1"] = fit[0] * V.PIP, fit[1] * V.PIP
                    o["repair_method"] = "text_anchor_bars"
                    break
            if o["repair_method"] != "none":
                break
    if o["repair_method"] == "none":
        fit = fit_line(day, o["t0"], o["t1"], f)
        if fit is not None:
            o["price0"], o["price1"] = fit[0] * V.PIP, fit[1] * V.PIP
            o["repair_method"] = "constrained_fit"
    if o["repair_method"] == "none" and f["prices"]:
        # "a short solid top at ≈1.3137": the text gives the level —
        # honour it verbatim rather than fitting bars
        p = f["prices"][0]
        o["price0"] = o["price1"] = p
        o["repair_method"] = "text_price"
    if o["repair_method"] == "none" and o["price0"] is None:
        # nothing recoverable: times known -> time_only, else unusable
        if o["t0"] is not None:
            o["status"], o["repair_method"] = "time_only", "time_only"
        else:
            o["status"], o["repair_method"] = "unusable", "unusable"
        return o
    o["fails"] = revalidate(rec, o, day)
    if o["repair_method"] == "none":
        o["status"] = "ok" if not o["fails"] else "unusable"
        if o["fails"]:
            o["repair_method"] = "unusable"
            o["price0"] = o["price1"] = None
    else:
        o["status"] = "repaired" if not o["fails"] else "unusable"
        if o["fails"]:
            o["repair_method"] += "+fail"
    return o


def _set_build_window(o, day):
    """D9 for a priced box: the drawn span [t0,t1] is cosmetic; the
    buildup era runs from the first close inside the edges to the bar
    before the first decisive close beyond them."""
    lo_p, hi_p = o["price_lo"] / V.PIP, o["price_hi"] / V.PIP
    idx = np.where(day.span(o["t0"], o["t1"]))[0]
    inside = (day.c[idx] <= hi_p + V.TOUCH_TOL) \
        & (day.c[idx] >= lo_p - V.TOUCH_TOL)
    if not inside.any():
        return
    first_in = int(np.argmax(inside))
    if first_in > 0:
        o["build_start"] = int(day.m[idx[first_in]])
    for j in idx[first_in + 1:]:
        if day.c[j] > hi_p + V.TOUCH_TOL or day.c[j] < lo_p - V.TOUCH_TOL:
            o["build_end"] = int(day.m[j - 1])
            break


def repair_box(rec, d, r, f, day, marks):
    o = base_v2(d, r)
    if o["t0"] is None:
        o["t0"], o["t1"] = o["text_t0"], o["text_t1"]
    if o["t0"] is None and f["spans"]:
        o["t0"], o["t1"] = f["spans"][0]
    if o["t1"] is None:
        o["t1"] = _hhmm(rec.get("x1"))
    if o["t0"] is None:
        # "left edge off-chart" (RANGE_OPEN over Asia) or similar
        o["t0"] = _hhmm(rec.get("x0"))
    if o["t0"] is None:
        o["status"], o["repair_method"] = "unusable", "unusable"
        return o
    if o["t1"] is not None and o["t1"] < o["t0"]:
        o["t0"], o["t1"] = o["t1"], o["t0"]

    if o["text_price"] is not None and o["text_price2"] is not None:
        # the author's measured/estimated prices are authoritative
        o["price_lo"] = min(o["text_price"], o["text_price2"])
        o["price_hi"] = max(o["text_price"], o["text_price2"])
        o["repair_method"] = "text_price"
        # D9 still applies: the rectangle is DRAWN to t1, but it is only
        # required to contain closes of its buildup era — i.e. from the
        # first in-band close to the first decisive breach.
        _set_build_window(o, day)
    elif r.get("price_lo") is not None and r.get("price_hi") is not None:
        o["price_lo"], o["price_hi"] = r["price_lo"], r["price_hi"]
        _set_build_window(o, day)
    else:
        o["repair_method"] = "pending"

    # validate what we have; if it fails and there are no text prices,
    # rebuild edges from bars (pokes excluded)
    o["fails"] = revalidate(rec, o, day)
    if o["fails"] and o["repair_method"] != "text_price":
        eb = fit_box_edges(day, o["t0"], o["t1"], f, marks,
                           span_pips=d.get("span_pips"))
        if eb is not None:
            lo, hi, bend, bstart, nt, nb, pl, ph = eb
            o["price_lo"], o["price_hi"] = lo * V.PIP, hi * V.PIP
            o["build_end"] = bend
            if bstart is not None:
                o["build_start"] = bstart
            o["pin_lo"], o["pin_hi"] = bool(pl), bool(ph)
            o["repair_method"] = "edge_from_bars"
            o["fails"] = revalidate(rec, o, day)
        # last resort for a stated-height box: bound only the contiguous
        # run that actually fits the height ("around the low base").
        # The stated height fixes hi-lo, so slide a single edge.
        if ("CONTAIN" in o["fails"] or "HEIGHT_TEXT" in o["fails"]) \
                and d.get("span_pips") \
                and o["repair_method"] != "text_price":
            mask = day.span(o["t0"], o["t1"])
            idx = np.where(mask)[0]
            sp = d["span_pips"]
            run = subwindow_run(day, idx, sp)
            if run and run[1] - run[0] >= 2:
                seg = idx[run[0]:run[1] + 1]
                lows = np.sort(np.unique(day.l[seg]))
                rr = (f["round_refs"][0] / V.PIP) \
                    if f.get("round_refs") else None
                best = None
                for c_lo in lows:
                    c_hi = c_lo + sp
                    nt = int((np.abs(day.h[seg] - c_hi)
                              <= V.TOUCH_TOL).sum())
                    nb = int((np.abs(day.l[seg] - c_lo)
                              <= V.TOUCH_TOL).sum())
                    inside = np.mean((day.c[seg] <= c_hi + V.TOUCH_TOL)
                                     & (day.c[seg] >= c_lo - V.TOUCH_TOL))
                    rr_pen = 0.0
                    if rr is not None:
                        if f["side"] == "under":
                            rr_pen = abs(c_hi - rr) / 5.0
                        elif f["side"] == "over":
                            rr_pen = abs(c_lo - rr) / 5.0
                        elif f.get("straddle"):
                            rr_pen = abs((c_lo + c_hi) / 2 - rr) / 5.0
                    sc = nt + nb + 3.0 * inside - rr_pen
                    if best is None or sc > best[0]:
                        best = (sc, float(c_lo), float(c_hi))
                if best is not None:
                    _, lo, hi = best
                    o["price_lo"], o["price_hi"] = lo * V.PIP, hi * V.PIP
                    o["build_start"] = int(day.m[seg[0]])
                    o["build_end"] = int(day.m[seg[-1]])
                    o["repair_method"] = "edge_from_bars+subwindow"
                    o["fails"] = revalidate(rec, o, day)
    if o["repair_method"] == "text_price":
        # keep the author's prices even if bars disagree slightly; only a
        # hard structural fail (wrong span, missing bars) marks unusable
        structural = [c for c in o["fails"]
                      if c in ("TIME_WINDOW", "SPAN_BARS", "HAS_GEOM")]
        o["status"] = "ok" if not structural else "unusable"
    elif o["repair_method"] == "pending":
        o["status"] = "ok" if not o["fails"] else "unusable"
        o["repair_method"] = "none" if not o["fails"] else "unusable"
    else:
        o["status"] = ("ok" if o["repair_method"] == "none" and not o["fails"]
                       else "repaired" if not o["fails"] else "unusable")
        if o["fails"]:
            o["repair_method"] += "+fail" if o["repair_method"] != "none" \
                else "unusable"
    return o


def repair_level(rec, d, r, f, day, marks):
    o = base_v2(d, r)
    rp = r.get("price")
    o["price"] = rp
    if o["t0"] is None:
        o["t0"], o["t1"] = o["text_t0"], o["text_t1"]
    if o["t0"] is None and f["spans"]:
        o["t0"], o["t1"] = f["spans"][0]
    if o["t1"] is None:
        o["t1"] = _hhmm(rec.get("x1"))
    # a trailing "to ~HH:MM" beyond the build span is the carry's drawn
    # end: "from the 14:00-14:40 congestion lows ~1.3318 to ~17:35"
    if o["t1"] is not None and f["times"]:
        last = max(f["times"])
        if last > o["t1"] + 10:
            o["t1"] = last

    if o["text_price"] is not None:
        o["price"] = o["text_price"]
        o["repair_method"] = "text_price"
    elif o["price"] is None:
        # derive from the named bars: a *different* span if the text names
        # one, else the object's own span ("a tiny horizontal under the
        # combi, ~17:50-18:00" -> level under that span's lows)
        src = None
        for (a, b) in f["spans"]:
            if (a, b) != (o["t0"], o["t1"]):
                src = (a, b)
                break
        if src is None and f["anchors"]:
            tm = f["anchors"][0][0]
            src = (tm - 10, tm + 10)
        if src is None and o["t0"] is not None:
            src = (o["t0"], o["t1"] if o["t1"] is not None else o["t0"] + 30)
        if src and f["level_ref"]:
            mask = day.span(*src)
            if int(mask.sum()) >= 1:
                off = 0.7     # the drawn line sits just past the extreme
                hi_side = f["level_ref"] == "high"
                vals = day.h[mask] if hi_side else day.l[mask]
                # the edge is the most extreme print with company — a
                # lone spike (the breakout) is a poke, not the ceiling
                order = np.argsort(-vals if hi_side else vals)
                p = None
                for pos in order:
                    c = vals[pos]
                    if int((np.abs(vals - c) <= V.TOUCH_TOL).sum()) \
                            >= V.MIN_TOUCHES:
                        p = float(c)
                        break
                if p is None:
                    p = float(vals[order[0]])
                p = p + off if hi_side else p - off
                o["price"] = p * V.PIP
                o["repair_method"] = "text_anchor_bars"
        elif src:
            # bare "a short horizontal": the level sits on whichever
            # extreme the bars keep testing
            mask = day.span(*src)
            if int(mask.sum()) >= 1:
                lo_p = float(np.min(day.l[mask]))
                hi_p = float(np.max(day.h[mask]))
                tl = int(((day.l[mask] <= lo_p + V.TOUCH_TOL)
                          & (day.h[mask] >= lo_p - V.TOUCH_TOL)).sum())
                th = int(((day.l[mask] <= hi_p + V.TOUCH_TOL)
                          & (day.h[mask] >= hi_p - V.TOUCH_TOL)).sum())
                if tl or th:
                    p = (lo_p - 0.7) if tl >= th else (hi_p + 0.7)
                    o["price"] = p * V.PIP
                    o["repair_method"] = "edge_from_bars"
        if o["price"] is None:
            o["status"] = "time_only"
            o["repair_method"] = "time_only"
            return o

    # "projected from that congestion top": the level references a
    # sibling formation, not a bar — take that sibling's stated price
    if o["repair_method"] != "text_price" and re.search(
            r"projected from|that (congestion|base|range|box|formation)|"
            r"the congestion", o["raw_note"].lower()):
        cands = []
        for x in rec.get("objects", []):
            if x is d:
                continue
            xp = x.get("price")
            if xp is None:
                continue
            xp2 = x.get("price2")
            edge = (min(xp, xp2) if xp2 is not None else xp) \
                if f["level_ref"] == "low" \
                else (max(xp, xp2) if xp2 is not None else xp)
            cands.append(edge)
        if cands:
            o["price"] = (min(cands) if f["level_ref"] == "low"
                          else max(cands))
            o["repair_method"] = "sibling_span"
    o["fails"] = revalidate(rec, o, day)
    if o["repair_method"] == "text_price":
        o["status"] = "ok" if "HAS_GEOM" not in o["fails"] else "unusable"
    elif o["repair_method"] == "none":
        o["status"] = "ok" if not o["fails"] else "unusable"
        if o["fails"]:
            o["repair_method"] = "unusable"
            o["price"] = None
    else:
        o["status"] = "repaired" if not o["fails"] else "unusable"
        if o["fails"]:
            o["repair_method"] += "+fail"
    return o


def repair_bracket(rec, d, r, f, day, marks):
    o = base_v2(d, r)
    o["price"] = r.get("price") or d.get("price")
    if o["t0"] is None:
        o["t0"], o["t1"] = o["text_t0"], o["text_t1"]
    if o["t0"] is None and f["spans"]:
        o["t0"], o["t1"] = f["spans"][0]
    if o["t0"] is None:
        # "W span under the base" — the bracket spans the formation it
        # labels; take the sibling box's span (or the whole window if a
        # W/M straddles the session range)
        sib = [x for x in rec.get("objects", [])
               if x.get("spec_type") in ("BOX", "CONTEXT_RANGE",
                                        "RANGE_OPEN")
               and (x.get("t0") or _hhmm(x.get("t0"))) is not None]
        if len(sib) == 1:
            s = sib[0]
            o["t0"] = _hhmm(s.get("t0")) or s.get("t0")
            o["t1"] = _hhmm(s.get("t1")) or s.get("t1")
            o["repair_method"] = "sibling_span"
            letter = (o.get("letter") or "").upper()
            mask = day.span(o["t0"], o["t1"] or (o["t0"] + 30))
            if int(mask.sum()) >= 2:
                if letter in ("M", "SHS"):
                    o["price"] = (float(np.max(day.h[mask])) + 1.5) * V.PIP
                elif letter in ("W", "ISHS", "WW"):
                    o["price"] = (float(np.min(day.l[mask])) - 1.5) * V.PIP
    o["fails"] = revalidate(rec, o, day)
    if "BRACKET_SIDE" in o["fails"] and o["t0"] is not None:
        mask = day.span(o["t0"], o["t1"])
        if int(mask.sum()) >= 2:
            letter = (o.get("letter") or "").upper()
            if letter in ("M", "SHS"):
                o["price"] = (float(np.max(day.h[mask])) + 1.5) * V.PIP
            elif letter in ("W", "ISHS"):
                o["price"] = (float(np.min(day.l[mask])) - 1.5) * V.PIP
            o["repair_method"] = "edge_from_bars"
            o["fails"] = revalidate(rec, o, day)
    o["status"] = ("ok" if not o["fails"] and o["repair_method"] == "none"
                   else "repaired" if not o["fails"] else "unusable")
    if o["fails"] and o["repair_method"] == "none":
        o["repair_method"] = "unusable"
    elif o["fails"]:
        o["repair_method"] += "+fail"
    return o


def repair_generic(rec, d, r, f, day, marks):
    """BAR_MARKER, SQUEEZE, fragments and the rest: normalise only."""
    o = base_v2(d, r)
    for k in ("price", "price0", "price1"):
        if r.get(k) is not None:
            o[k] = r[k]
    if o["price"] is None and o["text_price"] is not None:
        o["price"] = o["text_price"]
        o["repair_method"] = "text_price"
    if o["spec_type"] is None:
        o["status"] = "fragment"
    else:
        o["fails"] = revalidate(rec, o, day)
        o["status"] = "ok" if not o["fails"] else "unusable"
    return o


REPAIRERS = {
    "PATTERN_LINE": repair_line, "CONTEXT_LINE": repair_line,
    "BOX": repair_box, "CONTEXT_RANGE": repair_box, "RANGE_OPEN": repair_box,
    "LEVEL_CARRIED": repair_level, "MINI_LEVEL": repair_level,
    "BRACKET": repair_bracket,
}


# ------------------------------------------------------------------ #
# driver
# ------------------------------------------------------------------ #

def match_objects(dobjs, robjs):
    """Pair draft and refined objects; same length expected, index-aligned."""
    if len(dobjs) == len(robjs):
        return list(zip(dobjs, robjs))
    pairs, used = [], set()
    for d in dobjs:
        best, bd = None, 1e9
        for i, r in enumerate(robjs):
            if i in used or r.get("spec_type") != d.get("spec_type"):
                continue
            dt = abs((_hhmm(r.get("t0")) or -9999) - (_hhmm(d.get("t0"))
                                                     or -9999))
            if dt < bd:
                best, bd = i, dt
        if best is not None:
            used.add(best)
            pairs.append((d, robjs[best]))
        else:
            pairs.append((d, {}))
    return pairs


def process(split):
    s, e = V.SPLITS[split]
    draft = {r["id"]: r for r in (json.loads(l) for l in
                                  open(os.path.join(DRAFT,
                                       "BOOK2012_draft.jsonl"),
                                       encoding="utf8"))}
    ref = {r["id"]: r for r in (json.loads(l) for l in
                                open(os.path.join(HERE,
                                     "BOOK2012_%s.jsonl" % split),
                                     encoding="utf8"))}
    days = V.load_days(s, e)
    stats = collections.Counter()
    out_recs, log = [], []
    for pid, dr in sorted(draft.items(),
                          key=lambda kv: (kv[1]["date"], kv[1]["panel"])):
        rr = ref.get(pid)
        if rr is None:
            continue
        day = days.get(dr["date"])
        marks = []
        for m in dr.get("marks", []):
            marks.append({"kind": m.get("kind"), "letter": m.get("letter"),
                          "side": m.get("side"), "t": _hhmm(m.get("t"))})
        objs = []
        note_ord = {}
        for d, r in match_objects(dr.get("objects", []),
                                  rr.get("objects", [])):
            note = d.get("note") or r.get("raw_note") or ""
            oi = note_ord.get(note, 0)
            note_ord[note] = oi + 1
            clause = TF.clause_for(note, d, oi)
            d = dict(d); d["_clause"] = clause
            f = TF.parse(clause, d.get("spec_type"))
            if day is None or not len(day):
                o = base_v2(d, r)
                o["status"], o["repair_method"] = "unusable", "no_bars"
            else:
                otype = d.get("spec_type") or r.get("spec_type")
                fn = REPAIRERS.get(otype, repair_generic)
                o = fn(dr, d, r, f, day, marks)
            stats[(o["spec_type"], o["status"])] += 1
            stats[("method", o["repair_method"])] += 1
            objs.append(o)
        out_recs.append({
            "id": pid, "page": dr.get("page"), "panel": dr.get("panel"),
            "fig": dr.get("fig"), "date": dr["date"], "lesson": dr.get("lesson"),
            "bars_from": dr.get("bars_from"), "split": split,
            "window": {"x0": _hhmm(dr.get("x0")), "x1": _hhmm(dr.get("x1"))},
            "y_labels": dr.get("y_labels"),
            "schema": "BOOK2012_v2",
            "objects": objs, "marks": marks,
            "raw_drawn": dr.get("raw_drawn"), "raw_marks": dr.get("raw_marks"),
        })
    outp = os.path.join(DRAFT, "BOOK2012_%s_v2.jsonl" % split)
    with open(outp, "w", encoding="utf8") as fo:
        for rec in out_recs:
            fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("wrote %s (%d panels)" % (outp, len(out_recs)))
    print("%-18s %-12s %6s" % ("type", "status", "n"))
    for (t, st), n in sorted(stats.items(), key=lambda kv: (str(kv[0]),)):
        print("%-18s %-12s %6d" % (t, st, n))
    return out_recs


def main(argv):
    for split in (["TUNE", "HOLD"] if (argv and argv[0].upper() == "ALL")
                  else [argv[0].upper() if argv else "TUNE"]):
        print("=" * 66)
        print(split)
        process(split)


if __name__ == "__main__":
    main(sys.argv[1:])
