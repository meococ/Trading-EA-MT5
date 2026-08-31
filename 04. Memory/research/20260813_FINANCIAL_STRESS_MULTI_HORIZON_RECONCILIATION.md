# Financial-stress multi-horizon reconciliation — 2026-08-13

## Scope and evidence boundary

- Source-only, outcome-blind screen after the H4/D1 multi-horizon reset.
- No target return, PF, threshold, fitted inversion, payload download, purchase,
  code, compile, MT5 run or backtest was opened.
- Grok Build was a bounded source researcher. Lead checked the decision against
  official source behavior and the prior local NFCI screen before verdict.
- Acceptance required one exact official 2018-latest object with an identical
  live surface, first-public clock, PIT replay, mechanically frozen direction
  to one allowed pair, a documented Friday-flat-compatible horizon, adequate
  independent releases, lawful free internal use and source-family novelty.

## A — OFR Financial Stress Index

- Official surface: https://www.financialresearch.gov/financial-stress-index/
- The daily index is a market-based snapshot built from 33 variables and is
  published with data current through two business days earlier. Positive
  values mean stress above the historical average; that is not a defined
  EURUSD, GBPUSD, USDJPY or XAUUSD trade direction.
- The public contract does not provide a complete first-public vintage tape or
  a single HH:MM/time-zone publication clock for replay. OFR has revised past
  values when inputs/methodology changed.
- The object contains source-market credit, equity, funding, safe-asset,
  currency and commodity-volatility information, including gold/USD and broad
  USD inputs. It is therefore a target-leaking market/risk composite rather
  than a materially independent causal object.
- First fatal gate: no mechanically source-defined pair direction; composition
  leakage and missing first-public replay independently fail closed.

## B — New York Fed Corporate Bond Market Distress Index

- Official surface: https://www.newyorkfed.org/research/policy/cmdi
- Regular publication began on 2022-06-29 and is monthly, at or shortly after
  10:00 ET on the last Wednesday. Earlier historical values are not a chain of
  contemporaneous 2018-live first publications.
- The index measures U.S. corporate-bond market functioning. Its methodology
  does not freeze a direction to any allowed FX pair or XAUUSD, nor a causal
  H4/D1 holding window ending Friday.
- First fatal gate: no methodology-defined target direction. Missing 2018-live
  publication identity and the slow monthly horizon are independent failures.

## C — Chicago Fed NFCI / ANFCI

- Official surface: https://www.chicagofed.org/research/data/nfci/current-data
- ALFRED vintage surface: https://alfred.stlouisfed.org/series?seid=NFCI
- Weekly release is Wednesday 08:30 ET (Thursday after a Wednesday holiday),
  covering the prior Friday. Positive values mean tighter-than-average
  financial conditions. The full history is re-estimated as data, revisions
  and weights change.
- Correction to the prior local `N4` rejection: ALFRED does preserve NFCI
  vintages, so "no vintage surface" is not a valid final blocker. The old
  default `2–5/week` cadence objection also no longer controls after the
  multi-horizon reset.
- The candidate still fails. Neither Chicago Fed nor ALFRED defines tighter
  conditions as a frozen side for an allowed pair, and Wednesday-to-Friday is
  not a documented causal holding horizon. The 105-series money/debt/equity/
  shadow-banking composite is the already screened financial-conditions/regime
  family, not a new information mechanism.
- First fatal gate: no source-defined pair direction; de-dup and horizon also
  fail independently.

## Verdict

`NO_FINANCIAL_STRESS_CANDIDATE`

This verdict is scoped to OFR FSI, NY Fed CMDI and Chicago Fed NFCI/ANFCI. It is
not a declaration that the EA goal is globally infeasible. No hypothesis ID or
registry row is created because no source object reached preregistration.
Overall goal remains `ACTIVE / UNMET`; active market mechanism remains none.
