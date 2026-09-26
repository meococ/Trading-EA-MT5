"""e12_selftest.py — Ruling 7 items 1-2 / mandate E1+E2.

E1  Feed the golden v2 objects to a matcher as if they were engine
    output.  Two variants:

      A "identical" — engine record = golden coords verbatim.  Tests the
        matcher's self-consistency: anything below 1.0 is an internal
        contradiction in the ruler itself.
      B "realistic" — engine record constrained like real engine output:
        times snapped to the M5 bar grid, BAR_MARKER drawn as a point,
        and the eng_objects visibility filter applied (objects with
        t1 < w0 or t0 > w1 are dropped, eval.py:114).  Exposes
        ruler/golden boundary asymmetries.

E2  Perturb each golden object inside its own label precision
    (common.prec_sigmas) and re-match.  Report recall per type at
    0.5x / 1x / 2x the precision, N draws per object.

Usage:
    python evalcheck/e12_selftest.py              # E1 A+B vs eval.py
    python evalcheck/e12_selftest.py --jitter     # + E2 vs eval.py
    python evalcheck/e12_selftest.py --v2         # run vs eval_v2 matcher
"""
import argparse
import collections
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C                              # noqa: E402
import eval as EV                               # noqa: E402

N_JITTER = 200


# ------------------------------------------------------------------ #
# synthesis
# ------------------------------------------------------------------ #

def _snap(m, t):
    """Nearest bar's cet_min (what a real engine can produce)."""
    if t is None:
        return None
    return int(m[int(np.argmin(np.abs(m - t)))])


def synth(g, m, realistic=False, rng=None, k=0.0):
    """Golden object -> engine-format record.

    realistic: snap times to the bar grid, BAR_MARKER = point marker.
    k>0: apply a uniform perturbation of +/-k * label precision.
    """
    e = C.gold_as_engine(g, m)
    gt = g["spec_type"]
    ps, ts = C.prec_sigmas(g)

    def jit(v, sig):
        return None if v is None else v + rng.uniform(-k * sig, k * sig)

    if k > 0.0:
        e["t0"] = jit(e["t0"], ts)
        e["t1"] = jit(e["t1"], ts)
        if e["t0"] is not None and e["t1"] is not None \
                and e["t1"] < e["t0"]:
            e["t0"], e["t1"] = e["t1"], e["t0"]     # a sane engine draws
        e["t_birth"] = jit(e["t_birth"], ts)       # spans ordered
        if "bs" in e:
            e["bs"] = jit(e["bs"], ts)
        if "be" in e:
            e["be"] = jit(e["be"], ts)
        if e.get("bs") is not None and e.get("be") is not None \
                and e["be"] < e["bs"]:
            e["bs"], e["be"] = e["be"], e["bs"]
        if "lo" in e:
            e["lo"], e["hi"] = jit(e["lo"], ps), jit(e["hi"], ps)
            if e["lo"] > e["hi"]:
                e["lo"], e["hi"] = e["hi"], e["lo"]
        if "price" in e:
            e["price"] = jit(e["price"], ps)
        if "p0" in e:
            # endpoints jitter as (time, price) pairs, then re-ordered —
            # swapping t0/t1 without their prices would flip the slope
            p0a = e["p0"]
            p1a = e["p0"] + e["slope"] * _bar_delta(e, m)
            pts = sorted([(e["t0"], jit(p0a, ps)),
                          (e["t1"], jit(p1a, ps))])
            (e["t0"], p0), (e["t1"], p1) = pts
            j0, j1 = _bar_of_pair(e, m)
            e["t0_bar"] = j0
            e["slope"] = (p1 - p0) / max(j1 - j0, 1)
            e["p0"] = p0
    if realistic:
        e["t0"] = _snap(m, e["t0"])
        e["t1"] = _snap(m, e["t1"])
        e["t_birth"] = _snap(m, e["t_birth"])
        if "t0_bar" in e:
            e["t0_bar"] = int(np.argmin(np.abs(m - e["t0"])))
        if gt == "BAR_MARKER":                      # a marker is a point
            e["t1"] = e["t0"]
    return e


def _bar_of_pair(e, m):
    j0 = int(np.argmin(np.abs(m - e["t0"]))) if e["t0"] is not None else 0
    j1 = int(np.argmin(np.abs(m - e["t1"]))) if e["t1"] is not None else j0
    return j0, max(j1, j0)


def _bar_delta(e, m):
    j0, j1 = _bar_of_pair(e, m)
    return j1 - j0


def synth_mark(gm, m, w0=0, realistic=False, rng=None, k=0.0):
    e = C.mark_as_engine(gm, w0)
    if k > 0.0 and e["t_birth"] is not None:
        e["t_birth"] = e["t_birth"] + rng.uniform(-k * C.TIME_SIGMA_MIN,
                                                  k * C.TIME_SIGMA_MIN)
        e["t0"] = e["t1"] = e["t_birth"]
    if realistic:
        e["t_birth"] = _snap(m, e["t_birth"])
        e["t0"] = e["t1"] = e["t_birth"]
    return e


# ------------------------------------------------------------------ #
# miss diagnosis — walk eval.match's clauses and name the first failure
# ------------------------------------------------------------------ #

def explain_miss(g, e, m):
    """Short string: which eval.match clause rejects a self-copy."""
    gt = g["spec_type"]
    if EV.FAMILY.get(gt) != EV.FAMILY.get(e["type"]):
        return "family mismatch (eval.py:193)"
    t_only = C.is_time_only(g)
    s = EV.iou(g["t0"], g["t1"], e["t0"], e["t1"])
    if gt == "BOX":
        if s < 0.5 or t_only:
            return "BOX span IoU %.2f<0.5 (eval.py:199)" % s
        if e.get("lo") is None:
            return "engine box has no edges (eval.py:204)"
        tol = EV._tol_px(g)
        lo_g = (g.get("price_lo") or 0) / C.PIP
        hi_g = (g.get("price_hi") or 0) / C.PIP
        if abs(e["lo"] - lo_g) > tol:
            return "BOX lo diff %.1fp>%.1f (eval.py:205)" % (
                abs(e["lo"] - lo_g), tol)
        if abs(e["hi"] - hi_g) > tol:
            return "BOX hi diff %.1fp>%.1f (eval.py:206)" % (
                abs(e["hi"] - hi_g), tol)
        return "BOX ok??"
    if gt == "PATTERN_LINE":
        if e.get("p0") is None:
            return "engine line has no p0 (eval.py:208)"
        if t_only:
            return "LINE span IoU %.2f<0.5 t_only (eval.py:211)" % s
        tol = EV._tol_px(g)
        p0g, p1g = g.get("price0"), g.get("price1")
        if p0g is not None and p1g is not None:
            d0 = abs(e["t0"] - g["t0"])
            d1 = abs(e["t1"] - g["t1"])
            pe0 = EV._line_price_at(e, g["t0"], m)
            pe1 = EV._line_price_at(e, g["t1"], m)
            bad = []
            if d0 > 15:
                bad.append("t0 %.0f>15min" % d0)
            if d1 > 15:
                bad.append("t1 %.0f>15min" % d1)
            if abs(pe0 - p0g / C.PIP) > tol:
                bad.append("p0 %.1f>%.1fp" % (abs(pe0 - p0g / C.PIP), tol))
            if abs(pe1 - p1g / C.PIP) > tol:
                bad.append("p1 %.1f>%.1fp" % (abs(pe1 - p1g / C.PIP), tol))
            return ("LINE endpoint " + ";".join(bad) + " (eval.py:217-220)"
                    if bad else "LINE ok??")
        gd = {"up": 1, "down": -1}.get(g.get("dir"))
        if s < 0.5:
            return "LINE span IoU %.2f<0.5 (eval.py:223)" % s
        if gd is not None and gd != e.get("dirn"):
            return "LINE dir %s vs %s (eval.py:224)" % (gd, e.get("dirn"))
        return "LINE ok??"
    if gt in ("LEVEL_CARRIED", "MINI_LEVEL"):
        if g.get("price") is None or e.get("price") is None:
            return "LEVEL fallback IoU %.2f<0.3 (eval.py:227)" % s
        if abs(e["price"] - g["price"] / C.PIP) > 2.0:
            return "LEVEL price %.1fp>2.0 (eval.py:228)" % (
                abs(e["price"] - g["price"] / C.PIP))
        return "LEVEL no span overlap (eval.py:229-231)"
    if gt == "BRACKET":
        fam = lambda x: (x or "").replace("m", "").replace("w", "") \
            .replace("i", "")
        if s < 0.3:
            return "BRACKET IoU %.2f<0.3 (eval.py:235)" % s
        return "BRACKET letter %s vs %s (eval.py:236)" % (
            g.get("letter"), e.get("letter"))
    if gt == "SQUEEZE":
        return "SQUEEZE IoU %.2f<0.3 (eval.py:238)" % s
    if s < 0.3:
        return "%s span IoU %.2f<0.3 (eval.py:240)" % (gt, s)
    if g.get("price") is not None and e.get("price") is not None \
            and abs(e["price"] - g["price"] / C.PIP) > EV._tol_px(g):
        return "%s price tol (eval.py:243)" % gt
    if g.get("price_hi") is not None and e.get("hi") is not None:
        tol = EV._tol_px(g)
        if abs(e["lo"] - g["price_lo"] / C.PIP) > tol or \
                abs(e["hi"] - g["price_hi"] / C.PIP) > tol:
            return "%s edges tol (eval.py:246)" % gt
    return "%s ok??" % gt


# ------------------------------------------------------------------ #
# drivers
# ------------------------------------------------------------------ #

def build_panel(rec, matchmod, realistic=False, rng=None, k=0.0,
                gold_filter=None, mark_filter=None):
    """Assemble golden + synthetic-engine records for one panel.

    gold_filter/mark_filter (eval_v2's scorable boundary) drop golden
    items the engine could never produce inside the scored window."""
    w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
    _t, m, _o, _h, _l, _c = EV.day_bars(rec["date"])
    gobjs, n_un, n_to = EV.gold_objects(rec)
    for g in gobjs:                                  # eval.py:281-285
        if g.get("t0") is None:
            g["t0"] = w0
        if g.get("t1") is None:
            g["t1"] = w1
    if gold_filter is not None:
        gobjs = [g for g in gobjs if gold_filter(g, w0, w1)]
    gmarks = EV.gold_marks(rec)
    if mark_filter is not None:
        gmarks = [gm for gm in gmarks if mark_filter(gm, w0, w1)]
    eobjs = []
    for gi, g in enumerate(gobjs):
        e = synth(g, m, realistic, rng, k)
        e["src"] = gi
        e["w0"], e["w1"] = w0, w1
        eobjs.append(e)
    for mi, gm in enumerate(gmarks):
        e = synth_mark(gm, m, w0, realistic, rng, k)
        e["src"] = ("m", mi)
        e["w0"], e["w1"] = w0, w1
        eobjs.append(e)
    if realistic:                                    # eval.py:114 filter
        eobjs = [e for e in eobjs
                 if not (e["t1"] is not None and e["t1"] < w0)
                 and not (e["t0"] is not None and e["t0"] > w1)]
    emarks = [e for e in eobjs if e["type"] == "LABEL_TF"]
    return gobjs, eobjs, gmarks, emarks, m, w0, w1


def run_e1(recs, matchfn, markfn, scorefn=None, realistic=False,
           gold_filter=None, mark_filter=None):
    """Self-test.  Returns (per_type tally, miss list)."""
    agg = collections.defaultdict(lambda: {"g": 0, "e": 0, "m": 0})
    misses = []
    for rec in recs:
        gobjs, eobjs, gmarks, emarks, m, w0, w1 = build_panel(
            rec, None, realistic, gold_filter=gold_filter,
            mark_filter=mark_filter)
        pairs, mpairs = C.match_panel(gobjs, eobjs, gmarks, emarks, m,
                                      matchfn, markfn, scorefn)
        pt = C.tally(gobjs, eobjs, gmarks, pairs, mpairs)
        for t, d in pt.items():
            for kk in d:
                agg[t][kk] += d[kk]
        mg = {gi for gi, _ in pairs}
        for gi, g in enumerate(gobjs):
            if gi in mg:
                continue
            own = [e for e in eobjs if e.get("src") == gi]
            reason = explain_miss(g, own[0], m) if own else \
                "copy dropped: outside panel window (eval.py:114)"
            misses.append((rec["id"], g["spec_type"], g.get("status"),
                           (g["t0"], g["t1"]), w0, w1, reason))
        gm_hit = {id(gm) for gm, _ in mpairs}
        for gm in gmarks:
            if id(gm) not in gm_hit:
                misses.append((rec["id"], "LABEL_TF(mark)", None,
                               (gm.get("t"), None), w0, w1,
                               "mark unmatched"))
    return agg, misses


def print_table(agg, tag):
    print("\n## %s" % tag)
    print("| type | golden | engine | matched | recall | precision |")
    print("|---|---|---|---|---|---|")
    for t in sorted(agg):
        d = agg[t]
        r = d["m"] / d["g"] if d["g"] else float("nan")
        p = d["m"] / d["e"] if d["e"] else float("nan")
        print("| %s | %d | %d | %d | %.3f | %.3f |"
              % (t, d["g"], d["e"], d["m"], r, p))
    g = sum(d["g"] for d in agg.values())
    mh = sum(d["m"] for d in agg.values())
    print("TOTAL recall %.4f (%d/%d)" % (mh / g if g else 0, mh, g))
    return mh / g if g else 0.0


def run_e2(recs, matchfn, markfn, ks=(0.5, 1.0, 2.0), n=N_JITTER,
           seed=7, gold_filter=None, mark_filter=None):
    """Jitter test: per-object 1:1 matching under perturbation."""
    rng = np.random.default_rng(seed)
    out = collections.defaultdict(
        lambda: collections.defaultdict(list))     # type -> k -> hits
    for rec in recs:
        _t, m, _o, _h, _l, _c = EV.day_bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        for g in gobjs:
            if g.get("t0") is None:
                g["t0"] = w0
            if g.get("t1") is None:
                g["t1"] = w1
            # outside-window objects are unscorable either way
            if g["t1"] < w0 or g["t0"] > w1:
                continue
            if gold_filter is not None and not gold_filter(g, w0, w1):
                continue
            for k in ks:
                hits = 0
                for _ in range(n):
                    e = synth(g, m, realistic=True, rng=rng, k=k)
                    e["w0"], e["w1"] = w0, w1
                    hits += bool(matchfn(g, e, m))
                out[g["spec_type"]][k].append(hits / n)
        for gm in EV.gold_marks(rec):
            if mark_filter is not None and not mark_filter(gm, w0, w1):
                continue
            for k in ks:
                hits = 0
                for _ in range(n):
                    em = synth_mark(gm, m, realistic=True, rng=rng, k=k)
                    hits += bool(markfn(gm, em))
                out["LABEL_TF"][k].append(hits / n)
    print("\n## E2 jitter recall (object-level, realistic engine copy)")
    print("| type | n | rec@0.5x | rec@1x | rec@2x |")
    print("|---|---|---|---|---|")
    for t in sorted(out):
        row = "| %s | %d |" % (t, len(out[t][ks[0]]))
        for k in ks:
            row += " %.3f |" % (float(np.mean(out[t][k]))
                               if out[t][k] else float("nan"))
        print(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jitter", action="store_true")
    ap.add_argument("--v2", action="store_true")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    matchfn, markfn, scorefn, tag = EV.match, EV.match_mark, None, "eval.py"
    gfil = mfil = None
    if args.v2:
        import eval_v2
        matchfn, markfn, scorefn, tag = \
            eval_v2.match, eval_v2.match_mark, eval_v2.score, "eval_v2"
        gfil, mfil = eval_v2.scorable, eval_v2.scorable_mark

    recs = C.load_tune()
    print("panels:", len(recs), " matcher:", tag)

    for realistic in (False, True):
        agg, misses = run_e1(recs, matchfn, markfn, scorefn, realistic,
                             gold_filter=gfil, mark_filter=mfil)
        print_table(agg, "E1%s self-test vs %s (%s)"
                  % ("AB"[realistic], tag,
                     "realistic engine copy" if realistic
                     else "identical copy"))
        for x in misses:
            print("  MISS", x)

    if args.jitter:
        run_e2(recs, matchfn, markfn, seed=args.seed,
               gold_filter=gfil, mark_filter=mfil)


if __name__ == "__main__":
    main()
