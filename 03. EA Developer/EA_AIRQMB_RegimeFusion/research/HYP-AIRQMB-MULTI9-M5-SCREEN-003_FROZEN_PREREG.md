# HYP-AIRQMB Multi-9 M5 SCREEN-003 — Headless Frozen Preregistration

Frozen before any SCREEN-003 tester launch and before any performance outcome from BASE-001 or SCREEN-002 existed. Both predecessors were stopped before report generation.

## Mechanism and implementation identity

The trading equations, risk rules, dates, universe and small grid are unchanged from SCREEN-002. The only successor change is an outcome-independent integration optimization: all three `iCustom` handles receive their original calculation/model defaults explicitly while AIRD chart background/dashboard/pane/labels/matrix, MBB display objects and all indicator alerts are disabled. Public buffers and numerical rules remain unchanged.

- Source SHA-256: `B8AA382C4586646D8C932765B34E6DA10F97C90925D67BC19BFC7FFF4ED623A8`
- EA contract SHA-256: `1FDC453718A1D306AB67D686AAD4B96B892A9B45400CF267136A4071211C81E5`
- Compile: `0 errors, 0 warnings`
- Non-repaint: decisions read only shift 1/2; `iTime(...,0)` is a clock only
- Indicator source/runtime hashes remain those frozen in SCREEN-002.

EX5 is snapshotted per run but is not a durable prereg key because MetaEditor output bytes vary across recompiles of unchanged source.

## Ordered cells and screen contract

Independent IDs are `HYP-AIRQMB-<SYMBOL>-M5-SCREEN-003` for EURUSD, USDJPY, GBPUSD, USDCHF, USDCAD, AUDUSD, NZDUSD, XAUUSD and BTCUSD. Magics remain `5686101..5686109` in that order.

- Screen dates/model: `2023.01.02–2024.12.31`, Model 4.
- Deposit/leverage: `100000 USD / 1:100`; current tester spread.
- Identity overrides: expected symbol, SCREEN-003 hypothesis ID, symbol magic, research auto on, variant `SCREEN003_HEADLESS_MODEL4`.
- Strategy defaults: confidence `0.45`, stop `1.00` half-width, target `1.50R`, risk `0.25%`, spread/stop `0.15`, three entries/day, five-bar cooldown, max hold 48 bars, `07:00–20:00 UTC`, daily/Friday flat `20:00 UTC`.

Grid authorization requires compile/receipt/indicator/lifecycle reconciliation pass, history quality `>97%`, at least 100 trades, both directions each `>=20%`, cadence `1.5–6.0/week`, Model-4 PF `>=1.10`, positive expectancy and equity DD `<=8%`.

## Frozen grid and downstream locks

Only screen survivors may run the nine Model-4 combinations of confidence `{0.35,0.45,0.55}` and target `{1.25R,1.50R,1.75R}` with stop fixed `1.00`. Stable-neighbor median expectancy selects one pair; ties prefer higher confidence then lower target.

That pair is frozen before Model-0 confirmation on the same training window. Validation `2025` and holdout `2026.01.01–2026.07.31` remain locked in order. Model 4 cannot authorize economic-valid, cost validity or promotion. No session, weekday, year, direction, lane, indicator or stop search is authorized.

