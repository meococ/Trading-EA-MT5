# LEAD_DECISIONS_DR3 — saved verbatim (task T-VPA-DR3)

## Lead verdict on T-VPA-DR1-DIAG: ACCEPTED (excellent diagnosis)
The Lead independently looked at snapshots ab_case_025, ab_case_065, ab_case_012 and missed_07, and confirmed four things:
- Barrier lines sit at the right levels, and the signal-bar fix is right (tr.88/95).
- Case 025 (Lead A) was rejected by chop and buildup. The chop veto fired because of the impulse leg BEFORE the buildup, and the real tight buildup under the ceiling was rejected. Both definitions are wrong.
- Case 012 (Lead A) failed room because the "obstacle" is the ceiling's own earlier wick, ~0.5 pip above entry. That is part of the barrier zone, not an obstacle ahead.
- missed_07: the barrier was drawn THROUGH a chop zone that price crossed many times. A pro would never call that a line. Barrier integrity is missing.

Also, INDEX.csv shows `utc = -1:15` for missed_04, which is a time-conversion or formatting bug. Investigate it first (step 0).

## LEAD DECISIONS (binding)
- **F1 — Lane continues with DR3, option (B).** DR3 is the last detector revision. If DR3 fails its gates, the Lead escalates to the Owner (E1).
- **F2 — DR3 core. The hard gates are only the ones proven to discriminate, or required by the book or by safety.**
  - (a) Keep the DR2c recall fixes: signal bar = the last touch bar before the breakout (tr.88/95), signal window 0.50, v1 session windows, and the stop order 1 pip beyond the signal-bar extreme.
  - (b) Keep the direction rule D1a (tr.95) and the trend gate at DR1 parameters, θ=0.10 and frac_side 0.6. It is the only proven discriminator (13% A/B vs 71% C fail).
  - (c) NEW barrier integrity (tr.39–41, a ceiling must hold): between the first touch and the signal bar, no bar may CLOSE beyond B by more than eps (0.10×ATR, the same as the touch tolerance). A level crossed by closes is not a barrier. Measure how many burned A/B vs C cases this removes, as a diagnostic only.
  - (d) Cost gate unchanged.
- **F3 — Demoted to logged FEATURES, not gates:** buildup (both the DR1 4-condition version and the 2-of-4 version), chop, room, adverse magnet, anti-chase, EMA-squeeze and pressure. Compute them all per candidate and write them to the census and trace output; they will define DR4+ later.
  - Fix the room definition in the feature. Obstacles inside the barrier zone (≤ max(barrier eps, 0.5R) beyond the barrier) are the barrier itself, so ignore them. Use significant obstacles only.
  - Fix the chop feature so it is measured only inside the buildup window, not over the impulse leg.
- **F4 — Time sanity.** Explain and fix the `-1:15` UTC value. Verify `utc_min` against the data source's timezone and DST for 3 known timestamps: one winter, one summer, one DST transition week. Session windows are UTC, taken from v1. Keep the lunch window (tr.227/273) as a logged feature only.
- **F5 — Fidelity design, which neutralises the graders' known leniency.**
  - Sample 120 DR3-ACCEPTED candidates and 60 DR3-REJECTED candidates. Rejected means evaluated in session with the direction rule passing, then rejected by trend or integrity.
  - The samples are stratified random by year, drawn from DESIGN 2016–2021, and EXCLUDE every bar within ±50 bars of the 60 burned cases.
  - Shuffle them into one blind set of 180 (`PLAN/grading_dr3/`) with INDEX_BLIND and a hidden key. Snapshots show NO bars after the decision bar.
  - G1 and G2 grade blind with the unchanged GRADING_RUBRIC_V2. Hash both files BEFORE any unblinding. G3 grades the disagreements only, and the majority decides.
  - **Metric:** A/B share(accepted) − A/B share(rejected), with a 95% CI (Newcombe or bootstrap), reported both for the dual-agreement count and for the majority count.
  - **Fidelity GATE PASS** requires all of:
    - a difference ≥ +15pp;
    - a CI lower bound > 0;
    - A/B share(accepted, majority) ≥ 40%.
  - Also prepare `LEAD_SPOTCHECK_INDEX.csv`: 20 blind cases, 12 accepted and 8 rejected, with no labels anywhere.
- **F6 — Cadence rule D2 still applies** to the DR3 census: ≥10/week is normal, 3 to <10 is LOW_CADENCE, <3 is STOP.
- **F7 — No outcomes anywhere (E4).**
