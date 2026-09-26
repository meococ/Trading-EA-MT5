# REVIEW_2 — independent adversarial audit (post-remediation pass)

Scope: `research/market/` — M0/M2 (descriptive), M3/M4/M4b/M5/M6 pipelines,
shared machinery (`mk_common.py`), all `out/*.json`/`*.npz`, and the report
layer (`MARKET_MECHANICS.md`, `LEVELS.md`, `BOXES.md`, `BOXES_M4B.md`,
`LINES.md`, `MOMENTUM.md`, `RHYTHM.md`, `PERCEPTION_IMPLICATIONS.md`,
`TOM_TAT_VN.md`).  Deviation context limited to `_REVIEW2_DEVIATIONS_D1D5.md`.
Prereg verified: `STUDY_PLAN.md` sha256 =
`abc8b5ba5a80d04928b78204e2d690a5cdb74b091f515a6ff8669cfb499f962c` (exact
match to the hash cited in every report).

This is an audit, not a review: every claim below was re-derived from the
npz/json artifacts, not trusted from the reports.

## Module verdicts

| module | verdict | reason |
|---|---|---|
| M0 clock | PASS | Server UTC+2/+3 EU-DST proven empirically; `cet_minutes` (close-based, server−60) consistent everywhere; NFP deviations honestly logged. |
| M2 rhythm | PASS | Descriptive only, warmup excluded, no forward stats; numbers in `RHYTHM.md` reproduce `out/rhythm.json` and `m7_daily_range.json`. |
| M3 levels | **FAIL** | F1 (resolver barrier flip on side=+1) corrupts every outcome label on half the event population; F2 corrupts its inference; F5 is a live causality-wall violation on the grid sets. |
| M4 boxes | **FAIL** | F3 makes per-symbol reporting and the ≥3/4-symbol stability leg structurally impossible; F2 corrupts its inference. Detector itself is causal and honest. |
| M4b (addendum) | **FAIL** | Same F3 decode collapse (all `per_sym={'EURUSD'}`); F2 corrupts its CI/p; prereg-hash citation mismatch (F9). Design doc is honest about Arm-OUT selection. |
| M5 lines | **FAIL** | Correct resolver and correct key factors, but all pooled CI/p/q come through F2's biased bootstrap → inference unverifiable as shipped. |
| M6 momentum | PASS-with-notes | Own additive day-block bootstrap (not F2-affected); segments gap-broken; warmup excluded; VR scale correct; EMA counter-trend pivot filter causal. Notes: F-M family scope is per-symbol-12 (plan ambiguous), and EMA "significance" is mechanical. |
| Shared machinery | **FAIL** | `contrast_boot` empty-arm zero-fill (F2) is a genuine statistical defect in the file every family runs through; `placebo_grid_levels` shares the F5 lookahead; `ledger_row` is dead code (F6). |
| Report layer | **FAIL** | `MARKET_MECHANICS.md` inferential columns contradict the shipped JSONs (F4); downstream docs propagate the corrupted M3 numbers. |

---

## Findings

### F1 — M3 outcome resolver has the side=+1 barriers inside-out — **BLOCKER** — F-R, F-O, F-A, F-T, F-B

`mk_m3_levels.py:329-334`:
```python
if side == -1:
    brk = {x: ev["zhi"] + x * A ...}; bnc = {x: ev["zlo"] - x * A ...}
else:
    brk = {x: ev["zlo"] + x * A ...}; bnc = {x: ev["zhi"] - x * A ...}
```
`side` semantics (`mk_m3_levels.py:218-222`): `side=+1` = prior close ≥ zhi =
**approach from above = support touch**. The correct mirror (as implemented in
`mk_m5_lines.py:261-267` for the identical estimand) is break =
`lo <= zlo − x·A`, bounce = `hi >= zhi + x·A`. The shipped code instead sets
the "break" barrier *above* the zone (`zlo + x·A = zhi + 0.5·A` for x=1,
tol≈0.25·A) tested as `lo <= brk` (`:356`) — trivially true on the first
resolution bar — and the "bounce" barrier *below* the zone
(`zhi − x·A = zlo − 0.5·A`) tested as `hi >= bnc` (`:357`) — also trivially
true. Both fire on the same first M1 bar; the tie-break at `:372`
(`"BREAK" if fb < fn else "BOUNCE"`) resolves the tie to BOUNCE.

Empirical proof (recomputed from `out/m3_events_*.npz`, all 4 symbols):

| set | side −1 P(bounce x1) | side +1 P(bounce x1) |
|---|---|---|
| S1 EURUSD | 0.644 | **0.982** |
| PRAND EURUSD | 0.642 | **0.980** |
| S2 / PDHPDL / ASIA / RND (all syms) | ~0.62–0.65 | **~0.96–0.98** |

Symmetry demands the two sides produce comparable raw rates (as M5 does:
0.63 both sides). The +1 arm is not "bouncing" — it is labelled by barriers
that are hit before price moves. `overshoot_x1` on side +1 has p75 = 0.0
(resolution at bar 0) vs a real distribution on side −1.

*Failure mode:* every M3 outcome field — `out_x1/out_x2`, `resbar`,
`overshoot_*`, `retreat_*`, `retest_12/48`, `role_rev` — is corrupted for
~50% of events. Consequently **all M3 families are invalid**: F-R contrasts
mix a valid side −1 half with a saturated side +1 half (S1_x1: side −1
D=+2.46pt, side +1 D=+0.45pt ceiling-noise → pooled +1.48pt); F-O overshoot
quantiles are halved by a mass at 0; F-B's placebo "breaks" on side +1 are
~2% deep-plunge selections, not exchangeable breaks; F-A/F-T inherit the
labels. The invalidation propagates to `LEVELS.md`, `MARKET_MECHANICS.md`
Q-R/Q-O/Q-A/Q-T/Q-B, `PERCEPTION_IMPLICATIONS.md` rows (edge_tol, window_bars,
swing premium, Asia H/L), and `TOM_TAT_VN.md` items 1,2,5.

### F2 — `contrast_boot` zero-fills the placebo arm when a resample empties it — **BLOCKER** — all pooled CI/p/q in M3, M4, M4b, M5

`mk_common.py:547-558`: stratum eligibility is fixed once on pooled support
(`elig = (RN.sum(0)>=min_cell) & (PN.sum(0)>=min_cell)`), but inside the
replicate statistic `pdif = np.where(PN_>0, PS_/..., 0.0)` — a resampled
stratum with zero placebo weight contributes `rdif − 0 = rdif > 0` at weight
`RN_` instead of being dropped. The bootstrap distribution is shifted upward
by ≈ E[Σ_rdif·wgt over emptied cells] — proportional to placebo thinness.

Demonstrations:
- Synthetic true-null (two arms, identical 0.62 rates, thin placebo cells):
  shipped → point +0.0135, CI [+0.061,+0.129], **p=0.0005**; with
  replicate-level both-arms-present handling → CI [−0.008,+0.032], ns.
- Real data, F-T t3p contrast rebuilt from npz (2 symbols): shipped bootstrap
  median +0.0086 vs corrected −0.0024 — a +1.1pt shift.
- The artifact fingerprint is in the shipped tables: `LEVELS.md` F-T x1_t1
  D=0.0448 with CI [0.0541,0.0690] — **the point estimate lies below its own
  CI lower bound**; x1_t3p D=−0.0019, CI [+0.0031,+0.0182], p=0.007 — a
  "significant positive" CI around a negative point; F-B retest48
  lo == D exactly; role_rev_r48 D=+0.03pt "significant" (q=0.033); F-A 8–24h
  D=+0.0031 with CI [0.0032,0.0104]; M4b fb(1,2] D=+0.079, CI [−0.43,+0.58].
  A point outside its bootstrap CI is impossible under a valid resample of
  the same statistic.

*Failure mode:* every pooled CI and p in M3 (F-R/F-A/F-T/F-B/F-C), M4
(F-BO/F-FB), M4b (F-Xb), M5 (F-TL/F-SLOPE) is anti-conservative upward; all
q-values derive from these p's. The pre-vectorization implementation
(`mk_m3_levels.py:453-515`, `contrast()` line 491 `rn[k]>=5 and pn[k]>=5`
inside the resample) handled this correctly — the regression was introduced
by the optimized engine. Dense-placebo contrasts (e.g. S1 vs PRAND, shift
≈+0.05pt) are probably sign-safe; thin-mask contrasts (F-T t3+, F-B, F-C,
M4/M4b bins) are not. M6 uses its own `boot_days` (`mk_m6_momentum.py:142`)
— unaffected.

### F3 — M4/M4b symbol-key decode collapses all symbols to EURUSD — **material** — F-BO, F-FB, F-Xb

`mk_m4_analyze.py:85-90` encodes the symbol index at coefficient 252
(`2·7·6·3`, ×3 = 756 when `hgt_key=True`). `run_contrast`
(`mk_m3_analyze.py:112-133`) decodes with `sym_factor=SYM_FACTOR=2772`
(`:104`) for the default calls and 8316 for F-FB (`mk_m4_analyze.py:156`) and
F-Xb (`mk_m4b_analyze.py:121`). Since every key < 2772·(si+1) ≤ 8316,
`keys // factor == 0` for all symbols → `per_sym = {'EURUSD': pooled D}`.

Verified empirically: all 20 contrast entries in `out/m4_results.json` and
`out/m4b_results.json` have `per_sym` keys `['EURUSD']` only.

*Failure mode:* (a) the ≥3/4-symbol stability leg can never fire → every M4
and M4b `stable=no` is an artifact — a genuinely stable effect would still
report `no`; (b) the mandate's per-symbol reporting leg is void for these
families; (c) pooled D is silently attributed to EURUSD. Not a blocker only
because both families were already reported unidentified/no-claim — the M4b
"unstable" verdicts quoted in `MARKET_MECHANICS.md:152-154`/`164-169` cannot
be trusted to mean what they say.

### F4 — `MARKET_MECHANICS.md` contradicts the shipped artifacts — **material** — reporting layer

Point estimates match but inference columns do not:
- `MARKET_MECHANICS.md:120-122` (Q-B): "**all contrasts ns** (retest12
  p=0.33; role_rev p=0.73)". `out/m3_results.json` F-B: retest12 p=0.004,
  q=0.008, stable=YES; retest48 p=0.002, q=0.008, stable=YES; role_rev_r48
  p=0.025, q=0.033. Same story in `LEVELS.md:162-165`. The flagship denies
  results its own pipeline asserts (those assertions are themselves
  F1/F2-contaminated — but the document must describe the artifacts or the
  artifacts must be fixed).
- `MARKET_MECHANICS.md:111` (Q-T): t3+ q=0.70 — JSON q=0.0084.
- `MARKET_MECHANICS.md:57-61` (Q-R): CIs differ from `LEVELS.md` on every
  row (e.g. S1_x1 CI +1.09..+1.73 vs JSON +1.39..+2.07).

*Failure mode:* the consumed summary does not reproduce `out/*.json`. Likely
authored from a stale run; either way the headline document is not evidence.

### F5 — Grid/placebo level envelopes use full-day `nanmedian(abr)` — **material** (bounded) — RND, PRND10/20, PRAND, M4 P-RAND pool

`mk_m3_levels.py:154`: `A = nanmedian(abr[m])` over the whole day, sizing
`day_open ± 3.5·A`; identical pattern in shared `placebo_grid_levels`
(`mk_common.py:383`). The set of levels monitored on day d depends on
realized volatility of bars *after* the events — the day's level selection
is not a function of bars ≤ t. This is a literal violation of the mandate's
causality wall on the placebo workhorse itself (PRAND) plus RND/PRND grids
and, via reuse, the M4 fake-edge pool (`mk_m4_boxes.py:230` calls the same
`grid_columns`). Impact is bounded — band width only, anchor `o[i0]` is
causal — but it is exactly the class of leak the wall exists to prevent;
a causal equivalent (`abr` at the day's first bar) is one line away.

### F6 — Ledger-row requirement not implemented — **material** — compliance

`pa_ledger` imported (`mk_common.py:42`), `ledger_row` defined+exported
(`:744-763`), and docstrings promise "one ledger row per result family"
(`mk_m3_levels.py:12`) — but **no module calls it** (zero call sites).
Mandate lines 29-30 require each family appended as `kind=market_study`
referencing the prereg hash. Reports cite corrected rows T000380–387 and
T000390; whatever those rows contain, the shipped code path cannot have
produced them. Verdict: the prereg-discipline requirement is unmet in source.

### F7 — M4 placebo poke depth is not streak-merged — **minor** — F-FB bins

Real pokes merge consecutive wick bars and record max depth
(`mk_m4_boxes.py:170-191`); PPK events record only the first poking bar's
depth (`:261-289`, subsequent bars skipped by the FRESH gap). Placebo depth
distribution is biased shallow at equal event rate, degrading the declared
depth-bin matching further (subsumed by the D22 not-identified flag, but the
asymmetry is real and unremarked).

### F8 — Dead-code landmines with a different mis-anchoring — **minor**

`mk_common.resolve_touch_outcome` (`:340-345`) anchors side +1 barriers
`up=zlo+x·A`/`dn=zhi−x·A` — outward but ~2·tol tighter than the mirrored
spec. No callers (also `first_touch_events`, `match_strata`,
`block_boot_diff` are unused). If reused, they produce silently different
numbers. Delete or fix.

### F9 — Cosmetic / provenance notes

- `mk_m4b_shifted.py:2` cites addendum prereg `sha 9c1972ac…`; the current
  `STUDY_PLAN_ADDENDUM_M4B.md` hashes `4abca652…` — the file changed after
  hashing or the citation is wrong; prereg provenance unclear.
- `mk_m5_lines.py:153` freshness is `(t − last_hit) > 24` — off-by-one vs
  "prior 24 bars".
- `placebo_lines` (`mk_m5_lines.py:107`) uses one global RNG stream across
  symbols — deterministic but not per-symbol; same δ sequence reused.
- F-B pools {S1,S2,PDHPDL,ASIA,RND} (`mk_m3_analyze.py:382`) while F-T pools
  without RND — inconsistent scope, plan silent.
- M2's Asia window is `cet<480` (`mk_m2_rhythm.py:66`) vs M3's `cet<=480`
  (`mk_m3_levels.py:122`) — one boundary bar inconsistent across modules.
- Freshness window truncated at level birth (`mk_m3_levels.py:210-211`)
  admits formation-adjacent first touches: the confirming retrace guarantees
  a ≥1·ABR away-excursion inside the truncated window, so newborn pivot
  levels pass `away` more easily than day-start placebos — a declared,
  defensible choice; flagged as an interpretation caveat, not a defect.
- F-M family scope is per-symbol-12 (`mk_m6_momentum.py:355`); the plan's
  "family size 12" is ambiguous — acceptable reading, worth noting.

## Checks that passed (silence is not a pass)

- **Walls:** every loader call is `pa_data.load_m1(sym, split="DESIGN")`
  (`mk_common.py:69`, `mk_m0_clock.py:70`); no `pa_fill`/`pa_eval`/`pa_random`
  anywhere; all writes under `research/market/` (out/, *.md, figs/).
- **Causality, the parts that are right:** pivot confirmation lag
  (`dc_pivots`, `mk_common.py:137-200`); ASIA armed strictly post-window
  including the server-day wrap (`mk_m3_levels.py:102-138` — the prior
  lookahead is genuinely fixed); PDH/PDL = completed previous day
  (`:75-99`); freshness rechecked on the live window; forward indexing is
  `t+H` everywhere (`:587-591`, `mk_m4_boxes.py:303` `t+1`); warmup excluded
  in every detector; M5 line birth at second-pivot confirm with own causal
  death (`mk_m5_lines.py:72-97`); M6 segments break at >300s feed gaps and
  drop the boundary return (`mk_m6_momentum.py:57-96`).
- **Placebo machinery:** deterministic per-symbol seeds via `crc32` (D3
  satisfied: `mk_m3_levels.py:25-27`, `mk_m4_boxes.py:231`,
  `mk_m4b_shifted.py:30-31`); M5 shifted-line placebo is exchangeable by
  construction and correctly keyed (factor 8316 with slope folded in,
  2772 without).
- **Family sizes** match the plan exactly: F-R 24, F-A 5, F-T 6, F-B 4,
  F-C 4, F-X 6, F-L 4, F-M 12/symbol, F-Xb 5. Descriptive rows carry no q.
- **BH implementation** is a correct step-up (`mk_common.py:717-730`);
  **stability flags are computed**, not hardcoded
  (`mk_m3_analyze.py:136-141` — verified by recomputation on S1_x1, ASIA_x1,
  RND_x1); day-block bootstrap resamples both arms jointly; Hajek weighting
  as declared.
- **Honesty where it matters:** sparse cells are NaN'd and flagged
  (F-A >24h bins, F-FB bins, M4b acceptance criterion); the M4 P-RAND
  non-overlap is disclosed in `BOXES.md:44`; M4b's Arm-OUT selection caveat
  is disclosed (`BOXES_M4B.md:9`).
- **M2/M0/M6 outputs** reproduce their JSONs; `m7_daily_range.json` matches
  the ≤60p claims (GBPUSD 9.2%).

## Headline invalidation statement

- **Invalidated (F1):** every M3 quantity derived from outcome labels —
  S1 +1.48pt / S2 +1.09pt premia, ASIA −1.61pt "continuation" stable flag,
  RND +0.18pt, the +5pt <3h age premium and 0.5h half-life, the touch-ordinal
  decay (+4.5/+0.8/≈0), all retest/role-reversal numbers, all overshoot
  quantiles (hence the `edge_tol` zone-width claim). The published pooled
  D's are weighted averages of a valid side −1 half and a degenerate side +1
  half; the true values are unknown until re-run.
- **Invalidated as inference (F2):** every pooled CI, p and q in M3, M4,
  M4b, M5 — including the M5 +7.16pt/+8.39pt third-touch headline (point
  estimate plausibly survives; significance must be recomputed), the
  significant-stable retest flags, and every "ns" near the boundary
  (the shift can also mask true negatives).
- **Invalidated machinery (F3):** all M4/M4b per-symbol figures and all
  stability verdicts (`no` is structural, not empirical).
- **Stale report (F4):** `MARKET_MECHANICS.md`'s inferential claims do not
  reproduce `out/*.json`.
- **Standing:** M0, M2, M6, all descriptive distributions, the M4/M4b raw
  rates, and the "not identified" verdicts on F-BO/F-FB (under the declared
  placebo).

## The single most likely way this audit is wrong

F1 rests on my reading of `side` semantics. I verified it three ways —
detector assignment (`mk_m3_levels.py:218-222`), M5's mirrored-correct
resolver producing symmetric ~63% rates, and the degenerate 98%/0.02 split
with overshoot p75=0 on side +1 across every set including placebos. If the
declared estimand were instead "any 1·ABR excursion in either direction,"
98% would be correct — but the plan's "reversal ≥x·ABR before continuation
≥x·ABR" requires the outward barriers, and M5 implements exactly that.

## What would change my verdict

1. Fix `mk_m3_levels.py:333-334` to `zlo − x·A` / `zhi + x·A`, re-extract
   M3, re-analyze: if headline signs/magnitudes reproduce, F1 downgrades to
   "fixed-and-verified".
2. Make replicate-level eligibility require `RN_>0 & PN_>0` (or drop emptied
   cells) in `contrast_boot`, re-run all families: if CI/p survive, F2
   downgrades.
3. Fix M4/M4b decode factors (252 / 756), recompute per_sym and stability.
4. Regenerate `MARKET_MECHANICS.md` from current artifacts; wire
   `ledger_row` (or produce the ledger rows cited).

## VERDICT: FAIL
