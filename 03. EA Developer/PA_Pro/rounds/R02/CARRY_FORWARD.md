# R02 CARRY-FORWARD — one line per item (started 2026-09-20; completed per R01-FINAL-B §6.4)

Append-only between rounds. Each item: what, where, why it matters, status. Reviewer file:line
references are from `rounds/R01/REVIEW_R01_PREFLIGHT.md` (VERDICT FAIL).

1. **F1 / R02 CONTROL REDESIGN (the decisive item).** R02's primary control is an
   **arrival-matched observational design** (Lead R01-FINAL-B §6.1): enumerate every bar where price
   completes a fresh approach (identical freshness and away-bar rules) to a band of width w placed at
   the arrival location; TREATED arm = arrivals where an armed zone of the generator is there;
   CONTROL arm = arrivals where no armed zone is within a pre-declared margin; arms matched on side,
   ATR regime, hour-of-day and approach distance by exact strata. The literal "same distance, same
   side" band is degenerate (= the same price). BEFORE the prereg is written, measure and report the
   **eligible-control share** (share of arrivals with no armed zone within the margin, per
   generator). S-NEAR is cited in the R02 prereg as supporting evidence for the episode-type
   asymmetry, labelled as such. Status: OPEN.
2. **F2 (MAJOR, referee).** Eval-token bypasses: public `pa_metrics.register_token_checker`
   (`lib/pa_metrics.py:49-51`) and module-level `pa_eval._enter_eval`/`_mint_token`
   (`lib/pa_eval.py:86`). Fix: remove the public checker, move enter/mint behind a closure or a
   context manager, add a test asserting both old bypasses raise. Off the R01 outcome path.
   Status: OPEN.
3. **F3 (MINOR).** `struct/zones/refs.py:59-67` daily-level carry-forward (pdh/pdl/pdc written only
   at the day-rollover bar; 0.35% vs ~99.8% visibility; feeds `T_ref` in strength and `contam_ref`).
   Fix in R02 with a re-freeze. Status: OPEN.
4. **F4 (MINOR).** `research/physics/phys_stats.py:184-187` lenient 3-of-3 fallbacks in
   `years_4of6` and `symbols_3of4` (weaker than the charter's >= 4/6; inert this run, n_yr=6).
   Status: OPEN.
5. **F5 (MINOR).** `research/physics/phys_analysis.py:56-59` freeze-ordering guard documented but not
   implemented (existence check only). Implement the mtime comparison. Status: OPEN.
6. **F6 (MINOR, PROCESS).** The draft-to-frozen §3.2 freshness tightening was NOT declared in prereg
   §0 (it shrank the population ~23-37% vs the draft's ordered scan). The frozen spec binds and the
   code is faithful to it; the defect is the missing declaration. Every future prereg MUST carry a
   "diff vs draft" subsection in §0. Status: OPEN (process rule).
7. **F7 (MINOR).** Prereg required raw shares with NONE in the denominator; the first results artifact
   showed only conditional proportions (now in `DIAGNOSTICS.md`; conditioning slightly masked the
   negative D). Rule: raw shares are part of every future physics results artifact. Status: CLOSED
   for R01 (fixed), rule carried.
8. **F8 / FREEZE ADDENDUM POLICY (INFO, process).** A post-freeze edit to any file inside a frozen
   bundle is recorded in `rounds/<R>/FREEZE_ADDENDUM.md` with the old hash, the new hash, the reason
   and the authorizing Lead order. First entry written for `lib/pa_fill.py` (D8c).
   R02 narrows frozen bundles to outcome-path modules only. Status: DONE (file written); policy OPEN.
9. **F9 (INFO).** `lib/pa_ledger.py:170-197` `verify()` cannot detect a last-line tamper (nothing
   references its hash). Consider a sidecar head-hash or an append-time commit. Status: OPEN.
10. **F10 (INFO).** `research/physics/run_counts.py:126-128` stale `extract_controls` signature ->
    TypeError if run; not on the outcome path. Status: OPEN.
11. **F11 (INFO).** `research/physics/phys_analysis.py:227` + RESULTS column "K̄ (ctrl/ev)":
    `mean_k = n_ctrl / n_resolved` can exceed K=5 (`sd_base` 6.08); label/definition to fix.
    Status: OPEN.
12. **Hash narrowing (F8-adjacent).** `physics_code_sha256` should cover only the outcome-path
    modules so diagnostic scripts cannot drift the frozen hash. Status: OPEN.
13. **pa_fill TP-R bug** (`lib/pa_fill.py`, hardcoded `r = 2.0` -> `tp_mult`) fixed 2026-09-20 with
    regression test; recorded in `rounds/R01/FREEZE_ADDENDUM.md` per the new policy. Status: DONE.
14. **R01 verdict status.** R01 produced NO VALID EVIDENCE about zone physics either way (control
    confounded, F1); no winner; no family re-ranked; bounce question NOT closed, Addendum-2 control
    closed. `rounds/R01/ROUND_REPORT.md`. Status: CLOSED.
