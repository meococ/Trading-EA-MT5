# PROBE PLAN - HYP-LSS-OB-REPL-EURUSD-M15-001

Status: FROZEN 2026-07-18 before any outcome, PnL, forward-return, MFE, MAE,
stop/target result, or 2023+ bar of this exact object was read.

This file is immutable after its SHA256 enters the candidate registry. A
pre-outcome correction requires a versioned `_V2` file and a new registry
transition. A post-outcome decision-surface change requires a new hypothesis.

## 1. Identity and authority

- Hypothesis: `HYP-LSS-OB-REPL-EURUSD-M15-001`.
- Research package: `EA_LSSOBPropScalper`; no `.mq5` is authorized until the
  density gate passes.
- Owner authority: direct implementation of the accepted review/build plan in
  the active thread on 2026-07-18.
- Source report:
  `05. Playbook/Strategy/LSS_OB_Prop_Scalper_v1.0_BaoCao_DeepResearch_18Jul2026.docx`.
- Report SHA256:
  `8F3EE339C52B7271CC9382DE21379E8C35C0D1646CEF133D1050D083FEC19223`.
- Symbol/timeframe: EURUSD M15 decisions with closed H1 structure and closed H4
  premium/discount context.
- Scope: no-outcome detector/fidelity and elapsed-calendar cadence feasibility.
  Passing this probe is not evidence of edge and does not authorize Model 0.

## 2. De-dup and adverse priors

- This is an Owner-authorized exact replication feasibility test, not an
  independent mechanism claim and not a rescue of any killed ICT/FVG object.
- Bound adjacent records: `HYP-FVG-SCALP-CONFL-M5-EUR-001`,
  `HYP-ICTVIS-EURUSD-M5-001`, the PO3/KLR/Unicorn ordered funnels, and the
  parked `HYP-ICT-FVG-FIDNEWS-EURUSD-M5-002` report-fidelity child.
- The only bounded difference being measured is M15 decision geometry with an
  enforced 8-12 pip stop-distance band and exact H1/H4 context.
- Adverse prior: stricter sweep -> displacement -> FVG/OB -> retest funnels have
  repeatedly fallen below 2 setups per elapsed week; a terminal cadence stop is
  the default expectation.

## 3. Hash-bound data and seal

- Bar file:
  `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet`.
- Bar SHA256:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- Data manifest SHA256:
  `2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54`.
- News CSV:
  `02. AlphaFactory/data/forexfactory/EURUSD/news_events/forexfactory_high_impact_eurusd_2019_2022.csv`.
- News CSV SHA256:
  `80B9DE46517B42F8B1D9A3ACCEFA6CC6D3DCB4DD06CAE357F16DE46228C64307`.
- Raw weekly news SHA256:
  `78CB2656A27278B1DA04B2C594A2C73BB1877DBA3AB52BCCFAC36A215945EA8F`;
  source class C, diagnostic only.
- Load filter: `2019-01-03T00:00:00Z <= time_utc < 2023-01-01T00:00:00Z`.
  The parquet reader must apply the `< 2023-01-01` filter at read time and the
  artifact must state `holdout_bars_loaded=0`.
- Split A: 2019-01-03 through 2020-12-31. Split B: 2021-01-01 through
  2022-12-31. Cadence uses inclusive elapsed calendar weeks, never active weeks.
- M1 is resampled on UTC bar-open boundaries into M15/H1/H4 closed bars.
- Offline indicators use `atr_mt5` and `adx_mt5` from the canonical probe SDK.
  Wilder variants are forbidden for this Model-0-bound surface.

## 4. Frozen detector surface

Every decision is made at a completed bar close; the earliest executable quote
is the first M1 open at or after that decision time.

### Context

- Pivot strength is exactly 2 left / 2 right closed bars. A pivot becomes usable
  only when the second right-side bar closes.
- H1 bias is the direction of the latest closed-bar break through a confirmed H1
  pivot. It persists until an opposing break; absent bias fails closed.
- H4 dealing range is the latest confirmed H4 pivot low and pivot high that
  bracket decision price. Long requires price at or below the 50% midpoint;
  short requires price at or above it. Missing/non-bracketing range fails closed.
- Eligible M15 bar opens are `[07:00,10:00)` and `[13:00,16:00)` UTC.
- Closed M15 `adx_mt5(14)` must be strictly greater than 25.0 at the arm's
  decision bar.
- A decision within +/-30 minutes, inclusive, of a bound EUR or USD high-impact
  event is rejected. News coverage is diagnostic source C and fail-closed.

### Ordered setup

1. With no active setup, the current closed M15 bar must wick through the latest
   confirmed same-side M15 pivot from the preceding 20 bars and close back
   inside. Long uses a low sweep; short uses a high sweep. H1/H4 context must
   align at the sweep close.
2. Within the next three closed M15 bars, a same-direction displacement must
   have `abs(close-open) >= 1.8 * atr_mt5(14)` and create a strict three-bar FVG:
   bullish `low[i] > high[i-2]`, bearish `high[i] < low[i-2]`.
3. The OB is the last opposite-direction M15 candle from the sweep bar through
   the bar immediately before displacement. Its body interval must have a
   non-empty intersection with the FVG. Any intermediate close through the OB
   adverse wick invalidates it.
4. The matched control becomes decision-ready at displacement close when its
   ADX, session, news and 8-12 pip stop geometry pass.
5. The challenger waits at most 12 closed M15 bars, never beyond the originating
   killzone. A close beyond the sweep extreme, H1 bias reversal, non-bracketing
   H4 range, or first overlap touch without confirmation invalidates the setup.
6. The first overlap touch confirms only when the bar is a directional body
   engulfing of the previous bar or has body/range >=0.60 and closes in the
   outer 25% of its range in the entry direction.
7. Stop reference is the farther adverse extreme of the sweep and OB wick plus
   1.5 pip buffer. Using the first executable quote, distance must be within
   8.0-12.0 pips inclusive. The density probe records decision geometry only;
   it never evaluates the stop, target, fill, or any forward price outcome.
8. Exactly one setup may be active per symbol. New sweeps are ignored until the
   active setup becomes ready, expires, or invalidates.

### Trial accounting

- Exactly two arms: `CONTROL` and `LSS_OB_CHALLENGER`.
- No threshold, session, direction, symbol, timeframe, expiry, geometry, news,
  RR, management or indicator sweep is authorized. Trial family N=2.
- Spread is not a density gate because the historical spread column failed cost
  provenance. The eventual economic plan remains diagnostic cost proxy only:
  1.5/2.25/3.0 pip round trip at x1/x1.5/x2.

## 5. Probe gate and terminal routing

The artifact must use `performance_metrics_authorized=false`,
`promotion_eligible=false`, `outcomes_included=false`, and contain no PnL,
return, MFE, MAE, profit factor, win rate, stop/target result, or holdout data.

All density gates are required:

1. Registry validator is green and the plan SHA is bound before execution.
2. Challenger event count is at least 300 total and at least 100 in each split.
3. Challenger cadence is 2.0-5.0 events per inclusive elapsed calendar week in
   pooled data and in both splits.
4. Event IDs are unique and deterministic; a repeated run over identical hashes
   produces identical ordered event IDs and funnel counts.
5. Holdout bars loaded equals zero and the latest loaded bar is before 2023.

Routing is mechanical:

- Any outcome-like field or holdout access -> `INVALID_DISCARD_NO_VERDICT`.
- Count/cadence below the floor ->
  `TERMINAL_STOP_FIDELITY_CADENCE_NO_BUILD_NO_MODEL0`.
- Cadence above 5.0/week -> `PARK_OVERBROAD_DETECTOR_NO_BUILD`.
- All gates pass -> `DENSITY_FEASIBLE_ONLY`; then and only then may a separate
  build/Model-0 transition bind source, capability, cost and matched-control
  execution evidence.

## 6. Required artifacts

- `REQUIREMENT_TO_CODE_MATRIX.md`.
- `lss_ob_probe_engine.py` and `lss_ob_density_probe.py` plus contract tests.
- Hash-bound density JSON and decision-time event CSV under `research/evidence/`.
- One registry transition and a readout with the terminal routing result.
- `hot.md`, `do_not_repeat_failures.md` for a kill, active-shelf/index pointers,
  and source-of-truth validation during closeout.

## 7. Forbidden rescue

No post-result change to ADX, pivot strength/lookback, session, displacement,
OB/FVG geometry, H1/H4 definition, news, confirmation, expiry, stop band,
direction, symbol or timeframe. Any alternative is a new hypothesis and fresh
de-dup, not an amendment to this record.
