"""DR_RULES_S1_report.py — aggregate S1 transform results ->
DR_RULES_S1_summary.json + printed tables + DR_RULES_S1.md body data.
"""
import collections
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def rows(fn):
    p = os.path.join(HERE, fn)
    return [json.loads(x) for x in open(p, encoding="utf8")] \
        if os.path.exists(p) else []


def main():
    evs = rows("DR_RULES_S1_events.jsonl")
    objs = rows("DR_RULES_S1_objects.jsonl")
    hits = rows("DR_RULES_S1_hits.jsonl")
    starts = rows("DR_RULES_S1_golden_starts.jsonl")
    pref = rows("DR_RULES_S1_prefix.jsonl")

    # ---------------- hits -----------------
    h0 = sum(1 for e in evs if e["hits"]["0"])
    ha = sum(1 for e in evs if e["hits"]["a"])
    hb = sum(1 for e in evs if e["hits"]["b"])
    lost_a = [e for e in evs if e["hits"]["0"] and not e["hits"]["a"]]
    gain_a = [e for e in evs if not e["hits"]["0"] and e["hits"]["a"]]
    lost_b = [e for e in evs if e["hits"]["0"] and not e["hits"]["b"]]
    gain_b = [e for e in evs if not e["hits"]["0"] and e["hits"]["b"]]
    nf = collections.Counter()
    for e in evs:
        for f, n in (e.get("nf_hits") or {}).items():
            nf[f] += n

    # ---------------- drops ----------------
    n_ev_drop = sum(1 for e in evs if e["n_dropped_a"])
    n_obj_drop = sum(e["n_dropped_a"] for e in evs)
    n_box_ev = sum(e["n_live_boxes"] for e in evs)
    lv = collections.defaultdict(set)
    dv = collections.defaultdict(set)
    for o in objs:
        lv[(o["panel"], o["id"])].add(o["tau"])
        if o["a_dropped"]:
            dv[(o["panel"], o["id"])].add(o["tau"])
    full_drop = {k for k in dv if lv[k] == dv[k]}
    any_drop = set(dv)

    # ---------------- owner-clean on picks ---------------
    def clean_rows(flag, key):
        sub = [o for o in objs if o[flag]]
        out = {}
        for lab, pred in (("hit", lambda o: o["matched0"]),
                          ("nonhit", lambda o: not o["matched0"]),
                          ("all", lambda o: True)):
            s2 = [o for o in sub if pred(o)]
            for rule in ("C1@1.0", "C3w@3.0", "C4w@4", "C6g", "C5@q95"):
                vals = [o[key][rule] for o in s2 if o[key] is not None]
                out[(lab, rule)] = (sum(vals), len(vals))
        return out, len(sub)

    c0, npick0 = clean_rows("picked0", "clean0")
    ca, npicka = clean_rows("picked_a", "clean_a")
    cb, npickb = clean_rows("picked_b", "clean_b")

    # all live boxes (secondary population)
    def clean_all(key):
        out = {}
        for rule in ("C1@1.0", "C3w@3.0", "C4w@4", "C6g", "C5@q95"):
            vals = [o[key][rule] for o in objs if o[key] is not None]
            out[rule] = (sum(vals), len(vals))
        return out

    a0, aa, ab = clean_all("clean0"), clean_all("clean_a"), \
        clean_all("clean_b")
    n_clean_a_eval = sum(1 for o in objs if o["clean_a"] is not None)

    # ---------------- per-hit table ----------------------
    per_hit = {}
    for d in hits:
        per_hit.setdefault((d["panel"], d["gi"]), {})[d["arm"]] = d
    hit_lines = []
    for (panel, gi), dd in sorted(per_hit.items()):
        a, b = dd["a"], dd["b"]
        for arm, d in (("a", a), ("b", b)):
            if d["orig_dropped"]:
                why = "dropped(<3 bars)"
            elif d["same_pick"] and d["matched1"]:
                why = "kept"
            elif d["same_pick"] and not d["matched1"]:
                why = "lost: iou %.2f->%s" % (
                    d["iou0"] or 0,
                    "NA" if d["iou1"] is None else "%.2f" % d["iou1"])
            elif d["fill"]:
                why = "fill by %s (%s)" % (
                    d["pick"], "match" if d["matched1"] else "miss")
            else:
                why = "?"
            hit_lines.append({
                "panel": panel, "gi": gi, "arm": arm,
                "iou0": d["iou0"], "iou1": d["iou1"],
                "cov0": d.get("cov0"), "cov1": d.get("cov1"),
                "dlo": d["dlo"], "dhi": d["dhi"],
                "we0": d["we0"], "we1": d["we1"], "wg": d["wg"],
                "matched1": d["matched1"], "why": why})

    # ---------------- author starts ----------------------
    gaps = [s["gap"] for s in starts if s["gap"] is not None]
    n_none = sum(1 for s in starts if s["gap"] is None)
    gs = {"n": len(starts), "no_event": n_none,
          "gap_le2": sum(1 for g in gaps if g <= 2),
          "gap_le3": sum(1 for g in gaps if g <= 3),
          "gap_le5": sum(1 for g in gaps if g <= 5),
          "median": float(np.median(gaps)) if gaps else None,
          "p90": float(np.percentile(gaps, 90)) if gaps else None,
          "n_ev": len(gaps)}

    # ---------------- prefix ------------------------------
    n_same = sum(1 for p in pref if p["same"])
    pref_out = {"n": len(pref), "same": n_same,
                "diff": [p for p in pref if not p["same"]][:10]}

    # ---------------- clutter (published census) ----------
    import sys
    PERC = os.path.dirname(HERE)
    sys.path.insert(0, os.path.join(PERC, "evalcheck"))
    sys.path.insert(0, PERC)
    import common as C                      # noqa: E402
    import eval as EV                       # noqa: E402
    import eval_v2 as V2                    # noqa: E402
    import cache as CA                      # noqa: E402
    import DR_RULES_measure as M            # noqa: E402

    rec_by_id = {r["id"]: r for r in C.load_tune()}
    n_eng = {}
    n_gold = {}
    for panel in {o["panel"] for o in objs}:
        rec = rec_by_id[panel]
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m_day, _o, _h, _l, _c = CA.bars(rec["date"])
        e = M.pickled(rec["date"], w1)
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        eobjs = V2.eng_objects(e, m_day, w0, w1) if e is not None else []
        n_eng[panel] = len(eobjs)
        n_gold[panel] = len(g2)
    drop_per_panel = collections.Counter(p for (p, _i) in full_drop)
    ratios = {}
    for arm, drops in (("0", {}), ("a", drop_per_panel)):
        rs = [((n_eng[p] - drops.get(p, 0)) / n_gold[p])
              for p in n_eng if n_gold[p]]
        ratios[arm] = (float(np.median(rs)) if rs else None,
                       sum(1 for r in rs if r <= 5.0), len(rs))
    ratios["b"] = ratios["0"]          # S1-b never drops

    out = {"hits": {"0": h0, "a": ha, "b": hb},
           "nf_hits": dict(nf),
           "lost": {"a": len(lost_a), "b": len(lost_b)},
           "gained": {"a": len(gain_a), "b": len(gain_b)},
           "drops": {"events": n_ev_drop, "obj_events": n_obj_drop,
                     "box_events": n_box_ev,
                     "full_drop_objs": len(full_drop),
                     "any_drop_objs": len(any_drop)},
           "clean_pick": {"0": {"|".join(k): v for k, v in c0.items()},
                          "a": {"|".join(k): v for k, v in ca.items()},
                          "b": {"|".join(k): v for k, v in cb.items()},
                          "n0": npick0, "na": npicka, "nb": npickb,
                          "n_a_eval": n_clean_a_eval},
           "clean_all": {"0": a0, "a": aa, "b": ab,
                         "n": len(objs), "n_a_eval": n_clean_a_eval},
           "per_hit": hit_lines,
           "golden_starts": gs,
           "prefix": pref_out,
           "census": ratios}
    with open(os.path.join(HERE, "DR_RULES_S1_summary.json"), "w",
              encoding="utf8") as fh:
        json.dump(out, fh, indent=1, default=float)

    print("hits 0/a/b = %d/%d/%d  lost a=%d b=%d  gained a=%d b=%d "
          "nonbox=%s" % (h0, ha, hb, len(lost_a), len(lost_b),
                         len(gain_a), len(gain_b), dict(nf)))
    print("drops: %d obj-events dropped (%d box-events), %d evs, "
          "full-drop objs=%d" % (n_obj_drop, n_box_ev, n_ev_drop,
                                 len(full_drop)))
    print("golden starts:", gs)
    print("prefix: %d/%d same" % (n_same, len(pref)))
    for lab in ("hit", "nonhit"):
        print("clean picks %s:" % lab)
        for rule in ("C1@1.0", "C3w@3.0", "C4w@4", "C6g", "C5@q95"):
            b0 = c0[(lab, rule)]; ba = ca[(lab, rule)]
            bb = cb[(lab, rule)]
            print("  %-8s 0:%d/%d a:%d/%d b:%d/%d" % (
                rule, b0[0], b0[1], ba[0], ba[1], bb[0], bb[1]))


if __name__ == "__main__":
    main()
