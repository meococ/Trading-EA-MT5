# HYP-RSF-EURUSD-M5-SEQUENCE-002 — frozen preregistration

## Research question

Does replacing same-bar indicator voting with a closed-bar temporal state machine improve EURUSD M5 expectancy without route deletion, timezone cherry-picking, or indicator-parameter tuning?

This is a materially new mechanism. The terminal parent is `HYP-RSF-EURUSD-M5-ABI-CORRECTED-001` (PF 0.8516, 720 trades, net -5,238.92 USD). The complete 2018–2022 window and seven native loss charts are design-exposed; this first run is development evidence only.

## Only authorized mechanism change

`InpUseTemporalSequence=true` replaces immediate entry with one pending setup state. All inputs below are frozen before implementation and the first run:

- Minimum confirmation age: 1 completed M5 bar after arm.
- Expiry: 3 completed M5 bars after arm.
- First-active-arm wins; a later setup cannot overwrite a live arm.
- Opposite-direction setup cancels the live arm. Expiry or loss of context cancels it.
- Setup bar can never also be the entry bar.
- Context must still be valid on the confirmation bar.
- QQE direction and slope must confirm on the confirmation bar.
- TB structure must confirm on the confirmation bar.
- Price location and runway are checked before submission.

### Arm rules

- Breakout: MBB S3 long/short plus compression-origin and confidence context.
- Trend: MBB S2 long/short plus matching AIRD/VRC trend context.
- Range: MBB S1 long/short plus AIRD/VRC range context and QQE at the existing frozen extreme threshold.

### Confirmation rules

- Breakout long/short: matching TB structure and displacement; matching QQE side and reacceleration; closed price remains beyond the matching MBB band; extension beyond that band is no more than `0.35 ATR`.
- Trend long/short: matching persistent trend context; matching TB bias and structure/zone; matching QQE side and reacceleration; closed price is on the trade side of basis and no farther than `0.75` current half-width from basis.
- Range long/short: persistent range context; matching TB sweep; TB bias is not opposite; QQE reverses from the stored arm extreme; closed price remains inside the band and in the entry-side half (long at/below basis, short at/above basis).

### Runway rule

After the unchanged stop is built, range/trend trades require room from entry to the opposite MBB band of at least `0.75R`. Breakout trades use the frozen extension cap instead because the confirming close must remain outside the band.

## Frozen controls

- Symbol/timeframe: EURUSD M5; context timeframe M15.
- Development window/model: 2018-01-01 through 2022-12-31, Model 0 (generated from M1 bars; not broker real ticks).
- Sessions: London + overlap, unchanged.
- Routes: range + trend + breakout, both directions, unchanged.
- Risk: 0.20%; high-vol scale 0.50; unchanged.
- Stop geometry, structural anchors, maximum hold, cooldown and reward:risk 1.50: unchanged.
- AIRD, VRC, MBB, TB and QQE parameters: unchanged.
- Telemetry: lifecycle-v3 trade-only.
- No weekday/hour/year/direction filter is authorized.
- One development run only. No parameter sweep, optimization, validation, or holdout access under this ID.

## Development gate

All registered project gates remain binding: PF >= 1.30, 2–5 trades/week, max DD <= 8%, cost PF at 1.5x >= 1.25, cost PF at 2x >= 1.00, Monte Carlo p95 DD <= 8%. A raw PF below 1.00 is an immediate kill without cost rescue. Passing development only authorizes a separately preregistered non-overlapping OOS run; it does not authorize promotion.

## Anti-overfit boundary

The seven charts justify a causal sequence/location mechanism only. They do not estimate profitable thresholds. The frozen values above are geometry-based, round and deliberately low-dimensional. Any later change to expiry, extension, half-width, runway, route, session, stop, RR, indicator value, or direction requires a fresh hypothesis ID and increments the trial count.
