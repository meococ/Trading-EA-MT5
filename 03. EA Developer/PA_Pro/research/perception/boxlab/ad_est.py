"""AD-EST (Ruling 86) — "adopt, don't yield" offline estimate.

PART 1 diagnostics:
  1a. box@1 at each golden tau: identity age / band-version age /
      drawn width vs the author's box length (med 17b).
  1b. per E3 edge-matched miss: did the incumbent rewrite inside the
      candidate's pool window; to what band; and which clause of the
      uip_rewrite trigger (pipes.py) declined when it did not.

PART 2 simulate AD on the ev-UIP incumbent:
  trigger: pool box cand alive at j (pending / suppressed while
  fam_n>=1) AND c.first > incumbent's last write AND close[j] inside
  c.band+-tol_e AND close[j] outside incumbent's current band+-tol_e.
  AD-a: trigger alone.  AD-b: + current band version box_broken
  (TT-3, j_from = incumbent t_left / adopted t_left) AND c.first >
  exit_bar.
  Effect: append a new band version (j, c.lo, c.hi, c.t0) to the
  incumbent's chain; c consumed.  Real uip_birth/uip_rewrite events
  keep applying — path dependence preserved.
Read-only.  Writes boxlab/ad_est.jsonl only.
"""

import glob
import json
import os
import pickle
import re
import sys
from collections import Counter, defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)
sys.path.insert(0, HERE)

import common as C                       # noqa: E402
import eval as EV                       # noqa: E402
import eval_v2 as V2                    # noqa: E402
import cache as CA                      # noqa: E402
import trade_tags as TT                 # noqa: E402
from snapshot import tau_of, live_records  # noqa: E402
from kernel import FAMILY               # noqa: E402

from ys_est import (VAR, HASH, BOXK, TERM, pkl_for, ema25, jb,
                    ranked_at, band_seq, band_at, cand_alive_map,
                    pending_at)        # noqa: E402

NAMED12 = ("9.10c", "9.11b", "9.17b", "9.25a", "9.2b", "9.33c",
           "9.36c", "9.40a", "9.42b", "9.48b", "9.52a", "9.57b")

# uip_rewrite trigger constants (pipes.py:66-67)
DTOL, SEP, PBSEP, COOL = 2.0, 8, 8, 10
HMIN, HMAX, WIN = 6.0, 34.0, 600


def ev_object(e):
    """the persistent UIP incumbent (meta_ev_route box), if any."""
    evs = [o for o in e.objects
           if o.type == "BOX" and o.geometry.get("meta_ev_route")]
    return evs[-1] if evs else None


def classify_pivot(e, piv, i, born):
    """replay pipes.py:71-141 for one confirmed pivot at bar i.
    Returns (cls, cand|None): 'rd' (would rewrite), 'pb_only',
    'no_cand'."""
    idx, price, side = piv.t_ext, piv.price, piv.dir
    seq = [p for p in e.book.seq if p is not piv and p.t_ext <= idx]
    same = [p for p in seq if p.dir == side and idx - p.t_ext <= WIN]
    opp = [p for p in seq if p.dir == -side and idx - p.t_ext <= WIN]
    cands = []
    for prev in reversed(same):
        if idx - prev.t_ext < SEP:
            continue
        if abs(prev.price - price) <= DTOL:
            lo_i = min(prev.t_ext, idx)
            seg = e.bars[max(0, lo_i - 2):idx + 1]
            if side > 0:
                top = max(prev.price, price)
                bot = min(x["l"] for x in seg)
            else:
                bot = min(prev.price, price)
                top = max(x["h"] for x in seg)
            cands.append((bot, top, max(prev.t_ext, 0),
                          "ev_range_double_" +
                          ("top" if side > 0 else "bottom")))
            break
    if opp:
        last_opp = opp[-1]
        L, H = (price, last_opp.price) if side < 0 else \
            (last_opp.price, price)
        t0a = min(idx, last_opp.t_ext)
        pb_gate = 3 if not born else PBSEP
        if idx - t0a >= pb_gate:
            cands.append((L, H, t0a, "ev_pullback_end"))
    if not cands:
        return "no_cand", None
    top = cands[0]
    if top[3].startswith("ev_range_double"):
        return "rd", top
    return "pb_only", top


def simulate_ad(e, j_tau, h, l, c, abr, variant, cmap=None):
    """adoption chain on the ev-UIP incumbent.  Returns (versions,
    events): versions = [(bar, lo, hi, t0, src)] sorted by bar,
    src in {'real','adopt'}; events = [{bar, lo, hi, t0, route}]."""
    ob = ev_object(e)
    if ob is None or ob.t_birth is None or ob.t_birth > j_tau:
        return [], []
    if ob.t_right is not None and ob.t_right <= j_tau:
        return [], []           # incumbent dead before tau -> spent
    seq0 = band_seq(ob, e)
    if not seq0:
        return [], []
    if cmap is None:
        cmap = cand_alive_map(e)
    # versions carry j_from for TT-3: real versions anchor at the
    # object's t_left; adopted versions at c.t0 (ruling: t_left=c.t_left)
    vers = [[b_, lo_, hi_, t0_, "real", int(ob.t_left or 0)]
            for (b_, lo_, hi_, t0_) in seq0]
    events = []
    consumed = {}
    for j in range(j_tau + 1):
        cur = None
        for v in vers:
            if v[0] <= j:
                cur = v
        if cur is None:
            continue
        pool = pending_at(cmap, j)
        qual = []
        for r in pool:
            if consumed.get(id(r)):
                continue
            if r["first"] <= cur[0]:
                continue          # born before incumbent's last write
            tol = TT.tol_e(abr[j] if j < len(abr) else 5.0)
            if not (r["lo"] - tol <= c[j] <= r["hi"] + tol):
                continue          # close not inside c's band
            _b, lo, hi, t0 = cur[0], cur[1], cur[2], cur[3]
            if lo - tol <= c[j] <= hi + tol:
                continue          # close not outside incumbent band
            if variant == "b":
                bb = TT.s_box_broken(lo, hi, cur[5], j, c, abr)
                if not bb["bbroken"] or r["first"] <= bb["exit_bar"]:
                    continue
            qual.append(r)
        if not qual:
            continue
        best = max(qual, key=lambda r: r["score"])
        vers.append([j, float(best["lo"]), float(best["hi"]),
                     int(best.get("t0") or j), "adopt",
                     int(best.get("t0") or j)])
        vers.sort(key=lambda v: v[0])
        consumed[id(best)] = True
        events.append(dict(bar=j, lo=best["lo"], hi=best["hi"],
                           t0=best.get("t0"), route=best["route"],
                           first=best["first"], score=best["score"]))
    return vers, events


def band_of(vers, j):
    cur = None
    for v in vers:
        if v[0] <= j:
            cur = v
    return cur


def er_of(lo, hi, t0_bar, tau, m, w0):
    return dict(type="BOX", lo=lo, hi=hi,
                t0=int(m[min(int(t0_bar), len(m) - 1)]),
                t1=int(tau), w0=w0, w1=int(tau))


def main():
    recs = C.load_tune()
    byid = {r["id"]: r for r in recs}
    e3 = [json.loads(x) for x in
          open(os.path.join(HERE, "e3_diag.jsonl"), encoding="utf-8")]
    ecache, bcache, cmcache = {}, {}, {}

    def eng(date, tau):
        if (date, tau) not in ecache:
            ecache[(date, tau)] = pkl_for(date, tau)
        return ecache[(date, tau)]

    def day(date):
        if date not in bcache:
            _t, m, o, h, l, c = CA.bars(date)
            bcache[date] = (m, o, h, l, c, CA.abr(date), ema25(c))
        return bcache[date]

    def cmap(e):
        if id(e) not in cmcache:
            cmcache[id(e)] = cand_alive_map(e)
        return cmcache[id(e)]

    # ---- all golden decisions (all families) ----
    dec = []
    for rec in recs:
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        m, o, h, l, c, abr, ema = day(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        for g in gobjs:
            fam = EV.FAMILY.get(g["spec_type"])
            if fam not in ("box", "level", "line", "bracket") or \
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
            j_tau = jb(m, tau)
            ranked = ranked_at(e, m, w0, tau)
            top = [r for r in ranked if FAMILY.get(r["type"]) == fam]
            k = {"box": 1, "level": 1, "line": 2, "bracket": 1}[fam]
            hitrec = next((r for r in top[:k]
                           if V2.match(g, r, m)), None)
            dec.append(dict(panel=rec["id"], date=rec["date"],
                            tau=int(tau), j_tau=j_tau, w0=w0, fam=fam,
                            hit=hitrec is not None,
                            hit_id=hitrec["id"] if hitrec else None,
                            g=g, e=e, box1=(top[0] if top else None)))
    print("decisions:", dict(Counter((d["fam"], d["hit"]) for d in dec)))

    out = []

    # ================= PART 1a: box@1 age anatomy =================
    print("\n=== PART 1a: box@1 age anatomy (119) ===")
    stat = defaultdict(lambda: dict(id=[], ver=[], wid=[]))
    for d in dec:
        if d["fam"] != "box":
            continue
        b1 = d["box1"]
        if b1 is None:
            continue
        obj = next((o for o in d["e"].objects if o.id == b1["id"]),
                   None)
        if obj is None:
            continue
        seq = band_seq(obj, d["e"])
        v = band_at(seq, d["j_tau"])
        key = "hit" if d["hit"] else "miss"
        stat[key]["id"].append(d["j_tau"] - int(obj.t_birth))
        stat[key]["ver"].append(d["j_tau"] - int(v[0]))
        stat[key]["wid"].append(d["j_tau"] - int(v[3]))
    for key in ("hit", "miss"):
        for mname in ("id", "ver", "wid"):
            a = np.array(stat[key][mname], dtype=float)
            print("  %s %-3s n=%d med=%.0f p25=%.0f p75=%.0f"
                  % (key, mname, len(a), np.median(a),
                     np.percentile(a, 25), np.percentile(a, 75)))
            out.append(dict(item="p1a", grp=key, metric=mname,
                            n=len(a), med=float(np.median(a)),
                            p25=float(np.percentile(a, 25)),
                            p75=float(np.percentile(a, 75))))

    # ================= PART 1b: rewrite-in-window audit ============
    print("\n=== PART 1b: rewrite-in-window (E3 edge-matched) ===")
    em_rows = [r for r in e3 if r.get("edge_matched")]
    clause_rows = Counter()
    for r in em_rows:
        rec = byid[r["panel"]]
        e = eng(rec["date"], r["tau"])
        if e is None:
            continue
        m, o, h, l, c, abr, ema = day(rec["date"])
        inc = next((x for x in e.objects
                    if x.id == r["box1"]["id"]), None)
        if inc is None:
            continue
        j_tau = jb(m, r["tau"])
        w0c = int(r["cand"]["idx"]) if r["cand"] else 0
        pend_end = j_tau if r["killer"] == "proposed" \
            else int(r["kill_bar"])
        seq = band_seq(inc, e)
        wrotes = [ev for ev in inc.events
                  if ev[1] == "uip_rewrite"
                  and w0c <= ev[0] <= pend_end]
        row = dict(item="p1b", panel=r["panel"], tau=r["tau"],
                   inc=inc.id, window=[w0c, pend_end],
                   n_rewrite=len(wrotes), wrote_bands=[], clauses=[])
        glo, ghi = r["cand"]["lo"], r["cand"]["hi"]
        for ev in wrotes:
            _b, lo, hi, _t = band_at(seq, ev[0])
            a = abr[min(ev[0], len(abr) - 1)]
            row["wrote_bands"].append(
                [ev[0], round(lo, 1), round(hi, 1),
                 round(abs(lo - glo) / max(a, 0.1), 2),
                 round(abs(hi - ghi) / max(a, 0.1), 2)])
        # clause replay at every confirmed pivot inside the window
        # (incumbent exists -> _ev_uip_born=True -> pb gate = PBSEP)
        for j in range(w0c, min(pend_end, j_tau) + 1):
            pivs = [p for p in e.book.seq
                    if getattr(p, "t_conf", None) == j]
            if not pivs:
                row["clauses"].append((j, "no_confirmed_pivot"))
                continue
            for p in pivs:
                cls, cd = classify_pivot(e, p, j, True)
                row["clauses"].append((j, cls))
        for cname in {c2 for _j, c2 in row["clauses"]}:
            clause_rows[cname] += 1
        out.append(row)
    n_wr = sum(1 for r in out
               if r["item"] == "p1b" and r["n_rewrite"] > 0)
    print("  edge-matched rows: %d | incumbent rewrote inside window: "
          "%d" % (len(em_rows), n_wr))
    print("  clause presence per row:", dict(clause_rows))

    # ================= PART 2: AD simulation =======================
    print("\n=== PART 2: AD simulation ===")
    sims = {}

    def sim(d, variant):
        key = (d["date"], d["tau"], variant)
        if key not in sims:
            sims[key] = simulate_ad(d["e"], d["j_tau"], *day(d["date"])[2:6],
                                    variant, cmap(d["e"]))
        return sims[key]

    # item 1: box hits lost / gained
    for variant in ("a", "b"):
        lost, gained = [], []
        for d in dec:
            if d["fam"] != "box":
                continue
            vers, evs = sim(d, variant)
            if not vers:
                continue      # no ev incumbent -> nothing changes
            v = band_of(vers, d["j_tau"])
            if v is None:
                continue
            er = er_of(v[1], v[2], v[5], d["tau"],
                       day(d["date"])[0], d["w0"])
            ok = V2.match(d["g"], er, day(d["date"])[0])
            if d["hit"] and not ok:
                lost.append((d["panel"], d["tau"], d["hit_id"],
                             len(evs)))
            if not d["hit"] and ok:
                gained.append((d["panel"], d["tau"], len(evs)))
        print("  AD-%s: box hits lost %d %s | gained %d %s | net %+d"
              % (variant, len(lost), lost, len(gained), gained,
                 len(gained) - len(lost)))
        out.append(dict(item="ad_hits", variant=variant,
                        lost=lost, gained=gained,
                        net=len(gained) - len(lost)))

    # item 2: churn
    for variant in ("a", "b"):
        per_pan = []
        hit_pan = []
        for d in dec:
            if d["fam"] != "box":
                continue
            _v, evs = sim(d, variant)
            per_pan.append((d["panel"], len(evs)))
            if d["hit"]:
                hit_pan.append(len(evs))
        cnt = np.array([n for _p, n in per_pan], dtype=float)
        print("  AD-%s adoptions/panel: med=%.0f p90=%.0f max=%d | "
              "hit panels: %s" % (variant, np.median(cnt),
                                  np.percentile(cnt, 90),
                                  int(cnt.max()), hit_pan))
        out.append(dict(item="ad_churn", variant=variant,
                        per_panel=per_pan, hit_panels=hit_pan,
                        med=float(np.median(cnt)),
                        p90=float(np.percentile(cnt, 90)),
                        mx=int(cnt.max())))

    # item 3: cross-family at-risk
    print("\n=== ITEM 3: cross-family at-risk ===")
    yflips = [json.loads(l)["flip"] for l in open(
        os.path.join(HERE, "y_measure_y1.jsonl"), encoding="utf8")
        if '"flip"' in l]
    ylost = [f for f in yflips
             if f["parent_hit"] and not f["y_hit"]
             and f["fam"] in ("level", "line", "bracket")]
    for variant in ("a", "b"):
        risk = defaultdict(list)
        for d in dec:
            if d["fam"] == "box" or not d["hit"]:
                continue
            vers, evs = sim(d, variant)
            evs = [x for x in evs if x["bar"] <= d["j_tau"]]
            if not evs:
                continue
            hit_obj = next((o for o in d["e"].objects
                            if o.id == d["hit_id"]), None)
            why = []
            for x in evs:
                # channel (a): level seeded at the incumbent's
                # pre-adoption band edge (carry routes spawn at
                # box edges: boxes.py:1211-1223)
                if hit_obj is not None and hit_obj.type in (
                        "LEVEL_CARRIED", "MINI_LEVEL") and \
                        hit_obj.why in ("broken_box_edge_up",
                                        "broken_box_edge_down",
                                        "congestion_edge"):
                    why.append("carry-band-rewritten")
                # channel (b): caps — adoption is a rewrite, not a
                # birth: consumes no signal/context/hard slot and no
                # famlive (STEP 0) -> nothing
            if why:
                risk[d["fam"]].append((d["panel"], d["tau"],
                                       d["hit_id"], why))
        yleg = []
        for f in ylost:
            d = next((x for x in dec
                      if x["panel"] == f["panel"]
                      and x["tau"] == f["tau"]), None)
            n = None
            if d is not None:
                _v, evs = sim(d, variant)
                n = len([x for x in evs if x["bar"] <= d["j_tau"]])
            yleg.append((f["panel"], f["tau"], f["fam"],
                         f["parent_pick"], n))
        for fam in ("level", "line", "bracket"):
            print("  AD-%s %s at-risk: %d %s"
                  % (variant, fam, len(risk[fam]), risk[fam]))
            out.append(dict(item="ad_atrisk", variant=variant, fam=fam,
                            rows=risk[fam]))
        print("  AD-%s arm-Y lost hits: %s" % (variant, yleg))
        out.append(dict(item="ad_armY", variant=variant, rows=yleg))

    # item 4: 12 fixed review panels
    print("\n=== ITEM 4: fixed review panels ===")
    review = json.load(open(
        os.path.join(PERC, "review", "review_panels.json")))
    for p in review["panels"]:
        if p["name"] not in NAMED12:
            continue
        rec = byid.get(p["name"])
        if rec is None:
            continue
        tau = int(p["tau"])
        e = eng(rec["date"], tau)
        if e is None:
            continue
        m, o, h, l, c, abr, ema = day(rec["date"])
        j_tau = jb(m, tau)
        d = dict(panel=p["name"], date=rec["date"], tau=tau,
                 j_tau=j_tau, w0=rec["window"]["x0"], fam="box",
                 hit=False, hit_id=None, g=None, e=e)
        gobjs, _u, _to = EV.gold_objects(rec)
        gs = [g for g in gobjs if g["spec_type"] in V2.BOX_TYPES]
        for vn in ("a", "b"):
            vers, evs = sim(d, vn)
            v = band_of(vers, j_tau) if vers else None
            ok = False
            if v is not None:
                er = er_of(v[1], v[2], v[5], tau, m, d["w0"])
                ok = any(V2.match(g, er, m) for g in gs)
            print("  %-6s AD-%s adoptions=%d box@1-author-match=%s "
                  "final=[%s]" % (p["name"], vn, len(evs), ok,
                                  ",".join("%.1f" % x for x in
                                           ((v[1], v[2]) if v
                                            else ()))))
            out.append(dict(item="ad_review", variant=vn,
                            panel=p["name"], adoptions=len(evs),
                            author_match=ok,
                            final=[v[1], v[2]] if v else None,
                            evs=[(x["bar"], x["route"]) for x in evs]))

    with open(os.path.join(HERE, "ad_est.jsonl"), "w",
              encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, default=str) + "\n")
    print("\nwrote ad_est.jsonl (%d rows)" % len(out))


if __name__ == "__main__":
    main()
