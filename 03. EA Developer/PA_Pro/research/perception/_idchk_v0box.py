"""R63 s.63.4 prep: flag-OFF identity for the box_v0_family port.

Compares fresh engine runs at the CURRENT hash (all research flags
OFF = C-2 defaults) against the verified C-2 baseline pickles
a4b_off_54bd315b070afbd6 across EVERY cached (date, w1) combo -
the same 576-file canonical check used for the ev-route and UIP arms.
"""
import os
import pickle
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "evalcheck"))
sys.path.insert(0, _HERE)

import cache as CA
import eval as EV
import funnel as F
import engine as ENG

REF = "a4b_off_54bd315b070afbd6"


def sig(e):
    objs = [(o.id, o.type, o.t_birth, o.t_left, o.t_right, o.state,
             repr(sorted(o.geometry.items()))) for o in e.objects]
    cl = [repr(sorted(c.items())) if isinstance(c, dict) else repr(c)
          for c in (e.cand_log or [])]
    ev = [o.events for o in e.objects]
    return (objs, cl, ev)


def main():
    h = F.code_hash(F.V1_FILES)
    print("hash", h, "ref", REF, flush=True)
    same = diff = 0
    diffs = []
    for f in sorted(os.listdir(CA.CACHE)):
        if not f.startswith("run_%s_" % REF):
            continue
        rest = f[len("run_%s_" % REF):-4]
        date, w1 = rest.rsplit("_", 1)
        w1 = int(w1)
        with open(os.path.join(CA.CACHE, f), "rb") as fh:
            e0 = pickle.load(fh)
        t, m, o, hh, l, c = CA.bars(date)
        e1 = EV.run_engine(ENG.PerceptionEngine, m, t, o, hh, l, c, w1)
        ok = sig(e0) == sig(e1)
        same += ok
        if not ok:
            diff += 1
            diffs.append(f)
    print("identical %d | diff %d" % (same, diff), flush=True)
    for f in diffs[:10]:
        print("  DIFF", f)


if __name__ == "__main__":
    main()
