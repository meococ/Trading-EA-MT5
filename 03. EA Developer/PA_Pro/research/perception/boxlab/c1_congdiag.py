"""c1_congdiag.py — R46 §46.3.1: diagnose the no-edge BOX goldens
under K6 (cong_trigger ON, k=5.5, N=6) at hash 9acaa206.

For each golden that no box candidate ever edge-matches:
  1. does a congestion-scan proposal overlap its buildup in time?
  2. if yes — top/bottom edge errors vs golden, in pips and ABR;
  3. failure cause: edge_tol | band_tall | run_short | blocked |
     silent (no qualifying run and no proposal).

The run check mirrors BoxBook._cong_run: expand back from bar i
while the h-l envelope stays <= cong_h_abr * abr[i]; qualifies at
>= cong_min_bars.  Bars only — no engine re-run (cache pickles).
"""
import collections
import os
import pickle
import sys
import glob

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)

import common as C                         # noqa: E402
import eval as EV                          # noqa: E402
import eval_v2 as V2                       # noqa: E402
import funnel as F                         # noqa: E402
import cache as CA                         # noqa: E402
from scoreboard import panel_cands         # noqa: E402

H8 = "9acaa206c8d386dc"
VAR = "m1_v1"          # K6 kept config (params carry cong ON @ k5.5)
CONG_H, CONG_N = 5.5, 6


def _pkls(variant, h):
    return sorted(glob.glob(os.path.join(
        PERC, "evalcheck", "_cache",
        "run_%s_%s_*.pkl" % (variant, h))))


def _idx(m, minute):
    return int(np.searchsorted(m, minute))


def main():
    recs = C.load_tune()
    rows = []
    causes = collections.Counter()
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        # full-window pickle: run_<var>_<hash>_<date>_<w1>.pkl
        pk = os.path.join(
            PERC, "evalcheck", "_cache",
            "run_%s_%s_%s_%s.pkl" % (VAR, H8, rec["date"], w1))
        if not os.path.exists(pk):
            continue
        e = pickle.load(open(pk, "rb"))
        abr = e.abr          # engine ABR — matches _cong_run's cap
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        cands = panel_cands(e, m, w0, w1)
        same = [r for r in cands if EV.FAMILY.get(r["type"]) == "box"]
        cong = [r for r in e.cand_log or []
                if r.get("route") == "congestion_scan"
                and r.get("cong")]
        for gi, g in enumerate(g2):
            if g["spec_type"] != "BOX":
                continue
            if g.get("price_lo") is None:
                continue
            # no-edge class: no cand ever carries BOTH golden edges
            if any(F.edges_pass(g, r) for r in same):
                continue
            glo, ghi = g["price_lo"] / C.PIP, g["price_hi"] / C.PIP
            gbs = g.get("build_start") or g.get("t0")
            gbe = g.get("build_end") or g.get("t1")
            # golden times and w0/w1 are minute-of-day; convert to
            # bar indices into the clipped day bars
            iw0, iw1 = _idx(m, w0), _idx(m, w1)
            i0 = _idx(m, gbs) if gbs is not None else iw0
            i1 = _idx(m, gbe) if gbe is not None else iw1
            i0, i1 = max(i0, iw0), min(max(i1, i0 + 1), iw1)
            tol = V2.tol_px(g)
            # cong proposals overlapping the buildup span
            ov = [r for r in cong
                  if r["t0"] <= i1 and r["t1"] >= i0]
            if ov:
                # best-overlap cand: min summed edge error
                def _err(r):
                    return (abs(r["top"] - ghi) +
                            abs(r["bottom"] - glo))
                r = min(ov, key=_err)
                et = abs(r["top"] - ghi)
                eb = abs(r["bottom"] - glo)
                a = r.get("abr") or abr[min(r["idx"], len(abr) - 1)]
                rows.append((rec["id"], gi, "edge_tol",
                             et, eb, et / a, eb / a,
                             len(ov)))
                causes["edge_tol"] += 1
                continue
            # no overlapping cong cand — recompute the run check
            best_len = 0
            best_env = 1e9          # min 6-bar envelope / abr
            block = collections.Counter()
            bp = e.p["box"]
            for i in range(i0, i1 + 1):
                if i >= len(h):
                    break
                cap = CONG_H * abr[i]
                hi, lo, j = -1e18, 1e18, i
                while j >= 0:
                    h2 = max(hi, h[j]); l2 = min(lo, l[j])
                    if h2 - l2 > cap:
                        break
                    hi, lo, j = h2, l2, j - 1
                rl = i - j
                best_len = max(best_len, rl)
                if i - CONG_N + 1 >= 0:
                    env6 = (max(h[i - CONG_N + 1:i + 1]) -
                            min(l[i - CONG_N + 1:i + 1]))
                    best_env = min(best_env, env6 / abr[i])
                if rl < CONG_N:
                    continue
                # run qualifies on the envelope — replay the
                # downstream gates of _buildup_run + scan tail
                top, bot = hi, lo
                bs = i
                while bs - 1 >= 0 and bot <= c[bs - 1] <= top:
                    bs -= 1
                if i - bs + 1 < CONG_N:
                    block["contained_run<6"] += 1
                    continue
                hh = top - bot
                if hh < max(bp["height_min_abr"] * abr[i],
                            bp["height_min_pips"]):
                    block["too_thin<6p"] += 1
                    continue
                if hh > min(bp["height_max_abr"] * abr[i],
                            bp["height_max_pips"]):
                    block["too_tall"] += 1
                    continue
                rb = c[bs:i + 1]
                inside = sum(bot <= x <= top for x in rb)
                if inside / len(rb) < bp["contain_min_frac"]:
                    block["contain_frac"] += 1
                    continue
                # live-cover early return: a BOX born before i whose
                # band holds close[i] (approximate — end-state only)
                cov = any(o.type == "BOX" and o.t_birth <= i and
                          o.geometry["bottom"] <= c[i] <=
                          o.geometry["top"] for o in e.objects)
                if cov:
                    block["live_cover"] += 1
                else:
                    block["other"] += 1
            if i0 > i1:
                rows.append((rec["id"], gi, "no_window",
                             None, None, 0.0, 0, 0))
                causes["no_window"] += 1
            elif block:
                cz = block.most_common(1)[0][0]
                rows.append((rec["id"], gi, "blocked:" + cz,
                             None, None, best_env, best_len, 0))
                causes["blocked:" + cz] += 1
            elif best_len < CONG_N and best_env <= CONG_H:
                rows.append((rec["id"], gi, "run_short",
                             None, None, best_env, best_len, 0))
                causes["run_short"] += 1
            else:
                rows.append((rec["id"], gi, "band_tall",
                             None, None, best_env, best_len, 0))
                causes["band_tall"] += 1
    print("%-8s %-3s %-18s %8s %8s %8s %8s %5s" %
          ("panel", "gi", "cause", "errT.pip", "errB.pip",
           "env/abr", "runlen", "#ov"))
    for r in rows:
        pid, gi, cz, et, eb, x, y, nov = r
        if cz == "edge_tol":
            print("%-8s %-3d %-18s %8.1f %8.1f %8.2f %8s %5d" %
                  (pid, gi, cz, et, eb, x, "-", nov))
        else:
            print("%-8s %-3d %-18s %8s %8s %8.2f %8d %5d" %
                  (pid, gi, cz, "-", "-", x, y, nov))
    print("\ncauses:", dict(causes), "n =", len(rows))


if __name__ == "__main__":
    main()
