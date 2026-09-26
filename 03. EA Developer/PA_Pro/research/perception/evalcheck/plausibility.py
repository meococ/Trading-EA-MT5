"""plausibility.py — mandate 4, W1: blind plausibility audit.

Sample (seed 20260921):
  * 90 engine false positives under eval_v2: 30 v0, 30 current v1,
    30 LINE-LAB lab engine (lines_lab.py);
  * 30 golden objects = hidden controls;
  * 30 golden misses = golden objects matched by NONE of the three
    engines.

Rendering: every item is drawn the SAME way — solid black on the
plain-candle panel (no golden objects, no engine colour codes) — so
the judge cannot tell an item's source.  A dashed vertical line marks
the decision time tau (engine items: birth; golden: mandate Z2 tau;
marks: mark time); everything left of it is knowable.

Output:
  plaus/items/item_NNN.png           — blind renders
  _plaus_items.jsonl                 — manifest WITH ground truth
                                     (never shown to the judge)
  PLAUSIBILITY.md                    — report (after judge scores
                                       land in _plaus_judge.jsonl)

Usage:
  python evalcheck/plausibility.py sample      # build items + renders
  python evalcheck/plausibility.py report      # after judge jsonl
"""
import argparse
import collections
import datetime as dt
import json
import os
import random
import sys
import types

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "golden", "qa"))
sys.path.insert(0, os.path.join(PERC, "golden"))
sys.path.insert(0, os.path.join(PERC, "linelab"))

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import funnel as F                              # noqa: E402
import _render_v2 as R                          # noqa: E402
import pa_slots                                 # noqa: E402
from snapshot import tau_of, file_hash          # noqa: E402

PIP = EV.PIP
SEED = 20260921
ITEM_DIR = os.path.join(HERE, "plaus", "items")
MANIFEST = os.path.join(HERE, "_plaus_items.jsonl")

GOLD_LINE_T = ("PATTERN_LINE", "CONTEXT_LINE")


# ------------------------------------------------------------------ #
# item model: everything normalised to one drawable record
# ------------------------------------------------------------------ #

def norm_engine(er):
    """Engine record (pips) -> drawable record in raw price units."""
    cv = lambda v: v * PIP if v is not None else None      # noqa: E731
    return {"kind": er["type"], "t0": er.get("t0"), "t1": er.get("t1"),
            "lo": cv(er.get("lo")), "hi": cv(er.get("hi")),
            "price": cv(er.get("price")), "letter": er.get("letter"),
            "side": er.get("side"), "p0": cv(er.get("p0")),
            "slope": cv(er.get("slope")), "t0_bar": er.get("t0_bar"),
            "id": er.get("id")}


def norm_golden(g):
    """Golden dict -> drawable record (already raw price units)."""
    st = g["spec_type"]
    r = {"kind": st, "t0": g.get("t0"), "t1": g.get("t1"),
         "letter": g.get("letter"), "side": g.get("side"),
         "id": None}
    if st in V2.BOX_TYPES or st in ("CONTEXT_RANGE",):
        r["lo"], r["hi"] = g.get("price_lo"), g.get("price_hi")
        if r["lo"] is None and g.get("pin_lo") is not None:
            r["lo"], r["hi"] = g["pin_lo"], g["pin_hi"]
    elif st in GOLD_LINE_T:
        r["p0"], r["p1"] = g.get("price0"), g.get("price1")
        if r["p0"] is None:
            r["price"] = g.get("price") or g.get("price0")
    else:
        r["price"] = g.get("price") or g.get("price0")
    return r


def draw_item(dr, vm, m, it, tau_x):
    """One item — one distinct colour and weight for every class
    (R30 §30.2: blue, ~2.5px, so the drawing never hides on the
    EMA).  All prices are raw units (1.3344).  Returns True when a
    mark was actually drawn (R25 §25.3)."""
    col = (25, 65, 205)      # item colour, same for all classes
    tau_col = (150, 150, 150)
    k = it["kind"]
    t0 = it.get("t0")
    t1 = it.get("t1") if it.get("t1") is not None else t0
    if t0 is None:
        return False
    x0, x1 = vm.x(t0), vm.x(t1)
    drew = True
    if k in V2.BOX_TYPES or k == "CONTEXT_RANGE":
        if it.get("lo") is None or it.get("hi") is None:
            return False
        dr.rectangle([x0, vm.y(it["hi"]), x1,
                      vm.y(it["lo"])], outline=col, width=3)
    elif k in GOLD_LINE_T:
        if it.get("p0") is not None and it.get("p1") is not None:
            dr.line([(x0, vm.y(it["p0"])), (x1, vm.y(it["p1"]))],
                    fill=col, width=3)
        elif it.get("p0") is not None and it.get("slope") is not None:
            def y_at(tmin):
                j = int(np.searchsorted(m, tmin))
                j = min(j, len(m) - 1)
                return vm.y(it["p0"] + it["slope"] * (j - it["t0_bar"]))
            dr.line([(x0, y_at(t0)), (x1, y_at(t1))], fill=col,
                    width=3)
    elif it.get("price") is not None:
        y = vm.y(it["price"])
        if k == "BAR_MARKER" or it.get("marker"):
            # visible marker: filled triangle + stem (R25 §25.3.2)
            dr.polygon([(x0, y - 9), (x0 - 6, y - 1),
                        (x0 + 6, y - 1)], fill=col)
            dr.line([(x0, y - 1), (x0, y + 9)], fill=col, width=3)
        else:
            dr.line([(x0, y), (x1, y)], fill=col, width=3)
            if it.get("letter"):
                dr.text(((x0 + x1) / 2 - 6, y + 5), it["letter"],
                        fill=col)
    else:
        drew = False
    if k == "LABEL_TF" and it.get("letter"):
        y = vm.y(it["price"]) if it.get("price") else vm.y0 + 20
        dr.text((x0 + 2, y - 14), it["letter"], fill=col)
        drew = True
    # tau divider
    for y in range(vm.y0, vm.y1, 8):
        dr.line([(tau_x, y), (tau_x, min(y + 4, vm.y1))],
                fill=tau_col)
    return drew


def tau_item(it):
    """R28 §28.3.1: tau = the drawn object's own decision time,
    R21 §21.2 family semantics applied to the ITEM's own fields
    (engine fps and negatives included — no golden needed):
      BOX / lines / CONTEXT_* : build end or break bar -> drawn t1;
      BAR_MARKER              : t0;
      LEVEL_CARRIED/MINI_LEVEL: t0 + 10 min;
      BRACKET / SQUEEZE       : t1."""
    k = it.get("kind") or ""
    t0 = it.get("t0")
    t1 = it.get("t1") if it.get("t1") is not None else t0
    if k == "BAR_MARKER" or it.get("marker"):
        return t0
    if k in ("LEVEL_CARRIED", "MINI_LEVEL"):
        return (t0 + 10) if t0 is not None else None
    return t1  # boxes, all lines, brackets, squeeze, label_tf


def render_item(rec, it, tau, path, blind=False):
    """Plain panel (no golden objects) + the item + tau divider.
    Returns {"ok", "drew", "tau_vis"} — drew/tau_vis feed the R25
    §25.3 per-item verification lines.  blind=True additionally
    erases the renderer's identifying title band and expands the
    view so tau is always inside the frame."""
    rec2 = dict(rec)
    rec2["objects"] = []
    rec2["marks"] = []
    tmp = path + ".base.png"
    if not R.render(rec2, tmp):
        return {"ok": False, "drew": False, "tau_vis": False}
    day = rec["date"]
    d0 = dt.date.fromisoformat(day)
    import book_loader
    bars = book_loader.load_m5(day + " 00:00",
                               (d0 + dt.timedelta(days=1)).isoformat()
                               + " 00:00")
    srv = bars["cet_min"].astype(int)
    t0 = int(rec["window"]["x0"]) - 150
    t1 = int(rec["window"]["x1"]) + 40
    if tau is None:          # no annotated decision time: use the
        tau = it.get("t1") or it.get("t0") or t0   # object's own end
    if blind:                # keep the tau divider inside the frame
        t0 = min(t0, int(tau) - 30)
        t1 = max(t1, int(tau) + 30)
    idx = np.where((srv >= t0) & (srv <= t1))[0]
    vm = R.VMap(t0, t1, float(bars["l"][idx].min()) - 8 * PIP,
                float(bars["h"][idx].max()) + 8 * PIP)
    im = Image.open(tmp).convert("RGB")
    dr = ImageDraw.Draw(im)
    if blind:                # strip the golden/id title line (R25 §25.3.1)
        dr.rectangle([0, 0, im.width, 24], fill=(255, 255, 255))
    it = dict(it)
    if it.get("price") is None and it.get("p0") is None \
            and it.get("lo") is None and it.get("t0") is not None:
        k = it["kind"]
        if k == "BAR_MARKER":
            j = int(np.argmin(np.abs(srv - it["t0"])))
            it["price"] = float(bars["h"][j]) + 2 * PIP
            it["marker"] = True
        else:
            sm = (srv >= it["t0"]) & (srv <= (it["t1"] or it["t0"]))
            if sm.any():
                side = it.get("side") or (
                    "above" if (it.get("letter") or "M")
                    in ("M", "Mm", "SHS") else "below")
                p = float(bars["h"][sm].max()) if side == "above" \
                    else float(bars["l"][sm].min())
                it["price"] = p + (4 * PIP if side == "above"
                                   else -4 * PIP)
    drew = draw_item(dr, vm, srv, it, vm.x(tau))
    im.save(path)
    return {"ok": True, "drew": bool(drew),
            "tau_vis": bool(vm.x0 <= vm.x(tau) <= vm.x1)}


# ------------------------------------------------------------------ #
# sampling
# ------------------------------------------------------------------ #

def engine_fps(cls, eng_hash, recs, rng, n_want):
    """(fps, matched_golden_ids) for one engine."""
    fps, gold_hit = [], set()
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        e = CA.run(eng_hash, cls, rec,
                   store=(eng_hash != "linelab"))
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
        hit_e = {ei for _, ei in pairs}
        hit_em = {id(em) for _, em in mpairs}
        for gi, _ in pairs:
            gold_hit.add((rec["id"], gi))
        for ei, er in enumerate(eboxes):
            if ei not in hit_e:
                fps.append({"engine": eng_hash, "panel": rec["id"],
                            "item": norm_engine(er),
                            "tau": er.get("t_birth") or er["t0"],
                            "src_type": er["type"]})
        for em in emarks:
            if id(em) not in hit_em:
                fps.append({"engine": eng_hash, "panel": rec["id"],
                            "item": norm_engine(em),
                            "tau": em.get("t_birth") or em["t0"],
                            "src_type": "LABEL_TF"})
    # stratified by type: proportional, min 2 per type when available
    by_t = collections.defaultdict(list)
    for f in fps:
        by_t[f["src_type"]].append(f)
    take = {}
    left = n_want
    types = sorted(by_t, key=lambda k: -len(by_t[k]))
    for ty in types:
        want = max(2, round(n_want * len(by_t[ty]) / len(fps)))
        want = min(want, len(by_t[ty]), left)
        take[ty] = want
        left -= want
    for ty in types:                     # top up if rounds left slack
        if left <= 0:
            break
        extra = min(len(by_t[ty]) - take[ty], left)
        take[ty] += extra
        left -= extra
    out = []
    for ty, k in take.items():
        out += rng.sample(by_t[ty], k)
    return out, gold_hit


def cmd_sample():
    rng = random.Random(SEED)
    import engine as ENG_V1
    import engine_v0 as ENG_V0
    import lines_lab
    recs = C.load_tune()
    lin_hash = file_hash(os.path.join(PERC, "linelab", "lines_lab.py"))
    engines = [("v0", ENG_V0.PerceptionEngine,
                F.code_hash(F.V0_FILES)),
               ("v1", ENG_V1.PerceptionEngine,
                F.code_hash(F.V1_FILES)),
               ("linelab", lines_lab.LineLabEngine, "linelab")]
    os.makedirs(ITEM_DIR, exist_ok=True)
    manifest = []
    union_hit = set()
    with pa_slots.slot("evalcheck-plaus", timeout=1800):
        fp_pools = {}
        for tag, cls, h in engines:
            fps, gold_hit = engine_fps(cls, h, recs, rng, 30)
            fp_pools[tag] = fps
            union_hit |= gold_hit
            manifest += [{"src": "fp", "engine": tag, **f}
                         for f in fps]
            print("%s: %d fps sampled" % (tag, len(fps)), flush=True)
        # golden controls + misses
        gpool, misses = [], []
        for rec in recs:
            w0 = rec["window"]["x0"]
            w1 = rec["window"]["x1"] or 1439
            gobjs, _u, _to = EV.gold_objects(rec)
            for gi, g in enumerate(gobjs):
                if not V2.scorable(g, w0, w1):
                    continue
                row = {"panel": rec["id"], "g": g,
                       "item": norm_golden(g), "tau": tau_of(g),
                       "src_type": g["spec_type"], "gi": gi}
                gpool.append(row)
                if (rec["id"], gi) not in union_hit:
                    misses.append(row)
        for row in rng.sample(gpool, 30):
            manifest.append({"src": "control", **row})
        for row in rng.sample(misses, min(30, len(misses))):
            manifest.append({"src": "miss", **row})
        print("controls 30 / misses sampled %d (pool %d)"
              % (min(30, len(misses)), len(misses)), flush=True)
        # anonymise + render
        order = list(range(len(manifest)))
        rng.shuffle(order)
        for new_i, mi in enumerate(order):
            row = manifest[mi]
            iid = "item_%03d" % new_i
            row["item_id"] = iid
            row["item"]["id"] = iid
            png = os.path.join(ITEM_DIR, iid + ".png")
            rec = next(r for r in recs if r["id"] == row["panel"])
            ok = render_item(rec, row["item"], row["tau"], png)["ok"]
            row["png"] = os.path.relpath(png, HERE)
            row["render_ok"] = ok
        with open(MANIFEST, "w", encoding="utf8") as fh:
            for row in manifest:
                fh.write(json.dumps(row, default=str) + "\n")
    print("wrote %d items -> %s + manifest" % (len(manifest), ITEM_DIR))


# ------------------------------------------------------------------ #
# W1b — negative controls (R17 §17.4): 30 causally-wrong items,
# rendered identically, judged blind by fresh judges.
# ------------------------------------------------------------------ #

NEG_DIR = os.path.join(HERE, "plaus", "neg")
NEG_MANIFEST = os.path.join(HERE, "_plaus_neg.jsonl")


def _abr_at(date, tmin):
    """ABR(14) in raw price units at a CET minute."""
    a = CA.abr(date, 14)
    t, m, o, h, l, c = CA.bars(date)
    j = int(np.searchsorted(m, tmin))
    j = min(j, len(m) - 1)
    return float(a[j]) * PIP


def _trend_window(m, lo, hi, w0, w1, span_min=60):
    """Find a [t0, t0+span] window where price trends hard (net move >
    2*span ABR-equivalent): a place no trader would box."""
    best = None
    for t0 in range(w0, max(w0 + 1, w1 - span_min), 15):
        j0 = int(np.searchsorted(m, t0))
        j1 = int(np.searchsorted(m, t0 + span_min))
        j1 = min(j1, len(m) - 1)
        if j1 <= j0:
            continue
        net = abs(float(hi[j0:j1].max()) - float(lo[j0:j1].min()))
        rng = float(hi[j0:j1].max() - lo[j0:j1].min())
        if best is None or rng > best[2]:
            best = (t0, t0 + span_min, rng)
    return best


def cmd_negatives():
    """Build + render 30 causally-wrong items (seed-offset sample)."""
    rng = random.Random(SEED + 77)
    recs = C.load_tune()
    os.makedirs(NEG_DIR, exist_ok=True)
    # collect golden pool
    gpool = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        gobjs, _u, _to = EV.gold_objects(rec)
        for gi, g in enumerate(gobjs):
            if not V2.scorable(g, w0, w1):
                continue
            gpool.append((rec, g))
    out = []
    tries = 0
    while len(out) < 30 and tries < 400:
        tries += 1
        rec, g = gpool[rng.randrange(len(gpool))]
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        it = norm_golden(g)
        how = rng.choice(["price", "time", "nonpivot", "trendbox"])
        abr = _abr_at(rec["date"], it.get("t0") or w0)
        ok = True
        if how == "price":
            sgn = rng.choice([-1, 1])
            d = abr * rng.uniform(3.0, 5.0)
            for k in ("lo", "hi", "price", "p0", "p1"):
                if it.get(k) is not None:
                    it[k] += sgn * d
        elif how == "time":
            dt = rng.choice([-120, 120])
            it["t0"] = (it.get("t0") or w0) + dt
            if it.get("t1") is not None:
                it["t1"] += dt
            if it["t0"] < w0 or (it["t1"] or it["t0"]) > w1:
                ok = False
        elif how == "nonpivot":
            if it.get("kind") not in GOLD_LINE_T:
                ok = False
            else:
                t, m, o, h, l, c = CA.bars(rec["date"])
                j0 = int(np.searchsorted(m, it["t0"]))
                j1 = int(np.searchsorted(m, it["t1"] or it["t0"]))
                j0, j1 = min(j0, len(m) - 1), min(j1, len(m) - 1)
                # anchors at bar midpoints (never pivot extremes)
                it["p0"] = float((h[j0] + l[j0]) / 2) * PIP
                it["p1"] = float((h[j1] + l[j1]) / 2) * PIP
        else:  # trendbox: a box drawn across a trending leg
            t, m, o, h, l, c = CA.bars(rec["date"])
            bw = _trend_window(m, l, h, w0, w1)
            if bw is None:
                ok = False
            else:
                t0b, t1b, rng_ = bw
                pad = 0.1 * rng_
                it = {"kind": "BOX", "t0": t0b, "t1": t1b,
                      "lo": (float(l[int(np.searchsorted(
                          m, t0b)):int(np.searchsorted(m, t1b))].min())
                          + pad) * PIP,
                      "hi": (float(h[int(np.searchsorted(
                          m, t0b)):int(np.searchsorted(m, t1b))].max())
                          - pad) * PIP}
        if not ok:
            continue
        iid = "neg_%03d" % len(out)
        png = os.path.join(NEG_DIR, iid + ".png")
        tau = it.get("t1") or it.get("t0")
        okr = render_item(rec, it, tau, png)["ok"]
        if not okr:
            continue
        out.append({"item_id": iid, "src": "neg", "how": how,
                    "panel": rec["id"], "item": it, "tau": tau,
                    "png": os.path.relpath(png, HERE),
                    "render_ok": okr})
        print(iid, how, rec["id"], flush=True)
    with open(NEG_MANIFEST, "w", encoding="utf8") as fh:
        for row in out:
            fh.write(json.dumps(row, default=str) + "\n")
    print("wrote %d negatives -> %s" % (len(out), NEG_DIR))


# ------------------------------------------------------------------ #
# report (reads judge answers from _plaus_judge.jsonl)
# ------------------------------------------------------------------ #

def cmd_report():
    items = {json.loads(l)["item_id"]: json.loads(l)
             for l in open(MANIFEST, encoding="utf8")}
    judge = {}
    for l in open(os.path.join(HERE, "_plaus_judge.jsonl"),
                  encoding="utf8"):
        j = json.loads(l)
        judge[j["item_id"]] = j
    out = ["# PLAUSIBILITY — blind audit (mandate W1, seed %d)" % SEED,
           ""]
    ctrl = [i for i in items.values() if i["src"] == "control"]
    fps = [i for i in items.values() if i["src"] == "fp"]
    miss = [i for i in items.values() if i["src"] == "miss"]
    cy = sum(judge.get(c["item_id"], {}).get("plausible") == "yes"
             for c in ctrl)
    crate = cy / len(ctrl)
    out.append("## judge calibration")
    out.append("")
    out.append("Golden-control 'yes' rate: **%d/%d = %.2f** — %s"
               % (cy, len(ctrl), crate,
                  "judge reliable (>= 0.8)"
                  if crate >= 0.8 else "JUDGE UNRELIABLE (< 0.8)"))
    out.append("")
    out.append("## plausible-FP rate (share of engine FPs a PA trader "
               "would plausibly draw)")
    out.append("")
    out.append("| engine | n | plausible | rate |")
    out.append("|---|---|---|---|")
    tags = {F.code_hash(F.V0_FILES): "v0", "linelab": "linelab"}
    v1_hashes = {f["engine"] for f in fps} - set(tags)
    for h in v1_hashes:
        tags[h] = "v1@" + h[:8]
    adj = {}
    for h in sorted({f["engine"] for f in fps}):
        sub = [f for f in fps if f["engine"] == h]
        p = sum(judge.get(f["item_id"], {}).get("plausible") == "yes"
                for f in sub)
        adj[tags[h]] = p / len(sub) if sub else 0
        out.append("| %s | %d | %d | %.2f |" % (tags[h], len(sub), p,
                                               adj[tags[h]]))
    out.append("")
    by_t = collections.defaultdict(lambda: [0, 0])
    for f in fps:
        j = judge.get(f["item_id"], {})
        by_t[f["src_type"]][1] += 1
        by_t[f["src_type"]][0] += j.get("plausible") == "yes"
    out.append("| fp type | n | plausible | rate |")
    out.append("|---|---|---|---|")
    for ty, (p, n) in sorted(by_t.items()):
        out.append("| %s | %d | %d | %.2f |" % (ty, n, p, p / n))
    out.append("")
    ky = sum(judge.get(mm["item_id"], {}).get("knowable") == "yes"
             for mm in miss)
    my = sum(judge.get(mm["item_id"], {}).get("plausible") == "yes"
             for mm in miss)
    out.append("## golden misses (golden objects no engine matched)")
    out.append("")
    out.append("knowable share: **%d/%d = %.2f** ; plausible share: "
               "**%d/%d = %.2f**" % (ky, len(miss), ky / len(miss),
                                     my, len(miss), my / len(miss)))
    out.append("")
    fk = sum(judge.get(f["item_id"], {}).get("knowable") == "yes"
             for f in fps)
    out.append("engine-FP knowable share (structure existed at "
               "decision time): **%d/%d = %.2f**"
               % (fk, len(fps), fk / len(fps)))
    out.append("")
    # ---- W1b: negative controls + Rogan-Gladen correction --------
    njf = os.path.join(HERE, "_plaus_neg_judge.jsonl")
    if os.path.exists(NEG_MANIFEST) and os.path.exists(njf):
        negs = {json.loads(l)["item_id"]: json.loads(l)
                for l in open(NEG_MANIFEST, encoding="utf8")}
        njudge = {}
        for l in open(njf, encoding="utf8"):
            j = json.loads(l)
            njudge[j["item_id"]] = j
        n_neg = len(negs)
        n_dec = sum(njudge.get(i, {}).get("plausible")
                    in ("yes", "no") for i in negs)
        spec_yes = sum(njudge.get(i, {}).get("plausible") == "yes"
                       for i in negs)
        # specificity on DECIDED items only (cant_tell excluded)
        spec = 1.0 - spec_yes / n_dec if n_dec else float("nan")
        sens = cy / len(ctrl)
        out.append("## judge specificity (W1b negative controls, "
                   "R17 §17.4)")
        out.append("")
        out.append("sensitivity (golden controls yes-rate): "
                   "**%d/%d = %.2f**" % (cy, len(ctrl), sens))
        out.append("")
        out.append("specificity (negatives judged not-plausible, "
                   "cant_tell excluded): **%d/%d = %.2f** "
                   "(n_decided %d/%d)%s" % (
                       n_dec - spec_yes, n_dec, spec,
                       n_dec, n_neg,
                       "" if spec >= 0.70 else
                       "  — **UNRELIABLE (< 0.70)**"))
        out.append("")
        rng = random.Random(SEED + 99)
        out.append("| engine | n | obs. plausible | Rogan–Gladen "
                   "corrected | CI95 |")
        out.append("|---|---|---|---|---|")
        for h in sorted({f["engine"] for f in fps}):
            sub = [f for f in fps if f["engine"] == h]
            obs = sum(judge.get(f["item_id"], {}).get("plausible")
                      == "yes" for f in sub) / len(sub)
            den = sens + spec - 1.0
            corr = (obs + spec - 1.0) / den if den > 0.05 else \
                float("nan")
            corr = min(1.0, max(0.0, corr))
            vals = []
            for _ in range(2000):
                b_spec = 1.0 - sum(
                    rng.random() < (spec_yes / max(n_dec, 1))
                    for _ in range(n_dec)) / max(n_dec, 1)
                b_sens = sum(rng.random() < sens
                             for _ in range(len(ctrl))) / len(ctrl)
                b_obs = sum(rng.random() < obs
                            for _ in range(len(sub))) / len(sub)
                d2 = b_sens + b_spec - 1.0
                v = ((b_obs + b_spec - 1.0) / d2
                     if d2 > 0.05 else float("nan"))
                if v == v:
                    vals.append(min(1.0, max(0.0, v)))
            vals.sort()
            ci = (vals[int(0.025 * len(vals))],
                  vals[int(0.975 * len(vals))]) if vals else \
                (float("nan"), float("nan"))
            out.append("| %s | %d | %.2f | %.2f | %.2f..%.2f |"
                       % (tags[h], len(sub), obs, corr,
                          ci[0], ci[1]))
    open(os.path.join(HERE, "PLAUSIBILITY.md"), "w",
         encoding="utf8").write("\n".join(out) + "\n")
    print("wrote PLAUSIBILITY.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sample", "report", "negatives"])
    args = ap.parse_args()
    {"sample": cmd_sample, "report": cmd_report,
     "negatives": cmd_negatives}[args.cmd]()


if __name__ == "__main__":
    main()
