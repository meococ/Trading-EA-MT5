# Design — Cross-asset / RV greenfield (Round 6)

Date: 2026-07-15
Parent: R1–R5 FX3 H4 ALL_KILL. Nested critic `cursor-grok-4.5-high-fast`.

## Why (vs saturated FX3 H4 path)
- Change **object + surface**, not retune majority/TS/spring/PB/solo/disp/ER/split/halfback.
- Parity / equity-beta / metal-ratio are identity or cross-asset residuals.

## 1 `HYP-EUR-TRIAD-H1-PARITY-RESID-MR-001`
resid=ln(EURGBP)−ln(EURUSD/GBPUSD); z_lb=48; |z|≥2.0;
fade EURGBP; SL=1.5 ATR RR=1.5 hold≤24; 1/day; next open.

## 2 `HYP-USDJPY-H1-NAS100-BETA-RESID-FADE-001`
Frozen β from 2019-01-01..2020-12-31 NAS100→USDJPY OLS (α=-1.39201e-05, β=0.013481, n=3193, R²=0.003364).
resid z_lb=60; |z|≥1.75; fire UTC16;
fade USDJPY; SL=1.2 ATR RR=2.0 hold≤24.
US500 missing on broker → NAS100 Demo H1 proxy (explicit, not VIX).

## 3 `HYP-XAU-XAG-H1-RATIO-ZMR-001`
spread=ln(XAU)−ln(XAG); z_lb=48; |z|≥2.0;
fade via XAGUSD; SL=1.5 ATR RR=1.5 hold≤36; UTC12.

## Model 0
Only PROBE_SURVIVOR. No FX3 H4 path densify.

## Engineering
`rolling_z` uses last lb **finite** observations (NAS/XAG session gaps break
contiguous lb windows on the FX clock). Thresholds unchanged — not densify.
