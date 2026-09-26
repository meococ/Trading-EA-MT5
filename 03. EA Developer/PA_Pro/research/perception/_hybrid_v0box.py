"""R60 s.60.3 hybrid count: 'v1 with v0's box family'.

Pre-stated (logged before run): v0's box objects are taken UNCHANGED.
Combined set per panel = v1 objects minus v1 box-family + v0 box objects.
Clutter = (combined non-LABEL_TF + v1 LABEL_TF) / len(g2).
Metrics: box@1, level@1, line@2, bracket@1, clutter med, margin
(panels <= 5.0), paired day-bootstrap CIs vs v0.

Sources: v1 = current tree @<hash> variant a4b_off (== C-2 defaults,
flags OFF, verified 198/198 vs 4c2df34d); v0 = engine_v0 variant m1_v0.
Read-only on caches.  No engine edits.
"""
import sys, collections
sys.path.insert(0, "evalcheck"); sys.path.insert(0, ".")
import numpy as np
import common as C, cache as CA
import eval as EV, eval_v2 as V2, recall_at_k as RK
import engine as ENG1
import engine_v0 as ENG0
import funnel as F
from snapshot import tau_of, live_records
from salience import FAMILY

SEED = 20261202
BOOT = 2000
M1 = (("box", 1), ("level", 1), ("line", 2))

H1 = F.code_hash(F.V1_FILES)
H0 = F.code_hash(F.V0_FILES)


def eng(src):
    return (H1, ENG1.PerceptionEngine, "a4b_off") if src == "v1" \
        else (H0, ENG0.PerceptionEngine, "m1_v0")


def resolve_scores(live, e, smap):
    osc = {o.id: getattr(o, "score", None) for o in e.objects}
    for r in live:
        s = osc.get(r["id"])
        if s is None:
            s = smap.get((r["type"], r.get("t_birth")))
        r["score"] = s
    return live


def panel_rows(recs, box_src="v0", other_src="v1"):
    rows = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        hh, cls, var = eng(other_src)
        e1 = CA.run(hh, cls, rec, variant=var)
        h0, cls0, var0 = eng(box_src)
        e0 = CA.run(h0, cls0, rec, variant=var0)
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        gmarks = [gm for gm in EV.gold_marks(rec)
                  if V2.scorable_mark(gm, w0, w1)]
        eo1 = V2.eng_objects(e1, m, w0, w1)
        eo0 = V2.eng_objects(e0, m, w0, w1)
        comb = [r for r in eo1
                if r["type"] != "LABEL_TF"
                and FAMILY.get(r["type"]) != "box"]
        comb += [r for r in eo0
                 if r["type"] != "LABEL_TF"
                 and FAMILY.get(r["type"]) == "box"]
        emarks = [r for r in eo1 if r["type"] == "LABEL_TF"]
        pairs, mpairs = C.match_panel(g2, comb, gmarks, emarks, m,
                                    V2.match, V2.match_mark, V2.score)
        hg = {gi for gi, _ in pairs}
        he = {ei for _, ei in pairs}
        diag = {"g": collections.Counter(), "ghit": collections.Counter(),
                "e": collections.Counter(), "ehit": collections.Counter(),
                "tf_den": 0, "tf_hit": 0,
                "ratio": (len(comb) + len(emarks)) / len(g2)
                         if g2 else np.nan}
        for gi, g in enumerate(g2):
            diag["g"][g["spec_type"]] += 1
            diag["ghit"][g["spec_type"]] += gi in hg
        for ei, er in enumerate(comb):
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
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is not None and tau >= w0:
                by_tau[min(tau, w1)].append(g)
        for tau, gs in sorted(by_tau.items()):
            rec_t = dict(rec)
            rec_t["window"] = dict(rec["window"], x1=tau)
            e1t = CA.run(hh, cls, rec_t, variant=var)
            e0t = CA.run(h0, cls0, rec_t, variant=var0)
            live1, _x = live_records(e1t, m, w0, tau)
            live0, _y = live_records(e0t, m, w0, tau)
            live = [r for r in live1 if FAMILY.get(r["type"]) != "box"]
            live = resolve_scores(live, e1t, RK.score_map(e1t))
            live0 = [r for r in live0 if FAMILY.get(r["type"]) == "box"]
            live0 = resolve_scores(live0, e0t, RK.score_map(e0t))
            ranked = RK.rank_live(live + live0, {})
            fam_ranked = collections.defaultdict(list)
            for r in ranked:
                f = EV.FAMILY.get(r["type"])
                if f:
                    fam_ranked[f].append(r)
            row = {"panel": rec["id"], "date": rec["date"], "tau": tau,
                   "diag": diag, "fg": collections.Counter(),
                   "fhit": collections.defaultdict(
                       lambda: collections.Counter())}
            for g in gs:
                fg = EV.FAMILY.get(g["spec_type"])
                if not fg:
                    continue
                row["fg"][fg] += 1
                top_f = fam_ranked.get(fg, [])
                for k in (1, 2, 5):
                    if any(V2.match(g, er, m) for er in top_f[:k]):
                        row["fhit"][fg][k] += 1
            rows.append(row)
    return rows


def fam_recall(rows, fam, k):
    g = sum(r["fg"][fam] for r in rows)
    h = sum(r["fhit"][fam][k] for r in rows)
    return h, g


def day_diff_ci(rows_a, rows_b, fam, k, rng):
    da = collections.defaultdict(lambda: [0, 0])
    db = collections.defaultdict(lambda: [0, 0])
    for r in rows_a:
        da[r["date"]][0] += r["fhit"][fam][k]
        da[r["date"]][1] += r["fg"][fam]
    for r in rows_b:
        db[r["date"]][0] += r["fhit"][fam][k]
        db[r["date"]][1] += r["fg"][fam]
    days = sorted(d for d in da if da[d][1] and db.get(d, [0, 0])[1])
    diffs = [da[d][0] / da[d][1] - db[d][0] / db[d][1] for d in days]
    if not diffs:
        return None
    diffs = np.array(diffs)
    bs = [np.mean([diffs[rng.randrange(len(diffs))]
                   for _ in range(len(diffs))]) for _ in range(BOOT)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return float(diffs.mean()), float(lo), float(hi), len(diffs)


def report(tag, rows, v0rows=None):
    print("\n=== %s ===" % tag)
    rng = __import__("random").Random(SEED)
    for fam, k in M1 + (("bracket", 1),):
        h, g = fam_recall(rows, fam, k)
        s = "%s@%d %.3f (%d/%d)" % (fam, k, h / g if g else 0, h, g)
        if v0rows is not None:
            d = day_diff_ci(rows, v0rows, fam, k, rng)
            if d:
                s += "  vs v0 %+.3f [%.3f..%s%.3f]" % (
                    d[0], d[1], "+" if d[2] >= 0 else "", d[2])
        print("  " + s)
    dg = collections.Counter(); gh = collections.Counter()
    en = collections.Counter(); eh = collections.Counter()
    tfd = tfh = 0; ratios = []; seen = set()
    for r in rows:
        if r["panel"] in seen:
            continue
        seen.add(r["panel"])
        d = r["diag"]
        dg.update(d["g"]); gh.update(d["ghit"])
        en.update(d["e"]); eh.update(d["ehit"])
        tfd += d["tf_den"]; tfh += d["tf_hit"]
        if not np.isnan(d["ratio"]):
            ratios.append(d["ratio"])
    margin = sum(x <= 5.0 for x in ratios)
    print("  diag: BOX rec %.3f prec %.3f | PL %.3f | LC %.3f | "
          "LTF-agree %d/%d | clutter ratio med %.2f | margin<=5.0 %d/%d"
          % (gh["BOX"] / dg["BOX"] if dg["BOX"] else 0,
             eh["BOX"] / en["BOX"] if en["BOX"] else 0,
             gh["PATTERN_LINE"] / dg["PATTERN_LINE"] if dg["PATTERN_LINE"] else 0,
             gh["LEVEL_CARRIED"] / dg["LEVEL_CARRIED"] if dg["LEVEL_CARRIED"] else 0,
             tfh, tfd, np.median(ratios) if ratios else 0,
             margin, len(ratios)))


if __name__ == "__main__":
    recs = C.load_tune()
    print("v0 hash %s | v1 hash %s" % (H0[:8], H1[:8]))
    hyb = panel_rows(recs, "v0", "v1")
    v0r = panel_rows(recs, "v0", "v0")
    report("v0 (same machinery)", v0r)
    report("v1+v0box HYBRID", hyb, v0r)
    import pickle, os
    out = "_scratch/hybrid_rows.pkl"
    pickle.dump({"hybrid": hyb, "v0": v0r}, open(out, "wb"))
    print("rows ->", out)
