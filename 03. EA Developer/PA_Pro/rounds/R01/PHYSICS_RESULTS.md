# R01 PHYSICS_RESULTS — zone-generator level-physics bake-off
**HEADLINE: R01 executed a faithful, verified, pre-registered experiment and produced NO VALID EVIDENCE about zone physics in either direction (Lead R01-FINAL-B).**
**The preregistered control compares two different episode types (approach-distance confound, reviewer F1), so neither the negative bounce result nor the large positive continuation result can be attributed to the zones. WINNER: NONE.**

UTC 2026-09-20T15:37:09Z · DESIGN · core symbols EURUSD, GBPUSD, USDJPY, AUDUSD · execution M5 · seed 20260920

**Estimand (Lead ruling R01-C1, quoted verbatim):**

> D = P(bounce | fresh approach to an ARMED zone of generator g) − P(bounce | fresh approach to a geometry-matched arbitrary band). D is the incremental value of using this generator's zones instead of an arbitrary level with the same geometry.

Hashes: prereg `91b21dc7dc5d3701ba5d68904c8621eb7e10df9e1324bf4aae59d26335252184` · addendum-2 `dcb85c81e4d1755d7fa2dd8ef5fd934e4f2b65c62556308aa6be4f5b964088ce` · physics code `d118b72fee2b6e11493386eca5f4fb8b195d801a6e712b297edddc358c290be9` · zones code `3676262d514d50cea959944387559471c999578112f651f641fb0ae12cf1c92d` · freeze `10a9830eb1f34cadc93fd8876f2d311f35fd175af36d974b434ee7330258be44`

A FAIL means: no measurable edge over arbitrary levels of the same geometry. It does NOT mean levels do not exist.

## Pooled core results (ARMED population)

| generator | events | resolved | K̄ (ctrl/ev) | cov med | D_top | 95% CI | p | D_mid | D_bot | mono | gate | BH q | D_cont_top | N brk top | cont gate | BH q cont |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `line1_cluster` | 44051 | 30782 | 5.34 | 0.55 | -0.0555 | [-0.0686,-0.0426] | 1.00000 | -0.0479 | -0.0462 | no | fail | 1.0000 | 0.2165 | 3323 | fail | 0.0002 |
| `fractal_h1` | 26243 | 19031 | 4.73 | 0.24 | -0.0630 | [-0.0807,-0.0450] | 1.00000 | -0.0596 | -0.0493 | no | fail | 1.0000 | 0.2087 | 2100 | fail | 0.0002 |
| `kde_swing` | 23311 | 16009 | 5.67 | 0.32 | -0.0573 | [-0.0746,-0.0394] | 1.00000 | -0.0450 | -0.0476 | no | fail | 1.0000 | 0.2867 | 1710 | PASS | 0.0002 |
| `profile_va` | 4785 | 3288 | 5.45 | 0.00 | -0.0532 | [-0.0937,-0.0131] | 0.99610 | -0.0489 | -0.0525 | no | fail | 1.0000 | 0.2730 | 336 | fail | 0.0002 |
| `sd_base` | 10607 | 7450 | 6.08 | 0.07 | -0.0699 | [-0.0945,-0.0454] | 1.00000 | -0.0317 | -0.0452 | no | fail | 1.0000 | 0.2857 | 891 | fail | 0.0002 |
| `ref_levels` | 23819 | 18218 | 4.79 | 0.13 | -0.0737 | [-0.0898,-0.0574] | 1.00000 | -0.0758 | -0.0847 | yes | fail | 1.0000 | 0.2471 | 2256 | PASS | 0.0002 |

## Gate detail (charter thresholds, SHORTLIST section 4)

- `line1_cluster`: checks {"D_top_ge_5pp": false, "ci_lo_gt_0": false, "monotone": false, "symbols_3of4": false, "years_4of6": false} · symbols +0/4 · years +0/6 · BH q(bounce) 1.0000 rejected False → FAIL
- `fractal_h1`: checks {"D_top_ge_5pp": false, "ci_lo_gt_0": false, "monotone": false, "symbols_3of4": false, "years_4of6": false} · symbols +0/4 · years +0/6 · BH q(bounce) 1.0000 rejected False → FAIL
- `kde_swing`: checks {"D_top_ge_5pp": false, "ci_lo_gt_0": false, "monotone": false, "symbols_3of4": false, "years_4of6": false} · symbols +0/4 · years +1/6 · BH q(bounce) 1.0000 rejected False → FAIL
- `profile_va`: checks {"D_top_ge_5pp": false, "ci_lo_gt_0": false, "monotone": false, "symbols_3of4": false, "years_4of6": false} · symbols +0/4 · years +0/6 · BH q(bounce) 1.0000 rejected False → FAIL
- `sd_base`: checks {"D_top_ge_5pp": false, "ci_lo_gt_0": false, "monotone": false, "symbols_3of4": false, "years_4of6": false} · symbols +0/4 · years +0/6 · BH q(bounce) 1.0000 rejected False → FAIL
- `ref_levels`: checks {"D_top_ge_5pp": false, "ci_lo_gt_0": false, "monotone": true, "symbols_3of4": false, "years_4of6": false} · symbols +0/4 · years +0/6 · BH q(bounce) 1.0000 rejected False → FAIL

## Declared descriptive views (Addendum 2; never gates)

| generator | coverage med | contam_zone rate | contam_ref rate | S-CLEAN D_top | N kept | S-NEAR D_top |
|---|---|---|---|---|---|---|
| `line1_cluster` | 0.55 | 0.5902 | 0.3150 | -0.0401 | 3779 | -0.1533 |
| `fractal_h1` | 0.24 | 0.4181 | 0.2668 | -0.0663 | 2659 | -0.1570 |
| `kde_swing` | 0.32 | 0.6281 | 0.3482 | -0.0157 | 1662 | -0.1570 |
| `profile_va` | 0.00 | 0.1144 | 0.3645 | -0.0474 | 588 | -0.1431 |
| `sd_base` | 0.07 | 0.1361 | 0.2481 | -0.0672 | 1843 | -0.1623 |
| `ref_levels` | 0.13 | 0.2298 | 0.1936 | -0.0749 | 4207 | -0.1827 |

Declared interpretation (Addendum 2 item 5): a sparser generator is attenuated less by contamination than a denser one; selectivity is part of what this bake-off measures and is not corrected for — coverage is reported so the reader can see it.

## Winner rule (SHORTLIST section 4, pre-declared)

- eligible (resolved >= 1000): profile_va, line1_cluster, kde_swing, fractal_h1, sd_base, ref_levels
- threshold passers (charter + BH q<=0.10, bounce endpoint): none
- ranked by D_top: profile_va -0.0532, line1_cluster -0.0555, kde_swing -0.0573, fractal_h1 -0.0630, sd_base -0.0699, ref_levels -0.0737
- **WINNER: NONE (bake-off FAIL — LINES MATTER not supported)**

## Viability arithmetic (charter §4; arithmetic, no measurement)

`required bias = c_rt / (2 m) + 2.00pp`, `m` = median event-barrier ATR14(H1) of the winner's top-tercile resolved events.

| symbol | c_rt x1 | median m (pips) | required bias | measured D_top |
|---|---|---|---|---|
| — | — | — | — | no winner |

## Notes

- All 12 hypotheses (6 generators x {bounce, continuation}) are ledger trials (family=PHYSICS); the program trial count includes the historical T000001 smoke line.
- Sensitivity views NOT RUN this round: all-intact-live population, width 0.20 vs 0.25, frozen-A barriers, block bootstrap (declared in PHYSICS_PREREG §0).
- No fills, no PnL, no costs are applied; this is a reaction-proportion experiment.

## Post-run diagnostic — control distance is NOT matched (not a gate; added 2026-09-20T15:44Z)

Measured after the freeze, from the frozen tables (EURUSD, line1_cluster; same construction for all generators):

- real zone near-edge distance from c[t-1] at the anchor: median 3.78 pips (p25 2.06, p75 6.59)
- control band near-edge distance from c[t-1]: median 29.76 pips (p25 19.27, p75 49.40)
- share of control events firing on the anchor bar itself: 2.1%; within 1 day: 64.6%

Addendum 2 specifies the control near edge only as a MINIMUM distance (>= 1.0 x ATR14(H1) from
c[t-1]); it does not match the real zone's distance. Real armed zones are necessarily near price
(within 2 x ATR14(H1) by the arming rule), while control bands are drawn from the whole same-side
5-day range. The measured D is therefore confounded by approach distance and by control-event timing;
the FAIL verdict is the preregistered one, but it is NOT clean evidence against zone physics. A
distance-matched control is the first candidate design change for R02 (Lead decision).

## Lead interpretation (R01-FINAL-B; supersedes R01-D2)

> R01 executed a faithful, verified, pre-registered experiment and produced NO VALID EVIDENCE about zone physics in either direction. The preregistered control compares two different episode types, so neither the negative bounce result nor the large positive continuation result can be attributed to the zones. What R01 did deliver: an infrastructure that verifies (freeze ordering, hash chain, ledger, causality, arming parity, independently reproduced statistics), one measured methodological defect that defines the next experiment, and a defect list for the referee.

The confound (reviewer F1, measured from the frozen tables): real ARMED events fire while price hovers at/retests adjacent
structure (median near-edge distance 0.28-0.34 ATR at the anchor); a control band must sit >= 1.0 ATR away by Addendum 2 and
actually draws at a median 2.11-2.37 ATR, so a control event can only fire after price has travelled to it (impulse-arrival).
That asymmetry predicts the sign of all three of bounce, break and NONE, and of the continuation endpoint. The asymmetry is
measured and real; the causal claim that it produces the whole gap is NOT established (the control bounce rate is flat across
control-distance deciles, 0.68 +- 0.005 - consistent with a mechanism that saturates past 1 ATR, not evidence for it).

The bounce endpoint is NOT closed: what is closed is the Addendum-2 control, not the question. The earlier "stall effect"
attribution and the "round's positive finding" label for the continuation endpoint are WITHDRAWN (Lead R01-FINAL-B section 2).
The continuation result is uninterpretable under this control. No zone claim is made from R01 in either direction.
