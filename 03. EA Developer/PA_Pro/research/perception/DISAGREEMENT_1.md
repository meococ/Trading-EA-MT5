# DISAGREEMENT_1 — v1 structure flooding (TUNE round 1)

Baseline after B1: engine births ~57 objects/day vs golden ~2.5/panel;
median object life ~20 bars; churn cycle birth→die→rebirth dominates.

## Observed disagreement

| type | golden | engine (before) | engine (after) |
|---|---|---|---|
| BOX | 111 | 1402 | 275 |
| BRACKET | 85 | 67 | 108 |
| CONTEXT_LINE | 9 | 906 | 252 |
| CONTEXT_RANGE | 6 | 116 | 160 |
| LEVEL_CARRIED | 48 | 2466 | 282 |
| PATTERN_LINE | 186 | 1164 | 548 |
| SQUEEZE | 2 | 125 | 79 |
| clutter median | — | 13.33 | **4.67** |

Death-reason census (15-panel diagnostic, before fix):
LEVEL_CARRIED `traversed` ×130, BOX `post_break_window` ×86,
lines `extension_done` ×101, `outranked` ×222 across types.
Every death freed a slot and the pool (always full of near-identical
siblings) birthed a replacement — ~20 objects/panel vs golden ~2.5.

## Root causes found

1. **Birth rate was unbounded.** `min_score_birth=0.5` + free slots on
   every death → births = deaths. DN_SALIENCE §5 stage 5 says the
   budget is "top-k where k follows the golden count distribution" —
   i.e. a *rate*, not just a concurrency cap.
2. **Mechanical carry births** (DN_LEVEL §6 names this exact failure:
   460 born vs 48 drawn in v0). Every box/line break spawned a carry.
3. **Near-twin rebirths.** A dead box reborn 1-2 pips shifted evaded
   the exact-signature grave check.
4. **Score separator absent.** Born-object scores: matched median 8.5,
   unmatched median 4.1 — a floor near 5 keeps most matched ink while
   cutting the weak-candidate tail.

## Fixes applied (all DN-grounded)

- `salience.py`: birth-rate caps per KIND + a joint cap
  (MEASURE-TUNE golden births/panel: BOX p90=1, PATTERN_LINE p90=2,
  LEVEL_CARRIED p90=1, MINI_LEVEL p90=1, BRACKET p90=1,
  CONTEXT_LINE/CONTEXT_RANGE p90=0 max=1; joint p95=5).  Keys are
  per-kind so a weak MINI_LEVEL cannot starve a strong LEVEL_CARRIED
  sharing the family; the joint cap stops all kinds hitting p90
  simultaneously (golden count is a joint distribution, not the sum
  of marginals).  RANGE_OPEN is exempt (session tracker that converts
  to BOX in place — a lifecycle transition, not a birth).
  Broken-edge/congestion carries are exempt from the joint cap — the
  parent's edge continuing, already paid for at parent birth — but
  still bound by `rate_level_carried`.
- `salience.py`: `_grave_band` — footprint-level grave for dead
  objects; a same-family candidate whose band shares >=50% mass with a
  band that died within `cand_ttl_bars` is the same evaluation
  resuming, not new ink.  Wide bands also require the candidate's
  buildup to reuse bars from the dead object's drawn span (same
  congestion episode, DN_BOX).
- `salience.py`: ordering fix — grave check runs before displacement
  so a blocked candidate cannot kill an incumbent on its way out.
- A per-class birth floor (`min_score_birth_signal=5.0`, measured
  separator matched ~8.5 vs unmatched ~4.1) was TRIED and REVERTED:
  it cut ~75% of unmatched ink but also blocked every short-fixture
  structure in the test suite (fixtures score ~4-6) while barely
  moving TUNE clutter (9.58→9.00 pre-rate).  The rate cap is the
  correct mechanism for the same gate.

## Metric deltas (full TUNE, v1)

| metric | before | after | gate |
|---|---|---|---|
| clutter median | 13.33 | 4.67 | ≤1.5 |
| BOX recall | 0.25 | 0.05 | ≥0.70 |
| PATTERN_LINE recall | 0.00 | 0.00 | ≥0.50 |
| LEVEL_CARRIED recall | 0.58 | 0.10 | ≥0.60 |
| LABEL_TF agreement | 0.14 | 0.00 | ≥0.60 |

Recalls dropped with volume: fewer births → fewer chance overlaps.
Precision stayed ~0.01-0.03 — the births are not the golden objects.

## What remains (round 2 targets)

- **Selection quality, not volume, is now the binding constraint.**
  Recalls dropped with volume: the rate cap picks score-best
  candidates but those are not the golden objects. 9.23c: golden box
  [1.3292–1.3305] vs ours 44-pip-wide earlier congestion bands —
  `cluster_edge` takes outermost company-supported extremes, including
  poke wicks → bands too wide and born too early.
- Carries land at wrong prices (9.1b golden 1.3318 vs ours 1.3331)
  because the parent box edges are wrong — carry inherits the error.
- PATTERN_LINE spans run to day-end (never traversed) while golden
  lines die at their break bar — the ±15-min `t1` match never fires.
  Worse, the geometry itself is wrong: only **2/57** golden lines with
  endpoints have any engine line within 6 pips of BOTH endpoints —
  `hull_max_touch` picks max-touch hull pairs, not the neckline-style
  anchors Volman draws (9.1a: rising line under the SHS lows).
- CONTEXT_LINE 252 vs golden 9 — own `rate_context_line=1` bucket but
  the route itself (hull_max_touch context evals on every pivot)
  proposes constantly; rate caps bound it, they don't fix selection.
