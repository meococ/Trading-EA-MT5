# Q2 — TUNE measurements + drawn-vs-not-drawn

Inputs: `draft/BOOK2012_TUNE_v2.jsonl` (frozen golden), real M5 bars via
`book_loader`, and the engine's `cand_log` candidate channel (opt-in,
behavior-neutral — 43/43 tests pass with it enabled).

Run: `python measure.py TUNE` → `draft/measure_TUNE.jsonl` (486 golden
rows), `draft/candidates_TUNE.jsonl` (19,385 raw rows → **8,804 unique
day-candidates** after collapsing the same physical evaluation counted
once per overlapping panel run).

## 1. Golden measurements (what Volman draws — DN_* part iv input)

| type | n | key distributions (p50) |
|---|---|---|
| BOX | 111 | height 16p (p10–90: 10–37), span 135min, buildup 65min, ~2.5 touches/edge, ~1.5 pokes, last buildup close 2.7p off an edge |
| PATTERN_LINE | 186 | span ~3.4h, slope p50 ≈ ±20p over the span; see measure_TUNE.jsonl for slope/hr + slope/ABR |
| BRACKET | 85 | span 34min (p10–90: 15–93) |
| LEVEL_CARRIED | 48 | point price + carry span |
| MINI_LEVEL | 32 | point price over a short span |
| RANGE_OPEN | 8 | height ~19p, span ~274min (the Asian range) |
| SQUEEZE | 2 | span ~67min (thin sample) |
| BAR_MARKER | 4 | single bars |

## 2. Candidate universe (unique day-candidates)

| kind | total | born | vetoed / merged / dedup | drawn-rate born | drawn-rate vetoed |
|---|---|---|---|---|---|
| BOX | 3,681 | 620 | governing 1,704 · shadow 897 · cooldown 345 · envelope 115 | 28% | 23–40% |
| PATTERN_LINE | 3,617 | 846 | offline 2,455 · merged 279 · stale 36 · inactionable 1 | 31% | 28–36% |
| BRACKET | 529 | 529 | (vetoes rare) | 8% | — |
| LEVEL_CARRIED | 460 | 460 | dedup fires inside `_spawn_carried` | 4% | — |
| SQUEEZE | 242 | 176 | no_walls 47 · dedup 19 | 0% | 0% |
| RANGE_OPEN | 66 | 66 | — | 0% | — |
| LABEL_TF | 209 | 209 | — | 0% | — |

BOX routes: pullback_end born 334, range_double_top 122,
range_double_bottom 98, asia_session 66.

## 3. Golden coverage (a candidate matched the drawn object)

| type | covered | note |
|---|---|---|
| BOX | 105/111 (95%) | engine finds drawn congestion reliably |
| CONTEXT_RANGE | 6/6 (100%) | |
| CONTEXT_LINE | 8/9 (89%) | |
| PATTERN_LINE | 157/186 (84%) | |
| RANGE_OPEN | 6/8 (75%) | usually covered by the asia_session BOX, not the RANGE_OPEN birth |
| BRACKET | 31/85 (36%) | M/W-only route misses labelled SHS/lead-in formations |
| LEVEL_CARRIED | 11/48 (23%) | only born on box-edge breaks; Volman carries many other sources |
| MINI_LEVEL | 6/32 (19%) | no engine route exists (nearest = LEVEL_CARRIED coincidences) |
| SQUEEZE | 0/2 | tiny sample |
| BAR_MARKER | 0/4 | no engine route (LABEL_TF is a poke mark, not a bar marker) |

## 4. What separates drawn from ignored (born candidates)

**Birth gates do not select drawn structures.** BOX drawn-rate is 28%
born vs 31% vetoed_governing and 40% vetoed_cooldown; for lines,
vetoed_offline (36%) exceeds born (31%). The current gates answer
"is another structure active / too soon?", not "would Volman draw it?".

Features that DO separate (median drawn vs ignored):

| feature | PATTERN_LINE | BOX | LEVEL_CARRIED | BRACKET |
|---|---|---|---|---|
| span/buildup min | 205 vs 95 | 161 vs 93 | — | 35 vs 35 |
| touches | 4.5 vs 3.4 | ~4 vs ~4 edge | — | — |
| abr at birth | 6.4 vs 4.4 | 4.6 vs 5.1 | — | — |
| n_active | 6.4 vs 5.4 | 5.6 vs 5.1 | 6.7 vs 6.8 | — |
| nearest_struct | 1.7 vs 0.9 | ~5 vs ~5 | 0 vs 0 (levels sit ON their source) | — |
| since_birth_min | 15 vs 14 | 33 vs 36 | 16 vs 21 (drawn sooner after prior structure) | — |
| fwd_range_60 | 26.9 vs 20.5 | 22.4 vs 22.9 | 29.9 vs 23.8 | 26.4 vs 21.4 |  ← WITHDRAWN (A4.2)
| fwd_rng_pctile | **0.68 vs 0.55** | 0.62 vs 0.59 | **0.74 vs 0.61** | **0.72 vs 0.56** |  ← WITHDRAWN (A4.2)
| session | drawn spread eu_am/us; ignored pile up in asia | ignored pile up in asia | — | ignored pile up in asia |

**WITHDRAWN (A4.2, Ruling 5b, 2026-09-21):** the `fwd_range_60`,
`fwd_move_60` and `fwd_rng_pctile` rows above measure price movement
AFTER birth on BOOK bars — an outcome-type measurement forbidden by
Addendum 4 A4.2. They are withdrawn as evidence: no DN section and no
DECISIONS entry may cite them as provenance. `measure.py` no longer
computes them (D12). Cause recorded by the Lead: Ruling 2 §2.2.3's
"last structure before the move" wording — a Lead deviation, not the
lane's. The causal correlates remain the intended read: compression,
buildup-against-barrier, span, touches, n_active, session.

Reading (fwd_* rows removed):
- ~~Drawn structures precede movement~~ — withdrawn with the rows.
- **Drawn lines are established**: ~2× the span, one more touch, born in
  higher ABR, embedded in more existing structure (n_active) and close
  to it (nearest_struct) — they are legs of formations, not lone swings.
- **Drawn boxes are longer-lived** (buildup 65→161min drawn span vs 93
  ignored) — the engine births short double-top/bottom ranges Volman
  never marks.
- **Asia session is where ignored candidates concentrate** for every
  type — the rules fire on thin pre-EU structure the author ignores.
- Level/minilevel/bracket/bar-marker coverage gaps (19–36%) say whole
  routes are missing, not just mis-tuned — a Q3/Q4 design item.

## 5. Caveats

- `drawn` matching: time-IoU ≥ 0.25 or any-overlap + edge within 4p for
  spans; point kinds need price within 4p and birth ±90min of the golden
  span. Borderline matches can shift rates a few points; the qualitative
  gaps (coverage, gates-don't-select, fwd_rng_pctile) are too large to
  be matching artefacts.
- fwd_* columns are post-birth analysis labels — WITHDRAWN (A4.2,
  Ruling 5b): outcome-type, removed from `measure.py`; they may not
  feed any rule. The separation they showed must be re-expressed
  through causal correlates only (compression, buildup-at-barrier,
  span, touches, n_active, session).
- Candidates are per-day (deterministic); the same physical structure
  evaluated on two panel windows is deduped by
  (date, kind, birth-minute, route, band).
