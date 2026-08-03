# HYP-LASR-EURUSD-M5-001 - Frozen Preregistration

Frozen before any MT5 performance launch or outcome read for this hypothesis.

## Decision identity

- EA: `EA_LOMX_MultiAssetMomentum`
- Atomic sleeve: `ENGINE_SWEEP` only
- Ordered cell: `EURUSD M5`
- Parent: `HYP-LOMX-DESIGN-M5-002`
- Source SHA-256:
  `6243A3BE573B305AEDF223953D4E68A37866AE8C53512EABC3D430969B194B47`
- EA contract SHA-256:
  `C3D0EA8E08BD4BF2F08A878FD76E9373FE8AF98134C9E88168D530B5ADB34D8C`
- Logic matrix SHA-256:
  `E38A2C51B450B80B976B7378B92627565853100C275A622AF15E28C9C4F3ABAB`
- Parent Stage-0 result SHA-256:
  `8193E68D4EC240B696CDB91884C95976F3B47ECFFF740D5416BE2BEB4D2EF1DB`
- Static non-repaint result: `PASS`, SHA-256:
  `A30110B6199F3166A2A5D0378ED06F0D8575A3C88334A8FEB8129935CDA82679`
- Cost-source manifest: `RESEARCH_PROXY`, SHA-256:
  `662E0A95CDA8635193B86454D950BE71B95BE1F671E4AB4128F8F6A7844A9AFC`

The XAUUSD predecessor produced an invalid, truncated tester population and is
terminally parked. Its exposed observations were not used to change this
preordered EURUSD cell. Signal, clock, thresholds, risk and exits remain exactly
the outcome-blind Stage-0 rules. The generic compression arm and combined
dual-engine stream remain excluded.

## Frozen splits and population identity

| Split | Dates | Access now |
|---|---|---|
| Training control | `2016.01.04` - `2022.12.30` | exactly one Model-0 run after canonical dry-run passes |
| Validation | calendar year 2023 | locked until training independently passes every fatal gate |
| Holdout | calendar year 2024 | locked until training and validation independently pass |

The training population was measured outcome-blind through read-only MT5 APIs:

- synchronized M5 bars: `521865`
- bars with valid raw BID/ASK tick: `521799` (`99.987353%`)
- raw ticks: `250132587`
- expected MT5 report history quality: `100%`
- expected data fingerprint:
  `95C8BF165697BF69F9CEE60D78CE247F3967D2811623B2EC2C34B2B1D914497E`
- population receipt SHA-256:
  `034728C2B5BAD520E8DAA41B2CEB0E03A51122D724ECF27885BF50AA178F6574`

Any post-run mismatch parks this ID as invalid evidence before PF/cadence is
used. It does not authorize a rerun or a signal change.

## Exact Model-0 control

- Run role: `control`
- Tester model: `0` (`Every tick based on real ticks`)
- Execution mode/fixed delay: `0 / 0 ms`
- Deposit/leverage: `10000 USD / 1:100`
- Spread: `current`, then independently repriced with raw-tick spread,
  maximum tester commission and the quote-latency proxy.
- Telemetry: `trade-only`, lifecycle-v3 sidecars mandatory.
- Validation stage / holding contract: `challenger / scalp`
- Research-cost proxy opt-in: required; `promotion_eligible=false` under every
  result.

Exact overrides, sorted and immutable:

```text
InpATRPeriod=14;InpAsianEndMinutesUtc=360;InpAsianStartMinutesUtc=0;InpDailyFlattenMinutesUtc=1200;InpDeviationPoints=20;InpEnableTelemetry=true;InpEngineMode=0;InpFridayFlattenMinutesUtc=1200;InpHypothesisId=HYP-LASR-EURUSD-M5-001;InpLotConsistencyLookbackFills=10;InpLotConsistencyMaxFactor=1.50;InpLotConsistencyMinFactor=0.50;InpLotConsistencyMinFills=10;InpMagic=5603102;InpMaxAccountDrawdownPct=8.0;InpMaxDailyLossPct=3.5;InpMaxHoldBars=96;InpMaxSpreadToRisk=0.15;InpMaxTradesPerDay=3;InpResearchAutoMode=true;InpRiskPercent=0.25;InpSweepEpsilonMult=0.30;InpSweepMinTp2R=1.50;InpSweepScaleOutFraction=0.50;InpSweepStopAtrMult=0.20;InpTradeEndMinutesUtc=960;InpTradeStartMinutesUtc=420;InpVariantTag=LASR_EUR_SWEEP_MODEL0;InpVolumeLookback=20;InpVolumeThreshold=1.50
```

## One-shot fatal gates

The training control is parked or killed without repair on this ID if any gate
fails:

1. source/prereg/task/receipt hashes, exact overrides, report population
   fingerprint, compile `0/0`, non-repaint `PASS`, or report-deal-lifecycle
   reconciliation does not match;
2. zero executed trades or cadence outside `2.0-5.0` trades per elapsed calendar
   week;
3. PF below `1.30` or maximum equity drawdown above `8%`;
4. cost-repriced PF below `1.25` at x1.5 costs or below `1.00` at x2 costs;
5. overnight/weekend exposure, unbounded hold, foreign-position mutation,
   duplicate/missing final close, missing deal, or nonpositive initial risk;
6. fewer than 20% of completed lifecycles in either direction or any
   unregistered override.

A valid pass is research-only permission to invest more effort. Validation,
holdout, full nine-symbol coverage, WFA/PBO/DSR/Monte Carlo, paper/live and
promotion remain locked.

## Trial and adaptation debt

- Economic trials consumed before this run: `0` for this identity.
- Authorized launches: exactly `1` training control.
- No grid, threshold search, session/weekday/year pruning, direction reversal,
  stop/target change, symbol pooling, or same-ID rerun.
- The invalid XAUUSD run counts in campaign adaptation debt but supplies no
  numeric tuning permission.
