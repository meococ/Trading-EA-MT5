"""DR_LINE_fidelity.py — E3a: which causal principle reproduces the
author's line/level picks on TUNE?

Read-only.  For every usable golden PATTERN_LINE / LEVEL_CARRIED /
MINI_LEVEL in BOOK2012_TUNE_v2 we:

  1. rebuild the anchor pool the engine would have had at the golden's
     decision time tau (snapshot.py semantics: lines use build_end else
     t1; levels use t0 + 10min);
  2. enumerate EVERY legal same-side anchor pair (mirroring lines.py's
     slope rule / defended veto / touch floors — the stream ceiling, not
     the tuned subset) and EVERY defended origin (levels.py defended_
     origin registry replayed causally);
  3. ask (a) is the golden REACHABLE — does any legal candidate match it
     under eval_v2; (b) which single-feature or short-composite causal
     rule ranks the matching candidate top-1 / top-2 — the DR-BOX "rule
     table" for lines and levels;
  4. funnel: reachable -> proposed by engine (cand_log) -> born
     (e.objects) -> matched at tau.

The ruler (evalcheck/eval_v2.py) is imported, never copied.

Outputs: deepresearch/DR_LINE_fidelity.jsonl + printed table.
"""
import collections
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

PIP = EV.PIP
OUT = os.path.join(HERE, "DR_LINE_fidelity.jsonl")


# ------------------------------------------------------------------ #
# causal anchor pools at bar j_tau (mirrors lines.py semantics) ------ #
# ------------------------------------------------------------------ #

def loc_ext(bars, j, side, k, sess_w):
    """lines.py _is_loc_ext ported: bar j's defended-side wick is the
    +-k extremum (confirmable once j+k <= now) OR the trailing sess_w
    extremum ending at j."""
    n = len(bars)
    ext = "l" if side < 0 else "h"
    px = bars[j][ext]
    lo = max(0, j - k)
    hi = min(j + k + 1, n)
    win = [bars[q][ext] for q in range(lo, hi)]
    if (px <= min(win)) if side < 0 else (px >= max(win)):
        return True
    if sess_w:
        win = [bars[q][ext] for q in range(max(0, j - sess_w), j + 1)]
        return (px <= min(win)) if side < 0 else px >= max(win)
    return False


def anchor_pool(e, j_tau, side, lp):
    """All anchor candidates the line route could use at bar j_tau:
    confirmed same-side alive pivots + named-bar local extremes +
    terminal leg extreme + session extreme (mirrors LineBook._pool)."""
    n = len(e.bars)
    lookback = lp["span_max_bars"]
    k = lp["loc_ext_bars"]
    seen = set()
    pool = []
    for p in e.book.seq:
        if p.dir != side or p.t_conf > j_tau or p.lone_spike:
            continue
        if p.prom_birth < e.book.floor_min(p):
            continue                      # alive() membership
        if p.t_ext < j_tau - lookback:
            continue
        if p.t_ext in seen:
            continue
        seen.add(p.t_ext)
        pool.append({"t": p.t_ext, "p": p.price, "kind": "piv",
                     "conf": p.t_conf})
    ext = "l" if side < 0 else "h"
    for j in range(max(0, j_tau - lookback), min(j_tau - k + 1, n - k)):
        if j in seen:
            continue
        if loc_ext(e.bars, j, side, k, lp.get("loc_sess_bars", 0)):
            pool.append({"t": j, "p": e.bars[j][ext], "kind": "loc",
                         "conf": j + k})
            seen.add(j)
    # terminal leg extreme: running extreme since last confirmed pivot
    seq = [p for p in e.book.seq if p.t_conf <= j_tau]
    j0 = seq[-1].t_conf if seq else 0
    seg = e.bars[j0:j_tau + 1]
    if seg:
        vals = [b[ext] for b in seg]
        jj = int(np.argmin(vals) if side < 0 else np.argmax(vals))
        jt = j0 + jj
        if jt not in seen and jt < j_tau and \
                j_tau - jt <= lp.get("term_lookback_bars", 0):
            pool.append({"t": jt, "p": vals[jj], "kind": "term",
                         "conf": jt + 1})
            seen.add(jt)
    # session extreme: running extreme since the most recent bar where
    # cet_min crossed a session boundary (480=EU open, 840=US open)
    jstart = 0
    for q in range(j_tau, -1, -1):
        c_q = e.bars[q]["cet_min"]
        c_prev = e.bars[q - 1]["cet_min"] if q else -1
        if (c_prev < 480 <= c_q) or (c_prev < 840 <= c_q):
            jstart = q
            break
    seg = e.bars[jstart:j_tau + 1]
    if seg:
        vals = [b[ext] for b in seg]
        jj = int(np.argmin(vals) if side < 0 else np.argmax(vals))
        jt = jstart + jj
        if jt not in seen and jt < j_tau:
            pool.append({"t": jt, "p": vals[jj], "kind": "sess",
                         "conf": jt + 1})
            seen.add(jt)
    pool.sort(key=lambda a: a["t"])
    return pool


def line_cands(e, j_tau, side, lp):
    """Every legal pair (a,b) from the pool: span/slope/defended/touch
    floors as lines.py._scan; returns candidate dicts with features."""
    pool = anchor_pool(e, j_tau, side, lp)
    abr = max(e.abr[j_tau], 1e-9)
    tol = max(lp["touch_tol_pips"], lp["touch_tol_abr_frac"] * abr)
    flat = lp["slope_flat_max"]
    drift = lp["flat_drift_pips"]
    dmul = lp.get("slope_drift_mult", 1.0)
    span_lo, span_hi = lp.get("span_min_bars", 2), lp["span_max_bars"]
    omul = lp.get("over_veto_tol_mult", 1.0)
    # confirmed same-side pivot stream for the overshoot veto
    stream = [p for p in e.book.seq
              if p.dir == side and p.t_conf <= j_tau
              and p.prom_birth >= e.book.floor_min(p)]
    ext = "l" if side < 0 else "h"
    out = []
    for ai in range(len(pool)):
        for bi in range(ai + 1, len(pool)):
            a, b = pool[ai], pool[bi]
            span = b["t"] - a["t"]
            if not (span_lo <= span <= span_hi):
                continue
            slope = (b["p"] - a["p"]) / span
            sf = lp.get("slope_floor", 0.0)
            if sf and abs(slope) < sf:
                continue
            if side > 0 and slope > 0 and \
                    (slope > flat or slope * span > drift * dmul):
                continue
            if side < 0 and slope < 0 and \
                    (-slope > flat or -slope * span > drift * dmul):
                continue
            over = 0.0
            n_pt = 0
            for q in stream:
                if not (a["t"] <= q.t_ext <= j_tau):
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
            if over > tol * omul or \
                    n_pt + n_anch < lp["min_touches"]:
                continue
            nt = n_ev = 0
            cur = False
            for j in range(a["t"], j_tau + 1):
                pj = a["p"] + slope * (j - a["t"])
                wv = abs(e.bars[j][ext] - pj) <= tol
                if wv:
                    nt += 1
                    if not cur:
                        n_ev += 1
                cur = wv
            if n_ev < lp.get("min_touch_events", 2):
                continue
            out.append({"a": a, "b": b, "slope": slope, "nt": nt,
                        "n_ev": n_ev, "n_pt": n_pt + n_anch,
                        "over": over, "span": span,
                        "t0": a["t"], "t1": b["t"]})
    return out


def cand_record(c, j_tau, side, m):
    """Candidate -> eval_v2-compatible engine record."""
    return {"type": "PATTERN_LINE",
            "t0": int(m[c["t0"]]), "t1": int(m[j_tau]),
            "t0_raw": int(m[c["t0"]]), "t1_raw": int(m[j_tau]),
            "t_birth": int(m[j_tau]), "p0": c["a"]["p"],
            "slope": c["slope"], "t0_bar": c["t0"],
            "side": "top" if side > 0 else "bottom",
            "dirn": 1 if c["slope"] > 0.05 else
                    (-1 if c["slope"] < -0.05 else 0),
            "w0": 0, "w1": 10**9}


# ------------------------------------------------------------------ #
# defended origins at j_tau (levels.py defended_origin replay) ------- #
# ------------------------------------------------------------------ #

def defended_origins(e, j_tau, lp):
    """Replay levels.py's defended-origin registry over bars <= j_tau.

    origins: confirmed pivots (theta1/theta2 by floor) + running
    session/Asia extremes; merges same-side within tol keeping the
    defended EDGE price; n_def = deduped bar-extreme touch events."""
    tol_min = lp["def_touch_tol_pips"]
    frac = lp["def_touch_tol_abr_frac"]
    asia_end = lp["def_asia_end_min"]
    origins = []
    run = {1: None, -1: None}

    def tol(j):
        return max(tol_min, frac * max(e.abr[j], 1e-9))

    def add(j, price, side, cls, sess=False):
        t = tol(j)
        for og in origins:
            if og["dir"] != side:
                continue
            if abs(og["price"] - price) <= t:
                og["price"] = min(og["price"], price) if side < 0 \
                    else max(og["price"], price)
                og["n_piv"] += 1
                return
        origins.append({"bar": j, "price": price, "dir": side,
                        "cls": cls, "n_def": 0, "n_piv": 1,
                        "last_t": j, "sess": sess})

    for j in range(j_tau + 1):
        b = e.bars[j]
        # session/Asia running extremes (levels.session_update flag path)
        if b["h"] > (run[1]["price"] if run[1] else -1e18):
            add(j, b["h"], 1, "asia" if b["cet_min"] < asia_end
                else "session", sess=True)
            run[1] = {"bar": j, "price": b["h"]}
        if b["l"] < (run[-1]["price"] if run[-1] else 1e18):
            add(j, b["l"], -1, "asia" if b["cet_min"] < asia_end
                else "session", sess=True)
            run[-1] = {"bar": j, "price": b["l"]}
        # confirmed pivots emitted at this bar
        for p in e.book.seq:
            if p.t_conf == j:
                add(p.t_ext, p.price, p.dir,
                    "theta2" if e.book.is_structural(p) else "theta1")
        # defence sweep (dedupe consecutive in-tol bars)
        for og in origins:
            ext = b["l"] if og["dir"] < 0 else b["h"]
            hit = abs(ext - og["price"]) <= tol(j)
            if hit and not og.get("_run"):
                og["n_def"] += 1
                og["last_t"] = j
            og["_run"] = hit
    for og in origins:
        og.pop("_run", None)
    return origins


def level_record(price, side, t0m, t1m):
    return {"type": "LEVEL_CARRIED", "price": price, "side": side,
            "t0": t0m, "t1": t1m, "t0_raw": t0m, "t1_raw": t1m,
            "t_birth": t0m, "w0": 0, "w1": 10**9}


# ------------------------------------------------------------------ #
# per-panel driver --------------------------------------------------- #
# ------------------------------------------------------------------ #

def j_at(m, tau):
    return min(int(np.searchsorted(m, tau, "right")) - 1, len(m) - 1)


def side_of_line(g):
    """Golden line's defended side from raw_note or direction: the
    author's convention — a rising line under lows defends below."""
    note = (g.get("raw_note") or "").lower()
    if "under the lows" in note or "under lows" in note or \
            "along the lows" in note or "across the lows" in note or \
            "neckline" in note and "rising" in note:
        return -1
    if "across the highs" in note or "over the highs" in note or \
            "over highs" in note:
        return 1
    return None


def main():
    recs = C.load_tune()
    rows = []
    n_pan = 0
    for rec in recs:
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        t, m, o, h, l, c = EV.day_bars(rec["date"])
        e = EV.run_engine(ENG.PerceptionEngine, m, t, o, h, l, c, w1,
                          w0=w0)
        eobjs = V2.eng_objects(e, m, w0, w1)
        lp = e.p["line"]
        lvp = e.p["level"]
        gobjs, _u, _to = EV.gold_objects(rec)
        n_pan += 1
        for g in gobjs:
            st = g["spec_type"]
            if not V2.scorable(g, w0, w1):
                continue
            if st in ("PATTERN_LINE", "CONTEXT_LINE"):
                tau = g.get("build_end") or g.get("t1")
                if tau is None:
                    continue
                jt = j_at(m, min(tau, w1))
                if jt < 5:
                    continue
                # golden side: direction of slope + anchor location
                p0g, p1g = g.get("price0"), g.get("price1")
                gslope = None
                if p0g is not None and p1g is not None and \
                        g.get("t1") and g.get("t0") and \
                        g["t1"] > g["t0"]:
                    gslope = (p1g - p0g) / PIP / (g["t1"] - g["t0"])
                sides = []
                sd = side_of_line(g)
                if sd:
                    sides = [sd]
                else:
                    # infer from where price sat relative to the line:
                    # a defended line stays on its defended side
                    for s_ in (-1, 1):
                        sides.append(s_)
                best = {"side": None}
                per_side = []
                for side in sides:
                    cands = line_cands(e, jt, side, lp)
                    recs_c = [(c, cand_record(c, jt, side, m))
                              for c in cands]
                    hits = [(c, r) for c, r in recs_c
                            if V2.match(g, r, m)]
                    per_side.append((side, len(cands), hits, recs_c))
                # choose the side with any hit; else the busier side
                pick = None
                for side, nc, hits, recs_c in per_side:
                    if hits:
                        pick = (side, nc, hits, recs_c)
                        break
                if pick is None and per_side:
                    pick = max(per_side, key=lambda x: x[1])
                if pick is None:
                    continue
                side, nc, hits, recs_c = pick
                reach = len(hits) > 0
                row = {"panel": rec["id"], "type": st, "tau": tau,
                       "n_cand": nc, "reach": reach,
                       "gslope": gslope, "side": side}
                if recs_c:
                    # rule table: rank all legal candidates, does a
                    # top-k pick match the golden?
                    abr = max(e.abr[jt], 1e-9)
                    px = e.bars[jt]["c"]
                    rules = {
                        "nt": lambda c: (-c["nt"], -c["span"]),
                        "nev": lambda c: (-c["n_ev"], -c["nt"]),
                        "npt": lambda c: (-c["n_pt"], -c["nt"]),
                        "young_b": lambda c: (-c["b"]["t"], -c["nt"]),
                        "young_a": lambda c: (-c["a"]["t"], -c["nt"]),
                        "long_span": lambda c: (-c["span"], -c["nt"]),
                        "min_over": lambda c: (c["over"], -c["nt"]),
                        "engine": lambda c: (
                            -(c["nt"] - 0.5 * max(
                                0, (jt - c["t0"]) * 5 - lp[
                                    "span_max_min"]) / 60.0)),
                        "lab": lambda c: (
                            -(c["n_ev"]
                              - lp.get("overshoot_w", .5) * c["over"]
                              / max(1e-9, max(lp["touch_tol_pips"],
                                              lp["touch_tol_abr_frac"]
                                              * abr))
                              - lp.get("span_age_w", .5) * max(
                                0, (jt - c["t0"]) * 5 - lp[
                                    "span_max_min"]) / 60.0)),
                        "prox": lambda c: (
                            abs(px - (c["a"]["p"] + c["slope"]
                                      * (jt - c["t0"])))),
                        "nev_young": lambda c: (-c["n_ev"],
                                                -c["b"]["t"]),
                        "nev_over": lambda c: (-c["n_ev"], c["over"]),
                    }
                    for rn, key in rules.items():
                        order = sorted((c for c, _r in recs_c),
                                       key=key)
                        for kk in (1, 2):
                            ok = any(V2.match(g, cand_record(
                                c, jt, side, m), m)
                                for c in order[:kk])
                            row["%s@%d" % (rn, kk)] = ok
                # engine funnel: proposed in cand_log before tau?
                # born (any engine object matching cumulatively)?
                prop = False
                for cl in (e.cand_log or []):
                    if cl.get("kind") not in ("PATTERN_LINE",
                                              "CONTEXT_LINE"):
                        continue
                    if cl.get("cet_min") is None or \
                            cl["cet_min"] > tau or \
                            cl.get("p0") is None:
                        continue
                    cj = j_at(m, cl["cet_min"])
                    rec_c = {"type": cl["kind"],
                             "t0": int(m[int(cl["t0"])]),
                             "t1": int(m[cj]),
                             "t0_raw": int(m[int(cl["t0"])]),
                             "t1_raw": int(m[cj]),
                             "t_birth": int(m[cj]),
                             "p0": cl["p0"], "slope": cl["slope"],
                             "t0_bar": int(cl["t0"]),
                             "side": cl.get("side"),
                             "w0": 0, "w1": 10**9}
                    if V2.match(g, rec_c, m):
                        prop = True
                        break
                row["proposed"] = prop
                row["born"] = any(V2.match(g, eo, m) for eo in eobjs)
                rows.append(row)
            elif st in ("LEVEL_CARRIED", "MINI_LEVEL"):
                if g.get("t0") is None:
                    continue
                tau = min(g["t0"] + 10, w1)
                jt = j_at(m, tau)
                if jt < 5:
                    continue
                ogs = defended_origins(e, jt, lvp)
                px = e.bars[jt]["c"]
                abr = max(e.abr[jt], 1e-9)
                cands = []
                for og in ogs:
                    for side_s, side_i in (("above", 1),
                                           ("below", -1)):
                        if og["dir"] != side_i:
                            continue
                        cands.append((og, side_s))
                def lv_match(og, side_s):
                    r = level_record(og["price"], side_s,
                                     int(m[og["bar"]]), int(m[jt]))
                    return V2.match(g, r, m)
                hits = [(og, s) for og, s in cands if lv_match(og, s)]
                row = {"panel": rec["id"], "type": st, "tau": tau,
                       "n_cand": len(cands), "reach": len(hits) > 0}
                rules = {
                    "near": lambda cs: abs(px - cs[0]["price"]),
                    "ndef": lambda cs: (-cs[0]["n_def"],
                                       abs(px - cs[0]["price"])),
                    "ndef_dist": lambda cs: -(
                        cs[0]["n_def"]
                        - abs(px - cs[0]["price"]) / abr
                        + (1.0 if jt - cs[0]["last_t"]
                           <= lvp["def_ret24_bars"] else 0.0)),
                    "ndef2_near": lambda cs: (
                        0 if cs[0]["n_def"] >= 2 else 1,
                        abs(px - cs[0]["price"])),
                    "young": lambda cs: -cs[0]["bar"],
                    "old": lambda cs: cs[0]["bar"],
                }
                for rn, key in rules.items():
                    order = sorted(cands, key=key)
                    for kk in (1, 2):
                        ok = any(lv_match(og, s)
                                 for og, s in order[:kk])
                        row["%s@%d" % (rn, kk)] = ok
                row["born"] = any(V2.match(g, eo, m) for eo in eobjs)
                rows.append(row)
        if n_pan % 25 == 0:
            print("panel %d/%d rows=%d" % (n_pan, len(recs), len(rows)),
                  flush=True)
    with open(OUT, "w", encoding="utf8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    # aggregate
    print("\n=== AGGREGATE ===")
    for st in ("PATTERN_LINE", "CONTEXT_LINE", "LEVEL_CARRIED",
               "MINI_LEVEL"):
        sub = [r for r in rows if r["type"] == st]
        if not sub:
            continue
        print("\n%s  n=%d  reach=%d (%.2f)  proposed=%d (%.2f)  "
              "born(cum-ink)=%d (%.2f)" % (
                  st, len(sub), sum(r["reach"] for r in sub),
                  sum(r["reach"] for r in sub) / len(sub),
                  sum(r.get("proposed", 0) for r in sub),
                  sum(r.get("proposed", 0) for r in sub) / len(sub),
                  sum(r.get("born") for r in sub),
                  sum(r.get("born") for r in sub) / len(sub)))
        keys = sorted({k for r in sub for k in r
                       if "@" in k})
        for k in keys:
            vals = [r.get(k) for r in sub if k in r]
            if vals:
                print("   %-14s %.2f (%d/%d)" % (
                    k, sum(vals) / len(vals), sum(vals), len(vals)))


if __name__ == "__main__":
    main()
