# Prereg — HYP-ITSM-PULLBACK-M15-001

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered` → Model 0 **`parked`** (`20260714_003635`)  
Contract: `preflight/itsm_pullback_m15/contracts/20260714_HYP_ITSM_PULLBACK_M15_001_CONTRACT_RECEIPT.json`  
Overrides: `InpRiskPct=0.5;InpRR_Ratio=2.0;InpMaxTradesDay=2;InpTradeFri=0`  
Author: local self-research after Spark Asian park (no ChatGPT)

## Identity

- Hypothesis ID: `HYP-ITSM-PULLBACK-M15-001`
- EA name: `EA_ITSM` (pinned existing closed-bar Sonic R zone pullback)
- Path: `03. EA Developer/EA_ITSM/EA_ITSM.mq5`
- Parent / near-miss seed: `S509 / EA_ITSM` USDJPY NY-only RR2.0 (PF ~1.22, ~122/yr ≈ 2.35/week). Independent EMA-wave pullback — **not** Spark/SB/IB/Chop/VolExp/GoldJPY/TickVol/HourOpen/USBILL rescue.
- Explicitly **not**: T10 ADX/H4/skip-Tue densification mining (S510–S543); day vetoes from this readout.

## Thesis

Sonic R EMA zone (5/13/34/89) pullback continuation on closed `bar[1]` during London+NY kill zones has seed cadence already inside GOAL 2–5/week. Risk 0.5% and RR 2.0 are a priori (S509 RR; tonight risk standard). Mon–Thu weekend-flat. Confluence filters remain OFF (defaults) — no post-hoc ADX/MACD/H4 enable from killed T10 variants.

## Locked Design

| Item | Frozen value |
|---|---|
| Symbol / TF | USDJPY M15 |
| Decision | closed-bar shift=1 (EA contract) |
| Sessions | KZ1 `[09,12)` + KZ2 `[15,18)` (both on) |
| Days | Mon–Thu; Fri off |
| Risk | 0.50% |
| RR | 2.0 |
| Max trades/day | 2 |
| Confluence | all OFF (InpUseMACD/RSI/ADX/HTF/ZoneWidth/Vol/Slope/Trail = false) |
| Cost | research-proxy tester `current`; missing ≠ 0 |

Banned: enable confluence from losers; skip-Tue; hour mining; Spark/SB retune.

## Test Plan

- Model 0; 2021.01.01–2025.12.31; Deposit 10000; Leverage 100
- Kill if PF < 1.00 or trades/week outside `[1.5, 6.0]` or N < 80
- Near-miss if PF in `[1.00, 1.30)` with cadence OK
- HIT_RESEARCH_BAR if PF > 1.30 and cadence in `[2.0, 5.0]` (still not confirmed)

## Cost honesty

Tester spread ≠ Real QFSI. No GOAL claim from this screen alone.
