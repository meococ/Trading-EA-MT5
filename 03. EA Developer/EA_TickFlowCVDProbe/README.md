# EA_TickFlowCVDProbe

Collection-only MT5 Expert Advisor retained as the terminal source record for
`HYP-TFCVD-XAUUSD-M5-001`.

The probe translates TradingView's intrabar Volume Delta polarity idea into a
broker-native quote-tick delta that can be reproduced in MT5 Strategy Tester
Model 4 and on a live MT5 quote stream. It deliberately calls the feature
`quote_tick_delta`, not executed-volume CVD: XAUUSD CFD ticks may not expose
exchange trade volume or aggressor side.

The EA:

- accepts only XAUUSD M5 with the frozen hypothesis ID;
- aggregates only causally observed `OnTick` Bid/Ask updates;
- closes each feature row when the next M5 bar begins;
- uses uptick/downtick polarity and carries the previous non-zero polarity over
  unchanged mids, matching the documented intrabar-delta convention;
- writes `XAUUSD_TickFlow_StateTelemetry_*.csv` in the tester-local Files area;
- never sends, modifies or closes orders.

The only frozen run (`20260809_011952`) is a terminal source-feasibility KILL:
MT5 reported 0% History Quality, the journal proved broker-native XAUUSD real
ticks begin only in 2026, and the generated 2018–2022 path produced zero frozen
absorption candidates across 351,302 completed bars. See
`research/HYP-TFCVD-XAUUSD-M5-001_RESULT.md`.

This package has no rerun, economic, optimization, validation, promotion,
paper or live authority. It remains compilable for audit only.
