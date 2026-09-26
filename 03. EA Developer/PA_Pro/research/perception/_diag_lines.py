"""_diag_lines.py — PATTERN_LINE expressibility + selection audit.

For every usable golden PATTERN_LINE with price0/price1 the question is
not "is the anchor a pivot" (golden p0 is the line's price at t0, not
the extreme) but "can our confirmed pivot stream express this line":

  E1 expressible : exists a pivot pair (pa,pb), t_conf <= panel end,
                   same side as golden dir, whose chord evaluates within
                   TOL pips of the golden line at BOTH golden endpoints
  E2 defended    : E1 pair whose in-span pivots never exceed touch tol
                   on the defended side (our over<=tol birth gate)
  E3 causal      : E2 pair with pb.t_conf <= golden t1 bar (the line
                   could be born before the golden span ends)
  L4 logged      : cand_log holds a line within TOL at both endpoints
  L5 born        : an engine object matches (eval matcher terms)

Also reports, among E1 lines, the best pair's t0 gap vs golden t0
(does the expressible line start where golden ink starts?).

Usage: python _diag_lines.py [--limit N] [--tol 3]
"""
import json, os, sys, argparse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "golden"))

import eval as EV          # noqa: E402
import engine as ENG       # noqa: E402

PIP = 1e-4


def bar_of(m, tmin):
    return int(min(np.searchsorted(m, tmin), len(m) - 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--tol", type=float, default=3.0)
    args = ap.parse_args()
    TOL = args.tol

    recs = [json.loads(x) for x in open(EV.TUNE, encoding="utf8")]
    if args.limit:
        recs = recs[:args.limit]

    st = dict(n=0, e1=0, e2=0, e3=0, l4=0, l5=0)
    t0gaps, misses = [], []
    for rec in recs:
        date = rec["date"]
        t, m, o, h, l, c = EV.day_bars(date)
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        i_end = bar_of(m, w1)
        e = EV.run_engine(ENG.PerceptionEngine, m, t, o, h, l, c, w1)
        eobjs = EV.eng_objects(e, m, w0, w1)
        pivs = [p for p in e.book.seq if p.t_conf <= i_end]
        by_side = {1: [p for p in pivs if p.dir == 1],
                   -1: [p for p in pivs if p.dir == -1]}
        for g in rec["objects"]:
            if g.get("spec_type") != "PATTERN_LINE" or \
                    g.get("status") in EV.EXCLUDED or \
                    g.get("prec") == "time_only":
                continue
            p0g, p1g = g.get("price0"), g.get("price1")
            if p0g is None or p1g is None:
                continue
            st["n"] += 1
            gd = {"up": 1, "down": -1}.get(g.get("dir"))
            sides = {-1} if gd == 1 else ({1} if gd == -1
                                          else {1, -1})
            t0, t1 = g["t0"], g["t1"]
            i0, i1 = bar_of(m, t0), bar_of(m, t1)
            b0, b1 = p0g / PIP, p1g / PIP

            # E1: any same-side pair whose chord matches golden
            best = None
            for sd in sides:
                pl = by_side[sd]
                for a in range(len(pl)):
                    for b in range(a + 1, len(pl)):
                        pa, pb = pl[a], pl[b]
                        sp = pb.t_ext - pa.t_ext
                        if sp < 2:
                            continue
                        sl = (pb.price - pa.price) / sp
                        e0 = abs(pa.price + sl * (i0 - pa.t_ext) - b0)
                        e1 = abs(pa.price + sl * (i1 - pa.t_ext) - b1)
                        err = max(e0, e1)
                        if best is None or err < best[0]:
                            best = (err, pa, pb, sl)
            if best is None or best[0] > TOL:
                misses.append((rec["id"], "not-expressible",
                               None if best is None else round(best[0], 1)))
                continue
            st["e1"] += 1
            err, pa, pb, sl = best
            t0gaps.append(abs(m[pa.t_ext] - t0))
            # E2: defended AT BIRTH — in-span pivots up to the right
            # anchor's confirm (later pivots may traverse: lifecycle,
            # not a birth defect)
            over = 0.0
            for q in pivs:
                if q.dir != pa.dir or not (pa.t_ext <= q.t_ext) \
                        or q.t_conf > pb.t_conf:
                    continue
                d = (q.price - (pa.price + sl * (q.t_ext - pa.t_ext))) \
                    * pa.dir
                over = max(over, d)
            ttol = 1.5
            if over > ttol:
                misses.append((rec["id"], "undefended",
                               round(over, 1)))
                continue
            st["e2"] += 1
            # E3: right anchor confirmed before golden t1
            if pb.t_conf > i1:
                misses.append((rec["id"], "conf-too-late",
                               int(m[pb.t_conf]) - t1))
                continue
            st["e3"] += 1
            # L4 / L5
            hit4 = any(
                "slope" in cl and
                abs(cl["p0"] + cl["slope"] * (i0 - cl["t0"]) - b0) <= 6
                and
                abs(cl["p0"] + cl["slope"] * (i1 - cl["t0"]) - b1) <= 6
                for cl in (e.cand_log or []))
            if hit4:
                st["l4"] += 1
            hit5 = any(
                eo.get("p0") is not None and
                abs(eo["t0"] - t0) <= 15 and abs(eo["t1"] - t1) <= 15 and
                abs(EV._line_price_at(eo, t0, m) - b0) <= 6 and
                abs(EV._line_price_at(eo, t1, m) - b1) <= 6
                for eo in eobjs)
            if hit5:
                st["l5"] += 1

    print("golden endpoint lines     :", st["n"])
    print("E1 expressible in stream  : %d (%.0f%%)"
          % (st["e1"], 100 * st["e1"] / max(st["n"], 1)))
    print("E2 +defended edge         :", st["e2"])
    print("E3 +causal (conf<=t1)     :", st["e3"])
    print("L4 candidate logged       :", st["l4"])
    print("L5 born/matched           :", st["l5"])
    if t0gaps:
        t0gaps = np.array(t0gaps)
        print("E1 left-anchor |t0 gap| min: med %.0f p75 %.0f"
              % (np.median(t0gaps), np.percentile(t0gaps, 75)))
        print("   <=15min: %d/%d" % ((t0gaps <= 15).sum(), len(t0gaps)))
    from collections import Counter
    print("\nmiss kinds:", Counter(k for _, k, *_ in misses))


if __name__ == "__main__":
    main()
