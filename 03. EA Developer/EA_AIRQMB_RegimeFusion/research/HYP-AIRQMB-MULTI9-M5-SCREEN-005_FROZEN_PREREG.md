# HYP-AIRQMB Multi-9 M5 SCREEN-005 - Closed-Bar Fast-Path Preregistration

Frozen before any SCREEN-005 tester launch and before any performance outcome from BASE-001 through SCREEN-004 existed. All predecessor launches were stopped before report generation.

## Mechanism and implementation identity

Trading equations, defaults, risk rules, dates, universe and bounded grid are unchanged. The only outcome-independent successor change is execution cadence inside `MQL_TESTER`: each indicator returns immediately for repeated ticks within the same M5 bar. On the first tick of the next bar it fully recalculates the just-closed bar from final OHLC. The EA reads only shifts 1/2, so the decision series is invariant; server-side SL/TP remains tick-accurate.

Frozen source bindings:

- EA source SHA-256: `AB4D63AD66984636F1E8D6D6291B91280220D85E30E52ECB04F1ACF7F40FC4B0`
- AIRD source SHA-256: `D010798CDEDAEF77CB4F8F8C4BE51A8B35F17EBFC298EBB64A0B329060746759`
- MBB source SHA-256: `2E96AEFE68F1F094FF9FA2CE23802CB94D5592F8526B29A30BE393E1340544B3`
- QQE source SHA-256: `22456C83C73D2070F52D83BBCE7D5DC1982CD987F8BE807E10482703982CAF9A`
- EA contract SHA-256: `1FDC453718A1D306AB67D686AAD4B96B892A9B45400CF267136A4071211C81E5`
- Compile: EA and all three indicators `0 errors, 0 warnings`

## Ordered cells and screen contract

Independent IDs are `HYP-AIRQMB-<SYMBOL>-M5-SCREEN-005` for EURUSD, USDJPY, GBPUSD, USDCHF, USDCAD, AUDUSD, NZDUSD, XAUUSD and BTCUSD. Magics remain `5686101..5686109` in that order.

- Screen dates/model: `2023.01.02-2024.12.31`, Model 4 real ticks.
- Deposit/leverage: `100000 USD / 1:100`; current tester spread.
- Strategy defaults: confidence `0.45`, stop `1.00` MBB half-width, target `1.50R`, risk `0.25%`, spread/stop `0.15`, three entries/day, five-bar cooldown, max hold 48 bars, `07:00-20:00 UTC`, daily/Friday flat `20:00 UTC`.
- Identity overrides: expected symbol, SCREEN-005 hypothesis ID, symbol magic, research auto on, variant `SCREEN005_CBARFAST_MODEL4`.

A symbol survives only if compile, receipt, indicator initialization and lifecycle reconciliation pass; history quality is above 97%; trades are at least 100; both directions are at least 20%; cadence is `1.5-6.0/week`; PF is at least 1.10; expectancy is positive; and equity DD is at most 8%.

## Frozen grid and downstream locks

Only screen survivors may run the nine Model-4 combinations of confidence `{0.35,0.45,0.55}` and target `{1.25R,1.50R,1.75R}`, with stop fixed at `1.00`. Stable-neighbor median expectancy selects one pair; ties prefer higher confidence then lower target.

That pair is frozen before an independent confirmation run on the same training window. Validation `2025` and holdout `2026.01.01-2026.07.31` remain locked in order. The initial screen cannot by itself authorize economic validity, cost validity or promotion. No session, weekday, year, direction, lane, indicator or stop search is authorized.
