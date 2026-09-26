"""V1 — LEVEL_CARRIED / MINI_LEVEL yardstick audit.

For every golden level object on TUNE v2:
  price, span [t0,t1], tau = t0 (draw/decision start), repair_method,
  and bars-based sanity:
    - dist of `price` to the nearest prior same-price extreme
      (residual of "is this a real level price");
    - prior touch count within 2p in the 6h before t0 (defended?);
    - in-span price contact (does price ever trade through/touch it);
    - ABR at tau for scale.
Outputs levellab/audit_levels.json + console summary per stratum.

Run:  python -X utf8 audit_levels.py
"""
import collections
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(_HERE), "linelab")
sys.path.insert(0, _LAB)

import bars_cache  # noqa: E402  (linelab helper, read-only import)

TUNE = os.path.join(os.path.dirname(_HERE), "golden", "draft",
                    "BOOK2012_TUNE_v2.jsonl")
OUT = os.path.join(_HERE, "audit_levels.json")


def recs():
    return [json.loads(x) for x in open(TUNE, encoding="utf8")
            if x.strip()]


def local_ext(day, i, k=3):
    """Is bar i a +-k local extremum? Returns 'hi', 'lo', or None."""
    lo = max(0, i - k)
    hi = min(len(day["h"]) - 1, i + k)
    if day["h"][i] >= day["h"][lo:hi + 1].max():
        return "hi"
    if day["l"][i] <= day["l"][lo:hi + 1].min():
        return "lo"
    return None


def main():
    days = bars_cache.days()
    out = []
    for r in recs():
        day = days.get(r["date"])
        for j, o in enumerate(r.get("objects", [])):
            if o.get("spec_type") not in ("LEVEL_CARRIED", "MINI_LEVEL"):
                continue
            row = {"panel": r["id"], "obj": j, "date": r["date"],
                   "type": o["spec_type"],
                   "t0": o.get("t0"), "t1": o.get("t1"),
                   "price": o.get("price"),
                   "repair": o.get("repair_method"),
                   "status": o.get("status"),
                   "prec": o.get("prec"),
                   "approx_t": o.get("approx_time"),
                   "approx_p": o.get("approx_price"),
                   "clause": o.get("clause") or o.get("raw_note")}
            if day is None or o.get("price") is None \
                    or o.get("t0") is None:
                row["scorable"] = False
                out.append(row)
                continue
            m = day["m"]
            i0 = int(np.searchsorted(m, o["t0"]))
            i1 = int(np.searchsorted(m, o["t1"])) \
                if o.get("t1") is not None else i0
            i1 = min(i1, len(m) - 1)
            abr = bars_cache.abr(day)
            px = o["price"] / 1e-4  # pips
            abr0 = float(abr[min(i0, len(abr) - 1)])
            row.update(scorable=True, i0=i0, i1=i1, abr0=round(abr0, 2),
                       span_min=(o.get("t1") or o["t0"]) - o["t0"])
            # nearest prior local extreme (6h lookback = 72 bars)
            lo = max(0, i0 - 72)
            best = None
            for q in range(lo, i0):
                ex = local_ext(day, q)
                if ex == "hi":
                    d = abs(day["h"][q] - px)
                elif ex == "lo":
                    d = abs(day["l"][q] - px)
                else:
                    continue
                if best is None or d < best[0]:
                    best = (d, q, ex)
            if best is not None:
                row["nearest_ext_p"] = round(best[0], 2)
                row["nearest_ext_age_bars"] = i0 - best[1]
                row["nearest_ext_side"] = best[2]
            # nearest ANY bar extreme (no locality requirement)
            dd = min(np.abs(day["h"][lo:i0] - px).min() if i0 > lo
                     else 99.0,
                     np.abs(day["l"][lo:i0] - px).min() if i0 > lo
                     else 99.0)
            row["nearest_any_p"] = round(float(dd), 2)
            # prior touches within 2p over the lookback
            tch = int(((np.abs(day["h"][lo:i0] - px) <= 2.0) |
                       (np.abs(day["l"][lo:i0] - px) <= 2.0)).sum())
            row["prior_touch_bars_2p"] = tch
            # in-span contact: bars whose [l,h] contains price, and
            # the closest the market ever gets to the level in-span
            if i1 > i0:
                seg_l, seg_h = day["l"][i0:i1], day["h"][i0:i1]
                hit = ((seg_l <= px) & (seg_h >= px)).sum()
                gap = np.minimum(np.abs(seg_h - px),
                                 np.abs(seg_l - px))
                inside = (seg_l <= px) & (seg_h >= px)
                gap[inside] = 0.0
                row["span_nearest_p"] = round(float(gap.min()), 2)
            else:
                hit = 0
            row["span_contact_bars"] = int(hit)
            out.append(row)

    with open(OUT, "w", encoding="utf8") as f:
        json.dump(out, f, indent=1)

    sc = [r for r in out if r.get("scorable")]
    print("objects: %d total, %d scorable" % (len(out), len(sc)))
    by = collections.defaultdict(list)
    for r in sc:
        by[(r["type"], r["repair"])].append(r)
    for k in sorted(by, key=str):
        g = by[k]
        ne = [r["nearest_ext_p"] for r in g if "nearest_ext_p" in r]
        na = [r["nearest_any_p"] for r in g]
        pt = [r["prior_touch_bars_2p"] for r in g]
        sp = [r["span_min"] for r in g]
        ct = [r["span_contact_bars"] for r in g]
        sn = [r["span_nearest_p"] for r in g if "span_nearest_p" in r]
        p = lambda v, q: round(float(np.percentile(v, q)), 2) \
            if v else None
        print("%-28s n=%-3d extRes p50/p90 %s/%s  anyRes p90 %s  "
              "ptouch p50 %s  span p50 %sm  spanNear p50/p90 %s/%s"
              % (k, len(g), p(ne, 50), p(ne, 90), p(na, 90),
                 p(pt, 50), p(sp, 50), p(sn, 50), p(sn, 90)))


if __name__ == "__main__":
    main()
