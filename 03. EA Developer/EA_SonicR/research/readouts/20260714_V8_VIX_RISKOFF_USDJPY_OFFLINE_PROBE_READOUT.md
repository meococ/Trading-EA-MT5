# V8_VIX_RISKOFF_USDJPY_V1 Offline Probe Readout — 2026-07-14

Status: `KILL_AT_OFFLINE_PROBE`

## Contract

- Probe: `V8_VIX_RISKOFF_USDJPY_V1`
- VIX SHA256: `9D0B7EC855526BAC12ED0AD5B567FDDFCB5BC426402480242B6D10C766615A47`
- Contract: `03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/20260714_V8_VIX_RISKOFF_USDJPY_PROBE_CONTRACT_V1.md`
- De-dup: `readouts/20260714_VIX_RISKOFF_USDJPY_DEDUP_CLEARANCE.md`

## Train (2019–2022)

| Metric | Candidate | Control |
|---|---:|---:|
| Trades | 202 | 231 |
| Trades/week | 0.968 | 1.107 |
| PF stress-A | 0.6859130139763621 | 0.8053699403159067 |
| Expectancy-A (pips) | -12.544036019793156 | -6.980991939619924 |
| Year conc. pos net-A | 0.40376969784588684 | n/a |

## Kill reasons

- `pf_stress_a<1.05`
- `fail_beat_control_pf_a`
- `fail_beat_control_expectancy_a`

## Authority

Offline falsification only. No registry/prereg/EA/Model 0 unless survive.
Do not retune z / VIX transform / equity-bond overlay from this readout.
