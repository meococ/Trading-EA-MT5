"""VPA-P2b — validate/compile pass-1 grades and run the pre-registered analysis.

Inputs : PLAN/grading/GRADES_LLM_PASS1_RAW.txt, KEY_HIDDEN.csv
Outputs: PLAN/grading/GRADES_LLM_PASS1.csv (+ SHA printed), PLAN/grading/G2_FREQUENCY_ESTIMATE.md
Rule  : PLAN/GRADING_PREREG.md (frozen). No outcomes, no PnL.
"""

import csv
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(os.path.dirname(HERE))
G = os.path.join(PKG, "PLAN", "grading")

FRAME_SRS = 9776          # in-session raw breaks with 120-bar drawing history
WEEKS = 314.0
FRAME_RATE = FRAME_SRS / WEEKS     # 31.1338/week (prereg used 9,778/314 = 31.14)
P_STAR_KILL = 10.0 / FRAME_RATE    # p at which point estimate hits the GOAL floor
Z = 1.959963984540054


def wilson(k, n):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    denom = 1.0 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / denom
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / denom
    return p, max(0.0, centre - half), min(1.0, centre + half)


def n_needed(p, target=0.3212):
    n = 1
    while n < 100000:
        _, _, ub = wilson(round(p * n), n)
        if ub < target:
            return n
        n += 1
    return None


def main():
    raw = open(os.path.join(G, "GRADES_LLM_PASS1_RAW.txt"), encoding="utf-8").read().splitlines()
    rows, seen = [], set()
    for ln in raw:
        ln = ln.strip()
        if not ln:
            continue
        parts = ln.split(",", 2)
        assert len(parts) == 3, f"bad line: {ln[:80]}"
        cid, grade, reason = parts[0].strip(), parts[1].strip(), parts[2].strip()
        assert cid.startswith("case_") and grade in ("A", "B", "C"), f"bad row: {ln[:80]}"
        assert cid not in seen, f"duplicate {cid}"
        seen.add(cid)
        rows.append({"case_id": cid, "grade": grade, "reason": reason})
    assert len(rows) == 200, f"expected 200 rows, got {len(rows)}"
    missing = [f"case_{i:03d}" for i in range(1, 201) if f"case_{i:03d}" not in seen]
    assert not missing, f"missing {missing[:5]}"
    rows.sort(key=lambda r: r["case_id"])

    csv_path = os.path.join(G, "GRADES_LLM_PASS1.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["case_id", "grade", "reason"])
        w.writeheader()
        w.writerows(rows)
    sha = hashlib.sha256(open(csv_path, "rb").read()).hexdigest().upper()
    print("GRADES_LLM_PASS1_SHA256", sha)

    key = {r["case_id"]: r for r in csv.DictReader(open(os.path.join(G, "KEY_HIDDEN.csv"), encoding="utf-8"))}
    for r in rows:
        r["group"] = key[r["case_id"]]["sample_group"]
        r["stage"] = key[r["case_id"]]["funnel_stage"]
        r["setup"] = key[r["case_id"]]["setup"]
        r["session"] = key[r["case_id"]]["session"]
        r["side"] = key[r["case_id"]]["side"]

    def counts(rs):
        n = len(rs)
        c = {"A": 0, "B": 0, "C": 0}
        for r in rs:
            c[r["grade"]] += 1
        k = c["A"] + c["B"]
        p, lo, hi = wilson(k, n)
        return n, c, k, p, lo, hi

    srs = [r for r in rows if r["group"] == "srs"]
    ex = [r for r in rows if r["group"] == "exec"]
    n_s, c_s, k_s, p_s, lo_s, hi_s = counts(srs)
    n_e, c_e, k_e, p_e, lo_e, hi_e = counts(ex)

    verdict, detail = "PENDING", ""
    if hi_s * FRAME_RATE < 10.0:
        verdict = "KILL (pre-registered)"
        detail = f"Wilson upper {hi_s:.3f} x {FRAME_RATE:.2f} = {hi_s * FRAME_RATE:.1f}/week < 10"
    elif p_s * FRAME_RATE >= 10.0:
        verdict = "VPA-DR1 JUSTIFIED (pre-registered)"
        detail = f"point {p_s:.3f} x {FRAME_RATE:.2f} = {p_s * FRAME_RATE:.1f}/week >= 10"
    else:
        verdict = "INCONCLUSIVE (pre-registered)"
        nn = n_needed(p_s)
        detail = (f"point {p_s:.3f} x {FRAME_RATE:.2f} = {p_s * FRAME_RATE:.1f}/week < 10 but "
                  f"Wilson upper {hi_s:.3f} x {FRAME_RATE:.2f} = {hi_s * FRAME_RATE:.1f}/week >= 10; "
                  f"N* ~= {nn}")

    # cross-tab: grade x funnel stage for SRS
    stages = ["executable", "skip_no_buildup", "skip_no_pressure", "skip_chop", "skip_bias"]
    xtab = {s: {"A": 0, "B": 0, "C": 0, "n": 0} for s in stages}
    for r in srs:
        if r["stage"] in xtab:
            xtab[r["stage"]][r["grade"]] += 1
            xtab[r["stage"]]["n"] += 1

    exec_by_setup = {}
    for r in ex:
        d = exec_by_setup.setdefault(r["setup"], {"A": 0, "B": 0, "C": 0, "n": 0})
        d[r["grade"]] += 1
        d["n"] += 1

    by_session = {}
    for r in srs:
        d = by_session.setdefault(r["session"], {"A": 0, "B": 0, "C": 0, "n": 0})
        d[r["grade"]] += 1
        d["n"] += 1
    by_side = {}
    for r in srs:
        d = by_side.setdefault(r["side"], {"A": 0, "B": 0, "C": 0, "n": 0})
        d[r["grade"]] += 1
        d["n"] += 1

    md = []
    md += ["# G2_FREQUENCY_ESTIMATE — VPA-P2b (pre-registered analysis)", "",
           "Status: `PENDING LEAD ADJUDICATION` · Rule: `PLAN/GRADING_PREREG.md` "
           "(SHA256 `1355630CB1C7C28E398E734C1DBCE3FA988D19BE5BA3B9C4EA205168EFD95020`) · "
           "pass-1 grades: `GRADES_LLM_PASS1.csv` (SHA256 `" + sha + "`).", "",
           "All numbers below are derived from blind pass-1 grades joined with the hidden key AFTER grading. "
           "No outcome, no PnL, no MT5. The Lead-adjudicated grade is final; this is a preliminary verdict.", ""]
    md += ["## 1. Sample sizes and rates", "",
           f"- SRS group (in-session raw breaks): n={n_s} · A={c_s['A']} B={c_s['B']} C={c_s['C']} · "
           f"p(A+B)={p_s:.3f} · Wilson 95% CI [{lo_s:.3f}, {hi_s:.3f}]",
           f"- Executable group: n={n_e} · A={c_e['A']} B={c_e['B']} C={c_e['C']} · "
           f"p(A+B)={p_e:.3f} · Wilson 95% CI [{lo_e:.3f}, {hi_e:.3f}]", "",
           f"Frame rate: {FRAME_SRS:,} in-session breaks / {WEEKS:.0f} weeks = **{FRAME_RATE:.2f}/week**. "
           f"GOAL floor 10/week requires p* = 10/{FRAME_RATE:.2f} = **{P_STAR_KILL:.4f}**.", ""]
    md += ["## 2. Implied A+B cadence", "",
           f"- point: {p_s:.3f} x {FRAME_RATE:.2f} = **{p_s * FRAME_RATE:.2f}/week** "
           f"(CI {lo_s * FRAME_RATE:.2f} to {hi_s * FRAME_RATE:.2f})", ""]
    md += ["## 3. Cross-tab grade x funnel stage (SRS)", "",
           "| funnel stage | n | A | B | C | A+B rate |", "|---|---|---|---|---|---|"]
    for s in stages:
        d = xtab[s]
        rate = (d["A"] + d["B"]) / d["n"] if d["n"] else 0.0
        md.append(f"| {s} | {d['n']} | {d['A']} | {d['B']} | {d['C']} | {rate:.2f} |")
    md += ["", "By session (SRS):", "", "| session | n | A+B | rate |", "|---|---|---|---|"]
    for s, d in by_session.items():
        md.append(f"| {s} | {d['n']} | {d['A'] + d['B']} | {(d['A'] + d['B']) / d['n']:.2f} |")
    md += ["", "By side (SRS):", "", "| side | n | A+B | rate |", "|---|---|---|---|"]
    for s, d in by_side.items():
        md.append(f"| {s} | {d['n']} | {d['A'] + d['B']} | {(d['A'] + d['B']) / d['n']:.2f} |")
    md += ["", "Executable group by setup (detector precision proxy):", "",
           "| setup | n | A | B | C | A+B rate |", "|---|---|---|---|---|---|"]
    for s, d in exec_by_setup.items():
        rate = (d["A"] + d["B"]) / d["n"] if d["n"] else 0.0
        md.append(f"| {s} | {d['n']} | {d['A']} | {d['B']} | {d['C']} | {rate:.2f} |")
    md += ["", "## 4. Preliminary verdict (PENDING LEAD ADJUDICATION)", "",
           f"**{verdict}** — {detail}.", "",
           "Pre-registered boundaries: KILL if Wilson-upper x 31.13 < 10/week; DR1 if point x 31.13 >= 10/week; "
           "otherwise INCONCLUSIVE with N*. The drawing constraint excluded 2 early in-session breaks without "
           "120 bars of history (9,778 -> 9,776; the prereg's 31.14 becomes 31.13; the decision boundaries are "
           "unchanged at 0.03% scale).", "",
           "Notes: (a) pass-1 is the worker-LLM grading; the Lead's independent blind subset is the adjudicating "
           "grade; (b) the executable-group rate is a precision proxy for the current detector, not a cadence; "
           "(c) no case's future bars were drawn or consulted."]
    out = os.path.join(G, "G2_FREQUENCY_ESTIMATE.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("wrote", out)
    print(json.dumps({"srs": {"n": n_s, "A": c_s["A"], "B": c_s["B"], "C": c_s["C"], "p": p_s,
                              "ci": [lo_s, hi_s], "cadence": p_s * FRAME_RATE},
                      "exec": {"n": n_e, "A": c_e["A"], "B": c_e["B"], "C": c_e["C"], "p": p_e,
                               "ci": [lo_e, hi_e]},
                      "verdict": verdict}, indent=2))


if __name__ == "__main__":
    main()
