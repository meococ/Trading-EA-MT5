# Offline — Unpark W1 + M15 thick-stop + replacement

Receipt: `CB8FBE71981DABCE680CA5CF2177BC5166BD8BE3298CAE6CB761FA822CF6D7A2`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost: +$12 joint; window 2021–2025; deposit 100000

## Intake-killed (no probe metrics as survivor path)
- `HYP-USDJPY-M15-D1BIAS-PDHPDL-THICK-001` — INTAKE_KILL: identical surface to parked HYP-PDH-BREAK-M15-001 (D1 EMA50 + M15 beyond prior D1 H/L) + SB/session densify contamination. Replaced by RANGEEXP thick-stop + D1-inside greenfield.

| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-W1-HLBREAK-D1CONF-HOLD-001` | 80 | 0.9895 | 0.3068 | 0.898 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-USDJPY-M15-D1BIAS-RANGEEXP-THICK-001` | 1247 | 1.1857 | 4.783 | 1.0986 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-USDJPY-D1-INSIDE-H1-BREAK-CONT-001` | 179 | 1.2118 | 0.6866 | 1.1433 | **KILLED_AT_OFFLINE_PROBE** |

## Funnel notes
- `HYP-FX3-W1-HLBREAK-D1CONF-HOLD-001`: {'n_w1_breaks': 365, 'n_d1_confirm': 80, 'n_trades': 80, 'n_skip_open': 1180, 'n_skip_week': 0}
- `HYP-USDJPY-M15-D1BIAS-RANGEEXP-THICK-001`: {'n_bars': 124573, 'n_bias_ok': 17252, 'n_signal': 1247, 'n_trades': 1247, 'n_skip_open': 12691}
- `HYP-USDJPY-D1-INSIDE-H1-BREAK-CONT-001`: {'n_bars': 31128, 'n_inside_active': 2352, 'n_signal': 179, 'n_trades': 179, 'n_skip_open': 1101}

QFSI parallel: 007 accumulate hb=9480 quotes=6586 deadline=2026-07-15T07:39:26.186865Z; cost freeze still GAP; login not headline.
Best shelf RR2 `194548`. GOAL unmet.
