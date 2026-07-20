# HYP-ICT-FVG-CONTEXT-STATE-EURUSD-M5-012 — frozen Model-0 plan

Status: **FROZEN BEFORE HYP-012 SOURCE CHANGE, COMPILE OR OUTCOME**

Date frozen: 2026-07-19

## Research question

Does replacing immediate M5 sweep/reclaim entry with a short-lived,
closed-bar post-sweep acceptance/rejection state improve the probability and
payoff distribution of the same EURUSD M5 opportunity family?

This is a new decision geometry, not a rescue or rerun of terminal HYP-011.
HYP-011 showed that static M15/H1/H4/D1 location does not materially separate
the frozen C09/C10 pair or the short population. The new mechanism therefore
tests a transition after the raid rather than another static HTF veto.

## Human-to-system translation

A consistent discretionary trader does not need to predict the market. The
repeatable workflow is:

1. observe a liquidity event;
2. keep a bounded context state rather than enter from the event alone;
3. invalidate the idea if price accepts beyond the swept extreme;
4. require closed-bar evidence that price travels away from the raid;
5. execute the same risk policy when that state occurs.

The EA must implement exactly that sequence. It must not infer intent,
manipulation, smart money or future direction.

## Frozen signal arms

Both arms retain the parent closed-M5 strength-2 pivot sweep/reclaim detector,
London/New York sessions, spread/risk/prop guards, market order execution,
sweep-extreme stop plus 1.5 pip buffer, 2R target, +0.5R lock after +1R,
22:00 UTC flatten, 0.01% diagnostic risk, 100% EA account-DD ceiling and news
disabled consistently over the full interval.

### Arm 0 — immediate control

- `InpSignalMode=0`.
- Enter immediately after the closed sweep/reclaim bar, exactly as HYP-011.

### Arm 2 — context-state challenger

- `InpSignalMode=2`.
- The closed sweep/reclaim bar creates one active setup per direction/session.
- Observe at most the next `3` closed M5 bars.
- Invalidate a long if a later bar closes at or below the sweep low; invalidate
  a short if a later bar closes at or above the sweep high.
- A confirmation bar must satisfy all conditions:
  - direction away from the raid: bullish for long, bearish for short;
  - real body at least `1.00 ×` the mean real body of the prior 20 closed M5
    bars;
  - close beyond the opposite side of the original sweep bar: above its high
    for long, below its low for short;
  - close in the directional outer 25% of its own range: at or above 75% for
    long, at or below 25% for short.
- Enter on the first tick after that confirmation bar closes.
- Stop remains beyond the original sweep extreme plus the existing 1.5 pip
  buffer. Target and management are unchanged from control.
- If no confirmation occurs in three bars, expire. No late chase, limit entry,
  HTF veto, session/hour tuning or second threshold is allowed.

Frozen new inputs:

- `InpContextMaxBars=3`
- `InpContextBodyMultiple=1.00`
- `InpContextCloseFraction=0.25`

## Matched execution contract

- EA: `EA_ICTFVGReportFidelity`.
- Symbol/timeframe: FivePercent `EURUSD`, M5.
- Tester: MT5 Model 0, deposit 100,000, leverage 1:100.
- Window: `2018.01.01-2026.07.19`.
- Runs: exactly one control followed by exactly one challenger.
- No optimization, sensitivity sweep, alternate threshold, alternate exit,
  hour/day/year filter or rerun under this ID.
- Presets:
  - `presets/EURUSD_M5_CONTEXT_CONTROL_2018YTD.set`
  - `presets/EURUSD_M5_CONTEXT_CHALLENGER_2018YTD.set`
- Presets may differ only in `InpSignalMode` and isolated `InpMagic`.
- Historical execution-cost provenance remains failed and the known full-chart
  tester history may report 99%. Therefore `promotion_eligible=false`
  regardless of outcome.

## Required engineering proof before outcome

- Red-first contract test for HYP-012 identity, mode 2, exact state rule,
  telemetry counters and matched presets.
- All package tests pass.
- AlphaFactory compile returns 0 errors / 0 warnings.
- Exact-source non-repaint audit proves signal decisions use only closed M5
  bars and no MTF/bar-zero decision path is introduced.
- Fresh source → EX5 → compile-log receipt is hash-bound.
- Registry validator passes and `hot.md` identifies this active scope before
  the first Tester run.

## Predeclared measurements and gates

Primary comparison uses defined-risk closed positions and elapsed calendar
weeks:

- challenger cadence must be within `2.0–5.0` trades/week;
- challenger must have at least `800` defined-risk closed positions;
- challenger PF must be at least `1.10` and improve control PF by at least
  `0.20`;
- challenger expectancy must be at least `+0.05R/trade` and improve control by
  at least `+0.15R/trade`;
- at least 6 entry years must have PF above 1;
- no single entry year may contribute more than 35% of positive P&L;
- lifecycle opens and final closes must reconcile exactly;
- the context funnel must reconcile raw sweeps, duplicate-state rejections,
  acceptance invalidations, timeouts, confirmations and opened trades.

Workspace promotion bars remain stricter: PF above 1.30 after verified cost,
stress PF and robustness. This experiment cannot clear them because historical
cost provenance is unresolved.

## Verdict routing

- Any identity, receipt, accounting, history-quality or interval failure:
  `INVALID_DIAGNOSTIC`.
- Cadence below 2/week or fewer than 800 positions:
  `KILL_AT_MODEL0_CONTEXT_CADENCE`.
- Valid run but PF/expectancy/delta/year gates fail:
  `KILL_AT_MODEL0_CONTEXT_NO_EDGE`.
- All experiment gates pass:
  `ITERATE_FRESH_OOS_REQUIRED`, not promotion. A future hypothesis must freeze
  a genuinely new evaluation window or forward sample before any confirmation.

The pair C09/C10 may illustrate the problem but may not be used to change any
threshold after this freeze.
