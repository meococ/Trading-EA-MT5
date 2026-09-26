"""EVAL-AUDIT s.63.3: price option C - clutter counted as objects LIVE
at tau instead of every object intersecting the window.

Two live definitions, reported side by side:
  C-strict: engine object state == "ACTIVE" at the end of the
    tau-truncated run == literally on screen when the decision is made.
  C-loose : snapshot.live_records semantics (state != DELETED) - what
    the ranker actually sees; includes CLOSED-but-still-drawn objects.
LABEL_TF marks counted when live (matches today's numerator which
includes emarks).

Per panel the live count is taken at EVERY golden tau; the panel's
live-ink = mean over its taus (headline) and value at the last tau
(sensitivity).  Ratio = live_ink / len(scorable goldens), same
denominator as today's clutter.  Rows: parent, hybrid, evb_on,
evb2_on.  Cache-only.
"""
import collections
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import funnel as F                              # noqa: E402
from snapshot import tau_of                     # noqa: E402
from salience import FAMILY                     # noqa: E402

H1 = "ee2cbf1202db47b6"   # c1r_p_base == STABLE C-2 4c2df34d (F1 id)
V1 = "c1r_p_base"
H0 = "63c771d64e18f619"
V0 = "m1_v0"
ARMS = [("evb_on", "be204b980694216e"),
        ("evb2_on", "b07b8af4837476fb")]


def _pk(h, v, rec, w1):
    f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                     % (v, h, rec["date"], w1))
    if not os.path.exists(f):
        return None
    try:
        return pickle.load(open(f, "rb"))
    except Exception:
        return None


def _active(e, w0, tau, m):
    """Records of objects ACTIVE at run end (run truncated at tau),
    clipped to the window - plus live LABEL_TF count."""
    shim = type("S", (), {"objects": [o for o in e.objects
                                      if o.state == "ACTIVE"],
                          "bars": e.bars})
    recs = V2.eng_objects(shim, m, w0, tau)
    nl = [r for r in recs if r["type"] != "LABEL_TF"]
    lt = [r for r in recs if r["type"] == "LABEL_TF"]
    return nl, lt


def _loose(e, w0, tau, m):
    shim = type("S", (), {"objects": [o for o in e.objects
                                      if o.state != "DELETED"],
                          "bars": e.bars})
    recs = V2.eng_objects(shim, m, w0, tau)
    nl = [r for r in recs if r["type"] != "LABEL_TF"]
    lt = [r for r in recs if r["type"] == "LABEL_TF"]
    return nl, lt


def panel_live_rows(recs, box_side, other_side):
    """Per panel: for each golden tau, live ink under both defs.
    box_side/other_side in {'v1','v0','ARM:<variant>@<hash>'}."""
    def src(side):
        if side == "v1":
            return H1, V1
        if side == "v0":
            return H0, V0
        v, h = side.split("@")[0], side.split("@")[1]
        return h, v

    hb, vb = src(box_side)
    ho, vo = src(other_side)
    out = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        _t, m, _o, _h, _l, _c = CA.bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        if not g2:
            continue
        taus = sorted({min(tau_of(g), w1) for g in g2
                       if tau_of(g) is not None and tau_of(g) >= w0})
        s_counts, l_counts, s_box, l_box = [], [], [], []
        for tau in taus:
            eB = _pk(hb, vb, rec, tau)
            eO = _pk(ho, vo, rec, tau)
            if eB is None or eO is None:
                continue
            for counts, boxc, fn in ((s_counts, s_box, _active),
                                     (l_counts, l_box, _loose)):
                nlO, ltO = fn(eO, w0, tau, m)
                nlB, ltB = fn(eB, w0, tau, m)
                comb = [r for r in nlO
                        if FAMILY.get(r["type"]) != "box"]
                comb += [r for r in nlB
                         if FAMILY.get(r["type"]) == "box"]
                # LABEL_TF comes from the 'other' (v1) side
                counts.append(len(comb) + len(ltO))
                boxc.append(sum(1 for r in comb
                                if FAMILY.get(r["type"]) == "box"))
        if not s_counts:
            continue
        out.append({"panel": rec["id"], "date": rec["date"], "g": len(g2),
                    "s": s_counts, "l": l_counts,
                    "sb": s_box, "lb": l_box})
    return out


def summarize(tag, rows):
    def meds(key):
        mean_r = [np.mean(r[key]) / r["g"] for r in rows]
        last_r = [r[key][-1] / r["g"] for r in rows]
        return (np.median(mean_r), np.mean(mean_r) <= 5.0,
                sum(x <= 5.0 for x in mean_r), len(mean_r),
                np.median(last_r), sum(x <= 5.0 for x in last_r))
    sm, _ok, smarg, n, sl, slmarg = meds("s")
    lm, _ok2, lmarg, _n2, ll, llmarg = meds("l")
    sb = np.mean([np.mean(r["sb"]) for r in rows])
    print("%-26s | strict: med %.2f (last %.2f) margin %d/%d (%d) | "
          "loose: med %.2f (last %.2f) margin %d (%d) | "
          "live-box med %.2f"
          % (tag, sm, sl, smarg, n, slmarg, lm, ll, lmarg, llmarg, sb))
    return sm, smarg, lm, lmarg


def main():
    recs = C.load_tune()
    print("live-at-tau clutter (ratio = live objects / scorable "
          "goldens); 'strict'=ACTIVE at tau, 'loose'=not-DELETED")
    print("today's def (window census): parent 4.33/114 | hybrid "
          "5.67/77 | evb_on 6.00/71 | evb2_on 5.67/80 | v0 9.00/21")
    rows = {}
    rows["parent (C-2)"] = panel_live_rows(recs, "v1", "v1")
    summarize("parent (C-2)", rows["parent (C-2)"])
    rows["v0"] = panel_live_rows(recs, "v0", "v0")
    summarize("v0 (both sides)", rows["v0"])
    rows["hybrid v1+v0box"] = panel_live_rows(recs, "v0", "v1")
    summarize("hybrid v1+v0box", rows["hybrid v1+v0box"])
    for var, h in ARMS:
        tag = "%s@%s" % (var, h[:8])
        rows[tag] = panel_live_rows(recs, "ARM", "ARM") \
            if False else None
        # single-source arm: both sides = the arm
        hb = vb = var
        # reuse machinery with a synthetic side
        def arm_panel_rows(recs, var=var, h=h):
            out = []
            for rec in recs:
                w0 = rec["window"]["x0"]
                w1 = rec["window"]["x1"] or 1439
                _t, m, _o, _h, _l, _c = CA.bars(rec["date"])
                gobjs, _u, _to = EV.gold_objects(rec)
                g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
                if not g2:
                    continue
                taus = sorted({min(tau_of(g), w1) for g in g2
                               if tau_of(g) is not None
                               and tau_of(g) >= w0})
                s_counts, l_counts, s_box = [], [], []
                for tau in taus:
                    e = _pk(h, var, rec, tau)
                    if e is None:
                        continue
                    nl, lt = _active(e, w0, tau, m)
                    s_counts.append(len(nl) + len(lt))
                    s_box.append(sum(1 for r in nl
                                     if FAMILY.get(r["type"]) == "box"))
                    nl2, lt2 = _loose(e, w0, tau, m)
                    l_counts.append(len(nl2) + len(lt2))
                if s_counts:
                    out.append({"panel": rec["id"], "date": rec["date"],
                                "g": len(g2), "s": s_counts,
                                "l": l_counts, "sb": s_box,
                                "lb": s_box})
            return out
        rr = arm_panel_rows(recs)
        rows[tag] = rr
        summarize(tag, rr)
    out = os.path.join(HERE, "_live_clutter_rows.pkl")
    pickle.dump(rows, open(out, "wb"))
    print("rows ->", out)


if __name__ == "__main__":
    main()
