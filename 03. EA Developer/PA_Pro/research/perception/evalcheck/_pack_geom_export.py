"""EVAL-AUDIT: blind geometry export for DR-RULES Part E (R77 s.77.3).

DR-RULES escalated correctly: item geometry existed only inside the
keyed file.  This script reproduces the pack's seq->item mapping
(seed-deterministic, 0 swaps logged) and exports GEOMETRY ONLY:

    owner_pack/dr_rules_item_geom.jsonl
    {seq, kind, t0, t1, lo, hi, price, p0, p1, slope, panel, tau}

Dropped (class-identifying): truth, src(engine hash), how, id,
letter, side, tau_at.  `kind` is the shared spec-type vocabulary
(goldens and engine objects use the same names) -> no class leak.

Usage: python evalcheck/_pack_geom_export.py
"""
import collections
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import _m2_pack_c3 as P                         # noqa: E402

OUT = os.path.join(PERC, "owner_pack", "dr_rules_item_geom.jsonl")
KEEP = ("kind", "t0", "t1", "lo", "hi", "price", "p0", "p1", "slope")


def main():
    rng = random.Random(P.SEED)
    recs = C.load_tune()

    epool = P.engine_pool(recs)
    byfam = collections.Counter(
        EV.FAMILY.get(r["src_type"], "?") for r in epool)
    eng_items = []
    for fam, share in byfam.items():
        want = max(1, round(P.N_ENGINE * share / len(epool)))
        sub = [r for r in epool if EV.FAMILY.get(r["src_type"]) == fam]
        rng.shuffle(sub)
        eng_items += sub[:want]
    rest = [r for r in epool if r not in eng_items]
    rng.shuffle(rest)
    eng_items += rest[:P.N_ENGINE - len(eng_items)]
    rng.shuffle(eng_items)
    eng_items = eng_items[:P.N_ENGINE]

    gpool = P.gold_pool(recs)
    rng.shuffle(gpool)
    gold_items = gpool[:P.N_GOLD]
    npool = P.neg_pool()
    rng.shuffle(npool)
    neg_items = npool[:P.N_NEG]

    manifest = ([{"src": "engine", **r} for r in eng_items]
                + [{"src": "control", **r} for r in gold_items]
                + [{"src": "neg", **r} for r in neg_items])
    rng.shuffle(manifest)

    # sanity: seq order must match the sealed key's panel/tau/kind
    key = json.load(open(os.path.join(
        HERE, "_owner_judge_key", "m2_c3_key.json")))["key"]
    mism = 0
    out = []
    for i, row in enumerate(manifest):
        seq = "p%03d" % (i + 1)
        it = row["item"]
        krow = key[seq]
        if krow["panel"] != row["panel"] or krow["tau"] != row["tau"]:
            mism += 1
            continue
        rec = {"seq": seq, "panel": row["panel"], "tau": row["tau"]}
        for kk in KEEP:
            if kk in it:
                rec[kk] = it[kk]
        rec["family"] = EV.FAMILY.get(row.get("src_type"))
        out.append(rec)
    print("key-map mismatches:", mism, "of", len(manifest))
    with open(OUT, "w", encoding="utf8") as fh:
        for r in out:
            fh.write(json.dumps(r) + "\n")
    print("wrote %d rows -> %s" % (len(out), OUT))


if __name__ == "__main__":
    main()
