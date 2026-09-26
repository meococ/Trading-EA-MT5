"""neg_audit.py — R28 §28.3.2 negatives audit.

Every W1b negative was constructed to be causally wrong.  A negative
is INVALID for the specificity test iff it would match a golden object
on its own panel under the official ruler (eval_v2.match) — then the
judge saying "plausible" is correct, not a false accept.

For each negative: construction method, nearest golden (same family,
max span overlap), ruler match verdict + route, and the judge's call.
Output: _neg_audit.json + printed table.
"""

import collections
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cache as CA            # noqa: E402
import common as C            # noqa: E402
import eval_v2 as V2          # noqa: E402
import eval as EV             # noqa: E402

PIP = C.PIP


def neg_as_engine(it, m, w0, w1):
    """Negative item dict -> engine record (minute/pip space)."""
    k = it["kind"]
    t0, t1 = it.get("t0"), it.get("t1")
    rec = {"type": k, "why": "neg_audit",
           "t0": t0, "t1": t1 if t1 is not None else t0,
           "t0_raw": t0, "t1_raw": t1 if t1 is not None else t0,
           "t_birth": t0, "id": "neg", "events": [],
           "w0": w0, "w1": w1}
    if it.get("lo") is not None:
        rec["lo"], rec["hi"] = it["lo"] / PIP, it["hi"] / PIP
    if it.get("price") is not None:
        rec["price"] = it["price"] / PIP
        rec["side"] = it.get("side")
    if it.get("p0") is not None:
        rec["p0"] = it["p0"] / PIP
        j = int(np.searchsorted(m, t0))
        rec["t0_bar"] = min(j, len(m) - 1)
        if it.get("p1") is not None and t1 and t1 > t0:
            rec["slope"] = (it["p1"] - it["p0"]) / PIP / (t1 - t0)
        else:
            rec["slope"] = 0.0
        rec["side"] = it.get("side")
        rec["dirn"] = 1 if rec["slope"] > 0.05 else \
            (-1 if rec["slope"] < -0.05 else 0)
    if it.get("letter") is not None:
        rec["letter"] = it["letter"]
    return rec


def nearest_golden(er, gobjs):
    """Same-family golden with max span overlap (min |mid-t| gap on
    ties).  Returns (golden, overlap_min, dt_min)."""
    fam = EV.FAMILY.get(er["type"])
    best = None
    for g in gobjs:
        if EV.FAMILY.get(g["spec_type"]) != fam:
            continue
        g0, g1 = V2._span(g)
        e0, e1 = V2._span(er)
        if None in (g0, g1, e0, e1):
            continue
        ov = V2._overlap(e0, e1, g0, g1)
        dt = min(abs(e0 - g1), abs(g0 - e1)) if ov <= 0 else 0
        key = (ov, -dt)
        if best is None or key > best[0]:
            best = (key, g, ov, dt)
    if best is None:
        return None, 0.0, None
    return best[1], best[2], best[3]


def main():
    recs = {r["id"]: r for r in C.load_tune()}
    negs = [json.loads(x) for x in
            open(os.path.join(HERE, "_plaus_neg.jsonl"), encoding="utf8")]
    judged = {}
    for x in (json.loads(l) for l in
              open(os.path.join(HERE, "_plaus_neg_judge.jsonl"),
                   encoding="utf8")):
        judged.setdefault(x["item_id"], x)
    pack_negs = {x["origin_item"] for x in json.load(open(
        os.path.join(HERE, "_owner_judge_key", "_key.json"),
        encoding="utf8")) if x["truth_src"] == "neg"}

    out = []
    for n in negs:
        rec = recs[n["panel"]]
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        _t, m, _o, _h, _l, _c = CA.bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        er = neg_as_engine(n["item"], m, w0, w1)
        ng, ov, dt = nearest_golden(er, g2)
        matches = [(g.get("id"), g["spec_type"],
                    V2.match_detail(g, er, m)[1])
                   for g in g2 if V2.match(g, er, m)]
        j = judged.get(n["item_id"], {})
        out.append({
            "item_id": n["item_id"], "panel": n["panel"],
            "kind": n["item"]["kind"], "how": n["how"],
            "in_pack": n["item_id"] in pack_negs,
            "nearest": (None if ng is None else
                        {"id": ng.get("id"), "type": ng["spec_type"],
                         "ov_min": round(ov, 1), "gap_min": dt}),
            "matches": matches, "valid": not matches,
            "judge": j.get("plausible"),
            "judge_reason": j.get("reason", "")[:110]})

    json.dump(out, open(os.path.join(HERE, "_neg_audit.json"), "w",
                        encoding="utf8"), indent=1)

    print("%-8s %-6s %-9s %-6s pack nearest_golden           match  judge"
          % ("item", "kind", "how", "panel"))
    for r in out:
        ng = r["nearest"]
        ng_s = "-" if ng is None else "%s/%s ov%.0f gap%s" % (
            ng["type"], ng["id"], ng["ov_min"], ng["gap_min"])
        print("%-8s %-6s %-9s %-6s %-4s %-26s %-5s %s" % (
            r["item_id"], r["kind"], r["how"], r["panel"],
            "P" if r["in_pack"] else "", ng_s,
            "MATCH" if r["matches"] else "-", r["judge"]))

    # ---- W1b recompute -------------------------------------------- #
    def spec_ci(rows):
        """specificity = P(judge says implausible | truly negative)."""
        d = [r for r in rows if r["judge"] in ("yes", "no")]
        if not d:
            return 0, 0, (0, 0)
        rej = sum(1 for r in d if r["judge"] == "no")
        p = rej / len(d)
        rng = np.random.RandomState(0)
        bs = [np.mean([rng.choice(d)["judge"] == "no"
                       for _ in d]) for _ in range(4000)]
        return p, len(d), (float(np.quantile(bs, .025)),
                           float(np.quantile(bs, .975)))

    all_rows = out
    val_rows = [r for r in out if r["valid"]]
    sa, na, ca = spec_ci(all_rows)
    sv, nv, cv = spec_ci(val_rows)
    print("\nspecificity all-30:  %d/%d = %.2f  [%.2f-%.2f]"
          % (round(sa * na), na, sa, ca[0], ca[1]))
    print("specificity valid:   %d/%d = %.2f  [%.2f-%.2f]"
          % (round(sv * nv), nv, sv, cv[0], cv[1]))
    print("invalid negatives:  ",
          [r["item_id"] for r in out if not r["valid"]])
    print("pack negs invalid:  ",
          [r["item_id"] for r in out
           if r["in_pack"] and not r["valid"]])


if __name__ == "__main__":
    main()
