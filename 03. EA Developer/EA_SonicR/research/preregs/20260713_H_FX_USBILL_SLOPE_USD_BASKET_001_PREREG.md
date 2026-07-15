# HYP-SR-FX-USBILL-SLOPE-USD-BASKET-001 Preregistration

Date: 2026-07-13

State: `killed` (Model 0 research-pass FAIL 2026-07-14; offline was PROBE_SURVIVOR)

## Identity

- Hypothesis ID: `HYP-SR-FX-USBILL-SLOPE-USD-BASKET-001`
- Probe tag: `V8_USBILL_SLOPE_USD_BASKET_V1`
- Parent candidate: null
- Author/session: Lead quant self-research (skip-GPT); de-dup clearance
  `readouts/20260713_USBILL_SLOPE_VS_USD_FACTOR_DEDUP_CLEARANCE.md`
- Feature family: `us_treasury_bill_slope_usd_basket_d1`
- Lane: `fx_d1_exogenous_bill_slope_research`
- Symbol/timeframe: `EURUSD,GBPUSD,USDJPY` / D1 basket
- Window: train `[2019-01-01, 2023-01-01)`; holdout `[2023-01-01, 2026-01-01)`
  (Model 0 screen used full 2019.01.01–2025.12.31)

## Thesis

Lagged US Treasury bill curve slope (26W−4W) encodes USD funding / front-end
curve regime information that maps to a fixed equal-weight USD basket on
closed D1 bars, independent of contemporaneous FX-return cross-section
ranking and pullback-break architecture.

## De-dup

Independent of `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` (no FX-return factor,
no strongest-pair routing, no pullback-break). Independent of killed V8 carry /
COT / carry×vol / equity–bond differential books.

## Locked Design

Frozen in
`preflight/v8_exogenous/20260713_V8_USBILL_SLOPE_USD_BASKET_PROBE_CONTRACT_V1.md`:

- `slope = 26W − 4W` bill rates; `available_at = obs_date + 1d`
- `z` over prior 60 with ≥40 obs; thresh ±0.75
- Basket legs for USD strength/weakness; Mon–Thu; Friday flat
- Stop 1.5×ATR14_D1; time-stop 5 bars
- Control: same |z| gate; direction from 20d USD spot proxy
- Stress A/B = 1.5 / 3.0 pip RT per leg (synthetic; **not** Real broker cost)

## Banned post-result edits

No retune of z, tenor, ATR, time-stop, session, or pair set from the survivor
readout or Model 0 readout. No hour/day/year filters. No missing-cost-as-zero.

## Offline probe result (binding)

- Readout: `readouts/20260713_V8_USBILL_SLOPE_USD_BASKET_OFFLINE_PROBE_READOUT.md`
- Result JSON: `preflight/v8_probe/20260713_V8_USBILL_SLOPE_USD_BASKET_PROBE_RESULT_V1.json`
- Status: `PROBE_SURVIVOR` under probe floors
- GOAL gaps: cadence ~1.0–1.1/week < 2–5; train PF-A ~1.09 < 1.30; cost provenance gap

## Model 0 closeout (2026-07-14)

- EA: `03. EA Developer/EA_UsBillSlopeBasket/`
- Control `20260714_013628` InpMode=0: PF **1.05**, net $586.28, 1124 trades
- Challenger `20260714_014003` InpMode=1: PF **1.03**, net $383.49, 989 trades
- Verdict: **`KILLED_AT_MODEL_0`** (fail beat control; fail PF>1.30; cost unverified)
- Readout: `readouts/20260714_HYP_SR_FX_USBILL_SLOPE_USD_BASKET_001_MODEL0_READOUT.md`
