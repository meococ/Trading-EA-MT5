# SF01 / F4 — TREND PULLBACK TO ZONE — ROUND REPORT

**Verdict: DEAD.**  2026-09-21.

- Ledger prereg: `T000118` (spec_sha `11e1698e…`, SPEC.md sha `d31cf712…`)
- Detector: `families/f4_trend_pullback.py` v1 — structural H1/H4 trend,
  M5 pullback into a compatible armed zone, resumption close in trend
  direction, stop order beyond signal bar, inv at pullback extreme,
  S ladder (D1).
- Tests: 11/11 pass (incl. prefix invariance, future mutation, warm-up).
- Census: ~125/wk basket (~39k signals) — the densest family tested.
- Snapshots: 12 PNGs, visually correct pullback/resumption geometry.
- Screen: `SCREEN.json` — 20/20 configs, corrected tag contract (D9).

## Headline screen stats

Every one of the 20 cells is PF_x1 < 1.0 with t < 0:

| cell | N | PF_x1 | t |
|---|---|---|---|
| S24/sd_base h4 | 1240 | 0.933 | -1.04 |
| S32/line1 h4 | 3874 | 0.919 | -2.20 |
| S14/line1 h4 | 4131 | 0.915 | -2.60 |
| S32/line1 h1 | 3718 | 0.904 | -2.57 |
| ...16 more cells | 173–7,200 | 0.73–0.90 | all < -1 |

Large samples: 6 cells exceed N=3,000 trades — the estimate is precise,
and the sign is negative.

## Gate analysis

- N gate: satisfied by 17/20 cells — but PF never reaches 1.0.
- t-stat: all negative, most < -2 (significantly LOSING, not noise).
- Lift vs matched random: the random baseline with identical geometry
  beats or matches the setup in every cell — the trend-pullback-to-zone
  condition is worth less than nothing on DESIGN.
- No plateau question arises: the surface is uniformly sub-1.

## Diagnosis

Trend continuation at zones is the single most over-mined pattern in
retail PA. With ~39k signals and M1 fills + costs, the conditional edge
is negative across every rung, generator, and trend source — consistent
with F1-F3 and with the DR3/ECON-1 lesson. Any rescue (deeper pullback,
stronger trend filter, session shaping) would be fishing; the failure
is the hypothesis itself on this data, not the parametrisation.

## Disposition

0/2 logic revisions used. Family closes DEAD.
