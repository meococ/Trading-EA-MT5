# HYP-COP-EURUSD-H1-001 — Frozen Coppock Zero-Cross Source Screen

## Authority and thesis

- One outcome-blind source/cadence scan only: `COP001-SOURCE-ATTEMPT-001`.
- Native FivePercent EURUSD H1 Bid bars; source bars `[2018-01-01, 2023-01-01)` UTC; full `<2023` history may be materialized only for fixed lookback.
- Data SHA256 `78BF655C67392A23690C80DB127E24997D0CD14264B573A3832D167C9361FCF3`; manifest SHA256 `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`.

This is a fresh price-only double-horizon momentum thesis, not a filter or revision of ERAY/KVO/DCX/Fisher. TradingView documents Coppock Curve as the sum of 11- and 14-period rates of change smoothed with a 10-period weighted moving average and interpreted relative to zero: https://www.tradingview.com/support/solutions/43000589114/ . TradingView is formula provenance only, not parity or acceptance. Applying the bar-count formula to H1 and using symmetric FX zero crossings are explicit frozen research choices.

## Exact formula and event

- `ROC_n(t)=100*(Close_t/Close_(t-n)-1)` for `n in {11,14}`.
- `Raw_t=ROC_11(t)+ROC_14(t)`, first finite at index 14.
- `Curve_t=sum(k*Raw_(t-10+k), k=1..10)/55`; oldest weight 1, current weight 10; first finite at index 23.
- LONG raw event at completed bar `t>=24`: `Curve_(t-1)<=0 && Curve_t>0`.
- SHORT raw event: `Curve_(t-1)>=0 && Curve_t<0`.
- Current zero emits nothing; prior zero may arm a strict cross. Conflicts fail closed.

All full-history prices must be finite, positive and geometrically valid. No EMA, volume, filter, threshold, persistence, debounce, cooldown, session or direction selection exists.

An event is executable only if its immediate next physical row is both UTC `+1h` and source epoch `+3600`, with decision before 2023. Gap events are counted and consumed, not queued. No next-row OHLC. Annual gates use decision UTC year.

## Gates and boundary

All must pass: design rows >=25,000; feature coverage >=99%; exact-next coverage >=97%; executable events >=500; pooled cadence 2.0–5.0/week; each direction >=30%; max decision-year share <=30%; each 2018–2022 decision-year cadence 1.25–6.50/week; zero conflicts; deterministic replay.

Failure parks this exact mapping without economics. A pass authorizes only a separately reviewed direct MQL5 build/parity stage. No MT5, trades, costs, returns, PF, optimization, validation, holdout, paper or live authority is granted.
