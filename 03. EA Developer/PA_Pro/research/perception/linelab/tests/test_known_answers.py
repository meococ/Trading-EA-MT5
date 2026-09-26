"""Known-answer tests for the L3 anchor-first line proposer.

T1: a clean 3+ touch rising bottom line must be found.
T2: a line through a lone spike must NOT be drawn.

Run:  python -X utf8 tests/test_known_answers.py
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))   # linelab/
sys.path.insert(0, os.path.dirname(os.path.dirname(_HERE)))  # perception/

import lines_lab  # noqa: E402


def feed(e, bars):
    """bars are in pips; engine expects real prices (x1e-4)."""
    for j, (o, h, l, c) in enumerate(bars):
        e.update(1700000000 + j * 300, o * 1e-4, h * 1e-4, l * 1e-4,
                 c * 1e-4, cet_min=600 + j * 5)


def flat_bar(mid, i):
    """Body at `mid` pips with 1-pip wicks."""
    return (mid - 0.2, mid + 0.8, mid - 0.8, mid + 0.2)


def test_clean_three_touch_rising_line():
    """Lows stair-step up: 100 -> 106 -> 112 -> 118 -> 124 with a
    defended rising lower boundary.  The rising line under the leg lows
    must be born before the move ends."""
    bars = []
    px = 13000.0
    # 60-bar warm-up flat so ABR settles ~2-3 pips
    for i in range(60):
        bars.append(flat_bar(px, i))
    # rising leg: swing lows at 0/+8/+16/+24 bars of the leg, each ~+6p
    lows = [px, px + 6, px + 12, px + 18, px + 24]
    j = 0
    for k, lo in enumerate(lows):
        # dip to the low then recover -> defended touch
        for _ in range(4):
            bars.append(flat_bar(px + 6 * k + 8, j)); j += 1
        bars.append((px + 6 * k + 7, px + 6 * k + 9, lo, px + 6 * k + 6))
        j += 1
        for _ in range(3):
            bars.append(flat_bar(px + 6 * k + 8, j)); j += 1
    for _ in range(10):
        bars.append(flat_bar(px + 30, j)); j += 1
    e = lines_lab.LineLabEngine()
    feed(e, bars)
    lines = [o for o in e.objects if o.type == "PATTERN_LINE"
             and o.geometry["side"] == "bottom"
             and o.geometry["slope"] > 0]
    assert lines, "rising defended line under the leg lows not found"
    g = lines[0].geometry
    # expected slope ~ +6 pips / 8 bars = 0.75 pip/bar
    assert 0.3 < g["slope"] < 1.4, "slope off: %s" % g["slope"]
    print("T1 PASS: rising bottom line, slope %.2f p/bar, nt=%d"
          % (g["slope"], g["n_touches"]))


def test_lone_spike_no_line():
    """One huge isolated down-spike in a flat market must not anchor a
    line: lone_spike pivots are excluded and no second touch exists."""
    bars = []
    px = 13100.0
    for i in range(80):
        bars.append(flat_bar(px, i))
    # lone spike: range ~25 pips >> spike_abr_mult*ABR
    bars.append((px, px + 1, px - 25, px - 1))
    for i in range(40):
        bars.append(flat_bar(px, i + 80))
    e = lines_lab.LineLabEngine()
    feed(e, bars)
    lines = [o for o in e.objects if o.type == "PATTERN_LINE"]
    bad = [o for o in lines
           if abs(o.geometry["p0"] - (px - 25)) < 3 or
           abs(o.geometry["p0"] + o.geometry["slope"] *
               (80 - o.geometry["t0"]) - (px - 25)) < 3]
    assert not bad, "line anchored on the lone spike: %s" % bad
    print("T2 PASS: no line through the lone spike (drawn=%d)"
          % len(lines))


if __name__ == "__main__":
    test_clean_three_touch_rising_line()
    test_lone_spike_no_line()
    print("all known-answer tests passed")
