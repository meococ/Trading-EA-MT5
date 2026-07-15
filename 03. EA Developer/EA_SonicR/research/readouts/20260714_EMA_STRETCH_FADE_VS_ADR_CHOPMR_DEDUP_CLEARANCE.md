# Dedup — EMA Stretch Fade vs ADR / ChopMR / Pivot / ORB shelf

Date: 2026-07-14  
Verdict: `INTAKE_CLEARED / INDEPENDENT`

## Candidate

`HYP-EMA-STRETCH-FADE-M15-001` / `EA_M15EMAStretchFade` — fade when
`|Close−EMA20|/ATR14 ≥ 1.5` on closed M15 `bar[1]` during Europe `[9,17)`,
Mon–Thu, toward EMA.

## Contrast table

| Family | Mechanism | Relation |
|---|---|---|
| ADR Exhaust S680/S681 | Daily ADR% exhaustion MR | Different stretch definition (day range vs EMA) |
| ChopMeanRevert S652 | CI-gated MR | No CI; stretch vs EMA only |
| PivotBounce S196 | Classic floor pivots | No pivot math |
| ORB / PDH / NY / Spark | Range/level breakout | Not breakout |
| TimeFade scanner | Hour-mined displacement | Fixed Europe window a priori; no hour mining |
| ITSM / SB | Pullback / FVG | Different entry anatomy |

## Independence claim

Pure local EMA stretch mean-reversion with frozen threshold 1.50 ATR and
Europe session. Not a rescue of killed ADR/ChopMR books and not ORB/PDH/NY.

## Banned after readout

Do not mine stretch threshold, EMA period, hour/day vetoes, or flip to
trend-follow.
