"""EVAL-AUDIT STABLE C-3 freeze verification (R68 s.68.4 / R70 s.70.2).

Runs the CURRENT on-disk engine (default params = the folded
uip2_pbbirth set) over every TUNE record and compares canonical()
(output objects + cand_log + events) against the measured arm's cache
run_uip2_pbbirth_8361fe85e73f9437_*.  Disk is post-A1 (kernel.py
extraction); an identical result verifies BOTH the C-3 params fold and
the A1 pure-move identity in one pass.

Usage: python evalcheck/_c3_freeze_check.py
"""
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)

import common as C                              # noqa: E402
import cache as CA                              # noqa: E402
import engine as ENG                            # noqa: E402

ARM_H = "8361fe85e73f9437"
ARM_V = "uip2_pbbirth"


def main():
    import funnel as F
    h_now = F.code_hash(F.V1_FILES)
    print("on-disk code_hash at start:", h_now)
    recs = C.load_tune()
    by_key = {(r["date"], r["window"]["x1"] or 1439): r for r in recs}
    import glob
    arm_files = glob.glob(os.path.join(
        CA.CACHE, "run_%s_%s_*.pkl" % (ARM_V, ARM_H)))
    n = same_obj = same_log = same_ev = miss = 0
    diffs = []
    for ref in sorted(arm_files):
        stem = os.path.basename(ref)[:-4]
        date, w1s = stem.rsplit("_", 2)[1:]
        w1 = int(w1s)
        rec = by_key.get((date, w1))
        if rec is None:
            # tau-truncated run: base rec = same date, window contains w1
            base = next((r for r in recs
                         if r["date"] == date
                         and r["window"]["x0"] <= w1
                         <= (r["window"]["x1"] or 1439)), None)
            if base is None:
                miss += 1
                continue
            rec = dict(base, window=dict(base["window"], x1=w1))
        e_new = CA.run(h_now, ENG.PerceptionEngine, rec, store=False,
                       variant="c3chk")
        e_ref = pickle.load(open(ref, "rb"))
        n += 1
        _ot = lambda o: (o.type, o.why, o.t_birth, o.t_left, o.t_right,
                         o.state, o.id, o.geometry, o.events,
                         getattr(o, "score", None),
                         getattr(o, "priority", None),
                         getattr(o, "touches", None))
        so = CA._canon([_ot(o) for o in e_new.objects]) == \
            CA._canon([_ot(o) for o in e_ref.objects])
        sl = CA._canon(e_new.cand_log) == CA._canon(e_ref.cand_log)
        se = CA.canonical(e_new) == CA.canonical(e_ref)
        same_obj += so
        same_log += sl
        same_ev += se
        if not (so and sl and se):
            diffs.append((rec["id"], rec["date"], w1, so, sl, se))
    print("compared %d runs (miss %d) | objects %d/%d | cand_log %d/%d "
          "| events %d/%d" % (n, miss, same_obj, n, same_log, n,
                              same_ev, n))
    for d in diffs[:15]:
        print("  DIFF", d)
    h_end = F.code_hash(F.V1_FILES)
    print("on-disk code_hash at end:", h_end,
          "(stable)" if h_end == h_now else "(MOVED during run!)")


if __name__ == "__main__":
    main()
