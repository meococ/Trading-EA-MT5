"""DR_RULES_S2_measure.py — R82 s82.3 "the box ends at the breakout".

Extends DR_RULES_S1_measure / DR_RULES_S1ap_measure (imported; never
forked).  Parent = C-3 canonical caches (623 windows; OFF == C-3).

ARM S2 (fixed, no tuning).  At every golden-decision tau, for every
live box-family object:
  edges = the object's top/bottom as drawn at tau;
  tol   = trade_tags.tol_e (the engine edge tol used by line_broken;
          imported, never re-derived);
  break = the FIRST run of k consecutive bars j..j+k-1, all inside
          [drawn left edge, drawn right edge clipped at tau], whose
          closes are all > top+tol (up) or all < bottom-tol (down);
  close = if the break is confirmed by tau (j+k-1 <= tau) the box is
          CLOSED: removed from the live set BEFORE the budget/ranking
          pick (the next-ranked live box takes the box@1 slot), not
          drawn, not counted.  Sticky by construction (the first run
          stays the first run at every later tau).
Variants: S2-k2 (k=2), S2-k3 (k=3).

Outputs (deepresearch/):
  DR_RULES_S2_events.jsonl   per event: picks/hits baseline/k2/k3
  DR_RULES_S2_rows.jsonl     per live box: break stats + clean flags
  DR_RULES_S2_hits.jsonl     per parent-hit detail under each variant
  DR_RULES_S2_golden.jsonl   author compliance: same rule on golden
                             boxes at their own tau/span/edges
  DR_RULES_S2_prefix.jsonl   20-panel prefix invariance
  DR_RULES_S2_census.jsonl   published census + S2-drawn census /panel
  DR_RULES_S2_review_closed.jsonl  closed boxes on the 12 review panels
  DR_RULES_S2_k2_objects.jsonl / DR_RULES_S2_k3_objects.jsonl
                             G-KIT overrides (engine spelling, base set
                             = review/sets/c3/<panel>.json objects)
"""
import collections
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "boxlab"))

import common as C                      # noqa: E402
import eval as EV                       # noqa: E402
import eval_v2 as V2                    # noqa: E402
import cache as CA                      # noqa: E402
import recall_at_k as RK                # noqa: E402
from snapshot import tau_of, live_records  # noqa: E402
import trade_tags as TT                 # noqa: E402

import DR_RULES_measure as M            # noqa: E402
import DR_RULES_S1_measure as S1M       # noqa: E402
import DR_RULES_S1ap_measure as S1AP    # noqa: E402

FAM_BUDGET = S1M.FAM_BUDGET
BOX_TYPES = S1M.BOX_TYPES
REVIEW_JSON = os.path.join(PERC, "review", "review_panels.json")
C3_SET = os.path.join(PERC, "review", "sets", "c3")
tol_e = TT.tol_e                       # engine edge tol (imported)


def first_break(j0, j1, top, bot, c, abr, k):
    """First run of k consecutive closes beyond the band, all inside
    [j0..j1].  Returns (confirm_bar, side) or (None, None).
    tol_e applied per bar (abr[j]), the line_broken convention."""
    n = j1 - j0 + 1
    if n < k:
        return None, None
    seg = c[j0:j1 + 1]
    tseg = np.array([tol_e(abr[j0 + i]) for i in range(n)])
    up = seg > top + tseg
    dn = seg < bot - tseg
    run = 0
    side = None
    for i in range(n):
        s = "up" if up[i] else ("dn" if dn[i] else None)
        if s is None or s != side:
            run, side = (1, s) if s is not None else (0, None)
        else:
            run += 1
        if run >= k and side is not None:
            return j0 + i, side
    return None, None


def box_break_row(ob, nfed, o, h, l, c, abr):
    """(j0, j1, top, bot, {k: (confirm_bar, side)}) for one live box."""
    j0, j1 = S1AP.eng_box_span(ob, nfed)
    top, bot = ob.geometry["top"], ob.geometry["bottom"]
    br = {}
    for k in (2, 3):
        br[k] = first_break(j0, j1, top, bot, c, abr, k)
    return j0, j1, top, bot, br


def main():
    recs = C.load_tune()
    events = [json.loads(x) for x in open(
        os.path.join(HERE, "DR_RULES_events.jsonl"), encoding="utf8")]
    obj_events = [e for e in events if e["is_tau_event"]]
    rec_by_id = {r["id"]: r for r in recs}

    f_e = open(os.path.join(HERE, "DR_RULES_S2_events.jsonl"), "w",
               encoding="utf8")
    f_r = open(os.path.join(HERE, "DR_RULES_S2_rows.jsonl"), "w",
               encoding="utf8")
    f_h = open(os.path.join(HERE, "DR_RULES_S2_hits.jsonl"), "w",
               encoding="utf8")

    panels_seen = collections.OrderedDict()
    for ev in obj_events:
        panels_seen.setdefault(ev["panel"], []).append(ev)

    for panel, evs in panels_seen.items():
        rec = rec_by_id[panel]
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m_day, _o, _h, _l, _c = CA.bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        gidx = {id(g): i for i, g in enumerate(g2)}
        for ev in evs:
            tau = ev["tau"]
            e = M.pickled(rec["date"], tau)
            if e is None:
                continue
            nfed = len(e.bars) - 1
            m = np.array([b["cet_min"] for b in e.bars])
            o = np.array([b["o"] for b in e.bars])
            h = np.array([b["h"] for b in e.bars])
            l = np.array([b["l"] for b in e.bars])
            c = np.array([b["c"] for b in e.bars])
            ema = np.asarray(e.ema)
            abr = np.asarray(e.abr)
            ggs = [g for g in g2
                   if tau_of(g) is not None and tau_of(g) >= w0
                   and min(tau_of(g), w1) == tau]
            live, _emarks = live_records(e, m_day, w0, tau)
            osc = {ob.id: getattr(ob, "score", None)
                   for ob in e.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            ranked = RK.rank_live(live, RK.score_map(e))
            o_by_id = {ob.id: ob for ob in e.objects}

            rows = []
            for rank, r in enumerate(ranked):
                fam = EV.FAMILY.get(r["type"])
                if fam != "box":
                    continue
                ob = o_by_id.get(r["id"])
                if ob is None or "top" not in ob.geometry:
                    continue
                j0, j1, top, bot, br = box_break_row(
                    ob, nfed, o, h, l, c, abr)
                st0 = S1M.box_stats(bot, top, j0, j1, m, o, h, l, c,
                                    ema, abr)
                rows.append({"rank": rank, "rec": r, "id": r["id"],
                             "j0": j0, "j1": j1, "top": top, "bot": bot,
                             "t_birth": getattr(ob, "t_birth", None),
                             "br2": br[2], "br3": br[3],
                             "closed2": br[2][0] is not None,
                             "closed3": br[3][0] is not None,
                             "st0": st0})

            def pick(arm):
                for row in rows:
                    if arm == "k2" and row["closed2"]:
                        continue
                    if arm == "k3" and row["closed3"]:
                        continue
                    return row["rec"]
                return None

            picks = {"0": rows[0]["rec"] if rows else None,
                     "k2": pick("k2"), "k3": pick("k3")}
            hits, mgis = {}, {}
            for arm, pr in picks.items():
                if pr is None:
                    hits[arm], mgis[arm] = False, []
                    continue
                mgi = [gidx[id(g)] for g in ggs
                       if EV.FAMILY.get(g["spec_type"]) == "box"
                       and V2.match(g, pr, m_day)]
                hits[arm] = bool(mgi)
                mgis[arm] = mgi
            fam_ranked = collections.defaultdict(list)
            for r in ranked:
                fam_ranked[EV.FAMILY.get(r["type"])].append(r)
            nf_hits = {}
            for f, kk in FAM_BUDGET.items():
                if f == "box":
                    continue
                top = fam_ranked[f][:kk]
                nf_hits[f] = sum(
                    1 for g in ggs
                    if EV.FAMILY.get(g["spec_type"]) == f
                    and any(V2.match(g, r, m_day) for r in top))
            f_e.write(json.dumps(
                {"panel": panel, "tau": tau,
                 "n_live_boxes": len(rows),
                 "n_closed2": sum(1 for x in rows if x["closed2"]),
                 "n_closed3": sum(1 for x in rows if x["closed3"]),
                 "nf_hits": nf_hits,
                 "picks": {a: (p["id"] if p else None)
                           for a, p in picks.items()},
                 "hits": hits}) + "\n")

            for row in rows:
                oid = row["id"]
                f_r.write(json.dumps(
                    {"panel": panel, "tau": tau, "id": oid,
                     "rank": row["rank"],
                     "picked0": bool(picks["0"]
                                     and oid == picks["0"]["id"]),
                     "picked_k2": bool(picks["k2"]
                                       and oid == picks["k2"]["id"]),
                     "picked_k3": bool(picks["k3"]
                                       and oid == picks["k3"]["id"]),
                     "matched0": any(
                         V2.match(g, row["rec"], m_day) for g in ggs
                         if EV.FAMILY.get(g["spec_type"]) == "box"),
                     "j0": row["j0"], "j1": row["j1"],
                     "t_birth": row["t_birth"],
                     "br2": row["br2"][0], "br2_side": row["br2"][1],
                     "br3": row["br3"][0], "br3_side": row["br3"][1],
                     "closed2": row["closed2"],
                     "closed3": row["closed3"],
                     "bars_after2": (nfed - row["br2"][0]
                                     if row["br2"][0] is not None
                                     else None),
                     "bars_after3": (nfed - row["br3"][0]
                                     if row["br3"][0] is not None
                                     else None),
                     "clean0": S1M.owner_clean(row["st0"]),
                     "width0": row["st0"]["width_bars"],
                     "c3_0": row["st0"]["c3_r_win"],
                     "c4_0": row["st0"]["c4_r_win"],
                     "c6_0": row["st0"]["c6_maxd"]}) + "\n")

            # ---- per parent-hit detail under each variant ------------
            if hits["0"]:
                pr0 = picks["0"]
                row0 = next(x for x in rows if x["id"] == pr0["id"])
                for gi in mgis["0"]:
                    g = g2[gi]
                    wg = V2._gold_window(g)
                    we0 = V2._eng_window(pr0)
                    es0 = V2._span(pr0)
                    for arm in ("k2", "k3"):
                        pr = picks[arm]
                        closed0 = row0["closed2"] if arm == "k2" \
                            else row0["closed3"]
                        br0 = row0["br2"] if arm == "k2" \
                            else row0["br3"]
                        det = {"panel": panel, "tau": tau, "gi": gi,
                               "arm": arm, "pick0": pr0["id"],
                               "pick": pr["id"] if pr else None,
                               "pick0_closed": bool(closed0),
                               "confirm_bar": br0[0],
                               "confirm_side": br0[1],
                               "bars_before_tau": (nfed - br0[0]
                                                   if br0[0] is not None
                                                   else None),
                               "wg": wg, "we0": we0,
                               "same_pick": (pr is not None
                                             and pr["id"] == pr0["id"]),
                               "fill": (pr is not None
                                        and pr["id"] != pr0["id"]),
                               "cov0": (V2._coverage(*es0, *wg)
                                        if None not in es0 + wg
                                        else None),
                               "iou0": (V2.iou_true(*we0, *wg)
                                        if None not in we0 + wg
                                        else None)}
                        if pr is not None:
                            es1 = V2._span(pr)
                            we1 = V2._eng_window(pr)
                            det["cov1"] = (V2._coverage(*es1, *wg)
                                           if None not in es1 + wg
                                           else None)
                            det["iou1"] = (V2.iou_true(*we1, *wg)
                                           if None not in we1 + wg
                                           else None)
                            det["matched1"] = V2.match(g, pr, m_day)
                        else:
                            det["cov1"] = det["iou1"] = None
                            det["matched1"] = False
                        f_h.write(json.dumps(det) + "\n")
    f_e.close(); f_r.close(); f_h.close()

    # ---------------- author compliance ------------------------------
    f_g = open(os.path.join(HERE, "DR_RULES_S2_golden.jsonl"), "w",
               encoding="utf8")
    n_g = 0
    for panel, evs in panels_seen.items():
        rec = rec_by_id[panel]
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        e_full = M.pickled(rec["date"], w1)
        if e_full is None:
            continue
        m = np.array([b["cet_min"] for b in e_full.bars])
        o = np.array([b["o"] for b in e_full.bars])
        h = np.array([b["h"] for b in e_full.bars])
        l = np.array([b["l"] for b in e_full.bars])
        c = np.array([b["c"] for b in e_full.bars])
        abr = np.asarray(e_full.abr)
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        for g in g2:
            if g["spec_type"] not in BOX_TYPES:
                continue
            tau = tau_of(g)
            if tau is None:
                continue
            t0 = M.to_min(g.get("t0"))
            t1 = M.to_min(g.get("t1"))
            lo = g.get("price_lo")
            hi = g.get("price_hi")
            if t0 is None or lo is None or hi is None:
                continue
            j0 = M.jge(m, t0)
            end_min = min(t1, tau) if t1 is not None else tau
            j1 = M.jle(m, min(end_min, w1))
            if j0 is None or j1 is None or j0 > j1:
                continue
            top, bot = hi * M.PIP, lo * M.PIP
            br2 = first_break(j0, j1, top, bot, c, abr, 2)
            br3 = first_break(j0, j1, top, bot, c, abr, 3)
            f_g.write(json.dumps(
                {"panel": panel, "gi": gidx_note(g2, g), "tau": tau,
                 "j0": j0, "j1": j1,
                 "br2": br2[0], "br2_side": br2[1],
                 "br3": br3[0], "br3_side": br3[1],
                 "closed2": br2[0] is not None,
                 "closed3": br3[0] is not None}) + "\n")
            n_g += 1
    f_g.close()

    # ---------------- prefix invariance (20 panels) ------------------
    f_p = open(os.path.join(HERE, "DR_RULES_S2_prefix.jsonl"), "w",
               encoding="utf8")
    n_pan = 0
    for panel, evs in panels_seen.items():
        if n_pan >= 20:
            break
        n_pan += 1
        rec = rec_by_id[panel]
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        e_full = M.pickled(rec["date"], w1)
        for ev in evs:
            tau = ev["tau"]
            e = M.pickled(rec["date"], tau)
            if e is None or e_full is None:
                continue
            nfed = len(e.bars) - 1
            o = np.array([b["o"] for b in e.bars])
            h = np.array([b["h"] for b in e.bars])
            l = np.array([b["l"] for b in e.bars])
            c = np.array([b["c"] for b in e.bars])
            abr = np.asarray(e.abr)
            o2 = np.array([b["o"] for b in e_full.bars])
            h2 = np.array([b["h"] for b in e_full.bars])
            l2 = np.array([b["l"] for b in e_full.bars])
            c2 = np.array([b["c"] for b in e_full.bars])
            abr2 = np.asarray(e_full.abr)
            ob_full = {ob.id: ob for ob in e_full.objects}
            for ob in e.objects:
                if ob.type not in BOX_TYPES or "top" not in ob.geometry:
                    continue
                ob2 = ob_full.get(ob.id)
                if ob2 is None or ob2.t_left != ob.t_left:
                    continue
                j0, j1 = S1AP.eng_box_span(ob, nfed)
                if j0 > j1:
                    continue
                top, bot = ob.geometry["top"], ob.geometry["bottom"]
                for k in (2, 3):
                    b1 = first_break(j0, j1, top, bot, c, abr, k)[0]
                    b2 = first_break(j0, j1, top, bot, c2, abr2, k)[0]
                    f_p.write(json.dumps(
                        {"panel": panel, "tau": tau, "id": ob.id,
                         "k": k, "br_tau": b1, "br_full": b2,
                         "same": b1 == b2}) + "\n")
    f_p.close()

    # ---------------- census (published + S2-drawn) -------------------
    f_c = open(os.path.join(HERE, "DR_RULES_S2_census.jsonl"), "w",
               encoding="utf8")
    for panel, evs in panels_seen.items():
        rec = rec_by_id[panel]
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m_day, _o, _h, _l, _c = CA.bars(rec["date"])
        e = M.pickled(rec["date"], w1)
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        eobjs = V2.eng_objects(e, m_day, w0, w1) if e is not None else []
        eboxes = [r for r in eobjs if r["type"] != "LABEL_TF"]
        emarks = [r for r in eobjs if r["type"] == "LABEL_TF"]
        n_eng = len(eboxes) + len(emarks)
        drawn = {"k2": n_eng, "k3": n_eng}
        if e is not None:
            nfed = len(e.bars) - 1
            o = np.array([b["o"] for b in e.bars])
            h = np.array([b["h"] for b in e.bars])
            l = np.array([b["l"] for b in e.bars])
            c = np.array([b["c"] for b in e.bars])
            abr = np.asarray(e.abr)
            eobj_ids = {r["id"] for r in eobjs}
            closed = {"k2": 0, "k3": 0}
            for ob in e.objects:
                if ob.state == "DELETED" or ob.id not in eobj_ids:
                    continue
                if ob.type not in BOX_TYPES or "top" not in ob.geometry:
                    continue
                j0, j1 = S1AP.eng_box_span(ob, nfed)
                if j0 > j1:
                    continue
                top, bot = ob.geometry["top"], ob.geometry["bottom"]
                for k in (2, 3):
                    if first_break(j0, j1, top, bot, c, abr, k)[0] \
                            is not None:
                        closed["k%d" % k] += 1
            drawn = {"k2": n_eng - closed["k2"],
                     "k3": n_eng - closed["k3"]}
        f_c.write(json.dumps(
            {"panel": panel, "n_eng": n_eng, "n_gold": len(g2),
             "n_box": len(eboxes),
             "drawn_k2": drawn["k2"], "drawn_k3": drawn["k3"]}) + "\n")
    f_c.close()

    # ---------------- G-KIT overrides + review closed list -----------
    panels = json.load(open(REVIEW_JSON, encoding="utf8"))["panels"]
    outs = {k: open(os.path.join(
        HERE, "DR_RULES_S2_%s_objects.jsonl" % k), "w",
        encoding="utf8") for k in ("k2", "k3")}
    f_rc = open(os.path.join(HERE, "DR_RULES_S2_review_closed.jsonl"),
                "w", encoding="utf8")
    for p in panels:
        c3j = json.load(open(os.path.join(
            C3_SET, "%s.json" % p["name"]), encoding="utf8"))
        want = [o["id"] for o in c3j.get("objects", [])]
        e = M.pickled(p["date"], p["tau"])
        if e is None:
            continue
        nfed = len(e.bars) - 1
        mm = np.array([b["cet_min"] for b in e.bars])
        o = np.array([b["o"] for b in e.bars])
        h = np.array([b["h"] for b in e.bars])
        l = np.array([b["l"] for b in e.bars])
        c = np.array([b["c"] for b in e.bars])
        abr = np.asarray(e.abr)
        by_id = {ob.id: ob for ob in e.objects}
        sets = {"k2": [], "k3": []}
        for oid in want:
            ob = by_id.get(oid)
            if ob is None:
                continue
            keep = {"k2": True, "k3": True}
            if ob.type in BOX_TYPES and "top" in ob.geometry:
                j0, j1 = S1AP.eng_box_span(ob, nfed)
                top, bot = ob.geometry["top"], ob.geometry["bottom"]
                for k in (2, 3):
                    br = first_break(j0, j1, top, bot, c, abr, k)
                    if br[0] is not None:
                        keep["k%d" % k] = False
                        f_rc.write(json.dumps(
                            {"panel": p["panel"], "tau": p["tau"],
                             "id": oid, "k": k,
                             "confirm_bar": br[0],
                             "side": br[1],
                             "t0_min": int(mm[min(j0, len(mm) - 1)]),
                             "j0": j0, "j1": j1}) + "\n")
            for k in (2, 3):
                if keep["k%d" % k]:
                    sets["k%d" % k].append(
                        ob.to_dict() if hasattr(ob, "to_dict")
                        else dict(ob.__dict__))
        for k in ("k2", "k3"):
            outs[k].write(json.dumps(
                {"panel": p["panel"], "tau": p["tau"],
                 "objects": sets[k]}) + "\n")
    for f in outs.values():
        f.close()
    f_rc.close()
    print("obj_events=%d golden_boxes=%d" % (len(obj_events), n_g))


def gidx_note(g2, g):
    for i, gg in enumerate(g2):
        if gg is g:
            return i
    return None


if __name__ == "__main__":
    main()
