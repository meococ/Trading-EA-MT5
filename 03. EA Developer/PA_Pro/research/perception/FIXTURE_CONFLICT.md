# FIXTURE_CONFLICT — the seven named fixtures vs TUNE fidelity (R50 §50.3)

The frozen suite is 65/72.  The seven failures are one defect class:
a priority-1 box candidate loses the family live slot to a
CONTEXT_RANGE / CONTEXT_LINE incumbent (or a RANGE_OPEN precursor)
because the slot is score-gated and the context scores higher.  The
fixtures assert the spec §5 ranking — a priority-1 box outranks a
context object whatever the score.

The seven:

1. `test_pullback_end_box_birth`
2. `test_range_box_double_top`
3. `test_false_break_wick_keeps_edge`
4. `test_break_close_beyond_edge`
5. `test_tease_vs_proper_break_class`
6. `test_tf_relabel`
7. `test_reanchor_on_new_double_top`

Representative numbers (zigzag fixture): box cand score 6.76 vs
context incumbent 7.12 + hysteresis → "outranked".  Fixture wants the
box born anyway.

## What was tried (R49 §49.4.2 "yield, not evict" — three variants)

All three cure all seven fixtures (**72/72 unmodified suite**) and all
keep flag-OFF ≡ parent (576/576 canonical identical).  All three fail
the §34.5 keep rule the same way:

| arm | hash | box@1 | level@1 | line@2 | bracket@1 | clutter med |
|-----|------|-------|---------|--------|-----------|-------------|
| parent (K1–K6) | `9acaa206` | .076 (9/119) | .079 (6/76) | .104 (20/193) | .341 (29/85) | 5.00 |
| ctxyf: fam_context + ctx_yield | `a3742b16` | .092 +2 | .039 −3 | .104 = | .329 −1 | **5.67** |
| ctxy: standalone (context stays box-family) | `fcd56aaf` | .092 +2 | .039 −3 | .098 −1 | .329 −1 | **5.67** |
| ctxy + overlap-gated yield | `99249af2` | .092 +2 | .039 −3 | .098 −1 | .329 −1 | **5.67** |

(The overlap gate is a no-op on TUNE: a live context sits at current
price, so every priority-1 candidate's band overlaps it.)

## Mechanism of the failure

The fixture-required yield is score-blind, so it unmasks demand the
context blocker currently absorbs:

- In the parent, a context object holding the family slot kills ~1.4
  box candidates per panel by "outranked".
- Under yield, each of those candidates births instead.  Every yield
  starts a birth–death cycle: context yields → box born → box is
  outranked/closed → the slot frees → a context re-births → the next
  box candidate yields again.
- Measured: **+282 BOX births over 60 panels** (~+4.7 per
  context-bearing panel).  Born boxes stay ACTIVE as residual ink →
  clutter median 5.00 → 5.67; the extra churn displaces levels →
  level@1 −3.
- Metric note: hiding via `state = "DELETED"` removes the object from
  `snapshot.py`'s live book (`state != "DELETED"`) but NOT from
  `eval_v2.eng_objects` (no state filter; t1 falls through to last
  fed bar) — so under this implementation a hidden context still
  counts toward the clutter ratio.  A future variant that also closes
  `t_right` on hide would still not help: a restored object's drawn
  interval still intersects the window.

The M1 gain is real but bought at ~140 extra box births per golden
hit — exactly the trade the keep rule exists to refuse.

## Why this may be a spec-vs-author conflict

Spec §5 ranks the priority-1 box above CONTEXT (priority 4).  The
author's TUNE drawings punish that ranking: her panels never carry
the box volume this rule produces at our candidate density.  Either
(a) the author's box generator is far more selective than ours, so
score-blind priority never floods in her world, or (b) she does not
apply §5 as literally as the fixtures encode.

Directions carried to the next round (per §49.4.2 fallback):

- **Conversion-in-place** — the context object BECOMES the box
  (CONTEXT_RANGE→BOX relabel, the `asia_convert`/`asia_absorbed`
  precedent in boxes.py): zero net births, no flood.  The fixture
  sees its box; the ledger sees no new object.
- **Generator-level** — don't birth a context object where a box is
  forming (the context IS the proto-box): the blocked-candidate
  population never exists, so nothing needs yielding.

No lane edits the fixtures or the spec; the conflict is for the Lead
and possibly the Owner alongside the P-FREEZE package.

## R51 §51.4.2 — conversion-in-place attempted (13:1xZ)

`salience.ctx_convert` implements the first direction: a CONTEXT_RANGE
blocking a priority-1 box candidate is relabelled to BOX with the
candidate's geometry — same object, zero net births, t_left kept.

Suite leg: **72/72 GREEN under both gates** — all seven fixtures cured
with no side-effects (first mechanism to reach 72/72; the yield
variants passed fixtures but failed M1).

M1 on the K8 parent (`be4eea26`, marker.off + cong_pivedge):

| variant | gate | box@1 | level@1 | line@2 | bracket@1 | clutter | verdict |
|---|---|---|---|---|---|---|---|
| ctcv loose | overlap | .101 +2 | .053 **−4** | .088 **−3** | .353 +1 | 5.00 | FAIL §34.5 leg 2 |
| ctcv wraps | contains + ≤2× width | .092 +1 | .092 −1 | .093 **−2** | .341 = | 5.00 | FAIL §34.5 leg 2 |

Loose gate fired **186 conversions / 198 panels** — nearly one per
panel: the structural envelope is the context workhorse and converting
it removes coverage that levels/lines scored against.  The fixtures
need conversion across a ~1.5× width gap (context 46.6p vs box 31.6p),
so edge-equality is too strict (7/7 fail); the `wraps` gate (context
contains the box band AND ≤2× its width) keeps 7/7 green and is the
variant under test at `3ca9097b`.

**§51.4.2 verdict: the debt stands.**  Conversion-in-place is the
right *mechanism* — it reaches 72/72 without births — but every gate
that cures the fixtures consumes a CONTEXT_RANGE that carries real
load on TUNE.  The damage shrinks with gate strictness (loose: level
−4/line −3; wraps: level −1/line −2) yet stays past the −1 cap.  A
third iteration (e.g. score-gated conversion) cannot cure the
fixtures: they require the box to win while LOSING on score
(6.76 vs 7.12+hyst) — any score gate reintroduces the block.

Five mechanisms now measured, all suite-green, all M1-fail:
yield fam-lane / yield shared-slot / yield overlap / convert loose /
convert wraps.  The debt goes to the P-FREEZE package per §51.4.2.
Flag-OFF ≡ parent 576/576 at every hash (a3742b16, fcd56aaf,
99249af2, 084caa52, 3ca9097b).
