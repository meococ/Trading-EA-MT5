# DATA.md — SonicR_Lab data inventory (2026-09-23)

## Series inventory

| series | source | broker | file | first bar | last bar | rows | notes |
|---|---|---|---|---|---|---|---|
| EURUSD M1 | lab cache (etl.py from MQ-Demo .hcc) | MetaQuotes-Demo | `02. AlphaFactory/lab/cache/EURUSD_M1_2010_2026.parquet` | 2010-01-04 00:00 srv | 2026-09-19 ~15:18 srv | 6,200,976 | suspect 1.11% baked in |
| XAUUSD M1 | same | MetaQuotes-Demo | `02. AlphaFactory/lab/cache/XAUUSD_M1_2010_2026.parquet` | 2010-01-04 01:05 srv | 2026-09-18 15:18 srv | 5,773,626 | suspect 1.21% |
| EURUSD M1 (pre-2010) | .hcc direct via `02. AlphaFactory/tools/hcc_reader.py` | MetaQuotes-Demo | `.../history/EURUSD/{2000..2009}.hcc` | 2000-01-03 00:01 srv | 2009-12-31 18:59 srv | ~370k/yr | for J-parity extension only; 1998/1999 .hcc = stubs (0 valid bars) |
| XAUUSD M1 (pre-2010) | .hcc direct | MetaQuotes-Demo | `.../history/XAUUSD/{2004..2009}.hcc` | 2004-06-11 | 2009 | — | not loaded (lab window is the DESIGN base) |

Schema (parquet): index `ctm` = server-naive epoch seconds; cols `o,h,l,c` float64 (bid),
`tv` int32 tick_volume, `sp` float32 stored spread field, `suspect` bool, `mod` minute-of-day,
`dow`, `mow` minute-of-week, `day`, `year`.

Derived series used by the harness: M5/M15/H1 are resampled from M1 (closed bars, right edge
labelled by bar open time). All component state uses only closed bars.

## Gaps

- EURUSD: weekly gap Fri ~23:00/23:59 srv -> Mon 00:00 srv (weekend). Nonstandard intraday
  gaps exist (162k in the FivePercent manifest for a different plane; here: median gap-chain
  at 23:xx/00:xx = roll break 1-3 min + news holes). Bars are simply absent — no phantom rows.
- XAUUSD: week opens Mon ~01:00-01:05 srv (gold opens 1h later than FX). Otherwise same.
- Missing bar = no price; the sim never fabricates bars inside gaps.

## Timezone (verified this lane, 2026-09-23)

- `ctm` = server wall-clock-as-epoch (naive). Server offset follows **US DST**:
  UTC+3 during US EDT, UTC+2 during US EST. Evidence: all 868 weekly opens land
  Monday 00:00 server, including every mid-March week 2010-2026 (US-on/EU-off window);
  an EU-DST server would show Sunday 23:00 opens in those weeks. One exception
  (Sun 18:00 open) = holiday schedule.
- London = UTC +0/+1 (UK DST: last-Sun-Mar 01:00 UTC -> last-Sun-Oct 01:00 UTC).
- `london_time = server_naive - server_offset + uk_offset`. When both DST regimes align
  (most of the year): london = server - 2h. March gap weeks: -3h. Oct/Nov gap week: -3h
  (fixed 2F: UK off DST while US still on EDT -> server UTC+3 vs London UTC+0).
- The lab cache `mod/dow/day/year` columns are computed on server-naive time and reused.

## Spread / tick data

- `sp` column is NOT cost truth: 17.9% zeros + absurd outliers (packed burst records) —
  same verdict as the FivePercent spread audit (`FAIL_SPREAD_COST_PROVENANCE`) and the
  20260916 cost-plane audit. Not used.
- `suspect` flag (hcc_reader burst-marker logic): M1 bars inside tick-burst regions
  (roll 00:00-00:15 server on majors, XAUUSD 01:00-01:16, news minutes) are fabricated
  by the phase-scan; per hot.md standing rule, entries/exits priced inside suspect bars
  are void. Policy in this lab: signals/fills whose decisive price lands on a suspect M1
  bar are still simulated but FLAGGED (`suspect_touch` column) and excluded in a
  sensitivity column; SL/TP triggers inside suspect regions resolve on the bar's OHLC
  (conservative), flagged.

## Cost model (from 20260916 cost-plane audit + verified_cost_artifacts)

Per-symbol constants (cost x1), applied as adverse price + commission:

| symbol | spread (one leg) | slippage/side | commission | round-trip price equiv. |
|---|---|---|---|---|
| EURUSD | 0.1 pip (tester `spread=1`) | 0.1 pip (p90, 250ms) | $7/lot RT = 0.7 pip | ~1.0 pip |
| XAUUSD | 2.0 pip = $0.20 (tester `spread=20`, artifact HYP-GBB-S3) | 1.4 pip/side (p90) | $7/lot RT = 0.7 pip = $0.07/oz | ~5.5 pip = $0.55/oz |

Mechanics: bars are bid-side. Long entry pays spread+slippage (ask), exits pay slippage
(bid side). Short entry pays slippage only (bid), exits pay spread+slippage (ask side).
Commission added as fixed price-equivalent per round trip. x1.5 / x2 multiply ALL legs.
Pip sizes: EURUSD pip=0.0001, point=0.00001 (5-digit); XAUUSD pip=0.1, point=0.01 (2-digit).

## J-run window (known-answer test)

Run `20260816_205426` artifacts were deleted in the 31/08 cleanup; window not recorded.
Governed-era convention (`from` sentinel) -> EURUSD window assumed = all available M1 on
MQ-Demo = 2000-01-03 -> 2026-08-14 (last trading day before the Sunday run). Documented
assumption; parity tolerance check is per the brief (N ±20%, PF ±0.15).

## DESIGN / VALIDATION / HOLDOUT windows (fixed before any outcome)

Common history EURUSD+XAUUSD = 2010-01-04 -> 2026-09-18 (~16.7 years, >= 5y requirement OK).
Splits on the common timeline:
- DESIGN:     2010-01-04 -> 2020-01-13 04:47   (first 60%; epoch 1578890844)
- VALIDATION: 2020-01-13 -> 2023-05-17 14:23   (next 20%; epoch 1684333392)
- HOLDOUT:    2023-05-17 14:23 -> 2026-09-18   (last 20%, SEALED — loader refuses unless
              `allow_holdout=True`, which is never passed this round)

## E1 roll-window diagnostic (Lead step 2, 19:06Z - decides whether E1 applies)

Median M1 range in units of M15 ATR14, suspect vs clean, by server hour, DESIGN.

EURUSD (roll burst window 00:00-00:15 server):
- hour 0: n_sus=40,723 med=0.069 vs n_clean=112,175 med=0.059 -> ratio 1.16
- roll-window aggregate (h23+h0): sus 0.069 vs clean 0.080 -> **ratio 0.86**
- scattered suspect bars elsewhere are extreme (h12-h18 ratios 9-51) but tiny counts.

XAUUSD (roll burst window 01:00-01:16 server):
- hour 1: n_sus=39,952 med=0.078 vs n_clean=96,910 med=0.066 -> ratio 1.19
- scattered suspect bars h2-h21 often ratio>2 but tiny counts.

**Decision at 19:06Z: E1 SKIPPED** (both roll windows < 2.0 threshold).
Superseded by the Lead's addendum A1 (19:17Z): the median test was the
wrong statistic - a fabricated burst is a few extreme bars inside ~15
roll minutes/day, which a median hides.

## E1 diagnostic, CORRECTED (A1, measured 19:21-19:30Z)

(a) Exits per 1000 trade-minutes inside roll window vs outside
    (roll window measured as EUR 00:00-00:20, XAU 01:00-01:20 server):

| config (worst/best examples) | rate_in | rate_out | ratio |
|---|---|---|---|
| EURUSD F0_J | 253.5 | 2.14 | 118x |
| EURUSD F2_NH_b | 37.7 | 0.53 | 71x |
| EURUSD F3_LUCY_a | 358.8 | 18.7 | 19x |
| XAUUSD F2_NH_b | 34.3 | 0.59 | 58x |
| XAUUSD F0_J | 117.9 | 3.60 | 33x |
| XAUUSD F5_S3 | 32.3 | 0.54 | 60x |
(Full table: `runs/diag_roll_v2.py` output, all 25 configs x 2 syms;
every config shows 19x-450x more exits per minute inside the window.)

(b) Per-day extremes inside roll window vs two adjacent quiet windows
    of equal length (EUR 23:30-45/00:30-45, XAU 00:30-45/01:30-45):

| sym | statistic | ratio med | p90 | p99 |
|---|---|---|---|---|
| EURUSD | max M1 range | 30.9 | 63.0 | 115.6 |
| EURUSD | max \|open-prev_close\| | 71.2 | 270.0 | 664.4 |
| XAUUSD | max M1 range | 37.9 | 86.5 | 176.4 |
| XAUUSD | max \|open-prev_close\| | 68.8 | 279.5 | 839.1 |

Roll-window daily max range EUR 0.0089 vs quiet 0.0003; XAU $15.5 vs $0.40.

(c) Jump-and-revert: price moves >0.5 x ATR14(M15) from the pre-roll
    close inside the window and is back within 0.2 x ATR14 30 min later:
    **EURUSD 665/2586 days (25.7%), XAUUSD 455/2519 days (18.1%)**.

**Decision A1: E1 APPLIED.** Both harness versions are reported for
every config: H0 = E1b+E2+E3 (suspect bars tradable), H1 = H0 + E1
(`skip_suspect=True` in sim.py; SL/TP/pending checks skip suspect bars,
first clean bar after a suspect run resolves gaps per the Lead's rules).
Selection requires a config to pass on BOTH harnesses.

## Perception-lane EURUSD M5 (locator, per brief)

`03. EA Developer/PA_Pro/research/perception/golden/book_loader.py` loads the SAME
`02. AlphaFactory/lab/cache/EURUSD_M1_*.parquet` rolled to M5 (BOOK window 2012 only).
No separate bar store exists — the lab cache is the canonical plane for both lanes.
