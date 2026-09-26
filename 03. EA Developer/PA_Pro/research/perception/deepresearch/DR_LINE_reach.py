"""DR_LINE_reach.py — E3a-diagnosis: WHY do golden lines fall outside
the legal-candidate stream?

For every golden PATTERN_LINE/CONTEXT_LINE on TUNE we take the golden
chord itself (t0,p0,t1,p1) and ask, causally at tau = build_end|t1:

  A. anchor coverage: is there a pool anchor (engine semantics:
     confirmed pivot / named-bar loc-ext / terminal / session extreme)
     within tol_l of the golden line near each endpoint?  If not, the
     author's anchor is a bar the engine's stream never marks.
  B. exhaustive anchors: repeat A using EVERY bar extreme as a legal
     anchor — separates "anchor universe too narrow" from "the chord
     itself is unfit".
  C. legality of the golden chord under lines.py's own rules
     (slope sign, defended veto on the pivot stream, touch-event floor)
     on each defended side — separates "rules reject the right line"
     from "stream lacks the anchors".
  D. for reachable-via-pool goldens: which anchor KINDS carry the
     matching pairs (piv / loc / term / sess), i.e. what the author's
     anchors actually are.

Outputs: deepresearch/DR_LINE_reach.jsonl + printed table.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "golden"))
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, os.path.join(PERC, "..", "..", "lib"))

import numpy as np                      # noqa: E402

import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import common as C                     # noqa: E402
import engine as ENG                   # noqa: E402
import DR_LINE_fidelity as F           # noqa: E402

PIP = EV.PIP
OUT = os.path.join(HERE, "DR_LINE_reach.jsonl")


def chord_stats(e, g, jt, side, lp, m):
    """Evaluate the GOLDEN chord under engine legality on `side`."""
    t0, t1 = g["t0"], g["t1"]
    p0, p1 = g["price0"] / PIP, g["price1"] / PIP
    j0, j1 = F.j_at(m, t0), F.j_at(m, t1)
    span = max(j1 - j0, 1)
    slope = (p1 - p0) / span
    abr = max(e.abr[jt], 1e-9)
    tol = max(lp["touch_tol_pips"], lp["touch_tol_abr_frac"] * abr)
    # slope rule
    flat, drift = lp["slope_flat_max"], lp["flat_drift_pips"]
    dmul = lp.get("slope_drift_mult", 1.0)
    slope_ok = True
    if side > 0 and slope > 0 and \
            (slope > flat or slope * span > drift * dmul):
        slope_ok = False
    if side < 0 and slope < 0 and \
            (-slope > flat or -slope * span > drift * dmul):
        slope_ok = False
    # defended veto on the confirmed pivot stream
    stream = [p for p in e.book.seq
              if p.dir == side and p.t_conf <= jt
              and p.prom_birth >= e.book.floor_min(p)]
    over = 0.0
    for q in stream:
        if not (j0 <= q.t_ext <= jt):
            continue
        pj = p0 + slope * (q.t_ext - j0)
        over = max(over, (q.price - pj) * side)
    veto = over > tol * lp.get("over_veto_tol_mult", 1.0)
    # touch events
    ext = "l" if side < 0 else "h"
    n_ev = nt = 0
    cur = False
    for j in range(j0, jt + 1):
        pj = p0 + slope * (j - j0)
        wv = abs(e.bars[j][ext] - pj) <= tol
        if wv:
            nt += 1
            if not cur:
                n_ev += 1
        cur = wv
    return {"slope_ok": slope_ok, "veto": veto, "n_ev": n_ev,
            "nt": nt, "over": round(over, 2), "span": span,
            "j0": j0, "j1": j1, "slope": slope}


def anchors_on_line(e, g, jt, side, lp, m, tol_l, allbars=False):
    """Anchor bars sitting on the golden chord: |wick - chord| <= tol_l.
    Returns list of (bar, kind) — kind = pool class or 'bar'."""
    t0, t1 = g["t0"], g["t1"]
    p0, p1 = g["price0"] / PIP, g["price1"] / PIP
    j0, j1 = F.j_at(m, t0), F.j_at(m, t1)
    span = max(j1 - j0, 1)
    slope = (p1 - p0) / span
    ext = "l" if side < 0 else "h"
    hits = []
    if allbars:
        for j in range(max(0, j0 - 12), jt + 1):
            pj = p0 + slope * (j - j0)
            if abs(e.bars[j][ext] - pj) <= tol_l:
                hits.append((j, "bar"))
        return hits
    pool = F.anchor_pool(e, jt, side, lp)
    for a in pool:
        pj = p0 + slope * (a["t"] - j0)
        if abs(a["p"] - pj) <= tol_l:
            hits.append((a["t"], a["kind"]))
    return hits


def main():
    recs = C.load_tune()
    rows = []
    n_pan = 0
    for rec in recs:
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        t, m, o, h, l, c = EV.day_bars(rec["date"])
        e = EV.run_engine(ENG.PerceptionEngine, m, t, o, h, l, c, w1,
                          w0=w0)
        lp = e.p["line"]
        gobjs, _u, _to = EV.gold_objects(rec)
        n_pan += 1
        for g in gobjs:
            if g["spec_type"] not in ("PATTERN_LINE", "CONTEXT_LINE"):
                continue
            if not V2.scorable(g, w0, w1):
                continue
            if g.get("price0") is None or g.get("price1") is None \
                    or g.get("t0") is None or g.get("t1") is None \
                    or g["t1"] <= g["t0"]:
                continue
            tau = g.get("build_end") or g.get("t1")
            jt = F.j_at(m, min(tau, w1))
            if jt < 5:
                continue
            tol_g = V2.tol_px(g)
            slope_g = (g["price1"] - g["price0"]) / PIP / \
                max(g["t1"] - g["t0"], 1)
            tol_l = tol_g + abs(slope_g) * C.TIME_SIGMA_MIN
            row = {"panel": rec["id"], "type": g["spec_type"],
                   "tau": tau, "tol_l": round(tol_l, 2)}
            for side in (-1, 1):
                st = chord_stats(e, g, jt, side, lp, m)
                ah_pool = anchors_on_line(e, g, jt, side, lp, m, tol_l)
                ah_all = anchors_on_line(e, g, jt, side, lp, m, tol_l,
                                         allbars=True)
                row["side%d" % side] = {
                    "slope_ok": st["slope_ok"], "veto": st["veto"],
                    "n_ev": st["n_ev"], "nt": st["nt"],
                    "over": st["over"], "span": st["span"],
                    "n_pool_on": len(ah_pool),
                    "pool_kinds": sorted({k for _j, k in ah_pool}),
                    "n_bar_on": len(ah_all)}
            rows.append(row)
        if n_pan % 40 == 0:
            print("panel %d/%d" % (n_pan, len(recs)), flush=True)
    with open(OUT, "w", encoding="utf8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    # aggregate diagnosis
    n = len(rows)
    print("\n=== golden-chord diagnosis (n=%d) ===" % n)
    for side in (-1, 1):
        k = "side%d" % side
        sub = [r[k] for r in rows if k in r]
        print("side %+d: slope_ok %.2f  veto-free %.2f  n_ev>=3 %.2f  "
              "pool_anchor_on %.2f  any_bar_on %.2f  med_pool_on %.1f "
              "med_bar_on %.1f" % (
                  side,
                  sum(s["slope_ok"] for s in sub) / len(sub),
                  sum(not s["veto"] for s in sub) / len(sub),
                  sum(s["n_ev"] >= 3 for s in sub) / len(sub),
                  sum(s["n_pool_on"] > 0 for s in sub) / len(sub),
                  sum(s["n_bar_on"] > 0 for s in sub) / len(sub),
                  float(np.median([s["n_pool_on"] for s in sub])),
                  float(np.median([s["n_bar_on"] for s in sub]))))
    both_legal = sum(
        1 for r in rows
        for s in (-1, 1)
        if r["side%d" % s]["slope_ok"] and not r["side%d" % s]["veto"]
        and r["side%d" % s]["n_ev"] >= 3)
    print("golden chords passing full legality on >=1 side: %d" %
          both_legal)


if __name__ == "__main__":
    main()
