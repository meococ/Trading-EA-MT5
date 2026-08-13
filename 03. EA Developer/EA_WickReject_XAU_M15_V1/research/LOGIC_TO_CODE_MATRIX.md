# Logic-to-code matrix — HYP-CBWR-XAUUSD-M15-003

| ID | Trader decision | Frozen rule | Closed-bar information | Telemetry / verification |
|---|---|---|---|---|
| L01 | Extreme rejection anatomy | directional wick/range >=0.60; body/range <=0.35; close in directional half | signal bar shift 1 | `CBWR003_SIGNAL` wick/body/close-location |
| L02 | Local auction extreme | signal extreme within 0.15 ATR14 of shifts 2..9 extreme | shifts 1..9 only | swing level in signal log |
| L03 | Tradable volatility | ATR14 shift 1 / mean ATR14 shifts 2..51 in [0.70,2.20] | closed indicator buffers only | ATR/average/ratio in signal log |
| L04 | Causal execution | submit only on first tick of next M15 bar | decision shift 1, availability new bar | decision and availability epochs |
| L05 | Structural risk | wick extreme +/-0.25 ATR, entry risk clamp 1.20..2.80 ATR | signal bar plus actual quote | entry, SL and initial risk log |
| L06 | Exit geometry | TP 1.60R; BE +0.90R plus entry-spread buffer; 12-bar stop | actual position/ticks after entry | BE and exit logs with MFE/MAE |
| L07 | Prop-style risk | 0.60% equity risk; 1.50% daily and 3.50% weekly entry halts | account equity at server day/week anchors | summary risk-lock count |
| L08 | Flat book | server 21:50 daily, Friday 20:00, no weekend entry | current server clock only | explicit exit reason |
| L09 | Matched control | remove only the swing-contact requirement | same signal/entry/exit/cost surface | variant tag in every signal/init |

State sequence: `NEW_M15_BAR -> CLOSED_BAR_VALID -> ATR_REGIME -> WICK_ANATOMY -> SWING_CONTACT -> SPREAD/RISK -> MARKET_ENTRY -> BE|SL|TP|TIME/DAILY/FRIDAY_EXIT`. Duplicate decisions are suppressed by the signal bar epoch. Every unavailable or invalid input exits fail-closed.
