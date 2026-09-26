"""DR_RULES_report.py — R77 s77.3 aggregation: Parts B, C, D, G.

Reads DR_RULES_{golden,live,events}.jsonl (from DR_RULES_measure.py),
derives the author-quantile thresholds for C2/C5, then:

  B  author pass-rate per rule x family x variant + Wilson 95 CI +
     p10..p95 distributions of every continuous stat.
  C  per rule x family: pass-rate on C-3 matched picks (hits at risk)
     vs unmatched picks (false objects removed), canonical 625 events.
  D  first-order (selection-only): re-pick family top-k after dropping
     rule-failing live objects; hits/fam, clutter, slot fillers.
  G  verdicts per the preregistered contract.

Outputs: DR_RULES_summary.json (everything), DR_RULES_d.jsonl (per
variant x event replay detail), prints the verdict table.

Usage: python deepresearch/DR_RULES_report.py
"""
import collections
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FAM_BUDGET = {"box": 1, "line": 2, "level": 1, "bracket": 1}
RULE_FAMS = {"C1": ("box", "level"), "C2": ("box", "level", "line"),
             "C3": ("box",), "C4": ("box",), "C5": ("box",),
             "C6": ("box",), "C7": ("level", "line"), "C8": ("level",)}
QS = (10, 25, 50, 75, 90, 95)


def wilson(k, n, z=1.959964):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, ctr - half), min(1.0, ctr + half))


def q(v, pct):
    v = sorted(x for x in v if x is not None)
    if not v:
        return None
    return float(np.quantile(v, pct / 100.0))


def dist(v):
    return {("p%d" % q_): q(v, q_) for q_ in QS}


# ------------------------------------------------------------------ #
# pass predicates — None means "not evaluable on this row"
# ------------------------------------------------------------------ #

def make_pass(thr):
    """thr: {('C2',fam): s, ('C5','box'): w} author-quantile cutoffs."""
    def _p(rule_var, r):
        rid, var = rule_var.split("@")
        if rid == "C1":
            v = r.get("c1_abr")
            if v is None:
                return None
            return v <= float(var)
        if rid == "C1p":
            v = r.get("c1_pip")
            return None if v is None else v <= float(var)
        if rid == "C2":
            v = r.get("c2_s")
            if v is None:
                return None
            return v <= thr[("C2", r["fam"])]
        if rid == "C3":
            v = r.get("c3_r")
            return None if v is None else v < float(var)
        if rid == "C3w":
            v = r.get("c3_r_win")
            return None if v is None else v < float(var)
        if rid == "C4":
            v = r.get("c4_r")
            return None if v is None else v < float(var)
        if rid == "C4w":
            v = r.get("c4_r_win")
            return None if v is None else v < float(var)
        if rid == "C5":
            v = r.get("width_bars")
            if v is None:
                return None
            w = thr[("C5", "box")] if var in ("q90", "q95") \
                else float(var)
            key = ("C5", "box", var)
            if var in ("q90", "q95"):
                w = thr[key]
            return v <= w
        if rid == "C6":
            v = r.get("c6_maxd")
            if v is None:
                return None
            return v <= r["c6_tol"]
        if rid == "C6g":                       # ruler-tol sensitivity
            v = r.get("c6_maxd")
            if v is None or r.get("tol_g") is None:
                return None
            return v <= r["tol_g"]
        if rid == "C7":
            v = r.get("c7_sw")
            return None if v is None else v <= int(var)
        if rid == "C7s":                       # drawn-span sensitivity
            v = r.get("c7_sw_span")
            return None if v is None else v <= int(var)
        if rid == "C7f":                       # full-span sensitivity
            v = r.get("c7_sw_full")
            return None if v is None else v <= int(var)
        if rid == "C8":
            if "c8_npiv" not in r:
                return None
            v = r.get("c8_beyond_abr")
            return True if v is None else v < float(var)
        if rid == "C8a":                       # anchor-birth sensitivity
            if "c8_npiv_anch" not in r:
                return None
            v = r.get("c8_beyond_abr_anch")
            return True if v is None else v < float(var)
        raise KeyError(rule_var)
    return _p


def rule_id(rv):
    return {"C1p": "C1", "C3w": "C3", "C4w": "C4", "C5w": "C5",
            "C6g": "C6", "C7s": "C7", "C7f": "C7", "C8a": "C8"}.get(
        rv.split("@")[0], rv.split("@")[0])


def fam_of(r):
    return r["fam"]


def main():
    gold = [json.loads(x) for x in
            open(os.path.join(HERE, "DR_RULES_golden.jsonl"),
                 encoding="utf8")]
    live = [json.loads(x) for x in
            open(os.path.join(HERE, "DR_RULES_live.jsonl"),
                 encoding="utf8")]
    evs = [json.loads(x) for x in
           open(os.path.join(HERE, "DR_RULES_events.jsonl"),
                encoding="utf8")]
    by_ev = collections.defaultdict(list)
    for r in live:
        by_ev[(r["panel"], r["tau"])].append(r)

    # ---------------- thresholds from the author distribution -------
    g_by_fam = collections.defaultdict(list)
    for r in gold:
        g_by_fam[r["fam"]].append(r)
    thr = {}
    thr_val = {}
    for f in ("box", "level", "line"):
        vs = [r.get("c2_s") for r in g_by_fam[f]]
        thr[("C2", f, "q95")] = q(vs, 95)
        thr[("C2", f, "q90")] = q(vs, 90)
        thr_val["C2@" + f] = {"q95": thr[("C2", f, "q95")],
                              "q90": thr[("C2", f, "q90")]}
    wb = [r.get("width_bars") for r in g_by_fam["box"]]
    thr[("C5", "box", "q95")] = q(wb, 95)
    thr[("C5", "box", "q90")] = q(wb, 90)
    thr_val["C5@box"] = {"q95": thr[("C5", "box", "q95")],
                         "q90": thr[("C5", "box", "q90")]}
    ww = [r.get("width_win_bars") for r in g_by_fam["box"]]
    thr[("C5w", "box", "q95")] = q(ww, 95)
    thr[("C5w", "box", "q90")] = q(ww, 90)
    thr_val["C5w@box"] = {"q95": thr[("C5w", "box", "q95")],
                          "q90": thr[("C5w", "box", "q90")]}

    def p_of(rv):
        rid = rv.split("@")[0]
        if rid == "C2":
            return lambda r, _rv=rv: (
                None if r.get("c2_s") is None else
                r["c2_s"] <= thr[("C2", r["fam"], _rv.split("@")[1])])
        if rid == "C5":
            def _c5(r, _rv=rv):
                v = r.get("width_bars")
                if v is None:
                    return None
                var = _rv.split("@")[1]
                w = thr[("C5", "box", var)] if var in ("q90", "q95") \
                    else float(var)
                return v <= w
            return _c5
        if rid == "C5w":
            def _c5w(r, _rv=rv):
                v = r.get("width_win_bars")
                if v is None:
                    return None
                var = _rv.split("@")[1]
                w = thr[("C5w", "box", var)] if var in ("q90", "q95") \
                    else float(var)
                return v <= w
            return _c5w
        _p = make_pass(thr)
        return lambda r, _rv=rv: _p(_rv, r)

    VARIANTS = []
    for v in ("0.5", "1.0"):
        VARIANTS.append(("C1@" + v, ("box", "level")))
    VARIANTS.append(("C1p@2", ("box", "level")))      # 2-pip reference
    for v in ("q95", "q90"):
        VARIANTS.append(("C2@" + v, ("box", "level", "line")))
    for v in ("2.5", "3.0"):
        VARIANTS.append(("C3@" + v, ("box",)))
    for v in ("3", "4"):
        VARIANTS.append(("C4@" + v, ("box",)))
    for v in ("q95", "q90", "20"):
        VARIANTS.append(("C5@" + v, ("box",)))
    VARIANTS.append(("C6@clu", ("box",)))
    VARIANTS.append(("C6g@clu", ("box",)))            # ruler-tol sens.
    for v in ("2", "3"):
        VARIANTS.append(("C7@" + v, ("level", "line")))
        VARIANTS.append(("C7s@" + v, ("level", "line")))  # span sens.
    VARIANTS.append(("C7f@2", ("level", "line")))     # full-span sens.
    for v in ("1", "2"):
        VARIANTS.append(("C8@" + v, ("level",)))
        VARIANTS.append(("C8a@" + v, ("level",)))     # anchor sens.
    # containment-window sensitivities (the drawn span includes the
    # breakout bar + extension; the window is the congestion itself)
    for v in ("2.5", "3.0"):
        VARIANTS.append(("C3w@" + v, ("box",)))
    for v in ("3", "4"):
        VARIANTS.append(("C4w@" + v, ("box",)))
    for v in ("q95", "q90", "20"):
        VARIANTS.append(("C5w@" + v, ("box",)))

    # ---------------- Part B: author compliance ----------------------
    B = {}
    for rv, fams in VARIANTS:
        pf = p_of(rv)
        rid = rule_id(rv)
        for f in fams:
            rows = [r for r in g_by_fam[f]]
            vals = [pf(r) for r in rows]
            ev = [v for v in vals if v is not None]
            k = sum(1 for v in ev if v)
            lo, hi = wilson(k, len(ev))
            B[(rid, rv, f)] = {"n": len(rows), "n_ev": len(ev),
                               "k": k, "rate": (k / len(ev)
                                                if ev else None),
                               "lo": lo, "hi": hi}

    # continuous-stat distributions per family
    STATS = {"box": ["c1_pip", "c1_abr", "c2_s", "c3_r", "c4_r",
                     "width_bars", "c6_dhi", "c6_dlo", "c6_maxd",
                     "c3_r_win", "c4_r_win", "width_win_bars"],
             "level": ["c1_pip", "c1_abr", "c2_s", "c7_sw",
                       "c7_sw_full", "c8_beyond_abr"],
             "line": ["c2_s", "c7_sw", "c7_sw_full"]}
    Bdist = {}
    for f, keys in STATS.items():
        Bdist[f] = {s: dist([r.get(s) for r in g_by_fam[f]])
                    for s in keys}

    # ---------------- Part C: matched vs unmatched -------------------
    picks = [r for r in live if r["picked"]]
    ev_key = {(r["panel"], r["tau"]) for r in evs if r["is_tau_event"]}
    C3 = {}
    for rv, fams in VARIANTS:
        pf = p_of(rv)
        rid = rule_id(rv)
        for f in fams:
            mp = [r for r in picks if r["fam"] == f and r["matched"]]
            up = [r for r in picks if r["fam"] == f and not r["matched"]]
            up_tau = [r for r in up
                      if (r["panel"], r["tau"]) in ev_key]
            def rate(rows):
                vals = [pf(r) for r in rows]
                vv = [v for v in vals if v is not None]
                return (sum(1 for v in vv if v) / len(vv)
                        if vv else None, len(vv))
            rm, nm = rate(mp)
            ru, nu = rate(up)
            rut, nut = rate(up_tau)
            C3[(rid, rv, f)] = {
                "pass_matched": rm, "n_matched": nm,
                "pass_unmatched": ru, "n_unmatched": nu,
                "removal_unmatched": (None if ru is None else 1 - ru),
                "pass_unmatched_tauonly": rut,
                "n_unmatched_tauonly": nut,
                "removal_tauonly": (None if rut is None else 1 - rut)}

    # ---------------- Part D: first-order (selection-only) -----------
    D = {}
    d_rows = open(os.path.join(HERE, "DR_RULES_d.jsonl"), "w",
                  encoding="utf8")
    ev_by_key = {(e["panel"], e["tau"]): e for e in evs}
    base_hits = collections.Counter()
    # clutter: window-census live-at-tau ratio — per scored panel,
    # mean(live+marks at golden-object taus)/n_scorable_goldens,
    # median over panels (baseline reproduces GATE_PACK loose 3.89).
    def census(ev_clutter):
        """ev_clutter: {(panel,tau): live_count_after_filter}."""
        by_p = collections.defaultdict(list)
        n_g2 = {}
        for e in evs:
            by_p[e["panel"]].append(e)
            n_g2[e["panel"]] = e["n_g2"]
        rat = []
        for p, es in by_p.items():
            objs = [ev_clutter[(e["panel"], e["tau"])]
                    for e in es if e["kind"] == "obj"]
            if objs and n_g2[p]:
                rat.append(float(np.mean(objs)) / n_g2[p])
        return (float(np.median(rat)) if rat else None,
                sum(1 for x in rat if x <= 5.0), len(rat))

    base_map = {}
    for e in evs:
        base_map[(e["panel"], e["tau"])] = e["n_live"] + e["n_marks"]
    base_census = census(base_map)
    # plain live-at-tau median over object events
    base_live_med = float(np.median(
        [e["n_live"] + e["n_marks"] for e in evs
         if e["kind"] == "obj"]))
    # baseline hits per family from live rows (top-k by rank)
    for key, rows in by_ev.items():
        e = ev_by_key[key]
        gsf = collections.defaultdict(set)
        for g in e["gs"]:
            gsf[g["fam"]].add(g["gi"])
        for f, k in FAM_BUDGET.items():
            tops = [r for r in sorted(
                        (r for r in rows if r["fam"] == f),
                        key=lambda r: r["rank"])][:k]
            hit_gis = set()
            for r in tops:
                hit_gis |= set(r["match_gis"])
            base_hits[f] += len(hit_gis & gsf[f])

    for rv, fams in VARIANTS:
        pf = p_of(rv)
        rid = rule_id(rv)
        hits_a = collections.Counter()
        clutter_map = {}
        fills = []
        lost_picks = 0
        for e in evs:
            key = (e["panel"], e["tau"])
            rows = by_ev.get(key, [])
            gsf = collections.defaultdict(set)
            for g in e["gs"]:
                gsf[g["fam"]].add(g["gi"])
            n_drop = 0
            fam_ranked = collections.defaultdict(list)
            for r in sorted(rows, key=lambda r: r["rank"]):
                f = r["fam"]
                drop = f in fams and pf(r) is False
                # stat missing (None) -> keep (cannot condemn)
                if drop:
                    n_drop += 1
                else:
                    fam_ranked[f].append(r)
            clutter_map[key] = len(rows) - n_drop + e["n_marks"]
            for f, k in FAM_BUDGET.items():
                before = [r for r in sorted(
                              (r for r in rows if r["fam"] == f),
                              key=lambda r: r["rank"])][:k]
                after = fam_ranked[f][:k]
                bid = {r["id"] for r in before}
                hit_gis = set()
                for r in after:
                    hit_gis |= set(r["match_gis"])
                hits_a[f] += len(hit_gis & gsf[f])
                for r in after:
                    if r["id"] not in bid and f in fams:
                        fills.append({"rv": rv, "panel": e["panel"],
                                      "tau": e["tau"], "fam": f,
                                      "id": r["id"],
                                      "matched": bool(r["match_gis"])})
                lost_picks += sum(1 for r in before
                                  if r["fam"] in fams and
                                  r["id"] not in {a["id"]
                                                  for a in after})
            d_rows.write(json.dumps(
                {"rv": rv, "panel": e["panel"], "tau": e["tau"],
                 "n_drop": n_drop,
                 "clutter": clutter_map[key]}) + "\n")
        cm, cmargin, cn = census(clutter_map)
        D[(rid, rv)] = {
            "hits_after": dict(hits_a),
            "d_hits": {f: hits_a[f] - base_hits[f] for f in FAM_BUDGET},
            "clutter_med": cm, "clutter_margin": cmargin,
            "clutter_panels": cn,
            "live_med": float(np.median(
                [clutter_map[(e["panel"], e["tau"])] for e in evs
                 if e["kind"] == "obj"])),
            "n_fills": len(fills),
            "fills_matched": sum(1 for x in fills if x["matched"]),
            "lost_picks": lost_picks,
            "max_fam_loss": min(0, min(
                (hits_a[f] - base_hits[f]) for f in FAM_BUDGET))}
    d_rows.close()

    # ---------------- Part G: verdicts -------------------------------
    verdicts = []
    for rv, fams in VARIANTS:
        rid = rule_id(rv)
        if rv.split("@")[0] in ("C3w", "C4w", "C5w", "C6g", "C7s",
                                "C7f", "C8a"):          # sensitivities
            continue
        for f in fams:
            b = B[(rid, rv, f)]
            c = C3[(rid, rv, f)]
            d = D[(rid, rv)]
            comp = b["rate"]
            rem = c["removal_unmatched"]
            # R77 s77.3 literal: "every OTHER family" = non-target families.
            # In-family hit cost is reported (pass_matched / infam_loss),
            # not thresholded.
            ok_hits = all(v >= -1 for ff, v in d["d_hits"].items()
                          if ff not in fams)
            ok_clu = d["clutter_med"] <= 5.0
            infam_loss = min(v for ff, v in d["d_hits"].items()
                             if ff in fams)
            if comp is None:
                verd = "INFO"
            elif comp < 0.90:
                verd = "TRADER-ONLY"
            elif rem is not None and rem >= 0.20 and ok_hits and ok_clu:
                verd = "BUILD-CANDIDATE"
            else:
                verd = "INFO"
            verdicts.append({"rule": rid, "variant": rv, "fam": f,
                             "author_n": b["n_ev"], "author_pass": comp,
                             "author_ci": [b["lo"], b["hi"]],
                             "pass_matched": c["pass_matched"],
                             "n_matched": c["n_matched"],
                             "removal_unmatched": rem,
                             "n_unmatched": c["n_unmatched"],
                             "d_hits": d["d_hits"],
                             "infam_loss": infam_loss,
                             "clutter": d["clutter_med"],
                             "verdict": verd})

    out = {"thresholds": thr_val,
           "B": {"|".join(k): v for k, v in B.items()},
           "Bdist": Bdist,
           "C": {"|".join(k): v for k, v in C3.items()},
           "D": {"|".join(k): v for k, v in D.items()},
           "base_hits": dict(base_hits),
           "base_census": base_census,
           "base_live_med": base_live_med,
           "verdicts": verdicts}
    with open(os.path.join(HERE, "DR_RULES_summary.json"), "w",
              encoding="utf8") as fh:
        json.dump(out, fh, indent=1, default=float)

    print("base hits:", dict(base_hits), "census:", base_census,
          "live med:", base_live_med)
    for v in verdicts:
        print("%-8s %-6s pass=%s pm=%s rem=%s dhits=%s clu=%.2f -> %s" % (
            v["variant"], v["fam"],
            "NA" if v["author_pass"] is None else "%.3f" % v["author_pass"],
            "NA" if v["pass_matched"] is None
            else "%.2f" % v["pass_matched"],
            "NA" if v["removal_unmatched"] is None
            else "%.3f" % v["removal_unmatched"],
            v["d_hits"], v["clutter"], v["verdict"]))


if __name__ == "__main__":
    main()
