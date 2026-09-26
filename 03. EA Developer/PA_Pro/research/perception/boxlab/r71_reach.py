"""r71_reach.py — R71 s.71.5 items 2+3 on C-3 base, ruler-exact.

Item 2 `env_abr`: cand admissible iff 1.2*ABR[born] <= hi-lo <=
10.0*ABR[born] (replaces fixed 6-34p). Reach on the 13 tall (>34p)
unreachable goldens + all 119.

Item 3 `pair_edge` (PC channel): registers E_hi/E_lo = hi/lo of the
most recent born event cand; emit a PC cand when both set, E_hi>E_lo,
pair moved >1.0p on either edge since last emission, and pair gap in
6-34p.  Cand lo=E_lo hi=E_hi t0=min(src t0) born=later update bar.

Ruler-exact: V2.match_detail on {type:BOX, lo,hi, t0=m[start],
t1=tau, w0,w1} (no bs/be -> coverage/IoU fallback), born<=j_tau.
Also live-at-tau = no close outside band in (born, j_tau].
"""
import os
import pickle
import sys

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

PIP = 1e4
E_LO_ABR, E_HI_ABR = 1.2, 10.0    # item 2 envelope in ABR
PAIR_DEDUP = 1.0                  # item 3 edge dedup tol (pips)
HMIN, HMAX = 6.0, 34.0            # item 3 pair gap (fixed envelope)


def ruler_hit(g, cd, m, tau, w0, w1):
    rec = dict(type="BOX", lo=cd["lo"], hi=cd["hi"],
               t0=float(m[min(cd["t0"], len(m) - 1)]), t1=float(tau),
               w0=w0, w1=w1)
    ok, route = V2.match_detail(g, rec, m)
    return ok, route


def live_at(lo, hi, born, j_tau, c):
    seg = c[born + 1:j_tau + 1]
    return len(seg) == 0 or not ((seg > hi) | (seg < lo)).any()


def main():
    recs = C.load_tune()
    rows = pickle.load(open(
        os.path.join(PERC, "deepresearch", "dr_rows.pkl"), "rb"))
    drmap = {}
    for r in rows:
        drmap.setdefault(r["panel"], []).append(r)

    # per-panel full cand stream = union of goldens' pools
    streams = {}
    for r in rows:
        seen = streams.setdefault(r["panel"], {})
        for cd in r["pool"]:
            key = (cd["born"], cd["t0"], round(cd["lo"], 1),
                   round(cd["hi"], 1), cd["route"])
            seen[key] = cd
    for k in streams:
        streams[k] = sorted(streams[k].values(),
                            key=lambda x: (x["born"], x["t0"]))

    unreach = set()
    tall13 = set()
    for r in rows:
        key = (r["panel"], int(round(r["tau"])))
        if r["n_match"] == 0:
            unreach.add(key)
            if r["g_hi"] - r["g_lo"] > 34:
                tall13.add(key)

    res2 = dict(tall=set(), all=set(), tall_live=set(), all_live=set())
    res3 = dict(unpair=set(), all=set(), unpair_live=set(),
                all_live=set())
    births_abr = []
    births_pc = []
    live_pc = []
    n = 0
    hits2, hits3 = [], []

    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        abr = CA.abr(rec["date"])
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

        stream = streams.get(rec["id"], [])

        # ---- item 2: admissible-under-ABR-env cands --------------------
        abr_ok = [cd for cd in stream
                  if cd["born"] < nb and
                  E_LO_ABR * (abr[cd["born"]] if cd["born"] < len(abr)
                              else 5.0)
                  <= cd["hi"] - cd["lo"]
                  <= E_HI_ABR * (abr[cd["born"]] if cd["born"]
                                 < len(abr) else 5.0)]
        births_abr.append(sum(1 for cd in abr_ok
                              if w0 <= m[cd["born"]] < w1))

        # ---- item 3: PC channel emissions ------------------------------
        # E_hi/E_lo = distinct edge prices, updated independently:
        # a born cand updates E_hi only if its hi is a NEW top level
        # (>PAIR_DEDUP from current E_hi); same for E_lo.  Emit when the
        # pair is new and inside the fixed envelope.
        pc = []
        e_hi = e_lo = None
        t_hi = t_lo = b_hi = b_lo = None
        last_pair = (None, None)
        for cd in stream:
            changed = False
            if e_hi is None or abs(cd["hi"] - e_hi) > PAIR_DEDUP:
                e_hi, t_hi, b_hi = cd["hi"], cd["t0"], cd["born"]
                changed = True
            if e_lo is None or abs(cd["lo"] - e_lo) > PAIR_DEDUP:
                e_lo, t_lo, b_lo = cd["lo"], cd["t0"], cd["born"]
                changed = True
            if not changed or e_hi is None or e_lo is None:
                continue
            if e_hi <= e_lo or not (HMIN <= e_hi - e_lo <= HMAX):
                continue
            if last_pair[0] is not None and \
                    abs(e_hi - last_pair[0]) <= PAIR_DEDUP and \
                    abs(e_lo - last_pair[1]) <= PAIR_DEDUP:
                continue
            pc.append(dict(lo=e_lo, hi=e_hi, t0=min(t_hi, t_lo),
                           born=max(b_hi, b_lo)))
            last_pair = (e_hi, e_lo)
        births_pc.append(sum(1 for cd in pc
                             if w0 <= m[cd["born"]] < w1))

        for g, tau in golds:
            key = (rec["id"], int(round(tau)))
            n += 1
            is_un = key in unreach
            j_tau = min(int(np.searchsorted(m, tau)), nb - 1)
            live_pc.append(sum(1 for cd in pc
                               if cd["born"] <= j_tau and
                               live_at(cd["lo"], cd["hi"], cd["born"],
                                       j_tau, c)))
            # item 2 scoring
            for cd in abr_ok:
                if cd["born"] > j_tau:
                    continue
                ok, route = ruler_hit(g, cd, m, tau, w0, w1)
                if ok:
                    lv = live_at(cd["lo"], cd["hi"], cd["born"],
                                 j_tau, c)
                    res2["all"].add(key)
                    if lv:
                        res2["all_live"].add(key)
                    if key in tall13:
                        res2["tall"].add(key)
                        if lv:
                            res2["tall_live"].add(key)
                    hits2.append((key, route, lv,
                                  round(cd["hi"] - cd["lo"], 1)))
            # item 3 scoring
            for cd in pc:
                if cd["born"] > j_tau:
                    continue
                ok, route = ruler_hit(g, cd, m, tau, w0, w1)
                if ok:
                    lv = live_at(cd["lo"], cd["hi"], cd["born"],
                                 j_tau, c)
                    res3["all"].add(key)
                    if lv:
                        res3["all_live"].add(key)
                    if is_un:
                        res3["unpair"].add(key)
                        if lv:
                            res3["unpair_live"].add(key)
                    hits3.append((key, route, lv,
                                  round(cd["hi"] - cd["lo"], 1)))

    print("goldens:", n, " unreachable:", len(unreach),
          " tall:", len(tall13))
    print("ITEM2 env_abr [1.2,10]*ABR:")
    print("  tall13 reach: %d (live %d)" %
          (len(res2["tall"]), len(res2["tall_live"])))
    print("  all119 reach: %d (live %d)   [fixed-env reach was 46]" %
          (len(res2["all"]), len(res2["all_live"])))
    print("  admissible-cand births/panel in-window: mean %.2f med %.1f"
          % (np.mean(births_abr), np.median(births_abr)))
    print("ITEM3 pair_edge (dedup 1.0p, gap 6-34p):")
    print("  unreachable68 reach: %d (live %d)" %
          (len(res3["unpair"]), len(res3["unpair_live"])))
    print("  all119 reach: %d (live %d)" %
          (len(res3["all"]), len(res3["all_live"])))
    print("  PC emissions/panel in-window: mean %.2f med %.1f max %d"
          % (np.mean(births_pc), np.median(births_pc),
             max(births_pc)))
    print("  live PC objects at tau: mean %.2f med %.1f"
          % (np.mean(live_pc), np.median(live_pc)))
    print("item2 hits:", sorted(set(hits2)))
    print("item3 hits on unreachable:",
          sorted(set(x for x in hits3 if (x[0] in unreach))))
    pickle.dump(dict(res2=res2, res3=res3, births_abr=births_abr,
                     births_pc=births_pc, live_pc=live_pc,
                     hits2=hits2, hits3=hits3),
                open(os.path.join(HERE, "_r71.pkl"), "wb"))


if __name__ == "__main__":
    main()
