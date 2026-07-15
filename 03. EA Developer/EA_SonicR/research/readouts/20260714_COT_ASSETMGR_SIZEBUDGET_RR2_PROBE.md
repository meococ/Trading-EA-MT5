# COT Asset Manager Size-Budget RR2 Probe Readout

**Hypothesis:** `HYP-RR2-CFTC-JPY-ASSETMGR-SIZEBUDGET-001`
**Verdict:** `KILLED_AT_OFFLINE_PROBE`
**Notes:** ['stress_fail', 'no_stress_lift_vs_baseline']

Feature: `|net_asset_mgr|` percentile size budget (not lev-money; not skip-gate).

| Set | N | PF | TPW | Net | x1 PF | x1.5 PF | x2 PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 524 | 1.3794 | 2.0099 | 9851.14 | 1.1205 | 1.0134 | 0.9179 |
| Sized | 524 | 1.3756 | 2.0099 | 7860.33 | 1.1183 | 1.0118 | 0.9168 |

Stress lift: `-0.0016`
Histogram: `{'0.50': 87, '0.67': 183, '1.00': 254}`
Panel SHA: `93D69F957A503B38C729F41D2E6B6D714A25EB330147383867C65A5EFC19AE54`
Receipt SHA: `916636B3E4DE7FEA53FC28A5D3375A6A8D0FD6FB88B4DA71E5AF56865E19FFEE`
