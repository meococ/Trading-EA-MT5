"""DR_RULES_S2_report.py — aggregate S2 measurements -> summary json."""
import collections
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PANELS_E5 = ["9.17b", "9.36c", "9.42b", "9.48b"]
PANELS_S1B = {"9.10c": "BOX0001", "9.33c": "BOX0001",
              "9.36c": "BOX0001", "9.40a": "BOX0002"}


def rows_of(name):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        return []
    return [json.loads(x) for x in open(p, encoding="utf8") if x.strip()]


def clean_rate(rows, pred):
    keys = ("C1@1.0", "C3w@3.0", "C4w@4", "C6g", "C5@q95")
    n = {k: [0, 0] for k in keys}
    for r in rows:
        if not pred(r):
            continue
        cl = r.get("clean0")
        if cl is None:
            continue
        for k in keys:
            n[k][1] += 1
            if cl.get(k):
                n[k][0] += 1
    return {k: (v[0], v[1], (v[0] / v[1]) if v[1] else None)
            for k, v in n.items()}


def main():
    evs = rows_of("DR_RULES_S2_events.jsonl")
    rows = rows_of("DR_RULES_S2_rows.jsonl")
    hits = rows_of("DR_RULES_S2_hits.jsonl")
    gold = rows_of("DR_RULES_S2_golden.jsonl")
    pref = rows_of("DR_RULES_S2_prefix.jsonl")
    cen = rows_of("DR_RULES_S2_census.jsonl")
    rcl = rows_of("DR_RULES_S2_review_closed.jsonl")
    s1 = json.load(open(os.path.join(HERE, "DR_RULES_S1_summary.json"),
                        encoding="utf8"))

    # ---- hits -------------------------------------------------------
    H = {"0": sum(1 for e in evs if e["hits"]["0"]),
         "k2": sum(1 for e in evs if e["hits"]["k2"]),
         "k3": sum(1 for e in evs if e["hits"]["k3"])}
    nf_tot = collections.Counter()
    for e in evs:
        for f, v in e["nf_hits"].items():
            nf_tot[f] += v
    gained = {a: [(e["panel"], e["tau"]) for e in evs
                  if e["hits"][a] and not e["hits"]["0"]]
              for a in ("k2", "k3")}
    lost = {a: [(e["panel"], e["tau"]) for e in evs
                if e["hits"]["0"] and not e["hits"][a]]
            for a in ("k2", "k3")}
    # gained-by-promotion detail: pick changed and new pick matched
    promo = {a: [] for a in ("k2", "k3")}
    for e in evs:
        for a in ("k2", "k3"):
            if e["hits"][a] and e["picks"][a] != e["picks"]["0"]:
                promo[a].append({"panel": e["panel"], "tau": e["tau"],
                                 "pick0": e["picks"]["0"],
                                 "pick": e["picks"][a]})

    # ---- per-hit table ----------------------------------------------
    det = [d for d in hits]

    # ---- counts ------------------------------------------------------
    n_closed = {"k2": sum(1 for r in rows if r["closed2"]),
                "k3": sum(1 for r in rows if r["closed3"])}
    n_closed_pick = {"k2": sum(1 for r in rows
                               if r["closed2"] and r["picked0"]),
                     "k3": sum(1 for r in rows
                               if r["closed3"] and r["picked0"])}
    # drawn boxes per panel-event, before/after
    ev_boxes = [(e["n_live_boxes"], e["n_closed2"], e["n_closed3"])
                for e in evs]
    mean_boxes = {"before": float(np.mean([x[0] for x in ev_boxes])),
                  "k2": float(np.mean([x[0] - x[1] for x in ev_boxes])),
                  "k3": float(np.mean([x[0] - x[2] for x in ev_boxes]))}

    # ---- owner-clean: survivors only ---------------------------------
    def is_hit(r):
        return r["picked0"] or r["matched0"]

    clean = {"hit_before": clean_rate(rows, is_hit),
             "nonhit_before": clean_rate(rows,
                                         lambda r: not is_hit(r))}
    for a in ("k2", "k3"):
        key = "closed" + a[1]
        clean["hit_after_" + a] = clean_rate(
            rows, lambda r: is_hit(r) and not r[key])
        clean["nonhit_after_" + a] = clean_rate(
            rows, lambda r: (not is_hit(r)) and not r[key])

    # ---- census -------------------------------------------------------
    ratios = {"0": [], "k2": [], "k3": []}
    for x in cen:
        if x["n_gold"]:
            ratios["0"].append(x["n_eng"] / x["n_gold"])
            ratios["k2"].append(x["drawn_k2"] / x["n_gold"])
            ratios["k3"].append(x["drawn_k3"] / x["n_gold"])
    census = {a: [float(np.median(v)),
                  int(sum(1 for r in v if r <= 5.0)), len(v)]
              for a, v in ratios.items()}

    # ---- author compliance -------------------------------------------
    g_closed = {"k2": sum(1 for g in gold if g["closed2"]),
                "k3": sum(1 for g in gold if g["closed3"]),
                "n": len(gold)}

    # ---- prefix -------------------------------------------------------
    pref_n = {"k2": [0, 0], "k3": [0, 0]}
    for p in pref:
        a = "k%d" % p["k"]
        pref_n[a][1] += 1
        if p["same"]:
            pref_n[a][0] += 1

    # ---- reviewer cases -----------------------------------------------
    rev = {"s1b_fatal": [], "e5": []}
    rcl_by = collections.defaultdict(dict)
    for x in rcl:
        rcl_by[(x["panel"], x["id"])][x["k"]] = x
    for pan, oid in PANELS_S1B.items():
        ent = rcl_by.get((pan, oid), {})
        rev["s1b_fatal"].append(
            {"panel": pan, "id": oid,
             "closed_k2": 2 in ent,
             "closed_k3": 3 in ent,
             "confirm2": ent.get(2, {}).get("confirm_bar"),
             "confirm3": ent.get(3, {}).get("confirm_bar")})
    # E5: every closed box-family object in the drawn set per panel
    e5_by = collections.defaultdict(list)
    for x in rcl:
        if x["panel"] in PANELS_E5:
            e5_by[x["panel"]].append(x)
    for pan in PANELS_E5:
        rev["e5"].append({"panel": pan, "closed": e5_by.get(pan, [])})

    parent_nf = s1["nf_hits"]
    out = {
        "events": len(evs), "rows": len(rows),
        "hits": H, "nf_hits": dict(nf_tot), "parent_nf": parent_nf,
        "gained": gained, "lost": lost, "promoted": promo,
        "per_hit": det,
        "counts": {"closed_all": n_closed,
                   "closed_picked": n_closed_pick},
        "mean_boxes": mean_boxes,
        "clean": clean,
        "census": census,
        "author": g_closed,
        "prefix": pref_n,
        "review": rev,
        "keep": {a: {
            "box_ok": H[a] >= 16,
            "fams_ok": all(nf_tot[f] >= parent_nf[f] - 1
                           for f in parent_nf),
            "clutter_ok": census[a][0] <= 5.0,
            "prefix_ok": pref_n[a][0] == pref_n[a][1]}
            for a in ("k2", "k3")},
    }
    json.dump(out, open(os.path.join(HERE, "DR_RULES_S2_summary.json"),
                        "w", encoding="utf8"), indent=1)
    print(json.dumps({"hits": H, "nf": dict(nf_tot),
                      "gained": gained, "lost": lost,
                      "closed": n_closed, "closed_picked": n_closed_pick,
                      "mean_boxes": mean_boxes,
                      "census": census, "author": g_closed,
                      "prefix": pref_n, "keep": out["keep"],
                      "s1b_fatal": rev["s1b_fatal"]}, indent=1))


if __name__ == "__main__":
    main()
