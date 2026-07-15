# V8 Carry Rate-Event Offline Probe Readout — 2026-07-13

Status: `KILL_AT_OFFLINE_PROBE`

## Authority

Owner unlimited-GOAL + 1A. Independent frozen probe after daily cadence kill.
Single a priori threshold: rebalance only when any lagged G3 rate moves
**≥ 5 bp** vs its prior available observation. Not mined from weekly/daily
readouts beyond that one frozen constant. Not Strategy Tester. Not Model 0.

## Frozen design (pre-result)

| Item | Value |
|---|---|
| Probe ID | `V8_CARRY_RATE_EVENT_5BP_V1` |
| Mechanism | Same long-max / short-min deadband 0.25 book as daily; rebalance calendar = G3 rate-change events ≥ 5 bp |
| Symbols | EURUSD, GBPUSD, USDJPY |
| Control | Identical event calendar + 20d return percent scores + same deadband |
| Cost | Stress A 1.5 / B 3.0 pip RT |
| Train / holdout | 2018–2022 / 2023–2025 (holdout gated) |

Tool: `02. AlphaFactory/tools/v8_carry_differential_offline_probe.py --rebalance rate_event`  
Result: `preflight/v8_probe/20260713_V8_CARRY_RATE_EVENT_PROBE_RESULT_V1.json`

## Train result (candidate)

| Metric | Value |
|---|---|
| Trades | 24 |
| Trades / elapsed week | **0.092** |
| PF gross | 5.001 |
| PF stress A | 4.923 |
| PF stress B | 4.846 |
| Expectancy stress A | +224.3 pips / trade |

## Train control

| Metric | Value |
|---|---|
| Trades | 95 |
| Trades / elapsed week | 0.364 |
| PF stress A | 1.051 |

Candidate beats control on PF but **fails sample and cadence floors**
(`train_trades<80`, `train_cadence_below_structural_floor`). Holdout not
opened.

## Verdict

`KILL_AT_OFFLINE_PROBE`.

Event-driven rebalance collapses density further (24 trades / 0.09 per week).
High PF on sparse policy-change sleeves is the opposite of the North-Star
cadence requirement. No Model 0 promotion.

## Authority after this kill

| Action | Allowed? |
|---|---|
| Registry / prereg / Model 0 for this event book | No |
| Further threshold mining of bp / deadband from these results | No |
| Local self-research for a higher-frequency / independent exogenous surface | Yes |
| `EA_CarryPublicRates` engineering scaffold (compile only) | Yes — not evidence |

## Broker note

MT5 server: `MetaQuotes-Demo`. Falsification only.
