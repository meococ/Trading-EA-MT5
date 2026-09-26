"""identity_check.py — canonical object-stream compare between two
cached engine states (full panel window pickles).

Usage: python identity_check.py <hashA16> <variantA> <hashB16> <variantB>
Default B = frozen STABLE marker_off:584c7743924a8b1b.
Prints panels compared / missing / diffs.
"""
import glob
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C                     # noqa: E402
import cache as CA                     # noqa: E402


def canon(e):
    """Canonical object list: kind, times, why, geometry (floats
    rounded).  Events/log noise ignored — identity = what is drawn."""
    out = []
    for o in e.objects:
        g = dict(getattr(o, "geometry", {}) or {})
        gi = tuple(sorted(
            (k, round(v, 6) if isinstance(v, float) else v)
            for k, v in g.items()
            if isinstance(v, (int, float, str, type(None), bool))))
        out.append((o.type, getattr(o, "t_left", None),
                    getattr(o, "t_right", None),
                    getattr(o, "t_birth", None),
                    getattr(o, "why", None), gi))
    return sorted(map(repr, out))


def pkl(variant, h, date, w1):
    pat = "run_%s%s_%s_%s.pkl" % (
        variant + "_" if variant else "", h, date, w1)
    f = os.path.join(CA.CACHE, pat)
    if not os.path.exists(f):
        g = glob.glob(os.path.join(
            CA.CACHE, "run_%s%s*_%s_%s.pkl"
            % (variant + "_" if variant else "", h[:8], date, w1)))
        f = g[0] if g else None
    return f


def main():
    ha = sys.argv[1]
    va = sys.argv[2] if len(sys.argv) > 2 else "ab_base"
    hb = sys.argv[3] if len(sys.argv) > 3 else "584c7743924a8b1b"
    vb = sys.argv[4] if len(sys.argv) > 4 else "marker_off"
    recs = C.load_tune()
    miss = diff = 0
    for rec in recs:
        w1 = rec["window"]["x1"] or 1439
        fa = pkl(va, ha, rec["date"], w1)
        fb = pkl(vb, hb, rec["date"], w1)
        if not fa or not fb:
            miss += 1
            continue
        try:
            ea = pickle.load(open(fa, "rb"))
            eb = pickle.load(open(fb, "rb"))
        except Exception:
            miss += 1
            continue
        if canon(ea) != canon(eb):
            diff += 1
            if diff <= 3:
                print("DIFF", rec["id"], rec["date"])
    print("panels=%d missing=%d diffs=%d" % (len(recs), miss, diff))


if __name__ == "__main__":
    main()
