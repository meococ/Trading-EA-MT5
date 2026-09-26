## SUMMARY
Verdict: **R02-F implemented.** The anchor is now deployed, the data commitment covers every result-deciding field, and the residual limits are written down in plain words instead of implied.
- Deployed, not just claimed: `ledger/ANCHORS.jsonl` exists with a **retro-anchor** (n_lines 27, sha256 `4f1d3af8…`, 2026-09-20T19:40:59Z) whose note says nothing before that line has ex-post protection, plus the anchor for this report (19:43:53Z). `verify_against_anchors()` -> `(True, None)`.
- Writers emit: `phys_freeze` appends an anchor AND stores `ledger_anchor` in `FREEZE.json` (same record); `phys_analysis._write_results_md` appends an anchor AND embeds the line. Deployment is locked by `tests/test_referee_hardening_r02f.py::test_real_repo_ledger_is_anchored` (fails while `ANCHORS.jsonl` is missing or pre-anchor history is rewritten).
- Anchor semantics: prefix hash, appends legal by design, rewrite/truncation inside the covered prefix detected, earliest violated anchor reported, degenerate `n_lines=0` and missing anchors file fail closed.
- `data_sha256` fixed for red-team N8/D1-D3 and N9/D5: a frozen 30-field list (`lib/pa_eval._DATA_SHA_FIELDS`) covers `pip`, `starts`, `m5`, `m5_t`, `next_end`, `sess_mask`, `first_live_idx`, `c_rt_pips` and all arrays; the hash is computed by the referee from the actual objects and a caller-supplied `data_sha256` is ignored. A test perturbs every listed field and fails if any is unhashed.
- Old-code proof: the 9 new tests **9 failed / 0 passed** against the pre-R02-F `lib` snapshot (`_scratch/r02f/oldrepo_failures.txt`); the two writer tests **2 failed / 1 passed** against the reverted writers (`_scratch/r02f/oldrepo_physics_failures.txt`).
- Suites now: `tests` 66 passed (57 -> 66), `research/physics/tests` 43, `struct/zones/tests` 50. Real ledger untouched: 27 lines, sha256 `4f1d3af8…`, `verify() (True, None)`.
- Charter §6 items 6–7 added (plain-words residual limits + data coverage), new sha256 `4FCCE88A…`, recorded in `docs/CHARTER_HISTORY.md`; retro-anchor also recorded in `rounds/R01/FREEZE_ADDENDUM.md` §3 (the allowed R01 path; `FREEZE.json`/`ROUND_REPORT.md` stay frozen).

Lead must decide: (1) the R02 arrival worker must call `pa_ledger.append_anchor()` + embed `anchor_md()` in its freeze/report writers (paths not ours); (2) accept the listed residual limits as binding doctrine.

---

## 1. What is actually deployed and where

| artifact | carries | how verified |
|---|---|---|
| `ledger/ANCHORS.jsonl` line 1 | retro-anchor `{n_lines:27, sha256:4f1d3af8…, utc:19:40:59Z}` + note "nothing before this line has ex-post protection" | `verify_against_anchors()` `(True,None)`; test asserts the note |
| `ledger/ANCHORS.jsonl` line 2 | anchor for this report (19:43:53Z) | same |
| `research/physics/phys_freeze.py:26` `_anchor_record()` | appends the anchor and returns the FREEZE.json view (identical record) | `test_freeze_writer_embeds_ledger_anchor` |
| `research/physics/phys_analysis.py:381` | appends the anchor and embeds `anchor_md(rec)` in the results artifact | `test_results_writer_embeds_ledger_anchor` |
| `rounds/R01/FREEZE_ADDENDUM.md` §3 | the retro-anchor, and that `rounds/R01/FREEZE.json` was frozen before the key existed and is not rewritten (frozen artifact) | read-only record |

There is no `ledger_anchor` inside `rounds/R01/FREEZE.json` and there never can be without rewriting a frozen artifact; the addendum is the allowed carrier, and it says so.

## 2. Anchor semantics (R02-F item 2)

- `pa_ledger.anchor()` (`lib/pa_ledger.py:296`) is a PREFIX hash: `sha256` over the raw bytes of the first `n_lines` lines. Appending after an anchor is legal; any rewrite/truncation inside the covered prefix fails `check_anchor`.
- `pa_ledger.append_anchor(note)` (`:344`) appends the record to `ANCHORS.jsonl` under the ledger lock.
- `pa_ledger.verify_against_anchors()` (`:367`) validates each record (`n_lines >= 1`, 64-hex sha), re-hashes each prefix, and returns the EARLIEST violated anchor (with `reason` and `index`). Missing/empty anchors file -> `(False, …)`: a ledger with no anchors has no ex-post protection.
- Residual gap, in code and charter §6 item 6: lines appended after the last anchor rest on the chain + `.tail` only (both recomputable), and a party with write access can rewrite `ANCHORS.jsonl` itself. Anchors must be written at every freeze — this narrows the unprotected window; it does not close it.

## 3. data_sha256 completeness (R02-F item 3)

- Frozen list `lib/pa_eval._DATA_SHA_FIELDS` (`:76`): 8 top-level scalars (`symbol, split, tf, pip, first_live_idx, utc_start, utc_end, c_rt_pips`), 4 top-level structures (`m5_t, starts, sess_mask, next_end`), `m1{t,o,h,l,c}`, `bars{t,o,h,l,c,utc_min,srv_min,dow,warmup}`, `m5{o,h,l,c}` = 30 fields.
- `_provider_data_sha256` (`:418`) hashes the list via `_hash_field` (`:387`): arrays as dtype+shape+bytes, dicts/lists in fixed order, absent != None. No provider value is skipped silently.
- Caller assertion removed: `_evaluate_body` calls `_provider_data_sha256(d)` unconditionally; a `data_sha256` key in the provider dict is not in the list and is ignored, and the appended line records only the computed digest.
- Red-team N8/D1-D3 (swapped `pip`/`starts`/`m5`/`m5_t`/`next_end`/`sess_mask`/`first_live_idx`/`c_rt_pips` produced an identical hash) and N9/D5 (provider-asserted hash accepted verbatim) are dead.

## 4. Attack status after R02-F

| attack | status |
|---|---|
| N8 / D1-D3 — unhashed outcome-deciding provider fields | **FIXED** (every listed field perturbed -> hash changes) |
| N9 / D5 — provider asserts `data_sha256` | **FIXED** (ignored by construction) |
| "anchor deployed nowhere" (both red teams) | **FIXED** (deployed, retro-anchored, test-locked) |
| L3 / L8 — last-line / mid-history rewrite + rechain | caught by deployed anchors inside the covered prefix |
| A2 / A3 — fabricate or rewrite lines AFTER the last anchor | **NOT fixable by anchors** (prefix by design); mitigated by re-anchoring at every freeze, documented |
| A1 / A4 — writable anchor carrier / forged degenerate anchor | **NOT fixed** (write access wins); `n_lines=0` now rejected, and the limit is stated in charter §6 item 6 |
| N1–N4 — closure-dig / cell-write gate bypasses | unchanged, accepted residual (gate = accident guard, R02-C doctrine) |
| N5 — `sys._getframe` token theft inside a callback | unchanged, accepted residual (callbacks run in-process) |
| N6 — pre-seeding `sys.modules['pa_ledger']` | unchanged, accepted residual (import system is not seccomp) |
| N7 — `pa_eval.pa_ledger.append` monkeypatch | unchanged, accepted residual; independent re-execution is the control |

## 5. Evidence

- `python -m pytest tests -q` -> `66 passed in 4.46s`; `research/physics/tests -q` -> `43 passed in 2.89s`; `struct/zones/tests -q` -> `50 passed in 14.45s`.
- Old code: `_scratch/r02f/oldrepo_failures.txt` -> `9 failed in 1.48s`; `_scratch/r02f/oldrepo_physics_failures.txt` -> `2 failed, 1 passed in 1.05s`. The oldrepo is the pre-R02-F snapshot plus a script (`_scratch/r02f/patch_oldrepo.py`) that reverts exactly the two writer hooks.
- Real ledger: 27 lines, sha256 `4f1d3af8…`, `.tail` intact, `verify() (True, None)`, `verify_against_anchors() (True, None)`; the ledger file was not modified by R02-F (only `ANCHORS.jsonl` was created/appended).
- `_add_ruling.py` moved PA_Pro root -> `_scratch/_add_ruling.py` (item 5; move, never delete). `_scratch/HOUSEKEEPING.md` updated.

## 6. Deviations and open issues

- The real R02 freeze/report writers live in `research/arrival/` (another worker; NOT TOUCHED). The wiring done here is the pattern for `phys_freeze`/`phys_analysis`; the arrival worker must call `pa_ledger.append_anchor()` and embed `anchor_md()` — charter §6 item 6 makes it binding.
- Not committed: `spec_sha256` still hashes callables by `__qualname__` only, and the `entries_fn` output (the actual signals) is not committed by `data_sha256`. Residual, stated here rather than implied.
- The anchors file sits in the same writable tree as the ledger: an attacker who can write both can rewrite both. The retro-anchor is the only record that predates a rewrite, and it lives in-tree; its value is future detection against copies archived elsewhere. Stated plainly; not oversold.

Ledger anchor: `TRIALS.jsonl` sha256(first 27 lines) = `4f1d3af88f2f833fc6f2cc49b1c6bd479d208abcd1ad1aa03fbd099d383a8776` · n_lines = 27 · utc 2026-09-20T19:43:53Z
