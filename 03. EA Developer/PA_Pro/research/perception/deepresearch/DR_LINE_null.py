"""DR_LINE_null.py — null calibration for the reach numbers.

The vE reach (0.68) and level reach (0.81/0.90) mean little without a
null: dense candidate pools match ANYTHING.  Two placebo tests:

  LINES  — cross-panel null: for each golden line, evaluate match
    against the legal-pair space of a DIFFERENT day (same rule set vE).
    If a foreign golden also "reaches" ~0.5, reach is mostly density.
    Also: shifted-golden null — move the golden chord +-20 pips and
    +-60 minutes and re-test (the author's geometry, wrong place).

  LEVELS — price-shift null: for each golden level, test origin
    coverage at price+N*4 pips (N in 1,2,3) and price-N*4 — how far
    away must we go before "some defended origin sits within tol"
    stops being true.

Outputs: printed null table + DR_LINE_null.jsonl.
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

import numpy as np                      # noqa: E402

import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import common as C                     # noqa: E402
import engine as ENG                   # noqa: E402
import DR_LINE_fidelity as F           # noqa: E402
import DR_LINE_relax as R              # noqa: E402

OUT = os.path.join(HERE, "DR_LINE_null.jsonl")
VE = {"over_veto_tol_mult": 1e9, "min_touch_events": 2,
      "_noslope": True}


def main():
    recs = C.load_tune()
    rows = []
    # first pass: collect per-panel candidate space ONCE (engine run
    # to panel w1; evaluate at each golden's own tau)
    panels = []
    for k, rec in enumerate(recs):
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        t, m, o, h, l, c = EV.day_bars(rec["date"])
        e = EV.run_engine(ENG.PerceptionEngine, m, t, o, h, l, c, w1,
                          w0=w0)
        lp, lvp = e.p["line"], e.p["level"]
        gobjs, _u, _to = EV.gold_objects(rec)
        g_lines = [g for g in gobjs
                   if g["spec_type"] in ("PATTERN_LINE", "CONTEXT_LINE")
                   and V2.scorable(g, w0, w1)
                   and (g.get("build_end") or g.get("t1"))]
        g_lvls = [g for g in gobjs
                  if g["spec_type"] in ("LEVEL_CARRIED", "MINI_LEVEL")
                  and g.get("t0") is not None]
        taus = sorted({min(g.get("build_end") or g["t1"], w1)
                       for g in g_lines}
                      | {min(g["t0"] + 10, w1) for g in g_lvls})
        cand_at = {}
        for tau in taus:
            jt = F.j_at(m, tau)
            if jt < 5:
                continue
            lst = []
            for side in (-1, 1):
                for cd in R.cands_variant(e, jt, side, lp, VE):
                    lst.append({"t0": int(m[cd["a"]["t"]]),
                                "t1": int(m[jt]),
                                "t0_raw": int(m[cd["a"]["t"]]),
                                "t1_raw": int(m[jt]),
                                "t_birth": int(m[jt]),
                                "p0": cd["a"]["p"],
                                "slope": cd["slope"],
                                "t0_bar": cd["a"]["t"],
                                "side": "top" if side > 0 else "bottom",
                                "dirn": 0, "w0": 0, "w1": 10**9,
                                "type": "PATTERN_LINE"})
            ogs = F.defended_origins(e, jt, lvp)
            lv = [{"price": og["price"], "dir": og["dir"],
                   "n_def": og["n_def"], "bar": og["bar"]}
                  for og in ogs]
            cand_at[tau] = {"lines": lst, "lv": lv, "jt": jt}
        panels.append({"id": rec["id"], "m": m, "w0": w0, "w1": w1,
                       "g_lines": g_lines, "g_lvls": g_lvls,
                       "cand_at": cand_at})
        if (k + 1) % 40 == 0:
            print("prep %d/%d" % (k + 1, len(recs)), flush=True)

    # ---- line nulls ----
    rng = np.random.RandomState(7)
    n_line = 0
    real_hit = 0
    cross_hit = 0
    shift_p = [0] * 3
    shift_t = [0] * 3
    all_p = [p for p in panels if p["g_lines"]]
    for i, p in enumerate(all_p):
        other = all_p[rng.randint(0, len(all_p))]
        tries = 0
        while other is p and tries < 5:
            other = all_p[rng.randint(0, len(all_p))]
            tries += 1
        for g in p["g_lines"]:
            tau = min(g.get("build_end") or g["t1"], p["w1"])
            if tau not in p["cand_at"]:
                continue
            n_line += 1
            cands = p["cand_at"][tau]["lines"]
            m = p["m"]
            if any(V2.match(g, cd, m) for cd in cands):
                real_hit += 1
            # cross-panel: does a foreign panel's golden match THIS
            # pool?  pick a golden from `other` at its own tau
            og_lines = other["g_lines"]
            if og_lines:
                go = og_lines[rng.randint(0, len(og_lines))]
                if any(V2.match(go, cd, m) for cd in cands):
                    cross_hit += 1
            # price-shifted self: +-20 pips (record price fields are
            # absolute; golden price0/price1 absolute too)
            for s_i, dp in enumerate((20.0, -20.0, 40.0)):
                gs = dict(g)
                for kk in ("price0", "price1"):
                    if gs.get(kk) is not None:
                        gs[kk] = gs[kk] + dp * 1e-4
                if any(V2.match(gs, cd, m) for cd in cands):
                    shift_p[s_i] += 1
            # time-shifted self: +-60 min
            for s_i, dm in enumerate((60.0, -60.0, 120.0)):
                gs = dict(g)
                for kk in ("t0", "t1"):
                    if gs.get(kk) is not None:
                        gs[kk] = gs[kk] + dm
                if any(V2.match(gs, cd, m) for cd in cands):
                    shift_t[s_i] += 1
    print("\n=== LINE nulls (n=%d) ===" % n_line)
    print("real reach %.3f | cross-panel %.3f | "
          "+20p %.3f | -20p %.3f | +40p %.3f | "
          "+60min %.3f | -60min %.3f | +120min %.3f" % (
              real_hit / n_line, cross_hit / n_line,
              *[s / n_line for s in shift_p],
              *[s / n_line for s in shift_t]))
    rows.append({"kind": "line_nulls", "n": n_line,
                 "real": real_hit / n_line,
                 "cross": cross_hit / n_line,
                 "shift_p": [s / n_line for s in shift_p],
                 "shift_t": [s / n_line for s in shift_t]})

    # ---- level nulls ----
    n_lv = 0
    lv_real = 0
    lv_shift = {}
    for p in panels:
        m = p["m"]
        for g in p["g_lvls"]:
            if g.get("price") is None:
                continue
            tau = min(g["t0"] + 10, p["w1"])
            if tau not in p["cand_at"]:
                continue
            jt = p["cand_at"][tau]["jt"]
            ogs = p["cand_at"][tau]["lv"]
            n_lv += 1
            gp = g["price"] / 1e-4         # absolute -> pips
            tol = V2.tol_px(g)
            for sgn in (0, 1, -1, 2, -2, 3, -3):
                px = gp + sgn * 4.0
                ok = any(abs(og["price"] - px) <= tol for og in ogs)
                if sgn == 0:
                    lv_real += bool(ok)
                else:
                    lv_shift[sgn] = lv_shift.get(sgn, 0) + bool(ok)
    print("\n=== LEVEL nulls (n=%d; origin within golden tol) ===" % n_lv)
    print("real %.3f | " % (lv_real / n_lv) +
          " | ".join("%+d:%.3f" % (s, lv_shift[s] / n_lv)
                     for s in sorted(lv_shift)))
    rows.append({"kind": "level_nulls", "n": n_lv,
                 "real": lv_real / n_lv,
                 "shift": {str(s): lv_shift[s] / n_lv
                           for s in sorted(lv_shift)}})
    with open(OUT, "w", encoding="utf8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main()
