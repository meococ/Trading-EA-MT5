# SCC de-dup and legality review — 2026-07-25

Status: `LEGAL_NEW_STAGE0_ONLY_AFTER_CONTRACT_FIX`.

Proposed identity:

- `EA_SweepCascadeContinuation`
- `HYP-SCC-EURUSD-M5-001`
- EURUSD M5; FivePercent 2019–2022 design window; 2023+ sealed

## Thesis and evidence boundary

The mechanism tests continuation after a confirmed swing level is broken,
accepted and successfully retested. It does not assume that a stop sweep should
reverse. The causal prior is Osler's documented currency stop-loss positive
feedback and price cascades:
<https://www.newyorkfed.org/research/staff_reports/sr150.html>.

This source supports a continuation hypothesis, not the specific N=2 fractal
proxy, one-attempt-per-day cap, 12-bar contest, stop geometry or profitability.
Those remain falsifiable engineering choices. FivePercent OHLC cannot observe
dealer stop orders or signed order flow, so the epistemic class stays
`PRICE_ONLY_STOP_CLUSTER_PROXY_WITH_STRONG_ADVERSE_PRIOR`.

## Closest prior objects

| Prior object | Overlap | Material difference |
|---|---|---|
| `HYP-ASRS-EURUSD-M5-001` | Same symbol/TF and confirmed N=2 pivot vocabulary | ASRS fades a wick/depth sweep after reclaim; SCC requires a close-break, HOLD and retest, then continues in the breakout direction. No ASRS ADX/session/volume gate is reused. |
| `HYP-ICT-FVG-CONTEXT-STATE-EURUSD-M5-012` | Bounded post-event state | HYP-012 confirms sweep-reclaim reversal and lost economically; SCC trades the complementary accepted breakout direction around a frozen confirmed pivot. |
| `HYP-ICT-FVG-HUMAN-CONTEXT-POLICY-EURUSD-M5-017` | High-recall liquidity-event family | HYP-017 immediately faded reclaim context; SCC uses no FVG/human-policy/room state and cannot import its post-outcome subgroups. |
| `HYP-VRAS-EURUSD-M5-004` | EURUSD M5 continuation/path confirmation | VRAS confirms an existing rolling-VWAP trend entry with one bar; SCC begins from a consumed fractal-pivot close-break and a categorical retest first-passage contest. |
| `HYP-VRAS-EURUSD-M5-011` | First-passage FSM | HYP-011 is a rolling-VWAP reclaim continuation object and parked on data parity before counts; SCC uses confirmed swing breakaway and opposite level relation. Its thresholds cannot be imported. |
| `HYP-ECRS-EURUSD-M5-002` | Price continuation / range release | ECRS requires ER/ATR compression and a range breakout; SCC has no compression, ER, volume, session or trend filter. |

SCC is not legal because the prior families failed. It is legal only because the
direction, event identity, state transition and control surface are materially
different and are frozen before SCC counts or outcomes.

## Contract defects fixed before freeze

An independent bounded Grok forensic review returned
`LEGAL_ONLY_AFTER_CONTRACT_FIX`. The frozen plan resolves its material findings:

1. same-bar first-passage priority is deterministic: invalid close first,
   accepted retest second, then continue/expire;
2. pivot identity includes side, price, extreme time/index, confirmation time,
   arm/consume time and terminal reason;
3. pivot is consumed on the first BREAK arm regardless of later result;
4. only one arm attempt is allowed per UTC day, so control and challenger share
   the identical raw BREAK identity;
5. active state dies on non-contiguous M5 data or UTC-date change before a bar
   is evaluated;
6. `ATR14_MT5` is evaluated on the completed RETEST decision bar and is only
   Stage-0 geometry;
7. decision timestamp is the RETEST bar close; any future order is no earlier
   than the next M5 open/tick;
8. exact M1/manifest/clock hashes and 2023+ read-time seal are mandatory.

Review artifacts:

- `.context/scc-review-20260725/grok-request.json`
- `.context/scc-review-20260725/run1/summary.json`
- `.context/scc-review-20260725/run1/grok-response.json`

## Adverse priors and contamination

- ASRS Stage-0 did not establish reversal edge and failed its required
  volume/session materiality gate.
- HYP-012 and HYP-017 show that bounded reclaim context and high-recall
  sweep/reclaim entry do not create stable EURUSD M5 edge.
- HYP-004 shows a one-bar continuation confirmation reduced loss severity but
  did not create positive expectancy.
- ECRS shows continuation conjunctions can be too sparse.
- The 2019–2022 EURUSD design window has been inspected by many prior workspace
  lanes. It is suitable only for Stage-0 feasibility and later diagnostic
  matched testing, never independent promotion evidence.

## Decision

Open exactly one outcome-blind Stage-0 attempt under the frozen plan. No PnL,
future excursion, MQL5, Model 0 or threshold grid is authorized before every
Stage-0 gate passes. Failure cannot be rescued by changing the horizon, daily
cap, pivot strength, filters, symbol, timeframe, direction or stop buffer.

