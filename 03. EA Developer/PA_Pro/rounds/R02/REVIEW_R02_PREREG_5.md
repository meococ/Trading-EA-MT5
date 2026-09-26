# REVIEW_R02_PREREG_5 — targeted confirmation, B1/B2 only (R02-K)

Scope: pass-4 blockers B1/B2 only. Code and prereg read line-level;
nothing else re-audited.

## SUMMARY

B1: CONFIRMED
- (a) p recipe pinned and matches code: prereg D39(a) (PREREG.md:596-600)
  = code `_pack_boots`, arrival_estimate.py:50-62 — one-sided
  `(1 + #{D_b <= 0}) / (n_boot + 1)` over retained replicates. Note:
  text writes "(B + 1)", code uses retained count n_boot+1 — same thing
  when all replicates valid, code is the conservative side otherwise;
  n_boot is reported so the reading is self-documenting.
- (b) replicates retained: `_pack_boots` returns {lo, hi, p, n_boot,
  boots}; all five bootstrap_* return it (estimate.py:164, 260, 285,
  311, 402); callers read r["p"]/r["n_boot"] (outcome_run.py:94-97,
  220-221).
- (c) family unit pinned "generator (pair for E2) x endpoint" (D39b,
  PREREG.md:601-604) and the run path emits exactly that unit — one
  ledger trial per (family, unit, endpoint) with the pooled p
  (outcome_run.py:215-231); `bh_across` (phys_stats.py:159, standard
  monotone BH) exists for the within-family adjustment.
- (d) `bootstrap_pooled` (estimate.py:367-402) resamples DAY clusters:
  `carr = day_i` per cell (382-383), `rng.choice` over unique days
  (392), `sel` = all events in picked days (394-395) — day-level
  resampling within each contributing cell, not events.

B2: CONFIRMED
- (e) §6 (PREREG.md:1038-1040): "rank every candidate by ITS OWN
  experiment's claim statistic — E1 by `D_resid`, E2 by `D_{g,h}`,
  E3 by `D_recency`."
- (f) FULLY-CONFIRMED (1041-1045): own-gate pass AND none of
  {RECENCY-UNSEPARATED, RECENCY-DOMINATED, STALE≈NEVER-TOUCHED,
  THIN-RESIDUAL} — all flags are computable from frozen bundle tables
  (gate_pass, recency SMDs, cap_share_stale, R²). Decidable.
- (g) headline declare present (§1, 643-649): no E1 generator reaches
  3 contributing cells → E1 descriptive-only; single claim path =
  E3/line1_cluster.

FREEZE-BLIND: not-yet-written (rounds/R02/FREEZE.json absent; bundles
still building in _scratch/frozen_bundles). Writer code is blind:
arrival_freeze2.py stores events+treated+table only, imports
arrival_outcome nowhere, and emits ledger_anchor + prereg_sha256 +
code hashes before any outcome exists (freeze2.py:194-229).

FREEZE-GATE: OPEN
