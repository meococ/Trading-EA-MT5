"""flicker.py — R18 §18.4 / R20 §20.3: changes to the live top-k BOX
set per hour, per cached run tag.

A change event is a birth or a close (supersede/displace/tail_end).
At every event bar we take the live set (t_birth <= bar < t_right),
rank by birth score, and count one flicker when the top-k membership
differs from the previous event bar.  Rate = flickers / panel hours.
"""
import glob
import os
import pickle
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
for _p in (_HERE, _PERC, os.path.join(_PERC, "evalcheck"),
           os.path.join(_PERC, "golden")):
    if _p not in sys.path:
        sys.path.insert(0, os.path.abspath(_p))

import run_eval as RE  # noqa: E402
sys.modules.setdefault("__main__", RE)
sys.modules["__main__"] = RE  # _Shim lives there for the pickles
import common as C  # noqa: E402
import numpy as np  # noqa: E402


def panel_flicker(e, w1, k=2):
    bars = int(w1) + 1
    boxes = [o for o in e.objects if o.type == "BOX"]
    evs = sorted({o.t_birth for o in boxes} |
                 {o.t_right for o in boxes if o.t_right is not None})
    prev, fl = None, 0
    for b in evs:
        live = [o for o in boxes
                if o.t_birth <= b and (o.t_right is None or o.t_right > b)]
        live.sort(key=lambda o: -o.geometry.get("score", 0.0))
        top = tuple(o.id for o in live[:k])
        if prev is not None and top != prev:
            fl += 1
        prev = top
    hours = bars * 5.0 / 60.0
    return fl / max(hours, 1e-9)


def main(tag):
    rates = []
    for rec in C.load_tune():
        w1 = rec["window"]["x1"] or 1439
        f = os.path.join(RE.RUNS, "s2_%s_%s_%d.pkl" % (tag, rec["date"], w1))
        if not os.path.exists(f) or os.path.getsize(f) == 0:
            continue
        with open(f, "rb") as fh:
            e = pickle.load(fh)
        rates.append(panel_flicker(e, w1))
    print("%s: flicker/h med %.2f  mean %.2f  (n=%d panels)"
          % (tag, np.median(rates), np.mean(rates), len(rates)))
    return float(np.median(rates))


if __name__ == "__main__":
    for tag in sys.argv[1:] or ["lab_r28"]:
        main(tag)
