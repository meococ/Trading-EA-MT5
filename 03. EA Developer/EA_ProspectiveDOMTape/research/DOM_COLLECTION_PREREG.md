# Prospective XAU/Forex DOM collection preregistration

Date: 2026-08-13

Status: `FROZEN_SOURCE_COLLECTION_ONLY_PRE_BUILD`

## Purpose

Create a zero-cost, prospective database from the broker's currently visible
MT5 Depth of Market for `XAUUSD`, `EURUSD`, `GBPUSD` and `USDJPY`. This is the
next database-first step after the local historical/source shelf returned no
lawful revival candidate and the Economic Calendar lane was killed.

## Frozen collection contract

- Platform: MT5/MQL5 only; current `FivePercentOnline-Real` terminal.
- Symbols: exactly `XAUUSD`, `EURUSD`, `GBPUSD`, `USDJPY`.
- Input source: `MarketBookAdd`, `OnBookEvent`, `MarketBookGet` only.
- Record every successful changed full-book snapshot with terminal local,
  trade-server, terminal-current and monotonic millisecond clocks.
- Persist symbol, event sequence, payload hash, depth, and every level's
  `ENUM_BOOK_TYPE`, price, volume and `volume_real` in append-only UTF-8 output.
- Persist subscription, empty-book, API-error, duplicate-payload and heartbeat
  receipts. A restart must load only validated state and never silently reset a
  sequence backwards.
- No `CopyRates`, `CopyTicks`, indicators, Calendar APIs, WebRequest, trading
  classes, order APIs, positions, outcomes or future-price labels.
- Refuse Strategy Tester and optimization mode; all subscriptions must be
  released on shutdown.
- Missing subscription, I/O failure, malformed durable state, sequence rollback
  or an empty/failed book is explicit and fail-closed.

## Immediate engineering gate

One bounded live smoke may run after source tests and a fresh AlphaFactory
compile receipt showing 0 errors and 0 warnings. It passes source capability
only if all four subscriptions succeed, at least one nonempty snapshot is
captured for each symbol, sequence/time are monotonic, state/output are readable,
and the source contains no trading or price-outcome API.

## Research boundary

The broker DOM is not assumed to be firm exchange L2, and MT5 does not provide
historical DOM to Strategy Tester. Therefore a smoke pass proves only prospective
source capability. No imbalance sign, prediction, hypothesis ID, EA entry,
economics, validation, promotion, paper trading or live trading may open from
the collector itself. A later candidate requires sufficient hash-bound tape,
outcome-blind quality gates, a separately frozen causal mapping, and a
deterministic MT5 replay contract.
