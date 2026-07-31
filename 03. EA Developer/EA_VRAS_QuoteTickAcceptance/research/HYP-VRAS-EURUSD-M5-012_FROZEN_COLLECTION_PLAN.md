# HYP-VRAS-EURUSD-M5-012 — Frozen Quote-Tick Acceptance Collection Plan

## 1. Research identity and boundary

- Hypothesis ID: `HYP-VRAS-EURUSD-M5-012`.
- Package: `EA_VRAS_QuoteTickAcceptance`.
- Symbol/timeframe: EURUSD M5 with closed H1 bias.
- Parent evidence: HYP-008 is terminal negative and supplies only the causal arm
  event definition. Its PnL, losing buckets, exits, stop/target geometry and
  chart outcomes are forbidden inputs to this collection lane.
- Materially new information contract: chronological bid/ask quote ticks after
  a closed-bar arm event. This is not an OHLC next-bar or first-passage sibling.
- Stage: forward collection and engineering verification only.
- No economic backtest, PnL, SL, TP, position sizing, order request, live trade,
  promotion or threshold tuning is authorized by this plan.
- Historical 2018-present OHLC/Model-0 results cannot validate this mechanism.
  Tester-generated ticks may be used only for deterministic engineering smoke,
  explicitly labelled `SYNTHETIC_TESTER_TICKS`.

## 2. Frozen causal arm event

Evaluate only once per newly opened M5 bar using completed bars:

1. H1 close and H1 EMA200 use shift 1.
2. Rolling VWAP48 uses completed M5 shifts 1..48, typical price
   `(high+low+close)/3`, weighted by tick volume; zero-volume rows are skipped.
3. Long arm: closed H1 close > H1 EMA200; M5 shift-1 low <= VWAP; shift-1
   close > VWAP; shift-1 close > shift-2 high.
4. Short arm is the exact mirror.
5. The first valid quote after the closed-bar arm freezes direction, VWAP,
   arm bid/ask/mid/spread and `arm_time_msc`.
6. At most one active arm exists. A new arm cannot overwrite an active arm.

The arm is an observation trigger, not evidence that HYP-008 has edge.

## 3. Frozen quote-tick acceptance state machine

Maintain a pre-arm ring of the latest 60 unique chronological quote spreads.
An arm is fail-closed if fewer than 30 valid pre-arm quotes exist.

For every unique tick after the arm:

- valid quote: `time_msc` strictly increases, bid/ask are finite and positive,
  and ask >= bid;
- mid = `(bid+ask)/2`;
- quote update count includes every valid unique tick;
- price-change count excludes unchanged mid quotes;
- directional move count is an uptick for long / downtick for short;
- opposite move count is the mirror;
- imbalance = directional moves / (directional + opposite moves);
- directional net expansion = direction * (current mid - arm mid);
- maximum interquote gap and maximum spread/pre-arm-median ratio are tracked.

An arm becomes `ACCEPTED_OBSERVATION` only on a tick aged 30,000 through
120,000 ms inclusive when all gates hold simultaneously:

1. at least 20 valid quote updates;
2. at least 12 price-changing quotes;
3. directional imbalance >= 0.60;
4. directional net expansion >= the frozen arm spread;
5. current spread <= the pre-arm median spread;
6. maximum spread since arm <= 1.50 times the pre-arm median spread;
7. maximum interquote gap since arm <= 15,000 ms;
8. long bid remains strictly above frozen VWAP / short ask remains strictly
   below frozen VWAP (a touch or recross rejects immediately).

Terminal states are immutable per arm:

- `ACCEPTED_OBSERVATION`: all eight gates pass inside the age window;
- `REJECT_VWAP_RECROSS`: quote touches/crosses frozen VWAP;
- `REJECT_SPREAD_SPIKE`: spread exceeds 1.50 times pre-arm median;
- `REJECT_STALE_GAP`: interquote gap exceeds 15,000 ms;
- `REJECT_INVALID_QUOTE`: non-monotonic or invalid bid/ask input;
- `EXPIRE_NO_ACCEPTANCE`: age exceeds 120,000 ms without acceptance;
- `DEINIT_ACTIVE_ARM`: EA stops while an arm remains active.

The 60/30 quote history, 30–120 second window, 0.60 imbalance, one-arm-spread
expansion, 1.50 spread spike and 15-second stale limits are frozen before any
HYP-012 forward outcome or PnL exists. The old 2026-07-15 QFSI corpus may be
used only to verify schema/parser behavior and realistic quote cadence; it may
not be scored for HYP-012 trade outcomes.

## 4. Telemetry contract

The EA writes one CSV under the terminal-local MQL5 Files area (never
`FILE_COMMON`) with a run-unique name. Required columns:

`schema_version,hypothesis_id,run_id,event_time_msc,event_time_utc,symbol,` +
`event,direction,arm_bar_time,arm_time_msc,age_ms,bid,ask,mid,spread_points,` +
`prearm_median_spread_points,quote_updates,price_changes,directional_moves,` +
`opposite_moves,imbalance,directional_net_points,max_gap_ms,` +
`max_spread_ratio,frozen_vwap,data_source,promotion_eligible`

Required events: `ARMED`, zero or more `OBSERVE`, and exactly one terminal
event for every completed arm. `data_source` must be `LIVE_QUOTES` outside the
tester and `SYNTHETIC_TESTER_TICKS` in Strategy Tester.
`promotion_eligible` is always `false`.

## 5. Fail-closed implementation rules

- The source must not contain trade request structures, `OrderSend`,
  `OrderCheck`, CTrade buy/sell methods, position mutation, SL or TP logic.
- `OnTradeTransaction` is unnecessary and must not be implemented.
- Only shift-1-or-older M5/H1 bars may create an arm; quote evidence after the
  arm is causal `OnTick` data.
- `FILE_COMMON` is forbidden.
- Input identity is fail-closed: exact hypothesis ID, EURUSD chart, M5 chart,
  200/48/60/30/120000/20/12/0.60/1.50/15000 defaults and collection-only mode.
- Invalid handles, insufficient bars, insufficient pre-arm quotes, file-open
  failure or invalid quote data cannot produce acceptance.
- No optimizer surface is authorized; mechanism inputs are not optimizable.

## 6. Acceptance gates for this implementation session

1. Contract tests cover exact identity, closed-bar shifts, mirrored signal,
   all eight acceptance gates, all terminal states, immutable terminal state,
   pre-arm median, chronological deduplication and forbidden trade APIs.
2. MetaEditor compile: 0 errors / 0 warnings from the canonical active source.
3. Exact-source non-repaint audit passes; causal `OnTick` use is documented as
   post-arm evidence, not a closed-bar violation.
4. AlphaFactory package contract resolves the canonical active source with
   telemetry profile `none`.
5. One bounded read-only forward smoke may run only if broker identity is
   `FivePercentOnline-Real`, the terminal is connected, zero-order static audit
   passes and output stays on D:. Duration <= 180 seconds, EURUSD only, no cron.
6. Smoke success is engineering-only: valid manifest/CSV, monotonic unique
   `time_msc`, finite bid/ask with ask >= bid, exact row count/hash, and safety
   receipt `orders_sent=0`, `positions_opened=0`,
   `live_trading_authorized=false`.
7. Lack of an arm during a short smoke is not an economic failure; it requires
   a longer explicitly authorized collection window, not relaxed thresholds.

## 7. Decision after collection

- No PnL may be joined until a later, fresh, outcome-bound preregistration
  freezes sample size, purge/embargo, control, costs and decision thresholds.
- Any proposed threshold change after reading HYP-012 acceptance/outcome data
  belongs to a new hypothesis; HYP-012 cannot be rescued or tuned in place.
- A future economic challenger must compare the same base arms with and without
  acceptance on the same causal quote feed and must retain the unblocked-DD
  diagnostic requirement requested by the Owner.
