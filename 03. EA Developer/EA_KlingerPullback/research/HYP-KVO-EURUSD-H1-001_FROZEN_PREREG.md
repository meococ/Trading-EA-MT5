# HYP-KVO-EURUSD-H1-001 — Frozen Klinger Pullback Re-entry Source Screen

## Authority boundary

- Stage: one outcome-blind source/cadence scan only.
- Symbol/timeframe: native FivePercent `EURUSD` H1 Bid bars.
- Scored source-bar window: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`.
- Full source prehistory before 2018 is required once for recursive state; no reset at 2018.
- Attempt: `KVO001-SOURCE-ATTEMPT-001`, limit one, no retry.
- Data SHA256: `78BF655C67392A23690C80DB127E24997D0CD14264B573A3832D167C9361FCF3`.
- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`.

This is a materially new hypothesis. It does not tune or filter the parked ERAY object. It tests the standard Klinger range-path/volume-force oscillator inside its documented long-trend pullback/re-entry setup. FivePercent `tick_volume` is an unsigned broker-activity proxy only; it is not exchange volume, money flow, cash flow, aggressor flow, CVD or VPIN.

Formula provenance: TradingView Klinger Oscillator documentation, https://www.tradingview.com/support/solutions/43000589157-klinger-oscillator/ . TradingView is provenance only, never parity or acceptance.

## Frozen formula

For ordered H1 rows:

- `S_t = High_t + Low_t + Close_t`.
- `DM_t = High_t - Low_t`.
- For `t>=1`, `T_t=+1` iff `S_t>S_(t-1)`; equality and decrease are exactly `-1`.
- `CM_1=DM_0+DM_1`.
- For `t>=2`, `CM_t=CM_(t-1)+DM_t` when `T_t=T_(t-1)`; otherwise `CM_t=DM_(t-1)+DM_t`.
- `VF_t=tick_volume_t*2*(DM_t/CM_t-1)*T_t*100` exactly, with no absolute value.

All prices and tick volume must be finite; tick volume must be integer and nonnegative. `CM_t==0` or invalid required input kills the attempt. No substitution, deletion, interpolation or reset.

SMA-seeded recursive EMAs:

- EMA34(VF) seeds at index 34 from `VF[1..34]`.
- EMA55(VF) seeds at index 55 from `VF[1..55]`.
- `KO=EMA34-EMA55`, first finite at 55.
- Signal EMA13(KO) seeds at 67 from `KO[55..67]`.
- EMA100(close) seeds at 99 from `Close[0..99]`.
- Each recurrence uses `alpha=2/(N+1)`.
- First possible arm is index 99; first possible event is index 100.

## Frozen FSM

States: `IDLE`, `LONG_ARMED`, `SHORT_ARMED`. Existing state is evaluated before any new arm. An IDLE bar may arm but never emit on that bar.

- LONG arms strictly on `KO<0 && Close>EMA100`.
- SHORT arms strictly on `KO>0 && Close<EMA100`.
- LONG trigger: prior `KO<=Signal`, current `KO>Signal`, current `KO<=0`, `Close>EMA100`.
- SHORT trigger: prior `KO>=Signal`, current `KO<Signal`, current `KO>=0`, `Close<EMA100`.
- Current KO/signal equality is not a cross; prior equality may cross. KO zero cannot arm but may complete an armed event.
- LONG remains armed only while `KO<=0 && Close>EMA100`; SHORT remains armed only while `KO>=0 && Close<EMA100`.
- Trigger, invalidation or opposite context resets state. No same-bar rearm after a reset/event. A new event needs a fresh extreme-side arm.
- Invalid feature state resets to IDLE. Ordinary H1 closures/gaps create no synthetic bars and do not reset recursion or a valid FSM state.

Only source bars in the scoring window may emit. A raw event is executable only when the immediate next physical row has both UTC `+1h` and source epoch `+3600`, and the decision is before 2023. A gap event is counted and consumed, never queued. Never read next-row OHLC. Annual gates use decision UTC year.

## Gates

All must pass: at least 25,000 design rows; at least 99% feature coverage; at least 97% exact-next raw-event coverage; at least 500 executable events; pooled cadence 2.0–5.0/week; each direction at least 30%; no decision year above 30%; every 2018–2022 decision-year cadence 1.25–6.50/week; zero conflicts; deterministic replay.

Any failure parks this exact mapping without an economic conclusion. No period, signal threshold, trend average, timeframe, direction, session, cooldown, debounce, equality, volume treatment or FSM rescue is allowed under the same ID. A pass authorizes only a separately reviewed direct MQL5 implementation/parity stage; no MT5, trades, costs, PF, validation, holdout, paper or live authority exists here.
