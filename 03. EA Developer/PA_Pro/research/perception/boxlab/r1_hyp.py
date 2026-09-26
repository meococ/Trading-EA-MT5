"""r1_hyp.py -- R56 s.56.4 R1.4: hypothesis table with label-shuffle nulls.

For every panel with a box golden AND a wrong engine pick at tau:
  observed = mean( f(golden) - f(pick) )
Null: shuffle the golden label among the panel's candidate rectangles
(golden + every distinct BOX cand proposed <= tau + live boxes), 200
draws; keep a row only if observed > null p95 (one-sided).

All features use bars <= tau only.  Feature sign: higher = more
author-like.

H1 press:     last-10 closes within 1.5p of an edge (pre-break tension)
H2 flat_ema:  EMA25 inside-box fraction minus 10*|slope|
H3 probes:    wick rejections at edges in last 15 bars
H4 prior_leg: |close[t0]-close[t0-40]| / abr  (leg entering the box)
H5 recency:   -(tau - t1)
H6 height_r:  (hi-lo)/day_range_so_far
H7 overlap:   fraction of span bars intersecting [lo,hi]
H8 extremes:  -mean dist of each edge to span's wick extreme
H9 rnd50:     1 if a 50-pip round lies inside [lo,hi] else 0
H10 tall:     (hi-lo) in pips
"""
import sys, os, pickle, collections

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "evalcheck"))
sys.path.insert(0, os.path.join(HERE, ".."))

import common as C                         # noqa: E402
import eval as EV                          # noqa: E402
import eval_v2 as V2                       # noqa: E402
import cache as CA                         # noqa: E402
import recall_at_k as RK                   # noqa: E402
from snapshot import tau_of, live_records  # noqa: E402
import importlib.util                      # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "cm", os.path.join(HERE, "c1_missed.py"))
cm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cm)

HASH = os.environ.get("CM_HASH", "ee2cbf1202db47b6")
VAR = os.environ.get("CM_VAR", "c1r_p_base")
CACHE = os.path.join(HERE, "..", "evalcheck", "_cache")
PIP = C.PIP
DRAWS = 200
RNG = np.random.RandomState(56)


def _pk(rec, bar):
    f = os.path.join(CACHE, "run_%s_%s_%s_%s.pkl"
                     % (VAR, HASH, rec["date"], bar))
    return pickle.load(open(f, "rb")) if os.path.exists(f) else None


def ema25(c):
    a = 2.0 / 26.0
    out = np.empty(len(c))
    e = c[0]
    for k in range(len(c)):
        e = e + a * (c[k] - e)
        out[k] = e
    return out


def feats(lo, hi, i0, i1, o, h, l, c, ema, abr, day_lo, day_hi, tau_i,
          t1_drawn=None):
    """i0,i1 bar-index span (inclusive), clipped to <= tau_i."""
    i1 = min(i1, tau_i)
    if i1 <= i0 + 3:
        i1 = min(i0 + 3, tau_i)
    if t1_drawn is None:
        t1_drawn = i1
    sp_h = h[i0:i1 + 1]
    sp_l = l[i0:i1 + 1]
    sp_c = c[i0:i1 + 1]
    hh = float(sp_h.max())
    ll = float(sp_l.min())
    height = hi - lo
    # H1: last-10 closes pressing an edge
    tail = c[max(0, tau_i - 9):tau_i + 1]
    press = float(np.mean(
        (np.abs(tail - hi) <= 1.5) | (np.abs(tail - lo) <= 1.5)))
    # H2: flat ema inside box
    e_sp = ema[i0:i1 + 1]
    inside = float(np.mean((e_sp >= lo) & (e_sp <= hi)))
    slope = abs(e_sp[-1] - e_sp[0]) / max(1, len(e_sp))
    f_ema = inside - 10.0 * slope
    # H3: wick rejections at edges, last 15 bars
    pr = 0
    for k in range(max(0, tau_i - 14), tau_i + 1):
        if h[k] > hi and c[k] < hi:
            pr += 1
        if l[k] < lo and c[k] > lo:
            pr += 1
    # H4: leg into the box
    j0 = max(0, i0 - 40)
    leg = abs(c[i0] - c[j0]) / max(abr, 1e-9)
    # H5: drawn-span end vs tau (positive = drawn past tau -- "kept
    # past the break").  Uses the DRAWN t1, not build_end (which is
    # tau by construction and would trivialize the test).
    rec = float(t1_drawn - tau_i)
    # H6: height vs day range so far
    dr = max(day_hi - day_lo, 1e-9)
    hr = height / dr
    # H7: overlap ratio
    ov = float(np.mean((sp_l <= hi) & (sp_h >= lo)))
    # H8: edges sit ON wick tips inside the span (0 = edge == a wick tip)
    d_hi = float(np.abs(sp_h - hi).min())
    d_lo = float(np.abs(sp_l - lo).min())
    ext = -0.5 * (d_hi + d_lo)
    # H9: 50-pip round inside box
    f_rnd = 1.0 if np.any((np.arange(int(lo / 50) + 1, int(hi / 50) + 1)
                           * 50.0 >= lo) &
                          (np.arange(int(lo / 50) + 1, int(hi / 50) + 1)
                           * 50.0 <= hi)) else 0.0
    # H10: tallness (hi-lo already in pip scale)
    return np.array([press, f_ema, float(pr), leg, float(rec), hr,
                     ov, ext, f_rnd, height])


HNAMES = ["H1_press", "H2_flat_ema", "H3_probes", "H4_prior_leg",
          "H5_recency", "H6_height_r", "H7_overlap", "H8_extremes",
          "H9_rnd50", "H10_tall"]


def main():
    pairs = []   # (feats_golden, feats_pick, [feats pool])
    for rec in C.load_tune():
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        if _pk(rec, w1) is None:
            continue
        t, m, o, h, l, c = CA.bars(rec["date"])
        ema = ema25(c)
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        for gi, g in enumerate(g2):
            if EV.FAMILY.get(g["spec_type"]) != "box":
                continue
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            tau = min(tau, w1)
            e_t = _pk(rec, tau)
            if e_t is None:
                continue
            tau_i = int(np.searchsorted(m, tau))
            live, _em = live_records(e_t, m, w0, tau)
            osc = {ob.id: getattr(ob, "score", None)
                   for ob in e_t.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            ranked = RK.rank_live(live, RK.score_map(e_t))
            fam = [r for r in ranked
                   if EV.FAMILY.get(r["type"]) == "box"]
            if not fam:
                continue
            hit = any(V2.match(g, er, m) for er in fam[:1])
            if hit:
                continue
            top = fam[0]
            ob = next((o2 for o2 in e_t.objects if o2.id == top["id"]),
                      None)
            if ob is None:
                continue
            geo = getattr(ob, "geometry", {}) or {}
            pk_lo = geo.get("bottom")
            pk_hi = geo.get("top")
            if pk_lo is None:
                continue
            pk_t0 = int(np.searchsorted(m, top.get("t_birth") or w0))
            glo, ghi = g["price_lo"] / PIP, g["price_hi"] / PIP
            gi0 = int(np.searchsorted(m, g.get("t0") or w0))
            gi1 = int(np.searchsorted(
                m, g.get("build_end") or g.get("t1") or tau))
            day_lo = float(l[:tau_i + 1].min())
            day_hi = float(h[:tau_i + 1].max())
            abr = float(np.mean(h[max(0, tau_i - 20):tau_i + 1]
                                - l[max(0, tau_i - 20):tau_i + 1]))
            g_t1m = g.get("t1") or tau
            f_g = feats(glo, ghi, gi0, gi1, o, h, l, c, ema, abr,
                        day_lo, day_hi, tau_i,
                        t1_drawn=int(np.searchsorted(m, g_t1m)))
            f_p = feats(pk_lo, pk_hi, pk_t0, tau_i, o, h, l, c, ema,
                        abr, day_lo, day_hi, tau_i)
            # label pool: golden + every distinct cand + live boxes
            pool = []
            seen = set()
            for cd in (e_t.cand_log or []):
                if cd.get("kind") != "BOX":
                    continue
                if (cd.get("cet_min") or 0) > tau:
                    continue
                if cd.get("top") is None:
                    continue
                k = (round(cd["top"], 1), round(cd["bottom"], 1),
                     cd.get("t0"), cd.get("t1"))
                if k in seen:
                    continue
                seen.add(k)
                ci0 = int(max(0, min(cd.get("t0") or 0, len(m) - 1)))
                ci1 = int(max(0, min(cd.get("t1") or 0, len(m) - 1)))
                pool.append((cd["bottom"], cd["top"], ci0, ci1))
            for r in live:
                if r["type"] != "BOX":
                    continue
                ob2 = next((o2 for o2 in e_t.objects
                            if o2.id == r["id"]), None)
                if ob2 is None:
                    continue
                g2o = getattr(ob2, "geometry", {}) or {}
                if g2o.get("top") is None:
                    continue
                k = (round(g2o["top"], 1), round(g2o["bottom"], 1))
                if k in seen:
                    continue
                seen.add(k)
                pool.append((g2o["bottom"], g2o["top"],
                             int(np.searchsorted(
                                 m, r.get("t_birth") or w0)), tau_i))
            fpool = np.array([feats(a, b, c0, c1, o, h, l, c, ema, abr,
                                    day_lo, day_hi, tau_i)
                              for a, b, c0, c1 in pool]) \
                if pool else np.zeros((0, 10))
            pairs.append((f_g, f_p, fpool))
    print("pairs:", len(pairs))
    obs = np.array([pg - pp for pg, pp, _ in pairs])  # n_pairs x 10
    obs_mean = obs.mean(axis=0)
    # null: per draw, per pair pick a random pool rect as pseudo-golden
    null = np.zeros((DRAWS, len(HNAMES)))
    for d in range(DRAWS):
        diffs = []
        for pg, pp, fpool in pairs:
            if len(fpool) == 0:
                diffs.append(pg - pp)
                continue
            k = RNG.randint(len(fpool))
            diffs.append(fpool[k] - pp)
        null[d] = np.mean(diffs, axis=0)
    p95 = np.percentile(null, 95, axis=0)
    print("%-13s %9s %9s %9s  %s" % ("hyp", "obs", "null_p95",
                                   "null_mean", "verdict"))
    for i, nm in enumerate(HNAMES):
        print("%-13s %9.3f %9.3f %9.3f  %s"
              % (nm, obs_mean[i], p95[i], null[:, i].mean(),
                 "KEEP" if obs_mean[i] > p95[i] else "drop"))


if __name__ == "__main__":
    main()
