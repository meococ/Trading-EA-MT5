# Structural rebuild offline probes V9

Generated: 2026-07-14T16:30:01.446013Z
Authority: Owner GOAL after RR2 PARK_MISS + dichotomy empty; GPT waived
Status: **offline-first**; Model 0 only if `PROBE_SURVIVOR`

De-dup: `20260714_STRUCTURAL_V9_DEDUP_CLEARANCE.md`

| ID | Sym | N | PF | tpw | +$12 x1.5 | Real~$2.31 PF | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| `HYP-CHFJPY-H1-DISPLACE-CONT-001` | CHFJPY | 1730 | 1.077 | 6.63 | 1.020 | 1.070 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-USDJPY-H1-EXPANSION-BAR-CONT-001` | USDJPY | 664 | 1.235 | 2.55 | 1.162 | 1.225 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-NZDUSD-H1-ASIA-RANGE-LONDON-FAIL-001` | NZDUSD | 0 | 0.000 | 0.00 | 0.000 | 0.000 | **KILLED_AT_OFFLINE_PROBE** |

Offline survivors: `[]`
Offline parks: `[]`
Any Model 0 authorized: `False`
Receipt SHA: `3F47416C668D2BDC5947E2B141F4A5E51678B64F49C58D71DE35B994EB03CBC8`

## Funnels

- `HYP-CHFJPY-H1-DISPLACE-CONT-001`: {'n_displace': 1730, 'n_trades': 1730} notes=['cadence_fail', 'stress_fail']
- `HYP-USDJPY-H1-EXPANSION-BAR-CONT-001`: {'n_exp': 665, 'n_trades': 664} notes=['stress_fail']
- `HYP-NZDUSD-H1-ASIA-RANGE-LONDON-FAIL-001`: {'n_days': 1300, 'n_break': 1177, 'n_fail': 488, 'n_trades': 0} notes=['n_fail', 'cadence_fail', 'pf_fail', 'stress_fail']

## Notes

- Dichotomy D1–D3 already KILL (BE exit / yield-z / CorrCap).
- Best shelf historical RR2 `194548`; current same-ID Model0 `231750` PARK_MISS.
- Do not densify V9 params. Phase-0 still BLOCKED.
