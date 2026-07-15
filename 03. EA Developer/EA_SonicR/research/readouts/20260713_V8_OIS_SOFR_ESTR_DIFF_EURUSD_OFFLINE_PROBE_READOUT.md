# V8_OIS_SOFR_ESTR_DIFF_EURUSD_V1 Offline Probe Readout — 2026-07-13

Status: `KILL_AT_OFFLINE_PROBE`

## Contract

- Probe: `V8_OIS_SOFR_ESTR_DIFF_EURUSD_V1`
- Panel SHA256: `0EFEF0C0CF0D93552FF713CA9278B924F10BA2B7FB8099D4CB594B4667496600`
- Contract: `03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/20260713_V8_OIS_SOFR_ESTR_DIFF_EURUSD_PROBE_CONTRACT_V1.md`

## Train (2019–2022)

| Metric | Candidate | Control |
|---|---:|---:|
| Trades | 159 | 179 |
| Trades/week | 0.762 | 0.858 |
| PF stress-A | 1.0026606830004186 | 0.7952952657654327 |
| Expectancy-A (pips) | 0.08808024138654533 | -6.948936151506905 |
| Year conc. pos net-A | 0.36980824617250313 | n/a |

## Kill reasons

- `pf_stress_a<1.05`

## Authority

Offline falsification only. **No** registry / prereg / EA / Model 0.
Do not retune z-threshold or tenors. Do not auto-launch SOFR−SONIA as a
rescue twin. Candidate beat momentum control but failed absolute PF-A floor
(1.003 < 1.05) — classic near-miss, not a survivor.

Session closeout:
`readouts/20260713_OIS_USJP_SELF_RESEARCH_SESSION_CLOSEOUT.md`
