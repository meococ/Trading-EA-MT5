# Offline probes — XLK/XLF sector + Cu/Gold ratio

Date: 2026-07-15  
Status: `OFFLINE_ALL_KILL / NO_MODEL0`  
Sector panel SHA: `47911C4420655A8A6A808F82830EEDF40156CD807F2D47DCD50D45DED8B9D15E`  
CuGold panel SHA: `E424ABE51B82E5F50DF421024BB4A672C601E5D36A7CB6DA7157220AECC88DF5`  
Receipt: `7B252F9DA26EFB509605981155146F0EA726074399C64FB4E1F06FF082410799`

## Objects

| ID | N | PF | tpw | PF@$12 | x1.5 | Verdict | Notes |
|---|---|---|---|---|---|---|---|
| `HYP-AUDUSD-H1-XLKXLF-GROWTHLEAD-CONT-001` | 613 | 0.9095 | 2.3499 | 0.871 | 0.8525 | KILLED_AT_OFFLINE_PROBE | pf_fail,pf12_fail,stress_fail |
| `HYP-AUDUSD-H1-CUGOLD-RATIO-CONT-001` | 527 | 0.9793 | 2.0203 | 0.9419 | 0.9239 | KILLED_AT_OFFLINE_PROBE | pf_fail,pf12_fail,stress_fail |
| `HYP-BOOK-SECTOR-CUGOLD-APRIORI-001` | 809 | 0.9344 | 3.1013 | 0.8952 | 0.8763 | KILLED_AT_OFFLINE_PROBE | pf_fail,pf12_fail,stress_fail |

## Joint screen

N≥80 ∧ PF≥1.30 ∧ tpw∈[2,5] ∧ PF@$12≥1.30 ∧ x1.5≥1.25 → PROBE_SURVIVOR → Model 0 only.

## Cost

Cost surface still **GAP** (deals~11). Offline stress uses +$12 proxy only. Do not invent.
