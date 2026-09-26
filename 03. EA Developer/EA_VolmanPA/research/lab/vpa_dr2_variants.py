"""DR2 candidate variants: census cadence + funnel + recall acceptance on the
60 BURNED Lead cases (E3: diagnosis only, no fidelity claim). No outcome
fields (E4).

Variants (all on top of DR1 defaults):
  DR1  control
  V1   signal window lower bound relaxed: signal_atr 0.05 -> 0.50
       (book tr. 88/95/103: the signal bar sits in the buildup, its extreme
        is the trigger; the break bar is the entry bar, not the signal bar)
  V2   V1 + room only to significant obstacles (00/50 grid, PDH/PDL,
       barriers, +-5-bar pivots)   (book tr. 155/167/43)
  V3   V2 + buildup needs 2 of 4 conditions (book tr. 103/223: reference box,
       not rigid geometry)
"""

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PKG = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(PKG, "PLAN", "diag_dr1")
GRADING = os.path.join(PKG, "PLAN", "grading")

from vpa_data import load_m5_bars  # noqa: E402
from vpa_dr1 import run_dr1  # noqa: E402
from vpa_trace import classify_cases  # noqa: E402

VARIANTS = [
    ("DR1", {}),
    # exploratory ladder (diagnosis, not proposals)
    ("V1_signal_lo_0.50", {"signal_atr": 0.50}),
    ("V2_V1_room_sig", {"signal_atr": 0.50, "room_significant_only": True, "room_include_pdh": True}),
    ("V3_V2_buildup_2of4", {"signal_atr": 0.50, "room_significant_only": True,
                            "room_include_pdh": True, "buildup_min_conditions": 2}),
    # DR2 candidates
    ("DR2a_sig_sess", {"signal_atr": 0.50, "eu": (300, 660), "us": (690, 1050)}),
    ("DR2b_a_room_sig", {"signal_atr": 0.50, "eu": (300, 660), "us": (690, 1050),
                         "room_significant_only": True, "room_include_pdh": True}),
    ("DR2c_b_prev_bar", {"signal_atr": 0.50, "eu": (300, 660), "us": (690, 1050),
                         "room_significant_only": True, "room_include_pdh": True,
                         "signal_prev_bar": True}),
    ("DR2d_c_buildup_2of4", {"signal_atr": 0.50, "eu": (300, 660), "us": (690, 1050),
                             "room_significant_only": True, "room_include_pdh": True,
                             "signal_prev_bar": True, "buildup_min_conditions": 2}),
    # bound, not a candidate: everything off except trend + direction
    ("DR2e_trend_only_bound", {"signal_atr": 0.50, "eu": (300, 660), "us": (690, 1050),
                               "signal_prev_bar": True, "buildup_min_conditions": 0,
                               "room_r_min": 0.0, "adverse_pivot_r": 0.0,
                               "anti_entry_b_atr": 99.0, "anti_signal_range_atr": 99.0,
                               "anti_ema_atr": 99.0}),
]
FUNNEL = ["signal_eval", "skip_trend", "skip_room", "skip_no_buildup", "skip_chop",
          "skip_direction", "skip_anti_chase", "skip_adverse_magnet", "skip_session",
          "skip_missed_break", "chop_exempt_buildup"]


def main():
    os.makedirs(OUT, exist_ok=True)
    bars = load_m5_bars("EURUSD")
    weeks = (bars["t"][-1] - bars["t"][0]) / 604800.0
    key = {r["case_id"]: r for r in csv.DictReader(open(os.path.join(GRADING, "KEY_HIDDEN.csv"), encoding="utf-8"))}
    lead = {r["case_id"]: r for r in csv.DictReader(open(os.path.join(GRADING, "GRADES_LEAD_BLIND.csv"), encoding="utf-8"))}
    cases = []
    for cid, k in key.items():
        if cid not in lead:
            continue
        cases.append({"case_id": cid, "lead_grade": lead[cid]["grade"].strip().upper(),
                      "group": k.get("sample_group"), "setup_v1": k.get("setup"),
                      "bar_idx": int(k["bar_idx"]), "side": int(k["side"]),
                      "barrier_level": float(k["barrier_level"]) if k.get("barrier_level") else None,
                      "atr": float(k["atr"]) if k.get("atr") else None})
    cases.sort(key=lambda c: c["case_id"])
    rows = []
    for name, over in VARIANTS:
        cfg = {"round_grid_price": 50.0 * bars["pip"]}
        cfg.update(over)
        recs, cnt = run_dr1(bars, cfg=cfg)
        ex = sum(1 for r in recs if r.get("executable"))
        d, cls, _ = classify_cases(bars, cases, half=12, cfg=cfg)
        cat_ab = {}
        cat_c = {}
        for r in cls:
            tgt = cat_ab if r["lead_grade"] in ("A", "B") else cat_c
            tgt[r["category"]] = tgt.get(r["category"], 0) + 1
        row = {"variant": name, "exec_total": ex, "per_week": round(ex / weeks, 4),
               "signal_eval": cnt.get("signal_eval", 0),
               "AB_iv": cat_ab.get("(iv) executable", 0),
               "AB_iii": cat_ab.get("(iii) evaluated but failed", 0),
               "AB_ii": cat_ab.get("(ii) no signal eval", 0),
               "AB_i": cat_ab.get("(i) no barrier locked nearby", 0),
               "C_iv": cat_c.get("(iv) executable", 0),
               "C_iii": cat_c.get("(iii) evaluated but failed", 0),
               "C_ii": cat_c.get("(ii) no signal eval", 0),
               "C_i": cat_c.get("(i) no barrier locked nearby", 0)}
        for f in FUNNEL:
            row["fn_" + f] = cnt.get(f, 0)
        rows.append(row)
        print(f"[{name}] exec={ex} per_week={row['per_week']} "
              f"AB iv/iii/ii/i = {row['AB_iv']}/{row['AB_iii']}/{row['AB_ii']}/{row['AB_i']}  "
              f"C iv/iii/ii/i = {row['C_iv']}/{row['C_iii']}/{row['C_ii']}/{row['C_i']}")
    fields = list(rows[0].keys())
    with open(os.path.join(OUT, "DR2_VARIANTS.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    md = ["# DR2_VARIANTS — cadence + recall on the 60 BURNED cases", "",
          f"DESIGN weeks (span): {weeks:.1f}. Census baseline: exec=1, 0.0032/week. "
          "E3: this set is BURNED; counts here are diagnostic, never fidelity. E4: no outcomes.", "",
          "| variant | exec | /week | AB iv | AB iii | AB ii | AB i | C iv | C iii | C ii | C i |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['variant']} | {r['exec_total']} | {r['per_week']} | {r['AB_iv']} | {r['AB_iii']} | "
                  f"{r['AB_ii']} | {r['AB_i']} | {r['C_iv']} | {r['C_iii']} | {r['C_ii']} | {r['C_i']} |")
    md += ["", "Funnel counters per variant:", "", "| variant | " + " | ".join(FUNNEL) + " |",
           "|---|" + "---|" * len(FUNNEL)]
    for r in rows:
        md.append(f"| {r['variant']} | " + " | ".join(str(r['fn_' + f]) for f in FUNNEL) + " |")
    with open(os.path.join(OUT, "DR2_VARIANTS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("[write]", os.path.join(OUT, "DR2_VARIANTS.csv"))
    print("[write]", os.path.join(OUT, "DR2_VARIANTS.md"))


if __name__ == "__main__":
    main()
