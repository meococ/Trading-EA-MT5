# ECRS Stage-0 v2 Preflight — EURUSD M5 (OUTCOME-BLIND)

Lane: `EA_ECRS_CompressionReleaseScalper` (Efficiency-Compression-Release Scalper)
Hypothesis: **`HYP-ECRS-EURUSD-M5-002`** — a pre-outcome re-scope of `-001`.
Stage: Stage-0 data preflight + condition-frequency funnel. **Frequency only — no
edge, expectancy, PnL, or outcome is computed or claimed here.**

Generator: `preflight/stage0_scan_v2.py` · Funnel: `preflight/stage0_funnel_v2.json`
Schema: `ecrs_stage0_preflight_funnel.v2`

## 0. What changed vs v1 (`-001` → `-002`)

The **tick-volume surge gate is removed entirely** as a rule. In v1 it was `G4`
(`tick_volume[t] ≥ 1.7·sma20(tick_volume)[t-1]`) and sat between G3 and G5. In v2
it filters nothing; instead every final candidate records a diagnostic column
`tickvol_ratio = tick_volume[t] / sma20(tick_volume)[t-1]`, and its distribution is
reported below. Every other gate, threshold, window, seal, and convention is
inherited from v1 **unchanged**. Compression uses `variant_pre` only (no `variant_at`
in v2). Sample seed is `20260723`; all outputs are v2-suffixed and v1 artifacts are
never overwritten.

## 1. Data preflight (identical corpus to v1)

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
| Derived M5 parquet | `stage0_bars_m5.parquet` **REUSED byte-identically** (SHA `A2DDF0D4…89053532` matched) |

No bar with `time_utc ≥ 2023-01-01` was read (holdout enforced at read time).
`outcome_blind: true` — not computed: PnL/returns, forward returns, MFE/MAE, exit
prices/times/stops/targets/hold time, win rate/PF/expectancy, and any high/low/close
of the entry bar `t+1` or later. Entry bar reads limited to existence, time_utc,
open (=entry price), and spread. `tickvol_ratio` uses only bars `≤ t`.

**Cost caveat (unchanged):** 29.3% of in-session M5 bars report zero spread; the
manifest flags the spread field as not usable as cost truth. G8 is a fail-closed
eligibility gate only, never a cost.

## 2. Condition funnel — pooled 2019–2022 (variant_pre, news-gated, NO volume gate)

Cumulative counts; each row adds one gate to the row above.

| Step | Count | Note |
|---|---:|---|
| n_bars (entries in window) | 298,483 | |
| G1 regime shift (ER chop→trend) | 15,780 | |
| G1∧G2 compression (atr14[t-1] ≤ 0.70·sma20[t-1]) | 1,092 | |
| G1∧G2∧G3 breakout (12-bar range excl. t) | 462 | direction set here |
| +G5 EMA20 bias/slope align | **434** | (v1 inserted G4 here: 462→75→73) |
| +G6 session 07:00–16:30 UTC | **39** | **dominant bottleneck (−91%)** |
| +G7 news ±45 min | 39 | no candidate lost to news |
| **+G8 spread ≤0.8p = FINAL** | **30** | longs 10 · shorts 20 (9 lost to spread) |

**v1↔v2 reconciliation:** re-imposing the removed gate on the v2 finals as a filter
(`tickvol_ratio ≥ 1.7`) yields **exactly 8** pooled finals — identical to v1's pooled
final count. Removing G4 and re-adding it recovers the v1 population, confirming the
only mechanical change is the dropped volume filter.

## 3. Per-year final counts (variant_pre, no volume gate)

| Year | n_bars | G1 | G1∧G2∧G3 | +G5 | +G6 | Final | ≥1.2x | ≥1.7x(=v1 G4) | News |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2015 | 74,275 | 3,952 | 147 | 135 | 21 | 10 | 2 | 0 | NOT_EVALUATED |
| 2016 | 74,685 | 3,868 | 124 | 117 | 16 | 16 | 1 | 1 | NOT_EVALUATED |
| 2017 | 74,266 | 3,939 | 123 | 114 | 19 | 13 | 3 | 0 | NOT_EVALUATED |
| 2018 | 74,431 | 3,925 | 108 | 101 | 11 | 11 | 3 | 0 | NOT_EVALUATED |
| 2019 | 74,340 | 3,918 | 151 | 141 | 12 | 12 | 6 | 4 | EVALUATED |
| 2020 | 74,638 | 3,902 | 127 | 124 | 7 | 6 | 3 | 2 | EVALUATED |
| 2021 | 74,675 | 4,003 | 107 | 101 | 11 | 4 | 1 | 1 | EVALUATED |
| 2022 | 74,830 | 3,957 | 77 | 68 | 9 | 8 | 1 | 1 | EVALUATED |

2015–2018 have no news coverage: `+G7` is `NOT_EVALUATED` and their finals apply G8
directly after G6 (`≥1.2x` / `≥1.7x` columns are diagnostic only, never filters).

## 4. Cadence — pooled 2019–2022

| Metric | Value | vs v1 |
|---|---|---|
| Elapsed weeks | 208.71 | = |
| Final candidates | **30** | 8 |
| Raw signals / week | **0.1437** (≈ 1 every 7 weeks) | 0.0383 |
| Non-overlapping / week (greedy ≥18-bar gap) | **0.1437** (all 30 already ≥18 bars apart) | 0.0383 |

Removing the volume gate raises pooled cadence ~3.75× (8→30 finals), from roughly one
signal every 26 weeks to one every ~7 weeks. Still a low-frequency mechanism as frozen.
This is a frequency fact, not an edge verdict.

## 5. Weakened 1.2× volume line (freeze-decision input ONLY — filters nothing)

Count of finals that would **also** survive a weakened `tickvol_ratio ≥ 1.2` gate.
No separate case set is produced; this is a single number per year + pooled.

| Year | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | **Pooled 2019-22** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Finals ≥1.2× | 2 | 1 | 3 | 3 | 6 | 3 | 1 | 1 | **11 of 30** |

For reference, finals ≥1.7× (v1's removed G4 threshold): pooled **8 of 30**.

## 6. tickvol_ratio distribution — pooled 2019–2022 finals (diagnostic)

`tickvol_ratio = tick_volume[t] / sma20(tick_volume)[t-1]`, over all 30 pooled finals.

| Stat | min | p10 | p20 | p30 | p40 | p50 | p60 | p70 | p80 | p90 | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ratio | 0.384 | 0.599 | 0.664 | 0.719 | 0.775 | **0.846** | 1.070 | 1.389 | 1.816 | 2.112 | 4.490 |

Mean 1.246, median **0.846**. **Frequency observation:** the median final fires on
*below-baseline* tick volume — over half the finals (19 of 30) have `tickvol_ratio < 1.0`,
and only 11 reach ≥1.2× / 8 reach ≥1.7×. The removed v1 gate was selecting a minority
upper tail of this distribution. Stated as frequency structure only — no edge claim.

## 7. Weekly distribution sanity — pooled 2019–2022 finals (frequency only)

Finals bucketed into calendar weeks (pandas `W`, week-ending Sunday) across the window.

| Weeks in window | 0 entries | 1 entry | 2 entries | 3+ entries | max/week |
|---:|---:|---:|---:|---:|---:|
| 209 | 182 | 24 | 3 | 0 | 2 |

Even without the volume gate, entries never cluster: no week has more than 2 finals, and
87% of weeks (182/209) have none.

## 8. Entry-hour histogram (UTC) — and the session bottleneck

**Final candidates (post-G8), pooled:** 09h→5 · 10h→3 · 11h→5 · 13h→2 · 14h→1 ·
15h→6 · 16h→8 (all inside the 07:00–16:30 session; v2 finals skew later than v1's
09–13h cluster).

**Pre-session survivors (post-G5, before G6), pooled:** 00h→42 · 02h→10 · 03h→23 ·
04h→22 · 05h→18 · 09h→5 · 10h→4 · 11h→5 · 15h→6 · 16h→35 · **17h→55** · 18h→41 ·
19h→17 · 20h→29 · 21h→23 · 22h→26 · **23h→68**.

**Diagnosis (unchanged from v1, now on a larger population):** the compression→release
mechanism fires overwhelmingly off-session (late-US / roll hours, peaking 23h→68 and
17h→55). The fixed 07:00–16:30 session gate G6 removes ~91% of otherwise-qualifying
setups (434→39). This is the single dominant frequency constraint of the design as
frozen. Removing the volume gate did **not** change this — G6 remains the bottleneck.

## 9. Candidate cases + renderer

- `stage0_candidate_cases_v2.csv` — pooled 2019–2022 final candidates, variant_pre,
  news-gated. Requested 50; **30 exist**, all 30 included (stratified sample is a no-op
  below the 50 cap; seed 20260723). Split: 2019×12, 2020×6, 2021×4, 2022×8; longs 10,
  shorts 20. Columns: `case_id, entry_time_utc, direction, entry, side, year,
  signal_time_server, tickvol_ratio` (entry = open of bar t+1; `tickvol_ratio` is the
  recorded diagnostic).
- Renderer: `chart_case_render.py --mode asof --pre-bars 120 --overlay ema:20 --max-cases 50`.
  **Rendered 30 / skipped 0.** Every case has `cutoff_enforced=true`,
  `outcome_hidden=true`, `net_r_hidden=true`; last drawn bar strictly precedes entry
  (verified for all 30).
- Charts: `preflight/cases_asof_v2/*.png` (30) · Manifest:
  `preflight/cases_asof_v2/cases_manifest.json` (schema `chart_case_render.v2`,
  bars SHA `A2DDF0D4…89053532`).

## 10. Anomalies / observations

1. **Session gate is still the frequency killer** (434→39, −91%); removing the volume
   gate did not move it. The mechanism remains an off-session phenomenon fought by an
   on-session window.
2. **Median final fires on below-baseline tick volume** (median ratio 0.846; 19/30
   finals <1.0×). The removed v1 volume gate was isolating a minority high-volume tail.
3. **Spread now removes 9 finals** (39→30) where v1 lost 0 — with the larger population,
   the fail-closed G8 eligibility gate begins to bind. Spread stays a fail-closed gate
   only (29.3% in-session zero-rate).
4. **Entries never cluster:** ≤2 finals in any calendar week; 182/209 weeks empty.
5. **Non-contiguous entry bars: 0** — every final's entry bar t+1 is exactly 5 minutes
   after its signal bar; no weekend/gap contamination.
6. **v1↔v2 exact reconciliation:** finals ≥1.7× = 8 = v1 pooled final count.

## 11. Files produced

| File | Bytes | Purpose |
|---|---:|---|
| `stage0_scan_v2.py` | 27,104 | outcome-blind Stage-0 v2 scanner (this run's generator) |
| `stage0_funnel_v2.json` | 10,788 | data preflight + full funnel + cadence + histograms + tickvol deciles + weekly block |
| `stage0_candidate_cases_v2.csv` | 2,728 | 30 candidate setups (renderer input, + tickvol_ratio diagnostic) |
| `cases_asof_v2/*.png` (30) + `cases_manifest.json` | ~1,920 KB | asof-rendered setups + hash-bound manifest |
| `stage0_bars_m5.parquet` | 15,351,419 | shared derived M5 (REUSED byte-identically; SHA `A2DDF0D4…89053532`) |
