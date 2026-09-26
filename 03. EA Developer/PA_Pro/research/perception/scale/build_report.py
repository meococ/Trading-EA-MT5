"""build_report.py — aggregate _stats_*.jsonl into SCALE tables.

Reads:
  _stats_days_<tag>.jsonl  (one row per measured day x session)
  _stats_objs_<tag>.jsonl  (one row per drawn object)
  _golden_ref.json         (the author's TUNE reference row)

Emits per (arm, symbol, tf, year, session) aggregates and flags every
(year, session) or arm-level statistic that differs from the author's
reference row by more than 2x, with 3 example sessions each.

Aggregation notes:
  * "live objects per bar" stats are pooled as the bar-weighted mean of
    per-(day,session) shares and the median of per-(day,session)
    medians (labeled med*); exact pooled quantiles need per-bar
    storage, which the day files intentionally drop.
  * births/day denominators count measured days (a day contributes a
    session bucket only if it has bars there).

Usage: python scale/build_report.py --tags KEPT_EURUSD_M5 STABLE_EURUSD_M5
"""
import argparse
import collections
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SESS_ORDER = ("asia", "eu", "us", "other")
FAMS = ("box", "line", "level", "bracket", "squeeze", "annot")
PIP_SIZE = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDJPY": 1e-2,
            "AUDUSD": 1e-4}


def rn_share(objs, sym):
    """R38 §38.5: share of drawn price points within 1/2 true pips of a
    00/50 round level.  rn_pts are engine pips (price*1e4); true pips
    = (eng/1e4)/pip_size."""
    pip = PIP_SIZE.get(sym, 1e-4)
    d = []
    for o in objs:
        for p in o.get("rn_pts") or []:
            tp = p / 1e4 / pip                     # true pips
            d.append(min(tp % 50, 50 - tp % 50))
    if not d:
        return None, None, 0
    a = np.asarray(d)
    return float((a <= 1.0).mean()), float((a <= 2.0).mean()), len(a)


def load(tag):
    dr = os.path.join(HERE, "_stats_days_%s.jsonl" % tag)
    ob = os.path.join(HERE, "_stats_objs_%s.jsonl" % tag)
    days = [json.loads(x) for x in open(dr, encoding="utf8")]
    objs = [json.loads(x) for x in open(ob, encoding="utf8")] \
        if os.path.exists(ob) else []
    return days, objs


def year_of(r):
    return (r.get("date") or "")[:4]


def wmean(rows, field):
    num = sum(r[field] * r["bars"] for r in rows)
    den = sum(r["bars"] for r in rows)
    return num / den if den else 0.0


def med_field(rows, field):
    v = [r[field] for r in rows if r["bars"] > 0]
    return float(np.median(v)) if v else 0.0


def obj_agg(objs):
    """Object-level aggregates for one group of obj rows."""
    out = {}
    bh = [o["height_abr"] for o in objs
          if o.get("height_abr") is not None
          and o["type"] in ("BOX", "RANGE_OPEN", "CONTEXT_RANGE")]
    bd = [o["dur_bars"] for o in objs
          if o["type"] in ("BOX", "RANGE_OPEN", "CONTEXT_RANGE")]
    ls = [abs(o["slope_pips_hr"]) for o in objs
          if o.get("slope_pips_hr") is not None]
    lv = [o for o in objs if o["type"] in ("LEVEL_CARRIED", "MINI_LEVEL")]
    if bh:
        out["box_h_abr_med"] = float(np.median(bh))
        out["box_h_abr_p90"] = float(np.percentile(bh, 90))
    if bd:
        out["box_dur_med"] = float(np.median(bd))
        out["box_dur_p90"] = float(np.percentile(bd, 90))
    if ls:
        out["line_slope_med"] = float(np.median(ls))
        out["line_slope_p90"] = float(np.percentile(ls, 90))
    out["n_levels"] = len(lv)
    return out


def group_report(days, objs, sym, pooled=True):
    """Aggregate one tag into {(year, sess): stats}; ``pooled`` also
    adds ("ALL", sess) rows collapsing every year."""
    by = collections.defaultdict(list)
    for r in days:
        by[(year_of(r), r["sess"])].append(r)
        if pooled:
            by[("ALL", r["sess"])].append(r)
    oby = collections.defaultdict(list)
    for o in objs:
        oby[(o["date"][:4], o["sess"])].append(o)
        if pooled:
            oby[("ALL", o["sess"])].append(o)
    out = {}
    for key, rows in sorted(by.items()):
        n_days = len({r["date"] for r in rows})
        bars = sum(r["bars"] for r in rows)
        births = collections.Counter()
        for o in oby.get(key, []):
            births[o["type"]] += 1
        sa_share = sum(r["sa_bars"] for r in rows) / bars if bars else 0
        sa_reasons = collections.Counter()
        for r in rows:
            sa_reasons.update({k: v for k, v in r["sa"].items()})
        em_l = sum(r["edge_moves_logged"] for r in rows)
        em_u = sum(r["edge_moves_unlogged"] for r in rows)
        st = {
            "n_days": n_days, "bars": bars,
            "struct_med": med_field(rows, "struct_med"),
            "struct_p90": wmean(rows, "struct_p90"),
            "all_med": med_field(rows, "all_med"),
            "all_p90": wmean(rows, "all_p90"),
            "over5": wmean(rows, "over5"),
            "over8": wmean(rows, "over8"),
            "sa_share": sa_share,
            "sa_reasons": dict(sa_reasons.most_common(4)),
            "em_logged_100": em_l / bars * 100 if bars else 0,
            "em_unlogged_100": em_u / bars * 100 if bars else 0,
            "births_day": {k: v / n_days for k, v in
                           births.most_common()},
        }
        rn1, rn2, npts = rn_share(oby.get(key, []), sym)
        st["rn50_w1"] = rn1
        st["rn50_w2"] = rn2
        st["rn50_pts"] = npts
        for f in FAMS:
            st["%s_med" % f] = med_field(rows, "%s_med" % f)
        st.update(obj_agg(oby.get(key, [])))
        out[key] = st
    return out


AUTHOR = None


def _load_author():
    global AUTHOR
    if AUTHOR is None:
        AUTHOR = json.load(open(os.path.join(HERE, "_golden_ref.json"),
                                encoding="utf8"))
    return AUTHOR


def compare_to_author(st):
    """Return list of (metric, value, author_value, ratio) flags >2x."""
    a = _load_author()
    flags = []

    def chk(name, v, ref, floor=0.0, both=True):
        ref = float(ref)
        if ref <= 0:
            if v > floor:
                flags.append((name, v, ref, float("inf")))
        elif v > 2 * ref:
            flags.append((name, v, ref, v / ref))
        elif both and v < ref / 2:
            flags.append((name, v, ref, v / ref))

    chk("struct_med", st["struct_med"], a["live_all_med"])
    chk("over5", st["over5"], a["over5"], floor=0.05)
    chk("over8", st["over8"], a["over8"], floor=0.02)
    if "box_h_abr_med" in st:
        chk("box_h_abr_med", st["box_h_abr_med"], a["box_height_abr"][0])
    if "box_dur_med" in st:
        chk("box_dur_med", st["box_dur_med"], a["box_dur_bars"][0])
    if "line_slope_med" in st:
        chk("line_slope_med", st["line_slope_med"],
            a["line_slope_pips_hr"][0])
    chk("em_unlogged_100", st["em_unlogged_100"], 0.0, floor=0.5)
    chk("em_logged_100", st["em_logged_100"], 0.0, floor=2.0)
    if st.get("rn50_w2") is not None:
        chk("rn50_w2", st["rn50_w2"], a["rn50_within2"])
    # births/day by kind vs the author's per-session rates
    yr_sess = None
    return flags


def compare_births(st, sess):
    """Per-kind births/day flags vs author births_per_day_sess_kind."""
    a = _load_author()
    flags = []
    if sess == "other":
        return flags                    # author panels cover 3 windows
    for kind, v in st["births_day"].items():
        ref = a["births_per_day_sess_kind"].get("%s|%s" % (sess, kind),
                                                0.0)
        if ref <= 0:
            if v > 0.5:
                flags.append(("births|%s" % kind, v, ref, float("inf")))
        elif v > 2 * ref or v < ref / 2:
            flags.append(("births|%s" % kind, v, ref, v / ref))
    return flags


def print_table(tag, rep, days, objs):
    a = _load_author()
    print("\n## %s  (author ref: live med %.1f p90 %.1f; over5 %.2f; "
          "box h %.1fp/%.2fABR dur %.0fb; slope %.1f p/hr)"
          % (tag, a["live_all_med"], a["live_all_p90"], a["over5"],
             a["box_height_pips"][0], a["box_height_abr"][0],
             a["box_dur_bars"][0], a["line_slope_pips_hr"][0]))
    hdr = ("year", "sess", "days", "bars", "struct med/p90", ">5", ">8",
           "sa%", "emL/100", "emU/100", "rn50w2", "births/d top",
           "boxH abr", "boxDur", "slope", "lvl/d")
    print("| " + " | ".join(hdr) + " |")
    print("|" + "---|" * len(hdr))
    def _k(item):
        (yr, ss), _st = item
        return (0 if yr == "ALL" else 1, yr, SESS_ORDER.index(ss)
                if ss in SESS_ORDER else 9)
    for (yr, ss), st in sorted(rep.items(), key=_k):
        top = ", ".join("%s:%.2f" % (k, v) for k, v in
                        list(st["births_day"].items())[:4])
        print("| %s | %s | %d | %d | %.1f / %.1f | %.3f | %.3f | %.2f | "
              "%.2f | %.2f | %s | %s | %s | %s | %s | %.2f |" % (
                  yr, ss, st["n_days"], st["bars"],
                  st["struct_med"], st["struct_p90"],
                  st["over5"], st["over8"], st["sa_share"],
                  st["em_logged_100"], st["em_unlogged_100"],
                  "%.2f" % st["rn50_w2"]
                  if st["rn50_w2"] is not None else "—", top,
                  "%.1f" % st["box_h_abr_med"]
                  if "box_h_abr_med" in st else "—",
                  "%.0f" % st["box_dur_med"]
                  if "box_dur_med" in st else "—",
                  "%.1f" % st["line_slope_med"]
                  if "line_slope_med" in st else "—",
                  st["n_levels"] / max(st["n_days"], 1)))
    print_flags(tag, rep, days, objs)


def _examples(days, objs, key, name, k=3):
    """3 example (date, session) pairs that drive the flagged stat."""
    yr, ss = key
    rows = [r for r in days if year_of(r) == yr and r["sess"] == ss]
    metric = {
        "struct_med": "struct_med", "over5": "over5",
        "over8": "over8", "sa_share": None,
        "em_unlogged_100": "edge_moves_unlogged",
        "em_logged_100": "edge_moves_logged",
        "rn50_w2": None,
    }.get(name)
    if metric == "sa_share" or metric is None:
        rows = sorted(rows, key=lambda r: r["sa_bars"]
                      / max(r["bars"], 1), reverse=True)
    elif metric.startswith("edge_moves"):
        rows = sorted(rows, key=lambda r: r[metric]
                      / max(r["bars"], 1), reverse=True)
    else:
        rows = sorted(rows, key=lambda r: r.get(metric, 0),
                      reverse=True)
    return ["%s/%s" % (r.get("date", str(r["day"])), r["sess"])
            for r in rows[:k]]


def print_flags(tag, rep, days, objs):
    print("\nflags (>2x author):")
    for (yr, ss), st in sorted(rep.items()):
        for name, v, ref, ratio in compare_to_author(st) + \
                compare_births(st, ss):
            ex = _examples(days, objs, (yr, ss), name)
            print("  %s %s: %s = %.3g vs author %.3g (x%s)  ex: %s"
                  % (yr, ss, name, v, ref,
                     "inf" if ratio == float("inf") else "%.1f" % ratio,
                     ", ".join(ex)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", nargs="+", required=True)
    args = ap.parse_args()
    for tag in args.tags:
        days, objs = load(tag)
        sym = tag.split("_")[1]
        rep = group_report(days, objs, sym)
        print_table(tag, rep, days, objs)


if __name__ == "__main__":
    sys.exit(main())
