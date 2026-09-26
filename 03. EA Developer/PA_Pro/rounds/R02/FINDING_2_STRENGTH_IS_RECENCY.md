# FINDING 2 — THE STRENGTH SCORE IS A RECENCY PROXY ON THIS DATA

SUMMARY
-------
The E1 contrast (top vs bottom `zone_S` tercile among arrivals at armed
zones) cannot be separated from how recently the zone was retested.
Measured outcome-blind on all 24 symbol-generator cells: the
zone-recency sub-gate (since_near, zone_since_touch, zone_fresh each
|SMD| <= 0.05 post-weighting) fails EVERYWHERE — `zone_fresh` share
SMD 0.64–1.13, `zone_since_touch` SMD 0.32–48.98. The OLS of strength
on covariates + zone recency returns R-squared 0.36–0.898: depending
on generator, 36–90% of the "strength" score is already explained by
geometry + retest history. **A scoring layer built from touch history
measures touch history.** R01's F1 confound did not die with the
binary contrast — it lives inside E1's strength axis. This is a
finding about the score, not a failure of the estimator.

THE MEASUREMENT (post-weighting max |SMD| of the three recency
features per cell; all 24 cells FAIL the 0.05 claim sub-gate)
------------------------------------------------------------

| generator | EURUSD | GBPUSD | AUDUSD | USDJPY |
|---|---|---|---|---|
| line1_cluster | 0.693 | 0.640 | 0.661 | 0.663 |
| fractal_h1 | 1.066 | 1.094 | 1.022 | 1.014 |
| kde_swing | 2.202 | 2.300 | 1.723 | 1.830 |
| profile_va | 2.955 | 2.823 | 2.116 | 2.202 |
| sd_base | 0.972 | 0.906 | 0.868 | 0.826 |
| ref_levels | 45.5 | 49.0 | 43.9 | 42.0 |

`zone_fresh` (share with a retest inside the freshness window) drives
it: top-tercile arms carry 2–3x the in-window retest rate of
bottom-tercile arms. `zone_since_touch` shows the same gap
(0.32–2.96); `ref_levels` saturates the 1440-bar cap because its zones
are essentially never re-touched, so the capped feature degenerates.

R-squared of `zone_S ~ 8 propensity features + zone_touches +
zone_since_touch + zone_fresh`:

| generator | R2 range (4 symbols) | residual share |
|---|---|---|
| line1_cluster | 0.36–0.38 | 0.62–0.64 |
| fractal_h1 | 0.46–0.48 | 0.52–0.54 |
| sd_base | 0.48–0.52 | 0.48–0.52 |
| kde_swing | 0.80–0.81 | 0.19–0.20 |
| profile_va | 0.82–0.84 | 0.16–0.18 |
| ref_levels | 0.888–0.898 | 0.10–0.11 |

CONSEQUENCE
-----------
1. No raw-strength E1 cell can carry a "the score measures structure"
   claim — every estimate is stamped RECENCY-UNSEPARATED (D20/D25).
   The raw contrast is retained as the recency-contaminated view it
   is: reported, descriptive, never claim-bearing.
2. E1's claim-bearing estimand is the RESIDUAL-strength contrast
   (D21/D30), and only in cells whose residual arms themselves pass
   the recency sub-gate: 6/24 cells — sd_base EURUSD+GBPUSD,
   fractal_h1 AUDUSD+USDJPY, line1_cluster GBPUSD, ref_levels USDJPY
   (whose primary is underpowered-by-construction anyway).
3. ref_levels residual cells are flagged THIN-RESIDUAL: R2 0.888–0.898
   sits a hair under the 0.90 attenuation guard — reported with the
   caveat, not allowed to ride silently.
4. The honest reduction is E3 (R02-H SS3): test recency head-on —
   recently-touched vs long-ago armed zones — because every
   measurement this round says recency is the active ingredient
   hiding inside "strength".
