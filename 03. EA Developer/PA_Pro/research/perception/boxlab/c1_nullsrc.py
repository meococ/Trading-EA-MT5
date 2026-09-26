# c1_nullsrc.py — R49 §49.3.1 null test for the level-source census.
#
# For each causal source, measure the share of golden BOXes whose BOTH
# edges lie within tolerance of a level the source had produced by tau.
# Null: the same goldens shifted vertically by a random offset, uniform
# in +/-1..3 box heights (height unchanged, same tolerance), 200 draws.
# Report observed share, null mean, null p95; a source that does not
# beat the null p95 is dropped.
#
# Sources (levels observable by tau, i.e. the panel cutoff):
#   piv        book.seq pivots confirmed by tau
#   rnd10      10-pip round-number grid
#   close_ext  buildup close max/min over the golden's own window
#   sess_hi_lo trailing-6h (72 x M5) high/low ending at tau
#   prior_hi_lo high/low of all bars before tau's day
# Run: python c1_nullsrc.py   (imports evalcheck only)

import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evalcheck"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import common as C  # noqa: E402
import eval as EV  # noqa: E402
import eval_v2 as V2  # noqa: E402
import funnel as F  # noqa: E402
import cache as CA  # noqa: E402
from scoreboard import panel_cands  # noqa: E402

H8 = "9acaa206c8d386dc"
SESS_BARS = 72          # 6 h of M5 bars
DRAWS = 200
SEED = 20260922


def rnd_near(x, tol):
    # distance to the nearest 10-pip multiple <= tol
    return abs(x - round(x / 10.0) * 10.0) <= tol


def collect():
    """Per golden: edges, tol, and each source's level list (by tau)."""
    rows = []          # every scorable BOX golden
    for rec in C.load_tune():
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        pk = "../evalcheck/_cache/run_m1_v1_%s_%s_%s.pkl" % (
            H8, rec["date"], w1)
        if not os.path.exists(pk):
            continue
        e = pickle.load(open(pk, "rb"))
        tau_bar = int(np.searchsorted(m, w1))
        tb0 = min(tau_bar, len(t) - 1)
        day0 = int(np.searchsorted(t, np.datetime64(
            str(t[tb0])[:10]).astype(t.dtype)))
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
            i1 = int(np.searchsorted(m, gbe))
            i1 = min(i1, len(c) - 1)
            tb = min(tau_bar, len(h) - 1)
            srcs = {
                "piv": [p.price for p in e.book.seq
                        if p.t_conf <= tau_bar],
                "close_ext": [float(np.max(c[i0:i1 + 1])),
                              float(np.min(c[i0:i1 + 1]))],
                "sess_hi_lo": [float(np.max(h[max(0, tb - SESS_BARS):tb])),
                               float(np.min(l[max(0, tb - SESS_BARS):tb]))]
                if tb > 0 else [],
                "prior_hi_lo": [float(np.max(h[:day0])),
                                float(np.min(l[:day0]))]
                if day0 > 0 else [],
            }
            rows.append({
                "panel": rec["id"], "gi": gi, "glo": glo, "ghi": ghi,
                "tol": tol, "srcs": srcs,
                "hit": any(F.edges_pass(g, r) for r in same),
            })
    return rows


def pass_src(row, src, glo, ghi):
    """True iff source has a level within tol of each shifted edge."""
    tol = row["tol"]
    if src == "rnd10":
        return rnd_near(glo, tol) and rnd_near(ghi, tol)
    lv = row["srcs"].get(src) or []
    return (any(abs(x - glo) <= tol for x in lv)
            and any(abs(x - ghi) <= tol for x in lv))


def eval_set(rows, name):
    rng = np.random.default_rng(SEED)
    srcs = ["piv", "rnd10", "close_ext", "sess_hi_lo", "prior_hi_lo",
            "union"]
    out = {}
    for s in srcs:
        obs = np.mean([pass_src(r, s, r["glo"], r["ghi"]) if s != "union"
                       else any(pass_src(r, x, r["glo"], r["ghi"])
                                for x in srcs[:-1])
                       for r in rows])
        shares = []
        for _ in range(DRAWS):
            ok = 0
            for r in rows:
                hg = r["ghi"] - r["glo"]
                off = rng.uniform(1.0, 3.0) * hg * rng.choice([-1, 1])
                sg, sh = r["glo"] + off, r["ghi"] + off
                if s == "union":
                    ok += any(pass_src(r, x, sg, sh)
                              for x in srcs[:-1])
                else:
                    ok += pass_src(r, s, sg, sh)
            shares.append(ok / len(rows))
        shares = np.asarray(shares)
        out[s] = (obs, float(shares.mean()),
                  float(np.quantile(shares, 0.95)))
    print("\n=== %s (n=%d) ===" % (name, len(rows)))
    print("%-12s %8s %9s %8s  %s" % ("source", "obs", "null-mu",
                                     "null-p95", "verdict"))
    for s in srcs:
        o, mu, p95 = out[s]
        v = "KEEP" if o > p95 else "drop"
        print("%-12s %8.3f %9.3f %8.3f  %s" % (s, o, mu, p95, v))
    return out


def main():
    rows = collect()
    print("scorable BOX goldens:", len(rows))
    noedge = [r for r in rows if not r["hit"]]
    print("no-edge subset:", len(noedge))
    eval_set(noedge, "no-edge 38-class")
    eval_set(rows, "all BOX goldens")


if __name__ == "__main__":
    main()
