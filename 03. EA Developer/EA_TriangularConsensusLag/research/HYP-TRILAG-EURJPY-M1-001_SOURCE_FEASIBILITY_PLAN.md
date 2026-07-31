# HYP-TRILAG-EURJPY-M1-001 — Frozen Source-Feasibility Plan

- Status: `FROZEN_SOURCE_BUILD_ONLY`
- Frozen at: `2026-07-29T14:15:00Z`
- Attempt budget: exactly one source inventory attempt,
  `TRILAG001-SOURCE-001`
- Economic status: `NOT_AUTHORIZED`
- MT5 / MQL5 status: `NOT_AUTHORIZED`
- Validation / holdout / paper / live status: `NOT_AUTHORIZED`

## Research question

Can the D-portable FivePercent broker history support a later, outcome-blind
M1 test of a triangular consensus-lag mechanism across `EURUSD`, `USDJPY` and
`EURJPY` over a long enough calendar window?

This stage answers source availability only. It does not test whether the
mechanism has edge.

## Mechanism reserved for a later child hypothesis

The no-arbitrage identity is:

`log(EURJPY) = log(EURUSD) + log(USDJPY)`.

A later child may test whether two completed M1 lead legs that move in the
same direction imply a still-lagging `EURJPY` move that is followed after the
decision bar. The child must enter no earlier than the next observed bar/tick,
remain same-day flat, and use only information available at the close of the
decision bar.

This plan does **not** authorize that calculation. It only reserves the exact
identity so the source inventory cannot silently drift into a generic basket,
pair-z-score, three-leg latency arbitrage, or a post-event toxicity label.

## Primary-source basis and adverse prior

- Foucault, Kozhan and Tham (2017), *Toxic Arbitrage*, documents short-lived
  triangular opportunities and asynchronous adjustment, but its toxic versus
  non-toxic classification uses the initiating pair's subsequent path. That
  label is future information and is forbidden in a live rule.
- Akram, Rime and Sarno (2008), *Arbitrage in the Foreign Exchange Market:
  Turning on the Microscope*, finds that the relevant deviations require
  carefully matched tick data and can disappear at lower sampling frequency.

Therefore the prior for a broker M1-bar translation is adverse. A source pass
will not be presented as evidence that retail-speed continuation is viable.

Primary links:

- https://doi.org/10.1093/rfs/hhw103
- https://www.norges-bank.no/en/news-events/publications/Working-Papers/2005/200512/

## De-dup and failure radius

Previously tested H1/H4 objects include same-bar FX consensus, peer lead-lag,
USD-majority lag-follow, EUR lead catch-up and residual fade. Those objects
failed their own probes. This source object is materially narrower because it
requires the exact three-rate parity identity at M1 and reserves only
`EURJPY` as the lagging execution leg.

The later economics child, if source-feasible, must include the locked prior
lead-lag / consensus / laggard controls rather than claiming novelty by name.
It may not rescue any prior object by changing its hour, threshold, horizon,
symbol subset or direction after seeing outcomes.

## Frozen source scope

- Broker root: D-portable `FivePercentOnline-Real/history` selected from the
  existing AlphaFactory machine configuration; implementation must resolve it
  from workspace/runtime config and must not hardcode a user-specific path.
- Symbols: exactly `EURUSD`, `USDJPY`, `EURJPY`.
- Inventory years: exactly `2016` through `2024`, inclusive.
- Expected annual HCC set: exactly `3 symbols x 9 years = 27` files.
- Research holdout payload: every `2025+` HCC payload remains unopened. Parent
  exploratory directory metadata had already observed that later annual files
  exist; no later HCC payload, bar, timestamp or price was decoded.
- No cache file is part of the contract because cache files can mutate while
  the terminal is running.

## Allowed operations

The builder and synthetic tests may be created inside this package. The one
real source attempt, only after an independent implementation review and a new
registry authorization row, may:

1. resolve the exact configured D-portable history root;
2. construct only the 27 in-scope annual HCC paths;
3. reject symlinks/reparse points and any path escaping the allowed root;
4. record file size and UTC modification time before hashing;
5. stream SHA-256 over opaque file bytes without parsing HCC structures;
6. record file size and UTC modification time again and fail if either changed;
7. create fresh evidence artifacts atomically under the frozen attempt root.

## Forbidden operations and zero counters

The source attempt must keep all of these at zero/false:

- HCC records decoded;
- bars, timestamps, OHLC, tick volume or spread fields read;
- parity residuals, returns, ranks, signals or future paths computed;
- trades, costs, PF, expectancy, drawdown or economics computed;
- MT5 / MetaTrader5 / terminal launches;
- MQL5 files created or compiled;
- network calls or paid requests;
- validation / holdout payload access;
- paper, live or promotion actions.

## Acceptance gates

The one source attempt passes only if all gates pass together:

1. The resolved broker root is on drive `D:` and under the configured portable
   AlphaFactory runtime.
2. Exactly 27 expected HCC files exist; no extra year is inventoried.
3. Every expected file is a regular, non-reparse, non-symlink file.
4. Every file is non-empty and stable across its hash operation.
5. Every file has a valid SHA-256 and the aggregate symbol/year mapping is
   complete with no duplicate path, symbol or year.
6. No `2025+` HCC payload is opened or hashed.
7. Every forbidden-operation counter remains exactly zero/false.
8. `attempt_started.json`, `source_inventory.json`,
   `source_feasibility_receipt.json` and `attempt_terminal.json` are created
   once, hash-bound and mutually consistent.

Any failure yields `FAIL_SOURCE_FEASIBILITY_NO_ECONOMICS_AUTHORITY`. A pass
yields only `PASS_SOURCE_FEASIBILITY_FUTURE_CHILD_PREREG_ONLY`.

## Next-stage boundary

No M1 bar may be decoded under this ID. A pass permits only a fresh child ID
with a frozen, DESIGN-only structural contract that specifies synchronization,
decision-time information, robust event threshold, cooldown, missing-bar
handling, prior controls and one-shot falsification before it reads any price.
