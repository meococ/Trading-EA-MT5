# Prereg — HYP-SPARK-ASIAN-GBPUSD-001

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered`  
Campaign: Owner rebuild (2026-07-14 evening)  
Parent: `HYP-SPARK-ASIAN-M15-001` (parked USDJPY PF 1.31 / ~1.25/wk)  
Author: local structural symbol-transfer — not day densify of USDJPY

## Identity

- Hypothesis ID: `HYP-SPARK-ASIAN-GBPUSD-001`
- EA name: `EA_M15SparkAsian` (pinned; symbol + day-contract overrides)
- Path: `03. EA Developer/EA_M15SparkAsian/EA_M15SparkAsian.mq5`
- Seed: `S107 / EA_Spark v1.4 GBPUSD` baked config (historical PF~1.35, ~30/yr)
- Explicitly **not**: Mon–Thu densify of USDJPY (S223 banned); hour-11 mine;
  capacity MaxPerDay rescue of parked USDJPY readout; E8-suffix claim

## Thesis

Asian-range → LDN/NY breakout edge transfers to **GBPUSD** under the S107
a-priori **Wed–Thu** day contract (independent of S111 Tue–Wed USDJPY). Adds a
second symbol sleeve for cadence toward GOAL 2–5/wk without expanding killed
USDJPY day filters. Closed-bar[1], risk 0.5%, TP 1.5R retained.

## Locked Design

| Item | Frozen value |
|---|---|
| Symbol / TF | **GBPUSD** M15 |
| Decision | closed-bar shift=1 |
| Asian range | `[0,8)` lock; buffer ATR×0.15; body/range≥0.35 |
| Sessions | LDN `[9,13)` + NY `[15,18)`; flat 21 |
| Days | **Wed+Thu only** (S107); Mon/Tue/Fri off |
| Risk / TP | 0.50% / 1.5R |
| Max trades/day | 2 |
| Magic | 880931 (distinct from USDJPY 880930) |
| Cost | research-proxy tester `current`; missing ≠ 0 |
| Deposit | 100000 |

Banned: enable Mon/Tue from this readout; retune Asian/LDN/NY hours; body/ATR
threshold mine; claim confirmed without Real QFSI.

## Test Plan

- Model 0; 2021.01.01–2025.12.31; Deposit 100000; Leverage 100
- Overrides:
  `InpMagic=880931;InpTradeMon=0;InpTradeTue=0;InpTradeWed=1;InpTradeThu=1;InpTradeFri=0;InpRiskPct=0.5;InpTPRatio=1.5;InpMaxPerDay=2`
- Kill if PF < 1.00 or trades/week outside `[1.0, 6.0]` or N < 80
- Near-miss if PF in `[1.00, 1.30)` with any cadence, or PF≥1.30 with tpw<2.0
- HIT_RESEARCH_BAR if PF > 1.30 and cadence in `[2.0, 5.0]` (still not confirmed)

## Cost honesty

Tester spread ≠ Real QFSI. Historical S107 Demo edge ≠ current MetaQuotes
spread; E8 prior kill (S553/S572) is broker-cost warning only — does not ban
this Demo research screen.
