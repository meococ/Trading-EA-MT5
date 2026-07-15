# V8 Carry×Vol Regime Offline Probe Readout — 2026-07-13

Status: `KILL_AT_OFFLINE_PROBE`

## Authority

Owner night override: **no ChatGPT / GPT Deep Research**; local self-research
only. Probe implements the pre-frozen join contract
`preflight/v8_exogenous/20260713_V8_CARRY_VOL_JOIN_CONTRACT_V1.md` (Menkhoff-style
global FX vol innovation gate on point-in-time G3 short-rate carry).

Independent of killed weekly / daily / rate-event carry-rank books and of
`HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`. Not Strategy Tester. Not Model 0.

Tool: `02. AlphaFactory/tools/v8_carry_vol_regime_offline_probe.py`  
Result: `preflight/v8_probe/20260713_V8_CARRY_VOL_REGIME_PROBE_RESULT_V1.json`

## Frozen design (pre-result)

| Item | Value |
|---|---|
| Probe ID | `V8_CARRY_VOL_REGIME_V1` |
| Mechanism | Hold signed G3 carry on H4 only when AR(1) expanding residual of cross-pair daily |log-return| sigma is non-positive; flatten when positive |
| Symbols | EURUSD, GBPUSD, USDJPY |
| Session | Mon–Thu H4 decisions; Friday flat |
| Stops | 1.5×ATR14_H4; time-stop 6 bars |
| Cost | Stress A 1.5 / B 2.5 pip RT |
| Control | Sign of prior 20 H4 returns; same stops/costs/weekend |
| Train / holdout | 2021–2023 / 2024–2025 (holdout gated) |

## Train result (candidate)

| Metric | Value |
|---|---|
| Trades | 423 |
| Trades / elapsed week | **2.707** |
| PF gross | 1.030 |
| PF stress A | **0.947** |
| PF stress B | 0.896 |
| Expectancy stress A | **-0.97 pips / trade** |

## Kill reasons

- `train_pf_stress_a<1.10`

Cadence clears the structural floor and sits inside the North-Star 2–5/week
band, but **expectancy after stress cost is negative**. Holdout was not opened.

## Verdict

`KILL_AT_OFFLINE_PROBE`.

This falsifies the claim that a Menkhoff-style vol-innovation gate alone turns
public-rate carry into a positive-expectancy H4 book on the three G3 pairs
under demo history + pip stress. High cadence without edge is not a survivor.

## Explicit non-rescues

Do **not** post-hoc:

- retune deadband 0.25, ATR multiple, time-stop, or vol AR window from this
  readout;
- add session/hour filters mined from the 423 trades;
- promote `EA_CarryPublicRates` or any carry scaffold to Model 0.

## Authority after this kill

| Action | Allowed? |
|---|---|
| Registry / prereg / Model 0 for this carry×vol book | No |
| Independent exogenous surface (e.g. lagged COT / equity-bond) with new frozen probe | Yes |
| Compile/backtest of killed carry scaffolds as promotion evidence | No |

## Broker note

MT5 server observed in result JSON (MetaQuotes-Demo falsification only).
Same-broker Real cost provenance remains required before any meaningful Model 0
outcome claim.
