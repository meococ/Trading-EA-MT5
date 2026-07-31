# HYP-VRAS-EURUSD-M5-003 — Grok real-chart forensics (10 cases)

## Executive verdict

**Grok vision coverage PASS: 10/10 real Model-0 charts opened and reviewed.** Both five-image jobs passed runner, useful-output, structured-schema, exact case/position coverage, and `image_opened=true` checks. Parent reconciliation keeps the existing terminal verdict:

`KILL_MODEL0_NEGATIVE_EXPECTANCY_UNDER_CADENCE_REGIME_WHIPSAW`

The chart evidence explains failure anatomy but does not authorize a parameter rescue, source patch, rerun, promotion, or live use. It is consistent with the 93-position population: PF `0.591354`, net `-$5,243.22`, expectancy `-$56.38/trade` (`-0.231R` mean), 32 wins / 61 losses, Trend PF `0.641186`, and Range PF `0.133098`.

## Evidence and sampling integrity

- Population: all 93 positions with exactly one lifecycle `OPEN`, one final `CLOSE`, and one exact `ORDER_ACCEPTED` telemetry row.
- Sample was frozen before rendering: winner/loser tail and median, best/worst Range, seeded random winner/loser, and one matched Trend winner/loser pair.
- Ten unique high-resolution PNGs (`3240x2160`) were hash-verified against `casebook_manifest.json`.
- Each PNG contains M5 decision-as-of, M5 outcome anatomy, M15 context, H1 context, exact MT5 entry telemetry, initial SL/TP, actual exit, and bid-bar diagnostic MAE/MFE.
- Price alignment uses broker `server_time`. The D-side parquet `time_utc` clock differs from the EA telemetry clock by one hour during DST transition weeks; using it placed real fills on the wrong candles. EA UTC is retained only as telemetry metadata.
- Combined PNGs are outcome-aware. No observation here is a blinded entry-quality assessment.

Raw Grok artifacts remain under:

- `.context/vras-003-grok-chart-a-20260722/`
- `.context/vras-003-grok-chart-b-20260722/`

## Population decomposition (not inferred from the 10-case sample)

- Average winner: `+$237.11` / `+0.971R`; average loser: `-$210.34` /
  `-0.862R`; realized payoff ratio `1.127`. The implied breakeven win rate is
  `47.01%`, versus realized `34.41%`.
- Lifecycle commission totals `-$807.12` (`-$8.68/trade`); swap and fee are
  zero in the lifecycle. Before logged commission, PF is only `0.6398` and
  expectancy remains `-$47.70/trade`; commission moves these to PF `0.5914`
  and `-$56.38/trade`. This is bookkeeping, not verified broker TCA.
- 2019: 26 trades, PF `0.8420`, net `-$441.32`; 2020: 67 trades, PF `0.5216`,
  net `-$4,801.90`.
- London early: 31 trades, PF `0.8363`, net `-$691.12`; London/NY overlap:
  32 trades, PF `0.2582`, net `-$4,009.55`; NY late: 30 trades, PF `0.8306`,
  net `-$542.55`.
- BUY: 51 trades, PF `0.5607`, net `-$3,153.00`; SELL: 42 trades, PF `0.6302`,
  net `-$2,090.22`.
- Holding buckets: `<=15m` has 14 trades / zero winners / net `-$2,931.35`;
  `15-30m` PF `0.3409`; `30-60m` PF `0.3691`; `>60m` PF `1.6230` and net
  `+$2,003.64`. This is descriptive path decomposition, not authority to
  introduce a minimum hold or remove early stops.
- Top five winners contribute `26.11%` of gross winning P&L; worst five losses
  contribute `9.17%` of gross losing P&L. Failure is not explained by one or
  two isolated loss tails.

Hour, weekday, session, year, risk, ATR, or hold buckets must not be disabled
from this same outcome sample. Their purpose here is to test whether a claimed
failure is localized; the negative result is broad across both directions and
both active regimes.

## Case manifest and parent disposition

| Case | Stratum | Position | Signal | Net R | Bid MAE/MFE | Grok anatomy | Parent disposition |
|---|---|---:|---|---:|---:|---|---|
| C01 | winner tail | 88 | Trend short | +1.707 | 0.324 / 1.871 | Clean HTF-aligned continuation to target | Observed target-winner anatomy; not a distinct entry rule |
| C02 | loser tail | 86 | Trend short | -0.986 | 1.720 / 0.234 | Immediate adverse reclaim and near-stop exit | Strong stop-dominated failure; absolute stop width is not proven causal |
| C03 | winner median | 176 | Trend long | +1.021 | 0.899 / 1.392 | Survived near-stop MAE, then max-hold profit | MFE stayed below 1.8R TP; Grok target-region wording corrected |
| C04 | loser median | 14 | Trend short | -0.897 | 1.024 / 0.085 | Slow zero-MFE VWAP reclaim into stop | Strong stop-dominated failure |
| C05 | best Range winner | 60 | Range long | +0.448 | 0.837 / 2.070 | Partial mean reversion, max-hold under-capture | Best Range case still did not reach session-VWAP target |
| C06 | worst Range loser | 58 | Range long | -0.928 | 1.219 / 0.299 | Fade bought residual downside impulse | Consistent with very weak Range population, not a filter rule |
| C07 | seeded random winner | 74 | Trend short | +1.337 | 0.542 / 1.807 | HTF-aligned continuation, max-hold exit | Bid MFE does not prove executable TP; lifecycle says non-level exit |
| C08 | seeded random loser | 124 | Trend long | -0.901 | 1.115 / 0.948 | Nearly +1R MFE, then full reversal to stop | MFE-without-target binary-loss anatomy |
| C09 | matched Trend winner | 144 | Trend long | +1.549 | 0.178 / 1.916 | Clean H1/M15 continuation to target | Matched-case observation only |
| C10 | matched Trend loser | 132 | Trend long | -0.905 | 1.030 / 1.238 | +1.24R MFE, then reversal to stop | Same local gate family as C09; no population-causal claim |

## Ranked mechanisms

### 1. Stop-dominated Trend loss has two path shapes — HIGH confidence

- C02/C04 show gate-valid Trend entries with little or nearly zero favorable excursion before an economic full-stop loss.
- C08/C10 first produced substantial favorable excursion (`0.95R` and `1.24R`) but failed to reach the fixed target and then reversed to stop.
- Population support is independent of these selected cases: 55 stop exits lost `-$12,213.14` versus only 13 target exits earning `+$4,962.74`.

This explains the negative expectancy. It does **not** authorize break-even, trailing, target, or stop tuning from the observed paths.

### 2. Winner anatomy requires continuation after the same local gate stack — HIGH confidence

- C01/C09 are clean target winners with small MAE and coherent higher-timeframe continuation.
- C03/C07 are non-level, max-hold winners with deeper or incomplete path realization.
- The same Trend VWAP/AVWAP/M15 stack also appears in C02/C04/C08/C10 losers. Therefore the local gate stack is not visually discriminative by itself in this sample.

### 3. Range fades do not reliably separate exhaustion from residual impulse — HIGH confidence

- C05 is the best Range winner but realizes only `+0.448R` after `2.07R` bid MFE and never reaches the session-VWAP target.
- C06 buys the lower band while downside momentum remains active, reaches only `0.30R` MFE, and stops out.
- Population support: Range has only 10 trades, PF `0.133098`, and net `-$1,090.91`. No Range sub-edge is established.

### 4. ADX hysteresis labels can be stale relative to the current threshold reading — MEDIUM confidence

- C01 is still Trend at ADX `20.166` (between exit 19 and enter 25).
- C05 remains Range at ADX `27.097` while the dwell rule delays transition.
- C08 remains Trend at ADX `20.660`.

These are code-consistent states, not telemetry bugs. Together with the population diagnostic of 10,090 switches (`6.92/day`), they support the already-recorded regime-whipsaw failure mechanism. They do not identify a better threshold.

### 5. Matched C09/C10 suggests higher-timeframe path continuity as a future research lead — LOW/MEDIUM confidence

Both are Trend-long, London-early, mid-risk, mid-ATR positions with similar stop distance, ADX, and local VWAP/AVWAP/M15 acceptance. C09 has clean H1 continuation and shallow MAE; C10 has choppy H1 recovery and reverses after `1.24R` MFE. This is a two-case contrast, not evidence for an H1 filter. At most it is a mechanism-level lead for a fresh independent hypothesis.

## Parent corrections and boundaries

1. Grok described C03 as approaching or slightly exceeding the planned target region. Exact bid-bar MFE is `1.392R`, below the `1.8R` planned target; the correct interpretation is incomplete target capture followed by non-level max-hold profit.
2. C07 bid-bar MFE is `1.807R`, but lifecycle exit is `NON_LEVEL_FINAL_CLOSE`. A short closes on ask, and run-level spread provenance is incomplete; bid MFE cannot be promoted to an executable target hit.
3. C02's high `risk_pts` and ATR are descriptive. The ten-case review does not prove that wider absolute stop distance caused the loss.
4. The sample is deliberately stratified, so its five winners/five losers are not a win-rate estimate and its mechanism counts are non-exclusive.
5. Cost fields are EA estimates; strict execution/TCA truth remains blocked. The negative Model-0 result remains diagnostic and promotion-ineligible.

## Indicator-rich rendering correction

Owner review correctly rejected the original combined PNG format as an
indicator-overview chart. The ten Grok-bound files remain usable for candle
path anatomy, entry/SL/TP/exit, M15/H1 price context, and the exact MT5 entry
snapshot printed in their footer. They do **not** visualize the continuous
ADX/ATR/RSI/VWAP trajectories and therefore cannot support claims about how
those indicator paths evolved before or after entry.

An additive V2 renderer now produces a true indicator-rich chart without
overwriting the Grok-bound files. The C07 validation chart displays continuous
tick-weighted session VWAP and bands, equal-weight shadow VWAP, confirmed
AVWAP, ADX14 with 25/19 hysteresis, RSI14, ATR14/session SD, and M5/M15 VWAP
bias distances. All nine reconstructed entry values match exact MT5 telemetry
within frozen tolerances (`ENTRY PARITY PASS 9/9`). Artifact:

`indicator_rich_v2/VRAS-003-C07-P74_indicator_rich.png`

Until the remaining nine cases are rendered in V2 and re-reviewed, the Grok
10/10 verdict must be read as price-path plus entry-snapshot forensics, not
continuous-indicator trajectory forensics.

## Legal next work

No change to the killed object is legal from this evidence. If the Owner later opens a new research lane, the only defensible lead is an independently preregistered mechanism testing whether causal multi-timeframe directional continuity adds information beyond the current local VWAP/AVWAP/M15 gate stack. It must use a new hypothesis identity, fresh OOS data, a sealed definition, and no thresholds mined from these ten charts.

Current action remains: **do not rescue or rerun HYP-VRAS-EURUSD-M5-003.**
