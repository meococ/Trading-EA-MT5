# BOX-LAB — X3 prototype rounds

Ruler: `evalcheck/eval_v2.py` `50e11fd5a2ab7974` + `funnel.cand_right`
(prefix rule, §11.2).  TUNE v2 only.  Golden BOX = 108 scorable
(trusted subset = 68, `cache/box_audit.jsonl`).
198 panel runs per row (engine re-run per panel, day bars ≤ w1).

"oracle" = golden BOX with ≥1 right candidate; "born" = eval_v2
containment-IoU match on born objects; "born/panel" = born BOX objects
whose drawn span intersects the panel window; "live@τ" = live boxes at
golden τ=build_end (snapshot lens, §13.2) — metric added in r17,
earlier rows n/m.  `hash` = boxes_lab.py sha256[:16]; per-round hashes
were not snapshotted before r16 (process gap — fixed from r17).

| rd | what changed | oracle | born | born/panel | live@τ | hash |
|----|--------------|--------|------|-----------|--------|------|
| r1 | first causal pivot-pair proposer; born at formation, no budget | 21 (.194) | 38 (.352) | 37.6 | n/m | n/s |
| r2 | multi-anchor cand emission (run/first_edge/last_piv) | 39 (.361) | 1 (.009) | 0.46 | n/m | n/s |
| r3 | event-driven emit; edge = deepest-with-company, lone_gap | 54 (.500) | 1 | 0.97 | n/m | n/s |
| r4 | contacts relax (edge≥1, sum≥3) | 54 (.500) | 1 | 1.28 | n/m | n/s |
| r5 | watchlist + break-triggered birth v1 | 54 (.500) | 0 | 0.65 | n/m | n/s |
| r6 | born window recomputed at break (regression: micro-run collapse) | 54 (.500) | 0 | 0.55 | n/m | n/s |
| r7 | born_t0 anchor restored | 54 (.500) | 1 | 1.58 | n/m | n/s |
| r8 | watch born-flag persistence fix | 54 (.500) | 1 | 1.60 | n/m | n/s |
| r9 | break+mature birth, cap 8/day, slot 45min | 54 (.500) | 4 | 2.33 | n/m | n/s |
| r10 | R9a barrier-gate on broken edge (too strict: 1-pivot edges die) | 54 (.500) | 0 | 1.45 | n/m | n/s |
| r11 | emit_anchors ×5 (+first_piv, prev_piv) | 60 (.556) | 3 | 2.14 | n/m | n/s |
| r12 | birth_edge_ok (≥2 contacts or persistent non-spike) | 60 (.556) | 2 | 2.06 | n/m | n/s |
| r13 | NMS runner-up fix (skip blocked winner, take next) | 60 (.556) | 2 | 2.05 | n/m | n/s |
| r14 | birth gates: hgt≤32p, prom_sum≥5·ABR, n_piv≤7, persist≥4, span≥6 | 60 (.556) | 2 | 2.06 | n/m | n/s |
| r15 | score → prom_min/ABR + (8 − hgt/ABR) | 60 (.556) | 2 | 1.90 | n/m | n/s |
| r16 | same score, verified; gates as r14 | 60 (.556) | 2 (.019) | 1.88 | n/m | d9ccae0a1e579391 |

Trusted subset (n=68): oracle 45 (.662), born 2 (.029) at r16.

## Post-R17 protocol rounds (live budget, snapshot lens, recall@k)

Columns: oracle / born (eval_v2 `50e11fd5`) / prec = edge-valid share
of born objects / born·p = born boxes per panel / live@τ = median live
boxes at golden τ=build_end / r@k = snapshot recall with top-k live /
flick = changes to the live top-2 set per hour (median across panels).
Per-round file hashes were not snapshotted for r17–r28 (process gap,
logged); `cache/boxes_lab_rNN.py` snapshots start at r29.

| rd | what changed | oracle | born | prec | born·p | live@τ | r@1 | r@2 | flick/h | hash |
|----|--------------|--------|------|------|--------|--------|-----|-----|---------|------|
| r17 | live budget ≤2 + score displacement replaces day cap; mature_bars 24→6 (birth at knowable moment); barrier term +0.75·(levels pre-dating run) | 60 (.556) | 31 (.287) | .011 | 21.70 | 1.00 | 10 | 14 | 0.51 | n/s |
| r18 | birth_score_min=4.0 wired (was dead param); nested dedup vs same-day born | 60 | 10 (.093) | .012 | 4.16 | 0.00 | 3 | 3 | 0.17 | n/s |
| r19 | dedup upgrade-aware: same-episode born only blocks if not clearly weaker (−0.5) | 60 | 16 (.148) | .013 | 6.87 | 0.00 | 6 | 6 | 0.26 | n/s |
| r20 | envelope gate: ≤2 non-spike pivots deeper than edge+tease inside window | 60 | 17 (.157) | .015 | 5.91 | 0.00 | 5 | 6 | 0.23 | n/s |
| r21 | live edge tracking: born edges follow source-level repricing (edge_move events) | 60 | 17 (.157) | .015 | 5.94 | 0.00 | 5 | 6 | 0.22 | n/s |
| r22 | score += −0.8·edge_gap (own-window p95 wick); multiple same-event breakers may birth | 60 | 17 (.157) | .017 | 5.77 | 0.00 | 7 | 8 | 0.23 | n/s |
| r23 | gates relaxed (hgt≤45p, prom_sum≥3·ABR, n_piv≤10) | 60 | 16 (.148) | .013 | 7.00 | 0.50 | 7 | 8 | 0.27 | n/s |
| r24 | birth bs = fresh run-walkback from be (regression, reverted) | 60 | 13 (.120) | .011 | 6.53 | 0.50 | 9 | 10 | 0.25 | n/s |
| r25 | birth bs = first in-run edge pivot (regression, reverted) | 60 | 10 (.093) | .009 | 6.41 | 0.50 | 7 | 8 | 0.25 | n/s |
| r26 | persist≥2 / span≥5 / mature_bars=4; qual-time anchor restored | 60 | 15 (.139) | .013 | 7.56 | 0.50 | 6 | 6 | 0.31 | n/s |
| r27 | supersede: stronger same-episode birth closes weaker live box (live@τ collapsed — break-time supersede kills pre-τ boxes) | 60 | 18 (.167) | .013 | 8.44 | 0.00 | 5 | 5 | 0.31 | n/s |
| r28 | **BROKEN drawn-tail state** (tail_bars=45): box stays drawn past the break (author tail ~60 min); build_end = break bar; budget cuts broken tails before displacing live | 60 | **19 (.176)** lab conv; 18 (.167) ruler conv (`meta_build_end`=proposal bar, §21.5) | .012 | 9.49 | **2.00** | 7 | **10** | 0.21 | n/s |
| r29 | score: −0.8·edge_gap → −1.5·deep_piv (regression: own-window pivots miss the deciding pivot — it precedes both windows) | 60 | 13 (.120) | .008 | 10.65 | 2.00 | 1 | 4 | n/m | b5dce8bd |
| r30 | deeper_lv feature (defended lvls deeper than edge, ~1 ABR, window-independent); hgt term dropped (R20); tail 45→12 (§21.3) | 60 | 8 (.074) | .020 | 2.55 | 0.00 | 6 | 6 | n/m | cache/boxes_lab_r30.py |
| r31 | birth floor 4.0→1.2 (rescale after hgt removal) | 60 | 13 (.120) | .014 | 6.58 | 1.00 | 9 | 9 | n/m | cache/boxes_lab_r31.py |
| r32 | deeper_lv added ON TOP of r28 score (hgt+edge_gap kept); floor 3.0 | 60 | 19 (.176) | .018 | 7.22 | 1.00 | 11 | 12 | n/m | cache/boxes_lab_r32.py |
| r33 | barrier sign FLIPPED (anti-predictive: P(right\|barrier=0)=.92% vs .2%) + barrier_near feature measured (also anti-predictive) | 60 | **21 (.194)** | .025 | 5.30 | 1.00 | **16** | **16** | 0.20 | cache/boxes_lab_r33.py |
| r34 | score += −0.5·barrier_near (slight regression — reverted) | 60 | 19 (.176) | .025 | 5.02 | 1.00 | 15 | 15 | n/m | cache/boxes_lab_r34.py |
| r35 | birth geometry = watch's **best-ever qualified snapshot** (edges freeze at best-qual emit); edge_track OFF; break detect on best edges | 60 | 18 (.167) | .019 | 6.09 | 1.00 | 13 | 13 | n/m | cache/boxes_lab_r35.py |
| r36 | same_episode = same-edge NMS only (nested-window branch removed — wrong-window blockers were preempting right watches) | 60 | **28 (.259)** | .015 | 16.02 | 2.00 | 14 | 25 | n/m | cache/boxes_lab_r36.py |
| r37 | same_episode = same edges AND window IoU ≥ .5 (right-edge/wrong-window births no longer preempt) | 60 | **30 (.278)** | .015 | 17.49 | 2.00 | 14 | **26** | n/m | cache/boxes_lab_r37.py |
| r38 | birth floor 3.0→3.5 (ink probe: −13% births, −2 matches) | 60 | 28 (.259) | .016 | 15.13 | 2.00 | 14 | 24 | n/m | cache/boxes_lab_r38.py |
| r39 | emit anchors += `mn_touch` (earlier edge's first in-run touch), `mx_touch`, `tf_max` (later edge t_first) — targets the 18 start-anchor oracle misses | 60 | 30 (.278) | .015 | 17.49 | 2.00 | 14 | 26 | 0.32 | a9b1847a895d |
| r40 | nest_iou_min .5→.35 probe (no change — same-episode pairs overlap ≥.5 anyway); reverted | 60 | 30 (.278) | .015 | 17.20 | 2.00 | 14 | 26 | 0.32 | 64ff35d2a190 |
| r41s | SHUFFLE CONTROL (R23 §23.3): deeper_lv+barrier permuted in-panel | 60 | 33 (.306) | .009 | 35.75 | 2.00 | 16 | 20 | n/m | runtime flag |
| r41 | reemit_bars 24→6 (pre_window cands existed but were dropped by cand_as_record t1m<w0) | 60 | 31 (.287) | .013 | 18.68 | 2.00 | 13 | 24 | n/m | cache/boxes_lab_r41.py |
| r42 | `allpiv` anchors: one cand per recent in-run pivot bar (cap 8) — targets in_window_wrong_t0 | 63 (.583) | 31 (.287) | .013 | 18.68 | 2.00 | 13 | 24 | n/m | cache/boxes_lab_r42.py |
| r43 | **provisional DC-leg-extreme levels** (unconfirmed running extreme as edge; levellab `leg` origin pattern) | **68 (.630)** | 31 (.287) | .012 | 21.41 | 2.00 | 13 | 23 | n/m | cache/boxes_lab_r43.py |
| r44 | max_level_age_bars 144→288 (stale-level hypothesis — flat, kept) | 68 (.630) | 31 (.287) | .012 | 21.44 | 2.00 | 13 | 23 | n/m | cache/boxes_lab_r44.py |
| r45 | `_try_form` every bar (drop `_dirty` gate) — flat; no_intime_emit is not cadence | 68 (.630) | 31 (.287) | .012 | 21.44 | 2.00 | 13 | 23 | n/m | cache/boxes_lab_r45.py |
| r46 | emit watch's best-ever edges as extra cands (repricing hypothesis — flat; located .769→.778) | 68 (.630) | 31 (.287) | .012 | 21.44 | 2.00 | 13 | 23 | n/m | cache/boxes_lab_r46.py |
| r47 | **wick-tip edge variants** (p99/p01 of run wicks) — golden edges sit on lone spikes the level design excludes | **72 (.667)** | 31 (.287) | .012 | 21.44 | 2.00 | 13 | 23 | n/m | cache/boxes_lab_r47.py |
| r48 | + absolute run extremes (max/min) — flat vs r47 | 72 (.667) | 31 (.287) | .012 | 21.44 | 2.00 | 13 | 23 | n/m | cache/boxes_lab_r48.py |

## Dead ends worth keeping on record

- **Day-level birth cap is the wrong budget.** r9–r16: cap 8/day is
  exhausted before the golden break (e.g. 9.4b: 10 births by min ~475,
  golden break ~820 → right band blocked). §17.3 reframes budget as
  *live* boxes, not cumulative births.
- **Break-edge barrier gate (r10).** Golden breakout edges are often
  single fresh pivots — requiring a pre-existing defended level at
  birth killed every birth.
- **Born window recompute at break (r6).** Walking back from the break
  bar lands on a post-drift micro-run; the anchor recorded at
  qualification time is the right bs.
- **Selection AUC protocol.** `select_eval.py` on the r3 pool
  (127 221 cands, 469 right): no feature ≥0.60 AUC on every day-fold.
  `-hgt` ~0.686, `-hgt_abr` ~0.617, `prom_abr` ~0.584 overall but not
  fold-stable. Lab-stream numbers are hypotheses only (§15.1).

## Current blocker (post-r28, updated 20:50Z)

Snapshot coverage is solved: every golden τ has ≥1 live box
(live_any 108/108, median 2.0).  The loss is now purely upstream:
**41/60 oracle-hit goldens never get a born object with right
edges** — the right band loses the birth race to stronger-scoring
same-episode siblings (nested inner bands) or is dedup-blocked by
them.  Of the rest: 10 live-at-τ, 7 born after τ, 5 killed before τ
(mostly supersede churn, fixed by the r28 tail).

Also measured post-r28: the r22 `edge_gap` term is doubly wrong —
computed on the band's own window it lets late-anchored inner bands
escape, AND it penalises golden bands for lone-spike wick texture
(9.4b golden pair scored −0.43 at one point, below the birth floor).
The audit-consistent discriminator is `deep_piv` (non-spike pivots
beyond an edge): the golden edge sits ON the deepest defended pivot.
r29 swaps `−0.8·edge_gap` → `−1.5·deep_piv`.  r30 drops the `hgt`
term (failed on the production stream, R20 §20.2) and sets
`tail_bars=12` (golden tail ≈60 min on 5-min bars, §21.3).

> Correction (R25 §25.6): stamp "~22:35Z" was hand-written; file
> written 21:32:44Z (R14). From now on every time in this file comes
> from `logline.py --now` or `date`.

## Final state (post-r40, ~22:35Z)

**Best round: r37** (config restored after r40 probe) — born recall
30/108 = **.278 > v0's .21** at live@τ 2.0 (author's budget met);
recall@2 26/108 = .241; ink 17.5 born/panel is the residual cost.
The ink↔recall trade is a frontier, not a knob: r33 hit .194 at
ink 5.3; r37 hit .278 at 17.5.  Raising the birth floor (r38) or
tightening window-overlap dedup (r40) each costs ~2 matches for
~10% ink.  Cumulative-ink discipline needs an episode-complete
signal the causal stream cannot see; X4 proposes the engine-side
fix (budget the drawn tail, not births).

Oracle ceiling (r47): **.667** (72/108; trusted 53/68).  Full
miss taxonomy after the r41–r48 generation probes (~36 misses):
- **9 unwinnable by construction** — funnel clamps cand t0 to the
  panel window w0; golden `build_start < w0 − 20 min` can never
  satisfy the ±20-min rule.  True ceiling ≈ 99/108 = .917.
- **~19 no-edges** — the golden edge price never becomes any causal
  structure: not a confirmed-pivot level, not an unconfirmed leg
  extreme (r43 added those), not a day/session running extreme
  (covers ~half), mostly one side missing (10 hi_only / 8 lo_only
  on the unpruned book).
- **8 no-intime-emit** — right-edge pair exists but `band_ok`
  containment fails inside the scored window (not cadence: r45
  flat; not repricing: r46 flat).
- **4 wrong-t0** residual.

Generation levers that WORKED: r42 allpiv anchors (+3 → .583),
r43 provisional leg-extreme edges (+8 → .630), r47 wick-tip edge
variants (+4 → .667).  Probes that did NOT move it: r44 level-age,
r45 emit cadence, r46 best-edge re-emit, r48 absolute extremes.
The residual ~14 no-edge misses need a mid-band/eye-level edge
source — documented for the build lane.

## Cross-validation + controls (R23 §23.3 / R25 §25.6)

Weights are **frozen** (hand-set on all 108 goldens; nothing is
re-fit inside folds).  Folds = `select_eval.folds`, day-level
5-fold, the same split LEVEL-LAB uses.  CI = day-cluster bootstrap
(B=2000, seed 7).  Caveat: CV bounds fold-level variance of the
fixed scorer only — it does not remove the global hand-tuning bias.

| round | born CV [CI] | r@1 CV [CI] | r@2 CV [CI] | ink/panel |
|---|---|---|---|---|
| r33 | .194 [.127–.274] | .148 [.093–.207] | .148 [.093–.207] | 5.30 |
| r37 | .278 [.198–.357] | .130 [.074–.185] | .241 [.168–.316] | 17.49 |

Per-fold born recall is positive on every fold for both rounds
(r37: .235/.259/.292/.263/.333; r33: .211/.148/.208/.176/.238).

**Barrier sign per fold** (P(right | barrier=0) vs barrier≥1 on the
r33/r37 candidate stream — identical streams): anti-predictive on
ALL 5 folds — f0 .0058/.0029, f1 .0091/.0022, f2 .0123/.0018,
f3 .0043/.0002, f4 .0050/.0029.

**Shuffle control** (tag `lab_r41s`, seed 11): deeper_lv and barrier
permuted within each panel via a prefix pool in `_score`.  Result:
born .306 (NOT back to r28's .176 — say so per §23.3), r@1 .148,
r@2 **.185** (down from .241), ink doubled to 35.75.  Reading:
the features carry real ranking signal at τ (r@2 falls ~6 pts when
shuffled), but cumulative born recall is ink-limited, not
score-limited — with the ranking destroyed the engine births 2×
more objects and covers more goldens by volume.  The control
therefore validates the features for *snapshot selection* and
confirms ink, not score, bounds cumulative recall.  Single seed;
logged as such.
