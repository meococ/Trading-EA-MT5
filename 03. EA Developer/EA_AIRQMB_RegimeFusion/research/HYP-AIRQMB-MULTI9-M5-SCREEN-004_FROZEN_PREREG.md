# HYP-AIRQMB Multi-9 M5 SCREEN-004 - Tester-Safe Frozen Preregistration

Frozen before any SCREEN-004 tester launch and before any performance outcome from BASE-001, SCREEN-002 or SCREEN-003 existed. All predecessor launches were stopped before report generation.

## Mechanism and implementation identity

The trading equations, risk rules, dates, universe and bounded grid are unchanged. The successor is an outcome-independent integration repair:

- the EA requests all three `iCustom` indicators with their canonical default inputs, eliminating dependency on a long variadic input schema;
- AIRD, MBB and QQE skip only chart-object and alert work when `MQL_TESTER` is true;
- mathematical/model state and all public decision buffers are unchanged;
- decisions remain closed-bar only (shift 1/2); server-side SL/TP remains tick-accurate.

Frozen source bindings:

- EA source SHA-256: `AB4D63AD66984636F1E8D6D6291B91280220D85E30E52ECB04F1ACF7F40FC4B0`
- AIRD source SHA-256: `5B2F6D3B79E2287C996D634EDD0225433A56B3A929228899954D908487EC1113`
- MBB source SHA-256: `6688DF927D7D465ADC5BC11CBF6D03FA6AB36DC4022D8C76962D8763FD4D9071`
- QQE source SHA-256: `BFF6DED22B0607BBC81A928175995708BFB8F3F72E75EA329835BBC74A697981`
- EA contract SHA-256: `1FDC453718A1D306AB67D686AAD4B96B892A9B45400CF267136A4071211C81E5`
- Compile: EA and all three indicators `0 errors, 0 warnings`

EX5 bytes are recorded per run but are not a durable preregistration key because MetaEditor output may vary across recompiles of unchanged source.

## Ordered cells and screen contract

Independent IDs are `HYP-AIRQMB-<SYMBOL>-M5-SCREEN-004` for EURUSD, USDJPY, GBPUSD, USDCHF, USDCAD, AUDUSD, NZDUSD, XAUUSD and BTCUSD. Magics remain `5686101..5686109` in that order.

- Screen dates/model: `2023.01.02-2024.12.31`, Model 4.
- Deposit/leverage: `100000 USD / 1:100`; current tester spread.
- Strategy defaults: confidence `0.45`, stop `1.00` MBB half-width, target `1.50R`, risk `0.25%`, spread/stop `0.15`, three entries/day, five-bar cooldown, max hold 48 bars, `07:00-20:00 UTC`, daily/Friday flat `20:00 UTC`.
- Identity overrides: expected symbol, SCREEN-004 hypothesis ID, symbol magic, research auto on, variant `SCREEN004_TESTERSAFE_MODEL4`.

A symbol survives only if compile, receipt, indicator initialization and lifecycle reconciliation pass; history quality is above 97%; trades are at least 100; both directions are at least 20%; cadence is `1.5-6.0/week`; provisional Model-4 PF is at least 1.10; expectancy is positive; and equity DD is at most 8%.

## Frozen grid and downstream locks

Only screen survivors may run the nine Model-4 combinations of confidence `{0.35,0.45,0.55}` and target `{1.25R,1.50R,1.75R}`, with stop fixed at `1.00`. Stable-neighbor median expectancy selects one pair; ties prefer higher confidence then lower target.

That pair is frozen before Model-0 confirmation on the same training window. Validation `2025` and holdout `2026.01.01-2026.07.31` remain locked in order. Model 4 cannot authorize economic-valid, cost validity or promotion. No session, weekday, year, direction, lane, indicator or stop search is authorized.
