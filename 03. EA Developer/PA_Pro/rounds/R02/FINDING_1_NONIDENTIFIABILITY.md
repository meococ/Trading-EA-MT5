# R02 FINDING 1 — the binary zone question is NON-IDENTIFIABLE on this data

## SUMMARY

- **What was asked:** does price behave differently when it arrives at a
  place where a zone generator has marked structure, versus an
  arrival-matched place where it has marked nothing?
- **What was found:** the question cannot be answered by this design —
  not because of a bug, but because of **positivity failure that is
  structural, not statistical**. A zone exists BECAUSE price did
  something there; "place with a zone" and "place without a zone" are
  different kinds of location by construction and do not overlap on the
  covariates that decide behavior. No granularity, weighting, or
  trimming creates overlap that is not there.
- **Status:** measured outcome-blind on all four DESIGN symbols before
  any outcome was computed. This is R02's first finding and it stands
  regardless of what E1/E2 show. R01's F1 confound (approach-distance,
  0.3 vs 2.2 ATR) was a symptom of this same structure, not a defect of
  one control design.

## The numbers (all event-level, <= t, m = 0.5 x w_g, w = 0.75, anchor = day open)

Corrected definitions (LEAD RULING R02-C1): arms labelled at `t-1`;
CONTROL = no LIVE zone (armed or not) within `0.5 * w_p`; strata include
`anchor_dist` decile; co-primary adds symmetric `since_near` tercile.

Primary-key common support `supT` (share of treated events with >= 1
control in stratum), range over the four symbols:

| generator | supT range | fine-key supT | zone_stale_share |
|---|---|---|---|
| line1_cluster | 0.244 - 0.290 | 0.129 - 0.171 | 0.605 - 0.639 |
| fractal_h1    | 0.756 - 0.791 | 0.496 - 0.559 | 0.374 - 0.417 |
| kde_swing     | 0.574 - 0.626 | 0.351 - 0.405 | 0.482 - 0.524 |
| profile_va    | 0.807 - 0.834 | 0.562 - 0.617 | 0.408 - 0.439 |
| sd_base       | 0.900 - 0.913 | 0.704 - 0.723 | 0.350 - 0.385 |
| ref_levels    | 0.845 - 0.886 | 0.646 - 0.677 | 0.287 - 0.314 |

No generator clears the 0.90 floor on the co-primary key (max 0.723,
sd_base GBPUSD); only sd_base clears the primary floor, by 0.0002.

The asymmetries that produce it (medians, treated vs control, all
symbols):

- `anchor_dist` (|band mid - day open| / ATR): **1.24-1.57 vs
  1.87-2.48** — control events can only exist where no live zone of
  that generator sits, and empty space lives far from where the day
  anchored.
- `since_near` (bars since last touch of the band neighborhood):
  **95-123 vs 207-817** — control space is space price has not
  recently visited.
- `zone_stale_share`: 29-64% of treated events arrive at a zone that
  was ALREADY being retouched inside the freshness window — the
  treated arm is substantially "retest in progress", which no
  band-level freshness rule can see because the zone is wider than
  the band.
- Approach distance (`dist_cp`) stays matched (0.39-0.55 vs
  0.41-0.63 ATR) — the grid did fix R01's literal confound. The
  residual asymmetry is not distance-to-band; it is *which places can
  be empty at all*.

## Why this is the finding, not an obstacle

Under every correction that honesty required (arms at t-1, live-zone
control, anchor stratification), the measurable population shrank to a
sliver. The same result appeared on all four symbols, at all three
margins, under both anchors, at every stratum granularity tried
(deciles and quintiles). Propensity weighting cannot repair it —
weighting handles dimensionality, not missing support.

The methodological content: **zone-attribution questions of the form
"marked vs unmarked, all else equal" are not answerable by location
contrasts, because marking is caused by the location's history.** The
identifiable questions are the ones where both arms carry marks —
strength contrasts within one generator (E1) and cross-generator
contrasts at shared locations (E2). The round pivots there.

## Provenance

- Evidence tables: `rounds/R02/FEASIBILITY.md` §10-11 (corrected),
  §2-7 (superseded pre-C1 numbers, retained for audit).
- Harness: `research/arrival/` (`arrival_common.tag_arms`,
  `arrival_freeze.py` output JSON).
- Trigger: `rounds/R02/REVIEW_R02_PREREG.md` (neutral review, FAIL,
  F1-F3 measured the contamination); LEAD RULING R02-C1 fixed the
  definitions; the re-measurement produced this finding; LEAD RULING
  R02-D declared it the round's first result.
- No outcome column was computed at any point.
