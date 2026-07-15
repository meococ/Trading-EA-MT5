# V8_USUK_10Y_DIFF_GBPUSD_V1 Offline Probe Readout — 2026-07-13

Status: `KILL_AT_OFFLINE_PROBE`

## Contract

- Probe: `V8_USUK_10Y_DIFF_GBPUSD_V1`
- Panel SHA256: `B3FB71465C6652EA36E8E2010771473A814A4F97426FC00E2A52995E73AEBCF8`
- Contract: `03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/20260713_V8_USUK_10Y_DIFF_GBPUSD_PROBE_CONTRACT_V1.md`

## Train (2019–2022)

| Metric | Candidate | Control |
|---|---:|---:|
| Trades | 197 | 209 |
| Trades/week | 0.944 | 1.001 |
| PF stress-A | 0.8339141604033179 | 1.0764848409445191 |
| Expectancy-A (pips) | -9.153970419204969 | 3.5304984728226767 |
| Year conc. pos net-A | 0.40709039704014566 | n/a |

## Kill reasons

- `pf_stress_a<1.05`
- `fail_beat_control_pf_a`
- `fail_beat_control_expectancy_a`

## Authority

Offline falsification only. No registry / prereg / EA / Model 0 unless verdict is survive (it is not, if kill reasons non-empty).
Do not retune z-threshold or tenors from this readout.
