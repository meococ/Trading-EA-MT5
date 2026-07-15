# Structural rebuild offline probes V8

Generated: 2026-07-14T16:23:43.683042Z
Authority: Owner GOAL push; offline-first; GPT waived; outside V1–V7
Status: **offline-first**; Model 0 only if `PROBE_SURVIVOR`

De-dup: `20260714_STRUCTURAL_V8_DEDUP_CLEARANCE.md`
H1–H3 a priori: `20260714_STRUCTURAL_V7_DEDUP_CLEARANCE.md`

| ID | Sym | N | PF | tpw | +$12 x1.5 | Real~$2.31 PF | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| `HYP-H1-MONO-CONTRACT-BREAK-001` | USDJPY | 2362 | 1.075 | 9.05 | 0.998 | 1.064 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-M15-BROKEN-LEVEL-RETEST-001` | USDJPY | 2352 | 1.032 | 9.02 | 0.986 | 1.026 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-H1-FORMING-DAY-EXT-FADE-001` | USDJPY | 584 | 0.973 | 2.24 | 0.913 | 0.965 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-EURGBP-H1-LEAD-EURUSD-H1-001` | EURUSD | 207 | 0.916 | 0.79 | 0.822 | 0.904 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-AUDUSD-H1-OVERLAP-FAIL-FADE-001` | AUDUSD | 1 | 0.000 | 0.00 | 0.000 | 0.000 | **KILLED_AT_OFFLINE_PROBE** |

Offline survivors: `[]`
Offline parks: `[]`
Any Model 0 authorized: `False`
Receipt SHA: `A44893E0210258DC01F54097B2D0D4F3EDE27D19F715C2179CAB1F92865565CF`

## Funnels

- `HYP-H1-MONO-CONTRACT-BREAK-001`: {'n_coil': 3886, 'n_break': 2380, 'n_trades': 2362} notes=['cadence_fail', 'stress_fail']
- `HYP-M15-BROKEN-LEVEL-RETEST-001`: {'n_pivot': 18853, 'n_break': 8959, 'n_retest': 5834, 'n_trades': 2352} notes=['cadence_fail', 'stress_fail']
- `HYP-H1-FORMING-DAY-EXT-FADE-001`: {'n_eligible_days': 1449, 'n_ext': 755, 'n_trades': 584} notes=['pf_fail', 'stress_fail']
- `HYP-EURGBP-H1-LEAD-EURUSD-H1-001`: {'n_lead': 2009, 'n_align': 1301, 'n_trades': 207} notes=['cadence_fail', 'pf_fail', 'stress_fail']
- `HYP-AUDUSD-H1-OVERLAP-FAIL-FADE-001`: {'n_days': 1299, 'n_break': 1155, 'n_fail': 537, 'n_trades': 1} notes=['n_fail', 'cadence_fail', 'pf_fail', 'stress_fail']

## Notes

- +$12 x1.5 is conservative Demo friction proxy (legacy screen).
- Real P50 ~$2.31 is partial live-tick haircut — **not** full QFSI / not confirmed.
- Best shelf RR2 `194548` unchanged. Do not densify V8 kill params.
