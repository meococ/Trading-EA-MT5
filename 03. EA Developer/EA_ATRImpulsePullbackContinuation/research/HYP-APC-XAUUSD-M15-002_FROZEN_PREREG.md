# HYP-APC-XAUUSD-M15-002 — frozen engineering revision and untuned baseline

Status: `FROZEN_PRE_OUTCOME_BUILD`

APC002 is a fresh engineering child of terminal APC001. APC001 opened no admissible economics: AlphaFactory rejected it for missing D0 provenance and the EA reported runtime failure on valid flat bars. APC002 changes only those two engineering behaviors.

## Frozen identity and split

- Hypothesis: `HYP-APC-XAUUSD-M15-002`
- EA: `EA_ATRImpulsePullbackContinuation`
- Variant: `ATR14_EMA50_ADX14_IMPULSE_PULLBACK_RELEASE_V2_D0_FLATSAFE`
- Magic: `5603902`
- XAUUSD M15; Model 0; execution mode 0; fixed delay 0; current spread; deposit 100000 USD; leverage 1:100.
- TRAIN `[2010-01-04, 2018-01-01)`, validation `[2018-01-01, 2021-01-01)` sealed, final holdout `[2021-01-01, 2023-01-01)` sealed.
- One untuned TRAIN baseline. No same-ID retry, optimization, validation or holdout before the baseline passes.

## Frozen mechanism

Signal, indicator periods, thresholds, stop, target, maximum hold, position sizing and risk gates are byte-semantically unchanged from APC001: completed-bar ATR14 impulse `1.35`, body fraction `0.55`, close location `0.70`; one-bar pullback TR `0.85 ATR`; EMA50 slope; ADX14 at least `18` and rising with DI polarity; release extension no more than `0.35 ATR`; stop buffer `0.20 ATR`; TP `1.45R`; ten completed M15 bars; 0.25% risk; at most one signal per broker date.

Engineering changes only:

1. OnInit emits and validates the exact AlphaFactory `DATA_EPOCH_D0_SERIES_PROOF` using nondecision M5/M1 series metadata and a single `CopyTime` witness from the proven M5 first epoch.
2. A finite, geometrically valid impulse bar with true range exactly zero is consumed as a non-signal before close-location division. Nonfinite/negative TR remains fatal.

## Acceptance

- Compile 0 errors / 0 warnings; focused tests pass; nonrepaint audit passes with exactly one authorized nondecision provenance `CopyTime`; independent review passes.
- Journal has exactly one distinct valid D0 record, no `APC002_FATAL`, and summary `runtime_failed=false`.
- TRAIN: PF > 1.30 after native spread/commission/swap, expectancy > 0, 2–5 closed positions per elapsed calendar week, equity DD <= 8%, each direction >=30%, no calendar year >35%.
- Any headline economic failure kills APC002 without threshold/session/direction/stop/target/hold/risk rescue. If all pass, verified x1/x1.5/x2 cost stress is required before validation.
