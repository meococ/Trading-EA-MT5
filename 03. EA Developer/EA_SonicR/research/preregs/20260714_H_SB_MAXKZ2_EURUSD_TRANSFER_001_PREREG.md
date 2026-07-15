# Prereg — HYP-SB-MAXKZ2-EURUSD-TRANSFER-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Authority: Owner rebuke ~19:29; quant critic E2 — symbol transfer, not densify

## Identity

- Hypothesis ID: `HYP-SB-MAXKZ2-EURUSD-TRANSFER-001`
- EA: `EA_SilverBullet` (`EA_SilverBullet_v2.mq5`)
- Parent: `HYP-SB-MAXKZ2-DENSITY-002` geometry copied **verbatim** to EURUSD — no USDJPY readout retune

## Thesis

Killzone geometry that cleared research bar on USDJPY may transfer to EURUSD under identical MaxKZ2 overrides. Independent of SparkGBP fail (different family). If transfer fails → PARK/KILL; do not retune KZ from EURUSD losers.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | EURUSD M15 |
| Overrides | `InpFridayFlatHour=21;InpFridayFlatMinute=45;InpMaxTradesPerKZ=2;InpRiskPct=0.5;InpUseWeekendFlat=1` |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |

Banned: changing MaxTradesPerKZ / session / days from EURUSD readout; stacking with USDJPY densify.

## Kill / Park / HIT

Standard research bar. Expect transfer risk (SparkGBP precedent).

## Cost honesty

Tester `current` only.
