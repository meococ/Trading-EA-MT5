# V8 COT TFF LevMoney H4 Offline Probe Readout — 2026-07-13

Status: `KILL_AT_OFFLINE_PROBE`

## Authority

Owner night override: **no ChatGPT / GPT Deep Research**; local self-research.
Independent exogenous surface after four public-rates carry kills (weekly,
daily, rate-event, carry×vol). Uses lagged CFTC Traders in Financial Futures
leveraged-money net positioning. Not Strategy Tester. Not Model 0.

De-dup: independent of carry-rank / carry×vol books and of catastrophic
`EA_EqCloseFlow` S682–S685 (equity-close hour drift is a different, already
dead mechanism).

Tool: `02. AlphaFactory/tools/v8_cot_tff_levmoney_h4_offline_probe.py`  
Result: `preflight/v8_probe/20260713_V8_COT_TFF_LEVMONEY_H4_PROBE_RESULT_V1.json`

## Frozen design (pre-result)

| Item | Value |
|---|---|
| Probe ID | `V8_COT_TFF_LEVMONEY_H4_V1` |
| Signal | Lev_Money long − short on CME EURO FX / GBP / JPY; JPY sign flipped for USDJPY |
| Lag | `Report_Date + 4` calendar days (covers Friday ET release + buffer) |
| Deadband | 5,000 contracts (a priori) |
| Execution | Mon–Thu H4; Friday flat; 1.5×ATR14; time-stop 6 |
| Control | Sign of prior 20 H4 returns |
| Cost | Stress A 1.5 / B 2.5 pip RT |
| Train / holdout | 2021–2023 / 2024–2025 (holdout gated) |

## Train result

| Book | Trades | /week | PF stress A | Exp A (pips) |
|---|---:|---:|---:|---:|
| Candidate (COT) | 392 | **2.508** | **1.019** | +0.54 |
| Control (mom) | 973 | 6.226 | 0.870 | −2.17 |

## Kill reasons

- `train_pf_stress_a<1.10`

Cadence is North-Star-compatible and the book beats the matched momentum
control, but stress-A PF stays below the frozen 1.10 train floor. Holdout not
opened.

## Verdict

`KILL_AT_OFFLINE_PROBE`.

Lagged speculative positioning alone does not clear the first expectancy gate
under pip stress on G3 H4.

## Explicit non-rescues

Do **not** mine deadband, lag days, ATR, or session filters from these 392
trades. Any next COT child needs a new independent mechanism (for example a
pre-frozen change-in-positioning event design), not threshold rescue.

## Authority after this kill

| Action | Allowed? |
|---|---|
| Registry / prereg / Model 0 for this COT book | No |
| Further public exogenous surface or Phase-0 portfolio path | Yes, with new freeze |
| Treat near-miss PF 1.019 as promotion evidence | No |
