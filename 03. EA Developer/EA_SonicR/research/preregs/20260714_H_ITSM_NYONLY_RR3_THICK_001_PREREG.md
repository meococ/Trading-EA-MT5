# Prereg — HYP-ITSM-NYONLY-RR3-THICK-001

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered`  
Authority: Owner post-cost rebuild; prefer ITSM cadence-OK family  
Parent: `HYP-ITSM-NYONLY-STRICTALIGN-002` (parked PF 1.22 / ~2.07/wk)

## Identity

- Hypothesis ID: `HYP-ITSM-NYONLY-RR3-THICK-001`
- EA: `EA_ITSM` (`EA_ITSM.mq5`)
- Structural child: keep NY-only + StrictAlign; stretch TP **RR 2.0 → 3.0**
  a priori for thicker winner dollars after haircut
- Explicitly **not**: T10 confluence; hour/day mine; London flip; MaxKZ densify

## Thesis

NY-only StrictAlign already has GOAL-band cadence (~2.07/wk) but thin PF
(1.22). MaxKZ2 failed partial-Real cost stress at ~$2.31 P50. Child freezes
RR=3.0 (same thick-edge doctrine as H4 NR7 wave) without changing session
geometry — aim: higher gross expectancy/trade so post-haircut PF can clear
1.30 / x1.5≥1.25 under tester caveat.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY M15 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 10000 |
| Model | 0 |
| Session | KZ1=`[15,18)`, `InpUseKZ2=0`, `InpStrictAlign=1` |
| RR / Risk | **3.0** / 0.50% |
| Max trades/day | 2 |
| Days | Mon–Thu; Fri off |
| Overrides | `InpKZ1_StartH=15;InpKZ1_EndH=18;InpUseKZ2=0;InpStrictAlign=1;InpRiskPct=0.5;InpRR_Ratio=3.0;InpMaxTradesDay=2;InpTradeFri=0` |

## Kill / Park / HIT

Same research screen as parent. Cadence kill if tpw < 1.5 after RR stretch.

## Cost honesty

Tester `current` only. Never claim verified Real cost / GOAL.
