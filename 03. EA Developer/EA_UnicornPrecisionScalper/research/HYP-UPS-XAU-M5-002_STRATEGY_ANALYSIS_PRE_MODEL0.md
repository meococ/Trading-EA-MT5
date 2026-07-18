# Strategy Analysis (Pre-Model 0) — HYP-UPS-XAU-M5-002

## Evidence boundary

No Strategy Tester run exists. This document analyzes the frozen report
mapping, opportunity probe and code/execution design only. It contains no net
profit, PF, drawdown, win-rate or expectancy claim.

## What the EA actually trades

The EA is a closed-bar XAUUSD M5 continuation/reversal hybrid:

1. fixed London/NY UTC window and current-spread gate;
2. closed H4 EMA20/EMA50 directional bias, with closed D1 not allowed to oppose;
3. prior-12-bar liquidity sweep that remains valid for four closed M5 bars;
4. M5 displacement at least 1.2 ATR plus a three-candle FVG;
5. overlap between that FVG and a recent opposite candle as the quantified
   breaker proxy;
6. score >=75, then first executable quote after confirmation close;
7. sweep-extreme SL + 40 points, 2.5R TP, 1R break-even and 90-minute timeout.

This is a deterministic proxy for the report's discretionary Unicorn language;
it is not proof that the proxy labels what a human ICT trader would label.

## Probe diagnostics

- Frozen 002 opportunity count: `166` over roughly `132.3` elapsed weeks,
  approximately `1.25` candidates/week before spread, sizing, risk or broker
  rejection.
- Direction: `134` long (`80.7%`) and `32` short (`19.3%`).
- Active months: `25`; median `6` candidates per active month.
- The report prior was roughly `8-20` trades/month; the workspace book gate is
  `2-5` trades/week. Candidate density already sits below both lower bounds.

The density probe passed its preregistered build gate, but it did not pass the
final book cadence gate. Actual fills can only be equal or fewer, so cadence is
the leading expected kill reason. Long-side concentration is the second risk.
Neither observation authorizes a short-side threshold change or session filter.

## Engineering strengths

- Signal decisions use `CopyRates(..., 1, ...)`; only the new-bar gate uses
  `iTime(...,0)`. Static non-repaint audit passed.
- Default is alert-only; research-auto must be explicit.
- Money risk uses `OrderCalcProfit`, volume geometry and fail-closed min-lot
  oversizing; stops are never widened.
- Ownership is symbol + magic + position identifier, with one exposure at a
  time and bounded retcode handling.
- Lifecycle telemetry records actual deal IDs, volume/price, initial risk and
  P&L/commission/swap/fee components for report reconciliation.

## Material limitations

- Historical news is disabled in the frozen baseline because no hash-bound
  calendar dataset exists. Enabling the guard blocks all entries; therefore
  any baseline result remains research-only.
- UTC mapping freezes server offset `+2` and does not claim broker DST safety.
- H4/D1 EMA structure and opposite-candle overlap are proxies for discretionary
  structure/breaker judgment; label precision has not been measured on a human
  casebook.
- No same-broker XAU cost contract currently meets AlphaFactory's spread,
  commission and independent slippage sample gates.

## Pre-Model 0 verdict

`SCREENED / COST-DATA BLOCKED`. The source is compile-ready and safe enough for
one frozen Model 0 falsification after cost evidence exists. The thesis is not
promotion-ready and is already unlikely to satisfy book cadence. If Model 0 is
valid and fails economics or cadence, this ID must be parked/killed without
post-hoc rescue.
