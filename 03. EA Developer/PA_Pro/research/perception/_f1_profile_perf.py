"""_f1_profile_perf.py — same as _f1_profile.py but runs the PATCHED
engine (sys.path prefers _scratch/perf: patched engine.py+swings.py,
all other modules resolve to the frozen dir).  Lab script only; the
patch itself lives in _scratch/perf/ (R48 §48.5)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "_scratch", "perf"))  # patched first
sys.path.insert(0, os.path.join(HERE, "..", "..", "lib"))
sys.path.insert(0, os.path.join(HERE, "scale"))

import engine as ENG                                        # noqa: E402
assert ENG.__file__.startswith(HERE), ENG.__file__
assert "_scratch" in ENG.__file__, ENG.__file__

import _f1_profile as P                                    # noqa: E402
P.ENG = ENG   # patched module (P imports its own; rebind for main())

if __name__ == "__main__":
    # replicate main() but with patched engine already bound
    import pa_slots
    import design_loader as DL
    import time
    n_days = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    bars = DL.load_m5("EURUSD", "2019-01-01", "2019-06-01")
    t, m, o, h, l, c = (bars["t"], bars["cet_min"], bars["o"],
                        bars["h"], bars["l"], bars["c"])
    daykey = (bars["cet"] // 86400).astype(int)
    days = []
    last = None
    for j in range(len(t)):
        if daykey[j] != last:
            days.append(j)
            last = daykey[j]
    days.append(len(t))
    n_days = min(n_days, len(days) - 1)
    print("PATCHED engine: %d bars, %d days; profiling %d"
          % (len(t), len(days) - 1, n_days))
    with pa_slots.slot("f1-profile-perf", timeout=1800):
        e = ENG.PerceptionEngine(feed="DESIGN")
        for d in range(n_days):
            j0, j1 = days[d], days[d + 1]
            t0 = time.time()
            for j in range(j0, j1):
                e.update(int(t[j]), float(o[j]), float(h[j]),
                         float(l[j]), float(c[j]),
                         cet_min=int(m[j]))
            wall = time.time() - t0
            nb = j1 - j0
            sc = P.struct_counts(e)
            print("%3d %5d %6.0f | %5d %4d %4d | %7d | %4d %5d %5d %5d"
                  % (d, nb, nb / wall if wall else 0,
                     sc["obj_tot"], sc["obj_act"], sc["obj_del"],
                     sc["swing_seq"], sc["pool"], sc["births"],
                     sc["grave"], sc["grave_band"]))
