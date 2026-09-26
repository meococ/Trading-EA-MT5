"""DR_LINE_relax.py — which legality constraint binds the golden lines?

For every golden PATTERN_LINE/CONTEXT_LINE on TUNE, enumerate the full
anchor-pool pair space at tau (same pools as DR_LINE_fidelity) under
successively relaxed rule sets:

  v0  current params (slope rule, veto 2x tol, n_ev>=3, span<=96)
  vA  defended veto OFF          (a pierced chord is still a chord)
  vB  touch-event floor n_ev>=2  (two anchors alone may birth a line)
  vC  slope rule OFF             (any sign/steepness)
  vD  vA + vB
  vE  vA + vB + vC
  vF  vE + span cap 144 bars

Reach@variant = share of goldens with >=1 legal pair matching the
golden under eval_v2.  Also reported: n_legal candidates per variant
(the clutter a relaxed rule space creates — the selection cost).

Outputs: deepresearch/DR_LINE_relax.jsonl + printed table.
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

OUT = os.path.join(HERE, "DR_LINE_relax.jsonl")

VARIANTS = {
    "v0_base":      {},
    "vA_noveto":    {"over_veto_tol_mult": 1e9},
    "vB_nev2":      {"min_touch_events": 2},
    "vC_noslope":   {"_noslope": True},
    "vD_A_B":       {"over_veto_tol_mult": 1e9, "min_touch_events": 2},
    "vE_A_B_C":     {"over_veto_tol_mult": 1e9, "min_touch_events": 2,
                     "_noslope": True},
    "vF_wide":      {"over_veto_tol_mult": 1e9, "min_touch_events": 2,
                     "_noslope": True, "span_max_bars": 144},
}


def cands_variant(e, jt, side, lp, var):
    p = dict(lp)
    p.update(var)
    noslope = p.pop("_noslope", False)
    pool = F.anchor_pool(e, jt, side, p)
    abr = max(e.abr[jt], 1e-9)
    tol = max(p["touch_tol_pips"], p["touch_tol_abr_frac"] * abr)
    flat, drift = p["slope_flat_max"], p["flat_drift_pips"]
    dmul = p.get("slope_drift_mult", 1.0)
    span_lo, span_hi = p.get("span_min_bars", 2), p["span_max_bars"]
    omul = p.get("over_veto_tol_mult", 1.0)
    stream = [q for q in e.book.seq
              if q.dir == side and q.t_conf <= jt
              and q.prom_birth >= e.book.floor_min(q)]
    ext = "l" if side < 0 else "h"
    out = []
    for ai in range(len(pool)):
        for bi in range(ai + 1, len(pool)):
            a, b = pool[ai], pool[bi]
            span = b["t"] - a["t"]
            if not (span_lo <= span <= span_hi):
                continue
            slope = (b["p"] - a["p"]) / span
            if p.get("slope_floor", 0.0) and abs(slope) < p["slope_floor"]:
                continue
            if not noslope:
                if side > 0 and slope > 0 and \
                        (slope > flat or slope * span > drift * dmul):
                    continue
                if side < 0 and slope < 0 and \
                        (-slope > flat or -slope * span > drift * dmul):
                    continue
            over = 0.0
            n_pt = 0
            for q in stream:
                if not (a["t"] <= q.t_ext <= jt):
                    continue
                pj = a["p"] + slope * (q.t_ext - a["t"])
                d = (q.price - pj) * side
                if d > over:
                    over = d
                    if over > tol * omul:
                        break
                if abs(q.price - pj) <= tol:
                    n_pt += 1
            n_anch = int(a["kind"] != "piv") + int(b["kind"] != "piv")
            if over > tol * omul or n_pt + n_anch < p["min_touches"]:
                continue
            n_ev = 0
            cur = False
            for j in range(a["t"], jt + 1):
                pj = a["p"] + slope * (j - a["t"])
                wv = abs(e.bars[j][ext] - pj) <= tol
                if wv and not cur:
                    n_ev += 1
                cur = wv
            if n_ev < p.get("min_touch_events", 2):
                continue
            out.append({"a": a, "b": b, "slope": slope, "n_ev": n_ev})
    return out


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
            row = {"panel": rec["id"], "type": g["spec_type"]}
            for vn, var in VARIANTS.items():
                hit = False
                nc = 0
                for side in (-1, 1):
                    cands = cands_variant(e, jt, side, lp, var)
                    nc += len(cands)
                    if not hit:
                        for cd in cands:
                            r = {"type": "PATTERN_LINE",
                                 "t0": int(m[cd["a"]["t"]]),
                                 "t1": int(m[jt]),
                                 "t0_raw": int(m[cd["a"]["t"]]),
                                 "t1_raw": int(m[jt]),
                                 "t_birth": int(m[jt]),
                                 "p0": cd["a"]["p"],
                                 "slope": cd["slope"],
                                 "t0_bar": cd["a"]["t"],
                                 "side": "top" if side > 0
                                         else "bottom",
                                 "dirn": 0, "w0": 0, "w1": 10**9}
                            if V2.match(g, r, m):
                                hit = True
                                break
                row[vn] = hit
                row[vn + "_n"] = nc
            rows.append(row)
        if (k + 1) % 40 == 0:
            print("panel %d/%d" % (k + 1, len(recs)), flush=True)
    with open(OUT, "w", encoding="utf8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    n = len(rows)
    print("\n=== relax table (n=%d golden lines) ===" % n)
    for vn in VARIANTS:
        hits = sum(r[vn] for r in rows)
        nc = [r[vn + "_n"] for r in rows]
        print("%-10s reach %.2f (%d/%d)  med_cands %d" % (
            vn, hits / n, hits, n,
            int(sorted(nc)[n // 2])))


if __name__ == "__main__":
    main()
