# HANDOFF — BUILD → LEVEL-LAB

From: build lane (perception-build). To: LEVEL-LAB (mandate
`levellab/MANDATE_LEVEL_LAB.md`, R15 §15.2).

Ruler for all numbers below: `eval_v2` `50e11fd5`. Engine hash at
measurement time: `ef06f265ab84889f` (labels file
`evalcheck/labels_v1_ef06f265ab84889f.jsonl`, 198 TUNE panels).

## 1. The `session_extreme` route is completely starved

Route-level funnel on the ef06f265 labels (LEVEL_CARRIED candidates
only):

| route | proposals | right (FUNNEL label) | born |
|---|---|---|---|
| session_extreme | 990 | 12 | **0** |
| broken_line_edge | 749 | 19 | 5 |
| congestion_edge | 465 | 5 | 0 |
| broken_box_edge_up | 247 | 7 | 1 |
| broken_box_edge_down | 243 | 3 | 0 |

Outcome of the 12 right `session_extreme` proposals:
`rate_limited` 7, `expired` 3, `outranked` 2 — they never even reach
the birth gate while the joint `rate_total` window is full. Zero
`below_min_score` on this route: the score floor is not the blocker;
slot competition is.

Overall LEVEL_CARRIED on ef06f265: 2704 proposals, 46 right, 13
golden keys; born ~0.13–0.15 vs oracle ~0.50 (ruler) / 0.52 (mine).

## 2. Golden raw-note semantics (what the author actually draws)

Golden LEVEL_CARRIED raw notes name three situations:

- "old breakout base" — a level left behind by a break, carried
  forward;
- "congestion top projected" — a congestion edge carried forward as
  a level;
- "neckline".

All three share one shape: **the level is drawn where price left it,
and it matters when price comes back.** The routes in `levels.py`
map onto these semantics correctly — generation is not obviously the
gap; the gap is birth timing/selection.

## 3. Birth-on-return hypothesis (measured, not implemented)

Idea: a carried level only earns ink when price *revisits* it — the
author draws the old base when price returns to test it, not at the
moment of the break. Eval-safe: the drawn span is counted from the
candidate's `t0` (geometry), not from birth time, so a delayed birth
does not move the span.

Measured on FUNNEL labels (right vs wrong LEVEL_CARRIED candidates),
feature = did price return to within the level's tolerance band
within K bars of the proposal:

| feature | AUC (all) | per-fold AUC |
|---|---|---|
| ret_24 (return within 24 bars) | 0.645 | ~0.67 / 0.61 / 0.73 / 0.71 (one fold nan — few positives) |
| ret_48 (return within 48 bars) | 0.635 | ~0.62 / 0.63 / 0.68 / 0.66 |

This is the strongest causal signal found for the family — it beats
everything else I measured for LEVEL_CARRIED and it clears the
≥ 0.60-per-fold bar on the folds where it is defined.

Suggested shape (LEVEL-LAB owns the design): keep the candidate
**dormant** — parked outside the rate/budget competition — until
price trades back into its band; on return, promote it into the pool
with normal score competition. Dormancy should be bounded (e.g. the
existing TTL or a stated horizon) so stale levels do not linger
forever; candidates that are returned-to but lose the slot race can
stay dormant until the next touch.

Watch-out: `broken_line_edge` now shares `rate_level_carried`
(R13 §13.3) — check the interplay before picking the cap story.

## 4. Known residual: `retire_far` vs carried levels

Ruling 11 §11.4a retire_far (price > 3·ABR from band for ≥ 24
consecutive bars) can cut a *correct* carried level early: golden
LEVEL_CARRIED objects have internal no-touch streaks up to 63 bars
and at least one measured object (9.65a) has a 50-bar far streak
inside its drawn span. If LEVEL losses persist after your changes,
the Lead's §14.3 narrowing suggestion is: exempt level-family
objects with ≥ 2 defended touches from retire_far and let
`stale_bars` be their only exit. That exemption lives in `engine.py`
(build lane) — file a REQUESTS entry if you want it, do not edit
`engine.py` yourselves.

## 5. Files I did not touch

`levels.py` and the level params are LEVEL-LAB's from R15 §15.2
onward. All measurements above are from the production proposal
stream (FUNNEL prefix labels) per the §15.1 rule — no lab-stream
numbers.
