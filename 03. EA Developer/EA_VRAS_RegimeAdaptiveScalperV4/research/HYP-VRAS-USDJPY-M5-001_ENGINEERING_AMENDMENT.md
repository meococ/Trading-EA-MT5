# HYP-VRAS-USDJPY-M5-001 engineering amendment

Issued: 2026-08-02, after adversarial source review and before the final compile,
MT5 launch, trade outcome, Model 0, validation, or holdout access.

This amendment resolves implementation ambiguities in the frozen preregistration.
It does not change the symbol, timeframe, signal thresholds, session clock,
direction pair, economic gates, or sealed datasets.

## Estimator continuity

- Copy exactly 72 completed, contiguous M5 closes.
- Every estimator bar must belong to the same wrapping Asian session as the
  decision bar. A gap, weekend stitch, or prior-session stitch invalidates the
  estimate.
- Because the session opens at 22:15 UTC, the earliest eligible decision bar is
  04:15 UTC.

## Entry geometry and risk accounting

- The geometry price is the current executable price shifted adversely by the
  frozen 0.3-pip entry-slippage allowance (the `adverse entry bound`).
- The protective stop is the farther of the OU tail stop and 1.5 ATR from the
  adverse entry bound. A better confirmed fill reduces actual risk and does not widen the server stop after entry.
- The reverse control mirrors stop and target distances around the adverse entry
  bound.
- Cost-inclusive lot sizing uses stop loss at the adverse entry bound, round-trip
  commission, and the remaining exit slippage. Entry slippage is already
  represented by the adverse entry bound and must not be counted again.
- Lifecycle `risk_pts` and `initial_risk_account` both use the proportional
  stop-only basis. Cost-inclusive planned risk remains the lot-sizing control.
- Every partial fill receives only its proportional stop risk. Every fill is
  checked against the immutable adverse entry bound; a worse fill latches a
  hard-cut reason.

## Lifecycle and failure telemetry

- Pending deal reconciliation blocks re-entry.
- Entry reconciliation is identical for immediate and deferred history access.
- Final-close cleanup is scoped to the matching position identifier.
- Run metadata records persistence faults, confirmed adverse-fill breaches, and
  pending lifecycle reconciliation state.

No optimizer, economic threshold repair, outcome read, Model 0, validation,
holdout, promotion, paper, or live authority is opened by this amendment.
