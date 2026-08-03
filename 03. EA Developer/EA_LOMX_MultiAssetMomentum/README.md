# EA_LOMX_MultiAssetMomentum

This package is an engineering-valid, M5-only EA for two separable closed-bar
engines. The shipped defaults remain deliberately inert:
`InpResearchAutoMode=false` and `InpHypothesisId=UNREGISTERED_BUILD_ONLY`.
Initialization fails closed until an authorized workflow supplies a registered
ID, enables research auto mode, keeps lifecycle telemetry enabled, and runs on
M5.

The implementation campaign is complete, but the tested strategy plan is
**economic-invalid and not promotion-ready**. The exact EURUSD compression
breakout was killed by its frozen Model-0 base gates; the EURUSD sweep run was
identity-invalid and retained only as a strong adverse prior. XAUUSD was not
economically tested because its required full-population data/cost identity was
not valid. No optimization, validation, holdout, paper or live authority is
open.

## Campaign outcome

| Cell | Evidence status | Trades | PF | Trades/week | Net USD | DD | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| EURUSD Asian sweep-reclaim | identity-invalid full train observation | 694 | 0.5278 | 1.9036 | -7,052.61 | 6.81% | parked; no economic verdict, strong adverse prior |
| EURUSD generic compression breakout | valid full train Model 0 | 402 | 0.7467 | 1.1027 | -7,061.46 | 7.77% | killed: PF < 1.30 and cadence < 2/week |
| XAUUSD cells | no valid full-population Model 0 | — | — | — | — | — | unproven; no edge claim |

The breakout kill is valid before cost stress: both fatal base gates already
fail, so additional non-negative costs cannot rescue it. The cost builder also
reported a spread-coverage `total_count` metadata mismatch; no rerun was
authorized because it would not change the terminal base verdict. Canonical
evidence is in
`research/HYP-CBRK-EURUSD-M5-001_FAILURE_PACKET.json` and the latest registry
row for `HYP-CBRK-EURUSD-M5-001`.

## Frozen engine behavior

- `ENGINE_SWEEP`: builds the same UTC day's exact 00:00-06:00 Asian range from
  72 exact M5 bars. During 07:00-16:00 UTC, the last closed bar must sweep the
  relevant boundary by 0.30 ATR, reclaim it, and have prior-20 tick-volume
  z-score above 1.50. The stop is 0.20 ATR beyond the sweep extreme. Half is
  closed at the Asian midpoint, then SL moves to actual entry; TP2 is the
  opposite Asian boundary and the order is rejected unless it offers at least
  1.50R.
- `ENGINE_BREAKOUT`: bar 2 range must be below 0.70 of the prior-50 mean range;
  bars 2..16 form the box. Bar 1 must close at least 0.20 ATR beyond the box
  with tick volume above the prior-20 mean. The stop sits 0.10 ATR beyond the
  other box edge and TP is 2R.
- `ENGINE_BOTH`: evaluates both independently. If both fire on the same closed
  bar, Sweep wins deterministically; there is no Breakout fallback after a
  selected Sweep later fails execution geometry.

The FivePercent server clock is converted to UTC with the frozen era hybrid:
EU DST rules through 2023 and US DST rules from 2024. Friday flatten is 20:00
UTC. Every other trading day also flattens at 20:00 UTC; an independent
96-M5-bar max hold and a UTC date-change guard close only owned positions.

## Engineering controls

Trading state is scoped to `_Symbol + InpMagic`; unrelated positions do not
block the EA and are never closed. The 3.5% daily equity lock is persisted in
Terminal Global Variables by account, hypothesis, and symbol. Entry size uses
`OrderCalcProfit` with a tick-size/tick-value-loss fallback, floors to the
symbol volume step, validates stop/freeze geometry, and rejects excessive
spread relative to initial risk. A persistent 8% peak-equity account-DD lock
is independent of the daily lock. Live LOMX instances on the same account share
that peak/DD key; Strategy Tester runs isolate it by hypothesis to prevent
cross-experiment contamination. After enough same-magic entry fills, the
exact AvgLot10 may cap a new lot at 1.5x; a proposed lot below 0.5x AvgLot10
is rejected instead of being forced upward.

Lifecycle-v3 writes one `*_LifecycleTrades_*.csv` and one matching
`*_RunMeta_*.json`. `OnTradeTransaction` records the broker deal's real time,
volume, price, profit, commission, swap, fee, and reconciled deal net in the
exact `deal_*` columns required by the verified-cost builder. Each entry row
records its own fill-level initial risk, so partial fills cannot double-count
risk. Engine identity is attached to every deal row; a persistent final-close
marker prevents duplicate final rows.

## Verification

```powershell
python -X utf8 -m pytest "03. EA Developer\EA_LOMX_MultiAssetMomentum\tests" -q
powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory\alpha.ps1" compile "EA_LOMX_MultiAssetMomentum"
python "04. Memory\research\validate_candidate_registry.py" --registry "04. Memory\research\CANDIDATE_REGISTRY.jsonl"
```

The canonical breakout result is run `20260803_020947`: 100% history,
521,577 M5 bars, 167,237,751 tester ticks, exact preregistered account/data
fingerprints, and 402 OPEN rows reconciled to 402 final CLOSE rows with zero
unresolved closes.

## Exact input surface

The contract freezes these shipped names/defaults so a later preregistration can
bind overrides without guessing aliases:

```text
InpResearchAutoMode=false
InpEnableTelemetry=true
InpHypothesisId=UNREGISTERED_BUILD_ONLY
InpVariantTag=BUILD_SCAFFOLD_BOTH
InpEngineMode=ENGINE_BOTH
InpMagic=5603100
InpRiskPercent=0.25
InpMaxDailyLossPct=3.5
InpMaxAccountDrawdownPct=8.0
InpMaxSpreadToRisk=0.15
InpMaxTradesPerDay=3
InpDeviationPoints=20
InpATRPeriod=14
InpSweepEpsilonMult=0.30
InpSweepStopAtrMult=0.20
InpSweepMinTp2R=1.50
InpVolumeLookback=20
InpVolumeThreshold=1.50
InpAsianStartMinutesUtc=0
InpAsianEndMinutesUtc=360
InpTradeStartMinutesUtc=420
InpTradeEndMinutesUtc=960
InpDailyFlattenMinutesUtc=1200
InpFridayFlattenMinutesUtc=1200
InpSweepScaleOutFraction=0.50
InpMaxHoldBars=96
InpLotConsistencyMinFills=10
InpLotConsistencyLookbackFills=10
InpLotConsistencyMinFactor=0.50
InpLotConsistencyMaxFactor=1.50
```

Core strategy/session values are checked against this frozen profile at init;
they are visible inputs for receipt binding, not an invitation to tune the
unregistered scaffold.
