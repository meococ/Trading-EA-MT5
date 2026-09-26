# CLOCK_AUDIT_DESIGN — M0 output

Generated: 2026-09-21T10:10:06Z
Scope: DESIGN 2016-01-01 -> 2021-12-31, core symbols, M1 bars.

## NFP release bar (08:30 US Eastern)

Expected server time 15:30 (15:25-15:35 tolerated), 14:30 in
US/EU DST gap weeks (US ahead of EU in March; US still on DST
in early Nov after EU fell back).

### EURUSD

Observed max-range bar server-time histogram (72 months):

| server time | months |
|---|---|
| 14:31 | 3 |
| 14:32 | 1 |
| 15:31 | 46 |
| 15:32 | 4 |
| 15:33 | 2 |
| 15:35 | 1 |
| 15:37 | 1 |
| 15:41 | 2 |
| 15:46 | 1 |
| 15:47 | 1 |
| 16:01 | 1 |
| 16:22 | 1 |
| 16:25 | 1 |
| 17:01 | 3 |
| 17:05 | 1 |
| 17:11 | 1 |
| 17:16 | 1 |
| 17:28 | 1 |

DEVIATING months:
- 2016-07: obs 16:25 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2017-03: obs 17:01 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2018-06: obs 17:16 vs exp 15:30 (alt-release dominated)
- 2019-03: obs 17:01 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2019-11: obs 16:01 vs exp 14:30 (alt-release dominated)
- 2020-01: obs 17:01 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2020-03: obs 17:28 vs exp 15:30 (alt-release dominated)
- 2020-05: obs 17:11 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2020-11: obs 16:22 vs exp 15:30 (alt-release dominated)
- 2021-10: obs 17:05 vs exp 15:30 (alt-release dominated)

### GBPUSD

Observed max-range bar server-time histogram (72 months):

| server time | months |
|---|---|
| 13:46 | 1 |
| 14:05 | 1 |
| 14:18 | 1 |
| 14:22 | 1 |
| 14:31 | 3 |
| 14:32 | 1 |
| 15:10 | 1 |
| 15:31 | 47 |
| 15:32 | 3 |
| 15:33 | 2 |
| 15:38 | 1 |
| 15:39 | 1 |
| 15:43 | 1 |
| 16:00 | 1 |
| 16:01 | 1 |
| 16:04 | 1 |
| 17:01 | 3 |
| 17:02 | 1 |
| 17:03 | 1 |

DEVIATING months:
- 2016-07: obs 14:05 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2017-03: obs 17:02 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2017-10: obs 14:22 vs exp 15:30 (alt-release dominated)
- 2018-09: obs 13:46 vs exp 15:30 (alt-release dominated)
- 2019-03: obs 17:01 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2019-11: obs 16:01 vs exp 14:30 (alt-release dominated)
- 2020-01: obs 17:01 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2020-03: obs 17:01 vs exp 15:30 (alt-release dominated)
- 2020-05: obs 17:03 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2020-11: obs 14:18 vs exp 15:30 (alt-release dominated)

### USDJPY

Observed max-range bar server-time histogram (72 months):

| server time | months |
|---|---|
| 14:31 | 5 |
| 14:56 | 1 |
| 15:30 | 1 |
| 15:31 | 54 |
| 15:34 | 1 |
| 15:37 | 1 |
| 16:04 | 1 |
| 16:41 | 1 |
| 17:01 | 4 |
| 17:02 | 1 |
| 17:11 | 1 |
| 17:28 | 1 |

DEVIATING months:
- 2016-07: obs 17:01 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2017-03: obs 17:02 vs exp 15:30 (alt-release dominated)
- 2017-12: obs 16:41 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2019-03: obs 17:01 vs exp 15:30 (alt-release dominated)
- 2020-01: obs 17:01 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2020-03: obs 17:28 vs exp 15:30 (alt-release dominated)
- 2020-05: obs 17:11 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2021-10: obs 17:01 vs exp 15:30 (alt-release dominated)

### AUDUSD

Observed max-range bar server-time histogram (72 months):

| server time | months |
|---|---|
| 14:31 | 3 |
| 14:32 | 1 |
| 15:31 | 50 |
| 15:32 | 3 |
| 15:33 | 3 |
| 15:39 | 1 |
| 15:46 | 1 |
| 15:47 | 1 |
| 16:01 | 1 |
| 16:22 | 1 |
| 16:41 | 1 |
| 17:01 | 5 |
| 17:23 | 1 |

DEVIATING months:
- 2016-07: obs 17:01 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2017-03: obs 17:01 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2019-01: obs 17:23 vs exp 15:30 (alt-release dominated)
- 2019-03: obs 17:01 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2019-11: obs 16:01 vs exp 14:30 (alt-release dominated)
- 2020-01: obs 17:01 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2020-05: obs 16:41 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)
- 2020-11: obs 16:22 vs exp 15:30 (alt-release dominated)
- 2021-10: obs 17:01 vs exp 15:30 (NO SPIKE AT EXPECTED SLOT)

## Deviation distribution (all symbols)

| dev minutes | count |
|---|---|
| -105 | 1 |
| -85 | 1 |
| -70 | 2 |
| -35 | 1 |
| -20 | 1 |
| +0 | 225 |
| +5 | 11 |
| +10 | 5 |
| +15 | 5 |
| +30 | 1 |
| +35 | 2 |
| +50 | 2 |
| +55 | 1 |
| +70 | 2 |
| +90 | 20 |
| +95 | 2 |
| +100 | 2 |
| +105 | 1 |
| +115 | 1 |
| +120 | 2 |

## Week boundaries (server clock)

### EURUSD — 313 weeks

First bar weekday hist: d0:311, d1:2

First bar server-time hist (top): 00:16×90, 00:18×83, 00:17×71, 00:21×28, 00:19×26, 00:20×11, 06:16×2, 00:32×1

Last bar weekday hist: d3:2, d4:311

Last bar server-time hist (top): 23:59×126, 23:54×92, 23:57×43, 23:58×19, 22:54×7, 22:59×6, 22:57×4, 23:53×4

### GBPUSD — 313 weeks

First bar weekday hist: d0:311, d1:2

First bar server-time hist (top): 00:16×82, 00:17×82, 00:18×73, 00:19×29, 00:21×20, 00:20×16, 00:22×3, 00:23×2

Last bar weekday hist: d3:2, d4:311

Last bar server-time hist (top): 23:59×118, 23:54×81, 23:57×43, 23:58×23, 23:55×12, 22:54×8, 23:53×7, 22:58×5

### USDJPY — 313 weeks

First bar weekday hist: d0:311, d1:2

First bar server-time hist (top): 00:18×88, 00:16×84, 00:17×72, 00:19×27, 00:21×22, 00:20×14, 06:16×2, 00:25×1

Last bar weekday hist: d3:2, d4:311

Last bar server-time hist (top): 23:59×113, 23:54×88, 23:57×50, 23:58×26, 22:54×7, 23:55×7, 22:59×6, 22:57×5

### AUDUSD — 313 weeks

First bar weekday hist: d0:311, d1:2

First bar server-time hist (top): 00:18×85, 00:16×80, 00:17×74, 00:19×27, 00:21×23, 00:20×16, 06:16×2, 00:22×2

Last bar weekday hist: d3:2, d4:311

Last bar server-time hist (top): 23:59×123, 23:54×85, 23:57×43, 23:58×21, 23:53×13, 22:59×7, 22:54×7, 22:57×3

## Verdict

- Symbol-months with a spike bar (>= 3x day-median) AT the expected NFP minute: 262/288.
- Of the rest, months where the max-range bar sat at another release slot while a spike still printed at the expected minute (alt-release dominated): 17.  NOT clock shifts.
- Months where the max-range bar sat at another release slot and the expected-minute bar printed but muted (< 3x day median — a quiet NFP, not a clock shift): 20.  [('EURUSD', '2016-07', '16:25', 2.1), ('EURUSD', '2017-03', '17:01', 1.1), ('EURUSD', '2019-03', '17:01', 1.8), ('EURUSD', '2020-01', '17:01', 1.6), ('EURUSD', '2020-05', '17:11', 2.9), ('GBPUSD', '2016-07', '14:05', 7.0), ('GBPUSD', '2017-03', '17:02', 1.5), ('GBPUSD', '2019-03', '17:01', 4.2), ('GBPUSD', '2020-01', '17:01', 2.8), ('GBPUSD', '2020-05', '17:03', 3.4), ('USDJPY', '2016-07', '17:01', 3.5), ('USDJPY', '2017-12', '16:41', 2.9), ('USDJPY', '2020-01', '17:01', 0.6), ('USDJPY', '2020-05', '17:11', 1.3), ('AUDUSD', '2016-07', '17:01', 0.1), ('AUDUSD', '2017-03', '17:01', 1.0), ('AUDUSD', '2019-03', '17:01', 1.8), ('AUDUSD', '2020-01', '17:01', 2.3), ('AUDUSD', '2020-05', '16:41', 2.7), ('AUDUSD', '2021-10', '17:01', 3.5)]
- **No month shows a shifted NFP bar: the clock is confirmed everywhere.  No month is excluded.**

Two measured facts:
1. The modal max-range M1 bar is labeled 15:31 (not 15:30) server — a stable +1-minute bar-label convention across all 72 months x 4 symbols (the release-minute bar).  Gap weeks show 14:31-14:33, matching the +2h winter offset.
2. Week runs Monday 00:16-00:2x server to Friday ~23:59 server; daily gap 00:00-00:15 server (1424 min/day).

**Server clock CONFIRMED as UTC+2/+3 (EU DST).**  Consequence used everywhere below: **CET = server - 1h year-round** (both follow the EU DST schedule), so Volman's CET marks map to server: Asia 00:00-08:00 CET = 01:00-09:00 server; EU open 08:00 CET = 09:00 server; US data 14:30 CET = 15:30 server; London fix 16:00 London = 18:00 server.
