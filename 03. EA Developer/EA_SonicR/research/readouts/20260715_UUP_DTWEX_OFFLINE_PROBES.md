# Offline probes — UUP TW-USD + DTWEXBGS dollar TWI

Date: 2026-07-15  
Status: `OFFLINE_ALL_KILL / NO_MODEL0`  
Panels:
- `uup`: `5F0D2E65449FA54AB71D617AB46055207C84B0F89294F1BCB46FB376B13C41FE`
- `dtwex`: `FE0A8C77F3BDAD03B2011FFBEE8A072B3BE2786587761832BA4D887005B75F0A`
Receipt: `D74E8876CB324EBFD8A58625A580D2D00020A87D05AEEE72CF2B46F45A20AE22`

## Objects

| ID | N | PF | tpw | PF@$12 | x1.5 | Verdict | Notes |
|---|---|---|---|---|---|---|---|
| `HYP-AUDUSD-H1-UUP-TWUSD-STRENGTH-001` | 628 | 0.9675 | 2.4074 | 0.9305 | 0.9127 | KILLED_AT_OFFLINE_PROBE | pf_fail,pf12_fail,stress_fail |
| `HYP-AUDUSD-H1-DTWEXBGS-TWI-STRENGTH-001` | 603 | 1.0149 | 2.3116 | 0.978 | 0.9601 | KILLED_AT_OFFLINE_PROBE | pf_fail,pf12_fail,stress_fail |
| `HYP-BOOK-UUP-DTWEX-APRIORI-001` | 748 | 1.0125 | 2.8675 | 0.9751 | 0.9571 | KILLED_AT_OFFLINE_PROBE | pf_fail,pf12_fail,stress_fail |

## Joint screen

N≥80 ∧ PF≥1.30 ∧ tpw∈[2,5] ∧ PF@$12≥1.30 ∧ x1.5≥1.25 → PROBE_SURVIVOR → Model 0 only.

## Cost

Cost surface still **GAP** (deals~11). Offline stress uses +$12 proxy only. Do not invent.
