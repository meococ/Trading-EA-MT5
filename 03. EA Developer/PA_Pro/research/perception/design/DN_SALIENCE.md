# DN_SALIENCE — ranking, budget, and selection

The Q2 headline result: **the current gates do not select.** Drawn
rates among *vetoed* candidates equal or exceed those among born ones
(box cooldown-vetoed 40% drawn vs born 28%; line offline-vetoed 36%
vs born 31%). Selection must become a causal **ranking layer** over
the whole evaluated universe, with the object budget as a consequence
of scores — not a wall of ad-hoc vetoes.

## 1. Market mechanism

Attention is the scarce resource. RT3: published S/R levels predict
trend interruptions *because* the audience concentrates orders there
(Osler 2000) — a level matters partly because it is *visible*.
Salience ≈ "where latent flow concentrates + how fresh + how close".
Depth-consumption (K&OW mechanism) adds the temporal side: an object
that just consumed its wall is *less* salient than an untested one —
salience decays with touches, does not grow (anti-folklore rule).

## 2. Volman's criteria (RT1 §4.4–4.5)

- **~3 objects per panel, ~9 maximum** — the explicit budget.
- Drawn objects are "a selected subset of considered obstacles" —
  the author evaluates far more than he draws.
- **Room rule:** ~14 pips to the nearest obstacle gates signal
  relevance — distance-to-structure is a first-class salience term
  (≈2×ABR at ABR 6.6; express in ABR units, MEASURE).
- Didactic vs live ink: boxes often exist to teach; the *minimum*
  live object may be a single signal line. The engine must separate
  `context` objects (session range, context lines — dotted budget)
  from `signal` objects (the trade-decision ink) — two sub-budgets.
- Pre-break focus: objects near the decision bar outrank historical
  structure (recency term).

## 3. Other schools (RT2) — mostly absent

No school formalizes object selection; it is the craft gap. The
formal machinery comes from RT4 §9 (below). The one cross-school
signal: every tradition draws *boundaries of the current
compression* — salience concentrates on structure adjacent to live
price, decaying with distance and staleness.

## 4. Golden measurements (TUNE, Q2)

Drawn-vs-ignored separators among *evaluated* candidates:

| feature | drawn | ignored | note |
|---|---|---|---|
| PATTERN_LINE span_min | ~205 | ~95 | length = salience |
| PATTERN_LINE touches | ~4.5 | ~3.4 | defended > visited |
| `n_active` (context density) | ~6.4 | ~5.4 | drawn amid structure |
| `fwd_rng_pctile` | 0.68/0.72 | 0.55/0.56 | **WITHDRAWN (A4.2, Ruling 5b)** — outcome-type label, removed from `measure.py`; never a provenance. The causal correlate to engineer is "near decision point" (compression, buildup-at-barrier), not future range |
| `nearest_struct_pips` | larger | smaller | room-to-obstacle term |
| session | EU/US | Asia-heavy ignored | time-of-day prior |

Also: golden panel object counts cluster ~1–4 (median ~3) — the
budget is a measured distribution, not an aspiration. Born counts
today: boxes 620, lines 846, brackets 529, levels 460, squeezes 176
vs golden 111/186/85/48/2 → over-production factor ~4–6×.

## 5. Operational rule — score → NMS → hysteresis → budget

**Stage 1 — prominence floor (DN_SWING).** Micro-pivots die at
confirm time (`prom < 0.5×ABR`). This alone removes the largest FP
source upstream of any ranking.

**Stage 2 — candidate score.** For every *evaluated* candidate
(born or not — the cand_log universe), compute:

```
score = w1·touches_in_tol          (defended, not visited)
      + w2·span_min / scale        (persistence of the structure)
      + w3·prom(anchors)           (prominence of anchors, DN_SWING)
      + w4·recency(t0 vs now)
      + w5·proximity(dist_to_price / ABR)   (room-rule term — peaks ~1–2×ABR, decays both ways)
      + w6·session_prior(cet_min)          (EU/US > Asia; soft)
      − w7·depth_consumed          (K&OW anti-strength)
      − penalty_per_object          (MDL term, RT4 §9.3)
```

All weights MEASURE-class: fit the separator direction on TUNE via
the drawn/ignored tables (logistic-style inspection — hand-set,
documented, not learned-by-search; D5-style hidden coefficients are
banned). Every term causal (bars ≤ t). `fwd_*` fields are excluded
by construction.

**Stage 3 — non-maximum suppression.** Rank candidates; suppress
any whose footprint (type-family × price band × time span IoU on the
84-bar canvas) overlaps a higher-ranked live object (RT4 §9.4).
Containment-aware: a nested didactic box may coexist with its parent
when golden shows it (9.6a-style) — suppression needs a "nested-
allowed" flag per type pair.

**Stage 4 — rank hysteresis.** An incumbent is displaced only if a
challenger exceeds its score by margin m; minimum dwell bars per
object (RT4 §10). Prevents boundary flicker — geometry committed
once, revised only by named events.

**Stage 5 — budget as consequence.** Emit top-k by score where k
follows the golden count distribution (signal sub-budget ~3,
context sub-budget small; total ≤ ~9 hard ceiling per RT1). If fewer
than ~1–2 signal objects score positive → emit STAND_ASIDE (DN_TF),
never fill the budget with noise.

**Telemetry.** Every evaluated candidate logs score components +
rank outcome into cand_log — the audit channel that made Q2
possible stays the primary observability tool.

## 6. Failure modes

**False positives (over-production, today's disease):**
- `asia_session` boxes: 66 births, 0 drawn — auto-birth without
  ranking. Under score+NMS they compete and lose (Asia session_prior
  + didactic sub-budget).
- `mw_double` brackets (9.27b, 9.36a, 9.14a, 9.60a): 529 births on
  shape alone — relevance gate (proximity of completing pivot) +
  budget.
- `broken_box_edge` levels (9.1a ×3 in one morning): 460 births —
  mechanical source events create *candidates*, ranking decides ink.
- Long late-day lines (9.8c 16:30, 9.40c 16:10): stale span +
  distance → score decays; drawn only if it still bounds live price.

**False negatives (selection that must not over-prune):**
- Cooldown-vetoed boxes drawn 40% of the time — sequential
  congestion (9.44a→9.45a-style) must be able to *replace* or
  coexist by score, not wait out a timer.
- Offline-vetoed lines drawn 36% — `dist_to_last` p90 = 31 pips in
  golden: stale lines stay drawn; distance demotes, never vetoes.
- The 9.63a straddle-box class: near a round number at decision
  time — round-number proximity is a small positive feature
  (RT3 P2 magnet term), not an eligibility rule.

## 7. Tests

**Golden-derived:**
- (a) Object budget: engine objects per panel within golden count
  distribution (median ~3, p90 ≤ ~6); context objects counted
  separately.
- (b) Coverage ≥ Q2 levels (95% box, 84% line) *at the new born
  counts* — selection must not shrink coverage.
- (c) Born-drawn alignment: born set ≈ drawn set (the gap between
  them is the ranking error to minimize on TUNE, without touching
  HOLD).
- (d) Determinism: fixed ordering, no RNG; identical cand_log across
  runs.

**Theory fixtures:**
- (e) Crowded fixture: 8 valid candidates → top-3 by score +
  NMS footprint rules; incumbent displacement needs margin m.
- (f) Quiet fixture: no positive scores → STAND_ASIDE emitted, zero
  ink.
- (g) Flicker fixture: two near-tied candidates alternate in raw
  score → hysteresis keeps the incumbent (no boundary flicker).
- (h) Prefix-invariance (D7) extends to scores: score(t) depends
  only on bars ≤ t.
- (i) Weight documentation test: every weight in params_v1 has a
  provenance tag (`MEASURE:<source>` / `SPEC` / `EVIDENCE`) — CI
  lint over the params file.
