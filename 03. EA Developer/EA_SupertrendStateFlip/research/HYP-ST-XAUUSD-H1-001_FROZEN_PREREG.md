# HYP-ST-XAUUSD-H1-001 — Frozen Supertrend 10/3 Direction-flip Source Preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`  
Informing evidence: terminal source-only Vortex H1 over-frequency; no economic result.

## Identity and thesis

- Hypothesis: `HYP-ST-XAUUSD-H1-001`
- Family: `supertrend-atr10-factor3-recursive-direction-flip`
- Symbol/timeframe: FivePercent XAUUSD native H1 Bid bars
- State initialization source: earliest manifest H1 bar `2004-06-11T04:00:00Z`
- Scored design: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation 2023–2024 and holdout 2025+ remain sealed
- Sole attempt: `ST001-SOURCE-ATTEMPT-001`

TradingView documents Supertrend as a recursive ATR-based trailing-band state machine whose direction changes when price closes across the active band. This generates regime flips rather than every oscillator recross. Repository de-dup found no prior Supertrend object.

MT5 has no official built-in Supertrend handle. A source pass authorizes only a reviewed direct MQL5 state-machine implementation. `iATR` cannot be assumed parity-compatible until its seed is proven against the frozen calculation.

## Exact ATR10

- `TR[0] = high[0]-low[0]` because no prior close exists.
- For `i>0`, `TR[i]=max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1]))`.
- ATR is unavailable until index 9.
- `ATR[9] = mean(TR[0..9])`.
- For `i>9`, `ATR[i] = (9*ATR[i-1] + TR[i])/10` (Wilder RMA).

Every source row from inception through 2022 must have finite/geometrically valid high, low and close. Any invalid row fails the attempt; state is never reset at 2018 or across normal market closures/gaps.

## Exact Supertrend update order

Factor is exactly `3.0`; source is `hl2=(high+low)/2`.

At first ATR-ready bar `i=9`:

- final upper = `hl2 + 3*ATR`;
- final lower = `hl2 - 3*ATR`;
- semantic state = `DOWN`;
- Supertrend line = final upper;
- initialization is not a flip.

For every later completed bar:

1. compute basic upper/lower from current `hl2` and ATR;
2. final upper = basic upper iff basic upper is strictly below prior final upper **or** prior close is strictly above prior final upper; otherwise retain prior upper;
3. final lower = basic lower iff basic lower is strictly above prior final lower **or** prior close is strictly below prior final lower; otherwise retain prior lower;
4. if prior Supertrend line was prior final upper, current state is `UP` only when current close is strictly above current final upper, otherwise `DOWN`;
5. if prior line was prior final lower, current state is `DOWN` only when current close is strictly below current final lower, otherwise `UP`;
6. current line is final lower in `UP`, final upper in `DOWN`.

Equality retains the current regime. State uses explicit `UP`/`DOWN` enums; no numeric TradingView sign convention is imported.

## Signal and execution mapping

- raw LONG: completed-bar state changes `DOWN -> UP` during the scored design window.
- raw SHORT: `UP -> DOWN`.
- An executable event requires the immediately following native H1 timestamp to equal source time plus one hour. A raw gap flip is consumed and not persisted. Only next timestamp is inspected.
- Decision timestamp is source bar time plus one hour.

Forbidden: alternative ATR seed/smoothing/length/factor/source, initialization at 2018, state reset at closures, additional confirmation/filter/session/cooldown, optimization and outcomes.

## Frozen source and gates

- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- native H1 data SHA256: `B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3`
- allowed materialization: all rows with `time_utc < 2023-01-01T00:00:00Z`; no lower bound, because recursive state must begin at the earliest manifest bar;
- only symbol/timeframe/source epoch/time/UTC ambiguity/high/low/close may be read;
- scoring and ledger persistence are restricted to 2018–2022.

All gates must pass:

1. hash/registry/one-shot bindings and byte-identical replay;
2. source begins at the manifest-declared first timestamp and contains at least 25,000 design rows;
3. design-state feature coverage at least 99.0%;
4. exact-next H1 coverage at least 97.0% of raw design flips;
5. at least 500 executable events;
6. pooled cadence 2.0–5.0/week;
7. each direction at least 30%;
8. no year above 30%;
9. each year cadence 1.25–6.50/week;
10. zero direction conflicts;
11. exact source-only ledger allowlist.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_SUPERTREND10X3_FLIP`. All pass gives `SCREENED_SOURCE_PASS_MQL5_DIRECT_SUPERTREND_BUILD_AUTHORIZED`, allowing only direct formula implementation/parity/correctness work. Economics remains unauthorized.

## Authority boundary

No source access until analyzer/tests/hashes receive independent review and registry authority. No MQL5, MT5 tester, outcomes, validation, holdout, paper, promotion or live authority is granted.
