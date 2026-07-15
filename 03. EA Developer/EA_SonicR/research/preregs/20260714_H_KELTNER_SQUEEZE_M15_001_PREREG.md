# Prereg — HYP-KELTNER-SQUEEZE-M15-001

Date: 2026-07-14  
State on freeze: `preregistered` (Model 0 screen under Owner MT autonomy)  
Author: local self-research (GPT waived)

## Identity

- Hypothesis ID: `HYP-KELTNER-SQUEEZE-M15-001`
- EA name: `EA_KeltnerSqueeze`
- Path: `03. EA Developer/EA_KeltnerSqueeze/EA_KeltnerSqueeze.mq5`
- Parent / seed: `S654 / EA_KeltnerSqueeze` USDJPY+ M15 Europe h10-14 Mon+Wed+Thu
  (PF **1.15**, 209t / ~8yr). Not S655 Mon+Thu skip-Wed (robustness-killed densify).
- Explicitly **not**: VolExp/VolCluster realized-vol breakout, ChopTrend CI+EMA,
  HourOpen micro-ORB, Spark Asian range, ITSM/SB/USBILL rescues.

## Thesis

BB-inside-KC compression (TTM Squeeze proxy) then first closed `bar[1]` release
with EMA50 alignment continues in Europe `[10,14)`. Seed days Mon+Wed+Thu a
priori (S654 baseline — not mined from tonight). Weekend flat via exit hour 22.
Risk 0.5%.

## Locked Design (zero post-result edit)

| Item | Frozen value |
|---|---|
| Symbol / TF | USDJPY M15 (unsuffixed) |
| Decision bar | closed `bar[1]` only |
| Squeeze | BB(20,2) inside KC(EMA20 ± 1.5×ATR20); min 3 squeeze bars |
| Direction | bar[1] body + close vs EMA50 |
| Session | `[10, 14)`; exit flat hour `22` |
| Days | Mon+Wed+Thu (`SkipTue=1;SkipFri=1`; Mon/Wed/Thu on) |
| Risk | 0.50%; max lot 1.0; max 2 trades/day |
| SL / TP | ATR(14)×1.5 / `1.5R` |
| Magic | 224001 |
| Cost | tester `current` research-proxy; missing ≠ 0 |

Banned after first readout: day/hour vetoes, BB/KC period mining, skip-Wed
rescue (S655 path), symbol switch, adding CI/vol twin filters from this run.

## Test Plan

- Screen: Model 0
- Window: `2021.01.01`–`2025.12.31`
- Deposit / leverage: `10000` / `100`
- Kill if: PF < 1.05 (Owner pass rule), or trades/week outside `[1.0, 6.0]`
  elapsed, or N < 80, or PF < 1.00
- Park if: PF in `[1.05, 1.30)` with cadence OK, **or** PF ≥ 1.30 but cadence < 2.0
- PRIORITY_NEAR_GOAL if: PF ≥ 1.25 **and** trades/week ≥ 1.8 (no tune; matched
  control plan only)
- HIT_RESEARCH_BAR if: PF > 1.30 **and** elapsed cadence in `[2.0, 5.0]`

## Independence

Different signal family from VolExp (BB/KC geometry vs RV-ratio). Europe
session overlap with ChopTrend is coincidental; no CI gate. De-dup vs kill
shelf: not carry/bond/HourOpen/TickVol/InsideBar/GoldJPY/USBILL.

## Cost honesty

Demo/tester `current` ≠ FivePercentOnline-Real QFSI. Not GOAL confirmed.
