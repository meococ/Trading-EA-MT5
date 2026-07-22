# HYP-MZMS-MACD-HIST-SLOPE-EURUSD-M5-005 - Frozen Model-0 Instrumentation Replacement

Status: PRE-SOURCE-IDENTITY / PRE-MODEL0-OUTCOME

Frozen at: 2026-07-21T09:47:30Z

## Replacement boundary

HYP-004 attempted the Owner-directed 2018--YTD matched-pair diagnostic, but the
control stopped after 125 M5 bars and one trade. The FivePercent tester raised
a money-mode stop-out immediately after the first 0.01-lot position under a
USD 10,000 test deposit. Its report covers only 2018-01-01 to 2018-01-02 despite
the requested 2018--2026 window. Its one-trade economics are invalid and must
not select, kill, rescue or tune the strategy.

HYP-005 changes only identity, the test deposit to USD 100,000 (the established
FivePercent diagnostic lane level), and receipt authority completeness. Signal,
risk percentage, time window, execution model and all strategy rules remain
unchanged. If full coverage still fails, stop invalid rather than changing the
deposit again.

## Purpose and authority

The Owner explicitly requested a EURUSD M5 backtest from 2018 through the
current date after V3 had already reached `KILL_AT_FROZEN_OFFLINE_PROBE`.
This remains a descriptive diagnostic replay, not an unbiased successor or a
post-hoc rescue. It cannot reverse V3 or authorize optimization, promotion,
paper trading or live trading.

Run exactly one matched AlphaFactory Model-0 pair: `CONTROL` with
`InpSignalMode=0`, then `MZMS_CHALLENGER` with `InpSignalMode=1`. No third run,
threshold change, subgroup veto, BE arm, intrabar arm or rerun is authorized.

## Frozen identity and window

- EA/hypothesis: `EA_MZMS_Scalper` / `HYP-MZMS-MACD-HIST-SLOPE-EURUSD-M5-005`
- Broker/test lane: FivePercent portable MT5 on D:
- Symbol/timeframe/model: `EURUSD`, `M5`, Model `0`
- Window: `2018.01.01` through `2026.07.21`
- Deposit/leverage: USD 100,000 / 1:100
- Spread: Model-0 current/historical tick spread
- Commission and slippage provenance: unverified; diagnostic only

## Frozen data-availability deviation

The embedded high-impact EUR/USD calendar covers only 2019--2022 and the EA
fails closed outside that range. Freeze `InpRequireNewsGuard=false` uniformly
for the entire pair. This data-availability variant is not the V3 result.

## Frozen strategy contract

- 100% closed-bar decisions; no intrabar evaluation.
- MACD 12/26/9 histogram local extremum on shifts 1/2/3.
- Minimum normalized histogram delta `0.01 * ATR(14)`.
- EMA200 bias, RSI14 42--58 and directional, ADX14 >=18.
- Five-M5-bar cooldown and one owned position maximum.
- 08:00--17:00 UTC with FivePercent EU-DST conversion.
- Entry spread finite, strictly positive and <=0.8 pip.
- Farther of five-bar structural stop +/-0.5 pip and 1.5 ATR.
- Target 1.6R; max hold 15 M5 bars; hard flatten 18:15 UTC.
- Break-even: OFF. The replay does not evaluate an ON arm.
- Risk 0.01% of equity, max five trades/UTC day, 1.5% daily loss guard and 8%
  account drawdown guard.

## Validity and readout contract

The report must cover the requested start/end, materially exceed 125 bars,
show 99% history quality, exact source/EX5/config/report hashes, one RunMeta,
one LifecycleTrades file, no stop-out/error and terminal shutdown.

Report net profit, PF, trades, win rate, average trade, drawdown,
elapsed-calendar-week cadence, directions and year buckets. Compare challenger
with control and disclose the news/cost limitations. Inherited V3 thresholds
are context only and cannot reopen V3.

Terminal outcome is `DIAGNOSTIC_COMPLETE_NO_PROMOTION` if technically valid,
or `INVALID_ENGINEERING_RUN` if coverage, identity, sidecars, logs or report
reconciliation fail.
