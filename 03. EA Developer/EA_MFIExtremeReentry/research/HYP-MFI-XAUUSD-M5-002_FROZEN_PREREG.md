# HYP-MFI-XAUUSD-M5-002 — Frozen Four-step Failure-swing Source Preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`  
Parent: terminal over-frequency source object `HYP-MFI-XAUUSD-M5-001`.

## Identity and legal novelty

- Hypothesis: `HYP-MFI-XAUUSD-M5-002`
- Family: `tick-volume-weighted-mfi14-four-step-failure-swing`
- Symbol/timeframe: FivePercent XAUUSD native M5 Bid bars
- Design: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation 2023–2024 and holdout 2025+ remain sealed
- Sole attempt: `MFI002-SOURCE-ATTEMPT-001`

MFI001 explicitly froze and tested only one-step 20/80 re-entry and explicitly excluded TradingView's separate four-step failure-swing pattern before its source result. MFI002 therefore adds path/state information known before MFI001 outcomes; it is not a cooldown, session filter, threshold change or signal deletion.

The exact MFI14 calculation, source, input validity, terminology limits and 20/80 levels are unchanged from MFI001. `tick_volume` remains only broker activity weight, not real money flow, exchange volume or aggressor flow.

## Bound MFI calculation dependency

- Dependency: `research/analyze_mfi_source.py`
- Dependency SHA256: `FEEB94E517FB9D8ACE560703F98BE4F28150AA0A2071D01A179C365966DFDC2E`
- Formula: typical price `(H+L+C)/3`, raw flow `TP*tick_volume`, exact 14 classified positive/negative sums and standard MFI ratio
- MFI at `i` uses source bars `i-14..i`; path processing is completed-bar only

## Exact causal FSM

The bullish and bearish machines update on every completed, valid MFI14 value. Invalid MFI resets both machines to IDLE. Equality never counts as a strict decline/rise or trigger break.

Bullish machine:

1. `IDLE -> EXTREME` whenever `MFI <= 20`; a repeated value at/below 20 restarts EXTREME.
2. `EXTREME -> ADVANCE` on the first later `MFI > 20`; set `peak = MFI`.
3. In ADVANCE, any strict new high updates `peak`.
4. The first strict decline from the prior completed MFI while current MFI remains `>20` freezes `trigger = peak` and enters PULLBACK.
5. In PULLBACK, `MFI <=20` restarts EXTREME. Otherwise, the first strict `MFI > trigger` creates a raw LONG event.

Bearish machine is exact inverse:

1. `IDLE -> EXTREME` whenever `MFI >= 80`;
2. first later `MFI <80` enters ADVANCE and sets `trough = MFI`;
3. strict new lows update `trough`;
4. first strict rise from prior MFI while current remains `<80` freezes `trigger = trough` and enters PULLBACK;
5. `MFI >=80` restarts EXTREME; otherwise first strict `MFI < trigger` creates raw SHORT.

After any raw event, reset both machines to IDLE; another event requires a fresh extreme. Simultaneous LONG/SHORT raw events are rejected and both machines reset.

An executable source event additionally requires the immediately following source timestamp to equal event-bar time plus five minutes. A raw event at a gap is consumed/reset but is not persisted as executable. No next-row price is read.

Forbidden: timeout, cooldown, debounce, daily cap, price/wick/ATR/RV/session/trend/divergence filter, parameter optimization or subgroup pruning.

## Frozen source and authority

Source manifest/data/hashes and predicate are identical to MFI001:

- manifest `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`;
- XAUUSD M5 Parquet `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`;
- only allowed source columns from MFI001;
- only `2018 <= time_utc < 2023` may materialize;
- post-event OHLC and every economic field remain forbidden.

## Gates

All must pass:

1. all hash/registry/one-shot bindings and deterministic replay;
2. at least 300,000 valid design rows;
3. MFI path-feature coverage at least 99.0% after the first 14 unavailable MFI rows;
4. exact-next timestamp coverage at least 97.0% of raw FSM events;
5. at least 500 executable events;
6. pooled executable cadence 2.0–5.0/week;
7. LONG and SHORT share each at least 30%;
8. no year above 30%;
9. every design year cadence 1.25–6.50/week;
10. zero simultaneous direction conflicts;
11. ledger contains only source/decision timestamps, direction, prior/current MFI and frozen trigger.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_MFI_FAILURE_SWING`. All pass gives `SCREENED_SOURCE_PASS_MQL5_IMFI_FAILURE_SWING_BUILD_AUTHORIZED`, allowing only native `iMFI(..., VOLUME_TICK)` plus FSM implementation/parity/correctness work. Economics remains unauthorized.

## Failure radius and exclusions

Failure applies only to this exact MFI14 four-step FSM on XAUUSD M5 2018–2022. No outcomes, MT5 tester, MQL5 build, optimization, validation, holdout, paper, promotion or live authority is opened.

