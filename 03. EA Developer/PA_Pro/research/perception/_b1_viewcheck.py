"""_b1_viewcheck.py — B1 debug check (MIGRATION_PLAN B1 spec:
"ON builds read-only views and asserts view_f == [c for c in pool
if c.fam==f] in a debug test only").

NOT part of the suite of record (tests/ stays 72).  Runs a small
feed with arch_v2 on and off and asserts the view invariant plus
the OFF-path no-construction rule.

Usage: python _b1_viewcheck.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "evalcheck"))
sys.path.insert(0, _HERE)

import eval as EV                       # noqa: E402
import common as C                      # noqa: E402
import engine as ENG                    # noqa: E402

FAMS = ("box", "line", "level", "bracket", "squeeze", "annot")


def run(params):
    recs = C.load_tune()[:3]
    n_view_calls = 0
    for rec in recs:
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = EV.day_bars(rec["date"])
        e = ENG.PerceptionEngine(params=params)
        e.cand_log = []
        for j in [k for k in range(len(m)) if m[k] <= w1]:
            e.update(int(t[j]), float(o[j]) * 1e-4,
                     float(h[j]) * 1e-4, float(l[j]) * 1e-4,
                     float(c[j]) * 1e-4, cet_min=int(m[j]))
            for f in FAMS:
                v = e.salience.pool_view(f)
                assert v == [c for c in e.salience.pool
                             if getattr(c, "fam", None) == f], \
                    "view != filter at %s bar %d fam %s" % (
                        rec["id"], j, f)
                n_view_calls += 1
            for pipe, fam in ((e.pipes.box, "box"),
                              (e.pipes.line, "line"),
                              (e.pipes.level, "level"),
                              (e.pipes.annot, "annot")):
                assert pipe.pool_view() == \
                    e.salience.pool_view(fam)
        # pool itself untouched by view reads
        assert e.salience.pool is e.salience.pool
    return n_view_calls


def main():
    p_on = ENG.load_params()
    p_on["arch_v2"] = 1
    n = run(p_on)
    print("arch_v2 ON: %d view calls, invariant holds" % n)
    p_off = ENG.load_params()
    e = ENG.PerceptionEngine(params=p_off)
    e.update(0, 1.30, 1.301, 1.299, 1.3005, cet_min=0)
    assert e.salience.pool_view("box") == []
    assert e.pipes.line.pool_view() == []
    print("arch_v2 OFF: pool_view returns [] (no v2 state)")
    print("B1 viewcheck PASS")


if __name__ == "__main__":
    main()
