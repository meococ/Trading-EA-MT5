"""e3_diag.py — R82 s82.7 E3 diagnosis: THE CURRENT BOX IS MISSING.

Read-only on canonical caches (uip2_pbbirth@8361fe85 == C-3 @fa2e52e5
default flags, canonical-identical per EVAL-AUDIT A1 623/623).

For every golden BOX CURRENT at the decision tau (drawn right edge
t1 >= tau-15: covers tau, open right, or ended within 3 bars) that C-3
MISSES at box@1 (rank-1 live box-family record fails ruler match),
classify the miss into exactly one of:

  NEVER_BORN     no BOX/CONTEXT_RANGE/RANGE_OPEN cand in cand_log
                 overlapping the golden in time AND price.
  BORN_KILLED    a matching/overlapping cand or object existed and was
                 killed before tau — generation vetoes (vetoed_*,
                 dedup_existing, route_shadow, uip_spent, uip_skip_pb,
                 below_min_score) or an object death event.
  LIVE_OUTRANKED a live box-family object at tau ruler-matches the
                 golden but a different box holds rank-1.
  BUDGET_CUT     the best overlapping cand (edge-matching preferred)
                 was refused by the budget/rank machinery: outranked,
                 nms_suppressed, joint_capped, expired (pool TTL) or
                 still proposed-pending at tau.

Then: S2 overlap on LIVE_OUTRANKED (k consecutive closes beyond drawn
edges by > tol_e within [drawn left edge, tau]; tol from
trade_tags.tol_e), and a NEVER_BORN shape summary.

Outputs: boxlab/e3_diag.jsonl + printed tables (into E3_DIAG.md).
"""
import glob
import json
import os
import pickle
import sys
from collections import Counter, defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)

import common as C                      # noqa: E402
import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import cache as CA                     # noqa: E402
from snapshot import tau_of, live_records  # noqa: E402
from recall_at_k import rank_live, score_map  # noqa: E402
from kernel import FAMILY              # noqa: E402
from trade_tags import tol_e           # noqa: E402

VAR, HASH = "uip2_pbbirth", "8361fe85"
BUDGET_OUT = {"outranked", "nms_suppressed", "joint_capped", "expired",
              "proposed", "rate_limited"}
GEN_OUT = {"vetoed_height", "vetoed_cooldown", "dedup_existing",
           "route_shadow", "uip_spent", "uip_skip_pb",
           "below_min_score"}
BOXK = {"BOX", "CONTEXT_RANGE", "RANGE_OPEN"}
CONG_MIN_BARS, CONG_H_ABR = 6, 4.0     # boxes.py:843-878 cong gates


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


def eng_at(e, m, w0, tau):
    live, _em = live_records(e, m, w0, tau)
    osc = {o.id: getattr(o, "score", None) for o in e.objects}
    for r in live:
        r["score"] = osc.get(r["id"])
    return rank_live(live, score_map(e))


def jb(m, cet):
    return min(int(np.searchsorted(m, cet)), len(m) - 1)


def diagnose(e, g, m, c, ema, abr, w0, w1, tau):
    glo, ghi = g["price_lo"] * 1e4, g["price_hi"] * 1e4
    tol = V2.tol_px(g)
    j_tau = jb(m, tau)
    jg0 = jb(m, g["t0"])
    jg1 = jb(m, g.get("t1") or w1)

    ranked = eng_at(e, m, w0, tau)
    boxes = [r for r in ranked if FAMILY.get(r["type"]) == "box"]
    box1 = boxes[0] if boxes else None
    row = dict(g_geom=[round(glo, 1), round(ghi, 1)],
               g_span=[g["t0"], g.get("t1")],
               box1=_brief_rec(box1, m, c, j_tau))
    if box1 is not None and V2.match_detail(g, box1, m)[0]:
        row["cls"] = "HIT"
        return row
    live_match = [r for r in boxes if V2.match_detail(g, r, m)[0]]
    if live_match:
        r = live_match[0]
        row.update(cls="LIVE_OUTRANKED",
                   match=dict(id=r["id"], type=r["type"],
                              why=r.get("why"),
                              rank=boxes.index(r) + 1,
                              lo=round(r["lo"], 1),
                              hi=round(r["hi"], 1)))
        return row

    cands = [cd for cd in (e.cand_log or [])
             if cd.get("kind") in BOXK and cd["idx"] <= j_tau
             and _t_overlap(cd, jg0, jg1)
             and _p_overlap(cd, glo, ghi)]
    if not cands:
        row["cls"] = "NEVER_BORN"
        row["shape"] = shape(e, g, glo, ghi, j_tau, jg0, jg1,
                             m, ema, abr)
        return row

    edge = [cd for cd in cands
            if abs(cd["top"] - ghi) <= tol
            and abs(cd["bottom"] - glo) <= tol]
    pool = edge if edge else cands
    born = [cd for cd in pool if cd["outcome"] in ("born", "uip_birth")]
    if born:
        cd = born[-1]
        killer, when = _object_fate(e, cd, j_tau)
        row.update(cls="BORN_KILLED", killer=killer, kill_bar=when,
                   cand=_cand_brief(cd), edge_matched=bool(edge))
        return row
    cd = sorted(pool, key=lambda x: x["idx"])[-1]
    out = cd["outcome"]
    cls = "BUDGET_CUT" if out in BUDGET_OUT else "BORN_KILLED"
    killer = "overwritten_by_next_write" if out == "uip_rewrite" \
        else out
    row.update(cls=cls, killer=killer, kill_bar=int(cd["idx"]),
               kill_cet=int(cd.get("cet_min") or 0),
               cand=_cand_brief(cd), edge_matched=bool(edge),
               n_overlap=len(cands), n_edge=len(edge))
    return row


def _brief_rec(r, m, c, j_tau):
    if r is None:
        return None
    jb_ = jb(m, r.get("t_birth") or 0)
    px = c[j_tau]
    dist = 0.0 if r["lo"] <= px <= r["hi"] else min(
        abs(px - r["lo"]), abs(px - r["hi"]))
    return dict(id=r["id"], type=r["type"], why=r.get("why"),
                lo=round(r["lo"], 1), hi=round(r["hi"], 1),
                t_birth=r.get("t_birth"), t0=r.get("t0"),
                age_bars=int(j_tau - jb_), dist_pips=round(dist, 1))


def _t_overlap(cd, jg0, jg1):
    t0 = cd.get("t0")
    if t0 is None:
        t0 = cd.get("t_left")
    if t0 is None:
        return False
    return t0 <= jg1 and cd["idx"] >= jg0


def _p_overlap(cd, glo, ghi):
    b, t = cd.get("bottom"), cd.get("top")
    return b is not None and t is not None and b <= ghi and t >= glo


def _cand_brief(cd):
    return dict(route=cd.get("route"), idx=int(cd["idx"]),
                cet=int(cd.get("cet_min") or 0),
                lo=round(cd.get("bottom", 0), 1),
                hi=round(cd.get("top", 0), 1),
                t0=int(cd.get("t0") if cd.get("t0") is not None else -1),
                outcome=cd.get("outcome"))


def _object_fate(e, cd, j_tau):
    """Object born at bar cd['idx'] (o.t_birth is a bar index)."""
    for o in e.objects:
        if o.t_birth != cd["idx"] or o.type not in BOXK:
            continue
        if o.state == "ACTIVE":
            return "still_active_wrong_geom", j_tau
        for ev in reversed(o.events or []):
            if ev[0] <= j_tau and ev[1] in (
                    "close", "killed", "deleted", "outranked",
                    "joint_cap", "retire_far"):
                return "%s:%s" % (ev[1], str(ev[2])[:40]), int(ev[0])
        return "closed", int(o.t_right or j_tau)
    return "born_object_not_found", int(cd["idx"])


def shape(e, g, glo, ghi, j_tau, jg0, jg1, m, ema, abr):
    """NEVER_BORN anatomy + which generator requirement fails."""
    a = abr[j_tau] if j_tau < len(abr) else 5.0
    h_pips = ghi - glo
    w_bars = int(round(((g.get("t1") or m[j_tau]) - g["t0"]) / 5.0))
    mid = (glo + ghi) / 2.0
    d_ema = (mid - ema[j_tau]) / a if a else None
    # cong path: run of >=6 bars inside window whose envelope <= 4*ABR
    seg_ok = w_bars >= CONG_MIN_BARS and (h_pips <= CONG_H_ABR * a)
    # event path: a same-side pivot pair inside the window
    pivs = [p for p in e.book.seq
            if p.t_conf <= j_tau and jg0 <= p.t_ext <= jg1]
    pair = len(pivs) >= 2
    fails = []
    if w_bars < CONG_MIN_BARS:
        fails.append("width<%db" % CONG_MIN_BARS)
    if h_pips > CONG_H_ABR * a:
        fails.append("h>%.1fABR" % CONG_H_ABR)
    if h_pips < 6.0:
        fails.append("h<6p")
    if not pair:
        fails.append("no_pivot_pair")
    return dict(width_bars=w_bars, height_pips=round(h_pips, 1),
                height_abr=round(h_pips / a, 2) if a else None,
                dist_ema_abr=round(d_ema, 2) if d_ema is not None
                else None,
                n_pivots_in_win=len(pivs), cong_legal=bool(seg_ok),
                fails=fails)


def s2_closed(lo, hi, j_left, j_tau, c, abr, k):
    run_up = run_dn = 0
    for j in range(max(0, j_left), j_tau + 1):
        t = tol_e(abr[j] if j < len(abr) else 5.0)
        if c[j] > hi + t:
            run_up += 1
            run_dn = 0
        elif c[j] < lo - t:
            run_dn += 1
            run_up = 0
        else:
            run_up = run_dn = 0
        if run_up >= k or run_dn >= k:
            return j
    return None


def main():
    recs = C.load_tune()
    review = json.load(open(
        os.path.join(PERC, "review", "review_panels.json")))
    NAMED = ("9.10c", "9.11b", "9.17b", "9.25a", "9.2b", "9.33c",
             "9.52a")
    named = {p["name"]: (p["date"], int(p["tau"]))
             for p in review["panels"] if p["name"] in NAMED}
    ecache = {}

    def eng(date, tau):
        key = (date, tau)
        if key not in ecache:
            ecache[key] = pkl_for(date, tau)
        return ecache[key]

    out_rows = []

    print("=== ITEM 1: 7 named panels at review tau ===")
    for name, (date, tau) in sorted(named.items()):
        rec = next(r for r in recs if r["id"] == name)
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        _t, m, o, h, l, c = CA.bars(date)
        abr = CA.abr(date)
        ema = ema25(c)
        e = eng(date, tau)
        gobjs, _u, _to = EV.gold_objects(rec)
        cur = [g for g in gobjs
               if g["spec_type"] in V2.BOX_TYPES
               and V2.scorable(g, w0, w1)
               and g["t0"] <= tau
               and (g.get("t1") or w1) >= tau - 15]
        if not cur:
            out_rows.append(dict(panel=name, tau=tau,
                                 cls="NO_AUTHOR_BOX", named=True))
            print("%-7s tau=%-4d NO current author box" % (name, tau))
            continue
        for g in cur:
            row = diagnose(e, g, m, c, ema, abr, w0, w1, tau)
            row.update(panel=name, tau=tau, named=True)
            out_rows.append(row)
            print("%-7s tau=%-4d cls=%-14s g=[%.1f,%.1f] box1=%s" %
                  (name, tau, row["cls"], row["g_geom"][0],
                   row["g_geom"][1],
                   (row.get("box1") or {}).get("id")))

    print("\n=== ITEM 2: all TUNE golden box decisions ===")
    cls_ct = Counter()
    bycls = defaultdict(list)
    for rec in recs:
        d = rec["id"]
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        _t, m, o, h, l, c = CA.bars(rec["date"])
        abr = CA.abr(rec["date"])
        ema = ema25(c)
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
            e = eng(rec["date"], tau)
            if e is None:
                continue
            row = diagnose(e, g, m, c, ema, abr, w0, w1, tau)
            if row["cls"] == "HIT":
                continue
            row.update(panel=d, tau=int(tau), named=False)
            cls_ct[row["cls"]] += 1
            bycls[row["cls"]].append((d, int(tau), row))
            out_rows.append(row)
    print("miss classes:", dict(cls_ct))
    for k in ("NEVER_BORN", "BORN_KILLED", "LIVE_OUTRANKED",
              "BUDGET_CUT"):
        v = bycls.get(k, [])
        print("  %-14s %3d  e.g. %s" %
              (k, len(v), [(x[0], x[1]) for x in v[:4]]))

    print("\n=== ITEM 3: S2 overlap on outrankers ===")
    s2 = {2: 0, 3: 0}
    n_out = len(bycls.get("LIVE_OUTRANKED", []))
    for name, tau, row in bycls.get("LIVE_OUTRANKED", []):
        rec = next(r for r in recs if r["id"] == name)
        _t, m, o, h, l, c = CA.bars(rec["date"])
        abr = CA.abr(rec["date"])
        b1 = row.get("box1")
        if b1 is None:
            continue
        j_tau = jb(m, tau)
        j_left = jb(m, b1.get("t0") or b1.get("t_birth") or 0)
        for k in (2, 3):
            jb_ = s2_closed(b1["lo"], b1["hi"], j_left, j_tau, c, abr, k)
            if jb_ is not None:
                s2[k] += 1
            print("  %s@%d %-8s k%d close=%s" %
                  (name, tau, b1["id"], k, jb_))
    print("S2 closes the outranker: k2=%d k3=%d of %d outranked"
          % (s2[2], s2[3], n_out))

    nb = [r for _n, _t, r in bycls.get("NEVER_BORN", [])]
    if nb:
        ws = [r["shape"]["width_bars"] for r in nb]
        hs = [r["shape"]["height_abr"] for r in nb
              if r["shape"]["height_abr"]]
        ds = [abs(r["shape"]["dist_ema_abr"]) for r in nb
              if r["shape"]["dist_ema_abr"] is not None]
        print("\n=== ITEM 4: NEVER_BORN shape (n=%d) ===" % len(nb))
        print("  width bars: med %.0f p25 %.0f p75 %.0f" %
              (np.median(ws), np.percentile(ws, 25),
               np.percentile(ws, 75)))
        print("  height/ABR20: med %.2f p25 %.2f p75 %.2f" %
              (np.median(hs), np.percentile(hs, 25),
               np.percentile(hs, 75)))
        print("  |dist EMA25|/ABR20: med %.2f" % np.median(ds))
        fc = Counter(f for r in nb for f in r["shape"]["fails"])
        print("  gate fails:", dict(fc))
        print("  cong-legal windows:", sum(r["shape"]["cong_legal"]
                                           for r in nb))

    with open(os.path.join(HERE, "e3_diag.jsonl"), "w",
              encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, default=str) + "\n")
    print("\nwrote e3_diag.jsonl (%d rows)" % len(out_rows))


if __name__ == "__main__":
    main()
