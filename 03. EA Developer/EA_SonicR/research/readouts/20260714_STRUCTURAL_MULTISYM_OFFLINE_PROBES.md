# Structural MULTISYM offline probes (EURUSD / GBPUSD / XAUUSD)

Generated: 2026-07-14T16:18:58.148988Z
Escape: **USDJPY TF saturation** → EURUSD / GBPUSD / XAUUSD
Stem: **STRUCTURAL_MULTISYM_*** (collision-safe vs V6 restore + peer V7 coil)
De-dup: `20260714_STRUCTURAL_MULTISYM_DEDUP_CLEARANCE.md`

| ID | Sym | N | PF | tpw | cost×1.5 PF | Verdict |
|---|---|---:|---:|---:|---:|---|
| `HYP-EURUSD-H1-LONDON-OVERLAP-RANGE-BREAK-001` | EURUSD | 725 | 1.069 | 2.78 | 0.986 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-GBPUSD-H1-NY-OPEN-IMPULSE-001` | GBPUSD | 46 | 0.740 | 0.18 | 0.681 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-XAUUSD-H1-ASIA-COMPRESS-LONDON-BREAK-001` | XAUUSD | 0 | 0.000 | 0.00 | 0.000 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-EURUSD-D1-OUTSIDE-H1-FADE-001` | EURUSD | 74 | 0.695 | 0.28 | 0.608 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-GBPUSD-H4-BREAK-H1-OPEN-PB-001` | GBPUSD | 774 | 0.953 | 2.97 | 0.895 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-XAUUSD-H4-WICK-REJECT-FADE-001` | XAUUSD | 1059 | 0.877 | 4.06 | 0.764 | **KILLED_AT_OFFLINE_PROBE** |

Survivors: `[]`
Model 0 authorized: `False`
Receipt SHA: `C802A33A2601D65AF953814EBB02CDFE7E82840A86E4666839FA1346A1C514D3`

## Funnels

- `HYP-EURUSD-H1-LONDON-OVERLAP-RANGE-BREAK-001`: {'n_days': 1299, 'n_break': 1226, 'n_trades': 725} notes=['stress_fail']
- `HYP-GBPUSD-H1-NY-OPEN-IMPULSE-001`: {'n_days': 1298, 'n_impulse': 127, 'n_trades': 46} notes=['n_fail', 'cadence_fail', 'pf_fail', 'stress_fail']
- `HYP-XAUUSD-H1-ASIA-COMPRESS-LONDON-BREAK-001`: {'n_days': 1290, 'n_compress': 0, 'n_break': 0, 'n_trades': 0} notes=['n_fail', 'cadence_fail', 'pf_fail', 'stress_fail']
- `HYP-EURUSD-D1-OUTSIDE-H1-FADE-001`: {'n_outside_d1': 136, 'n_trades': 74} notes=['n_fail', 'cadence_fail', 'pf_fail', 'stress_fail']
- `HYP-GBPUSD-H4-BREAK-H1-OPEN-PB-001`: {'n_h4_break': 1821, 'n_pb': 793, 'n_trades': 774} notes=['pf_fail', 'stress_fail']
- `HYP-XAUUSD-H4-WICK-REJECT-FADE-001`: {'n_wick': 1321, 'n_trades': 1059} notes=['pf_fail', 'stress_fail']

Best shelf RR2 `194548` unchanged. No Phase-0 wait.
