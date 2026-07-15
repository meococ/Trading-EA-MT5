# V8 Equity–Bond Differential Offline Probe Readout — 2026-07-13

Status: `KILL_AT_OFFLINE_PROBE`

## Authority

Owner skip-GPT self-research after V8 campaign closeout. Implements
`preflight/v8_exogenous/20260713_V8_EQUITY_BOND_DIFF_JOIN_CONTRACT_V1.md`.
MetaQuotes-Demo falsification only. Not Strategy Tester. Not Model 0.

Tool: `02. AlphaFactory/tools/v8_equity_bond_diff_offline_probe.py`  
Result: `preflight/v8_probe/20260713_V8_EQUITY_BOND_DIFF_PROBE_RESULT_V1.json`  
(result SHA256 `f380d2b5d39219adcf66ea9411aaa7c7fee18281190fed0c91886dcad03701d3`)  
Trades CSV SHA256 `47e7d82de1d85db4478d559a6bfdbba3d2ffc5641b300da2f2003559a61943e1`

## Frozen design (pre-result)

| Item | Value |
|---|---|
| Probe ID | `V8_EQUITY_BOND_DIFF_V1` |
| Signal | `z(r_eq − r_bond)` with `r_bond = −7.0 · ΔDGS10` (decimal); thresh ±0.75 |
| Map | risk-on → USD weak; risk-off → USD strong |
| Lag | observation date + 1 calendar day |
| Basket | equal-weight EURUSD / GBPUSD / USDJPY |
| Controls | equity-only (must beat); bond-only diagnostic |
| Cost | Stress A 1.5 / B 3.0 pip RT per leg, mean-aggregated |

## Train result

| Metric | Candidate | Equity-only | Bond-only |
|---|---|---|---|
| Trades | 282 | 277 | 309 |
| Trades / week | 1.35 | 1.33 | 1.48 |
| PF stress A | **1.004** | 0.858 | 1.131 |
| Expectancy A | +0.08 | −3.48 | +2.64 |
| Year conc. | 0.347 | — | — |

**Kill:** `train_pf_stress_a<1.10`. Holdout gated shut.

## Non-rescues

Do not retune z, MOD_DUR, ATR, or add VIX/ECB from this readout.
Do not mint bond-only as a child from this kill.
Do not reopen carry/COT.

## Authority

| Action | Allowed? |
|---|---|
| Registry / prereg for this book | **No** |
| EA / compile / Model 0 | **No** |
