# Frozen prereg — HYP-TPR-EURUSD-M5-001

Status: FROZEN before compile and outcome-bearing execution on 2026-08-12.

Origin: Grok `/deep-research-trading-meta5` loop 3 after the positive-but-sparse XAU compression-break object was killed. This is a fresh EURUSD M5 trend-pullback-resumption state machine, not a parameter revision.

## Signal

- Completed M5 bars only; next-bar first-tick market entry; one position; maximum hold two hours; no weekend.
- Native ATR14, EMA8 and EMA21, all terminal shift 1.
- Trend long: EMA8 > EMA21, close > EMA8, bullish body >=0.35 ATR, and highest-high minus lowest-low of shifts 1..5 >=1.60 ATR. Short is symmetric.
- Within the next seven bars, long requires a bearish pullback whose low <= EMA8 -0.15 ATR; short is symmetric. Store that pullback bar.
- Within nine bars of trend definition, entry requires the first directional bar closing beyond EMA8 with body/range >=0.40. Otherwise cancel. Entry spread must be <=18 points.
- Primary `TPR_PRIMARY`; locked control `EMA_BODY_CONTROL` enters any body/range >=0.40 bar aligned with EMA8 vs EMA21 using identical downstream rules.

## Stop, exit and risk

- Long structural stop: `min(pullback low, EMA21 on resumption bar) -0.25 ATR`; short symmetric; entry-distance clamp `[1.10,2.40] ATR`.
- No fixed TP or partial close. At +1.00R move to entry +0.10R; at +1.60R arm a closed-bar trail at 0.75 ATR from the latest close; never loosen. Time stop 24 M5 bars.
- Daily flat 21:50 server, Friday flat 19:00. Daily/weekly entry locks at 1.10%/2.80% equity loss.
- Final volume is the normalized-down minimum of 0.35%-stop-risk volume, 4.50x-equity notional volume and 12%-free-margin volume. Recheck notional and margin after normalization.

## Design gate

Primary design window EURUSD M5 Model 0 `[2018-01-01,2022-01-01)`. Kill immediately for runtime/data invalidity, margin failure, trades <160 or >600, PF <1.10, expectancy <=0, DD >7%, or top three exits >45% of total net. Advance to matched control and OOS only with 160..600 trades, PF >=1.10, positive expectancy, DD <=7%, margin <=12%, top three <=40% net and reconciled telemetry.

OOS 2022-2023 and holdout 2024-latest remain inaccessible until the design gate passes. No optimization, session/day/direction filtering, cross-symbol transfer or live action is authorized by this prereg.
