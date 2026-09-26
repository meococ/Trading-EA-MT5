"""audit_lines — L1 yardstick audit for golden PATTERN_LINE.

Measures each scorable golden line against ITS OWN day's bars only
(book text parse for side; never engine output).  Per line:

  end0_res / end1_res : |endpoint - nearest defended-side bar extreme|
                        within +/-2 bars (pips)
  touches_<tol>       : wick touches of the defended side within tol
  closes_beyond       : closes on the wrong side by >1.5p (whole span)
  closes_beyond_head  : same over the first 80% of the span
  wick_overshoot      : max defended-side violation beyond line (pips)
  slope               : pips/bar, pips/hr, ABR/hr
  span_min            : t1 - t0

Defended side: textfeat side_cue on the clause ('under'->lows,
'over'->highs); falls back to dir heuristic (up->under, down->over)
and is FLAGGED when the two disagree.

Output: linelab/audit_lines.json + renders into linelab/audit_png/.
"""

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_PERC, "golden"))
sys.path.insert(0, _HERE)

import bars_cache  # noqa: E402
import textfeat  # noqa: E402
import overlay  # noqa: E402

TOUCH_TOL = 1.5
OUT_JSON = os.path.join(_HERE, "audit_lines.json")
OUT_PNG = os.path.join(_HERE, "audit_png")


def _hhmm(v):
    if v is None:
        return None
    if isinstance(v, str):
        h, m = v.split(":")[:2]
        return int(h) * 60 + int(m)
    return int(v)


def _bar_idx(m, tmin):
    """Index of first bar with cet_min >= tmin (eval convention)."""
    j = int(np.searchsorted(m, tmin))
    return min(j, len(m) - 1)


def _nearest_idx(m, tmin):
    j = int(np.argmin(np.abs(m - tmin)))
    return j


def audit_line(o, day, day_abr):
    """One golden PATTERN_LINE vs bars.  Returns metric dict."""
    t0, t1 = _hhmm(o.get("t0")), _hhmm(o.get("t1"))
    p0, p1 = o.get("price0"), o.get("price1")
    out = {"t0": t0, "t1": t1}
    if t0 is None or t1 is None or t1 <= t0:
        out["scorable"] = False
        out["why"] = "no_span"
        return out
    if p0 is None or p1 is None:
        out["scorable"] = False
        out["why"] = "no_endpoints"
        return out
    p0p, p1p = p0 * 1e4, p1 * 1e4
    m, lo, hi, cl = day["m"], day["l"], day["h"], day["c"]
    j0, j1 = _bar_idx(m, t0), _bar_idx(m, t1)

    f = textfeat.parse(o.get("clause") or "", "PATTERN_LINE")
    side_txt = f["side"]                       # 'under' | 'over' | None
    d = o.get("dir")                           # 'up' | 'down' | None
    side_dir = {"up": "under", "down": "over"}.get(d)
    side = side_txt or side_dir
    ext = lo if side == "under" else hi        # defended extreme series
    # violation = defended side breached: under -> low/close BELOW line
    sgn = 1.0 if side == "under" else -1.0     # violation = sgn*(line-ext)

    def line_at(tm):
        return p0p + (p1p - p0p) * (tm - t0) / (t1 - t0)

    # endpoint residuals: nearest defended-side extreme within +/-2 bars
    def end_res(tm, p):
        jc = _nearest_idx(m, tm)
        ks = range(max(0, jc - 2), min(len(m), jc + 3))
        return min(abs(ext[k] - p) for k in ks), ks

    r0, ks0 = end_res(t0, p0p)
    r1, ks1 = end_res(t1, p1p)

    js = np.arange(j0, j1 + 1)
    lv = np.array([line_at(int(m[j])) for j in js])
    dev = sgn * (lv - ext[js])         # >0: wick beyond defended side
    devc = sgn * (lv - cl[js])         # >0: close beyond defended side
    span_n = max(1, len(js))
    head = int(np.ceil(span_n * 0.8))
    pre60 = int(np.ceil(span_n * 0.6))
    n_beyond = int(np.sum(dev > TOUCH_TOL))
    n_beyond_c = int(np.sum(devc > TOUCH_TOL))
    n_beyond_c_head = int(np.sum(devc[:head] > TOUCH_TOL))
    touches = {t: int(np.sum(np.abs(ext[js] - lv) <= t))
               for t in (1.0, 1.5, 2.0, 3.0)}
    # hug precision: mean of the 4 smallest |extreme - line| residuals
    # (the line is *built* to pass near its best extremes; the spread of
    # those residuals is the label's effective price noise)
    absd = np.sort(np.abs(ext[js] - lv))
    best4 = float(np.mean(absd[:min(4, len(absd))]))
    # named-anchor fidelity: line value at each text-named bar vs that
    # bar's own extreme (repair contract: <=2 p when pinned)
    anch_res = []
    for (tm, kind) in (f.get("anchors") or []):
        for k in ([kind] if kind in ("low", "high")
                  else (["low"] if side == "under" else
                        ["high"] if side == "over" else
                        ["low", "high"])):
            arr = lo if k == "low" else hi
            ja = _nearest_idx(m, tm)
            ks = range(max(0, ja - 2), min(len(m), ja + 3))
            if not list(ks):
                continue
            ex = (min if k == "low" else max)(arr[q] for q in ks)
            anch_res.append(abs(ex - line_at(tm)))
            break
    anch_res_max = max(anch_res) if anch_res else None
    # worst close-through before the last 40% of span (pre-break zone)
    pre60_viol = float(np.max(devc[:pre60])) if pre60 else 0.0

    a0 = day_abr[j0]
    slope_ppb = (p1p - p0p) / (t1 - t0) * 5.0
    slope_pph = slope_ppb * 12.0
    out.update({
        "scorable": True,
        "span_min": t1 - t0, "n_bars": int(span_n),
        "price0": round(p0p, 2), "price1": round(p1p, 2),
        "slope_ppb": round(slope_ppb, 4),
        "slope_pph": round(slope_pph, 2),
        "slope_abr_hr": round(slope_pph / a0, 3) if a0 > 0 else None,
        "abr_at_t0": round(float(a0), 2),
        "end0_res": round(float(r0), 2), "end1_res": round(float(r1), 2),
        "touches": touches,
        "wick_overshoot": round(float(np.max(dev)), 2),
        "closes_beyond": n_beyond_c,
        "closes_beyond_head": n_beyond_c_head,
        "wicks_beyond": n_beyond,
        "hug4_dev": round(best4, 2),
        "anchor_res": (round(anch_res_max, 2)
                       if anch_res_max is not None else None),
        "n_anchors": len(anch_res),
        "pre60_viol": round(pre60_viol, 2),
        "side_text": side_txt, "side_dir": side_dir, "side": side,
        "side_mismatch": bool(side_txt and side_dir
                              and side_txt != side_dir),
        "broken_flag": bool(f["broken"]),
        "slope_sign_ok": (d is None or
                          (d == "up") == (slope_ppb > 0.005) or
                          abs(slope_ppb) <= 0.005),
        "anchor_mins": f.get("anchors"),
    })
    return out


def main():
    recs = bars_cache.tune_records()
    days = bars_cache.days()
    rows = []
    for rec in recs:
        day = days.get(rec["date"])
        if day is None:
            continue
        da = bars_cache.abr(day)
        for k, o in enumerate(rec.get("objects", [])):
            if o.get("spec_type") != "PATTERN_LINE":
                continue
            r = audit_line(o, day, da)
            r.update({"panel": rec["id"], "obj": k,
                      "date": rec["date"],
                      "status": o.get("status"),
                      "repair": o.get("repair_method") or "none",
                      "prec": o.get("prec"),
                      "dir": o.get("dir"),
                      "clause": (o.get("clause") or
                                 o.get("raw_note") or "")})
            rows.append(r)
    with open(OUT_JSON, "w", encoding="utf8") as f:
        json.dump(rows, f, indent=1)

    # ---- render stratified sample: 10 per big stratum, seed fixed ---
    rng = np.random.RandomState(20260921)
    os.makedirs(OUT_PNG, exist_ok=True)
    scor = [r for r in rows if r.get("scorable")]
    for meth in ("constrained_fit", "text_anchor_bars"):
        pool = [r for r in scor if r["repair"] == meth]
        pick = rng.choice(len(pool), size=min(10, len(pool)),
                          replace=False)
        for i in pick:
            r = pool[int(i)]
            rec = next(x for x in recs if x["id"] == r["panel"])
            rec = dict(rec, x0=rec["window"]["x0"],
                       x1=rec["window"]["x1"])
            day = days[rec["date"]]
            bars = {"t": day["t"], "o": day["o_abs"], "h": day["h_abs"],
                    "l": day["l_abs"], "c": day["c_abs"]}
            path = os.path.join(
                OUT_PNG, "%s_o%d_%s.png" % (r["panel"], r["obj"], meth))
            overlay.render_panel(rec, bars, path)
            _thicken(rec, day, r, path)
    print("lines total %d scorable %d -> %s" %
          (len(rows), len(scor), OUT_JSON))


def _thicken(rec, day, r, path):
    """Re-draw the audited line thicker so it stands out."""
    from PIL import Image, ImageDraw
    import numpy as np
    srv = day["m"]
    t_lo = int(rec["x0"]) - 150
    t_hi = int(rec["x1"]) + 40
    vis = (srv >= t_lo) & (srv <= t_hi)
    if not vis.any():
        return
    hh = day["h_abs"][vis]
    ll = day["l_abs"][vis]
    p_lo, p_hi = float(ll.min()) - 8e-4, float(hh.max()) + 8e-4
    vm = overlay.VMap(t_lo, t_hi, p_lo, p_hi)
    im = Image.open(path).convert("L")
    dr = ImageDraw.Draw(im)
    x0, x1 = vm.x(r["t0"]), vm.x(r["t1"])
    dr.line([(x0, vm.y(r["price0"] / 1e4)),
             (x1, vm.y(r["price1"] / 1e4))], fill=90, width=3)
    dr.text((x0 + 4, vm.y(r["price0"] / 1e4) - 14),
            "AUDIT o%d" % r["obj"], fill=0)
    im.save(path)


if __name__ == "__main__":
    main()
