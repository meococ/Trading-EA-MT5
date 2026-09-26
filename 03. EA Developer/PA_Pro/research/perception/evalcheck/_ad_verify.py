"""EVAL-AUDIT s.86.4 - independent verify of boxlab/AD_EST.md.

Own implementation of the same spec (ad_est.py read for semantics):
  incumbent = last BOX object carrying geometry['meta_ev_route'],
  alive at tau.  Per bar j the current version is the last band
  write <= j.  A pending box-family cand qualifies when:
    (a) cand.first_idx > incumbent's last write bar,
    (b) close[j] inside cand's band +- tol_e(abr[j]),
    (c) close[j] outside incumbent's current band +- tol_e(abr[j]),
    (d) AD-b only: current band s_box_broken (j_from = object t_left
        for real versions, cand t0 for adopted) AND cand.first >
        exit_bar.
  Effect: best-score qualifying cand is adopted -> new version
  [j, cand.lo, cand.hi, cand.t0], cand consumed.
  At tau the final version's band is scored against the golden by
  V2.match - real hits, not bounds.

usage: python evalcheck/_ad_verify.py [--panels 9.17b,9.33c]
"""
import collections
import glob
import json
import os
import pickle
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import trade_tags as TT                         # noqa: E402
from snapshot import tau_of, live_records       # noqa: E402

ARM_V, ARM_H = "uip2_pbbirth", "8361fe85e73f9437"
RE_W = re.compile(r"\[(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\]"
                  r".*?t0=(\d+)")
BOXK = ("BOX", "RANGE_OPEN", "CONTEXT_RANGE")
TERM = {"uip_skip_pb", "born", "vetoed_height", "vetoed_irrelevant",
        "uip_birth", "uip_rewrite", "expired", "dedup_existing",
        "revived", "lvfree_seed_veto", "below_min_score",
        "uip_spent", "nms_suppressed", "route_shadow",
        "vetoed_cooldown"}
NAMED12 = ("9.10c", "9.11b", "9.17b", "9.25a", "9.2b", "9.33c",
           "9.36c", "9.40a", "9.42b", "9.48b", "9.52a", "9.57b")


def ev_object(e):
    evs = [o for o in e.objects if o.type == "BOX"
           and o.geometry.get("meta_ev_route")]
    return evs[-1] if evs else None


def band_seq(o, e):
    g = o.geometry
    seq = []
    if (o.why or "").startswith("ev_") and o.type == "BOX":
        b = [cd for cd in e.cand_log
             if cd.get("outcome") == "uip_birth"
             and cd.get("idx") == o.t_birth]
        if b:
            seq.append((int(o.t_birth), float(b[-1]["bottom"]),
                        float(b[-1]["top"]),
                        int(b[-1].get("t0") or 0)))
        for ev in o.events:
            if ev[1] == "uip_rewrite":
                mm = RE_W.search(str(ev[2]))
                if mm:
                    seq.append((int(ev[0]), float(mm.group(1)),
                                float(mm.group(2)),
                                int(mm.group(3))))
        if seq:
            return sorted(seq, key=lambda v: v[0])
    if "bottom" in g:
        return [(int(o.t_birth or 0), float(g["bottom"]),
                 float(g["top"]), int(g.get("t0") or o.t_left or 0))]
    return seq


def cand_map(e):
    out = {}
    for cd in e.cand_log:
        if cd.get("kind") not in BOXK or cd.get("idx") is None:
            continue
        sig = (cd.get("route"), round(cd.get("bottom") or 0, 1),
               round(cd.get("top") or 0, 1), cd.get("t0"))
        r = out.setdefault(sig, {"first": cd["idx"],
                                 "last": cd["idx"], "term": None,
                                 "score": -1e18,
                                 "route": cd.get("route"),
                                 "lo": cd.get("bottom"),
                                 "hi": cd.get("top"),
                                 "t0": cd.get("t0")})
        r["first"] = min(r["first"], cd["idx"])
        r["last"] = max(r["last"], cd["idx"])
        if cd.get("score") is not None:
            r["score"] = max(r["score"], cd["score"])
        if cd.get("outcome") in TERM and r["term"] is None:
            r["term"] = cd["idx"]
    return out


def pending_at(cmap, j):
    return [r for r in cmap.values()
            if r["first"] <= j <= r["last"]
            and (r["term"] is None or r["term"] > j)]


def simulate_ad(e, j_tau, c, abr, variant, cmap=None):
    ob = ev_object(e)
    if ob is None or ob.t_birth is None or ob.t_birth > j_tau:
        return [], []
    if ob.t_right is not None and ob.t_right <= j_tau:
        return [], []
    seq0 = band_seq(ob, e)
    if not seq0:
        return [], []
    if cmap is None:
        cmap = cand_map(e)
    # version: [write_bar, lo, hi, t0, src, j_from]
    vers = [[b_, lo_, hi_, t0_, "real", int(ob.t_left or 0)]
            for (b_, lo_, hi_, t0_) in seq0]
    events = []
    consumed = set()
    for j in range(j_tau + 1):
        cur = None
        for v in vers:
            if v[0] <= j:
                cur = v
        if cur is None:
            continue
        tol = TT.tol_e(abr[j] if j < len(abr) else 5.0)
        lo_i, hi_i = cur[1], cur[2]
        if lo_i - tol <= c[j] <= hi_i + tol:
            continue          # close inside incumbent band
        qual = []
        for r in pending_at(cmap, j):
            if id(r) in consumed or r["first"] <= cur[0]:
                continue
            if not (r["lo"] - tol <= c[j] <= r["hi"] + tol):
                continue
            if variant == "b":
                bb = TT.s_box_broken(lo_i, hi_i, cur[5], j,
                                     np.asarray(c),
                                     np.asarray(abr))
                if not bb["bbroken"] \
                        or r["first"] <= bb["exit_bar"]:
                    continue
            qual.append(r)
        if not qual:
            continue
        best = max(qual, key=lambda r: r["score"])
        vers.append([j, float(best["lo"]), float(best["hi"]),
                     int(best.get("t0") or j), "adopt",
                     int(best.get("t0") or j)])
        vers.sort(key=lambda v: v[0])
        consumed.add(id(best))
        events.append(dict(bar=j, lo=best["lo"], hi=best["hi"],
                           route=best["route"],
                           first=best["first"],
                           score=best["score"]))
    return vers, events


def band_of(vers, j):
    cur = None
    for v in vers:
        if v[0] <= j:
            cur = v
    return cur


def er_rec(lo, hi, t0_bar, tau, m, w0):
    return dict(type="BOX", lo=lo, hi=hi,
                t0=int(m[min(int(t0_bar), len(m) - 1)]),
                t1=int(tau), w0=w0, w1=int(tau))


def base_rec(by_date, date, w1):
    cand = [x for x in by_date[date]
            if x["window"]["x0"] <= w1
            <= (x["window"]["x1"] or 1439)]
    for x in cand:
        w0 = x["window"]["x0"]
        w1f = x["window"]["x1"] or 1439
        g2 = [g for g in EV.gold_objects(x)[0]
              if V2.scorable(g, w0, w1f)]
        if any(tau_of(g) is not None
               and min(tau_of(g), w1f) == w1 for g in g2):
            return x
    return cand[0] if cand else None


def main():
    only = None
    if "--panels" in sys.argv:
        only = set(sys.argv[sys.argv.index("--panels") + 1]
                   .split(","))
    recs = list(C.load_tune())
    by_date = collections.defaultdict(list)
    for r in recs:
        by_date[r["date"]].append(r)

    stats = {v: dict(lost=0, gained=0, adopt=[], rows=0)
             for v in "ab"}
    named = {v: {} for v in "ab"}
    files = sorted(glob.glob(os.path.join(
        CA.CACHE, "run_%s_%s_*.pkl" % (ARM_V, ARM_H))))
    for f in files:
        stem = os.path.basename(f)[:-4]
        date, w1s = stem.rsplit("_", 2)[1:]
        w1 = int(w1s)
        rec = base_rec(by_date, date, w1)
        if rec is None:
            continue
        if only and rec["id"] not in only:
            continue
        w0 = rec["window"]["x0"]
        g2 = [g for g in EV.gold_objects(rec)[0]
              if V2.scorable(g, w0, w1)]
        g_box = [g for g in g2
                 if EV.FAMILY.get(g["spec_type"]) == "box"
                 and tau_of(g) is not None
                 and min(tau_of(g), rec["window"]["x1"] or 1439)
                 == w1]
        if not g_box:
            continue
        e = pickle.load(open(f, "rb"))
        _t, m, _o, _h, _l, c = CA.bars(date)
        m = np.asarray(m)
        abr = np.asarray(CA.abr(date))
        j_tau = min(int(np.searchsorted(m, w1)), len(e.bars) - 1)
        # real-run match (baseline)
        _tm, mm, _om, _hm, _lm, _cm = CA.bars(date)
        mm = np.asarray(mm)
        live, _em = live_records(e, mm, w0, w1)
        osc = {ob.id: getattr(ob, "score", None)
               for ob in e.objects}
        for r in live:
            r["score"] = osc.get(r["id"])
        import recall_at_k as RK
        ranked = RK.rank_live(live, RK.score_map(e))
        top = [r for r in ranked
               if EV.FAMILY.get(r["type"]) == "box"][:1]
        base_hit = bool(top) and any(
            V2.match(g, top[0], mm) for g in g_box)
        cm = cand_map(e)
        for v in "ab":
            vers, evs = simulate_ad(e, j_tau, np.asarray(c), abr,
                                    v, cm)
            b = band_of(vers, j_tau) if vers else None
            sim_hit = False
            if b is not None:
                # engine-consistent anchor: ob.t_left for real
                # versions, cand t0 for adopted (their v[5] column)
                er = er_rec(b[1], b[2], b[5], w1, m, w0)
                sim_hit = any(V2.match(g, er, m) for g in g_box)
            st = stats[v]
            st["rows"] += 1
            st["adopt"].append(len(evs))
            if base_hit and not sim_hit:
                st["lost"] += 1
                st.setdefault("lost_rows", []).append(
                    (rec["id"], w1, len(evs)))
            if sim_hit and not base_hit:
                st["gained"] += 1
                st.setdefault("gained_rows", []).append(
                    (rec["id"], w1, len(evs)))
            if rec["id"] in NAMED12:
                named[v][rec["id"]] = (len(evs), sim_hit)
    for v in "ab":
        st = stats[v]
        ad = np.asarray(st["adopt"])
        print("AD-%s: rows=%d lost=%d %s gained=%d %s | adoptions "
              "med=%.0f p90=%.0f max=%d"
              % (v, st["rows"], st["lost"],
                 st.get("lost_rows"), st["gained"],
                 st.get("gained_rows"),
                 np.median(ad), np.percentile(ad, 90), ad.max()))
        for p in NAMED12:
            if p in named[v]:
                print("   %-6s adopt=%d sim_hit=%s"
                      % (p, named[v][p][0], named[v][p][1]))


if __name__ == "__main__":
    main()
