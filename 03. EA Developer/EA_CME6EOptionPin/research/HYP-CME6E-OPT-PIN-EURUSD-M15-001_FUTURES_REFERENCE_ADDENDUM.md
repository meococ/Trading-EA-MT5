# HYP-CME6E-OPT-PIN-EURUSD-M15-001 - futures-reference addendum

Status: frozen after the source-semantics receipt and before any futures
reference payload, EURUSD target price, return, MQL5, or MT5 result was opened.

## Source gate

The DESIGN source campaign discovered 516 non-overlapping eligible option
events.  Strict point-in-time reconstruction produced 513 source-valid unique
positive OI pins over all 60 calendar months.  There were zero unresolved
instrument remaps and zero selected records at or after the decision.

The Databento dataset-condition record is authoritative for data availability.
The following four event dates were marked `degraded` and are excluded now from
every later futures-reference, target, comparator, economic, MQL5, and MT5
sample, regardless of their later outcome:

- 2019-02-22
- 2019-03-13
- 2020-02-28
- 2020-07-01

The frozen futures-reference universe is therefore 509 events.  The three
source-invalid zero-OI events remain no-trade and are not in this universe.

## Exact reference contract

For each of the 509 events:

- bind to the exact raw `underlying` futures symbol already carried by the
  source-valid option pin, for example `6EH8`; no continuous, front-month, or
  later remapping is allowed;
- use Databento dataset `GLBX.MDP3`, schema `mbp-1`, `stype_in=raw_symbol`, and
  the half-open receive-time window `[decision_utc - 60 seconds, decision_utc)`;
- retain the latest row whose `ts_recv < decision_utc`, best bid and ask are
  finite and positive, `bid_px_00 < ask_px_00`, and both best sizes are
  positive;
- compute `reference_mid = (bid_px_00 + ask_px_00) / 2`;
- locked, crossed, one-sided, zero-size, missing, stale-outside-window, or
  provider-degraded data fails that event closed.  There is no fallback to a
  wider window or a different futures contract.

Every raw payload and all request, quote, condition, source-pin, and source-gate
inputs must be SHA-256 bound before a reference can be accepted.  A Databento
dataset condition other than `available` on an event date excludes the event
before acquisition or analysis.

## Gate and comparators

- At least 95% of the 509 frozen events must produce a valid futures reference.
  Otherwise this candidate is killed before any EURUSD outcome is opened.
- Primary direction is the exact sign of `pin_strike - reference_mid`: positive
  means BUY EURUSD, negative means SELL EURUSD, equality means no trade.
- The falsification comparator is the exact reversed sign on the identical
  events and clocks.  No distance threshold, session filter, or wider data
  window may be added after a readout.

A source or futures-reference PASS authorizes only the next frozen data gate.
It is not evidence of expectancy and does not authorize an EA, MT5 backtest, or
promotion claim.
