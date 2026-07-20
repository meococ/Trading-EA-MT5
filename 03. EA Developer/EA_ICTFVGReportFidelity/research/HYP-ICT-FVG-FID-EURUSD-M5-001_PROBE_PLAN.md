# PROBE PLAN - HYP-ICT-FVG-FID-EURUSD-M5-001

Status: FROZEN 2026-07-18 before any outcome of this exact object was read.

## 1. Identity and authority

- Hypothesis: `HYP-ICT-FVG-FID-EURUSD-M5-001`
- EA package: `EA_ICTFVGReportFidelity`
- Symbol/timeframe: EURUSD M5 execution with closed M15 structure and ADX.
- Owner authority: direct build requested in the active thread on 2026-07-18.
- Source report: `05. Playbook/Strategy/BaoCao_DeepResearch_Scalping_ICT_Liquidity_PropFirm_072026.docx`, SHA256 `44638AA4999D35AF3C4B3CCA3C1D530D2AC1CCF6901D73A4291D2649687F4070`.
- Current `EA_FVGConfluence` remains a killed audit specimen and is not modified
  or rerun. This hypothesis tests the previously missing ordered report FSM.
- Build order exception: Owner explicitly requested the complete MQL5 build.
  Therefore source implementation precedes the cheap economics probe; trial
  budget remains frozen at two Model-0 arms and no result-driven edits are
  allowed.

## 2. De-dup and adverse priors

- Checked terminal FVGConfluence, Unicorn, PO3, KLR, DRAT and ICTVisualEdge
  records in `04. Memory/do_not_repeat_failures.md`.
- Material distinction from `HYP-FVG-SCALP-CONFL-M5-EUR-001`: ordered
  `sweep -> displacement+FVG -> closed-M15 MSS -> fresh OB/FVG overlap -> first
  retest confirmation` is mandatory; the killed source used an unordered 3-of-5
  score, H1/H4 proxy bias, no state lifetime, no fresh OB and no M15 MSS.
- Boundary versus other killed ICT lanes: this is an Owner-authorized exact
  report replication, not a threshold rescue of any killed ID. Results apply
  only to this exact EURUSD M5 configuration and cannot reopen predecessors.
- Adverse priors are strong: DRAT rules-only EURUSD M15 was uneconomic; KLR and
  PO3 ordered funnels were cadence-starved on XAU; the generous EURUSD M5 sweep
  object was cost-dominated. Default verdict is KILL unless every gate passes.

## 3. Data and time contract

- Development/Model-0 window: `2019.01.01` through `2022.12.31`.
- 2023 onward is sealed holdout and must not be used for this first verdict.
- Data manifest: `02. AlphaFactory/data/fivepercent/EURUSD/manifest.json`, SHA256
  `05904D8B89A7439B1D0C444D10CB4F49AA31D8E939F8F6A9640F50D3C5AD9BE4`.
- Broker: FivePercentOnline-Real portable tester. Historical spread column is
  unusable as cost truth.
- Server to UTC: FivePercent UTC+2 winter / UTC+3 summer; EU DST calendar for
  the entire 2019-2022 window, implemented from the canonical clock model.

## 4. Frozen decision surface

Two arms only; every rule uses closed bars (`shift >= 1`) and entry occurs at
the earliest quote after the decision bar closes.

### Matched high-recall control

- London 07:00-11:00 UTC or New York 13:00-17:00 UTC.
- M5 wick sweeps the latest confirmed pivot high/low and closes back inside.
- Enter in the reversal direction on the next quote.
- Structural stop beyond the sweep with 1.5 pip buffer; target 2R.
- Same risk, spread and management rules as challenger.

### Report-fidelity challenger

1. M5 sweep/reclaim of the latest confirmed pivot within 20 bars.
2. Within six M5 bars, opposite-direction displacement body must exceed 1.5x
   the mean body of the previous 20 closed M5 bars and form a strict three-bar
   FVG.
3. The last opposite M5 candle before displacement is the OB. The overlap of
   its body and the FVG must be non-empty. Any mitigation before MSS invalidates
   the setup.
4. A closed M15 bar after displacement must break the pre-sweep confirmed M15
   swing in the new direction.
5. Within 12 M5 bars after MSS, the first retest must reach both the OB/FVG
   overlap and 50-70% FVG depth, then close as a directional rejection.
6. Entry gate requires closed M15 `iADX(14) > 25`, spread <=1.5 pips, session
   eligibility and all prior states in order.
7. Entry is market at the earliest quote after the retest decision closes.
8. SL is beyond the OB origin candle by 1.5 pips; TP is fixed 2R.

### Risk and management

- Risk 0.25% of equity per trade; maximum two trades/day; one open position.
- Stop new entries at -1.5% daily equity loss or 8% peak-equity drawdown.
- After two consecutive losing lifecycles, cool off for 120 minutes.
- At +1R, tighten SL to lock +0.5R. Optional ATR trail is frozen OFF for the
  first test so the report's fixed 2R target remains the isolated exit.
- Flatten before 22:00 UTC; no overnight hold.
- Never widen a stop after volume calculation. Reconcile actual-fill money risk
  and close immediately if it exceeds planned risk by more than 10%.
- Historical high-impact news +/-30 minute filtering is `UNMET`: no hash-bound
  calendar exists. Model 0 is diagnostic and `promotion_eligible=false`.

Exact Model-0 overrides:

`InpResearchAutoMode=true;InpEnableTelemetry=true;InpSignalMode=0|1;InpRiskPercent=0.25;InpMagic=5600720;InpPivotStrength=2;InpSweepLookback=20;InpDisplacementBars=6;InpMeanBodyPeriod=20;InpDisplacementBodyMultiple=1.50;InpM15PivotStrength=2;InpM15Lookback=120;InpRetestBars=12;InpFvgDepthMin=0.50;InpFvgDepthMax=0.70;InpAdxPeriod=14;InpMinAdx=25.0;InpStopBufferPips=1.50;InpTargetRR=2.00;InpMaxSpreadPips=1.50;InpMaxTradesPerDay=2;InpDailyLossPct=1.50;InpMaxAccountDrawdownPct=8.00;InpMaxConsecutiveLosses=2;InpCooldownMinutes=120;InpBreakEvenTriggerR=1.00;InpBreakEvenLockR=0.50;InpFlattenUtcHour=22;InpServerUtcOffsetWinterHours=2;InpServerUsesEuropeDst=true;InpRequireNewsGuard=false;InpUseAtrTrail=false`

## 5. Costs, trials and inference

- Diagnostic round-trip cost: 1.5 pips; stress 2.25 and 3.0 pips.
- Cost status: `UNVERIFIED_PROXY`; never interpret missing tester commission as
  zero economic cost.
- Trial universe N=2: high-recall control and report-fidelity challenger.
- No optimization, parameter sweep, subgroup veto or post-result filter.
- Compare the arms on the same 2019-2022 window and Model 0 execution.

## 6. Acceptance and kill gates

All are required to survive:

1. Compile 0 errors/0 warnings and exact-source non-repaint PASS.
2. At least 300 closed challenger trades and 2.0-5.0 trades per elapsed week.
3. Challenger PF >=1.60 after x1 cost; expectancy >0.
4. PF >=1.25 at x1.5 and >=1.00 at x2.
5. Max DD <=8%; Monte Carlo P95 DD <=8%; Sharpe >=1.50.
6. Positive result is not dependent on one year, direction or session.
7. Challenger must beat the matched control on net expectancy without worse
   tail risk.

Failing sample/cadence is a terminal fidelity-cadence verdict. Failing gross or
cost economics is a terminal economic KILL. Passing Model 0 only advances to
WFO/Monte Carlo/holdout preparation; it is not promotion.

## 7. Forbidden edits

No hour/day/year veto, direction removal, pivot/lookback change, displacement
or ADX relaxation, FVG-depth change, retest extension, RR/BE change, symbol/TF
change, news fiction, or new control after outcomes. Any such idea requires a
fresh hypothesis and window.

## 8. Required artifacts

- Requirement-to-code matrix, canonical source and exact preset.
- Source/EX5/compile receipt and closed-bar/non-repaint audit.
- AlphaFactory control and challenger run manifests plus lifecycle-v3 telemetry.
- Cost stress, validate-full, comparative readout and one registry transition.
- `promotion_eligible=false` until verified same-broker costs and the full
  validation stack exist.
