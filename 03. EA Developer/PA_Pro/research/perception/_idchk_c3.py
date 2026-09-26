"""Canonical check for STABLE C-3: fresh engine at NEW defaults must be
byte-identical (canonical()) to the measured arm uip2_pbbirth @8361fe85
cache, on every TUNE panel."""
import sys, pickle, os
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "evalcheck"))
sys.path.insert(0, _HERE)
import eval as EV, engine as ENG, common as C, cache as CA

recs = C.load_tune()
ident = diff = 0
for rec in recs:
    w1 = rec["window"]["x1"] or 1439
    f = os.path.join(_HERE, "evalcheck", "_cache",
                     "run_uip2_pbbirth_8361fe85e73f9437_%s_%s.pkl"
                     % (rec["date"], w1))
    try:
        ref = pickle.load(open(f, "rb"))
    except Exception as ex:
        print("missing ref", rec["date"], w1, ex); continue
    t, m, o, h, l, c = EV.day_bars(rec["date"])
    e = EV.run_engine(ENG.PerceptionEngine, m, t, o, h, l, c, w1,
                      w0=rec["window"]["x0"])
    if CA.canonical(e) == CA.canonical(ref):
        ident += 1
    else:
        diff += 1
        print("DIFF", rec["date"], w1)
print("identical", ident, "| diff", diff)
