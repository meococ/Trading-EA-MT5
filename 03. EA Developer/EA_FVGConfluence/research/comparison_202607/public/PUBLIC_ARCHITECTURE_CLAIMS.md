# Public architecture claims versus the current EA

This matrix is based on pass-1 vendor descriptions. Every public-product cell
is `claimed`; none is promoted to `verified_exact` or `verified_proxy` without
source or reproducible execution evidence.

| ID | Signal-fidelity claim | Risk / prop claim | Execution-safety claim | Telemetry claim | Main uncertainty |
|---|---|---|---|---|---|
| Current EA | `verified_exact` closed FVG; `verified_proxy` sweep/OB/HTF; no sequential FSM | daily loss/trade count are RAM-only and differ from report | stop-level adjustment can occur after sizing | print log only | Code known; economic edge and report fidelity do not follow from compile hygiene. |
| F01 | BOS -> opposite sweep -> close-back | sizing, sweep SL, fixed R, partial/BE/trail; no daily challenge limit found | spread, stop/freeze, fill mode, deviation, cooldown | chart objects and claimed CSV/event export | Implementation unavailable. |
| F02 | range sweep -> MSS -> displacement/FVG -> configurable FVG entry | risk modes, stop bounds, RR, BE | time windows, pending expiry, spread adjustment | chart visualization | Closest claimed sequence to the report, but vendor-only. |
| F03 | HTF + BOS/CHOCH/MSS + FVG/OB mitigation + sweep + session/P-D | risk modifiers, exposure/margin caps, partial/BE/ATR trail | stop/freeze, volume, margin, retry cooldown | dashboard, alerts, Telegram, CSV | Broadest claim set; FX scope/default path and implementation unverified. |
| F04 | HTF -> sweep -> MSS -> FVG -> retracement limit | daily loss, trade count, equity proximity and correlation controls | limit, spread, ATR/Friday/swap guards | missing or unknown | Pair whitelist and implementation undisclosed. |
| F05 | session -> M15 structure -> sweep -> M5 CHOCH -> retest | daily/equity-peak kill, partial/BE/trail | closed candle, spread/ATR, cooldown, broker checks | missing or unknown | Pair scope and persistent-state behavior undisclosed. |
| F06 | H4/H1 structure -> M15 OB/FVG/breaker -> M5 trigger | ATR risk, staged exits, cooldown, correlation | multi-symbol, sessions, no-trade hours, optional news | dashboard and claimed CSV state logs | Default enabled module path unknown. |
| F07 | FVG/OB/sweep -> structure shift -> selected entry mode | daily loss, equity, consecutive-loss and correlation controls | market/limit, spread, ownership, broker guards | console/error and live state | Multiple selectable modes; default path unknown. |
| F08 | pierce/close-back -> wick/body -> H1 direction | daily loss/profit, split exit, BE/trail | spread; session merely recommended | missing or unknown | Broker safety and mandatory session path unclear. |
| F09 | swing -> BOS -> displacement | fixed lot, ATR SL/TP, margin | autonomous path with optional operator overrides | structure/session/liquidity dashboard | FVG/OB are not clearly mandatory entry primitives. |
| F10 | session pool -> sweep -> M5 MSS -> FVG retracement | basic lot/SL/TP only | volume, margin, min-stop, session inputs | missing or unknown | No daily prop control or structured telemetry found. |
| F11 | equal levels -> breakout -> impulse -> order block | basic fixed lot/SL/TP | missing or unknown | chart boxes/alerts | Mandatory retest and broker-safety path unclear. |
| F12 | session range plus selectable breakout/OB/false-break paths | sizing, partial/BE/trail, max trades | order ownership, netting, stop checks, GMT input | dashboard and detailed logs | Multiple modes and DST conversion unverified. |
| F13 | selectable SMC/ICT strategy families | multiple sizing modes and risk caps | spread, one-entry-per-bar, hedge/netting | live dashboard | Enabled strategy subset and grid-like modes unverified. |
| F14 | Asian range -> London M15 breakout + HTF/indicator filters | daily equity circuit breaker, partial/BE/trail | spread/slippage/GMT/ECN and manual news guard | alerts/logs | It is session-breakout, not necessarily FVG/sweep confluence. |
| F15 | CBDR ranges -> volatility state -> session protraction | sizing, session SL, partial/BE | spread, weekdays, cutoff, broker guards | dashboard | Exact candle trigger/timeframe undisclosed. |

## Architecture verdict

- **Against the original report:** current `EA_FVGConfluence` is `INFERIOR` in
  fidelity because the report requires an ordered sweep -> displacement -> M15
  MSS -> fresh OB/FVG -> retest state machine plus regime/news/prop controls,
  while the code uses an unordered score and several proxies.
- **Against similar public EA implementations:** `INCONCLUSIVE`. Several
  products claim a richer or more report-like sequence and controls, especially
  F02-F07, but marketing descriptions cannot prove that their code implements
  those claims correctly, non-repainting, or profitably.
- The current EA retains one evidential advantage: its exact source and compile
  closure are auditable. That is engineering transparency, not economic
  superiority.

