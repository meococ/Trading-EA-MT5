"""sf02_autopsy_run.py — executes AUTOPSY_PLAN.md (T000229).

Holds one pa_slots slot.  Writes:
  rounds/SF02/A1_drag.json     — referee (pa_eval) drag curve
  rounds/SF02/A2_mfemae.json   — DESCRIPTIVE exit-free edge
  rounds/SF02/A3_salience.json — DESCRIPTIVE perception audit
  rounds/SF02/A4_slices.json   — DESCRIPTIVE context slices
"""

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
PA_PRO = os.path.dirname(HERE)
for _p in (HERE, LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pa_fill      # noqa: E402
import pa_metrics   # noqa: E402
import pa_slots     # noqa: E402
import sf_autopsy as A   # noqa: E402

OUT = os.path.join(PA_PRO, "rounds", "SF02")


def _t():
    return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime())


def main():
    pa_slots.acquire(note="sf02-autopsy", timeout=0)
    print(_t(), "autopsy start", flush=True)

    # ---- regenerate thick-cell entries + matched randoms -----------
    entries, rnd = {}, {}
    for fam in A.THICK:
        entries[fam] = A.thick_entries(fam)
        rnd[fam] = A.randoms_for(entries[fam])
        tot = sum(len(v) for v in entries[fam].values())
        print(_t(), fam, "entries:", tot, flush=True)

    # ---- A1 (referee path) -----------------------------------------
    a1_path = os.path.join(OUT, "A1_drag.json")
    if os.path.exists(a1_path):
        print(_t(), "A1 exists, skip", flush=True)
    else:
        print(_t(), "A1 drag curve ...", flush=True)
        A.a1_run(a1_path)

    # ---- referee trade lists per thick cell (x1) --------------------
    trades, rtrades = {}, {}
    for fam, prm in A.THICK.items():
        sp = A.cell_spec(fam, prm)
        csp = pa_fill.resolve_spec(sp)
        trades[fam], rtrades[fam] = {}, {}
        for sym in A.SYMBOLS:
            ctx = A.fctx(sym, sp)
            trades[fam][sym] = pa_fill.simulate(csp, ctx,
                                                entries[fam][sym], "x1")
            rtrades[fam][sym] = pa_fill.simulate(csp, ctx,
                                                 rnd[fam][sym], "x1")
        print(_t(), fam, "sim done", flush=True)

    # ---- A2 exit-free edge ------------------------------------------
    a2_path = os.path.join(OUT, "A2_mfemae.json")
    if os.path.exists(a2_path):
        print(_t(), "A2 exists, skip", flush=True)
    else:
        print(_t(), "A2 MFE/MAE ...", flush=True)
        a2 = A.a2_run(entries, rnd)
        json.dump(a2, open(a2_path, "w"), indent=1)

    # ---- A3 salience -------------------------------------------------
    print(_t(), "A3 salience ...", flush=True)
    a3 = {"density": {}, "rank": {}, "terciles": {}}
    for gen in ("line1_cluster", "sd_base"):
        dens1b, dens2b = [], []
        for sym in A.SYMBOLS:
            D = A.cache(sym, gen)
            idx = np.arange(int(D["first_live_idx"]), len(D["t"]), 250)
            for t in idx:
                a1v = float(D["s_atr_h1"][t])
                if not (a1v == a1v and a1v > 0):
                    continue
                c = float(D["c"][t])
                k1 = k2 = 0
                for z in A.sf_ctx.zones_at(D, t):
                    if not z.get("armed"):
                        continue
                    d_edge = min(abs(z["lo"] - c), abs(z["hi"] - c))
                    if z["lo"] <= c <= z["hi"]:
                        d_edge = 0.0
                    k1 += d_edge <= a1v
                    k2 += d_edge <= 2 * a1v
                dens1b.append(k1); dens2b.append(k2)
        a3["density"][gen] = {
            "armed_within_1xATR_h1": float(np.mean(dens1b)),
            "armed_within_2xATR_h1": float(np.mean(dens2b))}

    for fam, prm in A.THICK.items():
        if "gen" not in prm:
            a3["terciles"][fam] = None
            continue
        sal, keys, rsum = [], [], []
        tr_all, tr_r = [], []
        for sym in A.SYMBOLS:
            D = A.cache(sym, prm["gen"])
            for e in entries[fam][sym]:
                z = A.zone_rec_at(D, int(e["sig"]), e.get("zid"))
                a1v = float(D["s_atr_h1"][int(e["sig"])])
                s = A.salience(z, D, int(e["sig"]), a1v)
                sal.append(s); keys.append((sym, int(e["tag"])))
            tr_all += [(sym, t) for t in trades[fam][sym]
                       if t.get("r") is not None]
            tr_r += [(sym, t) for t in rtrades[fam][sym]
                     if t.get("r") is not None]
        sal = np.asarray(sal)
        ok = np.isfinite(sal)
        t1, t2 = np.nanpercentile(sal, [33.33, 66.67])
        bins = {"lo": [], "mid": [], "hi": []}
        for (sym, tag), s in zip(keys, sal):
            b = "lo" if s <= t1 else ("mid" if s <= t2 else "hi")
            bins[b].append((sym, tag))
        row = {}
        for b, kk in bins.items():
            ss = set(kk)
            tr = [t for (sym, t) in tr_all if (sym, t["tag"]) in ss]
            rr = [t for (sym, t) in tr_r if (sym, t["tag"]) in ss]
            rs = np.array([t["r"] for t in tr]) if tr else np.array([])
            rr_ = np.array([t["r"] for t in rr]) if rr else np.array([])
            wr_s = float((rs > 0).mean()) if len(rs) else np.nan
            wr_r = float((rr_ > 0).mean()) if len(rr_) else np.nan
            lift = None
            if len(rs) and len(rr_):
                d, lo, hi = pa_metrics.newcombe_diff(
                    round(wr_s * len(rs)), len(rs),
                    round(wr_r * len(rr_)), len(rr_))
                lift = [round(d * 100, 2), round(lo * 100, 2),
                        round(hi * 100, 2)]
            row[b] = {"N": len(rs), "exp_R": float(rs.mean()) if len(rs) else None,
                      "PF": float(rs[rs > 0].sum() / -rs[rs < 0].sum())
                      if (rs < 0).any() else None,
                      "lift_pp": lift}
        # rank of triggering zone by strength among armed zones
        ranks = []
        for sym in A.SYMBOLS:
            D = A.cache(sym, prm["gen"])
            for e in entries[fam][sym][:3000]:
                t = int(e["sig"])
                zs = [z for z in A.sf_ctx.zones_at(D, t) if z.get("armed")]
                z = A.zone_rec_at(D, t, e.get("zid"))
                if z is not None and zs:
                    ranks.append(1 + sum(
                        1 for zz in zs
                        if zz["strength"] > z["strength"]))
        a3["rank"][fam] = {"median_rank": float(np.median(ranks))
                           if ranks else None}
        a3["terciles"][fam] = {"edges": [float(t1), float(t2)],
                               "bins": row}
    json.dump(a3, open(os.path.join(OUT, "A3_salience.json"), "w"),
              indent=1)

    # ---- A4 slices ----------------------------------------------------
    print(_t(), "A4 slices ...", flush=True)
    a4 = {}
    for fam, prm in A.THICK.items():
        feats = {}
        for sym in A.SYMBOLS:
            D = A.cache(sym, prm.get("gen", "line1_cluster"))
            for e in entries[fam][sym]:
                z = (A.zone_rec_at(D, int(e["sig"]), e.get("zid"))
                     if "gen" in prm else None)
                feats[(sym, int(e["tag"]))] = A.trade_slices(
                    D, e, z, prm["S_pips"])
        # ATR_H1 tercile edges per symbol from DESIGN distribution
        atr_edges = {}
        for sym in A.SYMBOLS:
            D = A.cache(sym, prm.get("gen", "line1_cluster"))
            live = ~np.asarray(D["warmup"], bool)
            a = np.asarray(D["s_atr_h1"])[live]
            atr_edges[sym] = np.nanpercentile(a, [33.33, 66.67])
        slices = {"tr_h1": {}, "tr_h4": {}, "h4_pos": {},
                  "atr_regime": {}, "room_R": {}, "chase": {}}
        tr_all = [(sym, t) for sym in A.SYMBOLS for t in trades[fam][sym]
                  if t.get("r") is not None]
        tr_r = [(sym, t) for sym in A.SYMBOLS for t in rtrades[fam][sym]
                if t.get("r") is not None]

        def _bin_stats(keyset):
            ss = set(keyset)
            rs = np.array([t["r"] for (s, t) in tr_all
                           if (s, t["tag"]) in ss])
            rr = np.array([t["r"] for (s, t) in tr_r
                           if (s, t["tag"]) in ss])
            out = {"N": int(len(rs)),
                   "exp_R": float(rs.mean()) if len(rs) else None,
                   "PF": float(rs[rs > 0].sum() / -rs[rs < 0].sum())
                   if (rs < 0).any() and (rs > 0).any() else None}
            if len(rs) and len(rr):
                w1 = float((rs > 0).mean()); w2 = float((rr > 0).mean())
                d, lo, hi = pa_metrics.newcombe_diff(
                    round(w1 * len(rs)), len(rs),
                    round(w2 * len(rr)), len(rr))
                out["lift_pp"] = [round(d * 100, 2),
                                  round(lo * 100, 2), round(hi * 100, 2)]
            else:
                out["lift_pp"] = None
            return out

        for name in ("tr_h1", "tr_h4"):
            for b in ("aligned", "flat", "counter"):
                kk = [k for k, f in feats.items() if f[name] == b]
                slices[name][b] = _bin_stats(kk)
        for b, lo_, hi_ in (("discount", -1, 1 / 3), ("mid", 1 / 3, 2 / 3),
                            ("premium", 2 / 3, 2)):
            kk = [k for k, f in feats.items()
                  if lo_ <= f["h4_pos"] < hi_]
            slices["h4_pos"][b] = _bin_stats(kk)
        for b, fi in (("low", lambda a, e: a <= e[0]),
                      ("mid", lambda a, e: e[0] < a <= e[1]),
                      ("high", lambda a, e: a > e[1])):
            kk = [k for k, f in feats.items()
                  if np.isfinite(f["atr_h1"])
                  and fi(f["atr_h1"], atr_edges[k[0]])]
            slices["atr_regime"][b] = _bin_stats(kk)
        for b, fi in (("lt1R", lambda r: r < 1.0),
                      ("1to2R", lambda r: 1.0 <= r < 2.0),
                      ("ge2R", lambda r: r >= 2.0)):
            kk = [k for k, f in feats.items()
                  if np.isfinite(f["room_R"]) and fi(f["room_R"])]
            slices["room_R"][b] = _bin_stats(kk)
        kk_none = [k for k, f in feats.items()
                   if not np.isfinite(f["room_R"])]
        slices["room_R"]["none"] = _bin_stats(kk_none)
        ch = np.array([f["chase"] for f in feats.values()])
        if np.isfinite(ch).any():
            c1, c2 = np.nanpercentile(ch, [33.33, 66.67])
            for b, fi in (("near", lambda x: x <= c1),
                          ("mid", lambda x: c1 < x <= c2),
                          ("far", lambda x: x > c2)):
                kk = [k for k, f in feats.items()
                      if np.isfinite(f["chase"]) and fi(f["chase"])]
                slices["chase"][b] = _bin_stats(kk)
            slices["chase"]["edges_atr_m5"] = [float(c1), float(c2)]
        a4[fam] = slices
        print(_t(), fam, "slices done", flush=True)
    json.dump(a4, open(os.path.join(OUT, "A4_slices.json"), "w"),
              indent=1)
    print(_t(), "autopsy done", flush=True)


if __name__ == "__main__":
    main()
