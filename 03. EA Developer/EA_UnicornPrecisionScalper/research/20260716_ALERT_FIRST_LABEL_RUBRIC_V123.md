# ALERT_FIRST_LABEL_RUBRIC_V1.3

Status: `FROZEN_PRE_OUTCOME_REVIEW_RUBRIC`  
Frozen: 2026-07-16, before any V1.3 reviewer output or outcome join  
Authority: labeling/data-quality only; no trading hypothesis or Model-0 authority

## Purpose and boundary

This rubric reviews the 200 blank-label alerts collected by AlphaFactory run
`20260716_155111` from source contract `UPS_ALERT_FIRST_CASEBOOK_V1_3` and
source SHA256
`10E278435644E63FD6418047AC775537CECEE8BBA4A9E5D89842E0F15312CB18`.
`decision_time_utc` is the information cutoff written by the source: the close
time of the final M5 bar used by `EvaluateClosedSignal`, not that bar's open
time. Reviewers may use only bars whose close time is no later than this cutoff.
They must not inspect any later bar, trade result, PnL, MFE, MAE, forward
return, fill or report performance field.

The source CSV remains immutable. Reviewer judgments live in separate overlay
files keyed by `event_id`. V1.3 provides the blank
`label_true_breaker_valid` column natively and binds every row to the exact
source. This schema correction does not change the detector or authorize a new
signal.

Automated or AI review is exploratory calibration only. It must record
`reviewer_type=AI_EXPLORATORY` and cannot be represented as the independent
human labeling required by `ALERT_FIRST_CASEBOOK_V1_CONTRACT.md`.

## Allowed labels

Each component is exactly one of `yes`, `no`, or `ambiguous`. `ambiguous` is a
real result and must not be coerced into a pass. Confidence is `high`, `medium`,
or `low`.

### True liquidity sweep

`yes` requires a completed M5 bar in the four-bar event window to wick beyond
a liquidity reference visible before that bar and to close back on the original
side by the decision. A confirmed local pivot must have two completed bars on
both sides before the sweep; equal highs/lows or a clearly bounded session
extreme may also qualify only when it is visible in the supplied context.

Use `no` for a directional close-through with no reclaim or when the detector
extreme is not attached to visible prior liquidity. Use `ambiguous` when the
claimed reference lies outside the packet or depends on discretionary session
annotation not present in the bars.

### True displacement

`yes` requires the detector direction, a real body at least `1.50 * ATR(14)`
as reported by the frozen row, and a close in the directional outer quartile
of the candle range. `no` applies below either quality condition. A zero-range
or inconsistent row is `ambiguous` and a data-quality failure.

### MSS/BOS close

`yes` requires a completed M5 or M15 close after the sweep beyond the nearest
opposing confirmed swing that existed before the sweep. A wick through the
swing is not enough. `no` applies when no close break occurs by the decision.
Use `ambiguous` if two plausible pre-sweep swing anchors produce opposite
answers; record both anchors in `notes`.

### Valid breaker

The memo does not define breaker taxonomy precisely enough to invent a hidden
binary rule. A reviewer may label `yes` only when all of the following are
visible: an opposing candle/order-block candidate existed before displacement,
price closed through its invalidation edge in the detector direction, the
failed block range overlaps the logged FVG, and the block was not already
fully traversed before the decision. `no` applies when a required fact is
visibly false. Otherwise use `ambiguous`; do not substitute the EA's maximum
overlap candle proxy for a true breaker.

### Fresh unfilled FVG

`yes` requires the logged three-candle directional gap to exist on completed
bars and no completed bar after formation and through the decision to trade
through its full range. `no` applies to a malformed or fully traversed gap.
Use `ambiguous` when the logged bounds cannot be reconciled to the supplied
bars. A newly formed decision-bar FVG may be fresh but has no later retest yet.

### Micro confirmation

`yes` requires a completed post-formation interaction with the logged FVG or
breaker overlap followed by a directional rejection close or a documented
CISD-like close shift, all no later than the decision. FVG formation itself is
not confirmation. `no` applies when no post-formation zone interaction exists.
Use `ambiguous` only when the zone or formation bar cannot be reconciled.

## Final decisions

`label_core_setup_accept=yes` only when true sweep, true displacement,
MSS/BOS, valid breaker and fresh FVG are all `yes`. Any `no` rejects; any
`ambiguous` makes the final core decision `ambiguous`.

`entry_readiness` is separate:

- `limit_candidate`: core accepted, but no micro confirmation;
- `market_confirmed`: core accepted and micro confirmation is `yes`;
- `reject`: a core component is `no`;
- `ambiguous`: no core component is `no`, but at least one is ambiguous.

The acceptance density gate uses only unambiguous `label_core_setup_accept=yes`
over all reviewed rows. Do not lower thresholds to raise density.

## Reviewer overlay schema

Required fields: `event_id`, six component labels including
`label_true_breaker_valid`, `label_core_setup_accept`, `entry_readiness`,
`primary_reject_reason`, `notes`, `confidence`, `reviewer_id`,
`reviewer_type`, `reviewed_at_utc`, and `outcome_seen=false`.

Preferred reject codes: `SWEEP_FALSE`, `DISPLACEMENT_WEAK`, `NO_MSS_CLOSE`,
`BREAKER_INVALID`, `BREAKER_AMBIGUOUS`, `FVG_INVALID_OR_FILLED`,
`NO_MICRO_CONFIRM`, `CONTEXT_INSUFFICIENT`, `DATA_MISMATCH`.

## Sealed gates

- At least 100 rows per reviewer.
- Prefer two independent human reviewers; Cohen kappa on the unambiguous final
  core accept/reject label must be at least `0.70`.
- AI-only agreement is diagnostic and does not clear the human-label gate.
- Accepted density below `25%` closes the detector-to-memo gap.
- Only after the human gate may one de-duplicated feature family be frozen for
  a no-outcome density/separation probe. No outcome join is authorized here.
