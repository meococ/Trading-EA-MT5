# HYP-MZMS-MACD-HIST-SLOPE-EURUSD-M5-004 - Frozen Owner-Directed Full-History Diagnostic

Status: PRE-SOURCE-IDENTITY / PRE-MODEL0-OUTCOME

Frozen at: 2026-07-21T09:38:31Z

## Purpose and authority

The Owner explicitly requested a EURUSD M5 backtest from 2018 through the
current date after V3 had already reached `KILL_AT_FROZEN_OFFLINE_PROBE`.
This is therefore a descriptive diagnostic replay, not an unbiased successor
hypothesis and not a post-hoc rescue. Its result cannot reverse V3, authorize
optimization, promotion, paper trading or live trading.

Run exactly one matched pair through AlphaFactory Model 0:

1. `CONTROL` with `InpSignalMode=0`.
2. `MZMS_CHALLENGER` with `InpSignalMode=1`.

No third run, threshold change, subgroup veto, BE arm, intrabar arm or rerun is
authorized by this preregistration.

## Frozen identity and window

- EA: `EA_MZMS_Scalper`
- Hypothesis: `HYP-MZMS-MACD-HIST-SLOPE-EURUSD-M5-004`
- Broker/test lane: FivePercent portable MT5 on D:
- Symbol/timeframe: `EURUSD`, `M5`
- Model: `0` (real ticks based on real ticks)
- Window: `2018.01.01` through `2026.07.21`
- Deposit/leverage: USD 10,000 / 1:100
- Spread: Model-0 current/historical tick spread
- Commission and slippage provenance: unverified; diagnostic only

## Frozen data-availability deviation

The embedded high-impact EUR/USD calendar covers only 2019--2022 and the EA
fails closed outside that range. Leaving it enabled would create a misleading
2018--YTD shell with no eligible entries outside 2019--2022. Freeze
`InpRequireNewsGuard=false` for the entire matched pair. This is a deliberate,
uniform data-availability variant and must not be presented as the V3 result.

## Frozen strategy contract

All signal, risk and management rules remain unchanged from V3:

- 100% closed-bar decisions; no intrabar evaluation.
- MACD 12/26/9 histogram local extremum on shifts 1/2/3.
- Minimum normalized histogram delta `0.01 * ATR(14)`.
- EMA200 bias, RSI14 42--58 and directional, ADX14 >=18.
- Five-M5-bar cooldown and one owned position maximum.
- 08:00 inclusive to 17:00 exclusive UTC with FivePercent EU-DST conversion.
- Entry spread finite, strictly positive and <=0.8 pip.
- Farther of five-bar structural stop +/-0.5 pip and 1.5 ATR.
- Target 1.6R; maximum hold 15 M5 bars; hard flatten 18:15 UTC.
- Break-even: OFF. The replay does not evaluate an ON arm.
- Risk 0.01% of current equity, max five trades per UTC day, 1.5% daily loss
  guard and 8% account drawdown guard.

## Readout contract

Report report-native net profit, PF, trade count, win rate, average trade,
absolute/relative drawdown, elapsed-calendar-week cadence, long/short counts,
exit reconciliation, modeled date coverage, history quality and log errors.
Compare the challenger with the matched control and disclose that the news
guard is disabled and cost provenance is not promotion-grade.

For context only, score the inherited V3 diagnostic thresholds: PF >=1.35,
expectancy >=0.18R, cadence 2--5 trades per elapsed week and max DD <=6%.
Passing any or all thresholds does not reopen V3 because this replay was
requested after the V3 outcome was known and changes the news contract.

Terminal outcome for this ID is `DIAGNOSTIC_COMPLETE_NO_PROMOTION` if the run
is technically valid, or `INVALID_ENGINEERING_RUN` if identity, sidecars,
history, logs or report reconciliation fail.
