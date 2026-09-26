"""VPA-DR1 recall trace on the 60 Lead-labelled cases (E3, BURNED set).

Runs the DR1 trace once over DESIGN and classifies every labelled case:
  (i) no barrier locked nearby; (ii) no signal eval (with reason);
  (iii) evaluated but failed (full fail set); (iv) executable.
Outputs PLAN/diag_dr1/RECALL_TRACE.csv + RECALL_SUMMARY.md (with the
discrimination table). No outcome fields (E4).
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

GATES = [k for k, _ in GATE_ORDER]


def main():
    os.makedirs(OUT, exist_ok=True)
    bars = load_m5_bars("EURUSD")
    key = {r["case_id"]: r for r in csv.DictReader(open(os.path.join(GRADING, "KEY_HIDDEN.csv"), encoding="utf-8"))}
    lead = {r["case_id"]: r for r in csv.DictReader(open(os.path.join(GRADING, "GRADES_LEAD_BLIND.csv"), encoding="utf-8"))}
    cases = []
    for cid, k in key.items():
        if cid not in lead:
            continue  # trace only the 60 Lead-labelled (BURNED) cases
        g = lead[cid].get("grade", "?").strip().upper()
        cases.append({
            "case_id": cid, "lead_grade": g, "group": k.get("sample_group"),
            "setup_v1": k.get("setup"), "bar_idx": int(k["bar_idx"]),
            "side": int(k["side"]), "barrier_level": float(k["barrier_level"]) if k.get("barrier_level") else None,
            "atr": float(k["atr"]) if k.get("atr") else None,
        })
    cases.sort(key=lambda c: c["case_id"])
    print(f"cases={len(cases)} A/B={sum(1 for c in cases if c['lead_grade'] in ('A','B'))} "
          f"C={sum(1 for c in cases if c['lead_grade']=='C')}")

    d, rows, counters = classify_cases(bars, cases, half=12)
    write_csv(os.path.join(OUT, "RECALL_TRACE.csv"), rows)

    ab = [r for r in rows if r["lead_grade"] in ("A", "B")]
    cc = [r for r in rows if r["lead_grade"] == "C"]
    cat = collections.Counter(r["category"] for r in rows)
    cat_ab = collections.Counter(r["category"] for r in ab)
    cat_c = collections.Counter(r["category"] for r in cc)

    def eval_rows(rs):
        return [r for r in rs if r["category"] in ("(iii) evaluated but failed", "(iv) executable")]

    ab_e, c_e = eval_rows(ab), eval_rows(cc)
    disc = []
    for g in GATES:
        f_ab = sum(1 for r in ab_e if g in (r["fail_set"] or "").split(";"))
        f_c = sum(1 for r in c_e if g in (r["fail_set"] or "").split(";"))
        disc.append({"gate": g, "fail_AB": f_ab, "n_AB": len(ab_e),
                     "rate_AB": round(f_ab / len(ab_e), 3) if ab_e else None,
                     "fail_C": f_c, "n_C": len(c_e),
                     "rate_C": round(f_c / len(c_e), 3) if c_e else None})

    md = ["# RECALL_SUMMARY — DR1 vs the Lead's eye (60 BURNED cases, E3)", "",
          "Source: `RECALL_TRACE.csv` (one row per case, full gate values). "
          "No outcome fields (E4). Set burned: no selection/fidelity use (E3).", "",
          "## 1. Categories (i)-(iv)", "",
          "| category | all | Lead A/B (16) | Lead C (44) |", "|---|---|---|---|"]
    for c in ["(i) no barrier locked nearby", "(ii) no signal eval",
              "(iii) evaluated but failed", "(iv) executable"]:
        md.append(f"| {c} | {cat.get(c,0)} | {cat_ab.get(c,0)} | {cat_c.get(c,0)} |")
    md += ["", "Reasons for (ii):", ""]
    for r in rows:
        if r["category"] == "(ii) no signal eval":
            md.append(f"- {r['case_id']} ({r['lead_grade']}): {r['reason']}")
    md += ["", "## 2. Discrimination table (evaluated cases only)", "",
           "A gate that fails most A/B cases is mis-specified; one that fails C much more "
           "than A/B is a good discriminator; equal failure is noise.", "",
           "| gate | fail A/B | rate A/B | fail C | rate C | rate gap (C-AB) |", "|---|---|---|---|---|---|"]
    for r in disc:
        md.append(f"| {r['gate']} | {r['fail_AB']}/{r['n_AB']} | {r['rate_AB']} | "
                  f"{r['fail_C']}/{r['n_C']} | {r['rate_C']} | "
                  f"{(r['rate_C'] - r['rate_AB']) if (r['rate_AB'] is not None and r['rate_C'] is not None) else None} |")
    md += ["", "## 3. Reading", "",
           f"- Lead A/B cases with an evaluation: {len(ab_e)}/16; Lead C: {len(c_e)}/44.",
           f"- A/B lost before evaluation: (i) {cat_ab.get('(i) no barrier locked nearby',0)}, "
           f"(ii) {cat_ab.get('(ii) no signal eval',0)}.",
           f"- C lost before evaluation: (i) {cat_c.get('(i) no barrier locked nearby',0)}, "
           f"(ii) {cat_c.get('(ii) no signal eval',0)}.", ""]
    with open(os.path.join(OUT, "RECALL_SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("[write]", os.path.join(OUT, "RECALL_TRACE.csv"))
    print("[write]", os.path.join(OUT, "RECALL_SUMMARY.md"))
    print("categories:", dict(cat))
    print("categories A/B:", dict(cat_ab))
    print("categories C:", dict(cat_c))
    for r in disc:
        print(f"  {r['gate']:14s} AB {r['fail_AB']}/{r['n_AB']} ({r['rate_AB']})  "
              f"C {r['fail_C']}/{r['n_C']} ({r['rate_C']})  gap {r['rate_C'] - r['rate_AB'] if (r['rate_AB'] is not None and r['rate_C'] is not None) else None}")


if __name__ == "__main__":
    main()
