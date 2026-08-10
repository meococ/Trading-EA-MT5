# HYP-MFI-XAUUSD-M5-003 — Frozen Strict Joint Price–MFI Pivot Divergence Source Preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`  
Parents: terminal over-frequency source objects `HYP-MFI-XAUUSD-M5-001` and `HYP-MFI-XAUUSD-M5-002`.

## Identity and legal novelty

- Hypothesis: `HYP-MFI-XAUUSD-M5-003`
- Family: `tick-volume-weighted-mfi14-strict-joint-pivot-divergence`
- Symbol/timeframe: FivePercent XAUUSD native M5 Bid bars
- Design: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation 2023–2024 and holdout 2025+ remain sealed
- Sole attempt: `MFI003-SOURCE-ATTEMPT-001`

MFI001 tested one-step 20/80 re-entry and MFI002 tested a four-state 20/80 failure swing. Both were terminally parked only for excessive source cadence. MFI003 removes thresholds and path states and instead requires strict, contemporaneous price–oscillator pivot divergence. This is a different decision surface, not a cooldown, session filter, threshold rescue or deletion of losing signals.

`tick_volume` remains only unsigned broker activity weight. MFI is not cash flow, exchange volume or aggressor flow.

## Bound MFI calculation dependency

- Dependency: `research/analyze_mfi_source.py`
- Dependency SHA256: `FEEB94E517FB9D8ACE560703F98BE4F28150AA0A2071D01A179C365966DFDC2E`
- Formula: typical price `(H+L+C)/3`, raw flow `TP*tick_volume`, exact 14 classified positive/negative sums and standard MFI ratio
- MFI at bar `i` uses source bars `i-14..i`

## Exact causal mapping

For pivot center `p`, confirmation bar `c=p+2` is completed before evaluation.

- Joint low: `low[p]` is strictly below each of `low[p-2], low[p-1], low[p+1], low[p+2]`, and `MFI[p]` is strictly below each corresponding MFI value.
- Joint high: exact inverse, with both price high and MFI strictly above all four neighbors.
- LONG raw event: the current joint low has price strictly below and MFI strictly above the immediately preceding valid joint-low anchor.
- SHORT raw event: the current joint high has price strictly above and MFI strictly below the immediately preceding valid joint-high anchor.
- Equality never qualifies.
- The first joint pivot initializes only. Every later joint pivot replaces the same-side anchor whether or not it signals. LONG and SHORT anchors are independent.
- Any nonfinite/invalid input or any non-5-minute interval in the complete dependency window resets both anchors.
- A raw event without an exact next source timestamp at `c+5 minutes` is consumed but not persisted. The current pivot still becomes the anchor.
- Decision timestamp is confirmation-bar close, represented as `c+5 minutes`. Only that next timestamp may be inspected; no next-row price is read.

The complete dependency window for confirmation `c` is `c-18..c`: the five MFI pivot-comparison values are at `c-4..c`, and the earliest needs raw inputs back to `c-18`. Therefore the first usable confirmation index is exactly 18.

Forbidden: 20/80 thresholds, sweep/reclaim/retest, ATR, ADX, wick, RV, trend, session, timeout, cooldown, debounce, daily cap, parameter optimization, subgroup pruning and any outcome field.

## Frozen source and authority

- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- XAUUSD M5 Parquet SHA256: `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`
- Only the MFI001 required source columns may be read.
- PyArrow must materialize only `2018 <= time_utc < 2023`, followed by a fail-closed post-read window assertion.
- Post-event OHLC and every economic field remain forbidden.

## Gates

All must pass:

1. all hash/registry/one-shot bindings and deterministic replay;
2. at least 300,000 valid design rows;
3. usable confirmation-window coverage at least 99.0% after exactly 18 warmup rows;
4. exact-next timestamp coverage at least 97.0% of raw divergence events;
5. at least 500 executable events;
6. pooled executable cadence 2.0–5.0/week;
7. LONG and SHORT share each at least 30%;
8. no year above 30%;
9. every design year cadence 1.25–6.50/week;
10. zero simultaneous direction conflicts;
11. ledger keys equal the frozen allowlist: hypothesis, pivot/confirmation/decision timestamps, direction, and previous/current source pivot price and MFI only.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_MFI_JOINT_DIVERGENCE`. All pass gives `SCREENED_SOURCE_PASS_MQL5_IMFI_JOINT_DIVERGENCE_BUILD_AUTHORIZED`, allowing only native `iMFI(..., VOLUME_TICK)` plus strict-pivot collector/parity/correctness work. Economics remains unauthorized.

## Failure radius and exclusions

Failure applies only to this exact N=2 strict joint price–MFI14 divergence mapping on FivePercent XAUUSD M5, 2018–2022. No outcomes, MT5 tester, MQL5 build, optimization, validation, holdout, paper, promotion or live authority is opened.
