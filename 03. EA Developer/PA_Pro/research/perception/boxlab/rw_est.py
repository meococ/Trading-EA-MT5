"""RW-EST (Ruling 87) - "write the right band" offline estimate.

PART 0 diagnostics:
  0a. edge-error split DEFENDED vs OPPOSITE (ABR20): for the 24
      rewrite-in-window rows (written band vs the edge-matched cand)
      and for the 16 hits (written band vs golden).
  0b. on the 12 no_cand rows, per confirmed pivot: which clause binds
      (SEP: no same-side prev with idx-t_ext>=8; DTOL: all eligible
      prevs |dprice|>2.0) and whether |dprice|<=dtol(=tol_e) passes.

PART 1 simulate RW on the UIP write chain by replaying
pipes.py:50-179 verbatim over the confirmed-pivot stream:
  RW-E: range-double OPPOSITE edge = trade_tags.cluster_edge over the
        same seg (tol=tol_e); defended edge unchanged; pb bands
        unchanged; non-UIP boxes unchanged.
  RW-G: pair test |dprice| <= dtol (=max(1.0,0.25*abr)) instead of the
        fixed DTOL=2.0.
Approximations (STEP 0): object death fixed at the real t_right; the
score floor at birth is assumed to pass; a pivot's peer pivots are
those with t_conf <= i (engine appends on confirm).
Read-only. Writes boxlab/rw_est.jsonl only.
"""

import json
import os
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
from snapshot import tau_of             # noqa: E402
from kernel import FAMILY               # noqa: E402

from ys_est import (pkl_for, ema25, jb, ranked_at, band_seq, band_at)  # noqa: E402
from ad_est import ev_object, er_of     # noqa: E402

NAMED12 = ("9.10c", "9.11b", "9.17b", "9.25a", "9.2b", "9.33c",
           "9.36c", "9.40a", "9.42b", "9.48b", "9.52a", "9.57b")

# pipes.py:66-67 constants
DTOL, SEP, PBSEP, COOL = 2.0, 8, 8, 10
HMIN, HMAX, WIN = 6.0, 34.0, 600
CARRY = ("broken_box_edge_up", "broken_box_edge_down",
         "congestion_edge")
RE_ROUTE = re.compile(r"(ev_\w+)\s*->")


def replay_uip(e, j_tau, mode, other_seqs):
    """verbatim replay of pipes.py:50-179 on confirmed pivots.
    mode: 'base' | 'e' | 'g'.  Returns dict(vers, born, dead).
    vers = [(i, lo, hi, t_left, route)] (i = confirmation bar)."""
    ob = ev_object(e)
    dead = int(ob.t_right) if (ob is not None
                               and ob.t_right is not None) else None
    pbbirth = e.p["salience"].get("ev_uip_pb_birth")
    pivs = sorted((p for p in e.book.seq
                   if getattr(p, "t_conf", None) is not None
                   and p.t_conf <= j_tau), key=lambda p: p.t_conf)
    vers, born, alive = [], False, False
    last_ev_birth = -999
    for p in pivs:
        i = int(p.t_conf)
        idx, price, side = int(p.t_ext), float(p.price), int(p.dir)
        a = e.abr[i] if i < len(e.abr) else 5.0
        dtol = max(1.0, 0.25 * a)
        pair_tol = dtol if mode == "g" else DTOL
        seq = [q for q in e.book.seq
               if q is not p and getattr(q, "t_conf", None) is not None
               and q.t_conf <= i and q.t_ext <= idx]
        same = [q for q in seq
                if q.dir == side and idx - q.t_ext <= WIN]
        opp = [q for q in seq
               if q.dir == -side and idx - q.t_ext <= WIN]
        cands = []
        for prev in reversed(same):
            if idx - prev.t_ext < SEP:
                continue
            if abs(prev.price - price) <= pair_tol:
                lo_i = min(prev.t_ext, idx)
                seg = e.bars[max(0, lo_i - 2):idx + 1]
                if side > 0:
                    defended = max(prev.price, price)
                    if mode == "e":
                        wk = sorted(x["l"] for x in seg)
                        opposite = TT.cluster_edge(wk, TT.tol_e(a),
                                                   False)
                    else:
                        opposite = min(x["l"] for x in seg)
                    bot, top = opposite, defended
                else:
                    defended = min(prev.price, price)
                    if mode == "e":
                        wk = sorted((x["h"] for x in seg),
                                    reverse=True)
                        opposite = TT.cluster_edge(wk, TT.tol_e(a),
                                                   True)
                    else:
                        opposite = max(x["h"] for x in seg)
                    bot, top = defended, opposite
                cands.append((bot, top, max(prev.t_ext, 0),
                              "ev_range_double_" +
                              ("top" if side > 0 else "bottom")))
                break
        if opp:
            last_opp = opp[-1]
            L, H = (price, last_opp.price) if side < 0 else \
                (last_opp.price, price)
            t0a = min(idx, last_opp.t_ext)
            pb_gate = 3 if (pbbirth and not born) else PBSEP
            if idx - t0a >= pb_gate:
                cands.append((L, H, t0a, "ev_pullback_end"))
        if not cands:
            continue
        lo, hi, t_left, why = cands[0]
        if alive:
            if dead is not None and i >= dead:
                alive = False          # v1 death (approx: real bar)
            elif why.startswith("ev_range_double"):
                vers.append((i, lo, hi, t_left, why))
            continue
        if born:
            continue                   # uip_spent
        if not (HMIN - 0.01 <= hi - lo <= HMAX + 0.01):
            continue                   # vetoed_height
        if idx - last_ev_birth < COOL:
            continue                   # vetoed_cooldown
        dup = False
        for _o2, sq in other_seqs:
            if not sq:
                continue
            _b, lo2, hi2, _t = band_at(sq, i)
            if abs(hi2 - hi) <= dtol and abs(lo2 - lo) <= dtol:
                dup = True
                break                  # dedup_existing
        if dup:
            continue
        vers.append((i, lo, hi, t_left, why))     # uip_birth
        born, alive = True, True
        last_ev_birth = idx
    return dict(vers=vers, born=born, dead=dead)


def writes_with_route(o, e):
    """[(bar, route, lo, hi)] from uip_birth cand + uip_rewrite
    events (route parsed from the event detail)."""
    out = []
    b = [cd for cd in e.cand_log
         if cd.get("outcome") == "uip_birth"
         and cd.get("idx") == o.t_birth]
    if b:
        out.append((int(o.t_birth), b[-1].get("route"),
                    float(b[-1]["bottom"]), float(b[-1]["top"])))
    for ev in o.events:
        if ev[1] == "uip_rewrite":
            mm = re.search(r"\[([\d.]+),([\d.]+)\]", str(ev[2]))
            rm = RE_ROUTE.search(str(ev[2]))
            if mm:
                out.append((int(ev[0]),
                            rm.group(1) if rm else "?",
                            float(mm.group(1)), float(mm.group(2))))
    return out


def split_err(route, lo, hi, glo, ghi, a):
    """(defended_err, opposite_err) in ABR given route direction."""
    a = max(a, 0.1)
    if route.endswith("_top"):
        return abs(hi - ghi) / a, abs(lo - glo) / a
    if route.endswith("_bottom"):
        return abs(lo - glo) / a, abs(hi - ghi) / a
    return None, None


def main():
    recs = C.load_tune()
    byid = {r["id"]: r for r in recs}
    ad = [json.loads(x) for x in
          open(os.path.join(HERE, "ad_est.jsonl"), encoding="utf-8")]
    e3 = [json.loads(x) for x in
          open(os.path.join(HERE, "e3_diag.jsonl"), encoding="utf-8")]
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

    # ---- all golden decisions (same construction as ad_est) ----
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
                            tau=int(tau), j_tau=j_tau, w0=w0,
                            fam=fam, hit=hitrec is not None,
                            hit_id=hitrec["id"] if hitrec else None,
                            g=g, e=e, box1=(top[0] if top else None),
                            ranked=ranked))
    print("decisions:", dict(Counter((d["fam"], d["hit"]) for d in dec)))

    out = []

    # ================= PART 0a: defended vs opposite ==============
    print("\n=== PART 0a: edge split (ABR20) ===")
    e3em = {(r["panel"], r["tau"]): r for r in e3
            if r.get("edge_matched")}
    p1b = [r for r in ad if r.get("item") == "p1b"]
    stat = defaultdict(list)
    for r in p1b:
        if r["n_rewrite"] <= 0:
            continue
        r3 = e3em.get((r["panel"], r["tau"]))
        if r3 is None or not r3.get("cand"):
            continue
        rec = byid[r["panel"]]
        e = eng(rec["date"], r["tau"])
        m, _o, _h, _l, _c, abr, _e2 = day(rec["date"])
        inc = next((x for x in e.objects if x.id == r["inc"]), None)
        if inc is None:
            continue
        glo, ghi = r3["cand"]["lo"], r3["cand"]["hi"]
        _gg, _u, _to = EV.gold_objects(rec)
        gg = next((x for x in _gg
                   if x["spec_type"] in V2.BOX_TYPES), None)
        if gg is not None:
            glo_g, ghi_g = gg["price_lo"] * 1e4, gg["price_hi"] * 1e4
        w0c, pend_end = r["window"]
        for (bar, route, lo, hi) in writes_with_route(inc, e):
            if not (w0c <= bar <= pend_end):
                continue
            a = abr[min(bar, len(abr) - 1)]
            de, oe = split_err(route, lo, hi, glo, ghi, a)
            if de is not None:
                stat["cand_def"].append(de)
                stat["cand_opp"].append(oe)
            if gg is not None:
                de, oe = split_err(route, lo, hi, glo_g, ghi_g, a)
                if de is not None:
                    stat["gold_def"].append(de)
                    stat["gold_opp"].append(oe)
    # 16 hits: last write vs golden
    for d in dec:
        if d["fam"] != "box" or not d["hit"]:
            continue
        obj = next((x for x in d["e"].objects
                    if x.id == d["hit_id"]), None)
        if obj is None:
            continue
        ws = [w for w in writes_with_route(obj, d["e"])
              if w[0] <= d["j_tau"]]
        if not ws:
            continue
        bar, route, lo, hi = ws[-1]
        glo, ghi = d["g"]["price_lo"] * 1e4, d["g"]["price_hi"] * 1e4
        a = day(d["date"])[5][min(bar, len(day(d["date"])[5]) - 1)]
        de, oe = split_err(route, lo, hi, glo, ghi, a)
        if de is None:
            stat["hit_pb"].append(d["panel"])
        else:
            stat["hit_def"].append(de)
            stat["hit_opp"].append(oe)
    for key in ("cand_def", "cand_opp", "gold_def", "gold_opp",
                "hit_def", "hit_opp"):
        arr = np.array(stat[key], dtype=float)
        if len(arr):
            print("  %-9s n=%d med=%.2f p75=%.2f"
                  % (key, len(arr), np.median(arr),
                     np.percentile(arr, 75)))
            out.append(dict(item="p0a", k=key, n=len(arr),
                            med=float(np.median(arr)),
                            p75=float(np.percentile(arr, 75))))
    print("  hits with pb-route last write:", stat["hit_pb"])

    # ================= PART 0b: clause binding ====================
    print("\n=== PART 0b: clause binding on no_cand rows ===")
    gate_rows = [r for r in p1b if r["n_rewrite"] == 0
                 and any(c2 == "no_cand" for _j, c2 in r["clauses"])]
    print("  gate rows:", len(gate_rows))
    cls_count = Counter()
    for r in gate_rows:
        rec = byid[r["panel"]]
        e = eng(rec["date"], r["tau"])
        if e is None:
            continue
        w0c, pend_end = r["window"]
        for j, c2 in r["clauses"]:
            if c2 != "no_cand":
                continue
            for p in e.book.seq:
                if getattr(p, "t_conf", None) != j:
                    continue
                idx, price, side = p.t_ext, p.price, p.dir
                a = e.abr[j] if j < len(e.abr) else 5.0
                dtol = max(1.0, 0.25 * a)
                seq = [q for q in e.book.seq
                       if q is not p
                       and getattr(q, "t_conf", None) is not None
                       and q.t_conf <= j and q.t_ext <= idx]
                same = [q for q in seq
                        if q.dir == side and idx - q.t_ext <= WIN]
                elig = [q for q in same if idx - q.t_ext >= SEP]
                if not elig:
                    cls_count["SEP"] += 1
                else:
                    dp = [abs(q.price - price) for q in elig]
                    cls_count["DTOL"] += 1
                    if min(dp) <= dtol:
                        cls_count["DTOL_pass_if_dtol"] += 1
                opp = [q for q in seq
                       if q.dir == -side and idx - q.t_ext <= WIN]
                if opp:
                    t0a = min(idx, opp[-1].t_ext)
                    cls_count["pb_gate_fail" if idx - t0a < PBSEP
                              else "pb_would_form"] += 1
                else:
                    cls_count["pb_no_opp"] += 1
    print("  clause counts:", dict(cls_count))
    out.append(dict(item="p0b", counts=dict(cls_count),
                    n_rows=len(gate_rows)))

    # ================= PART 1: RW simulation ======================
    print("\n=== PART 1: RW replay ===")
    maxjt = {}
    for d in dec:
        maxjt[d["date"]] = max(maxjt.get(d["date"], 0), d["j_tau"])
    # include review-panel taus
    review = json.load(open(
        os.path.join(PERC, "review", "review_panels.json")))
    for p in review["panels"]:
        if p["name"] in NAMED12 and p["name"] in byid:
            m = day(byid[p["name"]]["date"])[0]
            jt = jb(m, int(p["tau"]))
            dd = byid[p["name"]]["date"]
            maxjt[dd] = max(maxjt.get(dd, 0), jt)

    reps = {}
    for date, jt in maxjt.items():
        e = eng(date, jt_tau_cet(day(date)[0], jt))
        # fall back: eng at any cached tau for this date
        if e is None:
            taus = sorted({d["tau"] for d in dec if d["date"] == date})
            e = eng(date, taus[-1]) if taus else None
        if e is None:
            continue
        other = [(o2, band_seq(o2, e)) for o2 in e.objects
                 if o2.type == "BOX"
                 and not o2.geometry.get("meta_ev_route")]
        for mode in ("base", "e", "g"):
            reps[(date, mode)] = replay_uip(e, jt, mode, other)

    # fidelity: base replay vs real writes, sliced per decision tau
    n_exact = n_panel = 0
    diverge = []
    for d in dec:
        if d["fam"] != "box":
            continue
        rep = reps.get((d["date"], "base"))
        if rep is None:
            continue
        ob = ev_object(d["e"])
        real = [(v[0], round(v[1], 1), round(v[2], 1))
                for v in (band_seq(ob, d["e"]) if ob else [])
                if v[0] <= d["j_tau"]]
        sim = [(v[0], round(v[1], 1), round(v[2], 1))
               for v in rep["vers"] if v[0] <= d["j_tau"]]
        n_panel += 1
        if sim == real:
            n_exact += 1
        else:
            diverge.append((d["panel"], d["tau"],
                            len(sim), len(real)))
    print("  base replay == real writes: %d/%d panels; diverge %s"
          % (n_exact, n_panel, diverge[:8]))
    out.append(dict(item="fidelity", exact=n_exact, n=n_panel,
                    diverge=diverge))

    def sim_band(d, mode):
        """sim UIP band at d.j_tau -> (lo,hi,t_left) or None."""
        rep = reps.get((d["date"], mode))
        if rep is None:
            return None
        vs = [v for v in rep["vers"] if v[0] <= d["j_tau"]]
        if not vs:
            return None
        if rep["dead"] is not None and rep["dead"] <= d["j_tau"]:
            return None
        v = vs[-1]
        return (v[1], v[2], vs[0][3])

    def nonev_box1(d):
        for r in d["ranked"]:
            if FAMILY.get(r["type"]) != "box":
                continue
            obj = next((x for x in d["e"].objects
                        if x.id == r["id"]), None)
            if obj is not None and \
                    obj.geometry.get("meta_ev_route"):
                continue
            return r
        return None

    for mode in ("e", "g"):
        lost, gained = [], []
        for d in dec:
            if d["fam"] != "box":
                continue
            sb = sim_band(d, mode)
            if sb is not None:
                er = er_of(sb[0], sb[1], sb[2], d["tau"],
                           day(d["date"])[0], d["w0"])
                ok = V2.match(d["g"], er, day(d["date"])[0])
            else:
                r2 = nonev_box1(d)
                ok = bool(r2 and V2.match(d["g"], r2,
                                          day(d["date"])[0]))
            if d["hit"] and not ok:
                lost.append((d["panel"], d["tau"]))
            if not d["hit"] and ok:
                gained.append((d["panel"], d["tau"]))
        print("  RW-%s: lost %d %s | gained %d %s | net %+d"
              % (mode, len(lost), lost, len(gained), gained,
                 len(gained) - len(lost)))
        out.append(dict(item="rw_hits", variant=mode, lost=lost,
                        gained=gained,
                        net=len(gained) - len(lost)))

    # item 2: rewrites per panel
    for mode in ("e", "g"):
        psim, preal = [], []
        adds = []
        for d in dec:
            if d["fam"] != "box":
                continue
            rep = reps.get((d["date"], mode))
            n_sim = max(0, len([v for v in rep["vers"]
                                if v[0] <= d["j_tau"]]) - 1) \
                if rep else 0
            ob = ev_object(d["e"])
            n_real = max(0, len([v for v in
                                 (band_seq(ob, d["e"]) if ob else [])
                                 if v[0] <= d["j_tau"]]) - 1)
            psim.append(n_sim)
            preal.append(n_real)
            adds.append(n_sim - n_real)
        for nm, arr in (("sim", psim), ("real", preal)):
            a = np.array(arr, dtype=float)
            print("  RW-%s rewrites/panel %s: med=%.0f p90=%.0f "
                  "max=%d" % (mode, nm, np.median(a),
                              np.percentile(a, 90), int(a.max())))
        a2 = np.array(adds, dtype=float)
        print("    added>0 panels: %d (total +%d) | removed<0: %d "
              "(total %d)" % (int((a2 > 0).sum()), int(a2[a2 > 0].sum()),
                              int((a2 < 0).sum()), int(a2[a2 < 0].sum())))
        out.append(dict(item="rw_rewrites", variant=mode,
                        med_sim=float(np.median(psim)),
                        med_real=float(np.median(preal)),
                        added=int(a2[a2 > 0].sum()),
                        removed=int(-a2[a2 < 0].sum())))

    # item 3: cross-family at-risk
    print("\n=== ITEM 3: cross-family at-risk ===")
    yflips = [json.loads(l)["flip"] for l in open(
        os.path.join(HERE, "y_measure_y1.jsonl"), encoding="utf8")
        if '"flip"' in l]
    ylost = [f for f in yflips
             if f["parent_hit"] and not f["y_hit"]
             and f["fam"] in ("level", "line", "bracket")]
    for mode in ("e", "g"):
        risk = defaultdict(list)
        for d in dec:
            if d["fam"] == "box" or not d["hit"]:
                continue
            rep_b = reps.get((d["date"], "base"))
            rep_v = reps.get((d["date"], mode))
            if rep_v is None:
                continue
            hit_obj = next((x for x in d["e"].objects
                            if x.id == d["hit_id"]), None)
            ob = ev_object(d["e"])
            why = []
            v_b = [v for v in (rep_b["vers"] if rep_b else [])
                   if v[0] <= d["j_tau"]]
            v_v = [v for v in rep_v["vers"]
                   if v[0] <= d["j_tau"]]
            same_chain = [(x[0], round(x[1], 1), round(x[2], 1))
                          for x in v_b] == \
                         [(x[0], round(x[1], 1), round(x[2], 1))
                          for x in v_v]
            if hit_obj is not None and hit_obj.why in CARRY \
                    and not same_chain:
                why.append("carry-edge-differs")
            if ob is not None:
                real_born = ob.t_birth <= d["j_tau"]
                sim_born = bool(v_v)
                if real_born and not sim_born:
                    why.append("uip-never-born")
                elif real_born and sim_born and \
                        v_v[0][0] != int(ob.t_birth):
                    why.append("birth-bar-differs")
            if why:
                risk[d["fam"]].append((d["panel"], d["tau"],
                                       d["hit_id"], why))
        for fam in ("level", "line", "bracket"):
            print("  RW-%s %s at-risk: %d %s"
                  % (mode, fam, len(risk[fam]), risk[fam]))
            out.append(dict(item="rw_atrisk", variant=mode, fam=fam,
                            rows=risk[fam]))
        yleg = []
        for f in ylost:
            d = next((x for x in dec
                      if x["panel"] == f["panel"]
                      and x["tau"] == f["tau"]), None)
            if d is None:
                continue
            rep_b = reps.get((d["date"], "base"))
            rep_v = reps.get((d["date"], mode))
            diff = rep_v is not None and rep_b is not None and \
                [(x[0], round(x[1], 1), round(x[2], 1))
                 for x in rep_b["vers"] if x[0] <= d["j_tau"]] != \
                [(x[0], round(x[1], 1), round(x[2], 1))
                 for x in rep_v["vers"] if x[0] <= d["j_tau"]]
            yleg.append((f["panel"], f["tau"], f["fam"], diff))
        print("  RW-%s arm-Y lost rows, band-differs: %s"
              % (mode, yleg))
        out.append(dict(item="rw_armY", variant=mode, rows=yleg))

    # item 4: 12 fixed review panels
    print("\n=== ITEM 4: fixed review panels ===")
    for p in review["panels"]:
        if p["name"] not in NAMED12:
            continue
        rec = byid.get(p["name"])
        if rec is None:
            continue
        tau = int(p["tau"])
        m, _o, _h, _l, _c, _a, _e2 = day(rec["date"])
        j_tau = jb(m, tau)
        e = eng(rec["date"], tau)
        if e is None:
            continue
        gobjs, _u, _to = EV.gold_objects(rec)
        gs = [g for g in gobjs if g["spec_type"] in V2.BOX_TYPES]
        d = dict(j_tau=j_tau, date=rec["date"], tau=tau,
                 w0=rec["window"]["x0"], e=e, ranked=None)
        for mode in ("base", "e", "g"):
            rep = reps.get((rec["date"], mode))
            vs = [v for v in rep["vers"] if v[0] <= j_tau] \
                if rep else []
            ok, fin = False, None
            if vs and (rep["dead"] is None or rep["dead"] > j_tau):
                v = vs[-1]
                fin = [round(v[1], 1), round(v[2], 1)]
                er = er_of(v[1], v[2], vs[0][3], tau, m, d["w0"])
                ok = any(V2.match(g, er, m) for g in gs)
            print("  %-6s RW-%s vers=%d final=%s author=%s"
                  % (p["name"], mode, len(vs), fin, ok))
            out.append(dict(item="rw_review", variant=mode,
                            panel=p["name"], n_vers=len(vs),
                            final=fin, author_match=ok))

    with open(os.path.join(HERE, "rw_est.jsonl"), "w",
              encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, default=str) + "\n")
    print("\nwrote rw_est.jsonl (%d rows)" % len(out))


def jt_tau_cet(m, j):
    return int(m[min(j, len(m) - 1)])


if __name__ == "__main__":
    main()
