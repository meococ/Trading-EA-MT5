# HYP-EHPR-EURUSD-M15-002 — frozen source-feasibility preregistration

Status: `FROZEN_PRE_OUTCOME_ENGINEERING_REVISION`

Parent: `HYP-EHPR-EURUSD-M15-001`

## Reason for the child

The parent was stopped before its first source read because its Parquet predicate compared UTC window endpoints with broker-server `source_epoch`. The stored rows prove that `source_epoch` is not the same clock as `time_utc`. This child changes only that predicate to the canonical UTC `time_utc` field. No event count, price outcome, return, trade, PnL, MT5 run, validation row, or holdout row was observed.

## Frozen data contract

- Symbol/timeframe: EURUSD M15 derived only from complete M5 UTC triplets at offsets 0, 300, and 600 seconds.
- File: `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/EURUSD/EURUSD_M5_ALL_AVAILABLE_20260801.parquet`
- File SHA-256: `6B18C8BE6F772893428199A44708208EEB844F95BC02FD1317528E163EC72ED8`
- Manifest SHA-256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- Prehistory read: `2015-01-01T00:00:00Z` inclusive.
- DESIGN: `2016-01-04T00:00:00Z` inclusive to `2021-01-01T00:00:00Z` exclusive.
- Parquet selection: `time_utc >= prehistory_start AND time_utc < design_end`.
- Any later research-validation and holdout rows remain sealed.

## Frozen signal contract

- Input is completed-bar HL2.
- Four-bar smoother, 7-tap Hilbert coefficients `0.0962/0.5769`, correction multiplier `0.075 * prior_period + 0.54`.
- I2/Q2/Re/Im smoothing is `0.2/0.8`; period rate limit is `0.67x/1.5x`; period clamp is `[6,50]`; dominant-cycle smoothing is `0.33/0.67`.
- Warm-up is 40 consecutive M15 bars. Phase is `atan2(Q1,I1)` only when `hypot(I1,Q1) > 1e-12`; dominant period must be finite, positive, and `< 42.5`.
- `diff = sin(phase) - sin(phase + pi/4)`.
- LONG event: prior usable diff `<= 0` and current usable diff `> 0`.
- SHORT event: prior usable diff `>= 0` and current usable diff `< 0`.
- Unexpected intraday gaps reset all estimator state; recognized weekend pauses preserve state.
- An event is executable only when the exact next M15 timestamp exists. Decision time is the next M15 open; no next-bar price is read.

## Frozen source-only gates

- Complete derived-M15 coverage `>= 99%`.
- Usable estimator coverage in DESIGN `>= 80%`.
- Raw-event exact-next coverage `>= 97%`.
- Executable events `>= 1000`, every calendar year `>= 100`.
- Each direction share `>= 45%`; maximum calendar-year share `<= 25%`.
- Zero direction conflicts and all event features finite.
- Exactly one attempt: `EHPR002-SOURCE-ATTEMPT-001`.

## Prohibitions and next authority

The attempt may output timestamps, direction, estimator state, counts, coverage, balance, and concentration only. It may not read post-event OHLC, calculate returns or trades, build MQL5, launch MT5, optimize, or inspect validation/holdout. A pass only permits drafting a separately reviewed MQL5 Model-0 child; it is not evidence of edge.

Any later economic child is bound to the registry acceptance contract: PF `>= 1.30`, 2–5 completed trades/week, DD `<= 8%`, PF `>= 1.25` at 1.5x cost, PF `>= 1.00` at 2x cost, and Monte Carlo p95 DD `<= 8%`.
