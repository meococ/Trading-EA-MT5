# R02 — ROUND REPORT (Lead, 2026-09-21T06:10Z)

**Status: CLOSED. Verdict: no claim, no winner.**

| Item | Value |
|---|---|
| Executed seal | FREEZE_v3 `f0462985…` |
| Pre-registration | PREREG `6d6c751c…` |
| Runner | `arrival_outcome_run.py` `97e17afb…` |
| Split | DESIGN 2016–2021 |
| Symbols | EURUSD, GBPUSD, AUDUSD, USDJPY |

The claim-path numbers and gates are in **`CLAIM_VERDICT.md`**. This report adds the descriptive units, the deviations and the limitations.

> Note on `write_reports()`: the sealed runner's own report writer was never called, because the executor stopped at D43. So there is no ledger anchor stamp for this report. That writer would have printed the header "Freeze: FREEZE_v2.json" whatever freeze was executed (cosmetic, in sealed code). This hand-written report replaces it.

---

## 1. Question

Do arrivals at recently-tested zone bands resolve differently from arrivals at long-untested ones?
- The contrast is E3, "recency", measured on two endpoints: bounce and continuation.
- Claim path: the only one pre-declared is **E3 / line1_cluster**.
- **E1** (strength, raw and recency-residualized) was declared **descriptive only** before any outcome (D41a: no generator reached 3 contributing cells).
- **E2** (pairwise generator comparison) was **flagging only**.

## 2. Execution and reproduction

**Freezes**
- v1 `1cd40018…` — **VOID** (D40: post-freeze code edit).
- v2 `5b2f4980…` — **not executable** (D41: claim-path runner defect).
- v3 — **executed**.

**Execution under v3** (Devin executor `20260921013157-0b91ab`)
- Process A ran the claim unit.
- Process B ran the other units. It stopped at 03:38:14Z on unit `e2:fractal_h1|sd_base` (D43).
- Result: **25 unit files** written and fsync'd under `research/arrival/_scratch/r02_outcomes/`, and 38 ledger rows.

**Independent reproduction.** The Lead ran every one of the 25 unit files again in a fresh process, using the sealed runner's own `main()` with only two redirections (ledger → a private copy under the real lock; OUT_DIR → scratch). The output hashes were witnessed out-of-tree before each run.
- Claim unit: **MATCH**, bit-exact (20,048 floats), at 03:22Z.
- d1 (5 E3 + 6 E1R + 6 E1RAW): **MATCH**, bit-exact.
- d2 (7 E2 pairs): **MATCH**, bit-exact (≈20,010–20,016 floats per file). Only `trial_id` fields were excluded.
- Records (claude.ai project): `pa-pro-r02-reexec-witness.md`, `pa-pro-r02-reexec-result.md`, `pa-pro-r02-descriptive-witness.md`, `pa-pro-r02-descriptive-result.md`.

**Coverage**
- E3: 6/6 units. E1R: 6/6. E1RAW: 6/6.
- **E2: 7/15 pairs**; of the 9 design-eligible pairs, 3 were computed (D43).

## 3. Claim path — E3 / line1_cluster (from CLAIM_VERDICT.md)

| endpoint | pooled D (pp) | 95% CI | p (one-sided) | cells with D>0 | verdict |
|---|---|---|---|---|---|
| bounce | +1.04 | [−0.19, +2.16] | 0.048 | 2/4 | **gate NOT passed** |
| continuation | −2.12 | [−4.27, +0.13] | 0.968 | 0/4 | **gate NOT passed** (not ADVERSE: CI upper +0.13) |

- Neither endpoint meets the pre-declared bar (D ≥ +5.0pp, CI lower > 0, ≥ 3/4 cells).
- **R02 carries no claim.** There is no FULLY-CONFIRMED candidate, so **no winner is declared**.
- On the p recipe: `p = (1 + #{D_b ≤ 0}) / (B + 1)`, where "(B+1)" means n_boot + 1 = 10,001. `REVIEW_R02_PREREG_5.md` recorded that reading before any outcome existed: the text's "(B + 1)" equals the code's retained-count n_boot + 1.

## 4. Descriptive units (NOT claims; many cells, no multiplicity control, no inference)

### 4.1 E3, other generators
- **fractal_h1.** Only 1 contributing cell (GBPUSD), so the unit is not eligible.
  - bounce: +2.27 [−1.35, +5.49]
  - continuation: −2.85 [−7.61, +2.49]
- **kde_swing, profile_va, sd_base, ref_levels.** No contributing cells. This is a pre-declared gate fact, not an effect size.

### 4.2 E1 — descriptive only (DECLARE, D41a)

**E1R** (strength top vs bottom tercile after residualizing recency). No unit is eligible; there are at most 2 cells.

| unit | bounce pooled | continuation pooled |
|---|---|---|
| line1_cluster (GBPUSD) | −3.96 [−6.47, −1.56] | −0.01 [−4.31, +4.69] |
| fractal_h1 (AUD, JPY) | −2.34 [−4.47, −0.30] | +0.81 [−2.48, +4.26] |
| sd_base (EUR, GBP) | −2.01 [−5.43, +1.30] | −0.07 [−5.31, +6.34] |
| kde_swing / profile_va / ref_levels | no contributing cells | — |

**E1RAW** (raw strength top vs bottom tercile, per cell; no pooling):
- **Bounce.** Negative in 14 of 15 contributing cells. The CI lies **entirely below 0** in 8/15 (line1_cluster: EUR, GBP, JPY; kde_swing: EUR, JPY; sd_base: EUR, AUD, JPY). No CI lies above 0.
- **Continuation.** No CI excludes 0.
- **Reading (descriptive).** Zones ranked stronger by the strength-v0 score bounce *less*, not more. Strength v0 does not measure what a chart reader means by "strong". The Volman perception spec (Addendum 4) does not use it.

### 4.3 E2 — flagging only

**Label attached to every number:** E2 computed with a cell weight that deviates from the prereg's plain reading (see D42); not the pre-registered E2 analysis; descriptive only, carries no claim. Coverage is partial: 7/15 pairs, 3/9 eligible pairs (D43).

| pair (g\|h) | cells | bounce D (pp) | continuation D (pp) |
|---|---|---|---|
| fractal_h1 \| kde_swing | 4 | −2.41 [−3.68, −1.12] | +0.30 [−1.85, +2.43] |
| fractal_h1 \| profile_va | 4 | −3.14 [−5.01, −1.25] | −1.74 [−4.94, +1.48] |
| line1_cluster \| sd_base | 2 | −4.89 [−8.18, −1.82] | −1.43 [−7.29, +4.22] |
| line1_cluster \| fractal_h1 | 1 (not eligible) | +4.66 [+0.47, +9.05] | +2.62 [−5.35, +9.62] |
| line1_cluster \| ref_levels | 1 (not eligible) | +0.66 [−3.46, +4.58] | +0.06 [−7.25, +5.97] |
| line1_cluster \| kde_swing, line1_cluster \| profile_va | 0 | — | — |
| the other 8 pairs | — | NOT COMPUTED (D43) | — |

## 5. Deviations and limitations

**D40 — post-freeze code edit.** v1 is VOID. The standing rules that followed are the execution gate and role separation (Charter Addendum 3).

**D41 — runner defect in `run_e3` / `run_e1resid`.** The pooled numerator summed over the wrong list, so v2 could not be executed. Fixed in v3 and reviewed (`REVIEW_R02_FIX_D41.md`).

**D42 — E2 cell weight uses `len(ia)`,** not `len(ia)+len(ib)`. It affects E2 only, and the label above is attached to the E2 numbers.

**D43 — stale `base` in the `run_e2` pooled cell list.**
- Only `fractal_h1|sd_base` has a grid that differs across symbols, so only that pair is affected.
- It crashed on key 36182, which was predicted exactly from the frozen bundles.
- The 7 computed E2 pairs are unaffected. The other 8 pairs were not computed.
- Ruling: option (ii), no v4. See `DEVIATION_D43_E2_PAIR_KEYERROR.md`.

**R02-A1 — the forward pass's `_step_all` approximation vs exact replay** (outcome-blind audit, `R02_A1_STEP_ALL_DIVERGENCE.md`).
- On the same grid the event set is unchanged, because arrivals do not depend on zones.
- The approximation leaks only through the zone universe: pass-missed breaks leave "zombie" zones alive.
- For line1_cluster, about 2.0–2.4% of both-treated events flip their E3 arm, and about 3% of E3 labels change. Other generators change by 0–0.7%.
- Label noise of this size attenuates a contrast toward 0. It cannot turn this null into a claim; any claim would need a new round with exact-replay events.

**Cosmetic — the `write_reports()` header** prints "FREEZE_v2" (sealed code; see the note at the top).

**Latent, not triggered — `D_pooled` normalization.** `D_pooled` divides by all cells' weights but sums only the finite D's. No cell in any of the 25 files had a non-finite D.

**Carried into the R03 code base (if a zone-physics round is ever reopened):**
- D42 and D43 fixes, with regression fixtures;
- NaN-safe normalization;
- an execution gate over **every** pre-registered unit path, using fixtures that differ across symbols;
- exact-replay event construction.

## 6. What R02 means for the program

- **FINDING 1:** zone versus empty is not identifiable.
- **FINDING 2:** strength is mostly recency.
- **R02:** recency alone is not a tradable edge at the required scale. Raw strength v0 is, descriptively, anti-aligned with bouncing.
- **Consequence:** zones as currently generated do not carry usable information on their own.
- **Next step:** the program's next move is Charter Addendum 4. Perception is rebuilt on Volman's own chart grammar and validated against the author's drawings (BOOK2012 golden set) before any setup is screened on it.

## 7. Records

`FREEZE_v3.json` · `PREREG.md` · `CLAIM_VERDICT.md` · `DEVIATION_D40…D43` · `REVIEW_R02_PREREG_5.md` · `REVIEW_R02_FIX_D41.md` · `R02_A1_STEP_ALL_DIVERGENCE.md` · `ASK_LEAD.md` (executor v3 report + Lead ruling) · `research/arrival/_scratch/reexec_r02/` (driver, comparator, witnesses, d43_audit) · claude.ai project docs listed in §2.
