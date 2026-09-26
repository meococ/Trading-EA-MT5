"""EVAL-AUDIT s.84.5 — independent recount of boxlab/y3_est.jsonl.

Spec (their Y3_EST.md, re-implemented independently):
  band(j) of a UIP incumbent = birth band (cand_log 'uip_birth'
  at t_birth) then each 'uip_rewrite' event's [lo,hi] from its
  detail string.  stale onset = first bar j in [t_birth, j_tau]
  with s_stale_far on band(j).  cand pending window = [min,max]
  idx of cand_log rows matching (route, band rounded 1dp);
  pend_end = j_tau for 'proposed' killers else window max.
  frees = onset <= pend_end; edge-matched frees decide the
  s.84.5 >=5 bar.

usage: python evalcheck/_y3_verify.py
"""
import collections
import glob
import json
import os
import pickle
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "deepresearch"))

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import cache as CA                              # noqa: E402
import trade_tags as TT                         # noqa: E402

ARM_V, ARM_H = "uip2_pbbirth", "8361fe85e73f9437"
RE_W = re.compile(r"\[(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\]"
                  r".*?t0=(\d+)")
BOXK = ("cluster_range", "cluster_range_wick", "event_box",
        "range_double_bottom", "range_double_top", "range_mid",
        "pullback_end")


def band_versions(o, e):
    """[(bar, lo, hi)] oldest-first; my own parse of events+log."""
    g = o.geometry
    seq = []
    if (o.why or "").startswith("ev_") and o.type == "BOX":
        b = [cd for cd in e.cand_log
             if cd.get("outcome") == "uip_birth"
             and cd.get("idx") == o.t_birth]
        if b:
            seq.append((int(o.t_birth), float(b[-1]["bottom"]),
                        float(b[-1]["top"])))
        for ev in o.events:
            if ev[1] == "uip_rewrite":
                mm = RE_W.search(str(ev[2]))
                if mm:
                    seq.append((int(ev[0]), float(mm.group(1)),
                                float(mm.group(2))))
    if not seq and "bottom" in g:
        seq.append((int(o.t_birth or 0), float(g["bottom"]),
                    float(g["top"])))
    seq.sort(key=lambda v: v[0])
    return seq


def band_at(seq, j):
    cur = seq[0]
    for v in seq:
        if v[0] <= j:
            cur = v
        else:
            break
    return cur


def first_stale(seq, jb, j_from, j_to, h, l, c, abr):
    for j in range(int(j_from), int(j_to) + 1):
        _b, lo, hi = band_at(seq, j)
        s = TT.s_stale_far("box", {"bottom": lo, "top": hi},
                           int(jb), j, h, l, c, abr)
        if s["stale"]:
            return j
    return None


def cand_window(e, cand):
    sig = (cand.get("route"), round(cand.get("lo") or 0, 1),
           round(cand.get("hi") or 0, 1))
    idxs = [cd["idx"] for cd in e.cand_log
            if cd.get("kind") in BOXK
            and cd.get("route") == sig[0]
            and round(cd.get("bottom") or 0, 1) == sig[1]
            and round(cd.get("top") or 0, 1) == sig[2]]
    if not idxs:
        return int(cand["idx"]), int(cand["idx"])
    return min(idxs), max(idxs)


def main():
    recs = {r["id"]: r for r in C.load_tune()}
    e3 = [json.loads(x) for x in
          open(os.path.join(PERC, "boxlab", "e3_diag.jsonl"),
               encoding="utf8")]
    seen = set()
    n = n_sk = n_st = n_free = n_free_edge = 0
    uniq_free = set()
    uniq_free_edge = set()
    free_rows = []
    for r in e3:
        if r.get("cls") != "BUDGET_CUT":
            continue
        k3 = (r["panel"], r["tau"])
        if k3 in seen:
            continue
        seen.add(k3)
        rec = recs[r["panel"]]
        f = os.path.join(CA.CACHE,
                         "run_%s_%s_%s_%s.pkl"
                         % (ARM_V, ARM_H, rec["date"], r["tau"]))
        if not os.path.exists(f):
            print("  NO FILE", r["panel"], r["tau"])
            continue
        n += 1
        e = pickle.load(open(f, "rb"))
        _t, m, _o, h, l, c = CA.bars(rec["date"])
        m = np.asarray(m)
        abr = np.asarray(CA.abr(rec["date"]))
        j_tau = int(np.searchsorted(m, r["tau"])) if r["tau"] <= m[-1] \
            else len(m) - 1
        j_tau = min(j_tau, len(e.bars) - 1)
        j_kill = int(r["kill_bar"])
        inc = next((x for x in e.objects
                    if x.id == r["box1"]["id"]), None)
        if inc is None:
            print("  NO INC", r["panel"], r["tau"])
            continue
        seq = band_versions(inc, e)
        if not seq:
            print("  NO BAND", r["panel"], r["tau"])
            continue
        _b, lo_k, hi_k = band_at(seq, j_kill)
        s_k = TT.s_stale_far("box", {"bottom": lo_k, "top": hi_k},
                             int(inc.t_birth), j_kill, h, l, c, abr)
        _b, lo_t, hi_t = band_at(seq, j_tau)
        s_t = TT.s_stale_far("box", {"bottom": lo_t, "top": hi_t},
                             int(inc.t_birth), j_tau, h, l, c, abr)
        onset = first_stale(seq, inc.t_birth, int(inc.t_birth), j_tau,
                            h, l, c, abr)
        w0c, w1c = cand_window(e, r["cand"])
        pend_end = j_tau if r["killer"] == "proposed" else w1c
        frees = onset is not None and onset <= pend_end
        edge = bool(r.get("edge_matched"))
        n_sk += bool(s_k["stale"])
        n_st += bool(s_t["stale"])
        n_free += frees
        n_free_edge += frees and edge
        if frees:
            uniq_free.add((r["panel"], inc.id))
            free_rows.append((r["panel"], r["tau"], inc.id, edge,
                              onset, w0c, w1c))
        if frees and edge:
            uniq_free_edge.add((r["panel"], inc.id))
    print("BUDGET_CUT rows %d | stale@kill %d | stale@tau %d"
          % (n, n_sk, n_st))
    print("frees (onset<=pend_end): %d rows / %d unique incumbents"
          % (n_free, len(uniq_free)))
    print("frees edge-matched: %d rows / %d unique incumbents"
          % (n_free_edge, len(uniq_free_edge)))
    print("free rows:", [(p, t, i, e) for p, t, i, e, *_ in free_rows])


if __name__ == "__main__":
    main()
