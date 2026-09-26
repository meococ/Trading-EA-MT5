"""anatomy_levels — V2: how Volman's golden LEVELS are anchored.

For every trusted LEVEL_CARRIED / MINI_LEVEL (V1: scorable minus Tier-A):

  origin      : earliest prior bar whose extreme is within tol of the
                label price (tol = 2.0 p LEVEL, 1.5 p MINI).
  origin_cls  : prior_day | asia | session | theta2 | theta1 |
                box_edge | round_number | other_bar
  age_min     : t0 - origin bar minute
  touches     : prior bar extremes within tol between origin and t0
  dist_tau    : |price - close[t0]| in ABR units at golden start
  zone_w      : (max-min) of prior touch extremes inside 2*tol band
  carried     : sibling sub-panel same day holds a level within 2 p
  knowable_t  : earliest bar with >=2 cumulative touches -> lead vs t0

Swing stream: engine swings.py (DCStream+SwingBook), same params as
linelab/anatomy.py.  Prior-day H/L: previous cached day (Sun gap -> none).
"""

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_PERC, "golden"))
sys.path.insert(0, _PERC)
sys.path.insert(0, os.path.join(_PERC, "linelab"))

import bars_cache  # noqa: E402
from swings import DCStream, SwingBook  # noqa: E402

IN = os.path.join(_HERE, "audit_levels.json")
OUT = os.path.join(_HERE, "anatomy_levels.json")

K1_ABR, PMIN_ABR, PSTRUCT_ABR, SPIKE_MULT = 0.8, 0.5, 2.5, 2.5
TIER_A = {  # V1 Tier-A suspects
    "9.18c#0", "9.30b#0", "9.38a#1", "9.63a#1", "9.60a#3", "9.65a#0",
    "9.23c#0", "9.26a#2", "9.57b#3", "9.40a#0", "9.50a#1",
}
ASIA_END = 420        # Asia session ~01:00-07:00 CET (Berlin feed)
EU_OPEN = 480         # 08:00 CET rough EU-open boundary


def run_swings(day):
    abr = bars_cache.abr(day)
    dc = DCStream(lambda i: K1_ABR * abr[i],
                  lambda i: (day["h"][i] - day["l"][i])
                  > SPIKE_MULT * abr[i])
    book = SwingBook(PMIN_ABR, PSTRUCT_ABR, abr_fn=lambda i: abr[i])
    pivs = []
    for i in range(len(day["m"])):
        book.update_running(dc.dir, dc.ext_price)
        for p in dc.update(i, day["h"][i], day["l"][i]):
            piv = book.add(p)
            pivs.append({"t_ext": piv.t_ext, "t_conf": piv.t_conf,
                         "price": piv.price, "dir": piv.dir,
                         "struct": book.is_structural(piv)})
    return pivs, abr


def classify_origin(r, day, pday, pivs, tol):
    """Return (origin_idx_in_day_or_None, origin_class, origin_minute)."""
    m, h, l = day["m"], day["h"], day["l"]
    price = r["price"] * 1e4
    j0 = int(np.argmin(np.abs(m - r["t0"])))
    # prior-day H/L test first (origin lives in previous day)
    pdhit = None
    if pday is not None:
        pdh, pdl = float(np.max(pday["h"])), float(np.min(pday["l"]))
        if abs(price - pdh) <= tol:
            pdhit = ("prior_day_high", int(pday["m"][int(np.argmax(pday["h"]))]))
        elif abs(price - pdl) <= tol:
            pdhit = ("prior_day_low", int(pday["m"][int(np.argmin(pday["l"]))]))
    # earliest same-day bar within tol
    ext_h = np.abs(h[:j0] - price) <= tol
    ext_l = np.abs(l[:j0] - price) <= tol
    hits = np.where(ext_h | ext_l)[0]
    if len(hits) == 0:
        if pdhit:
            return None, pdhit[0], pdhit[1], None, True
        return None, "none", None, None, False
    oi = int(hits[0])
    cls = []
    # theta pivots at origin +-1 bar
    for p in pivs:
        if abs(p["t_ext"] - oi) <= 1 and abs(p["price"] - price) <= 2 * tol:
            cls.append("theta2" if p["struct"] else "theta1")
            break
    # congestion edge: >=3 touches in 60 bars ending at origin
    w0 = max(0, oi - 60)
    nt = int(((np.abs(h[w0:oi + 1] - price) <= tol)
              | (np.abs(l[w0:oi + 1] - price) <= tol)).sum())
    if nt >= 3:
        cls.append("box_edge")
    # session / asia extreme: origin bar was running extreme at its bar
    if l[oi] <= np.min(l[:oi + 1]) + 0.01 or h[oi] >= np.max(h[:oi + 1]) - 0.01:
        cls.append("asia" if m[oi] < ASIA_END else "session")
    # round number flags (secondary tag)
    rp = price % 10
    rnd = "round10" if min(rp, 10 - rp) <= 1.0 or abs(rp - 5) <= 1.0 else None
    rp2 = price % 25
    rnd2 = "round25" if min(rp2, 25 - rp2) <= 1.0 else None
    main = cls[0] if cls else (pdhit[0] if pdhit else "other_bar")
    return oi, main, int(m[oi]), rnd or rnd2, bool(pdhit)


def touches_between(day, oi, j0, price, tol):
    h, l = day["h"], day["l"]
    seg_h = np.abs(h[oi + 1:j0] - price) <= tol
    seg_l = np.abs(l[oi + 1:j0] - price) <= tol
    return int((seg_h | seg_l).sum())


def main():
    rows = json.load(open(IN, encoding="utf8"))
    days = bars_cache.days()
    recs = {r["id"]: r for r in bars_cache.tune_records()}
    dates = sorted(days)
    out = []
    for r in rows:
        if not r.get("scorable") or r.get("price") is None:
            continue
        key = "%s#%d" % (r["panel"], r["obj"])
        if key in TIER_A:
            continue
        rec = recs[r["panel"]]
        day = days[rec["date"]]
        di = dates.index(rec["date"])
        pday = days[dates[di - 1]] if di > 0 else None
        pivs, abr = run_swings(day)
        tol = 2.0 if r["type"] == "LEVEL_CARRIED" else 1.5
        price = r["price"] * 1e4
        m = day["m"]
        j0 = int(np.argmin(np.abs(m - r["t0"])))
        oi, ocls, omin, rnd, pd_flag = classify_origin(r, day, pday,
                                                      pivs, tol)
        age = (r["t0"] - omin) if omin is not None else None
        nt = touches_between(day, oi, j0, price, tol) if oi is not None else 0
        # zone width: spread of the extremes that are actually inside
        # the +-2*tol band around price
        hh = day["h"][:j0][np.abs(day["h"][:j0] - price) <= 2 * tol]
        ll = day["l"][:j0][np.abs(day["l"][:j0] - price) <= 2 * tol]
        ex = np.concatenate([hh, ll]) if len(hh) or len(ll) else None
        zw = round(float(ex.max() - ex.min()), 1) if ex is not None else None
        # first knowable: earliest bar with >=2 cumulative touches
        cum = 0
        kt = None
        for k in range(0, j0):
            if abs(day["h"][k] - price) <= tol or abs(day["l"][k] - price) <= tol:
                cum += 1
                if cum >= 2:
                    kt = int(m[k])
                    break
        # carried across sub-panels?
        day_id = r["panel"].rstrip("abc")
        sib = False
        for o in recs.get(r["panel"], {}).get("objects", []):
            pass
        for rid, ro in recs.items():
            if not rid.startswith(day_id) or rid == r["panel"]:
                continue
            for o in ro.get("objects", []):
                if o.get("spec_type") in ("LEVEL_CARRIED", "MINI_LEVEL") \
                        and o.get("price") is not None \
                        and abs(o["price"] - r["price"]) <= 2e-4:
                    sib = True
        dist_tau = abs(price - day["c"][j0]) / abr[j0]
        out.append({"key": key, "type": r["type"], "repair": r["repair"],
                    "cue": r.get("cue"), "price": r["price"],
                    "t0": r["t0"], "t1": r["t1"], "span": r["span_min"],
                    "origin_cls": ocls, "origin_min": omin, "rnd": rnd,
                    "pdh_pdl": pd_flag,
                    "age_min": age, "touches": nt, "zone_w": zw,
                    "dist_tau_abr": round(float(dist_tau), 2),
                    "knowable_t": kt,
                    "knowable_lead": (r["t0"] - kt) if kt else None,
                    "carried": sib,
                    "clause": (r["clause"] or "")[:80]})
    json.dump(out, open(OUT, "w", encoding="utf8"), indent=1)
    from collections import Counter
    for typ in ("LEVEL_CARRIED", "MINI_LEVEL"):
        g = [r for r in out if r["type"] == typ]
        print("== %s n=%d" % (typ, len(g)))
        print(" origin:", Counter(r["origin_cls"] for r in g))
        ages = [r["age_min"] for r in g if r["age_min"] is not None]
        print(" age p25/p50/p90: %s" % [int(np.percentile(ages, q))
                                        for q in (25, 50, 90)])
        print(" age<180:", sum(1 for a in ages if a < 180), "/",
              len(ages))
        print(" touches p50:", np.median([r["touches"] for r in g]))
        print(" dist_tau_abr p50:", np.median([r["dist_tau_abr"] for r in g]))
        print(" zone_w p50:", np.median([r["zone_w"] for r in g
                                         if r["zone_w"] is not None]))
        print(" carried:", sum(r["carried"] for r in g))
        kl = [r["knowable_lead"] for r in g if r["knowable_lead"] is not None]
        print(" knowable lead p50:", np.median(kl) if kl else None)
        print(" rnd:", Counter(r["rnd"] for r in g))
        print(" pdh_pdl price-match:", sum(r["pdh_pdl"] for r in g))


if __name__ == "__main__":
    main()
