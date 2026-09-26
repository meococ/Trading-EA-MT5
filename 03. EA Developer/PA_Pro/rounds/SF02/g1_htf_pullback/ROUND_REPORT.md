# G1 — HTF-structure pullback (LIMIT at salient zone edge) — DEAD

Screen: `SCREEN.json` (2026-09-21T06:58Z), 20/20 cells evaluated through
`pa_eval` with the D3 paired-random baseline (`<fam>_rand` ledger family;
limit randoms at signal-bar extreme ∓ buf). Spec v2 prereg T000282
(sha 948b62d2); superseded: T000279 (v1), T000281 (v2 pre-scan-fix).

## Headline

| cell | N | PF x1 | t | lift pp (CI) |
|---|---|---|---|---|
| S18 line1 h1 | 440 | 0.869 | -1.33 | -1.34 [-5.8,+3.4] |
| S18 line1 h4 | 548 | 0.668 | -4.30 | **-6.42 [-10.3,-2.3]** |
| S18 sd_base h1 | 180 | 0.721 | -2.00 | -5.73 [-12.3,+1.6] |
| S18 sd_base h4 | 230 | 0.688 | -2.57 | **-7.75 [-13.5,-1.4]** |
| S24 sd_base h4 | 101 | 1.335 | +1.26 | **+10.79 [+0.8,+20.6]** |
| S32 sd_base h4 | 81 | 1.438 | +1.30 | +10.26 [-0.9,+21.1] |
| S40 line1 h1 | 89 | 1.412 | +1.27 | +9.33 [-1.3,+19.7] |
| S40 sd_base h1 | 40 | 1.583 | +1.07 | **+18.64 [+2.7,+32.5]** |
| S40 sd_base h4 | 39 | 1.925 | +1.53 | +6.50 [-9.1,+21.8] |
| S55 sd_base h1 | 50 | 1.332 | +0.68 | +12.20 [-2.1,+25.4] |

Gates: **0/20 pass ALL**. Every cell fails `n300` except the two S18/line1
cells — and those are clearly negative (PF 0.67-0.87, lift <=0,
h4 lift CI entirely below zero).

## Read

- The mandate's "no-chase limit entry" fixed the location defect but did
  not create edge: the thick rung is negative, and its matched-random
  baseline is *better* than the strategy (lift < 0 at S18).
- Wide rungs on **sd_base** (sparse perception) show consistently
  positive lift point estimates (+10 to +19 pp), two with CI excluding
  zero — same direction as the SF01 F6 sd_base signal — but N=39-101
  makes them noise-compatible, not evidence.
- Pattern worth noting for the Lead: positive-lift cells concentrate at
  sd_base + S>=24 + h4 trend; negative at line1_cluster (dense zones).
  Consistent with the autopsy's "perception fix = sparsity" finding.

## Verdict

**DEAD** — 0/20 cells pass gates; the only adequately-sampled cells are
negative, the positive-lift cells are 3-8x too thin to screen. No
sub-population supports a rescue revision (a v3 that loosened cadence
would contradict the salience/sparsity design intent).
