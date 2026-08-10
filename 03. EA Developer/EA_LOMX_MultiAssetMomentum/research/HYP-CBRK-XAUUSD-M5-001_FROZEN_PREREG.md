# HYP-CBRK-XAUUSD-M5-001 — Frozen XAUUSD M5 compression breakout

Frozen before any new compile, MT5 launch, report read, trade outcome, PF, optimization, validation, or holdout access for this identity.

## Market thesis and decision identity

- EA: `EA_LOMX_MultiAssetMomentum`
- Atomic sleeve: `ENGINE_BREAKOUT` only
- Symbol/timeframe: native `XAUUSD / M5`
- Parent source screen: `HYP-LOMX-DESIGN-M5-002`
- Source SHA256: `D363121DC7FFCB128A67C796B76F8B86C8AB2262FF045EAC62B49FE19FB3298B`
- EA contract SHA256: `C3D0EA8E08BD4BF2F08A878FD76E9373FE8AF98134C9E88168D530B5ADB34D8C`
- Parent Stage-0 result SHA256: `8193E68D4EC240B696CDB91884C95976F3B47ECFFF740D5416BE2BEB4D2EF1DB`
- Parent candidate ledger SHA256: `4E836506FCB250B023DEE1B1DB1A2C0D141D7740DF893124941E971F7F438E0F`
- Native XAUUSD M5 bar source SHA256: `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`
- Hypothesis magic: `5603202`
- Variant: `CBRK_XAU_BREAKOUT_MODEL0`

The thesis is a participation-confirmed expansion from a locally compressed M5 balance during the liquid 07:00–16:00 UTC window. The compression bar defines reduced short-horizon auction range; the 15-bar box represents the balance; ATR-normalized clearance plus above-mean broker tick activity identifies price acceptance outside that balance. Tick volume is an activity proxy only, never aggressor flow, CVD, OFI, or true traded volume.

This is the exact XAUUSD atomic cell that the outcome-blind parent screen explicitly allowed to survive independently. It produced `2,072` source candidates over 2016-01-04 through 2024-12-31, `4.415220700152207/week`, LONG/SHORT `1,117/955`, and a maximum calendar-year share of `0.1303088803088803`. Source counts by year were `263/233/235/270/258/234/198/187/194` for 2016–2024. Thus the frozen 2018–2022 baseline window has `1,195` source candidates before execution/risk rejection.

The valid EURUSD run of the same atomic sleeve later failed with PF `0.7466504499` and cadence `1.1026645768/week`. That is a strong adverse cross-symbol prior, not permission to change a threshold, reverse direction, add a filter, or reject the untouched XAU cell without its own result. The XAU Asian-range sweep family is a different decision surface and supplies no parameter permission.

## Exact closed-bar signal

All arrays below are ordered from the most recently completed bar; `bar1` is the signal bar and the decision occurs at the next M5 open.

1. Wilder/MT5-equivalent `ATR14` is finite and positive on `bar1`.
2. `range(bar2) < 0.70 * mean(range(bar3..bar52))`; equality fails.
3. The buildup box is exactly `highest(high, bars2..16)` and `lowest(low, bars2..16)`.
4. Broker tick volume on `bar1` must be strictly above the mean of bars `2..21`; equality fails.
5. LONG iff `close1 > box_high + 0.20*ATR14`.
6. SHORT iff `close1 < box_low - 0.20*ATR14`.
7. LONG stop is `box_low - 0.10*ATR14`; SHORT stop is `box_high + 0.10*ATR14`.
8. Target is exactly `2.00R` from the requested entry after the source's outward tick normalization.
9. Signal window is `[07:00,16:00)` UTC. Daily and Friday flatten are `20:00 UTC`; maximum hold is `96` completed M5 bars.
10. One owned position/pending-order scope, no pyramiding. A signal is consumable once; risk, spread, session, geometry, exposure, or margin rejection does not queue a later entry.

No EMA/ADX/RSI/MACD, weekday deletion, news filter, direction veto, cooldown, break-even, trailing stop, partial exit, session change, threshold variant, or alternate target is authorized.

## Frozen baseline window and cost boundary

- Baseline TRAIN: `2018.01.02` through `2022.12.30`, one Model-0 control only.
- Validation: calendar 2023, locked until the baseline independently passes all engineering and economic gates.
- Holdout: calendar 2024, locked until TRAIN and validation independently pass.
- Tester deposit/leverage: `100000 USD / 1:100`.
- Broker/server: `Five Percent Online Ltd / FivePercentOnline-Real (Build 6090)`.
- Broker fingerprint: `E464F31D4B323A66DBC18D9409052E70F3711DB8F23597441648B19296B61D54`.
- Server fingerprint: `30B251638403D085CAB177A77A1B0EB69BD371793B501BE696F08033BE1E8DB0`.
- Account fingerprint: `0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073`.
- History quality must be strictly greater than `97%`; exact bars/ticks/data fingerprint and clock/series proof must reconcile before any outcome is admitted.
- Cost source is research-only XAUUSD evidence: observed M1 bid/ask spread population for 2018–2022, maximum tester-observed round-turn commission `$4.40/lot`, and direction-aware 1,000 ms quote-latency adverse-movement proxy. Missing fill slippage is not zero and blocks promotion under every baseline result.

The 2018–2022 run is a research falsification baseline, not the 84-month confirmed evidence required by `01. GOAL/GOAL.md`. If it passes, cost evidence and independent validation/holdout must be extended before a promotion-ready claim.

## Exact Model-0 controls

- Run role/model: `control / Model 0`.
- Execution mode/fixed delay: `0 / 0 ms`.
- Spread: `current`; cost repricing is applied only after identity, DQ, runtime, lifecycle, and deal reconciliation pass.
- Telemetry: `trade-only`, `lifecycle-v3`.
- Risk: `0.25%` equity requested risk; max daily loss `3.5%`; max account drawdown `8%`; max new trades/day `3`; max spread-to-initial-risk `0.15`; deviation `20` points.
- No optimization and no same-ID rerun.

Exact sorted override string:

```text
InpATRPeriod=14;InpAsianEndMinutesUtc=360;InpAsianStartMinutesUtc=0;InpDailyFlattenMinutesUtc=1200;InpDeviationPoints=20;InpEnableTelemetry=true;InpEngineMode=1;InpFridayFlattenMinutesUtc=1200;InpHypothesisId=HYP-CBRK-XAUUSD-M5-001;InpLotConsistencyLookbackFills=10;InpLotConsistencyMaxFactor=1.50;InpLotConsistencyMinFactor=0.50;InpLotConsistencyMinFills=10;InpMagic=5603202;InpMaxAccountDrawdownPct=8.0;InpMaxDailyLossPct=3.5;InpMaxHoldBars=96;InpMaxSpreadToRisk=0.15;InpMaxTradesPerDay=3;InpResearchAutoMode=true;InpRiskPercent=0.25;InpSweepEpsilonMult=0.30;InpSweepMinTp2R=1.50;InpSweepScaleOutFraction=0.50;InpSweepStopAtrMult=0.20;InpTradeEndMinutesUtc=960;InpTradeStartMinutesUtc=420;InpVariantTag=CBRK_XAU_BREAKOUT_MODEL0;InpVolumeLookback=20;InpVolumeThreshold=1.50
```

Sweep inputs are inert under `InpEngineMode=1` but remain frozen because the shared executable exposes them.

## Ordered gates

Engineering gates precede economics:

1. exact source/prereg/contract/parent/cost/task/receipt hashes and one-shot attempt authority;
2. fresh MetaEditor compile with `0 errors, 0 warnings` and nonempty EX5;
3. fresh exact-source non-repaint audit PASS; native M5 closed-bar parity for signal time, direction, ATR, box, stop, target, and rejection reason;
4. HQ `>97%`, exact window/clock/series/data identity, no truncation/runtime fatal/stop-out/orphan/pending exposure, and exact lifecycle↔deal↔report reconciliation;
5. `2.0–5.0` executed trades per elapsed calendar week, each direction at least `20%`, no overnight/weekend exposure, no hold beyond 96 completed bars;
6. PF `>1.30` after x1 research costs and maximum equity drawdown `<=8%`;
7. x1.5 cost PF `>=1.25`; x2 cost PF `>=1.00`.

Any engineering failure produces no economic verdict. Any economic failure closes this exact ID. A pass authorizes only a separately frozen validation stage; optimization, WFA/CPCV/PBO/DSR/Monte Carlo, holdout, paper, live, and promotion remain locked until their preceding gates pass.
