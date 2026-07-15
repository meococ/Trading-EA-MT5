# Offline probes — SB/RR2 quality-thickness (W27 child)

Date: 2026-07-15  
Status: `OFFLINE_ALL_KILL / NO_MODEL0`  
Receipt: `0816D9AC4686FA8D047F1BE393997EE03D2215979129C7AD807EBC8498533D26`  
Parent run: `20260714_194548`

## Objects

| ID | N | PF | tpw | PF@$12 | x1.5 | Verdict | Notes |
|---|---|---|---|---|---|---|---|
| `HYP-SB-MAXKZ2-RR2-FRICTION-001` | 524 | 1.3794 | 2.0099 | 1.1205 | 1.0134 | KILLED_AT_OFFLINE_PROBE | pf12_fail,stress_fail |
| `HYP-SB-RR2-QUALITY-THICK-DISP-001` | 52 | 1.0429 | 0.1995 | 0.8737 | 0.8017 | KILLED_AT_OFFLINE_PROBE | n_fail,pf_fail,cadence_fail,pf12_fail,stress_fail |

## Funnel
Parent N=524 → quality keep=52 drop=472  
Gate: body/ATR≥0.55, body/range≥0.75, close_frac≥0.67

## Joint screen
N≥80 ∧ PF≥1.30 ∧ tpw∈[2,5] ∧ PF@$12≥1.30 ∧ x1.5≥1.25 → PROBE_SURVIVOR → Model 0 only.
