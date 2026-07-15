# HIS Offline Gate-Count — EURUSD M15 (Owner A)

Generated: 2026-07-15T10:01:32Z
Requested: 2020-01-01 → 2026-07-15
Covered M15: 2022-07-11T06:15:00Z → 2026-07-15T10:00:00Z (100000 bars)
Covered H4: 12201 bars
Coverage note: Python copy_rates year-chunks: M15 usable ~2022+ on this terminal API; Model 0 tester had full 2020-2026 ticks. Gate ranking still valid on covered M15.
Artifact SHA256: `FDCB7258A7385C97833D619209C03C25E40D8B12FE0DCF58F455857E6523D006`

## Counts (sequential AND)

| Gate | Count | Pass ratio vs prior |
|---|---:|---:|
| N_bars_total | 99911 | — |
| N0_session | 54098 | 0.5415 |
| N1_atr_regime | 53781 | 0.9941 |
| N2_bias | 53781 | 1.0000 |
| N3_level_object | 53781 | 1.0000 |
| N4_near_level | 34310 | 0.6380 |
| N5_wave | 11909 | 0.3471 |
| N6_dragon | 5633 | 0.4730 |
| N7_pvsra | 1372 | 0.2436 |
| N8_sl_ok | 0 | 0.0000 |

| N6a mid reclaim (non-exclusive) | 895 | — |
| N6b outer break (non-exclusive) | 5069 | — |
| N8 SL fail after full stack (Dragon±40 vs MaxSl) | 1372 | — |

**First near-zero gate:** `N8_sl_ok`

## Interpretation

- Offline probe only — not Model 0 / not PF claim.
- Do not densify Dragon 30–38 or post-hoc hour veto from this.
- Parent hyp remains `KILL_AT_MODEL0_EMPTY`.

