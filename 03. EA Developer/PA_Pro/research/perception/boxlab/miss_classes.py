"""miss_classes — X2 engine comparison: nearest v0/v1 candidate per
golden BOX, edge/start/timing errors, and the generation miss taxonomy.

Uses the boxlab-cached engine runs (engine_runs.py) and the funnel's
own cand_right() / cand_as_record() conversions — identical semantics to
FUNNEL.md.  Output: cache/miss_classes.json + console tables.
"""
import collections
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
_EVALC = os.path.join(_PERC, "evalcheck")
for _p in (_HERE, _PERC, _EVALC, os.path.join(_PERC, "golden")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bars_cache as BC            # noqa: E402
import common as C                 # noqa: E402
import eval_v2 as V2               # noqa: E402
import eval as EV                  # noqa: E402
import funnel as FN                # noqa: E402
import engine_runs as ER           # noqa: E402

TUNE_JSONL = os.path.join(_PERC, "golden", "draft", "BOOK2012_TUNE_v2.jsonl")
OUT = os.path.join(_HERE, "cache", "miss_classes.json")
TS = C.TIME_SIGMA_MIN                      # 10 min
START_RULE = 2 * TS                        # cand_right start rule: 20 min


def _ovc(a0, a1, b0, b1):
    inter = max(0.0, min(a1, b1) - max(a0, b0))
    shorter = max(min(a1 - a0, b1 - b0), 1.0)
    return inter / shorter


def panel_rows(rec, tag):
    """Per golden BOX: nearest candidate diagnostics + miss class."""
    w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
    e = ER.run_cached(tag, _cls(tag), rec)
    t, m, o, h, l, c = EV.day_bars(rec["date"])

    gobjs, _un, _to = EV.gold_objects(rec)
    cands = []
    for k, cd in enumerate(e.cand_log or []):
        if cd.get("kind") == "LABEL_TF":
            continue
        r = FN.cand_as_record(cd, m, w0, w1)
        if r is not None and EV.FAMILY.get(r["type"]) == "box":
            r["cand_seq"] = k
            cands.append(r)
    eobjs = V2.eng_objects(e, m, w0, w1)
    ebox = [r for r in eobjs if EV.FAMILY.get(r["type"]) == "box"]

    rows = []
    for i, g in enumerate(gobjs):
        if g["spec_type"] != "BOX" or not V2.scorable(g, w0, w1):
            continue
        glo = g.get("price_lo"); ghi = g.get("price_hi")
        if glo is None or ghi is None:
            continue
        glo_p, ghi_p = glo * 1e4, ghi * 1e4
        gbs = g.get("build_start") or g.get("t0")
        gbe = g.get("build_end") or g.get("t1")
        tol = V2.tol_px(g)

        rights, near = [], []
        for r in cands:
            rc = FN.cand_right(g, r, m)
            oc = _ovc(r["t0"], r["t1"], gbs, gbe)
            lo_err = (r["lo"] - glo_p) if r.get("lo") is not None else None
            hi_err = (r["hi"] - ghi_p) if r.get("hi") is not None else None
            diag = {"r": r, "right": rc, "ovc": oc,
                    "lo_err": lo_err, "hi_err": hi_err,
                    "start_err": (r["t0"] - gbs) if gbs is not None else None,
                    "birth_minus_be": (r["t_birth"] - gbe)
                    if gbe is not None else None}
            if rc:
                rights.append(diag)
            if oc >= 0.3 or (
                    lo_err is not None
                    and abs(lo_err) <= 8 and abs(hi_err) <= 8
                    and max(0.0, min(r["t1"], gbe) - max(r["t0"], gbs)) > 0):
                near.append(diag)

        # born side
        born_pairs = []
        for er in ebox:
            ok, route = V2.match_detail(g, er, m)
            born_pairs.append((er, ok, route))
        born_hit = any(ok for _e2, ok, _rt in born_pairs)

        # nearest vicinity candidate (max overlap coef)
        nearest = max(near, key=lambda d: d["ovc"]) if near else None

        if born_hit:
            cat = "matched"
        elif rights:
            born_right = [d for d in rights if d["r"].get("outcome") == "born"]
            if born_right:
                cat = "right_born_lost_assignment"; why = ""
            else:
                cat = "right_filtered"
                why = "|".join(sorted({str(d["r"].get("outcome"))
                                       for d in rights}))
        elif nearest is None:
            cat = "never_near"; why = ""
        elif all(d["birth_minus_be"] is not None
                 and d["birth_minus_be"] > TS for d in near):
            cat = "too_late"; why = ""
        else:
            intime = [d for d in near
                      if d["birth_minus_be"] is not None
                      and d["birth_minus_be"] <= TS]
            best = max(intime, key=lambda d: d["ovc"]) if intime else nearest
            eok = (best["lo_err"] is not None
                   and abs(best["lo_err"]) <= tol
                   and abs(best["hi_err"]) <= tol)
            if eok and abs(best["start_err"]) > START_RULE:
                cat = "right_edges_wrong_start"; why = ""
            elif not eok:
                lo_e, hi_e = best["lo_err"], best["hi_err"]
                if lo_e is None:
                    cat = "wrong_edges"; why = "no_edges"
                elif lo_e > tol and hi_e < -tol:
                    cat, why = "wrong_edges", "narrower_band"
                elif lo_e < -tol and hi_e > tol:
                    cat, why = "wrong_edges", "wider_band"
                elif abs(lo_e) > tol and abs(hi_e) > tol \
                        and (lo_e > 0) == (hi_e > 0):
                    cat, why = "wrong_edges", "shifted_band"
                else:
                    cat, why = "wrong_edges", "one_edge"
            else:
                cat = "other"; why = "start_ok_edges_ok_not_right?"
        rows.append({"panel": rec["id"], "g_idx": i, "engine": tag,
                     "cat": cat, "why": why if cat != "matched" else "",
                     "n_cands": len(cands), "n_right": len(rights),
                     "n_born_box": len(ebox),
                     "gbs": gbs, "gbe": gbe, "tol": tol,
                     "nearest": None if nearest is None else {
                         "t0": nearest["r"]["t0"], "t1": nearest["r"]["t1"],
                         "t_birth": nearest["r"]["t_birth"],
                         "lo": nearest["r"].get("lo"),
                         "hi": nearest["r"].get("hi"),
                         "lo_err": nearest["lo_err"],
                         "hi_err": nearest["hi_err"],
                         "start_err": nearest["start_err"],
                         "birth_minus_be": nearest["birth_minus_be"],
                         "ovc": round(nearest["ovc"], 3),
                         "route": nearest["r"].get("why"),
                         "outcome": nearest["r"].get("outcome")}})
    return rows


_CLS = {}


def _cls(tag):
    if tag not in _CLS:
        if tag == "v0":
            import engine_v0 as E
        else:
            import engine as E
        _CLS[tag] = E.PerceptionEngine
    return _CLS[tag]


def main():
    recs = C.load_tune()
    all_rows = []
    for tag in ("v0", "v1"):
        for rec in recs:
            all_rows.extend(panel_rows(rec, tag))
    with open(OUT, "w", encoding="utf8") as f:
        json.dump(all_rows, f, indent=1)

    for tag in ("v0", "v1"):
        rs = [r for r in all_rows if r["engine"] == tag]
        ct = collections.Counter(r["cat"] for r in rs)
        print(f"\n== {tag} miss classes (n={len(rs)}) ==")
        for k, v in ct.most_common():
            print(f"  {k}: {v}")
        why = collections.Counter(r["why"] for r in rs if r["why"])
        if why:
            print("  why:", dict(why.most_common(12)))
        ne = [r["nearest"] for r in rs if r["nearest"]]
        for fld in ("lo_err", "hi_err", "start_err", "birth_minus_be"):
            v = np.array([abs(x[fld]) for x in ne if x[fld] is not None])
            if len(v):
                print(f"  |{fld}| med={np.median(v):.1f} "
                      f"p90={np.percentile(v, 90):.1f} n={len(v)}")
        routes = collections.Counter(x["route"] for x in ne)
        print("  nearest routes:", dict(routes.most_common(10)))


if __name__ == "__main__":
    main()
