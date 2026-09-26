# SF01 / F1 — ZONE REJECTION — ROUND REPORT

**Verdict: DEAD** (screen v2, 20/20 configs, DESIGN 2016-2021)

Spec: `SPEC.md` v2 — ledger `spec_prereg` T000059
(sha `8d182edf31e1f24214783540054964d666e9abb80dfb0fbcaea7f2517678b425`).
Screen data: `SCREEN.json` (every config ledger-logged via pa_eval).

## What was tested

Probe into an armed zone that closes back outside the band (2-bar
rejections admitted); stop order 1 pip beyond the signal bar; structural
stop = probe extreme snapped to the S ladder {11,14,18,24,32}; TP = 2R
fixed. Grid: 5 rungs x {line1_cluster, sd_base} x rej_body{0,1} = 20.

## Census (pre-outcome)

12,720 basket signals / 314 wk = 40.5/wk — cadence far above target.
Snapshot QA: 12 PNGs, Lead visual review PASS.

## Screen result (x1 costs)

| metric | best cell | range |
|---|---|---|
| PF x1 | 0.983 (S24/sd/b0) | 0.794 - 0.983 |
| t | -0.20 | -3.84 .. -0.20 |
| lift vs matched random | +0.93pp (CI -0.43..+2.32) | -13.4 .. +4.6 pp |
| years PF>1 | 3 | 0 - 3 of 6 |
| symbols exp_r>0 | 3 (one thin cell) | 0 - 3 of 4 |

Zero of 20 configs pass any of: PF>=1.15, t>=2.5, lift CI>0, year/symbol
robustness, plateau. The matched-random baseline itself runs PF 0.86-1.02;
the setup adds nothing over it — consistent with R02's finding that zone
"strength" is mostly recency and zone-vs-empty physics is not identifiable.

## Diagnosis

Uniform failure across the entire grid — no rung, generator, or body
filter rescues it; there is no sub-population worth a revision. Revising
further would be fishing against multiplicity, not diagnosing.

## Evidence files

- `SPEC.md`, `SCREEN.json`, `snapshots/` (12 PNGs)
- Detector: `families/f1_zone_rejection.py`; tests:
  `families/test_f1_zone_rejection.py` (all pass)
- Census funnel: F1 v1 diag (zones->armed->probe->range->sstruct->d_opp)
- Pre-outcome revisions: v1->v2 (d_opp gate removed, S ladder), ledger
  T000052 -> T000059; no outcome ever computed on v1.
