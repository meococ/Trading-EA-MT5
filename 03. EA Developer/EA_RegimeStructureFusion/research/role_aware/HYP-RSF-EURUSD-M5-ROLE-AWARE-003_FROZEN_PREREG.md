# HYP-RSF-EURUSD-M5-ROLE-AWARE-003 — frozen preregistration

## Research question

Does a causal, role-separated event state machine create positive EURUSD M5
expectancy where same-bar fusion and the delayed `SEQUENCE-002` AND-chain both
failed?

This is a new mechanism, not a parameter rescue. Design evidence is limited to:

- corrected-ABI control `HYP-RSF-EURUSD-M5-ABI-CORRECTED-001`: 720 trades,
  PF 0.8516, net -5238.92 USD;
- temporal control `HYP-RSF-EURUSD-M5-SEQUENCE-002`: 48 trades, PF 0.5519,
  net -2531.44 USD;
- seven preregistered native post-exit MT5 charts and their closed-bar joins in
  `HYP-RSF-EURUSD-M5-NATIVE-OUTCOME-006_RESULT.md`.

The complete 2018-2022 development block is design-exposed. No 2023-current
validation or holdout data is authorized under this development hypothesis.

## Frozen engine roles

The five engines cannot vote on an entry bar. Each owns one non-overlapping
decision:

1. **AIRD — slow market state.** Its held state routes Trend/Range and its
   posterior separation blocks ambiguous states. AIRD never triggers an order.
2. **VRC — volatility permission.** Compression/low-vol permits Breakout;
   Range/Mean-Reversion permits Range; high-vol only reduces risk. VRC direction
   cannot overrule TB structure.
3. **TB SMC — direction and stored price level.** Structure/bias selects side;
   sweep or breakout level supplies reclaim/retest and structural invalidation.
4. **MBB — location and objective.** S1/S2/S3 only arms a route. Basis/bands
   define pullback, retest, extension and the Range target.
5. **QQE — final transition trigger.** QQE is evaluated only after the stored
   price event. It never supplies regime or location.

## Frozen causal state machine

`InpUseRoleAwareSequence=true` is mutually exclusive with
`InpUseTemporalSequence=true`. One setup may be active at a time. A same-side
event cannot overwrite it; an opposite event cancels it and becomes a fresh
arm that still cannot enter on that bar. It expires after 12 completed M5 bars;
the arm bar can never enter.

### AIRD ambiguity rule

Trend/Range arming requires the held state's posterior to exceed the largest
alternative by at least `0.10`. This is two times the unchanged AIRD jump margin
(`0.05`) and is a calibration rule, not a value selected from a profitable
readout.

### Trend pullback route

Arm on MBB S2 in the direction of AIRD's separated Bull/Bear state and matching
TB bias/structure. Store MBB basis as the reclaim level. A later bar may enter
only when:

- price closes back on the trend side of the stored basis;
- current close is no farther than `0.75` current MBB half-width from basis;
- TB bias has not flipped and opposite TB structure has not appeared;
- QQE primary and secondary cross zero in the intended direction on that later
  bar.

Stop/target/risk geometry remains the existing structural geometry and 1.50R so
the entry mechanism remains identifiable.

### Breakout acceptance/retest route

Arm on MBB S3 only when VRC is Compression/low-vol at origin and TB has matching
structure plus displacement. Store the released outer band as the breakout
level. The first later bar that touches within `0.20 ATR` of that level and
closes no more than `0.20 ATR` through it becomes the retest. No entry is allowed
on the retest bar. A later bar enters only when:

- price closes on the breakout side of the stored level;
- close is no farther than `0.50 ATR` from the stored level on that side;
- TB bias/structure has not flipped;
- QQE is on the intended side and its primary and secondary slopes reaccelerate
  in the intended direction after the retest.

A close more than `0.50 ATR` through the stored breakout level cancels the arm.
Stop/target/risk geometry remains the existing breakout geometry and 1.50R.

### Range sweep/reclaim route

Arm on MBB S1 only when AIRD has a separated Range state, VRC is Range or
Mean-Reversion, and TB reports the matching edge sweep. Store the TB sweep price
as the reclaim level. A later bar may enter only when:

- price closes back through the stored sweep level and remains inside MBB;
- close remains in the entry-side half of the band;
- TB bias is not opposite and opposite TB structure has not appeared;
- QQE primary and secondary cross zero in the reversal direction.

The structural stop is unchanged. The target is the current MBB basis, because
that is the causal mean-reversion objective. Entry is rejected unless basis
distance is at least `1.00R`; target must also be on the profitable side of the
live bid/ask.

## Frozen controls

- Symbol/timeframe: EURUSD M5; context timeframe M15.
- Development window/model: 2018-01-01 through 2022-12-31, Model 0.
- Sessions: London + overlap; both directions; all three routes.
- Risk: 0.20%; high-vol multiplier 0.50; maximum DD/daily loss unchanged.
- Cooldown, maximum hold, spread-to-stop, stop ATR bounds, structure buffer and
  indicator parameters unchanged.
- Parameters introduced by this hypothesis only:
  - `InpRoleStateMargin=0.10`
  - `InpRoleExpiryBars=12`
  - `InpRoleRetestToleranceAtr=0.20`
  - `InpRoleBreakoutInvalidationAtr=0.50`
  - `InpRoleBreakoutMaxTriggerExtensionAtr=0.50`
  - `InpRoleTrendMaxBasisDistanceHalfWidths=0.75`
  - `InpRoleRangeMinTargetR=1.00`
- Telemetry: lifecycle-v3 trade-only plus role-state counters.
- One development run. No sweep, optimization, direction deletion, timezone
  selection or route selection is authorized under this ID.

## Development gate

Raw PF below 1.00 is an immediate kill. Otherwise the registered project gates
apply: PF > 1.30 after x1 verified cost, 2-5 executed trades per elapsed week,
DD <= 8%, x1.5 cost PF >= 1.25, x2 PF >= 1.00, and Monte Carlo p95 DD within the
declared budget. A development pass only authorizes a fresh cross-symbol and
non-overlapping validation campaign; it does not authorize promotion.

## Anti-overfit boundary

The seven loss charts justify event order, role separation and location-aware
geometry. They do not authorize fitting individual dates, hours, weekdays,
directions or thresholds. Any modification to the frozen state logic or values
after the first economic readout requires a new hypothesis ID and increments
trial debt.
