# HYP-ST-XAUUSD-H1-002 — Frozen flat-bar-valid Supertrend 10/3 source preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`  
Parent: `HYP-ST-XAUUSD-H1-001`  
Informing evidence: ST001 consumed its sole attempt before indicator analysis because its input contract required `high > low`; the source-only diagnostic found 194 finite `H=L=C` H1 bars and no other OHLC defect. No ST001 event, cadence or economic result exists.

## Identity and bounded revision

- Hypothesis: `HYP-ST-XAUUSD-H1-002`
- Family: `supertrend-atr10-factor3-recursive-direction-flip-flatbar-valid`
- Symbol/timeframe: FivePercent XAUUSD native H1 Bid bars
- State initialization source: earliest manifest H1 bar `2004-06-11T04:00:00Z`
- Scored design: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation 2023–2024 and holdout 2025+ remain sealed
- Sole attempt: `ST002-SOURCE-ATTEMPT-001`
- Formula dependency: the exact hash-bound ST001 `calculate_supertrend` implementation, SHA-256 `2B48F3AA01BB2B00EB66A5AE97346F810EF549CEC2626B0DC9F175EEC890211C`

The only revision from ST001 is source geometry. Every row must have finite high, low and close, `high >= low`, and `low <= close <= high`. A zero-range row is valid only when this implies `high=low=close`. Such a row contributes `high-low=0` to the first TR term; gap terms still use the prior close exactly as frozen. Invalid rows fail the attempt. No row is removed, altered or interpolated, and recursive state is never reset.

This correction is preregistered from source validation only, before any Supertrend events were computed. It does not change signal selectivity and is not an outcome-informed rescue.

## Exact ATR10

- `TR[0] = high[0]-low[0]` because no prior close exists.
- For `i>0`, `TR[i]=max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1]))`.
- ATR is unavailable through index 8.
- `ATR[9] = mean(TR[0..9])`.
- For `i>9`, `ATR[i] = (9*ATR[i-1] + TR[i])/10` (Wilder RMA).

## Exact Supertrend update order

Factor is exactly `3.0`; source is `hl2=(high+low)/2`.

At first ATR-ready bar `i=9`:

- final upper = `hl2 + 3*ATR`;
- final lower = `hl2 - 3*ATR`;
- semantic state = `DOWN`;
- Supertrend line = final upper;
- initialization is not a flip.

For every later completed bar:

1. Compute basic upper/lower from current `hl2` and ATR.
2. Final upper becomes basic upper iff it is strictly below prior final upper or prior close is strictly above prior final upper; otherwise retain prior upper.
3. Final lower becomes basic lower iff it is strictly above prior final lower or prior close is strictly below prior final lower; otherwise retain prior lower.
4. If the prior Supertrend line was prior final upper, current state becomes `UP` only when current close is strictly above current final upper; otherwise it is `DOWN`.
5. If the prior line was prior final lower, current state becomes `DOWN` only when current close is strictly below current final lower; otherwise it is `UP`.
6. Current line is final lower in `UP`, final upper in `DOWN`.

Equality retains the regime. State uses explicit `UP`/`DOWN` enums. Normal market closures and missing wall-clock hours do not reset the recursive bar-count state.

## Signal and decision mapping

- Raw LONG: completed-bar state changes `DOWN -> UP` in the scored window.
- Raw SHORT: completed-bar state changes `UP -> DOWN`.
- An event is executable only if the immediately following native H1 timestamp equals source time plus one hour. A raw gap flip is counted then consumed without persistence. Only the next timestamp is inspected.
- Decision timestamp is source bar time plus one hour.
- The ledger may contain only hypothesis ID, source/decision timestamps, direction, prior/current semantic state, current ATR10, final bands, Supertrend line and source close. It contains no next price, return, excursion or PnL.

Forbidden: alternative ATR seed/smoothing/length/factor/source, initialization at 2018, reset or skip at flat bars/closures, additional confirmation/filter/session/cooldown, optimization and outcomes.

## Frozen source and gates

- Manifest SHA-256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- Native H1 data SHA-256: `B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3`
- Allowed materialization: all rows with `time_utc < 2023-01-01T00:00:00Z`; no lower bound because recursion begins at manifest inception.
- Only symbol/timeframe/source epoch/time/UTC ambiguity/high/low/close may be read.
- Scoring and ledger persistence are restricted to 2018–2022.

All gates must pass:

1. Hash/registry/one-shot bindings and byte-identical same-frame replay.
2. Exact manifest inception and at least 25,000 design rows.
3. Design-state feature coverage at least 99.0%.
4. Exact-next H1 coverage at least 97.0% of raw design flips.
5. At least 500 executable events.
6. Pooled cadence 2.0–5.0/week.
7. Each direction at least 30%.
8. No year above 30% of events.
9. Every design year cadence 1.25–6.50/week.
10. Zero direction conflicts.
11. Exact source-only ledger allowlist.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_SUPERTREND10X3_FLATBAR_VALID`. All pass gives `SCREENED_SOURCE_PASS_MQL5_DIRECT_SUPERTREND_BUILD_AUTHORIZED`, authorizing only a separately reviewed direct MQL5 formula implementation and parity/correctness work. Economics remains unauthorized.

## Authority boundary

No source access until the analyzer, tests and their hashes receive independent pre-run review and the registry grants a fresh one-attempt authority. No MQL5, MT5 tester, outcomes, validation, holdout, paper, promotion or live authority is granted.
