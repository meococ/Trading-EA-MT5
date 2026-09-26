"""_m2_pack_c3.py — R71 §71.4(a): the M2 blind-precision pack on
STABLE C-3 (uip2_pbbirth@8361fe85 = 1a550212 defaults).

Composition per M2_PACK_PLAN.md (n=48 engine items floor for a
precision CI half-width <= .15):
    48 engine items  = the objects M1 counts: per-family top-k at
                       each golden tau (box@1, level@1, line@2),
                       deduped by object id, rendered at the item's
                       own tau (plausibility.tau_item)
    30 golden controls
    24 audited negatives from _plaus_neg.jsonl
    = 102 items, one colour, blind (no title band), fixed seed.

Outputs:
    owner_pack/items/pNNN.png     - blind renders (price-space path)
    owner_pack/manifest.jsonl     - seq + png ONLY (no truth)
    owner_pack/ANSWERS.md         - blank answer template
    owner_pack/HUONG_DAN.md       - Vietnamese instructions
    evalcheck/_owner_judge_key/m2_c3_key.json  - truth (outside pack)

Usage: python evalcheck/_m2_pack_c3.py   (heavy: book loads per item)
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
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import recall_at_k as RK                        # noqa: E402
import plausibility as PL                       # noqa: E402
from snapshot import tau_of, live_records       # noqa: E402

ARM_H = "8361fe85e73f9437"
ARM_V = "uip2_pbbirth"
STABLE = "1a5502129b4c1554"
SEED = 20260923

N_ENGINE, N_GOLD, N_NEG = 48, 30, 24

OUT = os.path.join(PERC, "owner_pack")
ITEMS = os.path.join(OUT, "items")
KEYDIR = os.path.join(HERE, "_owner_judge_key")
NEG_MANIFEST = os.path.join(HERE, "_plaus_neg.jsonl")

INSTR = """# Chấm mù M2 — 102 hình (~40–50 phút, chia 2 lần cũng được)

Anh ơi, mỗi hình là một panel EUR/USD M5 với **một** nét vẽ
(đường xu hướng / hộp / vạch ngang / marker) cộng một vạch đứt dọc
= thời điểm quyết định. Không nhãn, không metadata.

Câu hỏi duy nhất với mỗi hình:

> **"Anh có vẽ cái này lên chart của mình không?"**

Trả lời **yes** / **no** / **cant_tell** vào `ANSWERS.md`
(p001…p102). Không cần giải thích.

- Hình trong `items/` — mã pNNN chỉ là số thứ tự.
- Trong pack có cả vẽ của máy lẫn vẽ tay thật lẫn mồi sai — anh
  không biết cái nào là cái nào, đó là điểm của bài test.
- Đáp án nằm ngoài pack, em giữ riêng.
"""


def engine_pool(recs):
    """All distinct objects that are family top-k at some golden tau
    under the author's budget, on the C-3 arm cache."""
    pool = {}
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        _t, m, _o, _h, _l, _c = CA.bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        if not g2:
            continue
        taus = sorted({min(tau_of(g), w1) for g in g2
                       if tau_of(g) is not None and tau_of(g) >= w0})
        for tau in taus:
            # cache-only: load the tau pickle directly
            import pickle
            f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                             % (ARM_V, ARM_H, rec["date"], tau))
            if not os.path.exists(f):
                continue
            e = pickle.load(open(f, "rb"))
            live, _em = live_records(e, m, w0, tau)
            osc = {ob.id: getattr(ob, "score", None)
                   for ob in e.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            ranked = RK.rank_live(live, RK.score_map(e))
            fam_ranked = collections.defaultdict(list)
            for r in ranked:
                ff = EV.FAMILY.get(r["type"])
                if ff:
                    fam_ranked[ff].append(r)
            picks = (fam_ranked.get("box", [])[:1]
                     + fam_ranked.get("level", [])[:1]
                     + fam_ranked.get("line", [])[:2])
            for r in picks:
                key = (rec["id"], r.get("id") or
                       (r["type"], r.get("t0"), r.get("t1")))
                if key in pool:
                    continue
                hit = any(V2.match(g, r, m) for g in g2)
                pool[key] = {"panel": rec["id"], "date": rec["date"],
                             "item": PL.norm_engine(r), "tau_at": tau,
                             "src_type": r["type"], "hit": hit}
    out = []
    for row in pool.values():
        row["tau"] = PL.tau_item(row["item"])
        if row["tau"] is not None:
            out.append(row)
    return out


def gold_pool(recs):
    out = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        gobjs, _u, _to = EV.gold_objects(rec)
        for gi, g in enumerate(gobjs):
            if not V2.scorable(g, w0, w1):
                continue
            out.append({"panel": rec["id"], "item": PL.norm_golden(g),
                        "tau": tau_of(g), "src_type": g["spec_type"],
                        "gi": gi})
    return out


def neg_pool():
    rows = [json.loads(l) for l in open(NEG_MANIFEST, encoding="utf8")]
    return [r for r in rows if r.get("render_ok")]


def main():
    rng = random.Random(SEED)
    recs = C.load_tune()
    rec_by_id = {r["id"]: r for r in recs}

    epool = engine_pool(recs)
    print("engine pool: %d distinct top-k objects" % len(epool))
    byfam = collections.Counter(
        EV.FAMILY.get(r["src_type"], "?") for r in epool)
    print("  by family:", dict(byfam))

    # stratified 48: proportional to family share of the pool
    eng_items = []
    for fam, share in byfam.items():
        want = max(1, round(N_ENGINE * share / len(epool)))
        sub = [r for r in epool if EV.FAMILY.get(r["src_type"]) == fam]
        rng.shuffle(sub)
        eng_items += sub[:want]
    rest = [r for r in epool if r not in eng_items]
    rng.shuffle(rest)
    eng_items += rest[:N_ENGINE - len(eng_items)]
    rng.shuffle(eng_items)
    eng_items = eng_items[:N_ENGINE]
    print("engine items sampled: %d" % len(eng_items),
          collections.Counter(EV.FAMILY.get(r["src_type"], "?")
                              for r in eng_items))

    gpool = gold_pool(recs)
    rng.shuffle(gpool)
    gold_items = gpool[:N_GOLD]
    print("golden controls sampled: %d of pool %d"
          % (len(gold_items), len(gpool)))

    npool = neg_pool()
    rng.shuffle(npool)
    neg_items = npool[:N_NEG]
    print("negatives sampled: %d of pool %d"
          % (len(neg_items), len(npool)))

    manifest = ([{"src": "engine", **r} for r in eng_items]
                + [{"src": "control", **r} for r in gold_items]
                + [{"src": "neg", **r} for r in neg_items])
    rng.shuffle(manifest)

    os.makedirs(ITEMS, exist_ok=True)
    os.makedirs(KEYDIR, exist_ok=True)
    key = {}
    pub = []
    answers = ["# ANSWERS — điền yes / no / cant_tell sau mỗi mã\n"]
    n_swap = 0
    spare_e = [r for r in epool if r not in eng_items]
    spare_g = gpool[N_GOLD:]
    spare_n = npool[N_NEG:]
    for i, row in enumerate(manifest):
        iid = "p%03d" % (i + 1)
        rec = rec_by_id[row["panel"]]
        png = os.path.join(ITEMS, iid + ".png")
        res = PL.render_item(rec, row["item"], row["tau"], png,
                             blind=True)
        tries = 0
        while not (res["ok"] and res["drew"]) and tries < 25:
            tries += 1
            n_swap += 1
            spare = (spare_e if row["src"] == "engine"
                     else spare_g if row["src"] == "control"
                     else spare_n)
            if not spare:
                break
            row = spare.pop()
            res = PL.render_item(rec_by_id[row["panel"]],
                                 row["item"], row["tau"], png,
                                 blind=True)
        if not (res["ok"] and res["drew"]):
            print("  WARN undrawable item kept:", iid, row["src"])
        truth = ("engine_hit" if row["src"] == "engine" and
                 row.get("hit") else
                 "engine_fp" if row["src"] == "engine" else
                 "golden" if row["src"] == "control" else "negative")
        key[iid] = {"truth": truth, "family":
                    EV.FAMILY.get(row.get("src_type"), row["src"]),
                    "src_type": row.get("src_type"),
                    "panel": row["panel"], "tau": row["tau"],
                    "tau_at": row.get("tau_at"),
                    "engine": ARM_H if row["src"] == "engine" else None,
                    "how": row.get("how")}
        pub.append({"seq": iid, "png": "items/%s.png" % iid})
        answers.append("- %s: " % iid)

    with open(os.path.join(KEYDIR, "m2_c3_key.json"), "w",
              encoding="utf8") as fh:
        json.dump({"pack": "M2 C-3", "engine_hash": ARM_H,
                   "stable": STABLE, "seed": SEED,
                   "mix": "48 engine top-k + 30 golden + 24 neg",
                   "key": key}, fh, indent=1)
    with open(os.path.join(OUT, "manifest.jsonl"), "w",
              encoding="utf8") as fh:
        for r in pub:
            fh.write(json.dumps(r) + "\n")
    open(os.path.join(OUT, "ANSWERS.md"), "w",
         encoding="utf8").write("\n".join(answers) + "\n")
    open(os.path.join(OUT, "HUONG_DAN.md"), "w",
         encoding="utf8").write(INSTR)
    print("wrote %d items -> %s | swaps %d | key -> %s"
          % (len(pub), OUT, n_swap, KEYDIR))


if __name__ == "__main__":
    main()
