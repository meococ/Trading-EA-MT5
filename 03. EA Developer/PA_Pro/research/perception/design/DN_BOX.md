# DN_BOX — congestion boxes (incl. RANGE_OPEN, CONTEXT_RANGE)

A box marks a bounded two-sided congestion — the era when price was
*held* between a defended top and a defended bottom. Not every tight
patch gets one: boxes are the highest-ink object and mostly didactic
(RT1). The drawn rectangle may outlive its buildup era (D9).

## 1. Market mechanism

RT3 §6: a range is a region bounded by **two-sided resting flow** —
take-profit/limit depth at both edges (Osler 2003 mechanism;
Kavajecz & Odders-White 2004: depth peaks *at* technical levels).
Inside, mean-reverting liquidity provision dominates. Edge pokes hit
stop clusters just beyond (Osler's stop-offset asymmetry), so shallow
excursions that close back inside are the *expected* texture, not
violations (tease semantics — spec §3.2). Absorption of an edge
attack shows on bars as repeated rejection wicks with shrinking
follow-through; depth consumption implies the edge *weakens* per
touch (RT3 §4 — touch-count strengthening is FOLKLORE, falsified
for analyst labels in Osler 2000).

## 2. Volman's criteria (RT1 §4.1, §6; Q1 rulings)

- Boxes appear when **congestion or a pullback exists** (RT1 §4.1);
  they are "often didactic" — the live minimum may be only the
  signal line. Per-panel budget ~3 objects total (RT1 §4.4).
- **Buildup vs drawn span (D9):** every golden box whose stated
  height matched did so on the *pre-break* prefix — the drawn right
  edge is how long it was drawn, not containment. Objects carry
  `build_start`/`build_end` (buildup era) distinct from `t0`/`t1`
  (drawn span).
- **Edge = extreme with company:** the most extreme level still
  having ≥2 touches; lone spikes are pokes (validated: 9.15b,
  9.63a, 9.44a marginal case).
- **Straddle = containment:** "straddling 1.26" → the figure lies
  *inside* the box; never center on it (Q1 9.63a ruling).
- **Fixed height honored:** "~13 pips" constrains the edge pair
  jointly (HEIGHT_TEXT check; 9.63a rebuilt to exactly 13.0).
- Edges not moved by ordinary pokes; pre-break re-anchor only on a
  confirmed new alignment (RT1 §6.3).

## 3. Other schools (RT2)

- Wyckoff: trading range with creek/ice edges; adds event phases
  (SPRING/UTAD) — causal but narrative (PRACTITIONER).
- AMT: balance area → edges = value-area high/low; needs volume.
- Classical/Bulkowski: rectangle statistics on equities daily —
  direction supports "contraction precedes expansion," not pip sizes.
- Darvas (RT4 §5.3): box top = high not exceeded for n bars — the
  historical root of the constructive rule; cite, don't copy.
- Convergence: sideways zone bounded by edges; probes beyond edges
  mostly fail; what "confirms" a break differs per school → keep our
  spec close-out + follow-through rule (MEASURE: break-bars).

## 4. Golden measurements (TUNE v2, n=111; Q2 `measure_TUNE`)

- Height: median ≈ 15 pips (≈3×ABR at ABR_med 6.6); stated-height
  objects rebuilt to text within ~1 pip (9.63a 13.0, 9.50a 13.0).
- Stated heights seen: ~13, ~16, ~18, ~20–22 pips — all = pre-break
  range (D9).
- Buildup containment after repair: ~95–100% of buildup closes inside
  (tease wicks allowed); sub-window containment: box may bound a
  contiguous middle run of the stated span (9.56c — build_start
  interior).
- Touch counts at edges: bottom edges 3–22 touches over drawn span;
  min cluster support minPts=2.
- Q2 candidate stats (dedup'd): 3,681 BOX evaluations — 620 born
  (28% drawn), 345 cooldown-vetoed (**40% drawn**), 1,704
  governing-vetoed (31% drawn), 897 route-shadow (28%), 115
  envelope-vetoed (23%). **Gates do not select; they randomly kill.**
- Golden coverage 105/111 = 95% — the universe contains the objects;
  selection is the failure.

## 5. Operational rule — constructive birth, clustered edges, frozen geometry

**Birth.** Spec §3.1 constructive rule retained: a box forms when a
sideways sequence produces a **second touch on the eventual breakout
edge** (Darvas-rooted, spec-native). Required prior state: ≥1
structural pivot pair (θ₂ stream, DN_SWING) alternating sides within
the candidate span.

**Edge placement (RT4 §5.4c).** Bucket-merge clustering on member
extremes *within the buildup window*:
- `eps = max(1 pip, 0.25·ABR)`; `minPts = 2`.
- Top edge = most extreme high-cluster with minPts support; same for
  bottom; isolated-spike exclusion (a wick with no company within eps
  is a poke — D9 rule).
- Height = top − bottom cluster prices; must satisfy
  `h ∈ [~1×ABR, ~5×ABR]` (prior 6–34 pips → express in ABR units,
  MEASURE on TUNE height/ABR histogram).

**Buildup window (D9 formalized).** `build_end` = last bar before
the first close beyond an edge that is never re-entered in-span;
`build_start` = first close inside [lo,hi] (longest contained run
for sub-window cases). Containment measured on closes inside
`[build_start, build_end]`; requirement ≥ ~90% (MEASURE).

**Freeze.** Edges fixed at birth (RT4 §10). Re-anchor only via the
named rule: pre-break tightening when ≥2 new extremes align within
eps inside an edge (RT1 §6.3) — logged `re_anchor` events.

**Death.** Close-out + follow-through (spec): a close beyond an
edge by > tol followed by a bar not re-entering converts the box —
the broken edge becomes a LEVEL_CARRIED source (DN_LEVEL); the box
stops influencing birth decisions but may remain drawn to panel
edge. A "back-and-forth" break (re-entered next bar) demotes to
tease label on the box.

**RANGE_OPEN.** Asia session running min/max 00:00–08:00 CET
(spec); converts to BOX on post-open containment or dies on break.
Thin-range flag ≤ ~10 pips (9.40a 4.6p) → may still be drawn as the
session reference but counts against the budget as a *context*
object, not a signal object. MEASURE: golden RANGE_OPEN heights
(only 8 goldens — include the ~22p 9.47a and ~4.6p 9.40a bounds).

**CONTEXT_RANGE.** One per window at coarse θ₂ scale (20–40 pips
wide), dotted budget; dedupe vs BOX by containment overlap.

## 6. Failure modes

**False positives:**
- `asia_session` route births a 460-min box every day at 08:00 —
  e.g. 9.1a/9.3a/9.4a/9.5a (all ignored; drawn rate 0% across 66
  births). Asia box must only survive when it is the *referenced*
  session range, competing on salience — not auto-drawn.
- Vetoed-but-drawn evidence (Q2): cooldown-vetoed boxes are drawn
  40% of the time — the gate kills real structures (e.g., a second
  box forming right after the first, as in the 9.44→9.45 sequence
  style). Selection must be ranking, not cooldown.
- Envelope-vetoed 23% drawn: near-duplicate boxes where the second
  is genuinely drawn (nested/didactic pairs, e.g. 9.6a inner box).
  NMS must use containment-aware IoU, not a fixed distance veto.

**False negatives:**
- `9.44a#0` "small BOX around the tight 09:45–10:30 congestion
  (~13 pips)" — uncovered by any candidate: tight mid-morning
  congestion, no session anchor. The θ₂-pivot-pair birth must reach
  it (it has ≥2 defended extremes).
- `9.50b#3` "small box ~14:05–14:30" and `9.22a#2` chart-edge
  rectangle ≈1.3320–1.3335 — short boxes at/near panel edges; birth
  scan must not require a full breakout to *evaluate*.
- `9.48b#0` "Asian-box edges to ~07:50/09:10" — box *edges* drawn
  as lines continuing past 08:00; needs the broken-box → LEVEL path
  (DN_LEVEL), not only rectangle birth.
- `9.48a#1` "a new tall box starts at the right edge ~07:45" —
  birth-at-edge objects need partial-span evaluation.

## 7. Tests

**Golden-derived:**
- (a) Coverage ≥95% retained; born→drawn rate becomes a *ranking*
  outcome (target: born ≈ drawn ± budget slack) not a gate artifact.
- (b) Stated-height boxes: |h_drawn − h_stated| ≤ 1.5 pips when text
  gives "~N pips" (regression for 9.63a/9.50a).
- (c) Buildup containment ≥90% on repaired set; `build_end` ≤
  breakout bar for all with stated height.
- (d) Straddle rule: figure inside edges for all "straddling X"
  notes; never centered (regression 9.63a).

**Theory fixtures:**
- (e) Synthetic box: 20 bars oscillating ±5 pips between defended
  extremes → one BOX, edges on the cluster, build_end at break.
- (f) Lone-spike fixture: 19 bars in range + 1 wick 8 pips beyond →
  edge stays on cluster; wick classified tease.
- (g) Sub-window fixture: drift-in congestion (9.56c pattern) →
  build_start interior, not span start.
- (h) Freeze test: post-birth bars never move edges except logged
  re-anchor; prefix-invariance (D7) covers geometry.
- (i) News-window veto: box attempting birth inside 14:30 CET ±15
  min window → suppressed (RT3 P4; DN_TF hard window).
