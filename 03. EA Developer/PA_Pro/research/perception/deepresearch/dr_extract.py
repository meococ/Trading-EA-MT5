"""dr_extract.py -- DR-BOX (R64): per-(panel,golden) candidate-pool extraction.

For every scorable box-family golden in TUNE (tau >= w0), dump:
  * the golden's geometry + text fields (clause/lesson/marks);
  * the panel's event-route candidate stream (event_cands.pkl), each cand
    flagged born <= j_tau (causally available) and edge-match vs golden;
  * per-cand CAUSAL features (bars <= j_tau only);
  * per-cand POST-TAU outcome fields (bars in (j_tau, j_w1], inside the
    panel window) -- hypothesis-test only, never features.

Read-only on caches. Writes deepresearch/dr_rows.pkl.
"""
import sys, os, pickle, json, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "boxlab"))

import common as C                     # noqa: E402
import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import cache as CA                     # noqa: E402
from snapshot import tau_of            # noqa: E402

PIP = C.PIP
EC = pickle.load(open(os.path.join(PERC, "boxlab", "r_dataset",
                                   "event_cands.pkl"), "rb"))

# setup-code vocabulary seen in arrow 'raw' fields
SETUP_RE = ("dd", "fb", "sb", "bb", "rb", "irb", "arb",
            "pb", "pbc", "pbp", "tff", "pr", "press")


def _parse_t(raw_t):
    """Arrow mark t: 'HH:MM' string (v1 file) -> cet_min."""
    if raw_t is None:
        return None
    s = str(raw_t)
    if ":" in s:
        hh, mm = s.split(":")[:2]
        return int(hh) * 60 + int(mm)
    try:
        return int(float(s))
    except ValueError:
        return None


def zigzag_swings(cl, lo_i, hi_i, k):
    """Count direction changes of close inside [lo_i, hi_i] at amplitude k
    (pips).  Simple causal zigzag on closes."""
    if hi_i <= lo_i:
        return 0
    seg = cl[lo_i:hi_i + 1]
    if len(seg) < 3:
        return 0
    n = 0
    d = 0
    ext = seg[0]
    for v in seg[1:]:
        if d == 0:
            if v > ext:
                ext = v
            elif v < ext:
                ext = v
            if abs(v - seg[0]) >= k:
                d = 1 if v > seg[0] else -1
                ext = v
        elif d == 1:
            if v > ext:
                ext = v
            elif v <= ext - k:
                n += 1
                d = -1
                ext = v
        else:
            if v < ext:
                ext = v
            elif v >= ext + k:
                n += 1
                d = 1
                ext = v
    return n


def main():
    raw = {r["id"]: r for r in
           (json.loads(l) for l in open(
               os.path.join(PERC, "golden", "BOOK2012_TUNE.jsonl"),
               encoding="utf8"))}
    out = []
    for rec in C.load_tune():
        pid = rec["id"]
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        abr = CA.abr(rec["date"])          # causal ABR(50), pips
        jw1 = int(np.searchsorted(m, w1, "right")) - 1
        jw0 = int(np.searchsorted(m, w0, "left"))
        gobjs, _u, _to = EV.gold_objects(rec)
        # panel marks (setup arrows) from the v1 file (labels kept there)
        marks = []
        for mk_ in raw.get(pid, {}).get("marks", []):
            if mk_.get("kind") == "ARROW":
                marks.append({"t": _parse_t(mk_.get("t")),
                              "raw": str(mk_.get("raw") or ""),
                              "dir": mk_.get("dir")})
            elif mk_.get("kind") == "SESSION":
                marks.append({"t": _parse_t(mk_.get("t")),
                              "raw": "SESS:" + str(mk_.get("label") or
                                                     mk_.get("raw") or ""),
                              "dir": None})
        # day context levels (causal anchors)
        prior_date = None
        dates = sorted({r2["date"] for r2 in C.load_tune()})
        # prior-day high/low from bars cache if the day exists in BOOK
        asia = None   # 00:00-07:00 CET high/low same day
        am = (m >= 0) & (m < 420)
        if am.any():
            asia = (float(l[am].min()), float(h[am].max()))
        for g in gobjs:
            if EV.FAMILY.get(g["spec_type"]) != "box":
                continue
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            if not V2.scorable(g, w0, w1):
                continue
            tau = min(tau, w1)
            j_tau = int(np.searchsorted(m, tau, "right")) - 1
            if j_tau < 0:
                continue
            glo = g["price_lo"] / PIP
            ghi = g["price_hi"] / PIP
            tol = V2.tol_px(g)
            a_tau = float(abr[j_tau]) if j_tau < len(abr) else 5.0
            px_tau = float(c[j_tau])
            day_hi_so_far = float(h[:j_tau + 1].max())
            day_lo_so_far = float(l[:j_tau + 1].min())

            pool = []
            for cd in EC.get(pid, []):
                born = int(cd["born"])
                t0b = int(cd["t0"])
                hi_c, lo_c = float(cd["hi"]), float(cd["lo"])
                avail = born <= j_tau
                match = (abs(hi_c - ghi) <= tol and abs(lo_c - glo) <= tol)
                f = {"route": cd["route"], "born": born, "t0": t0b,
                     "hi": hi_c, "lo": lo_c, "leg": float(cd["leg"]),
                     "prom": float(cd["prom"]), "pairsep": int(cd["pairsep"]),
                     "avail": avail, "match": match}
                f["height"] = hi_c - lo_c
                f["age_bars"] = j_tau - born
                f["span_bars"] = born - t0b
                if avail:
                    inb = lo_c <= px_tau <= hi_c
                    f["px_in_box"] = float(inb)
                    f["dist_close_edge_abr"] = min(
                        abs(px_tau - hi_c), abs(px_tau - lo_c)) / a_tau
                    f["px_frac"] = ((px_tau - lo_c) /
                                    max(hi_c - lo_c, 1e-9))
                    # bars since any bar overlapped the band
                    touch = j_tau
                    for j in range(j_tau, -1, -1):
                        if l[j] <= hi_c and h[j] >= lo_c:
                            touch = j_tau - j
                            break
                    f["bars_since_touch"] = touch
                    # edge touches: bars in [t0, j_tau] whose extreme
                    # comes within 1.5p of each edge
                    t1e = min(j_tau, max(born, t0b))
                    tt = tl = 0
                    for j in range(max(0, t0b), t1e + 1):
                        if abs(h[j] - hi_c) <= 1.5 or \
                           (l[j] <= hi_c <= h[j]):
                            tt += 1
                        if abs(l[j] - lo_c) <= 1.5 or \
                           (l[j] <= lo_c <= h[j]):
                            tl += 1
                    f["touches_hi"] = tt
                    f["touches_lo"] = tl
                    # share of span bars whose range overlaps the band
                    ov = sum(1 for j in range(max(0, t0b), t1e + 1)
                             if l[j] <= hi_c and h[j] >= lo_c)
                    f["overlap_ratio"] = ov / max(1, t1e - max(0, t0b) + 1)
                    # swings inside the band over its span (zigzag 0.3*ABR)
                    f["n_swings"] = zigzag_swings(
                        c, max(0, t0b), t1e, 0.3 * a_tau)
                    # compression: range of second half vs first half
                    mid = (max(0, t0b) + t1e) // 2
                    r1 = (h[max(0, t0b):mid + 1].max()
                          - l[max(0, t0b):mid + 1].min()) if mid > t0b else 0
                    r2 = (h[mid + 1:t1e + 1].max()
                          - l[mid + 1:t1e + 1].min()) if t1e > mid else 0
                    f["compression"] = float(r2) / max(float(r1), 1e-9)
                    # round-50 anchors (pip space): dist of each edge to
                    # nearest multiple of 50 pips
                    f["hi_round50"] = min(hi_c % 50, 50 - hi_c % 50)
                    f["lo_round50"] = min(lo_c % 50, 50 - lo_c % 50)
                    f["min_round50"] = min(f["hi_round50"], f["lo_round50"])
                    # prior-structure anchors: day open, asia range,
                    # day-so-far extremes
                    day_open = float(o[0])
                    f["hi_dayopen"] = abs(hi_c - day_open)
                    f["lo_dayopen"] = abs(lo_c - day_open)
                    if asia:
                        f["hi_asia"] = min(abs(hi_c - asia[0]),
                                           abs(hi_c - asia[1]))
                        f["lo_asia"] = min(abs(lo_c - asia[0]),
                                           abs(lo_c - asia[1]))
                        f["min_asia"] = min(f["hi_asia"], f["lo_asia"])
                    f["hi_dayext"] = min(abs(hi_c - day_hi_so_far),
                                         abs(hi_c - day_lo_so_far))
                    f["lo_dayext"] = min(abs(lo_c - day_hi_so_far),
                                         abs(lo_c - day_lo_so_far))
                    # ---- POST-TAU outcomes (window bars only, j_tau<j<=jw1)
                    # hypothesis-test fields, never causal features ----
                    if j_tau < jw1:
                        seg_c = c[j_tau + 1:jw1 + 1]
                        up = np.where(seg_c > hi_c)[0]
                        dn = np.where(seg_c < lo_c)[0]
                        f["brk_up_bar"] = int(up[0]) + 1 if len(up) else None
                        f["brk_dn_bar"] = int(dn[0]) + 1 if len(dn) else None
                        firsts = [x for x in (f["brk_up_bar"],
                                              f["brk_dn_bar"])
                                  if x is not None]
                        f["brk_bar"] = min(firsts) if firsts else None
                        f["brk_dir"] = (1 if f["brk_bar"] == f["brk_up_bar"]
                                        else -1) if firsts else 0
                        # excursion beyond broken edge within 24 bars of tau
                        w2 = min(jw1, j_tau + 24)
                        if firsts:
                            bj = j_tau + f["brk_bar"]
                            end = min(jw1, bj + 24)
                            if f["brk_dir"] > 0:
                                f["post_exc_abr"] = float(
                                    (h[bj:end + 1].max() - hi_c)) / a_tau
                            else:
                                f["post_exc_abr"] = float(
                                    (lo_c - l[bj:end + 1].min())) / a_tau
                        else:
                            f["post_exc_abr"] = 0.0
                    pool.append(f)
            out.append({
                "panel": pid, "date": rec["date"], "w0": w0, "w1": w1,
                "jw0": jw0, "jw1": jw1, "tau": tau, "j_tau": j_tau,
                "abr_tau": a_tau, "px_tau": px_tau,
                "g_lo": glo, "g_hi": ghi, "g_t0": g.get("t0"),
                "g_t1": g.get("t1"), "g_bs": g.get("build_start"),
                "g_be": g.get("build_end"), "g_type": g["spec_type"],
                "prec": g.get("prec"), "tol": tol,
                "clause": g.get("clause") or g.get("raw_note"),
                "lesson": rec.get("lesson"), "marks": marks,
                "n_cands": len(pool), "n_avail": sum(p_["avail"]
                                                   for p_ in pool),
                "n_match": sum(p_["match"] and p_["avail"]
                               for p_ in pool),
                "pool": pool})
    with open(os.path.join(HERE, "dr_rows.pkl"), "wb") as fh:
        pickle.dump(out, fh, protocol=4)
    print("goldens:", len(out))
    print("avail cands:", sum(r["n_avail"] for r in out))
    print("reachable (>=1 avail match):", sum(1 for r in out
                                              if r["n_match"]))


if __name__ == "__main__":
    main()
