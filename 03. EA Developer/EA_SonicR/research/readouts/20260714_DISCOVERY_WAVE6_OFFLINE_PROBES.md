# Discovery Wave6 — offline probes (joint thick + cadence)

Generated: 2026-07-14T16:23:33.786455Z
De-dup: `readouts/20260714_DISCOVERY_WAVE6_DEDUP_CLEARANCE.md`
Receipt SHA: `AB9ED62FC88D91AF4395E6B22DBF710FDA55EFAD823C3E9979C0FE3F07BE9176`

| ID | Sym | N | PF | tpw | x1.5 | x2 | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| `HYP-H1-MONO-CONTRACT-BREAK-001` | USDJPY | 740 | 1.131 | 2.84 | 1.074 | 1.056 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-M15-BROKEN-LEVEL-RETEST-001` | USDJPY | 1464 | 1.089 | 5.61 | 1.051 | 1.039 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-H1-FORMING-DAY-EXT-FADE-001` | USDJPY | 670 | 0.889 | 2.57 | 0.844 | 0.829 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-FX3-H1-BODYATR-CONT-PORTFOLIO-001` | EURUSD+USDJPY+GBPUSD | 2814 | 1.074 | 10.79 | 1.011 | 0.991 | **KILLED_AT_OFFLINE_PROBE** |

Survivors: `[]`
Model 0 authorized: `False`

## Funnels

- `HYP-H1-MONO-CONTRACT-BREAK-001`: {'n_coil': 1371, 'n_break': 789, 'n_trades': 740} notes=['stress_fail']
- `HYP-M15-BROKEN-LEVEL-RETEST-001`: {'n_break': 7753, 'n_retest': 3058, 'n_trades': 1464} notes=['stress_fail']
- `HYP-H1-FORMING-DAY-EXT-FADE-001`: {'n_days': 1299, 'n_ext': 890, 'n_trades': 670} notes=['pf_fail', 'stress_fail']
- `HYP-FX3-H1-BODYATR-CONT-PORTFOLIO-001`: {'per_symbol_raw': {'EURUSD': 2316, 'USDJPY': 2045, 'GBPUSD': 2303}, 'n_pooled_raw': 6664, 'n_trades': 2814} notes=['cadence_fail', 'stress_fail']

Best shelf RR2 `194548` unchanged unless survivor promotes.
Cost grade: `UNVERIFIED_OFFLINE_PROXY` (+$12 baked).

