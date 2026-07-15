# Prereg — HYP-ADR-CONT-M15-001

Date: 2026-07-14  
State on freeze: `preregistered`

## Identity

- Hypothesis ID: `HYP-ADR-CONT-M15-001`
- EA: `EA_M15ADRCont` → `03. EA Developer/EA_M15ADRCont/EA_M15ADRCont.mq5`
- Seed: opposite of dead ADRExhaust (S680/S681). Not PDH/ORB/ITSM/SB rescue.

## Thesis

Intraday range ≥ 100% of ADR(14) with price at the day's extreme continues expansion rather than mean-reverts. Closed M15 bar[1], D1 EMA50, Mon–Thu, risk 0.5%, max 1/day.

## Locked design

| Item | Value |
|---|---|
| Symbol/TF | USDJPY M15 |
| ADR | period 14; threshold **1.00**; extreme band **0.15** of day range |
| Body | ≥0.40 |
| HTF | D1 EMA50 on |
| Window | `[10,17)`; flat 21; Mon–Thu |
| Risk | 0.5%; SL 1.0×ATR; TP 1.5R; max hold 32 |
| Magic | 880942 |
| Cost | tester `current`; missing ≠ 0 |

## Test plan

Model 0, 2021.01.01–2025.12.31, Deposit 10000.  
Kill: tpw∉[1.0,6.0] or PF<1.00 or N<80.  
Park: PF∈[1.00,1.30) cadence OK, or PF≥1.30 cadence<2.  
HIT_RESEARCH_BAR: PF>1.30 and tpw∈[2.0,5.0] (still unconfirmed).

## De-dup / probe

`readouts/20260714_ADR_CONT_VS_ADREXHAUST_DEDUP_CLEARANCE.md`  
`readouts/20260714_HYP_ADR_CONT_M15_001_PROBE.md`
