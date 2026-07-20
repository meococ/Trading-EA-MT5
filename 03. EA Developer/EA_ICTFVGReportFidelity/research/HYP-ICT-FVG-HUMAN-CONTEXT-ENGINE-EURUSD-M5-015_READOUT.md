# HYP-015 — Human Context Engine engineering readout

## Verdict

`PASS_ENGINEERING_HUMAN_CONTEXT_OBSERVATION_NO_EDGE_CLAIM`

The EA now records the decision-time context that a discretionary ICT/FVG
trader normally inspects, without changing the existing signal or trade
policy. This is an instrumentation and logic-surface result, not evidence of
economic edge.

## Implemented context

- H1/H4 closed 20-bar dealing ranges and raw entry locations.
- Latest two confirmed H1/H4 swing structures (strength 2, lookback 120).
- Previous broker-day/week extremes, current UTC Asia 00:00–07:00 range, and
  latest H1/H4 swing liquidity.
- Nearest directional draw-on-liquidity, pool count, pips and available R.
- Internal/external sweep classification and swept-pool count.
- Point-in-time partial H1/H4 candles reconstructed only from closed M5 bars.
- Confirmation impulse, directional M5 run, range extension and spread/risk.
- Explicit semantic state: incomplete, no target, exhaustion, structure
  conflict, external/internal sweep with room, or insufficient room.

Every snapshot is written to a separate pre-send decision ledger. Its schema
contains no exit, PnL, commission, MFE or MAE field. `TryOpenTrade` remains
outside the engine; HYP-015 cannot veto, resize or redirect a trade.

## Verification

- Frozen prereg SHA-256:
  `72D58A4D1EABB43F6188B38E1835E2562E5434FF84166FC625BA1EFBBFCD7799`.
- Source SHA-256:
  `17E8C20F323402C60B830E47109AD265212869E2E0A8526F21EFDA4734AA1450`.
- `HumanContextEngine.mqh` SHA-256:
  `A24196DD908AD83BF9CE2047C3DCE810C57FDA56C861EB0F097D11600A0998F2`.
- AlphaFactory compile: `0 errors, 0 warnings`; EX5 SHA-256
  `DC00141A5C94D6CB91F8E4F78DAF42A115B6B18302A7D07E409F4964B2599206`.
- Non-repaint audit V16: `PASS`, zero findings. Every H1/H4/D1/W1/M5
  context read begins at shift 1; the only bar-zero access in the package is
  the pre-existing `iTime` new-bar gate.
- Outcome-blind reference: 3,385 unique rows; 3,354 complete
  (`99.0841949778%`), above the frozen 99% gate.
- Six casebook H1 range locations: maximum absolute error `0.0` against the
  frozen chart-manifest anchors.
- Exact rerun reproduced both the reference CSV and result JSON hashes.

Of the 31 incomplete rows, 30 are at the beginning of the available 2018
history, where the frozen 120-bar H4 lookback does not yet exist. The last is
position `6770`: its 2026-07-17 15:35 UTC entry is later than the bound M5
parquet endpoint (07:35 UTC that day). They remain explicit `INCOMPLETE`; the
builder does not backfill from future data or another unbound source.

## Boundary and next legal step

No HYP-015 backtest was scored and no performance metric was created. Passing
this gate only permits a fresh, pre-outcome HYP-016 policy to select a small,
natural subset of these context states once. HYP-012 and HYP-014 remain
terminal; their thresholds or model cannot be tuned or revived.
