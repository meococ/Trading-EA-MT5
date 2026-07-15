# Prereg — HYP-RR2-EXIT-BE1R-M15PATH-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Authority: Owner dichotomy-break mandate; GPT waived; no densify

## Identity

- Hypothesis ID: `HYP-RR2-EXIT-BE1R-M15PATH-001`
- Parent: `HYP-SB-MAXKZ2-RR2-FRICTION-001` (frozen shelf `20260714_194548`)
- Class: cost-resilient **exit architecture** (not entry densify)
- Panel: `readouts/20260714_DICHOTOMY_BREAK_3CRITIC_MERGE_MEMO.md`
- De-dup: `readouts/20260714_DICHOTOMY_BREAK_DEDUP_CLEARANCE.md`

## Thesis

RR2 clears research PF/cadence under tester but fails +$12 / Real-P50
cost stress. Edge is mean-edge insolvency under friction, not missing
entries. Child freezes **BE@1.0R** via closed M15 path on the same
frozen RR2 opens, keeping original TP. Goal: cut give-back after 1R
without retuning MaxKZ/RR.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY M15 (path) on frozen RR2 opens |
| Donor run | `20260714_194548` (exact overrides unchanged) |
| BE trigger | arm when M15 high/low reaches +1.0R; SL → entry |
| TP | original RR2 TP kept |
| Window | 2021.01.01–2025.12.31 |
| Offline first | resim on trades CSV + MT5 M15 bars |

## De-dup

- Not T1 cost-arm (entry filter by min risk_$)
- Not MaxKZ / RR densify
- Not ATR-stop replace
- Not Wave3 Partial-R1 intake clone (that was banned densify family)

## Kill / Park / HIT (offline probe)

| Gate | Rule |
|---|---|
| KILL | N&lt;80 OR tpw∉[1.0,6.5] OR PF&lt;1.05 OR +$12 x1.5 PF&lt;1.10 OR no stress lift vs baseline |
| PROBE_SURVIVOR | PF&gt;1.20 ∧ tpw∈[1.5,6] ∧ x1.5 PF≥1.15 ∧ stress lift vs baseline |
| Model 0 | only if PROBE_SURVIVOR; same frozen RR2 overrides + BE exit code |

## Banned

- Mining BE threshold from readout
- Raising RR / MaxKZ from this probe
- Claiming GOAL from Demo / unverified cost
