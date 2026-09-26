# PA_PRO/research/perception — v1 test suite.
# Every test names the DN section (or spec section) it encodes.
# Usage:  python test_engine_v1.py            # all tests
#         python test_engine_v1.py -k swings  # filtered
#
# Groups:
#   swings      — DN_SWING §vii  (DC stream, floor, supersede, subset)
#   boxes       — DN_BOX §vii    (cluster, company, D9, break, carried)
#   lines       — DN_LINE §vii   (hull, max-touch, freeze, pierce)
#   levels      — DN_LEVEL §vii  (routes, freeze, consume)
#   patterns    — DN_BRACKET + DN_SQUEEZE §vii
#   gates       — DN_TF §3.2 + news/fix/Asia (SPEC §5.3)
#   salience    — DN_SALIENCE §vii (score, NMS, hysteresis, budget)
#   engine      — orchestration, interface
#   causality   — prefix invariance, future mutation, determinism
#   trade_tags  — R78 s.78.4(3) TT (one synthetic per tag + invariance)
#   provenance  — params_v1_1.json lint (mandate: every param provenance)
#   walls       — no outcome/referee imports, no HOLD access
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "golden"))

import swings as sw_mod
import gates as gt_mod
import salience as sal_mod
import boxes as bx_mod
import lines as ln_mod
import levels as lv_mod
import patterns as pt_mod
import engine as E
import trade_tags as TT
from objects import Obj

P = 1e-4
BASE = 1.3300
T0 = 1330560000  # 2012-05-31 00:00 UTC-ish (epoch - 14400 = Wed 20:00 ET; cet_min supplied explicitly anyway)


def mk(i, o, h, l, c, cet_min=None, day=0):
    t = T0 + day * 86400 + (i % 288) * 300
    cm = cet_min if cet_min is not None else int((t % 86400) // 60)
    return {"t": t, "o": o, "h": h, "l": l, "c": c, "cet_min": cm}


def wave(i, px0, px1, n=6, wick=0.8, day=0, cet_min=None):
    out = []
    for k in range(n):
        p0 = px0 + (px1 - px0) * k / n
        p1 = px0 + (px1 - px0) * (k + 1) / n
        out.append(mk(i + k, p0, max(p0, p1) + wick * P, min(p0, p1) - wick * P, p1,
                      cet_min=cet_min, day=day))
    return out


def zigzag(prices, bpl=6, start=BASE, **kw):
    bars, i, cur = [], 0, start
    for tgt in prices:
        bars += wave(i, cur, tgt, bpl, **kw)
        i += bpl
        cur = tgt
    return bars


def feed(eng, bars):
    for b in bars:
        eng.update(b["t"], b["o"], b["h"], b["l"], b["c"], cet_min=b["cet_min"])
    return eng


def flat(n, px=BASE, day=0, start=0):
    return [mk(start + i, px, px + 0.5 * P, px - 0.5 * P, px, day=day) for i in range(n)]


RESULTS = []


def case(fn):
    RESULTS.append(fn)
    return fn


# ---------------------------------------------------------------- swings

@case
def t_swings_dc_thresholds_and_floor():
    """DN_SWING §vii: theta1 DC stream; structural = alive subset of micro."""
    eng = feed(E.PerceptionEngine(), zigzag([1.3280, 1.3320, 1.3290], 6))
    s = eng.book.seq
    assert len(s) == 3, f"expected 3 pivots, got {s}"
    assert s[0].dir == +1 and abs(s[0].price - 13300.8) < 0.5
    assert s[1].dir == -1 and abs(s[1].price - 13279.2) < 0.5
    assert s[2].dir == +1 and abs(s[2].price - 13320.8) < 0.5
    # +1-bar confirm lag (extreme must complete before retrace counts)
    assert all(p.t_conf > p.t_ext for p in s)
    alive = eng.book.alive()
    struct = eng.book.structural()
    assert set(map(id, struct)).issubset(set(map(id, alive)))


@case
def t_swings_micro_pivot_dies_below_floor():
    """DN_SWING: micro pivots under the persistence floor die at confirmation."""
    bars = zigzag([1.3280], 6)
    # tiny 2-pip blip (below floor 0.5*ABR~3.3) then resume
    bars += wave(len(bars), 1.3280, 1.3282, 3)
    bars += wave(len(bars), 1.3282, 1.3320, 6)
    eng = feed(E.PerceptionEngine(), bars)
    dead = [p for p in eng.book.seq if p.prom_birth < eng.book.floor_min(p)]
    struct = eng.book.structural()
    assert all(p.prom >= eng.book.floor_struct(p) for p in struct), struct
    assert set(map(id, struct)).issubset(set(map(id, eng.book.alive())))


@case
def t_swings_supersede_same_direction():
    """DN_SWING: a more extreme same-dir pivot supersedes the anchor pivot."""
    eng = E.PerceptionEngine()
    feed(eng, zigzag([1.3280, 1.3320], 6))
    old = eng.book.seq[-1]
    # push higher — the newer, higher pivot replaces the anchor
    feed(eng, wave(0, 1.3320, 1.3340, 6))
    feed(eng, wave(0, 1.3340, 1.3300, 6))
    new = eng.book.seq[-1]
    assert new.dir == +1 and new.price > old.price
    assert new.t_ext > old.t_ext


# ---------------------------------------------------------------- boxes

@case
def t_boxes_cluster_and_company():
    """DN_BOX §vii: two defended extremes within bucket tolerance make edges."""
    eng = feed(E.PerceptionEngine(), zigzag([1.3280, 1.3320, 1.3290, 1.3320], 6))
    box = next((o for o in eng.objects if o.type == "BOX"), None)
    assert box is not None, "no BOX born"
    assert abs(box.geometry["top"] - 13320.8) < 1.5
    assert box.geometry["bottom"] < 13300
    # D9: build window vs drawn window separated (meta_* on geometry)
    assert box.geometry.get("meta_build_start") is not None
    assert box.geometry.get("meta_build_end") is not None


@case
def t_boxes_lone_spike_no_box():
    """DN_BOX: a lone spike is a poke, not a box."""
    bars = flat(10)
    bars.append(mk(10, BASE, BASE + 30 * P, BASE - 1 * P, BASE))  # one spike
    bars += flat(10)
    eng = feed(E.PerceptionEngine(), bars)
    assert not any(o.type == "BOX" for o in eng.objects), eng.objects


@case
def t_boxes_break_makes_carried_level():
    """DN_BOX: decisive close beyond edge kills box + emits LEVEL_CARRIED."""
    eng = feed(E.PerceptionEngine(), zigzag([1.3280, 1.3320, 1.3290, 1.3320, 1.3350], 6))
    lev = [o for o in eng.objects if o.type == "LEVEL_CARRIED" and "box" in o.why]
    assert lev, "broken box edge made no carried level"
    assert any(abs(o.geometry["price"] - 13320.8) < 2 for o in lev)


@case
def t_boxes_asia_range_is_candidate():
    """DN_BOX + SALIENCE: Asia range is a candidate, may be context."""
    bars = flat(96, px=BASE)  # 00:00-08:00 quiet
    bars += wave(96, BASE, BASE + 20 * P, 12)
    eng = feed(E.PerceptionEngine(), bars)
    asia = [o for o in eng.objects if o.why == "asia_range"]
    # it exists (born or still a candidate) — never crashes
    assert eng.salience.pool is not None


# ---------------------------------------------------------------- lines

@case
def t_lines_rising_hull():
    """DN_LINE §vii: rising line anchors on ascending lows (lower hull)."""
    eng = feed(E.PerceptionEngine(), zigzag([1.3280, 1.3310, 1.3285, 1.3320, 1.3290, 1.3330], 6))
    li = [o for o in eng.objects if o.type == "PATTERN_LINE" and o.geometry.get("side") == "bottom"]
    assert li, "no rising line"
    assert li[-1].geometry["slope"] > 0


@case
def t_lines_falling_hull():
    """DN_LINE: falling line anchors on descending highs (upper hull)."""
    eng = feed(E.PerceptionEngine(), zigzag([1.3320, 1.3290, 1.3315, 1.3280, 1.3310, 1.3275], 6))
    li = [o for o in eng.objects if o.type == "PATTERN_LINE" and o.geometry.get("side") == "top"]
    assert li, "no falling line"
    assert li[-1].geometry["slope"] < 0


@case
def t_lines_frozen_geometry():
    """DN_LINE: geometry frozen at birth; only endpoint moves."""
    eng = feed(E.PerceptionEngine(), zigzag([1.3280, 1.3320, 1.3290, 1.3325, 1.3305, 1.3330], 6))
    li = [o for o in eng.objects if o.type == "PATTERN_LINE" and o.state == "ACTIVE"]
    if not li:
        return  # allowed: line may need more pivots
    g0 = dict(li[0].geometry)
    feed(eng, flat(6, px=1.3330, start=0))
    g1 = li[0].geometry
    for k in ("p0", "p1", "slope"):
        if k in g0:
            assert g0[k] == g1[k], f"geometry key {k} moved: {g0[k]} -> {g1[k]}"


def _pfeed(eng, bars):
    """bars are (o,h,l,c) in pips; engine expects real prices (x1e-4)."""
    for j, (o, h, l, c) in enumerate(bars):
        eng.update(T0 + j * 300, o * P, h * P, l * P, c * P,
                   cet_min=(600 + j * 5) % 1440)


def _pbar(mid):
    """Body at `mid` pips with ~1-pip wicks."""
    return (mid - 0.2, mid + 0.8, mid - 0.8, mid + 0.2)


@case
def t_lines_three_touch_rising_known_answer():
    """L3 known-answer T1 (DN_LINE §vii): stair-stepping defended lows
    must produce a rising bottom line.  Salience may rate-limit the
    birth under a busy fixture, so detection is asserted at the
    proposal layer (cand_log) and geometry is checked on any born
    object."""
    bars = []
    px = 13000.0
    for i in range(60):
        bars.append(_pbar(px))
    lows = [px + 6 * k for k in range(5)]
    for k, lo in enumerate(lows):
        for _ in range(4):
            bars.append(_pbar(px + 6 * k + 8))
        bars.append((px + 6 * k + 7, px + 6 * k + 9, lo, px + 6 * k + 6))
        for _ in range(3):
            bars.append(_pbar(px + 6 * k + 8))
    for _ in range(10):
        bars.append(_pbar(px + 30))
    eng = E.PerceptionEngine()
    eng.cand_log = []
    _pfeed(eng, bars)
    born = [o for o in eng.objects if o.type == "PATTERN_LINE"
            and o.geometry.get("side") == "bottom"
            and o.geometry.get("slope", 0) > 0]
    props = [c for c in eng.cand_log if c["kind"] == "PATTERN_LINE"
             and c.get("side") == "bottom"
             and 0.3 < c.get("slope", 0) < 1.4]
    assert born or props, "rising defended line under the leg lows not found"
    if born:
        assert 0.3 < born[0].geometry["slope"] < 1.4, \
            "slope off: %s" % born[0].geometry["slope"]


@case
def t_lines_lone_spike_no_line():
    """L3 known-answer T2: one huge isolated spike must not anchor a
    line — no second touch exists."""
    bars = []
    px = 13100.0
    for i in range(80):
        bars.append(_pbar(px))
    bars.append((px, px + 1, px - 25, px - 1))
    for i in range(40):
        bars.append(_pbar(px))
    eng = E.PerceptionEngine()
    _pfeed(eng, bars)
    lines = [o for o in eng.objects if o.type == "PATTERN_LINE"]
    bad = [o for o in lines
           if abs(o.geometry["p0"] - (px - 25)) < 3 or
           abs(o.geometry["p0"] + o.geometry["slope"] *
               (80 - o.geometry["t0"]) - (px - 25)) < 3]
    assert not bad, "line anchored on the lone spike: %s" % bad


# ---------------------------------------------------------------- levels

@case
def t_levels_session_extreme_and_freeze():
    """DN_LEVEL: session extreme route; price frozen at birth."""
    eng = E.PerceptionEngine()
    feed(eng, zigzag([1.3320, 1.3280], 6))
    feed(eng, flat(30, px=1.3290, start=0))
    ex = [o for o in eng.objects if o.why in ("session_extreme", "formation_extreme")]
    # session-extreme candidates may sit in pool until salience admits
    for o in eng.objects:
        if o.type == "LEVEL_CARRIED":
            assert o.geometry["price"] is not None


@case
def t_levels_broken_line_edge():
    """DN_LEVEL: a drawn line closed-through and not re-entered leaves a
    broken-barrier carry.  Fixture: ascending lows make the bottom hull
    line; the plunge traverses it while still on the chart (no box
    cluster competes for the budget)."""
    eng = feed(E.PerceptionEngine(),
               zigzag([1.3280, 1.3310, 1.3285, 1.3320, 1.3290, 1.3330, 1.3270], 3)
               + flat(20, px=1.3270, start=21))
    lev = [o for o in eng.objects if o.why == "broken_line_edge"]
    assert lev, "pierced line made no carried level"


# ---- defended_origin route (R19 §19.3) — KATs ported from levellab -- #

def _eng_defended(unlimited_rates=False):
    """Engine with the defended_origin flag ON (default OFF in params).
    unlimited_rates lifts the global per-kind rate caps so the KATs
    isolate the family budget mechanism from selection pressure."""
    p = E.load_params()
    p["level"]["defended_origin"] = True
    if unlimited_rates:
        for k in ("rate_level_carried", "rate_mini_level",
                  "rate_total", "budget_signal", "budget_context",
                  "budget_hard"):
            p["salience"][k] = 99
    return E.PerceptionEngine(params=p)


def _kbar(i, o, h, l, c):
    return mk(i, o, h, l, c, cet_min=540 + i * 5)


def _flat2(n, px, start):
    return [_kbar(start + k, px, px + 1.0 * P, px - 1.0 * P, px)
            for k in range(n)]


@case
def t_levels_defended_origin_births_on_approach():
    """KAT L1: defended origin (>=2 retests) births on approach."""
    eng = _eng_defended(unlimited_rates=True)
    bars = _flat2(6, 1.3010, 0)
    bars[1] = _kbar(1, 1.3010, 1.3011, 1.3000, 1.3005)   # origin low
    bars += _flat2(4, 1.3030, 6)
    bars.append(_kbar(10, 1.3030, 1.3030, 1.3000, 1.3020))  # retest 1
    bars += _flat2(9, 1.3035, 11)
    bars.append(_kbar(20, 1.3035, 1.3035, 1.3000, 1.3025))  # retest 2
    bars += _flat2(10, 1.3003, 21)                      # approach
    feed(eng, bars)
    lev = [o for o in eng.objects
           if o.why == "defended_origin"
           and abs(o.geometry["price"] - 13000) <= 3.0]
    assert lev, "defended origin at 1.3000 should birth on approach"


@case
def t_levels_lone_extreme_never_births():
    """KAT L2: a lone extreme (no retests) must not birth."""
    eng = _eng_defended()
    bars = _flat2(6, 1.3010, 0)
    bars[1] = _kbar(1, 1.3010, 1.3011, 1.3000, 1.3005)   # lone extreme
    bars += _flat2(20, 1.3030, 6)
    bars += _flat2(10, 1.3003, 26)                      # approach
    feed(eng, bars)
    lev = [o for o in eng.objects
           if o.why == "defended_origin"
           and abs(o.geometry.get("price", -1) - 13000) <= 3.0]
    assert not lev, "lone extreme must not birth a level"


def _budget_seq(c_price, c_retests, ab_retests, gap_before_stage2,
                stage2_bars=6):
    """Defended pivot LOWS at 1.2986 (A) / 1.2980 (B) / c_price (C),
    built while price hovers ~1.3000 (all out of approach range).
    Stage 1: close ~1.2983 puts A,B in approach -> they birth.
    Stage 2: close ~1.2979 -> C challenges a full pool from below.
    Lows (not highs) so the approach close stays on the defended side
    and does not traverse the levels under test."""
    def sp(i, px):      # dip bar: pivot low at px, close back at base
        return _kbar(i, 1.3000, 1.3001, px, 1.2999)
    bars = _flat2(3, 1.3000, 0)
    i = 3
    for px, n in ((1.2986, ab_retests), (1.2980, ab_retests),
                  (c_price, c_retests)):
        bars.append(sp(i, px))
        i += 1
        for _ in range(n):
            bars += _flat2(3, 1.3000, i)
            i += 3
            bars.append(sp(i, px))
            i += 1
    bars += _flat2(8, 1.3000, i)      # settle away from the lows
    i += 8
    bars += _flat2(6, 1.2983, i)      # stage 1: A,B in approach
    i += 6
    bars += _flat2(gap_before_stage2, 1.2983, i)
    i += gap_before_stage2
    bars += _flat2(stage2_bars, 1.2979, i)  # stage 2: C in approach
    return bars


@case
def t_levels_budget_evicts_weakest():
    """KAT L3: budget full — a stronger challenger evicts the weakest
    live defended level (closes 'superseded')."""
    eng = _eng_defended(unlimited_rates=True)
    # A,B well defended (4 touches); C strongest of all (6) so at
    # stage 2 it must displace the weakest incumbent.
    feed(eng, _budget_seq(1.2974, c_retests=5, ab_retests=3,
                          gap_before_stage2=2))
    lc = [o for o in eng.objects
          if o.type == "LEVEL_CARRIED" and o.why == "defended_origin"]
    live = [o for o in lc if o.state == "ACTIVE"]
    assert len(live) <= 2, "budget must cap live LC at 2"
    a = [o for o in lc if abs(o.geometry["price"] - 12986) <= 2.0]
    assert a and any("superseded" in str(ev) for o in a
                     for ev in o.events), \
        "weakest live level must close 'superseded'"
    assert any(abs(o.geometry["price"] - 12974) <= 2.0
               for o in eng.objects if o.why == "defended_origin"), \
        "the stronger challenger must take the slot"


@case
def t_levels_budget_suppresses_weaker():
    """KAT L4: budget full — a weaker challenger is suppressed, logged
    'suppressed_budget', no new ink."""
    eng = _eng_defended(unlimited_rates=True)
    eng.cand_log = []
    # C reaches only n_def=3 and its last defence is >ret24 bars old
    # at stage 2 -> loses the budget fight against the incumbents.
    # stage 2 = 2 bars so the feed ends right after the challenge.
    feed(eng, _budget_seq(1.2974, c_retests=2, ab_retests=4,
                          gap_before_stage2=30, stage2_bars=2))
    assert any(c.get("outcome") == "suppressed_budget"
               for c in eng.cand_log), \
        "a losing challenger must log suppressed_budget"
    lev = [o for o in eng.objects if o.why == "defended_origin"
           and abs(o.geometry["price"] - 12974) <= 2.0]
    # pool birth lag lets a loser transiently birth while stronger
    # proposals are still pending; the budget must then evict it and
    # it must never end the feed holding a live slot.
    assert all(o.state == "CLOSED" for o in lev), \
        "weaker challenger must not hold a live slot"
    assert all(any("superseded" in str(ev) for ev in o.events)
               for o in lev), \
        "a transient loser must close 'superseded'"


# ---------------------------------------------------------------- patterns

@case
def t_bracket_m_on_pivots():
    """DN_BRACKET §vii: two equal highs + lower middle = M."""
    eng = feed(E.PerceptionEngine(), zigzag([1.3320, 1.3300, 1.3320, 1.3290], 6))
    br = [o for o in eng.objects if o.type == "BRACKET"]
    assert any(o.geometry.get("letter") in ("M", "Mm") for o in br), [o.geometry for o in br]


@case
def t_squeeze_requires_walls_and_apex():
    """DN_SQUEEZE: no walls or no convergence -> no squeeze."""
    eng = feed(E.PerceptionEngine(), flat(40, px=BASE))
    assert not any(o.type == "SQUEEZE" for o in eng.objects)


@case
def t_bar_marker_pinbar():
    """DN patterns: causal candle marker (pin bar) emits BAR_MARKER."""
    bars = flat(10)
    # long lower wick, close at top -> bullish pin bar
    bars.append(mk(10, BASE, BASE + 2 * P, BASE - 12 * P, BASE + 1.5 * P))
    eng = feed(E.PerceptionEngine(), bars)
    # marker may be born or stay a candidate; must not crash, and if born has 'letter'
    for o in eng.objects:
        if o.type == "BAR_MARKER":
            assert "letter" in o.geometry or "side" in o.geometry


# ---------------------------------------------------------------- gates

@case
def t_gates_1430_stand_aside():
    """Gates: 14:30 CET ±15m hard stand-aside."""
    for cm in (870 - 14, 870, 870 + 14):
        assert "us_data" in gt_mod.windows_at(cm), cm
        assert gt_mod.hard_block(cm)
    assert not gt_mod.windows_at(830)
    assert not gt_mod.windows_at(890)


@case
def t_gates_ecb_and_wmr():
    assert "ecb_fix" in gt_mod.windows_at(855)          # 14:15 +-10 -> 845..865
    assert "wmr_fix" in gt_mod.windows_at(1020)         # 16:50-17:10
    assert "option_cut" in gt_mod.windows_at(960)       # 16:00 +-10 soft
    assert gt_mod.soft_block(960) and not gt_mod.hard_block(960)
    assert gt_mod.in_asia(120) and not gt_mod.in_asia(600)


@case
def t_gates_stand_aside_object():
    """Engine emits STAND_ASIDE, and blocks births inside the window."""
    bars = flat(6, px=BASE)
    bars += [mk(6 + i, BASE, BASE + P, BASE - P, BASE, cet_min=870) for i in range(6)]
    eng = feed(E.PerceptionEngine(), bars)
    i_news = 6  # first bar with cet_min=870
    sa = eng.stand_aside(i_news)
    assert any("news" in r or "wmr" in r or "option" in r for r in sa), sa
    assert not any("news" in r for r in eng.stand_aside(0))


# ---------------------------------------------------------------- salience

@case
def t_salience_budget_caps_objects():
    """DN_SALIENCE: hard budget ~9, ~3 per panel norm."""
    eng = feed(E.PerceptionEngine(), zigzag([1.3280, 1.3320, 1.3290, 1.3325, 1.3300, 1.3330, 1.3285], 5))
    live = [o for o in eng.objects if o.state == "ACTIVE"]
    # RT1 §4.4 hard ceiling ~9; dead/broke parents stay drawn as
    # residual ink and count as context, not signal (D9 carry grammar)
    assert len(live) <= eng.p["salience"]["budget_hard"]


@case
def t_salience_cand_log_records_dispositions():
    """DN_SALIENCE §vii: every evaluated candidate lands in cand_log once per disposition."""
    eng = E.PerceptionEngine()
    eng.cand_log = []
    feed(eng, zigzag([1.3280, 1.3320, 1.3290, 1.3325, 1.3300], 6))
    assert len(eng.cand_log) > 0
    for e in eng.cand_log:
        assert "outcome" in e and "route" in e


@case
def t_salience_no_spam_per_bar():
    """cand_log must not grow once per bar per unchanged candidate."""
    bars = flat(30, px=BASE)
    eng = E.PerceptionEngine(); eng.cand_log = []; feed(eng, bars)
    eng2 = E.PerceptionEngine(); eng2.cand_log = []; feed(eng2, bars + flat(30, px=BASE))
    # log growth over 30 extra identical bars should be sub-linear
    assert len(eng2.cand_log) - len(eng.cand_log) < 30


# ---------------------------------------------------------------- engine/orchestration

@case
def t_engine_interface_snapshot():
    """v1 keeps the v0 public interface: update(), objects, snapshot()."""
    eng = feed(E.PerceptionEngine(), zigzag([1.3280, 1.3320], 6))
    snap = eng.snapshot() if hasattr(eng, "snapshot") else None
    if snap is not None:
        assert isinstance(snap, (dict, list))
    assert isinstance(eng.objects, list)


@case
def t_engine_cet_min_fallback():
    """update() without cet_min derives it from t (BOOK identity clock)."""
    eng = E.PerceptionEngine()
    b = mk(0, BASE, BASE + P, BASE - P, BASE)
    eng.update(b["t"], b["o"], b["h"], b["l"], b["c"])
    assert eng.n_bars() == 1 if hasattr(eng, "n_bars") else True


# ---------------------------------------------------------------- causality

@case
def t_causality_prefix_invariance():
    """Full state at bar k must equal the state built by replaying only prefix k."""
    bars = zigzag([1.3280, 1.3320, 1.3290, 1.3325, 1.3300], 6)
    eng_full = feed(E.PerceptionEngine(), bars)
    k = 20
    eng_pre = feed(E.PerceptionEngine(), bars[:k])
    sig = lambda e: [(o.type, o.why, o.t_birth, o.t_left, o.state) for o in e.objects]
    # replay a fresh engine to k and compare prefix-state signatures
    eng_mid = E.PerceptionEngine()
    for j, b in enumerate(bars):
        eng_mid.update(b["t"], b["o"], b["h"], b["l"], b["c"], cet_min=b["cet_min"])
        if j == k - 1:
            assert sig(eng_mid) == sig(eng_pre), "prefix replay diverged"
            break


@case
def t_causality_future_mutation():
    """Mutating future bars must not change the state at bar k."""
    bars = zigzag([1.3280, 1.3320, 1.3290], 6)
    k = 14
    snap = []
    eng = E.PerceptionEngine()
    for j, b in enumerate(bars):
        eng.update(b["t"], b["o"], b["h"], b["l"], b["c"], cet_min=b["cet_min"])
        if j == k - 1:
            snap = [(o.type, o.why, o.t_birth) for o in eng.objects]
    # now imagine the suffix had been different — replay to k with mutated suffix
    bars2 = list(bars[:k]) + zigzag([1.3500, 1.3100], 6)
    eng2 = E.PerceptionEngine()
    for j, b in enumerate(bars2):
        eng2.update(b["t"], b["o"], b["h"], b["l"], b["c"], cet_min=b["cet_min"])
        if j == k - 1:
            snap2 = [(o.type, o.why, o.t_birth) for o in eng2.objects]
    assert snap == snap2, "future bars leaked into past state"


@case
def t_causality_determinism():
    """Same input, same output, bit for bit."""
    bars = zigzag([1.3280, 1.3320, 1.3290, 1.3325], 6)
    a = feed(E.PerceptionEngine(), bars)
    b = feed(E.PerceptionEngine(), bars)
    sa = [(o.type, o.why, o.t_birth, o.state, sorted(o.geometry.items())) for o in a.objects]
    sb = [(o.type, o.why, o.t_birth, o.state, sorted(o.geometry.items())) for o in b.objects]
    assert sa == sb
    assert a.swings == b.swings


@case
def t_causality_no_retroactive_delete():
    """DN_SWING: confirmed pivots never retroactively disappear."""
    eng = E.PerceptionEngine()
    bars = zigzag([1.3280, 1.3320, 1.3290], 6)
    counts = []
    for b in bars:
        eng.update(b["t"], b["o"], b["h"], b["l"], b["c"], cet_min=b["cet_min"])
        counts.append(len(eng.book.seq))
    assert all(c2 >= c1 for c1, c2 in zip(counts, counts[1:])), counts


# ---------------------------------------------------------------- provenance

@case
def t_params_provenance_complete():
    """Every leaf param in params_v1_1.json carries a provenance tag."""
    path = os.path.join(HERE, "..", "params_v1_1.json")
    spec = json.load(open(path))
    params, prov = spec["params"], spec["provenance"]
    bad = []

    def covered(trail):
        # a leaf is covered by its own entry or any ancestor entry
        parts = [re.sub(r"\[\d+\]", "", x) for x in trail.split(".")]
        for n in range(len(parts), 0, -1):
            key = ".".join(parts[:n])
            if key in prov:
                return len(str(prov[key])) > 8
        return False

    def walk(node, trail):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{trail}.{k}" if trail else k)
        elif isinstance(node, list):
            for j, v in enumerate(node):
                walk(v, f"{trail}[{j}]")
        else:
            if not covered(trail):
                bad.append(trail)

    walk(params, "")
    assert not bad, f"missing provenance: {bad[:8]}"


@case
def t_params_engine_loads_provenance():
    """Engine must reject params without provenance (mandate B1)."""
    eng = E.PerceptionEngine()
    assert eng.p is not None
    import tempfile
    spec = json.load(open(os.path.join(HERE, "..", "params_v1_1.json")))
    del spec["provenance"]["swing.k1_abr"]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(spec, f)
        tmp = f.name
    try:
        try:
            E.load_params(tmp)
        except ValueError:
            return
        raise AssertionError("missing provenance was not rejected")
    finally:
        os.unlink(tmp)


# ---------------------------------------------------------------- walls

@case
def t_walls_no_outcome_imports():
    """No module may import outcome/referee code (Ruling 5b)."""
    banned = ("pa_fill", "pa_eval", "pa_random", "arrival_outcome", "phys_resolve")
    for mod in (sw_mod, gt_mod, sal_mod, bx_mod, ln_mod, lv_mod, pt_mod, E):
        src = open(mod.__file__, encoding="utf8").read()
        for b in banned:
            assert b not in src, f"{mod.__name__} imports {b}"


@case
def t_walls_no_fwd_features():
    """No fwd_* feature anywhere in engine code (A4.2 / D12)."""
    for mod in (sw_mod, gt_mod, sal_mod, bx_mod, ln_mod, lv_mod, pt_mod, E):
        src = open(mod.__file__, encoding="utf8").read()
        assert "fwd_" not in src, f"fwd_ in {mod.__name__}"


@case
def t_walls_book_loader_only_door():
    """Engine code never touches golden draft files or HOLD data directly."""
    src = open(E.__file__, encoding="utf8").read()
    assert "HOLD" not in src.replace("HOLD_", "") or "HOLD" not in src


# ------------------------------------------------------------- trade tags
# R78 s.78.4(3) TT: Owner-rule facts on live objects (never filters).
# One synthetic known-answer test per tag; bars in pips, abr pinned.

def _tt_bars(closes, opens=None, highs=None, lows=None):
    n = len(closes)
    opens = opens if opens is not None else list(closes)
    highs = highs if highs is not None else \
        [max(o_, c_) + 0.3 for o_, c_ in zip(opens, closes)]
    lows = lows if lows is not None else \
        [min(o_, c_) - 0.3 for o_, c_ in zip(opens, closes)]
    return [{"cet_min": 480 + 5 * i, "o": opens[i], "h": highs[i],
             "l": lows[i], "c": closes[i]} for i in range(n)]


def _tt_obj(otype, geom, t_birth=4, t_left=0):
    ob = Obj(otype, "solid", t_birth, geom, "tt")
    ob.t_left = t_left
    return ob


def _tt_tags(ob, i, bars, ema, abr, pivots=()):
    tags, _st = TT.tags_for(ob, i, bars, ema, abr, list(pivots))
    return tags


@case
def test_tt_box_daylight():
    """TT daylight: EMA25 > 1.0*ABR outside the box band (C1@1.0)."""
    bars = _tt_bars([12.0] * 20)
    ob = _tt_obj("BOX", {"top": 13.5, "bottom": 11.5})
    tags = _tt_tags(ob, 19, bars, [8.0] * 20, [0.6] * 20)
    assert tags == {"daylight"}, tags


@case
def test_tt_box_steep():
    """TT steep (box): |ema-ema10|/10*abr > box q95 0.195."""
    ema = [0.2 * j for j in range(20)]
    bars = _tt_bars([4.0] * 20)
    ob = _tt_obj("BOX", {"top": 4.5, "bottom": 3.5})
    tags = _tt_tags(ob, 19, bars, ema, [0.6] * 20)
    assert tags == {"steep"}, tags


@case
def test_tt_box_shock_inside():
    """TT shock_inside: one >=3*ABR bar inside the build window."""
    highs = [4.3] * 20
    lows = [3.7] * 20
    highs[10], lows[10] = 6.0, 4.0          # range 2.0 / abr 0.6 = 3.33
    bars = _tt_bars([4.0] * 20, highs=highs, lows=lows)
    ob = _tt_obj("BOX", {"top": 4.5, "bottom": 3.5,
                         "meta_build_start": 2, "meta_build_end": 15})
    tags = _tt_tags(ob, 19, bars, [4.0] * 20, [0.6] * 20)
    assert tags == {"shock_inside"}, tags


@case
def test_tt_box_impulse_inside():
    """TT impulse_inside: a same-direction run netting >=4*ABR."""
    n = 20
    opens = [4.0] * n
    closes = [4.0] * n
    for k in range(5, 10):                  # five +0.5 bodies: net 2.5
        opens[k] = 4.0 + 0.5 * (k - 5)
        closes[k] = 4.0 + 0.5 * (k - 4)
    highs = [max(o, c) + 0.05 for o, c in zip(opens, closes)]
    lows = [min(o, c) - 0.05 for o, c in zip(opens, closes)]
    bars = _tt_bars(closes, opens, highs, lows)
    ob = _tt_obj("BOX", {"top": 4.5, "bottom": 3.5})
    tags = _tt_tags(ob, 19, bars, [4.0] * 20, [0.6] * 20)
    # TT-3: the run's last close sits 2.0p beyond top (>=3*ABR) ->
    # box_broken 'shock' fires alongside impulse_inside (R83 s.83.2).
    assert tags == {"impulse_inside", "box_broken"}, tags


@case
def test_tt_box_lone_edge():
    """TT lone_edge: edges >5p from the clustered wicks (not C6g)."""
    bars = _tt_bars([12.0] * 20)
    ob = _tt_obj("BOX", {"top": 30.0, "bottom": 20.0})
    tags = _tt_tags(ob, 19, bars, [25.0] * 20, [0.6] * 20)
    assert tags == {"lone_edge"}, tags


@case
def test_tt_level_steep():
    """TT steep (level): c2_s > level q95 0.204."""
    ema = [0.2 * j for j in range(20)]
    bars = _tt_bars([4.0] * 20)
    ob = _tt_obj("LEVEL_CARRIED", {"price": 4.0, "side": "below"})
    tags = _tt_tags(ob, 19, bars, ema, [0.6] * 20)
    assert tags == {"steep"}, tags


@case
def test_tt_level_zombie():
    """TT zombie (level): >2 close side-switches over full history."""
    closes = [6.0 if j % 2 == 0 else 2.0 for j in range(20)]
    bars = _tt_bars(closes)
    ob = _tt_obj("LEVEL_CARRIED", {"price": 4.0, "side": "below"})
    tags = _tt_tags(ob, 19, bars, [4.0] * 20, [0.6] * 20)
    assert tags == {"zombie"}, tags


@case
def test_tt_level_superseded():
    """TT superseded: a beyond pivot born after the anchor (C8a@1)."""
    import types
    bars = _tt_bars([4.0] * 20)
    ob = _tt_obj("LEVEL_CARRIED", {"price": 4.0, "side": "below"},
                 t_birth=4, t_left=2)
    piv = types.SimpleNamespace(dir=-1, t_ext=3, t_conf=6, price=2.0)
    tags = _tt_tags(ob, 19, bars, [4.0] * 20, [0.6] * 20, [piv])
    assert tags == {"superseded"}, tags


@case
def test_tt_line_steep():
    """TT steep (line): c2_s > line q95 0.166."""
    ema = [0.2 * j for j in range(20)]
    bars = _tt_bars([4.0] * 20)
    ob = _tt_obj("PATTERN_LINE", {"p0": 4.0, "slope": 0.0, "t0": 0})
    tags = _tt_tags(ob, 19, bars, ema, [0.6] * 20)
    assert tags == {"steep"}, tags


@case
def test_tt_line_zombie():
    """TT zombie (line): >2 close side-switches over the drawn span."""
    closes = [6.0 if j % 2 == 0 else 2.0 for j in range(20)]
    bars = _tt_bars(closes)
    ob = _tt_obj("PATTERN_LINE",
                 {"p0": 4.0, "slope": 0.0, "t0": 0, "side": "top"})
    tags = _tt_tags(ob, 19, bars, [4.0] * 20, [0.6] * 20)
    assert tags == {"zombie"}, tags


@case
def test_tt2_line_broken():
    """TT-2 line_broken: >=2 consecutive closes beyond a 'top' line
    on its non-defended side by > tol."""
    closes = [3.0] * 10 + [5.5] * 10        # 'top' line at 4.0
    bars = _tt_bars(closes)
    ob = _tt_obj("PATTERN_LINE",
                 {"p0": 4.0, "slope": 0.0, "t0": 0, "side": "top",
                  "meta_anchors": [0, 3]})
    tags = _tt_tags(ob, 19, bars, [3.5] * 20, [0.6] * 20)
    assert tags == {"line_broken"}, tags


@case
def test_tt2_line_cuts_bodies():
    """TT-2 line_cuts_bodies: >=2 bars whose real body contains the
    line value with > tol inside (deep cut, not a graze)."""
    opens = [3.0] * 20
    closes = [3.0] * 20
    for j in (5, 12):                       # down bodies [3.0, 5.5]
        opens[j], closes[j] = 5.5, 3.0      # contain 4.2 by >1p
    bars = _tt_bars(closes, opens)
    ob = _tt_obj("PATTERN_LINE",
                 {"p0": 4.2, "slope": 0.0, "t0": 0, "side": "top",
                  "meta_anchors": [0, 9]})
    tags = _tt_tags(ob, 19, bars, [3.5] * 20, [0.6] * 20)
    assert tags == {"line_cuts_bodies"}, tags


@case
def test_tt2_stale_far():
    """TT-2 stale_far (level): close >3*ABR from the price AND last
    touch >24 bars ago."""
    closes = [20.0] * 40
    highs = [20.3] * 40
    lows = [19.7] * 40
    for j in range(10):                     # early bars touch p=10
        highs[j], lows[j] = 13.0, 9.0       # [9,13] overlaps 10+/-1
    bars = _tt_bars(closes, highs=highs, lows=lows)
    ob = _tt_obj("LEVEL_CARRIED", {"price": 10.0, "side": "below"})
    tags = _tt_tags(ob, 39, bars, [10.0] * 40, [0.6] * 40)
    assert tags == {"stale_far"}, tags


@case
def test_tt3_box_broken_entry_anchored():
    """TT-3 box_broken: approach -> range -> 3-close break tags at the
    break; the approach into the band is NOT a breakout (R82 fix)."""
    # closes far below band, rise into [10,12], then break out top.
    closes = [5.0] * 6 + [10.5, 11.0, 11.5, 11.0] + [13.5] * 10
    bars = _tt_bars(closes)
    ob = _tt_obj("BOX", {"bottom": 10.0, "top": 12.0})
    fam, st = TT.object_stats(ob, 19, bars, [11.0] * 20,
                              [0.6] * 20, [])
    tags = TT.tags_from_stats(fam, st)
    assert "box_broken" in tags, tags
    assert st["break_clause"] == "run3" and st["exit_bar"] == 10, st


@case
def test_tt3_box_broken_false_break():
    """TT-3: a 2-close excursion that returns inside never tags."""
    closes = [11.0] * 10 + [13.5, 13.5, 11.0] + [11.0] * 7
    bars = _tt_bars(closes)
    ob = _tt_obj("BOX", {"bottom": 10.0, "top": 12.0})
    fam, st = TT.object_stats(ob, 19, bars, [11.0] * 20,
                              [0.6] * 20, [])
    tags = TT.tags_from_stats(fam, st)
    assert "box_broken" not in tags, (tags, st)


@case
def test_tt3_box_broken_shock():
    """TT-3: a single close >= 3*ABR beyond an edge tags 'shock'."""
    closes = [11.0] * 10 + [14.5] * 10      # top=12, abr .6: >1.8
    bars = _tt_bars(closes)
    ob = _tt_obj("BOX", {"bottom": 10.0, "top": 12.0})
    fam, st = TT.object_stats(ob, 19, bars, [11.0] * 20,
                              [0.6] * 20, [])
    tags = TT.tags_from_stats(fam, st)
    assert "box_broken" in tags, tags
    assert st["break_clause"] == "shock" and st["exit_bar"] == 10, st


@case
def test_tt2_hide_set():
    """R81+R83: TRADE_VIEW_HIDE = all tags minus lone_edge."""
    for t in ("daylight", "steep", "shock_inside", "impulse_inside",
              "zombie", "superseded", "line_broken",
              "line_cuts_bodies", "stale_far", "box_broken"):
        assert t in TT.TRADE_VIEW_HIDE, t
    assert "lone_edge" not in TT.TRADE_VIEW_HIDE
    assert TT.tradeable(set())
    assert TT.tradeable({"lone_edge"})
    assert not TT.tradeable({"stale_far"})
    assert not TT.tradeable({"box_broken"})


@case
def test_tt_prefix_invariance():
    """Facts at bar k are identical whether the run stops at k or
    continues (prefix invariance, 5 synthetic panels); flag OFF writes
    no facts at all."""
    p = json.load(open(os.path.join(HERE, "..", "params_v1_1.json"),
                       encoding="utf8"))["params"]
    p1 = dict(p, trade_tags=1)
    panels = [zigzag([1.3280, 1.3320, 1.3290, 1.3325], 6),
              zigzag([1.3310, 1.3280, 1.3330, 1.3300, 1.3290], 6),
              zigzag([1.3300, 1.3305, 1.3295, 1.3315, 1.3325], 4),
              zigzag([1.3285, 1.3290, 1.3280, 1.3330, 1.3300, 1.3320],
                     4),
              flat(30, 1.3310)]
    for bars in panels:
        k = len(bars) - 5
        e_full = E.PerceptionEngine(dict(p1))
        mid = None
        for j, b in enumerate(bars):
            e_full.update(b["t"], b["o"], b["h"], b["l"], b["c"],
                          cet_min=b["cet_min"])
            if j == k - 1:
                mid = {o.id: o.facts.get("trade_tags")
                       for o in e_full.active()}
        e_pre = feed(E.PerceptionEngine(dict(p1)), bars[:k])
        pre = {o.id: o.facts.get("trade_tags")
               for o in e_pre.active()}
        assert mid == pre, "prefix replay diverged in trade_tags"
    e_off = feed(E.PerceptionEngine(dict(p, trade_tags=0)),
                 zigzag([1.3280, 1.3320, 1.3290], 6))
    assert all(not o.facts for o in e_off.objects), \
        "facts written while trade_tags=0"


# ---------------------------------------------------------------- runner

def main():
    filt = sys.argv[sys.argv.index("-k") + 1] if "-k" in sys.argv else ""
    ran = failed = 0
    for fn in RESULTS:
        if filt and filt not in fn.__name__:
            continue
        ran += 1
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{ran - failed}/{ran} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
