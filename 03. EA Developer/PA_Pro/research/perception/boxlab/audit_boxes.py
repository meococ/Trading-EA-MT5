"""audit_boxes — X1 box yardstick audit (BOX-LAB).

Measures every golden BOX label in TUNE v2 against the M5 bars inside its
containment window build_start..build_end (fallbacks t0..t1), per mandate X1:

  * closes outside the band (count, fraction, max depth, at 0 and 1.5p tol)
  * wick pokes beyond each edge (count, depth distribution)
  * touch events per edge at several hug tolerances (bars + event runs)
  * start: t0 vs build_start vs first edge touch
  * height in pips and ABR
  * edge support: nearest defended-side extreme cluster, residual, company
  * break bar vs build_end
  * strata: prec x repair_method x build_start presence

Writes cache/box_audit.jsonl (per-box rows) and prints the aggregate tables
used for BOX_YARDSTICK_AUDIT.md.  Bars via boxlab/bars_cache.py only.
"""
import json
import os
import sys
import collections

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
_EVALC = os.path.join(_PERC, "evalcheck")
for _p in (_HERE, _PERC, _EVALC, os.path.join(_PERC, "golden")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bars_cache as BC            # noqa: E402
import common as C                 # noqa: E402  evalcheck common (read-only)
import eval_v2 as V2               # noqa: E402  official ruler (read-only)
import eval as EV                  # noqa: E402  legacy ruler (read-only)

TUNE_JSONL = os.path.join(_PERC, "golden", "draft", "BOOK2012_TUNE_v2.jsonl")
OUT_JSONL = os.path.join(_HERE, "cache", "box_audit.jsonl")
TOUCH_TOL = 1.5                    # validator's edge_touch convention (pips)


def _edge_clusters(vals, bin_w=1.0):
    """Histogram defended-side extremes into bin_w-pip bins; return list of
    (centroid, count) sorted by centroid."""
    if len(vals) == 0:
        return []
    v = np.asarray(vals, dtype=float)
    bins = np.floor(v / bin_w)
    out = []
    for b in np.unique(bins):
        vv = v[bins == b]
        out.append((float(vv.mean()), int(len(vv))))
    out.sort()
    return out


def _touch_events(mins, side, edge, tol):
    """Count bars and event-runs whose defended extreme hugs the edge.
    side='top' uses highs, 'bot' uses lows.  mins = dict of arrays."""
    ext = mins["h"] if side == "top" else mins["l"]
    touch = np.abs(ext - edge) <= tol
    bars = int(touch.sum())
    ev = 0
    run = False
    for b in touch:
        if b and not run:
            ev += 1
        run = bool(b)
    return bars, ev


def audit_box(o, day, abr, w0, w1):
    """One golden BOX -> metric dict (all prices in pips)."""
    lo = o.get("price_lo"); hi = o.get("price_hi")
    if lo is None or hi is None:
        a, b = o.get("price"), o.get("price2")
        if a is not None and b is not None:
            lo, hi = min(a, b), max(a, b)
    lo_p = lo * 1e4 if lo is not None else None
    hi_p = hi * 1e4 if hi is not None else None

    t0, t1 = o.get("t0"), o.get("t1")
    bs = o.get("build_start") if o.get("build_start") is not None else t0
    be = o.get("build_end") if o.get("build_end") is not None else t1

    row = {"t0": t0, "t1": t1, "bs": bs, "be": be,
           "has_bs": o.get("build_start") is not None,
           "has_be": o.get("build_end") is not None,
           "lo": lo_p, "hi": hi_p,
           "prec": o.get("prec"), "repair": o.get("repair_method") or "none",
           "status": o.get("status"), "fails": o.get("fails") or [],
           "letter": o.get("letter"), "dir": o.get("dir"),
           "pin_lo": o.get("pin_lo"), "pin_hi": o.get("pin_hi")}
    row["height_p"] = (hi_p - lo_p) if (lo_p is not None) else None
    row["span_drawn"] = (t1 - t0) if (t0 is not None and t1 is not None) else None
    row["span_build"] = (be - bs) if (bs is not None and be is not None) else None

    mask = BC.day_slice(day, bs, be)
    n = int(mask.sum())
    row["n_bars"] = n
    jbs = BC.idx_of(day, bs)
    row["abr"] = float(abr[jbs]) if jbs is not None else None
    row["height_abr"] = (row["height_p"] / row["abr"]
                         if row["height_p"] and row["abr"] else None)
    if n == 0 or lo_p is None:
        row["degenerate"] = True
        return row

    mm = {k: day[k][mask] for k in ("m", "o", "h", "l", "c")}
    c, h, l, m = mm["c"], mm["h"], mm["l"], mm["m"]

    # containment: closes beyond the band
    out_c = (c > hi_p) | (c < lo_p)
    out_c_tol = (c > hi_p + TOUCH_TOL) | (c < lo_p - TOUCH_TOL)
    row["closes_out"] = int(out_c.sum())
    row["closes_out_tol"] = int(out_c_tol.sum())
    row["contain_frac"] = float(1.0 - out_c.mean())
    dep = np.maximum(np.maximum(c - hi_p, lo_p - c), 0.0)
    row["max_close_out"] = float(dep.max())

    # wick pokes: extreme beyond edge but close back inside
    poke_t = (h > hi_p) & (c <= hi_p)
    poke_b = (l < lo_p) & (c >= lo_p)
    row["pokes_top"] = int(poke_t.sum())
    row["pokes_bot"] = int(poke_b.sum())
    row["poke_dep_top_max"] = float((h[poke_t] - hi_p).max()) if poke_t.any() else 0.0
    row["poke_dep_bot_max"] = float((lo_p - l[poke_b]).max()) if poke_b.any() else 0.0
    deps = list(h[poke_t] - hi_p) + list(lo_p - l[poke_b])
    row["poke_dep_med"] = float(np.median(deps)) if deps else 0.0
    row["poke_dep_p90"] = float(np.percentile(deps, 90)) if deps else 0.0

    # touches per edge (bars + event runs) at several tolerances
    for tol in (1.0, 1.5, 2.0):
        tb, te = _touch_events(mm, "top", hi_p, tol)
        bb, be_ = _touch_events(mm, "bot", lo_p, tol)
        row[f"t_top_bars_{tol}"] = tb
        row[f"t_top_ev_{tol}"] = te
        row[f"t_bot_bars_{tol}"] = bb
        row[f"t_bot_ev_{tol}"] = be_
    row["touch_scatter_top"] = float(np.std(h[np.abs(h - hi_p) <= 2.0])) \
        if (np.abs(h - hi_p) <= 2.0).any() else None
    row["touch_scatter_bot"] = float(np.std(l[np.abs(l - lo_p) <= 2.0])) \
        if (np.abs(l - lo_p) <= 2.0).any() else None

    # first touch of either edge (within build window)
    tt = (np.abs(h - hi_p) <= TOUCH_TOL) | (np.abs(l - lo_p) <= TOUCH_TOL)
    row["first_touch_min"] = int(m[tt][0]) if tt.any() else None
    # first touch per edge
    ttop = np.abs(h - hi_p) <= TOUCH_TOL
    tbot = np.abs(l - lo_p) <= TOUCH_TOL
    row["first_touch_top"] = int(m[ttop][0]) if ttop.any() else None
    row["first_touch_bot"] = int(m[tbot][0]) if tbot.any() else None

    # start deltas (minutes)
    row["d_t0_bs"] = (t0 - bs) if (t0 is not None and bs is not None) else None
    ft = row["first_touch_min"]
    row["d_ft_bs"] = (ft - bs) if (ft is not None and bs is not None) else None
    row["d_ft_t0"] = (ft - t0) if (ft is not None and t0 is not None) else None

    # break bar: first close outside band after window start, anywhere in day
    after = day["m"] >= bs
    ca, ma = day["c"][after], day["m"][after]
    brk = np.where((ca > hi_p + 1.0) | (ca < lo_p - 1.0))[0]
    row["break_min"] = int(ma[brk[0]]) if len(brk) else None
    row["d_break_be"] = (row["break_min"] - be) if (
        row["break_min"] is not None and be is not None) else None
    row["break_dir"] = ("up" if len(brk) and ca[brk[0]] > hi_p else
                        "down" if len(brk) else None)

    # first touch of either edge in a 60-min lookback before build start
    # (does the edge pre-date the labelled window?)
    pre = (day["m"] >= bs - 60) & (day["m"] < bs) if bs is not None \
        else np.zeros(len(day["m"]), bool)
    if pre.any():
        hp, lp = day["h"][pre], day["l"][pre]
        row["pre_touch_top"] = int((np.abs(hp - hi_p) <= TOUCH_TOL).sum())
        row["pre_touch_bot"] = int((np.abs(lp - lo_p) <= TOUCH_TOL).sum())
    else:
        row["pre_touch_top"] = row["pre_touch_bot"] = 0

    # edge support: defended-side cluster nearest the stated edge
    for side, ext, edge in (("top", h, hi_p), ("bot", l, lo_p)):
        near = ext[np.abs(ext - edge) <= 8.0]
        cl = _edge_clusters(near, 1.0)
        best, bd = None, 1e9
        for cen, cnt in cl:
            d = abs(cen - edge)
            if d < bd:
                best, bd = (cen, cnt), d
        row[f"cl_{side}_cen"] = best[0] if best else None
        row[f"cl_{side}_n"] = best[1] if best else 0
        row[f"cl_{side}_resid"] = bd if best else None
    # where the edge sits vs the window extremes
    row["hi_minus_maxh"] = float(hi_p - h.max())
    row["minl_minus_lo"] = float(l.min() - lo_p)
    row["hi_minus_p95h"] = float(hi_p - np.percentile(h, 95))
    row["p05l_minus_lo"] = float(np.percentile(l, 5) - lo_p)

    # reliability flags — "supported edge" = >=2 hugging bars in window,
    # or >=1 touch bar plus a poke on that side (defence evidence), or
    # touches already visible in the 60-min lookback (edge pre-formed).
    row["flag_contain_ok"] = bool(row["closes_out_tol"] <= max(1, 0.10 * n))
    row["flag_top_ok"] = bool(row["t_top_ev_1.5"] >= 2)
    row["flag_bot_ok"] = bool(row["t_bot_ev_1.5"] >= 2)
    row["flag_top_sup"] = bool(row["t_top_bars_1.5"] >= 2
                               or (row["t_top_bars_1.5"] >= 1
                                   and row["pokes_top"] >= 1)
                               or row["pre_touch_top"] >= 1)
    row["flag_bot_sup"] = bool(row["t_bot_bars_1.5"] >= 2
                               or (row["t_bot_bars_1.5"] >= 1
                                   and row["pokes_bot"] >= 1)
                               or row["pre_touch_bot"] >= 1)
    row["flag_geom"] = bool(row["height_p"] and 4.0 <= row["height_p"] <= 80.0
                            and row["span_build"] and row["span_build"] >= 15)
    row["trusted"] = bool(row["flag_contain_ok"] and row["flag_top_sup"]
                          and row["flag_bot_sup"] and row["flag_geom"])
    return row


def main():
    recs = [json.loads(x) for x in open(TUNE_JSONL, encoding="utf8")]
    dates, bars = BC.load_all()
    abrs = {d: BC.abr50(bars[d]["h"], bars[d]["l"], bars[d]["c"])
            for d in dates}

    rows = []
    for rec in recs:
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        day = bars.get(rec["date"])
        if day is None:
            continue
        abr = abrs[rec["date"]]
        for i, o in enumerate(rec.get("objects", [])):
            if o.get("spec_type") != "BOX":
                continue
            r = audit_box(o, day, abr, w0, w1)
            r["panel"] = rec["id"]
            r["idx"] = i
            r["scorable"] = bool(V2.scorable(o, w0, w1))
            r["sigma_p"] = C.prec_sigmas(o)[0]
            rows.append(r)

    os.makedirs(os.path.dirname(OUT_JSONL), exist_ok=True)
    with open(OUT_JSONL, "w", encoding="utf8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    # ---- aggregate ----
    us = [r for r in rows if r["status"] in ("ok", "repaired")
          and r["scorable"] and not r.get("degenerate")]
    print("BOX rows:", len(rows), "| usable+scorable+nondegenerate:", len(us))
    print("build_start present:", sum(r["has_bs"] for r in rows))

    def q(v, name):
        v = np.array([x for x in v if x is not None], dtype=float)
        if not len(v):
            print(f"  {name}: n/a")
            return
        print(f"  {name}: n={len(v)} med={np.median(v):.2f} "
              f"p10={np.percentile(v, 10):.2f} p90={np.percentile(v, 90):.2f}")

    print("\n-- core distributions (usable scorable) --")
    q([r["height_p"] for r in us], "height_p")
    q([r["height_abr"] for r in us], "height_abr")
    q([r["span_drawn"] for r in us], "span_drawn_min")
    q([r["span_build"] for r in us], "span_build_min")
    q([r["closes_out"] for r in us], "closes_out")
    q([r["closes_out_tol"] for r in us], "closes_out_tol1.5")
    q([r["contain_frac"] for r in us], "contain_frac")
    q([r["max_close_out"] for r in us], "max_close_out")
    q([r["pokes_top"] + r["pokes_bot"] for r in us], "pokes_total")
    q([r["poke_dep_med"] for r in us], "poke_dep_med")
    q([r["poke_dep_p90"] for r in us], "poke_dep_p90")
    q([r["t_top_ev_1.5"] for r in us], "touch_ev_top@1.5")
    q([r["t_bot_ev_1.5"] for r in us], "touch_ev_bot@1.5")
    q([r["t_top_bars_1.5"] for r in us], "touch_bars_top@1.5")
    q([r["t_bot_bars_1.5"] for r in us], "touch_bars_bot@1.5")
    q([r["t_top_bars_2.0"] for r in us], "touch_bars_top@2.0")
    q([r["t_bot_bars_2.0"] for r in us], "touch_bars_bot@2.0")
    q([r["pre_touch_top"] for r in us], "pre60_touch_top_bars")
    q([r["pre_touch_bot"] for r in us], "pre60_touch_bot_bars")
    q([r["touch_scatter_top"] for r in us], "touch_scatter_top")
    q([r["touch_scatter_bot"] for r in us], "touch_scatter_bot")
    q([r["d_t0_bs"] for r in us], "t0 - build_start")
    q([r["d_ft_bs"] for r in us], "first_touch - build_start")
    q([r["d_ft_t0"] for r in us], "first_touch - t0")
    q([r["d_break_be"] for r in us], "break_bar - build_end")
    brk = collections.Counter(r["break_dir"] for r in us)
    print("  break_dir:", dict(brk))
    q([r["cl_top_resid"] for r in us], "edge_resid_top")
    q([r["cl_bot_resid"] for r in us], "edge_resid_bot")
    q([r["cl_top_n"] for r in us], "cluster_company_top")
    q([r["cl_bot_n"] for r in us], "cluster_company_bot")
    q([r["hi_minus_maxh"] for r in us], "hi - max_high")
    q([r["minl_minus_lo"] for r in us], "min_low - lo")
    q([r["hi_minus_p95h"] for r in us], "hi - p95_high")
    q([r["p05l_minus_lo"] for r in us], "p05_low - lo")

    print("\n-- strata reliability (contain_ok & edges_ok & geom_ok) --")
    groups = collections.defaultdict(list)
    for r in us:
        groups[("prec", r["prec"])].append(r)
        groups[("repair", r["repair"])].append(r)
        groups[("has_bs", r["has_bs"])].append(r)
        groups[("sigma", r["sigma_p"])].append(r)
    for k in sorted(groups):
        g = groups[k]
        ok = sum(r["trusted"] for r in g)
        print(f"  {k}: n={len(g)} trusted={ok} ({ok/len(g):.2f}) "
              f"contain_ok={np.mean([r['flag_contain_ok'] for r in g]):.2f} "
              f"edges_ok={np.mean([r['flag_top_ok'] and r['flag_bot_ok'] for r in g]):.2f} "
              f"edges_sup={np.mean([r['flag_top_sup'] and r['flag_bot_sup'] for r in g]):.2f}")

    print("\n-- suspects (usable+scorable, not trusted) --")
    for r in us:
        if not r["trusted"]:
            print(f"  {r['panel']}#{r['idx']} bs={r['bs']} be={r['be']} "
                  f"h={r['height_p']:.1f} cout={r['closes_out_tol']} "
                  f"tT={r['t_top_bars_1.5']}/{r['t_top_ev_1.5']} "
                  f"tB={r['t_bot_bars_1.5']}/{r['t_bot_ev_1.5']} "
                  f"prec={r['prec']} rep={r['repair']} fails={r['fails']}")
    n_tr = sum(r["trusted"] for r in us)
    print(f"\ntrusted: {n_tr}/{len(us)}")


if __name__ == "__main__":
    main()
