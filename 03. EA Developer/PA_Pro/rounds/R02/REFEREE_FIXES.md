# R02 REFEREE_FIXES — R02-A (Lead order 2026-09-20)

Every defect from `rounds/R01/REVIEW_R01_PREFLIGHT.md` / `REVIEW_R01_PHYSICS.md` that was assigned
to R02-A, with the regression test that locks it. Frozen R01 artifacts were not touched (only
`rounds/R01/FREEZE_ADDENDUM.md` was appended, the authorized exception for F3). No physics or
economic evaluation was run.

| ID | file:line (before) | what was wrong | what changed | regression test |
|---|---|---|---|---|
| F2 | `lib/pa_eval.py:86` + `lib/pa_metrics.py:49-51` | Two working bypasses: (a) `_enter_eval()` + `_mint_token()` were module attributes, so anyone could mint a valid token and get metrics with no ledger line; (b) public `register_token_checker` let a caller install a permissive checker (`lambda o: True`). | The token class, a per-session `secrets.token_hex(16)` nonce, the mint and the checker now live inside the closure that defines `evaluate`; a token is bound to the split and cleared in a `finally` (single evaluation session); `pa_metrics.register_token_checker` is removed from the public surface and the private one-shot handshake refuses re-registration; the historical `_enter_eval`/`_mint_token`/`_leave_eval` names are raising decoys. `evaluate` is still the only ledger-appending path. | `tests/test_eval_gate_bypass.py::test_bypass_a_enter_mint_is_dead`, `::test_bypass_b_register_checker_is_dead`, `::test_honest_path_works_and_appends_exactly_one_line` (all fail against the pre-fix code: the old names returned without raising and `register_token_checker` existed) |
| F3 | `struct/zones/refs.py:59-67` | `pdh/pdl/pdc` were written only on the first bar of each server day; `levels_at`/`confluence`/`ref_inside` saw daily levels on 1,577/445,858 EURUSD DESIGN bars (0.35%) instead of ~99.9%. | Previous-day H/L/C carry forward for the whole day exactly like `wk_*`/`asia_*`; recorded in `rounds/R01/FREEZE_ADDENDUM.md` (old `2e3387a5…` -> new `c79c89fa…`; zones bundle `3676262d…` -> `e480d451…`) per the new policy. Impact: 18.1-42.7% of frozen R01 EURUSD events gain a ref hit, mean ΔS +0.005..+0.011, tercile moves 2.2-10.0%; R01 tables/terciles stay frozen (`research/physics/_diag/REFS_IMPACT.json`). | `research/physics/tests/test_refs_carry_forward.py::test_daily_levels_carry_forward_all_day` |
| F4 | `research/physics/phys_stats.py:184-187` | `years_4of6` and `symbols_3of4` contained lenient "all-of-3" fallbacks (3 observed years/symbols all positive counted as a pass, weaker than the charter). | Both fallbacks deleted: `symbols_3of4 = n_sym >= 4 and n_sym_pos >= 3`, `years_4of6 = n_yr >= 6 and n_yr_pos >= 4`. No frozen R01 verdict changes (n_yr=6, n_sym=4; the branch was dead). | `research/physics/tests/test_gate_verdict.py` (3 tests; the 3-year and 3-symbol cases fail against the pre-fix code) |
| F5 | `research/physics/phys_analysis.py:56-59` | `_freeze_ok` claimed an mtime ordering guard in its docstring but only checked existence. | The guard now refuses when any input table (`EVENTS_*`/`CONTROLS_*`; `OUTCOME_*` excluded by design) is newer than `FREEZE.json`. | `research/physics/tests/test_freeze_guard.py` (3 tests; the "table newer" case fails against the pre-fix code) |
| F9 | `lib/pa_ledger.py:170-197` | `verify()` could not detect tampering with the LAST line (nothing referenced its hash). | Sidecar `<ledger>.tail` holds the SHA256 of the last line's raw bytes, written atomically after every `append`; `verify` compares it and bootstraps it once for pre-fix ledgers (chain-valid). Tradeoff vs a terminator line is stated in the code comment: no format/line-number change for existing readers, at the cost of a sidecar file. Existing 27 lines untouched; chain still `(True, None)`; sidecar bootstrapped for the real ledger. | `tests/test_ledger_tail.py` (3 tests; last-line tamper returns `(False, 2)`) |
| F10 | `research/physics/run_counts.py:126-128` | Called the pre-Addendum-2 `extract_controls` signature (`TypeError` if run). | Now `extract_controls(ev, srcs[name], ref, ctx.bars, symbol)`; stale `StructureIndex` use removed. | `research/physics/tests/test_run_counts_signature.py` (2 tests) |
| F11 | `research/physics/phys_analysis.py:227` | Column "K̄ (ctrl/ev)" was `n_ctrl / n_resolved` (could exceed K=5; `sd_base` 6.08) and mislabelled. | Renamed to `ctrl_per_resolved` and the true `mean_k_per_event = n_ctrl / n_events` added beside it; results-table header updated. | locked by the rename itself; no frozen artifact rewritten (R01 STATS.json keeps its historical field) |

Suite before/after (commands run from `03. EA Developer/PA_Pro`):

- `python -m pytest tests -q`: **43 passed** -> **49 passed** (4.31 s) — +6 tests (3 F2, 3 F9).
- `python -m pytest research/physics/tests -q`: **31 passed** -> **40 passed** (2.95 s) — +9 tests
  (1 F3, 3 F4, 3 F5, 2 F10).
- `pa_ledger.verify()` on the real ledger: `(True, None)`, 27 lines, sidecar present.
- No commit, no push; machine limits respected (all test runs are light; no physics/eval run).

Old-code failure evidence for the new tests (source-level, per the order's "stashing the fix
mentally"): the pre-fix `pa_eval.py` exposed `_enter_eval`/`_mint_token` as real functions and
`pa_metrics.register_token_checker` as a public setter — `REVIEW_R01_PREFLIGHT.md` §2 F2 records the
reviewer executing both bypasses successfully; the new tests assert raises where the old code
returned, so each fails on the old source.
