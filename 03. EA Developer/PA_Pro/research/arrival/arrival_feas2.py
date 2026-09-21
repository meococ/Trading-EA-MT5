"""arrival_feas2 — R02-D pivot feasibility, OUTCOME-BLIND.

E1 (strength): per (symbol, generator), among ARMED-overlap treated
events at m=0.5, arms = TOP vs BOTTOM zone_S tercile (bounds pooled per
cell, computed pre-outcome). Reports arm counts, propensity overlap,
pre/post-weighting max |SMD|, trimmed share, and exact-strata supT as
the robustness view; plus the FRESH-TO-ZONE restricted variant
(retained as history) and the RESIDUAL-strength contrast (R02-E/G/H —
the claim-bearing E1 estimand).

E3 (recency head-on, R02-H): same treated set, arms = RECENT
(zone_since_touch bottom tercile) vs STALE (top tercile); propensity
on E3_FEATURES — no recency variables, they are the treatment.

E2 (cross-generator): per (symbol, unordered pair {g,h}), events on the
FINER grid (smaller u_atr — declared rule); arm g = armed_g overlap AND
no live_h overlap at t-1; arm h = mirror; x = rest. Same balance
report. Arm A (y=1) = the pair's alphabetically-first generator
(deterministic; sign convention only).

    python -B arrival_feas2.py EURUSD [GBPUSD ...] [--pairs 0] [--e1 0]
        [--e3 0]

One JSON row per cell on stdout.  Computes no outcome column.
"""

import itertools
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import arrival_common as ac          # noqa: E402
import arrival_contrast as cc        # noqa: E402
import arrival_estimate as ae        # noqa: E402

W_SCALE = 0.75
GENS = ("line1_cluster", "fractal_h1", "kde_swing",
        "profile_va", "sd_base", "ref_levels")


def _grids_events(bars, ctx, segs, u_atr):
    o = np.asarray(bars["o"], dtype=np.float64)
    grids = []
    for di, (d0, _d1) in enumerate(segs):
        A = ctx.a(d0)
        bands, w_p = ac.build_day_grid(float(o[d0]), A, u_atr, W_SCALE)
        grids.append((bands, w_p, di, float(o[d0]), A) if bands
                     else None)
    return ac.arrival_events(bars, ctx, grids)


def run_symbol(symbol, do_e1=True, do_pairs=True, do_e3=True):
    from data_helpers import load_ctx
    import registry
    from phys_source import GenSource

    ctx = load_ctx(symbol, max_bars=None)
    bars = ctx.bars
    segs = ac.day_segments(bars)
    srcs, us, evs, arms = {}, {}, {}, {}
    for g in GENS:
        srcs[g] = GenSource(g, registry.get(g), ctx).run()
        us[g] = ac.armed_width_atr(srcs[g], step=288)[0]
        evs[g], _cnt = _grids_events(bars, ctx, segs, us[g])
        a, _d = ac.tag_arms(evs[g], srcs[g], margins=(0.5,), bars=bars)
        arms[g] = a[0.5]
        cc.attach_touches(evs[g], srcs[g])

    if do_e1:
        for g in GENS:
            ev, tr = evs[g], arms[g]["treated"]
            bounds = ae.tercile_bounds(ev, tr)
            e1 = cc.e1_arms(ev, tr, bounds)
            rep = cc.balance_report(ev, e1["top"], e1["bot"])
            rec = (cc.recency_report(ev, e1["top"], e1["bot"], rep)
                   if not rep.get("skipped") else {"skipped": True})
            rep = {k: v for k, v in rep.items() if not k.startswith("_")}
            sup = ac.common_support(ev, e1["top"], e1["bot"])
            ftop = [i for i in e1["top"] if ev[i].get("zone_fresh")]
            fbot = [i for i in e1["bot"] if ev[i].get("zone_fresh")]
            rep_f = (cc.balance_report(ev, ftop, fbot)
                     if len(ftop) >= 50 and len(fbot) >= 50
                     else {"skipped": True, "n_a": len(ftop),
                           "n_b": len(fbot)})
            rep_f = {k: v for k, v in rep_f.items()
                     if not k.startswith("_")}
            resid, rdiag = cc.resid_strength(ev, tr, return_diag=True)
            rb = (float(np.quantile(list(resid.values()), 1.0 / 3.0)),
                  float(np.quantile(list(resid.values()), 2.0 / 3.0))
                  ) if resid else None
            ra = cc.resid_arms(resid, tr, rb) if rb else None
            rep_r = (cc.balance_report(ev, ra["top"], ra["bot"])
                     if ra else {"skipped": True})
            rec_r = (cc.recency_report(ev, ra["top"], ra["bot"], rep_r)
                     if ra and not rep_r.get("skipped")
                     else {"skipped": True})
            rep_r = {k: v for k, v in rep_r.items()
                     if not k.startswith("_")}
            print("JSON " + json.dumps(
                {"symbol": symbol, "experiment": "E1", "generator": g,
                 "u_atr": us[g], "n_events": len(ev), "n_treated": len(tr),
                 "tercile_bounds": bounds,
                 "n_top": len(e1["top"]), "n_mid": len(e1["mid"]),
                 "n_bot": len(e1["bot"]),
                 "balance": rep, "supT_exact": sup["support_T"],
                 "recency": rec,
                 "fresh": {"n_top": len(ftop), "n_bot": len(fbot),
                           "balance": rep_f},
                 "resid": {"bounds": rb, "r2": rdiag["r2"],
                           "resid_var_share": rdiag["resid_var_share"],
                           "n_top": len(ra["top"]) if ra else 0,
                           "n_bot": len(ra["bot"]) if ra else 0,
                           "balance": rep_r, "recency": rec_r}},
                default=float), flush=True)

    if do_e3:
        for g in GENS:
            ev, tr = evs[g], arms[g]["treated"]
            zst = np.asarray([ev[i]["zone_since_touch"] for i in tr
                              if ev[i].get("zone_since_touch")
                              is not None], dtype=np.float64)
            e3b = (tuple(float(x) for x in
                         np.quantile(zst, [1.0 / 3.0, 2.0 / 3.0]))
                   if zst.size else None)
            e3 = (cc.e3_arms(ev, tr, e3b) if e3b else
                  {"recent": [], "mid": [], "stale": [],
                   "degenerate": True})
            rep3 = (cc.balance_report(ev, e3["recent"], e3["stale"],
                                      feats=cc.E3_FEATURES)
                    if not e3["degenerate"] else
                    {"skipped": True, "degenerate": True,
                     "n_a": len(e3["recent"]),
                     "n_b": len(e3["stale"])})
            rep3 = {k: v for k, v in rep3.items()
                    if not k.startswith("_")}
            st_a, st_b = e3["recent"], e3["stale"]
            cap_s = (float(np.mean([ev[i]["zone_since_touch"]
                                    >= cc.SINCE_CAP for i in st_b]))
                     if st_b else float("nan"))
            zs_a = [ev[i]["zone_S"] for i in st_a
                    if ev[i].get("zone_S") is not None]
            zs_b = [ev[i]["zone_S"] for i in st_b
                    if ev[i].get("zone_S") is not None]
            zs_smd = (float("nan") if not zs_a or not zs_b else
                      float(abs(np.mean(zs_a) - np.mean(zs_b))
                            / np.sqrt(max(0.5 * (np.var(zs_a)
                                                 + np.var(zs_b)),
                                          1e-12))))
            print("JSON " + json.dumps(
                {"symbol": symbol, "experiment": "E3",
                 "generator": g, "u_atr": us[g],
                 "n_treated": len(tr), "tercile_bounds": e3b,
                 "n_recent": len(e3["recent"]),
                 "n_mid": len(e3["mid"]), "n_stale": len(e3["stale"]),
                 "degenerate": e3["degenerate"],
                 "cap_share_stale": cap_s,
                 "zone_s_smd_diag": zs_smd,
                 "balance": rep3},
                default=float), flush=True)

    if do_pairs:
        all_tp = sorted({int(e["bar_idx"]) - 1
                         for g in GENS for e in evs[g]})
        tabs = {g: cc.live_overlap_tables(srcs[g], all_tp)
                for g in GENS}
        for g, h in itertools.combinations(GENS, 2):
            base = g if us[g] <= us[h] else h      # finer grid rule
            other = h if base == g else g
            ev = evs[base]
            tg = cc.tag_pair(ev, srcs[base], srcs[other], bars=bars,
                             live_tab_g=tabs[base],
                             live_tab_h=tabs[other])
            ia, ib = (tg["g"], tg["h"]) if base == g \
                else (tg["h"], tg["g"])
            rep = cc.balance_report(ev, ia, ib)
            rep = {k: v for k, v in rep.items() if not k.startswith("_")}
            sup = ac.common_support(ev, ia, ib)
            print("JSON " + json.dumps(
                {"symbol": symbol, "experiment": "E2",
                 "pair": f"{g}|{h}", "grid": base,
                 "n_events": len(ev),
                 "n_a": len(ia), "n_b": len(ib), "n_x": len(tg["x"]),
                 "balance": rep, "supT_exact": sup["support_T"]},
                default=float), flush=True)


if __name__ == "__main__":
    argv = sys.argv[1:]
    do_e1 = do_p = do_e3 = True
    syms = []
    i = 0
    while i < len(argv):
        if argv[i] in ("--e1", "--pairs", "--e3"):
            if argv[i] == "--e1":
                do_e1 = argv[i + 1] != "0"
            elif argv[i] == "--e3":
                do_e3 = argv[i + 1] != "0"
            else:
                do_p = argv[i + 1] != "0"
            i += 2
        else:
            syms.append(argv[i])
            i += 1
    for sym in syms:
        run_symbol(sym, do_e1=do_e1, do_pairs=do_p, do_e3=do_e3)
