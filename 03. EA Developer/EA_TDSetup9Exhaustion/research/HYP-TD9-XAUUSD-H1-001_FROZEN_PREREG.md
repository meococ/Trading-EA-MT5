# HYP-TD9-XAUUSD-H1-001 — Frozen Perfected Setup-9 Exhaustion Source Preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`

Informing evidence: WPR14 H1 extreme re-entry was parked only for 14.56 events/week. No TD9 event count, price outcome or economic metric informed this object.

## Identity and thesis

- Hypothesis: `HYP-TD9-XAUUSD-H1-001`
- Family: `td-setup9-strict-perfect-exhaustion-fsm`
- Symbol/timeframe: native FivePercent XAUUSD H1 Bid bars
- Source state: exact inception `2004-06-11T04:00:00Z` through `<2023`
- Design: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation 2023–2024 and holdout 2025+ remain sealed
- Sole attempt: `TD9001-SOURCE-ATTEMPT-001`

The official DeMARK 9-13 indicator on TradingView defines Setup as nine consecutive closes below/above the close four bars earlier. With default compare “without equal,” equality breaks the series. Setup perfection requires Buy Setup bar 8 or 9 low below the lows of bars 6 and 7, with the strict inverse for Sell Setup highs.

This object tests only perfected Setup-9 completion. It does not implement Countdown-13, TDST, risk levels, delayed perfection, cancellation qualifiers or any filter.

Repository de-dup found no TD Sequential/DeMARK/TD9 object in the registry or failure catalog. Run-length exhaustion is materially distinct from oscillator re-entry/crossover and compression/breakout families.

## Exact causal FSM

For each completed H1 bar `t` from index 4:

- Buy condition: `close[t] < close[t-4]`.
- Sell condition: `close[t] > close[t-4]`.
- Equality satisfies neither and resets both counts.
- A Buy condition increments the Buy count and resets Sell; Sell is symmetric.

When a count first reaches 9:

- LONG only if `min(low[bar8], low[bar9]) < min(low[bar6], low[bar7])`.
- SHORT only if `max(high[bar8], high[bar9]) > max(high[bar6], high[bar7])`.
- Here bar9 is current `t`, bar8=`t-1`, bar7=`t-2`, bar6=`t-3`.
- Failed perfection at bar9 is consumed; later bars cannot perfect that setup.
- Continuing qualifying bars are latched and cannot emit again. A condition break resets and a fresh nine-count is required.

The first possible event is index 12. Exact raw dependency for an event at `t` is `t-12..t`. Normal market closures do not synthesize bars or reset the bar-count FSM. Every inception row must have finite `high>=low` and `low<=close<=high`; flat bars are valid but equality comparison still breaks a count.

## Execution mapping

- decision only at exact next physical H1 row, both `source_epoch+3600` and UTC `+1 hour`;
- a raw gap event is consumed, never delayed;
- decision time is `t+1 hour`;
- next price is never read.

Forbidden: Countdown-13, TDST, risk levels, delayed perfection, equality-allowed setup, alternate count/lookback, M15 sibling/tournament, session/news/ATR/ADX/volume/trend filters, cooldown/debounce, stops/targets, outcomes and optimization.

## Frozen source and gates

- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- XAUUSD H1 SHA256: `B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3`
- PyArrow materializes only `time_utc<2023`; scoring uses `[2018,2023)`.

All gates must pass: hashes/one-shot/replay; design rows >=25,000; feature coverage >=99%; exact-next >=97%; executable N>=500; cadence 2–5/week; each direction >=30%; max year <=30%; every year 1.25–6.50/week; zero conflicts; exact outcome-blind ledger.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_TD9_PERFECTED_SETUP`. All pass gives `SCREENED_SOURCE_PASS_DIRECT_MQL5_PARITY_CHILD_AUTHORIZED`, permitting only a fresh direct-formula MQL5 correctness child.

No source access may occur before preregistration, analyzer, tests and independent review are registry-bound. No MT5, MQL5, economics, validation, holdout, paper, promotion or live authority is granted.

Reference: https://www.tradingview.com/script/gVMuxasg-DeMARK-9-13/
