"""_retire_ab.py — R14 §14.3 per-rule retirement audit for one engine
hash (must already be in evalcheck/_cache).

Usage: python _retire_ab.py <hash> [label]

Prints retirements by close-reason, bad retirements (retired object
matches a golden object under the ruler whose golden span runs
>= 3 bars past the retirement bar), cumulative recall per family,
snapshot live clutter median + snapshot recall.
"""
import collections
import sys

sys.path.insert(0, "evalcheck")
sys.path.insert(0, ".")

import numpy as np

import common as C
import eval as EV
import eval_v2 as V2
import cache as CA
from snapshot import tau_of, live_records

REASONS = ("retire_far", "retire_stale", "wall_exit", "wall_gone")
BAR_MIN = 5


def eng_obj_record(o, m):
    """Closed Pobj -> minute-space record mirroring V2.eng_objects."""
    g = o.geometry
    t0m, t1m = V2._min(m, o.t_left), V2._min(m, o.t_right)
    r = {"type": o.type, "t0": t0m, "t1": t1m, "t0_raw": t0m,
         "t1_raw": t1m, "id": o.id}
    if "top" in g:
        r["lo"], r["hi"] = g["bottom"], g["top"]
    if "price" in g:
        r["price"], r["side"] = g["price"], g.get("side")
    if "p0" in g:
        r["p0"] = g["p0"]
        r["slope"] = g["slope"]
        r["t0_bar"] = g["t0"]
        r["side"] = g.get("side")
        r["dirn"] = 1 if g["slope"] > 0.05 else \
            (-1 if g["slope"] < -0.05 else 0)
    if "letter" in g:
        r["letter"] = g["letter"]
    if g.get("level") is not None:
        r["price"] = g["level"]
    return r


def main():
    eng_hash = sys.argv[1]
    tag = sys.argv[2] if len(sys.argv) > 2 else eng_hash[:8]
    import engine
    cls = engine.PerceptionEngine
    recs = C.load_tune()
    ret_n = collections.Counter()
    bad_n = collections.Counter()
    hit_g = collections.Counter()
    gold_n = collections.Counter()
    clutter = []
    snap_g = 0
    snap_h = 0
    snap_fam_h = collections.Counter()
    snap_fam_g = collections.Counter()
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        e = CA.run(eng_hash, cls, rec)
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        eobjs = V2.eng_objects(e, m, w0, w1)
        eboxes = [r for r in eobjs if r["type"] != "LABEL_TF"]
        pairs, _mp = C.match_panel(g2, eboxes, [], [], m,
                                   V2.match, V2.match_mark, V2.score)
        hg = {gi for gi, _ in pairs}
        for gi, g in enumerate(g2):
            gold_n[g["spec_type"]] += 1
            hit_g[g["spec_type"]] += gi in hg
        # retirement audit on ALL closed objects (incl out-of-window)
        for obj in e.objects:
            why = next((w for _i, ev, w in obj.events
                        if ev == "close"), None)
            if why not in REASONS or obj.t_right is None:
                continue
            ret_n[why] += 1
            ret_min = V2._min(m, obj.t_right)
            er = eng_obj_record(obj, m)
            for g in g2:
                if V2.match(g, er, m) and g["t1"] >= ret_min + \
                        3 * BAR_MIN:
                    bad_n[why] += 1
                    break
        # snapshot lens
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            by_tau[min(tau, w1)].append(g)
        for tau, gs in by_tau.items():
            rec_t = dict(rec)
            rec_t["window"] = dict(rec["window"], x1=tau)
            e_t = CA.run(eng_hash, cls, rec_t)
            eboxes_t, _em = live_records(e_t, m, w0, tau)
            clutter.append(len(eboxes_t))
            for g in gs:
                snap_g += 1
                snap_fam_g[g["spec_type"]] += 1
                if any(V2.match(g, er, m) for er in eboxes_t):
                    snap_h += 1
                    snap_fam_h[g["spec_type"]] += 1
    print("=== %s ===" % tag)
    print("retirements:", dict(ret_n.most_common()))
    print("bad retirements:", dict(bad_n.most_common()),
          " (golden span >=3 bars past retire bar)")
    for st in sorted(gold_n):
        print("  %-14s recall %3d/%-3d = %.3f" % (
            st, hit_g[st], gold_n[st],
            hit_g[st] / gold_n[st] if gold_n[st] else 0))
    print("  snapshot live clutter median %.2f | snap recall %d/%d = %.3f"
          % (np.median(clutter), snap_h, snap_g,
             snap_h / snap_g if snap_g else 0))
    for st in sorted(snap_fam_g):
        print("    snap %-14s %d/%d" % (st, snap_fam_h[st],
                                        snap_fam_g[st]))


if __name__ == "__main__":
    main()
