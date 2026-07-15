# Offline probes — London–NY overlap EUR/GBP

Date: 2026-07-15
Receipt SHA256: `EEF617F060532C4095FDBC38548690B0C72CF88C2D949077B24CC1F941FD9E27`
Lane: `EXO_FRED_DISPLACE_SPAM_PAUSED`

| ID | N | PF | tpw | x1.5 | Verdict | Notes |
|---|---:|---:|---:|---:|---|---|
| `HYP-EURUSD-H1-LONDON-IMBAL-NY-FADE-001` | 109 | 0.9636 | 0.4181 | 0.8896 | **KILLED_AT_OFFLINE_PROBE** | cadence_fail,pf_fail,stress_fail |
| `HYP-GBPUSD-H1-LONDON-COIL-NY-BREAK-001` | 308 | 1.0278 | 1.1814 | 0.929 | **KILLED_AT_OFFLINE_PROBE** | cadence_fail,pf_fail,stress_fail |
| `HYP-GBPUSD-H1-EURUSD-LEAD-OVERLAP-CATCHUP-001` | 30 | 0.769 | 0.1151 | 0.7267 | **KILLED_AT_OFFLINE_PROBE** | n_fail,cadence_fail,pf_fail,stress_fail |

Survivor bar: N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15.
Cost proxy only — not research-grade freeze.

