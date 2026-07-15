# Prereg — HYP-SPARK-CAPACITY-3PD-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Author: local self-research (Owner rebuild/iteration auth; no ChatGPT)

## Identity

- Hypothesis ID: `HYP-SPARK-CAPACITY-3PD-001`
- Parent: `HYP-SPARK-ASIAN-M15-001` (parked PF 1.31 / ~1.25/wk)
- EA: `EA_M15SparkAsian`
- Feature family: `spark_asian_capacity_maxperday`

## Thesis

Raising Spark max-trades-per-day from 2→3 (capacity only; **days unchanged**
Tue–Wed) allows capturing a second independent LDN/NY break when the first
fills early, without densifying Mon/Thu (banned S223). Frozen a priori.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol / TF | USDJPY M15 |
| Window | 2021.01.01–2025.12.31 |
| Model | 0 |
| Deposit | 100000 |
| Control | parked Spark defaults (MaxPerDay=2); baseline `20260714_002821` |
| Challenger | `InpMaxPerDay=3` (all other defaults identical incl. Tue–Wed only) |
| Cost | tester `current`; missing≠0 |

Banned: enabling Mon/Thu/Fri; hour-window mining; body/ATR retune from readout.

## Kill / Park

- Kill: PF < 1.00 or N < 80 or tpw ∉ [1.0, 6.0]
- Park: survives kill, GOAL unmet
- HIT_RESEARCH_BAR: PF>1.30 and tpw∈[2.0,5.0] (not confirmed)
