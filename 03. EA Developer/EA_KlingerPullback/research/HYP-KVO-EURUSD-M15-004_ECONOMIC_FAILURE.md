# HYP-KVO-EURUSD-M15-004 — Economic baseline failure

Verdict: `KILL_BASE_PF_EXPECTANCY_CADENCE_AND_CONCENTRATION_FAIL`.

The sole untuned TRAIN baseline completed with valid engineering evidence. Run `20260810_212638` used EURUSD M15, Model 0, `[2010-01-04, 2018-01-01)`, 100,000 deposit, 1:100 leverage, current tester spread and the frozen KVO34/55/13 + signal13 + EMA100 pullback-reentry rules.

## Engineering evidence

- Source SHA256 `D106560C5960AE90E8AA83767C14065B51BDDF09D55DAF34DE0DCA67399249C2`; run EX5 SHA256 `CF27E344A52A9F1BB5F239B49D7B013A46216D695DEC8883D6128A9A3C6497BC`.
- Run manifest SHA256 `94C59DB2F32F1EC80984277C99549A3CE48FD9ABD80F2DCE73C34CF5C6ADB0CB`; report SHA256 `5384F54F9683F66ABD7E0AFABEA3BC1847DB015F4E8F269C4C479EA1CF32B570`.
- Journal SHA256 `CDCBB17A1B270F9B7A8EEB34AE0E02E8EB785BD5B701F987F07E37F94DE00AA6`; raw collection 482,010 bytes from three files, `truncated=false`.
- MT5 history quality 99%; exact D0 source proof present; `runtime_failed=false`; closed bars 197,804; raw signals 9,524; LONG 4,798; SHORT 4,726; invalid bars 0; exact-next clock rejects 11.
- Report contains 122 completed positions and reconciles with the terminal summary's 122 accepted entries.

## Economic evidence after report costs

- Completed positions: 122; BUY 57 (46.72%), SELL 65 (53.28%).
- Raw deal profit: -5,835.37 USD; commission: -2,029.48 USD; swap: 0; net: -7,864.85 USD.
- Gross net-cost wins 13,821.61 USD; gross net-cost losses 21,686.46 USD; PF `0.6373382286`.
- Expectancy `-64.46598361` USD/trade; win rate 32.79%; equity drawdown 7.7044%.
- Elapsed TRAIN is exactly 417 calendar weeks; cadence `122/417 = 0.29256595` trades/week, below 2–5.
- Every completed position occurred in 2010 before the frozen drawdown lock stopped new entries; max calendar-year share is 100%, above 30%.

The failure is large and coherent: PF, net, expectancy, cadence and temporal concentration all fail. Direction balance and the 8% drawdown ceiling do not rescue the thesis.

Failure radius is the exact EURUSD M15 Klinger 34/55/13 zero-line pullback re-entry with EMA100 trend, three-bar swing plus 0.15 ATR stop, 1.50R target, 16-bar time exit, one accepted trade/day and 0.25% equity risk on the frozen TRAIN window. It is not a claim that every Klinger strategy or every EURUSD continuation strategy lacks edge.

Forbidden rescue: Friday-only/session removal, direction deletion, SL/TP change, daily-cap change, drawdown-lock removal, KVO/EMA threshold tuning or mining the observed 2010 subset. Validation, holdout, optimization, paper and live remain unopened.
