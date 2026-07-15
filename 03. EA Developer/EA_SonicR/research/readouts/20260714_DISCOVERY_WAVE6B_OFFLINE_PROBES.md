# Discovery Wave6 pack B — offline probes

Generated: 2026-07-14T16:25:19.127836Z
De-dup: `readouts/20260714_DISCOVERY_WAVE6B_DEDUP_CLEARANCE.md`
Receipt SHA: `B38AE9E3535239DF376E65DFC308EDDC533B4615E20962AEDD5AF45B04902DFF`

| ID | Sym | N | PF | tpw | x1.5 | x2 | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| `HYP-H1-MOTHER-BAR-BREAK-001` | USDJPY | 377 | 1.327 | 1.45 | 1.232 | 1.202 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-H1-THREE-DAY-HIGHLOW-BREAK-001` | USDJPY | 265 | 1.688 | 1.02 | 1.408 | 1.325 | **PARK_OFFLINE** |
| `HYP-USDCHF-H1-LONDON-RANGE-BREAK-001` | USDCHF | 692 | 0.989 | 2.65 | 0.905 | 0.879 | **KILLED_AT_OFFLINE_PROBE** |

Survivors: `[]`
Model 0 authorized: `False`

## Funnels

- `HYP-H1-MOTHER-BAR-BREAK-001`: {'n_mother': 3171, 'n_inside': 1019, 'n_break': 411, 'n_trades': 377} notes=['stress_fail']
- `HYP-H1-THREE-DAY-HIGHLOW-BREAK-001`: {'n_eligible': 7254, 'n_break': 1262, 'n_trades': 265} notes=[]
- `HYP-USDCHF-H1-LONDON-RANGE-BREAK-001`: {'n_days': 1299, 'n_break': 1216, 'n_trades': 692} notes=['pf_fail', 'stress_fail']

Do not densify pack B params. Cost: `UNVERIFIED_OFFLINE_PROXY`.

