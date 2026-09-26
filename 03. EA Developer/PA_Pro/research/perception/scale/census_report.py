"""census_report.py — aggregate _census_<tag>.jsonl into the R48 §48.4
census table: per year x session, totals + median per day; and the
spread between years as a coefficient of variation (std/mean of the six
yearly totals, per session x metric).

Usage: python scale/census_report.py --tag C1_EURUSD_M5
"""
import argparse
import collections
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
METRICS = ("boxes", "range_open", "breaks", "teases", "levels", "lines")
SESS = ("asia", "eu", "us", "other")


def load(tag):
    f = os.path.join(HERE, "_census_%s.jsonl" % tag)
    return [json.loads(l) for l in open(f, encoding="utf8")]


def session_days(symbol="EURUSD"):
    """{sess: set(daynums)} for every DESIGN day that has >=1 bar inside
    the session window — the true denominator for per-day medians (days
    with zero drawings still count)."""
    import design_loader as DL
    bars = DL.load_m5(symbol)
    days = (bars["cet"] // 86400).astype(np.int64)
    lo_hi = {"asia": (0, 480), "eu": (480, 840), "us": (840, 1140)}
    out = {s: set() for s in SESS}
    for s in ("asia", "eu", "us"):
        lo, hi = lo_hi[s]
        out[s] = set(np.unique(days[(bars["cet_min"] >= lo)
                                    & (bars["cet_min"] < hi)]).tolist())
    out["other"] = set(np.unique(days).tolist())
    return out


def agg(rows, sess_days=None):
    """rows -> {sess: {metric: (total, med/day, [yearly totals])}}"""
    by_sess = collections.defaultdict(list)
    by_year_sess = collections.defaultdict(list)
    for r in rows:
        by_sess[r["sess"]].append(r)
        by_year_sess[(r["year"], r["sess"])].append(r)
    years = sorted({r["year"] for r in rows})
    out = {}
    for sess in SESS:
        rs = by_sess.get(sess, [])
        if sess_days is not None:
            all_days = sorted(sess_days[sess])
        else:
            all_days = sorted({r["day"] for r in rs})
        n_days = len(all_days)
        # zero-fill days with no row so medians are honest
        day_tot = collections.defaultdict(
            lambda: collections.Counter())
        for r in rs:
            day_tot[r["day"]].update(
                {m: r[m] for m in METRICS})
        mrow = {}
        for m in METRICS:
            tot = sum(r[m] for r in rs)
            per_day = [day_tot[d][m] for d in all_days]
            med = float(np.median(per_day)) if per_day else 0.0
            yearly = [sum(x[m] for x in by_year_sess.get((y, sess), []))
                      for y in years]
            cv = (float(np.std(yearly)) / float(np.mean(yearly))
                  if yearly and np.mean(yearly) > 0 else 0.0)
            mrow[m] = {"tot": tot, "med_day": med, "cv": cv,
                       "yearly": yearly}
        out[sess] = {"n_days": n_days, "m": mrow}
    return out, years


def print_report(tag):
    rows = load(tag)
    days = sorted({r["day"] for r in rows})
    sym = tag.split("_")[1]
    sd = session_days(sym)
    print("# census %s — %d day-rows; %d days had >=1 drawing\n" % (
        tag, len(rows), len(days)))
    a, years = agg(rows, sd)
    hdr = "| sess | days | " + " | ".join(
        "%s tot/med/cv" % m for m in METRICS) + " |"
    print(hdr)
    print("|---" * (len(METRICS) + 2) + "|")
    for sess in SESS:
        s = a[sess]
        cells = ["%d/%.2f/%.2f" % (s["m"][m]["tot"], s["m"][m]["med_day"],
                                   s["m"][m]["cv"]) for m in METRICS]
        print("| %s | %d | %s |" % (sess, s["n_days"], " | ".join(cells)))
    print("\nyears:", ", ".join(years))
    # per-year totals table (boxes/breaks/levels/lines)
    print("\n| year | sess | boxes | breaks | levels | lines |")
    print("|---|---|---|---|---|---|")
    by_year_sess = collections.defaultdict(
        lambda: collections.Counter())
    for r in rows:
        for m in ("boxes", "breaks", "levels", "lines"):
            by_year_sess[(r["year"], r["sess"])][m] += r[m]
    for (y, s), c in sorted(by_year_sess.items()):
        print("| %s | %s | %d | %d | %d | %d |" % (
            y, s, c["boxes"], c["breaks"], c["levels"], c["lines"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="C1_EURUSD_M5")
    args = ap.parse_args()
    print_report(args.tag)
