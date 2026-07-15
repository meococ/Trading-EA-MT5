# Offline probes — ECB BS primary + Brent importer ToT

Date: 2026-07-15  
Status: `OFFLINE_ALL_KILL / NO_MODEL0`  
ECB panel SHA: `FF4F0DF35797E9E9B0B6C5DFA0F70DF28DA62B75FACE6C0D1CB905E0816C0FC4`  
Brent panel SHA: `DA7C6417D263997DDE9D5F76F0A4239FF7E6354AEE7617F90D2815ABFBC45454`  
Receipt: `3A0DA01E6F71EFCA298FE9073F5827B27C0F870F2BE9DDF07ECD93B13099289C`

## Objects

| ID | N | PF | tpw | x1.5 | Verdict | Notes |
|---|---|---|---|---|---|---|
| `HYP-EURUSD-H1-ECB-BS-EXPAND-DISPLACE-001` | 463 | 0.9274 | 1.7749 | 0.8737 | KILLED_AT_OFFLINE_PROBE | pf_fail,stress_fail |
| `HYP-EURUSD-H1-ECB-BS-CONTRACT-DISPLACE-001` | 456 | 0.9033 | 1.7481 | 0.8511 | KILLED_AT_OFFLINE_PROBE | pf_fail,stress_fail |
| `HYP-EURUSD-H1-BRENT-IMPORTER-TOT-001` | 579 | 1.0303 | 2.2196 | 0.976 | KILLED_AT_OFFLINE_PROBE | pf_fail,stress_fail |

## Joint screen

N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15 → PROBE_SURVIVOR → Model 0 only.

## Cost

Cost surface still **GAP** (no invent). Offline stress uses +$12 proxy only.
