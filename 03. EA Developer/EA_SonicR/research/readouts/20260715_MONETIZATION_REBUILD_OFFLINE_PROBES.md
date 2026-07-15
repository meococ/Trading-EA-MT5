# Monetization rebuild — offline probes

Receipt: `373F18BCC434C17E39CB14D5C10D5EE6F50E6C7ED468E5E81FD3E0C2A696B45E`
Baseline: N=524 PF=1.3794 tpw=2.0099 x1.5=1.0134
Method: outcome-faithful (OHLC path voided)

| ID | N | PF | tpw | x1.5 | lift | Verdict | notes |
|---|---:|---:|---:|---:|---:|---|---|
| `HYP-RR2-EXIT-SCALEOUT-1R50-RUN2R-001` | 524 | 1.0366 | 2.0099 | 0.7296 | -0.2838 | `KILLED_AT_OFFLINE_PROBE` | pf_fail,stress_fail,no_stress_lift_vs_baseline |
| `HYP-RR2-EXIT-TIMEBOX-SCALPLOCK-2H-001` | 524 | 0.8081 | 2.0099 | 0.5405 | -0.4729 | `KILLED_AT_OFFLINE_PROBE` | pf_fail,stress_fail,no_stress_lift_vs_baseline |
| `HYP-RR2-VOLREGIME-RMULT-H1ATR-001` | 524 | 1.3349 | 2.0099 | 0.9766 | -0.0368 | `KILLED_AT_OFFLINE_PROBE` | stress_fail,no_stress_lift_vs_baseline |

Model 0: **WITHHELD**

