# HYP-TFCVD-XAUUSD-M5-001 — frozen source/cadence probe

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY` on 2026-08-09. No future price,
return, trade or PnL of this object has been read.

## 1. Identity and thesis

- EA: `EA_TickFlowCVDProbe`; symbol/timeframe: broker-native `XAUUSD` M5.
- Data engine: MT5 Strategy Tester Model 4 (real ticks), FivePercentOnline-Real.
- Source window: 2018-01-01 through 2022-12-31.
- Validation 2023-01-01 through 2024-12-31 and holdout 2025-01-01 onward are
  sealed and may not be opened by this hypothesis.
- TradingView documents Volume Delta as the signed accumulation of intrabar
  activity, using intrabar price direction and carrying prior polarity when an
  intrabar is unchanged: https://www.tradingview.com/support/solutions/43000725057-volume-delta/
- MQL5 exposes chronological tick history and Bid/Ask/Last/volume change flags:
  https://www.mql5.com/en/docs/series/copyticks
- Microstructure motivation is adverse-prior only: Cont, Kukanov and Stoikov
  find order-flow imbalance more robustly related to contemporaneous price
  change than raw trade volume (https://arxiv.org/abs/1011.6402). This does not
  establish profitable persistence or reversal on an XAUUSD CFD feed.

## 2. Exact object

The probe measures quote-tick delta, not true exchange CVD. For each unique
Bid/Ask update, mid-price upticks add one, downticks subtract one, and an
unchanged mid inherits the latest non-zero polarity. Exact duplicate Bid/Ask
coordinates do not enter delta. Invalid, non-positive or crossed quotes are
counted and rejected. Trade/BUY/SELL/volume flags are diagnostics and never
replace the primary unit weight.

One row is emitted only when a later M5 bar begins. Thus all row fields are
known by that completed bar's close; a future economic child may enter no
earlier than the next M5 open.

The one frozen source event is an absorption candidate when all conditions hold:

1. unique quote updates and classified updates are each at least 20;
2. `abs(quote_tick_delta / classified_updates) >= 0.35`;
3. mid-price close efficiency `abs(close-open)/(high-low) <= 0.20`;
4. signed delta multiplied by close-minus-open is non-positive.

Candidate direction is opposite the quote-tick delta. There is no threshold
grid, session filter, direction filter, parameter optimization or outcome label.

## 3. De-dup and adverse priors

- This is materially distinct from AIRD/VRC/MBB/QQE/TB and the closed
  price/indicator-fusion frontier because it consumes the intrabar tick path,
  not only closed-bar OHLC/indicator states.
- It is distinct from HYP-EURFXOFI-016: that object used classified CME 6E TBBO
  flow during a fixed final-15-second EURUSD event window; this object uses
  continuous broker quote updates on XAUUSD M5 and conditions on low realized
  price impact.
- It is not a renamed VRAS quote-acceptance arm: there is no EMA/VWAP/session
  setup and no 30-120 second post-arm acceptance funnel.
- Strong adverse prior: quote ticks are not trades, activity can be broker- and
  latency-specific, contemporaneous delta may have no next-bar forecast, and
  spread/slippage can consume any short-horizon edge.

## 4. Simultaneous source gates

All gates must pass; an almost-pass is a KILL for this exact mapping:

1. report History Quality strictly greater than 97%; exact Model 4 identity;
2. zero orders, deals, position mutations and trading API calls;
3. telemetry timestamps strictly increase by M5 bar and every row is marked
   completed before a later bar is processed;
4. at least 95% of emitted bars have 20 or more unique valid quote updates;
5. invalid quote share is at most 0.10%;
6. at least 500 absorption candidates across the five-year source window;
7. candidate cadence is between 2.0 and 8.0 per elapsed calendar week (source
   slack for a later 2-5 executed-trades/week contract);
8. each candidate direction has at least 30% share;
9. no single calendar year contains more than 30% of candidates;
10. telemetry contains no future-return, MFE/MAE, trade, PnL, PF, balance,
    equity, stop-hit or target-hit field.

PASS means only `PASS_SOURCE_FEASIBILITY_MAY_DRAFT_ECONOMIC_CHILD`. Failure
means `KILL_SOURCE_FEASIBILITY_EXACT_TICK_DELTA_MAPPING`; it does not close the
goal or every intrabar-flow mechanism.

## 5. Economics and deployment remain sealed

This hypothesis has zero economic trials and cannot compute PF, expectancy,
drawdown, DSR, cost stress, WFA, OOS, Monte Carlo or chart outcome forensics.
No `.set` file, trading EA, optimization, validation, holdout, paper/live or
deployment authority follows unless all source gates pass and a fresh child ID
freezes entry, exit, risk, costs and splits before reading any next-bar outcome.
