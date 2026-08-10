# HYP-ERAY-EURUSD-H1-001 Source Result

Verdict: `PARK_SOURCE_FEASIBILITY_EXACT_ERAY_EMA13_DOMINANCE`

The sole outcome-blind EURUSD H1 source scan completed. The exact Elder-Ray EMA13 full-bar dominance transition is causal, deterministic, balanced by direction and well covered, but it is structurally too frequent for the frozen 2-5 events/week envelope.

## Reconciled result

- Design rows: 31,094
- Raw events: 4,022
- Executable events: 4,002
- Exact-next coverage: 99.5027%
- LONG / SHORT: 2,030 / 1,972
- Pooled cadence: 15.3417/week
- Annual cadence: 14.8247-15.8411/week
- Maximum decision-year share: 20.6397%

Passed: row count, feature coverage, exact-next coverage, event count, direction balance, year concentration, zero conflict and deterministic replay.

Failed: pooled cadence and every decision-year cadence.

## Evidence

- Report SHA256: `66F07EEFF5591FAD5B57146637DF4AFEC65185C60C32E67E5228744275465101`
- Ledger SHA256: `F93837195368A71EB2704909C9ED82726E278223299D31E092317A4D4E86CB4F`
- Receipt SHA256: `6A907D65F36E824F13A720A1E66375E8A6B7039D30C09EC36BBBCF44EBA6DE4F`
- Terminal SHA256: `CA9B5C62E18F552707274F5715DD636746243C7C9F53B563827D8EDF7282CAEA`

No next-row OHLC, returns, trades, PF, costs, MT5, MQL5, validation or holdout were opened. This is not an economic no-edge result.

## Failure radius

Only the exact EMA13 Bull/Bear Power full-bar dominance transition on native EURUSD H1 for 2018-2022 is parked. Do not rescue it with a session, cooldown, debounce, persistence count, EMA change, threshold, direction filter or timeframe change under the same hypothesis.
