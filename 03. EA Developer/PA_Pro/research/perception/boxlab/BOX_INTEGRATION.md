# BOX_INTEGRATION — X4 (BOX-LAB, 2026-09-21 ~22:40Z)

> Correction (R25 §25.6): stamp "~22:40Z" was hand-written; file
> written 21:33:45Z (R14). From now on every time in this file comes
> from `logline.py --now` or `date`.

Status: **proposal only.** No production files touched. Lead rules
per §13.5 / R18–R25.  Evidence: `ROUND_X3.md` r1–r41; ruler
`eval_v2 50e11fd5a2ab7974`; lab engine `boxes_lab.py` r37 config
(snapshot `cache/boxes_lab_r37.py`).

## Headline numbers — lab, not engine (R23 §23.5)

Lab rows are day-CV with day-cluster bootstrap CIs (B=2000);
score weights **frozen** across folds (hand-set on all 108 goldens —
CV bounds fold variance, not the global tuning bias; stated per
R23 §23.3).  Engine columns are from `GATE_PACK_DRESS_584c7743.md`
(v0 `63c771d6`, v1 `584c7743`; per-family BOX recall@k).

| metric | v0 engine | v1 engine | lab r33 (low ink) | lab r37 (high recall) |
|---|---|---|---|---|
| born recall (eval_v2) | .21 (23/108) | .06 (6/108) | .194 [.127–.274] | .278 [.198–.357] |
| BOX recall@1 @ τ | .06 (6/106) | .00 (0/106) | .148 [.093–.207] | .130 [.074–.185] |
| BOX recall@2 @ τ | .10 (11/106) | .01 (1/106) | .148 [.093–.207] | .241 [.168–.316] |
| oracle ceiling | .31 | .29 | .556 | **.667 (r47)** |
| live boxes @ τ (med) | 16 (all fam) | 10 (all fam) | 1.0 | 2.0 |
| born ink / panel | ~1113 objs tot | ~301 tot | 5.30 | 17.49 |
| flicker / h | — | — | 0.20 | 0.32 |

**Ink–recall frontier (lab, CV-pooled):** r33 and r37 are two points
on one frontier — .194 recall at 5.3 born/panel vs .278 at 17.5.
Author's rate ≈ 108 golden / 198 panels ≈ **0.55 drawn boxes/panel**,
so r37 births ≈ **30×** the author's rate and r33 ≈ 10×.  The live
budget (≤2 at τ) keeps snapshot clutter at the author's level in
both; the excess is cumulative births.

**Controls (R23 §23.3):**
- *Shuffle* (`lab_r41s`, deeper_lv+barrier permuted in-panel):
  born .306 (did NOT fall to r28's .176 — stated per the ruling),
  r@2 .241→.185, ink 17.5→35.8.  Reading: the features carry real
  τ-ranking signal; cumulative recall is ink-limited, not
  score-limited (random ranking + 2× ink still covers goldens).
- *Barrier sign per fold:* anti-predictive on ALL 5 folds
  (P(right|bar=0) .0043–.0123 vs P(right|bar≥1) .0002–.0029).

## Change list for `boxes.py` (proposal geometry)

The lab's wins came from six changes, in order of effect size
(#5–#6 are the oracle/generation levers added r42–r46):

1. **Watchlist + deferred birth** (replaces propose-on-pivot).
   Every qualifying edge pair registers a *watch*; the object is
   born only when the band **breaks** (decisive close >0.5p beyond
   an edge) or matures.  Rationale: the author's draw moment is the
   episode's resolution, not its first detection — X2 anatomy: bs
   anchors to the turn into congestion, `build_end` ≈ first
   decisive close (median 5 min after last contained bar).
   Production surface: `_propose_window` stays as the qualifier;
   its `e.birth(...)` call moves behind a watch registry keyed on
   (top,bottom) level ids.  **This is the single biggest recall
   mechanism** — it lets a band's geometry settle before the
   object is committed.

2. **Drawn-tail lifecycle** (R21 §21.3 — already ruled).
   New states `BROKEN` → `CLOSED`.  On a decisive close: mark
   `BROKEN`, set `build_end = break_bar`, keep the object drawn
   for `tail_bars=12` (5-min bars ≈ 60 min — measured golden
   drawn-tail), then `CLOSED`.  Live budget counts ACTIVE+BROKEN;
   displacement prefers cutting a broken tail over a live box.
   `meta_build_end` stays = proposal bar for the frozen ruler
   (§21.5 dual convention is kept in the lab scorer).
   Expected delta at matched ink: this alone took live@τ from
   0.0 → 2.0 median (r27→r28); it is the precondition for any
   snapshot-metric credit.

3. **Same-episode dedup = same edges AND window IoU ≥ .5**
   (r36/r37).  Current production dedup (`_propose_window` l.187
   and `congestion_scan` l.376) rejects on edge proximity alone;
   the lab adds the same-edge test **plus** window-overlap so a
   wrong-window band can no longer preempt the right watch, while
   true redraws still dedup.  Expected delta: +10 born matches
   (r33→r37), cost ≈ +12 ink/panel — see limits.

4. **Birth ranking by causal score**, live-budget displacement
   (replaces day-level caps — R19).  Score terms that survived
   falsification: `prom_abr` (validated, R20), `contain`,
   `touches`, `deeper_lv` (defended levels deeper than an edge
   within ~1 ABR — window-independent envelope test), anti-`barrier`
   (golden edges are FRESH extremes; P(right|barrier=0)=.92% vs
   .2% — barrier as an *identity* test is anti-predictive).
   Terms falsified in-lab, do not port: `hgt` (R20 §20.2),
   `edge_gap` on own-window wick percentiles (r28 autopsy),
   `deep_piv` on own-window pivots (r29), `barrier`/`barrier_near`
   as positive terms (r33/r34).

5. **Provisional leg-extreme edges** (r43: oracle .556→.630,
   located .731→.769, trusted 50/68).  The running DC-leg extreme
   is exposed as a provisional level (side = leg dir) and joins
   the pairing pool; it either confirms into a pivot level or dies
   on leg flip.  This is levellab's `leg` origin pattern applied
   to box *edge generation* — 12/16 sampled no-edge misses sat
   within tol of an unconfirmed leg extreme.  Production surface:
   the DC stream already tracks `dir`/`ext_price`; one registry
   entry per running leg.

6. **Dense pivot anchors + 6-bar re-emit** (r41/r42: oracle
   .556→.583 before r43).  Each emit also writes one cand per
   recent in-run pivot bar (cap 8) and re-emits every 6 bars while
   qualifying — the funnel's ±20-min `build_start` rule needs an
   anchor that actually lands near it.

7. **Wick-tip edge variants** (r47: oracle .630→.667, located
   .769→.833).  Alongside each level-pair emit, one cand carries
   edges at the run's p99/p01 wick extremes — golden edges often
   sit on lone spikes that the defended-level design deliberately
   excludes (R12 excursion rule).  Keep it as a *candidate* route
   only: wick-tip geometry must not be promoted to born objects
   without defence evidence, or spike texture will flood the book.

## Parameters (with provenance)

| param | value | source |
|---|---|---|
| `tail_bars` | 12 | §21.3; golden drawn tail ≈60 min (X1 audit) |
| `break_tol_pips` | 0.5 | lab calibration; decisive-close test |
| `birth_min_span` | 5 bars | r26; below this bands are noise |
| `birth_min_persist` | 2 | r26 |
| `birth_score_min` | 3.0 | r38 probe: 3.5 costs 2 matches for −13% ink |
| `nest_iou_min` | 0.5 | r37 vs r40: .35 identical, .5 is the tested value |
| `max_live` | 2 | author's budget (§17.3) |
| `displace_hyst` | 1.0 | r17; challenger must beat incumbent score |
| `edge_track` | off | r35: golden boxes are static once drawn — birth geometry freezes at the watch's best-qualified snapshot |

## Provenance / causality notes

- Every feature is computable at decision time from confirmed
  pivots and closed bars only; no lookahead (the watch's `best`
  snapshot uses only past emits).
- `deeper_lv` needs a defended-level registry — levellab's
  `NOTES_FOR_BOXLAB.md` query is the intended production source.
- Selection features ≤4, equal-weight; `prom_abr` is the only one
  already validated on the production stream (R20).  The rest are
  lab-stream hypotheses pending a `select_eval` run on the
  production candidate log (§15.1).

## Tests to port (boxlab/tests/)

- `test_tail`: break → object still live for `tail_bars`, then closed;
  `build_end` == break bar, `meta_build_end` == proposal bar.
- `test_dedup_window`: same-edge/wrong-window band does NOT block a
  right-window watch; same-edge/high-IoU band does.
- `test_displace`: at max_live, stronger challenger displaces weakest;
  broken tail cut before any live box.
- `test_frozen_geometry`: born edges never reprice after birth.

## Honest limits / expected deltas at matched ink

- **Ink is the open problem.**  Author's rate ≈ 0.55 boxes/panel;
  r37 births ≈30×, r33 ≈10×.  The recall↔ink frontier is real and
  measured with CIs above.  Under the live-budget lens the damage
  is contained (median 2.0 at τ, flicker .32/h) because
  displacement swaps junk out — but cumulative object count will
  fail a strict ink audit.  Recommended engine-side fix: budget
  *drawn-tail occupancy* (a BROKEN box still occupies a slot),
  which the lab already enforces; the residual is births that
  never reach τ.
- **CV caveat:** score weights were hand-set on the same 108
  goldens across ~40 rounds of iteration.  Frozen-weight day-CV
  bounds fold variance only; true out-of-sample requires the
  production-stream A/B (§15.1).  Label per R26 §26.2:
  **"lab, TUNE, selection-optimistic"**.
- **Oracle .630 < .70 target.**  Full miss taxonomy (r43–r46
  probes, 40 misses): 9 unwinnable by construction (funnel clamps
  cand t0 to the panel window; `build_start < w0−20` can never
  match — true ceiling ≈ .917), ~19 no-edges (golden edge is no
  causal structure: not confirmed pivots, not leg extremes, not
  day/session extremes — one side missing in most), 8 bands whose
  containment fails inside the scored window, 4 residual anchors.
  Next lever is a *fourth* edge source: mid-band/eye-level
  structure the author draws through wicks.
- **Precision est .015** is a lab artifact (born_edges_ok counts
  only objects whose edges survive to eval in pip-space) — not a
  production metric; ignore for the ruling.

## Integration dependencies (R25 §25.5 / R27)

- **Per-family ledger first.**  R25 §25.4/R27 §27.1 showed that
  under the shared `rate_total` ledger, one family's gain is paid
  by another family — the lab's extra BOX births would spend the
  same ledger LC/PATTERN_LINE need.  Integrate #1–#4 only behind
  (or together with) the `famledger` per-family budget flag; BOX
  births must draw on BOX's share.
- **τ convention:** production `_gold_window` uses `build_end` =
  last contained bar; the lab's `build_end` = break bar.  Keep
  `meta_build_end` = proposal bar for the frozen ruler (§21.5) and
  report both conventions, as r28 did.

## Lead decision rules (R18 keep-rule applied)

- Adopt #1–#4 together only if a production A/B shows born recall
  up at equal-or-lower ink and no matched family loses >1 object.
- If ink discipline is binding: deploy #2 (tail) + #3 (dedup) at
  `birth_score_min≈4.0` — the lab predicts ~.19 recall at
  ~5–7 ink/panel, still ≥ v1 and near v0 with far better snapshot
  behavior.
- Do NOT port: `hgt`, own-window `edge_gap`, own-window
  `deep_piv`, positive `barrier` terms, day-level birth caps.

## Five-line summary

The author's box is an *episode*: born when congestion resolves, drawn
~60 min past the break, ≤2 live at once.  Lab (day-CV, frozen
weights): born recall .278 [.198–.357] and recall@2 .241
[.168–.316] at live@τ=2.0 — above v0 engine's .21 born / .10 r@2,
at ~30× the author's drawn-ink rate.  Mechanisms: birth at the
break (not first detection), the R21 drawn tail, window-aware
same-episode dedup.  Oracle lifted .31→.667 by adding unconfirmed
DC-leg extremes as provisional edges (r43) plus wick-tip edge
variants (r47); the residual gap is ~14 edges that are no causal
structure at all, 8 window-qualification gaps, 9 unwinnable
funnel-clamp cases (true ceiling ≈.917).

## C-round generation lessons (R44 §44.3, logged ~07:5xZ)

Two findings the next integration round must carry:

1. **Old-structure edges.**  Where the author's edges can be located
   causally at all, they sit on *prior* confirmed structure — median
   age ~7 h (413 min) between the edge-defining pivot and the
   golden's build_start (range 31-816 min).  Production's
   bucket_merge clusters only the current proposal window's own
   extremes, so it can never emit a 7-h-old level.  Any integration
   that keeps window-local clustering needs a separate old-level
   edge source (book.seq is too sparse per panel: on 9.10a zero
   retained pivots lie near the golden band — a richer level source
   such as eye-level/round-number/tick-density is required).

2. **Pivot-starved congestion.**  51/51 no-edge box goldens have
   ZERO structural pivot confirmations during their buildup —
   on_pivot never fires while the author's box forms, so the
   proposal stream is silent exactly when it is needed.  The gap is
   a missing *trigger*, not a missing edge source.  The bar-driven
   congestion_scan route is the right host; its alternating-pivot
   check is definitionally impossible inside congestion and must be
   bypassed for overlap-qualified bands (box.cong_trigger arm,
   N=6 bars, k=4.0 ABR from TUNE buildup shapes: len p25=5 med=10
   p90=31, envelope p75≈4.0 ABR).

3. **The congestion trigger (shipped arm).**  `box.cong_trigger`
   adds `_cong_run` inside congestion_scan: expand backward from the
   current bar while the high-low envelope stays ≤ k·ABR, require
   ≥ N bars, propose the run extremes as edges via
   `_buildup_run(..., fix_edges=True)`.  No pivot requirement — the
   overlap IS the evidence.  On the fixed hash `df79ade3` it adds
   ~6k congestion_scan proposals (13624→19662, +44%), 149→209 scan
   births, and lifts box@1 7→9 of 119 with every other family
   identical and clutter 5.00.  The k=4.0 gains are *timing*
   conversions, not new coverage (oracle 44 covered on both base and
   cong): fresh congestion boxes out-rank stale structural_envelope
   objects at τ.  Robust at k=4.0/5.5, N=6/8; k=3.0 too tight.
   k=5.5 widens the band enough to add +1 oracle coverage (45/108)
   and lifts born recall .093→.111 at the same box@1.

4. **Why snapping misses the tolerance.**  `p_cong_lev` snaps run
   edges to the nearest confirmed pivot level within tease; measured
   result is a *loss* (box@1 back to 7/119, born .083 vs .093).
   Two causes: (a) the author's edges are the run's own extremes —
   the nearest old level usually sits a few pips away, outside the
   ruler's edge tolerance; (b) per-panel the needed level often is
   not in book.seq at all (9.10a: zero retained pivots near the
   golden band).  So the old-structure edge problem (finding #1)
   and the trigger problem (finding #2) are SEPARATE: the trigger
   fix converts already-reachable goldens; the no-edge coverage gap
   still needs a richer level source, not snapping to confirmed
   swings that are absent or off-tolerance.

## R46 §46.3 — no-edge diagnosis under K6 + wick-density verdict

Under K6 (cong_trigger ON, k=5.5) the no-edge class is **38**
(down from 51 — cong cands now carry matching edges on 13 more
goldens; they moved to wrong-t0/late classes).  Per-golden
diagnosis (`c1_congdiag.py`):

| cause | n | detail |
|---|---|---|
| edge_tol | 22 | a cong proposal DOES overlap the buildup; med edge err ~9p, direction mixed (7 too-wide, 7 too-narrow, 8 shifted); 6 cases have one edge within 0.5p |
| blocked: too_tall | 11 | run qualifies (envelope ≤5.5 ABR) but band > min(6·ABR, 34 pips) — the 34-pip absolute cap binds in high-ABR regimes (runs 6–120 bars) |
| blocked: other | 4 | live-cover / dedup / session gates (approx) |
| no_window | 1 | 9.22a g2 buildup outside the panel window |

**`box.cong_density` verdict (both modes fail §34.5, not handed
off):**  the wick-tip density idea was built as specced — Gaussian
KDE over the run's high/low tips, kernel = mean bar range, edges at
outermost merged peaks (merge < 1·ABR), quantile fallback — plus a
pure-quantile mode (q0.90/q0.10).  Peak mode @`0a100806`: box@1
9/119 **flat**, oracle 45/45 identical set — inert, because merged
peaks collapse to interior wick clusters (2.9–6.9-pip micro-bands
that die on the 6-pip height floor; substitution accepted on only
8% of cong cands, 0 dens-tagged births, 0 dens cands ever overlap a
no-edge window).  Quantile mode @`13b3f53d`: box@1 **7/119 = −2**
— the trimmed spikes were exactly what let the cong boxes edge-
match at τ.  Flag-OFF ≡ K6 verified at both hashes (198/198, 0
diffs, objects + cand_log + events).

A third variant `box.cong_subband` (densest legal-height slice slid
inside an over-cap envelope, pooled wick-tip count as the slice
score — built for the too_tall 11) @`5928a0e2`: box@1 9/119 flat,
families identical, but **clutter 5.33 vs 5.00** — 1123 sub-tagged
cands fired, zero born, and they still pay ink at τ.  Rejected.

Ordering on the congestion band: run extremes (k55, **kept K6**) >
density peaks (inert) > quantiles (−2) > sub-band (flat + ink).

**Round-level conclusion:** the author's edges are not recoverable
as a *run-local* statistic — extremes overshoot, interior density
clusters undershoot, quantiles stay off tolerance.  The residual
no-edge class needs either (a) an old-structure level source
(~7 h median edge age — eye-level / round-number / tick-density
registry, not book.seq which is too sparse per panel), or (b) for
the too_tall 11, sub-band extraction inside a tall envelope or a
height-cap exception for cong bands — e.g. a density *pair*
constrained ≥ 6 pips apart (untested refinement, noted for next
round).

**Level-source census (`c1_lvlsrc.py`, causal — levels built only
from bars closed before build_start):**  on the 38 no-edge goldens,
fraction with BOTH edges within tolerance of each source —

| source | both edges in tol |
|---|---|
| book.seq confirmed pivots | 13/38 |
| wick-tip touch density (12 h, 0.5·ABR bins) | 2/38 |
| close-price tick density (24 h) | 0/38 |
| 10-pip round-number grid | 15/38 |
| 25-pip grid | 0/38 |
| **union (pivot ∪ touch ∪ tick ∪ rnd10)** | **23/38 (61%)** |
| **+ prior-day hi/lo, 6h-session hi/lo, close extremes** | **27/38 (71%)** |

Round numbers supply the marginal +10 over pivots; as *seed* levels
inside an already-qualified cong run they are cheap and bounded
(they only fire where a real run exists).  The remaining **11**
goldens (9.15c, 9.16c, 9.30a, 9.34b, 9.37b, 9.42b g0/g1, 9.50c,
9.54a, 9.60b g2/g4) have edges on no standard causal structure —
consistent with the author's eyeball levels drawn through wicks.
A structure-seeded cong route bounds near 27/38 coverage of this
class; the residual needs intent-level sources.

**One-exact-edge cases (R47 §47.2 lesson).**  6 of the 22 edge_tol
goldens already have ONE run-extreme edge within 0.5 pip of the
author's (9.2c top, 9.24c top, 9.42b g1 bot, 9.47b bot, 9.48c top;
9.15c has neither).  For the 5 true cases the *other* edge sits
within tol of a pivot-or-rnd10 level (d 0.0–2.0 vs tol 1.5–5.0) —
BUT the offline rule test disproved the runtime criterion: wick-tip
support does not separate exact from wrong edges (exact sup 1–4,
wrong sup 3–6, overlapping), and no interior-level selection rule
(nearest-to-extreme, max tip support) reliably picks the golden
level.  Snapping on `sup<3` would destroy two exact edges
(9.2c top → +8.0p; 9.48c top → +8.6p).  `cong_mixedge` was
prototyped, disproven pre-A/B, and reverted.  The open problem is
edge SELECTION, not source availability.

## R49 §49.3 — null-tested level sources + `cong_pivedge` (lever, fails §34.5 leg 3)

**Null test (`c1_nullsrc.py`, 200 draws, goldens shifted vertically
±1–3 box heights, same tol).**  Share with BOTH edges within tol of a
level the source produced by τ — observed vs null mean / p95:

| source | 38 no-edge obs | null μ / p95 | all-119 obs | null μ / p95 | verdict |
|---|---|---|---|---|---|
| book.seq pivots | .789 | .243 / .316 | .880 | .286 / .343 | **KEEP** |
| 10-pip rounds | .395 | .311 / .395 | .417 | .378 / .426 | drop |
| buildup close extremes | .211 | .053 / .053 | .398 | .019 / .019 | KEEP |
| 6h session hi/lo | .053 | .002 / .026 | .046 | .002 / .009 | KEEP (thin) |
| prior-day hi/lo | .053 | .027 / .026 | .019 | .011 / .019 | drop |
| union | .921 | .405 / .500 | .963 | .495 / .556 | **KEEP** |

Pivots are the real edge source — and the τ-cutoff matters: most
matching pivots confirm *during* the buildup, so they are available to
late-run candidates but not to a run-start seeding.  R48's null caveat
was right about rnd10 (exactly at p95 — pure grid coverage luck).

**Generator `box.cong_pivedge` (default OFF, `boxes.py::_pivedge_emit`).**
When a K6-trigger run qualifies at bar i: confirmed pivots
(t_conf ≤ i) within envelope ±3eps → clustered at 2eps → top-4
clusters by member-count + run wick-tip support → every height-legal
cluster pair containing ≥50% of run closes is emitted as a band via
`_buildup_run(fix_edges=True)` (own contained-close run), with
emit-on-change memo (fires only when the confirmed-cluster set
changes), extreme-band dedup, live-cover dedup.  Feats `cong`,
`pedg`.  The causal edge-pair rule: *the author's box edges are the
most-confirmed pivot levels the congestion is contained between* — a
pair, not a per-edge snap, so both golden edges can sit on the same
side of the envelope midline (the mixedge lesson).

**Measured (canonical `_m1`, flag-OFF ≡ STABLE 0/198 at every hash):**

| arm @hash | box@1 | lvl@1 | line@2 | brk@1 | oracle | clutter |
|---|---|---|---|---|---|---|
| p7_base 91c44677 | 9/119 | 6/76 | 20/193 | 29/85 | .417 | 5.00 |
| p7_pedg 91c44677 | **10/119** | **7/76** | 20/193 | 29/85 | .426 | 5.33 |

Proposal coverage +3 (9.44b g1, 9.47b g0, 9.50b g0 — three of the
eight envelope-reachable goldens), zero losses.  §34.5: legs 1–2–4
pass, **leg 3 fails (clutter 5.33 > 5.0)** → lever, not a keep.

**Pareto frontier (all measured):** npairs 6→3→2 trades gain for ink
linearly (10/9/9); topk=3 and minmem=2 both lose the box@1 flip (the
winning pair needs a rank-3/4 or singleton-member cluster); minrun=12
keeps the gain but births stay 1.55/panel; emit-on-change + extreme
dedup cut cand_log volume ~20% but births are the binding ink (≈54
born extras, net +2 live objects across 8 panels — the median was
already on the 5.0 boundary).

**Why it matters despite failing:** this is the first generation
variant since `cong_trigger` that adds *real* coverage (+3 goldens
covered, +1 box@1, +1 level@1).  The ink cost is a birth-side problem:
pedg cands pass scoring whenever a slot is free.  A salience-side
gate (pedg-tagged cands yield when a same-geometry box exists or
score below live incumbents) is build-lane territory — specced in
REQUESTS.md.  With births bounded to golden-relevant wins, this
mechanism is worth re-running next round on top of any kept fixture-
debt changes (yield-not-evict would change the slot math anyway).

## R50/R51 additions (C-round 2, STABLE 9acaa206 -> K7 81f7503f)

**Covered-but-missed anatomy** (`c1_missed.py`): 55/119 BOX goldens have
an edge-matching proposal by tau; 9 hit, 46 missed.  Zero misses are
born-then-lost: the funnel kills the right box BEFORE birth.
below_min_score 14 | wick-stream log_only 11 | outranked 10 |
rate_limited 8 | expired 3.  Selection-side = 35/46; that is the
build lane's territory (score floor / displacement / rate window).
Integration meaning: generation already proposes the right band for
46% of misses; more generation cannot fix a birth-gate loss.

**Pivot-support score term — design-level negative** (`c1_pivsup.py`).
Two-edges-on-confirmed-pivots saturates: 89% of score-starved RIGHT
cands and 96/103 of the wrong boxes that beat them (at their own birth
bar) both carry full support.  No separation -> the term would be a
disguised floor cut that lifts wrong cands equally.  Not implemented.

**wick_birth on K7** (`p_wick` same-process pair @81f7503f): pools the
cluster_range_wick variant stream for real.  box@1 8/119 (-1 vs 9),
oracle .407, lvl +1, line +1.  The 11 log_only goldens do NOT convert;
wick variants steal family slots from better boxes.  Rejected — the
log_only bucket is a dead lever, do not re-arm.

**pivedge on K7:** formal A/B is the build lane's (PERCEPTION_LOG 582,
headroom parent 81f7503f, clutter starts 4.67 -> the 5.33 ink may now
fit leg 3).  Arm kept at impl defaults (npairs=6/top-4/sig-memo).

## R53 / PLAYBOOK_C2 additions (K8 era)

**Score-floor anatomy (X3, `c1_pivsup.py`/`p_deep0`):** the below_min_score
bucket's dominant deficit is `deeper_lv` — starved cands carry median
deeper 4 (−6.0 pts) vs born median 1 (−1.5).  Golden congestion boxes are
nested inside prior structure by construction, so the −1.5·deeper term
systematically kills the right bands.  BUT `box.deeper_w=0` (only value
with reach — 0.75 clears zero starved cands) measured FAIL: coverage +1
yet box@1 −1, level −1, born/pan 1.56→2.40.  The freed births are wrong
boxes.  Verdict: the floor problem is structural — the score conflates
"nested = suspicious" with "nested = congestion".  Not a weight fix.
(`box.deeper_w` knob left in boxes.py, default 1.5 = inert.)

**Rate-window replacement (X2):** handed to build lane (R53 §53.1) —
spec in REQUESTS.md.  Pre-diagnosis: only 9.17b of the 8 rate-limited
right cands clears floor AND outscores the holder (5.66 vs 5.5).
Ceiling ≈ +1 box.

**Level registry vs density-matched null (`c1_registry.py`):** on the 65
no-pooled-coverage goldens — piv .708 (null .502/.585) KEEP; cext on the
TRIGGER window .400 (null .389/.477) DROP — EVAL-AUDIT's circularity
concern confirmed; sess .046 (null .044/.062) DROP; union .815
(.618/.708) KEEP but pivot-driven.  Registry design conclusion: carry
confirmed pivots only.

**Where the remaining gap lives:** box@1 10/119 vs v0 16.  Coverage is
57/119 and 47 of the covered-missed die pre-birth on score/slot/rate —
selection territory.  Generation-side residual: 62/119 goldens have NO
edge-matching proposal at all; ~12 of the 65 no-coverage goldens sit on
no standard causal structure (registry union misses them).

## R54 addendum — score-starvation class mapped and closed in boxes.py (14:15Z)

§54.5 names score starvation the round's main lever class (boxes AND
levels: 18 priced level misses die at the birth gate at 0.6–2.4 vs 7–9
born).  For BOX, every starvation dial inside boxes.py is now measured:

| dial | reach | result |
|---|---|---|
| `deeper_w=0` (full removal) | ~8 goldens' cands clear 5.0 | A/B FAIL: births 1.56→2.40/pan, box −1, level −1 — freed pool is mostly wrong cands |
| `deeper_cap=2` (saturating) | 0/31 starved cands reach 5.0 | dead pre-A/B by arithmetic |
| prom/contain/touches/barrier | — | no failure mechanism; adjusting = weight-fitting (§3.6) |

`outranked` corrected: budget displacement vs weakest live structure
(salience.py:1318, dwell/prio/hyst), not score-vs-incumbent.  Right
cands scored 0.5–15.4 and still lost slots.

**Boundary:** the starvation class lives in salience.py — floor
(`min_score_birth_signal`), budget displacement, dwell, rate window.
All are build-lane file + thresholds.  BOX-LAB has no remaining
principled lever here; logged for the Lead (§8.4).

## R56-57 addendum — research round: X.S registry closed, selection-side is the surviving lever (16:05Z)

**X.S level-registry:** the no-edge golden count is now measured at 62
(no-coverage) with ~12 residual no-causal-structure.  Under EVAL-AUDIT's
density-matched null (R57 §57.2), pivots do NOT beat density
(.711 vs p95 .763) — the earlier in-lab pass (.708 vs .585) used a
weaker null.  Pivots are a *generator*, not evidence for which box to
pick; a registry built on them has no selection evidence.  X.S closes
as "no surviving source" — the registry idea is archived, not built.

**Research-round outcome (BOX_RESEARCH.md R1–R3):**
- R1: 119-row author-vs-engine table, 30 renders, setup tags, 200-draw
  hypothesis nulls + R57 causal re-test.  83/107 wrong picks are stale
  `structural_envelope` objects.
- R2: A2 segmentation dead twice (28/119, 15/119); A2' level-pair dead
  across 5 deterministic rules (<=10/119 vs 82/119 edge reach).
- R3: **no rule-based boxes.py prototype survives** — the separating
  signal (liveness: close[tau] inside/near band, fresh touch, recent
  span-end) exists only at evaluation time, not at proposal time
  (97-99% of ALL cands contain price at emit).  The surviving
  formulation is selection-side:
  **A1 current-episode scope + A3 liveness birth-order**, both handed
  off via REQUESTS.md; `ESCALATE: A3 ready` logged for the Lead's fit
  (pooled CV cell@1 18/57=.316 vs shuffle p95 .298, baseline .088;
  birth-floor caveat disclosed — only 3/18 hits clear 5.0 today).

## R58–R59 addendum — selection class CLOSED by measurement; the residual is representation (16:45Z)

**Final verdicts on the selection-side programme (all official A/B or
arithmetic, none mine-alone):**

- `lvb_on` (@29de0689): **FLAT** — every M1 metric ≡ off
  (box 10/119, level 8/76, line 20/193, bracket 29/85, clutter 4.33).
  Independently re-counted cache-only by BOX-LAB.  The birth gate
  cannot discriminate because ~97% of all candidates are inside
  their own band at emit-time; staleness develops *after* emission,
  inside the object lifecycle — a gate at the proposal boundary is
  the wrong lifecycle point by construction.
- `a4_on` (@b1d94617): INERT — containment-liveness at birth never
  fires (proposals form around current price).
- `a4b_on` (@54bd315b): FAIL −2 box — edge-proximity eviction kills
  right picks; an incumbent whose edge is being tested is often
  *the* right pick.
- recency-order contest: arithmetic-dead pre-A/B — incumbent
  CONTEXT_RANGE has `recency_bars=0` in ≥75% of cells (envelopes
  update every bar: temporally fresh, positionally stale).
- A3 fitted ranker: reproduced byte-identical in the Lead's cloud
  (18/57 = .316) but matched by a stated `recency+age` rule
  (21.5/57) — closed, no fitted ranker deployed anywhere.

**One residual axis measured, not armed (18f):** positional staleness
of the incumbent *at eval-τ* — the pick's band misses current price
in 61/115 cells (CONTEXT_RANGE 52/80).  Ceiling: 28 cells where a
live+born right cand sits under a stale pick.  Exposure: 4/10 current
hits ride stale picks, and the author's "kept past the break"
convention makes the matched golden itself positionally stale at τ —
staleness is partly a *rightness* signal, so expected value is
genuinely ambiguous.  Details in REQUESTS.md addendum.

**Lane conclusion for integration:** the envelope-vs-box contest is a
*representation* question (ctx_convert direction — the author draws a
tight box where the engine keeps a wide envelope), not a selection
one.  BOX-LAB's geometry lane produced no surviving rule-based
prototype under §3.6; the boundary is documented, not shipped.
