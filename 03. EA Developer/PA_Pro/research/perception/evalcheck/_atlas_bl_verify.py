"""EVAL-AUDIT s.77.4a: independent recompute of the PA-ATLAS baseline
rows (bl_tdlines_k2 / bl_donchian_alt / bl_darvas_n7) + budget
accounting check + prefix invariance on 5 panels.

Own scoring loop: the baselines' emit() is the device under test
(their objects); scoring is mine (eval_v2.match + per-family top-k
WITHOUT the harness's global max_objs=6 cap; both conventions
reported so the budget accounting difference is visible).

Prefix invariance: emit() on the full day vs emit() on bars
truncated at tau must produce the same live-at-tau object set
(causality check), on the first 5 panels that have tau-runs.

Usage: python evalcheck/_atlas_bl_verify.py
"""
import collections
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
BASE = os.path.join(PERC, "practice", "baselines")
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, BASE)

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import bl_common as BL                          # noqa: E402
from snapshot import tau_of                     # noqa: E402

import b_tdlines                                # noqa: E402
import b_donchian                               # noqa: E402
import b_darvas                                 # noqa: E402

ARMS = [("bl_tdlines_k2", b_tdlines.emit, "line", 2),
        ("bl_donchian_alt", b_donchian.emit, "level", 1),
        ("bl_darvas_n7", b_darvas.emit, "box", 1)]
FAMS = ("box", "level", "line")
KS = {"box": 1, "level": 1, "line": 2}


def score_emit(emit, recs, global_cap):
    """Per-(panel,tau) hits with per-family top-k; global_cap=None is
    the pure per-family budget, global_cap=6 mirrors the harness."""
    hits = collections.Counter()
    gold = collections.Counter()
    ratios = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        abr = CA.abr(rec["date"])
        objs = emit(t, m, o, h, l, c, abr) or []
        vis = [x for x in objs if x["birth"] <= w1
               and (x["die"] is None or x["die"] > w0)]
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        if g2:
            ratios.append(len(vis) / len(g2))
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is not None and tau >= w0:
                by_tau[min(tau, w1)].append(g)
        for tau, gs in by_tau.items():
            live = [x for x in objs if x["birth"] <= tau
                    and (x["die"] is None or x["die"] > tau)]
            jl = min(int(np.searchsorted(m, tau)), len(m) - 1)
            live = [BL._rec(x, w0, tau, int(m[jl])) for x in live]
            live.sort(key=lambda r: (-r["_score"], -r["t_birth"]))
            if global_cap is not None:
                live = live[:global_cap]
            fam_r = collections.defaultdict(list)
            for r in live:
                f = EV.FAMILY.get(r["type"])
                if f:
                    fam_r[f].append(r)
            for g in gs:
                fg = EV.FAMILY.get(g["spec_type"])
                if not fg:
                    continue
                gold[fg] += 1
                top = fam_r.get(fg, [])[:KS.get(fg, 1)]
                if any(V2.match(g, r, m) for r in top):
                    hits[fg] += 1
    return hits, gold, float(np.median(ratios)) if ratios else float("nan")


def prefix_check(emit, recs, n=5):
    """emit(truncated day) live-at-tau == emit(full day) live-at-tau."""
    done = 0
    for rec in recs:
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        abr = CA.abr(rec["date"])
        taus = set()
        gobjs, _u, _to = EV.gold_objects(rec)
        for g in gobjs:
            tau = tau_of(g)
            if tau is not None and rec["window"]["x0"] <= tau < w1:
                taus.add(tau)
        if not taus:
            continue
        tau = sorted(taus)[0]
        jt = int(np.searchsorted(m, tau, side="right"))
        objs_full = emit(t, m, o, h, l, c, abr) or []
        objs_cut = emit(t[:jt], m[:jt], o[:jt], h[:jt], l[:jt],
                        c[:jt], abr[:jt]) or []
        # live-at-tau identity IGNORES die: a post-tau death is
        # unknowable at tau (die>tau and die=None are the same state).
        def key(x):
            return (x["type"], x["birth"], x["birth_drawn"],
                    repr(x.get("lo")), repr(x.get("hi")),
                    repr(x.get("price")), repr(x.get("p0")),
                    repr(x.get("slope")))
        live_f = {key(x) for x in objs_full if x["birth"] <= tau
                  and (x["die"] is None or x["die"] > tau)}
        live_c = {key(x) for x in objs_cut if x["birth"] <= tau
                  and (x["die"] is None or x["die"] > tau)}
        ok = live_f == live_c
        print("  %s tau=%d full-live=%d trunc-live=%d %s"
              % (rec["id"], tau, len(live_f), len(live_c),
                 "OK" if ok else "MISMATCH"))
        done += 1
        if done >= n:
            break
    return done


def main():
    recs = C.load_tune()
    for tag, fn, tfam, tk in ARMS:
        print("=" * 60)
        print(tag)
        h6, g6, r6 = score_emit(fn, recs, global_cap=6)
        hn, gn, rn = score_emit(fn, recs, global_cap=None)
        for fam in FAMS:
            print("  %s@%d  cap6 %d/%d | nocap %d/%d"
                  % (fam, KS[fam], h6[fam], g6[fam], hn[fam], gn[fam]))
        print("  clutter med: cap6 %.2f | nocap %.2f" % (r6, rn))
        print("  prefix invariance (5 panels):")
        n = prefix_check(fn, recs)
        if not n:
            print("    (no tau-rows found)")


if __name__ == "__main__":
    main()
