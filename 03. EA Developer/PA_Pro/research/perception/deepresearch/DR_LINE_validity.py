"""DR_LINE_validity.py — E3c: does price react at defended prices on
DESIGN data?  (outcome-blind; no PnL, no setups, no trade simulation)

DESIGN window only (2016-2021), EURUSD M5 via scale/design_loader.py.

PRE-REGISTERED DESIGN (declared in DR_LINE_LOG.md before the run):

  Origin stream = the defended-origin registry from levels.py's
    defended_origin route, replayed standalone: confirmed DC pivots
    (theta = 0.8*ABR retrace, prom floor 0.5*ABR — swing params
    k1_abr/pmin_abr) + running session/Asia extremes; same-side merges
    within def tol (max(1.5p, 0.25*ABR)) keep the EDGE price; n_def =
    deduped bar-extreme touches.

  Arrival event at origin P (side s in {support=-1, resistance=+1}):
    first bar i where close enters [P-tol, P+tol] after >=12 consecutive
    bars with close outside [P-1.75*ABR, P+1.75*ABR] on the defended
    side's approach direction (for support: arrival from above —
    closes were > P + 1.75*ABR; for resistance: from below).

  Arms:
    TREAT      arrival at an origin with n_def >= 2 (defended memory)
    CTRL0      arrival at an origin with n_def == 0 (marked extreme,
               never defended since registration)
    PLACEBO    the SAME arrival bar, but the "level" is P +/- 8 pips
               (not an origin): identical approach path, moved price —
               the identifiable price-specificity contrast.

  Reaction over the next H=12 bars (value-blind path geometry only):
    bounce   = max excursion AWAY on the defended side
               (support: max(h_j - P); resistance: max(P - l_j)) / ABR
    pierce   = max excursion THROUGH the level
               (support: max(P - l_j); resistance: max(h_j - P)) / ABR
    first    = which side of the +-0.5*ABR band around P is exited
               first (defended vs through; 'none' if still inside)

  Matching: TREAT vs CTRL0 nearest-neighbour on
    (approach speed = |c_i - c_{i-3}|/ABR, start distance in ABR,
     hour-of-day bucket, side), caliper 0.25 on each continuous dim.
    Report matched fraction; if common support is poor, descriptive only
    (R01/R02 lesson).

  Hypotheses (from essence): bounce-first probability and bounce/pierce
    asymmetry higher at defended origins than fresh ones and placebos;
    dose-response in n_def.

Output: DR_LINE_validity.jsonl + printed table.
"""
import json
import os
import sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "golden"))
sys.path.insert(0, os.path.join(PERC, "scale"))
sys.path.insert(0, os.path.join(PERC, "..", "..", "lib"))

import numpy as np                      # noqa: E402

import design_loader                   # noqa: E402
from swings import DCStream, SwingBook  # noqa: E402

OUT = os.path.join(HERE, "DR_LINE_validity.jsonl")

PIP = 1e4
K1_ABR = 0.8         # swing.k1_abr
PMIN_ABR = 0.5       # swing.pmin_abr
PSTRUCT_ABR = 2.5    # swing.pstruct_abr
DEF_TOL_P = 1.5      # level.def_touch_tol_pips
DEF_TOL_F = 0.25     # level.def_touch_tol_abr_frac
APPROACH_ABR = 1.75  # level.def_approach_abr
AWAY_BARS = 12       # must have been outside the approach band this long
H = 12               # forward reaction window (bars)
BAND = 0.5           # +-0.5*ABR exit band for 'first'


def day_list():
    """Every 21st calendar day inside DESIGN (2016-2021)."""
    d = date(2016, 1, 4)
    out = []
    while d <= date(2021, 12, 31):
        out.append(d)
        d += timedelta(days=21)
    return out


def replay(bars):
    """One DESIGN day -> (pivots, origins, abr).  All causal."""
    o, h, l, c = bars["o"] * PIP, bars["h"] * PIP, \
        bars["l"] * PIP, bars["c"] * PIP
    n = len(c)
    abr = np.zeros(n)
    for i in range(n):
        j0 = max(0, i - 49)
        abr[i] = (h[j0:i + 1] - l[j0:i + 1]).mean()
    abr = np.maximum(abr, 1e-9)
    dc = DCStream(lambda i: K1_ABR * abr[i])
    book = SwingBook(PMIN_ABR, PSTRUCT_ABR, abr_fn=lambda i: abr[i])
    pivs = []                       # (t_conf, Pivot)
    for i in range(n):
        book.update_running(dc.dir, dc.ext_price)
        for p in dc.update(i, h[i], l[i]):
            book.add(p)
            pivs.append((i, p))
    # origins registry (levels.py defended_origin semantics)
    origins = []
    run = {1: None, -1: None}
    piv_by_conf = {}
    for tc, p in pivs:
        piv_by_conf.setdefault(tc, []).append(p)

    def tol(i):
        return max(DEF_TOL_P, DEF_TOL_F * abr[i])

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

    evs = []
    for i in range(n):
        # running session/Asia extremes
        cm = int(bars["cet_min"][i])
        if h[i] > (run[1]["price"] if run[1] else -1e18):
            add(i, h[i], 1, "asia" if cm < 420 else "session",
                sess=True)
            run[1] = {"bar": i, "price": h[i]}
        if l[i] < (run[-1]["price"] if run[-1] else 1e18):
            add(i, l[i], -1, "asia" if cm < 420 else "session",
                sess=True)
            run[-1] = {"bar": i, "price": l[i]}
        for p in piv_by_conf.get(i, ()):
            add(p.t_ext, p.price, p.dir,
                "theta2" if book.is_structural(p) else "theta1")
        # defence sweep
        for og in origins:
            ext = l[i] if og["dir"] < 0 else h[i]
            hit = abs(ext - og["price"]) <= tol(i)
            if hit and not og.get("_run"):
                og["n_def"] += 1
                og["last_t"] = i
            og["_run"] = hit
        # arrival detection per origin
        for og in origins:
            if og.get("_arrived"):
                continue
            s = og["dir"]
            P = og["price"]
            if s < 0:    # support: arrival from above
                inside = abs(c[i] - P) <= tol(i)
                if inside and i >= AWAY_BARS + 1:
                    win = c[i - AWAY_BARS:i]
                    if (win > P + APPROACH_ABR * abr[i]).all():
                        evs.append({"og": og, "i": i,
                                    "n_def": og["n_def"],
                                    "side": s, "P": P})
                        og["_arrived"] = True
            else:        # resistance: arrival from below
                inside = abs(c[i] - P) <= tol(i)
                if inside and i >= AWAY_BARS + 1:
                    win = c[i - AWAY_BARS:i]
                    if (win < P - APPROACH_ABR * abr[i]).all():
                        evs.append({"og": og, "i": i,
                                    "n_def": og["n_def"],
                                    "side": s, "P": P})
                        og["_arrived"] = True
    for og in origins:
        og.pop("_run", None)
    return evs, abr, origins


def incidental(bars, evs, origins):
    """Zone-hover crossings of the same origins: a bar where the close
    crosses INTO the origin's tol zone having stayed within +-1.75*ABR
    of it for >=12 bars (no genuine return — same price, no journey)."""
    o, h, l, c = bars["o"] * PIP, bars["h"] * PIP, \
        bars["l"] * PIP, bars["c"] * PIP
    abr = np.zeros(len(c))
    for i in range(len(c)):
        j0 = max(0, i - 49)
        abr[i] = (h[j0:i + 1] - l[j0:i + 1]).mean()
    abr = np.maximum(abr, 1e-9)
    used = set()
    out = []
    for og in origins:
        s, P = og["dir"], og["price"]
        for i in range(og["bar"] + 1, len(c)):
            if abs(c[i] - P) <= max(DEF_TOL_P, DEF_TOL_F * abr[i]) \
                    and i >= AWAY_BARS + 1:
                win = c[i - AWAY_BARS:i]
                if s < 0 and (win > P).all() and \
                        (win < P + APPROACH_ABR * abr[i]).all():
                    pass
                elif s > 0 and (win < P).all() and \
                        (win > P - APPROACH_ABR * abr[i]).all():
                    pass
                else:
                    continue
                if id(og) in used:
                    break
                used.add(id(og))
                out.append({"og": og, "i": i, "n_def": og["n_def"],
                            "side": s, "P": P})
                break
    return out


def reaction(bars, abr, ev, shift_p=0.0):
    """Forward path geometry vs level price P(+shift)."""
    o, h, l, c = bars["o"] * PIP, bars["h"] * PIP, \
        bars["l"] * PIP, bars["c"] * PIP
    i, s, P = ev["i"], ev["side"], ev["P"] + shift_p
    j_end = min(i + H, len(c) - 1)
    if j_end <= i + 1:
        return None
    a = abr[i]
    if s < 0:   # support: defended = up, through = down
        bounce = (h[i + 1:j_end + 1] - P).max() / a
        pierce = (P - l[i + 1:j_end + 1]).max() / a
        exu = h[i + 1:j_end + 1] - P
        exd = P - l[i + 1:j_end + 1]
    else:       # resistance: defended = down, through = up
        bounce = (P - l[i + 1:j_end + 1]).max() / a
        pierce = (h[i + 1:j_end + 1] - P).max() / a
        exu = P - l[i + 1:j_end + 1]
        exd = h[i + 1:j_end + 1] - P
    first = "none"
    for k in range(len(exu)):
        if exu[k] >= BAND * a:
            first = "defended"
            break
        if exd[k] >= BAND * a:
            first = "through"
            break
    # approach features
    spd = abs(c[i] - c[i - 3]) / a if i >= 3 else 0.0
    dist0 = abs(c[i - AWAY_BARS] - P) / a if i >= AWAY_BARS else 0.0
    return {"bounce": bounce, "pierce": pierce, "first": first,
            "speed": spd, "dist0": dist0, "hour": i * 5 // 60,
            "n_def": ev["n_def"], "side": s}


def main():
    days = day_list()
    rows = []
    ndone = 0
    for d in days:
        s_cet = "%s 00:00" % d.isoformat()
        e_cet = "%s 23:55" % d.isoformat()
        try:
            bars = design_loader.load_m5("EURUSD", s_cet, e_cet)
        except Exception:
            continue
        if len(bars["c"]) < 60:
            continue
        evs, abr, origins = replay(bars)
        inc = incidental(bars, evs, origins)
        for ev in evs:
            r = reaction(bars, abr, ev)
            if r is None:
                continue
            for pl in (8.0, -8.0):
                rp = reaction(bars, abr, ev, shift_p=pl)
                if rp:
                    ev.setdefault("pl", []).append(rp)
            r["pl8"] = [round(x["bounce"], 3) for x in ev.get("pl", [])]
            r["pl8p"] = [round(x["pierce"], 3)
                         for x in ev.get("pl", [])]
            r["pl8f"] = [x["first"] for x in ev.get("pl", [])]
            r["date"] = d.isoformat()
            r["cls"] = ev["og"]["cls"]
            rows.append(r)
        # INCIDENTAL arm: same-origin crossings WITHOUT the >=12-bar
        # away condition (zone-hovers) — identifiable within-origin
        # contrast: does the return-from-distance carry the signal?
        for ev in inc:
            r = reaction(bars, abr, ev)
            if r is None:
                continue
            r["date"] = d.isoformat()
            r["cls"] = ev["og"]["cls"]
            r["incidental"] = True
            rows.append(r)
        ndone += 1
        if ndone % 20 == 0:
            print("day %d evs=%d" % (ndone, len(rows)), flush=True)
    with open(OUT, "w", encoding="utf8") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=str) + "\n")

    # ---- report ----
    arr = [r for r in rows if not r.get("incidental")]
    inc = [r for r in rows if r.get("incidental")]
    tr = [r for r in arr if r["n_def"] >= 2]
    c0 = [r for r in arr if r["n_def"] == 0]
    print("\n=== arrivals=%d incidental=%d | TREAT(n_def>=2)=%d "
          "CTRL0(n_def=0)=%d ==="
          % (len(arr), len(inc), len(tr), len(c0)))

    def stat(rs, name):
        if not rs:
            return "%s: n=0" % name
        b = np.array([r["bounce"] for r in rs])
        p = np.array([r["pierce"] for r in rs])
        fb = sum(r["first"] == "defended" for r in rs) / len(rs)
        ft = sum(r["first"] == "through" for r in rs) / len(rs)
        return ("%s n=%d bounce med=%.2f pierce med=%.2f "
                "P(first=defended)=%.2f P(first=through)=%.2f"
                % (name, len(rs), np.median(b), np.median(p), fb, ft))

    print(stat(tr, "TREAT"))
    print(stat(c0, "CTRL0"))
    print(stat(inc, "INCIDENTAL(hover, same origins)"))
    pl_b = [x for r in arr for x in r.get("pl8", [])]
    pl_p = [x for r in arr for x in r.get("pl8p", [])]
    pl_f = [x for r in arr for x in r.get("pl8f", [])]
    if pl_b:
        print("PLACEBO(+-8p) n=%d bounce med=%.2f pierce med=%.2f "
              "P(def)=%.2f P(thr)=%.2f" % (
                  len(pl_b), float(np.median(pl_b)),
                  float(np.median(pl_p)),
                  sum(f == "defended" for f in pl_f) / len(pl_f),
                  sum(f == "through" for f in pl_f) / len(pl_f)))
    # dose-response by n_def
    print("\nn_def dose-response (arrivals only):")
    for lo, hi, tag in ((0, 0, "0"), (1, 1, "1"), (2, 3, "2-3"),
                        (4, 99, "4+")):
        rs = [r for r in arr if lo <= r["n_def"] <= hi]
        print("  n_def=%-3s %s" % (tag, stat(rs, "d")))
    # approach-speed split (the R01 confound)
    sp = np.array([r["speed"] for r in arr])
    med_sp = np.median(sp) if len(sp) else 0
    print("\napproach-speed split (median speed %.2f):" % med_sp)
    for arm, rs in (("TREAT", tr), ("INCIDENTAL", inc)):
        for lab, cond in (("slow", lambda r: r["speed"] <= med_sp),
                          ("fast", lambda r: r["speed"] > med_sp)):
            sub = [r for r in rs if cond(r)]
            print("  %s/%s %s" % (arm, lab, stat(sub, "x")))
    # matched subsample TREAT vs CTRL0 on (speed, dist0, hour, side)
    print("\nmatching TREAT->CTRL0 (cal 0.25 speed/dist0, same hour "
          "bucket & side):")
    used = set()
    m_tr, m_c0 = [], []
    for r in tr:
        best, bd = None, 1e9
        for k, q in enumerate(c0):
            if k in used or q["side"] != r["side"] or \
                    q["hour"] != r["hour"]:
                continue
            d = abs(q["speed"] - r["speed"]) + \
                abs(q["dist0"] - r["dist0"])
            if d < bd:
                best, bd = k, d
        if best is not None and abs(c0[best]["speed"] - r["speed"]) \
                <= 0.25 and abs(c0[best]["dist0"] - r["dist0"]) <= 0.25:
            used.add(best)
            m_tr.append(r)
            m_c0.append(c0[best])
    print("  matched %d/%d treated (%.0f%%)" % (
        len(m_tr), len(tr), 100 * len(m_tr) / max(len(tr), 1)))
    print("  " + stat(m_tr, "TREAT(matched)"))
    print("  " + stat(m_c0, "CTRL0(matched)"))


if __name__ == "__main__":
    main()
