"""gate_pack.py — mandate 4, W2: gate-feasibility data pack.

For each gated type (BOX, PATTERN_LINE, LEVEL_CARRIED, LABEL_TF
agreement, clutter) and each engine (v0, current v1, lab prototypes):
  cumulative recall/precision, snapshot recall + live clutter,
  oracle ceiling, trusted-subset recall, plausibility-adjusted
  precision (W1, when _plaus_judge.jsonl exists), gap to the spec
  gate, per-panel distributions, bootstrap CIs (by panel, 1000
  resamples, seed 20260921), and a reproducibility block.

Tables only — the Lead writes the recommendation.

Usage: python evalcheck/gate_pack.py
"""
import collections
import datetime
import json
import os
import random
import re
import sys
import types

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
GATES = {"BOX": ("recall", 0.70),
         "BOX_prec": ("precision", 0.60),
         "PATTERN_LINE": ("recall", 0.50),
         "LEVEL_CARRIED": ("recall", 0.60),
         "LABEL_TF": ("agreement", 0.60),
         "clutter": ("median ratio", 1.5)}
TIER_A = os.path.join(HERE, "line_tierA.json")


def _rak_kcol(rak_txt, section_pat):
    """RECALL_AT_K.md -> {k: 'val [CI]'} for the ## section whose
    header contains section_pat.  Snapshot-recall + CI columns only."""
    sec = None
    out = {}
    for ln in rak_txt.splitlines():
        if ln.startswith("## "):
            sec = section_pat in ln
            continue
        if sec and ln.startswith("| "):
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if cells and cells[0].isdigit():
                rec_m = re.match(r"([\d.]+)", cells[1] or "")
                ci_m = re.match(r"([\d.]+)\.\.([\d.]+)",
                                cells[2] or "")
                if rec_m and ci_m:
                    out[int(cells[0])] = "%s [%s–%s]" % (
                        rec_m.group(1), ci_m.group(1), ci_m.group(2))
    return out


def _pickled(eng_hash, rec, variant=""):
    """Cached engine object without constructing the class — used when
    the engine is mid-edit (params fail provenance) but pickles exist."""
    import pickle
    w1 = rec["window"]["x1"] or 1439
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


def per_panel(cls, eng_hash, recs, store=True, tierA=None, variant=""):
    tierA = tierA or set()
    """Per-panel counts for one engine."""
    rows = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        if cls is not None:
            e = CA.run(eng_hash, cls, rec, store=store, variant=variant)
        else:
            e = _pickled(eng_hash, rec, variant=variant)
        if e is None:                    # engine mid-edit, no cache
            continue
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        gmarks = [gm for gm in EV.gold_marks(rec)
                  if V2.scorable_mark(gm, w0, w1)]
        eobjs = V2.eng_objects(e, m, w0, w1)
        eboxes = [r for r in eobjs if r["type"] != "LABEL_TF"]
        emarks = [r for r in eobjs if r["type"] == "LABEL_TF"]
        pairs, mpairs = C.match_panel(g2, eboxes, gmarks, emarks, m,
                                      V2.match, V2.match_mark,
                                      V2.score)
        hg = {gi for gi, _ in pairs}
        he = {ei for _, ei in pairs}
        row = {"panel": rec["id"], "g": collections.Counter(),
               "ghit": collections.Counter(), "e": collections.Counter(),
               "ehit": collections.Counter(), "n_gold": len(g2),
               "n_eng": len(eboxes) + len(emarks),
               "clutter_at_tau": [], "snap_g": 0, "snap_h": 0,
               "tf_den": 0, "tf_hit": 0,
               "orc": collections.Counter(), "orc_g": collections.Counter()}
        row["tr_g"] = collections.Counter()
        row["tr_m"] = collections.Counter()
        src_idx = [k for k, o in enumerate(rec["objects"])
                   if o.get("status") not in EV.EXCLUDED
                   and o.get("spec_type")]
        g2_orig = [i for i, g in enumerate(gobjs)
                   if V2.scorable(g, w0, w1)]
        for gi, g in enumerate(g2):
            st = g["spec_type"]
            row["g"][st] += 1
            row["ghit"][st] += gi in hg
            if st in V2.LINE_TYPES and tierA is not None and tierA:
                oi = src_idx[g2_orig[gi]]
                if "%s#%d" % (rec["id"], oi) not in tierA:
                    row["tr_g"][st] += 1
                    row["tr_m"][st] += gi in hg
        for ei, er in enumerate(eboxes):
            row["e"][er["type"]] += 1
            row["ehit"][er["type"]] += ei in he
        # LABEL_TF agreement on matched boxes: golden mark inside a
        # matched golden box's span must have its engine mark matched
        mbox = [g2[gi] for gi in hg if g2[gi]["spec_type"] == "BOX"]
        hit_marks = {id(gm) for gm, _ in mpairs}
        for gm in gmarks:
            if gm.get("t") is None:
                continue
            if any((g.get("t0") or w0) <= gm["t"] <= (g.get("t1") or w1)
                   for g in mbox):
                row["tf_den"] += 1
                row["tf_hit"] += id(gm) in hit_marks
        # oracle (cand_right or born)
        cands = []
        for cd in e.cand_log or []:
            if cd["kind"] == "LABEL_TF":
                continue
            r = F.cand_as_record(cd, m, w0, w1)
            if r is not None:
                cands.append(r)
        for gi, g in enumerate(g2):
            st = g["spec_type"]
            if st not in ("BOX", "PATTERN_LINE"):
                continue
            row["orc_g"][st] += 1
            same = [r for r in cands
                    if EV.FAMILY.get(r["type"]) == EV.FAMILY.get(st)]
            row["orc"][st] += (gi in hg) or any(
                F.cand_right(g, r, m) for r in same)
        # snapshot recall + live clutter at decision times
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is not None and tau >= w0:
                by_tau[min(tau, w1)].append(g)
        for tau, gs in by_tau.items():
            rec_t = dict(rec)
            rec_t["window"] = dict(rec["window"], x1=tau)
            e_t = (CA.run(eng_hash, cls, rec_t, store=store,
                          variant=variant)
                   if cls is not None else
                   _pickled(eng_hash, rec_t, variant=variant))
            if e_t is None:
                continue
            ebt, _emt = live_records(e_t, m, w0, tau)
            row["clutter_at_tau"].append(len(ebt))
            for g in gs:
                row["snap_g"] += 1
                row["snap_h"] += any(V2.match(g, er, m)
                                     for er in ebt)
        rows.append(row)
    return rows


def agg(rows):
    g = collections.Counter()
    gh = collections.Counter()
    e = collections.Counter()
    eh = collections.Counter()
    orc = collections.Counter()
    orcg = collections.Counter()
    tr_g = collections.Counter()
    tr_m = collections.Counter()
    tf_d = tf_h = snap_g = snap_h = 0
    clutter_ev = []
    ratios = []
    for r in rows:
        g.update(r["g"])
        gh.update(r["ghit"])
        e.update(r["e"])
        eh.update(r["ehit"])
        orc.update(r["orc"])
        orcg.update(r["orc_g"])
        tr_g.update(r["tr_g"])
        tr_m.update(r["tr_m"])
        tf_d += r["tf_den"]
        tf_h += r["tf_hit"]
        snap_g += r["snap_g"]
        snap_h += r["snap_h"]
        clutter_ev += r["clutter_at_tau"]
        if r["n_gold"]:
            ratios.append(r["n_eng"] / r["n_gold"])
    return {"g": g, "gh": gh, "e": e, "eh": eh, "orc": orc,
            "orcg": orcg, "tr_g": tr_g, "tr_m": tr_m,
            "tf": (tf_h, tf_d),
            "snap": (snap_h, snap_g), "clutter_ev": clutter_ev,
            "ratio_med": float(np.median(ratios)) if ratios else 0,
            "gold_per_panel": [r["n_gold"] for r in rows]}


def boot_ci(rows, what, rng):
    """Panel-cluster bootstrap CI for a metric."""
    vals = []
    n = len(rows)
    for _ in range(BOOT):
        samp = [rows[rng.randrange(n)] for _ in range(n)]
        a = agg(samp)
        if what == "BOX_rec":
            vals.append(a["gh"]["BOX"] / a["g"]["BOX"])
        elif what == "BOX_prec":
            vals.append(a["eh"]["BOX"] / max(a["e"]["BOX"], 1))
        elif what == "PL_rec":
            vals.append(a["gh"]["PATTERN_LINE"]
                        / a["g"]["PATTERN_LINE"])
        elif what == "LC_rec":
            vals.append(a["gh"]["LEVEL_CARRIED"]
                        / a["g"]["LEVEL_CARRIED"])
        elif what == "TF":
            h, d = a["tf"]
            if d:
                vals.append(h / d)
        elif what == "clutter":
            vals.append(a["ratio_med"])
    vals.sort()
    if not vals:
        return float("nan"), float("nan")
    lo = vals[int(0.025 * (len(vals) - 1))]
    hi = vals[int(0.975 * (len(vals) - 1))]
    return lo, hi


def pct(a, b):
    return "%.2f" % (a / b) if b else "—"


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--v1-hash", default="",
                    help="pin v1 to this hash, cache-only (frozen "
                         "STABLE / dress rehearsal)")
    ap.add_argument("--v1-variant", default="",
                    help="cache variant prefix for --v1-hash pickles")
    ap.add_argument("--out", default="GATE_PACK.md",
                    help="output filename under evalcheck/")
    args = ap.parse_args()
    rng = random.Random(SEED)
    import engine as ENG_V1
    import engine_v0 as ENG_V0
    import lines_lab
    recs = C.load_tune()
    lin_hash = file_hash(os.path.join(PERC, "linelab", "lines_lab.py"))
    v1h = args.v1_hash or F.code_hash(F.V1_FILES)
    engines = [("v0", ENG_V0.PerceptionEngine,
                F.code_hash(F.V0_FILES), True, ""),
               ("v1", (None if args.v1_hash
                      else ENG_V1.PerceptionEngine),
                v1h, not args.v1_hash, args.v1_variant),
               ("linelab", lines_lab.LineLabEngine, lin_hash, False,
                "")]
    tierA = set()
    if os.path.exists(TIER_A):
        tierA = set(json.load(open(TIER_A)))
    # W1/W1b plausibility: raw judge yes-rate, Rogan-Gladen corrected
    # once negative controls (_plaus_neg_judge.jsonl) give
    # sensitivity/specificity (R17 §17.4).
    plaus = {}
    plaus_note = ""
    pj = os.path.join(HERE, "_plaus_judge.jsonl")
    pm = os.path.join(HERE, "_plaus_items.jsonl")
    if os.path.exists(pj) and os.path.exists(pm):
        items = {json.loads(l)["item_id"]: json.loads(l)
                 for l in open(pm, encoding="utf8")}
        judge = {json.loads(l)["item_id"]: json.loads(l)
                 for l in open(pj, encoding="utf8")}
        h2tag = {F.code_hash(F.V0_FILES): "v0",
                 "linelab": "linelab"}
        for i in items.values():
            if i["src"] == "fp" and i["engine"] not in h2tag:
                h2tag[i["engine"]] = "v1"
        sens = spec = None
        nj = os.path.join(HERE, "_plaus_neg_judge.jsonl")
        nm = os.path.join(HERE, "_plaus_neg.jsonl")
        if os.path.exists(nj) and os.path.exists(nm):
            njud = {json.loads(l)["item_id"]: json.loads(l)
                    for l in open(nj, encoding="utf8")}
            nitems = [json.loads(l) for l in open(nm, encoding="utf8")]
            # R28 §28.3.2: restrict to ruler-valid negatives when the
            # audit file exists (invalid = would match a golden).
            na = os.path.join(HERE, "_neg_audit.json")
            valid_ids = None
            if os.path.exists(na):
                valid_ids = {r["item_id"] for r in
                             json.load(open(na, encoding="utf8"))
                             if r["valid"]}
            ny = [njud.get(i["item_id"], {}).get("plausible")
                  for i in nitems
                  if valid_ids is None or i["item_id"] in valid_ids]
            ny = [v for v in ny if v in ("yes", "no")]
            ctr = [i for i in items.values() if i["src"] == "control"]
            cj = [judge.get(i["item_id"], {}).get("plausible")
                  for i in ctr]
            cj = [v for v in cj if v in ("yes", "no")]
            if ny and cj:
                spec = 1 - sum(v == "yes" for v in ny) / len(ny)
                sens = sum(v == "yes" for v in cj) / len(cj)
        for eng in ("v0", "v1", "linelab"):
            sub = [i for i in items.values()
                   if i["src"] == "fp" and h2tag.get(i["engine"])
                   == eng]
            if sub:
                obs = sum(
                    judge.get(i["item_id"], {}).get("plausible")
                    == "yes" for i in sub) / len(sub)
                if sens is not None and spec is not None:
                    d = sens + spec - 1
                    corr = min(1.0, max(0.0, (obs + spec - 1) / d)) \
                        if d > 1e-9 else obs
                    plaus[eng] = corr
                else:
                    plaus[eng] = obs
        if sens is not None:
            v1src = sorted({h[:8] for h, tg in h2tag.items()
                            if tg == "v1"})
            plaus_note = (
                "W1b: judge sensitivity %.2f, specificity %.2f"
                " — %s; plausible-FP shares are Rogan-Gladen "
                "corrected (details: PLAUSIBILITY.md).  v1 FP sample "
                "was drawn at hash %s; applying it to a different v1 "
                "state is an approximation."
                % (sens, spec,
                   "SPEC < 0.70 -> plausibility-adjusted numbers "
                   "UNRELIABLE (wide CIs)"
                   if spec < 0.70 else "judge reliable",
                   "/".join(v1src) or "?"))

    out = ["# GATE_PACK — data for the 22/09 ~01:00Z gate decision",
           "",
           "Generated: %s.  Tables only; the Lead writes the "
           "recommendation."
           % datetime.datetime.now(datetime.timezone.utc).strftime(
               "%Y-%m-%d %H:%MZ"),
           "",
           "Gates (spec §6): BOX recall >= 0.70, BOX precision >= 0.60, "
           "PATTERN_LINE recall >= 0.50, LEVEL_CARRIED recall >= 0.60, "
           "T/F agreement on matched boxes >= 0.60, clutter ratio "
           "median <= 1.5.",
           ""]
    agg_by_tag = {}
    with pa_slots.slot("evalcheck-gatepack", timeout=1800):
        for tag, cls, h, store, variant in engines:
            mid_edit = None
            if cls is None:
                mid_edit = ("pinned hash, cache-only"
                            + (" variant=%s" % variant if variant
                               else ""))
            else:
                try:
                    cls()                    # mid-edit probe
                except Exception as ex:
                    mid_edit = str(ex)
                    cls = None
            rows = per_panel(cls, h, recs, store=store, tierA=tierA,
                             variant=variant)
            out.append("## %s (`%s`)" % (tag, h[:16]))
            out.append("")
            if mid_edit is not None:
                out.append("note: `%s`; %d/%d panels served from cache"
                           % (mid_edit, len(rows), len(recs)))
                out.append("")
            if not rows:
                out.append("no cached runs either — skipped")
                out.append("")
                continue
            a = agg(rows)
            agg_by_tag[tag] = a
            gh, g, eh, e = a["gh"], a["g"], a["eh"], a["e"]
            snap_h, snap_g = a["snap"]
            tf_h, tf_d = a["tf"]
            out.append("| metric | value | CI95 (panel bootstrap) | "
                       "gate | gap |")
            out.append("|---|---|---|---|---|")
            rec_box = gh["BOX"] / g["BOX"]
            ci = boot_ci(rows, "BOX_rec", rng)
            out.append("| BOX recall | %.2f (%d/%d) | %.2f..%.2f | "
                       ">=0.70 | %+.2f |"
                       % (rec_box, gh["BOX"], g["BOX"], ci[0], ci[1],
                          rec_box - 0.70))
            prec_box = eh["BOX"] / max(e["BOX"], 1)
            ci = boot_ci(rows, "BOX_prec", rng)
            # R25 §25.2: no judge-derived adjustment in gate rows —
            # plausibility figures live only in the plausibility
            # section (judge spec .67 < .70 = unreliable).
            out.append("| BOX precision | %.2f (%d/%d) | %.2f..%.2f |"
                       " >=0.60 | %+.2f |"
                       % (prec_box, eh["BOX"], e["BOX"], ci[0], ci[1],
                          prec_box - 0.60))
            rec_pl = gh["PATTERN_LINE"] / g["PATTERN_LINE"]
            ci = boot_ci(rows, "PL_rec", rng)
            out.append("| PATTERN_LINE recall | %.2f (%d/%d) | "
                       "%.2f..%.2f | >=0.50 | %+.2f |"
                       % (rec_pl, gh["PATTERN_LINE"],
                          g["PATTERN_LINE"], ci[0], ci[1],
                          rec_pl - 0.50))
            rec_lc = gh["LEVEL_CARRIED"] / g["LEVEL_CARRIED"]
            ci = boot_ci(rows, "LC_rec", rng)
            out.append("| LEVEL_CARRIED recall | %.2f (%d/%d) | "
                       "%.2f..%.2f | >=0.60 | %+.2f |"
                       % (rec_lc, gh["LEVEL_CARRIED"],
                          g["LEVEL_CARRIED"], ci[0], ci[1],
                          rec_lc - 0.60))
            if tf_d:
                ci = boot_ci(rows, "TF", rng)
                out.append("| T/F agreement on matched boxes | %.2f "
                           "(%d/%d) | %.2f..%.2f | >=0.60 | %+.2f |"
                           % (tf_h / tf_d, tf_h, tf_d, ci[0], ci[1],
                              tf_h / tf_d - 0.60))
            else:
                out.append("| T/F agreement on matched boxes | — "
                           "(no marks on matched boxes) | | >=0.60 | |")
            ci = boot_ci(rows, "clutter", rng)
            out.append("| clutter ratio (eng/gold per panel) | %.2f | "
                       "%.2f..%.2f | <=1.5 | %+.2f |"
                       % (a["ratio_med"], ci[0], ci[1],
                          a["ratio_med"] - 1.5))
            out.append("")
            out.append("supporting: snapshot recall **%s** (%d/%d); "
                       "live clutter at tau median **%s** "
                       "(p10 %s / p90 %s); oracle BOX **%s** "
                       "PATTERN_LINE **%s**"
                       % (pct(snap_h, snap_g), snap_h, snap_g,
                          pct(np.median(a["clutter_ev"])
                              if a["clutter_ev"] else 0, 1),
                          pct(np.percentile(a["clutter_ev"], 10)
                              if a["clutter_ev"] else 0, 1),
                          pct(np.percentile(a["clutter_ev"], 90)
                              if a["clutter_ev"] else 0, 1),
                          pct(a["orc"]["BOX"], a["orcg"]["BOX"]),
                          pct(a["orc"]["PATTERN_LINE"],
                              a["orcg"]["PATTERN_LINE"])))
            if a["tr_g"]:
                out.append("trusted-subset (non-Tier-A) line recall: "
                           + "; ".join(
                               "%s **%s** (%d/%d)"
                               % (ty, pct(a["tr_m"][ty], a["tr_g"][ty]),
                                  a["tr_m"][ty], a["tr_g"][ty])
                               for ty in sorted(a["tr_g"])))
            out.append("")
            # per-panel distributions
            out.append("per-panel: golden objects/panel p10/p50/p90 = "
                       "%s; engine objects/panel p10/p50/p90 = %s"
                       % (np.percentile(a["gold_per_panel"],
                                        [10, 50, 90]).round(1),
                          np.percentile([r["n_eng"] for r in rows],
                                        [10, 50, 90]).round(1)))
            out.append("")
    # recall@k (R17 §17.3)
    rak = os.path.join(HERE, "RECALL_AT_K.md")
    if os.path.exists(rak):
        out.append("## recall@k (R17 §17.3 author budget)")
        out.append("")
        out.append("Ranking rule, identical for every arm (R20 "
                   "§20.4.2): object-carried salience score "
                   "(`Obj.score`, in STABLE `9283b389` as output "
                   "only), else born `cand_log` score, else "
                   "recency.  The score wire-up to the ranking "
                   "records landed in this lane at 23:39Z; where "
                   "figures moved vs R31 §31.3, these supersede "
                   "(famledger (c): box@1 .025->.034, line@2 "
                   ".104->.109, bracket@1 .271->.282 — same flat "
                   "conclusion).")
        out.append("")
        rak_txt = open(rak, encoding="utf8").read()
        # R25 §25.2.2: plain statement — v1 selects no better than v0
        v1k = _rak_kcol(rak_txt, "STABLE")
        v0k = _rak_kcol(rak_txt, "## v0")
        if v1k and v0k and "v1" in agg_by_tag and "v0" in agg_by_tag:
            a1, a0 = agg_by_tag["v1"], agg_by_tag["v0"]
            out.append("**v1 does not select better than v0 at the "
                       "author's budget** — top-k snapshot recall, "
                       "all families:")
            out.append("")
            out.append("| engine | k=1 | k=2 | k=5 |")
            out.append("|---|---|---|---|")
            out.append("| v1 STABLE `%s` (= `584c7743`) | %s | %s "
                       "| %s |"
                       % (v1h[:8], v1k.get(1, "?"), v1k.get(2, "?"),
                          v1k.get(5, "?")))
            out.append("| v0 | %s | %s | %s |"
                       % (v0k.get(1, "?"), v0k.get(2, "?"),
                          v0k.get(5, "?")))
            out.append("")
            out.append("Cumulative BOX recall (unbudgeted): v1 "
                       "**%.2f** vs v0 **%.2f**.  v1's edge is ink "
                       "only — clutter ratio ~%.1f vs ~%.1f, live "
                       "objects at tau %d vs %d."
                       % (a1["gh"]["BOX"] / a1["g"]["BOX"],
                          a0["gh"]["BOX"] / a0["g"]["BOX"],
                          a1["ratio_med"], a0["ratio_med"],
                          np.median(a1["clutter_ev"]),
                          np.median(a0["clutter_ev"])))
            out.append("")
        # R31 §31.3: headline per-family budget table
        out.append("**At the author's own budget, per family** "
                   "(per-family recall@k at the family's budget k):")
        out.append("")
        out.append("| arm | box @1 | level @1 | line @2 | "
                   "bracket @1 † |")
        out.append("|---|---|---|---|---|")
        for _lbl, _pat in (("v0", "## v0"),
                           ("v1 STABLE", "STABLE"),
                           ("linelab", "## linelab"),
                           ("famledger (c)", "famledgerV2")):
            out.append("| %s | %s | %s | %s | %s |" % (
                _lbl,
                _fam_cell(rak_txt, _pat, "box"),
                _fam_cell(rak_txt, _pat, "level"),
                _fam_cell(rak_txt, _pat, "line"),
                _fam_cell(rak_txt, _pat, "bracket")))
        out.append("")
        out.append("† upper bound (R30 §30.3)")
        out.append("")
        for ln in rak_txt.splitlines():
            if ln.startswith(("|", "## ", "median", "ranking",
                              "per-family", "author per-family",
                              "BRACKET column", "†")):
                out.append(ln.rstrip())
        out.append("")
    if plaus_note:
        out.append("## plausibility (W1/W1b)")
        out.append("")
        out.append(plaus_note)
        out.append("")
        out.append("R22 §22.3 + R30 §30.1: the blind judge is too "
                   "lenient — specificity .67 on all 30 negatives, "
                   "**.68 [.50-.86] on the 28 valid** (2 invalid: "
                   "BRACKET price-shifts still match — the ruler's "
                   "bracket rule has no price check). The invalid "
                   "negatives do NOT explain the low specificity; "
                   "plausibility stays **inconclusive** and the pack "
                   "does NOT claim 'most engine extras are "
                   "defensible'. A 20-item human sample is prepared "
                   "under OWNER_JUDGE_PACK/.")
        out.append("OWNER_JUDGE_PACK: **GO** — 20 items re-rendered "
                   "with a uniform per-kind tau event (BOX/CONTEXT_"
                   "RANGE tau = drawn right edge for every class, "
                   "killing the tau-inside-box tell) and a single "
                   "blue ~2.5px item style (R30 §30.2); truth key "
                   "outside the pack.")
        out.append("")
    # levers: measured flagged-OFF arms (R20 §20.5, R21-R23) — these
    # are NOT the engine; each is a paired A/B on the frozen ruler.
    out.append("## levers (measured A/B arms — NOT the shipped engine)")
    out.append("")
    out.append("Same-hash pairs (R24 §24.3): every arm ran in this "
               "lane at one code hash `a62edc19` with runtime flags "
               "(`arm_ab.py`, variants `ab_*`); base arm reproduced "
               "STABLE `584c7743` numbers exactly, so the deltas also "
               "read against the frozen default.")
    out.append("")
    out.append("| lever | same-hash delta vs base | verdict |")
    out.append("|---|---|---|")
    out.append("| REQ-1(b) revive ON | BOX .06->.08, BRACKET .29->.38, "
               "LC .12->.10, snapR .10->.11; live clutter 10->12 | "
               "kept OUT of default (R20 §20.1: fails keep-rule on "
               "ink) — Owner lever: +2 BOX +7 BRACKET for +2 live |")
    out.append("| BAR_MARKER day_extreme_only ON | BOX .06->.06, "
               "PL .10->.09, LC .12->.12, BRACKET .29->.32, snapR "
               ".10, clutter 10->9 | flag OFF (PL -1, fails "
               "keep-rule); lever logged |")
    out.append("| BOX drawn tail (+12 bars) | BOX .06->.06, PL "
               ".10->.10, LC .12->.12, BRACKET .29->.31, snapR .10, "
               "clutter 10->11 | ~zero delta (BRACKET +2, clutter +1 "
               "— lane's 'zero' was close but not exact); lever |")
    out.append("| golden-faithful live budget (2/1/2/4) | BOX "
               ".06->.04, PL .10->.08, LC .12->.10, BRACKET .29->.11, "
               "snapR .10->.06, clutter 10->7 | REJECTED — score "
               "cannot select (R22 §22.1) |")
    out.append("| LABEL_TF cap exemption | cross-hash code arm "
               "(`28de3f03`): marks 242->462, BOX 9->6, LC 5->4 | "
               "REJECTED — not a runtime flag, excluded from "
               "same-hash table per R24 §24.3 |")
    out.append("| LEVEL-LAB `level.defended_origin` ON (lab flag, "
               "not shipped) | `e3538ee7` ab_labON: LC born "
               ".12->.21, BOX .06->.04, PL .10, BRACKET .29, "
               "snapR .10, clutter 10->11 | fails keep-rule "
               "(BOX -2) — lab lever only (R26) |")
    out.append("| LEVEL-LAB defended-origin + `def_mini_off` (lab "
               "flag) | `e3538ee7` ab_labV2: LC .12->.15, BOX .06 "
               "healed, PL .10->.09, clutter 11 | fails keep-rule "
               "(PL -1) — lab lever only (R26) |")
    out.append("| LEVEL-LAB + `def_all_lc` (lab flag) | `9283b389` "
               "ab_labV2B rerun complete: BOX .06, PL .10->.09, "
               "LC .12->.15, BRACKET .29->.33, snapR .10, clutter "
               "10->11 | fails keep-rule (PL -1) — lab lever only "
               "(R26); completes the e3538ee7 run that aborted "
               "mid-edit |")
    out.append("| `salience.fam_ledger` only (arm b, `9283b389` "
               "ab_famledger) | BOX .06->.04, LC .12->.10, BRACKET "
               ".29->.35, snapR .10, clutter 10 | ledger-only fails "
               "keep-rule (BOX -2) — EVAL-AUDIT verified "
               "(R29 §29.1) |")
    out.append("| famledger v1 + defended LC (arm c, `9283b389` "
               "ab_famledgerV2) | LC born .12->.21 (+27/-15 per "
               "golden, verified R29 §29.1); BOX .06, PL .10, "
               "BRACKET .29->.35; engine top-k all families: k1 "
               ".006 vs base .01, k2 .025 vs .01, k5 .088 vs .07; "
               "LC at tau .065 | **famledger v1 + defended LC: "
               "keep-rule pass on born recall (verified); four "
               "kinds silenced (defect); no gain at the author's "
               "budget** — R29 §29.2 |")
    out.append("| d2 ceiling probe — LC share 2, "
               "rate_level_carried 2 (lab flag, not shipped) | "
               "LC born .229->.292; births 6->7/panel, clutter "
               "2.5->3.0, live +1, flicker x2 | priced trade, "
               "not kept — ink leg fails (R29 §29.3) |")
    out.append("")
    out.append("famledger (c) defects (R29 §29.2): kinds with no "
               "share entry are never born — CONTEXT_RANGE, "
               "CONTEXT_LINE, MINI_LEVEL, SQUEEZE silenced; the "
               "live budget, geometric NMS and bar timing are still "
               "shared, so 'loses no BOX' is partly outcome luck, "
               "not proof of isolation; `cont` routes bypass the "
               "ledger.  Read as a direction, not an author-budget "
               "result.  Re-measured by this lane with the "
               "object-score ranking now wired (R20 §20.4.2): k1 "
               ".008, k2 .031, k5 .088 — same flat conclusion as "
               "the R29-quoted .006/.025/.088.")
    out.append("")
    # LEVEL-LAB V8 recall@k (R19 §19.4): lab, TUNE, day-level 5-fold CV
    v8 = os.path.join(HERE, "..", "levellab", "ROUND_L7.md")
    if os.path.exists(v8):
        txt = open(v8, encoding="utf8").read()
        if "recall@k" in txt.lower() or "recall@" in txt.lower():
            out.append("## LEVEL-LAB V8 recall@k + CV (lab, TUNE)")
            out.append("")
            grab = False
            for ln in txt.splitlines():
                ls = ln.lower()
                if ls.startswith("##"):
                    grab = ("recall@" in ls or "5-fold" in ls
                            or "cv" in ls.split())
                if grab and ln.strip():
                    out.append(ln)
            out.append("source: levellab/ROUND_L7.md")
            out.append("")
    out.append("## definitions & reconciliation (R15 §15.4)")
    out.append("")
    out.append(
        "- **Clutter gate** = median per panel of the "
        "engine_objects/golden_objects ratio (the row 'clutter "
        "ratio'); the live-objects-at-tau median is a separate "
        "diagnostic, not the gate.  This pack reports that "
        "median-per-panel definition (v1 STABLE ~5.0); the build "
        "lane's final-row 4.50 uses a different aggregation "
        "(R32 §32.3).")
    out.append(
        "- **T/F agreement** is computed only on golden marks that sit "
        "inside a MATCHED golden box's span (n shown in the row).")
    out.append(
        "- **tau per family** (snapshot / recall@k decision time, R21 "
        "§21.2): BOX and all lines = golden `build_end` (the LAST "
        "contained bar before the break, not the break bar itself), "
        "else drawn `t1` when `build_end` is absent; LEVEL_CARRIED / "
        "MINI_LEVEL = `t0` + 10 min; BRACKET / SQUEEZE = `t1`; "
        "BAR_MARKER = `t0`.")
    out.append(
        "- **Oracle (SCOREBOARD vs FUNNEL):** same `cand_right` rule, "
        "different aggregation. Scoreboard credits a golden when ANY "
        "same-family candidate is a right proposal (a candidate may "
        "credit several goldens); funnel assigns each candidate to its "
        "single best golden (best_cand_match). On ef06f265: PL oracle "
        ".397 (any) vs .375 (assigned) — a 4-golden gap. This pack "
        "reports the scoreboard (any) convention; funnel's is the "
        "stricter bound.")
    out.append(
        "- **Born recall:** funnel fills missing golden t0/t1 with the "
        "panel window before matching (gold_with_keys mutates); "
        "scoreboard/gate_pack match the ruler on raw goldens. On "
        "ef06f265 LC born: 7/48 (.146) funnel vs 6/48 (.125) raw. This "
        "pack reports raw-golden recall.")
    out.append(
        "- **Ruler caveat (W0 / R19 §19.1):** v1 BOX windows use "
        "proposal-time ends (`meta_build_end` = proposal bar); "
        "conversion to break-time ends (`break_bar`) measured NET on "
        "cached runs: +2 gains / -1 loss -> net +1 of 108 (~+0.01 "
        "recall) on v1@1f4bed5b and v1@4aaa6a7a; 0 on v0. Ruler frozen; "
        "not adopted before the morning.")
    out.append("")
    # scoreboard history
    out.append("## scoreboard history (all rows)")
    out.append("")
    sb = os.path.join(HERE, "SCOREBOARD.md")
    if os.path.exists(sb):
        for ln in open(sb, encoding="utf8"):
            if ln.startswith("| 20"):
                out.append(ln.rstrip())
    out.append("")
    out.append("## reproducibility")
    out.append("")
    out.append("```")
    out.append("python evalcheck/scoreboard.py v0   # one row")
    out.append("python evalcheck/scoreboard.py v1")
    out.append("python evalcheck/snapshot.py        # snapshot table")
    out.append("python evalcheck/funnel.py          # oracle ceilings")
    out.append("python evalcheck/gate_pack.py       # this file")
    out.append("```")
    out.append("")
    out.append("hashes: eval_v2 `%s`, common `%s`, eval.py `%s`, "
               "book_loader `%s`; engines v0 `%s`, v1 `%s`, linelab `%s`"
               % (file_hash(os.path.join(HERE, "eval_v2.py")),
                  file_hash(os.path.join(HERE, "common.py")),
                  file_hash(os.path.join(PERC, "eval.py")),
                  file_hash(os.path.join(PERC, "golden",
                                         "book_loader.py")),
                  F.code_hash(F.V0_FILES), F.code_hash(F.V1_FILES),
                  lin_hash))
    # one-screen status (R14 §14.5 / R18 §18.2.6)
    out.append("## one-screen status")
    out.append("")
    out.append("- IN: gate metrics + CIs on frozen v1 `%s`; same-hash "
               "lever table (R24 §24.3) incl. famledger b/c verified "
               "per R29 and the d2 priced trade; plausibility "
               "(all-30 vs valid-28, INCONCLUSIVE); recall@k "
               "all-family + per-family (k=1/2/5, CIs, author budget "
               "line, BRACKET upper-bound footnote); lab numbers "
               "separated and labelled 'lab ranker'; cache-integrity "
               "status; scoreboard history; reproducibility hashes."
               % v1h[:8])
    out.append("- OJP: **GO** (uniform tau + blue style, R30 §30.2 "
               "fixes verified p03/p04/p09).")
    out.append("- MISSING: none blocking. Known caveats: BRACKET "
               "figures are upper bounds (ruler has no price check, "
               "R30 §30.3); plausibility judge spec .68 < .70 "
               "(inconclusive, not an artefact of the 2 invalid "
               "negatives); famledger (c) is a direction, not an "
               "author-budget gain.")
    out.append("")
    open(os.path.join(HERE, args.out), "w",
         encoding="utf8").write("\n".join(out) + "\n")
    print("wrote %s" % args.out)



FAM_BUDGET_K = {"box": 1, "level": 1, "line": 2, "bracket": 1}


def _fam_cell(rak_txt, section_pat, fam):
    """RECALL_AT_K.md -> budget-k cell of `fam` in the per-family
    table of the ## section whose header contains section_pat."""
    sec = None
    k = FAM_BUDGET_K[fam]
    for ln in rak_txt.splitlines():
        if ln.startswith("## "):
            sec = section_pat in ln
            continue
        if sec and ln.startswith("| "):
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if cells and cells[0].rstrip(" †") == fam:
                return cells[1 + k].replace("*", "")
    return "?"


if __name__ == "__main__":
    main()
