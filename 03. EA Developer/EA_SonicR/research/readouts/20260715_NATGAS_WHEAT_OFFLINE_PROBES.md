# Offline probes — Natgas LNG + Wheat ag ToT

Date: 2026-07-15  
Status: `OFFLINE_ALL_KILL / NO_MODEL0`  
NG panel SHA: `3334E6BA1D300893BF0B27D308E3967948C08870FDA6B6646B986DC8CCF7D4F9`  
ZW panel SHA: `C4B7CFB945A9CE80E5A85B139E92D7C27CF485D0F1173DDBA12E617CC9AC4DD5`  
Receipt: `D88BA9DAFBC207B28E891A384E4501A5C281855EEE695AF1A805E5447325580F`

## Objects

| ID | N | PF | tpw | PF@$12 | x1.5 | Verdict | Notes |
|---|---|---|---|---|---|---|---|
| `HYP-AUDUSD-H1-NATGAS-LNG-TOT-CONT-001` | 613 | 0.9213 | 2.3499 | 0.882 | 0.8631 | KILLED_AT_OFFLINE_PROBE | pf_fail,pf12_fail,stress_fail |
| `HYP-AUDUSD-H1-WHEAT-AG-TOT-CONT-001` | 551 | 0.98 | 2.1123 | 0.9407 | 0.9219 | KILLED_AT_OFFLINE_PROBE | pf_fail,pf12_fail,stress_fail |
| `HYP-BOOK-NATGAS-WHEAT-APRIORI-001` | 806 | 0.9936 | 3.0898 | 0.9547 | 0.936 | KILLED_AT_OFFLINE_PROBE | pf_fail,pf12_fail,stress_fail |

## Joint screen

N≥80 ∧ PF≥1.30 ∧ tpw∈[2,5] ∧ PF@$12≥1.30 ∧ x1.5≥1.25 → PROBE_SURVIVOR → Model 0 only.

## Cost

Cost surface still **GAP** (deals~11). Offline stress uses +$12 proxy only. Do not invent.
