"""c1_registry.py -- PLAYBOOK_C2 X.S: old-structure level registry.

Lab prototype: a causal registry of structure levels per panel, fed ONLY
by sources that beat the R49 null:

  PIV  : confirmed pivots (t_conf <= i), each with price.
  CEXT : close extremes of the K6 TRIGGER window -- the congestion run
         the engine itself would detect (envelope < 5.5*ABR, >= 6 bars),
         NOT the golden's buildup window (EVAL-AUDIT circularity fix).
  SESS : rolling 6h session high/low.

Question: for the 38 no-edge BOX goldens (no pooled proposal with both
edges within tol by tau), does the registry hold levels within tol of
BOTH edges by tau?  Reported per source and union, vs a DENSITY-MATCHED
null: the golden shifted vertically by a random offset confined to the
price range traded during its own lookback window (200 draws).

Read-only lab script: bars + golden fixtures + engine pickles for the
book.seq pivot stream (pickles at K6 stable hash carry book).
"""
import sys, os, pickle, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "evalcheck"))
sys.path.insert(0, os.path.join(HERE, ".."))

import common as C                         # noqa: E402
import eval as EV                          # noqa: E402
import eval_v2 as V2                       # noqa: E402
import cache as CA                         # noqa: E402
from snapshot import tau_of                # noqa: E402
import c1_missed as CM                     # noqa: E402

HASH = os.environ.get("CM_HASH", "9acaa206c8d386dc")
VAR = os.environ.get("CM_VAR", "m1_v1")
PIP = C.PIP
RNG = np.random.RandomState(20260922)
DRAWS = 200
SESS_BARS = 360          # ~6h of 1-min bars
CONG_H, CONG_N = 5.5, 6  # K6 trigger params


def cong_runs(e, i_end):
    """K6-qualifying congestion runs ending <= i_end: longest suffix of
    bars whose high-low envelope < 5.5*ABR and length >= 6."""
    runs = []
    n = len(e.bars)
    for i in range(i_end + 1):
        # recompute suffix run ending at i (mirror _cong_run)
        if i >= len(e.abr):
            continue
        abr = max(e.abr[i], 1e-9)
        hi, lo = -1e18, 1e18
        j = i
        while j >= 0:
            b = e.bars[j]
            hi = max(hi, b["h"]); lo = min(lo, b["l"])
            if hi - lo >= CONG_H * abr:
                break
            j -= 1
        runlen = i - j
        if runlen >= CONG_N:
            s = j + 1
            seg = e.bars[s:i + 1]
            runs.append((s, i,
                         max(x["c"] for x in seg),
                         min(x["c"] for x in seg)))
    return runs


def registry_levels(e, m, i):
    """Levels visible at bar i. Returns dict src -> [prices]."""
    lv = {"piv": [], "cext": [], "sess": []}
    book = getattr(e, "book", None)
    if book is not None:
        lv["piv"] = [p.price for p in book.seq
                     if getattr(p, "t_conf", 10 ** 9) <= i]
    for s, e_, chi, clo in cong_runs(e, i):
        if e_ <= i:
            lv["cext"] += [chi, clo]
    lo_i = max(0, i - SESS_BARS)
    seg = e.bars[lo_i:i + 1]
    if seg:
        lv["sess"] = [max(b["h"] for b in seg),
                      min(b["l"] for b in seg)]
    return lv


def covered(lo, hi, levels, tol):
    return (any(abs(lo - p) <= tol for p in levels)
            and any(abs(hi - p) <= tol for p in levels))


def main():
    # ---- the 38 no-edge goldens: no pooled cand matched by tau ----
    rows = []
    for rec in C.load_tune():
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        if CM._pk(rec, w1) is None:
            continue
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        for gi, g in enumerate(g2):
            if g["spec_type"] != "BOX" or g.get("price_lo") is None:
                continue
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            tau = min(tau, w1)
            e_t = CM._pk(rec, tau)
            if e_t is None:
                continue
            tol = V2.tol_px(g)
            mc = [cd for cd in (e_t.cand_log or [])
                  if cd.get("kind") == "BOX"
                  and (cd.get("cet_min") or 0) <= tau
                  and CM.edge_match(cd, g, tol)
                  and CM.span_overlap(cd, g, m, w0, tau)
                  and cd.get("outcome") != "proposed"]
            if mc:
                continue          # had a pooled matching proposal
            rows.append((rec, g, gi, tau, tol, e_t, t, m, o, h, l, c,
                         w0, w1))
    print("no-edge goldens:", len(rows))
    obs = collections.Counter()
    null_share = {s: np.zeros(DRAWS) for s in
                  ("piv", "cext", "sess", "union")}
    per = []
    for rec, g, gi, tau, tol, e_t, t, m, o, h, l, c, w0, w1 in rows:
        bi = int(np.searchsorted(m, tau))
        bi = min(bi, len(e_t.bars) - 1)
        lv = registry_levels(e_t, m, bi)
        glo, ghi = g["price_lo"] / PIP, g["price_hi"] / PIP
        uni = lv["piv"] + lv["cext"] + lv["sess"]
        got = {}
        for src in ("piv", "cext", "sess", "union"):
            levs = uni if src == "union" else lv[src]
            got[src] = covered(glo, ghi, levs, tol)
            obs[src] += got[src]
        # density-matched null: vertical shift inside the lookback's
        # traded range; per-draw share over goldens for p95
        lo_i = max(0, bi - SESS_BARS)
        pr_lo = min(b["l"] for b in e_t.bars[lo_i:bi + 1])
        pr_hi = max(b["h"] for b in e_t.bars[lo_i:bi + 1])
        span = ghi - glo
        rng_room = max(pr_hi - pr_lo - span, 1e-9)
        for d in range(DRAWS):
            nlo = glo + RNG.uniform(-0.5, 0.5) * rng_room
            nhi = nlo + span
            for src in ("piv", "cext", "sess", "union"):
                levs = uni if src == "union" else lv[src]
                if covered(nlo, nhi, levs, tol):
                    null_share[src][d] += 1
        per.append((rec["id"], gi, tau, got))
    n = len(rows)
    print("\nsrc        obs    null-mean  null-p95")
    for src in ("piv", "cext", "sess", "union"):
        dist = null_share[src] / n
        print("%-9s %.3f  %.3f      %.3f"
              % (src, obs[src] / n, dist.mean(),
                 np.percentile(dist, 95)))
    print("\n-- per golden (piv/cext/sess/union) --")
    for pid, gi, tau, got in per:
        print("%-6s g%d t%-4d %s" % (pid, gi, tau,
                                     "".join("1" if got[s] else "0"
                                             for s in ("piv", "cext",
                                                       "sess",
                                                       "union"))))


if __name__ == "__main__":
    main()
