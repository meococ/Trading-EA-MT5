# Frozen prereg — HYP-CBWR-XAUUSD-M15-001

Status: FROZEN before compile and before any outcome-bearing MT5 run.

## Identity

- Hypothesis ID: `HYP-CBWR-XAUUSD-M15-001`
- EA package: `EA_WickReject_XAU_M15_V1`
- Candidate source: Grok skill `/deep-research-trading-meta5`, requested by Owner on 2026-08-12. Grok supplied the market thesis and V1 constants; this is advisory provenance, not evidence of edge.
- Independent mechanism: single completed-bar wick rejection at an 8-bar local extreme, with normalized ATR regime control.
- Exact de-dup: differs from TVER (no tick-volume/low-progress gate), VRAS (no VWAP/EMA/engulfing/regime fusion), MZMS (no RSI/ADX/delta/pivot/squeeze stack), and sweep/retest families (no multi-bar sweep FSM).
- Initial sleeve: `XAUUSD`, `M15`, Model 0.
- Design window: `[2018-01-01, 2022-01-01)`.
- Locked validation windows, unopened unless design advances: OOS1 `[2022-01-01, 2024-01-01)`; final `[2024-01-01, latest verified data)`.

## Trader thesis and quantified mapping

A dominant rejection wick at a fresh local extreme is treated as a short-lived failed auction/inventory absorption event. The next tradable quote after the M15 signal closes is used; no live-bar feature enters the decision.

- Bar `shift=1` is the signal bar. Swing extrema use exactly shifts `2..9` (the eight bars preceding it).
- Long anatomy: lower wick/range `>=0.60`, body/range `<=0.35`, close location in upper half (`>=0.50`), and signal low `<= prior swing low + 0.15*ATR14`.
- Short anatomy is symmetric: upper wick/range `>=0.60`, body/range `<=0.35`, close location in lower half (`<=0.50`), and signal high `>= prior swing high - 0.15*ATR14`.
- Regime: signal-bar `ATR14 / mean(prior 50 ATR14 values)` must be in `[0.70,2.20]`.
- Entry: market at the first tick of the next M15 bar. Skip if spread exceeds 55 symbol points or another position exists on the symbol.
- Raw structural stop: wick extreme plus `0.25*ATR14` outside the bar. Entry-to-stop risk is clamped to `[1.20,2.80]*ATR14`; clamp is measured from the actual entry quote.
- Target `1.60R`; break-even at `+0.90R` with the entry spread as buffer; no trailing; hard time stop after 12 M15 bars.
- Flat daily at server 21:50 and Friday at server 20:00. No weekend entry.
- Risk 0.60% of current equity per trade. Stop new entries after 1.50% daily or 3.50% weekly equity loss. Maximum one position per symbol.
- Missing/invalid bars, ATR, tick, symbol geometry, margin or volume data fail closed.

The ambiguous Grok phrase "close > open or close in the upper half" is frozen as close-location only. This keeps doji rejections valid and makes long/short mapping exactly symmetric.

## Frozen variants

- Primary: `InpVariantTag=SWING8_PRIMARY;InpRequireSwing=true`.
- Matched control, only if the primary is not an immediate economic kill: `InpVariantTag=NO_SWING_CONTROL;InpRequireSwing=false`. Every other input remains byte-for-byte identical.

All remaining inputs equal `ALPHAFACTORY_EA_CONTRACT.json`. Any signal, stop, target, clock, filter, risk, symbol-specific spread threshold or management change requires a new hypothesis ID.

## Cost and execution contract

- Broker: the configured FivePercent/FivePercentOnline portable MT5 research lane.
- Tester: Model 0, real broker spread, report commission and swap; deposit USD 100,000, leverage 1:100.
- `InpDeviationPoints=10` is an order acceptance limit, not assumed paid slippage. Baseline execution cost is therefore `UNVERIFIED` until report/contract receipts are inspected. Later x1.5/x2 cost stress is mandatory before an edge claim.
- No live trading or AutoTrading attachment is authorized.

## Design gate and stopping rule

Record N, PF, net profit, expectancy, win rate, max relative/equity DD, consecutive losses, largest loss, cadence, direction balance, time-stop share and the `CBWR001_SUMMARY` funnel.

- Immediate design kill: no trades, runtime/identity failure, PF `<1.00`, expectancy `<=0`, or Max DD `>12%` after reported costs.
- Advance to matched control and locked OOS only if N `>=300`, PF `>=1.15`, expectancy `>0`, Max DD `<=12%`, no single-year profit concentration above 50%, and telemetry/report counts reconcile.
- Goal/DONE threshold remains stricter: PF `>1.30` after verified x1 cost, x1.5 PF `>=1.25`, x2 PF `>=1.00`, independent holdout/WFA/DSR/Monte Carlo and risk/recovery gates.
- If the primary advances, it must materially beat the no-swing control on expectancy/PF without a tail-risk regression. Otherwise the swing qualifier has no demonstrated value.

## Forbidden post-result edits

No outcome-selected session, direction, year, symbol, wick/body/swing/ATR threshold, SL/TP/BE/time-stop or spread change may rescue this ID. A deterministic implementation bug may be fixed only under a new execution identity with the old artifacts preserved.
