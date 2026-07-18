# HYP-CFTC-FX-H1-001 — Frozen Offline-Probe Preregistration

Status: `FROZEN_PRE_OUTCOME`  
Frozen at UTC: `2026-07-16T08:43:00Z`  
Authority: workspace `GOAL.md`, `research_doctrine.md`, and active `hot.md`  
Build authority: **none until this probe passes every gate**

## Hypothesis

The weekly change in leveraged-money FX options positioning contains a short-lived
Monday price-discovery effect that is not present in the same report's futures-only
positioning. The testable predictor is a delta-adjusted options-equivalent residual:

`options_net = (combined_lev_long - combined_lev_short) - (futures_lev_long - futures_lev_short)`

`signal = sign(options_net[t] - options_net[t-1])`

The CFTC explains that the combined report expresses options positions on a
futures-equivalent basis. The residual is therefore an options-derived positioning
quantity, not strike-level IV/skew and not signed order flow.

## De-dup decision

Existing V8 COT probes used futures-only asset-manager/leveraged-money levels or
changes with multi-day H4/D1 exposure and momentum controls. This hypothesis uses a
previously unused official `Combined - FutOnly` options residual, a fixed Monday
intraday holding window, and a matched futures-only positioning control. It is a new
data-field/mechanism test, not a threshold, session, RR, or direction rescue of a
killed COT/KLR/Unicorn/PO3 hypothesis.

## Immutable source contract

- Official archive index:
  `https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm`
- Futures-only annual files:
  `https://www.cftc.gov/files/dea/history/fut_fin_txt_YYYY.zip`
- Futures+options-combined annual files:
  `https://www.cftc.gov/files/dea/history/com_fin_txt_YYYY.zip`
- Hash manifest:
  `02. AlphaFactory/external/cftc_fx_options_tff/source_manifest.json`
- Manifest SHA256:
  `F281B9378A9D7774B2B2246EDC4D9A12ECD43698C5A9BDF919B3F8189EB7B7FD`
- Acquired years: `2017-2023` only. The 2017 rows may supply the prior observation
  needed for the first 2018 signal. No 2024-2025 CFTC archive is downloaded.
- Exact CFTC contract mapping:
  - EURUSD: `099741` (`EURO FX`), direction multiplier `+1`.
  - GBPUSD: `096742` (`BRITISH POUND`), direction multiplier `+1`.
  - USDJPY: `097741` (`JAPANESE YEN`), direction multiplier `-1`.
- Pair rows by `CFTC_Contract_Market_Code + Report_Date_as_YYYY-MM-DD`.
- Require exactly one futures-only and one combined row per paired event. Missing,
  duplicate, non-numeric, wrong `FutOnly_or_Combined`, or code/name mismatch fails
  closed for that event and is counted; more than two malformed events per split
  kills the probe.

## Point-in-time and split contract

- CFTC report date is Tuesday. The predictor becomes usable only on the following
  Monday, exactly `report_date + 6 calendar days`, at `07:00 UTC`.
- No Friday/same-week trading, no backfill to earlier bars, and no use of a later
  report before its availability timestamp.
- Train: entry dates `2018-01-01` through `2021-12-31`.
- Internal validation: entry dates `2022-01-01` through `2023-12-31`.
- Sealed holdout: `2024-01-01` through `2025-12-31`; no source archive, price bar,
  metric, or outcome may be loaded during this probe.
- Both train and internal validation must pass independently. Pooled results cannot
  rescue a failed split.

## Frozen trading rules

- Symbols: `EURUSD`, `GBPUSD`, `USDJPY`; one independent position per symbol.
- Price timeframe: H1, UTC timestamps from the D-portable MT5 terminal.
- Every non-zero predictor change creates one trade; there is no magnitude
  threshold, rank, percentile, volatility, day, month, or regime filter.
- Candidate direction: `sign(weekly change in options_net) * direction_multiplier`.
- Matched control direction: `sign(weekly change in futures-only leveraged-money
  net) * direction_multiplier`, on exactly the same eligible symbol/report events.
- A zero change creates no trade for that arm; it may not inherit the prior sign.
- Entry: open of the H1 bar timestamped Monday `07:00 UTC`.
- ATR: simple mean of true range over the 14 fully closed H1 bars ending at 06:59
  UTC. Stop distance: `1.5 * ATR14`, fixed at entry.
- Exit: stop price if crossed first; otherwise open of the H1 bar timestamped
  Monday `16:00 UTC`. No target, trailing, break-even, partial exit, overnight or
  weekend exposure.
- A stop touch is executable at the frozen stop; an adverse gap beyond the stop
  exits at that H1 bar's open (the worse executable price). Any
  missing 07:00 or 16:00 bar skips and counts the event; more than two skipped price
  events per split kills the probe.
- No simultaneous-symbol veto and no portfolio rank. This preserves expected book
  cadence near three events per elapsed week.

## Frozen research-cost and risk contract

This discovery probe cannot establish promotion-grade real broker cost. It uses a
deliberately explicit round-trip proxy and may only reject/build-authorize:

| Symbol | x1 proxy | x1.5 | x2 |
|---|---:|---:|---:|
| EURUSD | 1.5 pips | 2.25 pips | 3.0 pips |
| GBPUSD | 2.0 pips | 3.0 pips | 4.0 pips |
| USDJPY | 1.5 pips | 2.25 pips | 3.0 pips |

- Net R = `(directional gross pips - round-trip cost pips) / stop_distance_pips`.
- Risk per trade = `0.25%` of current simulated equity at the fixed stop distance.
- When a cost makes loss exceed one R, the full negative net R is charged.
- Equity is compounded trade-by-trade in timestamp then symbol order
  `EURUSD, GBPUSD, USDJPY` solely to calculate deterministic max drawdown.
- The proxy must never be relabeled `verified real cost`; promotion remains blocked
  until same-broker spread, commission, and slippage provenance exists.

## Frozen pass gates — every gate is mandatory

For the candidate separately on train and internal validation:

1. `2.0 <= trades / elapsed calendar week <= 5.0`.
2. x1 profit factor `> 1.30`.
3. x1.5 profit factor `>= 1.25`.
4. x2 profit factor `>= 1.00`.
5. x1 net R `> 0`.
6. deterministic x1 max drawdown `<= 5.5%` at `0.25%` risk/trade.
7. Each symbol has at least `40` trades in train and `20` in internal validation.
8. Train has at least `3/4` positive calendar years at x1; internal validation
   has `2/2` positive calendar years at x1.
9. Candidate x1 PF exceeds matched-control x1 PF by at least `0.05` and candidate
   x1 net R exceeds matched-control x1 net R on the same split.
10. Malformed source events `<=2` and skipped price events `<=2` per split.

There is no near-pass, weighted score, pooled rescue, or discretionary override.
Any failed gate means `KILL_AT_OFFLINE_PROBE`, no `.mq5`, compile, Strategy Tester,
holdout access, or post-hoc variant. A full pass authorizes only an independent EA
implementation, non-repaint audit, compile, and matched Model 0; it does not satisfy
`GOAL.md` and does not authorize live/paper trading.

## Frozen outputs

- Probe JSON and trade CSV under
  `03. EA Developer/EA_CFTCOptionsPulse/research/evidence/`.
- Source/price/storage identities, split metrics, control metrics, every gate, and
  sealed-holdout counters must be present.
- MT5 initialization must name the portable terminal on `D:` and pass
  `portable=True`; `mt5.shutdown()` is mandatory in `finally`.
- Protected C-drive storage roots require metadata snapshots before and after. No
  C-drive file is deleted unless a run-owned mutation is proven first.
