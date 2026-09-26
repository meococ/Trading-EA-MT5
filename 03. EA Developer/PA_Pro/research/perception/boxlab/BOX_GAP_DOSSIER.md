# BOX GAP DOSSIER — F-X1 (R55 §55.3)

Freeze parent `ee2cbf1202db47b6` (= STABLE `9acaa206` + K7 marker.off +
K8 cong_pivedge + K9 rate_label_tf=2).  Compiled for the Owner's box
decision and for v2.  BOX-LAB, 2026-09-22.

**The gap:** box@1 = **10/119 (.084)** vs v0 **16/119 (.134)** — 6 hits
short.  Box is the only M1 family below v0.  The Lead does not relabel
it passed; the criterion goes to the Owner with the human ceiling.

---

## 1. The funnel (K9 state, `c1_missed.py` on `c1r_p_base@ee2cbf12`)

```
119  scorable BOX goldens
107  causally reachable at tau  (12 have NO causal edge pair — §4)
 57  covered by an edge-matching engine proposal
 10  hit at rank-1 (box@1)
 47  covered but missed — ALL die pre-birth, 0 born-and-missed
```

Missed buckets (golden-level, dominant resolution ≤ τ):

| bucket | n | mechanism |
|---|---:|---|
| `below_min_score` | 16 | cand score < `min_score_birth_signal` 5.0 |
| `outranked` | 11 | budget displacement vs weakest live structure (salience.py:1318 — dwell/priority/hysteresis), right cands scored 0.5–15.4 and still lost |
| `log_only` | 10 | covered only by `cluster_range_wick`/`kde` proposals — computed for the oracle, never pooled (`wick_birth` OFF) |
| `rate_limited` | 8 | `rate_box` 1/72 bars spent by an earlier cand; `box_score_pick` already live and still not enough |
| `expired` | 2 | cand TTL lapsed unresolved |
| born-and-missed | 0 | — |

The funnel is **pre-birth dominated**: every covered-missed golden had
the right geometry proposed and lost it in selection (floor / budget /
rate / pool-entry), not in ranking after birth.

## 2. Every C-1/C-2 box arm — one line each

### C-1 (parents → STABLE 9acaa206)

| arm | verdict |
|---|---|
| `cong_trigger` (congestion-run proposals) | **KEEP** — box 7→9/119 (+2), families identical, clutter 5.00. Mechanism: fresh cong boxes outrank stale envelopes at τ (timing, not coverage — 44/44 flat). Adopted into base 09:06Z. |
| `k55` born-rate with cong | kept — born recall .093→.111, oracle +1 (9.51b g0). |
| `lev_snap` | REJECTED (7/119). |
| `cong_density` peak | INERT — flat 9/119; density substitutes on 8% of cong cands, never reaches no-edge windows, 0 births. |
| `cong_density` quantile | REJECTED — box −2 (7/119); trimmed edges were what matched. |
| `cong_subband` (too_tall slice) | REJECTED — flat + clutter 5.33; 1123 cands, 0 born. |
| `cong_mixedge` (exact edge + old-structure edge) | disproved at design level — support counts do not separate right from wrong edges; reverted pre-A/B. |

### C-2 (K7→K9 parents)

| arm | verdict |
|---|---|
| `cong_pivedge` = **K8** (pivot-cluster-seeded cong bands) | **provisional KEEP** — box +1, level +1, coverage +3 (9.44b g1, 9.47b g0, 9.50b g0); standalone on pre-K7 it failed §34.5 leg3 (clutter 5.33), on the K7 config the formal `pedg_on` A/B passed at clutter 4.67. Default-ON in the K9 parent, awaiting F-E1. Mechanism (9.2b g0): pedg band scored 9.31 and displaced a 615-bar-old envelope at 6.56. |
| `wick_birth` (`p_wick`: pool the wick-variant stream) | REJECTED — box −1 (8/119), oracle .407; wick cands steal births on the shared `box_rank` formula instead of converting the log_only class. |
| `deeper_w=0` (X3: remove nesting penalty) | FAIL — coverage +1 but box −1, level −1, births 1.56→2.40/panel; the freed pool is mostly wrong cands. |
| `deeper_cap=2` (saturating penalty) | dead pre-A/B by arithmetic — 0/31 starved cands reach 5.0 (best 3.60). Every point on the deeper dial is dead. |
| pivot-support score term (X1) | NOT BUILT — saturates: 89% of right cands AND 96/103 wrong boxes carry 2-edge pivot support at own birth. |
| `box_score_pick` (X2: in-window score replacement) | already live since C1 — 153 BOX supersede events TUNE-wide; the 8 rate_limited goldens are limited *despite* it. Closed, no code. |
| level-registry vs density-matched null (X.S, `c1_registry.py`) | pivots KEEP (.708 vs null p95 .585); close-extremes-on-trigger-window DROP (.400 vs .477 — circularity confirmed); session hi/lo DROP (.046 vs .062); union .815 pivot-driven. Registry carries pivots only. |
| prior-day hi/lo/close rescue probe | 0/12 unreachable goldens rescued — dead. |

## 3. Levers left — and why each is banned

| lever | why not |
|---|---|
| cut `min_score_birth_signal` | floods 2488 wrong cands (build lane measured); also a threshold — banned |
| hysteresis → 0 | rescues 0 of the outranked right cands (median gap −5.83 to weakest incumbent), floods 112 wrong — build lane, 14:31Z |
| reweight prom/contain/touches/barrier | no failure mechanism named → weight-fitting on TUNE, §3.6 banned |
| `deeper` dial | dead at every point (cap=2: 0/31; w=0: A/B −1 box −1 level) |
| widen rate window | threshold; `box_score_pick` already implements the principled version |
| budget / dwell / pool-order changes | salience.py lifecycle; buys box hits with other families' ink |
| `wick_birth` ON | measured −1 box |
| older-structure sources (prior day) | 0/12 reach — dead |

Build lane's independent conclusion (14:31Z, on K9 cache): the 21
outranked right cands lose on score itself; the 30 below-floor right
cands sit inside the wrong bulk. Their words: the deficit **"needs a
signal source not in the feature set."**

## 4. The causal boundary

12/119 goldens have **no causal edge pair at τ**: one edge sits on near
structure, the other 6–15 pips outside the lookback's traded range, on
no tested source (pivots, close extremes, session hi/lo, prior-day
hi/lo/close all fail).  These are drawn beyond the tape — a human
draws with memory of older structure; the engine at τ cannot.

Reachable ceiling under tested sources: **107/119**; generation-to-hit
conversion today: **10/57**.

## 5. v2 mechanisms — the two to try first

1. **Age-decayed competition score for live structures** (salience-side,
   lifecycle).  The *only* mechanism observed converting coverage into
   hits is freshness displacing staleness: 9.2b (pedg 9.31 over a
   615-bar-old envelope 6.56), C-1's +2 (cong age-15 over envelope
   age-615).  Symmetric evidence: 19 right cands (11 outranked +
   8 rate-limited) lost slots to first-arrival ink; several scored
   5–15 and still lost.  Decaying the *incumbent's* slot-defense score
   converts first-arrival luck into earned position.  Needs v2
   governance — lifecycle is build-lane territory and untested as an
   arm.

2. **A new birth-score signal: graded wick-tip density along the
   edges.**  10 goldens are covered *only* by `cluster_range_wick`
   geometry that never enters the pool; pooling it under `box_rank`
   failed (−1) because prom/contain/deeper does not price tip density —
   the author's actual "eye level" criterion.  A tip-count × recency
   feature is a new signal (§3.6-clean in concept), not a reweight.
   Caveat: the binary pivot-support version saturated; the graded
   version is unproven.

## 6. Audit trail

Scripts (all read-only or flag-gated): `c1_missed.py` (anatomy),
`c1_nullsrc.py` (source null), `c1_registry.py` (density-matched null),
`c1_pivsup.py` (pivot-support diagnosis), `c1_ab.py` (arm registry),
`c1_livedump.py`, `c1_killtrace.py`.  Engine edits: `boxes.py` carries
`cong_pivedge` (default ON in K9 parent) plus inert flag-OFF knobs
(`cong_density`, `cong_subband`, `deeper_w`, `wick_birth` plumbing).
Flag-OFF identity vs parent verified at every measured hash.
