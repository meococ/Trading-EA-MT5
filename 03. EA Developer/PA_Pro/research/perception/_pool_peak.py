"""_pool_peak.py — R-1 (R75 s.75.3.4): peak pool occupancy per family,
measured on the canonical set (623 cached TUNE windows).  Feeds the
MQL5 port cap decision.  Runs fresh engines at defaults.

Usage: python _pool_peak.py
"""
import glob
import os
import re
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "evalcheck"))
sys.path.insert(0, _HERE)

import eval as EV                       # noqa: E402
import engine as ENG                    # noqa: E402
import cache as CA                      # noqa: E402

PAT = re.compile(r"run_uip2_pbbirth_8361fe85e73f9437_"
                 r"(\d{4}-\d{2}-\d{2})_(\d+)\.pkl$")


def main():
    files = sorted(f for f in glob.glob(os.path.join(
        _HERE, "evalcheck", "_cache",
        "run_uip2_pbbirth_8361fe85e73f9437_*.pkl"))
        if PAT.search(f))
    print("canonical windows: %d" % len(files), flush=True)
    agg = {}
    per_day = []
    for k, f in enumerate(files):
        m0 = PAT.search(f)
        date, w1 = m0.group(1), int(m0.group(2))
        t, m, o, h, l, c = CA.bars(date)
        e = EV.run_engine(ENG.PerceptionEngine, m, t, o, h, l, c,
                          w1)
        pp = getattr(e.salience, "pool_peak", {"*": 0})
        for fam, v in pp.items():
            agg.setdefault(fam, []).append(v)
        per_day.append((date, w1, dict(pp)))
        if (k + 1) % 50 == 0:
            print("window %d/%d" % (k + 1, len(files)), flush=True)
    print("\n=== peak pool occupancy (canonical 623) ===")
    print("%-10s %6s %6s %6s %6s" % ("fam", "med", "p90", "p99", "max"))
    for fam in sorted(agg):
        v = np.array(agg[fam])
        print("%-10s %6.1f %6.0f %6.0f %6d" % (
            fam, np.median(v), np.percentile(v, 90),
            np.percentile(v, 99), v.max()))
    top = sorted(per_day, key=lambda r: -r[2].get("*", 0))[:8]
    print("\nworst windows by total pool peak:")
    for d, w, pp in top:
        print("  %s w1=%d peak=%s" % (d, w, pp))


if __name__ == "__main__":
    main()
