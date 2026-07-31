# HYP-SCC-MT5-REPLICATION-EURUSD-M5-004 - frozen micro-risk replication

Status: **FROZEN PRE-SOURCE-CHANGE / PRE-RUN**  
Frozen: `2026-07-25T14:01:32Z`  
EA: `EA_SweepCascadeContinuation`

## 1. Diagnostic-child boundary

HYP-004 is a scale-only diagnostic child of terminal-invalid HYP-003.
HYP-002 and HYP-003 controls both reached the same broker/tester stop-out on
`2022.01.11` after cumulative balance loss from `100,000 USD` to
`89,986.63 USD`. HYP-003 proved that synchronous orchestration does not solve
the truncation.

This child changes only:

- `InpHypothesisId`:
  `HYP-SCC-MT5-REPLICATION-EURUSD-M5-003` to
  `HYP-SCC-MT5-REPLICATION-EURUSD-M5-004`;
- `InpMagic`: `5600753` to `5600754`;
- `InpRiskPercent`: `0.05` to `0.01`;
- embedded prereg hash, task/receipt/run identities and evidence hashes.

The fivefold risk reduction is a predeclared tester-survival instrument. It
does not change signal selection, entry timing, stop price, target price,
timeout, data, spread guard, control/challenger definition or acceptance
thresholds. Dollar P/L and percentage drawdown cannot be compared directly
with HYP-002/HYP-003. Trade count, funnel, PF, win rate, realized-R distribution
and control/challenger relative metrics remain admissible diagnostic outputs.

## 2. Bound predecessors

- HYP-003 prereg SHA256:
  `BDF19994229DA9BE07FCF20D9A6670223A727D78C17A68D9DB970109245FE88C`
- HYP-003 source snapshot SHA256:
  `E56AF40AB7DA7EB02AD312596062BD9547F8590FF0C652233B4246370D624B05`
- HYP-003 invalid readout:
  `03. EA Developer/EA_SweepCascadeContinuation/research/HYP-SCC-MT5-REPLICATION-EURUSD-M5-003_INVALID_READOUT.md`
- Parent HYP-001 plan SHA256:
  `6541239D88FFF99D9C8D1E2B3C78645ECE0BE01A69FFCF32BA1620ED6557FA3B`
- Parent HYP-001 result SHA256:
  `B15465AF7B99BC1807550B03D0FA67B057159B0D0143CCA646803FCB2D5AB7CD`

## 3. Exact unchanged strategy contract

- EURUSD M5, FivePercent broker data, Model 0.
- Test interval: `2019.01.01` through `2022.12.31`.
- Strict confirmed N=2 pivot stream using closed bars only.
- First close BREAK attempt per UTC date with pivot consumption.
- Control: next-bar continuation entry after the first confirmed BREAK.
- Challenger: immediate HOLD, then 12-bar first-passage RETEST continuation.
- Challenger stop: complex extreme plus/minus `0.25 ATR14`.
- Control stop: BREAK extreme plus/minus `0.25 ATR14`.
- Target: `2.00R`.
- Wall-clock timeout: 24 M5 bars.
- Spread guard: `2.00` pips.
- Europe-DST-aware FivePercent server-to-UTC conversion.
- No session, weekday, ADX, volume, news, HTF, VWAP, FVG or score filter.
- No break-even, trailing, partial close, optimizer or post-outcome subgroup.

Exact common overrides:

`InpResearchAutoMode=true;InpEnableTelemetry=true;InpHypothesisId=HYP-SCC-MT5-REPLICATION-EURUSD-M5-004;InpMagic=5600754;InpPivotStrength=2;InpRetestBars=12;InpStopAtrBuffer=0.25;InpTargetR=2.00;InpMaxHoldBars=24;InpRiskPercent=0.01;InpMaxSpreadPips=2.00;InpBrokerGMTOffsetWinter=2;InpBrokerFollowsEuropeDST=true`

Control:

`InpVariantTag=CONTROL_FIRST_CLOSE_BREAK;InpUseHoldRetest=false`

Challenger:

`InpVariantTag=CHALLENGER_HOLD_RETEST;InpUseHoldRetest=true`

## 4. Validity gates

Before economic comparison, both arms must:

1. use the exact frozen symbol, timeframe, window, Model 0 and overrides;
2. show history quality `>=99%`;
3. process at least `298,000` bars and reach December 2022;
4. end flat with lifecycle OPEN count equal to final CLOSE count;
5. use the same exact source SHA and matched `0.01%` risk scale;
6. reconcile report positions and net P/L to lifecycle telemetry;
7. pass exact-source compile 0/0 and non-repaint audit;
8. include LifecycleTrades, RunMeta and DecisionTelemetry sidecars;
9. contain no broker/tester stop-out, crash, timeout or early termination.

Any failure is `PARK_INVALID_MICRO_RISK_DIAGNOSTIC` and authorizes no same-ID
rerun.

## 5. Economic gates

- challenger N `>=418`;
- cadence `2.00..5.00` trades per full elapsed calendar week;
- native PF `>=1.30`;
- max relative DD `<=6.0%` at the frozen micro-risk scale;
- mean realized R `>0`;
- at least three of four calendar years PF `>1`;
- fixed 1.5-pip stress PF `>=1.25`;
- fixed 2.25-pip stress PF `>=1.00`;
- versus control: PF lift `>=0.10`, mean-R lift `>=0.05R`, and micro-risk DD
  change `<=+1.0pp`.

PF, R, cadence, funnel and direction/year breakdown decide the diagnostic.
Dollar net P/L is reported only as a scale check.

## 6. Decision policy

- Any validity failure: park invalid.
- Valid pair with any core economic gate failure: kill HYP-004 and the exact
  SCC control/challenger mechanism on this frozen EURUSD M5 contract.
- Passing descriptive economics still cannot promote: costs are unverified and
  this child is scale-diagnostic only.
- No threshold, time, weekday, direction, stop, target or subgroup rescue may
  be derived from the readout.

This prereg is `promotion_eligible=false`,
`cost_status=UNVERIFIED_DIAGNOSTIC_ONLY`, news disabled matched, and grants no
paper/live authority.
