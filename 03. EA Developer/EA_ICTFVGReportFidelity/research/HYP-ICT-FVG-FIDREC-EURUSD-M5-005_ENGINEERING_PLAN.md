# HYP-ICT-FVG-FIDREC-EURUSD-M5-005 - restart reconciliation plan

Status: **FROZEN BEFORE SOURCE EDIT; NO PRICE OUTCOME AUTHORIZED**

## Lineage and invariant

- Parent `HYP-ICT-FVG-FIDSAFE-EURUSD-M5-004` is terminal parked at source SHA
  `B3367A3D70C26805931473B3F7185A00337231E05A3C3E9DF1A51BDF35D8630E`.
- Signal, news, thresholds, sessions, entry/SL/TP and normal management remain
  unchanged. This child reconciles broker history after offline terminal time.

## Frozen delta

1. Persist a lossless `last_classified_position_id` marker.
2. Classify a lifecycle through one idempotent function using its full net P&L
   and actual final-deal time; cooldown begins at that time, not restart time.
3. If a persisted owned position is already absent on restart, rebuild its full
   lifecycle from deal history and apply the missed final classification once.
4. Recount unique actual entry position IDs for the current UTC day from broker
   history, preventing a missed entry callback from understating the two-trade
   daily cap.
5. If a persisted closed lifecycle cannot be reconstructed, fail closed by
   activating the two-loss cooldown guard; never assume it was a winner.

## Acceptance

- Tests cover idempotent replay, final-deal timestamp use, actual daily-entry
  recount and all prior receipt bindings.
- AlphaFactory compile 0 errors / 0 warnings; exact-source non-repaint PASS;
  new source/include/EX5/log receipt fully hash-bound.
- No Strategy Tester outcome, Model 0, holdout, optimization, promotion or live
  attachment. Final state remains parked until verified cost provenance exists.
