"""DR_RULES_S1ap_measure.py — R81 s81.4 arm S1-a' (no-drop reset).

Extends DR_RULES_S1_measure.py (imported as S1M; never forked).

S1-a': identical to S1-a (t_left -> first bar after the last impulse
run >=4*ABR20 within <=6 consecutive same-direction bars, or shock bar
range >=3*ABR20, inside the drawn span [t_left,tau]; edges unchanged),
EXCEPT: when the reset would leave fewer than 3 bars, t_left is set to
tau - 2 bars (the last 3 bars are kept) instead of dropping the object.

Outputs (deepresearch/):
  DR_RULES_S1ap_events.jsonl   per event: picks/hits arm ap + nf_hits
  DR_RULES_S1ap_rows.jsonl     per live box: ap transform + clean stats
  DR_RULES_S1ap_hits.jsonl     per parent-hit detail under arm ap
  DR_RULES_S1ap_prefix.jsonl   20-panel prefix invariance for arm ap
  DR_RULES_S1ap_objects.jsonl  engine-spelling override rows for the 12
                               fixed review panels (G-KIT --override)
  DR_RULES_S1a_objects.jsonl / DR_RULES_S1b_objects.jsonl
                               same engine spelling for arms a/b (G-KIT
                               R81.5-2 render inputs; stats rows stay in
                               DR_RULES_S1_objects.jsonl)
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

import DR_RULES_measure as M            # noqa: E402
import DR_RULES_S1_measure as S1M       # noqa: E402

FAM_BUDGET = S1M.FAM_BUDGET
BOX_TYPES = S1M.BOX_TYPES
REVIEW_JSON = os.path.join(PERC, "review", "review_panels.json")


def xform_ap(j0, j1, o, h, l, c, abr):
    """S1-a' transform on span [j0..j1].

    Returns (ap_j0, end, kind):
      kind 'none'   -> no impulse/shock inside; unchanged
      kind 'reset'  -> a_j0 = end+1 leaves >= 3 bars; same as S1-a
      kind 'clamp3' -> reset would leave < 3 bars; t_left = tau-2 bars
                       (j1-2), i.e. the last 3 bars kept
    ap_extended is flagged by the caller if ap_j0 < j0 (edge case: an
    original span narrower than 3 bars with an event inside would get
    its left edge moved *earlier* than drawn)."""
    end = S1M.last_event_end(j0, j1, o, h, l, c, abr)
    if end is None:
        return j0, None, "none"
    a_j0 = end + 1
    if (j1 - a_j0 + 1) >= 3:
        return a_j0, end, "reset"
    return max(j1 - 2, 0), end, "clamp3"


def eng_box_span(ob, nfed):
    """(j0,j1) for a live engine box object — same rule as S1M.xform_box."""
    t1_src = ob.geometry.get("t1_drawn") or \
        (ob.t_right if ob.t_right is not None else nfed)
    j1 = min(int(t1_src), nfed)
    j0 = min(int(ob.t_left), j1)
    return j0, j1


def override_rows(panel, date, tau):
    """Engine-spelling objects live at tau under arms a/b/ap, for G-KIT."""
    e = M.pickled(date, tau)
    if e is None:
        return None
    nfed = len(e.bars) - 1
    o = np.array([b["o"] for b in e.bars])
    h = np.array([b["h"] for b in e.bars])
    l = np.array([b["l"] for b in e.bars])
    c = np.array([b["c"] for b in e.bars])
    abr = np.asarray(e.abr)
    arms = {"a": [], "b": [], "ap": []}
    for ob in e.objects:
        if ob.state == "DELETED":
            continue
        if ob.type not in BOX_TYPES or "top" not in ob.geometry:
            d = ob.to_dict() if hasattr(ob, "to_dict") else dict(
                ob.__dict__)
            for arm in arms:
                arms[arm].append(d)
            continue
        j0, j1 = eng_box_span(ob, nfed)
        end = S1M.last_event_end(j0, j1, o, h, l, c, abr)
        # arm a: drop if reset leaves <3 bars
        a_j0 = j0 if end is None else end + 1
        if end is None or (j1 - a_j0 + 1) >= 3:
            d = ob.to_dict()
            if a_j0 != j0:
                d = dict(d)
                d["t_left"] = int(a_j0)
                d["geometry"] = dict(d["geometry"])
                d["geometry"]["t0"] = int(a_j0)
            arms["a"].append(d)
        # arm b: age cap 375 minutes
        m_arr = np.array([bb["cet_min"] for bb in e.bars])
        b_j0 = max(j0, min(M.jge(m_arr, int(tau) - 375.0), j1))
        d = ob.to_dict()
        if b_j0 != j0:
            d = dict(d)
            d["t_left"] = int(b_j0)
            d["geometry"] = dict(d["geometry"])
            d["geometry"]["t0"] = int(b_j0)
        arms["b"].append(d)
        # arm ap
        ap_j0, _e2, _k = xform_ap(j0, j1, o, h, l, c, abr)
        d = ob.to_dict()
        if ap_j0 != j0:
            d = dict(d)
            d["t_left"] = int(ap_j0)
            d["geometry"] = dict(d["geometry"])
            d["geometry"]["t0"] = int(ap_j0)
        arms["ap"].append(d)
    return arms


def main():
    recs = C.load_tune()
    events = [json.loads(x) for x in open(
        os.path.join(HERE, "DR_RULES_events.jsonl"), encoding="utf8")]
    obj_events = [e for e in events if e["is_tau_event"]]
    rec_by_id = {r["id"]: r for r in recs}

    f_e = open(os.path.join(HERE, "DR_RULES_S1ap_events.jsonl"), "w",
               encoding="utf8")
    f_r = open(os.path.join(HERE, "DR_RULES_S1ap_rows.jsonl"), "w",
               encoding="utf8")
    f_h = open(os.path.join(HERE, "DR_RULES_S1ap_hits.jsonl"), "w",
               encoding="utf8")

    panels_seen = collections.OrderedDict()
    for ev in obj_events:
        panels_seen.setdefault(ev["panel"], []).append(ev)

    n_ext = 0
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
                j0, j1 = eng_box_span(ob, nfed)
                ap_j0, end, kind = xform_ap(j0, j1, o, h, l, c, abr)
                if ap_j0 < j0:
                    n_ext += 1
                lo, hi = ob.geometry["bottom"], ob.geometry["top"]
                st0 = S1M.box_stats(lo, hi, j0, j1, m, o, h, l, c, ema,
                                    abr)
                st_ap = S1M.box_stats(lo, hi, ap_j0, j1, m, o, h, l, c,
                                      ema, abr)
                rows.append((rank, r, j0, j1, ap_j0, end, kind,
                             st0, st_ap))

            # ---- picks: baseline (untouched) and arm ap -------------
            pick0 = rows[0][1] if rows else None
            pick_ap = None
            if rows:
                _rank, r, j0, j1, ap_j0 = rows[0][:5]
                pick_ap = (S1M.rec_with(r, m[ap_j0])
                           if ap_j0 != j0 else r)
            hits = {"0": False, "ap": False}
            mgis = {"0": [], "ap": []}
            for arm, pr in (("0", pick0), ("ap", pick_ap)):
                if pr is None:
                    continue
                mgi = [gidx[id(g)] for g in ggs
                       if EV.FAMILY.get(g["spec_type"]) == "box"
                       and V2.match(g, pr, m_day)]
                hits[arm] = bool(mgi)
                mgis[arm] = mgi
            # non-box families: untouched; recount once
            fam_ranked = collections.defaultdict(list)
            for r in ranked:
                fam_ranked[EV.FAMILY.get(r["type"])].append(r)
            nf_hits = {}
            for f, k in FAM_BUDGET.items():
                if f == "box":
                    continue
                top = fam_ranked[f][:k]
                nf_hits[f] = sum(
                    1 for g in ggs
                    if EV.FAMILY.get(g["spec_type"]) == f
                    and any(V2.match(g, r, m_day) for r in top))
            f_e.write(json.dumps(
                {"panel": panel, "tau": tau,
                 "n_live_boxes": len(rows),
                 "n_reset": sum(1 for x in rows if x[6] == "reset"),
                 "n_clamp3": sum(1 for x in rows if x[6] == "clamp3"),
                 "nf_hits": nf_hits,
                 "picks": {"0": pick0["id"] if pick0 else None,
                           "ap": pick_ap["id"] if pick_ap else None},
                 "hits": hits}) + "\n")

            for (rank, r, j0, j1, ap_j0, end, kind, st0, st_ap) in rows:
                oid = r["id"]
                f_r.write(json.dumps(
                    {"panel": panel, "tau": tau, "id": oid,
                     "rank": rank,
                     "picked0": bool(pick0 and oid == pick0["id"]),
                     "picked_ap": bool(pick_ap
                                       and oid == pick_ap["id"]),
                     "matched0": any(
                         V2.match(g, r, m_day) for g in ggs
                         if EV.FAMILY.get(g["spec_type"]) == "box"),
                     "j0": j0, "j1": j1,
                     "ap_j0": ap_j0, "ap_end": end, "ap_kind": kind,
                     "ap_extended": ap_j0 < j0,
                     "clean0": S1M.owner_clean(st0),
                     "clean_ap": S1M.owner_clean(st_ap),
                     "width0": st0["width_bars"],
                     "width_ap": st_ap["width_bars"],
                     "c3_0": st0["c3_r_win"],
                     "c3_ap": st_ap["c3_r_win"],
                     "c4_0": st0["c4_r_win"],
                     "c4_ap": st_ap["c4_r_win"],
                     "c6_0": st0["c6_maxd"],
                     "c6_ap": st_ap["c6_maxd"]}) + "\n")

            # ---- per parent-hit detail under arm ap ------------------
            if hits["0"]:
                pr0 = pick0
                xf0 = next(x for x in rows if x[1]["id"] == pr0["id"])
                for gi in mgis["0"]:
                    g = g2[gi]
                    wg = V2._gold_window(g)
                    we0 = V2._eng_window(pr0)
                    es0 = V2._span(pr0)
                    pr = pick_ap
                    det = {"panel": panel, "tau": tau, "gi": gi,
                           "arm": "ap", "pick0": pr0["id"],
                           "pick": pr["id"] if pr else None,
                           "kind0": xf0[6],
                           "wg": wg, "we0": we0,
                           "iou0": (V2.iou_true(*we0, *wg)
                                    if None not in we0 + wg else None),
                           "cov0": (V2._coverage(*es0, *wg)
                                    if None not in es0 + wg else None),
                           "dlo": (abs(pr0["lo"] - g["price_lo"] * M.PIP)
                                   if g.get("price_lo") is not None
                                   else None),
                           "dhi": (abs(pr0["hi"] - g["price_hi"] * M.PIP)
                                   if g.get("price_hi") is not None
                                   else None),
                           "same_pick": (pr is not None
                                         and pr["id"] == pr0["id"]),
                           "fill": (pr is not None
                                    and pr["id"] != pr0["id"])}
                    if pr is not None:
                        we1 = V2._eng_window(pr)
                        es1 = V2._span(pr)
                        det["we1"] = we1
                        det["iou1"] = (V2.iou_true(*we1, *wg)
                                       if None not in we1 + wg
                                       else None)
                        det["cov1"] = (V2._coverage(*es1, *wg)
                                       if None not in es1 + wg
                                       else None)
                        det["matched1"] = V2.match(g, pr, m_day)
                    else:
                        det["we1"] = det["iou1"] = det["cov1"] = None
                        det["matched1"] = False
                    f_h.write(json.dumps(det) + "\n")
    f_e.close(); f_r.close(); f_h.close()

    # ---------------- prefix invariance (20 panels, arm ap) ----------
    f_p = open(os.path.join(HERE, "DR_RULES_S1ap_prefix.jsonl"), "w",
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
            m = np.array([b["cet_min"] for b in e.bars])
            o = np.array([b["o"] for b in e.bars])
            h = np.array([b["h"] for b in e.bars])
            l = np.array([b["l"] for b in e.bars])
            c = np.array([b["c"] for b in e.bars])
            abr = np.asarray(e.abr)
            nfed = len(e.bars) - 1
            m2 = np.array([b["cet_min"] for b in e_full.bars])
            o2 = np.array([b["o"] for b in e_full.bars])
            h2 = np.array([b["h"] for b in e_full.bars])
            l2 = np.array([b["l"] for b in e_full.bars])
            c2 = np.array([b["c"] for b in e_full.bars])
            abr2 = np.asarray(e_full.abr)
            jlim = min(M.jle(m2, tau), len(m2) - 1)
            ob_full = {ob.id: ob for ob in e_full.objects}
            for ob in e.objects:
                if ob.type not in BOX_TYPES or "top" not in ob.geometry:
                    continue
                ob2 = ob_full.get(ob.id)
                if ob2 is None or ob2.t_left != ob.t_left:
                    continue
                j0, j1 = eng_box_span(ob, nfed)
                if j0 > j1:
                    continue
                # causal span (j0,j1) fixed on both sides; only the bar
                # arrays differ -> checks pickle-prefix integrity, and
                # edge_moved flags objects whose drawn edge later grew
                a1 = xform_ap(j0, j1, o, h, l, c, abr)[0]
                a2 = xform_ap(j0, min(j1, jlim), o2, h2, l2, c2, abr2)[0]
                t1_2 = ob2.geometry.get("t1_drawn") or ob2.t_right
                t1_1 = ob.geometry.get("t1_drawn") or ob.t_right
                f_p.write(json.dumps(
                    {"panel": panel, "tau": tau, "id": ob.id,
                     "ap_j0_tau": a1, "ap_j0_full": a2,
                     "same": a1 == a2,
                     "edge_moved": t1_2 != t1_1}) + "\n")
    f_p.close()

    # ---------------- G-KIT override files (12 review panels) --------
    panels = json.load(open(REVIEW_JSON, encoding="utf8"))["panels"]
    outs = {}
    for arm in ("a", "b", "ap"):
        outs[arm] = open(os.path.join(
            HERE, "DR_RULES_S1%s_objects.jsonl" % arm), "w",
            encoding="utf8")
    n_obj = 0
    for p in panels:
        arms = override_rows(p["panel"], p["date"], p["tau"])
        if arms is None:
            continue
        for arm, objs in arms.items():
            outs[arm].write(json.dumps(
                {"panel": p["panel"], "tau": p["tau"],
                 "objects": objs}) + "\n")
            n_obj += len(objs)
    for f in outs.values():
        f.close()
    print("obj_events=%d ap_extended=%d override_objs=%d"
          % (len(obj_events), n_ext, n_obj))


if __name__ == "__main__":
    main()
