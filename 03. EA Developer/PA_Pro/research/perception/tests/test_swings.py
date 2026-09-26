"""test_swings.py — DN_SWING theory fixtures for the DC detector.

Fixtures (e)-(i) from design/DN_SWING §7: exact zigzag, lone spike,
prefix invariance, determinism, and the strict-subset hierarchy.
Prices in pips (bars carry absolute prices; detector works in the
same units it is fed — here pips for readability).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from swings import DCStream, SwingBook  # noqa: E402

THETA = 4.0        # micro threshold (pips)
PMIN = 2.0         # persistence floor
PSTRUCT = 10.0     # structural floor (~theta2)


def zigzag(points, wick=0.5):
    """Build bars whose closes hit each turning point in order,
    small symmetric wicks.  points = [(n_bars_in_leg, price), ...]."""
    bars = []
    px = points[0][1]
    for n, tgt in points[1:]:
        for k in range(1, n + 1):
            p = px + (tgt - px) * k / n
            bars.append((p + wick, p - wick))
        px = tgt
    return bars


def run(bars, theta_fn=None, spike_fn=None):
    dc = DCStream(theta_fn or (lambda i: THETA), spike_fn)
    book = SwingBook(PMIN, PSTRUCT)
    emitted = []
    for i, (hi, lo) in enumerate(bars):
        for p in dc.update(i, hi, lo):
            emitted.append(book.add(p))
    return emitted, book


def test_zigzag_confirms_each_extreme():
    """(e) a clean zigzag: pivots confirm at the right extremes."""
    # up 100->120 (20 bars), down to 108, up to 122, down to 110,
    # trailing leg up to 116 so the 110 low confirms (the final
    # stream-end extreme stays unconfirmed — correct DC semantics)
    bars = zigzag([(20, 100.0), (20, 120.0), (12, 108.0),
                   (14, 122.0), (12, 110.0), (8, 116.0)])
    em, book = run(bars)
    highs = [p for p in em if p.dir == 1]
    lows = [p for p in em if p.dir == -1]
    assert len(highs) == 2 and len(lows) == 2
    assert abs(highs[0].price - (120.0 + 0.5)) < 1e-9
    assert abs(lows[0].price - (108.0 - 0.5)) < 1e-9
    assert abs(highs[1].price - (122.0 + 0.5)) < 1e-9
    assert abs(lows[1].price - (110.0 - 0.5)) < 1e-9
    # confirmation lags positive and bounded by the leg length
    for p in em:
        assert p.t_conf > p.t_ext


def test_no_pivots_in_flat_drift():
    """(e cont.) a monotonic drift with <theta wiggles emits nothing."""
    bars = []
    px = 100.0
    for k in range(60):
        px += 0.5                      # drift up 0.5/bar, dips of 2 < theta
        dip = 2.0 if k % 7 == 3 else 0.0
        bars.append((px + 0.4, px - 0.4 - dip))
    em, book = run(bars)
    assert em == []


def test_lone_spike_flag_and_retrace_gate():
    """(f) a spike wick with shallow retrace emits nothing; deep
    retrace emits a flagged pivot."""
    base = [(p + 0.5, p - 0.5) for p in [100 + k * 0.5 for k in range(20)]]
    # spike bar: huge upper wick, 2-pip lower wick; follow-ups dip
    # only 1 pip below it (total retrace 3 < theta=4 -> no confirm)
    spike_i = len(base)
    bars = base + [(130.0, 128.0)] + [(129.0, 127.0)] * 3
    em, _ = run(bars, spike_fn=lambda i: i == spike_i)
    assert em == []
    # deep retrace after the spike -> flagged pivot at the spike bar
    bars2 = base + [(130.0, 128.0)] + [(128.0, 125.0)] * 3
    em2, _ = run(bars2, spike_fn=lambda i: i == spike_i)
    assert len(em2) == 1
    assert em2[0].lone_spike and em2[0].t_ext == spike_i


def test_prefix_invariance():
    """(g) pivot set on bars[0:n] identical for all n >= t_conf."""
    bars = zigzag([(10, 100.0), (16, 118.0), (10, 106.0),
                   (14, 120.0), (10, 108.0), (8, 116.0)])
    full, _ = run(bars)
    for n in range(len(bars)):
        pref, _ = run(bars[:n])
        expect = [p for p in full if p.t_conf < n]
        got = [(p.t_ext, p.price, p.dir) for p in pref]
        want = [(p.t_ext, p.price, p.dir) for p in expect]
        assert got == want


def test_determinism():
    """(h) two runs produce identical pivot tuples."""
    bars = zigzag([(10, 100.0), (15, 115.0), (10, 104.0), (15, 118.0)])
    a, _ = run(bars)
    b, _ = run(bars)
    sig = lambda ps: [(p.t_ext, p.t_conf, p.price, p.dir, p.prom) for p in ps]
    assert sig(a) == sig(b)


def test_structural_subset_and_prominence():
    """(i) structural set is a strict subset; micro-valleys prune."""
    # big legs (16 pips) alternating with shallow 3-pip wiggles that
    # still retrace theta?  Use theta=1.0 so wiggles emit, then the
    # 2-pip prom floor + 10-pip structural floor split them.
    dc = DCStream(lambda i: 1.0)
    book = SwingBook(pmin=2.0, pstruct=10.0)
    # leg up 100->116 (16 bars), shallow dip to 114.5 (prom ~1.5),
    # continue to 122, deep dip to 104 (prom ~18), up to 120
    bars = zigzag([(16, 100.0), (16, 116.0), (4, 114.5), (8, 122.0),
                   (16, 104.0), (14, 120.0)], wick=0.3)
    emitted = []
    for i, (hi, lo) in enumerate(bars):
        for p in dc.update(i, hi, lo):
            emitted.append(book.add(p))
    alive = book.alive()
    structural = book.structural()
    ids = lambda ps: {id(p) for p in ps}
    assert ids(structural) <= ids(alive) <= ids(emitted)
    # the shallow 1.5-pip valley pivot must not survive pmin
    assert all(p.prom >= 2.0 for p in alive)
    # deep valley + highs survive structurally; shallow ones don't
    assert all(p.prom >= 10.0 for p in structural)
    assert len(structural) < len(emitted)
