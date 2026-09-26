"""DR_RULES_S1_measure.py — R78 s78.4(2) box shape transforms, read-only.

Same replay path as DR-RULES Part D: cached pickles (canonical 623),
snapshot.live_records + recall_at_k.rank_live, per-family budgets.
At every GOLDEN-DECISION tau (events with scorable goldens) each live
BOX object gets two transforms:

  S1-a left-edge reset: t_left -> first bar after the last impulse run
      (>=4*ABR20 net move within <=6 consecutive same-direction bars)
      or shock bar (range >=3*ABR20) inside the drawn span [t_left,tau].
      Dropped if the reset leaves < 3 bars.
  S1-b age cap: t_left -> max(t_left, tau - 75 bars)  (375 minutes).

Causality: bars <= tau only.  Selection order unchanged; a transformed
object replaces the original in its pick slot (or frees it for the
next-ranked box if dropped).

Outputs (deepresearch/):
  DR_RULES_S1_objects.jsonl    per event per live box: transform result
                               + owner-clean features before/after
  DR_RULES_S1_events.jsonl     per event: picks/hits before & per arm
  DR_RULES_S1_hits.jsonl       per parent box-hit: IoU/edges before-after
  DR_RULES_S1_golden_starts.jsonl  author box t0 vs last impulse/shock
  DR_RULES_S1_prefix.jsonl     20-panel prefix-invariance rows
"""
import collections
import json
import os
import pickle
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
from r73_edges import edge_defs         # noqa: E402

import DR_RULES_measure as M            # noqa: E402

FAM_BUDGET = {"box": 1, "line": 2, "level": 1, "bracket": 1}
BOX_TYPES = ("BOX", "RANGE_OPEN", "CONTEXT_RANGE")
CAP_MIN = 375.0        # 75 M5 bars
C6_TOL = 3.0           # engine-side C6g tolerance (mid-ruler), pips
W95 = 75.4             # author drawn-width q95 (DR-RULES Part B)


def last_event_end(j0, j1, o, h, l, c, abr):
    """Largest end-bar of a shock bar (range>=3*abr) or an impulse
    window (<=6 same-direction bars, net >=4*abr[b]) inside [j0..j1].
    None if no event."""
    end = -1
    for k in range(j0, j1 + 1):
        if (h[k] - l[k]) / abr[k] >= 3.0:
            end = k
    sg = np.sign(c[j0:j1 + 1] - o[j0:j1 + 1])
    n = j1 - j0 + 1
    i = 0
    while i < n:
        if sg[i] == 0:
            i += 1
            continue
        e2 = i
        while e2 + 1 < n and sg[e2 + 1] == sg[i]:
            e2 += 1
        for b in range(i, e2 + 1):
            for a in range(max(i, b - 5), b + 1):
                if abs(c[j0 + b] - o[j0 + a]) / abr[j0 + b] >= 4.0:
                    if j0 + b > end:
                        end = j0 + b
                    break
        i = e2 + 1
    return end if end >= 0 else None


def box_stats(lo, hi, j0, j1, m, o, h, l, c, ema, abr):
    """Owner-clean feature set on span [j0..j1] (bars<=tau)."""
    wa, wb = j0, j1                      # window = span for transformed
    out = M.s_c1(lo, hi, j1, ema, abr)
    out["c3_r_win"] = M.s_c3(wa, wb, h, l, abr)["c3_r"]
    out["c4_r_win"] = M.s_c4(wa, wb, o, c, abr)["c4_r"]
    out["width_bars"] = (m[j1] - m[j0]) / 5.0
    out.update(M.s_c6(j0, j1, h, l, o, c, abr, hi, lo))
    return out


def owner_clean(st):
    """The five Owner-rule predicates used in this lane."""
    return {
        "C1@1.0": bool(st["c1_abr"] is not None
                       and st["c1_abr"] <= 1.0),
        "C3w@3.0": bool(st["c3_r_win"] is not None
                        and st["c3_r_win"] < 3.0),
        "C4w@4": bool(st["c4_r_win"] is not None
                      and st["c4_r_win"] < 4.0),
        "C6g": bool(st["c6_maxd"] is not None
                    and st["c6_maxd"] <= C6_TOL),
        "C5@q95": bool(st["width_bars"] is not None
                       and st["width_bars"] <= W95),
    }


def xform_box(rec, ob, tau, m, o, h, l, c, abr, nfed):
    """Apply both transforms; return dicts describing each arm."""
    t1_src = ob.geometry.get("t1_drawn") or \
        (ob.t_right if ob.t_right is not None else nfed)
    j1 = min(int(t1_src), nfed)
    j0 = min(int(ob.t_left), j1)
    out = {"id": rec["id"], "j0": j0, "j1": j1}
    # ---- S1-a
    end = last_event_end(j0, j1, o, h, l, c, abr)
    if end is None:
        out["a_j0"], out["a_end"] = j0, None
    else:
        out["a_j0"], out["a_end"] = min(end + 1, j1 + 1), end
    out["a_dropped"] = (j1 - out["a_j0"] + 1) < 3
    # ---- S1-b
    cap = M.jge(m, tau - CAP_MIN)
    out["b_j0"] = max(j0, min(cap, j1))
    out["b_dropped"] = False
    return out


def rec_with(rec, t0m):
    """Copy of an engine record with the drawn left edge moved."""
    r = dict(rec)
    r["t0_raw"] = int(t0m)
    r["t0"] = max(int(t0m), r.get("w0", -10 ** 9))
    if r.get("bs") is not None:
        r["bs"] = max(r["bs"], int(t0m))
    return r


def main():
    recs = C.load_tune()
    events = [json.loads(x) for x in open(
        os.path.join(HERE, "DR_RULES_events.jsonl"), encoding="utf8")]
    obj_events = [e for e in events if e["is_tau_event"]]
    rec_by_id = {r["id"]: r for r in recs}

    f_o = open(os.path.join(HERE, "DR_RULES_S1_objects.jsonl"), "w",
               encoding="utf8")
    f_e = open(os.path.join(HERE, "DR_RULES_S1_events.jsonl"), "w",
               encoding="utf8")
    f_h = open(os.path.join(HERE, "DR_RULES_S1_hits.jsonl"), "w",
               encoding="utf8")
    f_p = open(os.path.join(HERE, "DR_RULES_S1_prefix.jsonl"), "w",
               encoding="utf8")

    panels_seen = collections.OrderedDict()
    for ev in obj_events:
        panels_seen.setdefault(ev["panel"], []).append(ev)

    # cumulative census (published method): per panel n_eng/n_gold on
    # the w1 full-window pickle; arm A drops objects dropped at EVERY
    # tau where live.
    drop_votes = collections.defaultdict(set)     # (panel,id)->taus dropped
    live_votes = collections.defaultdict(set)     # (panel,id)->taus live
    census = {}
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
        census[panel] = {"n_eng": len(eboxes) + len(emarks),
                         "n_gold": len(g2), "n_box": len(eboxes)}

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
            live, emarks = live_records(e, m_day, w0, tau)
            osc = {ob.id: getattr(ob, "score", None)
                   for ob in e.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            ranked = RK.rank_live(live, RK.score_map(e))
            o_by_id = {ob.id: ob for ob in e.objects}

            # ---- transform each live box (both arms) -----------------
            rows = []
            for rank, r in enumerate(ranked):
                fam = EV.FAMILY.get(r["type"])
                if fam != "box":
                    continue
                ob = o_by_id.get(r["id"])
                if ob is None or "top" not in ob.geometry:
                    continue
                xf = xform_box(r, ob, tau, m, o, h, l, c, abr, nfed)
                lo, hi = ob.geometry["bottom"], ob.geometry["top"]
                j1, j0 = xf["j1"], xf["j0"]
                st0 = box_stats(lo, hi, j0, j1, m, o, h, l, c, ema, abr)
                st_a = None if xf["a_dropped"] else box_stats(
                    lo, hi, xf["a_j0"], j1, m, o, h, l, c, ema, abr)
                st_b = box_stats(lo, hi, xf["b_j0"], j1, m, o, h, l, c,
                                 ema, abr)
                row = {"panel": panel, "tau": tau, "rank": rank,
                       "xf": xf, "stats0": st0, "stats_a": st_a,
                       "stats_b": st_b, "rec": r}
                rows.append((rank, r, xf, row))
                live_votes[(panel, r["id"])].add(tau)
                if xf["a_dropped"]:
                    drop_votes[(panel, r["id"])].add(tau)

            # ---- hits: baseline + arms (same ranked order) ----------
            def box_pick(arm):
                for rank, r, xf, row in rows:
                    if arm == "a" and xf["a_dropped"]:
                        continue
                    if arm == "a" and xf["a_j0"] != xf["j0"]:
                        return rec_with(r, m[xf["a_j0"]])
                    if arm == "b" and xf["b_j0"] != xf["j0"]:
                        return rec_with(r, m[xf["b_j0"]])
                    return r
                return None

            picks = {"0": box_pick("0"), "a": box_pick("a"),
                     "b": box_pick("b")}
            hit_rows = {}
            for arm, pr in picks.items():
                if pr is None:
                    hit_rows[arm] = {"pick": None, "hit": 0}
                    continue
                mgi = [gidx[id(g)] for g in ggs
                       if EV.FAMILY.get(g["spec_type"]) == "box"
                       and V2.match(g, pr, m_day)]
                hit_rows[arm] = {"pick": pr["id"], "hit": bool(mgi),
                                 "match_gis": mgi}
            # non-box families: picks are untouched recs; recount hits
            # once (identical for every arm by construction)
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
            ev_out = {"panel": panel, "tau": tau,
                      "n_live_boxes": len(rows),
                      "n_dropped_a": sum(1 for _r, _rr, xf, _ro in rows
                                         if xf["a_dropped"]),
                      "nf_hits": nf_hits,
                      "picks": {a: (hit_rows[a]["pick"]) for a in picks},
                      "hits": {a: bool(hit_rows[a]["hit"])
                               for a in picks}}
            f_e.write(json.dumps(ev_out) + "\n")

            for rank, r, xf, row in rows:
                oid = r["id"]
                o_out = {"panel": panel, "tau": tau, "id": oid,
                         "rank": rank,
                         "picked0": oid == picks["0"]["id"]
                         if picks["0"] else False,
                         "picked_a": oid == picks["a"]["id"]
                         if picks["a"] else False,
                         "picked_b": oid == picks["b"]["id"]
                         if picks["b"] else False,
                         "matched0": False,
                         "j0": xf["j0"], "j1": xf["j1"],
                         "a_j0": xf["a_j0"], "a_end": xf["a_end"],
                         "a_dropped": xf["a_dropped"],
                         "b_j0": xf["b_j0"],
                         "clean0": owner_clean(row["stats0"]),
                         "clean_a": (owner_clean(row["stats_a"])
                                     if row["stats_a"] else None),
                         "clean_b": owner_clean(row["stats_b"]),
                         "width0": row["stats0"]["width_bars"],
                         "width_a": (row["stats_a"]["width_bars"]
                                     if row["stats_a"] else None),
                         "width_b": row["stats_b"]["width_bars"],
                         "c3_0": row["stats0"]["c3_r_win"],
                         "c3_a": (row["stats_a"]["c3_r_win"]
                                  if row["stats_a"] else None),
                         "c4_0": row["stats0"]["c4_r_win"],
                         "c4_a": (row["stats_a"]["c4_r_win"]
                                  if row["stats_a"] else None),
                         "c6_0": row["stats0"]["c6_maxd"],
                         "c6_a": (row["stats_a"]["c6_maxd"]
                                  if row["stats_a"] else None),
                         "c6_b": row["stats_b"]["c6_maxd"]}
                o_out["matched0"] = any(
                    V2.match(g, r, m_day) for g in ggs
                    if EV.FAMILY.get(g["spec_type"]) == "box")
                f_o.write(json.dumps(o_out) + "\n")

            # ---- per parent-hit detail -------------------------------
            if hit_rows["0"]["hit"]:
                pr0 = picks["0"]
                ob0 = o_by_id[pr0["id"]]
                xf0 = next(xf for _rk, rr, xf, _ro in rows
                           if rr["id"] == pr0["id"])
                for gi in hit_rows["0"]["match_gis"]:
                    g = g2[gi]
                    wg = V2._gold_window(g)
                    we0 = V2._eng_window(pr0)
                    for arm in ("a", "b"):
                        pr = picks[arm]
                        es0 = V2._span(pr0)
                        det = {"panel": panel, "tau": tau, "gi": gi,
                               "arm": arm, "pick0": pr0["id"],
                               "pick": pr["id"] if pr else None,
                               "wg": wg, "we0": we0,
                               "iou0": (V2.iou_true(*we0, *wg)
                                        if None not in we0 + wg
                                        else None),
                               "cov0": (V2._coverage(*es0, *wg)
                                        if None not in es0 + wg
                                        else None),
                               "dlo": (abs(pr0["lo"] - g["price_lo"] *
                                           M.PIP)
                                       if g.get("price_lo") is not None
                                       else None),
                               "dhi": (abs(pr0["hi"] - g["price_hi"] *
                                           M.PIP)
                                       if g.get("price_hi") is not None
                                       else None)}
                        if pr is not None:
                            we1 = V2._eng_window(pr)
                            det["we1"] = we1
                            det["iou1"] = (V2.iou_true(*we1, *wg)
                                           if None not in we1 + wg
                                           else None)
                            es1 = V2._span(pr)
                            det["cov1"] = (V2._coverage(*es1, *wg)
                                           if None not in es1 + wg
                                           else None)
                            det["matched1"] = V2.match(g, pr, m_day)
                        else:
                            det["we1"] = det["iou1"] = None
                            det["matched1"] = False
                        det["orig_dropped"] = (arm == "a"
                                               and xf0["a_dropped"])
                        det["fill"] = (pr is not None
                                       and pr["id"] != pr0["id"])
                        det["same_pick"] = (pr is not None
                                            and pr["id"] == pr0["id"])
                        f_h.write(json.dumps(det) + "\n")
    f_o.close(); f_e.close(); f_h.close()

    # ---------------- author box starts ------------------------------
    f_g = open(os.path.join(HERE, "DR_RULES_S1_golden_starts.jsonl"),
               "w", encoding="utf8")
    n_st = 0
    for panel, evs in panels_seen.items():
        rec = rec_by_id[panel]
        w1 = rec["window"]["x1"] or 1439
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs
              if V2.scorable(g, rec["window"]["x0"], w1)]
        e = M.pickled(rec["date"], w1)     # full-window: covers all t0
        if e is None:
            continue
        m = np.array([b["cet_min"] for b in e.bars])
        o = np.array([b["o"] for b in e.bars])
        h = np.array([b["h"] for b in e.bars])
        l = np.array([b["l"] for b in e.bars])
        c = np.array([b["c"] for b in e.bars])
        abr = np.asarray(e.abr)
        for g in g2:
            if g["spec_type"] not in BOX_TYPES:
                continue
            t0 = M.to_min(g.get("t0"))
            if t0 is None:
                continue
            j0 = M.jge(m, t0)
            end = last_event_end(0, max(j0 - 1, 0), o, h, l, c, abr)
            f_g.write(json.dumps(
                {"panel": panel, "t0": t0, "j0": j0,
                 "last_end": end,
                 "gap": (j0 - end if end is not None else None)})
                + "\n")
            n_st += 1
    f_g.close()

    # ---------------- prefix invariance (20 panels) ------------------
    n_pan = 0
    for panel, evs in panels_seen.items():
        if n_pan >= 20:
            break
        n_pan += 1
        rec = rec_by_id[panel]
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m_day, _o, _h, _l, _c = CA.bars(rec["date"])
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
            lim = M.jle(m2, tau)
            ob_full = {ob.id: ob for ob in e_full.objects}
            for ob in e.objects:
                if ob.type not in BOX_TYPES or "top" not in ob.geometry:
                    continue
                ob2 = ob_full.get(ob.id)
                if ob2 is None or ob2.t_left != ob.t_left:
                    continue
                j0 = int(ob.t_left)
                j1 = M.jle(m, tau)
                j1 = min(j1, nfed)
                if j0 > j1:
                    continue
                end1 = last_event_end(j0, j1, o, h, l, c, abr)
                j1b = min(M.jle(m2, tau), len(m2) - 1)
                end2 = last_event_end(j0, j1b, o2, h2, l2, c2, abr2)
                same = (end1 == end2)
                f_p.write(json.dumps(
                    {"panel": panel, "tau": tau, "id": ob.id,
                     "end_tau": end1, "end_full": end2, "same": same})
                    + "\n")
    f_p.close()
    print("obj_events=%d golden_starts=%d" % (len(obj_events), n_st))


if __name__ == "__main__":
    main()
