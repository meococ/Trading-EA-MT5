# Offline probes — Iron ore ToT + CNY strength

Date: 2026-07-15  
Status: `OFFLINE_ALL_KILL / NO_MODEL0`  
Iron panel SHA: `85DE1CAC628A0476570CE490B33A8C80911EBEB66A79E1C89DC781A35F9A9A0E`  
CNY panel SHA: `9C173814E2453948D31EEA1F915CAA2B2F9AFBDCFD81781BA7214F1948E2FA48`  
Receipt: `D9CEC93CD1C37CDDF6C2C634DDADCE002C3D0BD116EB5046E5119A603C8CF3AD`

## Objects

| ID | N | PF | tpw | PF@$12 | x1.5 | Verdict | Notes |
|---|---|---|---|---|---|---|---|
| `HYP-AUDUSD-H1-IRONORE-TOT-CONT-001` | 677 | 0.9128 | 2.5953 | 0.8776 | 0.8606 | KILLED_AT_OFFLINE_PROBE | pf_fail,pf12_fail,stress_fail |
| `HYP-AUDUSD-H1-CNYSTRENGTH-DEMAND-CONT-001` | 667 | 1.0323 | 2.557 | 0.9933 | 0.9745 | KILLED_AT_OFFLINE_PROBE | pf_fail,pf12_fail,stress_fail |
| `HYP-BOOK-IRONORE-CNY-APRIORI-001` | 863 | 0.9952 | 3.3083 | 0.9584 | 0.9407 | KILLED_AT_OFFLINE_PROBE | pf_fail,pf12_fail,stress_fail |

## Joint screen

N≥80 ∧ PF≥1.30 ∧ tpw∈[2,5] ∧ PF@$12≥1.30 ∧ x1.5≥1.25 → PROBE_SURVIVOR → Model 0 only.

## Cost

Cost surface still **GAP** (deals~11). Offline stress uses +$12 proxy only. Do not invent.
