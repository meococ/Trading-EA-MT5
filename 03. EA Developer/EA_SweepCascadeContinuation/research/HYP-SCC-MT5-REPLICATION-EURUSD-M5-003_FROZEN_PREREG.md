# HYP-SCC-MT5-REPLICATION-EURUSD-M5-003 — frozen instrumentation replacement

Status: **FROZEN PRE-SOURCE-IDENTITY-CHANGE / PRE-RERUN**  
Frozen: `2026-07-25T13:48:12Z`  
EA: `EA_SweepCascadeContinuation`

## 1. Replacement boundary

HYP-003 is the instrumentation-only successor to invalid HYP-002. HYP-002's
control was truncated by the outer shell timeout and ended with an unresolved
position on `2022-01-11`; its challenger completed the requested horizon.

This replacement changes only:

- `InpHypothesisId`:
  `HYP-SCC-MT5-REPLICATION-EURUSD-M5-002` →
  `HYP-SCC-MT5-REPLICATION-EURUSD-M5-003`;
- `InpMagic`: `5600752` → `5600753`;
- task/receipt/run identities and evidence hashes;
- orchestration: both commands run synchronously with a 120-second caller
  timeout, while AlphaFactory retains its frozen 5,400-second tester timeout.

Every signal, state, execution, sizing, stop, target, time-exit, cost, date,
symbol, timeframe, data and acceptance rule remains byte-semantically
identical to HYP-002.

## 2. Bound predecessor

- HYP-002 prereg SHA256:
  `12B13C309B60BDA6AD4BC88A11F7389DB3E8EE18E9493CC2950DDB95AED53796`
- HYP-002 invalid readout:
  `03. EA Developer/EA_SweepCascadeContinuation/research/HYP-SCC-MT5-REPLICATION-EURUSD-M5-002_INVALID_READOUT.md`
- Parent HYP-001 plan SHA256:
  `6541239D88FFF99D9C8D1E2B3C78645ECE0BE01A69FFCF32BA1620ED6557FA3B`
- Parent HYP-001 result SHA256:
  `B15465AF7B99BC1807550B03D0FA67B057159B0D0143CCA646803FCB2D5AB7CD`

## 3. Exact unchanged strategy contract

The full Sections 3–8 of the HYP-002 prereg are inherited without amendment:

- strict confirmed N=2 pivot stream;
- first close BREAK attempt per UTC date and pivot consumption;
- control next-bar continuation entry;
- challenger immediate HOLD then 12-bar first-passage RETEST;
- challenger complex-extreme ±0.25 ATR14 stop;
- control BREAK-extreme ±0.25 ATR14 stop;
- 2.00R target, 24 M5-bar wall-clock timeout;
- 0.05% equity risk, 2.00-pip spread guard;
- Europe-DST-aware FivePercent UTC clock;
- no session, weekday, ADX, volume, news, HTF, VWAP, FVG or score;
- no break-even, trailing, partial close or optimizer.

Exact common overrides:

`InpResearchAutoMode=true;InpEnableTelemetry=true;InpHypothesisId=HYP-SCC-MT5-REPLICATION-EURUSD-M5-003;InpMagic=5600753;InpPivotStrength=2;InpRetestBars=12;InpStopAtrBuffer=0.25;InpTargetR=2.00;InpMaxHoldBars=24;InpRiskPercent=0.05;InpMaxSpreadPips=2.00;InpBrokerGMTOffsetWinter=2;InpBrokerFollowsEuropeDST=true`

Control:

`InpVariantTag=CONTROL_FIRST_CLOSE_BREAK;InpUseHoldRetest=false`

Challenger:

`InpVariantTag=CHALLENGER_HOLD_RETEST;InpUseHoldRetest=true`

## 4. Replacement validity gates

Before economic comparison, both runs must:

1. use Model 0, EURUSD M5, `2019.01.01`–`2022.12.31`;
2. show history quality `>=99%`;
3. process at least `298,000` bars and cover lifecycle through December 2022;
4. end flat with lifecycle OPEN count = final CLOSE count;
5. use the same exact source SHA and requested overrides;
6. reconcile report and lifecycle position count/net P/L;
7. pass exact-source compile 0/0 and non-repaint audit;
8. include LifecycleTrades, RunMeta and DecisionTelemetry sidecars.

Any failure is `PARK_INVALID_INSTRUMENTATION` and authorizes no same-ID rerun.

## 5. Unchanged economic gates

The HYP-002 economic gates remain unchanged:

- challenger N `>=418`;
- cadence `2.00..5.00` per full elapsed calendar week;
- native PF `>=1.30`;
- max relative DD `<=6.0%`;
- mean realized R `>0`;
- at least three of four years PF `>1`;
- fixed 1.5-pip stress PF `>=1.25`;
- fixed 2.25-pip stress PF `>=1.00`;
- versus control: PF lift `>=0.10`, mean-R lift `>=0.05R`, DD change
  `<=+1.0pp`.

This is diagnostic-only, `promotion_eligible=false`,
`cost_status=UNVERIFIED_DIAGNOSTIC_ONLY`, news disabled matched, no paper/live
authority, and no post-outcome parameter or subgroup rescue.
