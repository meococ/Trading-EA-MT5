# Structural rebuild offline probes V5

Generated: 2026-07-14T16:13:13.267259Z
Authority: Owner GOAL push; offline-first; GPT waived
Status: **offline-first**; Model 0 only if `PROBE_SURVIVOR`

De-dup: `20260714_STRUCTURAL_V5_DEDUP_CLEARANCE.md`

| ID | N | PF | tpw | +$12 x1.5 PF | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-H1-ORDERBLOCK-MITIGATION-001` | 412 | 0.985 | 1.58 | 0.931 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-D1-INSIDE-H4-BREAK-001` | 369 | 0.987 | 1.41 | 0.900 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-H1-LONDON-DRIVE-FAIL-FADE-001` | 298 | 0.915 | 1.14 | 0.852 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-M15-ASIA-BREAK-FAIL-FADE-001` | 102 | 0.923 | 0.39 | 0.871 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-H4-BREAK-PAUSE-BREAK-001` | 31 | 0.635 | 0.12 | 0.589 | **KILLED_AT_OFFLINE_PROBE** |

Offline survivors: `[]`
Any Model 0 authorized: `False`
Receipt SHA: `59C951DFA93BA7AF5BBD50ECA427A107DC4C8982D81025CAA3240AA8BB1B2CA2`

## Funnels

- `HYP-H1-ORDERBLOCK-MITIGATION-001`: {'n_displace': 1802, 'n_ob': 1794, 'n_trades': 412} notes=['pf_fail', 'stress_fail']
- `HYP-D1-INSIDE-H4-BREAK-001`: {'n_inside_d1': 1248, 'n_break': 564, 'n_trades': 369} notes=['pf_fail', 'stress_fail']
- `HYP-H1-LONDON-DRIVE-FAIL-FADE-001`: {'n_london_days': 1299, 'n_displace': 699, 'n_fail': 381, 'n_trades': 298} notes=['pf_fail', 'stress_fail']
- `HYP-M15-ASIA-BREAK-FAIL-FADE-001`: {'n_asia_days': 1300, 'n_break': 1104, 'n_fail': 790, 'n_trades': 102} notes=['cadence_fail', 'pf_fail', 'stress_fail']
- `HYP-H4-BREAK-PAUSE-BREAK-001`: {'n_break': 1393, 'n_pause': 294, 'n_trades': 31} notes=['n_fail', 'cadence_fail', 'pf_fail', 'stress_fail']

## Phase-0 / best shelf

Discovery continues without Phase-0 Owner clear. Best shelf RR2 `194548`.
Do not densify any V5 kill parameters.
