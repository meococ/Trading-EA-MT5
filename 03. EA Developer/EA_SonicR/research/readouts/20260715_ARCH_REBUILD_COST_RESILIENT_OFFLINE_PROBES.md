# Offline probes — architecture rebuild cost-resilient (Track B)

Date: 2026-07-15
Status: `OFFLINE_ALL_KILL / NO_MODEL0`
Receipt SHA: `90D5E4500A072B06C4958F4627E4AEB87051F7FE97A503023F83B392617DB864`

## Baseline RR2 `194548`

- N=524 PF=1.3794 tpw=2.0099 x1.5=1.0134

## Board

| ID | N | PF | tpw | stress x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-RR2-VOLTARGET-ATRRISK-001` | 524 | 1.4432 | 2.0099 | 0.9895 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-RR2-H4-REGIME-ALIGN-GATE-001` | 210 | 1.3282 | 0.8055 | 0.9812 | **KILLED_AT_OFFLINE_PROBE** |

## Notes

- `HYP-RR2-VOLTARGET-ATRRISK-001`: notes=['stress_fail', 'no_stress_lift_vs_baseline'] funnel=None
- `HYP-RR2-H4-REGIME-ALIGN-GATE-001`: notes=['cadence_fail', 'stress_fail', 'no_stress_lift_vs_baseline'] funnel={'n_in': 524, 'n_kept': 210, 'n_skip_data': 5, 'n_skip_atr_pctile': 289, 'n_skip_align': 20}

## Model 0

Withheld.

## Artifacts

- `03. EA Developer/EA_SonicR/research/preflight/20260715_ARCH_REBUILD_COST_RESILIENT_OFFLINE_PROBES.json`
- `03. EA Developer/EA_SonicR/research/readouts/20260715_ARCH_REBUILD_DEDUP_CLEARANCE.md`
- `03. EA Developer/EA_SonicR/research/readouts/20260715_ARCH_REBUILD_DESIGN_MEMO.md`

Do not densify vol clip / H4 ATR%ile / EMA from this readout.

