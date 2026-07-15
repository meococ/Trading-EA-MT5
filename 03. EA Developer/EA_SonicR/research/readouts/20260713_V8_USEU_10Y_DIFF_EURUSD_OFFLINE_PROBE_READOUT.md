# V8_USEU_10Y_DIFF_EURUSD_V1 Offline Probe Readout — 2026-07-13

Status: `KILL_AT_OFFLINE_PROBE`

## Contract

- Probe: `V8_USEU_10Y_DIFF_EURUSD_V1`
- Mechanism: lagged US Treasury 10Y − ECB AAA gov 10Y z-score → EURUSD
- Panel SHA256: `27D4BE9BAEBDE5062813D98869C886DC2E0E0CDA5E8B6967D723085308E7D18D`
- Contract: `preflight/v8_exogenous/20260713_V8_USEU_10Y_DIFF_EURUSD_PROBE_CONTRACT_V1.md`
- Result JSON: `preflight/v8_probe/20260713_V8_USEU_10Y_DIFF_EURUSD_PROBE_RESULT_V1.json`
- MT5 server used for falsification: `MetaQuotes-Demo` (not QFSI Real)

## De-dup (pre-result)

Independent of killed G3 short-rate carry, COT TFF, carry×vol, USBILL curve-shape
basket, USD-factor FX-return architecture, S619 price catch-up, and equity-close
hour books. Causal variable is lagged sovereign bond differential only.

## Train (2019-01-01 → 2023-01-01)

| Metric | Candidate | Momentum control |
|---|---:|---:|
| Trades | 224 | 248 |
| Trades/week | 1.073 | 1.188 |
| PF gross | 0.607 | 0.878 |
| PF stress-A (1.5 pip) | **0.579** | 0.834 |
| Expectancy-A (pips) | **−17.21** | −5.32 |
| Year conc. pos net-A | 0.361 | n/a |

Holdout gated shut (train failed).

## Kill reasons

- `pf_stress_a<1.05`
- `fail_beat_control_pf_a`
- `fail_beat_control_expectancy_a`

Cadence/sample floors passed (≥80 trades, ≥0.5/week). Edge failed decisively:
candidate is worse than matched-calendar momentum control after cost stress.

## Authority

Offline falsification only. **No** registry / prereg / EA / MetaEditor /
Strategy Tester / Model 0. Do not retune z-threshold, tenors, or add GBP/JPY
sleeves from this readout.
