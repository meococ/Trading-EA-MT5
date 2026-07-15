# Design — Round 8 corr / yen-cross / Parkinson greenfield

Date: 2026-07-15
Parent: Unpark + R1–R7 ALL_KILL. Nested critic `cursor-grok-4.5-high-fast`.

## Why these could break thick∩cadence
- **Yen-cross β-resid:** H1 |z| can print 2–5 tpw while EURJPY decoupling
  from USDJPY is a distinct yen-risk RV (not equity NAS-β, not CHF basket).
  Thickness: RR=2 fade after structural residual extremes.
- **Corr-break recouple:** Policy/risk de-link episodes are quality events
  (thick PF potential) that still recur on H1 without needing H4 path spam.
  Mechanism = rolling corr + divergence — **not** EURGBP parity residual z.
- **Parkinson compress→expand:** Cadence-friendly expansion after true
  HL-RV squeeze; edge only if squeeze filters continuation better than
  raw TSMOM/ER (which died post-cost).

## 1 `HYP-EURJPY-H1-USDJPY-BETA-RESID-FADE-001`
Frozen β 2019-01-01..2020-12-31 (α=3.81949e-06, β=0.643058, n=12421, R²=0.359421).
resid z_lb=60; |z|≥1.75; fire UTC12;
fade EURJPY; SL=1.2 ATR RR=2.0 hold≤24; 1/day.
Yen-cross FX RV — **not** NAS100 equity-β densify / CHF risk-basket densify.

## 2 `HYP-EURGBP-H1-CORR-BREAK-RECOUPLE-001`
corr_lb=48; corr<0.35; |div|_12≥1.5 ATR;
fade stronger USD-leg (EURUSD or GBPUSD); fire UTC13;
SL=1.2 ATR RR=2.0 hold≤24; 1/day.
≠ Round6 triad parity-z on EURGBP; ≠ LNY EUR-lead catchup.

## 3 `HYP-FX3-H1-PARKINSON-COMPRESS-EXPAND-CONT-001`
Parkinson mean12 ≤ p25 for ≥6 bars;
then bar range ≥1.2×ATR → continue; fire UTC8;
FX3 first-eligible; SL=1.2 ATR RR=2.0 hold≤16; 1/day.
≠ NR7 single-bar densify; ≠ R7 ADR exhaust fade; ≠ D1 volregime.

## Model 0
Only PROBE_SURVIVOR. No unpark/R1–R7 densify.
