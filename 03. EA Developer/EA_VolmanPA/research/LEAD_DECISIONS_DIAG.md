# LEAD DECISIONS — DR1-DIAG (T-VPA-DR1-DIAG), saved verbatim

- **E1 — Trial budget.** Outcome-blind detector revisions do not consume the economic trial budget, because no outcome was observed. To stop endless iteration, cap detector revisions at DR2 and DR3. After DR3 the Lead escalates to the Owner.
- **E2 — Anti-chase.** The interpretation `entry − B ≤ buffer + 0.35×ATR` is accepted (F6).
- **E3 — D4 relaxed for diagnosis.** You may use all 60 cases in `PLAN/grading/GRADES_LEAD_BLIND.csv` (Lead A+B = 16, C = 44) together with their locations (`selected_cases.json` / `KEY_HIDDEN.csv` / `INDEX_BLIND.csv`) as a recall and discrimination set. This set is then BURNED:
  - The DR2 fidelity estimate must use new cases only.
  - Record the burn in `research/LEAD_DECISIONS_DIAG.md`.
- **E4 — No outcomes, same as D6.** No PnL, win rate, MFE/MAE or fill-to-exit, anywhere.
- **E5 — What DR2 must be.** Book-grounded, driven by the discrimination table (below), and never loosened just to reach a cadence number. A variant that lifts cadence by passing Lead-C cases as easily as Lead-A/B cases is a bad variant.

## Burn record (E3)

The 60 cases in `PLAN/grading/GRADES_LEAD_BLIND.csv` (16 Lead A/B + 44 Lead C)
are BURNED as of this task (2026-09-20): they were used to diagnose DR1's gate
stack and to score DR2 variants. They must never be used for a DR2 fidelity
estimate or any selection; DR2 fidelity must use NEW cases only. The 60 cases
remain valid as a fixed grader-drift check set (D4/P2b) but carry no selection
weight.
