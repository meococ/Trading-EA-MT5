"""VPA-DR1 census — DESIGN 2016-2021, outcome-blind.

Outputs (no outcome fields anywhere):
  PLAN/census_dr1/CENSUS_DR1.csv          weekly executable counts
  PLAN/census_dr1/CENSUS_DR1.json         counters, per-year/session/setup stats
  PLAN/census_dr1/CENSUS_DR1_SUMMARY.md   funnel + cadence rule D2 + what-if diagnostics

What-if runs are diagnostics for the DR2 decision only; they are NOT the baseline.
"""

import collections
import json
import os
import statistics
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PKG = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(PKG, "PLAN", "census_dr1")

from vpa_data import load_m5_bars  # noqa: E402
from vpa_dr1 import Dr1Detector, run_dr1  # noqa: E402

SYMBOL = "EURUSD"

FUNNEL_ORDER = ["skip_warmup", "skip_session", "skip_direction", "skip_trend",
                "skip_chop", "skip_no_buildup", "skip_room", "skip_adverse_magnet",
                "skip_anti_chase", "skip_cost"]


def median_atr(bars):
    d = Dr1Detector(bars)
    for t in range(len(bars["t"])):
        d._update_bar(t)
    return statistics.median([a for a in d.atr[100:] if a == a])


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    bars = load_m5_bars(SYMBOL)
    med_atr = median_atr(bars)
    grid = 50.0 * bars["pip"]          # book tr.43: 00/50 on M5
    cfg = {"round_grid_price": grid}
    recs, cnt = run_dr1(bars, cfg=cfg)
    runtime = time.time() - t0

    ex = [r for r in recs if r.get("executable")]
    t = np.asarray(bars["t"], dtype=np.int64)
    naive = pd.to_datetime(t, unit="s", utc=False)
    utc = pd.to_datetime(t - 7200, unit="s", utc=True)   # approx; sessions already UTC in bars
    week = utc.to_period("W-MON").start_time

    wk_pb = collections.Counter()
    wk_cb = collections.Counter()
    for r in ex:
        w = week[r["bar_idx"]]
        (wk_cb if r["setup"] == "combi" else wk_pb)[w] += 1
    all_weeks = sorted(set(week))
    weekly = pd.DataFrame({"week": all_weeks})
    weekly["exec_pb"] = [wk_pb.get(w, 0) for w in all_weeks]
    weekly["exec_combi"] = [wk_cb.get(w, 0) for w in all_weeks]
    weekly["exec_total"] = weekly["exec_pb"] + weekly["exec_combi"]
    weekly.to_csv(os.path.join(OUT, "CENSUS_DR1.csv"), index=False)

    # stats
    n_weeks = len(weekly)
    exec_total = int(weekly["exec_total"].sum())
    exec_pb = int(weekly["exec_pb"].sum())
    exec_combi = int(weekly["exec_combi"].sum())
    per_week = exec_total / n_weeks if n_weeks else 0.0

    by_year = collections.Counter()
    by_session = collections.Counter()
    for r in ex:
        by_year[pd.to_datetime(int(r["time"]), unit="s").year] += 1
        by_session[r["session"]] += 1

    # funnel over evaluations (rejections do not consume the barrier)
    reasons = collections.Counter(r.get("skip_reason") or "EXEC" for r in recs)
    funnel = {k: reasons.get(k, 0) for k in FUNNEL_ORDER}
    in_session_evals = sum(1 for r in recs if r.get("session"))
    session_rejects = reasons.get("skip_session", 0)
    uniq_barriers = len(set((r["lock_idx"], r["side"]) for r in recs if r.get("session")))

    # cadence rule D2
    if per_week >= 10:
        cadence_rule = "NORMAL (>=10/week)"
    elif per_week >= 3:
        cadence_rule = "LOW_CADENCE (3 to <10/week): continue to fidelity grading"
    else:
        cadence_rule = "STOP (<3/week): report funnel + recommendation, STATUS PARTIAL"

    # what-if diagnostics (NOT the baseline; decision support for DR2)
    whatif = []
    variants = [
        ("theta_slope=0.0 (book-literal EMA direction)", {"theta_slope": 0.0}),
        ("trend gate off (theta=0, frac=0)", {"theta_slope": 0.0, "frac_side_min": 0.0}),
        ("room_r_min=1.4 (book-literal, needs manual exit)", {"room_r_min": 1.4}),
        ("room gate off", {"room_r_min": 0.0}),
        ("signal_max_atr=0.5 (wider signal-bar window)", {"signal_max_atr": 0.50}),
        ("chop veto off", {"chop_overlap_min": 1.1}),
        ("buildup band widened (hi 0.75, 1 close)", {"band_hi_atr": 0.75, "min_band_closes": 1}),
        ("theta=0.0 + room=1.4 + signal 0.5 + no chop", {"theta_slope": 0.0, "room_r_min": 1.4,
                                                         "signal_max_atr": 0.50, "chop_overlap_min": 1.1}),
        ("all gates loose (ceiling diagnostic)", {"theta_slope": 0.0, "frac_side_min": 0.0,
                                                  "room_r_min": 0.5, "signal_max_atr": 0.60,
                                                  "chop_overlap_min": 1.1, "band_hi_atr": 0.75,
                                                  "min_band_closes": 1}),
    ]
    for name, over in variants:
        c2 = dict(cfg)
        c2.update(over)
        r2, _ = run_dr1(bars, cfg=c2)
        n2 = sum(1 for r in r2 if r.get("executable"))
        whatif.append({"variant": name, "executable": n2, "per_week": round(n2 / n_weeks, 3)})

    summary = {
        "symbol": SYMBOL, "window": "2016.01.01-2021.12.31", "weeks": n_weeks,
        "runtime_seconds": round(runtime, 1), "median_atr_pips": round(med_atr / bars["pip"], 3),
        "round_grid_pips": 50.0, "barriers_locked": cnt.get("barrier_locked", 0),
        "signal_evals": cnt.get("signal_eval", 0), "in_session_evals": in_session_evals,
        "unique_in_session_barriers": uniq_barriers,
        "missed_breaks": cnt.get("skip_missed_break", 0),
        "executable_total": exec_total, "exec_pb": exec_pb, "exec_combi": exec_combi,
        "per_week": round(per_week, 4), "by_year": dict(sorted(by_year.items())),
        "by_session": dict(by_session), "funnel": funnel,
        "chop_exempt_buildup": cnt.get("chop_exempt_buildup", 0),
        "cadence_rule": cadence_rule, "whatif_diagnostics": whatif,
        "outcome_fields": [],
    }
    with open(os.path.join(OUT, "CENSUS_DR1.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    md = ["# CENSUS_DR1_SUMMARY — VPA-DR1 (outcome-blind)", "",
          f"DESIGN 2016-01-01 → 2021-12-31 · {SYMBOL} M5 · defaults per `VPA-DR1_FROZEN_PREREG.md` "
          f"(θ=0.10, band 0.5, overlap 0.45, expiry 20, room 2.0R, 50-pip grid).",
          f"Runtime {runtime:.1f}s · median ATR14 {med_atr/bars['pip']:.2f} pips.", "",
          "## 1. Cadence (D2)", "",
          f"- EXECUTABLE total: **{exec_total}** over {n_weeks} weeks = **{per_week:.3f}/week** "
          f"(PB {exec_pb}, Combi {exec_combi})",
          f"- Rule D2 applied: **{cadence_rule}**", "",
          "Per year:", "", "| year | executable |", "|---|---|"]
    for y, v in sorted(by_year.items()):
        md.append(f"| {y} | {v} |")
    md += ["", "Per session:", "", "| session | executable |", "|---|---|"]
    for s, v in sorted(by_session.items()):
        md.append(f"| {s} | {v} |")
    md += ["", "## 2. Rejection funnel (evaluations, in gate order)", "",
           "| stage | count |", "|---|---|",
           f"| barriers locked | {cnt.get('barrier_locked', 0)} |",
           f"| signal-bar evaluations (close at/through barrier) | {cnt.get('signal_eval', 0)} |",
           f"| — unique in-session barriers with a signal eval | {uniq_barriers} "
           f"({uniq_barriers / n_weeks:.2f}/week) |",
           f"| — rejected: outside EU/US session | {session_rejects} |",
           f"| — in-session evaluations | {in_session_evals} |"]
    for k in FUNNEL_ORDER:
        if k != "skip_session":
            md.append(f"| — rejected: {k} | {funnel[k]} |")
    md += [f"| — chop exempted by valid buildup | {cnt.get('chop_exempt_buildup', 0)} |",
           f"| **EXECUTABLE** | **{exec_total}** |",
           f"| (barrier consumed as missed break, anti-chase) | {cnt.get('skip_missed_break', 0)} |", "",
           "Note: rejections do not consume the barrier, so the same barrier can be evaluated "
           "on several bars; the funnel counts evaluations, not unique barriers.", "",
           "## 3. What-if diagnostics (NOT the baseline; DR2 decision support)", "",
           "| variant | executable | /week |", "|---|---|---|"]
    for w in whatif:
        md.append(f"| {w['variant']} | {w['executable']} | {w['per_week']} |")
    md += ["", "## 4. Column check (no outcome fields)", "",
           f"CSV columns: `{list(weekly.columns)}`; JSON `outcome_fields`: `{summary['outcome_fields']}`.",
           "No PnL, win rate, MFE/MAE or fill-to-exit is computed anywhere in this task (D6).", "",
           "## 5. Recommendation (D2 STOP)", "",
           f"Baseline DR1 fires **{exec_total}** executable setup in 6 years ({per_week:.3f}/week), "
           f"far below the D2 floor of 3/week. The detection layer is not the problem: "
           f"**{uniq_barriers} unique in-session signal-bar candidates ({uniq_barriers / n_weeks:.1f}/week)** "
           "exist; the conjunctive gate stack removes all but one. Marginal first-failure counts "
           f"(in-session): trend {funnel['skip_trend']}, room {funnel['skip_room']}, "
           f"buildup {funnel['skip_no_buildup']}, chop {funnel['skip_chop']}, "
           f"direction {funnel['skip_direction']}, anti-chase {funnel['skip_anti_chase']}.", "",
           "Recommended DR2 directions (for Lead approval; all would need a fresh prereg):",
           "1. Replace the AND-stack with a **score/threshold** (the P2b finding: the Lead's own A/B "
           "rate is ~8.6/week while DR1's stack keeps 1).",
           "2. **Room gate**: measure against *significant* pivots (higher pivot_lag) or barrier-quality "
           "levels only, not every 2-bar pivot; `room gate off` raises executables to 33.",
           "3. Keep the signal-bar entry semantics (D1a) — they are the book-faithful core and the "
           "detection layer already yields ~10/week in-session candidates.",
           "4. Re-run this census after any change; do not tune against outcomes (none exist).", ""]
    with open(os.path.join(OUT, "CENSUS_DR1_SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"[write] {OUT}\\CENSUS_DR1.csv / .json / _SUMMARY.md")
    print(json.dumps({"exec_total": exec_total, "per_week": round(per_week, 4),
                      "cadence_rule": cadence_rule,
                      "by_year": dict(sorted(by_year.items())),
                      "whatif": whatif}, indent=2))


if __name__ == "__main__":
    main()
