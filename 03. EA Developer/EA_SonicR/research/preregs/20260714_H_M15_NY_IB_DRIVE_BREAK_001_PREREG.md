# Prereg — HYP-M15-NY-IB-DRIVE-BREAK-001

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered`  
Authority: Owner Discovery Wave5 — joint thick + cadence (NY session microstructure)  
GPT: waived

## Identity

- Hypothesis ID: `HYP-M15-NY-IB-DRIVE-BREAK-001`
- EA: `EA_M15NYIBDriveBreak`
- Path: `03. EA Developer/EA_M15NYIBDriveBreak/EA_M15NYIBDriveBreak.mq5`
- Explicitly **not**: London IB hour densify; NYOpenDrive impulse rescue; DualWin

## Thesis

NY session **Initial Balance** [13,14) on USDJPY M15 is an independent
microstructure object from London IB. Closed-M15 break in [14,17) with IB-width
and body quality + **RR=2.5** targets joint cadence (M15 NY window) and thicker
post-cost expectancy than thin-overlap spam.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY M15 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| NY IB | server [13,14) lock high/low |
| Break window | [14,17); IB width≥0.40 ATR; body≥0.35 ATR |
| Days | Mon–Thu; Fri off |
| Risk / RR | 0.50% / 2.5 |
| SL | opposite IB extreme ± 0.10×ATR |
| Max/day | 2 |
| Flat | hour≥21 / weekend; max hold 32 M15 |
| Magic | 880997 |
| Overrides | (none) |

## Kill / Park / HIT

Same Wave5 screen.

## Cost honesty

`UNVERIFIED_TESTER_DEFAULT`. Not Real QFSI. Not GOAL.

## Independence

`readouts/20260714_DISCOVERY_WAVE5_DEDUP_CLEARANCE.md`
