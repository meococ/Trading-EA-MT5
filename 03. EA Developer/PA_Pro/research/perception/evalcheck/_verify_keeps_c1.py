"""_verify_keeps_c1.py — EVAL-AUDIT independent verification of the
C-round-1 keeps (R34 §34.8 item 3.2, R36 §36.2, R39 §39.2, R40 §40.2).

For each keep, both arms are loaded from the cache in ONE process at ONE
hash and scored by m1_row.py (this lane's own scorer — never _m1.py):

  * M1 (box@1, level@1, line@2) + paired day-bootstrap CIs vs v0;
  * clutter median (gate_pack definition) + the per-panel distribution;
  * the six diagnostic rows;
  * flag-OFF identity vs the kept-parent reference: canonical objects
    AND cand_log compared on every shared cached run;
  * flag provenance: the params actually baked into each arm's pickles
    (e.p), so a stale arm definition can't pass silently.

Usage: python evalcheck/_verify_keeps_c1.py [--only K1|K2|K3]
"""
import argparse
import collections
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)

import common as C                              # noqa: E402
import cache as CA                              # noqa: E402
import funnel as F                              # noqa: E402
import m1_row as M                              # noqa: E402
import pa_slots                                 # noqa: E402

# keep name -> (A/B hash, off variant, on variant, parent references
#               [(ref hash, ref variant, label)], flag paths expected)
KEEPS = {
    "K1": dict(
        name="line.lab_score", ab_hash="afba83c5f74d96c4",
        off="labscore_off", on="labscore_on",
        parents=[("9283b3892c7fe8fc", "ab_base",
                  "STABLE 9283b389 (=584c7743), all flags OFF")],
        flags_on=["line.lab_score"],
        flags_off=["line.lab_score"]),
    "K2": dict(
        name="level.defended_origin+level.def_mini_off",
        ab_hash="e62f2dc9ee7fa6e2",
        off="deforig_off", on="deforig_on",
        parents=[("afba83c5f74d96c4", "labscore_on",
                  "K1-kept state (lab_score ON) at parent hash"),
                 ("e62f2dc9ee7fa6e2", "famv2_off",
                  "same-hash flag-inert check")],
        flags_on=["line.lab_score", "level.defended_origin",
                  "level.def_mini_off"],
        flags_off=["line.lab_score"]),
    "K3": dict(
        name="bxcombo (wd + box_rank + fam_budget/caps + in-family "
             "displacement)",
        ab_hash="dd96c5fe49c28d74",
        off="bxcombo_off", on="bxcombo_on",
        parents=[("2ca5c67f620291d8", "lcpick2_off",
                  "K2-kept state at parent hash 2ca5c67f"),
                 ("dd96c5fe49c28d74", "c1r_base",
                  "same-hash flag-inert check")],
        flags_on=["line.lab_score", "level.defended_origin",
                  "level.def_mini_off", "box.wick_edges",
                  "box.dedup_iou", "box.rank_score",
                  "salience.box_lab_score_use", "salience.fam_budget",
                  "salience.fam_caps"],
        flags_off=["line.lab_score", "level.defended_origin",
                   "level.def_mini_off"]),
    "K4": dict(
        name="salience.box_score_pick (box supersede, arm A)",
        ab_hash="cfb862d40c805a25",
        off="bxsup_off", on="bxsup_on",
        parents=[("dd96c5fe49c28d74", "bxcombo_on",
                  "K3-kept state at parent hash dd96c5fe "
                  "(= defaults ON at 22888182)")],
        flags_on=["line.lab_score", "level.defended_origin",
                  "level.def_mini_off", "box.wick_edges",
                  "box.dedup_iou", "box.rank_score",
                  "salience.box_lab_score_use", "salience.fam_budget",
                  "salience.fam_caps", "salience.box_score_pick"],
        flags_off=["line.lab_score", "level.defended_origin",
                   "level.def_mini_off", "box.wick_edges",
                   "box.dedup_iou", "box.rank_score",
                   "salience.box_lab_score_use", "salience.fam_budget",
                   "salience.fam_caps"],
        target="box"),
    # arm B is a REJECTED arm, not a keep: measured so the rejection
    # itself is verified (B-vs-A: box must not drop >1).
    "K4B": dict(
        name="box_score_pick_prio (arm B, REJECTED arm - verify the "
             "rejection)",
        ab_hash="cfb862d40c805a25",
        off="bxsupp_off", on="bxsupp_on",
        parents=[("cfb862d40c805a25", "bxsup_on",
                  "same-hash: arm-A kept state = B's parent")],
        flags_on=["line.lab_score", "level.defended_origin",
                  "level.def_mini_off", "box.wick_edges",
                  "box.dedup_iou", "box.rank_score",
                  "salience.box_lab_score_use", "salience.fam_budget",
                  "salience.fam_caps", "salience.box_score_pick",
                  "salience.box_score_pick_prio"],
        flags_off=["line.lab_score", "level.defended_origin",
                   "level.def_mini_off", "box.wick_edges",
                   "box.dedup_iou", "box.rank_score",
                   "salience.box_lab_score_use", "salience.fam_budget",
                   "salience.fam_caps", "salience.box_score_pick"],
        target="box"),
    "K5": dict(
        name="line.slope_floor=0.25 (R41 §41.4 flatness item)",
        ab_hash="75a9650ca6ae7f79",
        off="lnfloor_off", on="lnfloor_on",
        parents=[("cfb862d40c805a25", "bxsup_on",
                  "K4-kept state at parent hash cfb862d4")],
        flags_on=["line.lab_score", "level.defended_origin",
                  "level.def_mini_off", "box.wick_edges",
                  "box.dedup_iou", "box.rank_score",
                  "salience.box_lab_score_use", "salience.fam_budget",
                  "salience.fam_caps", "salience.box_score_pick"],
        flags_off=["line.lab_score", "level.defended_origin",
                   "level.def_mini_off", "box.wick_edges",
                   "box.dedup_iou", "box.rank_score",
                   "salience.box_lab_score_use", "salience.fam_budget",
                   "salience.fam_caps", "salience.box_score_pick"],
        target="line"),
    "BXP": dict(
        name="salience.box_prio (R42 §42.4 / R43 §43.6 price-priority "
             "rank rule)",
        ab_hash="cd00d0bede994c8e",
        off="bxprio_off", on="bxprio_on",
        parents=[("75a9650ca6ae7f79", "lnfloor_on",
                  "K5-kept state at parent hash 75a9650c")],
        flags_on=["line.lab_score", "level.defended_origin",
                  "level.def_mini_off", "box.wick_edges",
                  "box.dedup_iou", "box.rank_score",
                  "salience.box_lab_score_use", "salience.fam_budget",
                  "salience.fam_caps", "salience.box_score_pick",
                  "line.slope_floor", "salience.box_prio"],
        flags_off=["line.lab_score", "level.defended_origin",
                   "level.def_mini_off", "box.wick_edges",
                   "box.dedup_iou", "box.rank_score",
                   "salience.box_lab_score_use", "salience.fam_budget",
                   "salience.fam_caps", "salience.box_score_pick",
                   "line.slope_floor"],
        target="box"),
    "FAMCTX": dict(
        name="fam_context (R44 §44.2: CONTEXT_* own family, live "
             "budget 1 under fam_budget)",
        ab_hash="88438120dc55043f",
        off="famctx_off", on="famctx_on",
        parents=[("75a9650ca6ae7f79", "lnfloor_on",
                  "K5-kept state at parent hash 75a9650c")],
        flags_on=["line.lab_score", "level.defended_origin",
                  "level.def_mini_off", "box.wick_edges",
                  "box.dedup_iou", "box.rank_score",
                  "salience.box_lab_score_use", "salience.fam_budget",
                  "salience.fam_caps", "salience.box_score_pick",
                  "line.slope_floor", "salience.fam_context"],
        flags_off=["line.lab_score", "level.defended_origin",
                   "level.def_mini_off", "box.wick_edges",
                   "box.dedup_iou", "box.rank_score",
                   "salience.box_lab_score_use", "salience.fam_budget",
                   "salience.fam_caps", "salience.box_score_pick",
                   "line.slope_floor"],
        target="box"),
    "FAMCTX2": dict(
        name="fam_context + CONTEXT_RANGE births OFF (R44 §44.2 "
             "contingency, famcap_context_range=-1)",
        ab_hash="4dcc44d73e081c02",
        off="famctx_off", on="famctx_nocr_on",
        parents=[("75a9650ca6ae7f79", "lnfloor_on",
                  "K5-kept state at parent hash 75a9650c")],
        flags_on=["line.lab_score", "level.defended_origin",
                  "level.def_mini_off", "box.wick_edges",
                  "box.dedup_iou", "box.rank_score",
                  "salience.box_lab_score_use", "salience.fam_budget",
                  "salience.fam_caps", "salience.box_score_pick",
                  "line.slope_floor", "salience.fam_context"],
        flags_off=["line.lab_score", "level.defended_origin",
                   "level.def_mini_off", "box.wick_edges",
                   "box.dedup_iou", "box.rank_score",
                   "salience.box_lab_score_use", "salience.fam_budget",
                   "salience.fam_caps", "salience.box_score_pick",
                   "line.slope_floor"],
        target="box"),
}

# flag paths we report provenance for (all flags that moved this round)
PROBE = ["line.lab_score", "level.defended_origin", "level.def_mini_off",
         "box.wick_edges", "box.dedup_iou", "box.rank_score",
         "box.leg_edges", "box.dense_anchors", "box.watch_birth",
         "box.tail_bars", "box.wait_ttl",
         "salience.box_lab_score_use", "salience.fam_budget",
         "salience.fam_caps", "salience.fam_ledger",
         "salience.lc_score_pick", "salience.box_prom_rank",
         "salience.level_touch_rec", "salience.line_dedup_merge",
         "salience.revive_exempt", "marker.day_extreme_only",
         "salience.box_score_pick", "salience.box_score_pick_prio",
         "salience.fam_total_live", "salience.famcap_bracket",
         "line.slope_floor", "line.steep_pick", "salience.box_prio",
         "salience.fam_context"]


def _getp(p, dotted):
    d = p
    for k in dotted.split("."):
        if not isinstance(d, dict) or k not in d:
            return "<absent>"
        d = d[k]
    return d


def flag_state(eng_hash, variant, rec):
    """The flags baked into one cached run (from the pickled e.p)."""
    w1 = rec["window"]["x1"] or 1439
    f = os.path.join(CA.CACHE, "run_%s%s_%s_%s.pkl"
                     % (variant + "_" if variant else "",
                        eng_hash, rec["date"], w1))
    if not os.path.exists(f):
        return None
    e = pickle.load(open(f, "rb"))
    p = getattr(e, "p", None) or {}
    return {k: _getp(p, k) for k in PROBE}


def canon(e, with_events=False):
    """(objects, cand_log) canonical tuple.  Objects compared as
    (type, why, t_birth, t_left, t_right, state, geometry); events
    included only when with_events."""
    objs = []
    for o in e.objects:
        row = (o.type, getattr(o, "why", None), getattr(o, "t_birth", None),
               getattr(o, "t_left", None), getattr(o, "t_right", None),
               getattr(o, "state", None), CA._canon(o.geometry))
        if with_events:
            row += (CA._canon(getattr(o, "events", None)),)
        objs.append(row)
    return repr(sorted(map(repr, objs))), repr(CA._canon(e.cand_log))


def identity(h_a, v_a, h_b, v_b, recs):
    """Compare objects+cand_log on every shared cached run."""
    import glob
    n = same_obj = same_log = same_ev = miss = 0
    diffs = []
    for rec in recs:
        pa = os.path.join(CA.CACHE, "run_%s%s_%s_*.pkl"
                          % (v_a + "_" if v_a else "", h_a,
                             rec["date"]))
        for fa in glob.glob(pa):
            w1s = fa.rsplit("_", 1)[1].split(".")[0]
            fb = os.path.join(
                CA.CACHE, "run_%s%s_%s_%s.pkl"
                % (v_b + "_" if v_b else "", h_b, rec["date"], w1s))
            if not os.path.exists(fb):
                miss += 1
                continue
            try:
                ea = pickle.load(open(fa, "rb"))
                eb = pickle.load(open(fb, "rb"))
            except Exception:
                miss += 1
                continue
            oa, la = canon(ea)
            ob, lb = canon(eb)
            oae, _lae = canon(ea, with_events=True)
            obe, _lbe = canon(eb, with_events=True)
            n += 1
            same_obj += oa == ob
            same_log += la == lb
            same_ev += oae == obe
            if (oa != ob or la != lb) and len(diffs) < 6:
                diffs.append("%s w1=%s obj_eq=%s log_eq=%s"
                             % (rec["date"], w1s, oa == ob, la == lb))
    return n, same_obj, same_log, same_ev, miss, diffs


def clutter_dist(res):
    """Per-panel clutter ratio distribution + panels-to-move analysis."""
    r = sorted(res["diag_ratios"])
    n = len(r)
    med = float(np.median(r))
    # how many panels must rise above `med` for the median to exceed
    # `thresh`: median moves past t when fewer than n/2 values are <= t.
    def need(thresh):
        le = sum(1 for x in r if x <= thresh)
        return max(0, le - (n - 1) // 2) if n % 2 else max(
            0, le - (n // 2 - 1))
    qs = np.percentile(r, [0, 10, 25, 50, 75, 90, 100])
    hist = collections.Counter()
    for x in r:
        hist[round(x * 3) / 3] += 1      # 1/3-wide buckets
    return {"n": n, "median": med, "p": qs,
            "need_gt_5_0": need(5.0), "need_gt_5_33": need(5.33 + 1e-9),
            "at_or_below_5": sum(1 for x in r if x <= 5.0),
            "hist": sorted(hist.items())}


def run_keep(key):
    k = KEEPS[key]
    recs = C.load_tune()
    import random
    rng = random.Random(M.SEED)
    print("\n" + "=" * 72)
    print("%s: %s" % (key, k["name"]))
    print("A/B hash %s  off=%s  on=%s" % (k["ab_hash"], k["off"],
                                          k["on"]))
    for ph, pv, pl in k["parents"]:
        print("parent ref: %s var=%s (%s)" % (ph[:8], pv, pl))
    # flag provenance from the pickles themselves
    fs_off = flag_state(k["ab_hash"], k["off"], recs[0])
    fs_on = flag_state(k["ab_hash"], k["on"], recs[0])
    fs_par = flag_state(k["parents"][0][0], k["parents"][0][1], recs[0])
    if fs_off is None or fs_on is None:
        print("!! cache missing for an arm — cannot verify")
        return
    norm = lambda x: False if x == "<absent>" else x       # noqa: E731
    print("\nflag provenance (pickled e.p, panel %s):" % recs[0]["id"])
    prov_ok = True
    for f in PROBE:
        a, b, pp = fs_off.get(f), fs_on.get(f), (fs_par or {}).get(f)
        mark = ""
        if f in k["flags_on"] and not b:
            mark, prov_ok = "  <-- expected ON", False
        if a != b or (f in k["flags_on"] or f in k["flags_off"]):
            print("  %-32s off=%-9s on=%-9s parent=%s%s"
                  % (f, a, b, pp, mark))
    # OFF arm must carry exactly the kept flags of the parent state
    for f in k["flags_off"]:
        if norm(fs_off.get(f)) != norm(fs_par.get(f)):
            print("  !! OFF arm flag %s=%s but parent ref has %s"
                  % (f, fs_off.get(f), fs_par.get(f)))
            prov_ok = False
    # scoring
    off = M.measure(k["ab_hash"], k["off"], recs)
    on = M.measure(k["ab_hash"], k["on"], recs)
    v0 = M.measure(F.code_hash(F.V0_FILES), "m1_v0", recs)
    if len(v0["tau"]) < 400:
        v0 = M.measure(F.code_hash(F.V0_FILES), "", recs)
    print("\nM1 rows (own scorer, cache-only):")
    M.report("v0", v0, rng=rng)
    o_off = M.report("%s OFF" % k["off"], off, v0=v0, rng=rng)
    o_on = M.report("%s ON" % k["on"], on, v0=v0, rng=rng)
    # identity: OFF vs each parent reference, all shared cached runs
    id_all_ok = True
    for ph, pv, pl in k["parents"]:
        n, so, sl, se, miss, diffs = identity(k["ab_hash"], k["off"],
                                            ph, pv, recs)
        print("\nflag-OFF identity vs %s var=%s (%s): shared=%d  "
              "objects_eq=%d  cand_log_eq=%d  with_events_eq=%d  "
              "missing=%d" % (ph[:8], pv, pl, n, so, sl, se, miss))
        for dline in diffs:
            print("   DIFF " + dline)
        if miss or so != n or sl != n:
            id_all_ok = False
    # clutter distribution
    cd = clutter_dist({**on, "diag_ratios":
                       [d["ratio"] for d in on["diag"]
                        if not np.isnan(d["ratio"])]})
    print("\nclutter dist ON arm: n=%d median=%.2f  p0/p25/p50/p75/p100="
          % (cd["n"], cd["median"])
          + " ".join("%.2f" % x for x in (cd["p"][0], cd["p"][2],
                                         cd["p"][3], cd["p"][4],
                                         cd["p"][6])))
    print("  panels with ratio<=5.0: %d/%d; to push median>5.0 need "
          "%d panel(s) raised above 5.0; >5.33 need %d"
          % (cd["at_or_below_5"], cd["n"], cd["need_gt_5_0"],
             cd["need_gt_5_33"]))
    print("  hist (1/3 buckets):", cd["hist"])
    # verdict
    v0r = {f: M.fam_recall(v0["tau"], f, kk) for f, kk in M.M1}
    onr = {f: M.fam_recall(on["tau"], f, kk) for f, kk in M.M1}
    offr = {f: M.fam_recall(off["tau"], f, kk) for f, kk in M.M1}
    legs = []
    tgt = k.get("target") or {"K1": "line", "K2": "level",
                              "K3": "box"}.get(key)
    for f, kk in M.M1:
        up = onr[f][0] > offr[f][0]
        drop = offr[f][0] - onr[f][0]
        legs.append("%s@%d %d->%d" % (f, kk, offr[f][0], onr[f][0]))
        if f == tgt:
            legs[-1] += " target+%s" % ("UP" if up else "NOT-UP")
        elif drop > 1:
            legs[-1] += " DROP>1"
    cl_ok = cd["median"] <= 5.0
    print("\nlegs: %s | clutter %.2f<=5.0:%s | OFF-id all-ok:%s | "
          "provenance %s"
          % ("; ".join(legs), cd["median"], cl_ok, id_all_ok, prov_ok))
    return {"key": key, "on": o_on, "off": o_off, "v0": v0,
            "id_ok": id_all_ok, "clutter": cd, "prov_ok": prov_ok}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    keys = [args.only] if args.only else list(KEEPS)
    with pa_slots.slot("evalcheck-verify-c1", timeout=1800):
        for key in keys:
            run_keep(key)


if __name__ == "__main__":
    main()
