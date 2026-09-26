"""EVAL-AUDIT verify of R73 L-arm A/Bs (flagged line/level
experiments).  Cache-only, own scorer.  Generic: works for any
variant pair at one hash against the C-3 parent.

Checks (s.73.2 contract):
  1. OFF-identity: OFF arm vs uip2_pbbirth@8361fe85 (canonical-proven
     == tree 2d497427) on all shared runs.
  2. M1 row both arms + paired day-bootstrap CIs vs v0.
  3. Clutter median + margin (panels <= 5.0).
  4. Births per panel per family (cand_log outcome==born).
  5. Median line/level candidates per panel pre-salience (explosion
     watch: cand_log proposals of LINE/LEVEL-ish kinds per panel).
  6. Flipped goldens ON vs OFF for the target family (top-k hit).

Usage:
    python evalcheck/_verify_l_arms.py <H> <OFF_VAR> <ON_VAR> <fam>
    fam in {box, level, line, bracket}   (default line)
"""
import collections
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import recall_at_k as RK                        # noqa: E402
import m1_row as M1                             # noqa: E402
import _verify_keeps_c1 as VK                   # noqa: E402
from snapshot import tau_of, live_records       # noqa: E402

PARENT_H = "8361fe85e73f9437"
PARENT_V = "uip2_pbbirth"
TOPK = {"box": 1, "level": 1, "line": 2, "bracket": 1}


def births_per_family(variant, H, recs):
    """{family: np.array per-panel born counts} from cand_log."""
    out = collections.defaultdict(list)
    for rec in recs:
        w1 = rec["window"]["x1"] or 1439
        f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                         % (variant, H, rec["date"], w1))
        if not os.path.exists(f):
            continue
        e = pickle.load(open(f, "rb"))
        cnt = collections.Counter()
        for cd in e.cand_log or []:
            if cd.get("outcome") == "born":
                cnt[EV.FAMILY.get(cd.get("kind"), "?")] += 1
        for fam in ("box", "level", "line", "bracket"):
            out[fam].append(cnt[fam])
    return {k: np.array(v) for k, v in out.items()}


def cand_medians(variant, H, recs):
    """Median per-panel candidate proposals (any outcome) for line and
    level kinds - the pre-salience explosion watch."""
    per = {"line": [], "level": []}
    for rec in recs:
        w1 = rec["window"]["x1"] or 1439
        f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                         % (variant, H, rec["date"], w1))
        if not os.path.exists(f):
            continue
        e = pickle.load(open(f, "rb"))
        cnt = collections.Counter()
        for cd in e.cand_log or []:
            fam = EV.FAMILY.get(cd.get("kind"))
            if fam in per:
                cnt[fam] += 1
        per["line"].append(cnt["line"])
        per["level"].append(cnt["level"])
    return {k: (np.median(v), float(np.mean(v)), int(np.max(v)), len(v))
            for k, v in per.items()}


def fam_hits_by_golden(variant, H, recs, fam):
    """Set of (panel, spec_type, tau, lo, hi) goldens hit by any of the
    family's top-k live records at the golden's tau."""
    k = TOPK[fam]
    hits = set()
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        _t, m, _o, _h, _l, _c = CA.bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)
              and EV.FAMILY.get(g["spec_type"]) == fam]
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is not None and tau >= w0:
                by_tau[min(tau, w1)].append(g)
        for tau, gs in by_tau.items():
            f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                             % (variant, H, rec["date"], tau))
            if not os.path.exists(f):
                continue
            e = pickle.load(open(f, "rb"))
            live, _x = live_records(e, m, w0, tau)
            osc = {o.id: getattr(o, "score", None) for o in e.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            ranked = RK.rank_live(live, RK.score_map(e))
            top = [r for r in ranked
                   if EV.FAMILY.get(r["type"]) == fam][:k]
            for g in gs:
                if any(V2.match(g, r, m) for r in top):
                    hits.add((rec["id"], g["spec_type"], tau,
                              round(g.get("price_lo") or 0, 1),
                              round(g.get("price_hi") or 0, 1)))
    return hits


def main():
    H = sys.argv[1]
    OFF_VAR = sys.argv[2]
    ON_VAR = sys.argv[3]
    fam = sys.argv[4] if len(sys.argv) > 4 else "line"
    recs = C.load_tune()
    print("hash %s | off=%s on=%s | target family=%s"
          % (H, OFF_VAR, ON_VAR, fam))
    print("== 1. OFF-identity %s@%s vs %s@%s"
          % (OFF_VAR, H[:8], PARENT_V, PARENT_H[:8]))
    n, so, sl, se, miss, diffs = VK.identity(
        H, OFF_VAR, PARENT_H, PARENT_V, recs)
    print("n=%d obj=%d log=%d ev=%d miss=%d" % (n, so, sl, se, miss))
    for d in diffs:
        print("   ", d)

    print("== 2/3. M1 + clutter both arms")
    rng = __import__("random").Random(M1.SEED)
    off = M1.measure(H, OFF_VAR, recs)
    on = M1.measure(H, ON_VAR, recs)
    h0 = __import__("funnel").code_hash(__import__("funnel").V0_FILES)
    v0 = M1.measure(h0, "m1_v0", recs)
    o1 = M1.report("%s (parent)" % OFF_VAR, off, v0=v0, rng=rng)
    o2 = M1.report("%s  (arm)" % ON_VAR, on, v0=v0, rng=rng)
    r_on = np.array(sorted(o2["ratios"]))
    r_off = np.array(sorted(o1["ratios"]))
    print("margin<=5.0: off %d/%d | on %d/%d"
          % ((r_off <= 5.0).sum(), len(r_off),
             (r_on <= 5.0).sum(), len(r_on)))

    print("== 4. births per panel per family (window-end runs)")
    for v in (OFF_VAR, ON_VAR):
        bf = births_per_family(v, H, recs)
        print("  %s:" % v + "".join(
            "  %s med %.2f mean %.2f max %d"
            % (f, np.median(a), a.mean(), a.max())
            for f, a in sorted(bf.items())))

    print("== 5. pre-salience candidate medians (explosion watch)")
    for v in (OFF_VAR, ON_VAR):
        cm = cand_medians(v, H, recs)
        print("  %s: line med %.0f mean %.1f max %d | level med %.0f "
              "mean %.1f max %d (n=%d)"
              % (v, cm["line"][0], cm["line"][1], cm["line"][2],
                 cm["level"][0], cm["level"][1], cm["level"][2],
                 cm["line"][3]))

    print("== 6. flipped %s goldens (top-%d hit ON vs OFF)"
          % (fam, TOPK[fam]))
    ho = fam_hits_by_golden(ON_VAR, H, recs, fam)
    hf = fam_hits_by_golden(OFF_VAR, H, recs, fam)
    gained = sorted(ho - hf)
    lost = sorted(hf - ho)
    print("  gained %d: %s" % (len(gained), gained))
    print("  lost   %d: %s" % (len(lost), lost))


if __name__ == "__main__":
    main()
