"""_f1_profile.py — F1 throughput-collapse profile (R47 §47.4.3).

Profile-only: no engine edits.  DESIGN-window bars via
scale/design_loader.py (the only door; outcome-blind).  One pa_slots
slot, BelowNormal priority (pa_slots import side effect).

Measures on a continuous multi-week EURUSD M5 run:
  * bars/s per trading day (rate collapse vs day index);
  * structure growth: objects total / ACTIVE / DELETED, swing book
    seq len, salience pool / births ledger / grave maps, cand-eval
    call volume (via cProfile counts, cand_log stays off — the
    SCALE condition);
  * cProfile top functions for a single day at ~day 5 vs ~day 50.

Usage: python _f1_profile.py [n_days]   (default 55)
"""
import cProfile
import collections
import io
import os
import pstats
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "scale"))

import pa_slots                                    # noqa: E402  (BelowNormal)
import design_loader as DL                        # noqa: E402
import engine as ENG                              # noqa: E402


def struct_counts(e):
    act = deld = 0
    for o in e.objects:
        if o.state == "ACTIVE":
            act += 1
        else:
            deld += 1
    s = e.salience
    return dict(obj_tot=len(e.objects), obj_act=act, obj_del=deld,
                swing_seq=len(e.book.seq),
                pool=len(s.pool), births=len(s._births),
                grave=len(s._grave), grave_band=len(s._grave_band))


def prof_day(e, t, m, o, h, l, c, j0, j1):
    """cProfile over bars[j0:j1]; returns stats text."""
    pr = cProfile.Profile()
    pr.enable()
    for j in range(j0, j1):
        e.update(int(t[j]), float(o[j]), float(h[j]), float(l[j]),
                 float(c[j]), cet_min=int(m[j]))
    pr.disable()
    buf = io.StringIO()
    pstats.Stats(pr, stream=buf).sort_stats("cumulative") \
        .print_stats(18)
    return buf.getvalue()


def main():
    n_days = int(sys.argv[1]) if len(sys.argv) > 1 else 55
    # DESIGN window: EURUSD 2019-01 -> +N trading days (~n_days*288 bars)
    bars = DL.load_m5("EURUSD", "2019-01-01", "2019-06-01")
    t, m, o, h, l, c = (bars["t"], bars["cet_min"], bars["o"],
                        bars["h"], bars["l"], bars["c"])
    dow = bars["dow_cet"]
    # group bars by CET day (weekday-only data arrives Mon-Fri)
    daykey = (bars["cet"] // 86400).astype(int)
    days = []
    last = None
    for j in range(len(t)):
        if daykey[j] != last:
            days.append(j)
            last = daykey[j]
    days.append(len(t))
    n_days = min(n_days, len(days) - 1)
    print("loaded %d bars, %d trading days; profiling %d"
          % (len(t), len(days) - 1, n_days))

    with pa_slots.slot("f1-profile", timeout=1800):
        e = ENG.PerceptionEngine(feed="DESIGN")
        hdr = ("day bars/day bars/s | obj_tot act del | swingseq | "
               "pool births grave gband")
        print(hdr)
        profmarks = {5: None, min(50, n_days - 1): None}
        for d in range(n_days):
            j0, j1 = days[d], days[d + 1]
            t0 = time.time()
            if d in profmarks:
                t0p = time.time()
                txt = prof_day(e, t, m, o, h, l, c, j0, j1)
                profmarks[d] = txt
                wall = time.time() - t0p   # includes profiler overhead
            else:
                for j in range(j0, j1):
                    e.update(int(t[j]), float(o[j]), float(h[j]),
                             float(l[j]), float(c[j]),
                             cet_min=int(m[j]))
                wall = time.time() - t0
            nb = j1 - j0
            sc = struct_counts(e)
            rate = ("%.0f" % (nb / wall)) if wall else "prof"
            print("%3d %5d %6s | %5d %4d %4d | %7d | %4d %5d %5d %5d"
                  % (d, nb, rate, sc["obj_tot"], sc["obj_act"],
                     sc["obj_del"], sc["swing_seq"], sc["pool"],
                     sc["births"], sc["grave"], sc["grave_band"]))
        for d, txt in profmarks.items():
            if txt:
                print("\n==== cProfile day %d (one day, 288 bars) ===="
                      % d)
                print(txt)


if __name__ == "__main__":
    main()
