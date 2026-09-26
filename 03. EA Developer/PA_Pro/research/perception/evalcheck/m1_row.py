"""m1_row.py — the standard M1 command (C-round 1, R34 §34.8 item 3.1).

Prints one M1 row for any engine hash + cache variant (or live params),
with v0 in the same run:

  * M1 = per-family recall@k at the family's tau under the author's
    budget: box@1, level@1, line@2 (bracket@1 reported, diagnostic
    only — no price check, R30 §30.3).  Ranking: object-carried score,
    else born cand_log score, else recency (R20 §20.4.2), identical for
    every arm.
  * paired day-bootstrap CI of (arm - v0) per family, seed 20260921,
    1000 resamples;
  * clutter ratio median (gate_pack definition: median per panel of
    (engine objects incl. LABEL_TF) / scorable goldens);
  * the six diagnostic rows: BOX recall, BOX precision, PATTERN_LINE
    recall, LEVEL_CARRIED recall, LABEL_TF agreement n/N on matched
    boxes, clutter ratio median.

Everything is computed by evalcheck code (recall_at_k / snapshot /
eval_v2 / common / cache) — independent of the build lane's _m1.py.

Usage:
  python evalcheck/m1_row.py --hash 9283b3892c7fe8fc --variant ab_base
  python evalcheck/m1_row.py --hash afba83c5f74d96c4 --variant labscore_on
  python evalcheck/m1_row.py --live                 # current disk state
  python evalcheck/m1_row.py --hash H --variant V --json out.json
"""
import argparse
import collections
import json
import os
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
import funnel as F                              # noqa: E402
import recall_at_k as RK                        # noqa: E402
from snapshot import tau_of, live_records       # noqa: E402

SEED = 20260921
BOOT = 1000
M1 = (("box", 1), ("level", 1), ("line", 2))     # author's budget
EXTRA = (("bracket", 1),)
FKS = (1, 2, 5)


def _pickled(eng_hash, rec, variant, w1):
    import pickle
    f = os.path.join(CA.CACHE, "run_%s%s_%s_%s.pkl"
                     % (variant + "_" if variant else "",
                        eng_hash, rec["date"], w1))
    if not os.path.exists(f):
        return None
    try:
        with open(f, "rb") as fh:
            return pickle.load(fh)
    except Exception:
        return None


def measure(eng_hash, variant, recs, cls=None):
    """One pass over TUNE: per-(panel,tau) top-k rows + per-panel
    diagnostics.  cls=None => cache-only (read-only)."""
    tau_rows = []
    diag_rows = []
    n_cache_miss = 0
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        e = (CA.run(eng_hash, cls, rec, variant=variant)
             if cls is not None else
             _pickled(eng_hash, rec, variant, w1))
        if e is None:
            n_cache_miss += 1
            continue
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        gmarks = [gm for gm in EV.gold_marks(rec)
                  if V2.scorable_mark(gm, w0, w1)]
        eobjs = V2.eng_objects(e, m, w0, w1)
        eboxes = [r for r in eobjs if r["type"] != "LABEL_TF"]
        emarks = [r for r in eobjs if r["type"] == "LABEL_TF"]
        pairs, mpairs = C.match_panel(g2, eboxes, gmarks, emarks, m,
                                      V2.match, V2.match_mark, V2.score)
        hg = {gi for gi, _ in pairs}
        he = {ei for _, ei in pairs}
        diag = {"panel": rec["id"], "date": rec["date"],
                "g": collections.Counter(), "ghit": collections.Counter(),
                "e": collections.Counter(), "ehit": collections.Counter(),
                "tf_den": 0, "tf_hit": 0,
                "n_eng": len(eboxes) + len(emarks), "n_gold": len(g2),
                "ratio": (len(eboxes) + len(emarks)) / len(g2)
                         if g2 else np.nan}
        for gi, g in enumerate(g2):
            diag["g"][g["spec_type"]] += 1
            diag["ghit"][g["spec_type"]] += gi in hg
        for ei, er in enumerate(eboxes):
            diag["e"][er["type"]] += 1
            diag["ehit"][er["type"]] += ei in he
        mbox = [g2[gi] for gi in hg if g2[gi]["spec_type"] == "BOX"]
        hit_marks = {id(gm) for gm, _ in mpairs}
        for gm in gmarks:
            if gm.get("t") is None:
                continue
            if any((g.get("t0") or w0) <= gm["t"] <= (g.get("t1") or w1)
                   for g in mbox):
                diag["tf_den"] += 1
                diag["tf_hit"] += id(gm) in hit_marks
        diag_rows.append(diag)
        # tau rows (recall_at_k semantics, identical ranking rule)
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is not None and tau >= w0:
                by_tau[min(tau, w1)].append(g)
        for tau, gs in sorted(by_tau.items()):
            e_t = (CA.run(eng_hash, cls,
                          dict(rec, window=dict(rec["window"], x1=tau)),
                          variant=variant)
                   if cls is not None else
                   _pickled(eng_hash, rec, variant, tau))
            if e_t is None:
                continue
            live, _em = live_records(e_t, m, w0, tau)
            osc = {ob.id: getattr(ob, "score", None)
                   for ob in e_t.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            ranked = RK.rank_live(live, RK.score_map(e_t))
            fam_ranked = collections.defaultdict(list)
            for r in ranked:
                f = EV.FAMILY.get(r["type"])
                if f:
                    fam_ranked[f].append(r)
            row = {"panel": rec["id"], "date": rec["date"], "tau": tau,
                   "fg": collections.Counter(),
                   "fhit": collections.defaultdict(
                       lambda: collections.Counter()),
                   "n_live": len(live)}
            for g in gs:
                fg = EV.FAMILY.get(g["spec_type"])
                if not fg:
                    continue
                row["fg"][fg] += 1
                top_f = fam_ranked.get(fg, [])
                for k in FKS:
                    if any(V2.match(g, er, m) for er in top_f[:k]):
                        row["fhit"][fg][k] += 1
            tau_rows.append(row)
    return {"tau": tau_rows, "diag": diag_rows, "miss": n_cache_miss}


def fam_recall(rows, fam, k):
    g = sum(r["fg"][fam] for r in rows)
    h = sum(r["fhit"][fam][k] for r in rows)
    return h, g


def day_diff_ci(rows_a, rows_b, fam, k, rng):
    """Paired day bootstrap of (a - b) recall at (fam, k)."""
    da = collections.defaultdict(lambda: [0, 0])
    db = collections.defaultdict(lambda: [0, 0])
    for r in rows_a:
        da[r["date"]][0] += r["fhit"][fam][k]
        da[r["date"]][1] += r["fg"][fam]
    for r in rows_b:
        db[r["date"]][0] += r["fhit"][fam][k]
        db[r["date"]][1] += r["fg"][fam]
    days = sorted(d for d in da if da[d][1] and db.get(d, [0, 0])[1])
    diffs = np.array([da[d][0] / da[d][1] - db[d][0] / db[d][1]
                      for d in days])
    if not len(diffs):
        return None
    bs = sorted(np.mean([diffs[rng.randrange(len(diffs))]
                         for _ in range(len(diffs))])
                for _ in range(BOOT))
    return (float(diffs.mean()), bs[int(0.025 * (BOOT - 1))],
            bs[int(0.975 * (BOOT - 1))], len(diffs))


def diag_line(diag_rows):
    dg = collections.Counter()
    gh = collections.Counter()
    en = collections.Counter()
    eh = collections.Counter()
    tfd = tfh = 0
    ratios = []
    for d in diag_rows:
        dg.update(d["g"]); gh.update(d["ghit"])
        en.update(d["e"]); eh.update(d["ehit"])
        tfd += d["tf_den"]; tfh += d["tf_hit"]
        if not np.isnan(d["ratio"]):
            ratios.append(d["ratio"])
    return {"BOX_rec": gh["BOX"] / dg["BOX"] if dg["BOX"] else 0,
            "BOX_prec": eh["BOX"] / en["BOX"] if en["BOX"] else 0,
            "PL_rec": gh["PATTERN_LINE"] / dg["PATTERN_LINE"]
                      if dg["PATTERN_LINE"] else 0,
            "LC_rec": gh["LEVEL_CARRIED"] / dg["LEVEL_CARRIED"]
                      if dg["LEVEL_CARRIED"] else 0,
            "tf": (tfh, tfd),
            "clutter_med": float(np.median(ratios)) if ratios else 0,
            "ratios": ratios}


def report(tag, res, v0=None, rng=None):
    rows = res["tau"]
    d = res["diag"]
    out = {"tag": tag, "miss": res["miss"], "tau_rows": len(rows)}
    print("%s  (tau-rows %d, full-window misses %d)" % (tag, len(rows),
                                                      res["miss"]))
    for fam, k in M1 + EXTRA:
        h, g = fam_recall(rows, fam, k)
        s = "  %s@%d %.3f (%d/%d)" % (fam, k, h / g if g else 0, h, g)
        out["%s@%d" % (fam, k)] = {"h": h, "g": g,
                                   "v": h / g if g else 0}
        if v0 is not None and rng is not None:
            dd = day_diff_ci(rows, v0["tau"], fam, k, rng)
            if dd:
                s += "  vs v0 %+.3f [%+.3f..%+.3f]" % (dd[0], dd[1],
                                                       dd[2])
                out["%s@%d" % (fam, k)]["vs_v0"] = dd[:3]
        print(s)
    dd_ = diag_line(d)
    out["diag"] = {k: v for k, v in dd_.items() if k != "ratios"}
    print("  diag: BOX rec %.3f prec %.3f | PL %.3f | LC %.3f | "
          "LTF-agree %d/%d | clutter ratio med %.2f"
          % (dd_["BOX_rec"], dd_["BOX_prec"], dd_["PL_rec"],
             dd_["LC_rec"], dd_["tf"][0], dd_["tf"][1],
             dd_["clutter_med"]))
    out["ratios"] = dd_["ratios"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hash", default="")
    ap.add_argument("--variant", default="")
    ap.add_argument("--label", default="")
    ap.add_argument("--live", action="store_true",
                    help="run the on-disk engine fresh (hash must match "
                         "the on-disk code)")
    ap.add_argument("--params", default="",
                    help="JSON dict of dotted param overrides for "
                         "--live (baked into variant '_live')")
    ap.add_argument("--v0-variant", default="m1_v0",
                    help="cache variant for the v0 reference")
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    recs = C.load_tune()
    rng = __import__("random").Random(SEED)

    # v0 reference — cache-first, live fallback identical engine
    h0 = F.code_hash(F.V0_FILES)
    v0 = measure(h0, args.v0_variant, recs)
    if v0["miss"] or len(v0["tau"]) < 400:
        v0b = measure(h0, "", recs)
        if len(v0b["tau"]) >= len(v0["tau"]):
            v0 = v0b

    cls = None
    h = args.hash
    variant = args.variant
    label = args.label or (variant or "live")
    if args.live:
        import engine as ENG
        import copy
        hp = F.code_hash(F.V1_FILES)
        if h and h != hp:
            print("ABORT: on-disk hash %s != requested %s" % (hp, h))
            return 2
        h = hp
        over = json.loads(args.params) if args.params else {}
        base = ENG.load_params()

        def cls():
            p = copy.deepcopy(base)
            for kk, vv in over.items():
                node = p
                ks = kk.split(".")
                for kk2 in ks[:-1]:
                    node = node[kk2]
                node[ks[-1]] = vv
            return ENG.PerceptionEngine(params=p)
        variant = variant or "_live"
        if args.params:
            label += " params=" + args.params

    res = measure(h, variant, recs, cls=cls)
    outs = {"hash": h, "variant": variant}
    outs["v0"] = report("v0 (`%s`)" % h0[:8], v0, rng=rng)
    outs["arm"] = report("%s (`%s`%s)" % (label, h[:8],
                                         " var=" + variant
                                         if variant else ""),
                         res, v0=v0, rng=rng)
    if args.json:
        outs["arm"].pop("ratios", None)
        outs["v0"].pop("ratios", None)
        json.dump(outs, open(args.json, "w"), indent=1, default=str)
        print("wrote %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
