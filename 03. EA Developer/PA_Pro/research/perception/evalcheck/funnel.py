"""funnel.py — proposal-to-birth funnel + oracle ceiling (mandate 2 item 1).

For engine v0 and v1, on all 198 TUNE panels:

  * label every cand_log candidate (born or not) and every born object
    with the golden object it matches under eval_v2 rules, or null;
  * per type: oracle ceiling (recall if selection were perfect), born
    recall, and the gap;
  * per golden object: a miss-taxonomy label;
  * BOX-family route diagnostic (item 2): for every golden x born pair
    passing the edge test, containment IoU + overlap coefficient
    (intersection / shorter window), classified nested-same-episode
    (>=0.5) / partial (>0) / disjoint (0).

Candidate -> engine-record conversion (documented in FUNNEL.md):
  span    = [t_left or t0, t1 or idx]   (proposal-time window, bar idx)
  box win = same span                   (a candidate IS the buildup)
  edges   = lo/hi or bottom/top         (already pip-scale)
  line    = p0, slope, t0_bar = t0      (same convention as born lines)
  level   = price, side
  bracket = t0, t1, letter
  label   = cet_min mark (t_birth), price, side
  marker  = t0..t1 point, price, side
Everything clipped to [w0, w1] exactly like eval_v2.eng_objects.

Labels file: labels_<enginehash>.jsonl — one row per candidate and per
born object.  Re-run when the engine hash changes (--engine-hash-check).

Usage: python evalcheck/funnel.py [--engine v0|v1|both] [--limit N]
       [--engine-hash-check HASH]
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
import eval_v2 as V2                            # noqa: E402
import pa_slots                                 # noqa: E402

PERC = C.PERC
PIP = EV.PIP

V1_FILES = ["engine.py", "swings.py", "boxes.py", "lines.py",
            "levels.py", "patterns.py", "salience.py", "gates.py",
            "cet.py", "kernel.py", "objects.py", "pipes.py",
            "trade_tags.py", "params_v1_1.json"]
V0_FILES = ["engine_v0.py", "params_v1.json"]


def code_hash(files):
    h = hashlib.sha256()
    for f in files:
        h.update(f.encode())
        h.update(open(os.path.join(PERC, f), "rb").read())
    return h.hexdigest()[:16]


# ------------------------------------------------------------------ #
# candidate -> engine record
# ------------------------------------------------------------------ #

def cand_as_record(c, m, w0, w1):
    """One cand_log entry -> an eval_v2 engine record (or None)."""
    idx = c.get("idx")
    if idx is None:
        return None
    t0 = c.get("t0", c.get("t_left", idx))
    t1 = c.get("t1", idx)
    t0m, t1m = V2._min(m, t0), V2._min(m, t1)
    if t1m < w0 or t0m > w1:
        return None
    r = {"type": c["kind"], "why": c.get("route"),
         "t0": max(t0m, w0), "t1": min(t1m, w1),
         "t0_raw": t0m, "t1_raw": t1m,
         "t_birth": V2._min(m, idx),
         "id": "c%d" % idx, "events": [], "w0": w0, "w1": w1,
         "cand_idx": idx, "outcome": c.get("outcome")}
    lo = c.get("lo", c.get("bottom"))
    hi = c.get("hi", c.get("top"))
    if lo is not None and hi is not None:
        r["lo"], r["hi"] = lo, hi
    if c.get("price") is not None:
        r["price"], r["side"] = c["price"], c.get("side")
    if c.get("p0") is not None:
        r["p0"] = c["p0"]
        r["slope"] = c["slope"]
        r["t0_bar"] = c.get("t0", 0)
        r["side"] = c.get("side")
        r["dirn"] = 1 if c["slope"] > 0.05 else \
            (-1 if c["slope"] < -0.05 else 0)
    if c.get("letter") is not None:
        r["letter"] = c["letter"]
    # proposal-time window doubles as the containment window
    r["bs"] = t0m
    r["be"] = t1m
    return r


def cand_as_mark(c, m, w0, w1):
    t = c.get("cet_min")
    if t is None:
        t = V2._min(m, c.get("idx", 0))
    if t < w0 or t > w1:
        return None
    return {"type": "LABEL_TF", "t_birth": t, "price": c.get("price"),
            "side": c.get("side"), "letter": c.get("letter"),
            "why": c.get("route"),
            "cand_idx": c.get("idx"), "outcome": c.get("outcome")}


# ------------------------------------------------------------------ #
# golden keys + per-panel assembly
# ------------------------------------------------------------------ #

def gold_with_keys(rec):
    gobjs, n_un, n_to = EV.gold_objects(rec)
    w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
    for g in gobjs:
        if g.get("t0") is None:
            g["t0"] = w0
        if g.get("t1") is None:
            g["t1"] = w1
    keys = {}
    ctr = collections.Counter()
    for i, g in enumerate(gobjs):
        ctr[g["spec_type"]] += 1
        keys[i] = "%s/%s#%d" % (rec["id"], g["spec_type"],
                                ctr[g["spec_type"]])
    gmarks = EV.gold_marks(rec)
    mkeys = {}
    ctr.clear()
    for i, gm in enumerate(gmarks):
        ctr["LABEL_TF"] += 1
        mkeys[i] = "%s/LABEL_TF!%d" % (rec["id"], ctr["LABEL_TF"])
    return gobjs, gmarks, keys, mkeys


def edges_pass(g, e):
    """The BOX-family edge test alone (both edges within tol)."""
    if C.is_time_only(g) or g.get("price_lo") is None \
            or e.get("lo") is None:
        return None                         # no edge evidence
    tol = V2.tol_px(g)
    return abs(e["lo"] - g["price_lo"] / PIP) <= tol and \
        abs(e["hi"] - g["price_hi"] / PIP) <= tol


def cand_right(g, r, m):
    """R11 §11.2 prefix-consistent 'right proposal' test.  A candidate
    proposed at bar i is judged on what it knew SO FAR — its window is
    the buildup prefix, so full containment IoU would bias the oracle
    low.  Rules per family (i = proposal minute, r["t_birth"]):
      BOX:   both edges within tol AND candidate start within 2*sig_t
             (20 min) of g.build_start (fallback t0) AND
             i <= g.build_end + sig_t;
      line:  the eval_v2 two-point check on the SHARED span AND
             i <= g.t1;
      level: price within tol AND i inside g's span;
      other families: the ruler unchanged.
    """
    gt = g["spec_type"]
    if EV.FAMILY.get(gt) != EV.FAMILY.get(r["type"]):
        return False
    i_min = r.get("t_birth")
    ts = C.TIME_SIGMA_MIN
    if gt in V2.BOX_TYPES:
        if edges_pass(g, r) is not True:
            return False
        gbs = g.get("build_start")
        if gbs is None:
            gbs = g.get("t0")
        gbe = g.get("build_end")
        if gbe is None:
            gbe = g.get("t1")
        if gbs is None or gbe is None or i_min is None:
            return False
        return abs(r["t0"] - gbs) <= 2 * ts and i_min <= gbe + ts
    if gt in V2.LINE_TYPES:
        if i_min is not None and g.get("t1") is not None \
                and i_min > g["t1"]:
            return False
        g0, g1 = g.get("t0"), g.get("t1")
        if g0 is None:
            return False
        if g1 is None:
            g1 = g0
        a, b = max(r["t0"], g0), min(r["t1"], g1)
        if a > b:
            return False
        p0g, p1g = g.get("price0"), g.get("price1")
        if C.is_time_only(g) or p0g is None or p1g is None \
                or r.get("p0") is None:
            gd = {"up": 1, "down": -1}.get(g.get("dir"))
            return gd is None or gd == r.get("dirn")
        tol_l = V2.tol_px(g) + \
            abs((p1g - p0g) / PIP / max(g1 - g0, 1)) * ts
        ok_a = abs(V2._eng_line_at(r, a, m)
                   - V2._gold_line_at(g, a)) <= tol_l
        if a == b:
            return ok_a
        return ok_a and abs(V2._eng_line_at(r, b, m)
                            - V2._gold_line_at(g, b)) <= tol_l
    if gt in V2.LEVEL_TYPES:
        g0, g1 = g.get("t0"), g.get("t1")
        if g0 is None or i_min is None:
            return False
        if g1 is None:
            g1 = g0
        if not (g0 <= i_min <= g1):
            return False
        if g.get("price") is None or r.get("price") is None \
                or C.is_time_only(g):
            return True
        return abs(r["price"] - g["price"] / PIP) <= V2.tol_px(g)
    return V2.match_detail(g, r, m)[0]


def best_cand_match(r, g2, m):
    """Best golden index a candidate is a right proposal for (R11)."""
    best, bs = None, 0.0
    for j, g in enumerate(g2):
        if cand_right(g, r, m):
            s = V2.score(g, r)
            if s > bs:
                best, bs = j, s
    return best


# ------------------------------------------------------------------ #
# per-panel funnel
# ------------------------------------------------------------------ #

def funnel_panel(rec, cls):
    w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
    t, m, o, h, l, c = EV.day_bars(rec["date"])
    e = EV.run_engine(cls, m, t, o, h, l, c, w1, w0=w0)

    gobjs, gmarks, gkeys, gmkeys = gold_with_keys(rec)
    g2i = [i for i, g in enumerate(gobjs)
           if V2.scorable(g, w0, w1)]
    gm2i = [i for i, gm in enumerate(gmarks)
            if V2.scorable_mark(gm, w0, w1)]

    eobjs = V2.eng_objects(e, m, w0, w1)
    emarks = [r for r in eobjs if r["type"] == "LABEL_TF"]
    eboxes = [r for r in eobjs if r["type"] != "LABEL_TF"]

    cands = []                                # converted candidates
    for k, cd in enumerate(e.cand_log or []):
        if cd["kind"] == "LABEL_TF":
            r = cand_as_mark(cd, m, w0, w1)
        else:
            r = cand_as_record(cd, m, w0, w1)
        if r is not None:
            r["cand_seq"] = k
            cands.append(r)
    cmarks = [r for r in cands if r["type"] == "LABEL_TF"]
    cboxes = [r for r in cands if r["type"] != "LABEL_TF"]

    g2 = [gobjs[i] for i in g2i]
    gm2 = [gmarks[i] for i in gm2i]
    pairs, mpairs = C.match_panel(g2, eboxes, gm2, emarks, m,
                                V2.match, V2.match_mark, V2.score)
    born_hit_g = {g2i[gi] for gi, _ in pairs}
    gm_idx = {id(gm2[j]): gm2i[j] for j in range(len(gm2))}
    born_hit_gm = {gm_idx[id(gm)] for gm, _em in mpairs}
    born_pair = {}                            # eobj idx -> golden key
    for gi, ei in pairs:
        born_pair[ei] = gkeys[g2i[gi]]

    # ---- labels: born objects --------------------------------------
    obj_labels = []
    for ei, er in enumerate(eboxes):
        if ei in born_pair:
            lab, rt = born_pair[ei], "assigned"
        else:
            bj, rt = best_match_in(er, g2, m)
            lab = gkeys[g2i[bj]] if bj is not None else None
            rt = rt if bj is not None else None
        obj_labels.append({"src": "obj", "id": er.get("id"),
                           "kind": er["type"], "label": lab,
                           "route": rt, "t0": er["t0"], "t1": er["t1"]})
    for ei, er in enumerate(emarks):
        lab = None
        for mi in gm2i:
            if V2.match_mark(gmarks[mi], er):
                lab = gmkeys[mi]
                break
        obj_labels.append({"src": "obj", "id": er.get("id"),
                           "kind": "LABEL_TF", "label": lab,
                           "route": "mark" if lab else None,
                           "t0": er.get("t_birth"), "t1": None})

    # ---- labels: candidates -----------------------------------------
    cand_labels = []
    for r in cands:
        if r["type"] == "LABEL_TF":
            lab = None
            for mi in gm2i:
                if V2.match_mark(gmarks[mi], r):
                    lab = gmkeys[mi]
                    break
            cand_labels.append({"src": "cand", "cand_seq": r["cand_seq"],
                                "kind": "LABEL_TF", "label": lab,
                                "outcome": r["outcome"],
                                "route": r["why"], "t0": r["t_birth"],
                                "t1": None})
            continue
        bj = best_cand_match(r, g2, m)
        cand_labels.append({"src": "cand", "cand_seq": r["cand_seq"],
                            "kind": r["type"],
                            "label": gkeys[g2i[bj]] if bj is not None
                            else None,
                            "match_route": "r11_prefix" if bj is not None
                            else None,
                            "outcome": r["outcome"], "route": r["why"],
                            "t0": r["t0"], "t1": r["t1"]})

    # ---- miss taxonomy per golden object -----------------------------
    ts = C.TIME_SIGMA_MIN
    miss_rows = []
    for i in g2i:
        g = gobjs[i]
        gk = gkeys[i]
        if i in born_hit_g:
            miss_rows.append({"gold": gk, "type": g["spec_type"],
                              "cat": "matched"})
            continue
        fam = EV.FAMILY.get(g["spec_type"])
        same_born = [er for er in eboxes
                     if EV.FAMILY.get(er["type"]) == fam]
        same_cand = [r for r in cands
                     if r["type"] != "LABEL_TF"
                     and EV.FAMILY.get(r["type"]) == fam]
        prop_match = [r for r in same_cand if cand_right(g, r, m)]
        born_edge = [(er, edges_pass(g, er)) for er in same_born]
        born_edge_ok = [er for er, ok in born_edge if ok]
        cat, why = None, ""
        if prop_match:
            refus = collections.Counter(r["outcome"] for r in prop_match)
            if "born" in refus:
                cat = "born_unassigned"      # born twin exists but lost
                why = "assignment"
            else:
                cat = "proposed_not_born"
                why = "|".join("%s:%d" % kv for kv in refus.items())
        elif born_edge_ok:
            wg = V2._gold_window(g)
            disj = early = False
            for er in born_edge_ok:
                we = V2._eng_window(er)
                ov = V2._overlap(we[0], we[1], wg[0], wg[1])
                if ov <= 0:
                    disj = True
                elif we[1] < wg[1] - 2 * ts:
                    early = True
            if disj:
                cat, why = "born_diff_episode", "containment disjoint"
            elif early:
                cat, why = "born_closed_early", "engine end < build_end"
        if cat is None:
            if same_cand:
                cat = "proposed_wrong_geometry"
            elif same_born:
                cat = "born_wrong_geometry"
            else:
                cat = "never_proposed"
        miss_rows.append({"gold": gk, "type": g["spec_type"], "cat": cat,
                          "why": why,
                          "n_cand_samefam": len(same_cand),
                          "n_born_samefam": len(same_born)})
    for i in gm2i:
        gm = gmarks[i]
        gk = gmkeys[i]
        if i in born_hit_gm:
            miss_rows.append({"gold": gk, "type": "LABEL_TF",
                              "cat": "matched"})
            continue
        if any(V2.match_mark(gm, r) for r in cmarks):
            cat = "proposed_not_born"
        elif any(r["type"] == "LABEL_TF" for r in cmarks):
            cat = "proposed_wrong_geometry"
        else:
            cat = "never_proposed"
        miss_rows.append({"gold": gk, "type": "LABEL_TF", "cat": cat})

    # ---- BOX route diagnostic ----------------------------------------
    box_pairs = []
    for i in g2i:
        g = gobjs[i]
        if g["spec_type"] not in V2.BOX_TYPES:
            continue
        wg = V2._gold_window(g)
        for er in eboxes:
            if EV.FAMILY.get(er["type"]) != "box":
                continue
            ep = edges_pass(g, er)
            if ep is not True:
                continue
            we = V2._eng_window(er)
            inter = V2._overlap(we[0], we[1], wg[0], wg[1])
            shorter = max(min(we[1] - we[0], wg[1] - wg[0]), 1)
            oc = inter / shorter
            iou = V2.iou_true(we[0], we[1], wg[0], wg[1])
            cls_ = "disjoint" if oc == 0 else \
                ("nested" if oc >= 0.5 else "partial")
            box_pairs.append({"panel": rec["id"], "gold": gkeys[i],
                              "eng_id": er.get("id"),
                              "wg": list(wg), "we": list(we),
                              "iou": round(iou, 3), "ovcoef": round(oc, 3),
                              "cls": cls_})

    return {"id": rec["id"], "obj_labels": obj_labels,
            "cand_labels": cand_labels, "miss": miss_rows,
            "box_pairs": box_pairs,
            "n_gold": len(g2i) + len(gm2i), "n_eng": len(eobjs)}


def best_match_in(e, g2, m):
    """Best golden index matching engine record e (or None, route)."""
    best, route, bs = None, None, 0.0
    for j, g in enumerate(g2):
        ok, rt = V2.match_detail(g, e, m)
        if ok:
            s = V2.score(g, e)
            if s > bs:
                best, route, bs = j, rt, s
    return best, route


# ------------------------------------------------------------------ #
# driver
# ------------------------------------------------------------------ #

def run_engine_set(tag, cls, recs, out_dir):
    oracle = collections.Counter()            # type -> golden w/ cand match
    born = collections.Counter()              # type -> golden w/ born match
    denom = collections.Counter()
    miss = collections.Counter()
    whys = collections.defaultdict(collections.Counter)
    box_cls = collections.Counter()
    box_examples = collections.defaultdict(list)
    labels_path = os.path.join(out_dir, "labels_%s.jsonl" % tag)
    lf = open(labels_path, "w", encoding="utf8")
    for k, rec in enumerate(recs):
        r = funnel_panel(rec, cls)
        for row in r["obj_labels"] + r["cand_labels"]:
            row2 = dict(row); row2["panel"] = r["id"]
            lf.write(json.dumps(row2) + "\n")
        g_matched_by_cand = set()
        for cl in r["cand_labels"]:
            if cl["label"]:
                g_matched_by_cand.add(cl["label"])
        for mrow in r["miss"]:
            ty = mrow["type"]
            denom[ty] += 1
            miss[mrow["cat"]] += 1
            if mrow.get("why"):
                for wpart in mrow["why"].split("|"):
                    whys[ty][wpart.split(":")[0]] += 1
            if mrow["cat"] == "matched":
                born[ty] += 1
            if mrow["gold"] in g_matched_by_cand:
                oracle[ty] += 1
            elif mrow["cat"] == "matched":
                oracle[ty] += 1
        for bp in r["box_pairs"]:
            box_cls[bp["cls"]] += 1
            if len(box_examples[bp["cls"]]) < 8:
                box_examples[bp["cls"]].append(bp)
        if (k + 1) % 50 == 0:
            print("  %s %d/%d" % (tag, k + 1, len(recs)), flush=True)
    lf.close()
    return {"labels": labels_path, "denom": denom, "born": born,
            "oracle": oracle, "miss": miss, "whys": whys,
            "box_cls": box_cls, "box_examples": box_examples}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="both")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--engine-hash-check", default=None)
    args = ap.parse_args()

    import engine as ENG_V1
    import engine_v0 as ENG_V0
    recs = C.load_tune()
    if args.limit:
        recs = recs[:args.limit]

    hashes = {"v0": code_hash(V0_FILES), "v1": code_hash(V1_FILES)}
    if args.engine_hash_check:
        for tag, h in hashes.items():
            print("engine %s current hash %s" % (tag, h))
            exp = os.path.join(HERE, "labels_%s.jsonl" % tag)
            print("  labels file:", os.path.basename(exp),
                  "exists:", os.path.exists(exp))
        if args.engine_hash_check not in hashes.values():
            print("WARNING: %s is not a current engine hash — "
                  "re-run funnel.py" % args.engine_hash_check)
            sys.exit(2)
        print("hash OK")
        return

    engines = (("v0", ENG_V0.PerceptionEngine),
               ("v1", ENG_V1.PerceptionEngine))
    if args.engine != "both":
        engines = [x for x in engines if x[0] == args.engine]

    results = {}
    with pa_slots.slot("evalcheck-funnel", timeout=300):
        for tag, cls in engines:
            out_dir = HERE
            res = run_engine_set(tag + "_" + hashes[tag], cls, recs,
                                 out_dir)
            res["hash"] = hashes[tag]
            results[tag] = res
            print("%s done: labels -> %s" % (tag, res["labels"]))

    doc = ["# FUNNEL — proposal-to-birth funnel, TUNE v2, 198 panels", "",
           "## Candidate -> engine-record conversion",
           "",
           "A cand_log entry has no drawn span; it is converted at its "
           "proposal-time window:",
           "- `span = [t_left or t0, t1 or idx]` bar indices -> minutes, "
           "then clipped to [w0, w1] (same as `eval_v2.eng_objects`);",
           "- the containment window = the same span (`bs..be`): a "
           "candidate IS the buildup observed so far;",
           "- edges `lo/hi` (v0) or `bottom/top` (v1), already pip-scale;",
           "- lines: `p0, slope, t0_bar = t0` — evaluated at minutes via "
           "`searchsorted(m)`, same as born lines;",
           "- levels: `price, side`; brackets: `t0, t1, letter`;",
           "- `LABEL_TF` -> mark record with `t_birth = cet_min`;",
           "- `BAR_MARKER` -> point span `t0..t1`.",
           "",
           "Matching: born objects use `eval_v2.match_detail`/"
           "`match_mark` (the R11 ruler).  Candidates are judged by the "
           "R11 §11.2 prefix-consistent rule (`cand_right`): BOX = both "
           "edges within tol + start within 20 min of build_start + "
           "i <= build_end + 10 min; line = two-point check on the "
           "shared span + i <= t1; level = price within tol + i inside "
           "the golden span.  Born-object labels use the panel's greedy "
           "assignment; candidate labels are pairwise best-match under "
           "that rule.  Miss taxonomy precedence: matched > "
           "proposed_not_born (refusal reason kept) > "
           "born_diff_episode > born_closed_early > "
           "proposed_wrong_geometry > born_wrong_geometry > "
           "never_proposed.",
           ""]
    for tag, res in results.items():
        doc.append("## engine %s (`%s`)" % (tag, res["hash"]))
        doc.append("")
        doc.append("| type | golden | oracle ceiling | born recall | gap |")
        doc.append("|---|---|---|---|---|")
        for ty in sorted(res["denom"]):
            d = res["denom"][ty]
            o = res["oracle"].get(ty, 0)
            b = res["born"].get(ty, 0)
            doc.append("| %s | %d | %.2f (%d) | %.2f (%d) | %.2f |"
                       % (ty, d, o / d, o, b / d, b, (o - b) / d))
        doc.append("")
        doc.append("Miss taxonomy (golden objects): "
                   + ", ".join("%s=%d" % kv
                               for kv in res["miss"].most_common()))
        doc.append("")
        doc.append("BOX pairs passing edge test: "
                   + ", ".join("%s=%d" % kv
                               for kv in res["box_cls"].most_common()))
        doc.append("")
        for cls_ in ("nested", "partial", "disjoint"):
            doc.append("### %s examples" % cls_)
            for bp in res["box_examples"][cls_][:5]:
                doc.append("- `%s` %s golden W=%s engine W=%s "
                           "IoU=%.2f ovcoef=%.2f"
                           % (bp["panel"], bp["gold"], bp["wg"],
                              bp["we"], bp["iou"], bp["ovcoef"]))
            doc.append("")
    open(os.path.join(HERE, "FUNNEL.md"), "w", encoding="utf8").write(
        "\n".join(doc))
    print("wrote FUNNEL.md")


if __name__ == "__main__":
    main()
