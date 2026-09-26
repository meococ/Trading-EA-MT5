# ASK_LEAD — R02 post-pivot feasibility report (R02-D/R02-E)

Status: the pivot is implemented and measured, all outcome-blind.
`PREREG.md` is re-scoped to E1/E2 (D15–D18), `FINDING_1_NONIDENTIFIABILITY.md`
carries the retired binary contrast as the round's first result, and
`research/arrival/` gained `arrival_contrast.py` (E1/E2 arms, IRLS
propensity, balance), `arrival_feas2.py` (driver), and weighted-ATT +
refit-bootstrap in `arrival_estimate.py` — 17/17 synthetic tests pass.

## Measured verdicts post-R02-G (all four symbols, outcome-blind)

Item 1 (`side` into propensity + gate): **cost zero cells.** Raw side
imbalance (up to SMD ~0.32 for sd_base) is fully absorbed by
weighting — post-weighting side |SMD| <= 0.086 in every cell, and the
E2 pass/fail pattern is unchanged (same 7 pairs evaluable 4/4).

Item 2 (zone-level recency sub-gate, D25): **costs every E1 primary
cell its claim eligibility — 0/24 recency-separated.** zone_fresh
share SMD 0.64-1.13 top-vs-bottom (reviewer measured the shares:
top-tercile arms are 2-3x "retest in progress"); zone_since_touch
0.32-48.98. The strength contrast cannot be separated from zone
recency on this data — F1 was inside E1 all along, now measured.

Residual confirmatory after the corrected regressor set (D25):
balance 24/24 (<=0.035); R2 0.36-0.90 — ref_levels sits at
0.888-0.898, a hair under the 0.90 attenuation guard (does NOT
trigger, flagged near-boundary). Residual-arm recency sub-gate passes
in 6/24 cells: sd_base EURUSD+GBPUSD, fractal_h1 AUDUSD+USDJPY,
line1 GBPUSD, ref_levels USDJPY.

**Consequence for the round, stated plainly:** no E1 primary cell can
carry a "strength measures structure" claim — every estimate will be
stamped RECENCY-UNSEPARATED at best. Under D27 a stamped generator
may still be carried forward, but a winner declaration requires
beating the best FULLY-CONFIRMED generator by >= +5.0pp; if no
fully-confirmed generator exists, no winner can be declared from the
primary alone and the round's answer on the scoring layer is decided
by the residual contrast in its 6 evaluable-and-separated cells.

## Declared limitations (per R02-D §5 / R02-E, reported not repaired)

1. **Fresh-to-zone confirmatory: DROPPED per R02-E §1** — failed
   its own balance gate in 23/24 cells by construction (0.077-0.697;
   only AUDUSD line1 at 0.098). Recorded in D19 with the reason.
   Replaced by: (a) the `since_near` <= 0.05 claim sub-gate (D20,
   measured blind: line1 4/4, fractal 4/4, sd_base 2/4, kde 0/4 =
   RECENCY-UNSEPARATED); (b) the residual-strength confirmatory (D21),
   which balances in 24/24 cells (max post |SMD| 0.035) and is the
   real test of the scoring layer. D7's doubled bar is superseded
   (declared in D21): no unconfirmable case remains.
2. **E2 arm-count asymmetry is large in places** (e.g. profile|ref:
   ~3k vs ~12k). Balance is fine; power is adequate; reported.
3. `supT_exact` for the exact-strata robustness view is low
   (0.03-0.71) because tercile/pair contrasts partition treated events
   finely — it is reported, not gated, per the pinned design.

## Not flagged as problems

- kde_swing's GBPUSD E1 miss (0.103) is handled by the cell-level gate
  as designed; its wider issue is now the D20 recency stamp (0/4),
  which the pinning already covers.
- E2's `line1_cluster` exclusion is a finding about that generator
  (its marks are too dense to have a meaningful complement), parallel
  to the R02-C1 note about dense generators.

## For the re-review

Same neutral reviewer should attack: `PREREG.md` (D15-D22, §3b
tables, §6 pinned estimator + gates + winner rule), `FINDING_1_*.md`,
`arrival_common.py` (zone_zid), `arrival_contrast.py` (residual spec),
`arrival_feas2.py`, `arrival_estimate.py`, and the 19-test suite.
Nothing frozen; no outcome computed.


## Post-R02-H verdict (E3 measured blind)

**E3 overlap is natural, as the ruling predicted.** Recency terciles on
the armed-overlap treated set: trimmed shares 0.00-0.03 in every cell,
no degenerate bounds, arms ~1:1. Balance gate (7 features, no recency
variable): line1_cluster, fractal_h1, kde_swing, sd_base PASS 4/4
(0.032-0.093); profile_va and ref_levels pass AUDUSD+USDJPY only
(EURUSD 0.107-0.139, GBPUSD 0.114-0.119 FAIL) — underpowered there,
declared.

E1 is now inverted per D30: the raw-strength contrast is descriptive
only (RECENCY-UNSEPARATED 24/24 — FINDING_2); the claim-bearing E1
estimand is the residual contrast in its 6 evaluable-and-separated
cells (sd_base EUR/GBP, fractal AUD/JPY, line1 GBP, ref_levels JPY —
the last flagged THIN-RESIDUAL at R2 0.888-0.898).

Families pinned: E1 = 6 residual cells x 2 endpoints; E2 = evaluable
pairs x 2 (flagging only); E3 = evaluable generator-cells x 2. No
freeze, no outcome computed.

## Post-R02-J verdict (E3 under corrected covariates)

Section above superseded. With `since_near` + `zone_touches` in the
model (D33), E3 balance **killed almost everything**: only
`line1_cluster` passes 4/4 (0.045-0.062); `fractal_h1` keeps GBPUSD
only (0.100; rest 0.115-0.147). kde 0.13-0.31, profile 0.24-0.49,
sd_base 0.16-0.24 all FAIL. ref_levels' propensity saturates
(trim 1.00/1.00) — non-evaluable by the new saturation guard.
cap_share_stale stamps kde (0.63-0.76), profile (0.72-0.84),
ref_levels (1.00) STALE~NEVER-TOUCHED — different estimand, never
pooled into a recency claim (D35, threshold 0.50 fixed blind).
zone_S arm SMD 0.64-4.23 reported as diagnostic, excluded per D34.

E3 family shrinks to: line1_cluster x 4 cells + fractal_h1 GBPUSD.
No freeze, no outcome computed.

## Post-R02-K status (B1/B2 closed, targeted re-check PASSED)

B1 pinned + implemented: p recipe one-sided `(1+#{D_b<=0})/(B+1)` on
RETAINED replicates (every `bootstrap_*` returns {lo,hi,p,n_boot,
boots}); family unit = generator(pair) x endpoint uniformly;
`bootstrap_pooled` resamples days within each contributing cell and
recomputes the weighted mean per replicate.  B2 pinned: winner rule
ranks each candidate by its own statistic (E1 `D_resid`, E2 `D_{g,h}`,
E3 `D_recency`); FULLY-CONFIRMED = pass own gate + no flags; unflagged
E3 pass is fully-confirmed and can set the +5.0pp benchmark.

Targeted confirmation via gold-bean session: **B1 CONFIRMED, B2
CONFIRMED** (70s, scope held).  D34 concession recorded in the prereg.

The big declare is in the PREREG headline: E1 cannot carry a claim
(no generator reaches 3 contributing residual cells); the round's
single claim path is E3 on `line1_cluster`.
