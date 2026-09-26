"""Discrimination table for the recommended DR2c config on the 60 BURNED cases.

For every evaluated case, which gates fail it? A gate is useful when it fails
Lead-C much more than Lead-A/B. Writes PLAN/diag_dr1/DISCRIMINATION_DR2C.md.
No outcome fields (E4). E3: burned set, diagnostic only.
"""

import collections
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PKG = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(PKG, "PLAN", "diag_dr1")
GRADING = os.path.join(PKG, "PLAN", "grading")

from vpa_data import load_m5_bars  # noqa: E402
from vpa_trace import classify_cases, write_csv  # noqa: E402
from vpa_dr1 import GATE_ORDER  # noqa: E402

DR2C = {"signal_atr": 0.50, "eu": (300, 660), "us": (690, 1050),
        "room_significant_only": True, "room_include_pdh": True, "signal_prev_bar": True}


def main():
    bars = load_m5_bars("EURUSD")
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
    cfg = {"round_grid_price": 50.0 * bars["pip"]}
    cfg.update(DR2C)
    d, rows, _ = classify_cases(bars, cases, half=12, cfg=cfg)
    write_csv(os.path.join(OUT, "RECALL_TRACE_DR2C.csv"), rows)
    print("[write]", os.path.join(OUT, "RECALL_TRACE_DR2C.csv"))
    ab = [r for r in rows if r["lead_grade"] in ("A", "B") and r["category"].startswith("(iii") or
          (r["lead_grade"] in ("A", "B") and r["category"].startswith("(iv"))]
    cc = [r for r in rows if (r["lead_grade"] == "C" and (r["category"].startswith("(iii") or r["category"].startswith("(iv")))]
    gates = [k for k, _ in GATE_ORDER]
    lines = ["# DISCRIMINATION_DR2C — per-gate fail rates, Lead A/B vs C (BURNED set)", "",
             "Config: DR2c = signal_atr 0.50 + v1 sessions + room_sig/PDH + signal_prev_bar. "
             "Evaluated cases only ((iii)+(iv)). No outcomes (E4); burned set (E3).", "",
             "Source: `RECALL_TRACE_DR2C.csv` (same run, one row per case; the per-gate "
             "cells below are recomputable from its `category` + `fail_set` columns). "
             "NOTE: `RECALL_TRACE.csv` is the DR1-default trace and does NOT reproduce "
             "this table.", "",
             "| gate | fail A/B | rate | fail C | rate | gap (C-AB) |", "|---|---|---|---|---|---|"]
    for g in gates:
        f_ab = sum(1 for r in ab if g in (r["fail_set"] or "").split(";"))
        f_c = sum(1 for r in cc if g in (r["fail_set"] or "").split(";"))
        ra = f_ab / len(ab) if ab else None
        rc = f_c / len(cc) if cc else None
        gap = (rc - ra) if (ra is not None and rc is not None) else None
        lines.append(f"| {g} | {f_ab}/{len(ab)} | {ra:.3f} | {f_c}/{len(cc)} | {rc:.3f} | {gap:+.3f} |")
    ff_ab = collections.Counter(r["first_fail"] for r in ab)
    ff_c = collections.Counter(r["first_fail"] for r in cc)
    lines += ["", f"Evaluated: A/B {len(ab)}/16, C {len(cc)}/44.", "",
              "First-fail histogram (the funnel's binding gate):", "",
              "| first_fail | A/B | C |", "|---|---|---|"]
    for k in sorted(set(ff_ab) | set(ff_c)):
        lines.append(f"| {k} | {ff_ab.get(k, 0)} | {ff_c.get(k, 0)} |")
    with open(os.path.join(OUT, "DISCRIMINATION_DR2C.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("[write]", os.path.join(OUT, "DISCRIMINATION_DR2C.md"))
    for ln in lines:
        print(ln)


if __name__ == "__main__":
    main()
