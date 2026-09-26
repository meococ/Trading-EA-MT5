"""VPA-DR3 fidelity: unblind after the hash record; A/B shares, Newcombe CI, F5 gate.

Reads GRADES_V3_G1/G2/G3 + KEY_HIDDEN_DR3 (unblinding happens HERE, after
HASHES_BEFORE_UNBLIND.txt). Writes FIDELITY_DR3.md. No outcome fields (F7/E4).
"""

import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(os.path.dirname(HERE))
D = os.path.join(PKG, "PLAN", "grading_dr3")
ORDER = {"A": 0, "B": 1, "C": 2}


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def newcombe_diff(k1, n1, k2, n2, z=1.96):
    """95% CI for p1 - p2 (Newcombe method 10)."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1, z)
    l2, u2 = wilson(k2, n2, z)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return d, lo, hi


def main():
    g = {}
    for tag in ("G1", "G2", "G3"):
        p = os.path.join(D, f"GRADES_V3_{tag}.csv")
        g[tag] = {r["case_id"]: r["grade"].strip().upper() for r in csv.DictReader(open(p, encoding="utf-8"))}
    key = {r["case_id"]: r for r in csv.DictReader(open(os.path.join(D, "KEY_HIDDEN_DR3.csv"), encoding="utf-8"))}
    rows = []
    n3way = 0
    for cid, k in key.items():
        a, b = g["G1"][cid], g["G2"][cid]
        if a == b:
            dual = maj = a
        else:
            dual = None
            c = g["G3"].get(cid)
            votes = [a, b, c]
            top = max(set(votes), key=votes.count)
            if votes.count(top) >= 2:
                maj = top
            else:
                maj = sorted(votes, key=lambda x: ORDER[x])[1]   # no majority -> median
                n3way += 1
        rows.append({"case_id": cid, "group": k["group"], "g1": a, "g2": b,
                     "g3": g["G3"].get(cid), "dual": dual, "majority": maj})

    def share(sel, field):
        r = [x for x in rows if x["group"] == sel and x[field] is not None]
        ab = sum(1 for x in r if x[field] in ("A", "B"))
        return ab, len(r)

    out = []
    for field in ("dual", "majority"):
        ka, na = share("accepted", field)
        kr, nr = share("rejected", field)
        d, lo, hi = newcombe_diff(ka, na, kr, nr)
        gate = (d >= 0.15) and (lo > 0) and (ka / na >= 0.40)
        out.append({"field": field, "acc": (ka, na), "rej": (kr, nr),
                    "share_acc": ka / na, "share_rej": kr / nr, "diff": d, "ci": (lo, hi), "gate": gate})
    n_ab = sum(1 for x in rows if x["group"] == "accepted")
    md = ["# FIDELITY_DR3 — accepted vs rejected (blind, 180 cases, F5)", "",
          "Hash-before-unblind: `HASHES_BEFORE_UNBLIND.txt` (G1 5bef16c7…, G2 7df3c09a…, "
          "written before this join). G3 graded the 60 disagreements only (21/21/18); "
          f"no-majority 3-way splits: {n3way} (median fallback, documented).", "",
          f"Sample: 120 accepted + 60 rejected (trend 51, integrity 9), 30/year 2016-2021, "
          "all bars outside ±50 of the 60 burned cases (E3). No outcomes (F7).", "",
          "| count | accepted | rejected | A/B share acc | A/B share rej | diff | 95% CI | gate |",
          "|---|---|---|---|---|---|---|---|"]
    for o in out:
        md.append(f"| {o['field']} | {o['acc'][0]}/{o['acc'][1]} | {o['rej'][0]}/{o['rej'][1]} | "
                  f"{o['share_acc']*100:.1f}% | {o['share_rej']*100:.1f}% | {o['diff']*100:+.1f}pp | "
                  f"[{o['ci'][0]*100:+.1f}, {o['ci'][1]*100:+.1f}]pp | {'PASS' if o['gate'] else 'FAIL'} |")
    md += ["", "F5 gate: diff >= +15pp AND CI lower > 0 AND A/B share(accepted, majority) >= 40%.", "",
           "## Leniency caveat (F5)", "",
           "Both graders are LLMs with the known leniency: they see only 120 bars ending at the "
           "decision bar, they cannot know the outcome, and the rubric's 'A' bar is high. The "
           "dual-agreement count (both graders identical) is the stricter measure; the majority "
           "count includes G3's tie-breaks. The difference and CI are the discriminative evidence, "
           "not the absolute A/B levels.", ""]
    with open(os.path.join(D, "FIDELITY_DR3.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    with open(os.path.join(D, "FIDELITY_DR3.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    for o in out:
        print(f"{o['field']}: acc {o['acc'][0]}/{o['acc'][1]} = {o['share_acc']*100:.1f}% | "
              f"rej {o['rej'][0]}/{o['rej'][1]} = {o['share_rej']*100:.1f}% | "
              f"diff {o['diff']*100:+.1f}pp CI [{o['ci'][0]*100:+.1f}, {o['ci'][1]*100:+.1f}] | "
              f"{'PASS' if o['gate'] else 'FAIL'}")
    print("3-way splits (median fallback):", n3way)
    print("[write]", os.path.join(D, "FIDELITY_DR3.md"))


if __name__ == "__main__":
    main()
