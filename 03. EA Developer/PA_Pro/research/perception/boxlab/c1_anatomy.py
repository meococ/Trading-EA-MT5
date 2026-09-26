"""c1_anatomy.py — R38 §38.3.1 selection anatomy (the boxes' version
of the 19-case table).

For every BOX golden that HAS a right proposal under the wd arm
(oracle .407), at that golden's tau:
  - is a matching box live at all (coverable)?
  - what ranks top-1 in the box family, and with what score/route?
  - what was the right candidate's fate (born / rate_limited /
    nms_suppressed / proposed-only) and its logged score?

Prints one row per covered golden + a summary of separation patterns.

Usage: python c1_anatomy.py [variant hash]   (default c1r_wd e62f2dc9)
"""
import collections
import glob
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)

import common as C                      # noqa: E402
import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import cache as CA                     # noqa: E402
import funnel as F                     # noqa: E402
import recall_at_k as RK               # noqa: E402
from scoreboard import panel_cands     # noqa: E402
from snapshot import tau_of, live_records  # noqa: E402


def _pkl(variant, h8, date, w1):
    f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                     % (variant, h8, date, w1))
    if os.path.exists(f):
        return f
    g = glob.glob(os.path.join(
        CA.CACHE, "run_%s_%s*_%s_%s.pkl" % (variant, h8, date, w1)))
    return g[0] if g else None


def main():
    variant = sys.argv[1] if len(sys.argv) > 1 else "c1r_wd"
    h8 = sys.argv[2] if len(sys.argv) > 2 else "e62f2dc9"
    recs = C.load_tune()
    rows = []
    summ = collections.Counter()
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        ffull = _pkl(variant, h8, rec["date"], w1)
        if not ffull:
            continue
        efull = pickle.load(open(ffull, "rb"))
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        # (record, raw_row) pairs — raw rows carry the logged score,
        # records carry the converted fields cand_right needs
        pairs_ = []
        for cd in efull.cand_log or []:
            if cd["kind"] == "LABEL_TF":
                continue
            r = F.cand_as_record(cd, m, w0, w1)
            if r is not None:
                pairs_.append((r, cd))
        cands = [pr for pr in pairs_
                 if EV.FAMILY.get(pr[0]["type"]) == "box"]
        for g in g2:
            if g["spec_type"] != "BOX":
                continue
            right = [(r, cd) for r, cd in cands
                     if F.cand_right(g, r, m)]
            if not right:
                continue                       # oracle miss
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            tau = min(tau, w1)
            ft = _pkl(variant, h8, rec["date"], tau)
            if not ft:
                continue
            e_t = pickle.load(open(ft, "rb"))
            live, _em = live_records(e_t, m, w0, tau)
            osc = {o.id: getattr(o, "score", None)
                   for o in e_t.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            smap = RK.score_map(e_t)
            ranked = RK.rank_live(live, smap)
            boxes = [r for r in ranked
                     if EV.FAMILY.get(r["type"]) == "box"]
            match_live = [r for r in boxes if V2.match(g, r, m)]
            top = boxes[0] if boxes else None
            top_hit = top is not None and V2.match(g, top, m)
            outs = collections.Counter(cd["outcome"]
                                       for _r, cd in right)
            # the right cand's best logged score (if salience scored it)
            rscore = max((cd.get("score") for _r, cd in right
                          if cd.get("score") is not None),
                         default=None)
            fate = ("born" if outs.get("born")
                    else "rate" if outs.get("rate_limited")
                    else "nms" if outs.get("nms_suppressed")
                    else "prop")
            summ["coverable" if match_live else "uncoverable"] += 1
            if match_live:
                summ["hit@1" if top_hit else "match_not_top"] += 1
            rows.append({
                "id": rec["id"], "tau": tau, "fate": fate,
                "n_live_box": len(boxes), "coverable": bool(match_live),
                "top_hit": top_hit,
                "top": None if top is None else {
                    "route": top.get("why"), "score": top.get("score"),
                    "lo": top.get("lo"), "hi": top.get("hi"),
                    "t0": top.get("t0"), "born": top.get("t_birth")},
                "match_rank": (boxes.index(match_live[0]) + 1
                               if match_live else None),
                "match_score": (match_live[0].get("score")
                                if match_live else None),
                "right_score": rscore,
                "g_lo": g.get("price_lo"), "g_hi": g.get("price_hi"),
                "outs": dict(outs)})
    print("variant=%s hash=%s" % (variant, h8))
    print("summary:", dict(summ))
    print("%-7s %-5s %-5s %-8s %-6s %-9s %-8s %-8s %s" % (
        "panel", "tau", "fate", "coverable", "hit@1", "top_route",
        "top_sco", "right_sco", "top_edges vs golden"))
    for r in sorted(rows, key=lambda x: (x["id"], x["tau"])):
        te = ""
        if r["top"]:
            te = "%.1f-%.1f vs %.1f-%.1f" % (
                r["top"]["lo"], r["top"]["hi"],
                (r["g_lo"] or 0) * 1e4, (r["g_hi"] or 0) * 1e4)
        print("%-7s %-5d %-5s %-8s %-6s %-9s %-8s %-8s %s" % (
            r["id"], r["tau"], r["fate"], r["coverable"], r["top_hit"],
            (r["top"]["route"] or "")[:9] if r["top"] else "-",
            "%.2f" % r["top"]["score"]
            if r["top"] and r["top"]["score"] is not None else "-",
            "%.2f" % r["right_score"]
            if r["right_score"] is not None else "-", te))


if __name__ == "__main__":
    main()
