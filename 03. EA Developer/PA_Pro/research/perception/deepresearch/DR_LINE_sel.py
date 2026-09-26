"""DR_LINE_sel.py — under the relaxed legal space (vE: no veto,
n_ev>=2, no slope rule), which causal rule ranks the author's line?

Complements DR_LINE_relax.py: reach says the right line is IN the pool
68% of the time; this asks whether any single causal ordering can find
it inside the ~440-candidate clutter, at the author's ~2-object line
budget.

Rules (all causal at tau; ties broken deterministically):
  n_ev        most bar-touch events (defended-most)
  n_ev|young  n_ev, tiebreak freshest second anchor
  n_ev|over   n_ev, tiebreak least overshoot
  lab         n_ev - 0.5*over/tol - 0.5*age_min/60  (engine lab_score)
  young_b     freshest second anchor
  young_a     freshest first anchor
  lastpair    line through the TWO NEWEST same-side anchors only
              (the author's "connect the last two lows" gesture)
  prox        line's price at tau closest to current close
  over        least pivot overshoot
  contains_fresh: prefer pairs whose second anchor IS the freshest
              same-side pivot in the pool, then n_ev
  n_ev_lastp: n_ev but only among pairs whose b-anchor is the freshest
              confirmed pivot ("the line the market just confirmed")

Outputs: DR_LINE_sel.jsonl + printed table.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "golden"))
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, os.path.join(PERC, "..", "..", "lib"))

import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import common as C                     # noqa: E402
import engine as ENG                   # noqa: E402
import DR_LINE_fidelity as F           # noqa: E402
import DR_LINE_relax as R              # noqa: E402

OUT = os.path.join(HERE, "DR_LINE_sel.jsonl")

VE = {"over_veto_tol_mult": 1e9, "min_touch_events": 2,
      "_noslope": True}


def main():
    recs = C.load_tune()
    rows = []
    for k, rec in enumerate(recs):
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        t, m, o, h, l, c = EV.day_bars(rec["date"])
        e = EV.run_engine(ENG.PerceptionEngine, m, t, o, h, l, c, w1,
                          w0=w0)
        lp = e.p["line"]
        gobjs, _u, _to = EV.gold_objects(rec)
        for g in gobjs:
            if g["spec_type"] not in ("PATTERN_LINE", "CONTEXT_LINE"):
                continue
            if not V2.scorable(g, w0, w1):
                continue
            tau = g.get("build_end") or g.get("t1")
            if tau is None:
                continue
            jt = F.j_at(m, min(tau, w1))
            if jt < 5:
                continue
            abr = max(e.abr[jt], 1e-9)
            tol = max(lp["touch_tol_pips"],
                      lp["touch_tol_abr_frac"] * abr)
            px = e.bars[jt]["c"]
            row = {"panel": rec["id"], "type": g["spec_type"]}
            all_c = []
            for side in (-1, 1):
                pool = F.anchor_pool(e, jt, side, dict(lp, **VE))
                cands = R.cands_variant(e, jt, side, lp, VE)
                # attach features needed by rules
                for cd in cands:
                    cd["over"] = 0.0
                    for q in [q for q in e.book.seq
                              if q.dir == side and q.t_conf <= jt
                              and q.prom_birth
                              >= e.book.floor_min(q)]:
                        if not (cd["a"]["t"] <= q.t_ext <= jt):
                            continue
                        pj = cd["a"]["p"] + cd["slope"] * \
                            (q.t_ext - cd["a"]["t"])
                        cd["over"] = max(cd["over"],
                                         (q.price - pj) * side)
                    cd["px_tau"] = cd["a"]["p"] + cd["slope"] * \
                        (jt - cd["a"]["t"])
                    cd["age_min"] = max(0, (jt - cd["a"]["t"]) * 5
                                        - lp["span_max_min"])
                fresh = max((a["t"] for a in pool), default=-1)
                # freshest CONFIRMED pivot t_ext (lastpair semantics)
                conf_t = [a["t"] for a in pool if a["kind"] == "piv"]
                fresh2 = sorted(conf_t)[-2:] if len(conf_t) >= 2 \
                    else conf_t
                def mkrec(cd):
                    return {"type": "PATTERN_LINE",
                            "t0": int(m[cd["a"]["t"]]),
                            "t1": int(m[jt]),
                            "t0_raw": int(m[cd["a"]["t"]]),
                            "t1_raw": int(m[jt]), "t_birth": int(m[jt]),
                            "p0": cd["a"]["p"], "slope": cd["slope"],
                            "t0_bar": cd["a"]["t"],
                            "side": "top" if side > 0 else "bottom",
                            "dirn": 0, "w0": 0, "w1": 10**9}
                rules = {
                    "n_ev": lambda cd: (-cd["n_ev"], -cd["b"]["t"]),
                    "n_ev|young": lambda cd: (-cd["n_ev"],
                                              -cd["b"]["t"]),
                    "n_ev|over": lambda cd: (-cd["n_ev"], cd["over"]),
                    "lab": lambda cd: -(
                        cd["n_ev"] - 0.5 * cd["over"] / tol
                        - 0.5 * cd["age_min"] / 60.0),
                    "young_b": lambda cd: (-cd["b"]["t"], -cd["n_ev"]),
                    "young_a": lambda cd: (-cd["a"]["t"], -cd["n_ev"]),
                    "prox": lambda cd: abs(px - cd["px_tau"]),
                    "over": lambda cd: (cd["over"], -cd["n_ev"]),
                    "fresh_b": lambda cd: (
                        0 if cd["b"]["t"] == fresh else 1,
                        -cd["n_ev"]),
                    "lastpair": lambda cd: (
                        0 if (cd["a"]["t"], cd["b"]["t"])
                        == tuple(fresh2) else 1,
                        -cd["n_ev"]),
                }
                for cd in cands:
                    cd["rec"] = mkrec(cd)
                all_c += cands
            # one ranking over BOTH sides (the author's ~2-line budget
            # is joint, not per-side)
            rules_all = {
                "n_ev": lambda cd: (-cd["n_ev"], -cd["b"]["t"]),
                "n_ev|over": lambda cd: (-cd["n_ev"], cd["over"]),
                "lab": lambda cd: -(
                    cd["n_ev"] - 0.5 * cd["over"] / tol
                    - 0.5 * cd["age_min"] / 60.0),
                "young_b": lambda cd: (-cd["b"]["t"], -cd["n_ev"]),
                "young_a": lambda cd: (-cd["a"]["t"], -cd["n_ev"]),
                "prox": lambda cd: abs(px - cd["px_tau"]),
                "over": lambda cd: (cd["over"], -cd["n_ev"]),
                "ya_ev": lambda cd: (-cd["a"]["t"], -cd["n_ev"],
                                     cd["over"]),
                "ya_prox": lambda cd: (-cd["a"]["t"],
                                       abs(px - cd["px_tau"])),
            }
            for rn, key in rules_all.items():
                order = sorted(all_c, key=key)
                for kk in (1, 2, 3):
                    ok = any(V2.match(g, cd["rec"], m)
                             for cd in order[:kk])
                    row["%s@%d" % (rn, kk)] = ok
            rows.append(row)
        if (k + 1) % 40 == 0:
            print("panel %d/%d" % (k + 1, len(recs)), flush=True)
    with open(OUT, "w", encoding="utf8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    n = len(rows)
    print("\n=== selection under vE space (n=%d lines) ===" % n)
    keys = sorted({k for r in rows for k in r if "@" in k})
    for kk in keys:
        v = sum(r[kk] for r in rows)
        print("%-14s %.2f (%d/%d)" % (kk, v / n, v, n))


if __name__ == "__main__":
    main()
