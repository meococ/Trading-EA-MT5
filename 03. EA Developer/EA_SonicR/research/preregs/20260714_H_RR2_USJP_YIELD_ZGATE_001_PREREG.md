# Prereg — HYP-RR2-USJP-YIELD-ZGATE-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Authority: Owner dichotomy-break mandate; GPT waived; no densify

## Identity

- Hypothesis ID: `HYP-RR2-USJP-YIELD-ZGATE-001`
- Parent: `HYP-SB-MAXKZ2-RR2-FRICTION-001` (frozen shelf `20260714_194548`)
- Class: exogenous **allow-gate** (not directional exo signal)
- Panel: `readouts/20260714_DICHOTOMY_BREAK_3CRITIC_MERGE_MEMO.md`
- De-dup: `readouts/20260714_DICHOTOMY_BREAK_DEDUP_CLEARANCE.md`

## Thesis

US−JP 10Y yield differential |z| regimes may mark when RR2 mean-edge
survives friction. Gate **allows** frozen RR2 entries only when lagged
|z| ≥ 0.75; otherwise skip. Not a bond/VIX directional entry.

## Locked Design

| Item | Frozen |
|---|---|
| Panel | `preflight/v8_exogenous/panels/us_jp_bond_yield_diff_d1_v1.csv` |
| Gate | |z| ≥ 0.75 (lookback 60, min obs 40); lagged via `available_at_utc` |
| Donor | RR2 `20260714_194548` opens unchanged when allowed |
| Window | 2021.01.01–2025.12.31 |

## De-dup

- Not USEU/USUK/EU-curve bond **signal** kills
- Not VIX risk-off USDJPY signal
- Not USBILL Model 0 directional

## Kill / Park / HIT (offline probe)

| Gate | Rule |
|---|---|
| KILL | N&lt;80 OR tpw∉[1.0,6.5] OR PF&lt;1.05 OR +$12 x1.5 PF&lt;1.10 OR no stress lift vs ungated |
| PROBE_SURVIVOR | PF&gt;1.20 ∧ tpw∈[1.5,6] ∧ x1.5 PF≥1.15 ∧ stress lift |
| Model 0 | only if PROBE_SURVIVOR |

## Banned

- Mining z threshold from readout
- Using yield series as entry direction
- Densify MaxKZ/RR under the gate
