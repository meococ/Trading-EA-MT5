# R01 PROGRESS — resume log (UTC)

One line per completed step: `UTC | step | status | key files`. Append only.

2026-09-20T14:22Z | A0 | OK | charter+addendum hashes verified; R00 report/bank/draft/LINE-1 review read; ZONE-1 SHORTLIST+REVIEW PASS observed at 14:47Z
2026-09-20T14:50Z | A1 | OK | research/physics harness (phys_common, phys_source, phys_extract, phys_controls, phys_resolve, phys_stats) + 29 synthetic tests pass
2026-09-20T15:05Z | A2-pilot | OK | EURUSD 14k bars: line1_cluster 264 events / 512 zones; fractal_h1 142/190; realized K=0.08 under charter-literal control rule -> ASKED LEAD
2026-09-20T14:22Z | A0 | NOTE | UTC clock: this file is UTC; VN = UTC+7

2026-09-20T15:35Z | B1 | OK | PHYSICS_PREREG.md frozen; FREEZE.json (10a9830e..) written BEFORE any outcome file (verified 0 OUTCOME_* at freeze); 48 table hashes; q33/q67 per generator
2026-09-20T15:36Z | B2 | OK | resolve 4 symbols x 6 generators; 6 ledger trials T000022..T000027 (family=PHYSICS)
2026-09-20T15:37Z | B3 | OK | PHYSICS_RESULTS.md: all six bounce D_top negative (-5.3..-7.4pp); continuation +20.9..+28.7pp (BH q=0.0002); WINNER NONE
2026-09-20T15:49Z | B3-review | OK | REVIEW_R01_PHYSICS.md VERDICT PASS (2 MAJOR, 3 MINOR, 4 INFO); no prereg deviation/look-ahead/unlogged trial
2026-09-20T15:52Z | D7 | OK | PARITY.md already carries GBPUSD/USDJPY/AUDUSD 100-bar rows, 0 mismatches (no re-run needed)
2026-09-20T15:55Z | D8c | OK | lib/pa_fill.py TP exit r=tp_mult fixed + regression test; pytest tests -> 43 passed
2026-09-20T16:05Z | D1-D5 | OK | _diag/DIAG.json from frozen tables: D2 volatility refuted, D3 frozen-A worse, D4/D4b position arms overlap (folded 0.21-0.28 vs 0.19-0.22; D_bounce +6pp near extreme to -9pp mid-range), D5 timing
2026-09-20T16:10Z | D8a | OK | fresh readings: frozen=strict bucket; ordered admits +23.6%..+36.7% EURUSD candidates (_diag/FRESH_READINGS.json)
2026-09-20T16:12Z | D9 | OK | refs.py daily carry-forward defect confirmed (1577 vs 445595 bars); feeds T_ref/strength of all six + contam_ref
2026-09-20T16:15Z | D1-D9 | OK | rounds/R01/DIAGNOSTICS.md (286 lines) written; R01-D2 headline + Lead interpretation appended to PHYSICS_RESULTS.md
2026-09-20T16:16Z | R02 | OK | rounds/R02/CARRY_FORWARD.md started (11 items)
2026-09-20T16:17Z | HOLD | OK | Phase C NOT started per Lead order R01-D1/D2; Phase A3 dropped (families owned by another worker)
2026-09-20T16:20Z | D9-hash | OK | moved stray _diag_dist.py into _diag/; physics dir hash reproduces frozen d118b72f.. exactly; pa_ledger.verify()=(True,None)

2026-09-20T16:40Z | FINAL-1 | OK | DIAGNOSTICS.md D8a corrected (no divergence; strict rule matches frozen prereg; relabelled population-width sensitivity) + three-way bounce/break/NONE decomposition (stall effect) added as the headline table
2026-09-20T16:45Z | FINAL-2 | OK | rounds/R01/ROUND_REPORT.md written (charter section 7 + Lead R01-FINAL section 3 verdicts quoted verbatim)
2026-09-20T16:47Z | FINAL-3 | OK | LEADERBOARD.md R01 row (no candidate; physics row with both endpoints)
2026-09-20T16:50Z | FINAL-4 | OK | bank/HYPOTHESIS_BANK.md section 4 re-ranked on R01 evidence (fade/bounce families down, continuation families up, PAF-03 CONTESTED, no deletions)
2026-09-20T16:52Z | FINAL-5 | OK | rounds/R02/CARRY_FORWARD.md completed with the R02 control-design requirement (position +-0.02 and same-day timing arm alongside Addendum-2)
2026-09-20T16:53Z | FINAL-6 | OK | round closed per Lead; no Phase C, no R02 prereg, no commit, no push

2026-09-20T17:10Z | FB-1 | OK | REVIEW_R01_PREFLIGHT.md read in full (VERDICT FAIL; F1 control confounded by approach distance)
2026-09-20T17:15Z | FB-2 | OK | DIAGNOSTICS.md regenerated: three-way section retitled/rewritten as episode-type contrast; no zone attribution; F1 saturation caveat; F6 note (draft-vs-frozen process defect); summary updated
2026-09-20T17:20Z | FB-3 | OK | PHYSICS_RESULTS.md headline + interpretation replaced (R01-FINAL-B supersedes R01-D2; continuation uninterpretable; bounce not closed; no zone claim)
2026-09-20T17:25Z | FB-4 | OK | ROUND_REPORT.md rewritten: honest-answer quote verbatim as headline, both endpoints uninterpretable, F1 status as ruled, 5 reviewer answers quoted verbatim, defect inventory F1-F11
2026-09-20T17:27Z | FB-5 | OK | LEADERBOARD.md: R01 = no winner, no evidence, method defect found; bank section 4 re-ranking REVERSED (all families UNCHANGED; PAF-03 prior status)
2026-09-20T17:30Z | FB-6 | OK | rounds/R02/CARRY_FORWARD.md completed per section 6.4 (arrival-matched design + eligible-control-share feasibility first; F2/F3/F4/F5/F9/F10/F11 with reviewer file:line; F6 diff-vs-draft rule; F7 raw-shares rule; F8 policy; hash narrowing)
2026-09-20T17:32Z | FB-7 | OK | rounds/R01/FREEZE_ADDENDUM.md written (pa_fill.py old abfdbb93.. -> new 8e65a15e..; lib bundle afa4ac30 -> 9427a816; Lead order D8c)
2026-09-20T17:33Z | FB-8 | OK | round closed per R01-FINAL-B; no Phase C, no R02 prereg, no commit, no push
