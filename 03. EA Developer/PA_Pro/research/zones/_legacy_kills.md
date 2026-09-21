# Legacy kills in the support/resistance zone space

Task: T-PAPRO-ZONE-1 (program PA-PRO). Purpose: what the legacy repo already
killed in the zone/level space, with exact metrics and file:line, so PA-PRO
R01 (charter §4 level physics) does not re-run a dead trade strategy and does
not cite a dead object as if it were a zone-physics measurement.

Scope note (from `04. Memory/do_not_repeat_failures.md:3-8`): the catalog is an
evidence catalog, not a family blacklist. Each entry blocks only its bound
hypothesis/candidate identity and direct post-hoc rescue. A materially new
mechanism under a new ID with a declared delta may proceed.

Primary sources read: `04. Memory/do_not_repeat_failures.md`, `04. Memory/hot.md`,
`04. Memory/research/20260912_ERA2_FALSIFICATION_BOARD.md`,
`04. Memory/research/CANDIDATE_REGISTRY.jsonl`,
`04. Memory/research/CANDIDATE_REGISTRY.era1.archive.jsonl`,
`04. Memory/research/20260919_LAB_FALSIFICATION_MAP_AND_COST_REFRAME.md`,
`04. Memory/research/20260906_SMC_INTRADAY_METHODS.md`,
`04. Memory/research/20260906_TV_SMC_INDICATOR_REVIEW.md`,
`03. EA Developer/EA_VolmanPA/PLAN/econ1/ECON1_RESULTS.md`,
`03. EA Developer/PA_Pro/PA_PRO_CHARTER.md`.

Charter §0 index (authority summary, `03. EA Developer/PA_Pro/PA_PRO_CHARTER.md:15-24`):
VPA DR3 "micro-line + tight-stop object is dead" (line 18); "pin bar, engulfing,
fractal, order block, OTE, ICT FVG chains, liquidity sweeps at PDH/PDL/Asia
range (PF 0.56-1.01), round-number fade (PF 0.74 on 26,819 trades), ORB/session
breakouts (regime pockets), inside-bar/squeeze compression, VWAP family, z-fade
mean reversion (8,100 sims, max gross PF 1.25), exit overlays, AND-stacks"
(lines 20-24). Structural lessons: every dead family was tight geometry;
cost/stop ratio is the binding axis (lines 27-29). Any kill below is a trade
strategy/PnL verdict, not a zone-reaction measurement.

ERA-2 board context: `04. Memory/research/20260912_ERA2_FALSIFICATION_BOARD.md:10-26`
(kill table), `:41-52` (every tested mechanism gross-negative; "Cost drag is
~30% of PF: median cost PF x1.0 ≈ 0.68 vs gross ≈ 0.83. Even a hypothetically
break-even gross signal cannot reach 1.30.").

---

## 1. Round-number FADE (00/50 touch-and-reverse)

- **Family / hypothesis ID**: `HYP-RND-GB-M5-001` / `EA_Rnd`
  (ghost package `EA_RoundNumberCascade` is a different family — see §2).
- **What was tested**: GBPUSD M5 round-number fade with H4 EMA filter,
  1.5xATR stop / 1.5R target, research cost proxy
  (`"feature_family":"gbpusd-m5-round-number-fade-h4ema-1p5atr-1p5r-research-cost-proxy"`),
  window 1999.01.01-2026.09.11, Model 0, run `20260912_134228`.
- **Evidence**:
  - `04. Memory/research/CANDIDATE_REGISTRY.jsonl:21` — verdict
    `"KILLED_AT_MODEL_0"`; reason verbatim: `"Economic kill: gross PF 0.742, net -9200, DD 92.0%, cost PF x1.0=0.677 x1.5=0.627 x2.0=0.581. Cadence 18.6/wk PASS but economics gross-negative."`; metrics:
    `"trades":26819`, `"trades_per_week":18.6`,
    `"profit_factor":0.7422722490091693`, `"net_profit":-9200.19`,
    `"max_drawdown_pct":92.02802416480958`, `"win_rate_pct":38.5`,
    `"cost_pf_x1_0":0.676961499`, `"cost_pf_x1_5":0.626886964`,
    `"cost_pf_x2_0":0.580726287`, `"nonrepaint_audit":"PASS"`.
  - `03. EA Developer/PA_Pro/PA_PRO_CHARTER.md:21-22` — the metric is stated in
    the charter rather than a memory readout: `"round-number fade (PF 0.74 on
    26,819 trades)"`.
  - Ghost provenance only (no metric): `04. Memory/research/20260813_XAU_FOREX_ONLY_SCOPE_AND_CATALOG_AUDIT.md:125`
    lists `03. EA Developer/EA_RoundNumberCascade/research/`;
    `04. Memory/research/20260831_REPO_CLEANUP_AND_PATH_MIGRATION_PLAN.md:37`
    lists `EA_RoundNumberCascade` as a ghost (no folder, no verdict there).
  - Source-frontier statement:
    `04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P1_SOURCE_MATRIX.md:43`
    — `"Source evidence does not establish a profitable round-number rule, and
    Osler does not establish XAU/BTC transfer. If a universal scale fails, the
    field stays telemetry-only."`
  - Refusal row: `03. EA Developer/PA_Pro/bank/HYPOTHESIS_BANK.md:1036` (R1) —
    `"Round-number FADE (touch-and-reverse at 00/50) ... Same object and same
    side as the killed round-number fade; a grid/step change is a parameter
    change"`.
- **Why it does NOT forbid zone physics**: this tested a trade (touch-and-fade
  entry, stop/target/cost PnL at the round grid). It never measured the
  conditional reaction proportion at real 00/50 levels versus matched fake
  levels at the same time/side/distance/width. PA-PRO R01 introduces exactly
  that control: a real-vs-fake approach census with BOUNCE/BREAK/NONE and
  symmetric ATR barriers, no fills and no PnL. The mechanism delta is the
  measured quantity (reaction proportion, not fade profitability) and the
  control construction (matched fake zones, not a shifted grid).
- **Confidence**: high (direct registry line + charter line; ghost refs
  verified).

---

## 2. Round-number cascade / round-grid continuation (EURUSD M5)

- **Family / hypothesis ID**: `HYP-ROUND-CASCADE-EURUSD-M5-001..011` /
  `EA_RoundNumberCascade` (era-1 registry; final economic child HYP-011).
- **What was tested**: round-grid object on EURUSD M5 with a TRUE grid arm
  (`TRUE_0050`) versus a shifted-grid control (`SHIFTED_0025`), design
  economics only, public DESIGN split. HYP-002 source probe:
  `TRUE_0050 produced 1,229 signals at 4.7166 per elapsed week and
  SHIFTED_0025 produced 1,220 at 4.6820`; HYP-008 classified `2,449 fixed
  source rows`, `2,434 eligible rows`; HYP-010 eligible population
  `2,431 rows (TRUE=1,218; SHIFTED=1,213)`.
- **Evidence**:
  - `04. Memory/research/CANDIDATE_REGISTRY.era1.archive.jsonl:326-327`
    (HYP-011 rows). Killed reason verbatim: `"The single authorized HYP011
    public-DESIGN economics attempt completed engineering-valid with all 2,431
    pre-outcome eligible rows mapped and simulated. At 1.50 pips the TRUE arm
    produced PF=0.6762, mean=-0.12339R, total=-150.28R, zero positive years,
    DSR=1.55e-7 and 32.54% compounding drawdown; only cadence passed, while ten
    of eleven frozen gates failed. Higher costs worsened PF to 0.5655 and
    0.4747. The SHIFTED control was also negative, and TRUE-minus-SHIFTED
    separation was far below the frozen thresholds."`
  - `:295-296` — HYP-002 `PASS_SOURCE_FEASIBILITY` (cadence numbers above).
  - `:320-325` — HYP-008/HYP-010 timestamp-only PASS rows (population counts).
  - The whole HYP-001..010 chain is engineering-invalid/consumed (float
    materialization, timezone decoding, missing contiguous M1 window, receipt
    canonicalization, diagnostic-key guard); no economics before HYP-011.
- **Why it does NOT forbid zone physics**: HYP-011 is the closest legacy object
  to a "do levels matter" test (it had a shifted-grid control and failed), but
  it measured traded PnL on grid crossings (entry/stop/target/costs), not the
  conditional bounce/break proportion. Its control was a grid shifted by 25
  pips, not fake zones matched per event on time, side, distance and width.
  PA-PRO R01 measures the proportion of BOUNCE vs BREAK at real zones against
  K=5 matched fake zones with symmetric ATR barriers and no PnL, so the
  mechanism delta is the quantity measured and the control design. Do not cite
  HYP-011 as proof that "round levels do nothing" or that "they matter"; it
  proves only that the cascade trade object lost.
- **Confidence**: high (verbatim archived registry rows; line numbers verified).

---

## 3. PDH/PDL closed-bar sweep-reclaim fade (XAUUSD H1)

- **Family / hypothesis ID**: `HYP-SWEEPFADE-XAUUSD-H1-001`.
- **What was tested**: closed-bar prior-day-high/low sweep-reclaim fade,
  XAUUSD H1, MetaQuotes-Demo only, train run `20260816_130548`.
- **Evidence**:
  - `04. Memory/do_not_repeat_failures.md:25-33` — verbatim: `"Train
    `20260816_130548` HQ 99% / N=1150 / PF 1.01 / net +85 / DD 4.70% /
    exp +0.07. Six years PF 0.78–1.21 around 1; none ≥1.30. Exit mix
    SL-like ~48% / TP-like ~29% / DAILY_FLAT ~17% / FRIDAY_FLAT ~5% /
    TIME_STOP ~0 — no single exit defect."`; radius: `"Radius is this PDH/PDL
    fade envelope, not every sweep forever and not the goal."`
- **Why it does NOT forbid zone physics**: this was a fade trade at the level
  after a closed-bar reclaim; its PF ~1.0 says the entry/exit/cost structure
  had no edge, not that price does not react at PDH/PDL. R01 asks whether
  fresh approaches to real PDH/PDL zones produce BOUNCE more often than matched
  fake levels, with no order, no stop, no target. Mechanism delta: reaction
  proportion with a matched-fake control instead of a sweep-fade PnL.
- **Confidence**: high (direct file:line).

---

## 4. Multi-level liquidity-sweep reversion (EA_LiquiditySweep, EUR + XAU M5)

- **Family / hypothesis ID**: `HYP-LSWEEP-EUR-M5-001`,
  `HYP-LSWEEP-XAU-M5-001` / `EA_LiquiditySweep` (Osler 2003 stop-cluster
  reversion; `InpRoundStep` 0.0050 EURUSD / 5.0 XAUUSD).
- **What was tested**: multi-level liquidity-sweep reversion, EURUSD M5 and
  XAUUSD M5, 1.3R / 24-bar, governed Model 0.
- **Evidence**:
  - EUR: `04. Memory/research/20260912_LSWEEP_EURUSD_KILL_AND_AUDIT_UPGRADE.md:11-16`
    — verbatim: `"Trades | **172 — cadence 0.12/wk, FAIL outright**"`,
    `"Report PF / Net / DD | 0.68 / -887 USD / 10.0%"`,
    `"Cost PF x1.0 / x1.5 / x2.0 | **0.620** / 0.592 / 0.566"`. Registry:
    `04. Memory/research/CANDIDATE_REGISTRY.jsonl:10` — reason `"N=172, report
    PF=0.68, net -887 USD, max DD 10.0%, WR 28.5%. Cadence FAIL outright
    (0.12/wk vs 10-40 band)"`; metrics `"profit_factor":0.6776`,
    `"cost_pf_x1_00":0.6196`, `"cost_pf_x1_50":0.5922`,
    `"cost_pf_x2_00":0.5664`, `"trades_per_elapsed_week":0.12`.
  - XAU: `04. Memory/research/CANDIDATE_REGISTRY.jsonl:29` — reason `"N=136,
    report PF=0.556, net -950 USD, max DD 9.9%, WR 26.5%. Cadence FAIL outright
    (0.046/wk on the requested window, ~0.12/wk on real 2004-2026 coverage vs
    the 10-40 band)"`; `"PF 0.479 @x1.0, 0.443 @x1.5, 0.411 @x2.0"`; metrics
    `"profit_factor":0.5561`, `"net_profit":-950.29`,
    `"trades_per_elapsed_week":0.12`. Hot cache:
    `04. Memory/hot.md:16-22` — `"N=136, PF 0.556, net -950 USD, cadence
    ~0.12/tuần"` and `"Mechanism hiếm một cách cấu trúc (~6 sweep/năm) trên cả
    EUR lẫn XAU"`.
  - Lab sweep-fade class: `04. Memory/research/20260919_LAB_FALSIFICATION_MAP_AND_COST_REFRAME.md:34`
    — `"prior-day sweep fade | ~700 | EURUSD sweepLo PF 1.40, erratic years
    (−18.6/−27.9), n collapse post-2021 | MARGINAL — fails stability,
    sub-cadence"`; `:69` — `"EURUSD prior-day sweep-low fade — PF 1.40, +7.44p,
    ~0.5/wk, fat-tail year distribution, single-side single-symbol."`
- **Why it does NOT forbid zone physics**: both sleeves are sweep-reversion
  trades (enter after a sweep, stop at the wick, 1.3R target); they show the
  sweep trade is structurally rare and gross-negative after cost, not whether
  the swept level is a zone where price reacts. The matched control that killed
  them is the cadence band/cost, not fake levels. R01's fresh-approach census
  measures BOUNCE/BREAK at real levels versus matched fake levels; the sweep
  event itself is not required and no fill is taken. Mechanism delta: reaction
  proportion at levels instead of sweep-entry PnL.
- **Confidence**: high (two kill docs/registry rows with exact numbers).

---

## 5. Prior-day-liquidity raid → displacement/MSS → FVG (KLR, XAU M5)

- **Family / hypothesis ID**: `HYP-KLR-USD-PDLRAID-M5-XAU-001`,
  `HYP-KLR-MT5-REPLICATION-M5-XAU-001` / `EA_KLR_Scalper` (USD-gated
  prior-day-liquidity raid branch).
- **What was tested**: XAUUSD M5 prior-day raid, then displacement+MSS, then
  FVG retest; offline probe (2022-2024) plus native FivePercent Model 0
  replication.
- **Evidence**:
  - `04. Memory/research/CANDIDATE_REGISTRY.era1.archive.jsonl:21` — verdict
    `"KILL_AT_OFFLINE_PROBE"`; reason verbatim: `"Frozen 2022-2024 probe
    produced 210 prior-day raids, 42 displacement+MSS events, 16 FVGs and 3
    retests, but only 2 ungated core trades (0.0128/week, PF 0, -1.5083R) and
    zero USD-aligned challenger trades. Nine of eleven gates failed; no source
    or holdout access is legal."`; metrics `"sweeps":210`, `"displacements":42`,
    `"fvgs":16`, `"retests":3`, `"sweep_control_trades":100`,
    `"sweep_control_profit_factor":0.414160282`,
    `"sweep_control_net_r":-54.329372682`, `"core_trades":2`,
    `"core_trades_per_elapsed_week":0.0127853881`, `"core_net_r":-1.5082889313`.
  - `:40` — MT5 replication `"KILL_AT_MODEL0_CADENCE_REPLICATION"`: `"the core
    produced 4 trades (0.02555/week) and the USD-gated diagnostic 1 trade
    (0.00639/week) over 156.57 elapsed weeks. Positive tiny-sample PF cannot
    rescue the hard cadence miss."`; metrics `"native_sweeps":346`,
    `"native_displacements":61`, `"native_strict_fvgs":26`.
  - Summary row: `04. Memory/do_not_repeat_failures.md:1467`.
- **Why it does NOT forbid zone physics**: the funnel "raid → MSS → FVG →
  retest" is a full trade chain; it died on event rarity and economics, not on
  a measurement of level reaction. R01 does not trade the raid or the FVG; it
  measures whether a fresh approach to a real zone bounces more than at a
  matched fake zone. Mechanism delta: remove the raid/MSS/FVG chain entirely
  and measure the conditional reaction proportion with no fills.
- **Confidence**: high (archived registry rows + memory summary).

---

## 6. Range / session / weekly-extreme level fades (Asia, W1, Camarilla, ORF)

- **Family / hypothesis ID**: `HYP-ASIA-GB-M5-001` (EA_Asia),
  `HYP-W1-GB-M5-001` (EA_W1, prior-week H/L fade),
  `HYP-CAMF-EU-M15-001` (EA_CamarillaFade, H3/L3 reclaim fade),
  `HYP-ORF-GB-M5-001` (EA_Orf, session-open range fade).
- **What was tested**: GBPUSD M5 Asia-range fade (H4 EMA, 1.5ATR/1.5R);
  GBPUSD M5 prior-week high/low fade; EURUSD M15 Camarilla H3/L3 reclaim fade;
  GBPUSD M5 session-open-range fade. All governed Model 0, 1999-2026 window.
- **Evidence**:
  - Asia: `04. Memory/research/CANDIDATE_REGISTRY.jsonl:19` — `"Gross PF 0.770,
    net -4953 USD, DD 49.7% over 27.7y; cadence ~4.2/wk below floor; cost PF
    x1.0 0.663 / x1.5 0.612 / x2.0 0.565. Asia-range fade on GBPUSD M5 is
    gross-negative - overnight range reclaims do not revert profitably."`
    metrics `"trades":6119`, `"trades_per_week":4.24`.
  - W1: `04. Memory/research/CANDIDATE_REGISTRY.jsonl:20` — `"Gross PF 0.552,
    net -97 USD, only 42 trades over 27.7y = 0.03/wk - weekly extremes almost
    never touched intraday; cadence catastrophic, economics gross-negative.
    Weekly-level fade has no signal density."`
  - CAMF: `04. Memory/research/20260912_CAMF_EURUSD_KILL_AND_LIVEUPDATE_FP.md:11-16`
    — `"Trades | 14,755 — cadence **10.21/wk PASS**"`, `"Report PF / Net / DD |
    0.886 / -5,458 USD / 57.1%"`, `"Cost PF x1.0 / x1.5 / x2.0 | **0.763** /
    0.702 / 0.646"`.
  - ORF: `04. Memory/research/CANDIDATE_REGISTRY.jsonl:22` — `"Economic+cadence
    kill: gross PF 0.822, net -4673, DD 47.3%, cost PF x1.0=0.712 x1.5=0.657
    x2.0=0.606. Cadence 5.4/wk below 10/wk floor."`
  - ERA-2 board row: `04. Memory/research/20260912_ERA2_FALSIFICATION_BOARD.md:18`
    (`CAMF-EU` 14,755 trades, gross PF 0.76, cost PF x1 0.70).
- **Why it does NOT forbid zone physics**: each is a fade strategy at a range
  boundary or daily/weekly level with stop/target/cost; none measured the
  reaction proportion at real vs fake levels, and none had a per-event matched
  fake-zone control. R01 supplies the missing measurement (BOUNCE/BREAK
  proportions, symmetric barriers, K=5 matched fakes) and is not a fade entry.
  Mechanism delta: event study instead of PnL strategy; no fills.
- **Confidence**: high (registry + kill doc quotes).

---

## 7. Session-VWAP deviation fade + VRAS VWAP/fractal object

- **Family / hypothesis ID**: `HYP-VWF-XAU-M5-001` / `EA_VwapFade`;
  `HYP-VRAS-EURUSD-M5-003/004/005/006/008` /
  `EA_VRAS_RegimeAdaptiveScalperV3`, `EA_VRAS_PathConfirmedTrend`.
- **What was tested**: XAUUSD M5 session-VWAP ATR-deviation fade (all-available
  2004-2026); EURUSD M5 tick-volume London-anchor Session VWAP/SD + ADX
  25/19/dwell6 + confirmed fractal AVWAP + rejection + M15-bias (the
  "seven-gap" object); one-bar trend path confirmation with session VWAP,
  frozen-anchor AVWAP and closed-M15 VWAP bias.
- **Evidence**:
  - VWF: `04. Memory/research/20260912_VWF_CONTROL_KILL.md:11-24` — `"Trades |
    25,417 (~8.6/week — below 10–40 cadence band)"`, `"Report PF | 0.87; Net
    -7,645 USD; Max DD 76.8%; WR 43.8%"`, `"Cost-bound PF | **0.50** @x1.0 /
    **0.38** @x1.5 / **0.29** @x2.0"`, `"VWAP-fade has no positive
    mean-reversion edge on XAUUSD M5 at this cost level."` Registry:
    `04. Memory/research/CANDIDATE_REGISTRY.jsonl:3`.
  - VRAS seven-gap: `04. Memory/do_not_repeat_failures.md:1654-1657` — `"Valid
    Model 0 produced N=93, PF0.5914, net -$5,243.22 and only 0.4465
    trades/elapsed week; Range PF0.1331 and Trend PF0.6412 both failed."`
  - VRAS HYP-005: `04. Memory/do_not_repeat_failures.md:364-365` — `"Net Profit
    -$10,040.86, PF 0.74, WR 44.72% (144W/178L), Expectancy -$31.18/trade,
    Equity DD 12.71%, Balance DD 12.45%, Cadence 28.69 trades/week"`.
  - VRAS path-confirmed: `04. Memory/do_not_repeat_failures.md:1683-1686` —
    `"full challenger PF was 0.8996 with negative expectancy, only 1.385
    trades/week and 252 total trades"`; `"The filter improved PF by only 0.0069
    and mean realized R by 0.0065R"`.
  - Tick-plane VWAP: `04. Memory/research/20260919_LAB_FALSIFICATION_MAP_AND_COST_REFRAME.md:332-333`
    — `"**VWAP reversion** (AUDUSD ticks, 110d): dead, PF 0.42-0.58 at all
    thresholds — tick deviations continue rather than revert."`
  - Refusal row: `03. EA Developer/PA_Pro/bank/HYPOTHESIS_BANK.md:1045` (R10)
    — `"VWAP / session-VWAP / AVWAP deviation fade or reclaim ... Whole family
    dead including the VRAS seven-gap object"`.
- **Why it does NOT forbid zone physics**: VWAP is a running volume-weighted
  mean, not a horizontal support/resistance zone formed by price structure;
  these were fade/reclaim trades with stops and targets. R01's objects are
  swing-clustered zones and reference levels (PDH/PDL, session, week, round)
  approached from >= 1.0 x ATR14(H1) away, with matched fake zones. Mechanism
  delta: structural zones and a matched-fake reaction test instead of a VWAP
  deviation fade; no fills.
- **Confidence**: high (kill doc + memory sections + registry).

---

## 8. Volume-clock exhaustion (time/volume-at-level fade, VCEX)

- **Family / hypothesis ID**: `HYP-VCEX-EURUSD-M15-002` /
  `EA_VolumeClockExhaustion`.
- **What was tested**: EURUSD M15 "volume-clock exhaustion" fade:
  tau0.40 / early0.45ATR / exhaustion0.30 / 07-16 UTC / max-one-per-day /
  120-minute / source-stop / 1R-TP object on 807 matched TRUE fade and
  FOLLOW_CONTROL continuation pairs (public DESIGN).
- **Evidence**:
  - `04. Memory/do_not_repeat_failures.md:272-286` — verbatim: `"At 1.50 pips
    TRUE PF was 0.655314, mean -0.201794R, total -162.848100R, fixed-initial-
    equity DD 83.0077%, DSR `2.22e-9`, and positive years 0/5. TRUE was
    slightly worse than FOLLOW_CONTROL (PF delta -0.004031; mean-R delta
    -0.002629), so flipping polarity does not rescue the mechanism."`;
    `"Only cadence passed (`1/11` gates)."`; `"Failure radius is the exact VCEX
    M15 tau0.40/early0.45ATR/exhaustion0.30/07-16UTC/max-one-per-day/120-minute/
    source-stop/1R-TP object on these 807 pairs."`
  - Evidence path: `04. Memory/do_not_repeat_failures.md:286`.
  - Ghost listing: `04. Memory/research/20260831_REPO_CLEANUP_AND_PATH_MIGRATION_PLAN.md:37`
    (`EA_VolumeClockExhaustion` folder gone; verdict preserved in registry).
- **Why it does NOT forbid zone physics**: VCEX is a volume-time exhaustion
  fade with a 120-minute horizon, not a zone-reaction measurement; its
  "exhaustion" variable is clock/volume state, not distance-to-a-real-zone
  versus a matched fake. R01 measures BOUNCE/BREAK proportions at zones with
  symmetric ATR barriers and no PnL. Mechanism delta: level geometry + matched
  fake control instead of a volume-clock fade.
- **Confidence**: high (direct memory lines).

---

## 9. Volume-profile POC / value-area reversion

- **Family / hypothesis ID**: none found.
- **What was tested**: nothing found. A word-boundary search for `POC`,
  `value area`, `market profile`, `volume profile` across `04. Memory/` and
  `03. EA Developer/` returns no matching hypothesis, EA or metric
  (`rg -n -i "\bPOC\b|value area|market profile|volume profile"` — no output).
- **Evidence**: NOT FOUND. The nearest tested object is the VWAP family
  (§7): `HYP-VWF-XAU-M5-001`, VRAS (`HYP-VRAS-EURUSD-M5-003`), and tick VWAP
  reversion (`04. Memory/research/20260919_LAB_FALSIFICATION_MAP_AND_COST_REFRAME.md:332-333`,
  `"PF 0.42-0.58 at all thresholds"`). Those are volume-weighted means, not
  POC/value-area histograms.
- **Why it does NOT forbid zone physics**: no legacy evidence exists either
  way; PA-PRO must not cite a POC kill that does not exist. If a POC/value-area
  family is proposed later it needs its own de-dup against the VWAP family and
  a fresh prereg.
- **Confidence**: high for the negative search result (two source trees
  searched, zero matches); no metric to quote.

---

## 10. 3-bar FVG continuation (EA_FVG, EURUSD M15)

- **Family / hypothesis ID**: `HYP-FVG-EU-M15-001` / `EA_FVG`.
- **What was tested**: EURUSD M15 3-candle FVG continuation, 1 ATR / 8-bar,
  governed Model 0, 1999.01.01-2026.09.11.
- **Evidence**:
  - `04. Memory/research/20260912_FVG_H4PB_EURUSD_KILLS.md:7-13` — `"29,370
    trades (~20.3/wk PASS), PF **0.776**, net **−$9,259**, DD **92.6%**,
    WR 31.0%."`, `"Cost PF x1.0 **0.686** / x1.5 0.627 / x2.0 0.574."`,
    `"**Verdict: KILL.** Price-void continuation is gross-negative."`
  - `04. Memory/research/CANDIDATE_REGISTRY.jsonl:16` — reason `"Gross PF 0.776,
    net -9259 USD, DD 92.6% over 27.7y; cadence ~20.3/wk passed; cost PF x1.0
    0.686 / x1.5 0.627 / x2.0 0.574. 3-bar FVG continuation on EURUSD M15 is
    gross-negative - imbalance gaps do not persist."`; metrics
    `"trades":29370`, `"profit_factor":0.7762`, `"win_rate_pct":31.0`.
  - ERA-2 board row: `04. Memory/research/20260912_ERA2_FALSIFICATION_BOARD.md:26`
    (`FVG-EU` 29,370 trades, gross PF 0.78, cost PF x1 0.69).
- **Why it does NOT forbid zone physics**: this is a continuation trade that
  enters the gap and holds 8 bars; it tests whether an imbalance gap persists,
  not whether price reacts at a zone versus a matched fake zone. R01's zones
  are swing clusters and reference levels; FVG is not required and no
  continuation position is taken. Mechanism delta: reaction proportion at
  zones instead of FVG-continuation PnL.
- **Confidence**: high.

---

## 11. ICT FVG report-fidelity chain (HYP-ICT-FVG-007..026) + FVG confluence de-dup

- **Family / hypothesis ID**: `HYP-ICT-FVG-*` / `EA_ICTFVGReportFidelity`,
  `EA_FVGConfluence` (`HYP-FVG-SCALP-CONFL-M5-EUR-001`),
  `HYP-H1-DISPLACE-FVG-CONT-001` (parent de-dup target).
- **What was tested**: EURUSD M5 sweep → displacement → strict FVG → MSS →
  first retest chain and its context/ranking/collection children, 2018-2026;
  the full report-fidelity object and high-recall controls.
- **Evidence** (all in `04. Memory/do_not_repeat_failures.md`):
  - HYP-012 (three-bar post-sweep state): `:536-544` — `"3,385 positions, PF
    0.8104, -0.09799R/position, 7.592 trades/week and zero positive entry
    years"`.
  - HYP-011 (full-chart no-news): `:554-560` — `"returned PF 0.7588, -0.13775R
    per defined-risk position, 9.736 trades/week and PF<1 after commission in
    every entry year"`.
  - HYP-010 (micro-risk control): `:583-588` — `"2,070 exactly reconciled
    positions, 9.925 trades per elapsed week, PF 0.7625, -0.1348R/trade and
    negative net/PF<1 in every year (2019 0.585; 2020 0.840; 2021 0.709; 2022
    0.962)."`
  - HYP-008 (OrderCheck repair): `:598-601` — `"it lost USD 7,944.29 at PF
    0.5774 and 0.585 trades/week before exhausting the account-DD budget."`
  - HYP-007 (full ordered chain): `:606-614` — `"The full ordered chain
    produced 12,340 sweeps, 293 displacement/FVG events, 149 closed-M15 MSS
    events, 144 pre-MSS mitigations, one valid first retest, one ADX rejection
    and zero entries/trades."`
  - HYP-017 (human-context policy): `:503-509` — `"The 3,703 reconciled trades
    were already negative natively (PF 0.7553); after the frozen additional
    1.5-pip diagnostic PF was 0.3513 and expectancy -0.52139R/trade with
    week-block 95% CI `[-0.55998,-0.48317]`."`
  - HYP-014 (prob-rank policy): `:519-526` — `"PF 0.9577, -0.01577R/accepted
    trade and -0.0000927R/opportunity"`.
  - HYP-020 (level-path order): `:479-488` — `"It was killed before source,
    compile, tester run or outcome access."`
  - HYP-022 (repeated swept-level churn): `:1599-1607` — `"only 659
    repeated-churn cases among 6,399 defined confirmations (10.2985%,
    1.477578/elapsed week)"`.
  - HYP-024 (time-weighted level resilience): `:463-467` — `"dwell around the
    sweep wick tip was `FAVORABLE_DOMINANT` in 6,396 and `ADVERSE_DOMINANT` in
    only 3 (0.04688%, 0.006726/week)"`.
  - HYP-026 (pivot reclaim dwell): `:445-451` — `"pivot-relative
    `ADVERSE_DOMINANT` was only 181 (2.8290%, 0.40583/week) versus 6,217
    favorable rows."`
  - FVG confluence de-dup: `:1145-1153` — `"Its M5 three-candle FVG plus
    40-60% fill/rejection is the same primary object as killed
    `HYP-H1-DISPLACE-FVG-CONT-001`; HTF BOS, OB, premium/discount, liquidity
    sweep, session and management scoring only densify the dead price-only
    family."`
- **Why it does NOT forbid zone physics**: the whole chain is an entry sequence
  (sweep + displacement + FVG + retest) with tight sweep-extreme stops; it
  measures whether that sequence predicts a tradable move, not whether real
  levels react more than matched fake levels. R01 has no sweep, no
  displacement, no FVG, no MSS and no fill. Mechanism delta: a conditional
  reaction census on real vs matched fake zones; the ICT chain's components
  are not part of the R01 measurement. (Also note: the HYP-024/026 results are
  about label density of post-sweep states, not level reaction probability.)
- **Confidence**: high (direct memory lines; each metric quoted verbatim).

---

## 12. Order-block / SMC report-fidelity (LSS-OB, Unicorn, PO3-AMD, DRAT)

- **Family / hypothesis ID**: `HYP-LSS-OB-REPL-EURUSD-M15-001/002`;
  `HYP-UPSC-XAU-M5-002`, `HYP-UPS-XAU-M5-006/007/008`;
  `HYP-PO3-AMD-SCALP-M5-XAU-001/002/003`;
  `HYP-DRAT-ONNX-ICT-M15-EUR-001`; `EA_UnicornPrecisionScalper`,
  `EA_LSSOBPropScalper`, `EA_PO3_AMD_Scalper`.
- **What was tested**: EURUSD M15 SMC chain (H1/H4 sweep → 1.8 ATR
  displacement/strict-FVG → OB-body-overlap → first confirmed retest); XAUUSD
  M5 Unicorn breaker + displacement + MSS + FVG entries; XAUUSD M5 PO3-AMD
  (Asian range → sweep → displacement/MSS → FVG/retest); EURUSD M15
  ONNX-gated sweep → MSS → FVG/OB retest.
- **Evidence**:
  - LSS-OB offline: `04. Memory/do_not_repeat_failures.md:1582-1586` — `"Over
    2019-2022 it has only 383 upstream context-aligned sweeps versus the frozen
    cadence floor of 417 before any downstream rejection; the full challenger
    has zero events."` Archived metrics:
    `04. Memory/research/CANDIDATE_REGISTRY.era1.archive.jsonl:82` (HYP-001
    killed row) — `"context_aligned_sweeps":383`, `"displacement_fvg":0`,
    `"valid_ob_fvg_overlap":0`, `"control_events":0`, `"challenger_events":0`.
  - LSS-OB native MT5: `04. Memory/do_not_repeat_failures.md:624-637` —
    `"Both produced 388 context-aligned sweeps but zero 1.8x-ATR displacement/
    FVG, zero entries and zero trades."`
  - Unicorn four-bar control: `:1458` — `"N=138, 1.334/week, report PF
    0.986/net -$233.83; research full-cost PF 0.688, x1.5 0.574, x2 0.481;
    robustness 0%, MC P95 DD 5.654%"`.
  - Unicorn event-anchored sweep: `:1459` — `"N=130, 1.257/week, report PF
    0.724/net -$4,396.90; research full-cost PF 0.498, x1.5 0.413, x2 0.343;
    robustness 0%, MC P95 DD 7.118%, equity REJECT."`
  - Unicorn FVG-CE limit: `:1462` — `"115/251 fills in 3 bars, 45.82% fill
    rate, 1.110/week, 87 long/28 short."`
  - Unicorn RR1.5 replay: `:1463` — `"N=132, WR 35.606%, report PF 0.697/net
    -$4,904.75, full-cost PF 0.475/x1.5 0.391/x2 0.322, robustness 0%, MC P95
    DD 7.315%."`
  - PO3-AMD: `:1464-1466` — v1 `"only 6 dates met the frozen 80..300-point
    Asian range; sweep control N=1, full PO3 N=0"`; v2 `"121 sweeps -> 1
    displacement+MSS -> 1 FVG -> 0 retests; control N=36, PF 0.511, -10.71R"`;
    v3 `"122 sweeps -> 0 displacement+MSS; control N=37, PF 0.674, -5.42R and
    all three years negative; challenger N=0"`.
  - DRAT ONNX: `:1483` — `"rules-only PF 0.764 / -67.75R; ONNX gate PF 0.749 /
    -52.82R; all year buckets negative"`.
  - SMC display docs (not edge evidence, no economic claim):
    `04. Memory/research/20260906_SMC_INTRADAY_METHODS.md:23-24` — `"Raw
    BOS/MSS/void flags are structural facts, not entries"`;
    `04. Memory/research/20260906_TV_SMC_INDICATOR_REVIEW.md:306` —
    `"Treating this review as a reason to change buffer 2.3 or to claim
    expectancy. Snapshots are not a backtest."` The TV/TB SMC overlay was never
    a strategy claim; the SMC strategy kills are the EAs above.
- **Why it does NOT forbid zone physics**: all four families are complete SMC
  trade chains with entries, structural stops and targets; their kills are
  funnel-density, zero-trade or PnL verdicts. None measured whether price
  reacts at a real OB/SMC zone more than at a matched fake zone. R01 uses
  swing-cluster zones (not OB/breaker/FVG objects), takes no position and
  reports bounce/break proportions. Mechanism delta: matched-fake reaction
  measurement replaces the entire SMC entry chain.
- **Confidence**: high (memory table rows + archived metrics).

---

## 13. Fractal / confirmed-pivot setups (ASRS, SCC)

- **Family / hypothesis ID**: `HYP-ASRS-EURUSD-M5-001` /
  `EA_ASRS_AdaptiveSweepReclaim`; `HYP-SCC-EURUSD-M5-001`,
  `HYP-SCC-MT5-REPLICATION-EURUSD-M5-002/003/004` /
  `EA_SweepCascadeContinuation`.
- **What was tested**: EURUSD M5 confirmed N=2 fractal sweep + reclaim
  (0.25x ATR depth, ADX<=25, 1.5x prior-20 tick-volume, UTC 07:00-21:00,
  immediate retest, sweep-extreme +0.30x ATR stop); EURUSD M5 confirmed-pivot
  BREAK → HOLD → 12-bar first-passage retest continuation, complex-extreme
  +0.25x ATR14 stop.
- **Evidence**:
  - ASRS (Stage-0 park, no outcome): `04. Memory/do_not_repeat_failures.md:1707-1716`
    — `"280 candidates (1.3415/elapsed week), median risk 7.9482 pip,
    median/p75 1.5-pip proxy cost 0.1887R/0.2874R, and max year concentration
    29.29%"`; `"only 45.81% of all volume-qualified events occurred inside the
    report's London-NY wall, below the frozen 50% materiality floor. This is
    PARK with zero outcome, not an economic edge verdict."`
  - SCC Stage-0: `:1737-1746` — `"1,242 raw daily BREAK arms, 878 HOLD passes
    and 286 accepted retests = 1.3703 per elapsed week. Pooled and every-year
    cadence missed the frozen 2.0/week floor; N missed 418."`; `"median/p25
    risk was only 3.1866/2.1107 pip; a 1.5-pip RT proxy consumed median/p75
    0.4707R/0.7107R before commission/slippage."`
  - SCC Model 0: `:1775-1779` — `"The raw first-close BREAK control lost with
    N1112, PF0.698096 and mean realized R=-0.215618. HOLD→retest reduced fills
    to N261 but also lost with PF0.691278 and mean R=-0.231790"`; `"fixed
    1.5-pip stress reduced PF to 0.354074, and only one of four calendar years
    had PF>1."`
  - Registry park row: `04. Memory/research/CANDIDATE_REGISTRY.era1.archive.jsonl:246`
    (HYP-ASRS `PARK_STAGE0_REQUIRED_GATE_FAIL_NO_OUTCOME_READ`).
- **Why it does NOT forbid zone physics**: ASRS/SCC are sweep-reclaim and
  break-retest continuation trades on fractal/pivot objects with tight stops;
  they were killed on cadence/geometry or PnL, not on a measurement of pivot
  reaction probability. R01's objects are multi-scale swing-cluster zones with
  touches/role-flip/age, not N=2 fractals, and R01 takes no trade. Mechanism
  delta: stronger zone objects (clustered, scored, multi-touch) and a
  matched-fake reaction census instead of fractal sweep entries.
- **Confidence**: high (direct memory lines; registry park row verified).

---

## 14. DR3 micro-barrier Volman pattern break (EA_VolmanPA / ECON-1)

- **Family / hypothesis ID**: `HYP-VPA-EURUSD-M5-001` / `EA_VolmanPA` DR3
  ("locked barrier buildup stop-entry fixed2R", stop 8 pips / target 2R).
- **What was tested**: EURUSD M5 Bob Volman pattern break at micro-barriers
  (2 pivots in 17 bars), frozen DR3 signal, DESIGN 2016-2021, one verdict run
  G4; matched random bracket control (K=20, 84,320 entries / 42,257 fills).
- **Evidence**:
  - `03. EA Developer/EA_VolmanPA/PLAN/econ1/ECON1_RESULTS.md:11-21` — table:
    `"| PF x1 > 1.30 | x1 | 0.795 | > 1.3 | FAIL |"`,
    `"| gross PF >= 1.10 | gross | 0.992 | >= 1.1 | FAIL |"`,
    `"| N >= 500 | x1 | 2436 | >= 500 | PASS |"`,
    `"| LIFT x1 >= +14.1pp | x1 | +0.24pp (CI [-1.61, +2.14]) | >= 14.1 | FAIL |"`.
  - `:29-32` — per-scenario: `"| gross | 2436 | 34.98% | 0.992 | ..."`,
    `"| x1 | 2436 | 30.17% | 0.795 | ..."`, `"| x2 | 2436 | 26.97% | 0.667 |"`.
  - `:47-49` — `"Fills 2436; final equity at 0.5%/trade: **17.6%** of start;
    max DD **84.19%**"`; `"Realised b 1.839 (gate ≥ 1.70 PASS); the failure is
    the win rate, not the payoff."`
  - `03. EA Developer/PA_Pro/PA_PRO_CHARTER.md:15-18` — `"gross PF 0.992, x1 PF
    0.795, lift vs matched random +0.24pp, CI [-1.61, +2.14], every year
    negative. Preliminary ECON-1b: grade A/B did not predict outcome. =>
    "Looks like the book" is not edge. The micro-line + tight-stop object is
    dead."`
  - Refusal row: `03. EA Developer/PA_Pro/bank/HYPOTHESIS_BANK.md:1038` (R3) —
    `"Micro-line pattern break (2 pivots in 17 bars, DR3) ... The exact object
    that failed ECON-1 (stop 8 pips = 8 x c_rt EURUSD, structurally
    cost-dominated)"`.
- **Why it does NOT forbid zone physics**: DR3 is a pattern-break trade on
  micro-lines (2 pivots in 17 bars) with an 8-pip stop; ECON-1 shows the trade
  is cost-dominated and does not beat a matched random bracket, not that price
  fails to react at real zones. The matched-random control was random entries,
  not fake zones at matched geometry. PA-PRO R01 replaces micro-lines with
  scored multi-touch zones and measures the conditional reaction proportion at
  real vs matched fake zones, with no fills. Mechanism delta: object scale
  (clustered zones vs micro-lines) and quantity measured (reaction proportion
  vs pattern-break PnL).
- **Confidence**: high (ECON-1 table lines + charter).

---

## 15. Tight-stop sweep objects (ICTVIS visual feature discovery)

- **Family / hypothesis ID**: `HYP-ICTVIS-EURUSD-M5-001`.
- **What was tested**: Owner-approved OPEN visual feature-discovery on the
  generous EURUSD M5 sweep-reversion universe (39,122 DESIGN events); best
  in-sample feature selection (range-position + wick morphology) versus cost.
- **Evidence**:
  - `04. Memory/do_not_repeat_failures.md:1912-1917` — `"The generous M5
    sweep-reversion universe is near-random gross (PF 1.019 at zero cost) and
    its stops are too tight (median 4.5 pips) for realistic EURUSD cost; even
    the best in-sample DESIGN feature selection (range-position + wick
    morphology) posts PF 0.573 at 1.5 pip RT and dies by 0.5 pip."`
  - `04. Memory/research/CANDIDATE_REGISTRY.era1.archive.jsonl:69` — metrics
    `"design_n":39122`, `"design_win_gross":0.3453`, `"design_mean_r_gross":0.0124`,
    `"universe_pf_zero_cost":1.019`, `"top10_pf_zero_cost":1.12`,
    `"top10_pf_050pip":0.887`, `"top10_pf_150pip":0.573`,
    `"risk_pip_median":4.5`, `"F5_rangepos_rho":0.886`,
    `"F4_wick_rho":-0.915`.
- **Why it does NOT forbid zone physics**: this is a tight-stop sweep trade
  object, and the verdict is about cost/stop geometry. The zero-cost universe
  PF 1.019 and the visual features describe sweep outcomes, not whether price
  reacts at a zone more than at a matched fake zone. R01 has no stops and no
  cost drag at all. Mechanism delta: a no-fill reaction census; the tight-stop
  cost axis that killed ICTVIS cannot apply.
- **Confidence**: high (memory lines + archived metrics).

---

## 16. Day-open sweep fade probe (withdrawn, not a kill to cite)

- **Family / hypothesis ID**: none (2026-09-18 day-boundary Stage-0 probe;
  later withdrawn).
- **What was tested**: M5 bars 00:00-00:30 server piercing the prior-6h range →
  fade, next-bar-open entry, 1-4h hold, 7 majors; claimed per-bar PF 1.45-5.56
  (e.g. NZDUSD 5.56, USDCHF 3.88, AUDUSD 5.12; EURUSD 1.45).
- **Evidence**:
  - `04. Memory/research/20260918_DAY_BOUNDARY_MARKET_PHYSICS.md:3-10` —
    `"deep-history event-level verification (M1 .hcc, 2010→2025) FALSIFIED the
    pierce-fade claim below — up-pierces CONTINUE (fade loses −2 to −7.7p, win
    15–35%, all symbols all years). The verified mechanism is **roll-reopen gap
    reversion**, not sweep-fade."`; `"Treat all "fade PF 1.45–5.56" numbers
    here as withdrawn."`
  - Table lines `:38-46` (the withdrawn numbers).
- **Why it does NOT forbid zone physics**: the probe was a sweep-pierce fade
  trade with next-bar-open fills; its positive read was withdrawn as a
  sign/tranche artifact of a truncated M5 sample. It contains no real-vs-fake
  zone control and no reaction-probability measurement. R01's event is a fresh
  approach to an existing zone (not a day-open pierce) and reports
  BOUNCE/BREAK/NONE with no fills. Mechanism delta: zone-approach census
  instead of a boundary-pierce fade.
- **Confidence**: high (correction block quoted).

---

## 17. Detrended-z mean reversion grid (MR-GRID) — boundary case

- **Family / hypothesis ID**: `HYP-MR-GRID-EURUSD-H1-002` (exhaustive grid
  closure of the regime-gated OHLC-MR family; `HYP-MR-REGIME-EURUSD-H1-001`
  stays terminal).
- **What was tested**: EURUSD H1 std-normalized detrended-z mean reversion,
  full legal variant grid (W / Z / K_sl / TP_cap / k_ts / trailing x 6 gate
  arms), 2015-2022 unsealed splits, DSR over the full trial count.
- **Evidence**:
  - `04. Memory/do_not_repeat_failures.md:1362-1366` — `"**RESULT (same day):
    the grid ran and the family IS `CLOSED_EXHAUSTIVE`.** 8100 simulations,
    ZERO arms reached the necessary condition gross PF ≥ 1.25 (max 1.2476,
    median 0.8902); max net PF@x1 anywhere 1.0991; best deflated arm DSR 0.0129
    vs floor 0.95 with negative expectancy; Stage-2 auto-skipped. The failure
    is the object, not the tuning."`
  - Refusal row: `03. EA Developer/PA_Pro/bank/HYPOTHESIS_BANK.md:1046` (R11) —
    `"z-score / detrended mean reversion with regime gates ... the object fails,
    not the tuning"`.
- **Why it does NOT forbid zone physics**: the MR object is a statistical
  price-deviation z, not a support/resistance zone, and the grid is a trade
  strategy with stops/targets. It says the detrended-z trade has no edge, not
  that price reacts at real levels. R01 measures structural zones against
  matched fake zones with no strategy and no tuning grid. Mechanism delta:
  geometry-defined zones and a matched-fake reaction census.
- **Confidence**: high (direct memory lines).

---

## 18. Liquidity-vacuum overshoot reversal (LVOR) — no market verdict

- **Family / hypothesis ID**: `HYP-LVOR-EURUSD-M15-001/002/003` /
  `EA_LiquidityVacuumOvershootReversal` (ghost package).
- **What was tested**: EURUSD M15 liquidity-vacuum overshoot reversal
  source feasibility (public DESIGN), frozen thresholds; never reached
  economics.
- **Evidence**:
  - `04. Memory/research/CANDIDATE_REGISTRY.era1.archive.jsonl:315` (HYP-003
    parked row) — `"SOURCE_FAIL_NO_ECONOMICS_AUTHORITY"`: `"PRIMARY produced
    197 source-executable candidates over 260.5714 elapsed calendar weeks, or
    0.7560 per week, below the preregistered 2.0 minimum."`; HYP-001/002 are
    `"ENGINEERING_INVALID_NO_MARKET_VERDICT"` (schema-guard false positives).
  - De-dup note: `03. EA Developer/PA_Pro/bank/HYPOTHESIS_BANK.md:1015-1017` —
    `"no readout; ... no verdict exists, so it is not a kill but cannot be
    cited as evidence either"`.
- **Why it does NOT forbid zone physics**: there is no market verdict at all
  (source-cadence fail + engineering invalids). It must not be cited in either
  direction. R01 is unaffected.
- **Confidence**: high for the "no verdict" status; medium for the exact
  cadence number (quoted from the archived row, not from a readout).

---

## Zone physics is a different question

- PA-PRO R01 tests one question only: does price react at REAL zones more than
  at MATCHED FAKE zones? Outcome = BOUNCE / BREAK / NONE proportions over
  <= 48 M5 bars with symmetric barriers m = 1.0 x ATR14(H1) from the zone edge
  (`03. EA Developer/PA_Pro/PA_PRO_CHARTER.md:105-118`). It is an event study:
  no orders, no fills, no PnL, no stop, no target.
- The killed families above are trade strategies (entry + stop + target +
  cost) on the same objects; their verdicts measure PnL, not reaction
  probability. None of them measured P(BOUNCE | real zone) minus
  P(BOUNCE | matched fake zone).
- R01's control is per-event matched fake zones: K=5, same time, same side,
  same distance from price, same width, placed where no real zone or reference
  level is within 2 widths (`PA_PRO_CHARTER.md:111-113`). Legacy controls were
  shifted grids (HYP-011), random entries (ECON-1), or no control at all —
  they do not pre-empt this design.
- The cost drag that killed the legacy board (~30% of PF; `20260912_ERA2_FALSIFICATION_BOARD.md:44`)
  does not apply to R01 because R01 books no trades; conversely, a positive R01
  result is not evidence of a cost-feasible edge.
- R01 is forbidden from being turned into any killed strategy by rename or
  parameter change: no round-number fade/continuation, no PDH/PDL sweep fade
  or reclaim, no Asia/weekly/Camarilla/session-open range fade, no VWAP or
  volume-clock fade, no FVG/OB/SMC/ICT chain, no DR3 micro-line break, no
  fractal-sweep or pivot-retest trade, no tight-stop sweep object. The refusal
  table `03. EA Developer/PA_Pro/bank/HYPOTHESIS_BANK.md:1034-1057` (R1-R18)
  already encodes these rows.
- If LINES MATTER passes, it licenses only the next preregistered setup family
  (F1-F9) with structural stops >= 10 x c_rt (`PA_PRO_CHARTER.md:100`); it
  does not revive any killed hypothesis ID and does not authorize a trade on
  the R01 event set.
- Do not cite R01 as evidence for or against any killed ID: R01 measures a
  proportion, the kills measured PnL. A setup built on R01 must be a new
  hypothesis with a stated mechanism delta and its own frozen prereg
  (`do_not_repeat_failures.md:3-8`; charter §5 lines 129-132).
