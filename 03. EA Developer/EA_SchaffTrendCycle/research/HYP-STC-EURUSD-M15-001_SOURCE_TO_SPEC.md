# HYP-STC-EURUSD-M15-001 source-to-spec matrix

| Frozen requirement | MQL5 implementation | Focused evidence |
|---|---|---|
| Classic STC `23/50/10/3/3` | `PreloadIndicatorState()` + `AdvanceIndicatorState()` | formula constants and synthetic oracle tests |
| Fixed-origin recurrence | require synchronized exact `2015.01.02 09:00` through `2015.12.31 20:00` native-M15 population of `24,776` bars, then one update per completed bar | origin proof plus seed/window drift regression test |
| Double stochastic, EMA smoothing | `WindowRange()` + `EmaStep()` | reference formula test |
| Trend-cycle direction | 25/75 cross plus MACD sign | exact predicate tests |
| Completed M15 bars | one `CopyRates(...,1,1,...)` update and `SERIES_LASTBAR_DATE` scheduler | no-shift-zero test |
| Exact next M15 availability | decision-to-open delta must equal 900s | clock boundary test |
| One first eligible signal/day | consumed decision date before execution gates | daily throttle test |
| ATR14 1.5 stop, 1.5R target | direct Wilder ATR and outward tick normalization | risk geometry test |
| 0.25% downward risk sizing | `OrderCalcProfit`, step floor, margin, `OrderCheck` | risk/order test |
| 16-bar exit | `iBarShift` against position open time | time-exit test |
| No weekend hold | Friday 20:00 server flatten and weekend guard | weekend test |
| No indicator router/filter | no `iCustom`, ADX, session or HTF branch | identity scan |
| Untuned DESIGN only | exact runtime input validation and sealed prereg | contract/prereg tests |

Economic truth begins only after the AlphaFactory Model-0 report passes the
engineering and evidence gates.
