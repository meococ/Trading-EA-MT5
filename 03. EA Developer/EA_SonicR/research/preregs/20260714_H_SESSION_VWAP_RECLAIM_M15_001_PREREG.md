# Prereg — HYP-SESSION-VWAP-RECLAIM-M15-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Authority: Owner rebuke — continue R&D; deferred trader P2 from prior wave

## Identity

- Hypothesis ID: `HYP-SESSION-VWAP-RECLAIM-M15-001`
- EA: `EA_M15SessionVWAPReclaim`
- Path: `03. EA Developer/EA_M15SessionVWAPReclaim/EA_M15SessionVWAPReclaim.mq5`

## Thesis

Cumulative session VWAP from server hour 7; when price stretches ≥0.80·ATR
away then closed-bar[1] reclaims through VWAP, fade the stretch (mean-revert
to value). London–NY trade window. Independent of SB KZ, ORB, ITSM FVG,
AsianSweep reclaim.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY M15 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| VWAP reset | hour ≥ 7 |
| Stretch | 0.80 ATR; reclaim buf 0.05 ATR |
| Session | trade [8,18); flat 21; Mon–Thu |
| Risk | 0.50%; max 2/day; TP 1.5R; SL 1.5 ATR |
| Magic | 880971 |
| Overrides | (none — defaults frozen) |

## De-dup

- Not SB densify / RR friction child
- Not LondonORB / LORBA / FailedORB
- Not ITSM pullback / Engulf / ASR (killed N=0)
- Not Scalp005 SessionVWAP resurrect (source absent; new closed-bar contract)

## Kill / Park / HIT

| Gate | Rule |
|---|---|
| KILL | PF < 1.00 or tpw outside [1.0, 6.0] or N < 80 |
| PARK | Survives kill but PF ≤ 1.30 or tpw outside [2, 5] |
| HIT | PF > 1.30 ∧ tpw ∈ [2, 5] tester `current` |

## Cost honesty

`UNVERIFIED_TESTER_DEFAULT`. Missing cost ≠ 0. Not confirmed / not GOAL.

## Banned

- Mining stretch/hour/day from readout
- Claiming GOAL from Demo
- Retuning StretchATR from Model 0 (needs new ID)
