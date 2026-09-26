"""R83 s.83.2 TT-3 report (build lane, INFO).

Measures the entry-anchored box_broken tag on C-3 objects and on the
author's boxes at golden-decision taus, reusing boxlab/e3_diag.py's
enumeration (golden BOX CURRENT at tau = right edge >= tau-15) and
pickled canonical engines (uip2_pbbirth@8361fe85 == C-3 defaults).

Items per s.83.2 report spec:
  1) share of live box objects tagged at taus, split by clause;
  2) of the 16 C-3 box hits at their tau, how many are tagged (list);
  3) golden compliance with the same entry-anchored rule, per clause;
  4) the 4 S1-b fatal boxes + the 4 E5 panels: tagged y/n, exit_bar;
  5) diagnostic creep count: boxes with >=3 closes beyond one edge in
     (j0, t] that never form a run of 3.
"""
import json
import os
import pickle
import sys
from collections import Counter, defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "evalcheck"))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "boxlab"))

import common as C                      # noqa: E402
import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import trade_tags as TT                # noqa: E402
from snapshot import tau_of, live_records  # noqa: E402
from recall_at_k import rank_live, score_map  # noqa: E402
from kernel import FAMILY              # noqa: E402
import e3_diag as E3                   # noqa: E402

BOXK = {"BOX", "CONTEXT_RANGE", "RANGE_OPEN"}
S1B = [("9.10c", "BOX0001"), ("9.33c", "BOX0001"),
       ("9.36c", "BOX0001"), ("9.40a", "BOX0002")]
E5P = ["9.17b", "9.36c", "9.42b", "9.48b"]


def eng_ob_stats(e, ob):
    nfed = len(e.bars) - 1
    return TT.object_stats(ob, nfed, e.bars, e.ema, e.abr,
                           e.book.seq)


def main():
    recs = list(C.load_tune())
    rev = {p["name"]: p for p in json.load(open(
        os.path.join(HERE, "review", "review_panels.json"),
        encoding="utf8"))["panels"]}

    n_live = 0
    clause_ct = Counter()
    creep_n = 0
    hits = []
    gold_ct = Counter()
    gold_cl = Counter()

    for rec in recs:
        d = rec["id"]
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        _t, m, o, h, l, c = E3.CA.bars(rec["date"])
        abr = E3.CA.abr(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        for g in gobjs:
            if g["spec_type"] not in V2.BOX_TYPES or \
                    not V2.scorable(g, w0, w1):
                continue
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            tau = min(tau, w1)
            if (g.get("t1") or w1) < tau - 15:
                continue
            e = E3.pkl_for(rec["date"], tau)
            if e is None:
                continue
            j_tau = E3.jb(m, tau)
            # ---- item 1: live boxes at tau -> tag share/clause ----
            eng_by_id = {}
            for ob in e.objects:
                if ob.type in BOXK and ob.state == "ACTIVE":
                    eng_by_id[ob.id] = ob
                    fam, st = eng_ob_stats(e, ob)
                    n_live += 1
                    if "box_broken" in TT.tags_from_stats(fam, st):
                        clause_ct[st.get("break_clause")] += 1
                    elif st.get("creep_n", 0) >= 3:
                        creep_n += 1
            # ---- item 2: the 16 hits -> tagged? ----
            ranked = E3.eng_at(e, m, w0, tau)
            boxes = [r for r in ranked
                     if FAMILY.get(r["type"]) == "box"]
            box1 = boxes[0] if boxes else None
            if box1 is not None and V2.match_detail(g, box1, m)[0]:
                ob = eng_by_id.get(box1["id"])
                tg = cl = xb = None
                if ob is not None:
                    fam, st = eng_ob_stats(e, ob)
                    tags = TT.tags_from_stats(fam, st)
                    tg = "box_broken" in tags
                    cl = st.get("break_clause")
                    xb = st.get("exit_bar")
                hits.append({"panel": d, "tau": int(tau),
                             "id": box1["id"], "tagged": tg,
                             "clause": cl, "exit_bar": xb})
            # ---- item 3: golden compliance (entry-anchored) -------
            glo, ghi = g["price_lo"] * 1e4, g["price_hi"] * 1e4
            jg0 = E3.jb(m, g["t0"])
            stg = TT.s_box_broken(glo, ghi, jg0, j_tau, c, abr)
            gold_ct["n"] += 1
            if stg.get("bbroken"):
                gold_ct["tagged"] += 1
                gold_cl[stg.get("break_clause")] += 1

    print("== LIVE C-3 boxes at golden-decision taus ==")
    print("live box objects evaluated: %d | tagged %d (%.3f) "
          "| clause %s | creep(>=3, unbroken) %d"
          % (n_live, sum(clause_ct.values()),
             sum(clause_ct.values()) / max(n_live, 1),
             dict(clause_ct), creep_n))
    print("\n== the C-3 box hits at their tau ==")
    nt = sum(1 for x in hits if x["tagged"])
    print("hits: %d | tagged: %d" % (len(hits), nt))
    for x in hits:
        print("  %s@%d %s tagged=%s clause=%s exit=%s"
              % (x["panel"], x["tau"], x["id"], x["tagged"],
                 x["clause"], x["exit_bar"]))
    print("\n== GOLDEN compliance (entry-anchored) ==")
    print("golden boxes: %d | tagged %d (%.3f) | clause %s"
          % (gold_ct["n"], gold_ct["tagged"],
             gold_ct["tagged"] / max(gold_ct["n"], 1), dict(gold_cl)))

    # ---- item 4: named boxes -------------------------------------
    print("\n== S1-b fatal boxes (capped-left objects) ==")
    for name, oid in S1B:
        p = rev.get(name)
        if p is None:
            continue
        e = E3.pkl_for(p["date"], p["tau"])
        if e is None:
            print("  %s %s: no engine" % (name, oid))
            continue
        ob = next((o for o in e.objects if o.id == oid), None)
        if ob is None:
            print("  %s %s: not in objects" % (name, oid))
            continue
        fam, st = eng_ob_stats(e, ob)
        tags = TT.tags_from_stats(fam, st)
        print("  %s %s tagged=%s clause=%s exit_bar=%s state=%s"
              % (name, oid, "box_broken" in tags,
                 st.get("break_clause"), st.get("exit_bar"),
                 ob.state))
    print("\n== E5 panels: live boxes at review tau ==")
    for name in E5P:
        p = rev.get(name)
        if p is None:
            continue
        e = E3.pkl_for(p["date"], p["tau"])
        if e is None:
            continue
        for ob in e.objects:
            if ob.type in BOXK and ob.state == "ACTIVE":
                fam, st = eng_ob_stats(e, ob)
                tags = TT.tags_from_stats(fam, st)
                print("  %s %s [%.1f,%.1f] tagged=%s clause=%s "
                      "exit=%s" % (name, ob.id, ob.geometry["bottom"],
                                   ob.geometry["top"],
                                   "box_broken" in tags,
                                   st.get("break_clause"),
                                   st.get("exit_bar")))


if __name__ == "__main__":
    main()
