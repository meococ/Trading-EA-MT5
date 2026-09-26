"""anatomy — L2: how Volman's golden lines are anchored, on the
trustworthy subset from L1 (audit_lines.json minus Tier-A suspects).

Per line, per endpoint:
  anchor type  : theta2 structural pivot | theta1 pivot | named-bar
                 local extreme | session extreme | spike bar | none
  draw lag     : second anchor's pivot confirm delay (t_conf - t_ext)
  end reason   : break (close-through near t1) | panel_edge | fade
  box relation : overlap with same-panel golden BOX, distance to its
                 edges, converging-toward-edge flag (pressure side)

Swing stream = the engine's own (swings.py DCStream+SwingBook,
params_v1_1 swing block) run per day — read-only import.
"""

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_PERC, "golden"))
sys.path.insert(0, _PERC)
sys.path.insert(0, _HERE)

import bars_cache  # noqa: E402
import textfeat  # noqa: E402
from swings import DCStream, SwingBook  # noqa: E402

IN = os.path.join(_HERE, "audit_lines.json")
OUT = os.path.join(_HERE, "anatomy_lines.json")

# params_v1_1 swing block (read-only reference values)
K1_ABR, PMIN_ABR, PSTRUCT_ABR, SPIKE_MULT = 0.8, 0.5, 2.5, 2.5
TIER_A = {  # suspect ids from L1 (Tier A)
    "9.3a#0", "9.4a#3", "9.4a#5", "9.7b#1", "9.9a#0", "9.10b#0",
    "9.10c#0", "9.12a#0", "9.12a#1", "9.14b#1", "9.14b#4", "9.14c#1",
    "9.17c#2", "9.18a#2", "9.18c#1", "9.18c#3", "9.19a#4", "9.19b#1",
    "9.19b#3", "9.20b#2", "9.21b#1", "9.21c#0", "9.23a#4", "9.23b#1",
    "9.26a#1", "9.29a#2", "9.30a#1", "9.31b#2", "9.31b#3", "9.31c#0",
    "9.33b#1", "9.33b#2", "9.36c#2", "9.37c#3", "9.37c#4", "9.40a#1",
    "9.41a#0", "9.48b#2", "9.53a#1", "9.58b#0", "9.58c#0", "9.59b#1",
    "9.64b#1", "9.66c#5",
}


def run_swings(day):
    """Confirmed pivots on the day: list of dicts."""
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
                         "prom": piv.prom, "struct": book.is_structural(piv),
                         "spike": piv.lone_spike})
    return pivs, abr


def classify_end(tm, price, side, day, pivs, abr, tol_bars=2, tol_p=3.0):
    """Anchor type of one endpoint.  side: 'under'->low, 'over'->high."""
    m = day["m"]
    jc = int(np.argmin(np.abs(m - tm)))
    lo, hi = max(0, jc - tol_bars), min(len(m), jc + tol_bars + 1)
    want = -1 if side == "under" else 1         # pivot dir on that side
    ext = day["l"] if side == "under" else day["h"]
    # pivots whose extreme bar is within +-tol_bars and price within tol
    cand = [p for p in pivs
            if p["dir"] == want and lo <= p["t_ext"] < hi
            and abs(p["price"] - price) <= tol_p]
    if any(p["struct"] for p in cand):
        return "theta2", cand[0]
    if cand:
        return "theta1", cand[0]
    # local extreme: is the nearest bar's defended extreme the min/max
    # over +-3 bars (v1 _local_extreme semantics)?
    j = jc
    w_lo, w_hi = max(0, j - 3), min(len(m), j + 4)
    is_loc = (ext[j] == (np.min(ext[w_lo:w_hi]) if side == "under"
                         else np.max(ext[w_lo:w_hi])))
    if is_loc and abs(ext[j] - price) <= tol_p:
        # spike bar?
        rng = day["h"][j] - day["l"][j]
        if rng > SPIKE_MULT * abr[j]:
            return "spike", None
        return "local_ext", None
    # running session extreme at that bar
    if side == "under" and abs(day["l"][j] - np.min(day["l"][:j + 1])) < 0.01 \
            and abs(day["l"][j] - price) <= tol_p:
        return "session", None
    if side == "over" and abs(day["h"][j] - np.max(day["h"][:j + 1])) < 0.01 \
            and abs(day["h"][j] - price) <= tol_p:
        return "session", None
    return "none", None


def end_reason(r, day, w1):
    """Why does the drawn span end at t1?"""
    m = day["m"]
    t1, side = r["t1"], r["side"]
    p0, p1, t0 = r["price0"], r["price1"], r["t0"]
    if w1 is not None and abs(t1 - w1) <= 5:
        return "panel_edge"
    j = int(np.argmin(np.abs(m - t1)))
    sgn = 1.0 if side == "under" else -1.0
    for k in range(max(0, j - 2), min(len(m), j + 3)):
        lv = p0 + (p1 - p0) * (m[k] - t0) / (t1 - t0)
        if sgn * (lv - day["c"][k]) > 1.5:
            return "break"
    return "fade"


def box_relation(r, rec):
    """Relation to same-panel golden boxes: (overlapped?, role)."""
    t0, t1 = r["t0"], r["t1"]
    p0, p1 = r["price0"], r["price1"]
    out = []
    for o in rec.get("objects", []):
        if o.get("spec_type") != "BOX" or o.get("status") == "unusable":
            continue
        b0 = o.get("t0"); b1 = o.get("t1")
        lo, hi = o.get("price_lo"), o.get("price_hi")
        if None in (b0, b1, lo, hi):
            continue
        b0, b1 = int(b0), int(b1)
        lo, hi = lo * 1e4, hi * 1e4
        ov = min(t1, b1) - max(t0, b0)
        if ov <= 10:
            continue
        # at the box's right edge, where is the line?
        tm = min(t1, b1)
        lv = p0 + (p1 - p0) * (tm - t0) / (t1 - t0)
        d_top = lv - hi         # >0 line above box top
        d_bot = lv - lo
        role = "inside" if d_bot > -2 and d_top < 2 else (
            "under_box" if lv < lo - 1 else
            "over_box" if lv > hi + 1 else "edge_zone")
        # converging: does line approach the nearer edge over the span?
        lm = p0 + (p1 - p0) * (max(t0, b0) - t0) / (t1 - t0)
        conv = None
        if role == "under_box" and p1 > p0:
            conv = "rising_toward_top" if d_top > -8 else None
        if role == "over_box" and p1 < p0:
            conv = "falling_toward_bot" if d_bot < 8 else None
        out.append({"box_t0": b0, "box_t1": b1, "ov_min": int(ov),
                    "role": role, "conv": conv,
                    "d_edge": round(min(abs(d_top), abs(d_bot)), 1)})
    return out


def main():
    rows = json.load(open(IN, encoding="utf8"))
    days = bars_cache.days()
    recs = {r["id"]: r for r in bars_cache.tune_records()}
    out = []
    for r in rows:
        if not r.get("scorable"):
            continue
        key = "%s#%d" % (r["panel"], r["obj"])
        r["tier_a"] = key in TIER_A
        if r["tier_a"]:
            continue                      # trusted subset only
        rec = recs[r["panel"]]
        day = days[rec["date"]]
        pivs, abr = run_swings(day)
        side = r["side"]
        a0, p_a = classify_end(r["t0"], r["price0"], side, day, pivs, abr)
        a1, p_b = classify_end(r["t1"], r["price1"], side, day, pivs, abr)
        # draw lag: confirm delay of the later anchor pivot
        later = p_b if (p_b and (p_a is None or p_b["t_ext"] > p_a["t_ext"])) \
            else p_a
        lag = later["t_conf"] - later["t_ext"] if later else None
        w1 = rec["window"]["x1"]
        out.append({
            "key": key, "panel": r["panel"], "obj": r["obj"],
            "repair": r["repair"], "dir": r["dir"], "side": side,
            "side_text": r["side_text"], "clause": r["clause"],
            "span_min": r["span_min"], "slope_pph": r["slope_pph"],
            "slope_abr_hr": r["slope_abr_hr"],
            "t0": r["t0"], "t1": r["t1"], "p0": r["price0"],
            "p1": r["price1"],
            "anchor0": a0, "anchor1": a1,
            "n_anchors_txt": r["n_anchors"],
            "draw_lag_bars": lag,
            "touches15": r["touches"]["1.5"],
            "mid_touches15": r["touches"]["1.5"],   # span touches
            "end_reason": end_reason(r, day, w1),
            "boxes": box_relation(r, rec),
            "early_fade": None,
        })
    with open(OUT, "w", encoding="utf8") as f:
        json.dump(out, f, indent=1)
    # ---- summary ----
    from collections import Counter
    print("trusted n=%d" % len(out))
    print("anchor0:", Counter(r["anchor0"] for r in out))
    print("anchor1:", Counter(r["anchor1"] for r in out))
    print("end_reason:", Counter(r["end_reason"] for r in out))
    lags = [r["draw_lag_bars"] for r in out if r["draw_lag_bars"] is not None]
    print("draw_lag p50/p90: %.0f / %.0f bars"
          % (np.percentile(lags, 50), np.percentile(lags, 90)))
    n_box = sum(1 for r in out if r["boxes"])
    print("overlap a golden box:", n_box)
    print("box roles:", Counter(b["role"] for r in out for b in r["boxes"]))
    print("conv:", Counter(b["conv"] for r in out for b in r["boxes"]))


if __name__ == "__main__":
    main()
