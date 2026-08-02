# P0 Design Confirmation Plan — HYP-VRAS-USDJPY-M5-001

Date frozen: 2026-08-02

## Purpose

Test one outcome-blind claim before any V4 EA source, compile, Strategy Tester
run, trade simulation, cost calculation, or PnL read:

> USDJPY M5 prices during the Asian sleeve from 22:15 UTC through 05:30 UTC
> retain a statistically stable short-horizon mean-reverting structure that is
> compatible with a single Ornstein-Uhlenbeck entry engine.

This is a fresh successor. It does not reopen or modify
`HYP-VRAS-EURUSD-M5-015`. The counter restarts at `001` for the new USDJPY
symbol lane, consistent with other multi-symbol families in the registry.

## Frozen source

- Dataset:
  `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/USDJPY/USDJPY_M5_ALL_AVAILABLE_20260801.parquet`
- Dataset SHA256:
  `FECD42A01AFD14D4149121A122468DA5597939A20DD1533A36DA711E6FA2DAFD`
- Required identity: `symbol=USDJPY`, `timeframe=M5` for every selected row.
- DESIGN only: `[2016-01-04T00:00:00Z, 2021-01-01T00:00:00Z)`.
- Read columns: `symbol,timeframe,time_utc,close` only.
- Validation 2021-2024 and holdout 2025+ remain unopened by this probe.

## Frozen session and estimators

- Session: bars whose UTC open is in `[22:15,24:00)` or `[00:00,05:30)`.
- Session key: UTC date after adding 1 hour 45 minutes, so the wrapping sleeve
  is never stitched across unrelated days.
- A session is eligible only when it contains at least 80 bars and every
  consecutive timestamp is exactly five minutes apart.
- Hurst: variance-time slope on log close using lags `2,4,8,16`.
- Variance ratio: overlapping log returns with `q=5`, normalized by `q`.
- OU: `X[t]=a+b*X[t-1]+e[t]`; valid only when `0<b<1`; half-life is
  `-ln(2)/ln(b)` M5 bars.
- Uncertainty: 5,000 session-level bootstrap resamples, seed `20260802`.
- OU-valid-share uncertainty: Wilson 95% lower bound.

## Frozen gates

All gates must pass:

1. At least 1,000 eligible sessions and at least 180 in each year 2016-2020.
2. Upper 95% bootstrap bound of median Hurst is `<0.50`.
3. Upper 95% bootstrap bound of median VR(5) is `<1.00`.
4. Wilson 95% lower bound of the valid-OU session share is `>=0.50`.
5. Median valid OU half-life bootstrap interval lies within `[1,36]` M5 bars.

## Authority after result

- Pass: authorize freezing one atomic USDJPY M5 OU EA build contract. It does
  not authorize Model 0, validation, optimization, promotion, paper, or live.
- Fail: park this exact USDJPY M5 Asian OU thesis before EA source. Do not
  repair thresholds or session bounds under the same ID.
- Engines 1 and 2, candle-volume proxies, multi-engine arbitration, async
  mutation, other symbols, and other sessions are outside this P0 claim.

## Outcome-blind prohibitions

No trade entries/exits, forward returns, MFE/MAE, costs, PF, PnL, drawdown,
Model 0/4, optimization, validation, holdout, paper, or live data are permitted.
