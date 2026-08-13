# HYP-MULTI-TSMOM-D1-004 — frozen Dukascopy source gate

Status: frozen before any V4 performance run or readout.

Authority: source and execution capability only. This gate sends no strategy
orders and authorizes no economic claim.

## Why V4 is a legal successor

V1/V2/V3 used broker history and a 252-observation signal. V3 was killed before
economics because six of nine FivePercent symbols lacked 2018 real ticks and
the tester stopped before the end of DESIGN. V4 changes two preregistered
objects, not a parameter inferred from performance:

1. every leg uses the same point-in-time Dukascopy Bid/Ask source imported into
   an MT5 custom symbol;
2. formation is exactly 365 calendar days rather than 252 observations.

No V1/V2/V3 PF, return, drawdown, direction, or trade subset is admissible in
V4 decisions.

## Frozen source object

The exact machine-readable contract is
`HYP-MULTI-TSMOM-D1-004_DUKASCOPY_SOURCE_CONTRACT.json`.

- Core universe from 2018-01-01: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDJPY,
  USDCAD, USDCHF, XAUUSD.
- BTCUSD source begins 2017-05-07. It is deterministically inactive until the
  first Monday after a full 365-calendar-day warmup: 2018-05-14 00:00 UTC.
- That activation schedule is listing/warmup availability, not an outcome
  filter. After activation BTCUSD is mandatory.
- Tick timestamps are UTC milliseconds. BI5 month folders are zero based.
- Every nonempty compressed hourly payload is retained and SHA256 hashed.
- A day becomes resumable only after all 24 hours validate, the ordered daily
  `AFDTICK1` binary is fsync/rename committed, and a hash-bound daily receipt
  is committed.
- Empty exchange hours are valid only as HTTP 404 or zero-byte responses and
  remain explicit in the daily receipt. Crossed quotes, nonpositive quotes,
  time regression, malformed LZMA, or a failed request after four retries are
  fatal for that day.

The custom symbols are named `AFD_<SOURCE>_DUKA_TSMOM_V4`. Origin-symbol trade
geometry is cloned only for contract size, lot step, margin and session
metadata. Price history and spread come solely from imported Dukascopy Bid/Ask
ticks. MT5 D1 bars therefore have a fixed UTC boundary under this source
identity.

## No-outcome pilot and full-source gates

Before a strategy run, all must pass:

1. the already available 2025-01-15 14:00 UTC scale probes remain structurally
   valid for all nine symbols;
2. fresh boundary probes pass for 2017-01-02 14:00 UTC on the eight core
   symbols and 2017-05-08 14:00 UTC on BTCUSD;
3. full contracted download completes through 2026-08-11 with no unbound or
   mismatched receipt;
4. the MT5 importer reports exact daily tick counts and hourly readback hashes
   for all nine custom symbols;
5. MT5 produces a synchronized D1 series for every custom symbol. DESIGN has
   209 calendar Mondays; the 2018-01-01 market holiday is not expected to emit
   a primary tick, so the execution contract expects 208 observed Monday
   attempts, at least 207 source-valid, and no two consecutive observed
   Mondays may fail source readiness;
6. from 2018-05-14 onward a source-valid decision requires all nine active
   symbols. A missing active quote never converts that symbol to zero weight:
   the entire rebalance is skipped and the previous basket is retained.

This data is a research proxy. A surviving V4 still requires forward/demo
spread, swap, symbol-basis and execution parity against the intended broker
before promotion.
