# V8 US Bill-Slope → USD Basket Offline Probe Readout — 2026-07-13

Status: `PROBE_SURVIVOR` (offline gates only)

## Authority

Owner night override: **no ChatGPT / GPT Deep Research**; local self-research
only. Implements the pre-frozen contract
`preflight/v8_exogenous/20260713_V8_USBILL_SLOPE_USD_BASKET_PROBE_CONTRACT_V1.md`
(SHA256 `C93E082B9F9BFB1C050A1FA01BF1082512D96F88BF9D069D2354613AE341538E`).

Independent of `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` (no FX-return factor /
pullback-break / strongest-pair routing) and of killed V8 carry / COT /
carry×vol books. MetaQuotes-Demo falsification only. Not Strategy Tester.
Not Model 0.

Tool: `02. AlphaFactory/tools/v8_usbill_slope_usd_basket_offline_probe.py`  
(SHA256 `A375730DAEE67ADD432C6813A70DDEB7C3C8A14C6F69EC420FF3CFC93A8AE777`)  
Result: `preflight/v8_probe/20260713_V8_USBILL_SLOPE_USD_BASKET_PROBE_RESULT_V1.json`  
(SHA256 `BE93F528537609E62C345E855E80EFB715CD88D88972535701C1444DA73BA8EC`)  
Trades CSV SHA256 `2767228FCA40F05E3A5C74A63F951641EDDC71DF2AB3D04029A8286135F729D9`

## De-dup (pre-result, honored)

| Closed / blocked family | Independence |
|---|---|
| `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` | Lagged US bill slope only |
| V8 carry weekly/daily/event | No G3 short-rate rank / differential |
| COT TFF / Carry×Vol | Different causal surface |

## Frozen design (pre-result)

| Item | Value |
|---|---|
| Probe ID | `V8_USBILL_SLOPE_USD_BASKET_V1` |
| Working ID | `HYP-SR-FX-USBILL-SLOPE-USD-BASKET-001` |
| Signal | `z(26W−4W)` ≥ +0.75 → USD strength; ≤ −0.75 → USD weakness |
| Lag | observation date + 1 calendar day |
| Basket | equal-weight EURUSD / GBPUSD / USDJPY (USD-direction legs) |
| Session | Mon–Thu D1 decisions; Friday flat |
| Stops | 1.5×ATR14_D1; time-stop 5 D1 bars |
| Cost | Stress A 1.5 / B 3.0 pip RT **per leg**, mean-aggregated |
| Control | Same \|z\| gate; direction = sign(20d USD spot proxy) |
| Train / holdout | `[2019-01-01, 2023-01-01)` / `[2023-01-01, 2026-01-01)` |

## Cost provenance (honest)

`COST_PROVENANCE_GAP`: stress haircuts are synthetic pips, not
FivePercentOnline-Real bid/ask / commission / side-aware slippage. Missing
broker cost fields are **not** zero. Offline survivor ≠ true-cost Model 0.

## Train result (candidate vs control)

| Metric | Candidate | Control |
|---|---|---|
| Trades | 237 | 250 |
| Trades / elapsed week | **1.136** | 1.198 |
| PF gross | 1.152 | 1.153 |
| PF stress A | **1.090** | 1.087 |
| PF stress B | 1.031 | 1.024 |
| Expectancy stress A | **+2.33 pips** | +2.11 pips |
| Year conc. (pos net-A) | 0.440 | — |

Train clears frozen floors (trades≥80, tpw≥0.5, PF-A≥1.05, beat control PF-A
**and** expectancy-A, year conc≤0.55). Control beat on PF-A is **thin**
(+0.0027); documented, not used to retune.

## Holdout result (gated open)

| Metric | Candidate | Control |
|---|---|---|
| Trades | 153 | 171 |
| Trades / elapsed week | **0.977** | 1.092 |
| PF stress A | **1.229** | 1.164 |
| PF stress B | **1.182** | 1.114 |
| Expectancy stress A | **+7.96 pips** | +5.16 pips |
| Year conc. (pos net-A) | 0.444 | — |

Holdout clears the contract’s gated checks (including beat control on PF-A and
expectancy-A, PF-B≥1.00, tpw in [0.5, 8], year conc≤0.55).

## Verdict

`PROBE_SURVIVOR` under the frozen offline contract.

Cadence (~1.0–1.1 basket trades/week) is **below** the North-Star 2–5/week
band but **above** this probe’s structural floor (0.5). That is a GOAL gap,
not a contract kill. Do not post-hoc raise the cadence floor from this readout.

## Explicit non-rescues / non-tunes

Do **not**:

- retune z=0.75, 26W−4W tenor, ATR multiple, or time-stop from this readout;
- mine hour/day/year filters;
- rename as `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`;
- treat synthetic stress as Real broker cost;
- compile / Strategy Tester / Model 0 until cost provenance is unblocked.

## Authority after this survivor

| Action | Allowed? |
|---|---|
| Registry row + frozen prereg path | Yes |
| EA build / compile / Model 0 | **No** until same-broker Real cost capture |
| QFSI login to `FivePercentOnline-Real` | Owner credentials required; do not invent |
| Post-hoc parameter rescue | No |

## Broker note

MT5 server in result JSON: `MetaQuotes-Demo`. Falsification only.
