"""identity_check.py — R23 §23.4: flag OFF at current engine hash must
be bit-identical to the 584c7743 STABLE default.

Reference: cached engine pickles `run_marker_off_584c7743*` in
evalcheck/_cache (the STABLE default arm).  Current: fresh flag-off
run (default params => defended_origin False) at the live code state.
Compared via cache.canonical (objects + cand_log + bars, pickled).
"""
import os
import pickle
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
sys.path.insert(0, _PERC)
sys.path.insert(0, os.path.join(_PERC, "golden"))
sys.path.insert(0, os.path.join(_PERC, "evalcheck"))
sys.path.insert(0, os.path.join(_PERC, "linelab"))
sys.path.insert(0, _HERE)

import bars_cache  # noqa: E402
import eval as EV  # noqa: E402
import cache as CA  # noqa: E402
import engine as ENG  # noqa: E402
import funnel as F  # noqa: E402

REF = "run_marker_off_584c7743924a8b1b"


def main():
    recs = bars_cache.tune_records()
    days = bars_cache.days()
    cur_hash = F.code_hash(F.V1_FILES)
    print("current engine hash: %s" % cur_hash)
    same = diff = miss = 0
    diffs = []
    for rec in recs:
        w1 = rec["window"]["x1"] or 1439
        f = os.path.join(CA.CACHE, "%s_%s_%s.pkl"
                         % (REF, rec["date"], w1))
        if not os.path.exists(f):
            miss += 1
            diffs.append((rec["id"], "no ref pickle"))
            continue
        with open(f, "rb") as fh:
            e_ref = pickle.load(fh)
        day = days[rec["date"]]
        e_cur = EV.run_engine(ENG.PerceptionEngine, day["m"], day["t"],
                              day["o"], day["h"], day["l"], day["c"], w1)
        c_ref, c_cur = CA.canonical(e_ref), CA.canonical(e_cur)
        if c_ref == c_cur:
            same += 1
        else:
            diff += 1
            # localize: objects first, then cand_log
            ob_ref = [(o.type, o.why, o.t_birth, o.t_left, o.t_right,
                       o.state, CA._canon(o.geometry))
                      for o in e_ref.objects]
            ob_cur = [(o.type, o.why, o.t_birth, o.t_left, o.t_right,
                       o.state, CA._canon(o.geometry))
                      for o in e_cur.objects]
            n_obj = sum(1 for a, b in zip(ob_ref, ob_cur) if a != b) \
                + abs(len(ob_ref) - len(ob_cur))
            n_cand = sum(1 for a, b in zip(e_ref.cand_log or [],
                                           e_cur.cand_log or [])
                         if CA._canon(a) != CA._canon(b)) \
                + abs(len(e_ref.cand_log or [])
                      - len(e_cur.cand_log or []))
            diffs.append((rec["id"], "obj_diffs=%d cand_diffs=%d"
                          % (n_obj, n_cand)))
    print("panels: %d identical, %d different, %d missing-ref"
          % (same, diff, miss))
    for d in diffs[:40]:
        print("  DIFF", d)


if __name__ == "__main__":
    main()
