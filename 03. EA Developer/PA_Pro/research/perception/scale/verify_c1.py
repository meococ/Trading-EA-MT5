"""verify_c1.py — prove arm C1 (snapshot 9acaa206, params_v1_1.json
defaults, K1-K6 ON) equals the cached m1_v1@9acaa206 TUNE runs.

Same pattern as verify_stable.py: re-runs the snapshot on 3 TUNE panels
and compares evalcheck's canonical form (objects + cand_log + bars)
against evalcheck/_cache/run_m1_v1_9acaa206c8d386dc_*.pkl (read-only).

BOOK bars come from evalcheck's bars_*.npz cache; this lane never reads
the 2010-2015 parquet itself.

Usage: python scale/verify_c1.py
"""
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
SNAP = os.path.join(HERE, "engine_9acaa206")
EVALC = os.path.join(PERC, "evalcheck")
# snapshot first: unpickled cached runs must bind to the SAME engine
# module the fresh run uses
for _p in (SNAP, EVALC, PERC, os.path.join(PERC, "golden"),
           os.path.join(PERC, "..", "..", "lib")):
    _p = os.path.abspath(_p)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import engine as ENG                            # noqa: E402  snapshot copy
import cache as CA                              # noqa: E402  evalcheck, read-only

PANELS = [("2012-03-01", 600), ("2012-03-01", 840), ("2012-03-01", 1080)]


def fresh_run(date, w1):
    t, m, o, h, l, c = CA.bars(date)            # cached npz (no parquet)
    params = ENG.load_params(os.path.join(SNAP, "params_v1_1.json"))
    e = ENG.PerceptionEngine(params=params, feed="BOOK")
    e.cand_log = []
    for j in np.where(m <= w1)[0]:
        e.update(int(t[j]), float(o[j]) * 1e-4, float(h[j]) * 1e-4,
                 float(l[j]) * 1e-4, float(c[j]) * 1e-4,
                 cet_min=int(m[j]))
    return e


def main():
    ok = True
    for date, w1 in PANELS:
        f = os.path.join(CA.CACHE,
                         "run_m1_v1_9acaa206c8d386dc_%s_%d.pkl" % (date, w1))
        with open(f, "rb") as fh:
            e_ref = pickle.load(fh)
        e_new = fresh_run(date, w1)
        a = CA.canonical(e_ref)
        b = CA.canonical(e_new)
        same = a == b
        ok &= same
        print("%s w1=%d  objects ref=%d new=%d  cand_log ref=%s new=%s  "
              "canonical %s" % (
                  date, w1, len(e_ref.objects), len(e_new.objects),
                  len(e_ref.cand_log or []), len(e_new.cand_log or []),
                  "EQUAL" if same else "DIFF"))
        if not same:
            ra = [(o.type, o.why, o.t_birth, o.t_left, o.t_right,
                   o.state) for o in e_ref.objects]
            rb = [(o.type, o.why, o.t_birth, o.t_left, o.t_right,
                   o.state) for o in e_new.objects]
            for k, (x, y) in enumerate(zip(ra, rb)):
                if x != y:
                    print("   first object diff at #%d: %s vs %s"
                          % (k, x, y))
                    break
    print("C1-VERIFY:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
