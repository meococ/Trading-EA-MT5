"""y3_est.py — R84 s84.5: Y3 = yield on stale_far ALONE (offline estimate).

Read-only.  Parent C-3 @e7d13384 (TT-3 landed); canonical caches
run_uip2_pbbirth_8361fe85* are canonical-identical (TT-3 verified
ON==OFF==parent 623/623; only facts differ).  Tag predicates are
IMPORTED from research/perception/trade_tags.py — never re-derived.

Y3 semantics: a live box-family object whose stale_far predicate
holds is closed; freed slot goes to the pool.  We measure, at the
golden-decision tau:

  ITEM1 of the 16 C-3 box HITS: does the picked object carry
        stale_far at tau?  (>0 = hits Y3 loses)
  ITEM2 for each of the 59 BUDGET_CUT misses (e3_diag.jsonl): the
        incumbent box holding the slot at the cand's refusal bar —
        stale_far at that bar? at tau? stale onset <= cand pending
        end?  and did an edge-matched cand exist (E3 row flag)?
  ITEM3 the 7 named review panels (subset view of ITEM2).
  ITEM4 context: lifetime of the box@1 pick across the 119
        decisions; retest rate — box_broken incumbents revisited by
        price at the old band within 24 bars after exit_bar.

Outputs: boxlab/y3_est.jsonl + printed tables -> Y3_EST.md.
"""
import glob
import json
import os
import pickle
import re
import sys
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)

import common as C                      # noqa: E402
import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import cache as CA                     # noqa: E402
import trade_tags as TT                # noqa: E402
from snapshot import tau_of, live_records  # noqa: E402
from recall_at_k import rank_live, score_map  # noqa: E402
from kernel import FAMILY              # noqa: E402

VAR, HASH = "uip2_pbbirth", "8361fe85"
BOXK = {"BOX", "CONTEXT_RANGE", "RANGE_OPEN"}
RE_W = re.compile(r"\[([\d.]+),([\d.]+)\]\s*t0=(\d+)")


def pkl_for(date, tau):
    fs = glob.glob(os.path.join(
        CA.CACHE, "run_%s_%s*_%s_%d.pkl" % (VAR, HASH, date, tau)))
    return pickle.load(open(fs[0], "rb")) if fs else None


def ema25(c):
    k = 2.0 / 26.0
    out = np.empty(len(c))
    v = c[0]
    for i in range(len(c)):
        v = v + k * (c[i] - v)
        out[i] = v
    return out


def jb(m, cet):
    return min(int(np.searchsorted(m, cet)), len(m) - 1)


def ranked_at(e, m, w0, cet):
    live, _em = live_records(e, m, w0, cet)
    osc = {o.id: getattr(o, "score", None) for o in e.objects}
    for r in live:
        r["score"] = osc.get(r["id"])
    return rank_live(live, score_map(e)), live


def band_seq(o, e):
    """[(bar, lo, hi, t0)] versions for a box object, oldest first."""
    if (o.why or "").startswith("ev_") and o.type == "BOX":
        seq = []
        b = [cd for cd in e.cand_log
             if cd.get("outcome") == "uip_birth"
             and cd.get("idx") == o.t_birth]
        if b:
            seq.append((int(o.t_birth), float(b[-1]["bottom"]),
                        float(b[-1]["top"]), int(b[-1].get("t0") or 0)))
        for ev in o.events:
            if ev[1] == "uip_rewrite":
                mm = RE_W.search(str(ev[2]))
                if mm:
                    seq.append((int(ev[0]), float(mm.group(1)),
                                float(mm.group(2)),
                                int(mm.group(3))))
        if not seq:
            g = o.geometry
            seq = [(int(o.t_birth), float(g["bottom"]),
                    float(g["top"]), int(g.get("t0") or 0))]
        return seq
    g = o.geometry
    if "bottom" in g and "top" in g:
        return [(int(o.t_birth), float(g["bottom"]), float(g["top"]),
                 int(g.get("t0") or o.t_left or 0))]
    return []


def band_at(seq, j):
    cur = seq[0]
    for v in seq:
        if v[0] <= j:
            cur = v
        else:
            break
    return cur


def stale_at(lo, hi, jb_, j, h, l, c, abr):
    return TT.s_stale_far("box", {"bottom": lo, "top": hi}, jb_, j,
                          h, l, c, abr)


def stale_onset(o, e, j_from, j_to, h, l, c, abr):
    """first bar j in [birth, j_to] with stale_far on band(j)."""
    seq = band_seq(o, e)
    for j in range(j_from, j_to + 1):
        _b, lo, hi, _t = band_at(seq, j)
        s = stale_at(lo, hi, o.t_birth, j, h, l, c, abr)
        if s["stale"]:
            return j
    return None


def cand_window(e, cand):
    """pending window [first_idx, last_idx] of this cand's log entries
    (matched by route + band + anchor)."""
    sig = (cand.get("route"), round(cand.get("lo") or 0, 1),
           round(cand.get("hi") or 0, 1))
    idxs = [cd["idx"] for cd in e.cand_log
            if cd.get("kind") in BOXK
            and cd.get("route") == sig[0]
            and round(cd.get("bottom") or 0, 1) == sig[1]
            and round(cd.get("top") or 0, 1) == sig[2]]
    if not idxs:
        return int(cand["idx"]), int(cand["idx"])
    return int(min(idxs)), int(max(idxs))


def main():
    recs = C.load_tune()
    byid = {r["id"]: r for r in recs}
    e3 = [json.loads(x) for x in
          open(os.path.join(HERE, "e3_diag.jsonl"), encoding="utf-8")]
    NAMED = ("9.10c", "9.11b", "9.17b", "9.25a", "9.2b", "9.33c",
             "9.52a")
    review = json.load(open(
        os.path.join(PERC, "review", "review_panels.json")))
    named_tau = {p["name"]: int(p["tau"]) for p in review["panels"]
                 if p["name"] in NAMED}

    ecache, bcache = {}, {}

    def eng(date, tau):
        if (date, tau) not in ecache:
            ecache[(date, tau)] = pkl_for(date, tau)
        return ecache[(date, tau)]

    def day(date):
        if date not in bcache:
            _t, m, o, h, l, c = CA.bars(date)
            bcache[date] = (m, o, h, l, c, CA.abr(date), ema25(c))
        return bcache[date]

    out = []

    # ---------- collect all 119 decisions: box1 at tau ----------
    dec = []   # (panel, tau, row: hit?, box1_obj, j_tau)
    for rec in recs:
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        m, o, h, l, c, abr, ema = day(rec["date"])
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
            e = eng(rec["date"], tau)   # official: run stopped at tau
            if e is None:
                continue
            j_tau = jb(m, tau)
            ranked, _lv = ranked_at(e, m, w0, tau)
            boxes = [r for r in ranked
                     if FAMILY.get(r["type"]) == "box"]
            box1 = boxes[0] if boxes else None
            hit = bool(box1 is not None
                       and V2.match_detail(g, box1, m)[0])
            obj = next((x for x in e.objects
                        if box1 and x.id == box1["id"]), None)
            dec.append(dict(panel=rec["id"], tau=int(tau),
                            j_tau=j_tau, hit=hit, box1=box1,
                            obj=obj, date=rec["date"], w0=w0))

    print("decisions:", len(dec), "hits:", sum(d["hit"] for d in dec))

    # ---------- ITEM 1: stale_far on the 16 hits at tau ----------
    hits_lost = []
    for d in dec:
        if not d["hit"] or d["obj"] is None:
            continue
        m, o, h, l, c, abr, ema = day(d["date"])
        seq = band_seq(d["obj"], eng(d["date"], d["tau"]))
        _b, lo, hi, _t0 = band_at(seq, d["j_tau"])
        s = stale_at(lo, hi, d["obj"].t_birth, d["j_tau"], h, l, c, abr)
        onset = stale_onset(d["obj"], eng(d["date"], d["tau"]),
                            int(d["obj"].t_birth), d["j_tau"],
                            h, l, c, abr)
        bb = TT.s_box_broken(lo, hi, int(d["obj"].t_left or 0),
                             d["j_tau"], c, abr)
        d["hit_stale"] = s
        d["hit_band"] = [lo, hi]
        if s["stale"] or onset is not None:
            hits_lost.append((d["panel"], d["tau"], d["box1"]["id"],
                              round(s["stale_dist_abr"], 2),
                              s.get("stale_gap"), onset,
                              bb.get("bbroken")))
        out.append(dict(item="hit", panel=d["panel"], tau=d["tau"],
                        id=d["box1"]["id"], band=[round(lo, 1),
                        round(hi, 1)], stale=s["stale"],
                        dist_abr=round(s["stale_dist_abr"], 2),
                        gap=s.get("stale_gap"), onset=onset,
                        bbroken=bb["bbroken"]))
    print("\n=== ITEM 1: stale_far on the %d box hits at tau ==="
          % sum(d["hit"] for d in dec))
    for x in hits_lost:
        print("  LOST:", x)
    print("hits carrying stale_far at tau:", sum(
        1 for r in out if r.get("item") == "hit" and r["stale"]),
        "| with stale onset before tau:", len(hits_lost))

    # ---------- ITEM 2: BUDGET_CUT incumbents ----------
    print("\n=== ITEM 2: BUDGET_CUT incumbents ===")
    bc = [r for r in e3 if r["cls"] == "BUDGET_CUT"]
    n_stale_kill = n_stale_tau = n_onset_in_win = 0
    n_stale_edge = 0
    for r in bc:
        rec = byid[r["panel"]]
        w0 = rec["window"]["x0"]
        date = rec["date"]
        e = eng(date, r["tau"])
        m, o, h, l, c, abr, ema = day(date)
        j_tau = jb(m, r["tau"])
        j_kill = int(r["kill_bar"])
        # incumbent = the box1-at-tau object if live at kill bar,
        # else rank-1 box at kill bar
        inc = next((x for x in e.objects if x.id == r["box1"]["id"]),
                   None)
        live_kill = (inc is not None and inc.t_birth is not None
                     and int(inc.t_birth) <= j_kill
                     and (inc.t_right is None
                          or int(inc.t_right) > j_kill))
        if not live_kill:
            rk, _lv = ranked_at(e, m, w0, int(r["kill_cet"]))
            bx = [x for x in rk if FAMILY.get(x["type"]) == "box"]
            inc = next((x for x in e.objects
                        if bx and x.id == bx[0]["id"]), inc)
        seq = band_seq(inc, e)
        _b, lo_k, hi_k, _t0k = band_at(seq, j_kill)
        s_k = stale_at(lo_k, hi_k, inc.t_birth, j_kill, h, l, c, abr)
        _b, lo_t, hi_t, _t0t = band_at(seq, j_tau)
        s_t = stale_at(lo_t, hi_t, inc.t_birth, j_tau, h, l, c, abr)
        onset = stale_onset(inc, e, int(inc.t_birth), j_tau,
                            h, l, c, abr)
        w0c, w1c = cand_window(e, r["cand"])
        pend_end = j_tau if r["killer"] == "proposed" else w1c
        frees = onset is not None and onset <= pend_end
        edge = bool(r.get("edge_matched"))
        n_stale_kill += s_k["stale"]
        n_stale_tau += s_t["stale"]
        n_onset_in_win += frees
        n_stale_edge += (frees and edge)
        out.append(dict(item="budget_cut", panel=r["panel"],
                        tau=r["tau"], named=r.get("named"),
                        killer=r["killer"], edge_matched=edge,
                        inc_id=inc.id, inc_why=inc.why,
                        live_at_kill=bool(live_kill),
                        kill_bar=j_kill,
                        stale_kill=s_k["stale"],
                        dist_kill=round(s_k["stale_dist_abr"], 2),
                        gap_kill=s_k.get("stale_gap"),
                        stale_tau=s_t["stale"],
                        onset=onset, cand_win=[w0c, w1c],
                        frees=frees))
        print("  %-7s@%-4d inc=%-7s live@kill=%s stale@kill=%s "
              "stale@tau=%s onset=%s cwin=[%d,%d] frees=%s edge=%s"
              % (r["panel"], r["tau"], inc.id, live_kill,
                 s_k["stale"], s_t["stale"], onset, w0c, w1c,
                 frees, edge))
    print("incumbents stale@kill_bar: %d | stale@tau: %d | "
          "onset<=cand-pending-end: %d | of those edge-matched: %d"
          % (n_stale_kill, n_stale_tau, n_onset_in_win, n_stale_edge))

    # ---------- ITEM 3: the 7 named panels ----------
    print("\n=== ITEM 3: named panels ===")
    nr = [x for x in out
          if x.get("item") == "budget_cut" and x.get("named")]
    for x in nr:
        print("  %-7s stale@kill=%s onset=%s frees=%s edge=%s"
              % (x["panel"], x["stale_kill"], x["onset"],
                 x["frees"], x["edge_matched"]))
    for nm in named_tau:
        if nm not in [x["panel"] for x in nr]:
            print("  %-7s (no current author box)" % nm)

    # ---------- ITEM 4a: box@1 lifetime ----------
    ages, spans = [], []
    for d in dec:
        ob = d["obj"]
        if ob is None:
            continue
        m, o, h, l, c, abr, ema = day(d["date"])
        ages.append(d["j_tau"] - int(ob.t_birth))
        last = int(ob.t_right) if ob.t_right is not None else len(m) - 1
        spans.append(last - int(ob.t_birth))
    print("\n=== ITEM 4a: box@1 lifetime (bars) ===")
    print("  age@tau: med %.0f p25 %.0f p75 %.0f max %.0f (n=%d)"
          % (np.median(ages), np.percentile(ages, 25),
             np.percentile(ages, 75), max(ages), len(ages)))
    print("  lifespan: med %.0f p25 %.0f p75 %.0f max %.0f"
          % (np.median(spans), np.percentile(spans, 25),
             np.percentile(spans, 75), max(spans)))

    # ---------- ITEM 4b: retest within 24 bars of exit_bar ----------
    print("\n=== ITEM 4b: retest of box_broken incumbents ===")
    seen = set()
    n_bb = n_rt = 0
    for d in dec:
        ob = d["obj"]
        if ob is None or (d["date"], ob.id) in seen:
            continue
        seen.add((d["date"], ob.id))
        m, o, h, l, c, abr, ema = day(d["date"])
        e = eng(d["date"], d["tau"])
        seq = band_seq(ob, e)
        _b, lo, hi, t0v = band_at(seq, d["j_tau"])
        jfrom = t0v if t0v else int(ob.t_left or 0)
        bb = TT.s_box_broken(lo, hi, jfrom, d["j_tau"], c, abr)
        if not bb["bbroken"]:
            continue
        n_bb += 1
        xb = bb["exit_bar"]
        retest = False
        for j in range(xb + 1, min(xb + 25, len(c))):
            t = TT.tol_e(abr[j])
            if l[j] <= hi + t and h[j] >= lo - t:
                retest = True
                break
        n_rt += retest
        out.append(dict(item="retest", panel=d["panel"], tau=d["tau"],
                        id=ob.id, band=[round(lo, 1), round(hi, 1)],
                        exit_bar=xb, clause=bb["break_clause"],
                        retest24=retest))
        print("  %-7s@%-4d %-7s exit=%d %s retest24=%s"
              % (d["panel"], d["tau"], ob.id, xb,
                 bb["break_clause"], retest))
    print("box_broken incumbents: %d | retested within 24 bars: %d"
          % (n_bb, n_rt))

    with open(os.path.join(HERE, "y3_est.jsonl"), "w",
              encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, default=str) + "\n")
    print("\nwrote y3_est.jsonl (%d rows)" % len(out))


if __name__ == "__main__":
    main()
