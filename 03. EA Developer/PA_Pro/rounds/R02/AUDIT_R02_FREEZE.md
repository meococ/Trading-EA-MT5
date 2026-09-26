# AUDIT_R02_FREEZE — independent freeze audit (fresh agent, outcome-blind)

Auditor: independent agent, no prior context. Scope: FREEZE ONLY. No outcome
file was opened, imported, or run; ledger rows were inspected structurally
(kind/round/utc/key-metrics-presence only), never by value. No effect size
was seen. All tamper work happened on copies in `_scratch/audit_r02/`.

## SUMMARY
- A: VERIFIED — 13 top-level keys, no outcome/effect/D/p/CI/verdict field anywhere (full nested key scan)
- B: VERIFIED — recomputed anchor: n_lines=27, sha256 `4f1d3af88f2f833fc6f2cc49b1c6bd479d208abcd1ad1aa03fbd099d383a8776`, matches FREEZE.json
- C: VERIFIED — recomputed PREREG sha256 `6d6c751cfab873fcb70a1389c92fc870bf999669f3d617030889a93b1a632581`, matches `prereg_sha256`
- D: VERIFIED — all 9 `code_sha256` entries recompute identically; `_scratch` excluded by whitelist bundle + `_is_scratch`, test-locked
- E: VERIFIED — REVIEW_R02_PREREG_5.md 22:01:51Z < FREEZE.json 22:09:42Z; ledger holds zero R02 rows (27 rows, all R00/R01, latest 15:37:09Z)
- F: VERIFIED (one gap) — anchor in FREEZE.json + ANCHORS.jsonl + R02-F report; `.tail` loss/truncation fails closed; `data_sha256` covers all named fields. Gap: arrival outcome/report writer has no `anchor_md`/`append_anchor` call yet
- TAMPER ATTEMPTS: 7 attempted, 6 caught (1 succeeds only with write access to every in-tree artifact — documented residual)
- FREEZE TRUSTWORTHY: QUALIFIED(all in-tree artifacts are mutually writable — real detection needs an off-tree anchor copy; the R02 round-report writer is not yet anchor-wired)

## A. FREEZE.json contents

`rounds/R02/FREEZE.json` (2003 lines). Top-level keys (enumerated):
`claim_paths, code_sha256, ledger_anchor, phase, prereg_sha256, round, seed,
split, symbols, tables, tf, thresholds, utc`.

Recursive key scan over the whole document: the only non-design names are
preregistration criteria (`claim_d_pp`, `bh_q`, `tie_margin_pp`, `p_recipe`
[the formula text], `boot_B`, `boot_seed`, `smd_gate`, `recency_gate`,
thresholds/features lists) and design-stage statistics inside `tables`
(`n_events`, `n_treated`, `n_a/n_b/n_x`, `smd_post`, `gate_pass`, `recency`,
`e1/e3 bounds`, `resid r2`, `u_atr`). `claim_paths` carries endpoint
declarations ("E3: line1_cluster x {bounce, continuation}"), not results.
No key holds an effect estimate, D statistic, p-value, confidence interval,
or verdict. The file also parses with one anomaly worth noting: several
`smd_post` values are literal `NaN` (Python-style JSON) — cosmetic, not an
outcome leak.

## B. Ledger anchor (recomputed)

- Ledger: `ledger/TRIALS.jsonl`, 27 lines (wc -l = 27).
- Recomputed `sha256` over the raw bytes of the first 27 lines (each + `\n`):
  `4f1d3af88f2f833fc6f2cc49b1c6bd479d208abcd1ad1aa03fbd099d383a8776`
- FREEZE.json `ledger_anchor` = `{n_lines: 27, sha256: 4f1d3af8…8776,
  utc: 2026-09-20T22:09:42Z}` — exact match. `pa_ledger.check_anchor()` on
  the embedded record: `(True, None)`.

## C. Prereg hash (recomputed)

- `sha256(rounds/R02/PREREG.md)` computed now:
  `6d6c751cfab873fcb70a1389c92fc870bf999669f3d617030889a93b1a632581`
- FREEZE.json `prereg_sha256`: identical. PREREG.md was NOT edited after
  freezing (as far as the hash can show — the frozen hash covers current
  bytes; a pre-freeze edit is by definition invisible).

## D. Code bundle

All 9 entries in `code_sha256` recomputed over current files — all match
(arrival_common, arrival_contrast, arrival_estimate, arrival_feas2,
arrival_freeze2, arrival_outcome, test_arrival, phys_common, phys_resolve).

`_scratch` exclusion, two independent mechanisms:
- FREEZE bundle is an explicit whitelist `CODE_FILES`
  (`research/arrival/arrival_freeze2.py:45-55`) — scratch paths cannot enter.
- The ledger-line `code_sha256` bundle (`lib/pa_ledger.py:446-460`) hashes
  `lib/*.py` skipping `_is_scratch` (`:441-443`: name starts `_`, except
  `__init__.py`).
- Regression tests: `tests/test_referee_hardening_r02c.py::
  test_scratch_never_changes_the_lib_bundle` (line 150) and
  `research/physics/tests/test_report_anchor.py::
  test_scratch_never_changes_a_bundle_hash` (line 66). Both pass.
- Demonstrated live: dropping `_evil_probe.py` beside lib code leaves the
  bundle hash unchanged; `evil.py` (no underscore) changes it — correct.

## E. Ordering

| artifact | mtime (UTC) |
|---|---|
| REVIEW_R02_PREREG_5.md | 2026-09-20 22:01:51 |
| FREEZE.json | 2026-09-20 22:09:42 |
| PREREG.md | 2026-09-20 21:48:46 |

Review is ~8 min OLDER than the freeze. FREEZE.json's own `utc` field
(22:09:42Z) equals its mtime and the third ANCHORS.jsonl record's utc —
self-consistent.

Ledger rows (structural inspection only): 27 rows, `round` ∈ {R00×21,
R01×6}, all `kind=eval`, latest `utc` 15:37:09Z. Zero R02 rows exist, so no
R02 trial row carrying an outcome can predate the freeze. The pre-freeze
rows legitimately carry `key_metrics` for already-completed rounds R00/R01.

## F. Hardening claims deployed

1. **Anchor deployed.** `ledger_anchor` in FREEZE.json; `ANCHORS.jsonl`
   holds 3 records — retro-anchor 19:40:59Z, R02-F report anchor 19:43:53Z,
   and "R02 freeze (conditional R02-K)" 22:09:42Z (written by
   `arrival_freeze2.py:211` `pa_ledger.append_anchor()`); the R02-F round
   report `REFEREE_HARDENING_2.md:69` carries the anchor line.
   `verify_against_anchors()` on the real ledger: `(True, None)`;
   `test_real_repo_ledger_is_anchored` passes.
   **Gap:** the R02 arrival outcome/report writer
   (`research/arrival/arrival_outcome_run.py`, `arrival_outcome.py`)
   contains no `anchor_md`/`append_anchor` call — grep returns nothing. The
   freeze writer is wired; the future round-report writer is not (flagged
   as an open deviation in REFEREE_HARDENING_2.md §6 itself). No R02 round
   report exists yet, so nothing is currently unprotected, but if the
   report ships through this writer unchanged it will lack the anchor.
2. **`.tail` fail-closed.** `pa_ledger.verify()` `lib/pa_ledger.py:263-273`:
   missing `.tail` on a non-empty ledger → `(False, len-1)`, never
   bootstrapped; a present-but-truncated `.tail` fails the equality check
   → `(False, len-1)`. Demonstrated in attacks 3a/3b. Test:
   `test_missing_sidecar_refused_and_not_recreated` (r02c.py:62).
3. **`data_sha256` coverage.** `lib/pa_eval.py` `_DATA_SHA_FIELDS` (~line
   76): 30 entries covering `pip, starts, m5{o,h,l,c}, m5_t, next_end,
   sess_mask, first_live_idx, c_rt_pips` plus m1/bars arrays — every field
   named in the audit is present. `_provider_data_sha256` (`:418`) computes
   from actual objects; caller-supplied `data_sha256` is ignored
   (`:41`,`:423`). `test_data_sha256_covers_every_listed_field`,
   `test_frozen_field_list_contains_the_red_team_fields`,
   `test_provider_cannot_assert_data_sha256` all pass.

## G. Tamper attempts (all on `_scratch/audit_r02/` copies)

| # | attack | result |
|---|---|---|
| 1 | Flip one byte inside covered ledger line 5 | CAUGHT — `verify` (False,5); anchors + FREEZE embedded anchor mismatch |
| 2 | Append forged anchor (`sha256:"0"*64`, n=27) to ANCHORS copy | CAUGHT — reported as violated anchor at index 3 |
| 3a | Delete `.tail` | CAUGHT — `verify` (False,26), not bootstrapped |
| 3b | Truncate `.tail` hex to 32 chars | CAUGHT — `verify` (False,26) |
| 4 | Truncate ledger to 20 lines + rewrite `.tail` honestly | CAUGHT by anchor layer — `verify` passes on the truncated file (self-consistent chain), but anchors and FREEZE anchor report "holds 20, covers 27" |
| 5 | Full rewrite: tamper line 5, rechain all `prev_line_sha256`, rewrite `.tail` AND `ANCHORS.jsonl` | NOT caught in-tree — `verify`+`verify_against_anchors` pass; ONLY the FREEZE.json embedded anchor still mismatches. If FREEZE.json is also rewritten, nothing in-tree detects it (nothing commits FREEZE.json's own bytes). Documented residual A1/A4 — write access wins; defence = anchor copies outside the tree + independent re-execution |
| 6 | Append a byte to a copy of PREREG.md | CAUGHT — sha `fa8392…` ≠ frozen `6d6c75…` |
| 7 | Drop `_evil_probe.py` next to lib code | CAUGHT — bundle hash unchanged (excluded); control file `evil.py` correctly changes the hash |

## Notes / limits

- FREEZE.json's own integrity is self-referential: it commits prereg, code
  and ledger, but nothing commits to FREEZE.json itself. A full in-tree
  rewrite (attack 5 extended) is undetectable from disk alone. This is
  stated plainly in `pa_ledger.py:27-48` and REFEREE_HARDENING_2.md §6 —
  disclosed, not hidden.
- `tables` contains design-balance statistics (SMDs, arm counts, gate
  flags). These are the legitimate frozen design state, not outcomes.
- No file in `rounds/R02/` post-dates FREEZE.json except this report and
  the scratch dir. Files named `*outcome*`/`RESULTS*` were not opened;
  `arrival_outcome_run.py`/`arrival_outcome.py` were grepped for identifier
  names only (no values seen).
