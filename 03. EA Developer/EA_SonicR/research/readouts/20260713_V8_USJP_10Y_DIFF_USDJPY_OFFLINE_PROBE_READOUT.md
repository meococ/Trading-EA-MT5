# V8_USJP_10Y_DIFF_USDJPY_V1 Offline Probe Readout — 2026-07-13

Status: `KILL_AT_OFFLINE_PROBE`

## Contract

- Probe: `V8_USJP_10Y_DIFF_USDJPY_V1`
- Panel SHA256: `3FD760682D9D198FD47E465792A3092E14FC70A092FABAE529DF02E434E04625`
- Contract: `03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/20260713_V8_USJP_10Y_DIFF_USDJPY_PROBE_CONTRACT_V1.md`

## Train (2019–2022)

| Metric | Candidate | Control |
|---|---:|---:|
| Trades | 215 | 262 |
| Trades/week | 1.030 | 1.255 |
| PF stress-A | 0.9767196154475268 | 0.9267262539000485 |
| Expectancy-A (pips) | -0.8753090486218615 | -2.4950864616814377 |
| Year conc. pos net-A | 0.49786587296561374 | n/a |

## Kill reasons

- `pf_stress_a<1.05`

## Authority

Offline falsification only. **No** registry / prereg / EA / Model 0.
Do not retune z/tenor. Not a USEU/USUK rescue. Session closeout:
`readouts/20260713_OIS_USJP_SELF_RESEARCH_SESSION_CLOSEOUT.md`
