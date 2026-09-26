# DN_LINE — PATTERN_LINE and CONTEXT_LINE

Drawn lines mark the slope of a defended extreme sequence — rising
support under a climb, falling resistance over a decline. The author
draws them *from* a named bar along the defended side; ink may confirm
or break a tie but never overrides textual direction (Q1 ruling).

## 1. Market mechanism

No direct microstructure study validates drawn trendlines (RT3 §4 —
ex-ante "strength" falsified in Osler 2000). The defensible mechanism
is indirect: a line through confirmed extremes is a **reaction-
function barrier** — the market's marginal rejection price drifting
at a fixed rate as positions roll. It attracts attention because it
is *visible*; the actionable content is the anchored extremes
(DN_SWING) plus the repeated rejection pattern at the line, which is
the same depth-consumption structure as a horizontal edge (RT3 §6).
Steep lines are short-lived momentum legs; flat lines approach
horizontal levels — the slope continuum is real.

## 2. Volman's criteria (RT1 §4.2–4.3, §6; Q1 rulings)

- Lines are drawn **from a named bar** (163 golden lines carry both
  anchor times; 57 name an explicit anchor bar). "A falling line from
  the ~15:45 high" anchors at that high — ray-sweep semantics, not
  symmetric fit (Q1 repair ruling).
- **Anchors bind to the object's own endpoints** — in compound notes
  each leg keeps its own anchors (Q1 9.33b ruling: the rising leg may
  not borrow the falling leg's 09:30 high).
- Slope direction is a hard constraint: rising/falling/"nearly
  flat"/steep classes; flat allows a few pips of drift over the span
  (Q1: ±10 pips per span, not per hour).
- Broken barriers extend rightward as **dashed lines** (RT1 §6.3;
  golden "broken by the 16:00 bar" notes, e.g. 9.44c).
- Barriers are exact lines, not zones (RT1 §6.2) — touch tolerance is
  a rendering/measurement convention (~1–1.5 pips), not a zone.

## 3. Other schools (RT2)

- Classical charting: two-touch minimum, third-touch "validation" —
  the validation claim is FOLKLORE (RT3 §4; no FX evidence for
  touch-count monotonicity).
- Brooks: trendlines are redrawn constantly ("always need adjusting")
  — conflicts with our freeze rule; we take Volman's (redraw only on
  named re-anchor events).
- AMT/Wyckoff: use channels/TR boundaries rather than diagonal lines;
  convergent only on "line = barrier tested repeatedly."
- Lo–Mamaysky–Wang (RT4 §7): patterns = relations among few
  extrema — a line is the minimal such relation (2+ anchors, slope).

## 4. Golden measurements (TUNE v2, n=184 PATTERN_LINE)

- Span: median 85 min, p25 45, p90 224 → drawn lines are *long*
  (hours, not bars).
- Slope: median |slope_per_hr| ≈ 3–10 pips/hr; slope_abr median
  ~1.1 (≈1×ABR per hour); extremes to ±20 p/hr (steep legs).
- Touches: median 6, p75 10 over drawn span (wicks within ~1.5 pips).
- `dist_to_last`: median 6.7 pips — lines are usually drawn near
  (but not at) current price; some stale ones kept (p90 31).
- CONTEXT_LINE (n=8): 3–8 h spans, dotted, session-extreme anchored.
- Q2 candidates: 3,617 evaluated — 846 born (≈31% drawn), 2,455
  vetoed_offline (**≈36% drawn** — veto kills real lines), 279
  merged, 36 stale-vetoed. Drawn-vs-ignored separators: span
  (205 vs 95 min), touches (4.5 vs 3.4), `n_active` (6.4 vs 5.4),
  `fwd_rng_pctile` (0.68 vs 0.55 — analysis-only).

## 5. Operational rule — hull anchors + max-touch select + freeze

**Anchor universe.** Lower hull of confirmed swing lows / upper hull
of swing highs over the θ₂ pivot stream (RT4 §5, §12.3): monotone-
chain append O(1) amortised; on window eviction rebuild O(n). Hull
vertices are the only points that can be least-touch anchors —
excluded: `lone_spike`-flagged pivots (DN_SWING) unless the text/
formation explicitly names them.

**Candidate generation.** Each new confirmed pivot triggers one
evaluation round:
- Candidates = hull edges through the new pivot + tolerance-feasible
  pairs with non-adjacent older hull vertices (bounded lookahead —
  the "line from X" rays).
- Score = touches within tol (~1–1.5 pips; MEASURE) − overshoot
  penalty (max excursion of the *defended side* beyond the line,
  pips) − age penalty beyond span_max.
- Select max score; ties break by longer span then earlier t0.
- Steep legs (|slope| ≥ ~2×ABR/hr, MEASURE) may anchor on θ₁ pivots
  — the "steep rising line" golden cases (9.21b, 9.21c) need the
  finer stream.
- Short lines (10–40 min) allowed when the note-scale formation is
  local (golden has them; today uncovered) — same machinery, shorter
  span gate.

**Freeze & re-anchor.** On ≥2-touch confirm, geometry freezes.
Re-anchor only on the logged rule (≥2 new extremes align within tol
with a *better* score by margin m — hysteresis, RT4 §10). Never
least-squares refit a drawn line.

**Death / conversion.** A close through the line by > tol that is
not re-entered next bar → the line converts to a *broken barrier*
(dashed extension to panel edge; becomes a LEVEL_CARRIED-adjacent
reference — DN_LEVEL). Tease pokes (wick beyond, close back) get
LABEL_TF treatment on the line (DN_TF).

**CONTEXT_LINE.** Same machinery at θ₂ on session-scale window
(3–8 h); at most one per direction per window; dotted budget.
Anchors tie to session extremes (e.g., "the dotted rising line
extended to ~14:40 (~7h)" — 9.23b).

## 6. Failure modes

**False positives:**
- `9.8c` 16:30 swing_line, 420-min span, 7 touches, ignored: the
  route births a line on any late-afternoon pivot pair; under hull
  + max-touch + salience this either wins or doesn't — today it's
  born unconditionally at birth.
- `9.40c` 16:10, `9.55c` 17:00, `9.46a` 08:55: same pattern — long
  late-day lines nobody draws. With a ~3-object budget these lose to
  session-relevant objects *only if* scoring competes globally
  (DN_SALIENCE).
- The 2,455 offline-vetoed candidates are drawn 36% of the time —
  the "offline" gate (line far from price / stale) kills objects the
  author *does* draw (stale-but-drawn exists: `dist_to_last` p90 31).
  Distance must demote, not veto.

**False negatives:**
- `9.11b#1` "a falling line from the ~12:35 high to ~14:30" —
  uncovered; named-bar ray from a θ₂ high, straightforward under the
  new rule.
- `9.21b#1` / `9.21c#0` "a steep rising line ~13:00→~14:10" —
  steep legs need θ₁ anchors (current detector's pivots too coarse).
- `9.19a#4` "a short falling line ~10:15→10:40", `9.17a#2` "small
  falling line at top right from ~10:05" — short/local lines below
  today's span minimums; allowed via the short-line gate.
- `9.5c#0` "a solid rising line under [the 1.3137 top]" — rising
  support *under a level*: compound formation; line anchors on the
  rising lows, level anchors on the flat top (DN_LEVEL sibling rule).
- `9.23b#0` 7-hour CONTEXT_LINE — needs session-scale window, not
  the panel window.

## 7. Tests

**Golden-derived:**
- (a) Hull-vertex recall: ≥90% of golden line anchors are hull
  vertices or within tol of a hull edge (RT4 §12.3 measurement).
- (b) Slope-class match: sign and flat/steep class of chosen
  candidate vs golden ≥ ~90% on covered objects.
- (c) Span distribution of born lines shifts toward golden (median
  born ≈ median golden ±50%); born count collapses toward ~186.
- (d) `dist_to_last` no longer vetoes — stale drawn lines retained
  in golden get candidates ranked, not killed.

**Theory fixtures:**
- (e) Three collinear rising lows + noise → exactly one rising line
  on the three anchors; a fourth off-line low does not move it.
- (f) Ray fixture ("from the 09:45 low"): anchor pinned at named
  extreme; free end sweeps to max touch — regression for the
  anchored-line path (9.6c).
- (g) Broken-line fixture: close through + no re-entry → dashed
  carry; tease poke → LABEL_TF, not death.
- (h) Freeze/hysteresis: challenger beats incumbent only by margin
  m — boundary flicker test at rank boundary.
- (i) Compound-note regression (9.33b): each leg binds its own
  anchors only.
