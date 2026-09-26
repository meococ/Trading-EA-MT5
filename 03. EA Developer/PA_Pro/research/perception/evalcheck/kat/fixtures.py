"""fixtures.py — hand-built bar fixtures with known right answers.

Each fixture is a dict:
    name      fixture id
    t,m,o,h,l,c   M5 series (t epoch s, m cet minutes, prices in PIPS)
    expected  list of golden-shaped objects (the right answer)
    negatives list of deliberately-wrong engine records that the ruler
              MUST NOT match (ruler test)

Bars are plain 5-minute bars starting 00:00.  Prices in pips
(13300 = 1.3300).  run_engine() divides by PIP back to raw units, so
fixtures are written in the same units golden uses / PIP.
"""
import numpy as np

BASE = 13300.0            # pips
STEP = 5                  # minutes per bar


def _series(n, o=None, h=None, l=None, c=None):
    m = np.arange(n) * STEP
    t = (m * 60 + 1700000000).astype(np.int64)   # arbitrary epoch base
    o = np.asarray(o if o is not None else np.full(n, BASE + 7.0))
    h = np.asarray(h if h is not None else o + 2.0)
    l = np.asarray(l if l is not None else o - 2.0)
    c = np.asarray(c if c is not None else o)
    h = np.maximum.reduce([h, o, c])
    l = np.minimum.reduce([l, o, c])
    return t.astype(np.int64), m.astype(np.int64), o, h, l, c


def _box(t0, t1, lo, hi, bs=None, be=None, **kw):
    d = {"spec_type": "BOX", "t0": t0, "t1": t1, "price_lo": lo * 1e-4,
         "price_hi": hi * 1e-4, "prec": "meas", "status": "ok"}
    d["build_start"], d["build_end"] = bs if bs is not None else t0, \
        be if be is not None else t1
    d.update(kw)
    return d


def _mark(t, side, letter):
    return {"kind": "LABEL_TF", "t": t, "side": side, "letter": letter}


# ------------------------------------------------------------------ #
# 1. clean_box — 3 touches per edge, then a proper break
# ------------------------------------------------------------------ #
def clean_box():
    n = 100
    o = np.full(n, BASE + 7.0)
    h = o + 1.0
    l = o - 1.0
    c = o.copy()
    for i in range(10, 75):                  # oscillate inside the box
        ph = i % 12
        if ph < 6:
            c[i] = BASE + 15.0 if ph == 0 else BASE + 11.0
            h[i] = BASE + 15.0
            l[i] = BASE + 8.0
            o[i] = BASE + 8.0
        else:
            c[i] = BASE if ph == 6 else BASE + 4.0
            l[i] = BASE + 0.0
            h[i] = BASE + 7.0
            o[i] = BASE + 7.0
    for i in range(78, n):                   # break out, hold above
        o[i] = BASE + 20.0
        h[i] = BASE + 24.0
        l[i] = BASE + 17.0
        c[i] = BASE + 22.0
    exp = [_box(50, 370, BASE, BASE + 15.0, bs=50, be=370)]
    neg = [_box(50, 370, BASE, BASE + 28.0, bs=50, be=370),  # edge off
           _box(400, 460, BASE, BASE + 15.0, bs=400, be=460)]  # late span
    return dict(name="clean_box", series=_series(n, o, h, l, c),
                expected=exp, negatives=neg)


# ------------------------------------------------------------------ #
# 2. spike_poke — lone spike must NOT become a box edge
# ------------------------------------------------------------------ #
def spike_poke():
    n = 80
    o = np.full(n, BASE + 4.0)
    h = o + 1.5
    l = o - 1.5
    c = o.copy()
    for i in range(8, 60, 9):                # 3+ touches each edge
        h[i] = BASE + 8.0
        c[i] = BASE + 7.0
    for i in range(12, 60, 9):
        l[i] = BASE + 0.0
        c[i] = BASE + 1.0
    i = 40                                    # lone poke to +40
    h[i] = BASE + 40.0
    c[i] = BASE + 4.0                          # closes back inside
    o[i] = BASE + 5.0
    exp = [_box(40, 295, BASE, BASE + 8.0, bs=40, be=295)]
    neg = [_box(40, 295, BASE, BASE + 40.0, bs=40, be=295)]   # spike edge
    return dict(name="spike_poke", series=_series(n, o, h, l, c),
                expected=exp, negatives=neg)


# ------------------------------------------------------------------ #
# 3. false_break — close beyond edge then close back -> 'F' mark
# ------------------------------------------------------------------ #
def false_break():
    n = 90
    o = np.full(n, BASE + 7.0)
    h = o + 1.0
    l = o - 1.0
    c = o.copy()
    for i in range(10, 55):
        ph = i % 10
        if ph < 5:
            h[i], l[i], c[i] = BASE + 15.0, BASE + 9.0, BASE + 14.0
        else:
            h[i], l[i], c[i] = BASE + 8.0, BASE + 0.0, BASE + 1.0
    h[58] = BASE + 19.0                        # poke beyond edge
    c[58] = BASE + 17.0                        # closes above edge
    o[58] = BASE + 14.0
    c[61] = BASE + 10.0                        # close back inside
    o[61] = BASE + 14.0
    h[61] = BASE + 15.0
    l[61] = BASE + 8.0
    exp = [_box(50, 290, BASE, BASE + 15.0, bs=50, be=270)]
    marks = [_mark(300, "above", "F")]         # close-back bar ~60*5
    neg = [_box(50, 290, BASE + 5.0, BASE + 15.0, bs=50, be=270)]
    neg_marks = [_mark(300, "below", "F"), _mark(450, "above", "F")]
    return dict(name="false_break", series=_series(n, o, h, l, c),
                expected=exp, expected_marks=marks,
                negatives=neg, neg_marks=neg_marks)


# ------------------------------------------------------------------ #
# 4. proper_break — buildup then sustained break (no F)
# ------------------------------------------------------------------ #
def proper_break():
    n = 90
    o = np.full(n, BASE + 7.0)
    h = o + 1.0
    l = o - 1.0
    c = o.copy()
    for i in range(10, 55):
        ph = i % 10
        if ph < 5:
            h[i], l[i], c[i] = BASE + 15.0, BASE + 9.0, BASE + 14.0
        else:
            h[i], l[i], c[i] = BASE + 8.0, BASE + 0.0, BASE + 1.0
    for i in range(56, n):                     # decisive break + hold
        o[i] = BASE + 18.0
        h[i] = BASE + 23.0
        l[i] = BASE + 16.0
        c[i] = BASE + 21.0
    exp = [_box(50, 275, BASE, BASE + 15.0, bs=50, be=270)]
    neg = [_box(50, 275, BASE + 4.0, BASE + 15.0, bs=50, be=270)]
    return dict(name="proper_break", series=_series(n, o, h, l, c),
                expected=exp, negatives=neg)


# ------------------------------------------------------------------ #
# 5. upline3 — three-touch rising support line
# ------------------------------------------------------------------ #
def upline3():
    n = 80
    slope = 0.3                                # pips per bar
    o = np.full(n, BASE + 30.0)
    h = o + 2.0
    l = o - 2.0
    c = o.copy()
    for i in range(n):
        base = BASE + 10.0 + slope * i
        o[i] = base + 4.0
        c[i] = base + 4.0
        h[i] = base + 7.0
        l[i] = base + 3.0
    for i in (15, 35, 55):                     # exact touches on line
        l[i] = BASE + 10.0 + slope * i
        c[i] = BASE + 12.0 + slope * i
    p0 = BASE + 10.0 + slope * 15
    p1 = BASE + 10.0 + slope * 55
    exp = [{"spec_type": "PATTERN_LINE", "t0": 15 * STEP, "t1": 55 * STEP,
            "price0": p0 * 1e-4, "price1": p1 * 1e-4, "dir": "up",
            "prec": "meas", "status": "ok"}]
    neg = [{"spec_type": "PATTERN_LINE", "t0": 15 * STEP, "t1": 55 * STEP,
            "price0": (p0 + 8.0) * 1e-4, "price1": (p1 - 8.0) * 1e-4,
            "dir": "up", "prec": "meas", "status": "ok"}]
    return dict(name="upline3", series=_series(n, o, h, l, c),
                expected=exp, negatives=neg)


# ------------------------------------------------------------------ #
# 6. m_bracket — M-shaped double top
# ------------------------------------------------------------------ #
def m_bracket():
    n = 70
    o = np.full(n, BASE + 10.0)
    h = o + 2.0
    l = o - 2.0
    c = o.copy()
    # leg up, dip, second top at same price, drop
    path = [(10, BASE + 30.0), (25, BASE + 14.0), (40, BASE + 30.0),
            (55, BASE + 12.0)]
    prev = BASE + 10.0
    pi = 8
    for tgt_i, tgt_p in path:
        for i in range(pi, tgt_i + 1):
            f = (i - pi) / max(tgt_i - pi, 1)
            mid = prev + (tgt_p - prev) * f
            o[i], c[i] = mid - 1.5, mid
            h[i], l[i] = mid + 1.5, mid - 3.0
        prev, pi = tgt_p, tgt_i
    exp = [{"spec_type": "BRACKET", "t0": 10 * STEP, "t1": 55 * STEP,
            "letter": "M", "price": (BASE + 30.0) * 1e-4,
            "prec": "eye", "status": "ok"}]
    neg = [{"spec_type": "BRACKET", "t0": 10 * STEP, "t1": 55 * STEP,
            "letter": "W", "prec": "eye", "status": "ok"}]
    return dict(name="m_bracket", series=_series(n, o, h, l, c),
                expected=exp, negatives=neg)


# ------------------------------------------------------------------ #
# 7. carried_level — broken box edge holds on pullback
# ------------------------------------------------------------------ #
def carried_level():
    n = 110
    o = np.full(n, BASE + 7.0)
    h = o + 1.0
    l = o - 1.0
    c = o.copy()
    for i in range(10, 45):
        ph = i % 10
        if ph < 5:
            h[i], l[i], c[i] = BASE + 15.0, BASE + 9.0, BASE + 14.0
        else:
            h[i], l[i], c[i] = BASE + 8.0, BASE + 0.0, BASE + 1.0
    for i in range(46, 75):                    # break up, run
        o[i] = BASE + 24.0
        h[i] = BASE + 28.0
        l[i] = BASE + 20.0
        c[i] = BASE + 26.0
    for i in range(75, 88):                    # pullback to old edge
        o[i] = BASE + 22.0
        l[i] = BASE + 14.0
        h[i] = BASE + 24.0
        c[i] = BASE + 18.0
    for i in range(88, n):                     # edge holds, resume up
        o[i] = BASE + 20.0
        h[i] = BASE + 27.0
        l[i] = BASE + 16.5
        c[i] = BASE + 25.0
    exp = [{"spec_type": "LEVEL_CARRIED", "t0": 46 * STEP, "t1": 88 * STEP,
            "price": (BASE + 15.0) * 1e-4, "side": "above",
            "prec": "meas", "status": "ok"}]
    neg = [{"spec_type": "LEVEL_CARRIED", "t0": 46 * STEP,
            "t1": 88 * STEP, "price": (BASE + 24.0) * 1e-4,
            "prec": "meas", "status": "ok"}]
    return dict(name="carried_level", series=_series(n, o, h, l, c),
                expected=exp, negatives=neg)


FIXTURES = [clean_box, spike_poke, false_break, proper_break,
            upline3, m_bracket, carried_level]
