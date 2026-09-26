"""Known-answer tests for boxes_lab lifecycle/dedup — X3 gate.

Synthetic objects only; no panel data needed.  Run:
    python -m pytest tests/        (or)   python tests/test_lifecycle.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import boxes_lab as BL  # noqa: E402


def _mk_engine():
    e = BL.BoxLabEngine()
    # minimal bars array so _dup_hit/_birth day math works
    e.bars = [{"t": i * 300, "cet_min": (i * 5) % 1440,
               "c": 100.0, "h": 100.0, "l": 100.0}
              for i in range(500)]
    return e


def _mk_obj(e, i, top, bot, bs, be, score=5.0):
    o = BL.Obj("BOX", i, {"top": top, "bottom": bot,
                          "build_start": bs, "build_end": be,
                          "t1_drawn": None, "score": score},
               why="test", t_left=bs)
    o.id = "T%03d" % len(e.objects)
    e.objects.append(o)
    return o


def test_tail():
    """Break marks BROKEN + build_end=break bar; box stays live for
    tail_bars then closes (R21 §21.3)."""
    e = _mk_engine()
    o = _mk_obj(e, 10, 105.0, 95.0, 0, 10)
    # contained bars extend build_end
    e._maintain(11, {"c": 100.0, "h": 100.5, "l": 99.5})
    assert o.geometry["build_end"] == 11 and o.state == "ACTIVE"
    # decisive close above top edge -> BROKEN, still drawn
    e._maintain(12, {"c": 106.0, "h": 106.5, "l": 99.5})
    assert o.state == "BROKEN"
    assert o.geometry["break_bar"] == 12
    assert o.geometry["build_end"] == 12
    # live through the tail (live check = state in ACTIVE/BROKEN)
    live = [x for x in e.objects
            if x.state in ("ACTIVE", "BROKEN")]
    assert o in live
    # tail expires -> CLOSED
    e._maintain(12 + e.p["tail_bars"], {"c": 106.0, "h": 106.5, "l": 99.5})
    assert o.state == "CLOSED"
    assert o.t_right == 12 + e.p["tail_bars"]
    print("test_tail ok")


def test_dedup_window():
    """Same edges + window IoU >= nest_iou_min -> same episode;
    same edges + low window IoU -> NOT (r37 fix)."""
    e = _mk_engine()
    g = {"top": 105.0, "bottom": 95.0, "build_start": 10,
         "build_end": 20}
    # same edges, overlapping window (IoU ~0.82) -> same episode
    assert e._same_episode(g, 95.0, 105.0, 12, 22)
    # same edges, disjoint window -> different band, must not block
    assert not e._same_episode(g, 95.0, 105.0, 30, 40)
    # different edges -> never same episode
    assert not e._same_episode(g, 90.0, 105.0, 12, 22)
    print("test_dedup_window ok")


def test_displace():
    """At max_live: weak challenger rejected; strong challenger
    displaces weakest; a BROKEN tail is cut before any ACTIVE box."""
    e = _mk_engine()
    a = _mk_obj(e, 10, 105.0, 95.0, 0, 10, score=5.0)
    b = _mk_obj(e, 20, 205.0, 195.0, 10, 20, score=7.0)

    weak_feats = {"lo": 300.0, "hi": 310.0, "t0": 0, "abr": 10.0,
                  "prom_min": 0.0, "prom_sum": 0.0, "hgt": 80.0,
                  "edge_gap": 0.0, "deeper_lv": 5.0, "barrier": 1.0,
                  "n_piv": 0}
    weak_w = {"best": weak_feats}
    # weak challenger (score ~0) cannot displace
    assert e._birth_ok(weak_w, 30) is False
    # a BROKEN incumbent is cut first regardless of challenger score
    b.state = "BROKEN"
    b.geometry["break_bar"] = 25
    assert e._birth_ok(weak_w, 30) is True
    assert b.state == "CLOSED"
    print("test_displace ok")


def test_frozen_geometry():
    """Born geometry comes from the watch's best-ever qualified
    snapshot, not the drifted current feats (r35)."""
    e = _mk_engine()
    w = {"born": False,
         "best": {"lo": 95.0, "hi": 105.0, "t0": 0, "abr": 10.0,
                  "prom_min": 30.0, "prom_sum": 30.0, "hgt": 10.0,
                  "edge_gap": 0.0, "deeper_lv": 0.0, "barrier": 0.0,
                  "n_piv": 5},
         "feats": {"lo": 97.0, "hi": 108.0, "t0": 0, "abr": 10.0,
                   "prom_min": 0.0, "prom_sum": 0.0, "hgt": 11.0,
                   "edge_gap": 0.0, "deeper_lv": 0.0, "barrier": 0.0,
                   "n_piv": 0},
         "born_t0": 0, "top": None, "bot": None}
    o = e._birth(w, 50, "mature")
    assert o.geometry["top"] == 105.0 and o.geometry["bottom"] == 95.0
    # edge_track off -> later maintain must not move the edges
    e._maintain(51, {"c": 100.0, "h": 100.5, "l": 99.5})
    assert o.geometry["top"] == 105.0
    print("test_frozen_geometry ok")


if __name__ == "__main__":
    test_tail()
    test_dedup_window()
    test_displace()
    test_frozen_geometry()
    print("all tests passed")
