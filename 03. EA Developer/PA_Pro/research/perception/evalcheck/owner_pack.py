"""OWNER_JUDGE_PACK (R22 §22.3): 20 blind items for the Owner.

  8 engine FPs (v1 sample hash), 6 golden controls, 6 negatives —
  stratified by the blind judge's verdict so the pack mirrors the
  measured mix.  Order shuffled (fixed seed), no labels on PNGs,
  same renders as W1/W1b.  `_key.json` carries the truth and stays
  out of the pack narrative.
"""
import json
import os
import random
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import common as C
import plausibility as PL
from PIL import Image, ImageDraw

MANIFEST = os.path.join(HERE, "_plaus_items.jsonl")
NEG_MANIFEST = os.path.join(HERE, "_plaus_neg.jsonl")
JUDGE = os.path.join(HERE, "_plaus_judge.jsonl")
NJUDGE = os.path.join(HERE, "_plaus_neg_judge.jsonl")
OUT = os.path.join(HERE, "OWNER_JUDGE_PACK")
KEYDIR = os.path.join(HERE, "_owner_judge_key")
STAGE = os.path.join(HERE, "_opk_stage")
SEED = 20260921
V1_PREFIX = "ef06f265"          # v1 FP sample hash (see PLAUSIBILITY.md)

INSTR = """# Chấm thử mù — 20 hình (~10 phút)

Anh ơi, mỗi hình là một panel EUR/USD M5 có **một** vẽ tay (đường
xu hướng / hộp / vạch ngang / tick) cộng một vạch đứt dọc = thời
điểm quyết định. Không có nhãn, không có metadata.

Câu hỏi duy nhất với mỗi hình:

> **"Anh có vẽ cái này lên chart của mình không?"**

Trả lời một trong ba: **yes** / **no** / **cant_tell** vào
`ANSWERS.md` (điền p01…p20). Không cần giải thích; nếu thích thì
ghi một từ (`trendline`, `box`, `level`...).

- Hình nằm trong `items/` — p01.png … p20.png (mã pNN ở góc trên
  chỉ là số thứ tự, không mang thông tin).
- Đáp án nằm ngoài pack này; anh không cần mở gì thêm.
- Không có đáp án "đúng" theo sách; em cần mắt anh làm thước.
"""


def pick(pool, verdict, n, rng):
    cand = [p for p in pool if p.get("_v") == verdict]
    rng.shuffle(cand)
    return cand[:n]


def degenerate(it):
    """Item that would render invisibly (R25 §25.3.2)."""
    g = it["item"]
    k = g.get("kind") or ""
    t0 = g.get("t0")
    t1 = g.get("t1") or t0
    if k in PL.V2.BOX_TYPES or k == "CONTEXT_RANGE":
        if g.get("lo") is None or g.get("hi") is None:
            return True
        return t0 is None or (t1 - t0) < 20 \
            or (g["hi"] - g["lo"]) < 2e-4
    if k in PL.GOLD_LINE_T:
        return not (g.get("p0") is not None or g.get("slope")
                    is not None or g.get("price") is not None)
    return False


def main():
    items = [json.loads(l) for l in open(MANIFEST, encoding="utf8")]
    negs = [json.loads(l) for l in open(NEG_MANIFEST, encoding="utf8")]
    judge = {json.loads(l)["item_id"]: json.loads(l)
             for l in open(JUDGE, encoding="utf8")}
    njudge = {json.loads(l)["item_id"]: json.loads(l)
              for l in open(NJUDGE, encoding="utf8")}
    rng = random.Random(SEED)

    v1fp = [dict(i, _v=judge.get(i["item_id"], {}).get("plausible"))
            for i in items
            if i["src"] == "fp"
            and i.get("engine", "").startswith(V1_PREFIX)]
    ctrl = [dict(i, _v=judge.get(i["item_id"], {}).get("plausible"))
            for i in items if i["src"] == "control"]
    neg = [dict(i, _v=njudge.get(i["item_id"], {}).get("plausible"))
           for i in negs]

    # verdict mix mirrors measured shares (v1 fp 21y/6n/3c;
    # controls 27y/3n; negatives 20n/10y)
    sel = (pick(v1fp, "yes", 6, rng) + pick(v1fp, "no", 1, rng)
           + pick(v1fp, "cant_tell", 1, rng)
           + pick(ctrl, "yes", 5, rng) + pick(ctrl, "no", 1, rng)
           + pick(neg, "no", 4, rng) + pick(neg, "yes", 2, rng))
    assert len(sel) == 20, len(sel)
    # R25 §25.3.2: swap out items that cannot render visibly for a
    # same-class replacement (same source + judge verdict).
    pools = {}
    for p in v1fp + ctrl + neg:
        pools.setdefault((p["src"], p.get("_v")), []).append(p)
    for p in pools.values():
        rng.shuffle(p)
    for i, it in enumerate(sel):
        if not degenerate(it):
            continue
        for cand in pools[(it["src"], it.get("_v"))]:
            if cand not in sel and not degenerate(cand):
                print("REPLACE %s -> %s (%s/%s, degenerate)"
                      % (it["item_id"], cand["item_id"],
                         it["src"], it.get("_v")))
                sel[i] = cand
                break
        else:
            print("WARN no replacement for", it["item_id"])
    rng.shuffle(sel)

    idir = os.path.join(OUT, "items")
    os.makedirs(idir, exist_ok=True)
    os.makedirs(KEYDIR, exist_ok=True)
    os.makedirs(STAGE, exist_ok=True)
    recs = {r["id"]: r for r in C.load_tune()}
    key = []
    checks = []
    for n, it in enumerate(sel, 1):
        pid = "p%02d" % n
        # R25 §25.3: re-render blind — no title band, tau in frame,
        # one clearly visible drawing.  Stage outside the pack so the
        # *.base.png temporaries never land in items/.
        stage_png = os.path.join(STAGE, pid + ".png")
        # R28 §28.3.1 + R30 §30.2: one tau event per kind, the same
        # for every class — tau_item() on the drawn object's own
        # times for ALL items (golden BOX controls move from
        # build_end to the drawn right edge = break bar, which R21
        # §21.2 allows; that removes the "tau inside box = golden"
        # class tell).
        old_tau = it.get("tau")
        tau = PL.tau_item(it["item"])
        r = PL.render_item(recs[it["panel"]], it["item"],
                           tau, stage_png, blind=True)
        im = Image.open(stage_png).convert("RGB")
        ImageDraw.Draw(im).text((4, 6), pid, fill=(0, 0, 0))
        im.save(os.path.join(idir, pid + ".png"))
        dt_bars = (abs(tau - old_tau) / 5.0
                   if tau is not None and old_tau is not None else 0)
        checks.append({"pid": pid, "drawing": bool(r["drew"]),
                       "tau": bool(r["tau_vis"]), "title": "stripped",
                       "tau_fix_bars": dt_bars})
        key.append({
            "pid": pid,
            "truth_src": it["src"],
            "truth_truth": ("engine_fp" if it["src"] == "fp"
                            else it["src"]),
            "judge_verdict": it.get("_v"),
            "origin_item": it["item_id"],
            "panel": it["panel"],
            "kind": it["item"].get("kind") or it["src_type"]
            if it.get("src_type") else it["item"].get("kind"),
        })
    open(os.path.join(KEYDIR, "_key.json"), "w",
         encoding="utf8").write(json.dumps(key, indent=1) + "\n")
    for c in checks:
        print("CHECK %s drawing=%s tau=%s title=%s taufix=%.1fbars"
              % (c["pid"], "yes" if c["drawing"] else "NO",
                 "yes" if c["tau"] else "NO", c["title"],
                 c["tau_fix_bars"]))
    open(os.path.join(OUT, "INSTRUCTIONS.md"), "w",
         encoding="utf8").write(INSTR)
    open(os.path.join(OUT, "ANSWERS.md"), "w", encoding="utf8").write(
        "# Tra loi\n\n" + "".join(
            "- p%02d: \n" % n for n in range(1, 21)))
    print("wrote %s (%d items)" % (OUT, len(key)))


if __name__ == "__main__":
    main()
