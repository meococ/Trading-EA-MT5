"""validate — semantic validation of every golden object (Ruling 2 §2.1a).

The golden set is our yardstick, so it must be right before anything is
scored against it.  A low pixel-fit residual proves only that the refiner
found *a* straight segment; it does not prove it found *the* object the
author describes.  This module therefore checks each object against the two
independent sources of truth we actually have:

1. **the catalogue text** — the author's statement of intent: slope, side,
   anchors, prices (parsed by `textfeat`);
2. **the real EURUSD M5 bars of that date** — Volman drew on these exact
   bars, so a line "under the lows" must touch lows, and a box's edges must
   be touched by bars and contain them.

Checks are graded:
- **HARD** — a failure means the geometry contradicts the source; the object
  must be repaired or marked unusable.  Never keep it as it stands.
- **SOFT** — informative, reported but not disqualifying (the catalogue is
  eyeballed to +/-5 pips / +/-10 min, so some looseness is expected).

Tolerances come from spec §6.1 and the catalogue's own precision flags:
a `[meas]` coordinate is good to 1-2 pips, an eyeballed one to ~5 pips.

Usage:  python validate.py TUNE|HOLD|ALL [--json out.jsonl]

No outcome or referee module is imported anywhere in this path (Addendum 4).
"""

import collections
import datetime as dt
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "..")):
    _p = os.path.abspath(_p)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import book_loader                                          # noqa: E402
import textfeat as TF                                       # noqa: E402

PIP = 1e-4
DRAFT = os.path.join(HERE, "draft")

# --- tolerances (pips) -------------------------------------------------- #
TOUCH_TOL = 1.5      # a bar extreme "touches" a line/level
CONTAIN_TOL = 2.0    # slack when testing that bars sit inside a box
TEXT_TOL = {"meas": 2.0, "eye": 5.0}   # catalogue price precision, spec 6.1
ANCHOR_BARS = 2      # "from the ~15:45 high" may be off by +/-2 bars
WINDOW_SLACK = 60    # minutes a note may reference outside the axis labels
MIN_TOUCHES = 2      # "under the lows" needs at least two lows on it

SPLITS = {"TUNE": ("2012-03-01", "2012-06-01"),
          "HOLD": ("2012-06-01", "2012-09-01")}


# ------------------------------------------------------------------ #
# bars
# ------------------------------------------------------------------ #

class Day:
    """One CET day of M5 bars, addressable by CET minute-of-day."""

    __slots__ = ("m", "o", "h", "l", "c")

    def __init__(self, m, o, h, l, c):
        self.m, self.o, self.h, self.l, self.c = m, o, h, l, c

    def __len__(self):
        return len(self.m)

    def idx(self, cet_min, tol_bars=0):
        """Index of the bar at this CET minute, else the nearest within
        tol_bars * 5 minutes, else None."""
        if not len(self.m):
            return None
        j = int(np.argmin(np.abs(self.m - cet_min)))
        if abs(int(self.m[j]) - cet_min) <= max(0, tol_bars) * 5 + 2:
            return j
        return None

    def span(self, m0, m1):
        """Boolean mask of bars with m0 <= cet_min <= m1 (order-safe)."""
        if m0 is None or m1 is None:
            return np.zeros(len(self.m), dtype=bool)
        lo, hi = (m0, m1) if m0 <= m1 else (m1, m0)
        return (self.m >= lo) & (self.m <= hi)


def load_days(start, end):
    """All BOOK M5 bars in [start, end) grouped by CET date string."""
    b = book_loader.load_m5(start + " 00:00", end + " 00:00")
    dates = np.array([dt.datetime.utcfromtimestamp(int(e)).date().isoformat()
                      for e in b["cet"]])
    out = {}
    for d in np.unique(dates):
        k = dates == d
        out[str(d)] = Day(b["cet_min"][k].astype(np.int64),
                          b["o"][k] / PIP, b["h"][k] / PIP,
                          b["l"][k] / PIP, b["c"][k] / PIP)
    return out


# ------------------------------------------------------------------ #
# geometry helpers (all prices in pips)
# ------------------------------------------------------------------ #

def obj_times(o):
    """(t0, t1) as CET minutes; tolerates the legacy 'HH:MM' strings."""
    def cv(v):
        if v is None:
            return None
        if isinstance(v, str):
            if ":" not in v:
                return None
            h, m = v.split(":")[:2]
            return int(h) * 60 + int(m)
        return int(v)
    return cv(o.get("t0")), cv(o.get("t1"))


def line_pts(o):
    """(p0, p1) endpoint prices in pips, or (None, None)."""
    p0, p1 = o.get("price0"), o.get("price1")
    if p0 is None or p1 is None:
        return None, None
    return p0 / PIP, p1 / PIP


def line_at(o, t):
    """Line price (pips) at CET minute t, linearly from its endpoints."""
    t0, t1 = obj_times(o)
    p0, p1 = line_pts(o)
    if None in (t0, t1, p0, p1) or t1 == t0:
        return None
    return p0 + (p1 - p0) * (t - t0) / (t1 - t0)


def box_edges(o):
    """(lo, hi) in pips from refined price_lo/price_hi, else catalogue
    price/price2, else (None, None)."""
    lo, hi = o.get("price_lo"), o.get("price_hi")
    if lo is None or hi is None:
        a, b = o.get("price"), o.get("price2")
        if a is None or b is None:
            return None, None
        lo, hi = min(a, b), max(a, b)
    return min(lo, hi) / PIP, max(lo, hi) / PIP


def cat_box_edges(o):
    """Catalogue (text) box edges in pips, or (None, None)."""
    a, b = o.get("price"), o.get("price2")
    if a is None or b is None:
        return None, None
    return min(a, b) / PIP, max(a, b) / PIP


def text_tol(o):
    return TEXT_TOL.get(o.get("prec"), 5.0)


# ------------------------------------------------------------------ #
# checks
# ------------------------------------------------------------------ #

class Result:
    """Check results for one object."""

    def __init__(self, panel, idx, otype):
        self.panel, self.idx, self.otype = panel, idx, otype
        self.checks = []          # (code, grade, ok, detail)

    def add(self, code, grade, ok, detail=""):
        self.checks.append((code, grade, bool(ok), detail))

    @property
    def hard_fails(self):
        return [c for c in self.checks if c[1] == "HARD" and not c[2]]

    @property
    def ok(self):
        return not self.hard_fails

    def to_dict(self):
        return {"panel": self.panel, "idx": self.idx, "type": self.otype,
                "ok": self.ok,
                "fails": [c[0] for c in self.hard_fails],
                "checks": [{"code": c[0], "grade": c[1], "ok": c[2],
                            "detail": c[3]} for c in self.checks]}


def check_window(res, rec, o, f):
    """Times must lie inside the panel's visible window (axis labels give
    the labelled range; the drawing extends a little past it)."""
    t0, t1 = obj_times(o)
    w0, w1 = obj_times({"t0": rec.get("x0"), "t1": rec.get("x1")})
    if w0 is None or w1 is None:
        return
    for name, t in (("t0", t0), ("t1", t1)):
        if t is None:
            continue
        if not (w0 - WINDOW_SLACK <= t <= w1 + WINDOW_SLACK):
            res.add("TIME_WINDOW", "HARD", False,
                    "%s=%d outside panel [%d,%d]+/-%d"
                    % (name, t, w0, w1, WINDOW_SLACK))
            return
    res.add("TIME_WINDOW", "HARD", True)


_STYLE_OK = {
    "dotted": {"CONTEXT_LINE", "CONTEXT_RANGE"},
    "long_dashed": {"LEVEL_CARRIED", "MINI_LEVEL", "RANGE_OPEN"},
}


def check_style(res, rec, o, f):
    """Style implies type: dotted => CONTEXT_*, long-dashed => a carried
    level (spec §2)."""
    st, ty = o.get("style"), o["spec_type"]
    allow = _STYLE_OK.get(st)
    if allow is None:
        return
    res.add("TYPE_STYLE", "SOFT", ty in allow,
            "style=%s type=%s" % (st, ty))


def check_line(res, rec, o, f, day):
    t0, t1 = obj_times(o)
    p0, p1 = line_pts(o)
    if None in (t0, t1, p0, p1):
        res.add("HAS_GEOM", "HARD", False, "missing endpoint(s)")
        return
    res.add("HAS_GEOM", "HARD", True)
    d_pips = p1 - p0

    # --- slope sign/magnitude vs the text
    if f["slope_bounds"]:
        lo, hi = f["slope_bounds"]
        ok = ((lo is None or d_pips >= lo) and (hi is None or d_pips <= hi))
        res.add("SLOPE_TEXT", "HARD", ok,
                "text=%s bounds=%s refined=%+.1fp" % (f["slope"],
                                                      f["slope_bounds"],
                                                      d_pips))
    elif f["flag"]:
        want = TF.flag_expected_slope(f["flag"])
        ok = (d_pips > 0) if want == "up" else (d_pips < 0)
        res.add("SLOPE_FLAG", "SOFT", ok,
                "%s-flag expects %s, refined=%+.1fp" % (f["flag"], want,
                                                        d_pips))

    # --- side: the line must actually rest on the extremes it names
    mask = day.span(t0, t1)
    n = int(mask.sum())
    if f["side"] and n >= 3:
        ts = day.m[mask]
        vals = np.array([line_at(o, int(t)) for t in ts], dtype=float)
        if f["side"] == "under":
            ext, beyond = day.l[mask], day.c[mask]
            touches = int((np.abs(ext - vals) <= TOUCH_TOL).sum())
            n_beyond = int((beyond < vals - TOUCH_TOL).sum())
        else:
            ext, beyond = day.h[mask], day.c[mask]
            touches = int((np.abs(ext - vals) <= TOUCH_TOL).sum())
            n_beyond = int((beyond > vals + TOUCH_TOL).sum())
        res.add("SIDE_TOUCH", "HARD", touches >= MIN_TOUCHES,
                "side=%s touches=%d/%d bars" % (f["side"], touches, n))
        allowed = max(1, int(0.10 * n))
        if not (f["broken"] or f["pierced"] or f["teased"]):
            res.add("SIDE_CLOSES", "SOFT", n_beyond <= allowed,
                    "%d closes beyond (allow %d), text says nothing broken"
                    % (n_beyond, allowed))

    # --- explicit anchors: "from the ~15:45 high" — the line must pass
    # within tol of that bar's extreme, allowing the text's +-2 bar
    # slack by measuring per-bar distance (a fast line is far from the
    # named extreme even 5 minutes later).  A compound note names anchors
    # belonging to sibling objects — only anchors at this line's own
    # endpoints apply ("a rising line from the ~08:35 low and a falling
    # line from the ~09:30 high": each leg owns one).
    anch = f["anchors"]
    own = [(tm, kind) for (tm, kind) in anch
           if t0 is not None and abs(tm - t0) <= 15
           or t1 is not None and abs(tm - t1) <= 15]
    if own:
        anch = own
    for (tm, kind) in anch:
        j = day.idx(tm, ANCHOR_BARS)
        if j is None:
            continue
        lo = max(0, j - ANCHOR_BARS)
        hi = min(len(day), j + ANCHOR_BARS + 1)
        best = None
        for jj in range(lo, hi):
            v = line_at(o, int(day.m[jj]))
            if v is None:
                continue
            if kind == "high":
                d = abs(day.h[jj] - v)
            elif kind == "low":
                d = abs(day.l[jj] - v)
            else:
                d = min(abs(day.h[jj] - v), abs(day.l[jj] - v))
            if best is None or d < best:
                best = d
        if best is None:
            continue
        res.add("ANCHOR", "HARD", best <= max(TOUCH_TOL, 2.0),
                "anchor %02d:%02d %s nearest bar gap=%.1fp"
                % (tm // 60, tm % 60, kind or "?", best))


def check_box(res, rec, o, f, day):
    t0, t1 = obj_times(o)
    lo, hi = box_edges(o)
    if lo is None or t0 is None:
        res.add("HAS_GEOM", "HARD", False, "missing edge(s) or t0")
        return
    if t1 is None:
        res.add("HAS_GEOM", "SOFT", False, "no right edge (t1)")
        t1 = t0 + 60
    else:
        res.add("HAS_GEOM", "HARD", True)

    # --- catalogue prices must survive refinement
    clo, chi = cat_box_edges(o)
    if clo is not None:
        tol = text_tol(o)
        d = max(abs(clo - lo), abs(chi - hi))
        res.add("PRICE_TEXT", "HARD", d <= tol,
                "text=%.1f-%.1f refined=%.1f-%.1f worst=%.1fp tol=%.1f"
                % (clo, chi, lo, hi, d, tol))

    mask = day.span(t0, t1)
    n = int(mask.sum())
    if n < 3:
        res.add("SPAN_BARS", "HARD", False, "only %d bars in span" % n)
        return
    res.add("SPAN_BARS", "HARD", True, "%d bars" % n)

    # --- stated height, when the text measures one ("(~22 pips)")
    sp = o.get("text_span_pips") or o.get("span_pips")
    if sp:
        h = hi - lo
        res.add("HEIGHT_TEXT", "HARD", abs(h - sp) <= max(3.0, 0.25 * sp),
                "text~%gp box=%.1fp" % (sp, h))

    # --- both edges must be touched by bars.  A text-named spike edge
    # ("bottom = the 10:25 spike low") is a lone print by definition:
    # one touch suffices there.
    nt = int((np.abs(day.h[mask] - hi) <= TOUCH_TOL).sum())
    nb = int((np.abs(day.l[mask] - lo) <= TOUCH_TOL).sum())
    need_t = 1 if (o.get("pin_hi")
                   or (o.get("pin_lo") and o.get("text_span_pips"))) \
        else MIN_TOUCHES
    need_b = 1 if (o.get("pin_lo")
                   or (o.get("pin_hi") and o.get("text_span_pips"))) \
        else MIN_TOUCHES
    res.add("EDGE_TOUCH_TOP", "HARD", nt >= need_t,
            "%d highs on top edge (need %d)" % (nt, need_t))
    res.add("EDGE_TOUCH_BOT", "HARD", nb >= need_b,
            "%d lows on bottom edge (need %d)" % (nb, need_b))

    # --- the box must contain the bars of its buildup; the drawn right
    # edge is how long it was DRAWN, not how long it held (D9).  The
    # buildup ends at the first close decisively beyond an edge.
    idxs = np.where(mask)[0]
    be = o.get("build_end") or t1
    bs = o.get("build_start") or t0
    # containment is judged over the buildup window [bs, be] only —
    # bars drawn after the break are outside the box's era (D9)
    cidx = idxs[(day.m[idxs] >= bs) & (day.m[idxs] <= be)]
    beyond = [j for j in cidx
              if day.c[j] > hi + TOUCH_TOL or day.c[j] < lo - TOUCH_TOL]
    if beyond:
        cut = max(int(np.where(cidx == beyond[0])[0][0]),
                  int(0.25 * len(cidx)), 3)
        cidx = cidx[:cut]
    # a buildup bar is "outside" only if it CLOSES beyond the edge;
    # wicks that poke and close back inside are teases, not escapes
    out = np.mean((day.c[cidx] > hi + TOUCH_TOL)
                  | (day.c[cidx] < lo - TOUCH_TOL))
    inside = 1.0 - out
    res.add("CONTAIN", "HARD", inside >= 0.80,
            "%.0f%% of %d buildup bars closed inside (broke at %s)"
            % (100 * inside, len(cidx),
               "%02d:%02d" % (day.m[beyond[0]] // 60, day.m[beyond[0]] % 60)
               if beyond else "never"))

    # --- pokes should coincide with a T/F mark
    poke_t = []
    for j in np.where(mask)[0]:
        if day.h[j] > hi + TOUCH_TOL or day.l[j] < lo - TOUCH_TOL:
            poke_t.append(int(day.m[j]))
    marks = [m for m in rec.get("marks", [])
             if m.get("kind") == "LABEL_TF" and m.get("t") is not None]
    mt = [int(m["t"]) if not isinstance(m["t"], str)
          else obj_times({"t0": m["t"]})[0] for m in marks]
    mt = [x for x in mt if x is not None]
    unmarked = [t for t in poke_t
                if not any(abs(t - x) <= 5 * ANCHOR_BARS for x in mt)]
    res.add("POKE_MARKS", "SOFT", len(unmarked) <= max(1, int(0.1 * n)),
            "%d poking bars, %d without a T/F mark" % (len(poke_t),
                                                       len(unmarked)))


def check_level(res, rec, o, f, day):
    t0, t1 = obj_times(o)
    p = o.get("price")
    if p is None or t0 is None:
        res.add("HAS_GEOM", "HARD", False,
                "missing price" if p is None else "missing t0")
        return
    res.add("HAS_GEOM", "HARD", True)
    p = p / PIP

    # --- anchored to the extreme the text names
    src = None
    for (a, b) in f["spans"]:
        if (a, b) != (t0, t1):
            src = (a, b)
            break
    if src is None and f["anchors"]:
        tm = f["anchors"][0][0]
        src = (tm - 10, tm + 10)
    ref = f["level_ref"]
    if src and ref:
        mask = day.span(*src)
        if int(mask.sum()) >= 1:
            got = (float(np.max(day.h[mask])) if ref == "high"
                   else float(np.min(day.l[mask])))
            res.add("LEVEL_ANCHOR", "HARD",
                    abs(got - p) <= max(text_tol(o), TOUCH_TOL),
                    "%s of %02d:%02d-%02d:%02d = %.1f, level %.1f, d=%.1fp"
                    % (ref, src[0] // 60, src[0] % 60, src[1] // 60,
                       src[1] % 60, got, p, p - got))

    # --- catalogue price must survive refinement
    for cp in f["prices"]:
        cp = cp / PIP
        if abs(cp - p) <= 20:      # same level, not another number in note
            res.add("PRICE_TEXT", "HARD", abs(cp - p) <= text_tol(o),
                    "text=%.1f refined=%.1f d=%.1fp" % (cp, p, p - cp))
            break

    # --- a drawn level should be tested by price somewhere in its span
    mask = day.span(t0, t1 if t1 is not None else t0 + 60)
    if int(mask.sum()) >= 2:
        near = int(((day.l[mask] - TOUCH_TOL <= p) &
                    (day.h[mask] + TOUCH_TOL >= p)).sum())
        res.add("LEVEL_TESTED", "SOFT", near >= 1,
                "%d bars reach the level in its span" % near)


def check_bracket(res, rec, o, f, day):
    t0, t1 = obj_times(o)
    if t0 is None or t1 is None:
        res.add("HAS_GEOM", "HARD", False, "missing span")
        return
    res.add("HAS_GEOM", "HARD", True)
    letter = (o.get("letter") or "").upper()
    res.add("LETTER", "SOFT", letter in ("M", "W", "SHS", "ISHS", "V"),
            "letter=%r" % letter)
    p = o.get("price")
    if p is None:
        return
    p = p / PIP
    mask = day.span(t0, t1)
    if int(mask.sum()) < 2:
        return
    top, bot = float(np.max(day.h[mask])), float(np.min(day.l[mask]))
    if letter.startswith("M") or letter == "SHS":
        res.add("BRACKET_SIDE", "HARD", p >= top - 2 * text_tol(o),
                "M/SHS must sit at/above the formation top %.1f, got %.1f"
                % (top, p))
    elif letter.startswith("W") or letter == "ISHS":
        res.add("BRACKET_SIDE", "HARD", p <= bot + 2 * text_tol(o),
                "W must sit at/below the formation low %.1f, got %.1f"
                % (bot, p))


def check_marks(rec, day, out):
    """T/F letters: on the correct side, and the bar really pokes."""
    boxes = [o for o in rec.get("objects", [])
             if o["spec_type"] in ("BOX", "CONTEXT_RANGE", "RANGE_OPEN")]
    for i, m in enumerate(rec.get("marks", [])):
        if m.get("kind") != "LABEL_TF":
            continue
        res = Result(rec["id"], "mark%d" % i, "LABEL_TF")
        t = m.get("t")
        t = obj_times({"t0": t})[0] if isinstance(t, str) else t
        if t is None:
            res.add("HAS_GEOM", "HARD", False, "no time")
            out.append(res)
            continue
        res.add("HAS_GEOM", "HARD", True)
        j = day.idx(int(t), ANCHOR_BARS)
        if j is None:
            res.add("MARK_BAR", "HARD", False, "no bar at %d" % t)
            out.append(res)
            continue
        side = m.get("side")
        owner = None
        for b in boxes:
            b0, b1 = obj_times(b)
            if b0 is None:
                continue
            if b0 - 10 <= t <= (b1 if b1 is not None else b0 + 120) + 10:
                owner = b
                break
        if owner is not None:
            lo, hi = box_edges(owner)
            if lo is not None:
                if side == "above":
                    res.add("MARK_POKE", "SOFT",
                            day.h[j] >= hi - TOUCH_TOL,
                            "high %.1f vs top %.1f" % (day.h[j], hi))
                elif side == "below":
                    res.add("MARK_POKE", "SOFT",
                            day.l[j] <= lo + TOUCH_TOL,
                            "low %.1f vs bottom %.1f" % (day.l[j], lo))
        else:
            res.add("MARK_OWNER", "SOFT", False, "no box spans this mark")
        out.append(res)


CHECKERS = {
    "PATTERN_LINE": check_line,
    "CONTEXT_LINE": check_line,
    "BOX": check_box,
    "CONTEXT_RANGE": check_box,
    "RANGE_OPEN": check_box,
    "LEVEL_CARRIED": check_level,
    "MINI_LEVEL": check_level,
    "BRACKET": check_bracket,
}


# ------------------------------------------------------------------ #
# driver
# ------------------------------------------------------------------ #

def validate_records(recs, days):
    out = []
    for rec in recs:
        day = days.get(rec["date"])
        if day is None or not len(day):
            for i, o in enumerate(rec.get("objects", [])):
                r = Result(rec["id"], i, o["spec_type"])
                r.add("BARS", "HARD", False, "no bars for %s" % rec["date"])
                out.append(r)
            continue
        for i, o in enumerate(rec.get("objects", [])):
            res = Result(rec["id"], i, o["spec_type"])
            f = TF.parse(o.get("clause") or o.get("raw_note") or "",
                         o["spec_type"])
            check_window(res, rec, o, f)
            check_style(res, rec, o, f)
            fn = CHECKERS.get(o["spec_type"])
            if fn is None:
                res.add("NO_CHECKER", "SOFT", True, o["spec_type"])
            else:
                fn(res, rec, o, f, day)
            out.append(res)
        check_marks(rec, day, out)
    return out


def summarise(results):
    by_type = collections.defaultdict(lambda: [0, 0])
    codes = collections.Counter()
    for r in results:
        s = by_type[r.otype]
        s[0] += 1
        s[1] += 1 if r.ok else 0
        for c, g, ok, _ in r.checks:
            if g == "HARD" and not ok:
                codes[c] += 1
    return by_type, codes


def main(argv):
    split = (argv[0] if argv else "TUNE").upper()
    names = ["TUNE", "HOLD"] if split == "ALL" else [split]
    allres = []
    for nm in names:
        s, e = SPLITS[nm]
        path = os.path.join(HERE, "BOOK2012_%s.jsonl" % nm)
        recs = [json.loads(l) for l in open(path, encoding="utf8")]
        days = load_days(s, e)
        res = validate_records(recs, days)
        allres += res
        by_type, codes = summarise(res)
        print("=" * 66)
        print("%s: %d panels, %d objects+marks checked" % (nm, len(recs),
                                                           len(res)))
        print("%-16s %6s %6s %7s" % ("type", "n", "pass", "pass%"))
        tn = tp = 0
        for t, (n, p) in sorted(by_type.items(), key=lambda kv: -kv[1][0]):
            print("%-16s %6d %6d %6.0f%%" % (t, n, p, 100.0 * p / n))
            tn += n
            tp += p
        print("%-16s %6d %6d %6.0f%%" % ("TOTAL", tn, tp,
                                          100.0 * tp / max(tn, 1)))
        print("\nhard failures by check:")
        for c, k in codes.most_common():
            print("  %-16s %4d" % (c, k))
        outp = os.path.join(DRAFT, "validate_%s.jsonl" % nm)
        with open(outp, "w", encoding="utf8") as fo:
            for r in res:
                fo.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
        print("\nwrote %s" % outp)
    return allres


if __name__ == "__main__":
    main(sys.argv[1:])
