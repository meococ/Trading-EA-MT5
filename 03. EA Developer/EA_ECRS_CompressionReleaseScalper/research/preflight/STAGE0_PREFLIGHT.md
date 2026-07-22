# ECRS Stage-0 Preflight — EURUSD M5 (OUTCOME-BLIND)

Lane: `EA_ECRS_CompressionReleaseScalper` (Efficiency-Compression-Release Scalper)
Stage: Stage-0 data preflight + condition-frequency funnel. **Frequency only — no
edge, expectancy, PnL, or outcome is computed or claimed here.**

Generator: `preflight/stage0_scan.py` · Funnel: `preflight/stage0_funnel.json`

## 1. Data preflight

| Item | Value |
|---|---|
| M1 parquet SHA256 | `2959C555…F724235A` |
| M1 manifest match | **true** (aborts on mismatch) |
| News CSV SHA256 | `80B9DE46…28C64307` |
| News manifest match | **true** |
| News high-impact events loaded | 1,282 (coverage 2019-01-01 … 2022-12-31) |
| Seal receipt | holdout_start `2023-01-01`, bars_loaded 2,977,638, holdout_bars_loaded 0, last bar `2022-12-30 21:59` |
| M5 rows (server-aligned resample) | 596,141 |
| M5 time_utc span | 2015-01-02 07:00 … 2022-12-30 21:55 |
| Session bars 2019-2022 (07:00–16:30 UTC) | 118,405 |
| **Spread zero-rate, session bars 2019-2022** | **0.2932 (29.3%)** |
| minute_count distribution | 5→594,291 · 4→1,138 · 3→368 · 2→183 · 1→161 (mean 4.995, median 5) |
| Weekend M5 bars present | 12,809 |

No bar with `time_utc ≥ 2023-01-01` was read (holdout enforced at read time).
`outcome_blind: true` — not computed: PnL/returns, forward returns, MFE/MAE, exit
prices/times/stops/targets/hold time, win rate/PF/expectancy, and any high/low/close
of the entry bar `t+1` or later. Entry bar reads limited to existence, time_utc,
open (=entry price), and spread.

**Cost caveat:** 29.3% of in-session M5 bars report zero spread; the manifest already
flags the spread field as not usable as cost truth. G8 is used only as a fail-closed
eligibility gate, never as a cost.

## 2. Condition funnel — pooled 2019–2022 (variant_pre mainline, news-gated)

Cumulative counts; each row adds one gate to the row above.

| Step | Count | Note |
|---|---:|---|
| n_bars (entries in window) | 298,483 | |
| G1 regime shift (ER chop→trend) | 15,780 | |
| G1∧G2 compression (atr14[t-1] ≤ 0.70·sma20) | 1,092 | |
| G1∧G2∧G3 breakout (12-bar range excl. t) | 462 | direction set here |
| +G4 volume surge (tv ≥ 1.7·sma20[t-1]) | **75** | large drop |
| +G5 EMA20 bias/slope align | 73 | |
| +G6 session 07:00–16:30 UTC | **8** | **dominant bottleneck (−89%)** |
| +G7 news ±45 min | 8 | no candidate lost to news |
| **+G8 spread ≤0.8p = FINAL** | **8** | longs 2 · shorts 6 |
| FINAL with variant_at compression | **1** | at-bar compression is far stricter |

## 3. Per-year final counts (variant_pre)

| Year | n_bars | G1 | G1∧G2∧G3 | +G4 | +G5 | +G6 | Final | Final (variant_at) | News |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2015 | 74,275 | 3,952 | 147 | 10 | 10 | 0 | 0 | 0 | NOT_EVALUATED |
| 2016 | 74,685 | 3,868 | 124 | 10 | 9 | 1 | 1 | 0 | NOT_EVALUATED |
| 2017 | 74,266 | 3,939 | 123 | 12 | 12 | 0 | 0 | 0 | NOT_EVALUATED |
| 2018 | 74,431 | 3,925 | 108 | 7 | 7 | 0 | 0 | 0 | NOT_EVALUATED |
| 2019 | 74,340 | 3,918 | 151 | 28 | 27 | 4 | 4 | 1 | EVALUATED |
| 2020 | 74,638 | 3,902 | 127 | 22 | 22 | 2 | 2 | 0 | EVALUATED |
| 2021 | 74,675 | 4,003 | 107 | 15 | 15 | 1 | 1 | 0 | EVALUATED |
| 2022 | 74,830 | 3,957 | 77 | 10 | 9 | 1 | 1 | 0 | EVALUATED |

2015–2018 have no news coverage: `+G7` is `NOT_EVALUATED` and excluded from the
news-gated funnel row; their finals apply G8 directly after G6.

## 4. Cadence — pooled 2019–2022

| Metric | Value |
|---|---|
| Elapsed weeks | 208.71 |
| Final candidates | 8 |
| Raw signals / week | **0.0383** (≈ 1 every 26 weeks) |
| Non-overlapping / week (greedy ≥18-bar gap) | **0.0383** (all 8 already ≥18 bars apart) |

The mechanism as frozen is **extremely rare** at this cadence — roughly two signals
per year in-session. This is a frequency fact, not an edge verdict.

## 5. Entry-hour histogram (UTC) — and the session bottleneck

**Final candidates (post-G6):** 09h→1, 10h→3, 11h→2, 13h→2 (all inside session).

**Pre-session survivors (post-G5, before G6), pooled:**
00h→27 · 03h→5 · 04h→1 · 05h→2 · 09h→1 · 10h→3 · 11h→2 · 13h→2 · 17h→4 · 18h→3 ·
19h→1 · 20h→1 · 21h→1 · 22h→7 · **23h→13**.

**Diagnosis of the anomaly:** the compression→release+volume-surge mechanism fires
overwhelmingly around 00h and 22–23h UTC (low-liquidity roll / late-US hours). G4
measures a 1.7× surge relative to a trailing 100-minute tick-volume baseline, which is
easiest to trip when that baseline is thin — i.e. off-session. The fixed 07:00–16:30
session gate (G6) therefore removes ~89% of otherwise-qualifying setups (73→8). This is
the single dominant frequency constraint of the design as frozen.

## 6. variant_pre vs variant_at delta (Phase-2 freeze input)

Pooled final: **variant_pre = 8**, **variant_at = 1** (delta 7). Requiring compression
to still hold *at* the release bar (variant_at) instead of *going into* it (variant_pre)
collapses the population to a single case (2019). variant_pre is the mechanism-true and
far more sampleable choice; variant_at is near-degenerate at Stage-0 volume.

## 7. Candidate cases + renderer

- `stage0_candidate_cases.csv` — pooled 2019–2022 final candidates, variant_pre,
  news-gated. Requested 50; **only 8 exist**, so all 8 are included (stratified sample
  is a no-op below capacity; seed 20260722). Split: 2019×4, 2020×2, 2021×1, 2022×1;
  longs 2, shorts 6. Columns: `case_id, entry_time_utc, direction, entry, side, year,
  signal_time_server` (entry = open of bar t+1).
- Renderer: `chart_case_render.py --mode asof --pre-bars 120 --overlay ema:20`.
  **Rendered 8 / skipped 0.** Every case has `cutoff_enforced=true`,
  `outcome_hidden=true`, `net_r_hidden=true`; last drawn bar strictly precedes entry.
- Charts: `preflight/cases_asof/*.png` · Manifest:
  `preflight/cases_asof/cases_manifest.json`.

## 8. Anomalies / observations

1. **Session gate is the frequency killer** (73→8, −89%); the mechanism is an off-session
   phenomenon fought by an on-session window. Phase-2 must decide session scope on
   evidence, not assume it.
2. **variant_at is near-degenerate** (1 pooled case) — do not freeze on it at this volume.
3. **Total final volume is tiny** (8 pooled / 208.7 weeks). Any Stage-1 sampling or gate
   loosening must be pre-registered; post-hoc rescue is prohibited.
4. **Spread zero-rate 29.3%** in-session — spread stays a fail-closed eligibility gate only.
5. **Non-contiguous entry bars: 0** — every final candidate's entry bar t+1 is exactly
   5 minutes after its signal bar; no weekend/gap contamination in the final set. 12,809
   weekend M5 bars exist in the corpus but none survive to the final in-session set.

## 9. Files produced

| File | Purpose |
|---|---|
| `stage0_scan.py` | outcome-blind Stage-0 scanner (this run's generator) |
| `stage0_funnel.json` | data preflight + full funnel + cadence + histograms |
| `stage0_candidate_cases.csv` | 8 candidate setups (renderer input) |
| `stage0_bars_m5.parquet` | derived M5 bars for rendering (SHA `A2DDF0D4…89053532`) |
| `cases_asof/*.png` (8) + `cases_manifest.json` | asof-rendered setups + hash-bound manifest |
