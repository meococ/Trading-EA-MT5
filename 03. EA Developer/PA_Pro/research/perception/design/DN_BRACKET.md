# DN_BRACKET — pattern brackets (M / W / Ww / Mm / SHS)

Brackets annotate a confirmed-pivot *sequence* shaped like a letter —
double tops/bottoms (M/W), squeezed variants (Ww/Mm — small inner
turn), and head-and-shoulders (SHS). 85 golden brackets, coverage
36%; the engine's only route is `mw_double` on equal-extreme pairs.

## 1. Market mechanism

A double top is two attempts at the same latent-depth price: the
first attack consumed part of the TP/limit wall; the second attack
on *consumed* depth either breaks it or fails harder (RT3 §4 —
depth-consumption logic; "second touch weaker, not stronger" is the
mechanism-consistent reading). The middle pivot of an M (or W) is
the interim extreme where flow flipped — the "middle section" the
author marks with MINI_LEVELs. SHS adds a head: one excursion that
*did* get through before failing — evidence the wall is thinner off-
center. These are relations among few extrema (Lo–Mamaysky–Wang,
RT4 §7 — the academic bridge: patterns = extrema relations).

## 2. Volman's criteria (RT1 §4.4; golden census)

- Brackets are **decision-relevant annotations only** (RT1 §4.4):
  the author brackets a formation when its completion is the setup —
  not every equal pair earns ink (529 born vs 85 drawn).
- Letter census in golden: M, W, Ww, Mm (squeezed variants = small
  inner turn within the letter), SHS. The `w`/`m` marks a *minor*
  inner leg — micro-structure inside the major letter.
- Brackets bind to the **formation's own span**; "under the base",
  "above it" resolve against the sibling formation (Q1 sibling-span
  ruling — 9.12b, 9.21c, 9.40b, 9.55b keep truncated drawn spans as
  a documented residual).
- The bracket's middle often becomes a separate MINI_LEVEL
  (9.66a-style ticks; DN_LEVEL formation_extreme route).

## 3. Other schools (RT2)

- Classical: double top/bottom, H&S — the letters are classical;
  Bulkowski stats exist but daily-equities (direction only).
- Wyckoff: same events read as UTAD/Spring inside a TR — compatible
  naming on the same geometry.
- Brooks: "double top pullback" etc. — uses them liberally; we keep
  Volman's sparse usage.
- No school defines the equality tolerance numerically → MEASURE.

## 4. Golden measurements (TUNE v2)

- 85 brackets; uncovered 54 — misses concentrate in: SHS (9.1a#1
  "an SHS bracket above the formation ~04:00–08:00"), Ww/Mm
  variants (9.3b#1 "Ww bracket ~12:20–13:15"), and plain W/M whose
  equal extremes are >today's tol or at unusual separations
  (9.1b#1, 9.2c#2, 9.3a#1, 9.3a#2, 9.3c#2…).
- Q2 born-ignored examples: 9.27b 12:15 mw_double_bottom (135-min
  span), 9.36a 07:10 mw_double_top (135 min, 11 touches), 9.60a
  07:25, 9.14a 06:20 — births on any equal-extreme pair regardless
  of formation quality or relevance.
- From `mw_double` params: equality tol ~2–4 pips; separation 4–28
  bars (RT4 recommendation row) — both need the golden M/W
  separation/tolerance histogram (MEASURE).

## 5. Operational rule — pattern match on pruned pivots

**Input.** The persistence-pruned θ₂ pivot sequence (DN_SWING) —
never raw bars (RT4 §12.7).

**Templates (each a deterministic sequence predicate):**
- `M`: H L H' where |H−H'| ≤ eq_tol, separation s(H,H') ∈ [smin,smax],
  and L is the intervening lowest low (the "middle").
- `W`: mirror.
- `Mm`/`Ww`: the letter whose inner leg is a θ₁-scale turn (minor
  leg flagged) — same template run on the mixed-scale stream with a
  "minor leg" marker.
- `SHS`: L H L' sequence where |L−L'| ≤ shoulder_tol and H exceeds
  both by ≥ head_min (≈1×ABR, MEASURE); neckline = line through the
  intervening lows → often co-drawn (DN_LINE short-line path).
- All spans bounded [smin=4 bars? — MEASURE; golden separations set
  it; RT4 prior 4–28 bars] — equality tol prior 2–4 pips ≈ 0.4–0.6×
  ABR (normalize in ABR units).

**Sibling binding.** A bracket "under the base/above it" takes its
span from the referenced formation's build window when text says so
(convention from Q1 repair; engine-side: brackets may inherit span
from the sibling object they annotate).

**Salience gate (feeds DN_SALIENCE).** A bracket is emitted only
when decision-relevant: its completing pivot is within ~1–2×ABR of
current price, or its middle/edge is a live barrier now. Historical
brackets (completed and left behind) demote hard.

**Output.** Span marker + letter label; optional neckline/middle
MINI_LEVEL via DN_LEVEL formation_extreme.

## 6. Failure modes

**False positives:**
- `9.36a` 07:10 mw_double_top (11 touches, ignored): equal-extreme
  pair births a bracket with no relevance check — most of 529.
- `9.14a` 06:20 mw_double_bottom: early-Asia equal lows inside the
  overnight range — a "W" by shape, not by meaning (the θ₂ stream +
  salience relevance gate suppress).
- Nested duplicates: two pairs sharing a pivot birth two brackets —
  dedupe by shared anchors (NMS on pivot-id footprint).

**False negatives:**
- `9.1a#1` SHS ~04:00–08:00: no SHS template at all today.
- `9.3b#1` Ww / `9.3c#2` W and Mm-type variants: mixed-scale inner
  legs need the θ₁-minor-leg marker — single-scale matching misses
  them.
- `9.1b#1` M ~10:20–11:30, `9.2c#2` W ~17:15–18:30: plain letters
  missed when equality/sep sits just outside today's constants —
  ABR-normalized tolerances widen where golden allows.
- Brackets spanning a session boundary (SHS 04:00–08:00) need pivot
  memory across the session edge — no window truncation.

## 7. Tests

**Golden-derived:**
- (a) Coverage ≥80% of the 85; per-letter recall reported (M, W,
  Ww, Mm, SHS).
- (b) Equal-extreme tolerance histogram → sets eq_tol; separation
  histogram → sets [smin,smax]; both in ABR units.
- (c) Born count collapses 529 → O(100) via relevance gate while
  coverage holds.

**Theory fixtures:**
- (d) Clean M fixture: two equal highs + middle low → one bracket,
  correct span, middle emits MINI_LEVEL.
- (e) SHS fixture: three peaks, middle head → SHS + neckline
  candidate line.
- (f) Ww fixture: outer W with a minor inner turn → letter variant
  recognized, not two overlapping brackets.
- (g) Near-miss fixture: equal highs separated 200 bars, middle
  forgotten → no bracket (decay/relevance).
- (h) Determinism: same pivot stream → same bracket set, fixed
  ordering (price then birth bar).
