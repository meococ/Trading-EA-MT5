# Lead De-Dup Clearance — US Bill-Slope vs USD-Factor — 2026-07-13

Status: `INTAKE_CLEARED / INDEPENDENT`

## Question

Is `V8_USBILL_SLOPE_USD_BASKET_V1` /
`HYP-SR-FX-USBILL-SLOPE-USD-BASKET-001` a rename of
`HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`?

## Comparison

| Dimension | USD-FACTOR-001 | US bill-slope basket |
|---|---|---|
| Causal driver | Contemporaneous **FX-return** common-USD factor | Lagged **US Treasury bill curve slope** (26W−4W) |
| Selection | Strongest aligned pair among EUR/GBP/JPY | Equal-weight fixed basket; no pair rank |
| Entry | Fixed pullback-break on strongest pair | Regime z-threshold → basket direction |
| Timeframe | Synchronized closed M15 | Closed D1 Mon–Thu / Friday flat |
| Cost gate | Explicit same-broker tick bid/ask required | Offline synthetic stress only (gap noted) |

## Verdict

**Independent.** Fail-closed rename risk is **not** triggered.
Prior `intake-blocked pending de-dup` stop is lifted for this probe ID only.

## Caveats (do not inflate)

- Offline `PROBE_SURVIVOR` ≠ GOAL `confirmed`.
- Cadence ~1.0–1.1 basket trades/week is below North-Star 2–5.
- Train PF-A beat vs control is thin (~+0.003).
- Real broker cost provenance still missing (`FivePercentOnline-Real`).
- No EA / compile / Model 0 until cost capture + separate Model 0 prereg.

## Evidence cited

- Prereg USD-factor: `preregs/20260711_H_FX_CROSS_SECTIONAL_USD_FACTOR_001_PREREG.md`
- Bill-slope contract + readout + result JSON under `preflight/v8_exogenous/` /
  `readouts/` / `preflight/v8_probe/` dated 2026-07-13
