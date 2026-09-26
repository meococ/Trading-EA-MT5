"""box_ceiling — mandate 3, Z1: why is the BOX oracle ceiling ~0.31?

For every scorable golden BOX with NO right proposal under the R11
prefix-consistent rule (funnel.cand_right), find the nearest same-family
candidate BY EDGES and record:

  * lo/hi edge errors, in pips and in ABR (at the golden build_end bar);
  * start error:  cand.t0 - golden build_start (fallback t0), minutes;
  * proposal lag: cand proposal time - golden build_end, minutes.

Oracle sensitivity grid (per engine):
  edge tol x {1, 1.5, 2}  x  start window {20, 40, 60, none}  x
  proposal-time limit {on, off} — the fraction of golden BOXes with at
  least one right proposal, split by precision flag and by whether
  build_start is recorded or falls back to t0.

Miss classes (per golden BOX, mutually exclusive, in this order):
  no_candidate          - no same-family candidate in the panel at all
  none_within_2tol      - nearest candidate's worst edge > 2x tol
  edges_ok_start_wrong  - edges pass; |start err| > 20 min
  edges_ok_too_late     - edges+start pass; proposal > build_end + 10
  one_edge_wrong_hi/lo  - exactly one edge off (> tol); name the edge
                          (the breakout edge is hi for an up-break,
                          lo for a down-break, per golden `dir`)
  both_edges_wrong      - both edges off but <= 2x tol

Brief repeats for PATTERN_LINE and LEVEL_CARRIED (same skeleton).

Output: evalcheck/BOX_CEILING.md.  Bars/ABR/engine runs via cache.py.
Usage: python evalcheck/box_ceiling.py [--limit N]
"""

import argparse
import collections
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import funnel as F                              # noqa: E402
import cache as CA                              # noqa: E402
import pa_slots                                 # noqa: E402

PIP = EV.PIP
TS = C.TIME_SIGMA_MIN


def gold_boxes(rec, w0, w1):
    gobjs, _un, _to = EV.gold_objects(rec)
    out = []
    for g in gobjs:
        if g["spec_type"] != "BOX":
            continue
        if g.get("t0") is None:
            g["t0"] = w0
        if g.get("t1") is None:
            g["t1"] = w1
        if V2.scorable(g, w0, w1):
            out.append(g)
    return out


def gold_of_type(rec, w0, w1, types):
    gobjs, _un, _to = EV.gold_objects(rec)
    out = []
    for g in gobjs:
        if g["spec_type"] not in types:
            continue
        if g.get("t0") is None:
            g["t0"] = w0
        if g.get("t1") is None:
            g["t1"] = w1
        if V2.scorable(g, w0, w1):
            out.append(g)
    return out


def panel_cands(e, m, w0, w1):
    out = []
    for cd in e.cand_log or []:
        if cd["kind"] == "LABEL_TF":
            continue
        r = F.cand_as_record(cd, m, w0, w1)
        if r is not None:
            out.append(r)
    return out


def gbs_be(g):
    bs = g.get("build_start")
    if bs is None:
        bs = g.get("t0")
    be = g.get("build_end")
    if be is None:
        be = g.get("t1")
    return bs, be


def edge_errs(g, r):
    """(dlo, dhi) in pips: candidate minus golden edge."""
    return (r["lo"] - g["price_lo"] / PIP,
            r["hi"] - g["price_hi"] / PIP)


def right_p(g, r, tol_mult=1.0, start_win=20.0, prop_lim=True):
    """Parametrised R11 BOX right-proposal test."""
    if EV.FAMILY.get(r["type"]) != "box":
        return False
    if g.get("price_lo") is None or r.get("lo") is None \
            or C.is_time_only(g):
        edges = True
    else:
        tol = V2.tol_px(g) * tol_mult
        dlo, dhi = edge_errs(g, r)
        edges = abs(dlo) <= tol and abs(dhi) <= tol
    if not edges:
        return False
    gbs, gbe = gbs_be(g)
    if gbs is None or gbe is None:
        return False
    if start_win is not None and abs(r["t0"] - gbs) > start_win:
        return False
    if prop_lim and r.get("t_birth") is not None \
            and r["t_birth"] > gbe + TS:
        return False
    return True


def nearest_by_edges(g, cands):
    """Same-family candidates with edges, ranked by worst edge error
    in units of tol.  Returns (record, dlo, dhi, worst_in_tol) or None."""
    tol = V2.tol_px(g)
    if g.get("price_lo") is None or C.is_time_only(g):
        return None
    best = None
    for r in cands:
        if EV.FAMILY.get(r["type"]) != "box" or r.get("lo") is None:
            continue
        dlo, dhi = edge_errs(g, r)
        w = max(abs(dlo), abs(dhi)) / tol
        if best is None or w < best[3]:
            best = (r, dlo, dhi, w)
    return best


def classify_box(g, cands):
    """Miss class for a golden BOX with no right proposal."""
    fam = [r for r in cands if EV.FAMILY.get(r["type"]) == "box"]
    if not fam:
        return "no_candidate", None
    nb = nearest_by_edges(g, fam)
    if nb is None:
        return "no_edge_evidence", None
    r, dlo, dhi, w = nb
    tol = V2.tol_px(g)
    if w > 2.0:
        return "none_within_2tol", nb
    gbs, gbe = gbs_be(g)
    if abs(dlo) <= tol and abs(dhi) <= tol:
        if gbs is not None and abs(r["t0"] - gbs) > 2 * TS:
            return "edges_ok_start_wrong", nb
        if gbe is not None and r.get("t_birth") is not None \
                and r["t_birth"] > gbe + TS:
            return "edges_ok_too_late", nb
        return "edges_ok_other", nb      # passes all but still unborn? —
                                         # covered by cand_right params
    lo_ok, hi_ok = abs(dlo) <= tol, abs(dhi) <= tol
    if lo_ok != hi_ok:
        return ("one_edge_wrong_hi" if not hi_ok
                else "one_edge_wrong_lo"), nb
    return "both_edges_wrong", nb


# ---- brief versions for LINE / LEVEL ---------------------------------

def nearest_line(g, cands, m):
    tol_l = V2.tol_px(g)
    p0g, p1g = g.get("price0"), g.get("price1")
    g0, g1 = g.get("t0"), g.get("t1") or g.get("t0")
    if p0g is not None and p1g is not None and g1 and g1 > g0:
        tol_l += abs((p1g - p0g) / PIP / (g1 - g0)) * TS
    best = None
    for r in cands:
        if EV.FAMILY.get(r["type"]) != EV.FAMILY.get(g["spec_type"]):
            continue
        if r.get("p0") is None or p0g is None:
            continue
        a, b = max(r["t0"], g0), min(r["t1"], g1)
        if a > b:
            res = None
            w = 9e9
        else:
            res = max(abs(V2._eng_line_at(r, a, m)
                          - V2._gold_line_at(g, a)),
                      abs(V2._eng_line_at(r, b, m)
                          - V2._gold_line_at(g, b)))
            w = res / max(tol_l, 1e-9)
        if best is None or w < best[1]:
            best = (r, w, res)
    return best, tol_l


def classify_line(g, cands, m):
    fam = [r for r in cands
           if EV.FAMILY.get(r["type"]) == EV.FAMILY.get(g["spec_type"])]
    if not fam:
        return "no_candidate", None
    nb, tol_l = nearest_line(g, fam, m)
    if nb is None:
        return "no_price_evidence", None
    r, w, res = nb
    gd = {"up": 1, "down": -1}.get(g.get("dir"))
    if gd is not None and r.get("dirn") is not None \
            and gd != r["dirn"] and r["dirn"] != 0:
        return "dir_wrong", (r, w, res)
    if r.get("t_birth") is not None and g.get("t1") is not None \
            and r["t_birth"] > g["t1"]:
        return "too_late", (r, w, res)
    if w > 1.0:
        return ("no_shared_span" if res is None else "geometry_off"), \
            (r, w, res)
    return "passes_but_unclassified", (r, w, res)


def classify_level(g, cands):
    fam = [r for r in cands
           if EV.FAMILY.get(r["type"]) == EV.FAMILY.get(g["spec_type"])]
    if not fam:
        return "no_candidate", None
    tol = V2.tol_px(g)
    g0 = g.get("t0")
    g1 = g.get("t1") if g.get("t1") is not None else g0
    best = None
    for r in fam:
        if r.get("price") is None or g.get("price") is None:
            continue
        w = abs(r["price"] - g["price"] / PIP) / tol
        if best is None or w < best[1]:
            best = (r, w)
    if best is None:
        return "no_price_evidence", None
    r, w = best
    inside = r.get("t_birth") is not None and g0 <= r["t_birth"] <= g1
    if w > 1.0:
        return "price_off", (r, w)
    if not inside:
        return "outside_span", (r, w)
    return "passes_but_unclassified", (r, w)


# ------------------------------------------------------------------ #

def pct(a, q):
    return float(np.percentile(a, q)) if len(a) else float("nan")


def run_diag(tag, cls, recs, eng_hash):
    rows = []          # per-miss diagnostics
    n_right = 0
    n_oracle = 0       # right proposal OR born match (funnel oracle)
    n_gold = 0
    # sensitivity accumulation
    sens = collections.Counter()      # (tm, sw, pl, split_key) -> right
    sens_den = collections.Counter()  # split_key -> n gold
    brief = {"PATTERN_LINE": collections.Counter(),
             "LEVEL_CARRIED": collections.Counter()}
    brief_denom = collections.Counter()
    brief_near = collections.defaultdict(list)

    for rec in recs:
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        _t, m, _o, _h, _l, _c = CA.bars(rec["date"])
        abr = CA.abr(rec["date"])
        e = CA.run(eng_hash, cls, rec)
        cands = panel_cands(e, m, w0, w1)

        # born-side match state (funnel convention) so a golden can be
        # flagged "born-matched but never proposed right".
        gobjs, gmarks, _gk, _gmk = F.gold_with_keys(rec)
        g2i = [i for i, g in enumerate(gobjs)
               if V2.scorable(g, w0, w1)]
        g2 = [gobjs[i] for i in g2i]
        eobjs = V2.eng_objects(e, m, w0, w1)
        eboxes = [r for r in eobjs if r["type"] != "LABEL_TF"]
        gm2 = [gm for gm in gmarks if V2.scorable_mark(gm, w0, w1)]
        emarks = [r for r in eobjs if r["type"] == "LABEL_TF"]
        pairs, _mp = C.match_panel(g2, eboxes, gm2, emarks, m,
                                   V2.match, V2.match_mark, V2.score)
        born_hit = {g2i[gi] for gi, _ in pairs}
        gidx = {id(g): i for i, g in enumerate(gobjs)}

        for g in gold_boxes(rec, w0, w1):
            n_gold += 1
            gbs, gbe = gbs_be(g)
            jbe = int(np.searchsorted(m, gbe)) if gbe is not None \
                else len(m) - 1
            abr_be = float(abr[min(max(jbe, 0), len(abr) - 1)])
            same = [r for r in cands
                    if EV.FAMILY.get(r["type"]) == "box"]
            is_right = any(F.cand_right(g, r, m) for r in same)
            is_born = gidx.get(id(g)) in born_hit
            if is_right:
                n_right += 1
            if is_right or is_born:
                n_oracle += 1
            # sensitivity grid
            split = "%s/%s" % (g.get("prec"),
                               "bs" if g.get("build_start") is not None
                               else "t0fb")
            for tm in (1.0, 1.5, 2.0):
                for sw in (20.0, 40.0, 60.0, None):
                    for pl in (True, False):
                        ok = any(right_p(g, r, tm, sw, pl)
                                 for r in same)
                        sens[(tm, sw, pl, "ALL")] += ok
                        sens[(tm, sw, pl, split)] += ok
            sens_den["ALL"] += 1
            sens_den[split] += 1
            if is_right:
                continue
            cls_, nb = classify_box(g, cands)
            row = {"panel": rec["id"], "prec": g.get("prec"),
                   "bs": g.get("build_start") is not None,
                   "born_matched": gidx.get(id(g)) in born_hit,
                   "class": cls_}
            if nb is not None:
                r, dlo, dhi, w = nb
                row.update({"dlo": round(dlo, 2), "dhi": round(dhi, 2),
                            "dlo_abr": round(dlo / max(abr_be, 1e-9), 2),
                            "dhi_abr": round(dhi / max(abr_be, 1e-9), 2),
                            "worst_tol": round(w, 2),
                            "start_err": (None if gbs is None else
                                          r["t0"] - gbs),
                            "prop_lag": (None if gbe is None or
                                         r.get("t_birth") is None else
                                         r["t_birth"] - gbe)})
            rows.append(row)

        # brief: PATTERN_LINE + LEVEL_CARRIED
        for ty, fn in (("PATTERN_LINE", classify_line),
                       ("LEVEL_CARRIED", classify_level)):
            for g in gold_of_type(rec, w0, w1, (ty,)):
                brief_denom[ty] += 1
                fam = [r for r in cands if EV.FAMILY.get(r["type"])
                       == EV.FAMILY.get(ty)]
                if any(F.cand_right(g, r, m) for r in fam):
                    continue
                if ty == "PATTERN_LINE":
                    cls_, nb = fn(g, cands, m)
                else:
                    cls_, nb = fn(g, cands)
                brief[ty][cls_] += 1
                if nb is not None and cls_ == "geometry_off" \
                        and nb[2] is not None:
                    brief_near[ty].append(nb[2])   # residual pips
                if nb is not None and cls_ == "price_off":
                    r, w = nb
                    brief_near[ty].append(
                        abs(r["price"] - g["price"] / PIP))

    return {"tag": tag, "hash": eng_hash, "n_gold": n_gold,
            "n_right": n_right, "n_oracle": n_oracle, "rows": rows,
            "sens": sens, "sens_den": sens_den, "brief": brief,
            "brief_denom": brief_denom, "brief_near": brief_near}


def _headline(results):
    """Top-line verdict, computed from the sensitivity grid so it
    stays correct across reruns."""
    parts = []
    for res in results:
        tag, rows, n = res["tag"], res["rows"], res["n_gold"]
        # most-relaxed cell = 2.0x tol, start inf, prop-limit off
        relaxed = res["sens"].get((2.0, None, False, "ALL"), 0) / n
        cls = collections.Counter(r["class"] for r in rows)
        none2 = cls.get("none_within_2tol", 0)
        stwrong = cls.get("edges_ok_start_wrong", 0)
        inf1x = res["sens"].get((1.0, None, True, "ALL"), 0) / n
        parts.append((tag, relaxed, none2, len(rows), stwrong, inf1x))
    s = "; ".join(
        "%s: relaxed-cap %.2f, none_within_2tol %d/%d, "
        "edges_ok_start_wrong %d, start-inf@1x %.2f" % p
        for p in parts)
    return ["**HEADLINE: generation, not rule-strictness.**  Even with "
            "every rule maximally relaxed (edge tol x2, no start "
            "window, no proposal-time limit) the oracle caps at "
            + " / ".join("%.2f %s" % (p[1], p[0]) for p in parts)
            + ".  Detail: " + s + ".",
            ""]


def render(results):
    doc = ["# BOX_CEILING — why is the BOX oracle capped at ~0.31?",
           ""]
    doc += _headline(results)
    doc += [
           "Mandate 3 Z1.  Rule under test: R11 §11.2 `cand_right` "
           "(edges within tol + start within 20 min of build_start + "
           "proposal <= build_end + 10 min).  `tol` = object precision "
           "(eye 5p / meas 2p / refined 1.5p).  Engine runs via cache.",
           ""]
    for res in results:
        doc.append("## engine %s (`%s`)" % (res["tag"], res["hash"]))
        doc.append("")
        doc.append("Golden scorable BOXes: %d — right proposal exists "
                   "for %d; funnel-style oracle (right OR born-matched) "
                   "= %d (%.2f); diagnosed misses: %d"
                   % (res["n_gold"], res["n_right"], res["n_oracle"],
                      res["n_oracle"] / res["n_gold"],
                      len(res["rows"])))
        doc.append("")
        # miss classes
        cc = collections.Counter(r["class"] for r in res["rows"])
        nb_ = sum(1 for r in res["rows"] if r.get("born_matched"))
        doc.append("### Miss classes")
        doc.append("")
        for k, v in cc.most_common():
            doc.append("- `%s` = %d" % (k, v))
        doc.append("")
        doc.append("Of these misses, %d were nevertheless matched by a "
                   "born object (born-but-never-proposed-right)." % nb_)
        doc.append("")
        # error distributions on the rows with a nearest candidate
        dlo = [r["dlo"] for r in res["rows"] if "dlo" in r]
        dhi = [r["dhi"] for r in res["rows"] if "dhi" in r]
        dla = [r["dlo_abr"] for r in res["rows"] if "dlo_abr" in r]
        dha = [r["dhi_abr"] for r in res["rows"] if "dhi_abr" in r]
        se = [r["start_err"] for r in res["rows"]
              if r.get("start_err") is not None]
        pl = [r["prop_lag"] for r in res["rows"]
              if r.get("prop_lag") is not None]
        doc.append("### Nearest-candidate error distribution "
                   "(misses only)")
        doc.append("")
        doc.append("| quantity | p10 | p50 | p90 |")
        doc.append("|---|---|---|---|")
        for nm, a in (("lo edge err (p)", dlo), ("hi edge err (p)", dhi),
                      ("lo edge err (ABR)", dla), ("hi edge err (ABR)", dha),
                      ("start err (min)", se), ("proposal lag (min)", pl)):
            doc.append("| %s | %.2f | %.2f | %.2f |"
                       % (nm, pct(a, 10), pct(a, 50), pct(a, 90)))
        doc.append("")
        # absolute versions too
        doc.append("| quantity | p50 | p90 |")
        doc.append("|---|---|---|")
        for nm, a in (("|dlo| p", np.abs(dlo)), ("|dhi| p", np.abs(dhi)),
                      ("|dlo| ABR", np.abs(dla)),
                      ("|dhi| ABR", np.abs(dha)),
                      ("|start err| min", np.abs(se)),
                      ("|prop lag| min", np.abs(pl))):
            doc.append("| %s | %.2f | %.2f |" % (nm, pct(a, 50),
                                                 pct(a, 90)))
        doc.append("")

        # sensitivity table
        doc.append("### Oracle sensitivity (fraction of golden BOXes "
                   "with a right proposal)")
        doc.append("")
        den_all = res["sens_den"]["ALL"]
        doc.append("ALL %d boxes:" % den_all)
        doc.append("")
        doc.append("| edge tol x | start 20 | start 40 | start 60 |"
                   " start inf | (each row: prop-limit on / off) |")
        doc.append("|---|---|---|---|---|---|")
        for tm in (1.0, 1.5, 2.0):
            for pl in (True, False):
                cells = []
                for sw in (20.0, 40.0, 60.0, None):
                    v = res["sens"][(tm, sw, pl, "ALL")]
                    cells.append("%.2f" % (v / den_all))
                doc.append("| %.1fx / %s | %s | %s | %s | %s | |"
                           % (tm, "plim" if pl else "free",
                              cells[0], cells[1], cells[2], cells[3]))
        doc.append("")
        # splits
        for split in sorted(res["sens_den"]):
            if split == "ALL":
                continue
            d = res["sens_den"][split]
            doc.append("split `%s` (n=%d): oracle at tol x1.0/1.5/2.0, "
                       "start 20, plim on = %s"
                       % (split, d, " / ".join(
                           "%.2f" % (res["sens"][(tm, 20.0, True, split)]
                                     / d)
                           for tm in (1.0, 1.5, 2.0))))
        doc.append("")
        # brief line/level
        doc.append("### Brief: PATTERN_LINE / LEVEL_CARRIED misses "
                   "(no right proposal)")
        doc.append("")
        for ty in ("PATTERN_LINE", "LEVEL_CARRIED"):
            d = res["brief_denom"][ty]
            cc = res["brief"][ty]
            near = res["brief_near"].get(ty, [])
            doc.append("- %s: %d golden, %d without right proposal; "
                       "classes: %s%s"
                       % (ty, d, sum(cc.values()),
                          ", ".join("%s=%d" % kv
                                    for kv in cc.most_common()),
                          ("; geom/price residual p50/p90 = %.1f/%.1f p"
                           % (pct(near, 50), pct(near, 90)))
                          if near else ""))
        doc.append("")
    return "\n".join(doc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--v1-hash", default=None,
                    help="pin a cached v1 engine hash (cls=None, "
                         "pickle-only — for mid-integration states "
                         "where the engine cannot instantiate)")
    args = ap.parse_args()

    import engine as ENG_V1
    import engine_v0 as ENG_V0
    recs = C.load_tune()
    if args.limit:
        recs = recs[:args.limit]
    h0 = F.code_hash(F.V0_FILES)
    h1 = args.v1_hash or F.code_hash(F.V1_FILES)

    results = []
    with pa_slots.slot("evalcheck-boxceiling", timeout=600):
        for tag, cls, h in (("v0", ENG_V0.PerceptionEngine, h0),
                            ("v1", None if args.v1_hash
                             else ENG_V1.PerceptionEngine, h1)):
            res = run_diag(tag, cls, recs, h)
            results.append(res)
            print("%s done: %d gold, %d right, %d misses"
                  % (tag, res["n_gold"], res["n_right"],
                     len(res["rows"])), flush=True)

    md = render(results)
    open(os.path.join(HERE, "BOX_CEILING.md"), "w",
         encoding="utf8").write(md)
    # raw rows for later AUC/separator work
    with open(os.path.join(HERE, "_box_ceiling_rows.jsonl"), "w",
              encoding="utf8") as f:
        for res in results:
            for r in res["rows"]:
                f.write(json.dumps({"engine": res["tag"], **r}) + "\n")
    print("wrote BOX_CEILING.md + _box_ceiling_rows.jsonl")


if __name__ == "__main__":
    main()
