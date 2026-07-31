# HYP-VRAS-EURUSD-M5-014 engineering readout

## Verdict

`ENGINEERING_PASS_FEED_PLUMBING_ONLY_STOP_DATA_FRONTIER`

The collection-only confirmation mechanism is implemented and compilable. The
canonical MQL5 source passed 66 focused/operational tests, MetaEditor compile
with 0 errors / 0 warnings, exact-source non-repaint audit, zero forbidden
trade API matches and zero `FILE_COMMON` matches.

The sole preregistered 120-second read-only broker smoke passed its engineering
contract:

- exact server `FivePercentOnline-Real`;
- observed broker offset +10,800 seconds and timestamps normalized to UTC;
- 53 quote rows, 53 unique strictly increasing timestamps, zero duplicates;
- 239/239 connected heartbeats, maximum gap 684 ms;
- hash and row-count reconciliation passed;
- no future-of-manifest clock blocker;
- account history skipped, zero orders, zero positions and live authorization
  false.

The generic validation verdict remains `STOP_DATA_FRONTIER`, as preregistered.
The capture is only about two minutes and EURUSD-only; it cannot satisfy the
90-day quote window, commission/slippage samples or full QFSI symbol coverage.

## Mechanism now present in the EA

An entry candidate is armed only from completed bars: H1 EMA200 shift 1 plus a
completed-M5 VWAP48 reclaim/path break. For 30–120 seconds after the arm, the EA
observes causal bid/ask updates. It records acceptance only when all frozen
conditions agree: at least 20 quote updates, 12 price changes, directional
imbalance at least 0.60, net mid expansion at least the arm spread, current
spread no worse than the pre-arm median, max spread ratio at most 1.50, max gap
at most 15 seconds and no touch/recross of the frozen VWAP. It still sends no
orders and computes no SL/TP/PnL.

## Boundary and next legal step

This proves the collector and state machine can observe causal confirmation;
it does not prove that confirmation improves expectancy. A 2018-present OHLC
or synthetic-tick backtest would be misleading because the original ordered
bid/ask updates are unavailable. No PF, WR, expectancy, DD, stop or R:R claim
is authorized.

The next legal economic step requires a sufficiently long forward quote corpus
and independent commission/slippage evidence, then a fresh preregistered matched
pair comparing the frozen arm with versus without quote acceptance. Until that
external time/data boundary is met, no unattended collection, backtest,
optimization, order placement, promotion or live trading is authorized.
