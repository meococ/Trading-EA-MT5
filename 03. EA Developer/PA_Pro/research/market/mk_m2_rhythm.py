"""M2 — intraday rhythm (descriptive, no forward statistics).

Per CET half-hour and per weekday: ABR50 and bar-range distributions.
Asian range (00:00-08:00 CET) height distribution per day.
Volatility regime shift at EU open (08:00 CET) and US data (14:30-16:00).
Spike bar (>3x ABR) frequency by time of day.

Feeds the spec's session boxes, news windows and chop filters.
"""

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import mk_common as K  # noqa: E402


def rhythm_symbol(sym):
    d = K.load_symbol(sym)
    m5 = d["m5"]
    h = np.asarray(m5["h"])
    l = np.asarray(m5["l"])
    rng = h - l
    abr = K.abr_series(m5)
    cet = K.cet_minutes(m5)
    dow = np.asarray(m5["dow"])
    warm = np.asarray(m5["warmup"], dtype=bool)
    pip = float(m5["pip"])
    year = K.server_year(m5)
    live = (~warm) & np.isfinite(abr)
    hh = (cet // 30) % 48                      # CET half-hour bucket 0..47

    # --- half-hour table -------------------------------------------------
    tab = []
    for b in range(48):
        m = live & (hh == b)
        if m.sum() < 10:
            continue
        r = rng[m] / pip
        a = abr[m] / pip
        tab.append({
            "cet_min": int(b * 30),
            "cet": f"{b * 30 // 60:02d}:{(b * 30) % 60:02d}",
            "n": int(m.sum()),
            "range_med_pips": float(np.median(r)),
            "range_p90_pips": float(np.percentile(r, 90)),
            "abr_med_pips": float(np.median(a)),
            "spike_freq": float((rng[m] > 3.0 * abr[m]).mean()),
        })

    # --- weekday table ----------------------------------------------------
    wk = []
    for w in range(5):
        m = live & (dow == w)
        r = rng[m] / pip
        wk.append({"dow": w, "n": int(m.sum()),
                   "range_med_pips": float(np.median(r)),
                   "range_p90_pips": float(np.percentile(r, 90)),
                   "abr_med_pips": float(np.median(abr[m] / pip))})

    # --- Asia range height (00:00-08:00 CET = cet_min in [0,480)) ----------
    day = K.day_id(m5)
    asia_mask = live & (cet <= 480) & (cet > 0)   # Asia convention as M3
    asia = {}
    for dy in np.unique(day[asia_mask]):
        m = asia_mask & (day == dy)
        if m.sum() < 30:
            continue
        hi = float(h[m].max())
        lo = float(l[m].min())
        abr_day = float(np.nanmedian(abr[m]))
        asia[dy] = {"h_pips": (hi - lo) / pip, "abr": abr_day / pip,
                    "year": int(year[int(np.flatnonzero(day == dy)[0])])}
    hv = np.array([v["h_pips"] for v in asia.values()])
    ha = np.array([v["h_pips"] / v["abr"] for v in asia.values()])
    asia_out = {
        "n_days": int(len(hv)),
        "height_pips": {q: float(np.percentile(hv, q))
                        for q in (10, 25, 50, 75, 90)},
        "height_abr": {q: float(np.percentile(ha, q))
                       for q in (10, 25, 50, 75, 90)},
        "share_le_10pips": float((hv <= 10).mean()),
        "share_le_15pips": float((hv <= 15).mean()),
        "share_gt_27pips": float((hv > 27).mean()),
    }
    # per-year Asia median height
    per_year = {}
    for v in asia.values():
        per_year.setdefault(v["year"], []).append(v["h_pips"])
    asia_out["per_year_median"] = {y: float(np.median(v))
                                   for y, v in sorted(per_year.items())}

    # --- regime shift: bar range ratio around session marks ---------------
    def ratio_at(cet_mark, before_min=60, after_min=60):
        pre = live & (cet >= cet_mark - before_min) & (cet < cet_mark)
        post = live & (cet >= cet_mark) & (cet < cet_mark + after_min)
        if pre.sum() < 50 or post.sum() < 50:
            return None
        return float(np.median(rng[post]) / np.median(rng[pre]))

    regime = {
        "eu_open_08": ratio_at(480),
        "us_data_1430": ratio_at(870),
        "london_fix_1600": ratio_at(960),
        "asia_open_00": ratio_at(0),
        "eu_close_1700": ratio_at(1020),
    }

    # --- spike bars (>3x ABR) by CET hour ----------------------------------
    spike_hour = []
    spike = live & (rng > 3.0 * abr)
    for hr in range(24):
        m = live & (cet >= hr * 60) & (cet < hr * 60 + 60)
        if m.sum() < 10:
            continue
        spike_hour.append({"cet_hour": hr, "n": int(m.sum()),
                           "freq": float(spike[m].mean())})
    return {"symbol": sym, "pip": pip, "halfhour": tab, "weekday": wk,
            "asia": asia_out, "regime_shift": regime, "spike_hour": spike_hour,
            "n_bars": int(live.sum())}


def main():
    out = {}
    with K.pa_slots.slot("dr-market M2 rhythm", timeout=120):
        for sym in K.CORE:
            print(f"[M2] {sym} ...", flush=True)
            out[sym] = rhythm_symbol(sym)
    K.write_json("rhythm.json", out)

    # ---- markdown --------------------------------------------------------
    L = ["# RHYTHM — intraday rhythm (DESIGN 2016-2021, M5)", "",
         "Descriptive only; no forward statistics; no FDR.", "",
         "## ABR50 and bar range by CET half-hour (pooled read)", "",
         "Per-symbol tables are in `out/rhythm.json`. The pooled shape:", ""]
    # pooled half-hour medians across symbols (EURUSD units for pips)
    hh_all = {}
    for sym in K.CORE:
        for row in out[sym]["halfhour"]:
            hh_all.setdefault(row["cet_min"], []).append(row)
    L += ["| CET | ABR med (pips, per sym) | range p90 (pips) | spike f |",
          "|---|---|---|---|"]
    for m in sorted(hh_all):
        rows = hh_all[m]
        amed = ", ".join(f"{r['abr_med_pips']:.1f}" for r in rows)
        r90 = ", ".join(f"{r['range_p90_pips']:.1f}" for r in rows)
        sp = ", ".join(f"{100*r['spike_freq']:.1f}%" for r in rows)
        L.append(f"| {m//60:02d}:{m%60:02d} | {amed} | {r90} | {sp} |")
    L += ["", "## Asia range height (00:00-08:00 CET)", "",
          "| symbol | n days | p25 | median | p75 | p90 | <=10p | <=15p | >27p |",
          "|---|---|---|---|---|---|---|---|---|"]
    for sym in K.CORE:
        a = out[sym]["asia"]
        hp = a["height_pips"]
        L.append(f"| {sym} | {a['n_days']} | {hp[25]:.1f} | "
                 f"{hp[50]:.1f} | {hp[75]:.1f} | {hp[90]:.1f} | "
                 f"{a['share_le_10pips']:.2f} | {a['share_le_15pips']:.2f} | "
                 f"{a['share_gt_27pips']:.2f} |")
    L += ["", "Asia height in ABR units (median): " +
          ", ".join(f"{s}={out[s]['asia']['height_abr'][50]:.2f}"
                    for s in K.CORE),
          "", "Asia median height by year (pips):",
          ""]
    for sym in K.CORE:
        py = out[sym]["asia"]["per_year_median"]
        L.append(f"- {sym}: " + ", ".join(f"{y}:{v:.1f}" for y, v in py.items()))
    L += ["", "## Regime shifts (median range after / before, 60 min each side)",
          "", "| mark (CET) | " + " | ".join(K.CORE) + " |", "|---|---|---|---|---|"]
    marks = [("asia_open_00", "Asia open 00:00"), ("eu_open_08", "EU open 08:00"),
             ("us_data_1430", "US data 14:30"), ("london_fix_1600", "16:00 fix"),
             ("eu_close_1700", "17:00")]
    for k, name in marks:
        vals = ", ".join("-" if out[s]["regime_shift"][k] is None
                         else f"{out[s]['regime_shift'][k]:.2f}x"
                         for s in K.CORE)
        L.append(f"| {name} | {vals} |")
    L += ["", "## Spike bars (>3x ABR) frequency by CET hour", "",
          "| CET hour | " + " | ".join(K.CORE) + " |", "|---|---|---|---|---|"]
    for hr in range(24):
        vals = []
        for s in K.CORE:
            row = next((r for r in out[s]["spike_hour"]
                        if r["cet_hour"] == hr), None)
            vals.append("-" if row is None else f"{100*row['freq']:.2f}%")
        L.append(f"| {hr:02d} | " + " | ".join(vals) + " |")
    with open(os.path.join(_HERE, "RHYTHM.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("[M2] done -> RHYTHM.md")


if __name__ == "__main__":
    main()
