# SF01 / F3 — FAILED BREAKOUT / TRAP — ROUND REPORT

**Verdict: DEAD.**  2026-09-21.

- Ledger prereg: `T000099` (spec_sha `ece98548…`, SPEC.md sha `85043cb1…`)
- Detector: `families/f3_failed_breakout.py` v1 — probe beyond armed
  zone, reclaim close back inside within the window, stop order beyond
  the signal bar, inv at probe extreme, S ladder (D1).
- Tests: 11/11 pass (incl. prefix invariance, future mutation, warm-up).
- Census: ~28k signals ≈ 90/wk basket — every cell well above N≥300
  raw population.
- Snapshots: 12 PNGs, visually correct trap geometry.
- Screen: `SCREEN.json` — 20/20 configs, corrected tag contract (D9).

## Headline screen stats (all cells, PF_x1 sorted)

| cell | N | PF_x1 | PF_x2 | t | lift_pp | lift CI | yrs+ | syms+ |
|---|---|---|---|---|---|---|---|---|
| S11/sd_base rb=1 | 170 | 1.259 | 1.082 | 1.39 | +6.6 | [-0.8, 14.4] | 4/6 | 2/4 |
| S11/sd_base rb=0 | 171 | 1.246 | 1.071 | 1.33 | +7.4 | [-0.05, 15.1] | 4/6 | 2/4 |
| S32/line1 rb=0 | 3050 | 1.025 | 0.941 | 0.57 | +0.04 | [-1.8, 1.9] | 4/6 | 2/4 |
| S32/line1 rb=1 | 2962 | 1.024 | 0.940 | 0.53 | -0.04 | [-1.9, 1.8] | 4/6 | 2/4 |
| all other 16 cells | 170–5878 | 0.79–0.98 | <1 | <0 | — | — | ≤3 | ≤2 |

## Gate analysis

- Best PF cells (S=11/sd_base, PF≈1.25) fail **N≥300** (N≈170) and
  **t≥2.5** (t≈1.4); lift CI lower bound ≤ 0 → no confirmed lift over
  matched random.
- The only high-N cells (S=24/32, N≈3–5.8k) sit at PF≈0.92–1.03 with
  lift ≈ 0 → the trap adds nothing once stop geometry is realistic.
- No plateau: PF collapses between neighbouring rungs/generators
  (1.25 → 0.96 across S11 gen switch; 1.03 → 0.91 across S32 gen
  switch).

## Diagnosis

The reclaim event is real and frequent (~90/wk) but carries no
conditional edge: where the population is thick enough to test
(S≥14), PF is firmly sub-1; where PF nominally exceeds 1.2 the sample
is too thin to distinguish from noise (CI crosses 0). Consistent with
the R01/R02 lesson — zone membership alone is not value.

## Disposition

No rescue revision attempted: the failure is uniform across the
declared grid, not a single-gate miss; any post-hoc tightening (probe
depth, session, volatility filter) would be fishing against the
matched-random baseline. 0/2 logic revisions used → family closes
DEAD.
