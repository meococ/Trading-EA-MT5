# HYP-MIRB-EURUSD-M15-001 — source result

Verdict: `PARK_DUPLICATE_SOURCE_FEASIBILITY_ROWS_COVERAGE_AND_CADENCE_FAIL`.

The sole outcome-blind attempt `MIRB001-SOURCE-001` completed and sealed a
report, event ledger, receipt and terminal. It read only broker-native
FivePercent EURUSD M5 bars, aggregated complete triplets to M15, and did not
read outcomes, simulate trades, calculate PF or use paid data.

Post-source review found that the prereg de-dup claim was false:
`HYP-MASS-EURUSD-M15-001` already tested the same 9/9/25 Mass Index bulge and
parked at `5.07346/week`. MIRB changed seed/source-window details and direction
labels but did not create a materially new event-timing family. This is a
process failure and an additional reason to close the lane.

## Result

- M15 source rows: `198,837`; design rows: `174,061`.
- Feature-usable rows: `165,879`; coverage `95.29935%` — FAIL versus 99%.
- Raw/executable events: `1,851 / 1,850`; exact-next `99.94598%`.
- LONG/SHORT: `944 / 906`.
- Pooled cadence: `5.064529/week` — FAIL versus the frozen 2–5 range.
- Annual cadence: `4.73699–5.36986/week`; all annual gates pass.
- Direction balance and year concentration pass.
- Frozen minimum design-row floor `190,000` also fails. That floor was not
  calendar-derived and was unnecessarily high for the seven-year interval;
  this is a prereg design mistake. It is not used as the substantive reason to
  reject the market mechanism because feature coverage and pooled cadence fail
  independently.

Ledger-only reconciliation found 1,850 unique source epochs, exact +15-minute
decision timestamps, strict `MassIndex < 26.5` completion, and exact EMA-slope
direction mapping with zero violations.

## Failure radius

Park only the exact classic Mass Index 9/9/25 bulge (`>27`, then `<26.5`) with
EMA9-close slope reversal direction on EURUSD M15, 2016–2022. Do not lower the
bulge threshold, alter EMA/rolling periods, add cooldown/session/debounce, or
change direction logic under this ID. No economic or all-Mass-Index conclusion
exists; MQL5, baseline, optimization, validation and holdout remain unopened.

No Mass Index successor is authorized. Future de-dup must search full EA package
paths, hypothesis aliases and formula/timing signatures rather than display
names only.

## Evidence hashes

- Source report: `8D4AE3B3BDA5D62AC22E56D7D76BEFFD2C9590C7E6116468F8E113B113529FF9`.
- Event ledger: `EEECFD6700A45984BC8F8D3F6220F05C441587BF76E133C9D52CC03171F5BF65`.
- Receipt: `E7EFE4C962EB62349A39F18DE1A8438DD4687B4A16AEEA554DFF54E1633DC148`.
- Terminal: `8A23FCE8E7E7790132CF998D59E099BAAC074888EDC71490F507DB87FC21E3F8`.

