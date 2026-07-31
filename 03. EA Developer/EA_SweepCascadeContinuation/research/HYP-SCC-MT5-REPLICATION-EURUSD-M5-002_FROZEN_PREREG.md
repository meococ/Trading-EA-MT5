# HYP-SCC-MT5-REPLICATION-EURUSD-M5-002 — frozen Owner-directed Model-0 diagnostic

Status: **FROZEN PRE-SOURCE / PRE-COMPILE / PRE-ECONOMIC-OUTCOME**  
Frozen: `2026-07-25T13:32:40Z`  
EA: `EA_SweepCascadeContinuation`

This document is immutable after its SHA256 is registered. Any correction
before an economic result requires a new file and a new hypothesis ID. Any
strategy change after an economic result requires a materially new hypothesis;
this ID may not be tuned or rescued.

## 1. Authority and epistemic boundary

Owner explicitly requested an end-to-end EA loop and challenged stopping before
native MT5 on `2026-07-25`. This ID is an engineering/economic replication
successor to parked `HYP-SCC-EURUSD-M5-001`.

- It does **not** amend, reopen or pass the failed Stage-0 gates of HYP-001.
- It preserves HYP-001's exact confirmed-pivot BREAK→HOLD→RETEST challenger.
- It adds the previously undefined execution/exit contract needed for a native
  MT5 diagnostic and a matched immediate-break control.
- The 2019–2022 event counts and geometry are already known; SCC PnL, PF,
  expectancy and exits have not been read.
- Every outcome is `promotion_eligible=false`, cost status
  `UNVERIFIED_DIAGNOSTIC_ONLY`, and news status `DISABLED_MATCHED`.
- No optimizer, parameter sweep, paper attach, live attach or account mutation
  outside Strategy Tester is authorized.

The purpose is to complete the Owner-requested end-to-end falsification loop,
not to create a loophole around the HYP-001 park.

## 2. Hash-bound inherited identity

- Parent plan:
  `03. EA Developer/EA_SweepCascadeContinuation/research/HYP-SCC-EURUSD-M5-001_PROBE_PLAN.md`
- Parent plan SHA256:
  `6541239D88FFF99D9C8D1E2B3C78645ECE0BE01A69FFCF32BA1620ED6557FA3B`
- Parent Stage-0 result:
  `03. EA Developer/EA_SweepCascadeContinuation/research/evidence/HYP-SCC-EURUSD-M5-001_STAGE0/stage0_result.json`
- Parent result SHA256:
  `B15465AF7B99BC1807550B03D0FA67B057159B0D0143CCA646803FCB2D5AB7CD`
- FivePercent EURUSD M1 design-data SHA256:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`
- Native tester: D-drive portable FivePercent MT5, Model `0`.
- Symbol/timeframe: `EURUSD` / `M5`.
- Window: `2019.01.01` through `2022.12.31`.
- Holdout: `2023-01-01+` remains unopened by this ID.
- Deposit/leverage: `100000 USD` / tester account default leverage.

## 3. Common closed-bar event stream

Both arms use the same state stream and consume identities identically:

1. Strict N=2 confirmed pivots on closed M5 bars.
2. A pivot at `p` is eligible for BREAK `b` only when `p <= b-3`.
3. Latest confirmed pivot high is LONG-only; latest confirmed pivot low is
   SHORT-only.
4. BREAK requires a contiguous close crossing:
   LONG previous close `<= level`, current close `> level`; SHORT mirrors.
5. Only the first valid BREAK arm attempt of each UTC date is admitted.
6. The pivot is consumed on arm regardless of later execution or state result.
7. Only one candidate state may be active.
8. UTC conversion uses FivePercent server winter `UTC+2`, summer `UTC+3`
   under the Europe DST calendar.
9. Gaps fail closed. BREAK requires adjacent M5 bars exactly 300 seconds apart.
10. All decisions use closed bars. Orders may occur only on the first tick of
    the next M5 bar.

No session, weekday, ADX, volume, news, HTF, VWAP, FVG, score or directional
filter is allowed.

## 4. Frozen arms

### CONTROL_FIRST_CLOSE_BREAK

- On a valid daily BREAK, enter continuation on the next M5 bar first tick.
- LONG stop:
  `BREAK.low - 0.25 * ATR14_MT5(BREAK)`.
- SHORT stop:
  `BREAK.high + 0.25 * ATR14_MT5(BREAK)`.

### CHALLENGER_HOLD_RETEST

After the same valid daily BREAK:

1. The immediately next contiguous, same-UTC-date M5 HOLD bar must close
   strictly beyond the frozen pivot in the continuation direction.
2. Evaluate the following maximum 12 contiguous same-date closed M5 bars.
3. Priority on each passage bar:
   gap reject → day-boundary reject → close-inside reject → touch-and-close-
   outside accept → expiry at passage 12.
4. An accept enters continuation on the next M5 bar first tick.
5. LONG stop:
   `min(BREAK.low, HOLD.low, RETEST.low) - 0.25 * ATR14_MT5(RETEST)`.
6. SHORT stop mirrors with the maximum complex high.

## 5. Frozen execution and exit contract

Common to both arms:

- `InpRiskPercent=0.05`.
- `InpTargetR=2.00`.
- `InpMaxHoldBars=24` closed M5 bars / 120 wall-clock minutes after fill;
  close at the first available tick once the limit is reached.
- No break-even, trailing, scale-in, partial close or discretionary exit.
- Maximum one owned position; any symbol exposure blocks a new order.
- `InpMaxSpreadPips=2.00`; spread is an execution guard, not an alpha filter.
- Broker stop/freeze distances and `OrderCheck` must pass.
- Sizing uses account equity and `OrderCalcProfit`; volume is rounded down to
  broker step and must remain within broker min/max.
- `InpMagic=5600752`.
- Telemetry is `lifecycle-v3`; required sidecars are LifecycleTrades, RunMeta
  and DecisionTelemetry.
- Native tester spread/commission/swap are descriptive. Fixed additional
  `0.5 / 1.5 / 2.25 / 3.0` pip round-trip stress is analysis-only and may not
  alter entries or exits.

## 6. Exact variants and overrides

Common:

`InpResearchAutoMode=true;InpEnableTelemetry=true;InpHypothesisId=HYP-SCC-MT5-REPLICATION-EURUSD-M5-002;InpMagic=5600752;InpPivotStrength=2;InpRetestBars=12;InpStopAtrBuffer=0.25;InpTargetR=2.00;InpMaxHoldBars=24;InpRiskPercent=0.05;InpMaxSpreadPips=2.00;InpBrokerGMTOffsetWinter=2;InpBrokerFollowsEuropeDST=true`

Control:

`InpVariantTag=CONTROL_FIRST_CLOSE_BREAK;InpUseHoldRetest=false`

Challenger:

`InpVariantTag=CHALLENGER_HOLD_RETEST;InpUseHoldRetest=true`

No other override is authorized.

## 7. Predeclared gates and decision

A valid pair requires:

1. red-first contract test receipt;
2. exact canonical source + EX5 SHA binding;
3. compile `0 errors / 0 warnings`;
4. exact-source non-repaint PASS;
5. both Model-0 reports cover the frozen window with history quality `>=99%`;
6. report ↔ lifecycle position count and net P/L reconcile;
7. RunMeta identity, variant, magic, source/prereg hashes and diagnostic
   boundary match;
8. no tester/harness/override parsing error.

Economic gates for the challenger:

- trades `>=418`;
- cadence `2.00..5.00` per full elapsed calendar week;
- native PF `>=1.30`;
- max relative drawdown `<=6.0%`;
- mean realized R `>0`;
- at least three of four calendar years have PF `>1`;
- fixed 1.5-pip stress PF `>=1.25`;
- fixed 2.25-pip stress PF `>=1.00`;
- relative to control: PF lift `>=0.10`, mean-R lift `>=0.05R`, and max-DD
  change `<=+1.0` percentage point.

Failure of any required validity condition yields `PARK_INVALID_DIAGNOSTIC`.
Valid economics missing any economic gate yields
`KILL_DIAGNOSTIC_NO_COST_SURVIVING_EDGE`. Passing every diagnostic gate yields
only `PASS_DIAGNOSTIC_REQUIRES_INDEPENDENT_DATA`; it does not promote HYP-001
or authorize paper/live use.

## 8. End-to-end continuation rule

After this pair, the loop does not stop at compile or a single headline PF:

- parse report, lifecycle, RunMeta, decision funnel, calendar cadence, cost
  stress, direction/year buckets and representative chart anatomy;
- issue one terminal verdict for this exact ID;
- if killed, preserve the failure radius and open a later hypothesis only when
  it changes the causal information set or decision object materially. A stop,
  R:R, session, weekday, direction, pivot-strength, daily-cap or retest-window
  sibling is prohibited.
