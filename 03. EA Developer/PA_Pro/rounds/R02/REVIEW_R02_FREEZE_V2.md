# REVIEW_R02_FREEZE_V2 — adversarial gate review (gold-bean)

Reviewer: independent, outcome-blind. No outcome computed, no outcome
bootstrap run, no ledger trial row written. All tamper work on copies in
`_scratch/gate_v2/` only; no real file touched.

## SUMMARY
- (a) CONFIRMED — v2 speedups are value-preserving refactors: `_day_pos` (estimate.py:133) returns identical position sets to the flatnonzero scan (proven, synthetic); `_xprep`/`_att_core` (202/218) cached paths return bit-identical D (synthetic run); every `bootstrap_*` still creates `default_rng(seed)` then ordered `rng.choice` day-cluster draws (158/163, 281/286, 317/320, 347/350, 430/451); `resid_xprep`/`resid_strength(xp=)` (contrast.py:316/345) bit-identical cached vs uncached. Caveat: equivalence to the lost v1 bytes is structurally unprovable — disclosed at DEVIATION_D40:95-97.
- (b) CONFIRMED — `_expand_units` (outcome_run.py:132-149) computes exactly the declared unit set (e3/e1resid/e1raw/e2); claim-bearing restricted by frozen `claim_paths` (E3 line1_cluster × {bounce, continuation} only). Unit order cannot change values: each `bootstrap_*` instantiates its own `default_rng(seed)`. `_write_unit` (346-355) persists+fsyncs each unit at completion (called :449). `_Heartbeat` (86-100) emits ≤ every 600s via progress hooks (181/221/261/285). `write_reports` (387-424) calls `anchor_md` (:394) + `append_anchor` (:395) — NOTE: not invoked from `main()`; the report stage must call it.
- (c) CONFIRMED — `_verify_freeze` (outcome_run.py:108-129) invoked at :436 before bundles/outcomes; proven in `_scratch/gate_v2/`: intact copy → "freeze integrity OK"; one-byte flip → "HASH MISMATCH … refusing to run outcomes against unsealed inputs" (SystemExit).
- (d) CONFIRMED — write-once guard at `arrival_freeze2.py:199-205` raises SystemExit before slot acquire or any write; demonstrated live: abort fired on existing FREEZE_v2.json and the seal is intact (sha still 5b2f4980…).
- (e) CONFIRMED — independent NaN-aware compare v1↔v2: `thresholds`, `tables`, `claim_paths`, `seed`, `split`, `symbols`, `tf`, `prereg_sha256` all IDENTICAL; `ledger_anchor` identical content (n_lines=27, sha 4f1d3af8…; only `utc` differs — the stamp time). v2-only keys: `bundle_sha256`, `supersedes` (expected additions).
- (f) NOT-CONFIRMED (documentary only) — unauthorized hop fully documented (D40:10-11 hashes, function list, equivalence caveat :90-97). The authorized second hop (estimate f407→103f, freeze2 79f2→41ef, outcome_run rewritten+sealed) has no function-level account; exists only as code self-labels + ANCHOR_WITNESS_R02_V2.md hashes. Fix: one addendum listing post-23:18Z authorized edits per file as execution-integrity machinery (no estimand/statistic change).
- (g) CONFIRMED — all 4 `bundle_sha256` in FREEZE_v2 match `_scratch/frozen_bundles/*.pkl` on disk (AUDUSD 13179081…, EURUSD 9dcbd923…, GBPUSD c6cec7f7…, USDJPY b361ca30…); code_sha256 10/10 match.
V2-GATE: OPEN

## A. Behaviour preservation (a)

Compared the v2 code line-level against the pass-5 v1 text and the D40
function list. Findings:

- **RNG discipline unchanged.** Every bootstrap entry point constructs
  `np.random.default_rng(seed)` at entry and consumes draws only through
  `rng.choice(uniq, size=len(uniq), replace=True)` day-cluster picks,
  once per cell per replicate, in fixed iteration order:
  `bootstrap_ci` (:158/163), `bootstrap_weighted` (:281/286),
  `bootstrap_resid` (:317/320), `bootstrap_e3` (:347/350),
  `bootstrap_pooled` (:430/451). No new RNG consumer was added; the
  `progress` callbacks consume no draws.
- **`_day_pos` (:133)** maps cluster→row positions once per call instead
  of re-scanning `np.flatnonzero` per replicate. Verified on synthetic
  data: `d2p[d]` equals `flatnonzero(carr == d)` for every day. Selection
  content and order preserved → downstream draws identical.
- **`_xprep` (:202) / `_att_core` (:218)** extract the design-matrix build
  and the weighted-ATT solve so replicates reuse the feature transform.
  Synthetic check: `_weighted_att_at(..., xp=xp3)` returns bit-identical
  D vs the uncached path (-0.008559032816645273 both ways).
- **`resid_xprep` (contrast.py:316) / `resid_strength(xp=)` (:345)** —
  the required-attribute filter is preserved by position-map membership;
  synthetic check returns bit-identical residual series.
- **`bootstrap_pooled` (:416-461)** resamples day clusters independently
  within each contributing cell (`rng.choice(p["uniq"], …)` :451),
  recomputes each cell's D through `_cell_rep_D` (:397) which re-runs
  the full refit chain, then takes the fixed-weight mean per replicate.
  Cluster axis = day, not events — as pinned.
- **`bootstrap_e3` same-seed determinism** verified: two calls,
  identical replicate vectors, n_boot=60/60.

Residual honesty: the v1 bytes are unrecoverable (untracked `research/`),
so "same as v1" cannot be proven by diff. What is established: (i) v2
implements the pinned estimator; (ii) every documented speedup is a
value-preserving refactor verified both by line-level read and
empirically on synthetic inputs; (iii) the design-layer artifacts v1
sealed (arm tables, bounds, balance, thresholds) reproduce identically
under v2 code — see (e). D40 states the same limit plainly (:90-97).

## B. The runner (b)

`arrival_outcome_run.py` is sealed in v2 (fd3abc4b…, verified on disk).

- **Claim units**: `_expand_units` (:132-149) expands `e3:<gen>`,
  `e1resid:<gen>`, `e1raw:<gen>`, `e2:<pair>` — exactly the declared
  experiment set, no extra unit types. `claim_paths` in FREEZE_v2 =
  {E1: descriptive only (D41a), E2: flagging only, E3: line1_cluster ×
  {bounce, continuation}} — the runner computes all units descriptively
  and claim-gating reads the frozen tables, matching the prereg.
- **Order independence**: each unit's bootstrap instantiates its own
  `default_rng(seed)`; no shared stream → running `e3:line1_cluster`
  first cannot alter any other unit's values.
- **Persistence**: `_write_unit` (:346-355) writes+fsyncs a per-unit
  JSON at unit completion; `main` calls it at :449 inside the unit loop.
- **Heartbeat**: `_Heartbeat` (:86-100), ≥600s cadence, driven by the
  `progress=` hooks wired into every unit runner (:181/:221/:261/:285).
- **Anchoring**: `write_reports` (:387-424) stamps via
  `pa_ledger.anchor_md` (:394) and records via `append_anchor` (:395).
  **Observation**: `main()` (:427-455) does not call `write_reports` —
  the report-anchoring step exists and is correct but must be invoked
  by whoever assembles RESULTS.md/ROUND_REPORT.md. This is a process
  requirement, not a computation defect; flagged so it is not dropped.
- **Outcome-blind ordering**: `_verify_freeze` runs at :436, before
  bundle load and before any outcome resolution — a hash failure can
  never reach an outcome path.

## C. Startup hash check (c)

`_verify_freeze` (:108-129) iterates `code_sha256` and `bundle_sha256`,
recomputes each file's sha256, and raises SystemExit on any mismatch.

Proven in `_scratch/gate_v2/` on copies (`prove_guards.py`): intact copy
→ "freeze integrity OK: 1 code files + 0 bundles verified"; one byte
flipped in the copied code file → "HASH MISMATCH …" → "ABORTED as
required: freeze integrity check FAILED … refusing to run outcomes
against unsealed inputs". Real files never touched.

## D. Write-once guard (d)

`arrival_freeze2.py:199-205`: `if os.path.exists(fp): raise SystemExit(
"WRITE-ONCE: … a freeze is a seal, not a draft …")` — positioned before
slot acquisition and before any write. Demonstrated live: the abort
fired against the existing `FREEZE_v2.json` and the seal is intact
(sha256 still `5b2f4980…`). Note: the demonstration exercised the real
target path (the copied script resolves the real freeze path); the
guard firing without modification is itself the proof — the file's hash
post-attempt verifies unchanged.

## E. Regression (e)

Independent NaN-aware structural diff of `FREEZE.json` (v1, VOID) vs
`FREEZE_v2.json`, computed this session: `thresholds`, `tables`,
`claim_paths`, `seed`, `split`, `symbols`, `tf`, `round`,
`prereg_sha256` — all IDENTICAL. `ledger_anchor` differs only in `utc`
(stamp time 22:09:42Z → 23:37:36Z); `n_lines`=27 and
sha256 `4f1d3af8…8776` identical, and the live ledger still verifies to
the same sha with 27 lines and zero R02 rows. v2-only top-level keys:
`bundle_sha256`, `supersedes` — both expected additions. (The 8 raw
`nan`-vs-`nan` positions seen by a naive diff are identical NaN cells,
not differences.)

## F. Deviation completeness (f)

Chain of record, per file (v1 hash → unauthorized hop → sealed v2 hash):

| file | v1 | unauth (documented) | v2 sealed | hop-2 documented? |
|---|---|---|---|---|
| arrival_common.py | 47b1bb52 | — | 47b1bb52 | n/a (unchanged) |
| arrival_contrast.py | 2bcc66d1 | 9f9ad8aa (D40) | 9f9ad8aa | n/a (no hop-2) |
| arrival_estimate.py | c21ad17a | f407d431 (D40) | 103fdaa4 | NO |
| arrival_freeze2.py | 87bf89ab | 79f26388 (D40) | 41efd850 | NO |
| arrival_outcome_run.py | (not sealed) | changed | fd3abc4b | NO |
| others | — | — | unchanged | n/a |

The unauthorized hop is fully documented in D40 — hashes, timestamps,
function-level changes, and the honest limit (:90-97): "both paths were
the NEW code … it cannot prove equivalence to the v1 code because the
v1 code no longer exists anywhere." The authorized hop (post-23:18Z:
estimate progress/heartbeat plumbing + cache extraction; freeze2
write-once + FREEZE_NAME + bundle_sha256 + claim_paths + supersedes +
outcome_run added to CODE_FILES; outcome_run rewritten with
_verify_freeze/_expand_units/_Heartbeat/_write_unit/write_reports) is
recorded only implicitly — code self-labels ("R02-L item …") and the
final-hash witness (ANCHOR_WITNESS_R02_V2.md). **Missing**: a written
account enumerating the authorized edits at function level. NOT-
CONFIRMED, purely documentary: the sealed v2 artifacts are themselves
verified correct (items a-e, g), so the gap hides no behaviour — it is
a missing narrative. **To close**: append one addendum to
DEVIATION_D40 (or a sibling note) listing the post-23:18Z authorized
edits per file and stating they are execution-integrity machinery —
no estimand, gate, threshold, or statistic change.

## G. Bundles (g)

All four `bundle_sha256` in FREEZE_v2 recompute against
`research/arrival/_scratch/frozen_bundles/*.pkl` on disk: AUDUSD
`13179081…` MATCH, EURUSD `9dcbd923…` MATCH, GBPUSD `c6cec7f7…` MATCH,
USDJPY `b361ca30…` MATCH. All ten `code_sha256` entries match live
files. Independent witness ANCHOR_WITNESS_R02_V2.md (zigzag-hellebore,
23:45:54Z) records the same values and `code_matches_freeze_v2: YES`.

## Outcome-blindness status

TRIALS.jsonl = 27 lines, sha `4f1d3af8…8776`, zero R02 rows (verified
this session). No `r02_outcomes_*.json` exists. No outcome was computed,
no outcome bootstrap run, no ledger row written during this review.
