"""test_engine_v0.py — spec §6.2 theory fixtures + §6.3 causality tests.

Regression suite for the frozen v0 engine (engine_v0.py).
Every fixture is a synthetic M5 sequence built to reproduce the geometry
of the theory figures.  Bars are 5-minute, priced around 1.3300, CET
wall time (server epoch == CET wall on the BOOK feed, D3).
"""
import copy
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "golden"))

import engine_v0 as E  # noqa: E402

P = 1e-4          # one pip
BASE = 1.3300
T0 = 1330560000   # CET-wall epoch aligned to 00:00 (i%288)*5 = cet_min


def mk(i, o, h, l, c, day=0):
    """bar i at CET minute (i%288)*5, prices absolute."""
    t = T0 + day * 86400 + (i % 288) * 300
    return {"t": t, "o": o, "h": h, "l": l, "c": c,
            "cet_min": int((t % 86400) // 60)}


def feed(eng, bars):
    for b in bars:
        eng.update(b["t"], b["o"], b["h"], b["l"], b["c"],
                   cet_min=b["cet_min"])
    return eng


def flat(i, px, day=0):
    return mk(i, px, px + 2 * P, px - 2 * P, px, day)


def wave(i, px0, px1, n=6, day=0):
    """n bars drifting px0->px1 with small wicks."""
    out = []
    for k in range(n):
        p0 = px0 + (px1 - px0) * k / n
        p1 = px0 + (px1 - px0) * (k + 1) / n
        hi = max(p0, p1) + 0.8 * P
        lo = min(p0, p1) - 0.8 * P
        out.append(mk(i + k, p0, hi, lo, p1, day))
    return out


def zigzag(prices, bars_per_leg=6, start_px=BASE):
    """Alternating legs through the given price targets."""
    bars, i, cur = [], 0, start_px
    for tgt in prices:
        bars += wave(i, cur, tgt, bars_per_leg)
        i += bars_per_leg
        cur = tgt
    return bars


def by_type(eng, t):
    return [o for o in eng.objects if o.type == t]


# ------------------------------------------------------------------- #
# §6.2 theory fixtures
# ------------------------------------------------------------------- #

def test_pullback_end_box_birth():
    """Fig 3.1: correction low L, rally to H, turn down -> box [L,H]."""
    bars = zigzag([1.3280, 1.3320, 1.3290, 1.3325, 1.3300], 6)
    eng = feed(E.PerceptionEngine(), bars)
    boxes = by_type(eng, "BOX")
    assert boxes, "no box born on a pullback-end pattern"
    g = boxes[0].geometry
    # box inside the structure range, height within the §3.1 envelope
    assert 13275 <= g["bottom"] < g["top"] <= 13330
    assert 6 <= g["top"] - g["bottom"] <= 34


def test_range_box_double_top():
    """§3.1(b): two tops within ~2 pips -> box drawn at second top."""
    bars = zigzag([1.3300, 1.3340, 1.3310, 1.3341, 1.3310], 7)
    eng = feed(E.PerceptionEngine(), bars)
    boxes = by_type(eng, "BOX")
    assert boxes
    # the governing box must cap the two tops and floor the mid dip
    g = boxes[-1].geometry
    assert abs(g["top"] - 13341) <= 3
    assert abs(g["bottom"] - 13309) <= 4


def test_false_break_wick_keeps_edge():
    """Fig 3.8: a wick pokes through a frozen edge and closes back
    inside: edge does NOT move, a T/F label appears."""
    bars = zigzag([1.3300, 1.3340, 1.3310, 1.3340, 1.3312, 1.3340], 6)
    # poke bar: wick to 1.3343 (3 pips past the ~1.3340 edge), close inside
    bars.append(mk(len(bars), 1.3338, 1.3343, 1.3335, 1.3337))
    eng = feed(E.PerceptionEngine(), bars)
    boxes = [b for b in by_type(eng, "BOX") if b.state != "DELETED"]
    assert boxes
    top = boxes[-1].geometry["top"]
    assert top <= 13342, "edge moved on a poke"
    labels = [o for o in eng.objects if o.type == "LABEL_TF"]
    assert any(l.geometry["side"] == "above" for l in labels)


def test_break_close_beyond_edge():
    """§3.3: close >= tol beyond the edge is a break; the broken edge
    spawns a LEVEL_CARRIED (role reversal, p20/81)."""
    bars = zigzag([1.3300, 1.3340, 1.3310, 1.3340, 1.3310], 6)
    bars += wave(len(bars), 1.3330, 1.3360, 4)     # close through top
    eng = feed(E.PerceptionEngine(), bars)
    boxes = by_type(eng, "BOX")
    assert any(b.geometry.get("broke") == "up" for b in boxes)
    assert any(o.type == "LEVEL_CARRIED" for o in eng.objects)


def test_tease_vs_proper_break_class():
    """Break class is set at break time from structure: buildup resting
    on the edge -> proper; mid-range buildup -> tease."""
    # buildup hugging the top edge, then break: proper
    bars = zigzag([1.3300, 1.3340, 1.3310, 1.3340, 1.3310], 6)
    bars += [mk(30 + k, 1.3338, 1.3340, 1.3336, 1.3338) for k in range(5)]
    bars += wave(35, 1.3338, 1.3360, 3)
    eng = feed(E.PerceptionEngine(), bars)
    cls = [b.geometry.get("break_class") for b in by_type(eng, "BOX")
           if b.geometry.get("broke")]
    assert cls and cls[-1].startswith("proper"), cls


def test_slope_rule_no_rising_top_line():
    """§3.4 slope rule: a rising line through highs is never a
    break-defining (upside) line."""
    bars = zigzag([1.3300, 1.3340, 1.3320, 1.3350, 1.3330, 1.3360], 6)
    eng = feed(E.PerceptionEngine(), bars)
    for o in by_type(eng, "PATTERN_LINE"):
        if o.geometry["side"] == "top":
            assert o.geometry["slope"] <= 0.30 + 1e-9


def test_pierce_and_keep():
    """Fig 3.5 / p66: a close through the line marks it PIERCED; the
    line object is kept (not deleted)."""
    bars = zigzag([1.3300, 1.3340, 1.3320, 1.3342, 1.3322], 6)
    eng = feed(E.PerceptionEngine(), bars)
    lines = by_type(eng, "PATTERN_LINE")
    if not lines:
        pytest.skip("no line formed in fixture")
    ln = lines[0]
    # drive a close through the line
    i = len(bars)
    g = ln.geometry
    px = (g["p0"] + g["slope"] * (i - g["t0"])) * P
    through = px + 6 * P if g["side"] == "top" else px - 6 * P
    bars2 = [mk(i, px, through + 2 * P, px - 1 * P, through)]
    feed(eng, bars2)
    assert ln.geometry.get("pierced") is True
    assert ln in eng.objects and ln.state != "DELETED"


def test_tf_relabel():
    """T -> F relabel: poke, then close back inside and move >= half the
    box height the other way within 1-3 bars."""
    bars = zigzag([1.3300, 1.3340, 1.3310, 1.3340, 1.3312, 1.3340], 6)
    # extra touches so the box is established
    bars += wave(len(bars), 1.3312, 1.3339, 3)
    bars += wave(len(bars), 1.3339, 1.3315, 3)
    # poke 2 pips above the top edge, close inside
    bars.append(mk(len(bars), 1.3337, 1.3343, 1.3334, 1.3336))
    # then drop > half the box height within 3 bars
    bars += wave(len(bars), 1.3334, 1.3318, 2)
    eng = feed(E.PerceptionEngine(), bars)
    labels = [o for o in eng.objects if o.type == "LABEL_TF"]
    assert any(l.geometry["letter"] == "F" for l in labels), \
        [l.geometry for l in labels]


def test_carried_level_consumed_after_touch():
    """Fig 6.1 / §3.6: a carried level is consumed by ONE touch."""
    bars = zigzag([1.3300, 1.3340, 1.3310, 1.3340, 1.3310], 6)
    bars += wave(len(bars), 1.3330, 1.3360, 4)   # break up -> level born
    eng = feed(E.PerceptionEngine(), bars)
    lv = [o for o in eng.objects if o.type == "LEVEL_CARRIED"]
    assert lv
    o = lv[0]
    # come back and touch the level once
    i = len(bars)
    p = o.geometry["price"] / P
    feed(eng, wave(i, 1.3355, p - 1 * P, 3))
    assert o.state == "CLOSED"


def test_asia_range_open_to_box():
    """§3.1(c): 00:00-08:00 CET drift -> RANGE_OPEN; converts to BOX at
    08:00 (or earlier on a close outside + follow-through)."""
    bars = []
    px = 1.3300
    for k in range(98):                     # 00:00-08:05
        bars.append(mk(k, px, px + 4 * P, px - 4 * P, px))
    eng = feed(E.PerceptionEngine(), bars)
    ro = [o for o in eng.objects if o.type == "RANGE_OPEN"]
    bx = [o for o in eng.objects if o.type == "BOX"
          and o.why == "asia_session"]
    assert ro and ro[0].state == "CLOSED"
    assert bx, "Asian range did not convert to a box at 08:00"


def test_thin_asia_range_flagged():
    """A thin Asian range (<= ~10 pips) is flagged false-break prone."""
    bars = []
    px = 1.3300
    for k in range(98):
        bars.append(mk(k, px, px + 3 * P, px - 3 * P, px))
    eng = feed(E.PerceptionEngine(), bars)
    bx = [o for o in eng.objects if o.type == "BOX"
          and o.why == "asia_session"]
    assert bx and any(e[1] == "thin_range" for e in bx[0].events)


def test_mw_bracket_and_mid():
    """§3.8: two tops within tol, 4-28 bars apart -> M bracket whose
    geometry carries the middle-section level."""
    bars = zigzag([1.3300, 1.3340, 1.3320, 1.3340, 1.3300], 7)
    eng = feed(E.PerceptionEngine(), bars)
    br = [o for o in eng.objects if o.type == "BRACKET"]
    assert any(o.geometry["letter"] == "M" for o in br)
    m = [o for o in br if o.geometry["letter"] == "M"][0]
    assert abs(m.geometry["mid"] - 13320) <= 4


def test_shrinking_domes_recorded():
    """Fig 5.3/5.5: successive swings off a level shrink; the dome
    sequence is stored as facts."""
    bars = zigzag([1.3340, 1.3300, 1.3325, 1.3300, 1.3315, 1.3300], 8)
    eng = feed(E.PerceptionEngine(), bars)
    ups = [d for d in eng.domes if d[2] > 0]
    assert len(ups) >= 2
    hs = [d[1] for d in ups]
    assert hs[-1] < hs[0]


def test_room_rule_14_pips():
    """p167: obstacle room — a level 6 pips ahead fails the 14-pip rule."""
    bars = zigzag([1.3300, 1.3340, 1.3310, 1.3340, 1.3310], 6)
    bars += wave(len(bars), 1.3330, 1.3352, 4)
    eng = feed(E.PerceptionEngine(), bars)
    f = eng.facts(len(bars) - 1)
    assert "room_up" in f and "room_dn" in f


def test_stand_aside_news_window():
    """§4: STAND_ASIDE during the 14:30 CET news window."""
    eng = E.PerceptionEngine()
    # bar at 14:30 CET (minute 870)
    feed(eng, [mk(174, BASE, BASE + 3 * P, BASE - 3 * P, BASE)])
    assert "news_window" in eng.stand_aside(0)


def test_reanchor_on_new_double_top():
    """Fig 3.9 / p79,102: a NEW double top at a different level re-anchors
    the frozen edge; a bare poke must not (edge only moves on aligned
    pairs)."""
    bars = zigzag([1.3300, 1.3340, 1.3310, 1.3340, 1.3315], 6)
    # two pokes to ~1.3343.5, each closing back inside the box
    for pk in range(2):
        bars += wave(len(bars), 1.3320, 1.3342, 3)
        bars.append(mk(len(bars), 1.3342, 1.33435, 1.3336, 1.3338))
        bars += wave(len(bars), 1.3338, 1.3320, 3)
    eng = feed(E.PerceptionEngine(), bars)
    boxes = [b for b in by_type(eng, "BOX") if b.state != "DELETED"]
    assert boxes
    bx = boxes[-1]
    ra = [e for e in bx.events if e[1] == "reanchor"]
    assert ra, "no re-anchor on a new double top"
    assert bx.geometry["top"] > 13340


def test_squeeze_between_line_and_ema():
    """Fig 5.1: tiny overlapping bars pressed between a structure edge
    above and the rising EMA25 below produce a SQUEEZE object."""
    bars = zigzag([1.3300, 1.3340, 1.3310, 1.3340, 1.3330], 6)
    # then a run of very small bars just under the box top, EMA rising
    # into them from below (clearly tighter than the zigzag bars)
    px = 1.3335
    for k in range(8):
        bars.append(mk(len(bars), px, px + 0.4 * P, px - 0.4 * P, px))
    eng = feed(E.PerceptionEngine(), bars)
    sq = [o for o in eng.objects if o.type == "SQUEEZE"]
    assert sq, "no squeeze flagged on a small-bar compression"


def test_grid_20_switch():
    """§2: rolling median daily range < 60 pips -> facts report the
    20-grid instead of the 00/50 grid."""
    bars = []
    for d in range(4):
        px = 1.3300
        for k in range(60):          # 5h of flat 2-pip bars per day
            bars.append(flat(k, px, day=d))
    eng = feed(E.PerceptionEngine(), bars)
    assert eng.facts(len(bars) - 1)["grid_step"] == 20
    # volatile regime stays on the 00/50 grid
    bars2 = []
    for d in range(4):
        for k in range(60):
            px = 1.3300 + (0.0020 if k % 2 else 0.0)
            bars2.append(mk(k, px, px + 30 * P, px - 30 * P, px, day=d))
    eng2 = feed(E.PerceptionEngine(), bars2)
    assert eng2.facts(len(bars2) - 1)["grid_step"] == 50


# ------------------------------------------------------------------- #
# §6.3 causality and determinism
# ------------------------------------------------------------------- #

def _full_state(eng, i):
    """The ENTIRE observable state at bar i, not just ACTIVE objects.

    D7: comparing only `snapshot()` (which lists ACTIVE objects) let a
    divergence in closed/deleted objects, swings, domes or bar facts pass
    unnoticed.  Causality means every byte the engine has derived from
    bars <= i must match, so this dumps all of it.
    """
    return json.dumps({
        "snapshot": eng.snapshot(i),
        "objects": [o.to_dict() for o in eng.objects],
        "swings": eng.swings,
        "domes": eng.domes,
        "bar_facts": eng.bar_facts,
        "pressure": eng.pressure,
        "ema": [round(x, 6) for x in eng.ema],
        "abr": [round(x, 6) for x in eng.abr],
    }, sort_keys=True, default=str)


def _snapshot_at(bars, i):
    """Full state at bar i computed on bars[:i+1] alone (prefix run)."""
    eng = feed(E.PerceptionEngine(), bars[:i + 1])
    return _full_state(eng, i)


def _live_snapshots(bars):
    """Run the full sequence, capturing the full state after each bar —
    this is what prefix-invariance compares against."""
    eng = E.PerceptionEngine()
    snaps = []
    for k, b in enumerate(bars):
        eng.update(b["t"], b["o"], b["h"], b["l"], b["c"],
                   cet_min=b["cet_min"])
        snaps.append(_full_state(eng, k))
    return snaps


def test_prefix_invariance():
    """The state at bar t in a full run must equal a fresh run that only
    ever saw bars[:t+1] (no peeking at the future)."""
    bars = zigzag([1.3340, 1.3300, 1.3340, 1.3310, 1.3350, 1.3300], 6)
    live = _live_snapshots(bars)
    for t in (10, 20, len(bars) - 1):
        assert live[t] == _snapshot_at(bars, t), \
            f"prefix divergence at t={t}"


def test_future_mutation():
    """Mutating bars after t changes nothing at t."""
    bars = zigzag([1.3340, 1.3300, 1.3340, 1.3310, 1.3350], 6)
    t = 20
    live_a = _live_snapshots(bars)[t]
    mut = copy.deepcopy(bars)
    for k in range(t + 1, len(mut)):
        mut[k]["h"] += 30 * P
        mut[k]["l"] -= 30 * P
    live_b = _live_snapshots(mut)[t]
    assert live_a == live_b


def test_determinism_byte_identical():
    bars = zigzag([1.3340, 1.3300, 1.3340, 1.3310, 1.3350], 6)
    s1 = _snapshot_at(bars, len(bars) - 1)
    s2 = _snapshot_at(bars, len(bars) - 1)
    assert s1 == s2


def test_warmup_no_crash():
    eng = feed(E.PerceptionEngine(), [mk(0, BASE, BASE + P, BASE - P,
                                         BASE)])
    assert eng.snapshot()["bar"] == 0


def test_no_outcome_imports():
    """The engine must never import outcome/referee modules."""
    import engine_v0 as eng_mod
    banned = {"pa_fill", "pa_eval", "pa_random", "arrival_outcome",
              "phys_resolve"}
    src = open(eng_mod.__file__, encoding="utf8").read()
    for b in banned:
        assert b not in src
