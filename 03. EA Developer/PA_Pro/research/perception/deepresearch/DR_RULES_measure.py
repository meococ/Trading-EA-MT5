"""DR_RULES_measure.py — R77 s77.3 Parts B+C(+raw for D), read-only.

One pass over the canonical 623 windows (R75 s75.6: STABLE C-3 =
uip2_pbbirth@8361fe85e73f9437, the tau-clipped cached runs).  At each
event (panel, tau) we load the cached engine, which carries causal
e.bars / e.ema (EMA25) / e.abr (ABR20) / e.book.seq pivots / e.objects /
e.cand_log, all fed only bars <= tau.  The SAME engine arrays drive the
golden-side measures (Part B), so units are "engine abr/ema" by
construction.

Per object we emit CONTINUOUS rule stats; pass/fail per variant is
decided downstream in DR_RULES_report.py.

Rules (s77.3 verbatim):
  C1 d(ema[t_end], band)/abr <= d          band: box [bot,top]; level [p,p]
  C2 |ema[t]-ema[t-10]|/(10*abr[t]) <= s   at t_end
  C3 no bar in span with range >= m*abr
  C4 no run of <=6 same-direction bars (body sign) with |c[b]-o[a]| >= r*abr[b]
  C5 width in bars = (min(t1,tau)-t0)/5 <= W
  C6 both box edges within tol of cluster_edge (r73_edges.edge_defs)
  C7 close side-switches across level/line (beyond tol_j) birth..t_end <= n
  C8 no confirmed same-polarity pivot born after level beyond k*abr

Span = bars <= min(t1, tau), start at t0 (drawn).  Bar-index convention
matches _bar_of/r73_edges: first bar with cet_min >= x; span end = last
bar with cet_min <= min(t1, tau) == last fed bar when t1 >= tau.

Outputs (deepresearch/):
  DR_RULES_golden.jsonl  one row per scorable golden (box/level/line fam)
  DR_RULES_live.jsonl    one row per live engine signal object per event
  DR_RULES_events.jsonl  one row per (panel,tau) event

Usage: python deepresearch/DR_RULES_measure.py [--limit N]
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
# R78 s.78.4(3) TT: predicates moved to trade_tags.py (leaf module the
# engine can import); edge_defs comes along via r73_edges' re-export.
from trade_tags import (to_min, jge, jle, tol_e, edge_defs,     # noqa: E402
                        s_c1, s_c2, s_c3, s_c4, s_c6, s_c7, s_c8)

PAR = ("uip2_pbbirth", "8361fe85e73f9437")
CACHE = os.path.join(PERC, "evalcheck", "_cache")
PIP = 1e4
FAM_BUDGET = {"box": 1, "line": 2, "level": 1, "bracket": 1}
RULE_FAMS = {"box": ("BOX", "RANGE_OPEN", "CONTEXT_RANGE"),
             "level": ("LEVEL_CARRIED", "MINI_LEVEL"),
             "line": ("PATTERN_LINE", "CONTEXT_LINE")}


def pickled(date, w1):
    f = os.path.join(CACHE, "run_%s_%s_%s_%s.pkl" % (PAR[0], PAR[1],
                                                   date, w1))
    if not os.path.exists(f):
        return None
    try:
        with open(f, "rb") as fh:
            return pickle.load(fh)
    except Exception:
        return None


# ------------------------------------------------------------------ #
# per-object descriptors -> stats
# ------------------------------------------------------------------ #

def gold_stats(g, m, o, h, l, c, ema, abr, pivots, tau, w1):
    st = g["spec_type"]
    fam = EV.FAMILY.get(st)
    t0, t1 = to_min(g.get("t0")), to_min(g.get("t1"))
    end = min(t1 if t1 is not None else tau, tau)
    j1 = jle(m, end)
    j0 = jge(m, t0) if t0 is not None else None
    out = {"fam": fam, "spec_type": st, "prec": g.get("prec"),
           "t0": t0, "t1": t1, "end_min": end, "j0": j0, "j1": j1,
           "width_bars": ((end - t0) / 5.0 if t0 is not None else None),
           "bs": to_min(g.get("build_start")),
           "be": to_min(g.get("build_end"))}
    if j0 is None or j1 is None or j0 > j1:
        out["degenerate"] = True
        return out
    out["n_bars_span"] = j1 - j0 + 1
    jb = jge(m, t0) if t0 is not None else None      # golden birth ~ t0
    if fam == "box" and g.get("price_lo") is not None:
        lo, hi = g["price_lo"] * PIP, g["price_hi"] * PIP
        out.update(s_c1(lo, hi, j1, ema, abr))
        out.update(s_c3(j0, j1, h, l, abr))
        out.update(s_c4(j0, j1, o, c, abr))
        out.update(s_c6(j0, j1, h, l, o, c, abr, hi, lo))
        # containment-window sensitivity (build_start..build_end clip)
        bs = out["bs"] if out["bs"] is not None else t0
        be = out["be"] if out["be"] is not None else end
        wa, wb = jge(m, bs), jle(m, min(be, tau))
        if wb is not None and wa <= wb:
            out["c3_r_win"] = s_c3(wa, wb, h, l, abr)["c3_r"]
            out["c4_r_win"] = s_c4(wa, wb, o, c, abr)["c4_r"]
            out["width_win_bars"] = (min(be, tau) - bs) / 5.0
    elif fam == "level" and g.get("price") is not None:
        p = g["price"] * PIP
        out.update(s_c1(p, p, j1, ema, abr))
        out.update(s_c7(jb, j1, c, abr, lambda j: p))
        out["c7_sw_full"] = s_c7(0, j1, c, abr, lambda j: p)["c7_sw"]
        pol = g.get("dir")
        if pol not in ("above", "below"):
            pol = "above" if p >= c[jb] else "below"
        out["c8_pol"] = pol
        out.update(s_c8(jb, j1, p, pol, pivots, abr))
    if fam in ("box", "level", "line"):
        out.update(s_c2(j1, ema, abr))
    if fam == "line":
        p0, p1 = g.get("price0"), g.get("price1")
        if p0 is not None and p1 is not None and t0 is not None \
                and t1 is not None and t1 > t0:
            p0p, p1p = p0 * PIP, p1 * PIP
            lp = lambda j: p0p + (p1p - p0p) * (m[j] - t0) / (t1 - t0)
            out.update(s_c7(jb, j1, c, abr, lp))
            out["c7_sw_full"] = s_c7(0, j1, c, abr, lp)["c7_sw"]
    return out


def eng_stats(ob, m, o, h, l, c, ema, abr, pivots, nfed):
    fam = EV.FAMILY.get(ob.type)
    g = ob.geometry
    t1_src = g.get("t1_drawn") or \
        (ob.t_right if ob.t_right is not None else nfed)
    j1 = min(int(t1_src), nfed)
    j0 = min(int(ob.t_left), j1)
    jb = int(ob.t_birth) if ob.t_birth is not None else None
    if jb is not None:
        jb = min(jb, nfed)
    out = {"fam": fam, "type": ob.type, "state": ob.state,
           "t0m": int(m[j0]), "t1m": int(m[j1]), "j0": j0, "j1": j1,
           "width_bars": (m[j1] - m[j0]) / 5.0,
           "t_birth_m": (int(m[jb]) if jb is not None else None)}
    if fam == "box" and "top" in g:
        lo, hi = g["bottom"], g["top"]
        out.update(s_c1(lo, hi, j1, ema, abr))
        out.update(s_c3(j0, j1, h, l, abr))
        out.update(s_c4(j0, j1, o, c, abr))
        out.update(s_c6(j0, j1, h, l, o, c, abr, hi, lo))
        bs = g.get("meta_build_start", g.get("build_start"))
        be = g.get("meta_build_end", g.get("build_end",
                                           g.get("break_bar")))
        if bs is None:
            bs = j0                      # _eng_window: fallback drawn left
        if be is None:
            be = t1_src                  # _eng_window: fallback drawn right
        if bs is not None and be is not None:
            wa, wb = min(int(bs), nfed), min(int(be), nfed)
            if wa <= wb:
                out["c3_r_win"] = s_c3(wa, wb, h, l, abr)["c3_r"]
                out["c4_r_win"] = s_c4(wa, wb, o, c, abr)["c4_r"]
                out["width_win_bars"] = (m[wb] - m[wa]) / 5.0
    elif fam == "level" and "price" in g:
        p = g["price"]
        out.update(s_c1(p, p, j1, ema, abr))
        out.update(s_c7(jb, j1, c, abr, lambda j: p))
        out["c7_sw_span"] = s_c7(j0, j1, c, abr, lambda j: p)["c7_sw"]
        out["c7_sw_full"] = s_c7(0, j1, c, abr, lambda j: p)["c7_sw"]
        pol = g.get("side")
        if pol not in ("above", "below"):
            pol = "above" if p >= c[jb] else "below"
        out["c8_pol"] = pol
        out.update(s_c8(jb, j1, p, pol, pivots, abr))
        # anchor variant: superseding extreme born after the drawn
        # left edge (the level's structural anchor), not after t_birth
        a = s_c8(j0, j1, p, pol, pivots, abr)
        out["c8_beyond_abr_anch"] = a["c8_beyond_abr"]
        out["c8_npiv_anch"] = a["c8_npiv"]
    if fam in ("box", "level", "line"):
        out.update(s_c2(j1, ema, abr))
    if fam == "line" and "p0" in g:
        p0, slope, tb = g["p0"], g["slope"], g["t0"]
        out.update(s_c7(jb, j1, c, abr, lambda j: p0 + slope * (j - tb)))
        out["c7_sw_span"] = s_c7(j0, j1, c, abr,
                                 lambda j: p0 + slope * (j - tb))["c7_sw"]
        out["c7_sw_full"] = s_c7(0, j1, c, abr,
                                 lambda j: p0 + slope * (j - tb))["c7_sw"]
    return out


# ------------------------------------------------------------------ #

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    recs = C.load_tune()
    if args.limit:
        recs = recs[:args.limit]

    f_g = open(os.path.join(HERE, "DR_RULES_golden.jsonl"), "w",
               encoding="utf8")
    f_l = open(os.path.join(HERE, "DR_RULES_live.jsonl"), "w",
               encoding="utf8")
    f_e = open(os.path.join(HERE, "DR_RULES_events.jsonl"), "w",
               encoding="utf8")
    n_ev = n_miss = 0
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        _t, m_day, _o, _h, _l, _c = CA.bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        gmarks = [gm for gm in EV.gold_marks(rec)
                  if V2.scorable_mark(gm, w0, w1)]
        by_tau = collections.defaultdict(list)
        for gi, g in enumerate(g2):
            tau = tau_of(g)
            if tau is not None and tau >= w0:
                by_tau[min(tau, w1)].append((gi, g))
        mark_taus = set()
        for gm in gmarks:                      # canonical 623 includes
            if gm.get("t") is not None and w0 <= gm["t"] <= w1:
                mark_taus.add(gm["t"])         # mark-only decision taus
        for tau in mark_taus:
            by_tau.setdefault(tau, [])
        if w1 not in by_tau:
            by_tau[w1] = []                    # full-window panel-end run
        for tau, ggs in sorted(by_tau.items()):
            e = pickled(rec["date"], tau)
            if e is None:
                n_miss += 1
                continue
            n_ev += 1
            nfed = len(e.bars) - 1
            m = np.array([b["cet_min"] for b in e.bars])
            o = np.array([b["o"] for b in e.bars])
            h = np.array([b["h"] for b in e.bars])
            l = np.array([b["l"] for b in e.bars])
            c = np.array([b["c"] for b in e.bars])
            ema = np.asarray(e.ema)
            abr = np.asarray(e.abr)
            pivots = e.book.seq
            # ---- engine side: live set, ranking, picks, matches ----
            live, emarks = live_records(e, m_day, w0, tau)
            osc = {ob.id: getattr(ob, "score", None)
                   for ob in e.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            ranked = RK.rank_live(live, RK.score_map(e))
            fam_ranked = collections.defaultdict(list)
            for r in ranked:
                fam_ranked[EV.FAMILY.get(r["type"])].append(r)
            picks = []
            for f, k in FAM_BUDGET.items():
                picks += fam_ranked[f][:k]
            pick_ids = {r["id"] for r in picks}
            gs = [g for _gi, g in ggs]
            o_by_id = {ob.id: ob for ob in e.objects}
            for rank, r in enumerate(ranked):
                fam = EV.FAMILY.get(r["type"])
                mgi = [gi for gi, g in ggs if V2.match(g, r, m_day)]
                row = {"panel": rec["id"], "date": rec["date"],
                       "tau": tau, "id": r["id"], "rank": rank,
                       "fam": fam, "type": r["type"],
                       "picked": r["id"] in pick_ids,
                       "matched": bool(mgi), "match_gis": mgi}
                if fam in RULE_FAMS:
                    ob = o_by_id.get(r["id"])
                    if ob is not None:
                        row.update(eng_stats(ob, m, o, h, l, c,
                                             ema, abr, pivots, nfed))
                f_l.write(json.dumps(row) + "\n")
            # ---- golden side ----
            for gi, g in ggs:
                if EV.FAMILY.get(g["spec_type"]) not in RULE_FAMS:
                    continue
                st = gold_stats(g, m, o, h, l, c, ema, abr, pivots,
                                tau, w1)
                st.update({"panel": rec["id"], "date": rec["date"],
                           "tau": tau, "gi": gi,
                           "tol_g": V2.tol_px(g)})
                f_g.write(json.dumps(st) + "\n")
            f_e.write(json.dumps({
                "panel": rec["id"], "date": rec["date"], "tau": tau,
                "is_tau_event": bool(ggs),
                "kind": ("obj" if ggs else
                         ("mark" if tau in mark_taus else "panel_end")),
                "n_g2": len(g2), "n_gm": len(gmarks),
                "n_live": len(live), "n_marks": len(emarks),
                "gs": [{"gi": gi,
                        "fam": EV.FAMILY.get(g["spec_type"])}
                       for gi, g in ggs],
                "gs_fam": [EV.FAMILY.get(g["spec_type"]) for g in gs],
                "picks": [{"id": r["id"],
                           "fam": EV.FAMILY.get(r["type"]),
                           "matched": any(V2.match(g, r, m_day)
                                          for g in gs)}
                          for r in picks]}) + "\n")
    f_g.close()
    f_l.close()
    f_e.close()
    print("events=%d missing_pkl=%d" % (n_ev, n_miss))


if __name__ == "__main__":
    main()
