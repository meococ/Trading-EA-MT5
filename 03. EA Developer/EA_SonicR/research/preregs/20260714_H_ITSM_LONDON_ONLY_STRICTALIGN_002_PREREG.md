# Prereg — HYP-ITSM-LONDON-ONLY-STRICTALIGN-002

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered`  
Campaign: Owner rebuild (2026-07-14 ~19:09 ICT)  
Parent: `HYP-ITSM-PULLBACK-M15-001` (parked PF 1.16 / ~3.27/wk)  
Author: local structural rebuild — matched a-priori opposite session arm

## Identity

- Hypothesis ID: `HYP-ITSM-LONDON-ONLY-STRICTALIGN-002`
- EA name: `EA_ITSM`
- Path: `03. EA Developer/EA_ITSM/EA_ITSM.mq5`
- Sibling of `HYP-ITSM-NYONLY-STRICTALIGN-002` (frozen same night; not
  post-hoc after NY arm readout)
- Explicitly **not**: day-of-week mining; confluence rescue; hour retune

## Thesis

Structural **London-only** session routing (KZ1 `[09,12)`, `InpUseKZ2=0`)
plus the same a-priori strict EMA alignment gate. Independent session
isolation arm vs NY-only — frozen before either Model 0 result. Tests
whether LDN liquidity alone carries PF while keeping ≥2 tw/w under risk 0.5%
RR 2.0.

## Locked Design

| Item | Frozen value |
|---|---|
| Symbol / TF | USDJPY M15 |
| Decision | closed-bar shift=1 |
| Session | London-only: KZ1=`[09,12)`, `InpUseKZ2=0` |
| Entry quality | `InpStrictAlign=1` |
| Days | Mon–Thu; Fri off |
| Risk / RR | 0.50% / 2.0 |
| Max trades/day | 2 |
| Confluence | all OFF |
| Cost | research-proxy tester `current`; missing ≠ 0 |

Banned: enable confluence; skip days from readout; widen hours after fail.

## Test Plan

- Model 0; 2021.01.01–2025.12.31; Deposit 10000; Leverage 100
- Overrides:
  `InpUseKZ2=0;InpStrictAlign=1;InpRiskPct=0.5;InpRR_Ratio=2.0;InpMaxTradesDay=2;InpTradeFri=0`
- Kill if PF < 1.00 or trades/week outside `[1.5, 6.0]` or N < 80
- Near-miss if PF in `[1.00, 1.30)` with cadence OK
- HIT_RESEARCH_BAR if PF > 1.30 and cadence in `[2.0, 5.0]` (still not confirmed)

## Cost honesty

Tester spread ≠ Real QFSI. No GOAL claim from this screen alone.
