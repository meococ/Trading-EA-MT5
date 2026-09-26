"""test_volman_setups.py — synthetic-Snapshot fixture tests for the
Q2' Volman setup drafts.  No real data, no outcomes — detector logic
only, per LEAD_RULINGS Review 1 (no census/screen/prereg pre-P-FREEZE).
"""

import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import volman_setups as vs   # noqa: E402

PIP = 0.0001
ABR = 5.0          # 5 pips


def mkbox(id=1, lo=1.1000, hi=1.1015, state="live", t_left=0,
          touches_hi=2, touches_lo=2, events=None, broken_edge=None):
    touches = ([{"edge": "hi", "t": i} for i in range(touches_hi)] +
               [{"edge": "lo", "t": i} for i in range(touches_lo)])
    return {"id": id, "type": "BOX", "lo": lo, "hi": hi, "t_birth": 0,
            "t_left": t_left, "t_right": None, "state": state,
            "role": None, "touches": touches, "events": events or [],
            "why": "test"}


def snap(t, o, h, l, c, ema=None, pressure="UP", objects=None,
         facts=None, abr=ABR):
    n = len(c)
    return {
        "t": t, "o": np.asarray(o, float), "h": np.asarray(h, float),
        "l": np.asarray(l, float), "c": np.asarray(c, float),
        "ema25": np.asarray(ema if ema is not None else c, float),
        "abr": abr, "pip": PIP, "utc_min": 600, "dow": 2,
        "pressure": {"state": pressure, "conf": 1.0},
        "objects": objects or [], "facts": facts or {},
    }


def flat_bars(n, px=1.1000, rng=0.0004):
    o = np.full(n, px); h = np.full(n, px + rng)
    l = np.full(n, px - rng); c = np.full(n, px)
    return o, h, l, c


# ---------------------------------------------------------------- PB

def test_pb_fires_on_proper_break():
    # box [1.1000, 1.1015]; buildup rests on the top edge, bar 9 closes beyond
    o, h, l, c = flat_bars(10)
    for j in range(5, 9):                       # buildup on the edge
        o[j] = 1.1012; c[j] = 1.1014; h[j] = 1.1015; l[j] = 1.1010
    o[9] = 1.1014; h[9] = 1.1030; l[9] = 1.1013; c[9] = 1.1028
    s = snap(9, o, h, l, c, pressure="UP",
             objects=[mkbox()], facts={})
    sig = vs.detect_pb(s)
    assert sig and sig["side"] == 1 and sig["order_px"] > h[9]
    assert sig["inv"] == 1.1000


def test_pb_vetoed_without_buildup():
    # far-away run at the edge: no bars resting on it -> not proper
    o, h, l, c = flat_bars(10)
    o[9] = 1.1000; h[9] = 1.1030; l[9] = 0.9998; c[9] = 1.1028
    s = snap(9, o, h, l, c, pressure="UP", objects=[mkbox()])
    assert vs.detect_pb(s) is None


def test_pb_vetoed_by_counter_pressure_and_room():
    o, h, l, c = flat_bars(10)
    for j in range(5, 9):
        o[j] = 1.1012; c[j] = 1.1014; h[j] = 1.1015; l[j] = 1.1010
    o[9] = 1.1014; h[9] = 1.1030; l[9] = 1.1013; c[9] = 1.1028
    # counter pressure
    s = snap(9, o, h, l, c, pressure="DOWN", objects=[mkbox()])
    assert vs.detect_pb(s) is None
    # obstacle 8 pips ahead -> room rule fails
    s = snap(9, o, h, l, c, pressure="UP", objects=[mkbox()],
             facts={"obstacles_up": [{"px": 1.1045, "kind": "carried",
                                      "dist_pips": 8.0}]})
    assert vs.detect_pb(s) is None


def test_pb_single_touch_breakout_edge_rejected():
    o, h, l, c = flat_bars(10)
    for j in range(5, 9):
        o[j] = 1.1012; c[j] = 1.1014; h[j] = 1.1015; l[j] = 1.1010
    o[9] = 1.1014; h[9] = 1.1030; l[9] = 1.1013; c[9] = 1.1028
    s = snap(9, o, h, l, c, pressure="UP",
             objects=[mkbox(touches_hi=1)])
    assert vs.detect_pb(s) is None


def test_pb_close_on_line_with_squeeze():
    # corrected rule: close ON the edge allowed when a squeeze fills
    # the last gap
    o, h, l, c = flat_bars(10)
    for j in range(5, 9):
        o[j] = 1.1012; c[j] = 1.1014; h[j] = 1.1015; l[j] = 1.1010
    o[9] = 1.1014; h[9] = 1.1020; l[9] = 1.1012; c[9] = 1.1015
    s = snap(9, o, h, l, c, pressure="UP", objects=[mkbox()],
             facts={"squeeze": {"obj_ids": [1, 2]}})
    sig = vs.detect_pb(s)
    assert sig and sig["side"] == 1
    # without the squeeze fact, a close merely ON the line is not a break
    s2 = snap(9, o, h, l, c, pressure="UP", objects=[mkbox()])
    assert vs.detect_pb(s2) is None


def test_pb_stand_aside_and_longbar_veto():
    o, h, l, c = flat_bars(10)
    for j in range(5, 9):
        o[j] = 1.1012; c[j] = 1.1014; h[j] = 1.1015; l[j] = 1.1010
    o[9] = 1.1014; h[9] = 1.1030; l[9] = 1.1013; c[9] = 1.1028
    s = snap(9, o, h, l, c, pressure="UP", objects=[mkbox()],
             facts={"stand_aside": ["news"]})
    assert vs.detect_pb(s) is None
    # an abnormal long bar just before the signal vetoes too
    o2, h2, l2, c2 = o.copy(), h.copy(), l.copy(), c.copy()
    h2[8] = 1.1035; l2[8] = 1.0995          # 40-pip bar >> 2*ABR
    s2 = snap(9, o2, h2, l2, c2, pressure="UP", objects=[mkbox()])
    assert vs.detect_pb(s2) is None


# ---------------------------------------------------------------- PBP

def test_pbp_fires_on_poke_and_close_back():
    # box broke up earlier; price returns to the extension, pokes below
    # and closes back above
    o, h, l, c = flat_bars(12, px=1.1030)
    o[11] = 1.1022; h[11] = 1.1032; l[11] = 1.1013; c[11] = 1.1028
    s = snap(11, o, h, l, c, pressure="UP",
             objects=[mkbox(state="broken")])
    sig = vs.detect_pbp(s)
    assert sig and sig["side"] == 1


def test_pbp_rejects_deep_reentry():
    # pullback closed back but dipped past the box mid -> failed-break
    # territory, not PBP
    o, h, l, c = flat_bars(12, px=1.1030)
    o[11] = 1.1022; h[11] = 1.1032; l[11] = 1.1006; c[11] = 1.1028
    s = snap(11, o, h, l, c, pressure="UP",
             objects=[mkbox(state="broken")])
    assert vs.detect_pbp(s) is None


def test_pbp_requires_broken_state_and_pressure():
    o, h, l, c = flat_bars(12, px=1.1030)
    o[11] = 1.1022; h[11] = 1.1032; l[11] = 1.1013; c[11] = 1.1028
    s = snap(11, o, h, l, c, pressure="UP",
             objects=[mkbox(state="live")])
    assert vs.detect_pbp(s) is None
    s = snap(11, o, h, l, c, pressure="DOWN",
             objects=[mkbox(state="broken")])
    assert vs.detect_pbp(s) is None


# ---------------------------------------------------------------- PBC

def test_pbc_fires_on_combi_at_box_edge():
    o, h, l, c = flat_bars(10, px=1.1010)
    # strong bull bar at the box top, then an inside bar
    o[8] = 1.1005; h[8] = 1.1020; l[8] = 1.1004; c[8] = 1.1018
    o[9] = 1.1018; h[9] = 1.1019; l[9] = 1.1010; c[9] = 1.1016
    s = snap(9, o, h, l, c, pressure="UP", objects=[mkbox()])
    sig = vs.detect_pbc(s)
    assert sig and sig["side"] == 1 and sig["order_px"] > h[9]


def test_pbc_needs_boundary_context():
    o, h, l, c = flat_bars(10, px=1.1010)
    o[8] = 1.1005; h[8] = 1.1020; l[8] = 1.1004; c[8] = 1.1018
    o[9] = 1.1018; h[9] = 1.1019; l[9] = 1.1010; c[9] = 1.1016
    s = snap(9, o, h, l, c, pressure="UP", objects=[])   # no boundary
    assert vs.detect_pbc(s) is None


def test_pbc_rejects_weak_strong_bar_and_opposite_low_half():
    o, h, l, c = flat_bars(10, px=1.1010)
    # strong bar too small
    o[8] = 1.1008; h[8] = 1.1011; l[8] = 1.1008; c[8] = 1.1010
    o[9] = 1.1010; h[9] = 1.10105; l[9] = 1.1009; c[9] = 1.1010
    s = snap(9, o, h, l, c, pressure="UP", objects=[mkbox()])
    assert vs.detect_pbc(s) is None
    # opposite-colour inside bar closing in the bottom half
    o2, h2, l2, c2 = flat_bars(10, px=1.1010)
    o2[8] = 1.1005; h2[8] = 1.1020; l2[8] = 1.1004; c2[8] = 1.1018
    o2[9] = 1.1018; h2[9] = 1.1019; l2[9] = 1.1010; c2[9] = 1.1011  # bear, low half
    s2 = snap(9, o2, h2, l2, c2, pressure="UP", objects=[mkbox()])
    assert vs.detect_pbc(s2) is None


# ---------------------------------------------------------------- PR

def test_pr_fires_after_ema_touch_on_trigger_line():
    # uptrend pullback: lows touched ema25 at bar 7; trigger = close
    # through a PATTERN_LINE drawn over the pullback highs
    n = 12
    o, h, l, c = flat_bars(n, px=1.1000)
    ema = np.full(n, 1.1005)
    for j in range(6, 9):                        # the dip to the ema
        l[j] = 1.1003
    o[11] = 1.1008; h[11] = 1.1016; l[11] = 1.1007; c[11] = 1.1015
    line = {"id": 7, "type": "PATTERN_LINE", "a": 0.0, "b": 1.1012,
            "t_birth": 4, "t_left": 4, "t_right": None,
            "state": "live", "role": "pullback", "touches": [],
            "events": [], "why": "test"}
    s = snap(11, o, h, l, c, ema=ema, pressure="UP", objects=[line])
    sig = vs.detect_pr(s)
    assert sig and sig["side"] == 1


def test_pr_needs_ema_touch():
    n = 12
    o, h, l, c = flat_bars(n, px=1.1000)
    ema = np.full(n, 1.0990)                     # pullback never reached it
    o[11] = 1.1008; h[11] = 1.1016; l[11] = 1.1007; c[11] = 1.1015
    s = snap(11, o, h, l, c, ema=ema, pressure="UP")
    assert vs.detect_pr(s) is None


def test_pr_second_break_trigger_without_line():
    n = 12
    o, h, l, c = flat_bars(n, px=1.1000)
    ema = np.full(n, 1.1005)
    for j in range(6, 9):
        l[j] = 1.1003
    # no trigger object -> fallback: close above max of previous 2 highs
    o[11] = 1.1009; h[11] = 1.1016; l[11] = 1.1008; c[11] = 1.1014
    s = snap(11, o, h, l, c, ema=ema, pressure="UP")
    sig = vs.detect_pr(s)
    assert sig and sig["side"] == 1 and sig["inv"] < 1.1003


# ---------------------------------------------------------------- TFF

def test_tff_fires_on_failed_counter_break():
    # box broke DOWN against UP pressure at bar 7 (a bear trap);
    # bar 11 is a strong bull bar whose high reclaims the barrier (lo)
    n = 12
    o, h, l, c = flat_bars(n, px=1.1000)
    o[7] = 1.1002; h[7] = 1.1004; l[7] = 1.0986; c[7] = 1.0988   # counter-break
    o[11] = 1.0994; h[11] = 1.1008; l[11] = 1.0992; c[11] = 1.1006
    box = mkbox(lo=1.0998, hi=1.1014, state="broken",
                events=[{"kind": "break", "t": 7, "side": -1}])
    s = snap(11, o, h, l, c, pressure="UP", objects=[box])
    sig = vs.detect_tff(s)
    assert sig and sig["side"] == 1 and sig["order_px"] > h[11]
    assert sig["inv"] < 1.0986


def test_tff_vetoed_until_reclaim():
    # signal bar's HIGH still below the barrier -> no trade (p201 veto)
    n = 12
    o, h, l, c = flat_bars(n, px=1.1000)
    o[7] = 1.1002; h[7] = 1.1004; l[7] = 1.0986; c[7] = 1.0988
    o[11] = 1.0986; h[11] = 1.0995; l[11] = 1.0984; c[11] = 1.0993
    box = mkbox(lo=1.0998, hi=1.1014, state="broken",
                events=[{"kind": "break", "t": 7, "side": -1}])
    s = snap(11, o, h, l, c, pressure="UP", objects=[box])
    assert vs.detect_tff(s) is None


def test_tff_vetoed_when_counter_break_held():
    # a second close beyond the barrier -> break is holding, not failing
    n = 12
    o, h, l, c = flat_bars(n, px=1.1000)
    o[7] = 1.1002; h[7] = 1.1004; l[7] = 1.0986; c[7] = 1.0988
    o[9] = 1.0987; h[9] = 1.0989; l[9] = 1.0982; c[9] = 1.0984   # held below
    o[11] = 1.0994; h[11] = 1.1008; l[11] = 1.0992; c[11] = 1.1006
    box = mkbox(lo=1.0998, hi=1.1014, state="broken",
                events=[{"kind": "break", "t": 7, "side": -1}])
    s = snap(11, o, h, l, c, pressure="UP", objects=[box])
    assert vs.detect_tff(s) is None


def test_tff_needs_strong_reversal_bar():
    n = 12
    o, h, l, c = flat_bars(n, px=1.1000)
    o[7] = 1.1002; h[7] = 1.1004; l[7] = 1.0986; c[7] = 1.0988
    o[11] = 1.0999; h[11] = 1.10005; l[11] = 1.0999; c[11] = 1.10003  # tiny bar
    box = mkbox(lo=1.0998, hi=1.1014, state="broken",
                events=[{"kind": "break", "t": 7, "side": -1}])
    s = snap(11, o, h, l, c, pressure="UP", objects=[box])
    assert vs.detect_tff(s) is None


def test_tff_mirror_short():
    # up-break against DOWN pressure fails; strong bear bar reclaims
    n = 12
    o, h, l, c = flat_bars(n, px=1.1000)
    o[7] = 1.0998; h[7] = 1.1014; l[7] = 1.0996; c[7] = 1.1012   # counter up-break
    o[11] = 1.1006; h[11] = 1.1008; l[11] = 1.0992; c[11] = 1.0994
    box = mkbox(lo=1.0986, hi=1.1002, state="broken",
                events=[{"kind": "break", "t": 7, "side": 1}])
    s = snap(11, o, h, l, c, pressure="DOWN", objects=[box])
    sig = vs.detect_tff(s)
    assert sig and sig["side"] == -1 and sig["order_px"] < l[11]


# ------------------------------------------------------------------
# causality: mutating bars AFTER t must not change the decision

def _extend(s, extra=8):
    """Return a copy of snap with `extra` random bars appended after t;
    detector output at bar t must be identical."""
    rng = np.random.default_rng(7)
    e = {}
    for k in ("o", "h", "l", "c", "ema25"):
        tail = s[k][-1] + rng.normal(0, 0.0005, extra)
        e[k] = np.concatenate([s[k], tail])
    s2 = dict(s)
    s2.update(e)
    return s2


def test_causality_pb_future_bars():
    o, h, l, c = flat_bars(10)
    for j in range(5, 9):
        o[j] = 1.1012; c[j] = 1.1014; h[j] = 1.1015; l[j] = 1.1010
    o[9] = 1.1014; h[9] = 1.1030; l[9] = 1.1013; c[9] = 1.1028
    s = snap(9, o, h, l, c, pressure="UP", objects=[mkbox()])
    base = vs.detect_pb(s)
    fut = vs.detect_pb(_extend(s))
    assert base == fut


def test_causality_tff_future_bars():
    n = 12
    o, h, l, c = flat_bars(n, px=1.1000)
    o[7] = 1.1002; h[7] = 1.1004; l[7] = 1.0986; c[7] = 1.0988
    o[11] = 1.0994; h[11] = 1.1008; l[11] = 1.0992; c[11] = 1.1006
    box = mkbox(lo=1.0998, hi=1.1014, state="broken",
                events=[{"kind": "break", "t": 7, "side": -1}])
    s = snap(11, o, h, l, c, pressure="UP", objects=[box])
    base = vs.detect_tff(s)
    fut = vs.detect_tff(_extend(s))
    assert base == fut and base is not None
