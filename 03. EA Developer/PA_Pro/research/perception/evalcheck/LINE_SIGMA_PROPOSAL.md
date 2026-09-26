# LINE_SIGMA_PROPOSAL — EVAL-AUDIT mandate 2, item 7

2026-09-21, lane EVAL-AUDIT.  **Proposal only — no ruler change made.**
The Lead decides.  Source measurements: `linelab/LINE_YARDSTICK_AUDIT.md`
+ `linelab/audit_lines.json` (185 scorable TUNE-v2 lines, all `prec=eye`,
184 `repaired`).

## What the ruler does today

`common.prec_sigmas`: `repair_method` in {constrained_fit,
text_anchor_bars, edge_from_bars(+subwindow), sibling_span} →
`REFINED_PRICE_SIGMA = 1.5 p`; `meas` → 2 p; else `eye` → 5 p.
`eval_v2` line rule: `tol_l = σ_p + |slope_g|·10 min`, evaluated at the
two *overlap-edge* times of the clipped spans (mid-span probes, never
the ink end).

## Measured residuals vs the σ in force

| probe point (label vs its own bars) | trusted p50 | trusted p90 | trusted p95 | current σ |
|---|---|---|---|---|
| named anchor bar (`anchor_res`) | 0.00 | 1.06 | — | 1.5 p ✔ supported |
| hugged extremes mid-span (`hug4_dev`) | 0.29 | 1.57 | 2.03 | ~2 p supported |
| unanchored t0 (`end0_res`) | 0.00 | 6.20 | — | not probed (span used) |
| t1 ink end (`end1_res`) | 0.70 | 20.0 | — | not probed (correct) |

Effective `tol_l` (σ=1.5 + slope·10min, median 2.09 p) covers the
label's own mid-span deviation in **75.2%** of the trusted 141 lines
(`hug4_dev ≤ tol_l`); at σ=2.0 → 75.9%, σ=2.5 → 85.1%.  `hug4_dev` is
a max-over-4-extremes statistic, so these fractions are a *conservative*
bound on the ruler's two-probe test.

## Reading

- 1.5 p is right **at anchors** (p90 = 1.06 p) and too tight **at
  mid-span** (trusted p95 ≈ 2.0 p).  Since eval_v2 probes mid-span, the
  relevant label noise for a truthful engine line is ≈2 p, not 1.5 p.
- Endpoint sigmas would be meaningless (t1 p90 ≈ 20 p); eval_v2 already
  avoids them.
- Separately: E2 jitter showed eval_v2 @1× noise (σ=1.5) still recalls
  ≥0.963 — the ruler is not *under*-tolerant for label-faithful copies.
  The σ question is about labels vs bars, i.e. how far an honest engine
  line may sit from a *fitted* label.

## Options for the Lead

| option | line σ | effect |
|---|---|---|
| A (recommended) | σ_line = 2.0 p for PATTERN_LINE/CONTEXT_LINE probes; keep 1.5 p for box/level prices and anchor-pinned checks | matches trusted p95 ≈ 2.0 p (≈0.45·ABR); probe coverage 75.9% on the conservative hug4 bound |
| B | keep 1.5 p everywhere | strictest; ~1 in 4 trusted labels carries a mid-span deviation beyond tolerance |
| C | stratum-split: 1.5 p text_anchor_bars / 2.0–2.5 p constrained_fit | hug4 p95 is ≈2 p in *both* strata — not supported by the data |

Recommended: **A**, implemented as a line-type σ override in `prec_sigmas`
(or a `LINE_PRICE_SIGMA = 2.0` in eval_v2's line rule only).  No other
tolerance changes; time stays ±10 min; endpoints stay unprobed.

Ruler frozen at `eval_v2.py:04c6f7bdff6459d5` — this file changes
nothing; adoption requires a Lead ruling + E1/E2 rerun + new hash.
