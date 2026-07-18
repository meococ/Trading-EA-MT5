# Prereg — HYP-DRAT-ONNX-ICT-M15-EUR-001

Status: FROZEN before the first offline outcome readout.

## Identity

- Hypothesis ID: `HYP-DRAT-ONNX-ICT-M15-EUR-001`
- EA package: `EA_DRAT_ONNX_ICT_Hybrid`
- Parent: Owner-authorized `DRAT EA ONNX&ICT Hybrid` build, independent mechanism
- Source provenance: `05. Playbook/Strategy/DRAT EA ONNX&ICT Hybrid.md`
- Feature family: causal regime classification + liquidity-sweep state machine
- Symbol / timeframe: `EURUSD` / `M15`
- Train window: `2020.01.01` through `2023.12.31`
- Untouched probe and first Model 0 window: `2024.01.01` through `2026.06.30`
- Role / MT5 model: rules-only control then ONNX-gated challenger / `0`

## De-dup boundary

The killed Hybrid-Sonic lane used Dragon/PVSRA/Sonic context plus ICT level
gates and failed Model 0 at PF 0.98 / 0.22 trades per elapsed week. This
hypothesis does not reuse its signal, session rescue, stop contract or source.
It reuses only safe engineering conventions. Its independent decision object is
an explicit sweep -> MSS -> FVG/OB retest state machine whose playbook is gated
by two ONNX classifiers. Adding an ONNX filter to the killed source is forbidden.

## Causal model contract

Two separate float32 models resolve the brief's ambiguous multi-head output:

1. `regime_model_v1.onnx`: probabilities for `trend`, `range`, `stress`.
2. `breakout_model_v1.onnx`: probabilities for no-event / breakout-event.

Frozen feature order, all computed on completed bars:

1. four-bar return / ATR(14)
2. signed EMA(20)-EMA(50) gap / ATR(14)
3. ATR(14) / ATR(96)
4. bar range / ATR(14)
5. 16-bar price efficiency ratio
6. tick-volume z-score over 20 bars
7. close location within the completed candle
8. distance beyond the prior 20-bar extreme / ATR(14)

Labels are causal state labels, not future-return labels. Stress is ATR-ratio
`>=1.35` or range/ATR `>=2.00`; trend is non-stress with efficiency `>=0.35`
and absolute EMA gap/ATR `>=0.25`; otherwise range. Breakout event is completed
close at least `0.05 ATR` beyond the preceding 20-bar extreme. Train-only
standardization is embedded in each ONNX graph.

## Frozen signal and execution surface

- Sweep: wick beyond the prior 8 completed M15 bars and reclaim by close; close
  location must be `>=0.55` bullish or `<=0.45` bearish.
- MSS/CHOCH: within 4 bars, close beyond the pre-sweep 3-bar opposite extreme.
- Zone: first causal three-candle FVG after sweep; otherwise last opposing
  candle before MSS as the deterministic OB proxy.
- Retest: within 8 bars, touch the zone and close beyond its midpoint.
- Entry: next bar open/first executable quote only; never the signal close.
- Session: server-hour `[06:00,20:00)`, weekdays only. No hour/day mining.
- Regime gate: confidence `>=0.50`; trend must agree with EMA-gap direction;
  stress requires breakout probability `>=0.65`; range uses the state machine.
- SL: sweep extreme plus `0.15 ATR`; reject geometry over `3 ATR`.
- TP: fixed `2.0R`; time exit after 32 M15 bars; no BE/trail/partial exit.
- Risk: 0.25% equity, maximum one owned position, magic fixed in source.
- Spread: fail closed above the source's frozen cap; missing quote/geometry
  blocks entry.
- Daily loss stop: 1.0% of day-start equity. Account drawdown stop: 8.0%.
- No overnight/weekend carry: flatten at the frozen session boundary and before
  the weekend.

## Cheap offline probe

Script: `02. AlphaFactory/tools/drat_onnx_ict_probe.py`.

- Rules-only control and ONNX-gated challenger use the same OOS bars.
- Fill semantics: next-bar open; stop-first on same-bar SL/TP collision.
- Frozen falsification cost: `0.10R` per round trip, explicitly unverified.
- Survivor requires every check: breakout Brier `<=0.25`; challenger PF
  `>=1.15`; positive net R; cadence 2-5 trades per elapsed week; PF and net R
  not below rules-only control; 2024 and 2025 each positive.
- Failure means `KILL_AT_OFFLINE_PROBE`; no threshold/session/exit rescue under
  this hypothesis ID.

## Model 0 acceptance and kill gates

- Profit factor `>1.30` on the frozen window after report-bound cost.
- Cadence 2-5 trades per elapsed calendar week.
- Maximum relative drawdown 8%; Monte Carlo P95 DD <=8%.
- Cost stress x1.5 PF >=1.25 and x2 PF >=1.00.
- Positive net and non-negative control-relative PF, net and net/DD.
- Non-repaint audit PASS; no bar-zero signal/data access.
- `validate-full` and lifecycle telemetry must reconcile; missing verified cost
  remains `INSUFFICIENT`, never zero.

## Experiment budget and forbidden edits

- One frozen offline probe.
- One compile/audit repair loop limited to correctness.
- One rules-only Model 0 control and one ONNX-gated challenger if all preflight
  capability/cost gates permit execution.
- No optimization, parameter scan, hour/day/year veto, post-result model
  retraining or threshold rescue. Any such change requires a new hypothesis ID.
