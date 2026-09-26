# DN_SWING — confirmed pivots / directional-change skeleton

Every object the engine draws anchors on confirmed swing extremes.
Today the swing layer is `params.swing.confirm_pullback` (a raw-pip
retrace) fed into ad-hoc pivots; it is the source of the micro-pivot
flood and, downstream, of the 620 born-vs-111-drawn box over-production.
This note specifies the replacement.

## 1. Market mechanism

An extremum is drawn — not merely visited — when the market reverses
far enough that position-holders treat the extreme as a reference
("that was the high"). RT3 §3–4: reversal/interruption probability
rises near round numbers and published levels because take-profit
depth sits at the level and stop depth sits behind it (Osler 2003);
the *depth-consumption* view (Kavajecz & Odders-White 2004 mechanism)
says each touch executes part of the resting book. For a pivot
detector the implication is only this: a swing extreme matters when
the retracement is large enough to have executed meaningful
counter-flow — i.e., a fraction of prevailing volatility, not a fixed
pip count. [EVIDENCE for direction; magnitude = our measurement]

## 2. Volman's criteria (RT1 §4.2, §6, §9)

- RT1 §4.2: the author draws on extremes that *held* — "the area
  around the earlier swing high … a level price respected" (p.~approx
  refs in RT1 §9 table). A lone spike is a "poke," not an edge —
  edges need **company** (validated in Q1: 9.15b ceiling, 9.63a
  shelf, D9/D11).
- RT1 §6.2–6.3: barriers are *exact* lines; an extreme that is poked
  but not broken stays the edge ("edges are not moved by ordinary
  pokes"; pre-break tightening allowed only on a confirmed new
  alignment — p. 2012 chapter refs in RT1 §9).
- The author never states a pivot threshold numerically → this is a
  `MEASURE` parameter, not a spec constant (RT1 §9 row "pullback
  confirmation depth").

## 3. Other schools (RT2)

- Brooks: swing = "major" vs "minor" by prominence, never
  parameterized (PRACTITIONER).
- Wyckoff: pivots are events in an accumulation/distribution
  narrative — causal but human-scale (PRACTITIONER).
- AMT/Market Profile: extremes = value-area edges; requires volume
  we do not have — not directly portable.
- Convergence across schools: *the extreme that matters is the one
  that was defended* — supports a retrace-depth (DC) definition over
  bar-count definitions.

## 4. Golden measurements (TUNE, Q2 `measure_TUNE` + `Q2_MEASUREMENTS.md`)

- Golden PATTERN_LINE anchors: median span 85 min, p25 45, p90 224;
  slope |per-hr| median ~3–10 p/hr.
- Golden BOX heights: ~15 pips median ≈ 3×ABR (ABR median 6.6 pips
  in panels) → the *drawn* scale is ≈2–3×ABR.
- Golden double-top equality tolerances (BRACKET notes, DN_BRACKET):
  ~2–4 pips ≈ 0.4×ABR.
- Q2 candidate evidence: drawn candidates sit at larger
  `nearest_struct_pips` and inside denser `n_active` contexts —
  consistent with "prominent extreme" rather than "any extreme".

## 5. Operational rule — DC state machine + persistence pruning

**Detector.** Replace the current pivot scan with a two-threshold
directional-change (DC) state machine (RT4 §2.3, §12.1):

- Track running extreme (wick) while in an up/down leg; a leg ends
  and a pivot *confirms* when price retraces ≥ θ from the extreme.
- Two nested thresholds on the same tick stream:
  - θ₁ = k₁·ABR, k₁ ≈ 0.8 — *micro* stream, feeds MINI_LEVEL,
    SQUEEZE, bracket inner structure.
  - θ₂ = k₂·ABR, k₂ ≈ 2–3 — *structural* stream, feeds BOX edges,
    PATTERN_LINE anchors, CONTEXT_*.
- ABR = mean M5 bar range, window 20 (existing `self.abr`).
- Confirmation on *close* retracing θ vs *wick* retracing θ: A/B on
  TUNE (RT4 flags the tick-vs-close lag trade-off; default = wick for
  fidelity, measured).
- Each pivot carries: `t_ext` (bar of the extreme), `t_conf` (bar of
  confirmation), `price`, `dir`, `θ`, `prom` (see below).
  `t_conf − t_ext` = `confirm_lag_bars` logged in telemetry (RT4 §12.10).

**Persistence pruning (hierarchy without a second detector).**
Maintain prominence-so-far over the alternating pivot sequence
(RT4 §9.1 — merge-tree/union-find, amortised O(α(n))):
`prom(pivot)` = height above the nearest opposite extreme that would
merge it with a dominating swing. Kill any θ₁-pivot with
`prom < pmin ≈ 0.5×ABR` at confirm time. The θ₂ set is derived from
θ₁ by the persistence floor, guaranteeing the coarse set is a strict
subset — the two scales can never disagree.

**Parameters — all MEASURE-class:**

| param | prior | provenance |
|---|---|---|
| k₁ (micro θ) | 0.8×ABR | RT4 §12.1 prior; set so golden micro-anchors (MINI_LEVEL spans, bracket inner turns) survive — TUNE A/B |
| k₂ (structural θ) | 2–3×ABR | RT4 §6 (invert count law: 4–8 DC events per 84-bar window); check vs golden leg sizes — keep ~90% of golden anchor legs, kill micro-pivots |
| pmin (persistence floor) | 0.5×ABR | RT4 §9.1; pick at precision/recall knee on "is this pivot a golden anchor" |
| confirm mode | wick-retrace | A/B vs close-retrace on TUNE lag/quality |
| inter-DC scaling | ~θ^1.9 | sanity check on our feed (RT4 §11: tick-law exponent may not transfer to bars) |

**Death/aging.** Pivots never die, but consumers weight by recency;
a structural pivot is *superseded* (for anchor purposes) when a same-
direction pivot with equal-or-higher prominence confirms.

## 6. Failure modes

**False positives (drawn, shouldn't be):**
- `9.8c#0`-type FP: a 420-min swing line born at 16:30 off two
  ordinary afternoon pivots — under DC θ₂ + prominence, ordinary
  afternoon wiggles never confirm (root cause of PATTERN_LINE
  over-production: 846 born vs 186 drawn).
- `9.46a` 08:55 swing_line (420 min, 3 touches, ignored): a slow
  drift produces only low-prominence pivots; today it still births a
  line.
- `9.40a` thin Asian range: with θ in ABR units, a 4.6-pip Asia tape
  cannot produce θ₂ events → no structure (correct: Volman draws
  the *range box*, not its micro-wiggles).
- Spike falsification: a 15:15-type news spike (9.15b) currently can
  confirm a pivot that becomes an anchor → with company-rule edge
  selection downstream, a lone spike stays a poke, not an edge.

**False negatives (missed draws):**
- Golden `9.21c#0` "a steep rising line ~13:00→~14:10" missed today:
  a steep leg has deep retraces at each pause; θ₂ may confirm the
  *pauses* as pivots → mitigate: candidate lines may use θ₁ pivots
  when the text-scale slope is steep (|slope| ≥ ~2×ABR/hr) —
  measurement gate on TUNE.
- Golden `9.23b#0` 7-hour CONTEXT_LINE: needs pivots older than any
  rolling window → structural pivots persist for the session, not a
  fixed window.
- `9.5c#0` "a short solid top at ≈1.3137": a top that held for ~50
  min on ≤1-pip touch spacing — θ₂ may never confirm the *reverse*
  if the drift is slow → level objects must also accept
  cluster-detected extremes (DN_LEVEL), not only DC pivots.

## 7. Tests

**Golden-derived (TUNE):**
- (a) Leg-size calibration: ≥90% of golden PATTERN_LINE anchor legs
  (consecutive anchors per repaired object) have ≥θ₂ displacement.
- (b) Micro-suppression: θ₂ pivot count per golden panel ≤ ~8
  (spec's ~3-object budget needs few anchors).
- (c) Confirm-lag distribution logged; median ≤ ~15 bars at k₂.
- (d) `confirm_lag_bars` in telemetry for every pivot.

**Theory fixtures:**
- (e) Zigzag synthetic: exact pivots at known bars; detector
  confirms each within θ tolerance; no extra pivots in flat drift.
- (f) Spike fixture: single 30-pip wick, retrace < θ → no pivot;
  retrace ≥ θ → pivot at the spike bar, flagged `lone_spike`.
- (g) Prefix-invariance extension (D7): pivot set on bars[0:n]
  identical for all n ≥ t_conf.
- (h) Determinism: two runs → identical (t_ext, t_conf, price, prom)
  tuples.
- (i) Hierarchy: θ₂-pivot set ⊆ persistence-filtered θ₁ set, exact
  (not approximate) by construction.
