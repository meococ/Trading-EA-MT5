"""_idchk_full.py — full canonical check: fresh engine at current
defaults vs EVERY cached uip2_pbbirth@8361fe85e73f9437 panel (623 =
all TUNE windows, the C-3 arm cache), not just the 198 eval recs.
Satisfies the ARCH_REVIEW A1 FIX gate (full canonical set) and
exercises the A2 __setstate__ legacy-pickle bridge on real caches.

Usage: python _idchk_full.py
"""
import sys, pickle, os, re, glob
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "evalcheck"))
sys.path.insert(0, _HERE)
import eval as EV, engine as ENG, cache as CA

PAT = re.compile(r"run_uip2_pbbirth_8361fe85e73f9437_"
                 r"(\d{4}-\d{2}-\d{2})_(\d+)\.pkl$")

files = sorted(f for f in
               glob.glob(os.path.join(
                   _HERE, "evalcheck", "_cache",
                   "run_uip2_pbbirth_8361fe85e73f9437_*.pkl"))
               if PAT.search(f))
print("cache files:", len(files), flush=True)
ident = diff = err = 0
for f in files:
    m0 = PAT.search(f)
    date, w1 = m0.group(1), int(m0.group(2))
    try:
        ref = pickle.load(open(f, "rb"))
        w0 = getattr(ref, "w0_min", None)
        t, m, o, h, l, c = EV.day_bars(date)
        e = EV.run_engine(ENG.PerceptionEngine, m, t, o, h, l, c, w1,
                          w0=w0)
        if CA.canonical(e) == CA.canonical(ref):
            ident += 1
        else:
            diff += 1
            print("DIFF", date, w1, flush=True)
    except Exception as ex:
        err += 1
        print("ERR", date, w1, repr(ex)[:120], flush=True)
print("identical", ident, "| diff", diff, "| err", err)
