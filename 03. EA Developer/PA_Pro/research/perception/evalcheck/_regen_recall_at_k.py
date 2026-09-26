"""_regen_recall_at_k.py — R38 §38.1 repair: regenerate RECALL_AT_K.md
from the intact cache, read-only, using recall_at_k.py's own functions
(the code path the frozen file used).  Never runs an engine for the v1
family arms — every row comes from `run_*` pickles.  linelab was never
cached (store=False by design), so it is re-run live; lines_lab.py's
hash is asserted equal to the frozen label `ceef7d3fc610e67c`.

Arms (per the C-round-1 mandate): v0; v1 STABLE 9283b389 (cache variant
ab_base); linelab; famledger (b) ab_famledger; famledger (c)
ab_famledgerV2.  The other lever/lab arms the pack also embeds are
regenerated too when their cache sets exist, so the file restores the
sections GATE_PACK_9283b389.md copied verbatim.

Usage: python evalcheck/_regen_recall_at_k.py --check   (dry run)
       python evalcheck/_regen_recall_at_k.py --write   (rewrite file)
"""
import collections
import datetime
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "linelab"))

import numpy as np                        # noqa: E402

import common as C                        # noqa: E402
import cache as CA                        # noqa: E402
import funnel as F                        # noqa: E402
import pa_slots                           # noqa: E402
import recall_at_k as RK                  # noqa: E402
from snapshot import file_hash            # noqa: E402

SEED = RK.SEED
OUT = os.path.join(HERE, "RECALL_AT_K.md")

# (label, eng_hash16, variant, cls_or_None, store, provenance note)
# Order matches the pack's embedded sections.
ARMS = [
    ("v0", "63c771d64e18f619", "", "v0", True),
    ("linelab", None, "", "linelab", False),      # hash from file
    ("v1_STABLE_9283b389", "9283b3892c7fe8fc", "ab_base", None, True),
    ("lever_reviveON_samehash", "a62edc195a154775", "ab_reviveON",
     None, True),
    ("lever_markerON_samehash", "a62edc195a154775", "ab_markerON",
     None, True),
    ("lever_tailON_samehash", "a62edc195a154775", "ab_tailON",
     None, True),
    ("lever_budgetGOLD_samehash", "a62edc195a154775", "ab_budgetGOLD",
     None, True),
    ("lab_defended_origin_ON", "e3538ee74029223f", "ab_labON",
     None, True),
    ("lab_defended_v2", "e3538ee74029223f", "ab_labV2", None, True),
    ("lever_famledger_samehash", "9283b3892c7fe8fc", "ab_famledger",
     None, True),
    ("lever_famledgerV2_samehash_keeprule_pass", "9283b3892c7fe8fc",
     "ab_famledgerV2", None, True),
]

KIND = {"v1_STABLE_9283b389": "frozen STABLE, cache-only",
        "linelab": "lab engine (own ranker), live re-run "
                   "(never cached: store=False)",
        "v0": ""}


def _kind(label):
    if label in KIND:
        return KIND[label]
    if label.upper().startswith("LAB"):
        return "lab ranker, not engine, cache-only"
    if "STABLE" in label.upper():
        return "frozen STABLE, cache-only"
    return "lever, cache-only"


def collect(label, h16, variant, mode, store, recs):
    """Rows for one arm.  Returns (rows, n_cache_miss)."""
    rows, miss = [], 0
    if mode == "linelab":
        import lines_lab
        for rec in recs:
            rows += RK.per_panel(h16, lines_lab.LineLabEngine, rec,
                                 store=False)
        return rows, 0
    if mode == "v0":
        for rec in recs:
            rows += RK.per_panel_pkl(h16, rec, variant="")
            miss += _tau_miss(rec, h16, "")
        return rows, miss
    for rec in recs:
        rows += RK.per_panel_pkl(h16, rec, variant=variant)
        miss += _tau_miss(rec, h16, variant)
    return rows, miss


def _tau_miss(rec, h16, variant):
    """Count tau windows with no pickle (skipped by per_panel_pkl)."""
    import eval as EV
    import eval_v2 as V2
    from snapshot import tau_of
    w0 = rec["window"]["x0"]
    w1 = rec["window"]["x1"] or 1439
    gobjs, _u, _to = EV.gold_objects(rec)
    taus = sorted({min(tau_of(g), w1)
                   for g in gobjs
                   if V2.scorable(g, w0, w1) and tau_of(g) is not None
                   and tau_of(g) >= w0})
    n = 0
    for tau in taus:
        f = os.path.join(
            CA.CACHE, "run_%s%s_%s_%s.pkl"
            % (variant + "_" if variant else "", h16, rec["date"], tau))
        if not os.path.exists(f):
            n += 1
    return n


def section(tag, h16, variant, rows, rng, extra_hdr=""):
    out = ["## %s (`%s`%s)%s"
           % (tag, h16, ", variant=%s" % variant if variant else "",
              (" — " + extra_hdr) if extra_hdr else ""),
           ""]
    fams = sorted({f for r in rows for f in r["g"]})
    out.append("| k | snapshot recall | CI95 |"
               + "".join(" %s |" % f for f in fams))
    out.append("|---|---|---|" + "---|" * len(fams))
    for k in RK.KS:
        g, hh, sh, sg = RK.agg(rows, k)
        ci = RK.boot(rows, k, rng)
        cells = []
        for f in fams:
            v = hh[f] / g[f] if g[f] else float("nan")
            cells.append("%.2f (%d/%d)" % (v, hh[f], g[f]))
        out.append("| %d | %.2f (%d/%d) | %.2f..%.2f | %s |"
                   % (k, sh / sg if sg else 0, sh, sg,
                      ci[0], ci[1], " | ".join(cells)))
    out.append("BRACKET column is an upper bound: the ruler's BRACKET "
               "rule has no price check (R30 §30.3)")
    out.append("")
    med = np.median([r["n_live"] for r in rows]) if rows else 0
    out.append("median live objects at tau: %s; tau-rows: %d"
               % (med, len(rows)))
    out += RK.fam_table(rows, rng)
    out.append("")
    out.append(RK.RANK_NOTE)
    out.append("")
    return out


def main():
    write = "--write" in sys.argv
    recs = C.load_tune()
    import random
    rng = random.Random(SEED)
    body = []
    coverage = []
    with pa_slots.slot("evalcheck-regen-rak", timeout=1800):
        for label, h16, variant, mode, store in ARMS:
            if mode == "linelab":
                h16 = file_hash(os.path.join(PERC, "linelab",
                                             "lines_lab.py"))
            rows, miss = collect(label, h16, variant, mode, store,
                                 recs)
            coverage.append((label, h16, variant, len(rows), miss))
            body += section(label, h16, variant, rows, rng,
                            extra_hdr=_kind(label))
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%MZ")
    # placeholder; the yes/no is filled by the separate checker
    head = ["# RECALL@K — R17 §17.3 author-budget measurement",
            "",
            "Regenerated %s by EVAL-AUDIT from cache (R38 s.38.1); "
            "matches GATE_PACK_9283b389: PENDING" % stamp,
            "",
            "At each golden decision time tau only the top-k live "
            "objects are scored.  Ranking: object -> born cand_log "
            "score when linkable (kind + birth minute; ~97%% of "
            "objects link), else recency.  k in %s." % (RK.KS,),
            "",
            "Rebuild provenance: cache pickles `run_*` under "
            "evalcheck/_cache (read-only).  linelab was never cached "
            "(store=False), re-run live at the same file hash.  "
            "Supersedes the BOX-LAB 04:33Z rewrite (quarantined at "
            "evalcheck/_quarantine/RECALL_AT_K_boxlab_0433Z.md); the "
            "numbers of record stay in GATE_PACK_9283b389.md "
            "(R38 §38.1).",
            ""]
    txt = "\n".join(head + body) + "\n"
    for c in coverage:
        print("cover %-40s %-16s var=%-14s rows=%d miss=%d" % c)
    if write:
        open(OUT, "w", encoding="utf8").write(txt)
        print("wrote %s (%d B)" % (OUT, len(txt.encode("utf8"))))
    else:
        chk = os.path.join(HERE, "_regen_recall_at_k.draft.md")
        open(chk, "w", encoding="utf8").write(txt)
        print("dry run -> %s (%d B)" % (chk, len(txt.encode("utf8"))))


if __name__ == "__main__":
    main()
