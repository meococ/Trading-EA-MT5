"""_f1_speed_spot.py — E3 speed leg: patched (perf/v2) vs live engine on
a continuous DESIGN run.  Reports per-day bars/s for both and a final
canonical equality check (objects + cand_log + events).

Usage: python evalcheck/_f1_speed_spot.py [n_days]
"""
import copy
import importlib.util
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "scale"))

import design_loader as DL                       # noqa: E402
import pa_slots                                 # noqa: E402
from _verify_keeps_c1 import canon              # noqa: E402

PERF = os.path.join(PERC, "_scratch", "perf", "v2")


def load_patched():
    for mod, path in [("perf_swings", os.path.join(PERF, "swings.py")),
                      ("perf_engine", os.path.join(PERF, "engine.py"))]:
        spec = importlib.util.spec_from_file_location(mod, path)
        m = importlib.util.module_from_spec(spec)
        if mod == "perf_engine":
            sys.modules["swings"] = sys.modules["perf_swings"]
        sys.modules[mod] = m
        spec.loader.exec_module(m)
    return sys.modules["perf_engine"]


def run(cls, t, m, o, h, l, c, days, n_days, feed):
    e = cls(feed=feed)
    rates = []
    for d in range(n_days):
        j0, j1 = days[d], days[d + 1]
        t0 = time.time()
        for j in range(j0, j1):
            e.update(int(t[j]), float(o[j]), float(h[j]),
                     float(l[j]), float(c[j]), cet_min=int(m[j]))
        rates.append((j1 - j0) / max(time.time() - t0, 1e-9))
    return e, rates


def main():
    n_days = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    with pa_slots.slot("evalcheck-f1-speed", timeout=2400):
        bars = DL.load_m5("EURUSD", "2019-01-01", "2019-04-01")
        t, m = bars["t"], bars["cet_min"]
        o, h, l, c = (bars["o"], bars["h"], bars["l"], bars["c"])
        daykey = (bars["cet"] // 86400).astype(int)
        days, last = [], None
        for j in range(len(t)):
            if daykey[j] != last:
                days.append(j)
                last = daykey[j]
        days.append(len(t))
        n_days = min(n_days, len(days) - 1)
        print("loaded %d bars; running %d days x2 engines"
              % (len(t), n_days))
        import engine as E0
        pe = load_patched()
        e0, r0 = run(E0.PerceptionEngine, t, m, o, h, l, c,
                     days, n_days, "DESIGN")
        e1, r1 = run(pe.PerceptionEngine, t, m, o, h, l, c,
                     days, n_days, "DESIGN")
        for d in range(n_days):
            print("day %2d  live %6.0f b/s   patched %6.0f b/s"
                  % (d, r0[d], r1[d]))
        oa, la = canon(e0)
        ob, lb = canon(e1)
        oae, _ = canon(e0, with_events=True)
        obe, _ = canon(e1, with_events=True)
        print("canonical: objects %s | cand_log %s | events %s"
              % ("EQ" if oa == ob else "DIFF",
                 "EQ" if la == lb else "DIFF",
                 "EQ" if oae == obe else "DIFF"))


if __name__ == "__main__":
    main()
