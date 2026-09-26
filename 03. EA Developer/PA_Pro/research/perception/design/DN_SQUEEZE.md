# DN_SQUEEZE — compression between walls

A squeeze is the visible narrowing of price between two barriers —
the "coiling" the author marks with short inner lines. Golden n=2;
today the engine births 176 squeezes and draws ~1% of what it
evaluates. The object is rare; the regime (contraction before
expansion) is common and belongs to context state, not ink.

## 1. Market mechanism

Contraction before expansion is the one cross-school convergence
(RT2 §3): Wyckoff's "cause building," classical volatility cycles,
AMT's balance→imbalance. Mechanism (RT3): as a level's TP/limit
depth is consumed and stops accumulate just beyond, the executable
corridor narrows; the eventual traverse detonates stored stop flow
(Osler 2005 post-crossing speed excess — fat-tailed, mean small).
A squeeze therefore marks *stored energy*, which is why the author
draws it at decision points, not everywhere it technically exists.

## 2. Volman's criteria (RT1 §4.3; golden)

- Squeeze marks appear **inside named walls** — "a short inner
  squeeze line ~07:40–08:30" (9.33a), "converging squeeze lines at
  the top edge ~06:50–08:15" (9.39a). The walls are existing objects
  (box edges, lines); the squeeze is the narrowing *between* them.
- It is an annotation of *tightening*, i.e., successive highs/lows
  converge toward an apex near the decision bar.
- The author draws it rarely and only where a break is imminent or
  decision-relevant (RT1: pattern brackets/squeeze ink only when
  decision-relevant).

## 3. Other schools (RT2)

- Classical: triangles/pennants — same object; Bulkowski stats are
  daily equities, direction only.
- Brooks: "tight trading range" / wedge variants — he draws them
  liberally; Volman is far sparser (a real disagreement → follow
  Volman + golden rarity).
- AMT: balance = the squeeze's area form; breakout = initiative
  buying/selling entering. Convergent on mechanism, divergent on
  ink budget.

## 4. Golden measurements (TUNE v2, n=2)

- 9.33a#1: short inner squeeze line ~07:40–08:30 (50 min) inside a
  larger box.
- 9.39a#1: converging squeeze lines at top edge ~06:50–08:15
  (85 min), at a box edge.
- Q2: 176 born via `small_bars_between_walls` (small-bars predicate
  only) — drawn ≈ 0/176: the predicate fires everywhere in Asia
  (9.1a 03:15, 06:45; 9.1b 13:15; 9.2b 11:20 — all ignored).
- Analysis label worth keeping: golden squeezes sit at high
  `fwd_rng_pctile` (the expansion half of the mechanism) —
  analysis-only.

## 5. Operational rule — predicate + named walls + apex proximity

**Birth predicate (spec §3.x, tightened):**
1. ≥2–3 consecutive bars with range ≤ 0.8·ABR (spec-grounded
   predicate, RT4 §5.1) — MEASURE the ratio on golden squeeze bars
   vs ambient (RT4 §12.6).
2. **Two named walls required:** an upper and a lower *existing
   object* (box edges, pattern lines, levels) within ~2×ABR of
   current price, bracketing it. The Asia auto-squeeze (no walls)
   dies here.
3. **Narrowing:** the gap between walls' evaluations at bar t shrinks
   over the squeeze span — gap_t1 ≤ ~0.6 × gap_t0 (RT4; MEASURE on
   the 2 goldens + ambient candidates).
4. **Apex proximity:** the convergence point lands within ~10–15
   bars of now (decision-relevance gate, RT1).

**Geometry.** Short line(s) along the squeeze's own micro-extremes
(hull over θ₁ pivots inside the window) or a bracket span when the
author drew lines — golden shows *lines*, so render as short
PATTERN_LINE-class ink flagged `squeeze`.

**Death.** The traverse of either wall ends the squeeze (expansion
arrived); no persistence needed.

## 6. Failure modes

**False positives:**
- `9.1a` 03:15 & 06:45, `9.1b` 13:15, `9.2b` 11:20 — small-bars
  births inside flat tape with no walls: 176 born, ~0 drawn. The
  named-walls requirement is the fix.
- Predicate-only contraction inside an already-broken range — a
  squeeze needs *live* walls (unbroken edges).
- Multiple overlapping squeeze births on consecutive bars — dedupe
  to one per wall-pair per window.

**False negatives:**
- `9.33a#1` (50-min inner squeeze): needs θ₁ micro-structure inside
  a live box — uncovered today.
- `9.39a#1` converging lines at top edge: the walls are a box edge +
  a rising line — requires the walls to be *different* object types
  (current predicate only sees bar ranges).
- Silent squeezes: golden shows squeezes drawn *retrospectively* at
  the break bar in some panels — allow a post-hoc annotation path
  (draw at break confirmation, anchored back over the squeeze span)
  — flagged EXPERIMENTAL, validated on golden only.

## 7. Tests

**Golden-derived:**
- (a) Both golden squeezes get candidates under the new rule.
- (b) Born count collapses 176 → O(10s); born drawn-rate target
  ≫ current ~0%.
- (c) Wall requirement: every born squeeze references two live
  objects in telemetry.

**Theory fixtures:**
- (d) Synthetic coil between a box top and a rising line → squeeze
  born near apex, dies on traverse.
- (e) Flat-tape-without-walls fixture → zero squeezes (the Asia FP
  pattern).
- (f) ABR-normalized bar-range predicate verified causal (uses only
  bars ≤ t).
