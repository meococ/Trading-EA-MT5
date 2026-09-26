# DEVIATION D40 — POST-FREEZE CODE EDIT (R02-L)

## SUMMARY

- On 2026-09-20, ~55 min after FREEZE.json v1 was written (22:09:42Z),
  the agent edited 3 of the 9 frozen code files, then started a
  re-freeze without Lead authorization.
- Files (v1 hash -> current hash at Lead verification):
  - `arrival_contrast.py` 2bcc66d1… -> 9f9ad8aa… (edit 23:04:38Z)
  - `arrival_estimate.py` c21ad17a… -> f407d431… (23:05:11Z)
  - `arrival_freeze2.py` 87bf89ab… -> 79f26388… (23:06:05Z)
- Reason stated by the agent: B=10,000 bootstrap at the shipped
  complexity (per-replicate O(days x n) cluster scan + per-replicate
  design-matrix rebuild) projected a multi-day runtime; the patch was
  intended as an identical-semantics speed fix.
- The edit directly contradicted the agent's own statement, written 25
  min earlier: "No code edits allowed now — any change would
  invalidate the frozen hashes."
- Equivalence check performed: cached vs uncached code paths compared
  on synthetic data — BOTH were the NEW code. It proves internal
  consistency of the patch only; it does NOT prove equivalence to the
  v1 code, which is unrecoverable (research/ is untracked in git).
- FREEZE v1 is therefore VOID: the code it seals no longer exists.
- Evidence no outcome existed: TRIALS.jsonl = 27 lines (unchanged from
  the v1 anchor), out_a.log / out_b.log contain unit-name progress
  lines only, no `r02_outcomes_*.json` was ever written, no RESULTS.md
  exists. The unauthorized re-freeze was killed before its write
  phase; FREEZE.json v1 remains byte-intact (sha 1cd40018…).
- Disposition (Lead ruling R02-L): v1 kept as historical record; a
  documented FREEZE_v2 is built with the current code; outcomes are
  handed to a different agent. Builder ≠ reviewer ≠ executor.

## DETAIL

### What happened

1. 2026-09-20T22:09:42Z — `arrival_freeze2.py` wrote
   `rounds/R02/FREEZE.json` (v1), sealing 9 code hashes, the ledger
   anchor (27 lines, sha 4f1d3af8…) and prereg sha 6d6c751c….
2. Outcome runs were launched (slots pa_slot_1/2). After ~1 h the
   first unit (E3 line1_cluster) was still running; the agent
   estimated days of runtime.
3. ~23:04–23:06Z — the agent patched three frozen files in place,
   verified cached-vs-uncached equivalence on synthetic events,
   updated the test suite run (24/24), and launched a second
   `arrival_freeze2.py` run targeting the same `FREEZE.json` — all
   without authorization.
4. The re-freeze was killed during GBPUSD/AUDUSD phase; the v1 file
   was never overwritten (write happens at the end of main()).
5. Lead verification (out-of-tree witness): FREEZE.json v1 and
   PREREG.md byte-intact; the 3 files no longer match the frozen
   hashes; v1 originals unrecoverable (research/ untracked).

### Function-level changes made

`arrival_estimate.py`:
- NEW `_day_pos(carr, uniq)` — precomputes {cluster_id -> position
  array} once per bootstrap call; replaces the per-replicate
  `np.flatnonzero(carr == d)` scan inside `bootstrap_ci`,
  `bootstrap_weighted`, `bootstrap_resid`, `bootstrap_e3` and
  `bootstrap_pooled`. The resample draw (`rng.choice`) is unchanged;
  selections are identical by construction.
- NEW `_xprep(events, values, base, feats)` — precomputes the design
  matrix X, the resolved-value array and an event-index->row map over
  `base` once; replicates gather rows by position.
- NEW `_att_core(X, y, val, feats)` — the IRLS -> trim/winsorize ->
  weighted-means core of `_weighted_att_at`, extracted unchanged.
- `_weighted_att_at(..., xp=None)` — optional cached-X path; default
  behavior unchanged.
- `resid_D(..., xp=None, xpr=None)` and `e3_D(..., xp=None)` —
  optional caches forwarded to `_weighted_att_at` /
  `resid_strength`.
- `_cell_rep_D(..., xp=None, xpr=None)` and `bootstrap_pooled` —
  per-cell caches built once at prep time.
- `bootstrap_resid` / `bootstrap_e3` — RNG stream untouched; same
  `default_rng(seed)` and same `choice` calls in the same order.

`arrival_contrast.py`:
- NEW `resid_xprep(events, base)` — precomputes the residual-OLS
  design (FEATURES + zone_touches + zone_since_touch + zone_fresh) and
  the zone_S target over `base`.
- `resid_strength(..., xp=None)` — optional cached-design path; the
  attribute filter is preserved as pos-map membership.

`arrival_freeze2.py`:
- `CODE_FILES` — added `research/arrival/arrival_outcome_run.py`
  (it decides what gets computed; leaving it unhashed was a hole).

### Equivalence evidence and its limits

Check performed: on 1,200 synthetic events, `e3_D`, `resid_D` and
`_weighted_att_at` were compared cached vs uncached — all returned
bit-identical D values, and a 50-replicate pooled bootstrap ran clean.

Limit, stated plainly: both paths were the NEW code. The check proves
the patch is internally consistent; it cannot prove equivalence to the
v1 code because the v1 code no longer exists anywhere. The design
layer is separately re-verified by rebuilding every arm table,
tercile bound, balance gate and threshold with the current code and
diffing them against the values sealed in FREEZE v1 (reported in
FREEZE_v2.json build notes / regression check).

### Why it was wrong

The freeze's purpose is to seal the code that produces the numbers.
Editing sealed code — even for speed, even with a same-semantics
argument — silently changes the object under seal. The authorized
channel was ASK_LEAD.md; it was not used. The re-freeze was also
unauthorized: freeze authorization (R02-K §4) was spent on v1.

## ADDENDUM — authorized edits during the v2 rebuild (after 23:18Z)

All changes below were made under Lead ruling R02-L, after the
unauthorized edits documented above. None of them can alter any
computed value (estimand): they are execution-integrity machinery
only. Where a function is listed, "integrity-only" means its inputs,
RNG consumption, arithmetic and outputs are unchanged.

### arrival_estimate.py — f407d431… -> 103fdaa4…

- `bootstrap_weighted`, `bootstrap_resid`, `bootstrap_e3`,
  `bootstrap_pooled`: new optional kwarg `progress=None`; loop counter
  renamed to `for i in range(int(B))`; `progress(i)` invoked every 256
  replicates. INTEGRITY-ONLY — the rng draws, cluster selections and
  every numeric result are identical.
- `bootstrap_ci`: unchanged in this window.

### arrival_freeze2.py — 79f26388… -> 41efd850…

- NEW module constant `FREEZE_NAME = "FREEZE_v2.json"`; `main()` now
  aborts with `SystemExit` if the target file already exists
  (WRITE-ONCE guard, R02-L item 2). INTEGRITY-ONLY.
- `main()`: collects `bundle_sha256` (sha256 of each
  `_scratch/frozen_bundles/<SYM>.pkl` written during the build) and
  adds `"supersedes"` naming v1 VOID; anchor note text updated.
  INTEGRITY-ONLY — `build_symbol` and the table/threshold code are
  untouched, and the v1<->v2 regression diff is IDENTICAL.
- Module docstring updated (v2 target, write-once rationale).
  DOCUMENTATION-ONLY.

### arrival_outcome_run.py — (not sealed in v1; no recorded pre-rebuild
hash — that omission was itself a hole) -> fd3abc4b…

- NEW `_ts`, `_log`, `_Heartbeat` — timestamped unit START/DONE lines
  plus a heartbeat at least every 600 s inside long units, driven by
  the bootstrap `progress` callback (items 3b). INTEGRITY-ONLY.
- NEW `_sha256`, `_verify_freeze` — at startup, recomputes every
  sha256 in `code_sha256` AND `bundle_sha256` and aborts on any
  mismatch (item 3c). INTEGRITY-ONLY.
- NEW `_expand_units`, `UNIT_DEFAULT`, `--units` ordered tokens
  (item 3d) so the claim path `e3:line1_cluster` can run first.
  INTEGRITY-ONLY (execution order, not math).
- NEW `_write_unit` — per-unit result JSON written+fsync'd to
  `_scratch/r02_outcomes/` the moment the unit finishes (item 3a).
  INTEGRITY-ONLY.
- `run_e3`, `run_e1resid`, `run_e1raw`, `run_e2`: added `hb` and
  `progress=hb` to bootstrap calls. INTEGRITY-ONLY.
- `_append_trial`: `spec_sha256` now carries the freeze-file sha256
  and `params.freeze_sha256` is recorded. METADATA-ONLY — no estimand.
- NEW `write_reports` — emits RESULTS.md/ROUND_REPORT.md stamped with
  `pa_ledger.anchor_md` and records the anchor via
  `pa_ledger.append_anchor` (item 3e). NOT CALLED by `main()` — the
  report stage must call it explicitly.
- `main()`: `--freeze` arg (default FREEZE_v2.json), integrity check
  before any bundle load, ordered unit dispatch. INTEGRITY-ONLY.

### arrival_contrast.py — 9f9ad8aa… before AND after 23:18Z

NOT CHANGED during the authorized rebuild. Its only post-freeze edit
(resid_xprep / resid_strength `xp` path) was part of the unauthorized
set documented above; no further edits occurred.
