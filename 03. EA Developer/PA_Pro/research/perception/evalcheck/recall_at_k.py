"""recall_at_k.py — R17 §17.3: recall@k author-budget measurement.

At every golden decision time tau, keep only the top-k live objects and
re-score recall.  Ranking key: the object's own salience score when it
can be linked to its `born` cand_log record (kind + cet_min == t_birth),
falling back to birth recency for unlinked objects — both are reported.

k = 1, 2, 3, 5.  Outputs per-family recall, snapshot recall, and
panel-cluster bootstrap CIs (seed 20260921, 1000 resamples).

Usage: python evalcheck/recall_at_k.py [--engines v0 v1 linelab]
"""
import collections
import datetime
import glob
import json
import os
import random
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "linelab"))

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import funnel as F                              # noqa: E402
import pa_slots                                 # noqa: E402
from snapshot import tau_of, live_records, file_hash  # noqa: E402

SEED = 20260921
BOOT = 1000
KS = (1, 2, 3, 5)
FKS = (1, 2, 5)          # per-family k grid (R28 §28.2)
# author's per-family budget = birth-rate params (golden count p90):
# box 1, line 2, level 1, bracket 1 (params_v1_1 rate_*/fam_rate_*)
FAM_BUDGET = {"box": 1, "line": 2, "level": 1, "bracket": 1}
OUT = os.path.join(HERE, "RECALL_AT_K.md")
BAD_PKL = []
RANK_NOTE = ("ranking provenance: object-carried salience score when "
             "present, else born `cand_log` score linked on "
             "(kind + birth minute), else recency by `t_birth` "
             "(R20 §20.4.2)")


def score_map(e):
    """obj identity -> born-candidate salience score.  Link on
    (kind == type, cet_min == t_birth); ambiguous links take the max
    score (conservative for top-k ranking)."""
    m = {}
    for cd in e.cand_log or []:
        if cd.get("outcome") != "born" or cd.get("kind") == "LABEL_TF":
            continue
        key = (cd["kind"], cd.get("cet_min"))
        m[key] = max(m.get(key, 0.0), cd.get("score") or 0.0)
    return m


def rank_live(live, smap):
    """Sort live records: (1) object-carried salience score when the
    engine exposes it (R20 §20.4.2); (2) born-cand_log linked score;
    (3) recency (t_birth desc).  All desc."""
    def key(r):
        s = r.get("score")
        if s is None:
            s = smap.get((r["type"], r.get("t_birth")))
        if s is not None:
            return (0, -s, -(r.get("t_birth") or 0))
        return (1, -(r.get("t_birth") or 0), 0)
    return sorted(live, key=key)


def per_panel(eng_hash, cls, rec, store):
    """One row per (panel, tau): per-family golden count + hits@k."""
    w0 = rec["window"]["x0"]
    w1 = rec["window"]["x1"] or 1439
    t, m, o, h, l, c = CA.bars(rec["date"])
    e = CA.run(eng_hash, cls, rec, store=store)
    gobjs, _u, _to = EV.gold_objects(rec)
    g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
    by_tau = collections.defaultdict(list)
    for g in g2:
        tau = tau_of(g)
        if tau is not None and tau >= w0:
            by_tau[min(tau, w1)].append(g)
    out = []
    for tau, gs in sorted(by_tau.items()):
        rec_t = dict(rec)
        rec_t["window"] = dict(rec["window"], x1=tau)
        e_t = CA.run(eng_hash, cls, rec_t, store=store)
        live, _em = live_records(e_t, m, w0, tau)
        # attach the object-carried salience score (R20 §20.4.2) —
        # eng_objects() does not copy it onto the record
        osc = {o.id: getattr(o, "score", None) for o in e_t.objects}
        for r in live:
            r["score"] = osc.get(r["id"])
        smap = score_map(e_t)
        ranked = rank_live(live, smap)
        row = {"panel": rec["id"], "tau": tau,
               "g": collections.Counter(g["spec_type"] for g in gs),
               "hit": {k: collections.Counter() for k in KS},
               "fg": collections.Counter(),
               "fhit": {f: {k: 0 for k in FKS}
                        for f in set(EV.FAMILY.values())},
               "n_live": len(live)}
        for k in KS:
            top = ranked[:k]
            for g in gs:
                if any(V2.match(g, er, m) for er in top):
                    row["hit"][k][g["spec_type"]] += 1
        fam_ranked = collections.defaultdict(list)
        for r in ranked:
            f = EV.FAMILY.get(r["type"])
            if f:
                fam_ranked[f].append(r)
        for g in gs:
            fg = EV.FAMILY.get(g["spec_type"])
            if not fg:
                continue
            row["fg"][fg] += 1
            top_f = fam_ranked.get(fg, [])
            for k in FKS:
                if any(V2.match(g, er, m) for er in top_f[:k]):
                    row["fhit"][fg][k] += 1
        out.append(row)
    return out


def agg_fam(rows):
    """{fam: {k: (hits, goldens)}} accumulated over rows."""
    g = collections.Counter()
    h = collections.defaultdict(lambda: collections.Counter())
    for r in rows:
        g.update(r["fg"])
        for f, kk in r["fhit"].items():
            for k, v in kk.items():
                h[f][k] += v
    return {f: {k: (h[f][k], g[f]) for k in FKS}
            for f in g}


def boot_fam(rows, fam, k, rng):
    n = len(rows)
    vals = []
    for _ in range(BOOT):
        samp = [rows[rng.randrange(n)] for _ in range(n)]
        a = agg_fam(samp)
        if fam in a and a[fam][k][1]:
            vals.append(a[fam][k][0] / a[fam][k][1])
    vals.sort()
    if not vals:
        return float("nan"), float("nan")
    return (vals[int(0.025 * (len(vals) - 1))],
            vals[int(0.975 * (len(vals) - 1))])


def fam_table(rows, rng):
    """Per-family recall@k table (R28 §28.2) + author budget line."""
    a = agg_fam(rows)
    lines = ["", "per-family recall@k (top-k within the golden's own "
             "family at its tau):", "",
             "| family | goldens | k=1 | k=2 | k=5 | author k |",
             "|---|---|---|---|---|---|"]
    for f in sorted(a):
        cells = []
        for k in FKS:
            h, g = a[f][k]
            if not g:
                cells.append("-")
                continue
            lo, hi = boot_fam(rows, f, k, rng)
            s = "%.3f [%.2f-%.2f]" % (h / g, lo, hi)
            cells.append("**%s**" % s if FAM_BUDGET.get(f) == k else s)
        bk = FAM_BUDGET.get(f)
        lines.append("| %s%s | %d | %s | %s |" % (
            f, " †" if f == "bracket" else "",
            max(a[f][k][1] for k in FKS), " | ".join(cells),
            "k=%d" % bk if bk else "-"))
    lines.append("author per-family budget (birth-rate params, golden "
                 "p90): box k=1, line k=2, level k=1, bracket k=1 — "
                 "budget-k cells in bold")
    lines.append("† ruler: BRACKET rule has no price check — every "
                 "bracket figure is an upper bound (R30 §30.3)")
    return lines


def agg(rows, k):
    g = collections.Counter()
    h = collections.Counter()
    for r in rows:
        g.update(r["g"])
        h.update(r["hit"][k])
    snap_g = sum(g.values())
    snap_h = sum(h.values())
    return g, h, snap_h, snap_g


def boot(rows, k, rng, fam=None):
    n = len(rows)
    vals = []
    for _ in range(BOOT):
        samp = [rows[rng.randrange(n)] for _ in range(n)]
        g, h, sh, sg = agg(samp, k)
        if fam is None:
            if sg:
                vals.append(sh / sg)
        elif g[fam]:
            vals.append(h[fam] / g[fam])
    vals.sort()
    if not vals:
        return float("nan"), float("nan")
    return (vals[int(0.025 * (len(vals) - 1))],
            vals[int(0.975 * (len(vals) - 1))])


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--engines", nargs="+",
                    default=["v0", "v1", "linelab"])
    ap.add_argument("--arms", nargs="*", default=[],
                    help="hash8=label cache-only arms (levers, "
                         "frozen states); e.g. 03dbe495=revive_ON")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    rng = random.Random(SEED)
    recs = C.load_tune()
    if args.limit:
        recs = recs[:args.limit]
    engines = {}
    if "v0" in args.engines:
        import engine_v0 as ENG_V0
        engines["v0"] = (ENG_V0.PerceptionEngine,
                         F.code_hash(F.V0_FILES), True)
    if "v1" in args.engines:
        import engine as ENG_V1
        engines["v1"] = (ENG_V1.PerceptionEngine,
                         F.code_hash(F.V1_FILES), True)
    if "linelab" in args.engines:
        import lines_lab
        engines["linelab"] = (lines_lab.LineLabEngine,
                              file_hash(os.path.join(
                                  PERC, "linelab", "lines_lab.py")),
                              False)
    out = ["# RECALL@K — R17 §17.3 author-budget measurement", "",
           "Generated: %s UTC.  At each golden decision time tau only "
           "the top-k live objects are scored.  Ranking: object -> born "
           "cand_log score when linkable (kind + birth minute; ~97%% of "
           "objects link), else recency.  k in %s."
           % (datetime.datetime.now(datetime.timezone.utc)
              .strftime("%Y-%m-%d %H:%MZ"), KS), ""]
    with pa_slots.slot("evalcheck-recallk", timeout=1800):
        for tag, (cls, h, store) in engines.items():
            mid_edit = None
            try:
                cls()
            except Exception as ex:
                mid_edit = str(ex)
                cls = None
            rows = []
            for rec in recs:
                if cls is not None:
                    rows += per_panel(h, cls, rec, store)
                else:
                    import pickle
                    w1 = rec["window"]["x1"] or 1439
                    f = os.path.join(
                        CA.CACHE, "run_%s_%s_%s.pkl"
                        % (h, rec["date"], w1))
                    if os.path.exists(f):
                        # reuse scoreboard-style per_panel on pickles
                        rows += per_panel_pkl(h, rec)
            out.append("## %s (`%s`)" % (tag, h[:16]))
            if mid_edit:
                out.append("engine not instantiable (`%s`); "
                           "%d tau-rows from cache" % (mid_edit,
                                                      len(rows)))
            out.append("")
            fams = sorted({f for r in rows for f in r["g"]})
            hdr = "| k | snapshot recall | CI95 |" + "".join(
                " %s |" % f for f in fams)
            out.append(hdr)
            out.append("|---|---|---|" + "---|" * len(fams))
            for k in KS:
                g, hh, sh, sg = agg(rows, k)
                ci = boot(rows, k, rng)
                cells = []
                for f in fams:
                    v = hh[f] / g[f] if g[f] else float("nan")
                    cells.append("%.2f (%d/%d)" % (v, hh[f], g[f]))
                out.append("| %d | %.2f (%d/%d) | %.2f..%.2f | %s |"
                           % (k, sh / sg if sg else 0, sh, sg,
                              ci[0], ci[1], " | ".join(cells)))
            out.append("BRACKET column is an upper bound: the "
                       "ruler's BRACKET rule has no price check "
                       "(R30 §30.3)")
            out.append("")
            med = np.median([r["n_live"] for r in rows]) \
                if rows else 0
            out.append("median live objects at tau: %s; tau-rows: %d"
                       % (med, len(rows)))
            out += fam_table(rows, rng)
            out.append("")
            out.append(RANK_NOTE)
            out.append("")
        # cache-only arms (levers / frozen states), R20 §20.5
        import glob
        for spec in args.arms:
            lhs, label = spec.split("=", 1)
            if ":" in lhs:
                var, h8 = lhs.split(":", 1)
                pat = "run_%s_%s*_2012-*_*.pkl" % (var, h8)
            else:
                var, h8 = "", lhs
                pat = "run_%s*_2012-*_*.pkl" % h8
            g = sorted(glob.glob(os.path.join(CA.CACHE, pat)))
            if not g:
                out.append("## %s (`%s`) — NO CACHE" % (label, h8))
                out.append("")
                continue
            hh = re.search(r"_([0-9a-f]{16})_",
                           os.path.basename(g[0])).group(1)
            vm = re.match(r"run_(.+)_%s_" % hh, os.path.basename(g[0]))
            var_tag = var if var else (vm.group(1) if vm else "")
            rows = []
            for rec in recs:
                rows += per_panel_pkl(hh, rec, variant=var)
            kind = ("frozen STABLE, cache-only"
                    if "STABLE" in label.upper()
                    else "lab ranker, not engine, cache-only"
                    if label.upper().startswith("LAB")
                    else "lever, cache-only")
            out.append("## %s (`%s`%s) — %s"
                       % (label, hh,
                          ", variant=%s" % var if var else "", kind))
            out.append("")
            fams = sorted({f for r in rows for f in r["g"]})
            out.append("| k | snapshot recall | CI95 |" + "".join(
                " %s |" % f for f in fams))
            out.append("|---|---|---|" + "---|" * len(fams))
            for k in KS:
                g2, hh2, sh, sg = agg(rows, k)
                ci = boot(rows, k, rng)
                cells = []
                for f in fams:
                    v = hh2[f] / g2[f] if g2[f] else float("nan")
                    cells.append("%.2f (%d/%d)" % (v, hh2[f], g2[f]))
                out.append("| %d | %.2f (%d/%d) | %.2f..%.2f | %s |"
                           % (k, sh / sg if sg else 0, sh, sg,
                              ci[0], ci[1], " | ".join(cells)))
            out.append("BRACKET column is an upper bound: the "
                       "ruler's BRACKET rule has no price check "
                       "(R30 §30.3)")
            out.append("")
            med = np.median([r["n_live"] for r in rows]) \
                if rows else 0
            out.append("median live objects at tau: %s; tau-rows: %d"
                       % (med, len(rows)))
            out += fam_table(rows, rng)
            out.append("")
            out.append(RANK_NOTE)
            out.append("")
    open(OUT, "w", encoding="utf8").write("\n".join(out) + "\n")
    print("wrote %s (bad pickles refused: %d)" % (OUT, len(BAD_PKL)))


def per_panel_pkl(eng_hash, rec, variant=""):
    """Cache-only path: engine pickles at tau windows."""
    import pickle
    w0 = rec["window"]["x0"]
    w1 = rec["window"]["x1"] or 1439
    t, m, o, h, l, c = CA.bars(rec["date"])
    gobjs, _u, _to = EV.gold_objects(rec)
    g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
    by_tau = collections.defaultdict(list)
    for g in g2:
        tau = tau_of(g)
        if tau is not None and tau >= w0:
            by_tau[min(tau, w1)].append(g)
    out = []
    for tau, gs in sorted(by_tau.items()):
        pat = ("run_%s%s_%s_%s.pkl"
               % (variant + "_" if variant else "",
                  eng_hash, rec["date"], tau))
        f = os.path.join(CA.CACHE, pat)
        if not os.path.exists(f):
            continue
        try:
            e_t = pickle.load(open(f, "rb"))
        except Exception:
            BAD_PKL.append(f)   # R26 §26.4: refuse, never serve
            continue
        live, _em = live_records(e_t, m, w0, tau)
        osc = {o.id: getattr(o, "score", None) for o in e_t.objects}
        for r in live:
            r["score"] = osc.get(r["id"])
        smap = score_map(e_t)
        ranked = rank_live(live, smap)
        row = {"panel": rec["id"], "tau": tau,
               "g": collections.Counter(g["spec_type"] for g in gs),
               "hit": {k: collections.Counter() for k in KS},
               "fg": collections.Counter(),
               "fhit": {f: {k: 0 for k in FKS}
                        for f in set(EV.FAMILY.values())},
               "n_live": len(live)}
        for k in KS:
            top = ranked[:k]
            for g in gs:
                if any(V2.match(g, er, m) for er in top):
                    row["hit"][k][g["spec_type"]] += 1
        fam_ranked = collections.defaultdict(list)
        for r in ranked:
            f = EV.FAMILY.get(r["type"])
            if f:
                fam_ranked[f].append(r)
        for g in gs:
            fg = EV.FAMILY.get(g["spec_type"])
            if not fg:
                continue
            row["fg"][fg] += 1
            top_f = fam_ranked.get(fg, [])
            for k in FKS:
                if any(V2.match(g, er, m) for er in top_f[:k]):
                    row["fhit"][fg][k] += 1
        out.append(row)
    return out


if __name__ == "__main__":
    main()
