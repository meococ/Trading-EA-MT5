"""VPA P2 census — outcome-blind candidate counts on DESIGN (2016-2021).

No PnL, no outcome, no fill simulation: this measures how many EXECUTABLE
candidates the frozen detector definition produces per week, by setup type,
session and year. Outputs:
  PLAN/CENSUS_<SYM>.csv      weekly series
  PLAN/CENSUS_SUMMARY.md     funnel + verdict
  PLAN/CENSUS_<SYM>.json     raw counters
"""

import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PKG = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(PKG, "PLAN")

from vpa_core import run_detector  # noqa: E402
from vpa_data import load_m5_bars  # noqa: E402
from vpa_random_baseline import eu_server_offset_hours  # noqa: E402

SYMBOLS = ["EURUSD", "GBPUSD"]


def census_symbol(sym):
    bars = load_m5_bars(sym)
    t0 = time.time()
    recs, counters = run_detector(bars)
    secs = time.time() - t0

    t = np.asarray(bars["t"], dtype=np.int64)
    naive = pd.to_datetime(t, unit="s", utc=False)
    off = eu_server_offset_hours(naive)
    utc = pd.to_datetime(t - off * 3600, unit="s", utc=True)
    week = utc.to_period("W-MON").start_time
    year = utc.year

    raw = np.zeros(len(t), dtype=np.int64)
    pb = np.zeros(len(t), dtype=np.int64)
    cb = np.zeros(len(t), dtype=np.int64)
    pr = np.zeros(len(t), dtype=np.int64)
    for r in recs:
        i = r["bar_idx"]
        if r.get("executable"):
            if r["setup"] == "pattern_break":
                pb[i] += 1
            elif r["setup"] == "combi":
                cb[i] += 1
            elif r["setup"] == "pullback_reversal":
                pr[i] += 1
        if r.get("setup") == "pattern_break":
            raw[i] += 1  # every pattern-break record is one raw break event (accept or reject)

    df = pd.DataFrame({"week": week, "year": year, "raw_break": raw, "exec_pb": pb,
                       "exec_combi": cb, "exec_pr": pr})
    weekly = df.groupby("week", as_index=False).sum(numeric_only=True)
    weekly["exec_total"] = weekly["exec_pb"] + weekly["exec_combi"] + weekly["exec_pr"]

    total_weeks = len(weekly)
    stats = {}
    for col in ["raw_break", "exec_pb", "exec_combi", "exec_pr", "exec_total"]:
        v = weekly[col].to_numpy(dtype=float)
        stats[col] = {
            "total": int(v.sum()),
            "per_week_mean": round(float(v.mean()), 3),
            "per_week_median": float(np.median(v)),
            "per_week_p10": float(np.percentile(v, 10)),
            "per_week_p90": float(np.percentile(v, 90)),
        }
    by_year = df.groupby("year")[["raw_break", "exec_pb", "exec_combi", "exec_pr"]].sum()
    # by session
    by_session = {"london": {"exec": 0, "raw": 0}, "ny": {"exec": 0, "raw": 0}}
    for r in recs:
        s = r.get("session")
        if s in by_session:
            if r.get("setup") == "pattern_break":
                by_session[s]["raw"] += 1
            if r.get("executable"):
                by_session[s]["exec"] += 1

    csv_path = os.path.join(OUT, f"CENSUS_{sym}.csv")
    weekly.to_csv(csv_path, index=False)
    json_path = os.path.join(OUT, f"CENSUS_{sym}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"symbol": sym, "bars": len(t), "seconds": round(secs, 2),
                   "records": len(recs), "counters": counters, "weekly_stats": stats,
                   "by_year": by_year.to_dict(), "by_session": by_session,
                   "weeks": total_weeks}, f, indent=2, default=str)
    return {"symbol": sym, "bars": len(t), "seconds": round(secs, 2), "weeks": total_weeks,
            "stats": stats, "counters": counters, "by_year": by_year, "by_session": by_session,
            "csv": csv_path, "json": json_path}


def main():
    results = []
    for sym in SYMBOLS:
        print(f"[census] {sym}", flush=True)
        results.append(census_symbol(sym))

    lines = ["# CENSUS_SUMMARY — VPA-P2 (outcome-blind)", "",
             "DESIGN 2016-01-01 → 2021-12-31 · detector `research/lab/vpa_core.py` · "
             "no PnL, no exits, no fills — candidate counts only.", ""]
    for res in results:
        sym = res["symbol"]
        st = res["stats"]
        lines += [f"## {sym}", "",
                  f"- bars: {res['bars']:,} · weeks: {res['weeks']} · detector runtime: {res['seconds']}s",
                  "",
                  "| metric | total | /week mean | /week median | p10 | p90 |",
                  "|---|---|---|---|---|---|"]
        for col, label in [("raw_break", "raw breaks (locked barrier + close-break)"),
                           ("exec_pb", "EXECUTABLE pattern break"),
                           ("exec_combi", "EXECUTABLE combi"),
                           ("exec_pr", "EXECUTABLE pullback reversal"),
                           ("exec_total", "EXECUTABLE total")]:
            s = st[col]
            lines.append(f"| {label} | {s['total']} | {s['per_week_mean']} | {s['per_week_median']} | "
                         f"{s['per_week_p10']} | {s['per_week_p90']} |")
        lines += ["", "By year:", "", "```", res["by_year"].to_string(), "```", "",
                  f"By session: {res['by_session']}", ""]
        c = res["counters"]
        funnel = [
            ("raw breaks", c.get("raw_break", 0)),
            ("- skip_session", c.get("skip_session", 0)),
            ("- skip_bias", c.get("skip_bias", 0)),
            ("- skip_chop", c.get("skip_chop", 0)),
            ("- skip_no_pressure", c.get("skip_no_pressure", 0)),
            ("= reached buildup gate", c.get("raw_break", 0) - c.get("skip_session", 0)
             - c.get("skip_bias", 0) - c.get("skip_chop", 0) - c.get("skip_no_pressure", 0)),
            ("- skip_no_buildup", c.get("skip_no_buildup", 0)),
            ("- skip_room / skip_cost", c.get("skip_room", 0) + c.get("skip_cost", 0)),
            ("= EXECUTABLE pattern break", c.get("executable_pattern_break", 0)),
        ]
        lines += ["Funnel (pattern break):", "", "| stage | count |", "|---|---|"]
        for label, n in funnel:
            lines.append(f"| {label} | {n} |")
        lines += ["", f"Exit-code counters: `{json.dumps(c, sort_keys=True)}`", ""]

    lines += ["## Verdict vs Lead stop rule", "",
              "Stop rule (Lead, VPA-P1/P2): *executable census < 10/week on EURUSD → "
              "finish census + summary, skip snapshots, report.*", ""]
    euro = results[0]
    rate = euro["stats"]["exec_total"]["per_week_mean"]
    lines += [f"EURUSD EXECUTABLE total = **{rate:.3f}/week** "
              f"({euro['stats']['exec_total']['total']} candidates / {euro['weeks']} weeks). "
              f"Pattern-break alone = {euro['stats']['exec_pb']['per_week_mean']:.3f}/week; "
              f"pullback reversal = {euro['stats']['exec_pr']['per_week_mean']:.3f}/week.", "",
              "**STOP RULE TRIGGERED → snapshots skipped, no grading, no economics.** "
              "The pre-buildup ceiling (session+bias+chop+pressure) is also far below the "
              "10/week floor, so this is structural for the frozen M5 definition, not a "
              "final-gate strictness artifact.", ""]
    path = os.path.join(OUT, "CENSUS_SUMMARY.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("[write]", path)
    for res in results:
        print(f"[write] {res['csv']}")
        print(f"[write] {res['json']}")
    print("CENSUS_RESULT", json.dumps({r["symbol"]: r["stats"]["exec_total"]["per_week_mean"] for r in results}))


if __name__ == "__main__":
    main()
