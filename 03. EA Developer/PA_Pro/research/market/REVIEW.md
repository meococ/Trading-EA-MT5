# M8 — Independent review (adversarial-auditor) + remediation record

Reviewer: subagent that wrote none of the code.  Scope: causality /
leakage, placebo validity, multiple testing, stability claims, forbidden
data access.  This file records the upheld findings and their
disposition; the full audit trail lives in `DEVIATIONS.md` (D6–D21).

## Verdict

The first execution of M3–M6 deviated from `STUDY_PLAN.md` in ~15 places.
Two defects were causal (lookahead), two placebo designs were
non-exchangeable (voiding/weakening headline results), and the M6
module omitted declared tests.  All findings were upheld by inspection
and remediated; extraction and analysis were re-run from scratch.
Ledger rows T000367–T000379 refer to pre-review numbers.

## Upheld findings → disposition

| # | Finding | Severity | Fix | Dev |
|---|---|---|---|---|
| 1 | ASIA columns: server-day/CET wraparound armed levels ~9–10% of events before the Asia window completed (lookahead) | causal | arm strictly after window close; CET≥1380 bars belong to prior CET date | D6 |
| 2 | M3 freshness counted prior intersections of the *column* zone, not the *event* zone | estimand | per-candidate check vs event [zlo,zhi] from level birth | D7 |
| 3 | M3 cross threshold / fwd off-by-one / retest lag origin / role-reversal path | estimand | close beyond outer edge; fwd at t+H; lag from break bar; declared post-retest path | D8 |
| 4 | M4 detector ≠ declared §5 detector (longest-window, fixed pip heights) | spec | rewrote to W=30, 1.5–6 ABR, interleave, span≥9, 100-bar death | D9 |
| 5 | M4 placebo = random bars → non-exchangeable; F-FB +13.8pt unreliable | placebo | declared P-RAND fake edges (≥2 touches in trailing 30), height-tercile strata | D10 |
| 6 | M5 placebo = random bars; ~70% never intersect → F-TL −13.7pt **void** | placebo | 2 shifted copies/line (same anchors+slope, ±δ·ABR, δ~U[1.5,4]) | D11 |
| 7 | M5 detection (M5 index) vs resolution (M1 time) geometry mismatch — extreme across feed gaps | estimand | resolution evaluates line at M5 bar index | D12 |
| 8 | M5 freshness counted accepted events, not zone intersections | estimand | every zone hit refreshes the clock | D13 |
| 9 | M6: θ=2.0 labelled θ₂; warmup leaks; no gap segmentation; wrong session edges; VR/EMA grids and formal family incomplete | spec | θ₁=1.0/θ₂=2.5, warmup excluded, >300s gap breaks, CET 480/870/1080, full grids, F-M=12 tests | D14 |
| 10 | Strata quantile edges pooled across symbols (USDJPY collapse) | stats | per-symbol edges on pooled real+placebo | D15 |
| 11 | Analyzer family structure ≠ plan (F-A bins, F-T/F-B pooling, F-C h48 formal, F-R missing secondary estimand) | spec | analyzers rebuilt to declared families/sizes | D16 |

Self-found during remediation (also logged): D17 (moving-edge streaks),
D19 (M5 lines on θ₁ not θ₂), D20 (F-O ran contrasts though declared
descriptive), D21 (VR missing 1/k; segment-boundary returns).

## Result status after remediation

- **Voided:** F-TL −13.7pt (third-touch contrast) — placebo
  non-exchangeable.  Replaced by the corrected run's numbers.
- **Weakened/unverified:** F-FB +13.8pt @5p — recomputed against the
  declared fake-edge placebo.
- **Contaminated:** all ASIA rows — recomputed without lookahead.
- **Detector artefact withdrawn:** "box heights cluster 27–33p" — old
  detector's maximal-window bias; F-BX re-derived on the declared
  detector.
- **Re-derived:** every other contrast under per-symbol strata and the
  declared family structure.

## Re-review checklist for the second pass

- ASIA causality (no event before window close).
- M5 placebo exchangeability (same anchors/slope/machinery).
- M4 fake-edge conditioning (≥2 touches in trailing 30).
- M6 F-M family = 12 declared tests; VR(k) = Var(Σ_k r)/(k·Var r).
- Family sizes: F-R 24, F-A 5, F-T 6, F-B 4, F-C 4, F-X 6, F-L 4, F-M 12.
