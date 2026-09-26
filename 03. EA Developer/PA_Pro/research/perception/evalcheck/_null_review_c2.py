"""_null_review_c2.py — PLAYBOOK_C2 E2: EVAL-AUDIT's independent null
review of BOX-LAB's edge-source census (R49 §49.5.2, R50 §50.5).

Independent re-implementation (own seed, own run-detection code) of:

  1. The plain vertical-shift null of c1_nullsrc.py — sanity reproduce:
     piv .789/null-p95 .316 on the 38 no-edge set, .880/.343 on all 119.
  2. A DENSITY-MATCHED null: each golden is shifted vertically only
     inside the price range traded during its own lookback (buildup
     start -> tau), so a source with many levels (pivots) faces a fair
     comparison.  Reported for both the golden-buildup lookback and
     BOX-LAB's trailing-360-bar choice.
  3. The close_ext circularity check: close extremes re-measured on
     the K6 TRIGGER window (engine-detectable congestion run) instead
     of the golden's own buildup window.

Sources: piv (book.seq pivots t_conf<=tau), cext_trig, sess72 (6h M5),
sess360 (BOX-LAB registry's de-facto 30h), rnd10, prior_hi_lo,
close_ext_golden (the circular original, contrast only).
"""
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "boxlab"))

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import funnel as F                              # noqa: E402
import cache as CA                              # noqa: E402
from scoreboard import panel_cands              # noqa: E402

H8 = "9acaa206c8d386dc"
DRAWS = 200
SEED = 20260923            # deliberately different from BOX-LAB's 20260922
CONG_H, CONG_N = 5.5, 6    # K6 trigger params


def cong_close_extremes(e, i_end):
    """Close extremes of every K6-qualifying congestion run ending <=
    i_end.  Own implementation of the K6 rule: a run ending at i is the
    longest suffix of bars whose high-low envelope stays < 5.5*ABR(i);
    it qualifies when its length >= 6 bars."""
    out = []
    bars = e.bars
    n = min(i_end + 1, len(bars))
    for i in range(n):
        if i >= len(e.abr):
            continue
        abr = e.abr[i]
        if not abr or abr <= 0:
            continue
        hi = lo = None
        j = i
        while j >= 0:
            b = bars[j]
            h2 = hi if hi is not None else b["h"]
            l2 = lo if lo is not None else b["l"]
            h2 = max(h2, b["h"])
            l2 = min(l2, b["l"])
            if h2 - l2 >= CONG_H * abr:
                break
            hi, lo = h2, l2
            j -= 1
        runlen = i - j
        if runlen >= CONG_N:
            seg = bars[j + 1:i + 1]
            out.append((max(x["c"] for x in seg),
                        min(x["c"] for x in seg)))
    return out


def collect():
    """Same golden set + edges as c1_nullsrc.collect(), keeping the
    engine object and bars so the nulls can be recomputed."""
    rows = []
    for rec in C.load_tune():
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        pk = os.path.join(CA.CACHE, "run_m1_v1_%s_%s_%s.pkl"
                          % (H8, rec["date"], w1))
        if not os.path.exists(pk):
            continue
        e = pickle.load(open(pk, "rb"))
        tau_bar = int(np.searchsorted(m, w1))
        tb = min(tau_bar, len(t) - 1)
        day0 = int(np.searchsorted(t, np.datetime64(
            str(t[tb])[:10]).astype(t.dtype)))
        gobjs, _, _ = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        cands = panel_cands(e, m, w0, w1)
        same = [r for r in cands if EV.FAMILY.get(r["type"]) == "box"]
        for gi, g in enumerate(g2):
            if g["spec_type"] != "BOX" or g.get("price_lo") is None:
                continue
            glo = g["price_lo"] / C.PIP
            ghi = g["price_hi"] / C.PIP
            tol = V2.tol_px(g)
            gbs = g.get("build_start") or g.get("t0")
            gbe = g.get("build_end") or g.get("t1")
            i0 = int(np.searchsorted(m, gbs))
            i1 = min(int(np.searchsorted(m, gbe)), len(c) - 1)
            eb = e.bars
            # the golden's own decision time (build_end), not w1:
            # "visible by tau" means visible when the box should exist
            tau_g = gbe if gbe is not None else gbs
            bi = min(int(np.searchsorted(m, tau_g)), len(eb) - 1)
            piv = [p.price for p in e.book.seq
                   if getattr(p, "t_conf", 10 ** 9) <= bi]
            s72 = eb[max(0, bi - 72):bi]
            s360 = eb[max(0, bi - 360):bi]
            srcs = {
                "piv": piv,
                "cext_trig": sum(([a, b] for a, b in
                                 cong_close_extremes(e, bi)), []),
                "sess72": [max(x["h"] for x in s72),
                           min(x["l"] for x in s72)] if s72 else [],
                "sess360": [max(x["h"] for x in s360),
                            min(x["l"] for x in s360)] if s360 else [],
                "close_ext_golden": [float(np.max(c[i0:i1 + 1])),
                                     float(np.min(c[i0:i1 + 1]))],
                "prior_hi_lo": [float(np.max(h[:day0])),
                                float(np.min(l[:day0]))]
                if day0 > 0 else [],
            }
            # traded range over the golden's lookback (buildup -> tau)
            lb = eb[max(0, min(bi, i0)):bi + 1]
            tr_lo = min(x["l"] for x in lb) if lb else glo
            tr_hi = max(x["h"] for x in lb) if lb else ghi
            # BOX-LAB registry's variant: trailing 360 bars to tau
            s360f = eb[max(0, bi - 360):bi + 1]
            r360_lo = min(x["l"] for x in s360f) if s360f else glo
            r360_hi = max(x["h"] for x in s360f) if s360f else ghi
            rows.append({"panel": rec["id"], "gi": gi, "glo": glo,
                         "ghi": ghi, "tol": tol, "srcs": srcs,
                         "tr": (tr_lo, tr_hi), "r360": (r360_lo, r360_hi),
                         "hit": any(F.edges_pass(g, r) for r in same)})
    return rows


def covered(row, src, glo, ghi):
    tol = row["tol"]
    if src == "rnd10":
        return (abs(glo - round(glo / 10.0) * 10.0) <= tol
                and abs(ghi - round(ghi / 10.0) * 10.0) <= tol)
    lv = row["srcs"].get(src) or []
    return (any(abs(x - glo) <= tol for x in lv)
            and any(abs(x - ghi) <= tol for x in lv))


def eval_set(rows, name, rng):
    srcs = ["piv", "cext_trig", "sess72", "sess360", "rnd10",
            "prior_hi_lo", "close_ext_golden", "union"]
    core = [s for s in srcs if s not in ("union", "close_ext_golden")]
    print("\n=== %s (n=%d) ===" % (name, len(rows)))
    print("%-18s %7s | %-21s | %-21s" %
          ("source", "obs", "plain null mu/p95",
           "dense null mu/p95"))
    for s in srcs:
        obs = np.mean([
            covered(r, s, r["glo"], r["ghi"]) if s != "union"
            else any(covered(r, x, r["glo"], r["ghi"]) for x in core)
            for r in rows])
        plain = np.zeros(DRAWS)
        dense = np.zeros(DRAWS)
        dense360 = np.zeros(DRAWS)
        for d in range(DRAWS):
            for r in rows:
                hg = r["ghi"] - r["glo"]
                off = rng.uniform(1.0, 3.0) * hg * rng.choice([-1, 1])
                sg, sh = r["glo"] + off, r["ghi"] + off
                ok = (covered(r, s, sg, sh) if s != "union"
                      else any(covered(r, x, sg, sh) for x in core))
                plain[d] += ok
                # density-matched: shift inside the buildup->tau traded
                # range, golden stays inside it
                lo, hi = r["tr"]
                room = max(hi - lo - hg, 1e-9)
                nlo = lo + rng.uniform(0, 1) * room
                okd = (covered(r, s, nlo, nlo + hg) if s != "union"
                       else any(covered(r, x, nlo, nlo + hg)
                                for x in core))
                dense[d] += okd
                lo, hi = r["r360"]
                room = max(hi - lo - hg, 1e-9)
                nlo = lo + rng.uniform(0, 1) * room
                okd = (covered(r, s, nlo, nlo + hg) if s != "union"
                       else any(covered(r, x, nlo, nlo + hg)
                                for x in core))
                dense360[d] += okd
        n = len(rows)
        print("%-18s %7.3f | %5.3f / %.3f       | %5.3f / %.3f  "
              "(r360 %5.3f / %.3f)"
              % (s, obs, plain.mean() / n, np.quantile(plain / n, .95),
                 dense.mean() / n, np.quantile(dense / n, .95),
                 dense360.mean() / n, np.quantile(dense360 / n, .95)))


def main():
    rows = collect()
    print("scorable BOX goldens:", len(rows))
    noedge = [r for r in rows if not r["hit"]]
    print("no-edge subset:", len(noedge))
    rng = np.random.default_rng(SEED)
    eval_set(noedge, "no-edge set", rng)
    eval_set(rows, "all BOX goldens", rng)


if __name__ == "__main__":
    main()
