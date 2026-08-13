# HYP-DMR-XAUUSD-M15-002 — frozen preregistration

Frozen before source revision, compile, or outcome access for this hypothesis.

## Thesis and exact signal

- Symbol/timeframe: FivePercent `XAUUSD`, native `M15`.
- Indicator: native MT5 `iDeMarker`, period `14`, closed bars only.
- LONG: prior completed DeMarker `<= 0.30` and current completed DeMarker `> 0.30`.
- SHORT: prior completed DeMarker `>= 0.70` and current completed DeMarker `< 0.70`.
- Decision/entry clock: exact next native M15 open (`+900` seconds); a missing next bar consumes the event.
- Maximum one accepted entry per server calendar day; no session, trend, volatility, weekday, or direction filter.

## Unchanged exit and risk contract

- Structural SL: extreme of the prior five completed M15 bars plus/minus `0.20 * ATR14`.
- TP: `1.50R` from the actual requested entry and unchanged structural stop.
- Time exit: after `12` completed M15 bars.
- Risk: `0.25%` equity, maximum daily loss `3.5%`, peak-equity drawdown latch `8%`, Friday flatten hour `20`, no weekend hold.
- Deposit `100000`, leverage `1:100`, current spread, FivePercent commission/cost evidence, Model `0`.

## Sole engineering revision from HYP001

Before `OrderCheck`, validate the unchanged tick-normalized SL/TP against the broker reference quote used for protective-stop geometry:

- BUY: `Bid - SL >= stops_level * point` and `TP - Bid >= stops_level * point`.
- SELL: `SL - Ask >= stops_level * point` and `Ask - TP >= stops_level * point`.

If either distance is invalid/nonfinite, consume and reject that signal once. Do not move, widen, clamp, or retry SL/TP. All signal, indicator, exit, sizing, margin, and risk logic stays unchanged. Fresh hypothesis identity, variant, magic, compile/nonrepaint evidence, and one new baseline are required.

## Baseline gates

- Engineering: compile `0 errors / 0 warnings`, nonrepaint PASS, HQ `>97`, full fixed-window DQ, nontruncated journal, `runtime_failed=false`, zero fatal markers, deterministic duplicate summaries, no unresolved order/position state.
- Economic TRAIN gate after all engineering gates: PF `>1.30` after costs, positive expectancy, cadence `2–5/week`, both directions `>=30%`, max calendar-year share `<=30%`, acceptable DD/risk.
- Any engineering failure produces no economic verdict. Any economic failure kills this exact object; no post-hoc filter or parameter rescue.
