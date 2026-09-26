"""e4_bridge.py — Ruling 7 item 4 / mandate E4 (R9/R9a revision).

For engine_v0 and the current engine, on all 198 TUNE panels:

  * Q2-loose coverage  — the measure.py candidate-universe rule
    (span IoU>=0.25 or any-overlap+band within 4p; point kinds: price
    within 4p and birth inside golden span +/-90min), evaluated on the
    engine's cand_log (every evaluated candidate, born or vetoed).
  * strict(pre-R9.1)   — eval.py as shipped at 16:12Z: ACTIVE objects
    stretched to len(m)-1 (day end), no clipping, span "IoU" =
    intersection / max(len).  Replicated by
    eval_v2.eng_objects_pre_r91 + eval.match.
  * strict(now)        — eval.py after the build lane's R9.1 fix
    (ACTIVE -> len(e.bars)-1), same match() and non-true IoU.
  * strict+trueIoU     — eval.py's match() with eval.iou patched to
    intersection / union (R9.2), same conversion as strict(now).
  * eval_v2            — the D9-consistent ruler from this lane
    (frozen clipped conversion + containment-IoU BOX route).

One engine run per panel feeds all five columns.  Also counts panels
where the engine produced no object inside the window, freezes the
sha256 of every engine source file + params actually imported, records
the current eval.py hash, and for BOX reports how many eval_v2 matches
used the containment-IoU route vs the coverage fallback (and how many
of the fallback matches would fail a true containment IoU >= 0.5).

Usage: python evalcheck/e4_bridge.py [--limit N]
Writes: evalcheck/bridge_report.md + evalcheck/_bridge_rows.jsonl
"""
import argparse
import collections
import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2                                  # noqa: E402
import pa_slots                                 # noqa: E402

PERC = C.PERC

# measure.py's loose-matching pieces, reused unmodified
sys.path.insert(0, os.path.join(PERC, "golden"))
import validate as V                            # noqa: E402
from measure import (_TYPE_GROUPS, _POINT_KINDS, _overlap,  # noqa: E402
                     _price_near, _gold_prices, cand_span, cand_band)


# ------------------------------------------------------------------ #
# code fingerprint
# ------------------------------------------------------------------ #

V1_FILES = ["engine.py", "swings.py", "boxes.py", "lines.py",
            "levels.py", "patterns.py", "salience.py", "gates.py",
            "cet.py", "params_v1_1.json"]
V0_FILES = ["engine_v0.py", "params_v1.json"]


def code_hash(files):
    h = hashlib.sha256()
    per = {}
    for f in files:
        p = os.path.join(PERC, f)
        b = open(p, "rb").read()
        per[f] = hashlib.sha256(b).hexdigest()[:16]
        h.update(f.encode())
        h.update(b)
    return h.hexdigest()[:16], per


def file_hash(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


# R11 §11.3: LINE-LAB Tier-A suspect line labels — excluded from tuning
# and AUC work; they stay in the recall denominators, and the trusted
# subset (n=141) is reported alongside.
TIERA = set(json.load(open(os.path.join(HERE, "line_tierA.json"),
                           encoding="utf8")))


# ------------------------------------------------------------------ #
# Q2-loose coverage (measure.py semantics, verbatim logic)
# ------------------------------------------------------------------ #

def q2_hits(cand_log, gold, day):
    """Set of golden indices covered by any evaluated candidate."""
    hits = set()
    for c in cand_log or []:
        m0, m1 = cand_span(day, c)
        mb = c.get("cet_min") or m0
        plo, phi = cand_band(c)
        group = _TYPE_GROUPS.get(c["kind"], (c["kind"],))
        point = c["kind"] in _POINT_KINDS
        best_iou, hit = 0.0, None
        for gi, g in enumerate(gold):
            if g["spec_type"] not in group:
                continue
            gt0 = g.get("t0")
            gt1 = g.get("t1") or gt0
            if gt0 is None:
                continue
            gp = _gold_prices(g)
            pok = _price_near((plo, phi), gp)
            if point:
                iou = 0.0
                ok = (gt0 - 90) <= mb <= (gt1 + 90) and pok
            else:
                iou = _overlap(m0, m1, gt0, gt1)
                ok = iou >= 0.25 or (iou > 0 and pok)
            if ok and (hit is None or iou > best_iou or pok):
                best_iou = max(best_iou, iou)
                hit = gi
        if hit is not None:
            hits.add(hit)
    return hits


# ------------------------------------------------------------------ #
# per-panel driver
# ------------------------------------------------------------------ #

def _tally(gobjs, eobjs, gmarks, emarks, m, matchfn, markfn, scorefn):
    p, mp = C.match_panel(gobjs, eobjs, gmarks, emarks, m,
                          matchfn, markfn, scorefn)
    return C.tally(gobjs, eobjs, gmarks, p, mp), p


def eval_panel_all(rec, cls):
    """Run one engine once; score all ruler columns."""
    w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
    t, m, o, h, l, c = EV.day_bars(rec["date"])
    e = EV.run_engine(cls, m, t, o, h, l, c, w1)

    gobjs, n_un, n_to = EV.gold_objects(rec)
    for g in gobjs:
        if g.get("t0") is None:
            g["t0"] = w0
        if g.get("t1") is None:
            g["t1"] = w1
    gmarks = EV.gold_marks(rec)

    # ---- column: strict(pre-R9.1) — day-end stretch, non-true IoU ---
    eo_pre = eval_v2.eng_objects_pre_r91(e, m, w0, w1)
    emarks = [r for r in eo_pre if r["type"] == "LABEL_TF"]
    t_pre, _ = _tally(gobjs, eo_pre, gmarks, emarks, m,
                      EV.match, EV.match_mark, None)

    # ---- column: strict(now) — post-R9.1 conversion, non-true IoU ---
    eo_now = EV.eng_objects(e, m, w0, w1)
    t_now, _ = _tally(gobjs, eo_now, gmarks, emarks, m,
                      EV.match, EV.match_mark, None)

    # ---- column: strict+trueIoU — same conv, patched iou -----------
    saved_iou = EV.iou
    EV.iou = eval_v2.iou_true
    try:
        t_ti, _ = _tally(gobjs, eo_now, gmarks, emarks, m,
                         EV.match, EV.match_mark, None)
    finally:
        EV.iou = saved_iou

    # ---- column: eval_v2 (frozen clipped conv + D9 semantics) ------
    eo_v2 = eval_v2.eng_objects(e, m, w0, w1)
    emarks2 = [r for r in eo_v2 if r["type"] == "LABEL_TF"]
    g2 = [g for g in gobjs if eval_v2.scorable(g, w0, w1)]
    gm2 = [gm for gm in gmarks if eval_v2.scorable_mark(gm, w0, w1)]
    t_v2, p_v2 = _tally(g2, eo_v2, gm2, emarks2, m,
                        eval_v2.match, eval_v2.match_mark,
                        eval_v2.score)

    # R11 diagnostics: "located" (BOX-family golden with any engine
    # object in the right place/edges — never a match) and the
    # trusted-subset (non-Tier-A) line recall.
    located = collections.Counter()
    loc_den = collections.Counter()
    tg = collections.Counter()
    tm = collections.Counter()
    matched_gi = {gi for gi, _ in p_v2}
    src_idx = [k for k, o in enumerate(rec["objects"])
               if o.get("status") not in EV.EXCLUDED
               and o.get("spec_type")]
    g2_orig = [i for i, g in enumerate(gobjs)
               if eval_v2.scorable(g, w0, w1)]
    for gi, g in enumerate(g2):
        ty = g["spec_type"]
        if ty in eval_v2.BOX_TYPES:
            loc_den[ty] += 1
            if any(eval_v2.box_located(g, eo, m) for eo in eo_v2):
                located[ty] += 1
        if ty in eval_v2.LINE_TYPES:
            oi = src_idx[g2_orig[gi]]
            if "%s#%d" % (rec["id"], oi) not in TIERA:
                tg[ty] += 1
                if gi in matched_gi:
                    tm[ty] += 1

    # BOX route accounting on matched pairs
    routes = collections.Counter()
    cov_would_fail_iou = 0
    for gi, ei in p_v2:
        g, er = g2[gi], eo_v2[ei]
        if g["spec_type"] not in eval_v2.BOX_TYPES:
            continue
        _ok, route = eval_v2.match_detail(g, er, m)
        routes[route] += 1
        if route != "containment_iou":
            wg0, wg1 = eval_v2._gold_window(g)
            we0, we1 = eval_v2._eng_window(er)
            if None not in (wg0, wg1, we0, we1) and wg1 > wg0 \
                    and we1 > we0 and \
                    eval_v2.iou_true(we0, we1, wg0, wg1) < 0.5:
                cov_would_fail_iou += 1

    # ---- column: Q2-loose coverage on the candidate universe --------
    day = V.Day(m, o, h, l, c)
    gold_q2 = [g for g in rec["objects"]
               if g["status"] in ("ok", "repaired", "time_only")]
    for g in gold_q2:                            # same panel-bound fill
        if g.get("t0") is None:
            g["t0"] = w0
        if g.get("t1") is None:
            g["t1"] = w1
    cov = q2_hits(e.cand_log, gold_q2, day)
    q2_by_type = collections.Counter(g["spec_type"] for g in gold_q2)
    q2_hit_type = collections.Counter(gold_q2[i]["spec_type"]
                                      for i in cov)

    return {"id": rec["id"], "pre": t_pre, "strict": t_now,
            "strict_ti": t_ti, "v2": t_v2,
            "q2_den": q2_by_type, "q2_hit": q2_hit_type,
            "routes": routes, "cov_fail_iou": cov_would_fail_iou,
            "located": located, "loc_den": loc_den,
            "trusted_g": tg, "trusted_m": tm,
            "n_eng": len(eo_now), "n_gold": len(gobjs) + len(gmarks),
            "n_un": n_un, "n_to": n_to}


def merge(dst, src):
    for t, d in src.items():
        for k, v in (d.items() if hasattr(d, "items") else []):
            dst[t][k] += v


def rec_cell(tally, ty):
    g, mh = tally[ty]["g"], tally[ty]["m"]
    return "%.2f (%d)" % (mh / g if g else float("nan"), mh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out",
                    default=os.path.join(HERE, "bridge_report.md"))
    args = ap.parse_args()

    import engine as ENG_V1
    import engine_v0 as ENG_V0
    recs = C.load_tune()
    if args.limit:
        recs = recs[:args.limit]

    h1, per1 = code_hash(V1_FILES)
    h0, per0 = code_hash(V0_FILES)
    h_eval = file_hash(os.path.join(PERC, "eval.py"))

    out_rows = open(os.path.join(HERE, "_bridge_rows.jsonl"), "w",
                    encoding="utf8")
    doc = ["# E4 bridge — TUNE v2, 198 panels, five rulers", ""]
    doc.append("engine v1 hash `%s` %s" % (h1, per1))
    doc.append("engine v0 hash `%s` %s" % (h0, per0))
    doc.append("eval.py hash (post-R9.1) `%s`" % h_eval)
    doc.append("eval_v2.py hash (R11 ruler) `%s` ; common.py `%s`"
               % (file_hash(os.path.join(HERE, "eval_v2.py")),
                  file_hash(os.path.join(HERE, "common.py"))))
    doc.append("")
    doc.append("Columns: `pre` = eval.py pre-16:28Z conversion "
               "(ACTIVE -> len(m)-1, day end); `now` = current eval.py "
               "(ACTIVE -> len(e.bars)-1); `now+trueIoU` = same with "
               "intersection/union; `v2` = evalcheck/eval_v2.py "
               "(clipped conversion, D9 containment).")
    doc.append("")

    with pa_slots.slot("evalcheck-e4", timeout=300):
        for tag, cls in (("v0", ENG_V0.PerceptionEngine),
                         ("v1", ENG_V1.PerceptionEngine)):
            T = {k: collections.defaultdict(
                lambda: {"g": 0, "e": 0, "m": 0})
                for k in ("pre", "strict", "strict_ti", "v2")}
            Q2D = collections.Counter()
            Q2H = collections.Counter()
            routes = collections.Counter()
            LOC = collections.Counter()
            LOCD = collections.Counter()
            TG = collections.Counter()
            TM = collections.Counter()
            cov_fail = 0
            empty = 0
            clutter = []
            for k, rec in enumerate(recs):
                r = eval_panel_all(rec, cls)
                for key in T:
                    merge(T[key], r[key])
                Q2D.update(r["q2_den"])
                Q2H.update(r["q2_hit"])
                routes.update(r["routes"])
                LOC.update(r["located"])
                LOCD.update(r["loc_den"])
                TG.update(r["trusted_g"])
                TM.update(r["trusted_m"])
                cov_fail += r["cov_fail_iou"]
                empty += (r["n_eng"] == 0)
                if r["n_gold"]:
                    clutter.append(r["n_eng"] / r["n_gold"])
                out_rows.write(json.dumps(
                    {"engine": tag, "id": r["id"], "n_eng": r["n_eng"]})
                    + "\n")
                if (k + 1) % 25 == 0:
                    print("  %s %d/%d" % (tag, k + 1, len(recs)),
                          flush=True)
            doc.append("## engine %s" % tag)
            doc.append("")
            doc.append("| type | gold | Q2-loose | pre-R9.1 | now |"
                       " now+trueIoU | eval_v2 | located |")
            doc.append("|---|---|---|---|---|---|---|---|")
            types = sorted(set(list(T["strict"]) + list(T["v2"])
                               + list(Q2D)))
            for ty in types:
                gq2 = Q2D.get(ty, 0)
                q2r = Q2H.get(ty, 0) / gq2 if gq2 else float("nan")
                loc = ("%.2f (%d)" % (LOC[ty] / LOCD[ty], LOC[ty])
                       if LOCD.get(ty) else "—")
                doc.append("| %s | %d | %.2f (%d) | %s | %s | %s | %s |"
                           " %s |"
                           % (ty, gq2, q2r, Q2H.get(ty, 0),
                              rec_cell(T["pre"], ty),
                              rec_cell(T["strict"], ty),
                              rec_cell(T["strict_ti"], ty),
                              rec_cell(T["v2"], ty), loc))
            for ty in sorted(TG):
                doc.append("| %s trusted | %d | — | — | — | — |"
                           " %.2f (%d) | — |"
                           % (ty, TG[ty], TM[ty] / TG[ty] if TG[ty]
                              else float("nan"), TM[ty]))
            doc.append("")
            doc.append("- panels with zero engine objects in window: "
                       "**%d / %d**" % (empty, len(recs)))
            doc.append("- clutter ratio median: **%.2f**"
                       % (float(np.median(clutter)) if clutter
                          else float("nan")))
            doc.append("- BOX-family eval_v2 match routes: "
                       + ", ".join("%s=%d" % kv
                                   for kv in sorted(routes.items()))
                       + " ; coverage-route matches failing true "
                         "containment IoU>=0.5: **%d**" % cov_fail
                       + " (R11: coverage allowed only when a side "
                         "recorded no containment window)")
            doc.append("- precision now / v2 (all types): "
                       + "; ".join("%s %.2f/%.2f" % (t,
                                   T["strict"][t]["m"] /
                                   T["strict"][t]["e"]
                                   if T["strict"][t]["e"]
                                   else float("nan"),
                                   T["v2"][t]["m"] / T["v2"][t]["e"]
                                   if T["v2"][t]["e"] else float("nan"))
                                   for t in sorted(T["strict"])))
            doc.append("")
    out_rows.close()
    open(args.out, "w", encoding="utf8").write("\n".join(doc))
    print("wrote", args.out)


if __name__ == "__main__":
    main()
