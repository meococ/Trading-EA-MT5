# DEVIATION D42 — E2 CELL-WEIGHT ASYMMETRY (R02-N)

## SUMMARY

- Defect: `run_e2` in
  `research/arrival/arrival_outcome_run.py` builds the pair cell's
  pooled weight as `float(len(ia))` — the arm-A contributing-event
  count alone — not `len(ia) + len(ib)` (arm A + arm B). The same
  `"w"` feeds both `bootstrap_pooled` (fixed-weight mean) and the
  `D_pooled` numerator.
- Location: `run_e2`, the `cells.append(...)` line (~:306) and the
  `cl` comprehension (~:311).
- PRE-EXISTING, sealed in FREEZE_v2 — NOT introduced by the D41 fix.
  Found by the independent fix review (out-of-scope flag).
- Lead ruling (R02-N): record, do NOT fix this round. E2 carries no
  claim in R02 (E3/line1_cluster is the sole claim path; E1 is
  descriptive-only); changing a statistic's weighting is an estimand
  change and hastily editing one at freeze time is how quiet errors
  enter; a correction needs prereg grounding and its own test. E2 is
  NOT dropped — it was pre-registered.
- Prereg on the E2 cell weight: D39(c) is the only clause — "the
  sample-size-weighted mean of its per-symbol cell D's (`w_c` = the
  cell's observed contributing-event count)" — and it is GENERIC
  across E1/E2/E3. Under its plain reading an E2 cell's contributing
  events are the union of both arms, `len(ia) + len(ib)`; there is NO
  E2-specific sentence pinning the weight.
- Disposition: E2 output is reported FLAGGED and descriptive-only; the
  weighting must be corrected from the prereg, with its own test,
  before E2 may ever carry a claim.
