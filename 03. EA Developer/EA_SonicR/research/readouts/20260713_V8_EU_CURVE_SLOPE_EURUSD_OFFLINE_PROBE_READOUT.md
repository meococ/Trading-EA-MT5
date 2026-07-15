# V8_EU_CURVE_SLOPE_EURUSD_V1 Offline Probe Readout — 2026-07-13

Status: `KILL_AT_OFFLINE_PROBE`

## Contract

- Probe: `V8_EU_CURVE_SLOPE_EURUSD_V1`
- Panel SHA256: `27D4BE9BAEBDE5062813D98869C886DC2E0E0CDA5E8B6967D723085308E7D18D`
- Field: `eu_curve_10y_minus_2y`
- Contract: `03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/20260713_V8_EU_CURVE_SLOPE_EURUSD_PROBE_CONTRACT_V1.md`

## Train (2019–2022)

| Metric | Candidate | Control |
|---|---:|---:|
| Trades | 217 | 242 |
| Trades/week | 1.040 | 1.159 |
| PF stress-A | 0.7730625860052829 | 0.8679045572799311 |
| Expectancy-A (pips) | -8.631638275955464 | -4.2155115310796365 |
| Year conc. pos net-A | 0.3558442779675889 | n/a |

## Kill reasons

- `pf_stress_a<1.05`
- `fail_beat_control_pf_a`
- `fail_beat_control_expectancy_a`

## Authority

Offline falsification only. No registry / prereg / EA / Model 0 on kill. Do not retune z/tenors from this readout.
