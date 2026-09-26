# COMM_INDEX — reports, reviews and findings under `rounds/` and `docs/`

One row per markdown file; `bytes` = size on disk at index time (2026-09-21).
Status rules (Lead, R02-HK2): multi-pass review files — highest pass is CURRENT,
earlier passes are HISTORICAL-RECORD (audit record, never movable); anything
referenced by a FREEZE.json, a PREREG or the ledger is HISTORICAL-RECORD.

## READ-ORDER FOR A NEW AGENT

1. `docs/CHARTER_ADDENDUM_4.md` and `docs/perception/VOLMAN_PERCEPTION_SPEC_v1.md`. Current direction: perception first, validated against Volman's own drawings (BOOK2012). Then `research/perception/LEAD_RULINGS.md`: Ruling 2 stops engine tuning until the golden set passes G-AUDIT, and sets the reasoning protocol.
2. `docs/perception/research/DR_THEORY_BRIEF.md` (deep theory research, run by the Perception lane's sub-agents) and `research/market/MANDATE.md` (DR-MARKET, the empirical market-mechanics lane, DESIGN only; starts when a Devin slot frees).
3. `rounds/R02/ROUND_REPORT.md`. R02 is CLOSED with no claim and no winner; `rounds/R02/CLAIM_VERDICT.md` holds the claim path.
4. `rounds/SF01/LEAD_RULINGS.md` (Review 3). SF01 is closed, 0/6 setups survived.
5. `rounds/SF02/MANDATE.md` and `rounds/SF02/LEAD_RULINGS.md`. The SF02 box ended at 07:37Z with its queue done. Its screens are EXPLORATORY only; the Q2′ setup drafts wait for P-FREEZE.
6. `rounds/R01/ROUND_REPORT.md`. R01 outcome: WINNER NONE, confounded by approach distance (F1).
7. `rounds/R02/FINDING_1_NONIDENTIFIABILITY.md` and `rounds/R02/FINDING_2_STRENGTH_IS_RECENCY.md`.
8. `rounds/R02/REFEREE_HARDENING_2.md`. Current state of the referee, ledger and anchors, with residuals.

## INDEX

| path | bytes | purpose (from heading) | status |
|---|---|---|---|
| `rounds/R00/REGRESSION_DR3.md` | 6519 | R00 mandatory DR3 regression through the PA-PRO referee (parity PASS) | HISTORICAL-RECORD |
| `rounds/R00/REVIEW_R00.md` | 36745 | R00 neutral adversarial review (VERDICT: FAIL) | HISTORICAL-RECORD |
| `rounds/R00/ROUND_REPORT.md` | 16889 | PA-PRO Round 00 foundation report | HISTORICAL-RECORD |
| `rounds/R00/_review/REGRESSION_DR3_rerun.md` | 5505 | R00 DR3 regression rerun with redirected ledger (audit copy) | HISTORICAL-RECORD |
| `rounds/R01/00_LEAD_RULINGS_READ_FIRST.md` | 1367 | Lead rulings for R01 before the prereg/freeze | HISTORICAL-RECORD |
| `rounds/R01/DIAGNOSTICS.md` | 22746 | R01 post-freeze descriptive bounce/break/NONE diagnostics (no gates) | HISTORICAL-RECORD |
| `rounds/R01/FREEZE_ADDENDUM.md` | 4399 | Post-freeze edits inside frozen R01 bundles + R02-F retro-anchor | HISTORICAL-RECORD |
| `rounds/R01/PARITY.md` | 865 | R01 harness arming vs `gen.views_at` parity (0 mismatches) | HISTORICAL-RECORD |
| `rounds/R01/PHYSICS_PREREG.md` | 14392 | R01 frozen zone-generator level-physics bake-off prereg | HISTORICAL-RECORD |
| `rounds/R01/PHYSICS_PREREG_DRAFT.md` | 20374 | Pre-freeze draft of the physics prereg (never frozen) | SUPERSEDED-BY(`rounds/R01/PHYSICS_PREREG.md`) |
| `rounds/R01/PHYSICS_RESULTS.md` | 8855 | R01 results: WINNER NONE, no valid evidence (F1 confound) | HISTORICAL-RECORD |
| `rounds/R01/PROGRESS.md` | 4980 | R01 resume log (append-only, UTC) | HISTORICAL-RECORD |
| `rounds/R01/REVIEW_R01_PHYSICS.md` | 12409 | Adversarial review of R01 Phase B (VERDICT: PASS) | HISTORICAL-RECORD |
| `rounds/R01/REVIEW_R01_PREFLIGHT.md` | 20435 | R01 preflight audit (VERDICT: FAIL, F1 confound) | HISTORICAL-RECORD |
| `rounds/R01/ROUND_REPORT.md` | 11483 | PA-PRO Round 01 report (bake-off outcome + F1 ruling) | HISTORICAL-RECORD |
| `rounds/R02/ASK_LEAD.md` | 5588 | R02 post-pivot feasibility report to Lead (E1/E2 re-scope) | HISTORICAL-RECORD |
| `rounds/R02/CARRY_FORWARD.md` | 4466 | R01→R02 carry-forward item list (F1–F11 statuses) | HISTORICAL-RECORD |
| `rounds/R02/FEASIBILITY.md` | 27959 | R02 arrival-matched design feasibility (Verdict: GO, outcome-blind) | HISTORICAL-RECORD |
| `rounds/R02/FINDING_1_NONIDENTIFIABILITY.md` | 4467 | R02 finding: binary zone question non-identifiable (positivity failure) | HISTORICAL-RECORD |
| `rounds/R02/FINDING_2_STRENGTH_IS_RECENCY.md` | 3274 | R02 finding: strength score is a recency proxy on this data | CURRENT |
| `rounds/R02/PREREG.md` | 63613 | R02 prereg, arrival-matched design (NOT FROZEN, post-review draft) | CURRENT |
| `rounds/R02/PROGRESS.md` | 1580 | R02 resume log (append-only, UTC) | CURRENT |
| `rounds/R02/REFEREE_FIXES.md` | 5442 | R02-A referee fixes F2/F3/F4/F5/F9/F10/F11 with regression tests | HISTORICAL-RECORD |
| `rounds/R02/REFEREE_HARDENING.md` | 9897 | R02-C/D hardening report (token gate doctrine, anchors, scratch exclusion) | HISTORICAL-RECORD |
| `rounds/R02/REFEREE_HARDENING_2.md` | 8516 | R02-F hardening report (anchors deployed, data_sha256, residual limits) | CURRENT |
| `rounds/R02/REVIEW_R02_PREREG.md` | 14389 | Pre-freeze review pass 1 (VERDICT: FAIL, R02-F1..F10) | HISTORICAL-RECORD |
| `rounds/R02/REVIEW_R02_PREREG_2.md` | 16874 | Pre-freeze review pass 2 (VERDICT: FAIL, recency gate measures wrong variable) | HISTORICAL-RECORD |
| `rounds/R02/REVIEW_R02_PREREG_3.md` | 13427 | Pre-freeze review pass 3 (VERDICT: FAIL, E1 inversion + E3) | HISTORICAL-RECORD |
| `rounds/R02/REVIEW_R02_PREREG_4.md` | 8095 | Pre-freeze review pass 4 (VERDICT: FAIL narrow, post-D38 freeze decision) | CURRENT |
| `rounds/R02/REVIEW_REFEREE_FIXES.md` | 11515 | Red-team on R02-A token gate + ledger tail (VERDICT: FAIL, 7 bypasses) | HISTORICAL-RECORD |
| `rounds/R02/REVIEW_REFEREE_FIXES_2.md` | 15568 | Red-team pass 2 on R02-C/F referee (VERDICT: FAIL, residuals accepted) | CURRENT |
| `rounds/R02/ROUND_REPORT.md` | 8933 | R02 round report: CLOSED, no claim, no winner; descriptive E1/E2; D40–D43; R02-A1 | CURRENT |
| `rounds/R02/CLAIM_VERDICT.md` | 5199 | R02 claim-path verdict E3/line1_cluster (gate NOT passed both endpoints) | CURRENT |
| `rounds/R02/DEVIATION_D40_POSTFREEZE_CODE_EDIT.md` | 8784 | Deviation D40: post-freeze code edit, FREEZE v1 VOID | HISTORICAL-RECORD |
| `rounds/R02/DEVIATION_D41_RUNNER_CELLS_DEFECT.md` | 3853 | Deviation D41: runner cells defect, v2 not executable | HISTORICAL-RECORD |
| `rounds/R02/DEVIATION_D42_E2_WEIGHT_ASYMMETRY.md` | 1573 | Deviation D42: E2 cell weight len(ia) | HISTORICAL-RECORD |
| `rounds/R02/DEVIATION_D43_E2_PAIR_KEYERROR.md` | 5908 | Deviation D43: stale base in run_e2, KeyError 36182, ruling (ii) | CURRENT |
| `rounds/R02/R02_A1_STEP_ALL_DIVERGENCE.md` | 14711 | R02-A1 audit: _step_all vs exact replay (~3% E3 label flips, outcome-blind) | CURRENT |
| `rounds/SF01/LEAD_RULINGS.md` | — | SF01 Lead rulings (Reviews 1–3; SF01 closed 0/6) | CURRENT |
| `rounds/SF02/MANDATE.md` | 8597 | SF02 lane mandate (autopsy, families; Q2 paused by Addendum 4) | CURRENT |
| `docs/CHARTER_ADDENDUM_1.md` | 1840 | Charter addendum 1 (binding): zone-first perception + generator bake-off | HISTORICAL-RECORD |
| `docs/CHARTER_ADDENDUM_2.md` | 2481 | Charter addendum 2 (binding): control design for level physics | HISTORICAL-RECORD |
| `docs/CHARTER_ADDENDUM_3.md` | 2878 | Charter addendum 3 (binding): compute cap 4, execution gate before any freeze, independent reproduction, setups not gated on physics | CURRENT |
| `docs/CHARTER_ADDENDUM_4.md` | 1885 | Charter addendum 4 (binding): perception first (setups only on a P-v1-validated layer), BOOK 2012 carve-out (perception fidelity only, excluded from CONFIRM-PRE), book material private | CURRENT |
| `docs/perception/VOLMAN_PERCEPTION_SPEC_v1.md` | 22383 | Volman perception spec v1: object grammar, construction rules, budget, BOOK2012 golden-set validation, P-v1 gates | CURRENT |
| `docs/perception/research/DR_THEORY_BRIEF.md` | 9788 | DR-THEORY brief: deep research (Volman craft, other schools, FX microstructure, perception algorithms, adversarial review) run by the Perception lane's sub-agents | CURRENT |
| `docs/CHARTER_HISTORY.md` | 1284 | Charter version → sha256 history | CURRENT |
| `docs/COSTS.md` | 18559 | Cost model + `c_rt` per symbol (RESEARCH_PROXY) | CURRENT |
| `docs/DATA_INVENTORY.md` | 31142 | 7-symbol M1→M5 data inventory (R00 scan) | CURRENT |
| `docs/PROVENANCE.md` | 4502 | Frozen VPA sources reused vs PA-PRO re-implementations | CURRENT |
