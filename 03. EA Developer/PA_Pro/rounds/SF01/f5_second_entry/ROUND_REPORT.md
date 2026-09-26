# SF01 / F5 — SECOND ENTRY (H2/L2 two-legged pullback) — ROUND REPORT

**Verdict: DEAD.**  2026-09-21.

- Ledger prereg: v1 `T000143` (sha `1e85a227`) -> v2 `T000181`
  (sha `b923336e`; SPEC.md sha `cd7cb222…`). v2 moved `inv` to the
  deepest point of the two-legged pullback after v1's pivot-bar stop
  failed the 10x c_rt floor on ~84% of candidates (D10, pre-outcome).
- Detector: `families/f5_second_entry.py` v2 — fires at the
  confirmation bar of the second leg's pivot; bounce pivot required
  between legs; stop beyond the pivot bar; Brooks stop below/above the
  whole pullback.
- Tests: 11/11 pass (incl. prefix invariance, future mutation, warm-up).
- Census v2: best cell ~2.6/wk basket (S14/h1 824 sig); thin.
- Snapshots: 12 PNGs, geometry visually correct.
- Screen: `SCREEN.json` — 20/20 configs.

## Headline screen stats (top 5 by PF_x1)

| cell | N | PF_x1 | PF_x2 | t | lift_pp | lift CI | yrs+ | syms+ |
|---|---|---|---|---|---|---|---|---|
| S32/tol1.0/h1 | 69 | 1.400 | 1.318 | 1.21 | +5.7 | [-6.4, 17.6] | 3/6 | 1/4 |
| S24/tol1.0/h4 | 255 | 1.331 | 1.143 | 1.99 | +4.4 | [-1.8, 10.7] | 5/6 | 3/4 |
| S32/tol0.5/h1 | 24 | 1.189 | 1.153 | 0.35 | +10.0 | [-9.7, 28.4] | 2/6 | 2/4 |
| S11/tol0.5/h1 | 90 | 1.127 | 1.061 | 0.51 | +8.8 | [-1.2, 19.5] | 5/6 | 2/4 |
| S24/tol0.5/h4 | 100 | 1.091 | 0.981 | 0.38 | +2.0 | [-7.6, 12.1] | 3/6 | 3/4 |

## Gate analysis

- Best cell (S24/tol1.0/h4): N=255 fails N>=300, t=1.99 fails t>=2.5,
  lift CI [-1.8, 10.7] contains 0. Closest to the gates of any family
  this round — still fails three of them.
- Every nominally positive cell is under-sampled; every well-sampled
  cell (S14 h1: N=637 PF 0.83; S14 h4: N=717 PF 0.92) is sub-1.
- Direction of the signal is mildly encouraging (positive-lift cells
  cluster at tol_atr=1.0, h4 trend) but the CIs always include 0.

## Diagnosis

Two-legged pullbacks confirmed by M5 pivots are rare (~2.6/wk) because
pivot confirmation lag + the bounce-leg requirement strip the event
count, and the residual edge does not separate from the matched-random
baseline at any sample size we can field. A cadence-loosening v3
(longer leg_span, wider tol) might push one cell over N=300, but the
lift CI at the best cell already includes zero — loosening gates
widens the CI, it does not shrink it.

## Disposition

1/2 logic revisions used (D10). Family closes DEAD.
