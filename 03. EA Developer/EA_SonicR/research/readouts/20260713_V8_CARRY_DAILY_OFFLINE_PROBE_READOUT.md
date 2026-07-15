# V8 Carry Daily Rank Offline Probe Readout — 2026-07-13

Status: `KILL_AT_OFFLINE_PROBE`

## Authority

Owner unlimited-GOAL + 1A evidence quality. Independent frozen probe — **not** a
post-hoc rescue of the Friday-weekly kill (`V8_CARRY_DIFF_WEEKLY_V1`). Constants
were locked a priori to match the `EA_CarryPublicRates` scaffold (deadband 0.25,
long max / short min). Not Strategy Tester. Not Model 0 / promotion authority.

## Frozen design (pre-result)

| Item | Value |
|---|---|
| Probe ID | `V8_CARRY_DAILY_RANK_V1` |
| Mechanism | Point-in-time G3 short-rate differential; daily D1 rebalance; long max / short min when spread ≥ 0.25; hold until flip or flat |
| Symbols | EURUSD, GBPUSD, USDJPY |
| Deadband | 0.25 percentage points (max−min pair differential) |
| Control | Identical long/short book with 20d lagged spot-return scores in percent; same deadband |
| Cost | Stress A 1.5 pip RT; Stress B 3.0 pip RT |
| Train / holdout | 2018–2022 / 2023–2025 (holdout gated) |

Tool: `02. AlphaFactory/tools/v8_carry_differential_offline_probe.py --rebalance daily`  
Result: `preflight/v8_probe/20260713_V8_CARRY_DAILY_PROBE_RESULT_V1.json`

## Train result (candidate)

| Metric | Value |
|---|---|
| Trades | 68 |
| Trades / elapsed week | **0.261** |
| PF gross | 2.196 |
| PF stress A | 2.141 |
| PF stress B | 2.087 |
| Expectancy stress A | +51.8 pips / trade |

## Train control

| Metric | Value |
|---|---|
| Trades | 416 |
| Trades / elapsed week | 1.596 |
| PF stress A | 0.957 |

Candidate beats control on PF but **fails sample and cadence floors**
(`train_trades<80`, `train_cadence_below_structural_floor`). Holdout was
**not** inspected (train fail-closed).

## Verdict

`KILL_AT_OFFLINE_PROBE`.

Daily rebalance raises density vs weekly (13 → 68 trades) but remains far below
the structural 0.5 trades/week floor and the North-Star 2–5/week band. Attractive
stress-A PF on a sparse long/short sleeve is not a cadence-viable book.

## Explicit non-rescues

Do **not** post-hoc:

- mine deadband / ATR / Friday-flat from this readout;
- promote `EA_CarryPublicRates` compile SUCCESS to Model 0 evidence;
- threshold-tune the next idea from these 68 trades.

One further independent frozen probe ran separately: rate-change event
rebalance (≥5 bp any G3 leg), new ID, no mining beyond that single frozen 5 bp
(see `20260713_V8_CARRY_RATE_EVENT_OFFLINE_PROBE_READOUT.md`).

## Authority after this kill

| Action | Allowed? |
|---|---|
| Registry / prereg / Model 0 for this daily book | No |
| `EA_CarryPublicRates` as engineering scaffold only | Yes (compile already SUCCESS) |
| Independent rate-event probe (frozen 5 bp) | Yes |

## Broker note

MT5 server observed: `MetaQuotes-Demo`. Falsification only.
