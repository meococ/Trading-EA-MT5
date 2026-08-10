# HYP-STBS-XAUUSD-M15-001 — frozen engineering preregistration

Status: `FROZEN_PRE_MT5_REVISION_3_NO_OUTCOME`

Parent evidence: `HYP-ST-XAUUSD-H1-012`, whose only claim is exact direct
MQL5/MT5 parity for standard Supertrend 10×3. Parent outcomes are zero.

## Falsifiable market thesis

A confirmed H1 Supertrend state flip identifies a volatility-adjusted regime
transition. If that transition has useful short-horizon information on
XAUUSD, the first two hours after the confirmation should exhibit enough
same-direction continuation to overcome current spread, broker commission and
a conservative one-second execution degradation. The H1 indicator is the
event clock; M15 ATR is only the local risk unit. There is no indicator vote,
session-selection search or post-result filter.

This is materially different from the parent H1 flip-and-trail object. It is a
fresh M15 burst/scalp mapping with a fixed target and fixed time exit.

## Frozen signal and state

- Symbol / execution timeframe: `XAUUSD` / native `M15`.
- State timeframe: native `H1`.
- H1 Supertrend: exact parent formula, ATR period `10`, factor `3.0`, direct
  chronological implementation, initial state `DOWN`, no `iSuperTrend`, no
  rounding and no reset across normal market closures.
- State is rebuilt from the earliest frozen H1 history available to the parent
  (`2004-06-11 07:00` server time) and then advanced on completed H1 bars only.
- Raw event: `DOWN→UP` or `UP→DOWN` on completed H1 bar `t`.
- Executable event: the next native H1 open exists exactly at `t+3600` and is
  also an exact native M15 open. A gap consumes the event; it is never queued.
- Entry: at the first tick of the exact next open, market LONG for `UP` and
  SHORT for `DOWN`.
- One position only; no pyramid, scale-in or same-state re-entry. A stopped or
  timed-out trade cannot re-enter until a fresh H1 flip.
- If a fresh opposite flip arrives while a position remains open, close it and
  require confirmed flat state before submitting the reverse entry. A failed
  close consumes that flip and cannot create a second position.

## Frozen M15 risk and exit mapping

- Risk unit: MT5 native `iATR(XAUUSD, M15, 14)` value on the last completed M15
  bar at the decision time. Missing, nonfinite or nonpositive ATR fails closed.
- Initial stop distance: `1.00 × ATR14_M15` from the requested market entry.
- Take profit: `1.50R` from the same requested entry and stop distance.
- Stop is normalized outward to `SYMBOL_TRADE_TICK_SIZE`; target is normalized
  away from entry. No epsilon, digits-only rounding or stop widening.
- Wrong-side price, stops/freeze-level violation, invalid tick geometry,
  unavailable quote, margin rejection or volume below broker minimum consumes
  the signal once. There is no retry on a later tick or bar.
- Time exit: close at the first tick of the ninth M15 bar open after entry,
  i.e. after eight complete M15 holding bars (`120` minutes maximum under
  contiguous bars). Missing bars do not synthesize time or signals.
- Broker SL/TP may exit intrabar. No break-even, partial close or trailing stop
  exists in this first baseline.

## Frozen sizing and operational risk

- Risk per accepted entry: `0.25%` of current equity.
- Use `OrderCalcProfit` for a one-lot entry-to-stop loss, then floor to symbol
  volume step and enforce min/max. Never round volume upward.
- One symbol/magic position; asynchronous mode disabled; filling mode comes
  from symbol settings; every successful call also requires a successful
  trade retcode.
- Daily loss lock: no new entry after realized+floating equity drawdown reaches
  `1.50%` from UTC day-start equity.
- Account lock: no new entry after equity drawdown reaches `8.00%` from the
  running peak; the EA may only reduce/close risk after a lock.
- No weekend hold: reject Saturday/Sunday entries; on Friday reject decisions
  at or after `18:00 UTC` and force-flat at or after `20:00 UTC`.
- FivePercent clock: winter UTC+2; Europe DST through 2023, US DST from 2024,
  using the already project-tested deterministic clock conversion.

## Engineering stage authorized by this ID

HYP001 may only:

1. implement the causal engineering ancestor used by the audit; any economic
   child must receive a new ID/source guard and separately harden restart-safe
   persistent risk anchors before it may trade;
2. run unit/static contracts, compile 0 errors/0 warnings and non-repaint audit;
3. run one no-trade audit-only MT5 correctness check that reconciles H1 signal
   identity to the sealed parent events and tests M15 ATR/geometry readiness;
4. inspect tester journal, source-only telemetry and visual correctness cases.

Orders, performance metrics, PnL, PF, returns, optimization, validation,
holdout, paper and live execution are forbidden under HYP001. A separately
reviewed child is required before a trading baseline.

The sole correctness invocation is frozen to AlphaFactory `control`, native
`XAUUSD`/`M15`, `2005.01.01` through `2023.01.01`, Model `0`, execution mode
`0`, fixed delay `0`, telemetry profile/tier `none`/`off`, current spread and
`10,000` deposit at `1:100`. `InpAuditOnly=true` and
the source-default/guarded `InpEnableTelemetry=false` are mandatory; the
Alpha override string contains only `InpAuditOnly=true`. The 2005 start is a
prehistory preload contract, while signals remain emitted/scored only inside
DESIGN 2018–2022. Evidence is tester report, run-local
journal and manifest only; no lifecycle sidecar is claimed. PASS requires
parent counts raw/executable/gap/LONG/SHORT = `690/683/7/339/344`, exact event
epoch/direction equality to the sealed parent oracle, ATR-ready on every
executable current-decision event, quote/tick/SL/TP/volume/margin geometry-ready
on every executable current-decision event, zero fatal lines and zero
order/deal/trade. Historical backlog ATR is resolved from the exact decision
M15 bar and its exact immediately preceding M15 bar; it never borrows the
current bar's ATR.

The run must also emit exactly one valid `DATA_EPOCH_D0_SERIES_PROOF` record
for broker-native M5/M1 availability. Its single `CopyTime` call is provenance
only, executes during OnInit, never supplies a decision field and is frozen as
an explicit non-decision allowance in the non-repaint manifest.

## Future split and cost boundary (declared, not opened here)

- DESIGN/TRAIN: `2018-01-01` through `2022-12-31`.
- Validation: `2023-01-01` through `2024-12-31`, sealed.
- Final holdout/forward proxy: `2025-01-01` onward, sealed.
- Historical research cost evidence for any later TRAIN falsification must bind
  FivePercent XAUUSD M1 bid/ask spread coverage, maximum tester commission
  `4.40 USD/lot round turn`, and the existing independent-quote `1000 ms` P90
  adverse proxy of `80 XAU pips round turn` at x1/x1.5/x2.
- That proxy has `fill_observed=false`; therefore even a passing historical
  child remains non-promotable until observed same-broker commission and
  slippage fills exist. Zero slippage is missing evidence, never zero cost.

Before optimization or validation, the future frozen TRAIN child must pass all
of: PF `>1.30` after x1 cost, expectancy `>0`, cadence `2–5` executed
trades/elapsed week, x1.5 PF `>=1.25`, x2 PF `>=1.00`, max DD `<=8%`, both
directions represented, no single year over `30%` of trades, and stable yearly
economics. Failure closes only that exact economic mapping and does not close
the workspace goal.

## Engineering kill conditions

Kill or revise before economics if any of the following occurs: parent signal
identity mismatch; lookahead/repaint; state reset at DESIGN; entry on a gap;
non-closed-bar ATR; duplicate/same-state entry; unconfirmed reverse; upward
volume rounding; widened stop; weekend hold; source/audit/backtest logic drift;
compile warning/error; unreconciled signal→request→order→deal→position/exit.

Official formula provenance only (not acceptance evidence):

- https://www.tradingview.com/support/solutions/43000634738-supertrend/
- https://www.tradingview.com/support/solutions/43000501823-average-true-range-atr/
