# Design — CHF-risk + AUD-com3 + ADR greenfield (Round 7)

Date: 2026-07-15
Parent: Round6 ALL_KILL. Nested critic `cursor-grok-4.5-high-fast`.

## Why
- Outside Round6 parity / NAS equity-β / metal-ratio densify.
- Outside FX3 H4 R1–R5 path saturation.
- W1 / M15 remain parked (de-dup not clear).

## 1 `HYP-USDCHF-H1-FXRISK-BASKET-RESID-FADE-001`
risk_on=mean(r_EURUSD,r_GBPUSD,−r_USDJPY);
Frozen β 2019-01-01..2020-12-31 (α=-4.83048e-06, β=-0.77113, n=12421, R²=0.497748).
resid z_lb=60; |z|≥1.75; fire UTC12;
fade USDCHF; SL=1.2 ATR RR=2.0 hold≤24; 1/day.
FX-only risk basket — **not** NAS100 equity-β densify.

## 2 `HYP-AUD-COM3-H1-BASKET-RESID-MR-001`
spread=ln(AUDUSD)−0.5ln(NZDUSD)−0.5ln(1/USDCAD);
z_lb=48; |z|≥2.0; fire UTC0;
fade AUDUSD; SL=1.5 ATR RR=1.5 hold≤36; 1/day.
Ternary commodity FX — **not** AUDNZD 2-leg ZMR / AONIA/CORRA.

## 3 `HYP-FX3-H1-ADR-EXHAUST-FADE-001`
By UTC8: day range ≥ 0.9×ATR_D1(prior) and close in outer third;
fade first eligible of EURUSD→GBPUSD→USDJPY; SL=1.5 ATR_H1 RR=1.5 hold≤16; 1/day book.
≠ thin3 jump / consec3 / H4 path / weekend-gap.

## Model 0
Only PROBE_SURVIVOR. No triad / NAS β / metal / H4 path densify.
