# Offline probes — entry-state rebuild (post ATR-trail Model0 KILL)

Date: 2026-07-15
Receipt SHA256: `85C53902CAC674BFE11369CF080BCFC8670668C5A71A310CE614B3D7CD8A246D`
Authority: post ATR-trail native double KILL; offline-first; Model 0 survivors only

## Baseline RR2 `194548`

- N=524 PF=1.3794 tpw=2.0099 x1.5=1.0134
- trades_csv: `02. AlphaFactory/runs/EA_SilverBullet/20260714_194548/logs/USDJPY_20260325_PX6_Trades_20210101_000000_90095968.csv`

## Results

| ID | N | PF | tpw | x1.5 | lift | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `HYP-RR2-ENTRY-IMPULSE-BODYATR-GATE-001` | 167 | 1.0613 | 0.6405 | 0.8213 | -0.1921 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-RR2-BOOK-DROP-THINRISK-P25-001` | 393 | 1.3316 | 1.5074 | 1.0219 | 0.0085 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-USDJPY-H1-ASIA-PDCLOSE-MAGNET-FADE-001` | 766 | 0.8953 | 2.9381 | 0.8228 | n/a | **KILLED_AT_OFFLINE_PROBE** |

Survivor bar: N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15 (+ stress lift vs RR2 baseline for RR2 children).

## Kill notes

- `HYP-RR2-ENTRY-IMPULSE-BODYATR-GATE-001`: cadence_fail, pf_fail, stress_fail, no_stress_lift_vs_baseline
- `HYP-RR2-BOOK-DROP-THINRISK-P25-001`: stress_fail, no_stress_lift_vs_baseline
- `HYP-USDJPY-H1-ASIA-PDCLOSE-MAGNET-FADE-001`: pf_fail, stress_fail

Survivors: **0** / 3
Model 0: **WITHHELD_ZERO_SURVIVOR**
Best shelf: RR2 `20260714_194548`
GOAL unmet.

