"""_m1.py — C-round-1 M1 harness (R34 §34.4, keep-rule §34.5).

Uses evalcheck measurement code imported UNMODIFIED (evalcheck is
read-only for build): recall_at_k for tau/ranking, gate_pack for the
six diagnostic rows, eval_v2 for matching.  One CA.run pass per
(panel, tau) feeds both the M1 rows and the diagnostics.

Arms are runtime param-override factories in _ab_onehash.py —
one engine hash per pair (R24 §24.3), variant-keyed caches.

Usage:
  python _m1.py v0 v1                 # reproduce the baseline
  python _m1.py arm famledger_on      # arm vs v0 + parent (stable)
  python _m1.py arm famledger_on tail_off  # arm vs named parent arm
"""
import collections
import os
import sys

sys.path.insert(0, "evalcheck")
sys.path.insert(0, ".")
sys.path.insert(0, os.path.join("linelab"))

import numpy as np

import common as C
import eval as EV
import eval_v2 as V2
import cache as CA
import funnel as F
from snapshot import tau_of, live_records
import recall_at_k as RK
import engine as ENG
import engine_v0 as ENG_V0
import _ab_onehash as AB

SEED = 20260921
BOOT = 1000
# author's per-family budget (R34 §34.4 / R31 §31.3)
FAM_BUDGET = {"box": 1, "line": 2, "level": 1, "bracket": 1}
M1 = (("box", 1), ("level", 1), ("line", 2))


def panel_rows(eng_hash, cls, recs, variant=""):
    """One row per (panel, tau) + cumulative diagnostics — merges
    recall_at_k.per_panel and gate_pack.per_panel on one cache pass."""
    rows = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        e = CA.run(eng_hash, cls, rec, variant=variant)
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
        diag = {"g": collections.Counter(), "ghit": collections.Counter(),
                "e": collections.Counter(), "ehit": collections.Counter(),
                "tf_den": 0, "tf_hit": 0,
                "ratio": (len(eboxes) + len(emarks)) / len(g2)
                         if g2 else np.nan}
        for gi, g in enumerate(g2):
            diag["g"][g["spec_type"]] += 1
            diag["ghit"][g["spec_type"]] += gi in hg
        for ei, er in enumerate(eboxes):
            diag["e"][er["type"]] += 1
            diag["ehit"][er["type"]] += ei in he
        # LABEL_TF agreement on matched boxes (gate_pack.py:141-151)
        mbox = [g2[gi] for gi in hg if g2[gi]["spec_type"] == "BOX"]
        hit_marks = {id(gm) for gm, _ in mpairs}
        for gm in gmarks:
            if gm.get("t") is None:
                continue
            if any((g.get("t0") or w0) <= gm["t"] <= (g.get("t1") or w1)
                   for g in mbox):
                diag["tf_den"] += 1
                diag["tf_hit"] += id(gm) in hit_marks
        # tau rows (recall_at_k)
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is not None and tau >= w0:
                by_tau[min(tau, w1)].append(g)
        for tau, gs in sorted(by_tau.items()):
            rec_t = dict(rec)
            rec_t["window"] = dict(rec["window"], x1=tau)
            e_t = CA.run(eng_hash, cls, rec_t, variant=variant)
            live, _em = live_records(e_t, m, w0, tau)
            osc = {o.id: getattr(o, "score", None) for o in e_t.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            smap = RK.score_map(e_t)
            ranked = RK.rank_live(live, smap)
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
    # diagnostics from the first row's per-panel diag (same each row)
    dg = collections.Counter()
    gh = collections.Counter()
    en = collections.Counter()
    eh = collections.Counter()
    tfd = tfh = 0
    ratios = []
    seen = set()
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
    print("  diag: BOX rec %.3f prec %.3f | PL %.3f | LC %.3f | "
          "LTF-agree %d/%d | clutter ratio med %.2f"
          % (gh["BOX"] / dg["BOX"] if dg["BOX"] else 0,
             eh["BOX"] / en["BOX"] if en["BOX"] else 0,
             gh["PATTERN_LINE"] / dg["PATTERN_LINE"]
             if dg["PATTERN_LINE"] else 0,
             gh["LEVEL_CARRIED"] / dg["LEVEL_CARRIED"]
             if dg["LEVEL_CARRIED"] else 0,
             tfh, tfd, np.median(ratios) if ratios else 0))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "v0v1"
    recs = C.load_tune()
    if mode in ("v0v1", "v0", "v1"):
        h0 = F.code_hash(F.V0_FILES)
        h1 = F.code_hash(F.V1_FILES)
        print("v0 hash %s | v1 hash %s" % (h0[:8], h1[:8]))
        v0 = panel_rows(h0, ENG_V0.PerceptionEngine, recs, "m1_v0")
        report("v0", v0)
        v1 = panel_rows(h1, ENG.PerceptionEngine, recs, "m1_v1")
        report("v1 STABLE", v1, v0)
        return
    # arm mode: _m1.py arm <name> [parent_name]
    arm = sys.argv[2]
    parent = sys.argv[3] if len(sys.argv) > 3 else None
    h = F.code_hash(F.V1_FILES)
    print("hash %s | arm %s" % (h[:8], arm))
    v0 = panel_rows(F.code_hash(F.V0_FILES), ENG_V0.PerceptionEngine,
                    recs, "m1_v0")
    report("v0", v0)
    if parent:
        prow = panel_rows(h, AB.ARMS[parent], recs, parent)
        report("parent %s" % parent, prow, v0)
    arows = panel_rows(h, AB.ARMS[arm], recs, arm)
    report("arm %s" % arm, arows, v0)


if __name__ == "__main__":
    main()
