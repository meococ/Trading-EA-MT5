FAIL

# REVIEW_3 — independent re-review of DR-MARKET v2 (post-REVIEW_2 remediation)

Reviewer: REVIEW_3 (independent of REVIEW_2). Date of review: post-r2 artifacts
(`out/*` 23:18–23:21, reports 23:18–23:23, ledger rows T000392–T000396).
Scope: governance + correctness audit of the corrected market-mechanics lane;
descriptive science on DESIGN data only. No new findings were searched for and
no trading claims were evaluated.

## Why FAIL when everything in the lane is clean

Every REVIEW_2 finding is verifiably closed, the known-answer suite is 22/22
green on a fresh run, all 12 corrected event-table hashes recompute to the
ledger values, and a fresh look-ahead scan found no new causal defect. The
science is, as far as this audit can determine, correct and honest.

The single blocker is **N1**: the shared append-only ledger
(`ledger/TRIALS.jsonl`) fails its own integrity check —
`pa_ledger.verify()` returns `(False, 365)`. The break sits at the
`T000366` (perception lane, foreign writer) → `T000365` edge and is provably a
serialization-basis mismatch, not content tampering — but the chain **cannot be
healed by any byte-level repair** (see N1 for the proof), so the file as shipped
will fail verification for any governed tester who runs `verify()`. Certifying
the v2 headlines as FINAL over an evidence store that fails its own verifier is
exactly the kind of finding this review exists to catch. The fix is a Lead
ruling, not lane code — options and exact remediation are in "Required fixes".

Everything else in this report documents what was verified, so that once N1 is
ruled on, clearance is mechanical.

---

## 1. Method

Read in the prescribed order: `MANDATE.md` → `LEAD_RULINGS.md` → `REVIEW_2.md`
→ `DEVIATIONS.md` (D25–D32) → `STUDY_PLAN.md` → `STUDY_PLAN_ADDENDUM_M4B.md` →
`tests/` → all `mk_*.py` + `lib/pa_ledger.py` → `out/*.json` + `out/*.npz` →
reports → `ledger/TRIALS.jsonl` → `MARKET_LOG.md`. All "verified" claims below
were re-derived from current bytes, not trusted from the log.

## 2. Known-answer suite — fresh run

```
cd research/market/tests && python run_tests.py
```

Fresh output (this review, not the log's claim):

```
  PASS test_resolver.test_freeze_at_resolution
  PASS test_resolver.test_no_resolution_none
  PASS test_resolver.test_overshoot_support
  PASS test_resolver.test_resistance_bounce
  PASS test_resolver.test_resistance_break
  PASS test_resolver.test_side_symmetry_rates
  PASS test_resolver.test_support_bounce
  PASS test_resolver.test_support_break
  PASS test_contrast_boot.test_planted_effect_recovered
  PASS test_contrast_boot.test_planted_null_stays_null
  PASS test_contrast_boot.test_point_always_inside_ci_dense
  PASS test_contrast_boot.test_sparse_strata_nan_coherent
  PASS test_contrast_boot.test_thin_placebo_no_bias
  PASS test_lookahead.test_detect_touches_features_causal
  PASS test_lookahead.test_grid_envelope_ignores_future_abr
  PASS test_lookahead.test_placebo_grid_levels_ignores_future_abr
  PASS test_decode.test_m3_decode_roundtrip
  PASS test_decode.test_m4_decode_roundtrip
  PASS test_decode.test_m4b_decode_roundtrip
  PASS test_decode.test_m5_decode_roundtrip
  PASS test_decode.test_no_key_overflow_ambiguity
  PASS test_decode.test_old_factors_collapse_to_eurusd

22/22 tests pass
```

**22/22 PASS** — matches the 16:23Z log claim; the r2 gate was real.

## 3. REVIEW_2 finding closure

| # | finding | status | evidence |
|---|---------|--------|----------|
| F1 | side=+1 barriers inside-out → all outcome labels corrupt | **CLOSED** | `mk_m3_levels.py:329-336` mirrored outward barriers (`brk=zhi+xA`/`bnc=zlo−xA` for −1; `brk=zlo−xA`/`bnc=zhi+xA` for +1); `:351-362` side-mirrored hit scans; `:324-327` outcome path starts after the touch minute (no pre-touch contamination). `test_resolver` 8/8 incl. `test_side_symmetry_rates`. **Data-level fingerprint**: recomputed per-side P(bounce,x1) on current npz — S1 res 0.644/sup 0.638, S2 0.639/0.630, PRAND 0.641/0.647 (EURUSD); symmetric ~0.62–0.65 on all 4 symbols — the pre-fix degenerate split is gone. |
| F2 | `contrast_boot` zero-fills empty-arm replicates | **CLOSED** | `mk_common.py:522-585`: pooled eligibility `elig=(RN.sum(0)>=5)&(PN.sum(0)>=5)` computed once (`:548`); per-replicate `present=(RN_>0)&(PN_>0)`, `valid=elig&present` (`:561`); invalid cells zero-weighted; NaN only when no valid denominator. `test_contrast_boot` 5/5 incl. `test_sparse_strata_nan_coherent` and the planted-effect/null recovery tests. Shipped-data scan: no formal row has finite D paired with NaN CI, no D outside its CI. |
| F3 | M4/M4b key decode collapses symbols → EURUSD | **CLOSED** | `mk_m4_analyze.py:85-91` encodes sym into `key` (factor 252/756 per the corrected scheme); `test_decode` 6/6 incl. `test_m4_decode_roundtrip`, `test_m4b_decode_roundtrip`, `test_old_factors_collapse_to_eurusd` (locks the old bug as a regression test). Current `m4_results.json`/`m4b_results.json` have populated `per_sym` for all 4 symbols; M4b race24 `stable=true` requires ≥3/4 symbols decoded — computationally impossible under the old collapse. |
| F4 | `MARKET_MECHANICS.md` contradicts shipped JSONs | **CLOSED** | Regenerated at 23:21 (post-r2). Spot-checks against current JSONs: S1_x1 D=+2.4499pt (report "+2.45pt") q=0.0015 stable; PDHPDL_x1 D=−3.2023pt q=0.0024 not-stable; ASIA_x1 D=−1.4292pt q=0.0514 stable; M4b race24 D=+1.1434pt p=0.0030 q=0.0075 stable — all match. |
| F5 | grid envelopes used full-day `nanmedian(abr)` (lookahead) | **CLOSED** | `mk_m3_levels.py:154` `A=float(abr[i0])` — day-open causal ABR; `mk_common.py` `placebo_grid_levels`/`grid_columns` take the same causal scalar. `test_lookahead` 3/3: mutating future bars leaves `grid_columns`, `placebo_grid_levels`, and `detect_touches` output bit-identical; the pre-fix full-day-median version is shown to change under the same mutation. |
| F6 | ledger rows not implemented | **CLOSED (lane-side)** | `mk_ledger.py` wired: `emit()` (`:66`) with `_already(family,run_tag)` idempotency (`:57-64`), `supersedes` list, per-symbol `data_sha256`. Rows T000393–396 exist, one per family, `run_tag="r2"`, `supersedes` covering T000380–387+T000391. **All 12 event-table hashes recompute exactly** (M3: c42c0596/a31149bc/7de5c2a6/aadea7fe; M4: 1885de89/081ebf2e/82cd9dee/052c947d; M4b: 81422d8b/fda2fdea/8af7f999/227742a8; M5: 2d2c8c96/d1536b18/671f9497/f6ef271b — AUDUSD/EURUSD/GBPUSD/USDJPY). Caveat: see N1 (global chain) and N2 (empty key_metrics on two rows). |
| F7 | M4 placebo pokes not streak-merged | **CLOSED** | `mk_m4_boxes.py:23` docstring + `:127` `poke_streak` state + `:162-187` merge: consecutive same-direction pokes merge into one event with `depth=max`, `end` updated; end-relative freshness. D30 documented. |
| F8 | dead-code landmines w/ different mis-anchoring | **CLOSED** | `mk_common.resolve_touch_outcome` (`:326-352`) now uses outward barriers on both sides (`up=zhi+xA`/`dn=zlo−xA`) — the mis-anchored variant is gone. `first_touch_events`, `block_boot_diff`, `match_strata` remain dead code but no longer carry divergent barrier math. REVIEW_2's "delete or fix" → fixed. Residual hazard → N3. |
| F9 | cosmetic/provenance minors | **CLOSED (5/6), 1 residual** | (a) `mk_m4b_shifted.py:2-3` now cites T000392/`4abca652` correctly — fixed; **but** `mk_m4b_analyze.py:2` still cites "prereg T000390" (superseded) → N5. (b) M5 freshness `(t−last_hit)>24` at `mk_m5_lines.py:153` is **correct**, not off-by-one: "no touch in prior 24 bars" = bars t−24..t−1 clean ⟺ last_hit ≤ t−25 ⟺ t−last_hit > 24. Verified. (c) `placebo_lines` RNG now per-symbol (`mk_m5_lines.py:150` `default_rng(seed)` with seed=crc32(sym) at caller). (d) F-B pool = `["S1","S2","PDHPDL","ASIA"]` (`mk_m3_analyze.py:382`) — matches F-T scope, RND excluded per plan. (e) M2 Asia `cet<=480 & cet>0` (`mk_m2_rhythm.py:66`) now matches M3 `(0,480]` — comment says "Asia convention as M3". (f) birth-truncated freshness — declared/defensible, unchanged, noted as interpretation caveat. F-M per-symbol-12 — acceptable reading, noted. |

## 4. New look-ahead / defect scan

Fresh grep+read pass over all `mk_*.py` for forward-looking statistics
(`nanmedian`, `percentile`, `max/min` over windows, `shift`, `iloc[-k:]`):
**no new causal defect found.** Everything whole-window is one of:
trailing windows (`mk_m4_boxes.py:122` rolling-30), completed-window
descriptives (M2 Asia `nanmedian(abr[m])` over the *completed* 00–08 CET window
— descriptive context, not decision input), analysis-time strata quantiles
applied symmetrically to both arms (`mk_m3_analyze.py:82-83`,
`mk_m4_analyze.py:69-73`, `mk_m5_analyze.py:56-57`), or explicitly post-event
forward windows (allowed). M5 line birth/death (`mk_m5_lines.py:141-157`)
bounds touches to `[birth,death)`, freshness counts every zone hit, placebos
die under identical machinery — causal and exchangeable.

Checked specifically: side+1 overshoot/retest/role-reversal coherence (mirrored
correctly, `:364-384`); both-arm mask does not eliminate legitimate cells
(`valid` only drops cells already ineligible or resample-emptied); day-open
ABR causal (`abr[i0]`); decode on symbol-free keys (`test_no_key_overflow_ambiguity`);
P-RAND streak freshness no double-count (merge before event emission);
finite-D/zero-valid-replicate scan clean.

## 5. Governance / output integrity

- **DESIGN-only**: all loads via `pa_data.load_m1(sym, split="DESIGN")`
  (`mk_common.py:69`, `mk_m0_clock.py:70`); no `pa_fill`/`pa_eval`/`pa_random`
  imports; no trading metrics anywhere.
- **Prereg ordering**: T000392 (addendum prereg, sha `4abca652` — recomputed
  = on-disk `STUDY_PLAN_ADDENDUM_M4B.md` hash) precedes compute row T000395.
  T000392 correctly supersedes T000390 (`9c1972ac`, same design re-registered
  after caveat edits — disclosed in `mk_m4b_shifted.py:2-3`).
- **Stability rule**: programmatic recompute of `stable` over all rows —
  same sign ≥4/6 years AND ≥3/4 symbols — **zero mismatches**.
- **Stale marking**: `MARKET_LOG.md:86-92` records the 15:36Z halt and marks
  partial M3/M4 outputs STALE; `:110` records the gated r2 re-run after the
  suite passed. Honest.
- **Family sizes** match the plan: F-R 24, F-A 5, F-T 6, F-B 4, F-C 4, F-X 6,
  F-L 4, F-M 12/symbol, F-Xb 5.

## 6. New findings

### N1 — shared ledger fails its own verifier — **BLOCKER (governance)**

`pa_ledger.verify('ledger/TRIALS.jsonl')` → `(False, 365)`.

Mechanism (fully reverse-engineered, benign): lines 364, 365 (T000365, T000366 —
perception-lane `perception_golden` rows, ~10:23–10:26Z) are the **only** lines
written by a foreign writer: spaced JSON separators (`"k": v`) + CRLF
terminators, vs `pa_ledger.append`'s compact separators + LF
(`pa_ledger.py:218,222`). The foreign writer computed `prev_line_sha256` as
`sha256(json.dumps(prev_obj, sort_keys=True))` — the spaced reserialization,
byte-identical to raw-minus-`\r` — while `verify()` hashes raw bytes *including*
the `\r` (`:249,262`). Proven: stored prev `46a823b5…` ==
sha256(line364.rstrip(`\r`)) == sha256(spaced reser), ≠ sha256(raw incl `\r`)
= `c5abe29d…`. The forward edge T000366→T000367 verifies because `pa_ledger`
hashed T000366's committed bytes — so **the DR-MARKET suffix chain
T000367→T000396 is intact** and no content tampering is evidenced (adding a lone
`\r` post-hoc changes nothing semantic and no plausible motive exists).

Why it still blocks: (a) the shipped artifact fails its own integrity check —
any governed tester running `verify()` sees `False`; (b) the break is
**structurally unhealable**: stripping `\r` from line 364 heals edge 364→365
but line 365 also has `\r`, and T000367's stored prev was hashed over raw-bytes-
incl-`\r`, so stripping 365 breaks edge 365→366 — no byte edit fixes the file
without cascading history rewrites; (c) remediation is outside the lane's code
scope (`lib/` + foreign rows). This is a Lead-ruling item, not a lane defect —
see "Required fixes".

### N2 — `mk_ledger` headline extractors mismatch the result schemas — **minor**

`_fx` reads `families["F-X"]` but M4 stores `F-BO`/`F-BX`/`F-FB`; `_fl` reads
`families["F-L"]` but M5 stores `F-TL`/`F-SLOPE` (`mk_ledger.py:99-117` vs the
JSON keys). Result: **T000394 and T000396 carry empty `key_metrics`**
(`{run_tag, supersedes}` only) — the declared "headline metrics in every row"
is half-met (T000393's `_fr`→`F-R` and T000395's `_fxb`→`F-Xb` work). Rows
exist, hashes verify, idempotency holds — provenance completeness gap only.

### N3 — dead legacy machinery still present — **minor (latent)**

`mk_common.py:209` `first_touch_events` (non-birth-bounded freshness), `:326`
`resolve_touch_outcome` (barriers now fixed but still the old non-mirrored-tie
code path), `:618` `block_boot_diff` (still carries the F2-era per-replicate
≥5 eligibility), `mk_m3_levels.contrast` (old eligibility), `block_boot_stat`,
`level_arrays_from_daily`, `placebo_grid_levels` (test-only). No production
callers — verified. If any is ever imported, the exact bug classes this
remediation just killed return silently. F8 said "delete or fix" — barriers
were fixed; the recommendation stands: delete.

### N4 — `stable=YES` rendered on non-inferential rows — **minor (presentation)**

Descriptive rows (M3 age/touch/cascade-desc, M4b fwd-desc, M5 real-vs-placebo
desc, M5 all-touch) display `stable=YES` computed by the sign rule while
carrying `q=None`/no CI — e.g. `LINES.md` rising_vs_rest_up (q=0.103, ns,
stable YES), `LEVELS.md` `RNDvsPRND20_h48_desc` inside the formal F-C table.
The flag is computed per its declared definition (sign counts) so technically
correct, and `MARKET_MECHANICS.md` words the claims correctly — but on rows
with no significance the YES can be read as an inferential endorsement. All
genuinely formal rows are clean; this is a labeling ambiguity, not an error.

### N5 — stale provenance citations — **minor (cosmetic)**

`mk_m4b_analyze.py:2` docstring cites "prereg T000390" (the superseded hash)
while the extractor and `BOXES_M4B.md` correctly cite T000392. Also
`T000395.key_metrics` contains bare `NaN` literals (json `allow_nan` default)
— non-strict JSON, readable by Python, rejected by strict parsers.

### N6 — interpretation caveats to keep on the record — **informational**

(a) `detect_crosses` freshness counts the column's trailing-288 touches across
day boundaries and level instances — stricter than "that grid price untouched"
near day-start; symmetric across real/placebo, internally valid. (b) Real
M4 pokes use streak-merge freshness while the placebo arm uses the declared
FRESH-gap rule — per-spec asymmetry, already disclosed as part of the
not-identified arm. (c) Birth-truncated freshness admits formation-adjacent
first touches (REVIEW_2's declared/defensible note) — unchanged.

## 7. Required fixes (to flip FAIL → PASS)

Exactly one item blocks; N2–N5 are worth fixing in the same pass but are
individually non-blocking.

1. **N1 — Lead ruling on the ledger break (REQUIRED).** Either:
   (a) amend `pa_ledger.verify()` to accept the dual basis on the inbound edge —
   `stored_prev ∈ {sha256(raw_prev), sha256(raw_prev.rstrip(b"\r"))}` — while
   continuing to propagate `prev_hash=sha256(raw)` for the outbound edge
   (preserves tamper-evidence on every pa_ledger-written line; one-line change
   to the check at `pa_ledger.py:260`); **or**
   (b) record a Lead deviation stating: chain break at index 365 is a known
   foreign-writer serialization-basis defect (perception lane, 10:23–10:26Z),
   mechanism proven benign, suffix chain T000366→EOF verified, lane rows
   T000367–396 unaffected. Do **not** byte-edit the file — impossible without
   cascade (proof in N1).
   After (a) or (b): re-run `verify()`, confirm `(True, None)` or document the
   accepted break-point, and this review converts to PASS on the evidence
   already gathered.

2. N2 (recommended): fix `_fx`→`F-BO`/`F-BX`/`F-FB` and `_fl`→`F-TL`/`F-SLOPE`
   key reads (or emit union keys) so T000394/T000396 carry headline metrics;
   re-emit those two rows idempotently (same `(family,run_tag)` → `_already`
   skips — bump run_tag or allow field-merge if the row must be amended).

3. N3 (recommended): delete the dead functions listed in N3.

4. N4 (recommended): render `stable` only on rows with a formal q/CI, or add a
   "descriptive — no inference" marker column in the section headers.

5. N5 (recommended): correct the `mk_m4b_analyze.py:2` citation to T000392;
   write key_metrics with strict JSON (`allow_nan=False` → null).

## 8. What would change my verdict

- **To PASS**: a Lead ruling per §7.1 (either branch), with `verify()` re-run
  and the outcome logged in `MARKET_LOG.md`. Nothing else needs re-computation —
  all science evidence in this report stands.
- **To deeper FAIL**: any evidence that lines 364–365's CRLF bytes post-date
  T000366's write (e.g., a snapshot showing LF at those lines before 10:26Z)
  would convert N1 from benign-basis-mismatch to suspected post-hoc byte
  modification — at which point the whole ledger's evidentiary value, not just
  one edge, is impeached. Current evidence weighs strongly against this (both
  foreign lines share the spaced+CRLF signature; the stored prev matches the
  writer's own canonical basis).

## 9. The single most likely way this audit is wrong

That N1 is over-weighted: the Lead may rule that `verify()`'s raw-byte basis is
the platform contract and the foreign writer is the defect to be fixed at
source — in which case the correct action is identical (fix the writer or
tolerate the basis), but the *blame* sits on the perception lane, not
DR-MARKET, and this FAIL would read as the lane being held hostage to a
shared-infra bug. I accept that framing risk: the binary verdict reflects the
artifact's verifiability, and the artifact as shipped does not verify.

## 10. Closure statement

REVIEW_2's science defects are genuinely fixed — F1 through F9 all closed with
data-level and test-level evidence, the suite is green on a fresh run, hashes
and prereg ordering are clean, and no new causal defect exists. **The v2
market-mechanics headlines are NOT cleared for FINAL** pending exactly one
governance ruling (N1) on the shared ledger's failed verification. Once the
Lead rules, a re-check of `pa_ledger.verify()` plus this report's evidence is
sufficient to clear — no science re-computation is needed.

— REVIEW_3
