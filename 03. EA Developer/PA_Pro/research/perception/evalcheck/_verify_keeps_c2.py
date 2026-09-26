"""_verify_keeps_c2.py — EVAL-AUDIT independent verification of the
C-round-2 keeps (PLAYBOOK_C2 §5.3 E1, keep rules §3.1/§3.2/§3.4).

Same machinery as _verify_keeps_c1.py (imported), plus:
  * margin leg: panels with clutter ratio <= 5.0, both arms (the §3.2
    headline number);
  * keep-class aware legs: "gen" -> §3.1, "ink" -> §3.2.

Usage: python evalcheck/_verify_keeps_c2.py [--only K7|K8|K9]
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)

import common as C                              # noqa: E402
import funnel as F                              # noqa: E402
import m1_row as M                              # noqa: E402
import pa_slots                                 # noqa: E402
import _verify_keeps_c1 as V                    # noqa: E402

# extra C-2 flags in the provenance report
V.PROBE += ["marker.off", "marker.day_extreme_only", "box.cong_pivedge",
            "box.wick_birth", "salience.rate_label_tf",
            "salience.ctx_yield", "salience.ctx_convert"]

K16 = ["line.lab_score", "level.defended_origin", "level.def_mini_off",
       "box.wick_edges", "box.dedup_iou", "box.rank_score",
       "salience.box_lab_score_use", "salience.fam_budget",
       "salience.fam_caps", "salience.box_score_pick", "line.slope_floor",
       "box.cong_trigger"]

KEEPS = {
    "K7": dict(
        name="marker.off (ink-only headroom keep, §3.2)",
        kind="ink", ab_hash="66f596dc8234b436",
        off="ctxy_off", on="bmoff_on",
        parents=[("9acaa206c8d386dc", "m1_v1",
                  "STABLE C-1 = K7's parent, cross-hash OFF identity")],
        flags_on=K16 + ["marker.off"],
        flags_off=K16),
    "K7B": dict(
        name="bmday = marker.day_extreme_only (REJECTED alt: verify "
             "margin +4 < +5)",
        kind="ink", ab_hash="66f596dc8234b436",
        off="ctxy_off", on="bmday_on",
        parents=[("9acaa206c8d386dc", "m1_v1",
                  "STABLE C-1 parent")],
        flags_on=K16 + ["marker.day_extreme_only"],
        flags_off=K16),
    "K8": dict(
        name="box.cong_pivedge (generation keep on K7 parent, §3.1)",
        kind="gen", ab_hash="81f7503f346dab9f",
        off="pedg_off", on="pedg_on",
        parents=[("81f7503f346dab9f", "c1r_p_base",
                  "K7 defaults at same hash (flag-inert check)"),
                 ("66f596dc8234b436", "bmoff_on",
                  "K7 ON arm at its own A/B hash (cross-hash)")],
        flags_on=K16 + ["marker.off", "box.cong_pivedge"],
        flags_off=K16 + ["marker.off"],
        target="box"),
    "K9": dict(
        name="salience.rate_label_tf=2 (ink-only, §3.2)",
        kind="ink", ab_hash="759d9036b20969a8",
        off="ltfcap_off", on="ltfcap_on",
        parents=[("81f7503f346dab9f", "pedg_on",
                  "K8 ON state = K9's parent (be4eea26 equiv, "
                  "cross-hash)")],
        flags_on=K16 + ["marker.off", "box.cong_pivedge",
                        "salience.rate_label_tf"],
        flags_off=K16 + ["marker.off", "box.cong_pivedge"]),
    # chain consistency: post-flip default arms must equal the ON arms
    "K9D": dict(
        name="chain: c1r_p_base@ee2cbf12 (K9 defaults) == ltfcap_on",
        kind="chain", ab_hash="759d9036b20969a8",
        off="ltfcap_on", on=None,
        parents=[("ee2cbf1202db47b6", "c1r_p_base",
                  "K9-as-default arm at post-flip hash")],
        flags_on=[], flags_off=[]),
    "K8D": dict(
        name="chain: ltfcap_off@759d9036 == pedg_on (K8 default flip)",
        kind="chain", ab_hash="81f7503f346dab9f",
        off="pedg_on", on=None,
        parents=[("759d9036b20969a8", "ltfcap_off",
                  "K9 A/B OFF arm at its own hash")],
        flags_on=[], flags_off=[]),
}


def margin(res):
    r = [d["ratio"] for d in res["diag"] if not np.isnan(d["ratio"])]
    return sum(1 for x in r if x <= 5.0), len(r)


def run_keep(key):
    k = KEEPS[key]
    recs = C.load_tune()
    import random
    rng = random.Random(M.SEED)
    print("\n" + "=" * 72)
    print("%s: %s" % (key, k["name"]))
    print("A/B hash %s  off=%s  on=%s" % (k["ab_hash"], k["off"], k["on"]))
    for ph, pv, pl in k["parents"]:
        print("parent ref: %s var=%s (%s)" % (ph[:8], pv, pl))
    fs_off = V.flag_state(k["ab_hash"], k["off"], recs[0])
    if fs_off is None:
        print("!! cache missing for OFF arm — cannot verify")
        return
    if k["on"]:
        fs_on = V.flag_state(k["ab_hash"], k["on"], recs[0])
        fs_par = V.flag_state(k["parents"][0][0], k["parents"][0][1],
                              recs[0])
        norm = lambda x: False if x == "<absent>" else x       # noqa: E731
        print("\nflag provenance (pickled e.p, panel %s):"
              % recs[0]["id"])
        prov_ok = True
        for f in V.PROBE:
            a, b, pp = fs_off.get(f), fs_on.get(f), (fs_par or {}).get(f)
            mark = ""
            if f in k["flags_on"] and not b:
                mark, prov_ok = "  <-- expected ON", False
            if a != b or (f in k["flags_on"] or f in k["flags_off"]):
                print("  %-32s off=%-9s on=%-9s parent=%s%s"
                      % (f, a, b, pp, mark))
        for f in k["flags_off"]:
            if norm(fs_off.get(f)) != norm(fs_par.get(f)):
                print("  !! OFF arm flag %s=%s but parent ref has %s"
                      % (f, fs_off.get(f), fs_par.get(f)))
                prov_ok = False
    else:
        prov_ok = True
    off = M.measure(k["ab_hash"], k["off"], recs)
    v0 = M.measure(F.code_hash(F.V0_FILES), "m1_v0", recs)
    if len(v0["tau"]) < 400:
        v0 = M.measure(F.code_hash(F.V0_FILES), "", recs)
    M.report("v0", v0, rng=rng)
    o_off = M.report("%s OFF" % k["off"], off, v0=v0, rng=rng)
    if k["on"]:
        on = M.measure(k["ab_hash"], k["on"], recs)
        o_on = M.report("%s ON" % k["on"], on, v0=v0, rng=rng)
    id_all_ok = True
    for ph, pv, pl in k["parents"]:
        n, so, sl, se, miss, diffs = V.identity(k["ab_hash"], k["off"],
                                              ph, pv, recs)
        print("\nflag-OFF identity vs %s var=%s (%s): shared=%d  "
              "objects_eq=%d  cand_log_eq=%d  with_events_eq=%d  "
              "missing=%d" % (ph[:8], pv, pl, n, so, sl, se, miss))
        for dline in diffs:
            print("   DIFF " + dline)
        if miss or so != n or sl != n:
            id_all_ok = False
    if not k["on"]:
        print("chain check done: OFF-id %s" % id_all_ok)
        return {"key": key, "id_ok": id_all_ok}
    cd = V.clutter_dist({**on, "diag_ratios":
                         [d["ratio"] for d in on["diag"]
                          if not np.isnan(d["ratio"])]})
    cd_off = V.clutter_dist({**off, "diag_ratios":
                             [d["ratio"] for d in off["diag"]
                              if not np.isnan(d["ratio"])]})
    m_on, n_on = margin(on)
    m_off, n_off = margin(off)
    print("\nclutter: OFF med=%.2f margin=%d/%d -> ON med=%.2f "
          "margin=%d/%d (delta %+d)"
          % (cd_off["median"], m_off, n_off, cd["median"], m_on, n_on,
             m_on - m_off))
    offr = {f: M.fam_recall(off["tau"], f, kk) for f, kk in M.M1}
    onr = {f: M.fam_recall(on["tau"], f, kk) for f, kk in M.M1}
    legs = []
    ok = True
    if k["kind"] == "gen":
        tgt = k["target"]
        for f, kk in M.M1:
            up = onr[f][0] > offr[f][0]
            drop = offr[f][0] - onr[f][0]
            legs.append("%s@%d %d->%d" % (f, kk, offr[f][0], onr[f][0]))
            if f == tgt:
                legs[-1] += " target+%s" % ("UP" if up else "NOT-UP")
                ok &= up
            elif drop > 1:
                legs[-1] += " DROP>1"
                ok = False
        ok &= cd["median"] <= 5.0
    else:  # ink
        for f, kk in M.M1:
            drop = offr[f][0] - onr[f][0]
            legs.append("%s@%d %d->%d" % (f, kk, offr[f][0], onr[f][0]))
            if drop > 0:
                legs[-1] += " LOSS"
                ok = False
        ok &= cd["median"] <= cd_off["median"] + 1e-9
        ok &= (m_on - m_off) >= 5
    ok &= id_all_ok and prov_ok
    print("legs: %s | clutter %.2f->%.2f margin %+d | OFF-id %s | "
          "prov %s => %s"
          % ("; ".join(legs), cd_off["median"], cd["median"],
             m_on - m_off, id_all_ok, prov_ok,
             "CONFIRMED" if ok else "FAILED"))
    return {"key": key, "confirmed": ok, "id_ok": id_all_ok,
            "margin": (m_off, m_on), "clutter": (cd_off["median"],
                                                cd["median"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    keys = [args.only] if args.only else list(KEEPS)
    with pa_slots.slot("evalcheck-verify-c2", timeout=1800):
        for key in keys:
            run_keep(key)


if __name__ == "__main__":
    main()
