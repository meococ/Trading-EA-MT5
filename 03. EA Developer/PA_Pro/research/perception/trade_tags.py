"""trade_tags.py — R78 s.78.4(3) TASK TT: the Owner's rules as FACTS
on every object, never as filters.

Single source of truth for the rule predicates: moved verbatim out of
deepresearch/DR_RULES_measure.py (s_c1..s_c8, tol_e, jge, jle) and
boxlab/r73_edges.py (edge_defs, cluster_edge) — both files re-import
them from here, so in-engine tags are provably identical to the
research measures on the same inputs.  Leaf module: numpy only — the
engine must not import evalcheck/boxlab/golden at run time.

Tag map (R78 s.78.4(3); a tag = the rule FAILS, "tradeable" = no tag):
  BOX    daylight        C1@1.0    dist(ema[j1] -> [bot,top]) / abr > 1.0
         steep           C2@q95box |ema[j1]-ema[j1-10]|/(10*abr[j1]) > 0.195
         shock_inside    C3w@3.0   max range/abr on the build window >= 3.0
         impulse_inside  C4w@4     max <=6-bar same-direction run/abr >= 4
         lone_edge       not C6g   max(top-clu_hi, bot-clu_lo) > 5.0p —
                                   engine objects carry no label
                                   precision, so the ruler default
                                   (common.prec_sigmas fallback) = 5.0p
  LEVEL  steep           C2@q95lvl > 0.204
         zombie          C7f@2     full-history close side-switches > 2
         superseded      C8a@1     same-polarity pivot born after the
                                   anchor, beyond the price by >= 1*abr
  LINE   steep           C2@q95lin > 0.166
         zombie          C7s@2     drawn-span close side-switches > 2
TT-2 (R81 s.81.5(1), lifetime tags answering G-REVIEW R1 E1/E2):
  LINE   line_broken        >=2 consecutive closes beyond the line on
                            its non-defended side by > tol_e(abr)
         line_cuts_bodies   >=2 bars whose real body contains the
                            line value with > tol inside
  ALL    stale_far          dist(close, object) > 3*ABR20 AND last
                            touch (bar range within tol) > 24 bars
                            before t; distances: box -> band,
                            level -> price, line -> value at t
TT-3 (R83 s.83.2, the reviewer's "end the box at the breakout"):
  BOX    box_broken        entry-anchored break: j0 = first bar >=
                            t_left whose close is inside [bot-tol,
                            top+tol]; break on (j0,t] = 3 consecutive
                            closes beyond one edge, or one close >=
                            3*ABR beyond an edge.  Facts: exit_bar,
                            break_clause in {run3, shock}.
TRADE_VIEW_HIDE (R81): all tags above except lone_edge - it is a
fact but does NOT hide (author obeys C6 only 34%; hiding would strip
~99% of engine boxes).  tradeable(tags) = no hide-set tag.
Missing stats (None) never tag — same "cannot condemn" convention as
DR_RULES_report.  All inputs causal: only bars <= the current bar.
"""
import numpy as np

PIP = 1e4

# author-quantile C2 thresholds (R78 s.78.4(3) verbatim values;
# measured in deepresearch/DR_RULES_summary.json:
# box q95=0.19548, level q95=0.20447, line q95=0.16613).
C2_Q95 = {"box": 0.195, "level": 0.204, "line": 0.166}

# engine-side analog of DR_RULES C6g tol_g: objects have no label
# precision, so the ruler default (common.prec_sigmas fallback) = 5.0p.
LONE_EDGE_TOL_PIPS = 5.0

# R81 s.81.5(1): the trade-view hide set.  lone_edge stays a FACT but
# does not hide - the author obeys C6 only 34% of the time, and hiding
# on it would strip ~99% of engine boxes out of M2-TV.
TRADE_VIEW_HIDE = frozenset({
    "daylight", "steep", "shock_inside", "impulse_inside",
    "zombie", "superseded",
    "line_broken", "line_cuts_bodies", "stale_far",
    "box_broken"})


def tradeable(tags):
    """R81 s.81.5(1): tradeable = no tag in TRADE_VIEW_HIDE."""
    return not (set(tags) & TRADE_VIEW_HIDE)


# R81 s.81.5(1) fixed parameters (not tunable)
STALE_FAR_ABR = 3.0            # dist(close, object) > 3*ABR20
STALE_GAP_BARS = 24            # last touch more than 24 bars before t
LINE_BREAK_N = 2               # >=2 consecutive beyond-side closes
LINE_CUTS_N = 2                # >=2 body-cut bars
BOX_BREAK_RUN = 3              # >=3 consecutive closes beyond one edge
BOX_SHOCK_ABR = 3.0            # single close >= 3*ABR beyond an edge

RULE_FAMS = {"box": ("BOX", "RANGE_OPEN", "CONTEXT_RANGE"),
             "level": ("LEVEL_CARRIED", "MINI_LEVEL"),
             "line": ("PATTERN_LINE", "CONTEXT_LINE")}

_TYPE_FAM = {t: f for f, ts in RULE_FAMS.items() for t in ts}


# ------------------------------------------------------------------ #
# helpers (verbatim from DR_RULES_measure.py)
# ------------------------------------------------------------------ #

def to_min(v):
    """CET minute: accept int/float or 'HH:MM'."""
    if v is None:
        return None
    if isinstance(v, str):
        hh, mm = v.split(":")
        return int(hh) * 60 + int(mm)
    return int(v)


def jge(m, x):
    return min(int(np.searchsorted(m, x)), len(m) - 1)


def jle(m, x):
    """Last bar index with cet_min <= x (None if x before first bar)."""
    j = int(np.searchsorted(m, x, "right")) - 1
    return j if j >= 0 else None


def tol_e(a):
    return max(1.0, 0.25 * a)


# ------------------------------------------------------------------ #
# cluster edges (verbatim from boxlab/r73_edges.py — all segs pip-scale)
# ------------------------------------------------------------------ #

def edge_defs(h_seg, l_seg, o_seg, c_seg, tol):
    """Return dict side-> {defname: price}.  All segs pip-scale."""
    out = {}
    # --- top side ---
    hs = np.sort(h_seg)[::-1]                       # desc
    out["raw_hi"] = hs[0]
    drop = len(hs) > 1 and (hs[0] - hs[1]) > tol
    out["drop1_hi"] = hs[1] if drop else hs[0]
    # spec tail test: drop only when the extreme bar's offending tail
    # (h - max(o,c)) is > 50% of that bar's range (s3.1 FALSE_EXT)
    i_max = int(np.argmax(h_seg))
    rng = max(h_seg[i_max] - l_seg[i_max], 1e-9)
    tail = (h_seg[i_max] - max(o_seg[i_max], c_seg[i_max])) / rng
    out["drop1t_hi"] = hs[1] if (drop and tail > 0.5) else hs[0]
    out["clu_hi"] = cluster_edge(hs, tol, top=True)

    # --- bottom side ---
    ls = np.sort(l_seg)                             # asc
    out["raw_lo"] = ls[0]
    drop = len(ls) > 1 and (ls[1] - ls[0]) > tol
    out["drop1_lo"] = ls[1] if drop else ls[0]
    i_min = int(np.argmin(l_seg))
    rng = max(h_seg[i_min] - l_seg[i_min], 1e-9)
    tail = (min(o_seg[i_min], c_seg[i_min]) - l_seg[i_min]) / rng
    out["drop1t_lo"] = ls[1] if (drop and tail > 0.5) else ls[0]
    out["clu_lo"] = cluster_edge(ls, tol, top=False)
    return out


def cluster_edge(sorted_wicks, tol, top):
    """Most extreme price with >=2 wicks within tol of each other.
    sorted_wicks desc for top, asc for bottom."""
    n = len(sorted_wicks)
    best = None
    for i in range(n):
        p = sorted_wicks[i]
        cnt = 1
        j = i + 1
        while j < n and abs(sorted_wicks[j] - p) <= tol:
            cnt += 1
            j += 1
        if cnt >= 2:
            best = p          # first qualifying = most extreme (sorted)
            break
    return best if best is not None else sorted_wicks[0]


# ------------------------------------------------------------------ #
# rule statistics (verbatim from DR_RULES_measure.py; j indices into
# the fed-bar arrays)
# ------------------------------------------------------------------ #

def s_c1(lo, hi, j, ema, abr):
    """distance ema[j]->[lo,hi] in pips and ABR; +zone variant (band
    padded by edge tol for levels: the level's own zone)."""
    e = ema[j]
    d = 0.0 if lo <= e <= hi else min(abs(e - lo), abs(e - hi))
    dz = max(0.0, d - tol_e(abr[j]))          # band +- edge tol
    return {"c1_pip": d, "c1_abr": d / abr[j], "c1_abr_zone": dz / abr[j]}


def s_c2(j, ema, abr):
    if j < 10:
        return {"c2_s": None}
    return {"c2_s": abs(ema[j] - ema[j - 10]) / (10.0 * abr[j])}


def s_c3(j0, j1, h, l, abr):
    r = (h[j0:j1 + 1] - l[j0:j1 + 1]) / abr[j0:j1 + 1]
    return {"c3_r": float(np.max(r))}


def s_c4(j0, j1, o, c, abr):
    """max over same-direction (body-sign) contiguous windows of length
    <=6 of |c[b]-o[a]|/abr[b]."""
    best = 0.0
    n = j1 - j0 + 1
    if n <= 0:
        return {"c4_r": None}
    sg = np.sign(c[j0:j1 + 1] - o[j0:j1 + 1])
    i = 0
    while i < n:
        if sg[i] == 0:
            i += 1
            continue
        j2 = i
        while j2 + 1 < n and sg[j2 + 1] == sg[i]:
            j2 += 1
        # run = bars j0+i .. j0+j2 ; all contiguous windows len<=6
        for a in range(i, j2 + 1):
            for b in range(a, min(a + 6, j2 + 1)):
                net = abs(c[j0 + b] - o[j0 + a]) / abr[j0 + b]
                if net > best:
                    best = net
        i = j2 + 1
    return {"c4_r": best}


def s_c6(j0, j1, h, l, o, c, abr, top, bot):
    """cluster-edge distances; tol_e at span end (r73 convention)."""
    a = abr[j1]
    tol = tol_e(a)
    ed = edge_defs(h[j0:j1 + 1], l[j0:j1 + 1], o[j0:j1 + 1],
                   c[j0:j1 + 1], tol)
    dhi = abs(top - ed["clu_hi"])
    dlo = abs(bot - ed["clu_lo"])
    return {"c6_dhi": dhi, "c6_dlo": dlo, "c6_tol": tol,
            "c6_maxd": max(dhi, dlo)}


def s_c7(jb, j1, c, abr, price_at):
    """side switches of the close across price_at(j), beyond
    tol_j = max(1p, .25 abr).  state carried across in-band bars."""
    if jb is None or jb > j1:
        return {"c7_sw": None}
    sw = 0
    state = 0
    for j in range(jb, j1 + 1):
        d = c[j] - price_at(j)
        t = tol_e(abr[j])
        s = 1 if d > t else (-1 if d < -t else 0)
        if s and state and s != state:
            sw += 1
        if s:
            state = s
    return {"c7_sw": sw}


def s_c8(jb, j1, price, pol, pivots, abr):
    """max beyond-distance (ABR) of qualifying pivots; None = none.
    pol 'above' -> dir=+1 swing highs beyond price; 'below' -> dir=-1."""
    if jb is None:
        return {"c8_beyond_abr": None, "c8_npiv": None}
    want = 1 if pol == "above" else -1
    best = 0.0
    n = 0
    for p in pivots:
        if p.dir != want or p.t_ext <= jb or p.t_conf > j1:
            continue
        n += 1
        d = (p.price - price) if want == 1 else (price - p.price)
        if d > best:
            best = d
    if n == 0:
        return {"c8_beyond_abr": None, "c8_npiv": 0}
    return {"c8_beyond_abr": best / abr[j1], "c8_npiv": n}


# ------------------------------------------------------------------ #
# R81 s.81.5(1) TT-2 lifetime measures (fixed parameters; causal)
# ------------------------------------------------------------------ #

def s_line_broken(g, jb, j1, c, abr):
    """E1: >= LINE_BREAK_N consecutive closes beyond the line on its
    non-defended side by more than tol_e(abr).  Once true it stays
    true within [jb, j1] (scan is monotone in j1).  'top' lines are
    defended from above: the break side is below->above closes."""
    side = g.get("side")
    p0, slope, tb = g["p0"], g["slope"], g["t0"]
    run = 0
    for j in range(jb, j1 + 1):
        lv = p0 + slope * (j - tb)
        t = tol_e(abr[j])
        if side == "top":
            thru = c[j] > lv + t
        elif side == "bottom":
            thru = c[j] < lv - t
        else:                        # side unknown: either direction
            thru = abs(c[j] - lv) > t
        if thru:
            run += 1
            if run >= LINE_BREAK_N:
                return {"lbroken": True}
        else:
            run = 0
    return {"lbroken": False}


def s_line_cuts(g, j0, j1, o, c, abr):
    """E1: >= LINE_CUTS_N bars over [j0, j1] whose real body contains
    the line value with more than tol inside (deep cut, not a graze).
    j0 = the line's first anchor bar."""
    p0, slope, tb = g["p0"], g["slope"], g["t0"]
    n = 0
    for j in range(j0, j1 + 1):
        lv = p0 + slope * (j - tb)
        blo = min(o[j], c[j])
        bhi = max(o[j], c[j])
        t = tol_e(abr[j])
        if blo + t < lv < bhi - t:
            n += 1
            if n >= LINE_CUTS_N:
                return {"lcuts": True, "lcuts_n": n}
    return {"lcuts": False, "lcuts_n": n}


def s_stale_far(fam, g, jb, j1, h, l, c, abr):
    """E2: dist(close[j1] -> object) > STALE_FAR_ABR*abr[j1] AND the
    last touch (bar [l,h] within tol_e of the object) lies more than
    STALE_GAP_BARS before j1.  Distances: box = to band (0 inside),
    level = to price, line = to the line's value at the bar."""
    a = abr[j1]
    cc = c[j1]
    if fam == "box":
        lo, hi = g["bottom"], g["top"]
        dist = 0.0 if lo <= cc <= hi else min(abs(cc - lo),
                                              abs(cc - hi))
        val = None
    elif fam == "level":
        dist = abs(cc - g["price"])
        val = g["price"]
    else:                            # line: distance to value at j1
        dist = abs(cc - (g["p0"] + g["slope"] * (j1 - g["t0"])))
        val = None
    if dist <= STALE_FAR_ABR * a:
        return {"stale": False, "stale_dist_abr": dist / a}
    last = None
    for j in range(j1, -1, -1):
        t = tol_e(abr[j])
        if fam == "box":
            touched = l[j] <= hi + t and h[j] >= lo - t
        elif fam == "level":
            touched = l[j] <= val + t and h[j] >= val - t
        else:
            v = g["p0"] + g["slope"] * (j - g["t0"])
            touched = l[j] <= v + t and h[j] >= v - t
        if touched:
            last = j
            break
    gap = (j1 - last) if last is not None else \
        (j1 - jb if jb is not None else j1)
    return {"stale": gap > STALE_GAP_BARS,
            "stale_dist_abr": dist / a,
            "stale_gap": gap, "stale_last": last}


def s_box_broken(lo, hi, j_from, j1, c, abr):
    """R83 s.83.2 E5: entry-anchored box break.
    Entry bar j0 = first bar >= j_from (drawn left edge) whose close is
    INSIDE [lo-tol_e, hi+tol_e]; no such bar -> cannot fire (price
    arriving into the zone is not a breakout - the R82 error).
    Break on bars in (j0, j1]: (i) BOX_BREAK_RUN consecutive closes
    all > hi+tol or all < lo-tol; or (ii) one close beyond an edge by
    >= BOX_SHOCK_ABR*abr[j].  Sticky (monotone scan), causal.
    Returns bbroken/exit_bar/break_clause plus creep_n: closes beyond
    the same edge in (j0, j1] that never formed a run (Gemini b1)."""
    j0 = None
    for j in range(max(0, j_from), j1 + 1):
        t = tol_e(abr[j])
        if lo - t <= c[j] <= hi + t:
            j0 = j
            break
    if j0 is None:
        return {"bbroken": False, "entry": None, "creep_n": 0}
    run = sgn = 0
    n_up = n_dn = 0
    for j in range(j0 + 1, j1 + 1):
        t = tol_e(abr[j])
        if c[j] > hi + t:
            d, dist = 1, c[j] - hi
        elif c[j] < lo - t:
            d, dist = -1, lo - c[j]
        else:
            d = 0
        if not d:
            run = sgn = 0
            continue
        if d > 0:
            n_up += 1
        else:
            n_dn += 1
        if dist >= BOX_SHOCK_ABR * abr[j]:
            return {"bbroken": True, "exit_bar": j,
                    "break_clause": "shock", "entry": j0,
                    "creep_n": max(n_up, n_dn)}
        run = run + 1 if d == sgn else 1
        sgn = d
        if run >= BOX_BREAK_RUN:
            return {"bbroken": True, "exit_bar": j - BOX_BREAK_RUN + 1,
                    "break_clause": "run3", "entry": j0,
                    "creep_n": max(n_up, n_dn)}
    return {"bbroken": False, "entry": j0,
            "creep_n": max(n_up, n_dn)}


# ------------------------------------------------------------------ #
# per-object tag computation (engine-side; mirrors DR_RULES_measure's
# eng_stats index conventions so the stats match field-for-field)
# ------------------------------------------------------------------ #

def object_stats(ob, i, bars, ema, abr, pivots):
    """Continuous rule stats for one engine Obj at bar i (all arrays
    causal: bars[j] for j<=i).  Returns (fam, stats) — fam None when
    the object's type has no rules."""
    fam = _TYPE_FAM.get(ob.type)
    if fam is None:
        return None, {}
    g = ob.geometry
    if isinstance(bars, dict):          # pre-materialised np arrays
        m, o, h, l, c = (bars[k] for k in ("m", "o", "h", "l", "c"))
    else:
        m = np.array([b["cet_min"] for b in bars])
        o = np.array([b["o"] for b in bars])
        h = np.array([b["h"] for b in bars])
        l = np.array([b["l"] for b in bars])
        c = np.array([b["c"] for b in bars])
    ema = np.asarray(ema)
    abr = np.asarray(abr)
    nfed = i
    t1_src = g.get("t1_drawn") or \
        (ob.t_right if ob.t_right is not None else nfed)
    j1 = min(int(t1_src), nfed)
    j0 = min(int(ob.t_left), j1)
    jb = int(ob.t_birth) if ob.t_birth is not None else None
    if jb is not None:
        jb = min(jb, nfed)
    out = {"fam": fam, "type": ob.type, "state": ob.state,
           "t0m": int(m[j0]), "t1m": int(m[j1]), "j0": j0, "j1": j1,
           "width_bars": (m[j1] - m[j0]) / 5.0,
           "t_birth_m": (int(m[jb]) if jb is not None else None)}
    if fam == "box" and "top" in g:
        lo, hi = g["bottom"], g["top"]
        out.update(s_c1(lo, hi, j1, ema, abr))
        out.update(s_c3(j0, j1, h, l, abr))
        out.update(s_c4(j0, j1, o, c, abr))
        out.update(s_c6(j0, j1, h, l, o, c, abr, hi, lo))
        bs = g.get("meta_build_start", g.get("build_start"))
        be = g.get("meta_build_end", g.get("build_end",
                                           g.get("break_bar")))
        if bs is None:
            bs = j0                      # _eng_window: fallback drawn left
        if be is None:
            be = t1_src                  # _eng_window: fallback drawn right
        if bs is not None and be is not None:
            wa, wb = min(int(bs), nfed), min(int(be), nfed)
            if wa <= wb:
                out["c3_r_win"] = s_c3(wa, wb, h, l, abr)["c3_r"]
                out["c4_r_win"] = s_c4(wa, wb, o, c, abr)["c4_r"]
                out["width_win_bars"] = (m[wb] - m[wa]) / 5.0
        # R83 s.83.2 TT-3: entry-anchored break (E5 fix)
        out.update(s_box_broken(lo, hi, j0, j1, c, abr))
    elif fam == "level" and "price" in g:
        p = g["price"]
        out.update(s_c1(p, p, j1, ema, abr))
        out.update(s_c7(jb, j1, c, abr, lambda j: p))
        out["c7_sw_span"] = s_c7(j0, j1, c, abr, lambda j: p)["c7_sw"]
        out["c7_sw_full"] = s_c7(0, j1, c, abr, lambda j: p)["c7_sw"]
        pol = g.get("side")
        if pol not in ("above", "below"):
            pol = "above" if p >= c[jb] else "below"
        out["c8_pol"] = pol
        out.update(s_c8(jb, j1, p, pol, pivots, abr))
        # anchor variant: superseding extreme born after the drawn
        # left edge (the level's structural anchor), not after t_birth
        a = s_c8(j0, j1, p, pol, pivots, abr)
        out["c8_beyond_abr_anch"] = a["c8_beyond_abr"]
        out["c8_npiv_anch"] = a["c8_npiv"]
    if fam in ("box", "level", "line"):
        out.update(s_c2(j1, ema, abr))
    if fam == "line" and "p0" in g:
        p0, slope, tb = g["p0"], g["slope"], g["t0"]
        out.update(s_c7(jb, j1, c, abr, lambda j: p0 + slope * (j - tb)))
        out["c7_sw_span"] = s_c7(j0, j1, c, abr,
                                 lambda j: p0 + slope * (j - tb))["c7_sw"]
        out["c7_sw_full"] = s_c7(0, j1, c, abr,
                                 lambda j: p0 + slope * (j - tb))["c7_sw"]
        # R81 s.81.5(1) TT-2 lifetime measures (E1)
        if jb is not None:
            out.update(s_line_broken(g, jb, j1, c, abr))
        ja = min(g.get("meta_anchors") or [int(tb)])
        ja = max(0, min(ja, j1))
        out.update(s_line_cuts(g, ja, j1, o, c, abr))
    # R81 s.81.5(1) TT-2: stale_far for every rule family (E2)
    have_geom = (fam == "box" and "top" in g) or \
        (fam == "level" and "price" in g) or \
        (fam == "line" and "p0" in g)
    if have_geom:
        out.update(s_stale_far(fam, g, jb, j1, h, l, c, abr))
    return fam, out


def tags_from_stats(fam, st):
    """Continuous stats -> the tag set (R78 s.78.4(3)).  None stats
    never tag (cannot condemn, same as DR_RULES_report)."""
    tags = set()
    if fam == "box":
        v = st.get("c1_abr")
        if v is not None and v > 1.0:
            tags.add("daylight")
        v = st.get("c3_r_win")
        if v is not None and v >= 3.0:
            tags.add("shock_inside")
        v = st.get("c4_r_win")
        if v is not None and v >= 4:
            tags.add("impulse_inside")
        v = st.get("c6_maxd")
        if v is not None and v > LONE_EDGE_TOL_PIPS:
            tags.add("lone_edge")
        if st.get("bbroken"):                        # R83 s.83.2 E5
            tags.add("box_broken")
    if fam == "level":
        v = st.get("c7_sw_full")
        if v is not None and v > 2:
            tags.add("zombie")
        v = st.get("c8_beyond_abr_anch")
        if v is not None and v >= 1:
            tags.add("superseded")
    if fam == "line":
        v = st.get("c7_sw_span")
        if v is not None and v > 2:
            tags.add("zombie")
        if st.get("lbroken"):                       # R81 s.81.5(1) E1
            tags.add("line_broken")
        if st.get("lcuts"):                         # R81 s.81.5(1) E1
            tags.add("line_cuts_bodies")
    v = st.get("c2_s")
    if v is not None and v > C2_Q95[fam]:
        tags.add("steep")
    if st.get("stale"):                             # R81 s.81.5(1) E2
        tags.add("stale_far")
    return tags


def tags_for(ob, i, bars, ema, abr, pivots):
    """(tags, stats) for one live Obj at bar i — the engine entry
    point.  tags is a set; stats carries the continuous measures."""
    fam, st = object_stats(ob, i, bars, ema, abr, pivots)
    if fam is None:
        return set(), {}
    return tags_from_stats(fam, st), st
