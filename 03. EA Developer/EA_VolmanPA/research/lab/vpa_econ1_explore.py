"""VPA-ECON-1 — analysis of the ONE verdict run (no re-simulation).

Reads PLAN/econ1/TRADES_DESIGN.csv (x1 fills), ECON1_METRICS.json,
RANDOM_MATCHED.csv + the bars' utc_min (for the news-window sensitivity) and
writes PLAN/econ1/ECON1_RESULTS.md. EXPLORATORY only; no effect on the verdict.
"""

import csv
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PKG = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(PKG, "PLAN", "econ1")

from vpa_data import load_m5_bars  # noqa: E402

PREREG_SHA = "644DBCBA91B9859AF598906C8BB9C7D8CAB034CBCE99675554B48938C5BE9663"
GATES = [
    ("PF x1 > 1.30", "x1", "PF", ">", 1.30),
    ("PF x1.5 >= 1.25", "x1.5", "PF", ">=", 1.25),
    ("PF x2 >= 1.00", "x2", "PF", ">=", 1.00),
    ("gross PF >= 1.10", "gross", "PF", ">=", 1.10),
    ("N >= 500", "x1", "N", ">=", 500),
    ("max DD <= 6%", "x1", "max_dd_pct", "<=", 6.0),
    ("b >= 1.70", "x1", "b", ">=", 1.70),
    ("LIFT x1 >= +14.1pp", "x1", "lift", ">=", 14.1),
    ("LIFT x2 >= +18.2pp", "x2", "lift", ">=", 18.2),
]


def pf(rrs):
    w = sum(r for r in rrs if r > 0)
    l = -sum(r for r in rrs if r < 0)
    return (w / l) if l > 0 else float("inf")


def dd_pct(rrs):
    eq, peak, dd = 1.0, 1.0, 0.0
    for r in rrs:
        eq *= (1 + 0.005 * r)
        peak = max(peak, eq)
        dd = max(dd, (peak - eq) / peak)
    return dd * 100


def stats(rrs):
    if not rrs:
        return {"N": 0, "WR": 0.0, "PF": 0.0, "b": float("nan"), "exp_r": 0.0, "R": 0.0, "dd": 0.0}
    w = [r for r in rrs if r > 0]
    l = [r for r in rrs if r < 0]
    return {"N": len(rrs), "WR": len(w) / len(rrs), "PF": pf(rrs),
            "b": (statistics.mean(w) / abs(statistics.mean(l))) if w and l else float("nan"),
            "exp_r": statistics.mean(rrs), "R": sum(rrs), "dd": dd_pct(rrs)}


def terciles(rows, key):
    vals = sorted(float(v[key]) for v in rows if v.get(key) not in (None, ""))
    if len(vals) < 30:
        return None
    q1, q2 = vals[len(vals) // 3], vals[2 * len(vals) // 3]
    groups = {"low": [], "mid": [], "high": []}
    for v in rows:
        x = v.get(key)
        if x in (None, ""):
            continue
        x = float(x)
        groups["low" if x <= q1 else ("mid" if x <= q2 else "high")].append(float(v["r"]))
    return {k: stats(v) for k, v in groups.items()}, (q1, q2)


def main():
    bars = load_m5_bars("EURUSD")
    um = bars["utc_min"]
    trades = list(csv.DictReader(open(os.path.join(OUT, "TRADES_DESIGN.csv"), encoding="utf-8")))
    metrics = json.load(open(os.path.join(OUT, "ECON1_METRICS.json"), encoding="utf-8"))
    rnd = list(csv.DictReader(open(os.path.join(OUT, "RANDOM_MATCHED.csv"), encoding="utf-8")))
    rows = []
    for t in trades:
        t["r"] = float(t["r"])
        t["sig"] = int(t["signal_bar_idx"])
        t["um"] = int(um[t["sig"]])
        rows.append(t)
    rrs = [t["r"] for t in rows]

    sc = metrics["scenarios"]
    lines = ["# ECON1_RESULTS — first economic baseline of frozen DR3 (DESIGN 2016-2021)", "",
             f"Prereg `research/VPA-DR3_ECON1_PREREG.md` SHA256 `{PREREG_SHA}` (mtime 17:52:06, "
             f"before every file in this directory). DR3 code SHA `{metrics['dr3_code_sha']}`. "
             f"ONE verdict run (G4): no parameter changes, no variants.", "",
             f"Frame: {metrics['frame']['first_bar_utc']} → {metrics['frame']['last_bar_utc']} "
             f"({metrics['frame']['n_m5']} M5 bars, {metrics['frame']['n_m1']} M1 bars). "
             "VAL/OOS/HOLDOUT not loaded (G5).", "",
             f"Signals: {metrics['signals']} DR3-accepted; matched subset {metrics['signals'] - 115} "
             f"(115 signal bars sit outside the session windows while their trigger bar is inside; "
             f"the lift uses the matched subset). Random: K=20 → {metrics['random_entries']} entries, "
             f"{sc['x1']['random']['N']} fills.", ""]

    # 1. verdict table
    lines += ["## 1. Verdict (G6)", "",
              "| gate | scenario | value | threshold | verdict |", "|---|---|---|---|---|"]
    all_pass = True
    for name, scn, field, op, thr in GATES:
        if field == "lift":
            val = sc[scn]["lift_pp"]
            ok = (val >= thr) and (sc[scn]["lift_ci_pp"][0] > 0)
            v = f"{val:+.2f}pp (CI [{sc[scn]['lift_ci_pp'][0]:+.2f}, {sc[scn]['lift_ci_pp'][1]:+.2f}])"
        else:
            val = sc[scn]["signals"][field]
            ok = (val > thr) if op == ">" else ((val >= thr) if op == ">=" else (val <= thr))
            v = f"{val:.3f}" if isinstance(val, float) else str(val)
        all_pass = all_pass and ok
        lines.append(f"| {name} | {scn} | {v} | {op} {thr} | {'PASS' if ok else 'FAIL'} |")
    lines += ["", f"**VERDICT: {'PASS' if all_pass else 'FAIL'}** "
              "(G6: any gate fails → FAIL; the Lead escalates to the Owner).", ""]

    # 2. metrics per scenario
    lines += ["## 2. Metrics per cost scenario", "",
              "| scenario | N | WR | PF | b | exp R | total R | max DD @0.5% | TP/SL/DAILY/FRIDAY/MIDNIGHT/DATA_END |",
              "|---|---|---|---|---|---|---|---|---|"]
    for name in ("gross", "x1", "x1.5", "x2"):
        s = sc[name]["signals"]
        lines.append(f"| {name} | {s['N']} | {s['WR']*100:.2f}% | {s['PF']:.3f} | {s['b']:.3f} | "
                     f"{s['exp_r']:+.4f} | {s['R_total']:+.1f} | {s['max_dd_pct']:.2f}% | "
                     f"{s['n_tp']}/{s['n_sl']}/{s['n_daily']}/{s['n_friday']}/{s['n_midnight']}/{s['n_data_end']} |")
    lines += ["", "Matched random (same engine/bracket):", "",
              "| scenario | N | WR | PF | b | lift vs DR3 | 95% CI |", "|---|---|---|---|---|---|---|"]
    for name in ("gross", "x1", "x1.5", "x2"):
        r = sc[name]["random"]
        lines.append(f"| {name} | {r['N']} | {r['WR']*100:.2f}% | {r['PF']:.3f} | {r['b']:.3f} | "
                     f"{sc[name]['lift_pp']:+.2f}pp | [{sc[name]['lift_ci_pp'][0]:+.2f}, {sc[name]['lift_ci_pp'][1]:+.2f}] |")
    lines += ["", "Signal status counts (cost-independent): `" +
              json.dumps(metrics["status_counts"]["x1"], sort_keys=True) + "`", ""]

    # 3. equity/DD summary
    x1 = sc["x1"]["signals"]
    lines += ["## 3. Equity / DD summary (x1)", "",
              f"- Fills {x1['N']}; final equity at 0.5%/trade: **{x1['final_eq']*100:.1f}%** of start; "
              f"max DD **{x1['max_dd_pct']:.2f}%** (gate ≤ 6%).",
              f"- Gross (no cost) final equity {sc['gross']['signals']['final_eq']*100:.1f}%, "
              f"max DD {sc['gross']['signals']['max_dd_pct']:.2f}%.",
              f"- Realised b {x1['b']:.3f} (gate ≥ 1.70 PASS); the failure is the win rate, not the payoff.", ""]

    # 4. per-year
    lines += ["## 4. Per-year (x1 fills)", "", "| year | N | WR | PF | total R |", "|---|---|---|---|---|"]
    for y in sorted(set(t["year"] for t in rows)):
        s = stats([t["r"] for t in rows if t["year"] == y])
        lines.append(f"| {y} | {s['N']} | {s['WR']*100:.1f}% | {s['PF']:.3f} | {s['R']:+.1f} |")

    # 5. EXPLORATORY
    lines += ["", "## 5. EXPLORATORY (no effect on the verdict; DR4 hypotheses only)", "",
              f"Baseline x1: WR {x1['WR']*100:.2f}%, PF {x1['PF']:.3f}, N {x1['N']}.", "",
              "| feature | low | mid | high |", "|---|---|---|---|"]
    for key in ("room_r", "ema_dist_atr", "gap_atr"):
        res = terciles(rows, key)
        if res:
            g, qs = res
            lines.append(f"| {key} (q1={qs[0]:.3g}, q2={qs[1]:.3g}) | " +
                         " | ".join(f"N{g[k]['N']} WR{g[k]['WR']*100:.1f}% PF{g[k]['PF']:.2f}" for k in ("low", "mid", "high")) + " |")
    for key, label in (("squeeze", "squeeze=1"), ("lunch", "lunch=1"), ("pressure", "pressure=1")):
        a = stats([t["r"] for t in rows if t[key] == "1"])
        b = stats([t["r"] for t in rows if t[key] == "0"])
        lines.append(f"| {label} vs 0 | N{a['N']} WR{a['WR']*100:.1f}% PF{a['PF']:.2f} | "
                     f"N{b['N']} WR{b['WR']*100:.1f}% PF{b['PF']:.2f} | — |")
    for key, label in (("session", "session"), ("setup", "setup"), ("side", "side")):
        vals = sorted(set(t[key] for t in rows))
        cells = " | ".join(f"{v}: N{stats([t['r'] for t in rows if t[key]==v])['N']} "
                           f"WR{stats([t['r'] for t in rows if t[key]==v])['WR']*100:.1f}% "
                           f"PF{stats([t['r'] for t in rows if t[key]==v])['PF']:.2f}" for v in vals)
        lines.append(f"| {label} | {cells} | | |")
    # sensitivities
    news = [t for t in rows if (745 <= t["um"] < 765) or (805 <= t["um"] < 825)]
    gap = [t for t in rows if t["gap_atr"] not in (None, "") and float(t["gap_atr"]) > 0.3]
    sn = stats([t["r"] for t in rows if t not in news])
    sg = stats([t["r"] for t in rows if t not in gap])
    fr = [t for t in rows if t["reason"] == "FRIDAY"]
    sf = stats([t["r"] for t in rows if t["reason"] != "FRIDAY"])
    lines += ["", "Sensitivities (same trades, no re-run):", "",
              f"- News-window exclusion (12:25-12:45 / 13:25-13:45 UTC): removes {len(news)} fills → "
              f"N {sn['N']}, WR {sn['WR']*100:.2f}%, PF {sn['PF']:.3f}.",
              f"- HYP §3.3 gap recheck (>0.3 ATR): would remove {len(gap)} fills → "
              f"N {sg['N']}, WR {sg['WR']*100:.2f}%, PF {sg['PF']:.3f}.",
              f"- Thursday/Friday calendar deviation (see §6): excluding the {len(fr)} FRIDAY-reason "
              f"fills → N {sf['N']}, WR {sf['WR']*100:.2f}%, PF {sf['PF']:.3f} (the deviation is "
              f"slightly favourable to DR3; verdict unchanged).",
              "", "No outcome fields other than the trade P&L are present; the run is DESIGN-only (G5)."]

    # 6. deviations (review round-1 findings, documented not re-run)
    lines += ["", "## 6. DEVIATIONS & CORRECTIONS (post-review, no re-simulation)", "",
              "1. **Recorded prereg SHA was a 63-char transcription error.** The file's true SHA256 is "
              f"`{PREREG_SHA}` (mtime 17:52:06, earlier than every outcome file — the ordering evidence "
              "is the file hash + mtime, both verified). The wrong string was recorded in "
              "`vpa_econ1_run.py:29`, `vpa_econ1_explore.py:21`, this file's §0 line and "
              "`ECON1_METRICS.json`'s `prereg_sha`; all four were corrected after review round 1. "
              "The prereg itself was NOT edited after the freeze.",
              "2. **Thursday/Friday calendar deviation (inherited from the frozen P1 baseline).** The "
              "weekday formula `((t//86400)+4)%7` used by `vpa_random_baseline.py:157` and inherited by "
              "`vpa_econ1_sim.py` is Sunday=0, so the `dow == 4` branch labelled \"Friday\" fires on "
              "**Thursday** 20:00 server. Effect: the Friday veto (22 signals) and the FRIDAY flat (61 "
              "exits) act on Thursday; real Friday 20:00 has no special flat (the DAILY 22:00 flat "
              "still caps the day). The DR3 and matched-random sides use the identical rule, so the "
              "LIFT is unaffected; the sensitivity above shows the verdict is unaffected (PF 0.784 vs "
              "0.795). Per G4 (one run) the semantics were NOT re-run; a corrected `dow` is a DR4 fix.",
              "3. `TRADES_DESIGN.csv` holds the x1 fills (one row per fill, with `cost_mult`/`cost_pips` "
              "and the exit reason); the gross/x1.5/x2 aggregates are in `ECON1_METRICS.json` from the "
              "same run.",
              "4. 115 of the 4,331 DR3 signals have their SIGNAL bar outside the session windows while "
              "their trigger bar is inside (the DR3 session gate is measured at the trigger bar). The "
              "matched-random universe skips those signal bars; the LIFT therefore uses the matched "
              "subset (4,216 signals); the strategy metrics use all fills.",
              "5. Within-bar assumption: the exit scan includes the fill M1 bar itself (SL-before-TP "
              "inside it), matching the frozen baseline convention — not intra-bar path truth.",
              ""]
    with open(os.path.join(OUT, "ECON1_RESULTS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(x.encode("ascii", "replace").decode("ascii") for x in lines[:20]))
    print("[write]", os.path.join(OUT, "ECON1_RESULTS.md"))


if __name__ == "__main__":
    main()
