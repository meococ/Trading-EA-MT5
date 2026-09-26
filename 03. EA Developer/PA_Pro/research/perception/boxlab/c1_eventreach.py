"""c1_eventreach.py — R61 §61.4 queue item 2: for the 15 event-route
goldens v0 hits, does the ported rule (v0's two box routes replayed on
v1's SwingBook pivot stream) reach the golden's edges before tau?

Offline, cache-only, no fitting:
  1. find v0-hit BOX goldens whose v0 top-1 was an event route
     (pullback_end / range_double_*)  — the 15;
  2. load the v1 pivot stream from the lvb_off @29de0689 pickle at tau
     (book.seq is causal: contains every pivot confirmed <= tau);
  3. replay v0's _box_birth route enumeration verbatim (t_ext axis,
     window 84, min_sep 4, dtol 2.0p, pullback sep 3; route (b) first,
     (a) shadowed; envelope gate 6-34p noted but reach counts raw
     route output);
  4. reach = emitted cand whose both edges sit within tol_px(golden)
     of the golden's edges, with t_conf <= tau.
"""
import glob
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)

import common as C                      # noqa: E402
import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import cache as CA                     # noqa: E402
import funnel as F                     # noqa: E402
import recall_at_k as RK               # noqa: E402
from snapshot import tau_of, live_records  # noqa: E402

V0H = F.code_hash(F.V0_FILES)
V1H = "29de0689984fe342"
V1V = "lvb_off"

WIN = 84
MIN_SEP = 4
DTOL = 2.0
PB_SEP = 3
HMIN, HMAX = 6.0, 34.0


def _pkl(variant, h8, date, tau):
    f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                     % (variant, h8, date, tau))
    if os.path.exists(f):
        return f
    g = glob.glob(os.path.join(
        CA.CACHE, "run_%s_%s*_%s_%s.pkl" % (variant, h8, date, tau)))
    return g[0] if g else None


def _load(variant, h, date, tau):
    f = _pkl(variant, h, date, tau)
    return pickle.load(open(f, "rb")) if f else None


def v0_hit(g, e0, m, w0, tau):
    """v0's top-1 box at tau matches the golden and rides an event route."""
    live, _em = live_records(e0, m, w0, tau)
    osc = {o.id: getattr(o, "score", None) for o in e0.objects}
    for r in live:
        r["score"] = osc.get(r["id"])
    ranked = RK.rank_live(live, RK.score_map(e0))
    boxes = [r for r in ranked if EV.FAMILY.get(r["type"]) == "box"]
    if not boxes or not V2.match(g, boxes[0], m):
        return None
    why = str(boxes[0].get("why") or "")
    if why.startswith("pullback_end") or why.startswith("range_double"):
        return why
    return None


def replay_routes(pivs, bars_l, bars_h):
    """v0 _box_birth route enumeration on the v1 pivot stream.
    pivs: list of Pivot sorted by t_conf.  Returns list of cand dicts.
    e = piv.t_ext axis (v0 passes the extreme bar as idx)."""
    cands = []
    confirmed = []          # (t_ext, price, dir) in confirm order
    for p in pivs:
        e, price, side, tc = p.t_ext, p.price, p.dir, p.t_conf
        same = [s for s in confirmed
                if s[2] == side and e - s[0] <= WIN]
        opp = [s for s in confirmed
               if s[2] == -side and e - s[0] <= WIN]
        route_cands = []
        # (b) range_double first
        for prev in reversed(same):
            if e - prev[0] < MIN_SEP:
                continue
            if abs(prev[1] - price) <= DTOL:
                lo_i = min(prev[0], e)
                seg_l = bars_l[max(0, lo_i - 2):e + 1]
                seg_h = bars_h[max(0, lo_i - 2):e + 1]
                if side > 0:
                    top, bot = max(prev[1], price), min(seg_l)
                else:
                    bot, top = min(prev[1], price), max(seg_h)
                route_cands.append(
                    dict(route="range_double_" +
                         ("top" if side > 0 else "bottom"),
                         lo=bot, hi=top, t0=prev[0], born=tc))
                break
        # (a) pullback_end
        if opp:
            last_opp = opp[-1]
            L, H = (price, last_opp[1]) if side < 0 \
                else (last_opp[1], price)
            t0a = min(e, last_opp[0])
            if e - t0a >= PB_SEP:
                route_cands.append(
                    dict(route="pullback_end", lo=L, hi=H,
                         t0=t0a, born=tc))
        if route_cands:
            cands.append(route_cands[0])
            for c in route_cands[1:]:
                cands.append(dict(c, shadowed=True))
        confirmed.append((e, price, side))
    return cands


def main():
    recs = C.load_tune()
    n_v0hit = n_reach = n_reach_env = 0
    detail = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        for g in g2:
            if g["spec_type"] != "BOX":
                continue
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            tau = min(tau, w1)
            e0 = _load("m1_v0", V0H, rec["date"], tau)
            if e0 is None:
                continue
            why = v0_hit(g, e0, m, w0, tau)
            if why is None:
                continue
            n_v0hit += 1
            e1 = _load(V1V, V1H, rec["date"], tau)
            if e1 is None:
                detail.append((rec["id"], tau, why, "NO V1 PKL"))
                continue
            pivs = sorted(
                [p for p in e1.book.seq if p.t_conf <= tau],
                key=lambda p: (p.t_conf, p.t_ext))
            cands = replay_routes(pivs, l, h)
            tol = V2.tol_px(g)
            glo, ghi = g["price_lo"] * 1e4, g["price_hi"] * 1e4
            hits = [cd for cd in cands if not cd.get("shadowed")
                    and abs(cd["hi"] - ghi) <= tol
                    and abs(cd["lo"] - glo) <= tol]
            hits_env = [cd for cd in hits
                        if HMIN <= cd["hi"] - cd["lo"] <= HMAX]
            if hits:
                n_reach += 1
            if hits_env:
                n_reach_env += 1
            detail.append((rec["id"], tau, why,
                           "%d cands, edge-reach=%d, +env=%d"
                           % (len(cands), len(hits), len(hits_env)),
                           hits[:1] and
                           "%s [%.1f-%.1f] t0=%d born=%d"
                           % (hits[0]["route"], hits[0]["lo"],
                              hits[0]["hi"], hits[0]["t0"],
                              hits[0]["born"]) or "-"))
    print("v0 event-route box@1 hits found:", n_v0hit)
    print("ported rule reaches golden edges before tau:", n_reach)
    print("  of which inside the 6-34p envelope gate:", n_reach_env)
    for d in detail:
        print("  %-7s tau=%-5d %-18s %-30s %s" % d)


if __name__ == "__main__":
    main()
