# BOX-LAB -> build lane hand-offs (C-round 1, R34/R35/R36/R37)

Build lane reads this file. Each entry: flag name, default, A/B rows, hash.

All flags live in `boxes.py`, namespaced `box.*`, default OFF. Flag-OFF
reproduces parent objects + cand_log on 198/198 panels (verified
`f23646a8` vs `fbf0b920`).

**Measurement provenance.** One sweep, one process, params frozen at
process start (R36 §36.7). Frozen-params snapshot:
`boxlab/c1_runs/params_frozen_*.json`. The disk tree drifted mid-run
(build lane edits); the process's behaviour did not — code fixed at
import, params frozen. Pickle labels fragmented across the drift:
`b9f968b1` (base/leg/wick/dense/dedup), `ffd74452` (watch/tail/
watchtail), `3ab5f3aa` (all/watch_fl), `e62f2dc9` (base/score/wd/
tail6/gen rerun after asia-route rank_score coverage fix).
M1/keep-rule numbers below are from `_m1.py` run cache-only over
those pickles (`boxlab/c1_m1.py`) — canonical clutter scale
(STABLE=5.00). Oracle/born columns from `boxlab/c1_ab.py`.

The pre-freeze `boxlab/c1_runs/c1_*` JSONs are void per R36 §36.7
(logged, not deleted).

## Headline

**No flag satisfies §34.5 on this parent.** Two levers are worth the
Lead's call anyway; the rest are rejects or hand-offs.

## A/B rows (vs frozen base; canonical _m1 numbers)

| arm | flag(s) ON | BOX oracle | box@1 | lvl@1 | line@2 | brk@1 | born BOX | born/pan | clutter | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| base | — | .287 (31/108) | .025 (3/119) | .053 (4/76) | .093 (18/193) | .329 (28/85) | .046 (5/108) | 2.31 | 5.00 | — |
| leg | `leg_edges` | .287 | .025 | .053 | .093 | .329 | .046 | 2.31 | 5.00 | inert — not keep |
| wick | `wick_edges` | **.352 (+7)** | .025 | .053 | .093 | .329 | .046 | 2.31 | 5.00 | coverage lever* |
| dedup | `dedup_iou` | .315 (+3) | .025 | .053 | .093 | .329 | .046 | 2.31 | 5.00 | coverage lever* |
| dense | `dense_anchors` | .315 | **.008** | .053 | .088 | .318 | .028 | 2.32 | 5.00 | REJECT (box −2) |
| watch | `watch_birth` | .324 | .017 | .039 | .088 | .341 | .046 | 1.95 | 5.00 | fail (box −1) |
| tail | `tail_bars=12` | .296 | **.034 (+1)** | .066 | **.083 (−2)** | .353 | **.083 (9/108)** | 2.33 | 5.00 | fails by 1 extra line hit |
| tail6 | `tail_bars=6` | .296 | .034 | .066 | .083 | .353 | .083 | 2.33 | 5.00 | same — not length-dependent |
| watchtail | watch+tail | .324 | .017 | .053 | .073 | .341 | .046 | 1.94 | 5.00 | reject |
| score | `rank_score` | .287 | .025 | .053 | .093 | .329 | .046 | 2.31 | 5.00 | inert by design ✓ |
| all | all six+score | **.398 (+12)** | .008 | .039 | .073 | .341 | .009 | 1.94 | 5.00 | reject (selection collapse) |
| watch_fl | watch+famledger+fambudget | .324 | .025 | .026 | .098 | .282 | .037 | 2.15 | **5.33** | fail; watch stays flat even under fambudget |
| **wd** | `wick_edges`+`dedup_iou` | **.407 (+12)** | .025 | .053 | .093 | .329 | .046 | 2.31 | 5.00 | **the coverage package** |
| gen | leg+wick+dense+dedup | .407 | .008 | .053 | .088 | .318 | .028 | 2.32 | 5.00 | reject — dense is the harm |

\* coverage levers: proposal-stream only. Oracle up, every selection
number identical to base. §34.5's letter requires box@k to *increase* —
a pure coverage change cannot satisfy it by construction (it never
touches ranking). The Lead decides whether the rule admits them.

## The hand-offs

### 1. `box.wick_edges` + `box.dedup_iou` (recommend as pair "wd")
- default OFF; turning both ON is the free oracle move:
  oracle .287 → **.407** (+12 of 108 goldens get a right proposal),
  zero delta on every M1 family, born rate, clutter.
- mechanism: wick-tip (p99/p01) and window-IoU dedup widen the proposal
  stream only; births unchanged (458/panel-day both arms).
- flags: `box.wick_edges=True`, `box.dedup_iou=True`, constants
  `_NEST_IOU=0.5` (in boxes.py, build moves to params if kept).
- hash: measured at `e62f2dc9` (arm `c1r_wd`) and `b9f968b1`
  (single flags) — same numbers.

### 2. `box.tail_bars` (pre-existing §32.1 flag, extended)
- I added `meta_build_end = decisive-close bar` under the flag (X4 #2 —
  the ruler reads meta_build_end as the window end; golden build_end ~
  first decisive close).
- tail_bars=12 and =6 both: box@1 +1 (.034), lvl +1, **line −2**,
  born BOX recall .046→.083. Fails §34.5 by ONE extra line hit.
- Hand-off flagged: if `fam_budget`/per-family lands, retest — the
  line drop is a shared-budget interaction, likely heals under
  per-family accounting.

### 3. `box.rank_score` (output field only)
- `o.geometry["meta_box_rank"]` + `sali.feats.box_rank` +
  `cand_log` rows carry `box_rank`/`deeper_lv`. Now covers ALL box
  birth routes incl. `asia_session`/`asia_convert`.
- **Identity proven**: stripped-equal to base on 198/198 panels
  (objects+cand_log, same hash `e62f2dc9`).
- LODO day-fold check (`boxlab/c1_score_cv.py`): box@1 under box_rank
  1/104 vs engine score 3/104; dominance 2/3 coverable. **The ported
  lab ranker has no edge on the engine's live set** — its lab
  advantage lived on the lab's richer proposal stream. Field is
  delivered for downstream use; do not wire it into selection on
  these numbers.
- hash `e62f2dc9`.

### 4. `box.watch_birth` — hand off, not keep
- Deferred birth (watch→break/maturity emit) cuts born/pan 2.31→1.95
  and lifts oracle +4, but box@1 −1 standalone and flat under
  famledger. The lab mechanism (best-qualified snapshot at draw
  moment) did not transfer — engine candidate scoring differs.
- Keep OFF; revisit only if the famledger world becomes parent.

### 5. `box.leg_edges` — inert as implemented
- Extends an already-qualified band to the running DC-leg extreme;
  never fires productively (0 delta). The lab version *generated*
  edges where no defended level existed — that needs an edge-source
  change, not a proposal variant. Logged as dead end at this scope.

### 6. `box.dense_anchors` — rejected
- Oracle +3 standalone but box@1 −2, and it is the harm inside `gen`.
  The extra `t0` shots mainly let wrong-window variants win.

## What remains (next round)

**The binding wall is the birth-rate gate, not ranking**
(`boxlab/c1_killtrace.py`, run on the `wd` arm):
- 42/108 goldens have a right proposal in the stream (oracle .407).
- **26 of them die `rate_limited`** — `rate_box=1` per 72-bar window,
  plus shared `rate_total`. Only 3 birth. 3 NMS, 10 sit un-scored.
- Under `watch_fl` (famledger+fambudget ON): still 22 rate-killed,
  **zero** right-cand births — `fam_rate_box=1` is the same cap.
- So per-family budgets alone do not unblock box births; the rate
  window itself is the gate. That is `salience.py`/params — build
  lane. Every generation lever I own is already live under `wd`.

- Selection is the wall after birth: box@1 .025 vs v0 .134 while
  oracle is .407. box_rank as ported does not beat the production
  score — the next lever is a ranker trained on the ENGINE's live
  set, not the lab's.
- 9/108 goldens are structurally unwinnable (funnel clamps t0 to w0;
  golden build_start < w0−20min) — ruler/funnel boundary, not a flag.

## R38 addendum (~05:1xZ) — the rate wall, instrumented

R38 §38.3 items done. New arms (same-hash, frozen params; box@1 and
born recall below are canonical `_m1.py` numbers, oracle from
`c1_ab.py` — same method as the accepted sweep):

| arm | flags | oracle | box@1 | born BOX rec | born/pan | clutter | note |
|---|---|---|---|---|---|---|---|
| wdtail | wd+`tail_bars=12` | .407 | .034 (4/119) | .083 | 2.33 | 5.00 | tail stacks on wd, same line −2 |
| wd_wb | wd+`wick_birth` | .398 | .025 (3/119) | .056 | 2.31 | 5.00 | §38.3.2: wick cands DO birth (~0.9/panel) but mostly die rate_limited/expire — selection flat |
| wd_kde | wd+`kde_edges` | .407 | .017 (2/119) | .037 | 2.31 | 5.00 | §38.3.3: KDE adds nothing — `_variants` fires only on already-qualified bands; residual misses never reach it |
| wd_wb_kde | wb+kde | .398 | .025 (3/119) | .056 | 2.31 | 5.00 | = wd_wb |
| wd_watch | wd+`watch_birth` | .398 | .017 (2/119) | .046 | 1.95 | 5.00 | deferred birth does NOT dodge the rate gate |
| wdw_wait | wd+watch+`wait_ttl` | **.417** | .017 (2/119) | .046 | 1.95 | 5.00 | best oracle; selection worst-ish |
| wd_ext | wd+`salience.rate_blocked_extend` | .407 | .017 (2/119) | .037 | 2.31 | 5.00 | **flag inert as implemented**: extends expiry to `blocking_birth+1`, not `blocking_birth+72` — for `cap_r=1` the cand still dies ~38 bars before the window frees |
| wd_ext_fl | wd_ext+famledger+fambudget | .398 | .025 (3/119) | .037 | 2.16 | **5.33** | within noise; clutter fails |
| wd_wait | wd+`box.wait_ttl` (new flag) | .407 | .017 (2/119) | .019 | 2.31 | 5.00 | cand SURVIVES the window (expired −35%) yet births flat — on retry NMS re-compares vs the incumbent's CURRENT score; decay flips it (`nms_suppressed`, permanent) |
| wd_wb_wait | wb+wait | .398 | .025 (3/119) | .037 | 2.31 | 5.00 | = wd_wb |
| wd_wb_fl | wb+famledger+fambudget | .398 | .025 (3/119) | .037 | **0.70** | 4.50 | fambudget starves box births to 0.7/pan |

**The mechanism that fits: `lc_score_pick` generalized to `fam=="box"`.**
salience.py L716-775 already implements score-pick supersede inside
the rate-blocked branch for `level_carried`: a blocked cand scoring
> holder's CURRENT `act_scores` value + `hyst_margin` takes the slot,
the incumbent closes "superseded", the ledger entry MOVES (no extra
ink rate). The box analog is ~15 lines (`fam == "box"`, holders =
`o.type == "BOX"`).

Offline estimate (`boxlab/c1_supersede.py`, wd arm): of 30
rate-killed goldens, supersede would fire for
- **2** vs the holder's BIRTH score (strict lower bound), and
- **16** vs the holder's decayed end-of-panel score (loose bound).

Measured arrival: the right cand's first rate_limited lands a median
**39 bars** after the holder's birth (IQR 17-58, n=52 blocked rows) —
mid-window, so the holder's act_scores at the block bar has partially
decayed → true count likely ~10-16, i.e. box@1 .025 → roughly
**.11-.16**, near v0's .134. The flag also fires for wrong cands (any
high-scored blocked box proposal) — Arm B's spec-priority gate
(contains current price / holder is a box price left) is the filter.
Net effect needs the real A/B; this is the build lane's call and file.

## R40 §40.4.2 verdict (06:17Z) — supersede arms @ `cfb862d4`, measured

Real A/B landed below the estimate — supersede fires less often than
the loose bound but still converts.  Killtrace golden fates
(`c1_killtrace.py`): right-cand **born 3→7**, rate-kills **26→7**,
+outrank/score churn.  Live set (`c1_livedump.py` + `_m1`):

| arm | coverable | hit@1 | box@1 (_m1) | BOX rec | BOX births/pan | clutter |
|---|---|---|---|---|---|---|
| bxsup_off | 3 | 3 | .025 (3/119) | .037 | 0.70 | 5.00 |
| **bxsup_on (A)** | **9** | **6** | **.059 (7/119)** | **.093** | 1.32 | 5.00 |
| bxsupp_on (B) | 7 | 4 | .042 (5/119) | .074 | 1.14 | 5.00 |

(`bxsupp_off` ≡ `bxsup_on` row-for-row: the arm-B OFF toggles only the
priority gate — supersede stays engaged.  level@1 6/76, line@2 19/193,
bracket@1 29/85 identical across all four arms.)

**Verdict: keep Arm A — the plain supersede.**  box@1 +4 hits, born
recall .037→.093, no M1 family loses a single hit, clutter flat →
clean §34.5 pass.  Arm B's spec-priority gate costs −2 hits and −.019
recall for a +1 level inside noise — **reject the gate**.  Mechanism
confirmed as designed: the slot is recycled (BOX births +0.62/pan yet
live-ink flat at clutter 5.00; ~6 formerly rate-killed goldens now
have the matching box live at τ).

Caveat for the keep writeup: real gain .059 vs the .11-.16 bracket —
the fired supersedes are fewer than the loose bound suggested (holder
act_scores at block time decayed less than end-of-panel assumed), and
2 of the 7 hits were already covered pre-supersede.  Still the first
selection-side gain of the round; the remaining ~19 formerly-rate-killed
goldens now die `outranked`/`below_min_score` — next lever is the
live-set ranker (§40.4.5), headroom ≤ ~3 goldens at 9 coverable.

### Live-set ranker result (§40.4.5, 06:28Z — for the build lane)

`boxlab/c1_ranker_cv.py` on `livedump_bxsup_on_cfb862d4.json`
(9 coverable goldens, 26 live boxes, 8 days):

- engine `score` hit@1: **6/9**; `box_rank` alone: 4/9 (lab ranker
  still does not transfer — do not wire it into selection);
- 4-feature logistic (touches, log age, prom_abr, height), LODO:
  **8/9**, shuffle control P(rand ≥ obs) = 0/150;
- stable weights across folds: **−1.1·log_age dominates** — the three
  residual misses are stale `structural_envelope` boxes (age 365–685,
  band ~50 pips off the golden) out-scoring fresh matches.
- Net +2 hits if ported (would be ~9/119 ≈ .076) — a live-order
  rerank is salience-side, your file.  n=9 positives: suggestive, not
  proven.  The cleaner fix may be score decay on stale envelopes.

### §42.4 test cases — the three rank-2 misses (hand-off, 06:29Z)

These are the panels where a stale `structural_envelope` outranks the
fresh right box under `bxsup_on @ cfb862d4`.  §42.4's priority rule
(a box containing/just-left by price outranks everything regardless
of score) should flip all three.  Data:
`boxlab/c1_runs/livedump_bxsup_on_cfb862d4.json`.

| golden | τ | golden band (pips) | winner (stale) | right box (rank 2) |
|---|---|---|---|---|
| 9.2b g0 | 765 | 13239–13261 | `structural_env` 13311–13332, score 6.56, **age 615**, tch 5 | `cluster_range` 13240–13259, score 5.13, age 130, tch 8 |
| 9.2b g3 | 835 | 13212–13225 | same envelope, score 6.56, **age 685**, tch 5 | `cluster_range` 13212–13222, score 5.00, age 25, tch 9 |
| 9.18a g0 | 515 | 13250–13260 | `structural_env` 13272–13284, score 6.84, **age 365**, tch 6 | `cluster_range` 13252–13260, score 1.21, age 35, tch 17 |

In all three the winning envelope sits **~20–50 pips from current
price/golden band** — price is neither in it nor just left of it —
while the right box overlaps the golden band exactly.  If §42.4's
rule fires, box@1 goes 7 → ~9/119 (.076) at zero extra ink.
Watch for: the rule must consult "price just left within 12 bars"
(R21 §21.3), else the author's broken-box dwell breaks.

## R42 probes on the kept parent (canonical `_m1`, label `10c34e28`)

Parent = bxcombo + famcaps + K4 supersede all ON.  One process,
params frozen; `p_base` reproduces the kept config exactly
(7/119, .093 rec, clutter 5.00 — same numbers as `bxsup_on`).

| arm | box@1 | level@1 | line@2 | bracket@1 | BOX rec | clutter | verdict |
|---|---|---|---|---|---|---|---|
| p_base | 7/119 | 6/76 | 19/193 | 29/85 | .093 | 5.00 | parent |
| p_dense | 5/119 | 7/76 | 19/193 | 29/85 | .065 | **5.33** | **reject, definitive** |
| p_wait | 7/119 | 6/76 | 19/193 | 29/85 | .093 | 5.00 | neutral — no keep case |
| p_wb | 7/119 | 7/76 | 19/193 | 29/85 | .083 | 5.00 | neutral |
| p_dense_wait | 5/119 | 7/76 | 19/193 | 29/85 | .074 | 5.33 | reject |

- `dense_anchors` fails **even with the supersede recycling slots**:
  −2 box@1, clutter 5.33, born recall .065.  Same-band variant
  flooding is the cost regardless of the lifecycle lever.
- The wrong-t0 class is not fixable by re-anchoring at all: only
  **1/14** wrong-t0 goldens has ANY confirmed pivot within ±20 min
  of `build_start` (offsets bidirectional, median |off| ~55 min).
  The author's build start is a judgment call, not a pivot event.
- `wait_ttl` is inert under supersede (a blocked cand either
  supersedes at first contact or dies to NMS before the window rolls).
- Residual pool under the kept config: **51 no-edge + 14 wrong-t0**
  (+9 unwinnable clamp).  The next real lever is a mid-band /
  eye-level edge source — the author's edges sit on structure the
  defended-extreme clustering never emits.

Selection-anatomy summary (full table in BOX_LOG 04:5xZ): 42 covered
→ only 2 have a matching box live at τ (both hit@1). 40 uncoverable:
the right object never lives — killed upstream by the rate window,
not by ranking. Right cands usually out-score the τ incumbent
(~24/33 scored cases) but arrive after the slot is spent.

## R44 §44.3 hand-off (07:55Z) — `box.cong_trigger`, FIRST §34.5-passing generation lever

Flag: `box.cong_trigger` (default OFF, boxes.py `_cong_run`, called
from `congestion_scan` when the pivot/level-seeded band paths fail).
Trigger: longest run ending at bar i whose h-l envelope stays within
`cong_h_abr` * ABR; fires when the run reaches `cong_min_bars`.
No pivot requirement — this is the missing trigger for the 51/51
pivot-starved goldens.

Params (provenance: TUNE goldens with both build times, n=37 —
buildup len p25=5 med=10 p90=31 bars; envelope/ABR24 p75≈4.0 p90≈4.7):
`box.cong_min_bars` = 6, `box.cong_h_abr` = 4.0.

Canonical `_m1`, same hash `4dcc44d7`, flag OFF vs ON:

| arm | box@1 | level@1 | line@2 | bracket@1 | BOX rec | clutter |
|---|---|---|---|---|---|---|
| p2_base (flag OFF) | 7/119 (.059) | 6/76 | 20/193 | 29/85 | .093 | 5.00 |
| **p2_cong (ON)** | **9/119 (.076)** | 6/76 | 20/193 | 29/85 | .093 | **5.00** |
| p2_cong_lev (ON + level_edges snap) | 7/119 (.059) | 6/76 | 20/193 | 29/85 | .083 | 5.00 |

- **Passes §34.5's letter**: box@1 +2, every matched family identical,
  clutter median 5.00 (= STABLE), born recall flat .093, births
  1.34→1.40/pan.  Caveat: +2/119 is inside the CI — report as
  letter-passing but small.
- Mechanism (livedump): the flips are FRESH congestion_scan boxes
  (age 15–45, touches 36–38) outranking stale structural_envelope
  incumbents.  9.2b g0 — a §42.4 test case — flips rank2→1 without
  any birth-path priority rule; 9.4b g0 goes from no live match to
  rank-1.  One regression: 9.2b g3 lost its rank-2 match (not a
  hit loss).
- Proposal stream: congestion_scan 5979→8502 cands (+2523), scan
  births 66→90.  The extras die mostly in the funnel — no clutter.
- **p2_cong_lev rejected**: the old-level snap moves edges off the
  golden tolerance (rec .093→.083, box@1 back to 7).  Keep the
  trigger on pure run extremes; old levels are not close enough to
  help even when present.
- Suite leg still needed on your side if you keep it: run the seven
  theory fixtures + full suite on kept-defaults + cong_trigger.

Sensitivity (canonical _m1, same hash — the +2 is NOT a knife-edge):

| arm | k (ABR) | N (bars) | box@1 | BOX rec | clutter |
|---|---|---|---|---|---|
| p2_cong | 4.0 | 6 | 9/119 | .093 | 5.00 |
| p2_cong_k3 | 3.0 | 6 | 7/119 | .093 | 5.00 |
| **p2_cong_k55** | **5.5** | 6 | **9/119** | **.111** | **5.00** |
| p2_cong_n8 | 4.0 | 8 | 9/119 | .093 | 5.00 |

k=3.0 kills it (runs break before qualifying); k=4.0-5.5 and N=6-8
all hold the +2.  k55 also lifts born BOX recall .093->.111 with
clutter flat — the better point.  Recommend `cong_h_abr=5.5`,
`cong_min_bars=6` if kept.

Cross-arm note on the 42.4 test cases (livedump):
9.2b g0 flips rank2->1 under BOTH box_prio (your arm) AND cong_trigger
(mine) — different mechanisms, same fix.  9.2b g3 flips under box_prio
but loses its match under cong.  9.18a g0: box_prio makes it WORSE
(rank2->3), cong leaves it rank2.

Recommended keep order if §41.3 is consulted instead: this is the
only generation arm all round that moves box@1 UP without paying a
family — it complements K4 supersede (which unblocks births) by
supplying better-timed candidates.

## R45 §45.2 addendum (09:0xZ) — flag-OFF leak FIXED; cong_trigger re-verified on clean code

**The leak was mine.**  In the level_edges restructure of
`_propose_window`, the dir<0 anchor window was written
`piv.price - eps <= min(c) <= piv.price + eps` — the mirror of the
dir>0 rule requires `+ tease` on the inside (a touch may poke past
the edge by eps but sit within tease inside).  The ~2-pip narrowing
silently killed ~450 bottom-anchor `cluster_range`/`cluster_range_wick`
proposals and flipped one birth route (9.25c).  Fixed at `df79ade3`.

**Proof:** `c1r_p_base` @ `df79ade3` vs `lnfloor_on` @ `75a9650c`
(K5 kept config): **198/198 panels identical** — objects, cand_log,
bars, events (CA.canonical).  Flag OFF ≡ K5 restored.

**All prior p2_* numbers were measured on leaky code** — the leak
suppressed ~2 golden-covering proposals (oracle .398 was really
.407).  Re-measured on the fix; the cong gain SURVIVES:

| arm (@df79ade3, canonical _m1) | box@1 | level@1 | line@2 | bracket@1 | BOX rec | clutter |
|---|---|---|---|---|---|---|
| p3_base (flag OFF) | 7/119 (.059) | 6/76 | 20/193 | 29/85 | .093 | 5.00 |
| **p3_cong (ON)** | **9/119 (.076)** | 6/76 | 20/193 | 29/85 | .093 | 5.00 |
| **p3_cong_k55 (k=5.5)** | **9/119 (.076)** | 6/76 | 20/193 | 29/85 | **.111** | 5.00 |
| p3_cong_lev (+level snap) | 7/119 (.059) | 6/76 | 20/193 | 29/85 | .083 | 5.00 |

Sensitivity on clean code: k=3.0 loses the +2 (7/119, @9acaa206);
k=4.0/N6, k=5.5/N6 and k=5.5/N8 all hold 9/119.  Recommend
`cong_trigger=True`, `cong_h_abr=5.5` (adds born recall .093->.111
and +1 oracle coverage — 9.51b g0, zero swaps), `cong_min_bars=6`.
§34.5 letter passes on the clean hash: box@1 +2, no family loss,
clutter 5.00.

Note: `p_cong_n8` at `9acaa206` ran (k=5.5, N=8) — the 09:06Z params
update set `cong_trigger: True, cong_h_abr: 5.5` as the new default
(build lane adoption, §45.3.1 in progress), so the arm's h_abr
override no longer applies.  The (k=4.0, N=8) cell is unmeasured on
clean code; leak-era it held 9/119.

The p_cong_lev level snap still rejects (born .083) — keep the
trigger on pure run extremes.

## R46 §46.3 / R47 §47.2 — congestion edge variants: NO handoff (all fail §34.5)

Measured on the K6 parent, canonical `_m1`, flag-OFF ≡ K6 verified at
every hash (198/198 objects + cand_log + events) BEFORE each A/B:

| arm | hash | box@1 | level@1 | line@2 | bracket@1 | BOX rec | clutter | verdict |
|---|---|---|---|---|---|---|---|---|
| K6 parent | 9acaa206 | 9/119 (.076) | 6/76 | 20/193 | 29/85 | .111 | 5.00 | — |
| p_dens (KDE peaks) | 0a100806 | 9/119 | 6/76 | 20/193 | 29/85 | .111 | 5.00 | flat/inert |
| p_dens_q (q0.90/q0.10) | 13b3f53d | 7/119 | 7/76 | 20/193 | 29/85 | .093 | 5.00 | −2, rejected |
| p_sub (sub-band) | 5928a0e2 | 9/119 | 6/76 | 20/193 | 29/85 | .111 | **5.33** | flat + ink, rejected |

Nothing for the build lane to run — the round's edge-variant queue
is exhausted.  Lab data and the 38-golden diagnosis table are in
BOX_LOG (10:05Z census) and BOX_INTEGRATION.md.

## R49 §49.3 — pivot-seeded congestion edges: LEVER, not a keep (fails §34.5 leg 3)

Null test first (`c1_nullsrc.py`, 200 vertical-shift draws, ±1–3 box
heights): pivots KEEP (.789 obs vs null .243/.316 on the 38; .880 vs
.286/.343 on all 119).  rnd10 is grid luck (.395 vs .395 — dropped).
close_ext and sess_hi_lo KEEP but thin.  prior_hi_lo dropped on 119.

`box.cong_pivedge` (default OFF): inside a K6-qualifying run, confirmed
pivots within envelope ±3eps cluster at 2eps; all height-legal pairs
of the top-4 clusters by members+wick support that contain ≥50% of run
closes are seeded through `_buildup_run(fix_edges=True)`; emit-on-
change memo (fires only when the cluster set changes), extreme-band
dedup, same live-cover dedup.  Tagged `pedg`.

Canonical `_m1` @91c44677 (flag-OFF ≡ STABLE 0/198):

| arm | box@1 | level@1 | line@2 | bracket@1 | BOX rec | clutter |
|---|---|---|---|---|---|---|
| p7_base | 9/119 | 6/76 | 20/193 | 29/85 | .111 | 5.00 |
| p7_pedg | **10/119** | **7/76** | 20/193 | 29/85 | .102 | **5.33** |

Oracle .417→.426; proposal coverage +3 (9.44b g1, 9.47b g0, 9.50b g0).
§34.5: legs 1 (box@1 +1), 2 (no family −1), 4 (identity) pass; leg 3
fails — clutter 5.33.  Swept topk{2,3,4}, npairs{2,3,6}, minmem2,
mininside .7, minsup4, minrun2, emit-on-change: every config that
keeps +1 box@1 keeps +0.33 clutter; every config that cuts ink loses
the gain.  The lever is real but needs a birth-side constraint (a
salience gate on pedg-tagged cands — build lane's file) to pass.

## R51 s.51.5 follow-ups (12:39Z) — no new handoff

- **Pivot-support birth-score term: NOT BUILT** (design-level negative).
  c1_pivsup.py: both-edges-on-confirmed-pivots is saturated — 89% of the
  32 score-starved right cands AND 96/103 of the blocking boxes (at own
  birth) carry full support.  No separation => no term.
- **wick_birth on K7 (81f7503f): FAIL** — box@1 8/119 (-1), oracle .407.
  The 11 log_only-covered goldens do not convert; wick variants spend
  box-family slots on wrong bands.  Dead lever.
- cong_pivedge formal A/B on K7 is with the build lane (their 582 line);
  no BOX-LAB action pending.

## Hand-off spec — X2 in-window score-pick for BOX (to build lane, R53 §53.1)

Rule (the `lc_score_pick` pattern applied to the BOX rate gate): when a
signal-class BOX candidate is rate-blocked (`recent >= rate_box` inside
`rate_window_bars` = 72) AND has passed the score floor, let score decide
inside the window — if the candidate's score exceeds the in-window box
birth's score by `hyst_margin`, the incumbent closes "superseded" (its
ledger entry moves to this birth, conserving the rate ledger) and the
candidate births.  No new tuning parameter beyond existing score +
hysteresis (R53 §53.1.3).  Suggested flag: `salience.box_score_pick`
(default OFF), placed in the rate_limited branch next to the existing
lc_score_pick block (~line 912).

Pre-diagnosis on the 8 rate_limited right candidates (c1_missed.py @
9acaa206): only **9.17b g2** both clears the 5.0 floor AND outscores the
slot holder (5.66 vs 5.5 @bar690).  The other 7 are below the floor
anyway (dead on below_min_score regardless) or lose the score comparison
to the incumbent (e.g. 9.16c 1.25 vs 25.71; 9.56c 3.00 vs 8.75).
Expected gain <= +1 box hit; the mechanism is a general rule, not a
one-case fit, so it is allowed under 3.6 — but it is a thin lever.

### Resolution (build lane, 13:53Z) — X2 closed WITHOUT code

The mechanism is already live: `salience.box_score_pick` is ON in every
kept config since C1 row 16 (K1-K9 all carry it). Evidence @3ca9097b:
153 BOX `superseded` events TUNE-wide, including the exact 9.17b chain —
BOX0013->0022 supersession, cand@8.52 replaces holder@5.50 at idx143,
and the cited cand@5.66 supersedes BOX0021 (score 2.56) at idx145. The
8 rate_limited goldens are rate-limited DESPITE the mechanism (right
cands below floor or below holder's *current* score, which decays).
No flag to add; nothing to A/B. X1/X2/X3 all closed.

## A1 — current-episode scope for the birth slot (R56 §56.4, 16:55Z)

**Kind:** selection-side spec — `salience.py`, build lane's file.

**Rule (pre-stated, §3.6):** at a BOX birth decision, the candidate
must be *current*: `cand.t1 >= now - K` (K = 30 bars) OR its span
contains now.  Non-current candidates are not eligible for the slot
this bar (they are not evicted — they simply can't take the slot).
Among current candidates the existing score order is unchanged.
**Param:** `K = 30` bars.  Flag suggestion: `salience.box_live_scope`
(default OFF).

**Evidence for it (R1.4, label-shuffle nulls):** the author's drawn
box ends ~14 bars *past* τ while the engine's wrong picks ended ~40
bars *before* τ (H5, strongest surviving signal).  The incumbent that
beats right cands is typically stale first-arrival ink; 11 outranked
+ 8 rate-limited + 2 expired right cands were proposed *near* τ
(current) but lost to older objects.

**Falsify:** if replay shows the right cands' spans are also stale at
τ, A1 is empty.  Expected ceiling from the anatomy: the
current-episode subset of the 21 outranked/rate cases ≈ +3–8 box@1.

**Ownership:** I own no salience edits; this is a spec for the build
lane to implement and A/B when their queue allows.

### H5-causal pre-test on r_dataset (build lane, ~15:10Z) — for R57.1

Paired test on the new dataset (boxlab/r_dataset/rows.csv): per
(panel,tau) cell, strongest right cand (label_edge>=0, max score_last)
vs the engine's live wrong pick (is_engine_pick=1, label<0).  n=12
paired cells.  Null = label_edge shuffled within (panel,tau), 200 draws
(seed 7).

Causal-only features (bars <= tau) that beat the null:

| feat | obs diff (right-pick) | null p95/p5 | read |
|---|---|---|---|
| recency_bars | -64.8 | +12.3 / -20.1 | right structure ends nearer tau |
| bars_since_in_band | -26.6 | +21.0 / -2.1 | close sat in the band more recently |
| bars_since_touch | -22.2 | +20.4 / -1.4 | band touched more recently |
| dist_close_edge_abr | -2.17 | +2.06 / -0.14 | close closer to an edge |
| px_in_box | +0.50 | 0 / -0.34 | close inside the right box at tau |
| ema_slope_span | +0.54 | +0.15 / -0.31 | right box on SLOPING ema (H2 echo) |
| probes_bot | -2.42 | +0.77 / -1.13 | fewer rejected bottom probes |

Flat vs null: probes_top, h_abr, h_rel_day, overlap_ratio, prior_leg_abr.

Read: H5 survives in causal form - the right box is the one price is
*still interacting with* at tau (recent touch/in-band, price at or
inside the band).  The wrong pick is typically an older, stale box that
kept its slot via dwell/hysteresis.  n=12 is thin; re-run under
r1_hyp.py conventions for the R1 table, and consider density-null for
the price-position rows per s.57.1.

### Dataset v2 note (build lane, ~15:15Z) — pick columns + a structural finding

rows.csv regenerated: +age_bars (R57.1 causal quantity) and per-cell
pick_* columns (engine's top live box-family object at tau: type, hi/lo,
t0/t1, score, id).  48 cols now.  Deterministic rebuild verified
(SHA256 stable across runs).

Structural finding for R1/R2: at the 115 golden tau cells the engine's
top box-family object is **CONTEXT_RANGE in 80, BOX in 34, RANGE_OPEN
in 1**.  So "the engine picks the wrong box" is mostly "a wide context
envelope outranks the tight box" — box@1 competes with the family's own
envelope objects.  Any A1 context-first rule should consider the
type-mix at the slot, not just cand-vs-cand scoring.

### Lab counterfactual on r_dataset (build lane, ~15:20Z) — selection sim

Picking ONE live BOX cand (last_outcome in pending/born) per
(panel,tau) cell; hit = that cand's label_edge.  Golden-level count =
distinct goldens hit /119.

| rule | cell acc | goldens |
|---|---|---|
| oracle (always right if exists) | 49/115 | ~49 |
| argmax score_last (engine score on live pool) | 1/115 | - |
| min bars_since_touch / px_in_box / fresh combos | 4/115 | - |
| **min age_bars (youngest live cand)** | 15/115 | **15/119** |
| youngest + max touches tiebreak | 16/115 | - |

The engine's own score is near-zero as a live-pool selector (1/115);
formation recency alone nearly reaches the v0 bar (15 vs 16).  This is
the H5-causal story quantified: the author draws the *most recently
formed* congestion.  Caveats: counterfactual assumes a pending cand can
be birthed at tau; real engine must also beat incumbent objects and pay
clutter/budget.  Suggested A1 rule-shape for R2: 'at decision time,
prefer the youngest live BOX cand (tiebreak touches)' — not a score
weight.

### A1 measured ceiling + companion evidence (15:48Z)

On `r_dataset/rows.csv` (8975 cands / 115 cells, K9-state caches):

- Engine's wrong pick is live (`px_in_box` or within 0.5 ABR of edge)
  in only **3/12** paired cells; a right cand is live in **10/12**.
- Scope-only argmax over live cands flips **2/12** — the scope alone
  narrows the pool but the right cand still loses `score_last` inside
  it.  Recommend pairing the scope with the liveness-aware ranking
  evidence below.

### A3 ranker evidence (for the Lead's cloud fit — ESCALATE logged)

`r3_fit.py` (deterministic, LODO by `date`, 200-draw within-cell
label-shuffle control), features restricted to the R57 causal
null-survivors: **CV cell@1 = 18/67 = .269 vs shuffle p95 .254**
(baselines: score_last 5/67, box_rank 4/67).  Feature set:
`-dist_close_edge_abr, close_at_box, -recency_bars,
-bars_since_touch` — all computable in `feats_at` from bars <= tau.
Thin but real: this is the strongest selection-side evidence the round
has produced.  If the Lead's fit confirms, the ranker's weights are a
*spec for a salience-side birth-order change*, not a boxes.py edit.

### Resolution (build lane, 15:50Z) — A1 lvs arm: REJECTED (inert)

`salience.box_live_scope=30` implemented @c9f240f8 (gate in the cand
loop, non-evicting 'not_current' outcome).  Flag-OFF identity:
198/198 panels canonical-identical to parent cache.

**A/B @c9f240f8:** box 10->10 | level 8->8 | line 20->20 | bracket
29->29 | clutter med 4.33 flat.  The gate logged 730 not_current
events and DID change object sets (159/198 panels differ from off),
but zero M1 movement — blocked stale cands are replaced by other
wrong cands or were dying at later gates anyway.

**Mechanism (pre-registered prediction held):** only 1/309 BOX births
is stale-at-birth (t1 < idx-30) — incoming cands are fresh by
construction; the staleness lives in incumbent OBJECTS.  Incumbent
side also weak: in the 49 cells with a live right cand, the pick's
span ended >150min (30 bars) before tau in only **8 cells** — most
wrong picks are FRESH structures (a CONTEXT_RANGE still forming, or a
recent box).  A1 as specified (cand eligibility) is empty; the
incumbent-age variant would touch ~8 cells, below the +6 needed.

Counter-evidence to log: 'the wrong pick is stale ink' is true of
scores (score-blind pool argmax = 1/115) but the pick's *span* is not
stale — the wrong object is usually still-forming.  The real contest
isn't old-vs-new, it's envelope-vs-tight-box at the same moment.

### A1+A3 deployment note (15:58Z) — spec sharpened

The A3 diagnostic shows the scope alone is not enough (2/12 flips) and
the ranker alone does not reach M1 (only 3/18 hits clear the 5.0
floor).  The deployable form that matches all evidence:

> For the BOX birth slot, admit by **liveness order among current
> cands** — i.e. the cand with min `dist_close_edge_abr` /
> `bars_since_touch` / `recency` wins the slot — rather than by the
> static `box_rank >= 5.0` floor.  (The floor can still apply as a
> sanity minimum, e.g. box_rank > -inf gate or a reduced floor, but the
> ORDER must be liveness-first; current admission lets stale
> envelopes outrank live episodes.)

All four features are already computed in `feats_at` (bars <= tau) —
no new data plumbing, a birth-order change only.  This is the R56
research round's concrete engine recommendation; A/B per §3.1 on your
side.  If it fails, the remaining avenue is A4 (lifecycle redesign).

### A1 variant-2 (build lane, ~16:10Z) — yng arm: REJECTED (flat)

`salience.box_young_first` @97061ac5: within the box family's own
birth-order positions the youngest cand (max t0, tiebreak touches)
leads — cross-family competition untouched.  OFF-identity 198/198.

**A/B:** box 10->10 | level 8 | line 20 | bracket 29 | clutter 4.33 —
all flat (BOX recall diag .102->.111, no conversion).

**Why the 15/119 counterfactual did not port:** the dataset sim picks
among cands ALIVE AT tau — including proposals the funnel never
birthed.  In the live engine the order only matters when the slot is
contested; the youngest cand still dies at below_min_score/rate/
suppression before any contest, and births happen continuously, not
at tau.  Order cannot create the missing births.

**A1 closed (2/2 variants measured):** scope gate inert (fires 730x,
no conversion) + youngest-first flat.  Selection-by-recency does not
survive the continuous-birth funnel.  What remains unfalsified is the
A3 liveness RANK as the birth criterion itself (replace score, not
reorder) — pending the Lead's cloud fit of r3_fit.py weights.

### A4 addendum per R59 (16:25Z)

- R59 §59.2 withdrew the example order (min bars_since_touch scored at
  chance).  The stated order that measured best in the Lead's cloud
  check: **recency (min `recency_bars`), tie-broken by age** — no
  fitted weights.
- R59 §59.4 reporting requirement: in **80/115 cells the engine's top
  box-family object is a CONTEXT_RANGE, not a BOX** — every A4/liveness
  arm must report its effect on the envelope-vs-box contest (same
  contest as the R54 fixture debt).
- R59 §59.3: a fresh pick can fail strict span IoU; any freshness arm
  must report the left-edge/span effect.  (My span-side pre-test on
  boxes.py window fields: dead — right cands already span the episode;
  the fix is which cand gets born, not its recorded window.)

### A4 addendum RESOLVED (build lane) — both variants measured, class closed

- `a4_on` (box_live_birth @b1d94617): INERT — canonical 198/198 ≡ off.
  CONTEXT_RANGE envelopes always contain price; containment-liveness
  never discriminates.
- `a4b_on` (box_edge_birth @54bd315b): FAIL §3 — box@1 8/119 (−2),
  level/line/bracket flat, clutter 4.00.  Hook fires (all-panel
  canonical diffs) but evictions are net-wrong: an incumbent envelope
  whose edge IS being tested is often the right pick — incumbent
  edge-proximity is a rightness signal, not just activity.
- Recency-order contest variant (§58.3 order = min recency_bars,
  tie age): killed by arithmetic pre-A/B — incumbent CONTEXT_RANGE
  has recency_bars=0 in ≥75% of cells (envelopes are FRESH, still
  updating); cand fresher than incumbent in only 12/49 CR-held cells,
  and just 4/12 winners clear the 0.5 sanity floor.  Ceiling ≈ +4
  with symmetric wrong-cand flip risk.

**Selection-side is exhausted as a class:** scope (inert), cand
order (flat), liveness gate (flat), liveness floor-bypass (7% right
pool — arithmetic), containment contest (inert), edge contest
(harmful), recency contest (arithmetic dead).  The envelope-vs-box
problem is neither staleness nor liveness: the CONTEXT_RANGE is
fresh, updating, and often genuinely active.  What differs is
TYPE/representation — the author draws the tight box where the
engine keeps the wide envelope.  That is the ctx_convert direction
(fixtures 72/72 cured but M1 line −2): a representation question,
not a selection one.

### BOX-LAB measurement addendum (~16:45Z) — positional staleness at τ

Independent cache-only count on the lvb pickles (`29de0689`,
variant `lvb_off`/`lvb_on`, `_m1.panel_rows`): **lvb_on ≡ lvb_off,
all metrics identical (box 10/119, level 8/76, line 20/193,
bracket 29/85, clutter 4.33)** — confirms the flat verdict; the
birth gate never discriminates because ~97% of cands are inside
their band at emit-time (staleness develops post-emission).

One axis the closed-class list may not have covered — **positional
staleness of the incumbent at eval-τ** (price vs the object's
band), distinct from `recency_bars` (temporal freshness, which
envelopes satisfy trivially since they update every bar):

- pick stale at τ (close >5p outside band AND from nearest edge):
  **61/115 cells** — CONTEXT_RANGE 52/80, BOX 9/34.
- of the 64 cells holding a right cand: pick stale in **35**; a
  right cand that is itself live at τ exists in **28** (all
  born-eligible) — the ceiling for a "live-first" object ordering.
- exposure the other way: **4 of the 10 current box@1 hits ride a
  stale pick** (3 CONTEXT_RANGE, 1 BOX) — and the author's own
  "kept past the break" convention means the matched golden is
  often positionally stale at τ by design.  Positional staleness
  is therefore partly a RIGHTNESS signal for geometry-match, not
  pure noise — the same tension a4b_on showed (edge-proximity on
  the incumbent correlates with rightness).

If the "containment contest (inert)" entry already covered
object-level positional demotion at τ, this is its measured
explanation (eviction would fire in 61 cells yet net ≈ 0 — the
stale pick is often the right pick).  If it covered only
birth-time gating, the arithmetic above is the untested residual:
ceiling ≈ +28 cells, bounded downside −4, honest prior that every
neighbouring variant failed.  No new arm requested from this lane —
the class stays closed unless the Lead rules otherwise.

**Correction to the "wide envelope" framing** (same measurement,
pick band vs golden band, pip-scale): CONTEXT_RANGE picks are
NOT wider than the golden — median height 16.0p vs golden 15.6p
(1.04×; BOX picks 21.1p vs 16.0p = 1.45×).  What differs is
**placement**: CR picks' band-IoU vs golden median **0.02** —
a golden-sized box anchored to the *previous* episode's
structure, disjoint from the one the author drew (center offset
med 16p).  So the representation gap is not "tight box vs wide
envelope" — it is "same-shaped object, wrong anchor, wrong time":
the Owner's formulation verbatim.  A ctx_convert that only
narrows an envelope's height would not fix a 0.02-IoU object.

### Build-lane reply to positional-staleness addendum (measured on cache)

Reproduced the count on `a4b_off` cache @54bd315b (bands in pips,
stale = close >5.0p beyond band): **63/115 stale picks**
(CONTEXT_RANGE 57, BOX 6) — consistent with the 61/115 addendum.

But the OBJECT-level counterfactual (demote stale picks at tau,
next ranked live object takes the slot) is **net-zero**:

- stale pick that is itself a HIT: **1** (bounded downside −1)
- stale pick whose demotion yields a right pick: **+1**
- reason: in **50/63** stale cells there is NO other live box-family
  object at all; born right objects exist under a stale pick in only
  **3 cells**.  The +28 ceiling was counted on pending cands — those
  cands were never born, so nothing waits beneath the envelope.

Continuous-demotion variant (evict mid-life -> slot opens -> pending
cand births): the freed slot still feeds the same pending pool that
is ~93% wrong and mostly <0.5 floor — same arithmetic that killed
the floor-bypass.  Not fired.

Positional staleness residual: measured, dead at object level.
C-3 selection + lifecycle space is now fully closed by measurement
or arithmetic on every named mechanism.

### R60 s.60.3 hybrid count RESULT (build lane) — PASS box, FAIL clutter

Same-machinery rows (`_hybrid_v0box.py`, caches a4b_off + m1_v0,
day-bootstrap 2000 draws, seed 20261202).  v0 box objects taken
unchanged, as pre-stated.

| metric | v0 | v1 parent | hybrid |
|---|---|---|---|
| box@1 | 16/119 | 10/119 | **16/119** (+0.000 vs v0) |
| level@1 | 5/76 | 8/76 | 8/76 |
| line@2 | 18/193 | 20/193 | 20/193 |
| bracket@1 | 33/85 | 29/85 | 29/85 |
| clutter med | 9.00 | 4.33 | **5.67** |
| margin <=5.0 | 21/179 | 114/179 | 77/179 |

Verdict per s.60.3.2 gate: box@1 hits v0 parity exactly (every v0 box
hit transfers intact into the combined set) and level/line/bracket are
untouched — BUT clutter 5.67 > 5.0 -> hybrid FAILS s.3.1c.  No port.

**Ink accounting for BOX-LAB (s.60.3.3):**
- v0 box family: **6.0 objects/panel median** (mean 6.26, max 10).
- v1 box family: 1.0 median (mean 2.10).
- Delta: **+4.0 med / +4.16 mean / p90 +7 objects per panel**.
- v0 box-family composition (30-panel count): BOX 182, RANGE_OPEN 17 —
  **v0 has NO CONTEXT_RANGE at all**: its box family is pure
  event-route births, ~6/panel.  The clutter cost is the price of
  carrying v0's whole box stream.
- The 15 event-route goldens (s.60.2) need only the *event-moment*
  births — an event-gated port should cost far less than +4/panel.

### EVAL-AUDIT ink budget for the s.61.2 event-route port (00:46Z 23/09)

Parent: STABLE C-2 `4c2df34d` (measured on `a4b_off@54bd315b`, proven
1728/1728 identical to `c1r_p_base@ee2cbf12` incl. events; ee2cbf12 ==
4c2df34d by the F1 identity). 179 scored panels, parent clutter med
4.33, margin 114/179, goldens/panel median 3.

The ruler counts EVERY object whose span intersects the window —
a ported box keeps its ink even if it dies mid-window.

**Uniform budget (all panels take +k objects):**

| +k obj/panel | clutter med | margin | verdict |
|---|---|---|---|
| +1 | 4.67 | 106/179 | safe |
| +2 | 5.00 | 92/179 | exactly at the gate — no headroom |
| +3 | 5.33 | 87/179 | FAILS |

=> **1 extra box object per panel, everywhere, is the safe uniform
budget; 2/panel sits exactly on 5.0 with margin -22; 3+ fails.**
Per-panel headroom median = 1 object (51% of panels tolerate >=1,
49% >=2, 40% >=4 before crossing 5.0 alone).

**Concentrated budget (ink lands only on event panels):** the median
is robust — 40 random panels x +6 objects each -> med ~4.67
(worst draw 5.00), margin 96-108.  Even 60 panels x +4 stays <= 4.65.

**Design implication:** keep average ported ink <= +1 object/panel
(uniform) OR concentrate births on <= ~40 panels with <= ~4-6 each.
The fatal profile is many panels each carrying several persistent
boxes (v0's 6.0/panel everywhere = 5.67).  Live-at-tau count is a
separate metric — a dead box still spends its ink in the window.

## Event-route port spec (R61 §61.4 — BOX-LAB to build lane, ~01:0xZ)

Port **v0's birth criterion only**, not its lifecycle (hybrid failed
clutter on v0's ~6 boxes/panel, not on its births).  The port is a
flagged route inside `boxes.on_pivot` (the hook already exists —
every confirmed SwingBook pivot reaches it); birth admission, rank-1
handling and budget stay in `salience.py`.

### Trigger & qualifying pivots

- **Every confirmed SwingBook pivot** qualifies (both directions).
  v0 qualifies on `min_swing_pips` at confirm; v1's equivalent is
  simply "the book emitted the Pivot".  No structural/`is_structural`
  filter — v0 used all confirmed swings.
- **Timing subtlety (must port verbatim):** v0's `_confirm_pivot`
  passes `idx = t_ext` (the pivot's EXTREME bar) into `_box_birth`,
  not the confirm bar.  All window/min-sep/segment arithmetic below
  runs on the `t_ext` axis at `e = piv.t_ext`; the object is born at
  `t_conf`.

### Pools (at e = piv.t_ext)

- `same` = confirmed same-dir pivots with `e − p.t_ext ≤ 84`
  (`window_bars`), excluding the current pivot.
- `opp` = confirmed opposite-dir pivots with `e − p.t_ext ≤ 84`.

### Route (b) `range_double_{top,bottom}` — evaluated FIRST

Scan `same` most-recent-first; take the FIRST `prev` satisfying
`e − prev.t_ext ≥ 4` (`double_top_min_sep_bars`) AND
`|prev.price − piv.price| ≤ 2.0` pips (`double_top_tol_pips`).

Edge anchors (EVAL-AUDIT §61.3 — every edge names its structure):

| edge | anchor |
|---|---|
| double edge | the **confirmed pivot pair**: `top = max(prev.price, piv.price)` for a high pivot; `bottom = min(...)` for a low pivot |
| far edge | the **intervening segment extreme**: min low over `bars[prev.t_ext−2 … e]` (top route); max high (bottom route) |

Drawn `t0 = prev.t_ext` — **the box is born already spanning back to
the earlier pivot** (this is the span asymmetry vs v1's emit-time
cands; keep it).

### Route (a) `pullback_end` — SHADOWED if (b) produced a cand

Needs `last_opp` = most recent `opp` pivot; require
`e − last_opp.t_ext ≥ 3`.

| edge | anchor |
|---|---|
| one edge | the **new confirmed pivot**: `piv.price` |
| other edge | the **last opposite pivot**: `last_opp.price` |

(dir=−1: L=piv.price, H=last_opp.price; dir=+1 mirrored.)
Drawn `t0 = last_opp.t_ext`.

Both routes' candidates are logged (second route → `route_shadow`);
only the first births.

### Birth conditions (v1 adaptation)

- **Envelope gate:** `6.0 ≤ hi−lo ≤ 34.0` pips
  (`height_min/max_pips`) — else `vetoed_envelope`.
- **Dedup:** if a live box's top AND bottom are both within
  `tol = max(1.0p, 0.25·ABR)` (`edge_tol`), no new object.
- **Cooldown:** ≥10 bars between event births (`birth_cooldown_bars`)
  — can be folded into v1's existing rate machinery if simpler.
- **v0's governing-box veto is REPLACED** (this is the §60.4.2
  change): the incumbent CONTEXT_RANGE **stays alive** as the
  level/line carrier; the event box takes **box-family rank-1** at τ
  (spec §5 priority 1).  The CR is demoted only inside the box
  ranking — its level/line hits are untouched.
- **No v0 lifecycle ports:** no re-anchor, no one-governing-box
  veto, no v0 supersede.  v1's budget/lifecycle governs; live box
  objects per panel must stay at the author's level (~1).  Report
  live-objects-per-panel in every arm (§61.2).
- **Intra-event ordering (the volume caveat):** the replay shows
  ~39–84 route cands per panel — v0's governing veto collapsed them
  to ~1 live box; v1's budget decides coexistence.  Default: event
  boxes rank among themselves by the existing box-family score
  order (only their floor-vs-CR advantage is the rank-1 grant).
  Allowed variant #2 (§3.7): most-recent event birth takes rank-1.

### Stated parameters (§3.6 — all from params_v1.json)

`window_bars=84`, `double_top_min_sep_bars=4`, `double_top_tol_pips=2.0`,
`height_min_pips=6.0`, `height_max_pips=34.0`, `birth_cooldown_bars=10`,
`edge_tol = max(1.0p, 0.25·ABR)`, pullback min pair separation = 3 bars.


### Offline reach check (BOX-LAB, cache-only replay — c1_eventreach.py)

Replaying the two routes verbatim on v1's SwingBook stream (pivots
from the `lvb_off` @29de0689 pickles, `t_conf ≤ τ`):

- **12/15 event-route goldens reached** — a route cand with both
  edges inside `tol_px(golden)` exists before τ, and all 12 pass the
  6–34p envelope gate.
- Misses: 9.17c, 9.33c, 9.43b — the verbatim replay emits no cand
  with matching edges (dtol=4.0 variant still 0).  Root cause below:
  the golden-edge pivots exist in v1's book, but `last_opp` picks an
  intervening micro pivot — a stream-granularity gap, not absent
  structure.
- Born cands carry `t0` = the earlier pivot's bar and are born early
  (born t_conf ≪ τ: e.g. born=9 vs τ=560) — the span asymmetry is
  fixed by construction.
- Volume note for the budget: ~39–84 route cands per panel — the
  rank-1/budget mechanism, not the route, must do the choosing.
- **Miss mechanism (for the pivot-qualification knob):** in all 3
  misses the golden-edge pivots DO exist in v1's book (e.g. 9.17c:
  13252.2@t134 +1 and 13222.4@t152 −1), but `last_opp` = the *most
  recent* opposite pivot — an intervening micro pivot (148@13234.7)
  stole the slot, so the route emitted a tighter interior band.
  v0's coarser `min_swing_pips`-gated stream never confirmed the
  interloper.  **Two stated variants already tested offline, both
  rescue 0/3:** (a) opp/same pools restricted to
  `book.is_structural(p)` pivots — the interlopers are themselves
  structural; (b) `last_opp` = max-prom opposite pivot — still picks
  wrong.  Do not spend variant budget here: the 3 misses need a
  different pairing rule (e.g. adjacency-in-stream like v0's coarser
  book), not a pool filter.  **Verbatim port = 12/15 ceiling.**



## Event-route port RESULT (build lane, R61 §61.4 — all variants closed)

Spec landed ~01:0xZ; my first two arms ran pre-spec from the 17:19Z
feasibility note.  Three arms measured, mechanism CLOSED (§3.7):

| arm | design | box@1 | clutter | margin | verdict |
|---|---|---|---|---|---|
| evb_on @be204b98 | direct birth + gov-veto + NEWEST +100 | 7/119 | 6.00 | 71/179 | FAIL |
| evb2_on @b07b8af4 | + double-only (pullback off) | 7/119 | 5.67 | 80/179 | FAIL |
| evb_on @65c8f635 | SPEC DEFAULT: propose->pool admission, best-score rank-1 | 10/119 | 4.33 | 114/179 | INERT (0 born, byte-flat) |

### Flip decomposition (v1, per-golden pick diff): 12 flips +5/-7 —
every thief pick was the newest ev-box; `ev_pullback_end` caused 6/7
hit->miss losses (net -3), range_double_* net +1.  v2 removed
pullback births: double-only still lost 8 (newest double box at tau
is still a fresh micro-structure, not the author's mature range).

### The bind (for the next spec revision):
- **Direct birth** reproduces v0's coverage (BOX rec .213 = v0's
  .213) at ~6.5 births/panel — but ink +4 live objects/panel vs
  EVAL-AUDIT's +1 uniform budget, and the freshest-event pick is
  wrong more often than the incumbent it displaces.
- **Budget admission** (spec default as written): 33 proposals / 0
  born in a 3-panel smoke — outranked 33, below_min_score 19,
  expired 28.  The slot contest that killed right cands in the
  49/115 live-cand cells kills event cands identically.  INERT.
- Middle ground does not exist in the stated parameters: admission
  kills them, direct birth overflows ink, and neither rank policy
  (newest / best-score) rescues the pick because ~59% of the birth
  stream is pullback noise and even double-only births pick wrong.

### What the port proved, positively:
- v1's confirmed-pivot stream hosts the routes fine (266/266 v0
  event births have a v1 confirm <=30min; your 12/15 reach holds).
- The failure is NOT the route logic — it is that v1 has no seat
  for an event-born box: budget won't admit it (inert), direct
  birth can't be paid for in ink (+4 vs +1), and once live it is
  either thief (newest rank) or invisible (score rank).
- Same structural wall as every closed lane: the funnel cannot tell
  "author's box" from "wrong incumbent" at any gate — birth,
  contest, or tau-rank.


### BUILD-LANE pre-measurement for the §62.4 throttle spec (02:1xZ)
Replayed your verbatim routes on v1's pivot stream (c1_eventreach
machinery, all 66 TUNE dates, births = cand passing envelope+dedup+
cooldown-10), then applied each §62.4 shape.  CAUSAL birth counts are
per PANEL (born inside [w0,w1]); survival = a born cand matching the
golden's edges before tau (of the 15 v0 event-route hits):

| throttle | births/panel med | golden survive |
|---|---|---|
| none (envelope+cooldown only) | 6.0 | 9/15 |
| episode: exit X=1.0 ABR or K=120b | 3.0 | 7/15 |
| episode: exit X=1.5 ABR or K=240b | 2.0 | 5/15 |
| leg >= 2 ABR | 4.0 | 5/15 |
| leg >= 3 ABR | 3.0 | 3/15 |
| touches >= 3 each edge | 3.0 | 5/15 |
| first-per-session-segment | 1.0 | **1/15** |
| running-max leg per segment | 2.0 | 3/15 |
| running-max height per segment | 3.0 | 4/15 |

**Frontier finding:** no stated shape satisfies the joint constraint
(<=2 births AND keep ~12/15).  At ~2 births/panel the best shape keeps
5/15; the only shape reaching <=1-2/panel (first-per-segment) keeps
1/15 - the golden boxes are mid-episode events, not segment-firsts.
Even UNTHROTTLED births cover only 9/15 (your 12/15 reach counted
cands before cooldown/dedup).  A throttle that picks the RIGHT ~2
births per panel would need to identify the author's event a priori -
the same significance-judgment wall; no causal per-event feature in
the stream separates golden events from micro-events at that density
(leg_abr, height, touches all tested above).

If a smarter selector exists (e.g. event whose band still brackets
price at the NEXT pivot = survival-confirmed), it needs its own
replay check first - happy to run the counterfactual on cache if you
spec it.


## 19. R62 §62.4 — THROTTLED EVENT BIRTH: measured negative, s.62.5 frontier

BOX-LAB, cache-only measurement on the R61 port's own candidate stream
(`r_dataset/event_cands.pkl`, 198 panels, 9720 cands, med 49/panel).
Rule + every parameter stated in BOX_LOG.md 02:15Z before the formal
tally; stream statistics measured first to choose the shape (§62.4).

### Stated rule T1 (the formal spec, one variant used)

**UPDATE-IN-PLACE, double-edges only (UIP-rd):** the event family gets
exactly ONE object per panel. The first non-shadowed route cand births
it. Every later non-shadowed `range_double_*` cand rewrites its
`(lo, hi, t0)` in place — geometry mutation, no new object, no extra
ink. `pullback_end` cands never write (consistent with the build lane's
finding that pullbacks are net-negative). All other R61 parameters
unchanged: envelope 6–34p, dedup `max(1p, .25·ABR)`, cooldown 10b,
WIN 600, MIN_SEP 8, PB_SEP 8, DTOL 2.0p.

**Births/panel = 1.** Reachable-golden survival at τ (edge-tol match
on the object's final written edges): **5/15** — vs 12/15 unthrottled.
If rank-1 and born-eligible this projects to ≈ +5 vs parent →
BOX ≈ 15/119, still << v0's .213.

### Why every throttle fails (the measurement matrix)

| rule | births/panel | reachable goldens surviving |
|---|---|---|
| raw stream (R61 port) | ~6.5 | 12 |
| governing-release X=.5/1/2/3 ABR | 5.5/4.1/2.7/1.8 | 1/1/1/1 |
| gov + in-place re-anchor X=3 ABR | 1.8 | 1 |
| leg floor L=15/20/25p (v0-stream proxy) | 8/3/1 cands | 5/0/0 |
| touch-defer S=80/200 bars | 2/1 | 2/0 |
| edge-dedup D=5/8/12p | 13/9/6 | 11/8/6 |
| growth-supersede D=0/2/4p | 6.8/5/4.2 | 1/1/1 |
| UIP always / wider / left / left-or-wider | 1 | 4/0/0/3 |
| **UIP rd-only (T1)** | **1** | **5** |
| UIP re-anchor ≤8p, cd 12b (v0 semantics) | 1 | 0 |
| cumulative envelope (min lo / max hi) | 1 | 0 |

The matching cand is causally indistinguishable: leg med 8.8p hit vs
8.8 stream; prom 10.5 vs 10.5; pairsep 11 vs 8b; touches/edge 2 vs 2;
born at stream position ~50% (never first, rarely last). Any gate tight
enough to reach ≤2 births removes it. The only frontier point that
keeps most goldens (dedup D=5 → 13 births, 11/15) violates the ink cap
the throttle exists to satisfy.

### §62.5 FRONTIER — goes to the Owner

Two measured endpoints, no third point found in the stated parameter
space:

- **BOX ≈ .213 (v0 parity)** at ~6.5 event births/panel, clutter
  5.67–6.00 → FAILS the +1-object budget.
- **Clutter ≤ ~1.7** at 1–2 births/panel → BOX ≈ 10–15/119, the event
  gains largely gone.

Same wall the build lane's own A/B found at the admission and rank
gates — the funnel cannot tell "author's box" from "wrong incumbent" at
ANY causal decision point. This is arithmetic, not a tuning gap: the
right cand carries no readable signature before hindsight. Decision is
the Owner's: accept the ink (raise the object budget for event boxes),
or accept coverage ≈ parent. Suggested A/B if build wants the T1 arm
anyway: flag `ev_uip` in boxes.py — event object births once, rd events
mutate edges in place; report M1 row, BOX/level/line rec, clutter
med+margin, births and live objects per panel, flipped goldens,
flag-OFF identity, suite name.

**§63.3.4 assist (BOX-LAB cache numbers for T1, 02:20Z):** the T1 sim
is pure bookkeeping on `r_dataset/event_cands.pkl` — 1 event object
per panel (born at first non-shadowed cand, mutated by rd events),
live at τ in **15/15** event-golden cells. Live-at-τ ≈ parent(~1)
+ 1 ≈ **2**; today's dead-included clutter for T1 ≈ parent + ~1
(there are never dead event objects — the single object mutates in
place, span follows the last write's t0). Reproduce with
`c1_eventreach.py` + the UIP-rd rule in BOX_LOG.md 02:15Z.

### EVAL-AUDIT s.63.3 — option C priced: clutter counted LIVE at τ (02:24Z)

Own code `evalcheck/_live_clutter_c3.py`, cache-only, deadline 03:30Z met.
Two definitions shown (the Owner's ruler does not change — information
only):

- **STRICT** = object `state == ACTIVE` at the end of the τ-truncated
  run — literally on screen at the decision moment.
- **LOOSE** = `live_records` semantics (`state != DELETED`) — what the
  ranker sees; includes CLOSED-but-still-drawn objects.
- Numerator includes live LABEL_TF (matches today's convention);
  panel ink = mean live count over the panel's golden τs
  (last-τ sensitivity in parens); denominator = scorable goldens,
  same as today.

| row | today's clutter | STRICT live@τ | LOOSE live@τ |
|---|---|---|---|
| parent C-2 | med 4.33, margin 114/179 | **2.00**, margin 166 | 3.50, 128 |
| v0 | 9.00, 21 | 2.67, 150 | 6.83, 53 |
| hybrid v1+v0box | 5.67, 77 | **2.00**, margin 167 | 4.25, 111 |
| evb_on be204b98 | 6.00, 71 | 2.44, 156 | 5.00, 90 |
| evb2_on b07b8af4 | 5.67, 80 | 2.33, 160 | 4.78, 96 |

**Read:** v0's clutter is dead-object residue — at any decision
moment ~2.7 objects are actually on screen.  The hybrid's v0 box
stream costs **zero extra live ink** vs the parent under STRICT-C
(2.00 vs 2.00; margin 167 vs 166).  Under option C the box-parity
hybrid passes the clutter gate trivially; even the loose form
(4.25 < 5.0, margin 111 ≈ 114) passes.

**Caveats:** (1) C does not rescue the failed port arms — their
box@1 −3 is pick pollution, independent of the clutter definition.
(2) T1 throttle is not in the cache (offline replay only); per the
build lane's verified check its single event object is live at τ in
15/15 cells → estimated live ink ≈ parent + ~1 object.
(3) Last-τ variant gives the same ordering (hybrid 2.00 strict).
Rows artifact: `evalcheck/_live_clutter_rows.pkl`.


## 20. T1/UIP-rd formal A/B - measured (@6d955783, same-hash vs C-2)

Implemented verbatim in engine.py `_ev_uip_step` (flag `ev_uip`;
constants WIN600/SEP8/PB_SEP8/DTOL2.0/envelope6-34/dedup max(1p,.25ABR)/
cooldown10b@birth; ONE object per run; rd-only rewrites; pullback never
writes; rank-1 +100 via existing grant).  Two readings A/B'd:

**uip_on - strict v1 lifecycle** (object dies, family spent):
box 7/119(-3) | level 4/76(-4) | line 22/193(+2) | bracket 29/85 |
clutter 4.50 | margin 100/179 | births 1.0/panel | live 8.0@tau |
flips +4/-9 | suite 71/72 -> FAIL 3.1a.  Degenerate as predicted: the
object is outranked-evicted ~6 bars post-birth (CONTEXT_RANGE raw
score beats it), so the mutation stream never runs - the arm is just
"one early box + silence".

**uip2_on - persist** (sub-flag ev_uip_persist, close veto):
box **16/119 (+6 = V0 PARITY .134)** | level 4/76(-4) | line 23/193(+3) |
bracket 29/85 | clutter 4.67 | margin 95/179 | births 1.0/panel |
live 9.0@tau (+2) | flips +19/-14 | suite 71/72 (only
test_pullback_end_box_birth, named-seven) -> FAIL 3.1b.

**The frontier moved.**  Persist+mutate is the FIRST mechanism to reach
v0's box@1 at ink +1/panel - the governing-box economy reproduced on
v1's stream.  The cost is no longer clutter; it is FAMILY SLOTS: the
close-exempt object permanently occupies a box-family position, so
CONTEXT_RANGE births drop (189 vs 195 born) and carried levels die
earlier -> level@1 -4.  Level births are unchanged (482) - the loss is
lifetime, not generation.

Options not tried (out of my 2-variant budget, for your spec/Owner):
- exempt the ev object from the box-family cap entirely (it is the
  family's +1 object per EVAL-AUDIT; making it a non-counted member
  may unblock CONTEXT_RANGE births while ink stays 1);
- persist-until-window-edge instead of close-exempt-everything.

OFF-identity 576/576 (objects+cand_log+events) both arms.

### Correction to s.20 mechanism (verified on cache, 02:4xZ)
The level -4 is NOT (only) joint-cap death crowding - object death
profiles are nearly identical off vs on.  Two verified loss paths at
the pick: (a) the ev object's edges SEED competing LEVEL_CARRIED
objects that outrank the correct level (9.40c: ev box bottom 13195.4
-> level pick moved 13196->13192/13200); (b) the persistent slot
suppresses level presence entirely at tau (9.61c: zero live levels
under ON vs the correct 12575.2 pick under OFF).  i.e. the mutating
box's edges BECOME level structure - the "one object" perturbs the
level stream, it is not free even at ink-1.


## 21. DR-BOX lane findings for build/box lanes (deepresearch, R64)

Full report: `deepresearch/DR_BOX_SELECTION.md`. Cache-only
measurements on `event_cands.pkl` + TUNE goldens, 119 goldens.

For the `ev_uip_persist` arm (16/119 already measured):

1. WHY it works, measured: keep-last-1 re-anchor = "youngest-born cand"
   picks golden edges 20/51 reachable (null p95 7); matches sit at
   median birth-rank 32 — they are the LAST births, so keep-first-N
   throttles cap at 4/51 (N=2). Freshest-retention is the mechanism.
2. pb-route interleave: youngest-either 20/51 vs youngest-rd 18/38 —
   letting `pullback_end` also rewrite the object is worth ~+2 edge-exact
   goldens (T1/UIP-rd was rd-only). Cheap arm: allow pb writes too.
3. Span/IoU haircut: matching cands' drawn span has IoU>=0.5 vs the
   golden containment window in only 9/20 rule-hits. A causal fix —
   build_start = walk back from t0 while bars overlap the band —
   measures 14/20 (+5). Different from the ledger's failed ep-onset
   detector (lands inside episode); worth one A/B.
4. Ceiling honesty: oracle over 19 causal features = 30/51, over 35
   stated conjunctions = 34/51; >=17/51 reachable are causally
   indistinguishable (semantic pick). Plus 68/119 unreachable
   (edges never proposed; med nearest-cand 10.5p away; session proxies
   rescue <=8). Author-exact matching caps ~29% — consistent with
   Osler's ~30% inter-expert level agreement.
5. Hindsight rejected: fastest post-tau break picks golden 2-6/51
   (below random). Do not chase post-tau-correlated features.

Data questions for other lanes: none pending.


## 22. Option-B port PREPARED (build lane, R63 s.63.4 - not run, R64 hold)

Flag `salience.box_v0_family` (default False, provenance in
params_v1_1.json).  Implementation @8b67d0eb, engine.py `_v0_sync`:

- A verbatim `engine_v0.PerceptionEngine` runs alongside on the same
  bar stream (fed after `salience.round`); its box-family objects
  (BOX + RANGE_OPEN - v0 births no CONTEXT_RANGE) are mirrored into
  `e.objects` via `meta_v0_port` markers.
- Mirrors are NOT registered in `_act`, so `active()`, budgets,
  scoring and eviction never see them - v0's own lifecycle is
  authoritative (state/geometry/t_left/events resynced each bar).
- v1's own box-kind cands (BOX, RANGE_OPEN, CONTEXT_RANGE per
  `salience.FAMILY`) are suppressed at admission (`fam_v0` outcome).
- close() on a mirror is vetoed; vetoes logged to cand_log.
- Ranking: mirrors carry score=None -> eval ranking falls to recency
  = v0's newest-governs ordering.
- Arm `v0box_on`/`v0box_off` registered in `_ab_onehash.py`, group
  `v0box`.  DO NOT RUN until the Owner picks option B.

Verified:
- mirror set == standalone engine_v0 box family, byte-identical
  (type/t_birth/t_left/t_right/state/geometry) on 5/5 smoke panels.
- v1 own box-family objects: 0 born under flag (34-66 suppressions
  per panel); 0 mirrors in active().
- engine pickles/unpickles with _v0e intact (cache-compatible).
- OFF-identity 198/198 on current TUNE vs a4b_off@54bd315b070afbd6;
  full 576-file canonical in progress (log will carry the number).

Semantic note for the Lead: this is the REAL fused engine - v1
internals run with an empty own-box family, so v1' non-box objects
can differ slightly from the stacked-hybrid (which ran parent v1
internally, then filtered at eval).  The box set is verbatim v0;
level/line shifts vs the hybrid's 8/76 + 20/193 projection are what
the authorized A/B measures.


## 20. R66 §66.4 — episode-anchored `build_start` spec (BOX-LAB, stated params)

Purpose: the event object's recorded containment window currently
starts at the pivot-pair bar; the golden's `build_start` starts where
price first held inside the band. Recording the episode start lifts
the ruler's span test without touching edges. Measured by DR-BOX and
independently reproduced by BOX-LAB: span-IoU ≥ 0.5 on rule-hits goes
**9/20 → 14/20** (≈ +5 ruler-valid box hits on the youngest-pick rule).

### Rule (all parameters stated)

For the event-family object only (the UIP object under
`ev_uip_persist`), at **every write** (birth and each rewrite):

```
bs = t0_cand                       # earlier-pivot bar, as now
while bs > bar_of(w0) and       h[bs-1] >= lo and l[bs-1] <= hi:
    bs -= 1                        # walk back while the PREVIOUS bar's
                                   # range overlaps the band [lo,hi]
record meta_build_start = bs
```

- **Overlap test** (the only parameter): bar `b` overlaps the band iff
  `h[b] >= lo and l[b] <= hi` — any intersection, no tolerance added.
- **Left cap:** `bar_of(w0)` — never walk before the panel window.
- **Right side unchanged:** `be`/`break_bar` keep existing semantics
  (whatever the object already reports); only the left anchor moves.
- **Drawn span untouched:** `t0`/t_left stays the earlier-pivot bar —
  this is a *recorded containment window*, not a redraw. The ruler
  prefers `bs`/`be` when present (`_eng_window`), so the object flips
  from the `coverage` fallback route to `containment_iou` — that is
  the intended effect, and it is honest: the box semantically contains
  the buildup the author watched form.
- **Recompute on every rewrite:** when a later event rewrites
  (lo,hi,t0), recompute bs from the new values — the walk-back is a
  pure function of (lo,hi,t0,bars), no state.
- Non-event box-family objects (CONTEXT_RANGE etc.) are NOT touched.

### Expected effect

- Box@1: +0..+5 over `uip2_on`'s 16/119 (the +5 measured on
  rule-hit cells; flips depend on which object is picked at τ).
- Level/line/clutter: no mechanism for change — this alters only a
  recorded field on one object.
- No new births, no new ink, no lifecycle change.

### Why this differs from the dead ep_onset detector (ledger #23)

The R59-era detector tried to *find* the episode start as a birth
trigger and landed inside the episode (741 vs golden 580). This is not
a detector — it is a **recorded-window extension** on an object that
already exists: the band is known, the walk-back just marks where bars
stopped overlapping it. Detection problem → bookkeeping problem.
- 03:27Z ## 23. BUILD -> BOX-LAB: R66 s.66.3 official results (prereg score)
  
  OFFICIAL M1 @23504c93 (same-hash A/B vs C-2 parent evb_off + uip2_on base):
  
  | arm | box@1 | level@1 | line@2 | bracket@1 | clut med | margin<=5 | births/pan | live@tau | suite |
  |---|---|---|---|---|---|---|---|---|---|
  | evb_off (C-2) | 10/119 .084 | 8/76 .105 | 20/193 .104 | 29/85 .341 | 4.33 | 114/179 | 0 | 7.0 | 67/67 |
  | uip2_on | 16/119 .134 | 4/76 .053 | 23/193 .119 | 29/85 .341 | 4.67 | 95/179 | 1.0 | 9.0 | 67/67* |
  | uip2_lvfree (V1) | 16/119 .134 | 7/76 .092 | 20/193 .104 | 29/85 .341 | 4.33 | 111/179 | 1.0 | 8.0 | 67/67 |
  | uip2_lvfree_pb (V2) | 16/119 .134 | 7/76 .092 | 20/193 .104 | 29/85 .341 | 4.33 | 111/179 | 1.0 | 8.0 | 67/67 |
  
  (*uip2_on suite run earlier on the 72-test file showed 71/72 w/ only
  test_pullback_end_box_birth; current suite is 67 tests, parent 67/67.)
  
  Prereg score vs s.66.3 predictions: V1 lvl 7-8 -> 7 IN; box 16-17 -> 16
  IN; suite 71/72 -> 67/67 on current file (test_pullback_end_box_birth
  PASSES under lvfree - pb write not required for it). V2 box 16-18 -> 16
  IN; suite -> 67/67. V2 flips vs V1: +0/-0 - pb rewrites fired but
  produced zero pick changes on TUNE. V2 still carries UIP-all semantics
  (DR-BOX +2 edge-exact headroom) and cures the pb-route veto asymmetry.
  
  Level-loss mechanism confirmed closed by decoupling: (a) uip-edge
  LEVEL_CARRIED seeding vetoed (seed_veto=2/panel); (b) uip-persist object
  excluded from class-budget live/budget_hard/fam_total_live/joint_struct
  -> LC snap 4->6, level loss -4 -> -1 (residual: 2 lvl flips - 9.49a,
  9.56b - vs +1 gained 9.5c). Side effect: v1-box cands no longer
  veto-bypassed -> BOX births 342 -> 14 (cleaner stream).
  
  BOTH ARMS PASS s.3.1 keep-gate. Recommendation: V2 (uip2_lvfree_pb) -
  same row, plus pb-write headroom for s.66.4 build_start.
  
  OFF-identity @23504c93: 576/576 canonical. All research flags OFF by
  default. Engine tree clean at C-2 defaults.
- 03:46Z ## 24. BUILD -> BOX-LAB: R66 s.66.4 official result
  
  uip2_bs @c06365ce vs uip2_lvfree_pb base: BYTE-FLAT on every deliverable -
  box 16/119, level 7/76, line 20/193, bracket 29/85, clutter 4.33,
  margin 111/179, births 1.0/pan, live@tau 8.0, suite 67/67, flips +0/-0.
  
  Mechanism verified live end-to-end: meta_build_start recorded at birth
  + every rewrite (2012-03-01@600 smoke: bs_cet=240=w0 cap bound), eval
  _eng_window consumes rec['bs'] -> engine containment window extends
  earlier; yet zero of 119 box@1 cells flipped. The offline 9/20->14/20
  IoU-valid gain on the 20 rule-hit cells did not propagate to @k picks -
  likely the golden cells whose windows would benefit are matched to
  other objects, or their bs extension stayed within the already-matched
  overlap. Prereg +0..+5 -> landed at 0.
  
  Recommendation: keep the flag OFF-or-on is cosmetic for M1; it records
  a diagnostically-useful field at zero measured cost. If edge-exact/IoU
  instrumentation (box_ceiling) is rerun, expect the 14/20 gain to show
  there instead. OFF-identity @c06365ce: 576/576 canonical.

## 23. R67 s.67.4 — episode-container (EC) birth channel: measured spec (BOX-LAB)

Offline ruler-exact count on the cache (`boxlab/r67_channel.py`,
eval_v2 imported). Three pre-registered triggers measured once; only
`spike_base` v2 clears the reach bar. Numbers are birth-channel reach
(would the object exist and match if ranked first), not engine scores.

### Measured (preregistered params, BOX_RESEARCH.md R67 section)

| trigger | +reach on 68 unreachable | reach all-119 | births/panel |
|---|---|---|---|
| session_range (Asia 00-07 box @07:00) | 0 | 3 | ~1/date |
| spike_base v1 (K6,S2.0,M8,4-60p,G12) | 2 | 11 | ~3.7 |
| first_block (N6,L1.5,B8,X1.0) | 0 | 3 | low |
| **spike_base v2** (+absorption test) | **3** | **12** | **1.48 (med 1.0)** |

V2 = V1 plus: post-spike bars (i_s,i_s+M] mean range <= 1.0*ABR AND
base height <= 40p. Adds 3 unreachable goldens ruler-exact (9.17c,
9.33c, 9.35a; 2 of them live at tau under close-outside-band death).
This is borderline vs the "~1 extra birth/panel" bar -> handed off as
a candidate, build decides.

### Spec (EC-B v2 `spike_base`), all parameters stated

- Spike: bar i qualifies iff `|c[i]-c[i-6]| >= 2.0*ABR(50)[i]`
  (causal ABR in pips, `cache.abr` semantics).
- Spike extreme i_s: for an up-move argmax h over [i-6,i], down-move
  argmin l (the move's extreme bar, not i).
- Base window: bars [i_s, i_s+8] (spike bar + 40 min absorption).
- Absorption test: mean(h-l) over (i_s, i_s+8] <= 1.0*ABR[i_s].
- Height gate: 4p <= (max h - min l over [i_s,i_s+8]) <= 40p.
- Edges: [min l, max h] over [i_s, i_s+8] — the spike extreme is
  INCLUDED (book: "an absorption box after a spike includes the
  spike extreme").
- Birth: at bar i_s+8 close. t0 = i_s (drawn span starts at the
  spike extreme). Cooldown G=12 bars between births.
- Lifecycle: same as the UIP event object — one extra box-family
  object; dies on first close outside [lo,hi]; recorded window =
  episode-anchored bs = walk-back from i_s per s.66.4 (optional,
  same rule as s20).
- Family/slots: box family, exempt from level/line budgets; whether
  it shares the box-family slot with the UIP object is build's call —
  if shared, prefer the younger at pick time (unmeasured).

### Honest caveats

- +3/68 reach is small; 9/12 of its all-119 hits duplicate bands the
  event stream already covers (redundant but harmless).
- ~1.5 births/panel will add ~0.5-1.5 live objects at tau on some
  panels -> clutter may push above 5.0; measure in the A/B.
- EC-A (Asia range) reached ZERO unreachable goldens despite 12 of
  them starting before 07:00 — the author's Asia boxes are not the
  raw overnight extremes (interior edges again). Not recommended.
- EC-C (first sideways block) reached ZERO — the author's blocks are
  picked by pivot-pair structure, which the event stream owns.
- 04:19Z ## 25. BUILD -> all lanes: STABLE C-3 declared (R68 s.68.3-4)
  
  V3 uip2_lvfree_pbbirth PASSED the keep rule and is folded into
  params_v1_1.json defaults: STABLE C-3 = 1a5502129b4c1554.
  
  - M1 @8361fe85 (arm, pre-fold): box 16/119 .134 (=v0 bar), level 7/76
    .092, line 20/193 .104, bracket 29/85 .341, clutter 4.33, margin
    110/179. First arm meeting M1 on all 3 families AND clean suite.
  - Suite of record (research/perception/tests, 72 collected): 72/72 on
    arm params AND on post-fold defaults. test_pullback_end_box_birth
    cured: pb cand forms at v0's route gate (idx-t0a>=3) pre-birth.
  - Canonical: new defaults byte-identical to arm cache 198/198 TUNE.
  - OFF-identity pre-fold @8361fe85: 576/576 vs C-2.
  - Flips V3 vs V1: +0/-0 on TUNE picks (pb birth fires earlier on ~48
    more panels but rd rewrites converge edges identically).
  - Snapshot _scratch/freeze_candidates/1a5502129b4c1554/ + SHA256.txt.
  - Awaiting EVAL-AUDIT verify + GATE_PACK_C3 (s.68.4).
  
  NOTE for lanes reading caches: after the fold, 'off'-family arms
  (yng_off/evb_off = _KEPT defaults) produce the UIP objects - the C-3
  engine IS the new parent. All other research flags stay OFF by default.

### 24. MIGRATION A2-A6 landed pending ARCH_REVIEW (R71 s.71.2) — build, 04:58Z

Timing disclosure: A2 (ObjectStore) landed 04:31Z pre-R71; A3-A6
landed 04:36-04:56Z before this session read R71 (rulings checked
post-A6). Per s.71.2 they stand **pending review** — every step is a
pure move that passed id-check 198/198 vs C-3 cache + suite of record
72/72:

| step | hash | change | verify |
|---|---|---|---|
| A2 store | 033aad2b | Obj+ObjectStore -> objects.py; engine shims (objects/_act props, __setstate__ legacy-pickle bridge) | 198/198 + 72/72 |
| A3 pipes | ba1b9532 | pipes.py FamilyPipe shells; 12 engine.update call sites route pipes.* | 198/198 + 72/72 |
| A4 round split | e1775edd | salience.round() -> _grave_sweep/_yield_sweep/_score_pass/_grant_pass->_admit_one/_yield_birth/_ctx_convert/_displace/_joint_pass/_pool_sweep | 198/198 + 72/72 |
| A5 fam tags | 63148cff | Candidate.fam=FAMILY.get(kind) shadow field (unread) | 198/198 + 72/72 |
| A6 retire order | 350b5b69 | _retire pinned to declared RETIRE_FAM_ORDER family-major | 198/198 + 72/72 |

Current tree @350b5b69 = C-3 + A1-A6, byte-identical behavior.
Migration queue HALTED at A6 — Phase B not started. If ARCH_REVIEW
returns FIX/BLOCK on any step it is individually revertable (pure
moves, freeze snapshot 1a5502129b4c1554 intact).

Meanwhile build runs s.71.3: C-3 per-bar speed check 55 DESIGN days
via heavy_run.py (queued behind DR-LINE's lock).

### 25. ARCH_REVIEW fixes applied — build, 05:08Z @2d497427

- **A6 REVERTED** per review (c) BLOCK: `_retire` sweeps `active()`
  append order again (the parent order). `RETIRE_FAM_ORDER` remains as
  a declaration-only constant; family-major ordering becomes a
  measured arm later. (Family-major was measured 198/198-flat on TUNE
  — flat there, but the wall_gone close-order channel is real.)
- **A1 FIX satisfied**: `_idchk_full.py` = **623/623 byte-identical**
  on every cached `uip2_pbbirth@8361fe85` panel (all TUNE windows),
  stronger than the plan's 1728-run convention for this oracle.
- **A2**: id-check + suite now logged; `__setstate__` bridge verified
  on real pre-A2 pickles (623 files, 0 errors); mirror/ACTIVE-write
  invariant documented at `_v0_sync`.
- **A3**: pivot/tracker call order pinned textually at the call site.
- **A5**: `getattr(c,"fam",None)` convention documented for pre-A5
  pickled Candidates.
- Suite 72/72 on the final state. Queue halted for per-step review
  verdicts; B1-B7 verdicts already in ARCH_REVIEW (B2/B3/B5/B6/B7
  BLOCK on the plan texts — no Phase B work until re-spec'd).
- 06:02Z ### 26. BUILD -> ARCH: B4 spec literal-order audit (pre-landing catch)
- 06:02Z B4's pinned orders don't match code verbatim - an implementer following the table literally would produce a DIFFERENT sequence (not byte-identical -> B4 fails its own gate). Actual update() order @2d497427:
- 06:02Z   pivot fan-out: annot.on_pivot(=patterns) -> level.on_pivot -> box.on_pivot -> [if is_structural: reanchor_check + propose_context_range] -> [if ev_route_box: _ev_box_birth] -> [if ev_uip: _ev_uip_step] -> line.on_pivot. Spec text omits _ev_box_birth (flag-OFF but a real call site) and the is_structural guard on reanchor/context_range.
- 06:02Z   tracker order: asia_update -> congestion_scan -> session_update -> maintain(box,line,level = x3, annot has NO maintain) -> annot.squeeze_scan -> _retire -> salience.round -> _pressure_update. Spec says 'maintainx4 -> _retire -> round' - actual is maintainx3 + squeeze_scan between, plus _pressure_update after round. patterns.py owns squeeze_scan (no maintain method exists for annot).
- 06:02Z Recommend rev2 spec patch before re-review verdict: tracker pin = 'asia_update -> congestion_scan -> session_update -> box.maintain -> line.maintain -> level.maintain -> annot.squeeze_scan -> _retire -> round -> _pressure_update'; pivot pin adds '[flag ev_route_box: _ev_box_birth]' before ev_uip and marks reanchor/context_range as is_structural-gated.
- 07:39Z ### 27. R75 s.75.3(1) L-1 cross-family anatomy - build, read-only on caches (l1_close@8b330117 vs uip2_pbbirth@8361fe85)
- 07:39Z COUPLING PATH (named, file:line): L-1 relaxes the defended veto + re-orders line picks -> different line objects/anchors -> on decisive traverse lines.py:504 calls levels.spawn(i, price_at, 'broken_line_edge', src=line) -> levels.py:33 spawn proposes a LEVEL_CARRIED whose price IS the line's traverse price and whose feats inherit the src line's touches/prom_abr -> the carry cand competes for the same famlive_level=1 slot and same-family _displace (salience.py ~790/1328). Carries are joint-rate-ledger EXEMPT (salience.py ~905 cont exemption) but still consume the level live slot. defended_origin proposals additionally hit _budget_ok def_level_max_live=2 (levels.py ~300, suppressed_budget). Origins registry verified byte-identical (29=29 on 9.32b) - the divergence is NOT generation-side; it is carry geometry + slot timing.
- 07:39Z PER-CASE (5 lost level@1 hits): 9.5c gold 13137 - carry born 13126.31 vs par 13125.67 at same bar 22 (geometry inheritance, P1); the matching defended level@13136.77 never born in arm (bar166 slot went to 13139.7). 9.32b gold 13167 - bar91 arm slot taken by broken_line_edge LEV0013@13168.5 which DIED bar92 (t_right=92); defended cand 13166.2 was suppressed_budget; par born defended LEV0013@13164.9->repriced 13166.0. 9.40c gold 13194 - par carry LEV0016@13196.16 matched; arm's carry landed 13214.11, defended cands near 13196 all suppressed_budget. 9.51b gold MINI 12950 - defended cand 12949.4 proposed bars 89-91 then suppressed_budget; arm slot held by earlier wrong defended LEV0012@12942.5 (born bar88 vs par's 92). 9.64c gold MINI 12527.7 - par defended LEV0017@12528.0 born bar176 covers span 1010-1025; arm's same-price LEV0014 born LATER -> span no-overlap -> level_zone miss; defended cand suppressed at bar173.
- 07:40Z ANSWER to 'did extra line births change any level cand's birth time/state': YES, both. Birth TIME: carries fire at the line's traverse bar, which moved under L-1 (9.64c same-price object born later; 9.51b arm level born bar88 vs par bar92). STATE: carry feats inherit src line touches/prom -> different scores; same object id can change route (9.32b LEV0013 defended_origin in par, broken_line_edge in arm). Corpus-wide (623 windows): PL births 2558->2627 (+69), defended_origin level births 699->677 (-22), congestion_edge 0->+9.
- 07:40Z ISOLATION VARIANTS (proposed, NOT RUN per s.75.3.1 - joint estimate per s.75.2 standing rule): IV-1 'level.carry_slot' (separate carry lane): carry-route cands (route broken_*/congestion_edge) compete for a dedicated famlive_level_carry slot (default 1) and _displace partitions live levels by carry vs non-carry; defended/formation keep famlive_level=1. Estimated vs l1_close: level +3..+5 (the suppressed defended cands get their slot back), carries preserved (2 carry-route parent hits safe), box/line untouched, clutter +<=1 level on co-fire panels. Risk: raises level-family live cap to 2. IV-2 'level.carry_corroborated': spawn returns a carry cand only if a defended origin with n_def>=def_min_defences exists within def_nms_band_pips of price_at, else outcome 'carry_no_origin'. Estimated vs l1_close: kills uncorroborated shifted carries (4/5 lost cases had no origin at the shifted price zone), keeps the 2 carry hits - VERIFIED both carry winners have origins within 4p at birth (9.5c: 5 origins; 9.40c: 5). Displaces: <=0 on hits, possibly a few carry births total; box/line untouched. Both default OFF (flag OFF == parent). Awaiting Lead ruling to run.
- 08:31Z ### 28. EVAL-AUDIT -> DR-RULES: Part E unblocked. owner_pack/dr_rules_item_geom.jsonl (102 rows) = blind item geometry {seq,panel,tau,kind,t0,t1,lo,hi,price,p0,p1,slope,family} - class-identifying fields (truth/engine/how/id/letter/side/tau_at) stripped; kind is shared spec-type vocab. Seq<->item map reproduced seed-deterministically, 0/102 mismatch vs key. Compute C1-C8 on it blind; join vs key stays evalcheck-side (s.77.4b).
- 08:50Z 08:47Z ### 26 (addendum, post-B5 @bbdee030): pivot fan-out literal order unchanged positionally, but call name updated - line now reads 'if salience.ev_uip: pipes.box.event_step(i,piv)' (engine.py:415-416). Tracker order unchanged. Patch the B4 spec against this tree so the pinned contract names the post-B5 call.
- 09:05Z ### 29. EVAL-AUDIT note (DR-RULES/Lead): Part E was executed evalcheck-side - DR-RULES closed at 08:56Z, 2min before the geom unblock; I ran their own DR_RULES_measure/report code on the blind export -> evalcheck/DR_RULES_pack_features.csv + join vs key at evalcheck/M2_RULES_JOIN.txt (s.77.4b discharged). If Lead wants independent Part E, DR-RULES can re-run on owner_pack/dr_rules_item_geom.jsonl and diff vs my CSV.
- 09:47Z ### 27-TT. R78 s.78.4(3) trade tags - fractions on C-3 objects at golden-decision taus (arm tt_tags @d8daa611, parent bbdee030)
- 09:47Z LIVE objects (DR_RULES_live rows, n = object@tau evaluations): box n=1244 tradeable 6.5% - per-tag rates: lone_edge 88.0%, shock_inside 35.3%, impulse_inside 30.5%, daylight 26.6%, steep 5.0%. level n=1237 tradeable 9.9% - superseded 77.5%, zombie 69.4%, steep 2.2%. line n=1552 tradeable 74.4% - zombie 18.4%, steep 9.5%.
- 09:47Z GOLDEN objects same taus (DR_RULES_golden rows, reproduces DR-RULES Part B within rounding): box n=119 tradeable 30.3% - lone_edge 58.0% (C6g fail), daylight 17.6% (C1@1.0 fail), shock_inside 14.3% (C3w@3.0), steep 5.0% (C2 q95), impulse_inside 5.9% (C4w@4). level n=76 tradeable 42.1% - zombie 53.9% (C7f@2), steep 5.3%, superseded ~0% (C8a not evaluable on golden anchors; C8@1 pass was 1.000). line n=193 tradeable 80.3% - zombie 14.5% (c7_sw span, C7s n/a on golden per Part B - closest stat), steep 5.2%.
- 09:47Z READ: engine objects are far more tagged than the author's (box tradeable 6.5% vs 30.3%, level 9.9% vs 42.1%) - same conclusion DR-RULES reached: engine boxes sit off EMA with lone edges, engine levels are heavily superseded/zombie. Tags are FACTS only (object.facts['trade_tags'], excluded from canonical); nothing filtered. Equivalence proofs: 80/80 golden rows + 425/425 live rows recomputed identical via the shared predicates.
- 09:47Z IMPLEMENTATION NOTE for any future 'trade view': lone_edge on live objects uses the module's 5.0p ruler-default (tol_g is golden-only, not evaluable on live rows). File: trade_tags.py LONE_EDGE_TOL_PIPS; engine._trade_tag_step; render.py grey style behind the flag.
- 11:11Z ### 28-TT2. R81 s.81.5(1) lifetime trade tags - fractions on C-3 objects at golden-decision taus (arm tt2_tags @fa2e52e5, parent d8daa611). tradeable = no TRADE_VIEW_HIDE tag (lone_edge is a FACT, never hides - author obeys C6 only 34%).
- 11:11Z LIVE objects (DR_RULES_live rows, n = object@tau evaluations): box n=1244 tradeable v1-tags 44.7% -> v1+v2 44.7% (stale_far 13.5% fired but always co-tagged; untagged-only 6.5%). level n=1237 tradeable 9.9% -> 6.2% (stale_far 12.6% adds ~45 hidden). line n=1552 tradeable 74.4% -> 54.1% - NEW TAG RATES: line_broken 11.3%, line_cuts_bodies 17.5%, stale_far 14.9% (+zombie 18.4%, steep 9.5%).
- 11:11Z GOLDEN objects same taus (author compliance - would the author be hidden too): box n=119 tradeable 65.5% -> 65.5% - stale_far 0.0% (author keeps boxes near price). level n=76 tradeable 42.1% -> 40.8% - stale_far 2.6%. line n=193 tradeable 80.3% -> 37.8% - line_broken 58.0% (n/e 3), line_cuts_bodies 13.5% (n/e 3), stale_far 0.5% (n/e 3). Golden conventions: line side inferred from dir (up=rising support/bottom, down=falling resistance/top); birth ~ t0; per-bar slope conversion exact (lv endpoints match p0/p1 to 1e-6).
- 11:11Z READ: stale_far targets the engine's E2 cleanly (live 12-15% vs author 0-2.6%). line_cuts_bodies rates match (live 17.5% vs author 13.5%). line_broken is the outlier: 58% of AUTHOR lines would be tagged (vs 11.3% of engine lines) - the >tol x 2-close rule at R81's fixed params is much stricter than author practice (author leaves lines drawn through modest closes). Params are R81-fixed, not tuned; flagged for the Lead - if the hide set is meant to reproduce the author's view, line_broken as specced over-hides vs golden.
- 13:39Z ### 29-TT3. R83 s.83.2 box_broken (entry-anchored break; arm tt3_tags @e7d13384, parent fa2e52e5). j0 = first bar >= t_left whose close is inside [bot-tol_e, top+tol_e]; break on (j0,t]: 3 consec closes beyond one edge (run3) OR one close >=3*ABR beyond (shock). Facts: exit_bar+break_clause. Joins TRADE_VIEW_HIDE.
- 13:39Z LIVE C-3 boxes at golden-decision taus: 180 object-evaluations, tagged 138 = 76.7% (run3 135, shock 3). creep diagnostic (>=3 closes beyond one edge, never a run of 3): 10 boxes. THE 16 C-3 BOX HITS AT THEIR TAU: 12/16 tagged (all run3) - untagged hits: 9.6a@600 BOX0001, 9.13a@505 BOX0001, 9.32a@478 BOX0002, 9.45a@350 BOX0006. This is arm Y's upper-bound exposure before replacements.
- 13:40Z GOLDEN compliance (same entry-anchored rule, own span/edges/tau): 3/119 = 2.5% tagged (all run3) - vs S2's broken scan 14%. Entry anchoring works: the author almost never lets 3 closes confirm beyond his box's own span, while 77% of engine boxes do. S1-b fatal boxes: 9.10c BOX0001 TAGGED (run3 exit19), 9.33c BOX0001 NOT (same as S2), 9.36c BOX0001 TAGGED (run3 exit35), 9.40a BOX0002 TAGGED (run3 exit7) - 3/4 caught. E5 panels all 4/4 live boxes tagged run3: 9.17b BOX0001 exit17, 9.36c BOX0001 exit35, 9.42b BOX0001 exit20, 9.48b BOX0001 exit104.
- 13:40Z READ: box_broken reproduces the reviewer's E1/E5 eye on engine objects (77% tagged incl. all 4 E5 panels, 3/4 S1-b fatal boxes) while touching only 2.5% of author boxes - the cleanest engine-vs-author separation of any tag so far. The 12/16 hit-tagging is NOT noise: those hit boxes are the incumbents holding the family slot (E3 incumbent monopoly); arm Y frees the slot and lets the pool promote - the keep-rule question is whether promoted replacements re-match >=16.
- 14:09Z ### 30-Y. R83 s.83.4 arm Y (box_yield kills box_broken objects as natural death incl. UIP incumbents; Y2 = OR stale_far). Engine flag box_yield {0,1,2}; _box_yield_step runs before salience.round so freed slots go to existing pool rules; nothing else changes. Measure = 576 fresh engine runs/variant over the canonical (date,w1) grid.
- 14:09Z M1 ROW (golden hits at decision taus, fam budgets box1/line2/level1/bracket1): Y1 = Y2 IDENTICAL - box 7/119 (parent 16 -> KEEP RULE FAILS, needs >=16), level 3/76 (parent 7 -> FAILS parent-1=6), line 18/193 (parent 20 -> FAILS parent-1=19), bracket 30/85 (parent 29 ok), census clutter median 4.67<=5.0 (179 panels). stale_far adds nothing beyond box_broken for M1.
- 14:09Z PER-HIT FLIPS vs parent picks: box 16 parent hits -> kept 2 (9.13a@505 BOX0011, 9.18a@515 BOX0013), lost 14; replacements gained 5 box hits (9.2b@765 BOX0021, 9.4b@815 BOX0021, 9.14a@530 BOX0012, 9.15b@895 BOX0020, 9.45b@740 BOX0018) -> net box 7. Collateral: level parent hits 3 kept/4 lost +0 gained -> net -4; line 13 kept/3 lost, +13 gained rows -> net -2; bracket 17/17 kept +1 gained (9.57c@857) -> net +1.
- 14:09Z E3 re-diagnosis (e3_diag.diagnose imported, never forked) on the Y engine: classes {BORN_KILLED 48, BUDGET_CUT 50, HIT 7, LIVE_OUTRANKED 4, NEVER_BORN 10} vs parent {BUDGET_CUT 60, ...}. Parent BUDGET_CUT 60 -> only 4 became HIT under Y (9.2b@765, 9.4b@815, 9.15b@895, 9.45b@740). Yield deaths themselves create BORN_KILLED misses - the freed-slot mechanism works (5 promoted boxes match) but the pool's next-best box almost never has the golden's geometry.
- 14:09Z VERDICT: INFO; both variants FAIL the keep rule (box 7<16, level 3<6, line 18<19). NOT a KEEP candidate - killing the incumbent destroys more golden-matching boxes than the pool can replace. box_broken remains correct as a FACT/hide-tag (TT-3 @e7d13384); its use as a death sentence needs a Lead ruling if ever revisited. Prefix invariance: rerun with corrected comparator queued on heavy lane (see log).
- 14:10Z PREFIX INVARIANCE (corrected comparator _y_prefix.py: canonical() at floor-bar inside full run == stop-at-tau engine, 20 panels/55 tau-snapshots): Y1 55/55 PASS, Y2 55/55 PASS - arms are fully causal. (Comparator fix note: engine.update takes RAW price - eval.run_engine converts CA.bars pips via PIP=1e-4; a duplicated x1e4 in the first manual loop made a systematic false diff, and non-bar-minute taus like 533 need floor-bar snapshots.)
