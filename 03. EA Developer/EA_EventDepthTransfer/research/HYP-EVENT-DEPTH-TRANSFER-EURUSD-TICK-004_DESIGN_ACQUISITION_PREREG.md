# HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-004 — DESIGN acquisition preregistration

Status: `REVOKED_UNAUTHORIZED_POSTHOC_REVISION`.

This document was created and launched by a competing process without current
Owner approval for paid acquisition. It also changes the already-observed USD
0.02 per-event gate and treats observed zero-byte windows as FLAT, contrary to
the accepted HYP003/Grok boundary. It grants no authority and must not be run.
See `HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-004_UNAUTHORIZED_ACQUISITION_INTERRUPTION_RECEIPT.md`.

## Revision boundary

The parent metadata quote returned 329 clocks, 327 positive windows, aggregate USD
2.094538114962, and two zero-byte windows (`EVT0206`, `EVT0228`). This child changes
only acquisition feasibility:

- acquire every one of the 327 positive quote windows exactly once;
- freeze the two zero-byte windows as `SOURCE_UNAVAILABLE/FLAT` without retry;
- per-event live cap USD 0.03 and aggregate live cap USD 2.20.

The depth formula, event population, clock, T+15 baseline and T+60 decision are
unchanged. No payload or outcome informed this revision.

## Acquisition contract

- Source: Databento `GLBX.MDP3`, `mbp-10`, `6E.v.0`, `continuous`, output as
  `instrument_id`; `ts_recv` half-open `[T,T+60 seconds)` windows.
- Re-read all 327 live metadata quotes before purchase. Abort before purchase unless
  every size is positive, each quote is at most USD 0.03, and aggregate estimate is at
  most USD 2.20.
- Exactly one `timeseries.get_range` call per positive clock, up to 327 calls total.
  Calls may run with up to eight workers. No call retry and no batch/subscription.
- An exclusive output root and event-level `IN_FLIGHT/COMPLETE/FAILED` manifest make
  ambiguity visible. Any failed/in-flight request ends the attempt; it is not retried.
- Persist raw DBNv3, SHA-256, per-event source analysis, source ledger, manifest and
  acquisition receipt. Filenames use each event's actual `[start,end)` timestamps.

## Frozen formula and integrity

Use exactly the source-valid parent formula: weighted sizes on zero-based levels 1–9,
weights 9–1, last valid baseline at/before T+15, receive-time-weighted means on
`[T+15,T+60)`, buyer/seller aggressor sign on `[T,T+15)`, and the exhaustive signed
continuation/reversal score at T+60. Level 0 is excluded from the score.

Per-event semantic pass requires one instrument ID, half-open containment, monotone
`ts_recv`, valid baseline, at least 99% weighted coverage, no locked/crossed state over
50 ms, and nonzero initial aggressor imbalance. A completed event that fails semantics
is frozen as `SOURCE_INVALID/FLAT`; it is never re-downloaded.

## Source-census gates

- 327/327 paid requests complete and zero request failures;
- all 329 clock identities accounted (327 acquired + two frozen unavailable);
- at least 95% of acquired events pass semantics;
- at least 209 events have a non-FLAT effective classification (at least 2/week over
  the frozen 104.428571-week DESIGN span);
- continuation and reversal each represent at least 10% of semantic-pass events;
- long and short directions each represent at least 20% of semantic-pass events;
- no effective classification exceeds 80% of semantic-pass events.

These are source/cadence gates only. No EURUSD target price, return, PnL, economics,
MQL5, MT5, validation, holdout, optimization, paper, promotion, or live access is
authorized. A pass requires a new economic preregistration before outcomes are opened.
