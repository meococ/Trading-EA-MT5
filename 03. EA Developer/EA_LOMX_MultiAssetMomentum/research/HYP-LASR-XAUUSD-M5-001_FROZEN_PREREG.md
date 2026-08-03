# HYP-LASR-XAUUSD-M5-001 - Frozen Preregistration

Frozen before any MT5 performance execution or read for this hypothesis.

## Decision identity

- EA: `EA_LOMX_MultiAssetMomentum`
- Atomic sleeve: `ENGINE_SWEEP` only
- First ordered cell: `XAUUSD M5`
- Source SHA-256: `6243A3BE573B305AEDF223953D4E68A37866AE8C53512EABC3D430969B194B47`
- EA contract SHA-256: `C3D0EA8E08BD4BF2F08A878FD76E9373FE8AF98134C9E88168D530B5ADB34D8C`
- Logic matrix SHA-256: `37597039D03589EC505D285922D72369CD2ED1E3BADA14115CC59BD79DE281AB`
- Parent Stage-0 result SHA-256: `8193E68D4EC240B696CDB91884C95976F3B47ECFFF740D5416BE2BEB4D2EF1DB`
- Static non-repaint result: `PASS`, SHA-256
  `4D4043314744DA0FD3A1BF11F8F5D5B4CD109309396F5A005BAC0ED8F0C690A3`
- Cost-source manifest: `RESEARCH_PROXY`, SHA-256
  `60302CA3E1BFD0603D5EF38A2EA7B93DE58CA44EEBFE58C6CDA991BD2E184D9B`

The parked `HYP-LOMX-MULTI-M5-001` draft is not retroactively legalized.
`HYP-LOMX-DESIGN-M5-002` proved only outcome-blind density: the exact combined
two-engine stream failed its 2-5/week cadence gate, while this atomic XAU sweep
cell produced 2,085 candidates or 4.4429/elapsed week over 2016-2024. No PnL,
exit, win rate, PF, MAE or MFE was inspected in that probe.

## Frozen split and access

| Split | Dates | Access now |
|---|---|---|
| Training control | `2018.01.02` - `2022.12.30` | one Model-0 run authorized after guarded dry-run passes |
| Validation | calendar year 2023 | locked until the training control passes every fatal gate |
| Holdout | calendar year 2024 | locked until train and validation independently pass |
| 2016-2017 capability slice | two years | no economic claim; archived raw ticks/spread unavailable in current broker terminal |

The frozen read-only raw-tick acquisition for 2016-2024 failed at 0% archived
tick coverage while synchronized M5 bars existed. The successor window starts
in 2018 because exact historical M1 bid/ask evidence begins then. This is a
pre-outcome capability correction, not a result-driven date selection.

## Exact Model-0 control

- Run role: `control`
- Tester model: `0` (`Every tick based on real ticks`)
- Execution mode/fixed delay: `0 / 0 ms`
- Deposit/leverage: `10000 USD / 1:100`
- Spread: `current`; historical spread, maximum tester commission and 1-second
  executable-quote movement are independently repriced by the cost artifact.
- Telemetry: `trade-only`, lifecycle-v3 sidecars mandatory.
- Validation stage / holding contract: `challenger / scalp`
- Research-cost proxy opt-in: required; `promotion_eligible=false` under every
  possible result.

Exact overrides, sorted and immutable:

```text
InpATRPeriod=14;InpAsianEndMinutesUtc=360;InpAsianStartMinutesUtc=0;InpDailyFlattenMinutesUtc=1200;InpDeviationPoints=20;InpEnableTelemetry=true;InpEngineMode=0;InpFridayFlattenMinutesUtc=1200;InpHypothesisId=HYP-LASR-XAUUSD-M5-001;InpLotConsistencyLookbackFills=10;InpLotConsistencyMaxFactor=1.50;InpLotConsistencyMinFactor=0.50;InpLotConsistencyMinFills=10;InpMagic=5603101;InpMaxAccountDrawdownPct=8.0;InpMaxDailyLossPct=3.5;InpMaxHoldBars=96;InpMaxSpreadToRisk=0.15;InpMaxTradesPerDay=3;InpResearchAutoMode=true;InpRiskPercent=0.25;InpSweepEpsilonMult=0.30;InpSweepMinTp2R=1.50;InpSweepScaleOutFraction=0.50;InpSweepStopAtrMult=0.20;InpTradeEndMinutesUtc=960;InpTradeStartMinutesUtc=420;InpVariantTag=LASR_XAU_SWEEP_MODEL0;InpVolumeLookback=20;InpVolumeThreshold=1.50
```

## One-shot fatal gates

The training control is killed/parked without repair on the same ID if any
condition fails:

1. compile is not `0 errors / 0 warnings`, non-repaint is not `PASS`, history
   quality is not greater than 97%, or exact report/lifecycle deal
   reconciliation fails;
2. zero executed trades, or executed cadence is outside 2.0-5.0 trades per
   elapsed calendar week;
3. report/control PF is below 1.30 or maximum equity drawdown exceeds 8%;
4. research-proxy cost repricing gives PF below 1.25 at x1.5 costs or below
   1.00 at x2 costs;
5. any overnight/weekend exposure, unbounded hold, foreign position mutation,
   duplicate final close, missing deal, or nonpositive initial risk is found;
6. fewer than 20% of completed lifecycles occur in either direction, or the
   result depends on an unregistered override.

A pass is only `research pass / invest-more-effort`. It does not establish
economic-valid or promotion-ready status because slippage is a quote proxy and
commission is tester-derived, not observed same-account fills. A surviving
sleeve must then preserve these rules through the locked validation/holdout,
the full nine-symbol required-universe matrix, WFA/PBO/DSR/Monte Carlo and
promotion-grade cost provenance.

## Trial and adaptation debt

- Economic trials consumed before this run: `0` for this hypothesis.
- Authorized performance launches: exactly `1` training control.
- No grid, threshold search, weekday/session pruning, stop/target adjustment,
  symbol pooling, lot-based rescue, or re-read on the same ID.
- If killed, write a failure-radius packet and move to the next already-frozen
  atomic cell or a genuinely new mechanism under a fresh ID.
