# HYP-WTX-EURUSD-H1-001 — Pre-source PARK

Verdict: `PARK_PRE_SOURCE_GOAL_AND_INFORMATION_FAMILY_DEDUP`

- No Parquet row was opened and `WTX001-SOURCE-001` was never claimed.
- No signal count, post-event price, MQL5 build, MT5 run, trade, cost, PF,
  expectancy, validation or holdout value exists.
- The proposed WaveTrend `10/21/4` extreme cross is another single-oscillator
  extreme-transition screen. The recent CCI/DeMarker/UO/FRAMA/Connors/MFI class
  already supplies a strong adverse family prior; a different formula name is
  not a materially new information set.
- The proposed H1-only decision/entry clock also violates the active M5/M15
  deliverable and the workflow contract-equivalence gate.
- Static review additionally found that exact-next used server time rather than
  reconciling UTC/DST, positive-price validation was incomplete, and a start
  write failure could leave an unterminalized attempt root. These defects did
  not consume evidence authority because execution never began.
- Do not rescue by changing WaveTrend periods, thresholds, seed, symbol,
  timeframe, session, direction or cooldown. The next lane must use a materially
  different M5/M15 information set.

Process correction: run information-family de-dup and M5/M15 goal-fit before
writing a new analyzer. Reuse a validated source harness instead of recreating
clock, geometry and failure-terminal plumbing for each candidate.
