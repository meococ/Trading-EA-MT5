# Discovery Wave7 — offline probes

Generated: 2026-07-14T16:38:06.447009Z
De-dup: `readouts/20260714_DISCOVERY_WAVE7_DEDUP_CLEARANCE.md`
Receipt SHA: `EA4D74FB91D34D27D872B607C45FD2849A06A7751A65624EE05E2366EB79B757`
Server/login: `FivePercentOnline-Real` / `26451822`

| ID | Sym | N | PF | tpw | x1.5 | x2 | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| `HYP-NZDUSD-H1-ASIA-RANGE-LONDON-BREAK-001` | NZDUSD | 587 | 1.039 | 2.25 | 0.923 | 0.887 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-W1-OPEN-H1-ACCEPT-CONT-001` | USDJPY | 233 | 1.196 | 0.89 | 1.085 | 1.050 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-H1-LONDON-MID-RECLAIM-CONT-001` | USDJPY | 371 | 1.136 | 1.42 | 1.086 | 1.071 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-AUDUSD-LEAD-EURUSD-H1-001` | EURUSD | 919 | 0.833 | 3.52 | 0.774 | 0.755 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-EURUSD-H1-WEEKEND-GAP-FILL-001` | EURUSD | 123 | 1.117 | 0.47 | 1.057 | 1.038 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-BOOK-COMPOSE-3DAY-LONDONDRIVE-001` | USDJPY | 570 | 1.111 | 2.19 | 1.028 | 1.002 | **KILLED_AT_OFFLINE_PROBE** |

Survivors: `[]`
Model 0 authorized: `False`

## Funnels / extras

- `HYP-NZDUSD-H1-ASIA-RANGE-LONDON-BREAK-001`: funnel={'n_days': 1300, 'n_break': 1069, 'n_trades': 587} notes=['stress_fail']
- `HYP-W1-OPEN-H1-ACCEPT-CONT-001`: funnel={'n_eligible': 1850, 'n_signal': 1848, 'n_trades': 233} notes=['cadence_fail', 'stress_fail']
- `HYP-H1-LONDON-MID-RECLAIM-CONT-001`: funnel={'n_days': 1299, 'n_pierce': 1298, 'n_trades': 371} notes=['stress_fail']
- `HYP-AUDUSD-LEAD-EURUSD-H1-001`: funnel={'n_lead': 5668, 'n_follow': 2409, 'n_trades': 919} notes=['pf_fail', 'stress_fail']
- `HYP-EURUSD-H1-WEEKEND-GAP-FILL-001`: funnel={'n_gaps': 139, 'n_trades': 123} notes=['cadence_fail', 'stress_fail']
- `HYP-BOOK-COMPOSE-3DAY-LONDONDRIVE-001`: funnel={'n_3day': 265, 'n_london_drive': 305, 'n_pooled': 570} notes=['stress_fail'] extra={'sleeve_a_n': 265, 'sleeve_b_n': 305, 'same_day_overlap': 72, 'exact_entry_ts_overlap': 2, 'compose_rule': 'a_priori_equal_join_3day_PARK_plus_london_drive_thick'}

Do not densify Wave7 params. Cost: `UNVERIFIED_OFFLINE_PROXY`.
Compose is a priori thick-park join — not Phase-0 SB/Spark reopen.

