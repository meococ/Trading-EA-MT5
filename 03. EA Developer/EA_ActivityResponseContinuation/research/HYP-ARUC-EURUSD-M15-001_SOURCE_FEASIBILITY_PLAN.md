# HYP-ARUC-EURUSD-M15-001 — Frozen source-feasibility plan

Status: `FROZEN_PRE_OUTCOME_SOURCE_BUILD_ONLY`

This document freezes an inert, outcome-blind Stage-0 source/cadence screen for
`EA_ActivityResponseContinuation`. It is not authority to open DESIGN data. A
real source read remains disarmed until a later hash-bound run packet is
independently reviewed, its SHA replaces the source sentinel, and the exact
latest registry row grants the one bounded source-feasibility attempt.

## Identity and causal thesis

- Hypothesis: `HYP-ARUC-EURUSD-M15-001`
- Family: `activity-response-underreaction-continuation`
- Symbol/timeframe: FivePercent `EURUSD`, M15 decisions, H1 volatility.
- Thesis: unusually high broker activity accompanied by directionally coherent
  within-bar price changes can identify a gradual price response rather than a
  completed impulse. This stage asks only whether the causal decision surface
  forms often enough, is direction/year balanced, has executable timestamp
  coverage, and has plausible stop-to-cost geometry.
- Critical caveat: broker tick volume and `sign(delta close) * tick_volume` are
  directional activity proxies, not actual signed interdealer order flow. Any
  later economics study must beat both frozen controls by `delta PF >= 0.15`
  and `delta meanR >= 0.05`, in addition to the standard gates. Those economic
  comparisons are not computed here.

## Exact public DESIGN custody

Only public DESIGN dates `2016-01-04` through `2020-12-31` inclusive may be
addressed. The M1 and H1 manifests each contain the exact same ordered 1,555
date sequence: 1,298 Monday-Friday decision dates plus 257 Sunday history
dates, and no Saturdays. All shards remain available to causal history, but
Sunday rows never enter the activity business-date index, decision slots or
formation denominator. Research validation, holdout, private and sealed
branches remain closed.

### M1

- Manifest: `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl`
- Manifest SHA256: `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7`
- Receipt: `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_receipt.json`
- Receipt SHA256: `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8`
- Immutable source SHA256: `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`
- Exact public shape: 1,555 manifest dates and 1,859,820 DESIGN M1 rows.
- Exact shard template: `public/DESIGN/YYYY-MM-DD/m1.parquet`.
- Exact Arrow schema, in order: nullable `time_server timestamp[ns]`,
  `time_utc timestamp[ns]`, `utc_offset_h int8`, OHLC `float64`,
  `tick_volume uint64`, `spread int32`, `real_volume uint64`.
- Each shard must have one row group. Every manifest row binds exact date,
  relative path, byte count, row count and shard SHA256. The M1 public manifest
  contract has exactly those five fields plus date; it does not acquire a
  synthetic `schema_version` field.

### H1 BID

- Manifest: `02. AlphaFactory/data/fivepercent/EURUSD/h1_splitvault_002/public/design_manifest.jsonl`
- Manifest SHA256: `DA513911B01B1C4232611225C77A4F22E9E3C89E719EE530923BD574D06451E5`
- Receipt: `02. AlphaFactory/data/fivepercent/EURUSD/h1_splitvault_002/public/design_receipt.json`
- Receipt SHA256: `623328512F0CB77B52B155F6CD314EA2B47DAC40636A7714BD38167BEA807B13`
- Collection: `DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002`, closed H1 BID bars.
- Exact public shape: 1,555 manifest dates and 31,057 DESIGN H1 rows. Receipt
  `source_rows=71,785` is the raw full-source count and must not be equated to
  the public DESIGN manifest row sum.
- Exact shard template: `public/DESIGN/YYYY-MM-DD/h1.parquet` and manifest-row
  schema `h1_splitvault_002_public_design_shard.v1`.
- The same exact Arrow schema and one-row-group rule apply. Every manifest row
  binds exact schema, date, relative path, byte count, row count and SHA256.

Both decoders must reject non-canonical JSON, duplicate keys/timestamps,
unordered rows or dates, nulls, non-finite/invalid OHLC, wrong integer domains,
wrong physical schema or row-group count, bytes/rows/SHA mismatch, aliases,
hardlinks, symlinks, reparse points, path escape, alternate custody branches,
and time/clock drift. The audited FivePercent server-clock conversion remains
mandatory: naive `time_server`, naive `time_utc`, the recorded offset,
`server_offset_hours`, and `server_to_utc` must all agree exactly. No generic
timezone check is relaxed. The clock implementation is
`02. AlphaFactory/tools/research/fivepercent_server_clock.py`, SHA256
`A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52`.
The exact M1/H1 manifest date sequences must match before any shard is opened.

## Causal construction

### M15 and activity

- UTC M15 bins are aligned at minutes `00,15,30,45`.
- A complete bin contains exactly the 15 distinct contiguous M1 opens from
  bin open through `open+14m`, and the exact previous-minute close at
  `open-1m`. Without that previous close the bin is incomplete.
- `Q = sum(sign(close_i - close_{i-1}) * tick_volume_i)` for the 15 rows;
  zero price change contributes zero. `sum_tv = sum(tick_volume_i)`.
- `A = sum_tv / median(prior sum_tv)` using the same UTC M15 clock slot on the
  exact 20 preceding dates in the ordered 1,298-date Monday-Friday decision
  set. Sunday history rows, the current date and all future dates are excluded.
  A missing prior slot, non-positive median, or fewer than 20 prior dates makes
  activity unavailable; older dates are not substituted.
- Closed-bar decision availability is M15 open plus 15 minutes.

### H1 ATR20 and normalized response

- True range uses closed H1 BID bars. ATR20 seeds with the arithmetic mean of
  the first 20 true ranges (the first bar uses high-low), then applies Wilder
  recurrence `ATR_t = (19*ATR_(t-1) + TR_t)/20`.
- At an M15 decision close, select only the latest H1 bar whose
  `H1 open + 1h <= decision availability`. No still-forming H1 bar is eligible.
- Closed Sunday H1 bars remain in the causal ATR history; they never create a
  decision date by themselves.
- `R = (M15_close - M15_open) / ATR20`. Missing/non-positive ATR is ineligible.

## Frozen decision arms

All arms use Monday-Friday M15 opens `>=07:00` and `<15:00` UTC and independently
keep only the first qualifying signal per UTC date.

### PRIMARY

- `A >= 1.50`
- `abs(Q)/sum_tv >= 0.55`, with `sum_tv > 0`
- `sign(Q) == sign(R)` and both are non-zero
- `0.15 <= abs(R) <= 0.50`
- Direction is `sign(Q)`.

### PRICE_ONLY

The exact same `R`, clock window and daily cap apply, but Q and A are dropped.
Direction is `sign(R)`. This control may form as soon as its causal H1 ATR is
available; it does not inherit an activity-history condition that it removes.

### SHIFTED_TICKS

For a decision date at index `d` in the ordered 1,298-date Monday-Friday
decision list, use the tick-volume vector from the same UTC M15 slot at
index `d-5` but
multiply it by the 15 exact current-date M1 price signs. Its shifted activity
denominator is the same-slot `sum_tv` median from exact date indices
`d-25..d-6`, strictly before the shifted source date. It then applies the same
Q/A/R thresholds and cap as PRIMARY. Any missing date, slot, vector, or baseline
fails closed; no nearer/older substitute is allowed.

## Frozen timestamp-only ledgers and geometry

- PRIMARY, PRICE_ONLY and SHIFTED_TICKS each emit a deterministic canonical
  ledger, sorted by decision time. Every row has a stable arm-bound signal ID,
  decision/availability UTC timestamps, direction/year, only its arm-specific
  causal A/Q/sum_tv fields (none for PRICE_ONLY), the exact shifted source date
  for SHIFTED_TICKS, R, ATR20, cost-to-SL ratio, and its timestamp-only horizon
  mapping. Counts alone are insufficient.
- For every signal in every arm, entry time is the open timestamp of the first
  complete observed M15 bin at or after decision availability. Entry delay is
  recorded in minutes and is source-executable only when `delay <= 60`.
- The horizon API receives timestamps only. The entry bin is observed horizon
  bar 1; by observed-bin index, bars 1-4 are used even across wall-clock gaps.
  Exit availability is the close timestamp of observed horizon bar 4. Fewer
  than four bars is right-censored. No post-entry OHLC value may be passed,
  read, projected or emitted.
- Funnel reasons are explicit: no observed entry, delay over 60 minutes,
  fewer than four observed horizon bars, or source-executable.
- Geometry only: `SL = 1.0 * H1 ATR20`; record
  `1.50 pip / SL_pips`. There is no TP, break-even, trail, partial, return,
  PnL, PF, DSR, trade or performance field. A later economic contract would
  use the close of observed horizon bar 4 as its time exit and risk 0.25%, but
  neither price nor risk sizing is opened here.

## Frozen Stage-0 gates

PRIMARY must pass every gate:

1. cadence `2.0..5.0` per elapsed calendar week, inclusive;
2. long share `>=0.25` and short share `>=0.25`;
3. no calendar year share `>0.30`;
4. complete scheduled M15 formation ratio `>=0.99` after activity warmup;
5. source-executable horizon ratio `>=0.99`;
6. median `1.50 pip / SL_pips <=0.25`;
7. at least 20 PRIMARY signals per side.

The formation denominator is all 32 scheduled UTC slots on each Monday-Friday
decision date starting at decision-date index 20: `(1,298-20)*32 = 40,896`.
Sunday manifest dates are history-only and excluded. The numerator requires a
complete current M15 bin with its previous minute; missing prior activity or
ATR is reported separately and cannot turn an incomplete bin into a formed
bin. Reports emit all three frozen ledgers and counts, PRIMARY year/direction
counts, the formation funnel, PRIMARY horizon funnel and reason counts. Only
the PRIMARY timestamp horizons feed the unchanged PRIMARY gates.

`SOURCE_PASS_FUTURE_ECONOMICS_PREREG_ONLY` authorizes only drafting a separate
future economics preregistration. It never authorizes economics automatically.
Later context, not a computation in this task: exact cost tiers are
`1.50/2.25/3.00 pip`, and standard PF/DD/cadence gates still apply.

## Prohibitions and disarm

- No outcome/post-entry prices; returns, PnL, PF, DSR or performance analysis.
- No optimization, charting, validation/holdout/private/sealed access, network,
  paid request, MQL5, MT5, Model 0, promotion, paper or live action.
- No registry mutation and no evidence attempt in this build task.
- Import and default CLI are inert. A future real DESIGN read requires all of:
  explicit run switch, a canonical future packet whose exact SHA replaces the
  source sentinel, exact builder/test/plan/data bindings, and an exact latest
  registry row with a strict validation-object whitelist. Its key set must be
  exactly the two intended source-feasibility fields, every frozen-capability
  field and the six required attempt/data-binding fields; no extra key is
  permitted regardless of its name or value. `source_feasibility_only` and
  `source_feasibility_run_authorized` must be literal true, every frozen
  capability must be literal false, and all six binding values must match
  exactly.
