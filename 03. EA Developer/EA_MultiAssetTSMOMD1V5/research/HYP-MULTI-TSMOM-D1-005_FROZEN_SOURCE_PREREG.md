# HYP-MULTI-TSMOM-D1-005 — frozen Dukascopy Jetta H1 source preregistration

Status: frozen before source acquisition and before any V5 economic run.

V5 is a fresh source/execution identity for the already preregistered weekly
calendar-365 own-asset TSMOM mechanism. It does not mutate V4 and does not
inspect any return, trade or equity result from V5 before freezing this source.

## Why H1 is admissible

The signal consumes only completed UTC D1 BID closes; volatility consumes only
completed D1 returns; execution occurs only once per UTC Monday; and the EA has
no intraday signal, stop, target, trailing rule, session alpha filter or
intraday exit. Consequently the sub-hour path is outside the economic claim.
Only H1 open and completed H1 close are economically meaningful here.

## Frozen construction

- Source is the official Jetta service loaded by Dukascopy's current
  Historical Data Export widget.
- Download monthly H1 BID and ASK delta-JSON responses with one worker and a
  0.75-second minimum request-start interval.
- Retain both raw responses and bind them by SHA256 to a monthly receipt.
- H1 OHLC is BID. Per-bar spread is
  `max(1, ceil((ASK_open - BID_open) / source_point))`.
- Every BID timestamp must have an ASK timestamp. Any corresponding ASK OHLC
  below BID, time mismatch, malformed delta, or non-positive price fails the
  complete source month.
- Every decoded price is rounded to the frozen source point. Jetta occasionally
  publishes a close exactly one source point outside its H1 high/low envelope;
  high/low is expanded only enough to contain open/close, and every such
  one-point correction is counted in the monthly receipt. A correction larger
  than one source point fails the source month.
- D1 close is the last completed H1 BID close in the UTC day. There is no
  broker-time or future-bar substitution.
- Weekly decision is the first available Monday H1 open at or after 00:00 UTC
  where every active symbol is source- and quote-valid.
- If any active symbol is missing, the whole frozen snapshot retries unchanged
  through Tuesday; the previous basket remains afterward. No symbol is set to
  zero and no weights are recomputed from a smaller universe.

## Declared fidelity loss

V5 does not claim the sub-hour price path, tick-level spread distribution or
tick-level adverse selection. Generated intrabar ticks cannot be used to add
an exit, filter or stop. Changing that use requires a new hypothesis identity.

## Source gate before economics

1. Every monthly BID/ASK pair, decoded AFRATE1 binary and receipt is hash-bound.
2. Official Dukascopy D1 candles are session anchored (the FX pilot begins at
   New York 17:00), not UTC-day candles. For each symbol, aggregate H1 BID bars
   inside consecutive official D1 session boundaries and match official D1 BID
   OHLC within one source point on at least 99.5% of common sessions. This is a
   source-decoding check. The EA's UTC-day close remains the last completed H1
   BID close strictly before the UTC boundary and is not falsely compared with
   the provider's differently anchored D1 close.
3. All active symbols have a current Monday H1 bar on at least 98% of expected
   DESIGN weeks; weekly snapshots remain fail-closed regardless of this rate.
4. MT5 custom-symbol import readback matches exact H1 count, first/last epoch,
   OHLC and spread.
5. Commission, contemporaneous-spread slippage overlay and controlled
   financing are frozen and hash-bound before the first V5 economic run.

This source gate authorizes engineering evidence only. It does not authorize a
profit factor, expectancy, drawdown or edge verdict.
