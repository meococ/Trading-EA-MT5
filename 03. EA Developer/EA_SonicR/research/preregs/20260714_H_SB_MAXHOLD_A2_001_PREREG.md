# Prereg — HYP-SB-MAXHOLD-A2-001

Date: 2026-07-14  
State: `preregistered`  
Parent: parked `HYP-SB-WEEKEND-FLAT-001` / A1 `20260714_002505`  
Family: `silverbullet_management` · budget used this campaign after A1: **1/2**

## Thesis

Cap SilverBullet position age at **30 hours** (a priori input default) to cut
overnight/weekend-adjacent tails without changing ICT KZ+FVG entries. Stacked
on frozen A1 weekend-flat (not a combined V1 hyp — separate child ID).

## Offline probe

`preflight/sb_maxhold_a2/20260714_SB_MAXHOLD_A2_OFFLINE_PROBE.json`  
Verdict `PROBE_PASS_TO_MODEL0_NONDESTRUCTIVE_PROXY` (8/520 clipped; linear-path
delta ≈ −2.5% net). Not tick-true — Model 0 required.

## Locked design

| Item | Value |
|---|---|
| EA | `EA_SilverBullet` → `EA_SilverBullet_v2.mq5` |
| Symbol/TF | USDJPY M15 |
| Window | 2021.01.01–2025.12.31 |
| Model / Deposit | 0 / 100000 |
| Control | A1 parked metrics as reference (`20260714_002505`) — this run is **challenger-only** management stack |
| Overrides (sorted) | `InpFridayFlatHour=21;InpFridayFlatMinute=45;InpMaxHoldHours=30;InpUseMaxHold=1;InpUseWeekendFlat=1` |
| Cost | tester `current`; missing ≠ 0 |

## Gates

- Kill if PF < 1.00 or N < 80 or tpw ∉ [1.0, 6.0]
- Non-destructive vs A1: PF ≥ A1−0.05 and net not worse than −10% of A1 (research bar)
- HIT_RESEARCH if PF>1.30 and tpw∈[2.0,5.0] (still unconfirmed)
- **Banned:** Friday cutoff retune, NYPM, SkipFriday=0, trail ON

## Team critic memo (pre-run)

- **Trader:** Max-hold is exposure hygiene, not a new setup — won't create cadence.
- **Quant:** Offline clip rate 1.5% → expect near-null; Model 0 validates path risk.
- **MQL5:** `InpUseMaxHold` already implemented closed-time check — no source rebuild.
