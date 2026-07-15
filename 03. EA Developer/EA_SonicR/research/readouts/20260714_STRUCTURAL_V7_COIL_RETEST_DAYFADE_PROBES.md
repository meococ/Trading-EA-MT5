# Structural V7 — coil / retest / day-fade offline probes

Generated: 2026-07-14T16:21:42.287314Z
Stem: `STRUCTURAL_V7_COIL_RETEST_DAYFADE` (collision-safe)
Authority: Owner GOAL push; offline-first; GPT waived
Status: **offline-first**; Model 0 only if `PROBE_SURVIVOR`

De-dup: `20260714_STRUCTURAL_V7_DEDUP_CLEARANCE.md`

| ID | Symbol | N | PF | tpw | +$12 x1.5 PF | Verdict |
|---|---|---:|---:|---:|---:|---|
| `HYP-H1-MONO-CONTRACT-BREAK-001` | USDJPY | 1923 | 1.095 | 7.37 | 1.033 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-M15-BROKEN-LEVEL-RETEST-001` | USDJPY | 1555 | 1.070 | 5.96 | 1.009 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-H1-FORMING-DAY-EXT-FADE-001` | USDJPY | 505 | 1.086 | 1.94 | 1.021 | **KILLED_AT_OFFLINE_PROBE** |

Offline survivors: `[]`
Any Model 0 authorized: `False`
Receipt SHA: `F4FD11D2BB9379BA9E48FD5AC456A5717F8E3D2FBED8CE121206F540BA063B0E`

## Funnels

- `HYP-H1-MONO-CONTRACT-BREAK-001`: {'n_coil': 4057, 'n_trades': 1923} notes=['cadence_fail', 'stress_fail']
- `HYP-M15-BROKEN-LEVEL-RETEST-001`: {'n_break': 6901, 'n_retest': 2214, 'n_trades': 1555} notes=['stress_fail']
- `HYP-H1-FORMING-DAY-EXT-FADE-001`: {'n_ready': 2290, 'n_trades': 505} notes=['stress_fail']

## Best shelf

RR2 `194548`. Do not densify V7 coil/retest/dayfade params.
