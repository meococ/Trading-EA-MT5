# HYP-XBT-MM-TRADETHROUGH-002 — Engineering smoke result

## Verdict

`ENGINEERING_VALID_ONE_DAY` for the frozen one-day external-event engine.

This run had authority `DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE`.  Its PnL,
PF and drawdown fields are deliberately excluded from the verdict and may not be
used to tune, rescue or kill the hypothesis.

## Bound run

- AlphaFactory run: `02. AlphaFactory/runs/EA_XBTMMTradeThroughV2/20260812_062556`
- Native driver: EURUSD H1, Model 0, 2018-01-01 through 2018-01-03
- External market stream: official BitMEX XBTUSD quote/trade archives for
  2018-01-01
- Source SHA-256: `5292B0FDCCF36641714ED2D42641183B18B155EFE2B7E731324DABFD0BA8BC68`
- EX5 SHA-256: `AEE8896403DA47E8C9D77828E1311F8673157B03BBAD462D2691D9445010749E`
- Report SHA-256: `DD2A2687E350AAA7C829F379BF874496436E6B2FD47D83DE143EC2A645279963`
- Journal SHA-256: `C544607ADD514F34FAA3E1C6C1631D0FAF75F3FB7C77593FAC95F67D48B18B21`
- Fill sidecar SHA-256: `6F13305426C675C5D441037AED88C48E6A4C5C7F0D0EED74BFA374AE1BCE4542`
- Execution receipt SHA-256:
  `1FF0B9087C1856E8B31788677CCAA793D43996C6356F67D73480716EBDDA09EA`

Compile proof is the fresh package log: `0 errors, 0 warnings`.
The hash-bound non-repaint audit status is `PASS`.

## Source and engine gates

- Ordered records: 963,512 / 963,512
- Quotes: 730,578 / 730,578
- Trades: 232,934 / 232,934
- Timestamp regressions: 0
- Crossed records: 0
- Source gate: true
- Candidate engineering gate: true
- Matched-null engineering gate: true
- Action-interval violations: 0 / 0
- Pending-latency violations: 0 / 0
- Live orders after funding blackout: 0 / 0
- Matches after max-age expiry: 0 / 0
- FIFO accounting violations: 0 / 0
- Hard-cap violations: 0 / 0
- Maximum quote actions/hour: 1,652 / 1,652 (gate: at most 3,600)

Independent fill-sidecar checks also returned zero timestamp regressions, zero
non-positive quantities, maximum absolute inventory 80 and final inventory zero
for both engines.

## Repair included before the run

The final forced taker liquidation now updates XBT NAV drawdown after the
liquidation.  A focused source-contract test was added before the new source was
compiled, snapshotted and audited.  The prior V1 evidence remains sealed and was
not rewritten.

## Next gate

Do not open economic metrics yet.  First build and verify the resumable official
archive acquisition lane, point-in-time tick-size schedule, deterministic daily
index, cross-day state continuity and a no-outcome throughput run for the entire
DESIGN segment `[2018-01-01, 2022-01-01)`.
