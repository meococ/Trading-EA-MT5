"""_m2_tv_pack.py — the M2-TV 50-item blind pack (R79 §79.2 as
amended by R82 §82.5).  EVAL-AUDIT-only builder.

Engine under test: NAMED IN R83.  The script takes it as a constant
below — placeholder per §82.5(4) is the verified C-3 canonical cache
(uip2_pbbirth@8361fe85) with trade_tags=1 semantics: canonical output
is identical to C-3 (verified ON==parent 623/623), so the τ-run
pickles ARE the R83 engine state; tags are recomputed per object at τ
via trade_tags.object_stats — the same predicates the flag writes
into facts.

Composition (amended plan §2):
  30 engine   tradeable top-k objects at golden-decision τ
              (box@1, level@1, line@2, bracket@1), >=6/fam floor for
              box/level/line, rest proportional, <=1/panel/family
  10 golden   author objects with no TRADE_VIEW_HIDE tag at own τ,
              stratified by family, <=1/panel/family
  10 negative mutated tradeable engine objects (audited methods:
              price-shift / time-stretch / non-pivot re-anchor /
              trend-box), re-tagged after mutation

Every item: bars stop at τ (ceiling_render sheet), dashed now
divider, EMA25, ONE blue object clipped at τ, engine background under
the trade-view rule (drop TRADE_VIEW_HIDE-tagged objects), no title
band, no metadata.  Gemini render-checks before the Owner sees it.

Outputs:
  owner_pack/items/pNNN.png
  owner_pack/manifest.jsonl     {seq, png} only
  owner_pack/ANSWERS.md         blank
  owner_pack/HUONG_DAN.md       Vietnamese instructions
  evalcheck/_owner_judge_key/m2_tv_key.json   (sealed, outside pack)
  evalcheck/_m2_tv_geom.jsonl   geometry-only sidecar (no class)

DRY-RUN CLAUSE (§82.5(4)): until R83 names the engine this script is
STAGED ONLY.  Pool counts under the M1-consistent scorer (object-
carried score injected into live records, as recall_at_k.per_panel
does): engine 598 / golden 179 / negative source 598 — the dry run's
engine count (508) used cand_log-linked scores only; corrected and
re-logged 13:5xZ.  Running this file produces owner_pack artifacts;
do NOT run before the Lead approves.
"""
import argparse
import collections
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "deepresearch"))
sys.path.insert(0, os.path.join(PERC, "review"))
sys.path.insert(0, os.path.join(PERC, "golden", "qa"))
sys.path.insert(0, os.path.join(PERC, "golden"))

import numpy as np                              # noqa: E402
from PIL import Image, ImageDraw                # noqa: E402
import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import recall_at_k as RK                        # noqa: E402
import trade_tags as TT                         # noqa: E402
import plausibility as PL                       # noqa: E402
import DR_RULES_measure as DM                   # noqa: E402
import ceiling_render as CR                     # noqa: E402
import _render_v2 as R                          # noqa: E402
import render_review_set as RRV                 # noqa: E402
from snapshot import tau_of, live_records       # noqa: E402
from _tt2_report_verify import (gold_v2_stats,  # noqa: E402
                               tags_golden_v1)

# ---- R83 engine name goes here (placeholder per s.82.5(4)) ---------
ENGINE_DESC = "C-3 canonical uip2_pbbirth@8361fe85 + trade_tags=1"
SEED = 20260923
N_ENGINE, N_GOLD, N_NEG = 30, 10, 10
FAM_BUDGET = {"box": 1, "line": 2, "level": 1, "bracket": 1}
FAM_FLOOR = {"box": 6, "level": 6, "line": 6, "bracket": 0}
EXCLUDE_PANELS = {"9.46a", "9.34b", "9.1a", "9.30c"}   # p099-p102
PIP = 1e-4

OUT = os.path.join(PERC, "owner_pack")
ITEMS = os.path.join(OUT, "items")
KEYDIR = os.path.join(HERE, "_owner_judge_key")
GEOM_SIDECAR = os.path.join(HERE, "_m2_tv_geom.jsonl")
AXDIR = os.path.join(HERE, "_scratch_m2tv_ax")

INSTR = """# Chấm mù M2-TV — 50 hình (~20–25 phút)

Anh ơi, mỗi hình là một panel EUR/USD M5 đúng như "trade view":
nến + EMA25, các object nền của máy (object mỏi/không còn hợp lệ đã
bị ẩn đúng như chart thật), vạch đứt dọc = "bây giờ" (không có nến
nào sau nó), và **một** object màu xanh dương.

Câu hỏi duy nhất với mỗi hình:

> **"Ở thời điểm vạch đứt, anh có dùng được object xanh này để giao
> dịch không?"**

Trả lời **yes** / **no** / **cant_tell** vào `ANSWERS.md`
(p001…p050). Không cần giải thích.

- Trong pack có cả object của máy, vẽ tay thật, và mồi sai — anh
  không biết cái nào là cái nào.
- Đáp án nằm ngoài pack, em giữ riêng.
"""


# ------------------------------------------------------------------ #
# pools
# ------------------------------------------------------------------ #

def tags_of_obj(ob, nfed, bars, ema, abr, pivots):
    """Trade-view tags for one engine Obj at bar nfed (same as
    facts['trade_tags'] under trade_tags=1)."""
    ff, st = TT.object_stats(ob, nfed, bars, ema, abr, pivots)
    if ff is None:
        return None, set()
    return ff, TT.tags_from_stats(ff, st)


def engine_pool(recs):
    """(panel,obj_id) -> {fam, item, tau, panel, obj_id, hit, tags}
    for tradeable top-k picks at golden-decision taus.  tau = the
    FIRST golden-decision tau the object entered the pool at."""
    pool = {}
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        taus = sorted({min(tau_of(g), w1) for g in g2
                       if tau_of(g) is not None and tau_of(g) >= w0})
        for tau in taus:
            if tau > w1:
                continue
            e = DM.pickled(rec["date"], tau)
            if e is None:
                continue
            m = np.array([b["cet_min"] for b in e.bars])
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
            objs = {ob.id: ob for ob in e.objects}
            nfed = len(e.bars) - 1
            for fam, k in FAM_BUDGET.items():
                for r in fam_ranked.get(fam, [])[:k]:
                    rid = r.get("id")
                    ob = objs.get(rid)
                    if ob is None:
                        continue
                    _ff, tags = tags_of_obj(
                        ob, nfed, e.bars, e.ema, e.abr, e.book.seq)
                    if tags & TT.TRADE_VIEW_HIDE:
                        continue
                    it0 = PL.norm_engine(r)
                    if it0.get("t0") is not None and it0["t0"] > tau:
                        continue      # undrawable at its own tau
                    key = (rec["id"], rid)
                    if key in pool:
                        continue
                    hit = any(V2.match(g, r, m) for g in g2)
                    pool[key] = {"panel": rec["id"], "date": rec["date"],
                                 "obj_id": rid, "fam": fam,
                                 "item": PL.norm_engine(r),
                                 "tau": tau, "hit": hit,
                                 "tags": sorted(tags),
                                 "src_type": r["type"]}
    return pool


def golden_pool(recs):
    """(panel,gi) -> {fam, item, tau, tags} for golden objects with no
    hide tag at their own tau (golden conventions, identical rule)."""
    gold_rows = [json.loads(x) for x in open(
        os.path.join(PERC, "deepresearch", "DR_RULES_golden.jsonl"),
        encoding="utf8")]
    gold_by = collections.defaultdict(list)
    for r in gold_rows:
        gold_by[(r["panel"], r["tau"])].append(r)
    pool = {}
    for rec in recs:
        w1 = rec["window"]["x1"] or 1439
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs
              if V2.scorable(g, rec["window"]["x0"], w1)]
        rows_here = [r for (p, _t), rs in gold_by.items()
                     if p == rec["id"] for r in rs]
        by_tau = collections.defaultdict(list)
        for r in rows_here:
            by_tau[r["tau"]].append(r)
        for tau, trs in sorted(by_tau.items()):
            e = DM.pickled(rec["date"], tau)
            if e is None:
                continue
            m = np.array([b["cet_min"] for b in e.bars])
            o = np.array([b["o"] for b in e.bars])
            h = np.array([b["h"] for b in e.bars])
            l = np.array([b["l"] for b in e.bars])
            c = np.array([b["c"] for b in e.bars])
            abr = np.asarray(e.abr)
            for r in trs:
                g = g2[r["gi"]] if r["gi"] < len(g2) else None
                if g is None:
                    continue
                fam = r["fam"]
                t_v1 = tags_golden_v1(r)
                if t_v1 & TT.TRADE_VIEW_HIDE:
                    continue
                st2 = gold_v2_stats(g, fam, m, o, h, l, c, abr, tau)
                if st2.get("lbroken") or st2.get("lcuts") \
                        or st2.get("stale"):
                    continue
                tags = set(t_v1)
                for nm, tag in (("lbroken", "line_broken"),
                                ("lcuts", "line_cuts_bodies"),
                                ("stale", "stale_far")):
                    if st2.get(nm):
                        tags.add(tag)
                # R83 s83.2: golden-side box_broken under the same
                # entry-anchored rule (author's own span/edges/tau).
                if fam == "box":
                    lo = g.get("price_lo") or g.get("price0")
                    hi = g.get("price_hi") or g.get("price1")
                    if lo and hi and g.get("t0") is not None:
                        j_fr = int(np.searchsorted(m, g["t0"]))
                        j_t = min(int(np.searchsorted(
                            m, tau, "right")) - 1, len(m) - 1)
                        if TT.s_box_broken(
                                lo / PIP, hi / PIP, j_fr, j_t,
                                c, abr).get("bbroken"):
                            continue
                        tags.discard("box_broken")
                itg = PL.norm_golden(g)
                if itg.get("t0") is not None and itg["t0"] > tau:
                    continue          # undrawable at its own tau
                pool[(rec["id"], r["gi"])] = {
                    "panel": rec["id"], "date": rec["date"],
                    "gi": r["gi"], "fam": fam,
                    "item": PL.norm_golden(g), "tau": tau,
                    "tags": sorted(tags), "src_type": g["spec_type"]}
        # bracket goldens: no tag rules exist for the family, so the
        # identical rule admits them by design (DR_RULES_golden.jsonl
        # has no bracket rows — they are added here directly).
        for gi, g in enumerate(g2):
            if EV.FAMILY.get(g["spec_type"]) != "bracket":
                continue
            tau = tau_of(g)
            if tau is None or not (rec["window"]["x0"] <= tau <= w1):
                continue
            itg = PL.norm_golden(g)
            if itg.get("t0") is not None and itg["t0"] > tau:
                continue              # undrawable at its own tau
            pool.setdefault((rec["id"], gi), {
                "panel": rec["id"], "date": rec["date"], "gi": gi,
                "fam": "bracket", "item": PL.norm_golden(g),
                "tau": min(tau, w1), "tags": [],
                "src_type": g["spec_type"]})
    return pool


# ------------------------------------------------------------------ #
# negatives — audited mutations on tradeable engine objects
# ------------------------------------------------------------------ #

def _abr_at(date, tmin):
    return PL._abr_at(date, tmin)


def mutate_item(it, rec, how, rng, tau):
    """Audited M2_PACK methods (plausibility.cmd_negatives), adapted
    to a tradeable engine-source item.  Returns (item, ok).  The item
    must stay drawable at tau (its left edge at or before the
    decision) - a mutated object drawn entirely after tau is not a
    valid negative."""
    it = dict(it)
    w0 = rec["window"]["x0"]
    w1 = rec["window"]["x1"] or 1439
    ok = True
    if how == "price":                       # shift
        sgn = rng.choice([-1, 1])
        abr = _abr_at(rec["date"], it.get("t0") or w0)
        d = abr * rng.uniform(3.0, 5.0)
        for k in ("lo", "hi", "price", "p0", "p1"):
            if it.get(k) is not None:
                it[k] += sgn * d
    elif how == "time":                      # stretch (shift in time)
        dt = rng.choice([-120, 120])
        it["t0"] = (it.get("t0") or w0) + dt
        if it.get("t1") is not None:
            it["t1"] += dt
        if it["t0"] < w0 or (it["t1"] or it["t0"]) > w1:
            ok = False
    elif how == "nonpivot":                  # spike-free re-anchor
        if it.get("kind") not in PL.GOLD_LINE_T:
            ok = False
        else:
            _t, m, _o, h, l, _c = CA.bars(rec["date"])
            j0 = int(np.searchsorted(m, it["t0"]))
            j1 = int(np.searchsorted(m, it["t1"] or it["t0"]))
            j0, j1 = min(j0, len(m) - 1), min(j1, len(m) - 1)
            it["p0"] = float((h[j0] + l[j0]) / 2) * PIP
            it["p1"] = float((h[j1] + l[j1]) / 2) * PIP
    else:                                    # trendbox
        _t, m, _o, h, l, _c = CA.bars(rec["date"])
        bw = PL._trend_window(m, l, h, w0, w1)
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
    if it.get("t0") is not None and it["t0"] > tau:
        ok = False                       # drawn only right of tau
    return it, ok


def retag_item(it, rec, tau):
    """Re-tag a mutated item under the identical rule: wrap the
    mutated geometry in an Obj-shaped namespace and run the same
    TT.object_stats/tags_from_stats the engine would."""
    _t, m, _o, _h, _l, _c = CA.bars(rec["date"])
    m = np.asarray(m)
    e = DM.pickled(rec["date"], tau)
    if e is None:
        return None, set()
    nfed = len(e.bars) - 1

    def j_of(tmin):
        return max(0, min(int(np.searchsorted(m, tmin)), len(m) - 1))

    k = it["kind"]
    geom = {}
    if it.get("lo") is not None:
        geom["bottom"], geom["top"] = it["lo"] / PIP, it["hi"] / PIP
    if it.get("price") is not None:
        geom["price"] = it["price"] / PIP
        if it.get("side"):
            geom["side"] = it["side"]
    if it.get("p0") is not None:
        geom["p0"] = it["p0"] / PIP
    if it.get("slope") is not None:
        geom["slope"] = it["slope"] / PIP
        geom["t0"] = it.get("t0_bar") or j_of(it["t0"])
    elif it.get("p1") is not None and it.get("p0") is not None:
        j0, j1 = j_of(it["t0"]), j_of(it["t1"] or it["t0"])
        if j1 > j0:
            geom["slope"] = (it["p1"] - it["p0"]) / PIP / (j1 - j0)
            geom["t0"] = j0
    ob = type("Ob", (), {"type": k, "geometry": geom,
                         "t_left": j_of(it["t0"]),
                         "t_right": j_of(it["t1"] or it["t0"]),
                         "t_birth": j_of(it["t0"]),
                         "state": "ACTIVE", "events": []})
    ff, st = TT.object_stats(ob, nfed, e.bars, e.ema, e.abr,
                             e.book.seq)
    if ff is None:
        return None, set()
    return ff, TT.tags_from_stats(ff, st)


# ------------------------------------------------------------------ #
# render — ceiling sheet (bars<=tau) + trade-view background + item
# ------------------------------------------------------------------ #

def render_pack_item(rec, tau, item, bg_exclude_ids, png, axjson):
    """Base sheet stops bars at tau; background = engine objects at
    tau under drop_tagged (box_broken faded+truncated, R83 s83.6);
    item blue clipped at tau; now-line on top.  Returns True when
    the item drew."""
    t0 = item.get("t0")
    if t0 is not None and t0 > tau:
        return False                 # span entirely right of tau
    axis = CR.render_sheet(rec, tau, png, axjson)
    if axis is None:
        return False
    ax = json.load(open(axjson, encoding="utf8"))
    vm = R.VMap(ax["time_map"]["t_lo"], ax["time_map"]["t_hi"],
                ax["price_map"]["p_lo"], ax["price_map"]["p_hi"])
    tau_x = ax["tau_x"]
    _t, m, _o, h, l, _c = CA.bars(rec["date"])
    m = np.asarray(m)
    e = DM.pickled(rec["date"], tau)
    objs = []
    abr_tau = 5.0
    i_tau = int(np.searchsorted(m, tau, "right")) - 1
    if e is not None:
        i_tau = len(e.bars) - 1
        abr_tau = float(np.asarray(e.abr)[-1]) if len(e.abr) else 5.0
        for ob in e.objects:
            if ob.state == "DELETED":
                continue
            od = RRV.norm_engine(ob)
            _ff, st = TT.object_stats(ob, i_tau, e.bars, e.ema,
                                      e.abr, e.book.seq)
            tags = TT.tags_from_stats(_ff, st) if _ff else set()
            if tags:
                ttf = {"tags": sorted(tags)}
                if "box_broken" in tags:      # R83 s83.6 fade facts
                    ttf["exit_bar"] = st.get("exit_bar")
                    ttf["break_clause"] = st.get("break_clause")
                od["facts"] = {"trade_tags": ttf}
            objs.append(od)
    objs = [od for od in objs if od.get("id") not in bg_exclude_ids]
    im = Image.open(png).convert("L")
    dr = ImageDraw.Draw(im)
    RRV.draw_objects(dr, vm, objs, m, h, l, abr_tau, i_tau, tau_x,
                     drop_tagged=True, fade_broken=True)
    im = im.convert("RGB")          # int-ink code done; item is blue
    dr = ImageDraw.Draw(im)
    it = dict(item)
    if it.get("price") is None and it.get("p0") is None \
            and it.get("lo") is None and it.get("t0") is not None:
        # price-less span item (BRACKET etc): derive the mark's level
        # from the formation extreme over the DRAWN span [t0, tau]
        # (plausibility.render_item semantics, clipped at tau).
        sm = (m >= it["t0"]) & (m <= min(it.get("t1") or it["t0"], tau))
        if sm.any():
            side = it.get("side") or (
                "above" if (it.get("letter") or "M")
                in ("M", "Mm", "SHS") else "below")
            # bars h/l are pips; item prices are raw -> convert once
            ex = (float(np.asarray(h)[sm].max())
                  if side == "above"
                  else float(np.asarray(l)[sm].min()))
            it["price"] = (ex + (4 if side == "above" else -4)) * PIP
    drew = RRV.draw_item(dr, vm, it, tau_x, m)
    dr.rectangle([int(tau_x) + 2, vm.y0 + 1, vm.x1 - 1, vm.y1 - 1],
                 fill=(255, 255, 255))
    R._dash_v(dr, tau_x, vm.y0, vm.y1, (0, 0, 0), 6, 4)
    im.save(png)
    return bool(drew)


# ------------------------------------------------------------------ #
# sampling
# ------------------------------------------------------------------ #

def _largest_remainder(total, shares):
    """{fam: n} proportional allocation summing to total."""
    s = sum(shares.values())
    raw = {f: (total * shares.get(f, 0) / s if s else 0)
           for f in shares}
    out = {f: int(v) for f, v in raw.items()}
    rem = total - sum(out.values())
    for f in sorted(raw, key=lambda f: -raw[f] % 1)[:rem]:
        out[f] += 1
    return out


def sample_engine(pool, rng):
    """30 items: fam floor for box/level/line, rest proportional to
    tradeable pool share; <=1/panel/family."""
    byfam = collections.defaultdict(list)
    for row in pool.values():
        byfam[row["fam"]].append(row)
    quota = {f: FAM_FLOOR.get(f, 0) for f in byfam}
    rest = N_ENGINE - sum(quota.values())
    extra = _largest_remainder(rest, {f: len(v)
                                      for f, v in byfam.items()})
    for f in quota:
        quota[f] += extra[f]
    items, used = [], set()
    leftover = []
    for f in sorted(byfam):
        sub = list(byfam[f])
        rng.shuffle(sub)
        take = []
        for row in sub:
            k = (row["panel"], f)
            if len(take) < quota[f] and k not in used:
                take.append(row)
                used.add(k)
            else:
                leftover.append((f, row))
        items += take
    # shortfall: redistribute from leftovers (dedupe still enforced)
    if len(items) < N_ENGINE:
        rng.shuffle(leftover)
        for f, row in leftover:
            k = (row["panel"], f)
            if len(items) >= N_ENGINE:
                break
            if k not in used:
                items.append(row)
                used.add(k)
    return items[:N_ENGINE]


def sample_golden(pool, rng):
    """10 items stratified by family; <=1/panel/family."""
    byfam = collections.defaultdict(list)
    for row in pool.values():
        byfam[row["fam"]].append(row)
    quota = _largest_remainder(N_GOLD,
                               {f: len(v) for f, v in byfam.items()})
    items, used = [], set()
    leftover = []
    for f in sorted(byfam):
        sub = list(byfam[f])
        rng.shuffle(sub)
        take = []
        for row in sub:
            k = (row["panel"], f)
            if len(take) < quota[f] and k not in used:
                take.append(row)
                used.add(k)
            else:
                leftover.append((f, row))
        items += take
    if len(items) < N_GOLD:
        rng.shuffle(leftover)
        for f, row in leftover:
            k = (row["panel"], f)
            if len(items) >= N_GOLD:
                break
            if k not in used:
                items.append(row)
                used.add(k)
    return items[:N_GOLD]


def sample_negatives(pool, rec_by_id, rng):
    """10 mutated tradeable engine objects, <=1/panel/family."""
    srcs = list(pool.values())
    rng.shuffle(srcs)
    items, used = [], set()
    hows = ["price", "time", "nonpivot", "trendbox"]
    for row in srcs:
        if len(items) >= N_NEG:
            break
        k = (row["panel"], row["fam"])
        if k in used:
            continue
        rec = rec_by_id[row["panel"]]
        how = hows[len(items) % len(hows)]
        it, ok = mutate_item(row["item"], rec, how, rng, row["tau"])
        if not ok:
            for how in hows:
                it, ok = mutate_item(row["item"], rec, how, rng,
                                     row["tau"])
                if ok:
                    break
        if not ok:
            continue
        _ff, tags = retag_item(it, rec, row["tau"])
        items.append({"panel": row["panel"], "date": row["date"],
                      "fam": row["fam"], "item": it, "tau": row["tau"],
                      "tags": sorted(tags), "src_type": it["kind"],
                      "src_obj_id": row["obj_id"],
                      "how": how})
        used.add(k)
    return items


# ------------------------------------------------------------------ #
# main — ONE governed run (post-R83 + plan approval only)
# ------------------------------------------------------------------ #

def main():
    global OUT, ITEMS, KEYDIR, GEOM_SIDECAR, AXDIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None,
                    help="scratch output root (validation runs only)")
    ap.add_argument("--governed", action="store_true",
                    help="write the real owner_pack — ONE run, only "
                         "after all s83.7 gates hold")
    ap.add_argument("--limit", type=int, default=0,
                    help="render only the first N manifest items")
    args = ap.parse_args()
    if args.governed and args.out:
        raise SystemExit("--governed and --out are mutually exclusive")
    if args.out:
        OUT = os.path.abspath(args.out)
        ITEMS = os.path.join(OUT, "items")
        KEYDIR = os.path.join(OUT, "_key")
        GEOM_SIDECAR = os.path.join(OUT, "geom_sidecar.jsonl")
        AXDIR = os.path.join(OUT, "_ax")
    elif not args.governed:
        print("DRY RUN (no --out, no --governed): pools + sample "
              "only, nothing is written.")

    rng = random.Random(SEED)
    recs = [r for r in C.load_tune()
            if r["id"] not in EXCLUDE_PANELS]
    rec_by_id = {r["id"]: r for r in recs}

    epool = engine_pool(recs)
    print("engine pool: %d" % len(epool),
          dict(collections.Counter(v["fam"] for v in epool.values())))
    gpool = golden_pool(recs)
    print("golden pool: %d" % len(gpool),
          dict(collections.Counter(v["fam"] for v in gpool.values())))

    eng_items = sample_engine(epool, rng)
    gold_items = sample_golden(gpool, rng)
    neg_items = sample_negatives(epool, rec_by_id, rng)
    print("sampled: engine %d golden %d negative %d"
          % (len(eng_items), len(gold_items), len(neg_items)))
    print("engine fam:", dict(collections.Counter(
        r["fam"] for r in eng_items)))

    manifest = ([{"src": "engine", **r} for r in eng_items]
                + [{"src": "golden", **r} for r in gold_items]
                + [{"src": "negative", **r} for r in neg_items])
    rng.shuffle(manifest)
    if args.limit:
        manifest = manifest[:args.limit]
    if not (args.out or args.governed):
        print("dry-run manifest order:",
              [(r["src"], r["fam"], r["panel"]) for r in manifest[:8]],
              "...")
        return

    os.makedirs(ITEMS, exist_ok=True)
    os.makedirs(KEYDIR, exist_ok=True)
    os.makedirs(AXDIR, exist_ok=True)
    key, pub, geom_side = {}, [], []
    n_undrawn = 0
    answers = ["# ANSWERS — điền yes / no / cant_tell sau mỗi mã\n"]
    for i, row in enumerate(manifest):
        iid = "p%03d" % (i + 1)
        rec = rec_by_id[row["panel"]]
        png = os.path.join(ITEMS, iid + ".png")
        axj = os.path.join(AXDIR, iid + ".json")
        excl = {row["obj_id"]} if row["src"] == "engine" else \
            ({row["src_obj_id"]} if row["src"] == "negative" else set())
        drew = render_pack_item(rec, row["tau"], row["item"], excl,
                                png, axj)
        if not drew:
            print("  WARN undrawable:", iid, row["src"], row["fam"])
            n_undrawn += 1
        truth = ("engine_hit" if row["src"] == "engine" and
                 row.get("hit") else
                 "engine_fp" if row["src"] == "engine" else
                 "golden" if row["src"] == "golden" else "negative")
        key[iid] = {"truth": truth, "family": row["fam"],
                    "src_type": row.get("src_type"),
                    "panel": row["panel"], "tau": row["tau"],
                    "tags": row.get("tags"),
                    "obj_id": row.get("obj_id") or row.get("src_obj_id"),
                    "how": row.get("how"), "engine": ENGINE_DESC}
        pub.append({"seq": iid, "png": "items/%s.png" % iid})
        it = row["item"]
        geom_side.append({"seq": iid, "family": row["fam"],
                          "kind": it.get("kind"), "t0": it.get("t0"),
                          "t1": it.get("t1"), "lo": it.get("lo"),
                          "hi": it.get("hi"), "price": it.get("price"),
                          "p0": it.get("p0"), "p1": it.get("p1"),
                          "slope": it.get("slope")})
        answers.append("- %s: " % iid)

    with open(os.path.join(KEYDIR, "m2_tv_key.json"), "w",
              encoding="utf8") as fh:
        json.dump({"pack": "M2-TV", "engine": ENGINE_DESC,
                   "seed": SEED,
                   "mix": "30 engine tradeable + 10 golden + 10 neg",
                   "key": key}, fh, indent=1)
    with open(os.path.join(OUT, "manifest.jsonl"), "w",
              encoding="utf8") as fh:
        for r in pub:
            fh.write(json.dumps(r) + "\n")
    open(os.path.join(OUT, "ANSWERS.md"), "w",
         encoding="utf8").write("\n".join(answers) + "\n")
    open(os.path.join(OUT, "HUONG_DAN.md"), "w",
         encoding="utf8").write(INSTR)
    with open(GEOM_SIDECAR, "w", encoding="utf8") as fh:
        for r in geom_side:
            fh.write(json.dumps(r) + "\n")
    print("wrote %d items -> %s | key -> %s | undrawn %d"
          % (len(pub), OUT, KEYDIR, n_undrawn))
    if n_undrawn:
        print("PACK INVALID: %d undrawable items" % n_undrawn)


if __name__ == "__main__":
    main()
