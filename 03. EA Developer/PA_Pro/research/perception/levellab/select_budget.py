"""select_budget — V8: selection at the author's budget (R17 §17.2).

Three proposers, compared at matched ink on 198 TUNE panels:
  (a) lab proposer (levels_lab final config), objects ranked by score;
  (b) production levels.py proposal stream, rate caps removed
      (every cand_log proposal counts), ranked by production score;
  (c) naive baseline: every theta1/theta2 pivot with >= min_defences,
      ranked by distance to price (lab engine, sess_origins off,
      approach gate disabled).

Recall@k: at golden tau = t0+10min keep the top-k LIVE levels by a
ranker; hit if any kept object's price is within golden tol.
Birth caps: keep only the first C births per panel (chronological —
rate-limit semantics), match any live object at tau.

Rankers (features evaluated causally at tau):
  birth_score | -dist_abr | ndef_tau | age | cls | ret24 | barrier |
  combo (rank-avg of ndef, -dist, age)

Validation: day-level 5-fold CV — choose the best ranker on 4 folds,
score it on the 5th. Report CV numbers, never the in-sample best.
Every row carries births/panel and live levels at tau.

Run: python -X utf8 select_budget.py [--limit N] [--save out.json]
"""
import argparse
import bisect
import json
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
sys.path.insert(0, _PERC)
sys.path.insert(0, os.path.join(_PERC, "golden"))
sys.path.insert(0, os.path.join(_PERC, "evalcheck"))
sys.path.insert(0, os.path.join(_PERC, "linelab"))

import bars_cache  # noqa: E402
import eval as EV  # noqa: E402
import eval_v2 as E2  # noqa: E402
import common as C  # noqa: E402
import levels_lab  # noqa: E402
from anatomy_levels import TIER_A  # noqa: E402

LAB_P = {"sess_grace_bars": 48, "min_score": 1.0}
NAIVE_P = dict(LAB_P, sess_origins=False, approach_abr=1e9,
               min_score=-1e9, live_abr=1e9, stale_retire_bars=10 ** 9,
               pierce_dead_bars=10 ** 9)

CLS_ORD = {"theta2": 4, "theta1": 3, "asia": 2, "session": 2, "leg": 1}
ROUTE_CLS = {"session_extreme": 2, "broken_line_edge": 3,
             "broken_box_edge_up": 2, "broken_box_edge_down": 2,
             "congestion_edge": 2, "formation_mid": 1,
             "formation_extreme": 1}


def proxy_death_i(price, birth_i, day):
    """Simple causal lifecycle for stream proposals (uniform rules):
    dead at the first bar after birth whose close is > 3*ABR from the
    level, or after 2 consecutive closes through the level, or after
    60 bars without an extreme within tol."""
    n = len(day["m"])
    abr = day["abr"]
    tol = 1.5
    last_touch = birth_i
    pierce = 0
    prev_sgn = 0
    for i in range(birth_i, n):
        c, h, l = day["c"][i], day["h"][i], day["l"][i]
        if abs(c - price) > 3.0 * max(abr[i], 1e-9):
            return i
        hit = abs(h - price) <= tol or abs(l - price) <= tol
        if hit:
            last_touch = i
        if i - last_touch > 60:
            return i
        sgn = 1 if c > price + tol else (-1 if c < price - tol else 0)
        if sgn != 0 and prev_sgn != 0 and sgn != prev_sgn:
            pierce += 1
            if pierce >= 2:
                return i
        elif sgn == 0:
            pierce = 0
        if sgn != 0:
            prev_sgn = sgn
    return n - 1


def lab_objects(eng, day):
    """Live-span records for a lab-engine run: (birth_min, death_min,
    price, score0, cls, origin_min)."""
    m = day["m"]
    out = []
    for o in eng.objects:
        g = o.geometry
        b = m[o.t_birth]
        d = m[o.t_right] if o.t_right is not None else m[len(m) - 1]
        out.append({"b": int(b), "d": int(d), "price": g["price"],
                    "score": g.get("score0", 0.0),
                    "cls": g.get("cls"), "org": int(m[g["origin_i"]]),
                    "type": o.type})
    return out


def prod_objects(cands, day):
    """Production cand_log proposals -> same records with proxy life."""
    m = day["m"]
    out = []
    seen = set()
    for cd in cands:
        if cd["kind"] not in E2.LEVEL_TYPES or cd.get("price") is None:
            continue
        i = min(cd["idx"], len(m) - 1)
        key = (round(cd["price"], 1), cd["route"])
        if key in seen:          # same proposal re-logged at outcomes
            continue
        seen.add(key)
        di = proxy_death_i(cd["price"], i, day)
        out.append({"b": int(m[i]), "d": int(m[di]),
                    "price": cd["price"],
                    "score": cd.get("score") or 0.0,
                    "cls": ROUTE_CLS.get(cd.get("route"), 0),
                    "cls_name": cd.get("route"),
                    "org": int(m[min(int(cd.get("t0", i)),
                                     len(m) - 1)]),
                    "type": cd["kind"]})
    return out


def touches_between(price, i0, i1, day, tol=1.5):
    """Count distinct in-tol extreme runs (defence events) in [i0, i1]."""
    n = 0
    run = False
    for i in range(i0, i1 + 1):
        hit = abs(day["h"][i] - price) <= tol or \
            abs(day["l"][i] - price) <= tol
        if hit and not run:
            n += 1
        run = hit
    return n


def rankers(objs, tau_min, day):
    """Return {ranker_name: ordered list of objs (best first)}."""
    m = day["m"]
    ti = bisect.bisect_left(m, tau_min)
    if ti >= len(m):
        ti = len(m) - 1
    ct, abr_t = day["c"][ti], max(day["abr"][ti], 1e-9)
    travel = np.sign(day["c"][ti] - day["c"][max(0, ti - 12)])
    feats = {}
    for o in objs:
        oi = min(bisect.bisect_left(m, o["b"]), len(m) - 1)
        nd = touches_between(o["price"], oi, ti, day)
        dist = abs(ct - o["price"]) / abr_t
        age = tau_min - o["org"]
        cls = o["cls"] if isinstance(o["cls"], int) else \
            CLS_ORD.get(o["cls"], 0)
        r24 = 1 if touches_between(o["price"], max(0, ti - 24), ti,
                                   day) else 0
        side_ok = travel == 0 or \
            np.sign(o["price"] - ct) == travel or \
            np.sign(o["price"] - ct) == 0
        feats[id(o)] = {"bs": o["score"], "nd": nd, "dist": dist,
                        "age": age, "cls": cls, "r24": r24,
                        "side_ok": side_ok,
                        "barr": 0}
    # next barrier: nearest live level on the travel side
    cands = [o for o in objs if feats[id(o)]["side_ok"]]
    if cands:
        nb = min(cands, key=lambda o: feats[id(o)]["dist"])
        feats[id(nb)]["barr"] = 1

    def key(name):
        if name == "birth_score":
            return lambda o: feats[id(o)]["bs"]
        if name == "dist":
            return lambda o: -feats[id(o)]["dist"]
        if name == "ndef":
            return lambda o: feats[id(o)]["nd"]
        if name == "age":
            return lambda o: feats[id(o)]["age"]
        if name == "cls":
            return lambda o: (feats[id(o)]["cls"], feats[id(o)]["bs"])
        if name == "ret24":
            return lambda o: (feats[id(o)]["r24"],
                              feats[id(o)]["bs"])
        if name == "barrier":
            return lambda o: (feats[id(o)]["barr"],
                              feats[id(o)]["bs"])
        if name == "combo":
            return lambda o: feats[id(o)]["_combo"]
        raise KeyError(name)

    # equal-weight rank combo of ndef, -dist, age
    for nm, k in (("ndef", lambda f: f["nd"]),
                  ("dist", lambda f: -f["dist"]),
                  ("age", lambda f: f["age"])):
        order = sorted(objs, key=lambda o: k(feats[id(o)]))
        for rk, o in enumerate(order):
            feats[id(o)]["_c" + nm] = rk
    for o in objs:
        f = feats[id(o)]
        f["_combo"] = f["_cndef"] + f["_cdist"] + f["_cage"]

    return {nm: sorted(objs, key=key(nm), reverse=True)
            for nm in ("birth_score", "dist", "ndef", "age", "cls",
                       "ret24", "barrier", "combo")}


RANKER_NAMES = ("birth_score", "dist", "ndef", "age", "cls", "ret24",
                "barrier", "combo")
KS = (1, 2, 3)
CAPS = (1, 2, 3, 5)


def wilson(h, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = h / n
    den = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (p, max(0.0, ctr - half), min(1.0, ctr + half))


def collect(recs):
    panels = []
    days = bars_cache.days()
    for k, rec in enumerate(recs):
        day = days[rec["date"]]
        day["abr"] = bars_cache.abr(day)
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        lab = levels_lab.LevelLabEngine(params=LAB_P)
        nav = levels_lab.LevelLabEngine(params=NAIVE_P)
        for i in range(len(day["m"])):
            if day["m"][i] > w1:
                break
            args = (day["t"][i], day["o"][i] / 1e4, day["h"][i] / 1e4,
                    day["l"][i] / 1e4, day["c"][i] / 1e4)
            lab.update(*args, cet_min=int(day["m"][i]))
            nav.update(*args, cet_min=int(day["m"][i]))
        import engine as ENG  # noqa: E402
        pe = EV.run_engine(ENG.PerceptionEngine, day["m"], day["t"],
                           day["o"], day["h"], day["l"], day["c"], w1)
        gobjs, _, _ = EV.gold_objects(rec)
        for g in gobjs:
            if g.get("t0") is None:
                g["t0"] = w0
            if g.get("t1") is None:
                g["t1"] = w1
        g2 = [g for g in gobjs if E2.scorable(g, w0, w1)
              and g["spec_type"] in E2.LEVEL_TYPES]
        panels.append({"id": rec["id"], "date": rec["date"],
                       "day": day, "w0": w0, "w1": w1,
                       "streams": {"lab": lab_objects(lab, day),
                                   "naive": lab_objects(nav, day),
                                   "prod": prod_objects(
                                       pe.cand_log or [], day)},
                       "prod_objs": E2.eng_objects(pe, day["m"],
                                                 w0, w1),
                       "g2": g2})
        if (k + 1) % 20 == 0:
            print("  %d/%d" % (k + 1, len(recs)), flush=True)
    return panels


def fam_prices_fn(prod_objs, day):
    """Cross-family dedup: prices already carried at tau by a live
    production BOX edge or PATTERN_LINE (line price extrapolated)."""
    m = day["m"]

    def prices(tau_min):
        ti = min(bisect.bisect_left(m, tau_min), len(m) - 1)
        out = []
        for o in prod_objs:
            if not (o["t_birth"] <= tau_min <= o["t1"]):
                continue
            if o["type"] == "BOX":
                out += [o.get("lo"), o.get("hi")]
            elif o["type"] in ("PATTERN_LINE", "CONTEXT_LINE") \
                    and o.get("p0") is not None:
                out.append(o["p0"] + o["slope"] *
                           (ti - o.get("t0_bar", ti)))
        return [p for p in out if p is not None]
    return prices


def eval_stream(objs, g2, day, ranker, k, dedup_objs=None):
    """recall@k over golden list g2 for one stream+ranker."""
    if not g2:
        return 0, 0
    hits = 0
    for g in g2:
        if g.get("price") is None:
            continue
        tau = g["t0"] + 10
        tol = E2.tol_px(g)
        gp = g["price"] * 1e4
        live = [o for o in objs if o["b"] <= tau <= o["d"]]
        if dedup_objs:
            live = [o for o in live if not any(
                abs(o["price"] - x) <= 3.0 for x in dedup_objs(tau))]
        if not live:
            continue
        order = rankers(live, tau, day)[ranker]
        top = order[:k]
        if any(abs(o["price"] - gp) <= tol for o in top):
            hits += 1
    return hits, len(g2)


def cap_eval(objs, g2, cap):
    """Only the first `cap` births (chronological) may exist; hit if a
    capped object is live at tau with matching price."""
    keep = sorted(objs, key=lambda o: o["b"])[:cap]
    hits = 0
    for g in g2:
        if g.get("price") is None:
            continue
        tau = g["t0"] + 10
        gp = g["price"] * 1e4
        tol = E2.tol_px(g)
        if any(o["b"] <= tau <= o["d"] and abs(o["price"] - gp) <= tol
               for o in keep):
            hits += 1
    return hits, len(g2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--save", default="")
    args = ap.parse_args()
    recs = bars_cache.tune_records()
    if args.limit:
        recs = recs[:args.limit]
    panels = collect(recs)

    results = {}
    streams = ("lab", "prod", "naive")
    for st in streams:
        results[st] = {gkey: {"k": {r: {kk: [0, 0] for kk in KS}
                                    for r in RANKER_NAMES},
                              "ktr": {r: {kk: [0, 0] for kk in KS}
                                      for r in RANKER_NAMES},
                              "cap": {cc: [0, 0] for cc in CAPS},
                              "captr": {cc: [0, 0] for cc in CAPS}}
                       for gkey in ("LEVEL_CARRIED", "MINI_LEVEL")}
        results[st].update({"births": [], "live": [],
                            "dd": {kk: [0, 0] for kk in KS},
                            "fold_rows": {
                                gkey: {
                                    r: {kk: [[] for _ in range(5)]
                                        for kk in KS}
                                    for r in RANKER_NAMES}
                                for gkey in ("LEVEL_CARRIED",
                                             "MINI_LEVEL")}})
    # TIER_A needs the raw golden object index: recompute gold objects
    # once per panel and mark trusted on the scorable copies by value.
    for p in panels:
        gobjs, _, _ = EV.gold_objects(
            next(r for r in recs if r["id"] == p["id"]))
        for g in p["g2"]:
            try:
                oi = gobjs.index(g)
            except ValueError:
                oi = -1
            g["_trusted"] = ("%s#%d" % (p["id"], oi)) not in TIER_A

    dates = sorted({p["date"] for p in panels})
    folds = [set(dates[i::5]) for i in range(5)]
    for st in streams:
        for p in panels:
            objs = p["streams"][st]
            day = p["day"]
            fi = next(i for i in range(5) if p["date"] in folds[i])
            results[st]["births"].append(len(objs))
            for gkey in ("LEVEL_CARRIED", "MINI_LEVEL"):
                gs = [g for g in p["g2"] if g["spec_type"] == gkey]
                gtr = [g for g in gs if g.get("_trusted")]
                if not gs:
                    continue
                for rn in RANKER_NAMES:
                    for kk in KS:
                        h, n = eval_stream(objs, gs, day, rn, kk)
                        results[st][gkey]["k"][rn][kk][0] += h
                        results[st][gkey]["k"][rn][kk][1] += n
                        results[st]["fold_rows"][gkey][rn][kk][fi] \
                            .append((h, n))
                        if gtr:
                            h2, n2 = eval_stream(objs, gtr, day, rn,
                                                 kk)
                            results[st][gkey]["ktr"][rn][kk][0] += h2
                            results[st][gkey]["ktr"][rn][kk][1] += n2
                for cc in CAPS:
                    h, n = cap_eval(objs, gs, cc)
                    results[st][gkey]["cap"][cc][0] += h
                    results[st][gkey]["cap"][cc][1] += n
                    if gtr:
                        h2, n2 = cap_eval(objs, gtr, cc)
                        results[st][gkey]["captr"][cc][0] += h2
                        results[st][gkey]["captr"][cc][1] += n2
            for g in p["g2"]:
                tau = g["t0"] + 10
                results[st]["live"].append(
                    sum(1 for o in objs if o["b"] <= tau <= o["d"]))
            # cross-family dedup variant (combo ranker)
            dd = fam_prices_fn(p["prod_objs"], day)
            gs = [g for g in p["g2"] if g["spec_type"] == "LEVEL_CARRIED"]
            for kk in KS:
                h, n = eval_stream(objs, gs, day, "combo", kk,
                                   dedup_objs=dd)
                results[st]["dd"][kk][0] += h
                results[st]["dd"][kk][1] += n

    # ---- report ----
    for st in streams:
        print("\n=== proposer %s ===" % st)
        print("births/panel med %.1f   live@tau med %.1f" % (
            float(np.median(results[st]["births"])),
            float(np.median(results[st]["live"]))))
        for typ, gkey in (("LC", "LEVEL_CARRIED"),
                          ("MINI", "MINI_LEVEL")):
            R = results[st][gkey]
            print(" %s birth caps (all | trusted):" % typ)
            for cc in CAPS:
                h, n = R["cap"][cc]
                h2, n2 = R["captr"][cc]
                p_, lo, hi = wilson(h, n)
                p2, lo2, hi2 = wilson(h2, n2)
                print("   cap=%d  %.3f [%.2f-%.2f] (%d/%d)  |  "
                      "trusted %.3f [%.2f-%.2f] (%d/%d)"
                      % (cc, p_, lo, hi, h, n, p2, lo2, hi2, h2, n2))
            print(" %s recall@k (all | trusted):" % typ)
            for rn in RANKER_NAMES:
                row = []
                for kk in KS:
                    h, n = R["k"][rn][kk]
                    p_, lo, hi = wilson(h, n)
                    h2, n2 = R["ktr"][rn][kk]
                    p2, _, _ = wilson(h2, n2)
                    row.append("k%d %.3f[%.2f-%.2f]|tr %.3f"
                               % (kk, p_, lo, hi, p2))
                print("   %-11s %s" % (rn, "  ".join(row)))
        row = []
        for kk in KS:
            h, n = results[st]["dd"][kk]
            p_, lo, hi = wilson(h, n)
            row.append("k%d %.3f[%.2f-%.2f]" % (kk, p_, lo, hi))
        print("   LC combo+xfamily-dedup: %s" % "  ".join(row))

    # ---- day-level 5-fold CV: choose ranker on 4 folds, score on the
    # held-out fold. Metrics: LC@1, LC@2, MINI@2.
    print("\n=== 5-fold CV (choose ranker on 4 folds) ===")
    for gkey, kk in (("LEVEL_CARRIED", 1), ("LEVEL_CARRIED", 2),
                     ("MINI_LEVEL", 2)):
        tag = "%s@%d" % ("LC" if gkey == "LEVEL_CARRIED" else "MINI", kk)
        for st in streams:
            fr = results[st]["fold_rows"][gkey]
            cv = []
            chosen = []
            for f in range(5):
                train = [i for i in range(5) if i != f]
                def fold_score(rn):
                    h = sum(fr[rn][kk][i][j][0] for i in train
                            for j in range(len(fr[rn][kk][i])))
                    n = sum(fr[rn][kk][i][j][1] for i in train
                            for j in range(len(fr[rn][kk][i])))
                    return h / n if n else 0
                best = max(RANKER_NAMES, key=fold_score)
                h = sum(x[0] for x in fr[best][kk][f])
                n = sum(x[1] for x in fr[best][kk][f])
                cv.append(h / n if n else 0)
                chosen.append(best)
            print(" %s %s: CV = %.3f  (folds: %s; chosen: %s)"
                  % (st, tag, float(np.mean(cv)),
                     " ".join("%.2f" % v for v in cv),
                     ",".join(chosen)))

    if args.save:
        # per-panel meta so fold_rows (h,n) entries can be mapped back
        # to dates: fold_rows[gkey][rn][kk][fi] lists panels of fold fi
        # that had >=1 golden of gkey, in collection order.
        results["_meta"] = {
            "ids": [p["id"] for p in panels],
            "dates": [p["date"] for p in panels],
            "folds": [next(i for i in range(5)
                           if p["date"] in folds[i])
                      for p in panels],
            "n_lc": [sum(1 for g in p["g2"]
                         if g["spec_type"] == "LEVEL_CARRIED")
                     for p in panels],
            "n_mini": [sum(1 for g in p["g2"]
                           if g["spec_type"] == "MINI_LEVEL")
                       for p in panels]}
        with open(args.save, "w", encoding="utf8") as f:
            json.dump(results, f, default=str)
        print("saved", args.save)


if __name__ == "__main__":
    main()
