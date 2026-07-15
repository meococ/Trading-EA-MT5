# Design — Round 9 yen-synth / overnight-ratio / tickvol

Date: 2026-07-15
Parent: Round8 ALL_KILL. Nested critic `cursor-grok-4.5-high-fast`.

## Why these could break thick∩cadence
- **Yen-synth identity resid:** Microstructure no-arb gaps on EURUSD vs
  EURJPY/USDJPY recur often enough for cadence; fade is structurally thick
  when cross-rate dislocation snaps (≠ R6 EURGBP parity-z, ≠ R8 OLS-β).
- **Overnight-ratio cont:** 1×/day×FX3 natural cadence; overnight-dominant
  days often carry informational thickness into London (≠ Asia H/L break).
- **Tickvol climax fade:** Cadence from volume spikes; thickness only if
  climax mean-reverts after +$12 (cost-fragile; probe to kill fast).

## 1 `HYP-EURUSD-H1-YENCROSS-SYNTH-RESID-FADE-001`
spread=ln(EURUSD)−(ln(EURJPY)−ln(USDJPY)); z_lb=60; |z|≥1.75;
fire UTC12; fade EURUSD; SL=1.2 ATR RR=2.0 hold≤24.

## 2 `HYP-FX3-H1-OVERNIGHT-RATIO-CONT-001`
|ON|/(|ON|+|ID|)≥0.65; |ON|≥0.35 ATR; fire UTC8;
continue ON dir; FX3 first-eligible; SL=1.2 ATR RR=2.0 hold≤16.

## 3 `HYP-FX3-H1-TICKVOL-CLIMAX-FADE-001`
tick_volume z_lb=60; z≥2.5; |body|≥1.0 ATR;
fire UTC14; fade; SL=1.2 ATR RR=1.5 hold≤12.

## Model 0
Only PROBE_SURVIVOR. No R1–R8 densify.
