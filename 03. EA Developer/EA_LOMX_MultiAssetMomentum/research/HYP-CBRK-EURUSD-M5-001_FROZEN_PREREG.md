# HYP-CBRK-EURUSD-M5-001 - Frozen Compression Breakout Preregistration

Frozen before any MT5 performance launch or outcome read for this mechanism.

## Decision identity

- EA: `EA_LOMX_MultiAssetMomentum`
- Atomic sleeve: `ENGINE_BREAKOUT` only
- Ordered cell: `EURUSD M5`
- Parent: `HYP-LOMX-DESIGN-M5-002`
- Source SHA-256:
  `D363121DC7FFCB128A67C796B76F8B86C8AB2262FF045EAC62B49FE19FB3298B`
- EA contract SHA-256:
  `C3D0EA8E08BD4BF2F08A878FD76E9373FE8AF98134C9E88168D530B5ADB34D8C`
- Parent Stage-0 result SHA-256:
  `8193E68D4EC240B696CDB91884C95976F3B47ECFFF740D5416BE2BEB4D2EF1DB`
- Static non-repaint result: `PASS`, SHA-256:
  `9F1D0FE93B1FAA2DB252E6821BA24BBDCBC39BF467A20880980F17190B2DBC4A`
- Cost-source manifest: `RESEARCH_PROXY`, SHA-256:
  `B1791DC0C82FEEDB1E2906F8BA10097ED6E4064CFA794433061123EB6FAACE3F`

This is the second preordered EURUSD atomic cell from the outcome-blind Stage-0
matrix, where it produced `2117` candidates (`4.5111/week`). It is materially
different from the parked sweep-reclaim mechanism and was not derived by
filtering, reversing or tuning the sweep outcome.

The label means the exact generic bar-range compression rule implemented here;
it is not a claim to reproduce Bob Volman's discretionary grammar:

1. closed Bar 2 range `< 0.70 * mean(range, prior 50 closed bars)`;
2. buildup box is the high/low of Bars 1-15;
3. closed Bar 1 must break the box by `0.20 * ATR14` with tick volume above the
   prior-20 mean;
4. stop is opposite box edge plus `0.10 * ATR14`; target is fixed `2R`;
5. signal window is `07:00-16:00 UTC`, closed bars only.

## Frozen train identity and splits

| Split | Dates | Access now |
|---|---|---|
| Training control | `2016.01.04` - `2022.12.30` | exactly one Model-0 run after canonical dry-run passes |
| Validation | calendar year 2023 | locked until training independently passes every fatal gate |
| Holdout | calendar year 2024 | locked until training and validation independently pass |

The account/data identity was observed from a full-horizon Strategy Tester run
before any breakout performance existed. No sweep PnL/PF/cadence was imported
into the breakout rules:

- deposit/leverage: `100000 USD / 1:100`
- broker stop-out mode: money; margin call `$92,000`, stop-out `$90,000`
- account fingerprint:
  `0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073`
- history quality / bars / ticks: `100% / 521577 / 167237751`
- data fingerprint:
  `A6C8A9138AC7C924D2446AEA87963280F3BD9DAB896904BA46CC753D19B60DE5`
- identity source run-manifest SHA-256:
  `3087FDDC1C5CF3A106C3713EC96A4B988B716693CA63827973E6A75B7368A555`

Any post-run identity mismatch parks this ID as invalid evidence. It does not
authorize a rerun or parameter change.

## Exact Model-0 control

- Run role / model: `control / 0` (`Every tick based on real ticks`)
- Execution mode / fixed delay: `0 / 0 ms`
- Spread: `current`, followed only after all identity/lifecycle gates by the
  frozen research-proxy cost stress.
- Telemetry: `trade-only`, lifecycle-v3; generic lifecycle TCA discovery is
  mandatory.
- Validation stage / holding contract: `challenger / scalp`
- `promotion_eligible=false` under every result.

Exact overrides, sorted and immutable:

```text
InpATRPeriod=14;InpAsianEndMinutesUtc=360;InpAsianStartMinutesUtc=0;InpDailyFlattenMinutesUtc=1200;InpDeviationPoints=20;InpEnableTelemetry=true;InpEngineMode=1;InpFridayFlattenMinutesUtc=1200;InpHypothesisId=HYP-CBRK-EURUSD-M5-001;InpLotConsistencyLookbackFills=10;InpLotConsistencyMaxFactor=1.50;InpLotConsistencyMinFactor=0.50;InpLotConsistencyMinFills=10;InpMagic=5603201;InpMaxAccountDrawdownPct=8.0;InpMaxDailyLossPct=3.5;InpMaxHoldBars=96;InpMaxSpreadToRisk=0.15;InpMaxTradesPerDay=3;InpResearchAutoMode=true;InpRiskPercent=0.25;InpSweepEpsilonMult=0.30;InpSweepMinTp2R=1.50;InpSweepScaleOutFraction=0.50;InpSweepStopAtrMult=0.20;InpTradeEndMinutesUtc=960;InpTradeStartMinutesUtc=420;InpVariantTag=CBRK_EUR_BREAKOUT_MODEL0;InpVolumeLookback=20;InpVolumeThreshold=1.50
```

Sweep-only inputs remain frozen registry fields but are inert under
`InpEngineMode=1`; removing them would alter the shared executable contract.

## One-shot fatal gates

The training control is parked or killed without repair on this ID if any gate
fails:

1. source/prereg/task/receipt hashes, exact overrides, account/data
   fingerprints, compile `0/0`, non-repaint `PASS`, or lifecycle reconciliation;
2. any stop-out event, zero executed trades, or cadence outside `2.0-5.0`
   trades per elapsed calendar week;
3. PF below `1.30` or maximum equity drawdown above `8%`;
4. cost-repriced PF below `1.25` at x1.5 costs or below `1.00` at x2 costs;
5. overnight/weekend exposure, unbounded hold, foreign-position mutation,
   duplicate/missing final close, missing deal, or nonpositive initial risk;
6. fewer than 20% of completed lifecycles in either direction or any
   unregistered override.

A valid pass is research-only permission to invest more effort. Validation,
holdout, optimization, WFA/PBO/DSR/Monte Carlo, paper/live and promotion remain
locked.

## Trial and adaptation debt

- Economic trials consumed before this run: `0` for this identity.
- Authorized launches: exactly `1` training control.
- No grid, threshold search, session/weekday/year pruning, direction reversal,
  stop/target change, symbol pooling or same-ID rerun.
- Sweep observations contribute campaign adaptation debt and adverse prior only;
  they provide no numeric change permission for this breakout cell.
