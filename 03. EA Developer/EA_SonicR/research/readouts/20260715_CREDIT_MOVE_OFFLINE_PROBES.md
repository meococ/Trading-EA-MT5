# Offline probes — Credit HYG/LQD + MOVE bond-vol

Date: 2026-07-15  
Status: `OFFLINE_ALL_KILL / NO_MODEL0`  
Credit panel SHA: `A2BEB287BECC64FCD8930E0CBF52AB01F8A367F2615AEBBF766953AD315B8982`  
MOVE panel SHA: `7C00C1C616CD536FBEE4E93CD9820CD592173360F4D21F3D03B060EF0C7FC19A`  
Receipt: `9ACBB3D88F276ACBDC68E69B8268BC4A193B4B25D6590F1186EC116A0D2250AB`

## Objects

| ID | N | PF | tpw | PF@$12 | x1.5 | Verdict | Notes |
|---|---|---|---|---|---|---|---|
| `HYP-AUDUSD-H1-HYGLQD-CREDIT-CONT-001` | 633 | 0.9402 | 2.4266 | 0.904 | 0.8866 | KILLED_AT_OFFLINE_PROBE | pf_fail,pf12_fail,stress_fail |
| `HYP-AUDUSD-H1-MOVE-BONDVOL-RISKOFF-001` | 533 | 0.8692 | 2.0433 | 0.8321 | 0.8143 | KILLED_AT_OFFLINE_PROBE | pf_fail,pf12_fail,stress_fail |
| `HYP-BOOK-CREDIT-MOVE-APRIORI-001` | 819 | 0.8914 | 3.1396 | 0.8537 | 0.8356 | KILLED_AT_OFFLINE_PROBE | pf_fail,pf12_fail,stress_fail |

## Joint screen

N≥80 ∧ PF≥1.30 ∧ tpw∈[2,5] ∧ PF@$12≥1.30 ∧ x1.5≥1.25 → PROBE_SURVIVOR → Model 0 only.

## Cost

Cost surface still **GAP** (deals~11). Offline stress uses +$12 proxy only. Do not invent.
