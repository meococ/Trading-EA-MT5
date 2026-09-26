"""h0_hybrid.py — R78 s78.4(1): H0 hybrid generator estimate on C-3.

Compose, per canonical (panel,tau) window:
  H0-a: C-3 boxes@1 + C-3 lines@2 + donchian levels |C1@1.0| @1
  H0-b: C-3 boxes@1 + C-3 levels@1 + tdlines k2 |C7@2| @2
  H0-c: both substitutions.

C-3 = STABLE uip2_pbbirth@8361fe85e73f9437 tau-clipped caches (the 623
windows of R75 s75.6).  Brackets and marks stay C-3's.

All scoring via evalcheck/eval_v2.py (imported); engine-side picks via
snapshot.live_records + recall_at_k.rank_live (the replay path, not a
new selector); baseline-side features via DR_RULES_baselines.feats
(imported); rule gates C1@1.0 / C7@2 via DR_RULES_baselines.passes.

Clutter = the PUBLISHED cumulative window census: per panel
(objects intersecting [w0,w1] + marks) / scorable goldens, median —
the C-3 row's 4.33 convention, NOT the live-at-tau census.

Usage (PA_Pro cwd):
  python research/perception/practice/baselines/h0_hybrid.py
Outputs: practice/baselines/h0_{a,b,c}.jsonl + h0_summary.json
"""
import collections
import json
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PRACTICE = os.path.dirname(HERE)
PERC = os.path.dirname(PRACTICE)
for _p in (os.path.join(PERC, "evalcheck"), PERC,
           os.path.join(PERC, "deepresearch"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import recall_at_k as RK                        # noqa: E402
from snapshot import tau_of, live_records       # noqa: E402
from bl_common import _rec                      # noqa: E402
import DR_RULES_measure as M                    # noqa: E402
import DR_RULES_baselines as FB                 # noqa: E402
import b_tdlines                                # noqa: E402
import b_donchian                               # noqa: E402

FAM_BUDGET = {"box": 1, "line": 2, "level": 1, "bracket": 1}
ARMS = {"a": {"level": ("donchian", "C1@1.0")},
        "b": {"line": ("tdlines", "C7@2")},
        "c": {"level": ("donchian", "C1@1.0"),
              "line": ("tdlines", "C7@2")}}
EMITS = {"donchian": b_donchian.emit, "tdlines": b_tdlines.emit}
SEED = 78
C6G_TOL = 2.0          # meas-precision ruler tol proxy for C6g on
                       # non-golden objects (golden tol_px in {1.5,2,5})


# ------------------------------------------------------------------ #
def events_for(rec, g2, gmarks, w0, w1):
    """Canonical window set (DR_RULES_measure): golden scorable taus +
    mark taus + w1 panel-end."""
    by_tau = collections.defaultdict(list)
    for gi, g in enumerate(g2):
        tau = tau_of(g)
        if tau is not None and tau >= w0:
            by_tau[min(tau, w1)].append((gi, g))
    mark_taus = {gm["t"] for gm in gmarks
                 if gm.get("t") is not None and w0 <= gm["t"] <= w1}
    for tau in mark_taus:
        by_tau.setdefault(tau, [])
    if w1 not in by_tau:
        by_tau[w1] = []
    return by_tau


def eng_feats_for_picks(e, picks, mp, o, h, l, c, ema, abr, pivots,
                        nfed):
    """eng_stats per picked engine record (o_by_id lookup)."""
    o_by_id = {ob.id: ob for ob in e.objects}
    out = {}
    for r in picks:
        ob = o_by_id.get(r["id"])
        if ob is not None:
            out[r["id"]] = M.eng_stats(ob, mp, o, h, l, c, ema, abr,
                                       pivots, nfed)
    return out


def baseline_picks(objs_day, fam, rule, w0, tau, mp, cp, ema, abr20,
                   pivots, nfed):
    """Live baseline objects at tau -> _rec records -> rule filter ->
    ranked top-k.  Mirrors DR_RULES_baselines (sort, feats, keep[:k])."""
    live = [x for x in objs_day if x["birth"] <= tau and
            (x["die"] is None or x["die"] > tau)]
    j1 = min(M.jle(mp, tau), nfed)
    last_min = int(mp[j1])
    recs_live = [_rec(x, w0, tau, last_min) for x in live]
    recs_live.sort(key=lambda r: (-r["_score"], -r["t_birth"]))
    recs_live = recs_live[:6]
    for i, r in enumerate(recs_live):
        r["id"] = "bl_%s_%d" % (fam, i)      # _rec ids all "b" — make
                                             # unique per fam+rank for
                                             # stats lookup (fam[0]
                                             # collides: level/line)
    live_sorted = sorted(live, key=lambda x: (-x["score"],
                                              -x["birth"]))[:6]
    fts = [FB.feats(x, fam, j1, mp, cp, ema, abr20, pivots, nfed)
           for x in live_sorted]
    keep = [(r, ft) for r, ft in zip(recs_live, fts)
            if ft is None or FB.passes(ft, fam, rule, {})]
    return [r for r, _ in keep], [ft for _, ft in keep], \
        list(zip(recs_live, fts))


def m2_pass(fam, st):
    """M2-facing pass predicates on an eng_stats/feats dict (None =
    not evaluable).  C1-box, C3w@3.0, C4w@4, C6g@2.0-proxy, C7f@2,
    C8a@1."""
    out = {}
    if fam == "box":
        out["C1@1.0"] = (None if st.get("c1_abr") is None
                         else st["c1_abr"] <= 1.0)
        out["C3w@3.0"] = (None if st.get("c3_r_win") is None
                          else st["c3_r_win"] < 3.0)
        out["C4w@4"] = (None if st.get("c4_r_win") is None
                        else st["c4_r_win"] < 4.0)
        out["C6g@2.0"] = (None if st.get("c6_maxd") is None
                          else st["c6_maxd"] <= C6G_TOL)
    if fam in ("level", "line"):
        out["C7f@2"] = (None if st.get("c7_sw_full") is None
                        else st["c7_sw_full"] <= 2)
    if fam == "level":
        out["C8a@1"] = (True if st.get("c8_beyond_abr_anch") is None
                        else st["c8_beyond_abr_anch"] < 1.0)
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    recs = C.load_tune()
    if args.limit:
        recs = recs[:args.limit]
    emit_cache = {}       # date -> {name: objs}
    # per arm: per-event golden hit flags + clutter + m2 diag
    hits = {a: collections.defaultdict(dict) for a in "abc"}
    c3_hits = collections.defaultdict(dict)   # (panel,gi) -> bool
    gold_fam_of = {}
    census = {a: [] for a in "abc"}
    census["c3"] = []
    m2rows = {a: [] for a in "abc"}
    n_ev = n_miss = 0

    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        m = np.asarray(m); o = np.asarray(o); h = np.asarray(h)
        l = np.asarray(l); c = np.asarray(c)
        if rec["date"] not in emit_cache:
            abr50 = CA.abr(rec["date"])
            emit_cache[rec["date"]] = {
                nm: fn(t, m, o, h, l, c, abr50) or []
                for nm, fn in EMITS.items()}
        day_objs = emit_cache[rec["date"]]
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        gmarks = [gm for gm in EV.gold_marks(rec)
                  if V2.scorable_mark(gm, w0, w1)]
        for gi, g in enumerate(g2):
            gold_fam_of[(rec["id"], gi)] = EV.FAMILY.get(
                g["spec_type"])
        by_tau = events_for(rec, g2, gmarks, w0, w1)

        # ---------- census at w1 (published cumulative method) ------
        e_full = M.pickled(rec["date"], w1)
        if e_full is not None:
            erec = V2.eng_objects(e_full, m, w0, w1)
            eboxes = [r for r in erec if r["type"] != "LABEL_TF"]
            emarks = [r for r in erec if r["type"] == "LABEL_TF"]
            n_c3 = len(eboxes) + len(emarks)
            if g2:
                census["c3"].append(n_c3 / len(g2))
            mp = np.array([b["cet_min"] for b in e_full.bars])
            cp = np.array([b["c"] for b in e_full.bars])
            ema = np.asarray(e_full.ema)
            abr20 = np.asarray(e_full.abr)
            pivots = e_full.book.seq
            nfed = len(e_full.bars) - 1
            j1w = min(M.jle(mp, w1), nfed)
            c3_fam_n = collections.Counter()
            for r in eboxes:
                c3_fam_n[EV.FAMILY.get(r["type"])] += 1
            for arm, subs in ARMS.items():
                n_arm = n_c3
                for fam, (src, rule) in subs.items():
                    n_arm -= c3_fam_n[fam]
                    vis = [x for x in day_objs[src]
                           if x["birth"] <= w1 and
                           (x["die"] is None or x["die"] > w0)]
                    nfv = sum(1 for x in vis
                              if FB.passes(
                                  FB.feats(x, fam, j1w, mp, cp, ema,
                                           abr20, pivots, nfed),
                                  fam, rule, {}))
                    n_arm += nfv
                if g2:
                    census[arm].append(n_arm / len(g2))

        # ---------- canonical tau events ---------------------------
        e_cache = {}
        for tau, ggs in sorted(by_tau.items()):
            if tau not in e_cache:
                e_cache[tau] = M.pickled(rec["date"], tau)
            e = e_cache[tau]
            if e is None:
                n_miss += 1
                continue
            n_ev += 1
            mp = np.array([b["cet_min"] for b in e.bars])
            op = np.array([b["o"] for b in e.bars])
            hp = np.array([b["h"] for b in e.bars])
            lp = np.array([b["l"] for b in e.bars])
            cp = np.array([b["c"] for b in e.bars])
            ema = np.asarray(e.ema)
            abr20 = np.asarray(e.abr)
            pivots = e.book.seq
            nfed = len(e.bars) - 1
            live, emarks = live_records(e, m, w0, tau)
            osc = {ob.id: getattr(ob, "score", None)
                   for ob in e.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            ranked = RK.rank_live(live, RK.score_map(e))
            fam_ranked = collections.defaultdict(list)
            for r in ranked:
                fam_ranked[EV.FAMILY.get(r["type"])].append(r)
            c3_picks = {f: fam_ranked[f][:k]
                        for f, k in FAM_BUDGET.items()}
            # C-3 (parent) hit flags for this event
            gs = [g for _gi, g in ggs]
            for gi, g in ggs:
                fg = EV.FAMILY.get(g["spec_type"])
                if not fg:
                    continue
                c3_hits[(rec["id"], gi)] = any(
                    V2.match(g, r, mp) for r in c3_picks.get(fg, []))
            # arm picks + hits + m2 diag on picked objects
            for arm, subs in ARMS.items():
                picks = {f: list(v) for f, v in c3_picks.items()}
                bl_stats = {}
                for fam, (src, rule) in subs.items():
                    kp, fts, _all = baseline_picks(
                        day_objs[src], fam, rule, w0, tau, mp, cp,
                        ema, abr20, pivots, nfed)
                    picks[fam] = kp[:FAM_BUDGET[fam]]
                    for r, ft in zip(kp[:FAM_BUDGET[fam]],
                                     fts[:FAM_BUDGET[fam]]):
                        bl_stats[r["id"]] = dict(ft)
                # full-span c7 for baseline lines/levels (feats lacks
                # c7_sw_full) — add here for the M2 diag
                for fam, (src, rule) in subs.items():
                    j1 = min(M.jle(mp, tau), nfed)
                    for r in picks[fam]:
                        if r["id"] in bl_stats and \
                                fam in ("level", "line"):
                            if fam == "level":
                                lp_ = lambda j, p=r["price"]: p
                            else:
                                lp_ = (lambda j, r=r:
                                       r["p0"] + r["slope"] *
                                       (j - r["t0_bar"]))
                            bl_stats[r["id"]]["c7_sw_full"] = \
                                M.s_c7(0, j1, cp, abr20, lp_)["c7_sw"]
                for gi, g in ggs:
                    fg = EV.FAMILY.get(g["spec_type"])
                    if not fg:
                        continue
                    hit = any(V2.match(g, r, mp)
                              for r in picks.get(fg, []))
                    hits[arm][(rec["id"], gi)] = hit
                # m2 diag: pass-rates on the arm's PICKED objects
                estats = eng_feats_for_picks(
                    e, [r for f in ("box", "level", "line")
                        for r in picks[f] if r["id"] not in bl_stats],
                    mp, op, hp, lp, cp, ema, abr20, pivots, nfed)
                for f in ("box", "level", "line"):
                    for r in picks[f]:
                        st = estats.get(r["id"]) or \
                            bl_stats.get(r["id"])
                        if st is None:
                            continue
                        st = dict(st); st["fam"] = f
                        for rule, ok in m2_pass(f, st).items():
                            if ok is not None:
                                m2rows[arm].append(
                                    {"arm": arm, "fam": f,
                                     "rule": rule, "pass": bool(ok)})

    # ---------------- aggregate ----------------
    def fam_counts(hitmap):
        out = collections.Counter()
        tot = collections.Counter()
        for (pid, gi), ok in hitmap.items():
            fam = gold_fam_of[(pid, gi)]
            if fam:
                tot[fam] += 1
                out[fam] += bool(ok)
        return out, tot

    summ = {"events": n_ev, "pkl_miss": n_miss, "arms": {},
            "c3": {}, "m2": {}}
    c3h, tot = fam_counts(c3_hits)
    summ["c3"] = {"hits": dict(c3h), "gold": dict(tot),
                  "clutter": float(np.median(census["c3"]))}
    for arm in ARMS:
        ah, _t = fam_counts(hits[arm])
        summ["arms"][arm] = {"hits": dict(ah), "gold": dict(tot),
                             "clutter": float(np.median(census[arm]))}
        # flips vs C-3
        fl = collections.defaultdict(lambda: [0, 0])
        for key, ok in hits[arm].items():
            fam = gold_fam_of[key]
            was = c3_hits.get(key, False)
            if ok and not was:
                fl[key[0], fam][0] += 1
            elif was and not ok:
                fl[key[0], fam][1] += 1
        summ["arms"][arm]["flips"] = {
            "%s|%s" % k: v for k, v in sorted(fl.items())}
        # m2 pass rates
        agg = collections.defaultdict(lambda: [0, 0])
        for r in m2rows[arm]:
            k = (r["fam"], r["rule"])
            agg[k][0] += r["pass"]
            agg[k][1] += 1
        summ["m2"][arm] = {"%s|%s" % k: [v[0], v[1]]
                           for k, v in sorted(agg.items())}

    # ---------------- prefix invariance (20 random panels/source) --
    rng = random.Random(SEED)
    pool = [r for r in recs
            if any((tau_of(g) is not None and
                    r["window"]["x0"] <= tau_of(g) <
                    (r["window"]["x1"] or 1439))
                   for g in [x for x in EV.gold_objects(r)[0]
                             if V2.scorable(x, r["window"]["x0"],
                                            r["window"]["x1"]
                                            or 1439)])]
    sample = rng.sample(pool, min(20, len(pool)))
    pref = {}
    for src, fn in EMITS.items():
        ok_ct = tot_ct = 0
        mism = []
        for rec in sample:
            w1 = rec["window"]["x1"] or 1439
            t, m, o, h, l, c = CA.bars(rec["date"])
            taus = sorted({min(tau_of(g), w1)
                           for g in EV.gold_objects(rec)[0]
                           if V2.scorable(g, rec["window"]["x0"], w1)
                           and tau_of(g) is not None
                           and rec["window"]["x0"] <= tau_of(g)})
            if not taus:
                continue
            tau = taus[0]
            jt = int(np.searchsorted(m, tau, side="right"))
            abr50 = CA.abr(rec["date"])
            full = fn(t, m, o, h, l, c, abr50) or []
            cut = fn(t[:jt], m[:jt], o[:jt], h[:jt], l[:jt],
                     c[:jt], abr50[:jt]) or []

            def key(x):
                return (x["type"], x["birth"], x["birth_drawn"],
                        repr(x.get("lo")), repr(x.get("hi")),
                        repr(x.get("price")), repr(x.get("p0")),
                        repr(x.get("slope")))
            lf = {key(x) for x in full if x["birth"] <= tau and
                  (x["die"] is None or x["die"] > tau)}
            lc = {key(x) for x in cut if x["birth"] <= tau and
                  (x["die"] is None or x["die"] > tau)}
            tot_ct += 1
            if lf == lc:
                ok_ct += 1
            else:
                mism.append(rec["id"])
        pref[src] = {"ok": ok_ct, "n": tot_ct, "mismatch": mism}
    summ["prefix"] = pref

    # ---------------- write jsonl per arm ---------------------------
    for arm in ARMS:
        fp = os.path.join(HERE, "h0_%s.jsonl" % arm)
        with open(fp, "w", encoding="utf8") as fh:
            for (pid, gi), ok in sorted(hits[arm].items()):
                fh.write(json.dumps({
                    "panel": pid, "gi": gi,
                    "fam": gold_fam_of[(pid, gi)],
                    "hit": bool(ok),
                    "c3_hit": bool(c3_hits.get((pid, gi), False))})
                    + "\n")
    with open(os.path.join(HERE, "h0_summary.json"), "w",
              encoding="utf8") as fh:
        json.dump(summ, fh, indent=1)

    # ---------------- print -----------------------------------------
    print("events=%d pkl_miss=%d" % (n_ev, n_miss))
    print("C-3 parent: %s  clutter %.2f"
          % ({f: "%d/%d" % (c3h[f], tot[f]) for f in tot},
             summ["c3"]["clutter"]))
    for arm in ARMS:
        a = summ["arms"][arm]
        print("H0-%s: %s  clutter %.2f"
              % (arm, {f: "%d/%d" % (a["hits"].get(f, 0), a["gold"][f])
                       for f in a["gold"]}, a["clutter"]))
    for src in EMITS:
        p = pref[src]
        print("prefix %-9s %d/%d ok %s"
              % (src, p["ok"], p["n"], p["mismatch"] or ""))


if __name__ == "__main__":
    main()
