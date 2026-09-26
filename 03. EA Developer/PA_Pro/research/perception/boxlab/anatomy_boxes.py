"""anatomy_boxes — X2 box anatomy on the trusted subset.

Per trusted golden BOX (X1 flags):
  start anchor : swing extreme | first edge touch | session boundary |
                 prior-leg end (running day extreme) | other
  edge constr. : edge vs confirmed pivot / day extreme / pure cluster;
                 wick-vs-close; company counts
  draw moment  : first bar where both edges carry >=2 hug bars AND the
                 last K closes are contained (the 'knowable' bar);
                 2nd touch on the breakout edge
  buildup R9a  : breakout edge vs pre-existing level / earlier swing /
                 day extreme; opposite-side pressure; compression; EMA25
  nesting      : other golden boxes overlapping; asia flag; height vs
                 day range
  end          : break dir vs label dir; drawn tail (t1 - be)

Swings via swings.py DCStream+SwingBook (params_v1_1 values), read-only.
Output: cache/anatomy_boxes.json + console summary.
"""
import collections
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
for _p in (_HERE, _PERC, os.path.join(_PERC, "golden")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bars_cache as BC            # noqa: E402
from swings import DCStream, SwingBook  # noqa: E402

TUNE_JSONL = os.path.join(_PERC, "golden", "draft", "BOOK2012_TUNE_v2.jsonl")
AUDIT = os.path.join(_HERE, "cache", "box_audit.jsonl")
OUT = os.path.join(_HERE, "cache", "anatomy_boxes.json")

K1_ABR, PMIN_ABR, PSTRUCT_ABR, SPIKE_MULT = 0.8, 0.5, 2.5, 2.5
TOL = 1.5


def run_swings(day):
    abr = BC.abr50(day["h"], day["l"], day["c"])
    dc = DCStream(lambda i: K1_ABR * abr[i],
                  lambda i: (day["h"][i] - day["l"][i])
                  > SPIKE_MULT * abr[i])
    book = SwingBook(PMIN_ABR, PSTRUCT_ABR, abr_fn=lambda i: abr[i])
    pivs = []
    for i in range(len(day["m"])):
        book.update_running(dc.dir, dc.ext_price)
        for p in dc.update(i, day["h"][i], day["l"][i]):
            piv = book.add(p)
            pivs.append({"t_ext": int(piv.t_ext), "t_conf": int(piv.t_conf),
                         "price": float(piv.price), "dir": int(piv.dir),
                         "prom": float(piv.prom),
                         "struct": bool(book.is_structural(piv)),
                         "spike": bool(piv.lone_spike)})
    return pivs, abr


def ema25(c):
    out = np.zeros(len(c)); e = None; a = 2.0 / 26.0
    for i in range(len(c)):
        e = c[i] if e is None else e + a * (c[i] - e)
        out[i] = e
    return out


def classify_start(bs, day, pivs, first_touch):
    """What is build_start anchored on? Priority: pivot extreme,
    first edge touch, session boundary, prior-leg end (day extreme)."""
    m = day["m"]
    j = BC.idx_of(day, bs)
    if j is None:
        return "other", {}
    piv_near = [p for p in pivs
                if abs(int(m[p["t_ext"]]) - bs) <= 15]
    info = {"piv_at_bs": len(piv_near)}
    if piv_near:
        p = min(piv_near, key=lambda p: abs(int(m[p["t_ext"]]) - bs))
        return ("theta2" if p["struct"] else "theta1"), info
    if first_touch is not None and abs(first_touch - bs) <= 10:
        return "first_touch", info
    for sb in (0, 480, 780, 1020):
        if abs(bs - sb) <= 10:
            return "session", info
    if abs(day["h"][j] - np.max(day["h"][:j + 1])) < 0.5 or \
            abs(day["l"][j] - np.min(day["l"][:j + 1])) < 0.5:
        return "day_extreme", info
    return "other", info


def edge_kind(edge, side, day, pivs, mask_idx):
    """Classify one edge: pivot extreme / day extreme / cluster."""
    want = 1 if side == "top" else -1
    cand = [p for p in pivs if p["dir"] == want
            and abs(p["price"] - edge) <= 2.0
            and p["t_ext"] in mask_idx]
    if any(p["struct"] for p in cand):
        return "theta2_piv"
    if cand:
        return "theta1_piv"
    if cand == [] and pivs:
        cand = [p for p in pivs if p["dir"] == want
                and abs(p["price"] - edge) <= 2.0]
        if cand:
            return "piv_outside_window"
    return "cluster"


def knowable_minute(day, bs, be, lo, hi, k_contained=6):
    """Earliest minute when: >=2 hug bars on EACH edge (cumul. since bs)
    AND >=k_contained closes contained so far.  Returns cet_min."""
    mask = BC.day_slice(day, bs, be)
    idx = np.where(mask)[0]
    if not len(idx):
        return None, {}
    tt = tb = 0
    contained = 0
    for j in idx:
        if abs(day["h"][j] - hi) <= TOL:
            tt += 1
        if abs(day["l"][j] - lo) <= TOL:
            tb += 1
        if lo <= day["c"][j] <= hi:
            contained += 1
        if tt >= 2 and tb >= 2 and contained >= k_contained:
            return int(day["m"][j]), {"t2_top_min": None}
    return None, {}


def second_touch_minute(day, bs, be, edge, side):
    mask = BC.day_slice(day, bs, be)
    idx = np.where(mask)[0]
    ext = day["h"] if side == "top" else day["l"]
    n = 0
    for j in idx:
        if abs(ext[j] - edge) <= TOL:
            n += 1
            if n == 2:
                return int(day["m"][j])
    return None


def main():
    recs = {r["id"]: r for r in
            (json.loads(x) for x in open(TUNE_JSONL, encoding="utf8"))}
    audit = [json.loads(x) for x in open(AUDIT, encoding="utf8")]
    trusted = [r for r in audit if r.get("trusted") and r["scorable"]]
    dates, bars = BC.load_all()

    swings_by_day, abr_by_day, ema_by_day = {}, {}, {}
    out = []
    for r in trusted:
        rec = recs[r["panel"]]
        day = bars[rec["date"]]
        if rec["date"] not in swings_by_day:
            pivs, _abr = run_swings(day)
            swings_by_day[rec["date"]] = pivs
            abr_by_day[rec["date"]] = _abr
            ema_by_day[rec["date"]] = ema25(day["c"])
        pivs, abr, ema = (swings_by_day[rec["date"]],
                          abr_by_day[rec["date"]], ema_by_day[rec["date"]])
        lo, hi, bs, be = r["lo"], r["hi"], r["bs"], r["be"]
        mask = BC.day_slice(day, bs, be)
        midx = set(int(j) for j in np.where(mask)[0])

        row = {"key": "%s#%d" % (r["panel"], r["idx"]),
               "panel": r["panel"], "bs": bs, "be": be,
               "lo": lo, "hi": hi, "t0": r["t0"], "t1": r["t1"]}

        # --- start anchor ---
        row["start_anchor"], st_info = classify_start(
            bs, day, pivs, r["first_touch_min"])
        row.update(st_info)

        # --- edges ---
        row["edge_top_kind"] = edge_kind(hi, "top", day, pivs, midx)
        row["edge_bot_kind"] = edge_kind(lo, "bot", day, pivs, midx)
        # day extremes at build_end?
        jbe = BC.idx_of(day, be)
        if jbe is not None:
            row["top_is_day_hi"] = bool(
                abs(day["h"][:jbe + 1].max() - hi) <= 2.0)
            row["bot_is_day_lo"] = bool(
                abs(day["l"][:jbe + 1].min() - lo) <= 2.0)

        # --- draw moment ---
        kn, _ = knowable_minute(day, bs, be, lo, hi)
        row["knowable_min"] = kn
        row["knowable_minus_be"] = (kn - be) if kn is not None else None
        brk = r.get("break_dir")
        brk_edge_side = "top" if brk == "up" else ("bot" if brk == "down"
                                                   else None)
        row["break_dir"] = brk
        if brk_edge_side:
            edge = hi if brk_edge_side == "top" else lo
            t2 = second_touch_minute(day, bs, be, edge, brk_edge_side)
            row["brk_edge_2nd_touch"] = t2
            row["brk_edge_2nd_minus_be"] = (t2 - be) if t2 else None
            row["brk_edge"] = edge
            row["brk_edge_kind"] = (row["edge_top_kind"]
                                    if brk_edge_side == "top"
                                    else row["edge_bot_kind"])

        # --- R9a buildup vs barrier ---
        if brk_edge_side and jbe is not None:
            edge = row["brk_edge"]
            want = 1 if brk_edge_side == "top" else -1
            pre_piv = [p for p in pivs if p["dir"] == want
                       and abs(p["price"] - edge) <= 2.0
                       and int(day["m"][p["t_ext"]]) < bs]
            row["brk_edge_pre_level"] = bool(pre_piv)
            jbs = BC.idx_of(day, bs)
            if jbs is not None:
                if brk_edge_side == "top":
                    row["brk_edge_day_ext"] = bool(
                        abs(day["h"][:jbs + 1].max() - edge) <= 2.0)
                else:
                    row["brk_edge_day_ext"] = bool(
                        abs(day["l"][:jbs + 1].min() - edge) <= 2.0)
            # pressure: opposite extreme halves
            idx = np.where(mask)[0]
            half = len(idx) // 2
            if half >= 2:
                o1, o2 = idx[:half], idx[half:]
                if brk_edge_side == "top":
                    row["pressure"] = float(
                        day["l"][o2].min() - day["l"][o1].min())
                else:
                    row["pressure"] = float(
                        day["h"][o1].max() - day["h"][o2].max())
                last3 = idx[max(0, len(idx) - len(idx) // 3):]
                if len(last3):
                    mid = 0.5 * (lo + hi)
                    upper = day["c"][last3] > mid
                    row["late_close_side"] = float(upper.mean()) \
                        if brk_edge_side == "top" else \
                        float(1 - upper.mean())
            # compression: median range inside vs ABR at bs
            rng = day["h"][idx] - day["l"][idx]
            jbs2 = BC.idx_of(day, bs)
            row["compress"] = float(np.median(rng) / abr[jbs2]) \
                if jbs2 is not None and abr[jbs2] else None
            # EMA25 vs box
            ema_w = ema[idx]
            row["ema_vs_box"] = ("inside" if np.mean(
                (ema_w >= lo) & (ema_w <= hi)) > 0.5 else
                "above" if np.mean(ema_w > hi) > 0.5 else "below")

        # --- nesting / context ---
        row["asia"] = bool(bs < 480)
        row["tall_frac_day"] = float(
            (hi - lo) / max(day["h"].max() - day["l"].min(), 1))
        row["nested_golden"] = 0
        for i2, o2 in enumerate(rec.get("objects", [])):
            if o2.get("spec_type") != "BOX" or i2 == r["idx"]:
                continue
            b0, b1 = o2.get("t0"), o2.get("t1")
            l2, h2 = o2.get("price_lo"), o2.get("price_hi")
            if None in (b0, b1, l2, h2):
                continue
            ov = min(r["t1"] or be, b1) - max(r["t0"] or bs, b0)
            if ov > 0 and l2 * 1e4 <= lo + 2 and h2 * 1e4 >= hi - 2 \
                    and (h2 - l2) * 1e4 > hi - lo + 4:
                row["nested_golden"] += 1

        # --- end ---
        row["tail_min"] = (r["t1"] - be) if (r["t1"] and be) else None
        row["label_dir"] = r["dir"]
        out.append(row)

    with open(OUT, "w", encoding="utf8") as f:
        json.dump(out, f, indent=1)

    # ---- summary ----
    def cnt(k):
        return dict(collections.Counter(r.get(k) for r in out))

    print("trusted anatomy n=%d" % len(out))
    print("start_anchor:", cnt("start_anchor"))
    print("edge_top_kind:", cnt("edge_top_kind"))
    print("edge_bot_kind:", cnt("edge_bot_kind"))
    print("brk_edge_kind:", cnt("brk_edge_kind"))
    print("brk_edge_pre_level:", cnt("brk_edge_pre_level"))
    print("brk_edge_day_ext:", cnt("brk_edge_day_ext"))
    print("top_is_day_hi:", cnt("top_is_day_hi"))
    print("bot_is_day_lo:", cnt("bot_is_day_lo"))
    print("ema_vs_box:", cnt("ema_vs_box"))
    print("asia:", cnt("asia"))
    print("break_dir:", cnt("break_dir"))
    print("label_dir:", cnt("label_dir"))

    def q(v, name):
        v = np.array([x for x in v if x is not None], float)
        if len(v):
            print(f"  {name}: n={len(v)} med={np.median(v):.2f} "
                  f"p10={np.percentile(v, 10):.2f} "
                  f"p90={np.percentile(v, 90):.2f}")
    q([r.get("knowable_minus_be") for r in out], "knowable - be (min)")
    q([r.get("brk_edge_2nd_minus_be") for r in out],
      "2nd brk-edge touch - be")
    q([r.get("pressure") for r in out], "pressure (pips)")
    q([r.get("late_close_side") for r in out], "late closes near brk side")
    q([r.get("compress") for r in out], "compression (med rng / ABR)")
    q([r.get("tail_min") for r in out], "drawn tail t1 - be")
    q([r.get("tall_frac_day") for r in out], "box height / day range")
    print("nested_golden>0:", sum(1 for r in out
                                  if r["nested_golden"] > 0))
    kn_none = [r["key"] for r in out if r["knowable_min"] is None]
    print("not knowable in-window:", len(kn_none), kn_none[:12])


if __name__ == "__main__":
    main()
