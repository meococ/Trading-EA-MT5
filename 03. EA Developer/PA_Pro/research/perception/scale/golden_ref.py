"""golden_ref.py — the author's reference row for SCALE tables.

Computes the same statistics from the TUNE goldens
(golden/draft/BOOK2012_TUNE_v2.jsonl, usable objects only) that
scale_stats.py measures on the engine:

  * live objects per minute by family over each panel window
    (a golden object is "live" on [t0, t1]) -> median, p90, >5, >8;
  * births per session (t0 -> asia/eu/us) per day;
  * box height (pips + ABR, abr50 cache at the panel window), box
    duration in bars (minutes/5), level count, line slope (pips/hour).

ABR per panel: evalcheck's cached abr50 (evalcheck/_cache/abr50_*,
n=50 causal on BOOK bars) — read-only, no parquet touch.  HOLD is never
opened: only the TUNE file is read.

Usage: python scale/golden_ref.py  -> prints the reference row table and
       writes _golden_ref.json.
"""
import collections
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
EVALC = os.path.join(PERC, "evalcheck")
sys.path.insert(0, EVALC)

FAMILY = {
    "BOX": "box", "RANGE_OPEN": "box", "CONTEXT_RANGE": "box",
    "PATTERN_LINE": "line", "CONTEXT_LINE": "line",
    "LEVEL_CARRIED": "level", "MINI_LEVEL": "level",
    "BRACKET": "bracket", "SQUEEZE": "squeeze",
    "LABEL_TF": "annot", "BAR_MARKER": "annot",
}
FAMILIES = ("box", "line", "level", "bracket", "squeeze", "annot")
SESSIONS = (("asia", 0, 480), ("eu", 480, 840), ("us", 840, 1140))
USABLE = {"ok", "repaired"}
EXCLUDED = {"unusable", "fragment"}
TIME_ONLY = {"time_only"}

TUNE = os.path.join(PERC, "golden", "draft", "BOOK2012_TUNE_v2.jsonl")
ABR_CACHE = os.path.join(EVALC, "_cache", "abr50_%s.npy")


def session_of(m):
    for name, lo, hi in SESSIONS:
        if lo <= m < hi:
            return name
    return "other"


def panel_abr(date, w0, w1):
    """Median causal ABR50 (pips) over the panel window."""
    f = ABR_CACHE % date
    if not os.path.exists(f):
        return np.nan
    abr = np.load(f)
    # abr index k ~ k-th M5 bar of the day: minute = k*5
    i0, i1 = int(w0 // 5), min(int(w1 // 5), len(abr) - 1)
    if i1 < i0:
        return np.nan
    return float(np.median(abr[i0:i1 + 1]))


def main():
    recs = [json.loads(x) for x in open(TUNE, encoding="utf8")]
    live_all, live_fam = [], collections.defaultdict(list)
    over5, over8 = [], []
    births_sess = collections.Counter()
    births_sess_kind = collections.Counter()
    days = set()
    box_h_p, box_h_a, box_dur = [], [], []
    lvl_per_panel, line_slope = [], []
    objs_per_panel = []
    rn_d = []          # distance (true pips) of each drawn price point
                       # to the nearest 00/50 round level (R38 §38.5)
    for rec in recs:
        days.add(rec["date"])
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        objs = [o for o in rec["objects"]
                if o.get("status") in USABLE
                and o.get("spec_type")
                and o.get("status") not in TIME_ONLY
                and o.get("prec") != "time_only"]
        objs_per_panel.append(len(objs))
        # live-per-minute across the window
        for m in range(w0, w1, 5):
            cnt = collections.Counter()
            for o in objs:
                t0 = o.get("t0") if o.get("t0") is not None else w0
                t1 = o.get("t1") if o.get("t1") is not None else w1
                if t0 <= m <= t1:
                    cnt[FAMILY[o["spec_type"]]] += 1
            n_struct = sum(v for k, v in cnt.items() if k != "annot")
            live_all.append(sum(cnt.values()))
            over5.append(n_struct > 5)
            over8.append(n_struct > 8)
            for f in FAMILIES:
                live_fam[f].append(cnt.get(f, 0))
        abr = panel_abr(rec["date"], w0, w1)
        nlvl = 0
        for o in objs:
            st = o["spec_type"]
            t0 = o.get("t0")
            if t0 is not None:
                births_sess[session_of(t0)] += 1
                births_sess_kind[(session_of(t0), st)] += 1
            if st in ("BOX", "RANGE_OPEN", "CONTEXT_RANGE"):
                if o.get("price_hi") is not None \
                        and o.get("price_lo") is not None:
                    hp = (o["price_hi"] - o["price_lo"]) / 1e-4
                    box_h_p.append(hp)
                    if not np.isnan(abr):
                        box_h_a.append(hp / abr)
                    for p in (o["price_hi"], o["price_lo"]):
                        rn_d.append(min((p / 1e-4) % 50,
                                        50 - (p / 1e-4) % 50))
                if o.get("t0") is not None and o.get("t1") is not None:
                    box_dur.append((o["t1"] - o["t0"]) / 5.0)
            if st in ("LEVEL_CARRIED", "MINI_LEVEL"):
                nlvl += 1
                pr = o.get("price")
                if pr is None and o.get("price_hi") is not None:
                    pr = o["price_hi"]
                if pr is not None:
                    rn_d.append(min((pr / 1e-4) % 50,
                                    50 - (pr / 1e-4) % 50))
            if st in ("PATTERN_LINE", "CONTEXT_LINE"):
                if o.get("price0") is not None and \
                        o.get("price1") is not None and \
                        o.get("t0") is not None and o.get("t1") \
                        is not None and o["t1"] > o["t0"]:
                    slope = abs(o["price1"] - o["price0"]) / 1e-4 \
                        / ((o["t1"] - o["t0"]) / 60.0)
                    line_slope.append(slope)
        lvl_per_panel.append(nlvl)

    def ms(v):
        v = np.asarray(v, dtype=np.float64)
        return float(np.median(v)), float(np.percentile(v, 90))

    n_days = len(days)
    out = {"panels": len(recs), "days": n_days,
           "objs_per_panel": ms(objs_per_panel),
           "live_all_med": ms(live_all)[0], "live_all_p90":
           ms(live_all)[1],
           "over5": float(np.mean(over5)), "over8": float(np.mean(over8)),
           "fam": {f: ms(live_fam[f]) for f in FAMILIES},
           "births_per_day_sess": {s: births_sess[s] / n_days
                                   for s in ("asia", "eu", "us",
                                             "other")},
           "births_per_day_sess_kind": {
               "%s|%s" % k: v / n_days
               for k, v in births_sess_kind.items()},
           "box_height_pips": ms(box_h_p), "box_height_abr": ms(box_h_a),
           "box_dur_bars": ms(box_dur),
           "levels_per_panel": float(np.mean(lvl_per_panel)),
           "line_slope_pips_hr": ms(line_slope),
           "rn50_pts": len(rn_d),
           "rn50_within1": float(np.mean(np.asarray(rn_d) <= 1.0))
           if rn_d else 0.0,
           "rn50_within2": float(np.mean(np.asarray(rn_d) <= 2.0))
           if rn_d else 0.0}
    print(json.dumps(out, indent=2))
    with open(os.path.join(HERE, "_golden_ref.json"), "w",
              encoding="utf8") as f:
        json.dump(out, f, indent=2)
    print("wrote _golden_ref.json")


if __name__ == "__main__":
    sys.exit(main())
