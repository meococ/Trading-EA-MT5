"""test_ruler.py — known-answer tests for the window-stretch ruling.

R9/R9a acceptance cases, run with real eval.py / eval_v2 match paths:
  (a) an ACTIVE engine box ending at the panel edge w1 must match the
      identical golden box (golden drawn edge also at w1);
  (b) a box CLOSED at the golden drawn t1 must match;
  (c) the same active box stretched to the day end (len(m)-1) must FAIL
      under the pre-R9.1 conversion and MATCH once clipped by the
      frozen eval_v2 conversion;
  (d) an engine claiming t1_drawn = day end is clipped to w1;
  (e) an ACTIVE engine box vs a golden box whose drawn edge closed
      early: strict drawn-span IoU fails it, containment IoU matches —
      the residual strict defect post-R9.1.

Engine objects are faked as SimpleNamespace with exactly the attributes
eval.eng_objects / eval_v2.eng_objects read — no engine run needed.
Engine-side times are BAR INDICES; golden-side times are MINUTES.
"""
import os
import sys
from types import SimpleNamespace

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402

PIP = EV.PIP
recs = C.load_tune()
rec = recs[0]
_t, m, _o, _h, _l, _c = EV.day_bars(rec["date"])
w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
FED_END = int(np.searchsorted(m, w1))           # last bar fed to engine


def bar(minute):
    return int(np.searchsorted(m, minute))


def fake_engine(t_left, t_right, lo, hi, bs=None, be=None,
                t1_drawn=None):
    """A BOX object as engine_v1 produces it (geometry carries
    meta_build_* + break_bar).  t_right=None -> ACTIVE."""
    geom = {"top": hi, "bottom": lo}
    if bs is not None:
        geom["meta_build_start"] = bs
        geom["meta_build_end"] = be
    if t1_drawn is not None:
        geom["t1_drawn"] = t1_drawn
    e = SimpleNamespace(objects=[], bars=list(range(FED_END + 1)))
    o = SimpleNamespace(
        type="BOX", why="test", t_birth=t_left, t_left=t_left,
        t_right=t_right, geometry=geom, events=[], id="t", state="x")
    e.objects.append(o)
    return e


def gold_box(t0, t1, bs, be):
    return {"spec_type": "BOX", "t0": t0, "t1": t1,
            "price_lo": 20.0 * PIP, "price_hi": 30.0 * PIP,
            "precision": "meas", "build_start": bs, "build_end": be}


# containment window 300..360 for every case
BS, BE = 300, 360
G_ACTIVE = gold_box(BS, w1, BS, BE)              # drawn to panel edge
G_CLOSED = gold_box(BS, 400, BS, BE)             # drawn edge closed 400


def strict_match(gold, e_obj, conv):
    eobjs = conv(e_obj, m, w0, w1)
    assert len(eobjs) == 1, "engine record dropped"
    return EV.match(gold, eobjs[0], m), eobjs[0]


def v2_match(gold, e_obj):
    eobjs = V2.eng_objects(e_obj, m, w0, w1)
    assert len(eobjs) == 1, "engine record dropped"
    ok, route = V2.match_detail(gold, eobjs[0], m)
    return ok, route, eobjs[0]


results = []

# (a) ACTIVE box at the panel edge, golden also drawn to w1 ------------
e_a = fake_engine(bar(BS), t_right=None, lo=20.0, hi=30.0,
                  bs=bar(BS), be=bar(BE))
ok_now, rec_now = strict_match(G_ACTIVE, e_a, EV.eng_objects)
ok_v2, route, _ = v2_match(G_ACTIVE, e_a)
results.append(("a active@w1   strict(now)    ", ok_now))
results.append(("a active@w1   eval_v2        ", ok_v2))
assert rec_now["t1"] == w1, rec_now["t1"]       # last FED bar = w1
assert ok_now, "post-R9.1 eval.py should match the active box"
assert ok_v2 and route == "containment_iou", (ok_v2, route)

# (b) box CLOSED at the golden drawn t1 --------------------------------
e_b = fake_engine(bar(BS), t_right=bar(400), lo=20.0, hi=30.0,
                  bs=bar(BS), be=bar(BE))
ok_now, _ = strict_match(G_CLOSED, e_b, EV.eng_objects)
ok_v2, route, _ = v2_match(G_CLOSED, e_b)
results.append(("b closed@t1   strict(now)    ", ok_now))
results.append(("b closed@t1   eval_v2        ", ok_v2))
assert ok_now and ok_v2 and route == "containment_iou", (ok_now, ok_v2,
                                                       route)

# (c) same ACTIVE box under the PRE-R9.1 conversion --------------------
e_c = fake_engine(bar(BS), t_right=None, lo=20.0, hi=30.0,
                  bs=bar(BS), be=bar(BE))
ok_old, rec_old = strict_match(G_ACTIVE, e_c, V2.eng_objects_pre_r91)
results.append(("c stretched   strict(pre-R9.1)", ok_old))
assert rec_old["t1"] == m[len(m) - 1], (rec_old["t1"], m[-1])
assert not ok_old, "pre-R9.1 conversion must FAIL the same box"
ok_v2, route, rec_v2 = v2_match(G_ACTIVE, e_c)
results.append(("c clipped     eval_v2        ", ok_v2))
assert rec_v2["t1"] == w1, rec_v2["t1"]
assert ok_v2, "clipped conversion must match the same box"

# (d) engine claims t1_drawn = day end -> clipped to w1 -----------------
e_d = fake_engine(bar(BS), t_right=None, lo=20.0, hi=30.0,
                  bs=bar(BS), be=bar(BE), t1_drawn=len(m) - 1)
ok_v2, route, rec_d = v2_match(G_ACTIVE, e_d)
results.append(("d drawn=dayend eval_v2(clip) ", ok_v2))
assert rec_d["t1"] == w1, rec_d["t1"]
assert ok_v2

# (e) ACTIVE engine box vs golden drawn-closed-early -------------------
ok_now, _ = strict_match(G_CLOSED, e_a, EV.eng_objects)
ok_v2, route, _ = v2_match(G_CLOSED, e_a)
results.append(("e active vs drawn-closed strict", ok_now))
results.append(("e active vs drawn-closed v2    ", ok_v2))
assert not ok_now, "strict drawn-span IoU must still fail this"
assert ok_v2 and route == "containment_iou", (ok_v2, route)

# (f) R11: coverage REFUSED when both sides record real windows and the
#     containment IoU < 0.5 (engine built 300..320 inside golden
#     300..360 -> IoU 0.33; drawn span still covers the golden window).
#     The pair is "located" (right place, wrong extent) but NOT a match.
e_f = fake_engine(bar(300), t_right=bar(400), lo=20.0, hi=30.0,
                  bs=bar(300), be=bar(320))
g_f = gold_box(300, 400, 300, 360)
ok_v2, route, rec_f = v2_match(g_f, e_f)
results.append(("f IoU<0.5 coverage refused    ", ok_v2))
assert not ok_v2 and route == "box_span", (ok_v2, route)
assert V2.box_located(g_f, rec_f, m), "located diagnostic must fire"

# (g) R11: coverage ALLOWED when the engine side records no containment
#     window at all (no bs/be/break_bar -> drawn span 300..500; IoU vs
#     golden window = 0.30, coverage = 1.00 -> route "coverage").
e_g = fake_engine(bar(300), t_right=bar(500), lo=20.0, hi=30.0)
ok_v2, route, _ = v2_match(g_f, e_g)
results.append(("g no eng window -> coverage    ", ok_v2))
assert ok_v2 and route == "coverage", (ok_v2, route)

# (h) R11: coverage ALLOWED when the GOLDEN side records no containment
#     window (degenerate/absent -> resolved to drawn span).
g_h = gold_box(300, 360, None, None)
ok_v2, route, _ = v2_match(g_h, e_g)
results.append(("h no gold window -> coverage   ", ok_v2))
assert ok_v2 and route == "coverage", (ok_v2, route)

print("panel window w0..w1 = %d..%d ; fed bars 0..%d ; day-end bar = %d"
      % (w0, w1, FED_END, m[len(m) - 1]))
for name, ok in results:
    print("  %-36s -> %s" % (name, "MATCH" if ok else "no match"))
print("\nALL KNOWN-ANSWER TESTS PASSED")
