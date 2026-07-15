# V8 Carry Differential Offline Probe Readout — 2026-07-13

Status: `KILL_AT_OFFLINE_PROBE`

## Authority

Owner unlimited-GOAL + 1A evidence quality. ChatGPT Deep Research V8 remains
`BLOCKED_BY_BROWSER_AUTH`. This local probe falsifies one reconstructable
public-rates carry book on MetaQuotes-Demo D1 history. It is **not** Strategy
Tester evidence and **not** EA/compile/backtest authority.

## Frozen design (pre-result)

| Item | Value |
|---|---|
| Mechanism | Point-in-time G3 short-rate differential; Friday D1 rebalance; hold single highest positive-carry pair |
| Symbols | EURUSD, GBPUSD, USDJPY |
| USD leg | DFF merged with SOFR; lag +1 calendar day |
| EUR leg | ECB DFR SDMX; lag +1 |
| GBP leg | BoE IUDBEDR; lag +1 |
| JPY leg | BoJ uncollateralized overnight call; lag +2 |
| Control | Identical portfolio with 20-day lagged spot-return scores (rates unused) |
| Cost | Stress A 1.5 pip RT; Stress B 3.0 pip RT |
| Train / holdout | 2018–2022 / 2023–2025 (holdout gated behind train pass) |

Tool: `02. AlphaFactory/tools/v8_carry_differential_offline_probe.py`  
Result: `preflight/v8_probe/20260713_V8_CARRY_DIFF_PROBE_RESULT_V1.json`

## Train result (candidate)

| Metric | Value |
|---|---|
| Trades | 13 |
| Trades / elapsed week | **0.050** |
| PF gross | 1.764 |
| PF stress A | 1.751 |
| PF stress B | 1.739 |
| Expectancy stress A | +121.5 pips / trade |

## Train control

| Metric | Value |
|---|---|
| Trades | 86 |
| Trades / elapsed week | 0.330 |
| PF stress A | 0.899 |

Candidate beats control on PF but **fails sample and cadence floors**
(`train_trades<80`, `train_cadence_below_structural_floor`). Holdout was
**not** inspected (train fail-closed).

## Verdict

`KILL_AT_OFFLINE_PROBE`.

This is the classic GOAL non-goal: attractive PF on a sparse sleeve that cannot
deliver 2–5 trades/week. Weekly cross-sectional public-rate carry alone is not
a North-Star book under the current contract.

## Explicit non-rescues

Do **not** post-hoc:

- switch to daily rebalance / multi-pair concurrent books after seeing this
  readout;
- add price momentum, volatility, or session filters mined from these 13 trades;
- rename as `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`.

Any higher-frequency carry-linked state needs an **independent** frozen design
(preferably after Deep Research V8 once ChatGPT auth is restored), new probe ID,
and a mechanism-matched control that still isolates rates from spot path.

## Authority after this kill

| Action | Allowed? |
|---|---|
| Registry append for this exact weekly book | No |
| Prereg / EA / compile / Model 0 | No |
| Deep Research V8 submit (after ChatGPT login) | Yes (unlimited-GOAL) |
| New independent rates hypothesis with new frozen probe | Yes, after de-dup |

## Broker note

MT5 server observed: `MetaQuotes-Demo`. Falsification only. Same-broker Real
cost provenance remains required before any meaningful Model 0 outcome claim.
