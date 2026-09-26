"""EVAL-AUDIT s.87.4 - independent verify of boxlab/RW_EST.md.

Own replay of the UIP band-write rule (pipes.py:66-141) per panel:
  iterate confirmed pivots (t_conf == i) in book.seq order; classify
  (rd pair gate SEP>=8 + |dPrice|<=GATE, pb gate 3 while unborn /
  PBSEP once born under ev_uip_pb_birth); cands[0] wins.
  Birth path: spent check, height 6-34p, cooldown idx-last_birth>=10,
  dedup within dtol -> _birth.  Rewrite path (evs exists):
  rd cand writes, pb cand skips (ev_uip_pb_write OFF in C-3).
Variants:
  parent : GATE=DTOL=2.0, opposite edge = raw seg extreme   (sanity:
           must reproduce the recorded band-version chain)
  rw_e   : GATE=2.0, opposite edge = trade_tags.cluster_edge
           (clu_lo for side>0 bottom / clu_hi for side<0 top)
           over seg = bars[max(0,lo_i-2):idx+1], tol=tol_e(abr@idx)
  rw_g   : GATE=dtol=max(1,0.25*abr[i]), raw opposite edge.
Then V2.match on the simulated box@1 band at each golden tau.

usage: python evalcheck/_rw_verify.py [--panels 9.6a,9.7b]
"""
import collections
import glob
import os
import pickle
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import recall_at_k as RK                        # noqa: E402
import trade_tags as TT                         # noqa: E402
from snapshot import tau_of, live_records       # noqa: E402

ARM_V, ARM_H = "uip2_pbbirth", "8361fe85e73f9437"
RE_W = re.compile(r"\[(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\]"
                  r".*?t0=(\d+)")
DTOL0, SEP, PBSEP, COOL = 2.0, 8, 8, 10
HMIN, HMAX, WIN = 6.0, 34.0, 600
NAMED12 = ("9.10c", "9.11b", "9.17b", "9.25a", "9.2b", "9.33c",
           "9.36c", "9.40a", "9.42b", "9.48b", "9.52a", "9.57b")


def ev_object(e):
    evs = [o for o in e.objects if o.type == "BOX"
           and o.geometry.get("meta_ev_route")]
    return evs[-1] if evs else None


def band_seq(o, e):
    g = o.geometry
    seq = []
    if (o.why or "").startswith("ev_") and o.type == "BOX":
        b = [cd for cd in e.cand_log
             if cd.get("outcome") == "uip_birth"
             and cd.get("idx") == o.t_birth]
        if b:
            seq.append((int(o.t_birth), float(b[-1]["bottom"]),
                        float(b[-1]["top"]),
                        int(b[-1].get("t0") or 0)))
        for ev in o.events:
            if ev[1] == "uip_rewrite":
                mm = RE_W.search(str(ev[2]))
                if mm:
                    seq.append((int(ev[0]), float(mm.group(1)),
                                float(mm.group(2)),
                                int(mm.group(3))))
        if seq:
            return sorted(seq, key=lambda v: v[0])
    if "bottom" in g:
        return [(int(o.t_birth or 0), float(g["bottom"]),
                 float(g["top"]), int(g.get("t0") or o.t_left or 0))]
    return seq


def classify(e, piv, i, born, gate):
    """pipes.py:71-107 replayed.  Returns (bot,top,t_left,route,
    idx,prev_ext) for cands[0], or None."""
    idx, price, side = piv.t_ext, piv.price, piv.dir
    seq = [p for p in e.book.seq if p is not piv
           and getattr(p, "t_conf", None) is not None
           and p.t_conf <= i and p.t_ext <= idx]
    same = [p for p in seq if p.dir == side
            and idx - p.t_ext <= WIN]
    opp = [p for p in seq if p.dir == -side
           and idx - p.t_ext <= WIN]
    cands = []
    for prev in reversed(same):
        if idx - prev.t_ext < SEP:
            continue
        if abs(prev.price - price) <= gate(i):
            cands.append((idx, prev.t_ext, prev.price, side,
                          max(prev.t_ext, 0),
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
            cands.append((L, H, None, None, t0a,
                          "ev_pullback_end"))
    if not cands:
        return None
    return cands[0]


def rd_band(e, prev_ext, prev_price, price, idx, side, cluster,
            abr, i):
    """the range-double band for a confirmed pair: defended edge =
    the pair price; opposite edge = raw seg extreme or
    cluster_edge per `cluster` flag (tol = tol_e at the
    confirmation bar i).  Returns (lo, hi)."""
    lo_i = min(prev_ext, idx)
    seg = e.bars[max(0, lo_i - 2):idx + 1]
    hs = np.asarray([x["h"] for x in seg])
    ls = np.asarray([x["l"] for x in seg])
    a = abr[min(i, len(abr) - 1)]
    tol = max(1.0, 0.25 * a)
    if side > 0:
        bot = TT.cluster_edge(np.sort(ls), tol, False) \
            if cluster else float(ls.min())
        return bot, max(prev_price, price)
    top = TT.cluster_edge(np.sort(hs)[::-1], tol, True) \
        if cluster else float(hs.max())
    return min(prev_price, price), top


def replay(e, j_tau, abr, variant):
    """returns (versions, n_writes, t_left_obj): versions
    [(bar,lo,hi,t_left)] for the simulated ev object; birth at
    first qualifying cand.  variant in {'parent','rw_e','rw_g'}."""
    gate = (lambda i: DTOL0) if variant in ("parent", "rw_e") \
        else (lambda i: max(1.0, 0.25 * abr[min(i, len(abr) - 1)]))
    cluster = variant in ("rw_e", "rw_eg")
    born = False
    spent = False
    last_birth = -10 ** 9
    t_left_obj = None
    vers = []
    n_writes = 0
    other = [(o2, band_seq(o2, e)) for o2 in e.objects
             if o2.type == "BOX"
             and not o2.geometry.get("meta_ev_route")]
    piv_by_i = collections.defaultdict(list)
    for p in e.book.seq:
        tc = getattr(p, "t_conf", None)
        if tc is not None and tc <= j_tau:
            piv_by_i[int(tc)].append(p)
    for i in range(j_tau + 1):
        for piv in piv_by_i.get(i, ()):
            cd = classify(e, piv, i, born, gate)
            if cd is None:
                continue
            if cd[5] == "ev_pullback_end":
                if born:
                    continue          # uip_skip_pb (pb_write OFF)
                lo, hi, t_left, idx = cd[0], cd[1], cd[4], \
                    piv.t_ext
            else:
                idx, prev_ext, prev_price, side, t_left = cd[:5]
                lo, hi = rd_band(e, prev_ext, prev_price,
                                 piv.price, idx, side, cluster,
                                 abr, i)
            if born:
                vers.append([i, round(lo, 2), round(hi, 2),
                             int(t_left)])
                n_writes += 1
                continue
            if spent:
                continue
            if not (HMIN - 0.01 <= hi - lo <= HMAX + 0.01):
                continue              # vetoed_height
            if idx - last_birth < COOL:
                continue              # vetoed_cooldown
            a = abr[min(i, len(abr) - 1)]
            dtol = max(1.0, 0.25 * a)
            dup = False
            for _o2, sq in other:
                if not sq:
                    continue
                cur = None
                for v in sq:
                    if v[0] <= i:
                        cur = v
                if cur and abs(cur[2] - hi) <= dtol \
                        and abs(cur[1] - lo) <= dtol:
                    dup = True
                    break             # dedup_existing
            if dup:
                continue
            born = True
            last_birth = idx
            t_left_obj = int(t_left)
            vers.append([i, round(lo, 2), round(hi, 2),
                         int(t_left)])
            n_writes += 1
    return vers, n_writes, t_left_obj


def base_rec(by_date, date, w1):
    cand = [x for x in by_date[date]
            if x["window"]["x0"] <= w1
            <= (x["window"]["x1"] or 1439)]
    for x in cand:
        w0 = x["window"]["x0"]
        w1f = x["window"]["x1"] or 1439
        g2 = [g for g in EV.gold_objects(x)[0]
              if V2.scorable(g, w0, w1f)]
        if any(tau_of(g) is not None
               and min(tau_of(g), w1f) == w1 for g in g2):
            return x
    return cand[0] if cand else None


def main():
    only = None
    if "--panels" in sys.argv:
        only = set(sys.argv[sys.argv.index("--panels") + 1]
                   .split(","))
    recs = list(C.load_tune())
    by_date = collections.defaultdict(list)
    for r in recs:
        by_date[r["date"]].append(r)
    stats = {v: dict(lost=0, gained=0, rows=0, wr=[],
                     lost_rows=[], gained_rows=[])
             for v in ("parent", "rw_e", "rw_g")}
    par_wr = []
    named = {v: {} for v in stats}
    files = sorted(glob.glob(os.path.join(
        CA.CACHE, "run_%s_%s_*.pkl" % (ARM_V, ARM_H))))
    for f in files:
        stem = os.path.basename(f)[:-4]
        date, w1s = stem.rsplit("_", 2)[1:]
        w1 = int(w1s)
        rec = base_rec(by_date, date, w1)
        if rec is None:
            continue
        if only and rec["id"] not in only:
            continue
        w0 = rec["window"]["x0"]
        g2 = [g for g in EV.gold_objects(rec)[0]
              if V2.scorable(g, w0, w1)]
        g_box = [g for g in g2
                 if EV.FAMILY.get(g["spec_type"]) == "box"
                 and tau_of(g) is not None
                 and min(tau_of(g), rec["window"]["x1"] or 1439)
                 == w1]
        if not g_box:
            continue
        e = pickle.load(open(f, "rb"))
        _t, m, _o, _h, _l, c = CA.bars(date)
        m = np.asarray(m)
        # NOTE: use e.abr (engine-run axis), not CA.abr(date)
        # (full-day axis) - bar indices are on the run's bars.
        abr = np.asarray(e.abr)
        j_tau = min(int(np.searchsorted(m, w1)), len(e.bars) - 1)
        live, _em = live_records(e, m, w0, w1)
        osc = {ob.id: getattr(ob, "score", None)
               for ob in e.objects}
        for r in live:
            r["score"] = osc.get(r["id"])
        ranked = RK.rank_live(live, RK.score_map(e))
        top = [r for r in ranked
               if EV.FAMILY.get(r["type"]) == "box"][:1]
        base_hit = bool(top) and any(
            V2.match(g, top[0], m) for g in g_box)
        inc = ev_object(e)
        # parent write count from the recorded chain
        seq0 = band_seq(inc, e) if inc is not None else []
        par_wr.append(len(seq0))
        for v in ("parent", "rw_e", "rw_g"):
            vers, nwr, tlo = replay(e, j_tau, abr, v)
            st = stats[v]
            st["rows"] += 1
            st["wr"].append(nwr)
            sim_hit = False
            fin = [x for x in vers if x[0] <= j_tau]
            if fin:
                b = fin[-1]
                # anchor = first version's t_left (their vs[0][3]):
                # the object's own left edge, set at birth.
                anchor = int(vers[0][3]) if vers else (tlo or 0)
                er = dict(type="BOX", lo=b[1], hi=b[2],
                          t0=int(m[min(anchor, len(m) - 1)]),
                          t1=int(w1), w0=w0, w1=int(w1))
                sim_hit = any(V2.match(g, er, m) for g in g_box)
            if base_hit and not sim_hit:
                st["lost"] += 1
                st["lost_rows"].append((rec["id"], w1, nwr))
            if sim_hit and not base_hit:
                st["gained"] += 1
                st["gained_rows"].append((rec["id"], w1, nwr))
            if rec["id"] in NAMED12:
                named[v][rec["id"]] = (nwr, sim_hit)
    pwr = np.asarray(par_wr)
    print("parent recorded writes/panel: med=%.0f (n=%d)"
          % (np.median(pwr), len(pwr)))
    for v in ("parent", "rw_e", "rw_g"):
        st = stats[v]
        a = np.asarray(st["wr"], dtype=float)
        print("%s: rows=%d lost=%d %s gained=%d %s | writes "
              "med=%.0f max=%d"
              % (v, st["rows"], st["lost"], st["lost_rows"],
                 st["gained"], st["gained_rows"], np.median(a),
                 int(a.max())))
        for p in NAMED12:
            if p in named[v]:
                print("   %-6s writes=%d sim_hit=%s"
                      % (p, named[v][p][0], named[v][p][1]))


if __name__ == "__main__":
    main()
