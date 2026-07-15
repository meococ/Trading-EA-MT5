# Prereg — HYP-ITSM-NYONLY-STRICTALIGN-002

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered`  
Campaign: Owner rebuild (2026-07-14 ~19:09 ICT)  
Parent: `HYP-ITSM-PULLBACK-M15-001` (parked PF 1.16 / ~3.27/wk)  
Author: local structural rebuild — not readout mining

## Identity

- Hypothesis ID: `HYP-ITSM-NYONLY-STRICTALIGN-002`
- EA name: `EA_ITSM` (pinned existing; override-only structural child)
- Path: `03. EA Developer/EA_ITSM/EA_ITSM.mq5`
- Parent / seed: parked LDN+NY densifier; S509 NY-only PF~1.22 a priori
- Explicitly **not**: T10 confluence enable; skip-Tue; hour/day mining from
  parent readout; RR/risk retune from killed variants

## Thesis

Parent cadence is strong (~3.27/wk) but PF weak (1.16). Structural rebuild
isolates the **NY kill-zone only** (KZ1 remapped to [15,18), KZ2 off) —
matching the S509 seed session contract — and requires **strict 4-EMA
alignment** (`InpStrictAlign=1`) as an a-priori entry-quality gate (boolean
design already in EA; not a mined numeric threshold). Goal: lift PF toward
>1.30 while keeping elapsed cadence ≥2.0/wk.

## Locked Design

| Item | Frozen value |
|---|---|
| Symbol / TF | USDJPY M15 |
| Decision | closed-bar shift=1 |
| Session | NY-only: KZ1=`[15,18)`, `InpUseKZ2=0` |
| Entry quality | `InpStrictAlign=1` |
| Days | Mon–Thu; Fri off |
| Risk / RR | 0.50% / 2.0 |
| Max trades/day | 2 |
| Confluence | all OFF |
| Cost | research-proxy tester `current`; missing ≠ 0 |

Banned: enable MACD/ADX/H4 from losers; remine hours from parent PF; flip to
London after seeing this result without a new child ID.

## Test Plan

- Model 0; 2021.01.01–2025.12.31; Deposit 10000; Leverage 100
- Overrides:
  `InpKZ1_StartH=15;InpKZ1_EndH=18;InpUseKZ2=0;InpStrictAlign=1;InpRiskPct=0.5;InpRR_Ratio=2.0;InpMaxTradesDay=2;InpTradeFri=0`
- Kill if PF < 1.00 or trades/week outside `[1.5, 6.0]` or N < 80
- Near-miss if PF in `[1.00, 1.30)` with cadence OK
- HIT_RESEARCH_BAR if PF > 1.30 and cadence in `[2.0, 5.0]` (still not confirmed)

## Cost honesty

Tester spread ≠ Real QFSI. No GOAL claim from this screen alone.
