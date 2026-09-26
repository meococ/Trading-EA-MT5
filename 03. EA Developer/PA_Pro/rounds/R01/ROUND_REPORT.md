# PA-PRO — ROUND 01 REPORT (zone-generator level-physics bake-off)

Round: R01 · 2026-09-20 · Orchestrator: OpenCode worker (DeepSeek) · Owner: Mèo Cọc · Lead: Claude.
Charter `3C575368…` (verified) · Addendum 1 `37756D69…` (verified) · Addendum 2
`DCB85C81E4D1755D7FA2DD8EF5FD934E4F2B65C62556308AA6BE4F5B964088CE` (transcribed verbatim per Lead).
Prereg `rounds/R01/PHYSICS_PREREG.md` · freeze file sha256
`10a9830eb1f34cadc93fd8876f2d311f35fd175af36d974b434ee7330258be44`, written before any outcome
column existed on disk. ZONE-1 closed PASS. Reviews: `REVIEW_R01_PHYSICS.md` (VERDICT PASS, process
check) and `REVIEW_R01_PREFLIGHT.md` (VERDICT FAIL, F1 MAJOR — the finding that governs this report).

## HEADLINE (Lead R01-FINAL-B §4, quoted verbatim)

> R01 executed a faithful, verified, pre-registered experiment and produced NO VALID EVIDENCE about
> zone physics in either direction. The preregistered control compares two different episode types,
> so neither the negative bounce result nor the large positive continuation result can be attributed
> to the zones. What R01 did deliver: an infrastructure that verifies (freeze ordering, hash chain,
> ledger, causality, arming parity, independently reproduced statistics), one measured
> methodological defect that defines the next experiment, and a defect list for the referee.

The bounce endpoint is **NOT closed** — the earlier claim that it was is withdrawn. What is closed
is the *Addendum-2 control*, not the question.

## 1. Question and estimand

Lead ruling R01-C1 §2, quoted verbatim:

> D = P(bounce | fresh approach to an ARMED zone of generator g) − P(bounce | fresh approach to a
> geometry-matched arbitrary band). D is the incremental value of using this generator's zones
> instead of an arbitrary level with the same geometry.

Six frozen generators (`line1_cluster` baseline, `fractal_h1`, `kde_swing`, `profile_va`, `sd_base`,
`ref_levels`), DESIGN 2016-2021, core symbols EURUSD/GBPUSD/USDJPY/AUDUSD, M5, ARMED population,
K=5 Addendum-2 controls, seed 20260920.

## 2. What was frozen (before outcomes)

Prereg + Addendum 2 + sorted `struct/zones/*.py`, `research/physics/*.py`, `lib/*.py` hashes + every
EVENTS/CONTROLS table hash + per-generator q33/q67 + coverage + counters + seed + split + data
stamps. Harness arming parity vs `gen.views_at(t, arm=True)`: EURUSD 200 bars x 6 generators + 100
bars x 3 symbols for the baseline, **0 mismatches** (`rounds/R01/PARITY.md`). No outcome column
existed at freeze time. Ledger chain verified `(True, None)`.

## 3. What was measured

| generator | armed events | resolved | controls | BH q (bounce) | BH q (cont) |
|---|---|---|---|---|---|
| `line1_cluster` | 44,051 | 30,782 | 164,465 | 1.0000 | 0.0002 |
| `fractal_h1` | 26,243 | 19,031 | 89,945 | 1.0000 | 0.0002 |
| `kde_swing` | 23,311 | 16,009 | 90,844 | 1.0000 | 0.0002 |
| `profile_va` | 4,785 | 3,288 | 17,921 | 1.0000 | 0.0002 |
| `sd_base` | 10,607 | 7,450 | 45,284 | 1.0000 | 0.0002 |
| `ref_levels` | 23,819 | 18,218 | 87,341 | 1.0000 | 0.0002 |

One ledger trial per generator: **T000022 … T000027** (`family=PHYSICS`, `split=DESIGN`, `tf=M5`,
`spec_sha256` = frozen prereg). T000001 (R00 smoke) remains counted per the append-only policy.

## 4. The three-way decomposition — a description of two different episode types

Raw shares of events with a resolved outcome OR NONE; deltas = simple rate differences (real minus
control), unpaired percentile-bootstrap CIs (B=2,000, seed 20260920). Full table with top-tercile
rows in `rounds/R01/DIAGNOSTICS.md`.

| generator | bounce real | bounce ctrl | Δbounce pp [CI] | break real | break ctrl | Δbreak pp | NONE real | NONE ctrl | ΔNONE pp [CI] |
|---|---|---|---|---|---|---|---|---|---|
| `line1_cluster` | 0.4617 | 0.5191 | -5.74 [-6.28,-5.22] | 0.2370 | 0.2300 | +0.71 | 0.3012 | 0.2509 | +5.03 [4.56,5.53] |
| `fractal_h1` | 0.4616 | 0.5140 | -5.24 [-5.94,-4.54] | 0.2636 | 0.2519 | +1.17 | 0.2748 | 0.2341 | +4.07 [3.48,4.68] |
| `kde_swing` | 0.4630 | 0.5240 | -6.10 [-6.83,-5.38] | 0.2237 | 0.2147 | +0.90 | 0.3132 | 0.2613 | +5.20 [4.53,5.88] |
| `profile_va` | 0.4700 | 0.5066 | -3.65 [-5.23,-1.98] | 0.2171 | 0.2155 | +0.16 | 0.3129 | 0.2779 | +3.49 [2.03,4.98] |
| `sd_base` | 0.4561 | 0.5184 | -6.22 [-7.21,-5.16] | 0.2463 | 0.2498 | -0.35 | 0.2976 | 0.2319 | +6.57 [5.59,7.49] |
| `ref_levels` | 0.4499 | 0.5123 | -6.25 [-6.96,-5.54] | 0.3150 | 0.2783 | +3.67 | 0.2351 | 0.2094 | +2.57 [1.97,3.15] |

**The two arms differ in episode type, so this table describes the contrast, not the zones.** Real
ARMED events fire while price hovers at/retests adjacent structure (median near-edge distance
0.28-0.34 ATR at the anchor); a control band must sit >= 1.0 ATR away by Addendum 2 and actually
draws at a median 2.11-2.37 ATR, so a control event can only fire after price has TRAVELLED to it
(impulse-arrival episode). That asymmetry predicts the sign of all three columns and of the
continuation endpoint. No column is attributed to zone physics; no "stall effect" claim is made.

## 5. Endpoint status (supersedes R01-FINAL §3b/§3c)

- **Bounce endpoint:** the pre-registered FAIL stands as a faithful answer to the preregistered
  estimand (D_top −5.3 to −7.4pp, all CIs < 0, BH q = 1.0000), but under F1 it is **not valid
  evidence about zone physics either way**. The question is NOT closed; the Addendum-2 control is.
- **Continuation endpoint:** the large positive result (+20.9 to +28.7pp, BH q = 0.0002, kde_swing
  and ref_levels passing all clauses, the other four failing only monotonicity) is **uninterpretable
  under this control**. It is not the round's positive finding.
- **Winner: NONE.** No generator is promoted. `line1_cluster` stays the working default by inertia.
- **Honest status of F1 (Lead R01-FINAL-B §3, quoted):** "the asymmetry is measured and real; the
  causal claim that it produces the whole gap is NOT established." The control bounce rate is flat
  across control-distance deciles (0.68 +- 0.005) — consistent with a mechanism that saturates past
  1 ATR, but not evidence for it. The decisive test is R02's matched design, not more argument.
- D4b position-in-range is POST-HOC and unpaired; it is a hypothesis for R02, never a finding of R01.

## 6. Lead answers to the reviewer's open questions (R01-FINAL-B §6, verbatim)

1. Control design for R02: the literal "same distance, same side" band is DEGENERATE — at the same distance on the same side from the same bar it is the same price as the real zone. R02's primary control is therefore an ARRIVAL-MATCHED observational design: enumerate every bar where price completes a fresh approach (identical freshness and away-bar rules) to a band of width w placed at the arrival location; the TREATED arm is the arrivals where an armed zone of the generator is there, the CONTROL arm is the arrivals where no armed zone is within a pre-declared margin; the arms are matched on side, ATR regime, hour-of-day and approach distance by exact strata. That asks the question we actually care about: when price arrives somewhere, does it matter whether one of our zones is there? Before writing the prereg, measure and report the eligible-control share (the share of arrivals with no armed zone within the margin, per generator) — that is the feasibility number that killed the charter-literal control, and I want it measured first this time.
2. The draft-to-frozen §3.2 freshness tightening was NOT declared in §0 and should have been: it is a process defect, recorded as such; the frozen spec binds and the result stands. Every future prereg must carry a "diff vs draft" subsection in §0.
3. `pa_fill.py` at 15:52:27Z was my order (D8c), deliberate, outside the frozen physics path. Policy from now on: a post-freeze edit to any file inside a frozen bundle is recorded in `rounds/<R>/FREEZE_ADDENDUM.md` with the old hash, the new hash, the reason and the Lead order that authorized it. Write that file for `pa_fill.py` now. R02 narrows the frozen bundles to outcome-path modules only.
4. R02 fix list CONFIRMED: F2 (token-gate bypasses: remove the public `register_token_checker`, move `_enter_eval`/`_mint_token` behind a closure or context manager, and add a test that asserts both old bypasses now raise), F3 (refs.py daily carry-forward), F4 (the lenient 3-of-3 fallbacks in both clauses), F5 (the missing freeze-ordering guard), F9 (ledger last-line tamper), F10, F11. All go in `rounds/R02/CARRY_FORWARD.md` with the reviewer's file:line.
5. Yes — cite S-NEAR in the R02 prereg as supporting evidence for the episode-type asymmetry, labelled as such.

## 7. Defect inventory (carried to R02, from `REVIEW_R01_PREFLIGHT.md`)

- F1 MAJOR — control confounded by approach distance (this report; R02 redesign in §6.1).
- F2 MAJOR — eval-token bypasses via public `register_token_checker` and module-level `_enter_eval`/`_mint_token` (`lib/pa_eval.py:86`, `lib/pa_metrics.py:49-51`); off the R01 outcome path.
- F3 MINOR — `struct/zones/refs.py:59-67` daily-level carry-forward (0.35% vs ~99.8% of bars).
- F4 MINOR — `research/physics/phys_stats.py:184-187` lenient 3-of-3 fallbacks (inert this run).
- F5 MINOR — `research/physics/phys_analysis.py:56-59` freeze-ordering guard documented but not implemented (order held externally).
- F6 MINOR — draft-to-frozen §3.2 freshness tightening undeclared in §0 (process defect; frozen spec binds, code faithful).
- F7 MINOR — prereg required raw shares; the results artifact initially showed only conditional proportions (fixed in DIAGNOSTICS.md; conditioning slightly MASKED the negative D).
- F8 INFO — `lib/pa_fill.py` post-freeze edit; `FREEZE_ADDENDUM.md` written per §6.3.
- F9 INFO — `lib/pa_ledger.py:170-197` cannot detect a last-line tamper.
- F10 INFO — `research/physics/run_counts.py:126-128` stale signature (not on the outcome path).
- F11 INFO — `phys_analysis.py:227` mean_k uses resolved events (can exceed K=5; label misleading).

## 8. What the round delivered (method, not market)

1. A verified experiment infrastructure: freeze ordering, hash chain, ledger, causality, arming
   parity, independently reproduced statistics (two reviewers; re-extraction row-identical).
2. One measured methodological defect (F1) that defines the next experiment: the control must be
   arrival-matched, and the eligible-control share must be measured before the prereg.
3. A defect list (F2-F11) for the referee and codebase.
4. A withdrawn interpretation, recorded rather than hidden: no zone claim from R01 in either
   direction.

## 9. Next round

No R02 prereg is written by the orchestrator; the Lead writes the R02 ruling first. The R02
requirements are in `rounds/R02/CARRY_FORWARD.md` (arrival-matched two-arm design + feasibility
measurement; F2/F3/F4/F5/F9/F10/F11 fixes; S-NEAR cited as supporting evidence for the episode-type
asymmetry; freeze bundles narrowed to outcome-path modules; `FREEZE_ADDENDUM.md` policy).

## 10. Provenance and compliance

All writes stayed under `03. EA Developer/PA_Pro/`; no commit, no push, no worktree, no MT5/terminal,
no trading tool, no OCR/ML; heavy python through `lib/pa_slots.py` (≤2 processes, 4 threads,
BelowNormal); cache read-only. Outcome reads happened only after FREEZE.json existed. Evidence:
`rounds/R01/PROGRESS.md`, `PHYSICS_RESULTS.md`, `DIAGNOSTICS.md`, `REVIEW_R01_PHYSICS.md`,
`REVIEW_R01_PREFLIGHT.md`, `research/physics/bakeoff/STATS.json`.
