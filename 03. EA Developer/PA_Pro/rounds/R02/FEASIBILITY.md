# R02 FEASIBILITY — arrival-matched design, outcome-blind

**Verdict: GO** — the grid design is feasible and structurally removes the
R01 approach-distance confound. Primary spec recommendation:
**margin = 0.5 x w_g, w_g = median armed width, anchor = day open**
(fallback `w_g` = 0.75x median for `line1_cluster` robustness).
Estimation must be stratum-restricted (common support) — see §5.

**Outcome-blind statement.** No column in this pipeline looks forward past
the event bar. No bounce, break, continuation, or any post-event movement
is computed anywhere in `research/arrival/`. All features are functions of
bars `<= t`.

**Scope.** DESIGN split 2016-01-01..2021-12-31, EURUSD + GBPUSD, all six
frozen generators, margin in {0.5, 1.0, 2.0} x w_g, anchor in
{open, prevclose}, w_g scale in {0.75, 1.0, 1.5} (EURUSD, 2 generators).
`armed_ids_from(active_at_fast(t))` imported read-only via `GenSource`
from `research/physics/` (certified path, `rounds/R01/PARITY.md`).

Harness files (sha256):
`arrival_common.py` 628c4af1…, `arrival_run.py` e0b9662e…,
`arrival_sens.py` 13c4e232…, `tests/test_arrival.py` d3450a3f….
Unit tests: 4/4 PASS (prefix-invariance of event extraction, grid anchor
independence, away-move requirement, margin sweep monotonicity).

## 1. Design implemented (exactly as specified)

- Grid: first bar of each server day, bands of width `w_g` at spacing
  `w_g`, anchored at day open, `w_g = median armed-zone width of g in
  ATR units x A(day-open bar)`, spanning +/-5 ATR around the anchor.
  Fixed for the day. Median width `u_atr` measured per generator on a
  strided sample of armed snapshots.
- Arrival event = frozen R01 rule verbatim with band G in place of the
  zone: `range(t)` intersects G; no bar in [t-24, t-1) intersects G;
  some bar in that window has close-distance >= 1.0 x A(t) from G;
  side from `c[t-1]`; A(t) valid; t not warm-up.
- TREATED = armed zone of g overlaps G at t.
- CONTROL = no armed zone of g within `margin x w_g` of G at t.
- EXCLUDED = zone within margin but not overlapping (counted only).

## 2. Event/arm counts

### EURUSD (margin x w_g)

| generator | u_atr | events | m | T | C | X |
|---|---|---|---|---|---|---|
| line1_cluster | 0.509 | 18100 | 0.5/1.0/2.0 | 12050 | 4295/3380/1974 | 1755/2670/4076 |
| fractal_h1 | 0.338 | 27446 | 0.5/1.0/2.0 | 11680 | 12820/10878/8180 | 2946/4888/7586 |
| kde_swing | 0.600 | 15664 | 0.5/1.0/2.0 | 8094 | 6401/5660/4506 | 1169/1910/3064 |
| profile_va | 0.646 | 14247 | 0.5/1.0/2.0 | 1910 | 11670/11060/10085 | 667/1277/2252 |
| sd_base | 0.336 | 27049 | 0.5/1.0/2.0 | 4484 | 21040/19902/17852 | 1525/2663/4713 |
| ref_levels | 0.260 | 35849 | 0.5/1.0/2.0 | 10587 | 21501/18894/15146 | 3761/6368/10116 |

### GBPUSD (margin x w_g)

| generator | u_atr | events | m | T | C | X |
|---|---|---|---|---|---|---|
| line1_cluster | 0.509 | 18251 | 0.5/1.0/2.0 | 12020 | 4365/3434/2009 | 1866/2797/4222 |
| fractal_h1 | 0.338 | 27464 | 0.5/1.0/2.0 | 11359 | 13163/11262/8421 | 2942/4843/7684 |
| kde_swing | 0.600 | 15617 | 0.5/1.0/2.0 | 8017 | 6474/5739/4531 | 1126/1861/3069 |
| profile_va | 0.646 | 14309 | 0.5/1.0/2.0 | 1957 | 11596/10938/9989 | 756/1414/2363 |
| sd_base | 0.336 | 27555 | 0.5/1.0/2.0 | 4701 | 21249/19952/17715 | 1605/2902/5139 |
| ref_levels | 0.260 | 35996 | 0.5/1.0/2.0 | 10659 | 21720/19190/15652 | 3617/6147/9685 |

*event totals confirmed exact from the JSON log (post-note: all six
EURUSD n_events now printed, no estimates remain).

Counts are stable across symbols. Treated share: line1 ~66%,
ref_levels ~30%, fractal_h1 ~41%, kde_swing ~52%, sd_base ~17%,
profile_va ~13%. Grid bands/day: ~20 (w=1.0) EURUSD; `line1_cluster`
is armed nearly everywhere (EURUSD `no_armed_events` was small;
GBPUSD 1014/18251).

## 3. Covariate distributions (m = 0.5; p10/median/p90; GBPUSD shown — EURUSD same pattern)

| gen | arm | approach_atr | since_touch | dist_cp | pos_r5 |
|---|---|---|---|---|---|
| line1 | T | 1.12/1.64/2.73 | 31/91/766 | 0.36/0.57/1.09 | 0.07/0.50/0.92 |
| line1 | C | 1.34/2.20/3.67 | 112/542/1440 | 0.39/0.70/1.69 | -0.04/0.49/1.03 |
| ref_levels | T | /1.64/ | /99/ | /0.46/ | /0.49/ |
| ref_levels | C | /1.88/ | /247/ | /0.48/ | /0.50/ |
| fractal_h1 | T | /1.64/ | /99/ | /0.49/ | /0.50/ |
| fractal_h1 | C | /1.92/ | /255/ | /0.54/ | /0.49/ |
| profile_va | T | /1.78/ | /181/ | /0.68/ | /0.49/ |
| profile_va | C | /1.78/ | /180/ | /0.68/ | /0.50/ |
| kde_swing | T | /1.75/ | /143/ | /0.65/ | /0.50/ |
| kde_swing | C | /1.82/ | /230/ | /0.67/ | /0.50/ |
| sd_base | T | /1.70/ | /93/ | /0.49/ | /0.50/ |
| sd_base | C | /1.80/ | /205/ | /0.52/ | /0.50/ |

`dist_cp` = |band mid - c[t-1]| / A(t) — the quantity whose 7x real/control
asymmetry (0.3 vs 2.2 ATR) sank R01. **Here T and C agree to within
~0.1-0.2 ATR for every generator**: both arms only generate events when
price is already at the band, so arrival distance is matched by
construction. The residual gap is in `approach_atr` (how far price
travelled inside the 24-bar window) and `since_touch` (treated bands sit
where price recently was — that is *why* a zone is armed there), and only
for `line1_cluster` does it widen with margin. ATR decile and hour
distributions were near-identical in all arms (hour shares within ~2pp).

## 4. Common support — the deciding number

Strata: side x approach-distance decile x ATR decile x hour bucket.
`supT` = share of treated events with >=1 control in-stratum;
`supC` = converse. `supTn` = treated support vs the dist_cp<=2.5
nearness-restricted control arm.

### EURUSD supT / supC

| gen | m=0.5 | m=1.0 | m=2.0 |
|---|---|---|---|
| line1_cluster | 0.912/0.973 | 0.839/0.970 | 0.578/0.963 |
| fractal_h1 | 0.994/— | 0.990/— | 0.982/— |
| kde_swing | 0.978/— | 0.973/— | 0.950/— |
| profile_va | 0.993/— | 0.993/— | 0.991/— |
| sd_base | 0.997/— | 0.996/— | 0.997/— |
| ref_levels | 0.998/— | 0.998/— | 0.997/— |

### GBPUSD supT / supC / supTn

| gen | m=0.5 | m=1.0 | m=2.0 |
|---|---|---|---|
| line1_cluster | 0.900/0.975/0.898 | 0.847/0.973/0.848 | 0.619/0.967/0.622 |
| fractal_h1 | 0.993/0.984/0.993 | 0.989/0.982/0.989 | 0.977/0.980/0.979 |
| kde_swing | 0.982/0.975/0.981 | 0.972/0.974/0.972 | 0.959/0.970/0.959 |
| profile_va | 0.987/0.853/0.986 | 0.985/0.856/0.985 | 0.987/0.857/0.984 |
| sd_base | 0.998/0.949/0.996 | 0.997/0.948/0.996 | 0.995/0.950/0.995 |
| ref_levels | 0.996/0.979/0.996 | 0.994/0.976/0.994 | 0.991/0.976/0.991 |

Read: for five of six generators, >=95% of treated events have
same-stratum controls at every margin. `line1_cluster` — the densest
generator, armed ~everywhere — degrades with margin (0.90 -> 0.62),
because wide margins exile most candidate controls into the excluded
middle and the survivors are systematically longer-journey events.

`supTn` ~= `supT` everywhere: the dist_cp<=2.5 restriction built for
this test changes nothing, because the grid already matched distance.
**Do not carry a distance restriction into R02 — it buys nothing and
costs sample.**

## 5. Sensitivity (EURUSD, supT at margins 0.5/1.0/2.0)

| gen | wscale | anchor | events | supT 0.5 | supT 1.0 | supT 2.0 |
|---|---|---|---|---|---|---|
| line1 | 0.75 | open | 24474 | 0.951 | 0.931 | 0.805 |
| line1 | 0.75 | prevclose | 24362 | 0.957 | 0.931 | 0.797 |
| line1 | 1.00 | open | 18100 | 0.912 | 0.839 | 0.578 |
| line1 | 1.00 | prevclose | 17981 | 0.894 | 0.834 | 0.592 |
| line1 | 1.50 | open | 12141 | 0.794 | 0.636 | 0.388 |
| line1 | 1.50 | prevclose | 12097 | 0.777 | 0.615 | 0.390 |
| ref_levels | 0.75 | open | 47555 | 0.999 | 0.999 | 0.998 |
| ref_levels | 0.75 | prevclose | 47239 | 0.999 | 0.998 | 0.998 |
| ref_levels | 1.00 | open | 35849 | 0.998 | 0.998 | 0.997 |
| ref_levels | 1.00 | prevclose | 35717 | 0.999 | 0.998 | 0.996 |
| ref_levels | 1.50 | open | 23640 | 0.996 | 0.995 | 0.979 |
| ref_levels | 1.50 | prevclose | 23598 | 0.996 | 0.994 | 0.980 |

- Anchor: immaterial — supT shifts <0.02, counts <3% everywhere. The
  design does not hinge on the anchor.
- w_g: matters only through `line1_cluster` — smaller bands -> more
  bands/day, smaller margin in price -> fewer exclusions -> more
  controls. w=0.75 raises line1 supT to 0.95 at m=0.5; w=1.5 is bad.
- Margin is the real lever: m=0.5 is the only spec where every
  generator clears supT >= 0.90 at w=1.0, and >= 0.95 at w=0.75.

## 6. Power

Smallest arm pair (GBPUSD profile_va m=0.5): T=1957, C=11596.
SE of a proportion difference ~ sqrt(0.25*(1/1957 + 1/11596)) ~= 0.012
-> a ~2.4pp true effect is detectable at 95% on ONE symbol. Typical
pairs are 4k-12k per arm (SE ~0.5-1pp). Across 4 symbols the design
has power for effects far below the R01-magnitude signals; power is
not the constraint — common support is.

## 7. Recommendation to the Lead

**GO.** The arrival-matched grid answers "does it matter that a zone is
there" with both arms drawn by the same event process, and it fixes the
measured R01 confound by construction (dist_cp 0.5-0.8 vs 0.5-0.8 ATR;
was 0.3 vs 2.2).

Spec to freeze:
1. margin = 0.5 x w_g (largest margin where line1 keeps supT >= 0.90;
   every other generator is >= 0.95).
2. w_g = median armed width; if the Lead wants line1 supT >= 0.95,
   use 0.75x — cheap and measured.
3. Anchor = day open; keep prevclose as the robustness rerun.
4. Estimation on the common-support stratum set (drop treated events
   without same-stratum controls, and vice versa); report the dropped
   share — it is the price of validity and is now measurable (~10% for
   line1, <=5% elsewhere at m=0.5).
5. Report raw shares alongside conditional rates (carried over from
   the R01 F7 finding).
6. Bootstrap clustered by day — events share the day's grid and zones.
7. Keep the excluded-middle arm: T vs X vs C is a free second contrast
   (zone present vs zone nearby vs zone absent) at zero extra cost.

Residual caveat to carry into the prereg honestly: `since_touch` is
structurally shorter for treated bands (zones arm where price recently
was — that IS the treatment), so perfect matching on it is impossible;
the stratum-restriction bounds it. If the Lead wants one more layer,
add `since_touch` terciles to the stratum key and re-measure supT —
this harness already computes the feature; it is a one-line change and
one rerun, not a redesign.

## 8. What was checked

- Unit tests (synthetic data): prefix-invariance of the event table
  (truncate at 120 vs full 200 -> identical events), anchor produces
  distinct grids, no-away bars produce no events, margin sweep is
  monotone non-increasing in controls. 4/4 PASS.
- Freshness rule identical to frozen `phys_extract.py` semantics
  (strict 24-bar window).
- Armed path imported from `research/physics/` — not copied.
- No outcome column exists anywhere in the package (grep-verified:
  no reference to bars after t in any feature).
- DESIGN split enforced via `load_ctx` -> `pa_data.load_m1`
  (assert_allowed path).

## 9. Open items

- ~~EURUSD exact `n_events`~~ — CLOSED, exact values in §2.
- Whether `since_touch` enters the stratum key — RESOLVED by LEAD
  RULING R02-B (co-primary fine key); finer-key measurements now in
  `rounds/R02/PREREG.md` §0.
- ~~AUDUSD/USDJPY not yet run~~ — CLOSED: all four symbols measured at
  the frozen spec in `arrival_freeze.py` output (PREREG §0 tables).

---

## 10. R02-C1 CORRECTED MEASUREMENT — supersedes §2-§7 arm tables

After the neutral review (`REVIEW_R02_PREREG.md`, FAIL) the arm and
stratum definitions were corrected per LEAD RULING R02-C1:

- Arms labelled from zone state at `tp = t-1` (the measured bar no
  longer decides its own arm).
- CONTROL = NO LIVE zone (armed or not, broken or intact) within
  `margin * w_p` at `tp` — live-but-unarmed zones now exclude or
  contaminate nothing.
- `anchor_dist` decile added to BOTH stratum keys.
- Co-primary recency = `since_near` (symmetric, both arms);
  `since_touch` is diagnostic only.
- `zone_fresh` measured per treated event (`zone_stale_share` below).

All earlier support numbers in this file were measured under the
pre-C1 armed-only/at-t definitions and are SUPERSEDED — kept above for
the audit trail. The corrected table (m = 0.5, w = 0.75, anchor = open):

| symbol | generator | events | T | C | X | staleT | supT | supC | supT_fine | supC_fine |
|---|---|---|---|---|---|---|---|---|---|---|
| EURUSD | line1_cluster | 24474 | 15921 | 4117 | 4436 | 0.620 | 0.264 | 0.768 | 0.156 | 0.592 |
| EURUSD | fractal_h1 | 36597 | 14821 | 15506 | 6270 | 0.377 | 0.770 | 0.767 | 0.531 | 0.553 |
| EURUSD | kde_swing | 20853 | 10046 | 8133 | 2674 | 0.487 | 0.611 | 0.677 | 0.394 | 0.454 |
| EURUSD | profile_va | 19293 | 2234 | 15824 | 1235 | 0.430 | 0.831 | 0.281 | 0.617 | 0.161 |
| EURUSD | sd_base | 36171 | 5262 | 27356 | 3553 | 0.361 | 0.900 | 0.479 | 0.707 | 0.279 |
| EURUSD | ref_levels | 47555 | 12537 | 27405 | 7613 | 0.292 | 0.864 | 0.645 | 0.660 | 0.430 |
| GBPUSD | line1_cluster | 24525 | 15676 | 4272 | 4577 | 0.605 | 0.290 | 0.782 | 0.171 | 0.599 |
| GBPUSD | fractal_h1 | 36662 | 14446 | 16156 | 6060 | 0.374 | 0.791 | 0.776 | 0.559 | 0.566 |
| GBPUSD | kde_swing | 20951 | 10029 | 8269 | 2653 | 0.482 | 0.626 | 0.704 | 0.405 | 0.478 |
| GBPUSD | profile_va | 19382 | 2286 | 15781 | 1315 | 0.408 | 0.827 | 0.292 | 0.608 | 0.167 |
| GBPUSD | sd_base | 36823 | 5570 | 27516 | 3737 | 0.350 | 0.910 | 0.523 | 0.723 | 0.305 |
| GBPUSD | ref_levels | 47808 | 12458 | 27715 | 7635 | 0.292 | 0.845 | 0.615 | 0.646 | 0.416 |
| AUDUSD | line1_cluster | 26267 | 17955 | 3935 | 4377 | 0.639 | 0.244 | 0.760 | 0.129 | 0.563 |
| AUDUSD | fractal_h1 | 40538 | 16704 | 17327 | 6507 | 0.417 | 0.776 | 0.772 | 0.517 | 0.541 |
| AUDUSD | kde_swing | 22402 | 11366 | 8458 | 2578 | 0.524 | 0.574 | 0.670 | 0.353 | 0.432 |
| AUDUSD | profile_va | 22248 | 2630 | 18216 | 1402 | 0.439 | 0.834 | 0.269 | 0.593 | 0.150 |
| AUDUSD | sd_base | 41132 | 5544 | 32172 | 3416 | 0.385 | 0.907 | 0.439 | 0.708 | 0.248 |
| AUDUSD | ref_levels | 52798 | 13423 | 31326 | 8049 | 0.314 | 0.886 | 0.670 | 0.677 | 0.427 |
| USDJPY | line1_cluster | 25561 | 17286 | 3804 | 4471 | 0.620 | 0.246 | 0.741 | 0.130 | 0.544 |
| USDJPY | fractal_h1 | 38917 | 16191 | 16316 | 6410 | 0.399 | 0.756 | 0.742 | 0.496 | 0.514 |
| USDJPY | kde_swing | 21740 | 10329 | 8860 | 2551 | 0.504 | 0.581 | 0.644 | 0.351 | 0.405 |
| USDJPY | profile_va | 20690 | 2331 | 17109 | 1250 | 0.410 | 0.807 | 0.241 | 0.562 | 0.136 |
| USDJPY | sd_base | 41021 | 5650 | 31706 | 3665 | 0.368 | 0.913 | 0.457 | 0.704 | 0.255 |
| USDJPY | ref_levels | 50695 | 12898 | 30093 | 7704 | 0.287 | 0.882 | 0.635 | 0.667 | 0.417 |

Reading:

- PRIMARY floor 0.90: only `sd_base` clears it — 0.9002/0.9102/0.9071/
  0.9127 (EURUSD/GBPUSD/AUDUSD/USDJPY), within 0.02 of the floor on all
  four -> THIN SUPPORT. `line1_cluster` collapses to 0.244-0.290; the
  rest sit at 0.574-0.886.
- FINE floor: NO generator clears 0.90 anywhere (max 0.7233).
- `zone_stale_share` (treated events whose overlapping armed zone was
  touched in `[t-24,t-1]`): 0.287-0.639 — the reviewer's F1 confirmed
  at full scale; the fresh-to-zone restriction would discard
  29-64% of treated events.
- `anchor_dist` medians: treated 1.24-1.57 vs control 1.87-2.48 ATR —
  R01's F1 episode-asymmetry in the anchor coordinate, now inside the
  stratum key.
- The X arm ("live but not armed") is now a real third arm:
  e.g. EURUSD line1 X=4436 events, ~18% of all events.
- Granularity sensitivity (informational, NOT adopted — changing it
  post-measurement is the Lead's call): anchor quintiles instead of
  deciles partially rescue primary supT on EURUSD (fractal 0.909,
  profile_va 0.940, sd_base 0.960, ref_levels 0.965; line1 still
  0.388) but do not rescue the co-primary floor anywhere.

## 11. Corrected verdict

The arrival-matched event process still fixes the R01 distance confound
(`dist_cp` matched, treated 0.39-0.55 vs control 0.41-0.63 ATR). But
under honest arm semantics + honest stratification, the common-support
region is narrow: zones live where price hangs out (near the anchor,
recently visited), and genuinely-empty space is systematically
elsewhere. The floor as ruled leaves ONE primary-evaluable generator
(`sd_base`, thin) and ZERO co-primary-confirmable claims. That is the
measurement; whether the design should be re-specified (key
granularity, floor, or the live-zone control radius) is escalated in
`ASK_LEAD.md` — not silently repaired here.

## 12. Post-pivot feasibility — E1 (strength) and E2 (cross-generator)

R02-D ruling: the binary marked-vs-unmarked contrast is retired as
non-identifiable (FINDING_1); the round pivots to contrasts where both
arms are zone arrivals. Measured outcome-blind with the pinned
propensity estimator (IRLS logistic on the 7 features, per-cell, ATT
weights, trim [0.05,0.95], winsorize 99th); `smd` below = max
post-weighting |SMD| over the 7 features, gate <= 0.10.

### E1 — top vs bottom `zone_S` tercile among armed arrivals

| gen | EURUSD | GBPUSD | AUDUSD | USDJPY |
|---|---|---|---|---|
| line1_cluster | 0.065 PASS | 0.063 PASS | 0.035 PASS | 0.024 PASS |
| fractal_h1 | 0.026 PASS | 0.027 PASS | 0.013 PASS | 0.020 PASS |
| kde_swing | 0.088 PASS | 0.103 FAIL | 0.069 PASS | 0.076 PASS |
| profile_va | 0.228 FAIL | 0.188 FAIL | 0.146 FAIL | 0.151 FAIL |
| sd_base | 0.051 PASS | 0.055 PASS | 0.044 PASS | 0.058 PASS |
| ref_levels | 0.678 FAIL | 0.634 FAIL | 0.549 FAIL | 0.548 FAIL |

Arm sizes (top/bot, per symbol): line1 5.2-6.0k, fractal 4.8-5.6k,
kde 3.3-3.8k, profile 745-877, sd 1.75-1.88k, ref 4.1-4.5k.
Trims near zero (<2%) except ref_levels (14-17% arm A, 35-52% arm B —
propensity separates, still fails).

E1 fresh-restricted (D11 confirmatory): fails its own balance gate in
23/24 cells (0.077-0.697; only AUDUSD line1 0.098 passes). Strong
zones attract retests -> freshness is entangled with the assignment;
declared limitation, per ruling no relaxation attempted.

E1 exact-strata robustness view: supT_exact 0.30-0.45 for the passing
gens (line1 0.42-0.45, fractal 0.43-0.44, kde 0.30-0.33, sd 0.16-0.20)
— low because tercile-vs-tercile within treated strata is a much
finer partition; reported, not gated.

### E2 — marked by g not h vs marked by h not g (finer grid)

Balance gate per pair (P = <=0.10 all-check; values = max post SMD):

| pair | EURUSD | GBPUSD | AUDUSD | USDJPY |
|---|---|---|---|---|
| line1|fractal | 0.116 F | 0.088 P | 0.129 F | 0.113 F |
| line1|kde | 0.175 F | 0.187 F | 0.156 F | 0.185 F |
| line1|profile | 0.238 F | 0.236 F | 0.346 F | 0.416 F |
| line1|sd | 0.054 P | 0.063 P | 0.131 F | 0.162 F |
| line1|ref | 0.106 F | 0.049 P | 0.101 F | 0.148 F |
| fractal|kde | 0.028 P | 0.008 P | 0.018 P | 0.022 P |
| fractal|profile | 0.021 P | 0.028 P | 0.023 P | 0.040 P |
| fractal|sd | 0.082 P | 0.086 P | 0.093 P | 0.111 F |
| fractal|ref | 0.112 F | 0.159 F | 0.081 P | 0.107 F |
| kde|profile | 0.269 F | 0.572 F | 0.392 F | 0.404 F |
| kde|sd | 0.031 P | 0.037 P | 0.037 P | 0.065 P |
| kde|ref | 0.047 P | 0.089 P | 0.028 P | 0.033 P |
| profile|sd | 0.083 P | 0.080 P | 0.063 P | 0.085 P |
| profile|ref | 0.025 P | 0.028 P | 0.015 P | 0.013 P |
| sd|ref | 0.070 P | 0.077 P | 0.014 P | 0.024 P |

Pairs evaluable on all 4 symbols (7): fractal|kde, fractal|profile,
kde|sd, kde|ref, profile|sd, profile|ref, sd|ref. Failure modes are
structural: all five line1 pairs mostly fail (the "line1 but not h"
arm is large and heterogeneous — line1 marks nearly everywhere, so
its complement is rare and odd); kde|profile fails everywhere (arm B
only ~230-440 events and propensity saturates near 0.9 — the two
generators rarely disagree); fractal|ref and fractal|sd are marginal
(0.081-0.159 across symbols).

## 13. Post-pivot verdict

The pivot works as the ruling expected: both-arms-are-zone-arrivals
contrasts are dramatically healthier than the retired binary contrast
(E1: 4/6 generators evaluable on >= 3/4 symbols; E2: 7/15 pairs
evaluable everywhere, plus several near-misses). The honest residual
failures are real findings, not fixable defects:

- `profile_va` and `ref_levels` strength scores cannot be evaluated by
  E1 — declared UNDERPOWERED in the prereg.
- `line1_cluster` cannot serve as a cross-generator comparator in E2 —
  its marks are too dense for a "not-marked" arm to exist meaningfully.
- The fresh-to-zone confirmatory is evaluable almost nowhere — the
  doubled-bar (D7-translated) rule governs nearly all E1 claims.

Outcome-blind throughout: no outcome was joined at any point above.

## 14. R02-E measurements — recency sub-gate + residual-strength confirmatory

Per ruling R02-E: fresh restriction dropped (mechanical failure, 23/24);
replaced by (a) `since_near` claim-gate |SMD| <= 0.05, and (b) the
residual-strength confirmatory (OLS of zone_S on the 7 propensity
features + zone_touches; identical tercile contrast on residuals).

`since_near` post-weighting |SMD| per E1 cell (claim gate <= 0.05):

| gen | EURUSD | GBPUSD | AUDUSD | USDJPY | recency-separated |
|---|---|---|---|---|---|
| line1_cluster | 0.033 | 0.042 | 0.018 | 0.024 | 4/4 |
| fractal_h1 | 0.026 | 0.027 | 0.013 | 0.020 | 4/4 |
| kde_swing | 0.088 | 0.103 | 0.069 | 0.076 | 0/4 -> RECENCY-UNSEPARATED |
| profile_va | 0.228 | 0.167 | 0.146 | 0.151 | (underpowered) |
| sd_base | 0.051 | 0.040 | 0.044 | 0.058 | 2/4 |
| ref_levels | 0.678 | 0.634 | 0.549 | 0.548 | (underpowered) |

Residual-strength confirmatory balance (max post |SMD| over the 7
features, top vs bottom residual tercile): all 24 cells PASS at
0.0013-0.035 — near-zero by construction (residual orthogonal to the
regressors). Arm sizes equal the primary's tercile arms.

R02-E2 attenuation diagnostic — R-squared of the strength ~
covariates regression (share of the score recency+geometry explain),
and residual variance share, per cell:

| gen | EURUSD | GBPUSD | AUDUSD | USDJPY |
|---|---|---|---|---|
| line1_cluster | 0.317 / 0.683 | 0.321 / 0.679 | 0.322 / 0.678 | 0.304 / 0.696 |
| fractal_h1 | 0.346 / 0.654 | 0.340 / 0.660 | 0.363 / 0.637 | 0.360 / 0.640 |
| kde_swing | 0.417 / 0.583 | 0.408 / 0.592 | 0.414 / 0.586 | 0.402 / 0.598 |
| profile_va | 0.421 / 0.579 | 0.463 / 0.537 | 0.389 / 0.611 | 0.401 / 0.599 |
| sd_base | 0.380 / 0.620 | 0.358 / 0.642 | 0.404 / 0.596 | 0.409 / 0.591 |
| ref_levels | 0.545 / 0.455 | 0.540 / 0.460 | 0.531 / 0.469 | 0.528 / 0.472 |

(R2 / residual variance share per cell.) NO cell reaches the 0.90
attenuation floor — every score retains 45-70% residual variance, so
the residual confirmatory carries evidential weight in all 24 cells.
Note the asymmetry vs D22: `ref_levels`' propensity separation lives
in the ARM ASSIGNMENT (tercile membership is predictable), while
zone_S itself is only ~53% explained — consistent with a score whose
tercile split tracks covariates but whose continuous value does not.


## 15. Updated verdict

- E1 claim-carrying cells: `line1_cluster` and `fractal_h1` on all 4
  symbols; `sd_base` on GBPUSD+AUDUSD only (EURUSD/USDJPY miss the
  0.05 recency gate at 0.051/0.058); `kde_swing` produces estimates
  but is stamped RECENCY-UNSEPARATED on all 4.
- `profile_va`, `ref_levels`: UNDERPOWERED-BY-CONSTRUCTION (D22) —
  their strength scores have no independent variation left to test.
- E2 unchanged by R02-E (ruling scoped to E1 confirmatory).
- No outcome joined anywhere above.

## 16. R02-G re-measurement — side in the model, zone-level recency

Under the 8-feature propensity model (side added, D24): post-weighting
`side` |SMD| <= 0.086 in EVERY cell — the reviewer's raw 0.14-0.32
side imbalance is fully absorbed by weighting, and **no previously
balance-passing cell lost its pass**. E2 pair verdicts are unchanged
in kind (same 7 pairs evaluable on all 4 symbols).

The consequential change is the zone-level recency sub-gate (D25:
since_near + zone_since_touch + zone_fresh, all <= 0.05 under the same
weights). Measured per E1 cell (max of the three features shown):

| gen | EURUSD | GBPUSD | AUDUSD | USDJPY |
|---|---|---|---|---|
| line1_cluster | 0.693 | 0.640 | 0.661 | 0.663 |
| fractal_h1 | 1.066 | 1.094 | 1.022 | 1.014 |
| kde_swing | 2.202 | 2.300 | 1.723 | 1.830 |
| profile_va | 2.955 | 2.823 | 2.116 | 2.202 |
| sd_base | 0.972 | 0.906 | 0.868 | 0.826 |
| ref_levels | 45.5 | 49.0 | 43.9 | 42.0 |

**All 24 E1 primary cells are RECENCY-UNSEPARATED.** The driver is
`zone_fresh` (share SMD 0.64-1.13): top-tercile zone_S selection is
inseparable from an in-window retest of the zone — the F1 channel,
measured inside E1 rather than assumed away. `zone_since_touch` shows
the same (0.32-2.96; ref_levels saturates the 1440 cap because its
zones are essentially never re-touched).

Residual confirmatory after D25 (zone_last_touch + zone_fresh added to
the OLS): balance PASS 24/24 (<=0.035); R2 = 0.36-0.90 (line1 0.36-0.38,
fractal 0.46-0.48, sd_base 0.48-0.52, kde 0.80-0.81, profile 0.82-0.84,
ref_levels 0.888-0.898 — a hair under the 0.90 attenuation guard, does
not trigger but flagged near-boundary). The residual arms' own recency
sub-gate passes in 6/24 cells: sd_base EURUSD+GBPUSD, fractal_h1
AUDUSD+USDJPY, line1 GBPUSD, ref_levels USDJPY.

## 17. Post-R02-G verdict

- Item 1 (`side`) cost zero cells — absorbed by weighting everywhere.
- Item 2 (zone recency) costs every E1 primary cell its claim
  eligibility: the strength contrast cannot be recency-separated on
  this data at the zone level. Estimates will still be produced;
  claims ride on the residual confirmatory alone.
- The residual confirmatory is evaluable-and-recency-separated in
  exactly the cells listed above — that is the surviving claim path.
- No outcome joined anywhere.

## 18. R02-H — E3 recency head-on, blind feasibility

E3 arms = zone_since_touch terciles on the armed-overlap treated set
(RECENT = bottom, STALE = top; s >= q67 so the never-touched SINCE_CAP
mass is the stale arm). Propensity/balance on E3_FEATURES (7
covariates, NO recency variable — it is the treatment). Measured:

| gen | EURUSD | GBPUSD | AUDUSD | USDJPY |
|---|---|---|---|---|
| line1_cluster | 0.049 P | 0.051 P | 0.032 P | 0.049 P |
| fractal_h1 | 0.064 P | 0.050 P | 0.050 P | 0.066 P |
| kde_swing | 0.047 P | 0.055 P | 0.034 P | 0.041 P |
| profile_va | 0.139 F | 0.114 F | 0.070 P | 0.046 P |
| sd_base | 0.089 P | 0.093 P | 0.044 P | 0.054 P |
| ref_levels | 0.107 F | 0.119 F | 0.076 P | 0.073 P |

Natural overlap confirmed: trimmed shares 0.00-0.03 everywhere, no
degenerate bounds, arm sizes balanced (recent/stale ~1:1). Evaluable:
line1, fractal, kde, sd_base on all 4 symbols; profile_va and
ref_levels on AUDUSD+USDJPY only (EURUSD/GBPUSD cells underpowered).

## 19. R02-J — E3 under the corrected covariate set

`since_near` + `zone_touches` added to E3_FEATURES (9 features);
`zone_S` reported-but-excluded (treatment consequence, D34);
`cap_share_stale` and `zone_s_smd_diag` reported per cell; a
saturation guard added to balance_report (kept arms < 50 post-trim
can never pass). Post-J balance gate:

| gen | EURUSD | GBPUSD | AUDUSD | USDJPY | cap_s range |
|---|---|---|---|---|---|
| line1_cluster | 0.061 P | 0.062 P | 0.045 P | 0.059 P | 0.04-0.06 |
| fractal_h1 | 0.138 F | 0.100 P | 0.147 F | 0.115 F | 0.08-0.12 |
| kde_swing | 0.199 F | 0.308 F | 0.132 F | 0.134 F | 0.63-0.76 STAMP |
| profile_va | 0.487 F | 0.344 F | 0.238 F | 0.394 F | 0.72-0.84 STAMP |
| sd_base | 0.159 F | 0.241 F | 0.167 F | 0.166 F | 0.00 |
| ref_levels | SAT | SAT | SAT | SAT | 1.00 STAMP |

Section 18's naive E3 picture is superseded: with the confounders
controlled, only line1_cluster passes 4/4 and fractal_h1 keeps GBPUSD.
kde/profile carry STALE~NEVER-TOUCHED (cap_s > 0.50) even where they
fail balance anyway; ref_levels saturates (trim 1.00/1.00) and its
stale arm is 100% never-touched — a different experiment, excluded
from any E3 recency claim. zone_s_smd_diag 0.64-4.23 confirms the
bundled-contrast caveat (D36).
