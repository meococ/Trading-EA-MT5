"""r73_ladder.py — R73 s73.3 step 2: the box-candidate GATE LADDER.

Preregistered in BOX_LOG.md 06:21Z before measuring.  Re-enumerates the
event-route candidate stream (rd + pb) on the CONFIRMED pivot stream of
each date's c1r_p_base@ee2cbf12 engine pickle (book.seq — the same swing
stream the C-3 engine sees; swing detection is flag-invariant), under
each gate-relaxation cell, then scores ruler-exact reach (eval_v2
imported, never copied) on all 119 box goldens and on the 68
edge-unreachable subset (dr_rows n_match==0).

Cells (base = C-3 _ev_uip_step stream params):
  L0  base            WIN=600 SEP=8  DTOL=2.0 PB=3  first-pair shadow raw
  L1  win=inf         remove the 600-bar pair window      (engine.py:346)
  L2  sep=0           remove same-side min separation     (engine.py:352)
  L3  dtol=4          widen double-touch tolerance        (engine.py:354)
  L4  dtol=8          widen further
  L5  allpairs        emit every qualifying rd pair       (engine.py:363)
  L6  pbsep=0         pullback pair needs no separation   (engine.py:379)
  L7  unshadow        rd+pb both survive when both fire   (engine.py:384)
  L8  edge=cluster    rd opposite edge = defended-cluster extreme
                      (>=2 wicks within max(1p,.25ABR))   (engine.py:355)
  L9  cumulative      wininf+sep0+dtol4+allpairs+pbsep0+unshadow
  L10 L9 + cluster edge

Reported per cell: reach 119 / reach 68 / median cands per panel
(in-window births).  Birth-side gates (envelope 6-34p, cooldown,
dedup, uip_spent, score floor) do not change the pool — listed in the
gate map, not relaxed here (envelope measured 0/13 in R71).
"""
import glob
import os
import pickle
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)

import common as C                      # noqa: E402
import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import cache as CA                     # noqa: E402
from snapshot import tau_of            # noqa: E402

HASH = "ee2cbf12"
VAR = "c1r_p_base"

CELLS = {
    "L0_base":     dict(),
    "L1_winf":     dict(WIN=10**9),
    "L2_sep0":     dict(SEP=0),
    "L3_dtol4":    dict(DTOL=4.0),
    "L4_dtol8":    dict(DTOL=8.0),
    "L5_allpairs": dict(ALL=True),
    "L6_pbsep0":   dict(PBSEP=0),
    "L7_unshadow": dict(UNSHADOW=True),
    "L8_clu":      dict(EDGE="clu"),
    "L9_cum":      dict(WIN=10**9, SEP=0, DTOL=4.0, ALL=True,
                        PBSEP=0, UNSHADOW=True),
    "L10_cum_clu": dict(WIN=10**9, SEP=0, DTOL=4.0, ALL=True,
                        PBSEP=0, UNSHADOW=True, EDGE="clu"),
}
BASE = dict(WIN=600, SEP=8, DTOL=2.0, PBSEP=3, ALL=False,
            UNSHADOW=False, EDGE="raw")


def cluster_ext(vals, tol, top):
    """Most extreme price touched by >=2 wicks within tol."""
    s = sorted(vals, reverse=top)
    for x in s:
        if top:
            if sum(1 for y in vals if y >= x - tol) >= 2:
                return x
        else:
            if sum(1 for y in vals if y <= x + tol) >= 2:
                return x
    return s[0]


def enum_stream(pivs, h, l, abr, P):
    """v0/C-3 route enumeration on confirmed pivots, parameterized."""
    out = []
    confirmed = []                       # (t_ext, price, dir)
    for p in pivs:
        e, price, side, tc = p.t_ext, p.price, p.dir, p.t_conf
        same = [s for s in confirmed
                if s[2] == side and e - s[0] <= P["WIN"]]
        opp = [s for s in confirmed
               if s[2] == -side and e - s[0] <= P["WIN"]]
        rc = []
        for prev in reversed(same):
            if e - prev[0] < P["SEP"]:
                continue
            if abs(prev[1] - price) <= P["DTOL"]:
                lo_i = min(prev[0], e)
                a = max(0, lo_i - 2)
                seg_l, seg_h = l[a:e + 1], h[a:e + 1]
                tol = max(1.0, 0.25 * (abr[e] if e < len(abr) else 5.0))
                if side > 0:
                    top = max(prev[1], price)
                    bot = (min(seg_l) if P["EDGE"] == "raw"
                           else cluster_ext(seg_l, tol, False))
                else:
                    bot = min(prev[1], price)
                    top = (max(seg_h) if P["EDGE"] == "raw"
                           else cluster_ext(seg_h, tol, True))
                rc.append(dict(route="rd", lo=bot, hi=top,
                               t0=prev[0], born=tc))
                if not P["ALL"]:
                    break
        if opp:
            last = opp[-1]
            L, H = (price, last[1]) if side < 0 else (last[1], price)
            t0a = min(e, last[0])
            if e - t0a >= P["PBSEP"]:
                rc.append(dict(route="pb", lo=L, hi=H, t0=t0a, born=tc))
        out += rc if P["UNSHADOW"] else rc[:1]
        confirmed.append((e, price, side))
    return out


def ruler_hit(g, cd, m, tau, w0, w1):
    rec = dict(type="BOX", lo=cd["lo"], hi=cd["hi"],
               t0=float(m[min(cd["t0"], len(m) - 1)]), t1=float(tau),
               w0=w0, w1=w1)
    ok, _route = V2.match_detail(g, rec, m)
    return ok


def main():
    recs = C.load_tune()
    rows = pickle.load(open(
        os.path.join(PERC, "deepresearch", "dr_rows.pkl"), "rb"))
    drmap = {}
    for r in rows:
        drmap.setdefault(r["panel"], []).append(r)
    unreach = {(r["panel"], int(round(r["tau"])))
               for r in rows if r["n_match"] == 0}

    # panel -> (date, window); date -> latest golden tau across panels
    pan_date, pan_taus = {}, defaultdict(list)
    for r in rows:
        pan_date[r["panel"]] = r["date"]
        pan_taus[r["date"]].append(int(round(r["tau"])))
    date_tau = {d: max(v) for d, v in pan_taus.items()}

    # one pickle per date (latest tau) -> full-day pivot stream
    streams = {}
    for d, tau in sorted(date_tau.items()):
        fs = glob.glob(os.path.join(
            CA.CACHE, "run_%s_%s*_%s_*.pkl" % (VAR, HASH, d)))
        have = {}
        for f in fs:
            tt = int(os.path.basename(f).rsplit("_", 1)[1][:-4])
            if tt >= tau:
                have[tt] = f
        f = have[min(have)] if have else None
        if f is None:
            print("NO PKL", d, tau)
            continue
        e1 = pickle.load(open(f, "rb"))
        pivs = sorted(e1.book.seq, key=lambda p: (p.t_conf, p.t_ext))
        _t, m, o, h, l, c = CA.bars(d)
        abr = CA.abr(d)
        streams[d] = dict(pivs=pivs, m=m, h=h, l=l, abr=abr)

    res = {k: dict(all=set(), un=set(), npan=defaultdict(int))
           for k in CELLS}
    n = 0
    # enumerate once per (date, cell)
    cell_streams = defaultdict(dict)
    for d, st in streams.items():
        for name, over in CELLS.items():
            P = dict(BASE)
            P.update(over)
            cell_streams[d][name] = enum_stream(
                st["pivs"], st["h"], st["l"], st["abr"], P)

    for rec in recs:
        d = rec["id"]
        dt = pan_date.get(d)
        if dt not in streams:
            continue
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        st = streams[dt]
        m, h, l, abr = st["m"], st["h"], st["l"], st["abr"]
        nb = len(m)
        gobjs, _u, _to = EV.gold_objects(rec)
        golds = []
        for g in gobjs:
            if g["spec_type"] not in V2.BOX_TYPES or \
                    not V2.scorable(g, w0, w1):
                continue
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            golds.append((g, min(tau, w1)))
        if not golds:
            continue
        for name in CELLS:
            stream = cell_streams[dt][name]
            res[name]["npan"][d] += sum(
                1 for cd in stream if w0 <= m[min(cd["born"], nb - 1)]
                < w1)
            for g, tau in golds:
                key = (d, int(round(tau)))
                j_tau = min(int(np.searchsorted(m, tau)), nb - 1)
                for cd in stream:
                    if cd["born"] > j_tau:
                        continue
                    if ruler_hit(g, cd, m, tau, w0, w1):
                        res[name]["all"].add(key)
                        if key in unreach:
                            res[name]["un"].add(key)
                        break
        n += len(golds)

    print("goldens:", n, " unreach68:", len(unreach))
    print("%-11s %6s %6s %8s %8s" %
          ("cell", "r119", "r68", "cand/pan", "max/pan"))
    for name in CELLS:
        cps = [v for v in res[name]["npan"].values()]
        print("%-11s %6d %6d %8.1f %8d" %
              (name, len(res[name]["all"]), len(res[name]["un"]),
               np.median(cps), max(cps)))
    pickle.dump(res, open(os.path.join(HERE, "_r73_ladder.pkl"), "wb"))


if __name__ == "__main__":
    main()
