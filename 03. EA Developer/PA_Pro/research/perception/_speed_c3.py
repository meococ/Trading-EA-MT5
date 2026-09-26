"""_speed_c3.py — R71 s.71.3.1: per-bar speed check of C-3 over
55 DESIGN days.  One engine, feed=DESIGN; per-day bars/s + median.
Run under heavy_run.py (single heavy lock).

Usage: python _speed_c3.py [n_days]
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "evalcheck"))
sys.path.insert(0, os.path.join(HERE, "scale"))

import design_loader as DL                       # noqa: E402


def main():
    n_days = int(sys.argv[1]) if len(sys.argv) > 1 else 55
    import engine as E
    bars = DL.load_m5("EURUSD", "2019-01-01", "2019-07-01")
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
    print("loaded %d bars; running %d days" % (len(t), n_days),
          flush=True)
    e = E.PerceptionEngine(feed="DESIGN")
    rates = []
    for d in range(n_days):
        j0, j1 = days[d], days[d + 1]
        t0 = time.time()
        for j in range(j0, j1):
            e.update(int(t[j]), float(o[j]), float(h[j]),
                     float(l[j]), float(c[j]), cet_min=int(m[j]))
        rates.append((j1 - j0) / max(time.time() - t0, 1e-9))
        if d % 10 == 0 or d == n_days - 1:
            print("day %2d  %6.0f b/s" % (d, rates[-1]), flush=True)
    rates.sort()
    med = rates[len(rates) // 2]
    print("median %.0f b/s | min %.0f | max %.0f | objects %d"
          % (med, rates[0], rates[-1], len(e.objects)))


if __name__ == "__main__":
    main()
