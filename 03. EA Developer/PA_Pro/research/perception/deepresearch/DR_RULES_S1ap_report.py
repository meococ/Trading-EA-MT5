"""DR_RULES_S1ap_report.py — aggregate S1-a' measurements -> summary json.

Reads DR_RULES_S1ap_{events,rows,hits,prefix}.jsonl plus the parent
numbers from DR_RULES_S1_summary.json (baseline + arms a/b) and writes
DR_RULES_S1ap_summary.json.
"""
import collections
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def rows_of(name):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        return []
    return [json.loads(x) for x in open(p, encoding="utf8") if x.strip()]


def clean_rate(rows, key, pred):
    """Fraction of rows passing owner-clean predicate `pred` on field
    `key` (dict). key may be 'clean0' or 'clean_ap'."""
    n = {k: [0, 0] for k in
         ("C1@1.0", "C3w@3.0", "C4w@4", "C6g", "C5@q95")}
    for r in rows:
        if not pred(r):
            continue
        cl = r.get(key)
        if cl is None:
            continue
        for k in n:
            n[k][1] += 1
            if cl.get(k):
                n[k][0] += 1
    return {k: (v[0], v[1], (v[0] / v[1]) if v[1] else None)
            for k, v in n.items()}


def main():
    evs = rows_of("DR_RULES_S1ap_events.jsonl")
    rows = rows_of("DR_RULES_S1ap_rows.jsonl")
    hits = rows_of("DR_RULES_S1ap_hits.jsonl")
    pref = rows_of("DR_RULES_S1ap_prefix.jsonl")
    s1 = json.load(open(os.path.join(HERE, "DR_RULES_S1_summary.json"),
                        encoding="utf8"))

    # ---- hits -------------------------------------------------------
    h0 = sum(1 for e in evs if e["hits"]["0"])
    hap = sum(1 for e in evs if e["hits"]["ap"])
    # nf hits must equal parent
    nf_tot = collections.Counter()
    for e in evs:
        for f, v in e["nf_hits"].items():
            nf_tot[f] += v
    parent_hits = s1["hits"]["0"]            # 16
    parent_nf = s1.get("nf_hits")            # {'line':20,'level':7,'bracket':29}

    # ---- transform stats -------------------------------------------
    n_rows = len(rows)
    n_reset = sum(1 for r in rows if r["ap_kind"] == "reset")
    n_clamp = sum(1 for r in rows if r["ap_kind"] == "clamp3")
    n_none = sum(1 for r in rows if r["ap_kind"] == "none")
    n_ext = sum(1 for r in rows if r["ap_extended"])
    # how many would S1-a have dropped? clamp3 count == drop count under a
    evs_with_clamp = sum(1 for e in evs if e["n_clamp3"])

    # ---- owner-clean, hits vs non-hits ------------------------------
    def is_hit(r):
        return r["picked0"] or r["matched0"]

    hit_rows = [r for r in rows if is_hit(r)]
    non_rows = [r for r in rows if not is_hit(r)]
    # after-arm split uses picked_ap for "pick" view; report both
    pick_rows = [r for r in rows if r["picked_ap"]]
    nonpick = [r for r in rows if not r["picked_ap"]]
    clean = {
        "hit_before": clean_rate(rows, "clean0", is_hit),
        "hit_after": clean_rate(rows, "clean_ap", is_hit),
        "nonhit_before": clean_rate(rows, "clean0",
                                    lambda r: not is_hit(r)),
        "nonhit_after": clean_rate(rows, "clean_ap",
                                   lambda r: not is_hit(r)),
        "pick_after": clean_rate(rows, "clean_ap",
                                 lambda r: r["picked_ap"]),
        "nonpick_after": clean_rate(rows, "clean_ap",
                                    lambda r: not r["picked_ap"]),
    }

    # ---- per-hit table ----------------------------------------------
    det = []
    for d in hits:
        det.append({"panel": d["panel"], "tau": d["tau"], "gi": d["gi"],
                    "kind0": d.get("kind0"), "same": d["same_pick"],
                    "iou0": d["iou0"], "iou1": d.get("iou1"),
                    "cov0": d["cov0"], "cov1": d.get("cov1"),
                    "matched1": d["matched1"],
                    "dlo": d.get("dlo"), "dhi": d.get("dhi")})
    lost = [d for d in hits if not d["matched1"]]

    # ---- prefix ------------------------------------------------------
    pref_same = sum(1 for p in pref if p["same"])

    # ---- clutter: ap never drops -> parent census --------------------
    clutter = {"median_ratio": s1["census"]["0"][0],
               "n_le5": s1["census"]["0"][1],
               "n_panels": s1["census"]["0"][2]}

    out = {
        "events": len(evs),
        "rows": n_rows,
        "hits": {"0": h0, "ap": hap, "parent": parent_hits},
        "nf_hits": dict(nf_tot), "parent_nf": parent_nf,
        "transform": {"reset": n_reset, "clamp3": n_clamp,
                      "none": n_none, "extended": n_ext,
                      "evs_with_clamp3": evs_with_clamp},
        "clean": clean,
        "per_hit": det,
        "lost": [{"panel": d["panel"], "tau": d["tau"], "gi": d["gi"],
                  "kind0": d.get("kind0"),
                  "cov1": d.get("cov1"), "iou1": d.get("iou1")}
                 for d in lost],
        "prefix": {"n": len(pref), "same": pref_same},
        "clutter": clutter,
        "keep_rule": {
            "box_ok": hap >= parent_hits,
            "fams_ok": all(nf_tot[f] >= parent_nf[f] - 1
                           for f in parent_nf),
            "clutter_ok": clutter["median_ratio"] <= 5.0,
        },
    }
    json.dump(out, open(os.path.join(HERE, "DR_RULES_S1ap_summary.json"),
                        "w", encoding="utf8"), indent=1)
    print(json.dumps({k: out[k] for k in
                      ("hits", "nf_hits", "transform", "prefix",
                       "keep_rule")}, indent=1))
    print("lost:", out["lost"])


if __name__ == "__main__":
    main()
