# BOX_RESEARCH — C-round 3 (R56 §56.4)

Lane: BOX-LAB.  Parent: `ee2cbf1202db47b6` (STABLE 9acaa206 + K7 + K8 +
K9).  All numbers TUNE only, official eval path (`eval_v2`,
`recall_at_k`), pickles `c1r_p_base@ee2cbf12`.

**Executive summary (for the Owner report):** the machine does not
fail at finding the right box geometry — a matching candidate exists
for 57/119 goldens and the level stream already contains both golden
edges for 82/119.  It fails at *choosing the live one*: the pick at τ
is a stale `structural_envelope` in 83/107 misses while the right cand
dies pre-birth.  The separating signal is causal and confirmed under
the §57.1 nulls — **liveness**: the right box is the candidate whose
band still contains close[τ] (or lies within 0.5 ABR), touched most
recently, ending nearest τ.  Every fixed generation rule is falsified
(segmentation 28/119 and 15/119; level-pair selection ≤10/119 across 5
rules; emission-time gating saturated at 97–99%).  The surviving
formulation is selection-side — a **liveness-scoped, liveness-ranked
birth slot** (spec in REQUESTS.md; A3 ranker escalated).

---

## Ch. R1 — Evidence: why the author draws the box he draws

*(due 17:30Z — opening section taken from BOX_GAP_DOSSIER.md)*

### R1.0 The funnel

```
119  scorable BOX goldens
107  causally reachable at tau   (12 sit on no causal edge pair)
 57  covered by an edge-matching proposal
 10  hit at rank-1 (box@1)
 47  covered but missed — all pre-birth, 0 born-and-missed
```

Missed buckets: `below_min_score` 16 | `outranked` 11 (budget
displacement) | `log_only` 10 (wick variants never pooled) |
`rate_limited` 8 | `expired` 2.

### R1.1 The author-vs-engine table

Full table: `boxlab/c1_runs/r1_table.csv` (119 rows; golden
edges/span, engine box@1 pick + score/route/birth, best matching cand +
every score term, bucket).

Who holds box@1 at τ on the 107 misses:

| pick route | n |
|---|---:|
| `structural_envelope` | **83** |
| `cluster_range` | 17 |
| `congestion_scan` | 11 |
| `asia_range` | 6 |

Median wrong-pick score **7.32** — the incumbent ink is genuinely
strong, not gate noise.  Golden median height 16.0 p vs pick median
17.1 p — the engine's picks are *not* thin close-bands; they are broad
envelopes.  **The engine's default "box" is a stale session envelope;
the author's box is the current episode.**

### R1.2 The 30 renders (`boxlab/r_renders/`)

green = golden (build span), red = engine pick, blue = best matching
cand, dashed gray = τ (post-τ candles dimmed).

| file | what the author sees that the engine does not |
|---|---|
| 9.2b_g0_hit | Sideways block straddling 1.325 boxed whole; post-τ collapse — the box is the pre-break buildup zone. |
| 9.4b_g0_hit | The whole 4h range around 1.3131–1.3150; not the tightest band but the episode. |
| 9.6a_g0_hit | Large morning rectangle ≈18 pips — full Asian-EU transition block. |
| 9.14a_g0_hit | Parallel-line zone as a box; the band the next leg launched from. |
| 9.15b_g3_hit | W-bracket congestion; the box is the pattern's container. |
| 9.25b_g0_hit | 14-pip block under a falling EMA — episode, not close-hug. |
| 9.36b_g0_hit | The closed morning range 07:45–10:10 as one unit. |
| 9.39a_g0_hit | Overnight 11-pip range, 7.5 h long. |
| 9.45b_g0_hit | The base on 1.315 — a round-number base zone. |
| 9.48b_g1_hit | ~1.2990–1.3020 — the 30-pip block straddling 1.30. |
| 9.48a_g2_log_only | Absorption after a spike: the box **includes the spike extreme**; only a wick-variant cand reached it. |
| 9.27a_g0_log_only | Rectangle "to the right edge" — still-live box; engine cand pool has nothing tall enough. |
| 9.16c_g2_rate_limited | Afternoon rectangle 1.3188–1.3202; right cand existed, slot spent. |
| 9.32b_g1_outranked | 16-pip mid-day block; right geometry lost the budget fight. |
| 9.24b_g0_expired | The dotted range closed 13:40; cand expired unresolved. |
| 9.52b_g0_outranked | "box closed ~11:25" — author closes it *manually*; engine never does. |
| 9.43b_g0_below_min_score | **"the first sideways block after a leg is boxed immediately, before it resolves"** — author's own lesson; cand only covered the left half. |
| 9.56c_g0_rate_limited | The 8-pip low base after the drop; right cand sc 3.00, slot spent. |
| 9.47b_g0_outranked | Asian box to ~10:50; author's box excludes the early noise, engine cand started earlier. |
| 9.53b_g0_outranked | "box to ~11:40" — the live morning block. |
| 9.13a_g0_no_coverage | Asia-into-EU ~7 h rectangle; the scored buildup is only its last segment. |
| 9.60b_g2_no_coverage | Mid-morning episode; no cand at its edges. |
| 9.30c_g1_no_coverage | Afternoon block 1.3119–1.3131. |
| 9.54a_g0_no_coverage | **The whole day's range** ~02:00–09:10 (~22 p) — engine has no day-envelope proposal at these edges. |
| 9.56b_g0_no_coverage | "Asian box closed ~10:10". |
| 9.7a_g2_no_coverage | 11-pip block with a W bracket under it — the box is the bracket's container. |
| 9.12c_g0_no_coverage | Evening rectangle 16:35–18:00. |
| 9.60b_g4_no_coverage | "small TL inside the box" — container around a trendline move. |
| 9.50c_g0_no_coverage | Post-drop base ~12 p — the run is too short for the engine's min-bars containment gate. |
| 9.20b_g1_no_coverage | Mid-trend plateau ~15 p — sideways block between two legs. |

Cross-render reading: the author's box = **the whole sideways episode,
edges at the episode's wick/spike extremes, drawn before resolution and
kept live past the break**.  Engine candidates hug closes, start late,
and die unborn; the object that survives to rank-1 is an aged
structural envelope.

### R1.3 The book (via book notes `EA_VolmanPA/PLAN/book/notes/`)

- "Hộp bao (box): công cụ được ưa dùng hơn một đường nằm ngang" — the
  box is the preferred tool over a flat line (ch02:59).
- Range signal: EMA25 flat "bị giá xuyên lên xuống mà không đi theo hẳn
  bên nào"; box drawn around the zone, width:length ≈ 1:3 (ch05:25,
  tr. 156).
- Rectangle = multi-hour sideways zone, readable as extended M or flat
  H&S (ch06:36).
- Edges connect local tops/bottoms and are "luôn được điều chỉnh lại"
  — always readjusted as new price action appears (ch07:26).
- Buildup = "áp lực trước phá vỡ" — price pressing a threshold until
  one side yields (ch01:41); the buildup sits "ngay tại đường biên" —
  right at the boundary, the tighter the better (ch01:99–101).

Setup tags from the goldens' own `clause` field (111 box goldens,
multi-tag allowed): `round_anchor` 35 (32%) | `congestion` 12 |
`inner_small` 11 | `kept_past` 11 ("kept ~1.5h past the break", "to the
right edge") | `bracket_inside` 10 | `asia_range` 9 | `base` 7 |
`closed` 5 | `ema_ctx` 3.

**H1 supported by the text:** the box marks the zone that matters for
the trade *now* — the live buildup/episode, kept as reference past the
break.

### R1.4 Hypothesis table (`r1_hyp.py`)

107 pairs (missed golden vs engine's wrong pick in the same panel).
Null: golden label shuffled among the panel's candidate rectangles,
200 draws; keep rows beating null p95.

| id | feature (higher = author-like) | obs | null p95 | verdict |
|---|---|---:|---:|---|
| H1 | last-10 closes pressing an edge | +0.078 | 0.062 | KEEP (thin) |
| H2 | flat EMA25 through the box | −3.13 | −1.43 | **DROP — reversed**: author boxes sit on sloping-EMA transitions |
| H3 | wick rejections at edges, last 15 bars | +1.08 | 1.00 | KEEP (thin) |
| H4 | prior-leg amplitude (40 bars, ABR) | +0.59 | 0.465 | **KEEP** |
| H5 | drawn span end vs τ (drawn past τ > 0) | **+14.4** | −35.7 | **KEEP — strongest**: author boxes are live at τ, drawn past it ~14 bars; random cands end ~40 bars early |
| H6 | height / day range so far | +0.014 | −0.026 | KEEP (thin) |
| H7 | bar-overlap ratio inside box | +0.29 | 0.385 | DROP (goldens overlap *less* — they're taller) |
| H8 | edges on wick tips of own span | +0.11 | 1.47 | DROP — all proposals sit near wick tips; not separating |
| H9 | 50-pip round inside box | +0.12 | 0.16 | DROP (thin, rounds are dense) |
| H10 | height in pips | +1.19 | −1.10 | KEEP |

Survivors: **H5 (drawn-past-τ/live episode), H4 (prior leg), H10
(taller), H6, H1, H3 (thin)**.  H5 is not circular — it uses the
*drawn* t1, not build_end (τ ≡ build_end by definition).

### R1.4b — R57 §57.1 causal re-test (`r57_causal.py` → `c1_runs/r57_causal.txt`)

H5-drawn is hindsight (t1 is post-facto).  Re-tested causally on
`r_dataset/rows.csv` (8975 rows / 115 cells), two designs:
**PAIRED** (right cand − wrong engine pick, 12 cells) and
**VS-REST** (right-set − rest mean, 67 cells), each vs a 200-draw
within-cell label-shuffle null; the three price-position features also
vs a band-overlap-density-weighted null.  X = 0.5 ABR stated before
measurement.

| feature | PAIRED obs / p95 | VS-REST obs / p95 | dens-null p95 | verdict |
|---|---:|---:|---:|---|
| px_in_box | .455 / .250 | .305 / .045 | .066 | **KEEP** |
| close_at_box (in-box or ≤0.5 ABR of edge) | .547 / .167 | .338 / .051 | .055 | **KEEP — strongest causal** |
| −dist_close_edge_abr | 2.206 / 1.347 | 1.283 / .215 | .235 | **KEEP** |
| −recency_bars (fresh t1) | 66.4 / 43.3 | 30.0 / 4.27 | — | **KEEP** |
| −bars_since_touch | 22.1 / 14.9 | 12.2 / 2.21 | — | **KEEP** |
| prior_leg_abr (H4c) | .272 / .818 drop | .243 / .117 | — | thin KEEP (vs-rest only) |
| h_rel_day (H6c) | .006 / .059 drop | .031 / .017 | — | thin KEEP |
| h_abr (H10c) | .022 / .474 drop | .158 / .154 | — | razor KEEP |
| pressure (H1c) | — | — | — | drop (sparse) |
| probes (H3c) | −3.11 / 0 | −2.09 / .357 | — | **drop — reversed** |
| ema_slope_span (H2c) | drop | drop | — | dead stays dead |
| overlap_ratio (H7c) | 0 | 0 | — | dead stays dead |

**H5-causal verdict: the liveness cluster is the real signal.**  The
right box is the candidate that close[τ] sits inside or within 0.5 ABR
of, that was touched most recently, and whose span ends nearest τ.
Only the causal form may enter A1–A3 (§57.1) — it does, and it is the
strongest surviving family.

### R1.5 Synthesis — what R2 must encode

1. **Episode, not band.** The author's box = the whole sideways
   episode as one unit — edges at the episode's wick/spike extremes
   ("absorption box includes the spike extreme"), not a close-hugging
   run.  ⇒ segmentation-first (A2) is the natural formulation.
2. **Live and kept.** Golden spans are drawn past τ (+14 bars median
   effect); "kept past the break", "to the right edge", "first
   sideways block after a leg".  The box is the *current* reference —
   selection should prefer the live episode, not the strongest old
   ink.  ⇒ context-first selection (A1).
3. **The incumbent is the wrong object class.** 83/107 wrong picks are
   `structural_envelope` — broad stale session envelopes outliving
   their episodes.  No score term rescues this; the *object that
   represents "the current box"* is a different concept.
4. Legs frame boxes (H4): the first sideways block after a leg is the
   box.  ⇒ segmentation boundary = leg end.
5. The 12 unreachable goldens stand: no causal edge pair at τ.

---

## Ch. R2 — Approaches (due 19:30Z)

Four formulations, none is "add a term to `score()`".  Rules and
parameters are stated before any measurement (§3.6).  Literature:
Darvas box state machine (thepatternsite.com/Darvas.html;
LinnSoft DBOX); Wyckoff trading range — Phase-A edges set by the
climax/automatic-rally extremes, refined by secondary tests
(tradingwyckoff.com; robertbrain.com Wyckoff anatomy).

### A1. Context-first selection (selection-side — REQUESTS.md spec)

**Rule.** At every birth decision, restrict the birth slot to
candidates whose episode is *current*: `t1 >= now - K` (K = 30 bars)
or span containing now.  Older candidates wait.  Among current
candidates the existing score order stands — this is a *scope*
restriction, not a reweight.
**Params:** K = 30.
**Falsify:** replay — for the 47 covered-missed goldens, was the right
cand proposed within K of τ?  If the right cands are also old, A1 is
empty.  From the anatomy: right cands are proposed during the buildup
(close to τ), so most qualify — the check still runs.
**Expected (from R1):** converts part of `outranked` 11 +
`rate_limited` 8 + `expired` 2 → ceiling ≈ +6–10 box@1 if the slot
goes to the current-episode cand.  Cost: salience.py edit — belongs to
build lane; I write the spec.

**A1 measured ceiling (r_dataset, 15:45Z):** on the 12 paired cells
the engine's pick is live (`close_at_box`) in only **3/12** while a
right cand is live in **10/12** — the asymmetry is real and causal.
But a scope-only argmax on live cands flips just **2/12** to a hit:
inside the live pool the right cand still loses `score_last` to wrong
live rivals.  ⇒ scope narrows the pool; a liveness-aware *ranking*
(A3) orders it.  The two are complementary, not substitutes.

### A2. Segmentation-first: episode state machine (generation-side —
`boxes.py` flagged route `episode_box`)

**Rule (Darvas-flavoured, adapted to M1 + "first sideways block after
a leg").**  Two tape states per day:
- `LEG` while |c[i] − c[i−L]| ≥ θ·abr (θ = 1.5, L = 20 bars).
- When the condition fails for 5 consecutive bars → `CONG` opens at
  the first failing bar; box seeded at the running wick extremes of
  the episode.
- In `CONG`: **edges readjust in place to new wick extremes** (the
  author's "always readjusted", ch07).  One proposal per episode —
  the live box is re-emitted, not multiplied.
- `CONG` ends when price closes ≥ 2 pips beyond an edge (break) → the
  box closes as a completed episode.  A box whose span reaches τ is
  "live" — matching H5, the strongest surviving signal (+14.4 bars
  drawn past τ).
**Params:** θ = 1.5, L = 20, min_cong = 8 bars, break_tol = 2 p.
**Falsify (offline, before any engine run):** replay episodes per
panel; do golden edges fall within tol of the episode's running
extremes, and does the episode contain τ?  If < 30% of the 62
no-coverage goldens gain a covering episode → dead.
**Expected:** coverage ceiling is the reachable 107; episode extremes
≈ swing extremes, which the null study showed carry author edges
(pivots .708 vs p95 .585).  Conversion risk: episode boxes are taller
→ `box_rank` may still starve them; the A/B measures that.

### A3. Small learned ranker (escalation path — §56.4)

**Rule.** Rank pooled BOX cands at birth by a logistic score on ≤ 4
features drawn only from null-beating hypotheses.  Fit by
deterministic numpy logistic regression; leave-one-day-out CV;
within-cell shuffle-label control.  The reported score is the CV
number.
**Status (post-R58 §58.1):** `r3_fit.py` + `r_dataset/rows.csv` are
staged; `ESCALATE: A3 ready` logged.  **The numbers below came from
runs on the Owner's PC — a wall breach (R58 §58.1); they are NOT
evidence until the Lead reproduces them in the cloud.**  Kept here as
the hypothesis the cloud fit will confirm or kill.

| model | features | CV cell@1 | shuffle p95 | verdict |
|---|---|---:|---:|---|
| score_last baseline | — | 5/67 = .075 | — | — |
| box_rank baseline | — | 4/67 = .060 | — | — |
| liveness4 | −dist_edge, close_at_box, −recency, −bars_since_touch | **18/67 = .269** | .254 | PASS* |
| liveness3 | first three | 18/67 = .269 | .254 | PASS* |
| keep4+prior_leg | swap −touch → prior_leg | 18/67 = .269 | .254 | PASS* |
| liveness4, pooled-only rows | same | **18/57 = .316** | .298 | PASS* |

\* *PC-run numbers — pending Lead's cloud reproduction (R58 §58.1).*

≈ **3.6×** the engine's within-cell discrimination; mean best-right
rank-frac .140 vs .243 under `score_last`.

**Caveats (disclosed):**
(a) a per-feature cell@1 gate beats nothing — the liveness features
separate the right set on *mean* (the R57 §57.1 nulls all KEEP) but no
single one puts a right cand at rank-1 among ~78 rivals;
(b) .316 vs .298 is a thin PASS, not a rout;
(c) **of the 18 model-hit cells the winning right cand clears the 5.0
birth floor (or was born) in only 3** — the ranker converts to M1 only
if the *birth criterion itself* adopts the liveness order, i.e. "is
there a current-episode box cand?" replaces "does this cand's static
score clear 5.0" for the box slot.  Half of the hit cells' winners
carry negative `box_rank` (9.3b's right cand scores −20.75);
(d) under the strict ruler label (`label_golden`, 14 cells) the model
scores **1/14 vs baseline 3/14** — sparse-n, but the direction warns
that the lab `label_edge` convention is more generous than the ruler;
(e) cell@1 is a dataset proxy — the birth funnel sits between this
ranking and M1 box@1.

`ESCALATE: A3 ready` logged; the Lead runs the authoritative fit.

### A4. Mutable episode object (lifecycle — REQUESTS.md spec, mine)

**Rule.** The author's box is *edited*, not re-proposed: edges
readjust on new extremes, span extends right, closes manually.  Form:
a live BOX object may re-edge in place (new wick extreme within K of
the edge, episode still current) — the event is logged as `reedge`,
not a new birth.  Zero net births; the object stays the same ink.
**Params:** reedge_tol = 3 p, min gap = 10 bars.
**Falsify:** replay — would re-edging have moved any *born* box onto
golden edges?  Anatomy says born-and-missed = 0, so A4's direct
conversion is ~0; its value is keeping ONE object current instead of
spawning rivals (reduces the outranked/rate churn A1 fights).
**Expected:** ink-neutral; enables A1/A2 to work on a single live
object rather than a pool of stale duplicates.

### A2 measured — both variants fail the falsification (16:40Z)

| variant | rule | oracle coverage |
|---|---|---:|
| v1 | ER(20) < 0.5 × 5 bars opens CONG, edges = running wick extremes | 15/119 — edge never breaks (bug: edge ratchets include current bar) |
| v2 | same + absorb_tol 4 p, break bar joins episode | 28/119, 4/62 no-cov — ER episodes are 20–60-bar fragments; author boxes span 100–400 bars |
| swing-grammar | runs of ≥4 alternating k=3 pivots within 25 p spread | 15/119 — episodes land as shifted sub-bands of the golden |

Scripts: `r2_episode.py`, `r2_swingseg.py`.  The misses are systematic:
the author's box is **not** a running-extremes envelope of a
contiguous sideways episode — the edges are *price-pinned levels* the
episode respected, and the episode boundary itself is a judgment
(edges need the episode; the episode needs the edges).

### A2′. The level-pair inversion — reach exists, selection does not

Golden edges vs the engine's own level stream at τ (`cand_log`
LEVEL_CARRIED / MINI_LEVEL, ≤ τ): **82/119 have both edges within tol
of a proposed level price** (live objects alone: only 4 — levels die
before τ).  The prices exist; the problem is *which pair*.

Pair-selection rules tried (offline, oracle = both edges ≤ tol):

| rule | coverage |
|---|---:|
| any pivot-cluster pair inside the golden's span | 50/119 (oracle) |
| most-touched level above/below median | 10/119 — interior levels win touches |
| outermost tested (≥2) level each side | 8/119 — stale pre-episode pivots overshoot |
| hugging level (nearest outside last-60-bar range) | 3/119 — the "episode window" guess is wrong |
| straddle pair (nearest tested ≥2 level each side of close[τ]) | 7/119 — pair hugs current price too tightly; author's box bounds the whole episode, not its last position |

**Finding:** the author's edge pair is neither most-touched, nor
outermost, nor hugging — it is a judgment call among ~30–60 candidate
levels, made with the episode boundary already known.  A fixed
geometric selection rule does not reach it.  This is the precise
statement of "the deficit needs a signal source not in the feature
set": the missing signal is *which levels the market is treating as
the box* — and the author's clauses name it: the levels get their
status from the **setup** (Asia range, post-drop base, absorption
after spike, "straddling 1,325").

### Order of attack — final state (15:55Z)

1. ~~A2 offline falsification~~ — done: both variants fail (above).
2. ~~A1 spec~~ — REQUESTS.md, with measured ceiling (3/12 pick-live vs
   10/12 right-live; scope-only +2/12).
3. ~~A3~~ — `r3_fit.py` + dataset staged; `ESCALATE: A3 ready` logged.
   PC-run numbers (18/57 = .316 pooled CV cell@1) are **not evidence**
   pending the Lead's cloud reproduction (R58 §58.1).
4. A2′ level-pair: dead as a fixed rule (§A2′); archived.
5. A4 spec: parked (lifecycle, post-research).
→ R3 pick + rationale in Ch. R3 below.

---

## Ch. R3 — Prototype decision (15:55Z)

**The surviving formulation is selection-side; no rule-based
`boxes.py` prototype survives the null discipline.**  Falsification
trail for in-walls (generation-side) rules:

| avenue | result |
|---|---|
| A2 ER episode machine | oracle 28/119 (v2), 15/119 (v1) — dead |
| A2 swing-grammar | oracle 15/119 — dead |
| A2′ level-pair selection ×4 rules | best deterministic 10/119 — dead |
| live_emit (emit only if close in band at t1) | right 99.4% vs wrong 97.3% — saturated, dead |
| pivot-support score term | saturated 96/103 wrong also 2-edge (R51) — dead |
| deeper_w=0 / deeper_cap=2 | A/B fail / 0/31 arithmetic — dead |
| wick_birth pool join | box@1 −1 on K7 — dead |

**Why every generation rule dies the same death:** the signal that
separates right from wrong exists only *at evaluation time* — whether
close[τ] is inside the band, how fresh the last touch is.  At proposal
time 97–99% of ALL cands contain current price; staleness develops
after emission, inside the object lifecycle.  boxes.py controls the
geometry at emit; the discrimination needs the slot decision.  That is
`salience.py` — the build lane's file.  (Consistent with the anatomy:
0 born-and-missed; the funnel kills pre-birth via outranked/rate/floor
— all slot-side.)

**The surviving formulation = A1 + A3 combined:**
"liveness-scoped, liveness-ranked birth selection."

- A1 (spec'd in REQUESTS.md): birth slot restricted to current cands —
  measured asymmetry pick-live 3/12 vs right-live 10/12; scope-only
  ceiling +2/12.
- A3 (escalated, `r3_fit.py` + `r_dataset/`): liveness ranker —
  PC-run CV cell@1 = 18/57 = .316 pooled vs shuffle p95 .298 and
  score_last baseline 5/57 = .088 (**not evidence** pending the Lead's
  cloud reproduction, R58 §58.1).
  The four features (`-dist_close_edge_abr`, `close_at_box`,
  `-recency_bars`, `-bars_since_touch`) are already computable in
  `feats_at` from bars ≤ τ — a birth-order change, not new plumbing.
  **Conversion caveat:** only 3/18 hits clear today's 5.0 floor —
  deployment = the birth *criterion* adopts the liveness order, not a
  re-sort of born objects.  Strict-label check (14 cells): 1/14 vs
  baseline 3/14 — disclosed, sparse-n.

**Flagged-prototype status:** none is defensible inside `boxes.py`
under §3.6 — shipping a generator change the evidence says cannot work
would be worse than reporting the boundary.  The prototype vehicle is
the A1 scope flag in salience (build lane), optionally laced with the
A3 weights once the Lead's authoritative fit returns.  If both fail
the formal A/B, the remaining unexplored structure is A4 (mutable
episode object) — a lifecycle redesign, not this round.

---

## Tries ledger (R58 §58.4)

Every rule/arm BOX-LAB tried in the C-rounds, offline or A/B, with
parameters and outcome.  Count for the final report: **22 distinct
tries** (15 rule formulations + 7 hypothesis/feature tests folded into
the null tables; engine A/Bs marked).

### Generation-side rules (boxes.py reach)

| # | rule / arm | params | evidence | verdict |
|---|---|---|---|---|
| 1 | `cong_trigger` (C-1) | trigger-window close-extremes seed | engine A/B | KEPT (C-1) |
| 2 | `cong_pivedge` (K8) | topk=4, npairs=6, minrun=12, memo-on-change | engine A/B | KEPT (box 10/119, lvl 8/76) |
| 3 | `wick_birth` pool-join | flag on | engine A/B on K7 | FAIL (box −1) |
| 4 | `deeper_w=0` | weight 1.5→0 | engine A/B | FAIL (births +0.84/pan, box −1, lvl −1) |
| 5 | `deeper_cap=2` | saturate nesting penalty | arithmetic pre-A/B | DEAD (0/31 reach 5.0) |
| 6 | pivot-support score term | 2-edge pivot support at birth | offline audit | DEAD (saturated: 96/103 wrong also qualify) |
| 7 | in-window rate replacement (X2) | `box_score_pick` | audit | already deployed since C1 |
| 8 | episode machine v1 | ER(20)<0.5 ×5, running wick edges | offline oracle | FAIL 15/119 (edge-ratchet bug) |
| 9 | episode machine v2 | + absorb_tol 4p, break_tol 2p | offline oracle | FAIL 28/119 (fragments 20–60 vs author 100–400 bars) |
| 10 | swing-grammar | ≥4 alternating k=3 pivots, spread ≤25p | offline oracle | FAIL 15/119 (sub-bands) |
| 11 | level-pair: most-touched | cluster pivots 1.5p, touches≥? in span | offline oracle | FAIL 10/119 |
| 12 | level-pair: outermost tested | touches ≥2, extreme each side | offline oracle | FAIL 8/119 |
| 13 | level-pair: hugging | nearest outside last-60-bar range | offline oracle | FAIL 3/119 |
| 14 | level-pair: straddle | nearest tested ≥2 each side of close[τ] | offline oracle | FAIL 7/119 |
| 15 | `live_emit` gate | emit only if close in band at t1 | offline discrimination | DEAD (right 99.4% vs wrong 97.3%) |
| 15b | `span_episode` window (R59 §59.3) | bs=leg-boundary / sustained-entry | offline IoU on 172 right cands | DEAD (82→4 / 82→82; right cands already span the episode) |

### Selection-side rules (spec'd, not in my walls)

| # | rule | params | evidence | verdict |
|---|---|---|---|---|
| 16 | A1 live-scope birth gate | t1 ≥ now−30 | build-lane A/B | REJECTED (flat; stale-at-birth 1/309) |
| 17 | A1v2 `box_young_first` / `yng_on` | youngest-cand priority | build-lane A/B @97061ac5 | FLAT — A1 closed 2/2 (R59 §59.4) |
| 18 | A4 birth-by-liveness-order | order: min bars_since_touch, dist_edge tiebreak; floor = stated sanity min | spec'd in REQUESTS.md | superseded by 18c/18d — class closed |
| 18b | `lvb_on` (build lane) | birth only while close in-band or ≤0.5 ABR of edge | A/B @29de0689 | **FLAT** — every metric ≡ off (box 10/119); gate never discriminates, ~97% of cands are in-band at emit-time |
| 18c | `a4_on` / `box_live_birth` (build lane) | containment-liveness at birth | A/B @b1d94617 | INERT — canonical 198/198 ≡ off; envelopes always contain price at birth |
| 18d | `a4b_on` / `box_edge_birth` (build lane) | edge-proximity birth eviction | A/B @54bd315b | **FAIL −2 box** — incumbent edge-proximity is a rightness signal, evictions net-wrong |
| 18e | recency-order contest (build lane) | min recency_bars, tie age | arithmetic pre-A/B | DEAD — incumbent CONTEXT_RANGE has recency_bars=0 in ≥75% of cells (envelopes update every bar); ceiling ≈ +4 |
| 18f | positional-staleness ordering at τ (BOX-LAB measurement, not an arm) | demote incumbent when close[τ] >5p outside band+edge | dataset measurement + build-lane counterfactual | **DEAD at object level** — my +28 ceiling counted *pending* cands (field-name bug: `pick_born` vs `born_by_tau` silently passed all); correct count: born right objects under a stale pick in only **3 cells**, 50/63 stale cells have NO other live object beneath — counterfactual +1/−1 net-zero. Pick stale in 61/115 cells is real, but nothing waits beneath the envelope |
| 19 | A3 learned liveness ranker | 4 feats, LODO | cloud fit reproduced byte-identical (R59 §59.1) | **CLOSED** — a stated recency rule matches it without fitting |

### Lead's cloud offline rules (R59 §59.2, added per §59.4)

Expected cell@1 with random tie-breaks, pooled rows
(label_edge / label_golden-strict):

| # | rule | label_edge (57) | strict (14) | verdict |
|---|---|---:|---:|---|
| 20 | chance (random pick) | 6.4 | 2.1 | baseline |
| 21 | engine `score_last` | 5.0 | 3.0 | **below chance** |
| 22 | recency (min recency_bars) | 19.2 | 1.0 | best single key |
| 23 | recency, then age | **21.5** | 1.0 | best composite |
| 24 | youngest (min age_bars) | 17.9 | 0.0 | strong |
| 25 | close_at_box | 12.6 | — | moderate |
| 26 | min bars_since_touch | 11.8 | — | moderate |
| 27 | min dist_close_edge | 6.7 | — | chance |
| 28 | touch, then edge (§58.3 example) | 6.7 | — | chance — withdrawn |

(+7 more single-key / composite rules in the Lead's cloud check —
13 single-key + 3 composite total; the named nine above are the
instructive ones.)

### Hypothesis/feature tests (inform the above; null-gated)

| # | item | verdict |
|---|---|---|
| 20 | R1.4 null table H1–H10 | KEEP: H1,H3,H4,H5,H6,H10 / DROP: H2,H7,H8,H9 |
| 21 | R57 causal re-test ×13 feats ×2 designs + density null | KEEP: px_in_box, close_at_box, dist_edge, recency, bars_since_touch (+thin prior_leg, h_rel_day, h_abr) |
| 22 | registry sources (X.S): pivots/cext/session | pivots fail auditor density null (.711 vs .763) → registry archived |
| 23 | born-right-cand audit (born_by_tau=1, n=20) | all 20 are fresh fragments (0.04–0.54× golden span), all label_golden=0; but span isn't the discriminator — hit picks include 0.10× ratios; they were never the pick anyway. Episode-start extension can't rescue: causal ep detector lands *inside* the episode (741 vs t0 580) |
| 24 | anchoring check: stale picks vs ALL panel goldens | 55/61 stale picks match NO golden in the panel (IoU<0.3) — phantom envelopes on structure the author never drew, not displaced right answers |

### Phase 2 (R60–R61) — event-route port

| # | rule | params | evidence | verdict |
|---|---|---|---|---|
| 25 | v0 event-route port (`pullback_end` + `range_double_*` on v1 SwingBook confirms, idx=t_ext axis, t0=earlier pivot bar, CR stays alive as level/line carrier, box-family rank-1) | spec'd verbatim in REQUESTS.md; envelope 6–34p, dtol 2.0p, min_sep 4, window 84 | cache replay on v1 pivot stream (c1_eventreach.py) | **reach 12/15** event-route goldens, all inside envelope gate — handed to build lane for the A/B |
| 26 | pivot-pool variants for the 3 misses | (a) `is_structural`-only pools; (b) max-prom `last_opp` | offline replay | both 0/3 — interlopers are themselves structural; misses need adjacency-in-stream pairing (v0's coarser book), not pool filters |

### R62 §62.4 — throttled event birth (target: ≤2 births/panel AND keep 12/15 reachable)

Stream profile first (198 panels, 9720 cands, med 49/panel): the
matching cand is causally indistinguishable — leg med 8.8p (hit) vs
8.8 (stream); prom 10.5 vs 10.5; pairsep 11 vs 8 bars; min
touches/edge 2 vs 2; born at ~50% of the stream (never first, rarely
last); no quiet gaps ≥20 bars exist. Every stated shape measured:

| # | throttle rule | births/panel | reachable goldens surviving | verdict |
|---|---|---|---|---|
| 27 | governing-release, X∈{.5,1,2,3} ABR | 5.5 / 4.1 / 2.7 / 1.8 | 1 / 1 / 1 / 1 | FAIL — wrong cand is born each episode |
| 28 | governing + in-place re-anchor, X=3 ABR (v0 semantics: edge move ≤8p, cd 12b) | 1.8 | 1 | FAIL |
| 29 | leg floor L∈{15,20,25}p (v0-coarse-stream proxy: only big-leg pivots enter pools) | 8 / 3 / 1 cands | 5 / 0 / 0 | FAIL — golden-bounding pairs ride small legs (2.9–9.5p) |
| 30 | deferred birth, touch-ranked at slot-open, S∈{80,120,200}b | 2 / 2 / 1 | 2 / 1 / 0 | FAIL |
| 31 | edge-dedup, D∈{5,8,12}p vs all born | 13 / 9 / 6 | 11 / 8 / 6 | FAIL constraint — never reaches ≤2 births |
| 32 | growth-supersede, D∈{0,2,4}p widen | 6.8 / 5 / 4.2 | 1 / 1 / 1 | FAIL |
| 33 | UIP variants: always-update 4/15 · wider-only 0 · left-only 0 · left∨wider 3 · **rd-only 5** · re-anchor≤8p 0 | 1 | best = **5/15** | best within-budget but fails the 12/15 target |
| 34 | cumulative envelope (min lo / max hi over stream) | 1 | 0 | FAIL — over-wide |

**R62 verdict:** the stated joint target (≤2 births AND 12/15 kept)
is unreachable in the measured parameter space — every gate tight
enough for the ink cap removes the right cand, which carries no
causal signature. Per §62.5 this is the round's frontier and it is
handed to the Owner via REQUESTS.md §19 with the best measured
variant (T1 = UIP rd-only: 1 birth/panel, 5/15, projects ≈ BOX
15/119 if rank-1).

### R65 §65.3 — ruler-exact recount + throttle matrix redone on the 46-set

DR-BOX's 51/119 edge-match reproduced exactly; ruler-exact
(`eval_v2.match_detail`, event object modelled as the port emits it:
t0=earlier pivot bar, live at τ, no recorded containment window →
coverage fallback) = **46/119**. Throttle rules below were
preregistered in BOX_LOG.md 02:50Z before measurement — none added
after.

| # | rule (46-set, ruler-exact survival) | births/panel med (avg) | survivors /46 | verdict |
|---|---|---|---|---|
| 35 | UIP-all — one object, every event rewrites lo/hi/t0 | 1.0 (1.00) | 14 | best at 1 birth; ~30% of reachable |
| 36 | UIP-rd (R62 T1) — only range_double rewrites | 1.0 (1.00) | 13 | ≈ same |
| 37 | first-cand-only | 1.0 (1.00) | 3 | FAIL |
| 38 | governing + in-place re-anchor X=3 ABR | 1.0 (1.54) | 6 | FAIL |
| 39 | touch-defer S=200 | 1.0 (1.39) | 3 | FAIL |
| 40 | governing-release X=3 ABR | 1.0 (1.62) | 5 | FAIL |
| 41 | touch-defer S=80 | 9.0 (12.4) | 3 | FAIL — misses operating point |
| 42 | hard cap first-2 cands | 2.0 (2.00) | 4 | FAIL |
| 43 | dedup D=12p capped at 2 distinct | 2.0 (1.98) | 5 | FAIL |

**Net:** 62 tries (23 BOX-LAB C-round rules/measurements + 16 Lead
cloud rules + 4 build-lane A4 arms + 19 phase-2 rows #25–43) → 2 engine keeps (cong_trigger, cong_pivedge),
1 already-deployed mechanism (box_score_pick).  Closed: A1 2/2 (flat),
A3 (reproduced then out-scored by stated recency), lvb_on (flat —
gate fires at emit, staleness post-dates emission), the whole A4
birth/liveness-order class (a4_on inert, a4b_on −2, recency contest
arithmetic-dead).  18f positional-staleness residual: measured DEAD
at object level — the stale pick has nothing beneath it (right cands
died pre-birth; the funnel's "0 born-and-missed" cuts both ways).
C-3 selection + lifecycle space is fully closed by measurement or
arithmetic on every named mechanism.  The envelope-vs-box contest is
a representation/anchoring question: same height (1.04×), wrong
anchor (band-IoU vs golden med 0.02, center offset 16p) — the right
shape on the previous episode's structure.  HOLD remains the
one-shot test.

### R66 §66.6 — preregistration for the `uip2_lvfree*` arms (03:1xZ, before build measures)

`uip2_on` = my T1/UIP-rd spec (one persistent event object, rd
rewrites, close-exempt): measured by build @6d955783 — **box 16/119
(v0 parity), clutter 4.67, births 1.0/panel, suite 71/72** — the
frontier moved off ink; only blocker = level@1 −4 (4/76).

Loss mechanism as verified by build: (a) the mutating edges seed
competing LEVEL_CARRIED objects that outrank the correct level;
(b) the persistent box suppresses level presence at τ; (c) earlier
noted box-family slot occupation dropping CONTEXT_RANGE births
189→195Δ and shortening carried-level lifetimes.

**Predicted outcomes (stated before the arms run):**

| arm | level@1 | box@1 | suite | rationale |
|---|---|---|---|---|
| `uip2_lvfree` (V1) | **7–8/76** (Δ0..−1) | 16–17/119 | 71/72 | V1's two provisions remove exactly the three stated loss paths: no level seeding from ev edges kills (a); cap/slot exemption kills (b) and (c). Residual risk −1: level losses through channels not in the stated mechanism. `test_pullback_end_box_birth` still fails (rd-only) → M1-measure can pass but keep is test-blocked. |
| `uip2_lvfree_pb` (V2) | 7–8/76 | **16–18/119** (Δ +0..+2 vs V1) | **72/72** | pb rewrites measured headroom: UIP-all 14/46 vs UIP-rd 13/46 ruler-exact; DR youngest-either 20/51 vs rd 18/38. Cures the pb test → the keepable arm. Honest risk: R62 flip-decomp showed pullback births caused 6/7 hit→miss losses — a late pb rewrite can drag edges onto a micro-structure; if V2 box < V1 box, that mechanism reappeared in rewrite form. |

If V1 lands level ≤6/76, the stated mechanism is wrong — the loss is
through a channel neither lane has named (e.g., pick-score
contamination inside the level family itself).

**SCORED (R68, measured @23504c93, EVAL-AUDIT verified 03:33Z): HIT.**
- V1 `uip2_lvfree`: level **7/76** (predicted 7–8 ✓), box **16/119**
  (predicted 16–17 ✓), line 20/193, clutter 4.33 — **first arm in the
  programme to meet M1 on all three families at the author's ink**.
  Suite of record 71/72 — `test_pullback_end_box_birth` fails as
  predicted (rd-only can't birth inside its envelope).
- V2 `uip2_lvfree_pb`: **inert** — row and flip set identical to V1
  (+0/−0), retired. My 16–18 prediction brackets the observed 16; the
  pb headroom I banked on does not materialise on TUNE (pullback
  cands exist but don't flip any of the 119).
- The R66 level mechanism is confirmed causal: removing ev-edge level
  seeding + slot suppression returned exactly the −4 (8→4 → 7/76;
  net −1 vs parent = one residual flip through another channel).

### R67 §67.4 — PREREGISTRATION: episode-container birth channel (stated 03:4xZ, before any measurement)

Second birth channel `EC` (box family, `why="ec_<trigger>"`). All
bars M5; ABR = causal ABR(50) in pips (`cache.abr`); every window is
a bar range; a cand is evaluated only if it is born ≤ τ. Hypothetical
engine record for ruler-exact scoring: `{type:BOX, lo, hi (pips),
t0 = m[start_bar], t1 = τ (still live), w0, w1}` — no bs/be → the
ruler's coverage/IoU fallback governs, exactly as in the R65 recount.

**EC-A `session_range`** (book: "the Asian range is the day's first
reference box"): at the first bar with `m ≥ 420` (07:00), birth one
box with edges `[min l, max h]` over the day's bars with `m ∈ [0,420)`.
t0 = first bar of that window. At most 1 birth/date. No height gate
(book Asia boxes run 10–30+p; gating would re-impose the event
envelope this channel exists to escape). If no bars exist in
[0,420), no birth.

**EC-B `spike_base`** (book: "an absorption box after a spike includes
the spike extreme"): spike at bar i iff `|c[i]−c[i−K]| ≥ S·ABR[i]`,
K=6, S=2.0. The spike extreme bar i_s = argmax/argmin over the move's
last leg (for an up-spike, i_s = argmax h over [i−K,i]). Base window =
bars [i_s, i_s+M], M=8 (spike bar + 40 min absorption). Birth at
i_s+M iff base height `hi−lo ∈ [4p, 60p]` (4p floor kills degenerate
flat lines; 60p cap kills runaway trends). Cooldown: after a birth,
no new spike_base birth for G=12 bars.

**EC-C `first_block`** (book: "the first sideways block after a leg
is boxed immediately, before it resolves"): leg ends at bar i_l iff
`|c[i_l]−c[i_l−N]| ≥ L·ABR[i_l]` over N=6 bars. Sideways block = the
first run of ≥B=8 consecutive bars after i_l where every bar's range
`h−l ≤ X·ABR`, X=1.0. Birth at run end; edges = run `[min l, max h]`
iff height ∈ [4p, 60p]. One birth per leg; a new leg requires the
price to move ≥L·ABR again from the leg-end close.

**Measurement (once, no iteration):** per trigger and for the union —
(a) ruler-exact reach on the 68 edge-unreachable goldens; (b) reach
on all 119; (c) births/panel; (d) live objects/panel at τ. Hand-off
to REQUESTS.md only if a trigger adds reach at ≤~1 extra birth/panel.
At most 2 triggers handed off.

**V1 measured (03:48Z):** session_range 0/68 (3/119), spike_base
2/68 (11/119), first_block 0/68 (3/119); union **+2/68** unreachable
(9.17c, 9.48c), +13/119 total, live-at-τ only 6/13. Births
3.74/panel in-window — **fails the handoff bar** (too much birth for
+2). The three triggers mostly redraw bands the event stream already
covers; the unreachable goldens' edges are interior choices, not
container extremes.

**V2 (final variant, stated before measuring 03:48Z):**
`spike_base` v2 — same as EC-B plus an absorption test: the post-spike
bars (i_s, i_s+M] must have mean bar range ≤ X2·ABR, X2=1.0, and the
base height ≤ 40p. Everything else unchanged. Rationale: the book's
base is *quiet* after violence — the absorption filter should cut the
~3.7 births/panel toward ~1 while keeping the two observed hits.

**V2 measured (03:49Z):** reach **3/68** unreachable ruler-exact
(9.17c, 9.33c, 9.35a — the absorption test actually *gained* a golden
vs V1's 2 while halving births: V1's sloppy bases died on the 40p
cap), 2/3 live at τ, 12/119 total. Births **1.48/panel in-window
(med 1.0)** — borderline vs the "~1" bar. Handed off as a candidate
spec (REQUESTS.md §23); build decides whether +3 reach is worth the
ink. EC-A and EC-C reached **0/68** — the author's Asia boxes and
first-blocks are interior-edge choices, not raw container extremes;
the episode-container idea survives only as the post-spike base.
Tries 62→65 (EC-A, EC-B v1, EC-C, EC-B v2).

### R66 §66.4 `uip2_bs` — measured by build @c06365ce (03:46Z)

The §20 episode-anchored `build_start` spec ran as `uip2_bs`
(ev_uip_buildstart): **byte-flat** vs `uip2_lvfree_pb` — box 16/119,
level 7/76, line 20/193, clutter 4.33, +0/−0 flips, OFF-identity
576/576. My prereg "+0..+5" landed at the low end.

Why flat is informative: the offline 9→14/20 gain was measured on
*hypothetical* rule-hit records (the cand ranked first). In the live
arm the picked object already passes its span test or fails on edges
— zero containment flips on scored cells confirms the EVAL-AUDIT
decomposition (0/109 misses fail on window alone; the gap is edge
anchoring). `bs` recording works (smoke hit the w0 cap) and costs
nothing — keep it as instrumentation, not a mover. Try 66.

### UIP write-selection bound (04:05Z, cache, ruler-exact)

Question: the UIP object holds ONE write — would a different causal
state rule hold more reachable goldens than youngest? Measured on the
46 ruler-exact reachable set (eval_v2 imported, hypothetical live
records):

| state rule (causal at τ) | hits/46 |
|---|---|
| youngest write (current uip2) | **14** |
| oldest still-containing (v0 governing) | 14 |
| sticky = newest still-containing | 12 |
| widest band | 7 |
| most in-band closes since birth | 6 |
| oldest write | 3 |
| oracle over all writes | 46 |

**Closed.** No causal state rule beats youngest — the single-object
UIP ceiling is ~14–16, exactly what `uip2_lvfree` measures (16/119).
The 30-golden gap to the reachable set is not recoverable by write
selection; it needs either multiple objects (which re-imports the same
selection problem one level up) or new generation for the 68
unreachable. Try 67.

### R71 §71.5 — PREREGISTRATION: reach queue items 2+3 (stated 04:4xZ, before measuring)

Base: C-3 `1a550212`. Counts are offline ruler-exact on the cache
(identical under C-3 — the cand stream is unchanged; only the UIP
birth gate changed). Unreachable-68 recomputed from `dr_rows.pkl`
(n_match==0); my edges-seen classification: both 38 / one 21 /
neither 9 (DR's stricter level-vocab cut: 27/25/16 — same classes).

**Item 2 — `env_abr`:** replace the event channel's fixed 6–34p
envelope with an ABR envelope on cand height at birth:
`1.2·ABR[born] ≤ hi−lo ≤ 10.0·ABR[born]` (≈6–80p at ABR 5–8; the 13
tall goldens run 5.7–10.5×ABR; cap 10× keeps "a box" = congestion,
not a whole range). Measure: reach on the 13 tall unreachable +
all-119 delta + admissible-cand rate (→births if free-standing).

**Item 3 — `pair_edge` (PC channel), DR's "latest tested-high × latest
tested-low":** registers E_hi = hi of the most recent born event cand,
E_lo = lo of the most recent born event cand (both updated at each
birth). Emit a PC cand when (a) both set and E_hi > E_lo, (b) the pair
differs from the last emitted pair by > 1.0p on either edge (dedup
tol), (c) pair gap ∈ the fixed 6–34p envelope (pairing isolated;
item 2 tests the ABR envelope separately). Cand: lo=E_lo, hi=E_hi,
t0 = min(t0 of the two source cands), born = the later register's
update bar. Measure: reach on the 17/26 unpaired subset + all-119 +
emission rate/panel.

**Combined spec** to REQUESTS.md only if the union adds reach at
≤~1 extra birth/panel (R71 bar).

**V1 measured (04:4xZ):**
- `env_abr` on the event stream: **0/13** tall goldens — no born cand
  edge-matches them at ANY height (10/13 have both edges in the vocab,
  never combined). The envelope is not the blocker; pairing is.
  All-119 reach 45 (≈fixed-env 46; the relaxed floor drops one
  marginal).
- `pair_edge` v1 (independent registers, 1.0p dedup, gap 6–34p):
  **+1/68** (9.48a, live) at 13.9 emissions/panel — pairing works but
  the fixed envelope excludes the tall class, which is the majority of
  the unpaired pool.

**V2 (final variant, stated before measuring 04:5xZ):**
`pair_edge` + ABR gap — same independent-register channel, but the
pair gap test uses the item-2 envelope `[1.2, 10.0]·ABR[born]`
instead of 6–34p. This is the only variant that can reach the tall
unpaired class (10/13 tall goldens have both edges in the vocab).
Everything else unchanged. If the combined channel still adds <~2
reach or costs >~1 birth/panel, the item closes as a measured
negative and the 68 stay a generation problem, not a pairing one.

**V2 measured (04:5xZ): still 1/68** (same 9.48a), **0/13 tall**,
emissions 15.5/panel. Diagnosis: the registers only ever hold the
*two latest* distinct edges — but the author's paired edges were
seen scattered across time, never latest-adjacent. Pairing the
latest-two cannot surface them; pairing arbitrary vocab pairs is
combinatorial ink. **Items 2 and 3 CLOSE as measured negatives.**

### R71 §71.5 — VERDICT (all items measured once each + one variant)

| item | rule | +reach on 68 | births/panel | verdict |
|---|---|---|---|---|
| 1 EC-A session_range | Asia 00–07 box | 0 | ~1/date | dead — edges interior |
| 1 EC-C first_block | sideways run after leg | 0 | low | dead — same reason |
| 1 EC-Bv2 spike_base | spike + absorption | **+3** | **1.48** | borderline pass → §23 |
| 2 env_abr | [1.2,10]·ABR envelope | 0/13 | — | dead — pairing, not gate |
| 3 pair_edge v1 | latest hi×lo, 6–34p | +1 | 13.9 | dead — ink ≫ reach |
| 3 pair_edge v2 | + ABR gap | +1 | 15.5 | dead — same |

Union of qualifiers = EC-Bv2 alone (+3/68; 9.48a from pair_edge is
disjoint → union would be +4 but pair_edge fails the ink bar alone).
**Combined spec = REQUESTS.md §23 unchanged** — spike_base_v2 is the
only qualifier. The remaining 65/68 unreachable goldens are a pure
generation problem: the author's edges are interior holdings, not
container extremes, pivot pairs, or vocab recombinations.
Tries 67→70 (env_abr, pair_edge v1, pair_edge v2).




## R73 s73.3 — gate ladder + edge-definition audit (06:21Z-06:29Z)

Step 1, edge-definition check (r73_edges.py, containment window
[bs,be], fallback drawn span; tol=max(1p,0.25ABR)):

| def | unreach both | unreach edges | reach both | reach edges |
|---|---|---|---|---|
| raw extreme | 22/69 | 63/138 (41%) | 11/50 | 44/100 (44%) |
| drop1 outlier | 32/69 | 86/138 (62%) | 20/50 | 58/100 (58%) |
| 2-touch cluster | 33/69 | 86/138 (62%) | 23/50 | 65/100 (65%) |

VERDICT: author edge = DEFENDED CLUSTER inside the build window, not
the raw extreme. Confirms the DR-LINE carried hypothesis on anatomy.

Step 2, gate ladder (r73_ladder.py; stream re-enumerated on each
date's c1r_p_base@ee2cbf12 book.seq; base = C-3 params
WIN600/SEP8/DTOL2/PB3/first-pair/shadow/raw):

| cell | relaxed gate | r119 | r68 | cands/pan |
|---|---|---|---|---|
| L0 | base | 45 | 3 | 21 |
| L1 | win=inf (engine.py:346) | 45 | 3 | 21 |
| L2 | sep=0 (:352) | 47 | 3 | 24 |
| L3 | dtol=4 (:354) | 42 | 3 | 24 |
| L4 | dtol=8 (:354) | 47 | 8 | 25 |
| L5 | allpairs (:363) | 45 | 3 | 21 |
| L6 | pbsep=0 (:379) | 50 | 6 | 28 |
| L7 | unshadow (:384) | 46 | 3 | 28 |
| L8 | edge=cluster (:355) | 45 | 4 | 21 |
| L9 | wininf+sep0+dtol4+allpairs+pbsep0+unshadow | 57 | 10 | 132 |
| L10 | L9+cluster | 57 | 11 | 132 |

Deliverable reach under mandated youngest-born selection:

| cell | youngest-rd 119/68 | youngest-any 119/68 |
|---|---|---|
| L0 | 16/2 | 21/2 |
| L4 | 15/3 | 17/3 |
| L6 | 16/3 | 18/3 |
| L9 | 12/2 | 8/2 |
| L10 | 11/1 | 8/2 |

First-write freeze: 0/68 all cells. Rank probe (r73_rankprobe.py):
matching writes scattered mid-stream (L4 med 1 write-after, max 27;
L9 med 11, max 170); only 2-3/11 are last-write.

STEP 3/4 — CLEAN NEGATIVE. Pool-reach headroom (+5 to +8/68) is not
deliverable: the matching cands are overwritten before tau, no causal
selection rule keeps them (youngest already optimal on reachable set,
measured 04:05Z), and cumulative relaxation REGRESSES the 119
(youngest-write 12 vs 16). Birth gates (envelope/cooldown/dedup/
uip_spent/score) are admission-only - envelope already 0/13 in R71.
Upstream swing granularity (swings.py:38-98, 112-148) not relaxed
(needs engine re-run, not a read-only gate). The 68-wall stands as a
generation problem: defended edges exist per-edge (62%) but never
arrive paired in one causal candidate. EC-Bv2 (REQUESTS.md s23)
remains the only qualifying handoff. Ledger tries 71-73.
