"""Known-answer tests for levels_lab (V4 prototype).

L1: a defended price (origin extreme + >=2 retests) MUST birth a level
    when price returns within approach distance.
L2: a lone extreme (no retests) must NOT birth.
L3: live budget — a stronger challenger evicts the weakest live level
    ('superseded'), keeping the pool at level_max_live.
L4: live budget — a weaker challenger is suppressed (no new ink).
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from levels_lab import LevelLabEngine  # noqa: E402


def feed(e, seq, start_min=500):
    """seq = list of (o,h,l,c) in PIPS; feed absolute."""
    for k, (o, h, l, c) in enumerate(seq):
        e.update(1700000000 + (start_min + 5 * k) * 60,
                 o / 1e4, h / 1e4, l / 1e4, c / 1e4,
                 cet_min=start_min + 5 * k)
    return e


def test_defended_origin_births_on_approach():
    e = LevelLabEngine()
    # origin low at 13000 (bar 0), leave, retest twice (bars 10,20),
    # then approach again at the end.
    seq = [(o, o + 2, o - 1, o + 1) for o in [13010] * 6]
    seq[1] = (13010, 13011, 13000, 13005)          # origin low 13000
    seq += [(o, o + 2, o - 1, o + 1) for o in [13030] * 8]
    seq[10] = (13030, 13030, 13000, 13020)         # retest 1
    seq += [(o, o + 2, o - 1, o + 1) for o in [13035] * 8]
    seq[20] = (13035, 13035, 13000, 13025)         # retest 2
    # drift down toward the level: ABR ~3p, approach within ~1.3 ABR
    seq += [(o, o + 2, o - 1, o + 1) for o in [13003] * 10]
    feed(e, seq)
    lv = [o for o in e.objects if o.state in ("ACTIVE", "CLOSED")]
    assert any(abs(o.geometry["price"] - 13000) <= 3.0 for o in lv), \
        "defended origin at 13000 should birth a level on approach"


def test_lone_extreme_never_births():
    e = LevelLabEngine()
    # single spike low at 13000, never retested, then approach
    seq = [(o, o + 2, o - 1, o + 1) for o in [13010] * 6]
    seq[1] = (13010, 13011, 13000, 13005)          # lone extreme
    seq += [(o, o + 2, o - 1, o + 1) for o in [13030] * 20]
    seq += [(o, o + 2, o - 1, o + 1) for o in [13003] * 10]
    feed(e, seq)
    lv = [o for o in e.objects
          if abs(o.geometry["price"] - 13000) <= 3.0]
    assert not lv, "lone extreme must not birth a level"


def _three_origin_seq(extra_gap_bars, c_retests):
    """Three defended pivot highs at 13012/13018/13024 while price
    hovers ~13000; then an approach tail at close ~13017 puts all three
    within approach_abr at once, forcing a budget decision."""
    flat = (13000, 13002, 12999, 13001)
    def sp(px):
        return (13000, px, 12999, 13001)
    seq = [flat] * 3
    seq.append(sp(13012))                      # A origin (bar 3)
    seq += [flat] * 3
    seq.append(sp(13012))                      # A retest 1 (bar 7)
    seq += [flat] * 3
    seq.append(sp(13012))                      # A retest 2 (bar 11)
    seq += [flat] * 3
    seq.append(sp(13018))                      # B origin (bar 15)
    seq += [flat] * 3
    seq.append(sp(13018))                      # B retest 1 (bar 19)
    seq += [flat] * 3
    seq.append(sp(13018))                      # B retest 2 (bar 23)
    seq += [flat] * 3
    seq.append(sp(13024))                      # C origin (bar 27)
    for k in range(c_retests):                 # C retests -> n_def
        seq += [flat] * 3
        seq.append(sp(13024))
    seq += [flat] * extra_gap_bars             # age + kill ret24
    seq += [(13016, 13018, 13015, 13017)] * 6  # approach: all in range
    return seq


def test_budget_stronger_challenger_evicts_weakest():
    e = LevelLabEngine(params={"level_max_live": 2, "mini_max_live": 1})
    feed(e, _three_origin_seq(extra_gap_bars=8, c_retests=3))
    lc = [o for o in e.objects if o.type == "LEVEL_CARRIED"]
    live = [o for o in lc if o.state == "ACTIVE"]
    assert len(live) <= 2, "budget must cap live levels at 2"
    a = [o for o in lc if abs(o.geometry["price"] - 13012) <= 1.5]
    assert a and any("superseded" in str(ev) for o in a
                     for ev in o.events), \
        "weakest live level must close as 'superseded'"
    prices = sorted(o.geometry["price"] for o in live)
    assert any(abs(p - 13024) <= 1.5 for p in prices), \
        "the stronger challenger (n_def=3) must win the slot"


def test_budget_weaker_challenger_suppressed():
    e = LevelLabEngine(params={"level_max_live": 2, "mini_max_live": 1})
    e.cand_log = []
    # C only reaches n_def=2 and its last touch is >24 bars before the
    # approach -> live_score below the weakest incumbent -> suppressed.
    feed(e, _three_origin_seq(extra_gap_bars=24, c_retests=2))
    lc = [o for o in e.objects if o.type == "LEVEL_CARRIED"]
    assert not any(abs(o.geometry["price"] - 13024) <= 1.5
                   for o in lc), \
        "weaker challenger must not birth (suppressed by budget)"
    assert any(c.get("outcome") == "suppressed_budget"
               for c in e.cand_log), \
        "suppression must be logged as suppressed_budget"
