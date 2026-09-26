"""_regression.py — R10.3 regression analysis: per-golden-object match
status of v0 vs v1 under eval_v2, with v1 miss reasons.

Writes _regression_rows.jsonl + prints aggregate tables.
"""
import collections
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "evalcheck"))
import common as C                    # noqa: E402
import eval as EV                     # noqa: E402
import eval_v2                        # noqa: E402
import pa_slots                       # noqa: E402
import engine as ENG1                 # noqa: E402
import engine_v0 as ENG0              # noqa: E402

PIP = EV.PIP
TYPES = ("BOX", "BRACKET", "LEVEL_CARRIED")


def _fam_letter(s):
    return (s or "").replace("m", "").replace("w", "").replace("i", "")


def run_panel(rec, cls):
    """engine objects + golden + match set for one panel."""
    w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
    t, m, o, h, l, c = EV.day_bars(rec["date"])
    e = EV.run_engine(cls, m, t, o, h, l, c, w1)
    gobjs, _un, _to = EV.gold_objects(rec)
    for g in gobjs:
        if g.get("t0") is None:
            g["t0"] = w0
        if g.get("t1") is None:
            g["t1"] = w1
    g2 = [g for g in gobjs if eval_v2.scorable(g, w0, w1)]
    gmarks = EV.gold_marks(rec)
    gm2 = [gm for gm in gmarks if eval_v2.scorable_mark(gm, w0, w1)]
    eo = eval_v2.eng_objects(e, m, w0, w1)
    em = [r for r in eo if r["type"] == "LABEL_TF"]
    pairs, _mp = C.match_panel(g2, eo, gm2, em, m,
                               eval_v2.match, eval_v2.match_mark,
                               eval_v2.score)
    return e, g2, eo, {gi for gi, _ in pairs}, m


def _row_span_min(row, m):
    t0 = row.get("t0")
    t1 = row.get("t1")
    if t0 is None:
        return None, None
    t0 = m[int(min(max(t0, 0), len(m) - 1))]
    t1 = m[int(min(max(t1 if t1 is not None else t0, 0),
                   len(m) - 1))]
    return int(t0), int(t1)


def right_geom(g, row, m, tol):
    """Does this candidate/object carry golden's geometry?"""
    gt = g["spec_type"]
    if gt == "BOX":
        if g.get("price_lo") is None:
            return True                    # time-only: geometry n/a
        lo = row.get("bottom", row.get("lo"))
        hi = row.get("top", row.get("hi"))
        return lo is not None and hi is not None and \
            abs(lo - g["price_lo"] / PIP) <= tol and \
            abs(hi - g["price_hi"] / PIP) <= tol
    if gt == "LEVEL_CARRIED":
        if g.get("price") is None:
            return True
        p = row.get("price", row.get("level"))
        return p is not None and abs(p - g["price"] / PIP) <= tol
    if gt == "BRACKET":
        if _fam_letter(g.get("letter")) != _fam_letter(row.get("letter")):
            return False
        r0, r1 = _row_span_min(row, m)
        if r0 is None:
            return False
        ov = eval_v2._overlap(r0, r1, g["t0"], g["t1"])
        return ov >= 0.3 * max(g["t1"] - g["t0"], 1)
    return False


def classify(g, e, eo, m, w0, w1):
    """v1 miss reason, per R10.3 taxonomy."""
    gt = g["spec_type"]
    fam = EV.FAMILY.get(gt)
    tol = C.prec_sigmas(g)[0]
    wg0, wg1 = eval_v2._gold_window(g) if gt == "BOX" \
        else (g["t0"], g["t1"])

    # born engine objects of the same family overlapping golden
    born_same = []
    for er in eo:
        if EV.FAMILY.get(er["type"]) != fam:
            continue
        if eval_v2._overlap(er["t0"], er["t1"], g["t0"], g["t1"]) > 0:
            born_same.append(er)
    born_right = [er for er in born_same
                  if right_geom(g, er, m, tol)]

    # candidates of the same family in the funnel log
    rows = [r for r in e.cand_log
            if EV.FAMILY.get(r["kind"]) == fam]
    near = [r for r in rows if right_geom(g, r, m, tol)]

    if born_right:
        # right ink exists but eval said no: span/episode problem
        for er in born_right:
            ok, route = eval_v2.match_detail(g, er, m)
            if ok:
                continue            # matched by a different pairing
            if gt == "BOX":
                we0, we1 = eval_v2._eng_window(er)
                if er["t1"] < wg1 - 10:
                    return "closed_too_early", er, None
                return "born_wrong_episode", er, route
            if er["t1"] < g["t1"] - 10 and er["t0"] <= g["t1"]:
                return "closed_too_early", er, route
            return "born_wrong_span", er, route
        return "born_geom_ok_span_fail", born_right[0], None

    if near:
        outs = collections.Counter(r["outcome"] for r in near)
        if "born" in outs:
            return "born_geom_ok_span_fail", None, dict(outs)
        for o in ("rate_limited", "nms_suppressed", "outranked",
                  "below_min_score", "expired"):
            if outs.get(o):
                return "refused_" + o, None, dict(outs)
        # pre-salience vetoes / dedupe / grave-blocked (never logged):
        vetoes = [o for o in outs
                  if o.startswith("vetoed") or o.startswith("dedup")]
        if vetoes:
            return "refused_" + vetoes[0], None, dict(outs)
        return "refused_other", None, dict(outs)

    if born_same:
        return "born_wrong_edges", born_same[0], None
    # was the family ever proposed at all near golden's span?
    def _ov(r):
        r0, r1 = _row_span_min(r, m)
        if r0 is None:
            return 0.0
        return eval_v2._overlap(r0, r1, g["t0"], g["t1"])
    fam_near = [r for r in rows if _ov(r) > 0]
    if fam_near:
        outs = collections.Counter(r["outcome"] for r in fam_near)
        return "proposed_wrong_geom", None, dict(outs)
    return "never_proposed", None, None


def main():
    recs = C.load_tune()
    out = open("_regression_rows.jsonl", "w", encoding="utf8")
    agg = {t: collections.Counter() for t in TYPES}
    cross = collections.Counter()
    with pa_slots.slot("regression", timeout=300):
        res = {}
        for k, rec in enumerate(recs):
            e1, g2, eo1, m1s, m = run_panel(rec, ENG1.PerceptionEngine)
            e0, _g, eo0, m0s, _m = run_panel(rec, ENG0.PerceptionEngine)
            for gi, g in enumerate(g2):
                gt = g["spec_type"]
                if gt not in TYPES:
                    continue
                v0 = gi in m0s
                v1 = gi in m1s
                cross[(gt, v0, v1)] += 1
                if v1:
                    continue
                reason, er, outs = classify(g, e1, eo1, m,
                                            rec["window"]["x0"],
                                            rec["window"]["x1"] or 1439)
                agg[gt][reason] += 1
                out.write(json.dumps({
                    "panel": rec["id"], "type": gt, "gi": gi,
                    "v0_matched": v0, "reason": reason,
                    "gold": {k2: g.get(k2) for k2 in
                             ("t0", "t1", "price", "price_lo",
                              "price_hi", "letter", "build_start",
                              "build_end", "prec", "status")},
                    "born_obj": {k2: er.get(k2) for k2 in
                                 ("type", "t0", "t1", "lo", "hi",
                                  "price", "letter", "t_birth")}
                    if er else None,
                    "cand_outcomes": outs}) + "\n")
            if (k + 1) % 25 == 0:
                print("  %d/%d" % (k + 1, len(recs)), flush=True)
    out.close()
    print("\n=== match matrix (v0 x v1) ===")
    for t in TYPES:
        print(t, {k[1:]: v for k, v in cross.items() if k[0] == t})
    print("\n=== v1 miss reasons ===")
    for t in TYPES:
        print(t, dict(agg[t].most_common()))


if __name__ == "__main__":
    main()
