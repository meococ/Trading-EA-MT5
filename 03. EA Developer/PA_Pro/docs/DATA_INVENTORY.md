# PA-PRO — DATA INVENTORY (sub-agent B, Round 00)

Status: `DONE` — all 7 symbols scanned 2026-09-20.
Charter: `PA_PRO_CHARTER.md`, SHA256 `3C57536848A4AA6113950D06D50331B8C664E18B79D34E08DEF2F1019BC5DC2C`
(verified with `Get-FileHash -Algorithm SHA256` on 2026-09-20).
Scan script (resumable, read-only on the cache): `PA_Pro/docs/_data_inventory_scan.py`;
renderer: `PA_Pro/docs/_data_inventory_render.py`; raw per-symbol JSON:
`PA_Pro/docs/_data_inventory/<SYM>.json`.

Symbols: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD. Window 2010-2026
(the cache ends 2026-09-18, so 2026 is partial).

Source: `02. AlphaFactory/lab/cache/<SYM>_M1_2010_2026.parquet` — READ-ONLY (never written,
locked or re-saved by this work). Index `ctm` = int64 server epoch seconds; columns used:
`o,h,l,c,suspect`. The cache also carries `tv,sp,mod,dow,mow,day,year` columns, untouched.

---

## 1. ATR14 overall medians per symbol (REFERENCE FOR DOWNSTREAM WORK)

Medians over **all complete bars** of the whole 2010-2026 window, in pips
(pip = 1e-4, USDJPY = 1e-2). Wilder ATR14; method in §2. The last column is the
fraction of complete H1 bars with `ATR14(H1) >= 10 x c_rt` (the charter §3 geometry
guard); `c_rt` per symbol is in the COSTS.md table (AUDUSD/USDCAD/NZDUSD use the 1.4 p
proxy until measured).

| Symbol | ATR14(H1) median (pips) | ATR14(M15) median (pips) | H1 bars (ATR-valid) | M15 bars (ATR-valid) | H1 share ATR14 >= 10*c_rt |
|---|---|---|---|---|---|
| EURUSD | **15.40** | **7.23** | 95,387 | 400,402 | 87.9 % |
| GBPUSD | **19.40** | **9.18** | 95,666 | 400,826 | 97.2 % |
| USDJPY | **15.81** | **7.35** | 95,349 | 400,378 | 59.8 % |
| AUDUSD | **13.72** | **6.56** | 95,056 | 399,807 | 47.9 % |
| USDCAD | **15.25** | **7.05** | 94,423 | 398,626 | 59.6 % |
| USDCHF | **12.80** | **6.11** | 94,084 | 398,136 | 67.1 % |
| NZDUSD | **13.13** | **6.29** | 93,436 | 396,607 | 43.6 % |

---

## 2. Method (frozen; every number in this file follows it)

1. **Suspect bars are dropped before aggregation.** `suspect=True` marks burst/packed
   regions whose prices are not tradable evidence (`02. AlphaFactory/lab/data_plane.py:8-11`);
   the daily 00:00 summary record is among them. Suspect % is computed on the raw M1
   counts before/after dropping.
2. **H1 bars** = complete 60-M1 **server-hour** buckets; **M15 bars** = complete 15-M1
   server buckets. Buckets are keyed by `t // span` on server epoch seconds (the server
   offset is whole hours, so buckets align to server wall-clock hours/quarters). A bucket
   is complete only when it holds exactly 60 (resp. 15) non-suspect M1 bars; an hour
   containing the suspect roll bars is therefore dropped, not patched.
3. **Wilder ATR14**: `TR_t = max(h-l, |h-c_{t-1}|, |l-c_{t-1}|)`, first ATR =
   mean of the first 14 TR, then `ATR_t = (ATR_{t-1}*13 + TR_t)/14`. The ATR series is
   computed once over the whole continuous bucket series (server time), then grouped by
   server year for the per-year medians.
4. **Pip**: `1e-4` for all symbols except USDJPY = `1e-2` (`data_plane.py:26-27`).
5. **Server clock** = UTC + 2 (winter) / +3 (EU DST), applied via
   `eu_server_offset_hours` imported READ-ONLY from
   `03. EA Developer/EA_VolmanPA/research/lab/vpa_random_baseline.py:60` (sub-agent A's
   `PA_Pro/lib/pa_clock.py` did not exist at scan time; the script prefers it if present,
   and each JSON records which source was used). The UTC column = server epoch − offset
   at that timestamp.
6. **Gaps > 1 day** are measured on the raw timestamp sequence (all bars) as
   `dt > 86400 s`; a non-suspect-only variant is also stored in the JSON. The 10 largest
   gaps are reported with both server and UTC dates.
7. Per-year buckets use the **server-time year** of the bucket start.

`ASSUMPTION:` suspect bars are assumed correctly flagged by the ETL; this work does not
re-derive the flags.

---

## 3. Cross-symbol data quality summary (2010-2026)

| Symbol | first bar (server) | first bar (UTC) | last bar (server) | last bar (UTC) | M1 rows | suspect % | gaps > 1d (raw) | gaps > 1d (non-suspect) |
|---|---|---|---|---|---|---|---|---|
| EURUSD | 2010-01-04 00:00 | 2010-01-03 22:00 | 2026-09-18 16:50 | 2026-09-18 13:50 | 6,200,976 | 1.111 % | 884 | 885 |
| GBPUSD | 2010-01-04 00:00 | 2010-01-03 22:00 | 2026-09-18 16:50 | 2026-09-18 13:50 | 6,201,227 | 1.110 % | 884 | 885 |
| USDJPY | 2010-01-04 00:00 | 2010-01-03 22:00 | 2026-09-18 16:50 | 2026-09-18 13:50 | 6,200,596 | 1.111 % | 883 | 885 |
| AUDUSD | 2010-01-04 00:00 | 2010-01-03 22:00 | 2026-09-18 08:06 | 2026-09-18 05:06 | 6,199,005 | 1.108 % | 884 | 885 |
| USDCAD | 2010-01-04 00:00 | 2010-01-03 22:00 | 2026-11-23 08:57 | 2026-11-23 06:57 | 6,195,950 | 1.100 % | 885 | 885 |
| USDCHF | 2010-01-04 00:00 | 2010-01-03 22:00 | 2026-09-18 16:50 | 2026-09-18 13:50 | 6,193,336 | 1.097 % | 884 | 885 |
| NZDUSD | 2010-01-04 00:00 | 2010-01-03 22:00 | 2026-09-18 08:07 | 2026-09-18 05:07 | 6,192,049 | 1.105 % | 884 | 885 |

All caches: timestamps strictly increasing, 0 duplicates/backwards (field `timestamps_duplicate_or_backwards` = 0 in every JSON). Per-symbol SHA256 of each cache file is in the JSON (`cache_sha256`).

---

## 4. EURUSD — full detail

### Coverage and data quality

| item | value |
|---|---|
| first bar (server) | 2010-01-04 00:00 |
| first bar (UTC) | 2010-01-03 22:00 |
| last bar (server) | 2026-09-18 16:50 |
| last bar (UTC) | 2026-09-18 13:50 |
| M1 rows total | 6,200,976 |
| suspect rows total | 1.1106 % |
| timestamps strictly increasing | true (0 duplicate/backwards) |
| gaps > 1 day (raw / non-suspect) | 884 / 885 |
| cache SHA256 | `CDB65BF0CBEA09898C77C4A404F303A18FCC87BE42BD6FF062078575A0FE3995` |
| clock source | `03. EA Developer/EA_VolmanPA/research/lab/vpa_random_baseline.py:60` |

### Per-year M1 counts, suspect % and ATR14 (pips)

`c_rt` used for the share columns = 1.0 pips (threshold 10.0 pips). Overall medians: **H1 15.40 p** (n=95,387), **M15 7.23 p** (n=400,402). Overall shares ATR >= 10*c_rt: H1 87.9 %, M15 26.3 %.

| Year | M1 bars | suspect % | H1 med | H1 n | H1 share >= 10*c_rt | M15 med | M15 n | M15 share >= 10*c_rt |
|---|---|---|---|---|---|---|---|---|
| 2010 | 367,194 | 1.120 | 29.01 | 4,937 | 100.0 % | 12.99 | 22,664 | 80.2 % |
| 2011 | 369,020 | 1.137 | 29.74 | 5,267 | 99.8 % | 13.64 | 23,425 | 81.6 % |
| 2012 | 369,878 | 1.133 | 19.26 | 5,781 | 100.0 % | 9.01 | 24,002 | 39.0 % |
| 2013 | 368,613 | 1.129 | 17.23 | 5,802 | 99.3 % | 7.79 | 23,958 | 27.0 % |
| 2014 | 367,334 | 1.128 | 13.49 | 5,319 | 83.8 % | 5.88 | 23,168 | 11.6 % |
| 2015 | 370,886 | 1.125 | 22.02 | 5,686 | 99.9 % | 9.94 | 23,944 | 49.5 % |
| 2016 | 373,151 | 1.112 | 15.79 | 5,858 | 96.8 % | 7.35 | 24,247 | 22.2 % |
| 2017 | 370,355 | 1.012 | 14.24 | 5,720 | 94.8 % | 6.57 | 24,002 | 10.6 % |
| 2018 | 371,934 | 1.113 | 15.40 | 5,872 | 99.2 % | 7.46 | 24,201 | 18.8 % |
| 2019 | 371,476 | 1.113 | 9.81 | 5,854 | 47.5 % | 4.58 | 24,174 | 2.1 % |
| 2020 | 373,026 | 1.115 | 14.82 | 5,887 | 86.0 % | 6.89 | 24,294 | 21.3 % |
| 2021 | 373,168 | 1.108 | 11.51 | 5,883 | 74.7 % | 5.43 | 24,293 | 3.9 % |
| 2022 | 372,852 | 1.112 | 19.11 | 5,827 | 99.7 % | 8.69 | 24,178 | 37.2 % |
| 2023 | 371,354 | 1.085 | 13.65 | 5,769 | 95.2 % | 6.26 | 24,083 | 10.9 % |
| 2024 | 373,219 | 1.112 | 10.42 | 5,866 | 55.5 % | 4.81 | 24,268 | 4.7 % |
| 2025 | 370,639 | 1.109 | 14.57 | 5,812 | 93.0 % | 6.88 | 24,094 | 18.0 % |
| 2026 (partial) | 266,877 | 1.118 | 11.35 | 4,247 | 67.9 % | 5.45 | 17,407 | 7.5 % |

### 10 largest gaps > 1 day (raw series)

| from (server) | to (server) | from (UTC) | to (UTC) | hours |
|---|---|---|---|---|
| 2017-12-22 23:59 | 2017-12-26 06:00 | 2017-12-22 21:59 | 2017-12-26 04:00 | 78.02 |
| 2015-12-24 18:59 | 2015-12-28 00:05 | 2015-12-24 16:59 | 2015-12-27 22:05 | 77.1 |
| 2015-12-31 20:00 | 2016-01-04 00:00 | 2015-12-31 18:00 | 2016-01-03 22:00 | 76.0 |
| 2020-12-24 20:59 | 2020-12-28 00:04 | 2020-12-24 18:59 | 2020-12-27 22:04 | 75.08 |
| 2020-12-31 23:00 | 2021-01-04 00:01 | 2020-12-31 21:00 | 2021-01-03 22:01 | 73.02 |
| 2023-12-29 23:58 | 2024-01-02 00:00 | 2023-12-29 21:58 | 2024-01-01 22:00 | 72.03 |
| 2017-12-29 23:59 | 2018-01-02 00:00 | 2017-12-29 21:59 | 2018-01-01 22:00 | 72.02 |
| 2022-12-23 23:55 | 2022-12-26 09:04 | 2022-12-23 21:55 | 2022-12-26 07:04 | 57.15 |
| 2011-12-23 22:59 | 2011-12-26 08:00 | 2011-12-23 20:59 | 2011-12-26 06:00 | 57.02 |
| 2022-12-30 23:54 | 2023-01-02 07:02 | 2022-12-30 21:54 | 2023-01-02 05:02 | 55.13 |

---

## 5. GBPUSD — full detail

### Coverage and data quality

| item | value |
|---|---|
| first bar (server) | 2010-01-04 00:00 |
| first bar (UTC) | 2010-01-03 22:00 |
| last bar (server) | 2026-09-18 16:50 |
| last bar (UTC) | 2026-09-18 13:50 |
| M1 rows total | 6,201,227 |
| suspect rows total | 1.1098 % |
| timestamps strictly increasing | true (0 duplicate/backwards) |
| gaps > 1 day (raw / non-suspect) | 884 / 885 |
| cache SHA256 | `7DAB359F642D9AD5A68C75B02EC4536977B1D1E80647F09C74E184E8F8283B81` |
| clock source | `03. EA Developer/EA_VolmanPA/research/lab/vpa_random_baseline.py:60` |

### Per-year M1 counts, suspect % and ATR14 (pips)

`c_rt` used for the share columns = 1.1 pips (threshold 11.0 pips). Overall medians: **H1 19.40 p** (n=95,666), **M15 9.18 p** (n=400,826). Overall shares ATR >= 10*c_rt: H1 97.2 %, M15 34.3 %.

| Year | M1 bars | suspect % | H1 med | H1 n | H1 share >= 10*c_rt | M15 med | M15 n | M15 share >= 10*c_rt |
|---|---|---|---|---|---|---|---|---|
| 2010 | 367,557 | 1.125 | 31.55 | 5,054 | 100.0 % | 14.72 | 22,911 | 79.2 % |
| 2011 | 368,609 | 1.126 | 27.40 | 5,263 | 100.0 % | 12.99 | 23,338 | 66.3 % |
| 2012 | 369,905 | 1.128 | 18.18 | 5,812 | 98.9 % | 8.57 | 24,036 | 25.8 % |
| 2013 | 368,683 | 1.132 | 19.21 | 5,837 | 100.0 % | 8.89 | 24,010 | 28.7 % |
| 2014 | 368,049 | 1.127 | 16.34 | 5,544 | 90.5 % | 7.31 | 23,613 | 17.8 % |
| 2015 | 370,876 | 1.110 | 21.63 | 5,741 | 100.0 % | 10.09 | 24,003 | 42.4 % |
| 2016 | 373,111 | 1.128 | 24.83 | 5,786 | 100.0 % | 11.92 | 24,112 | 56.9 % |
| 2017 | 370,248 | 1.014 | 18.40 | 5,701 | 99.0 % | 8.72 | 23,941 | 25.6 % |
| 2018 | 371,927 | 1.123 | 19.03 | 5,863 | 100.0 % | 9.13 | 24,189 | 31.9 % |
| 2019 | 371,476 | 1.119 | 16.99 | 5,836 | 95.6 % | 8.15 | 24,158 | 24.0 % |
| 2020 | 372,994 | 1.122 | 22.44 | 5,853 | 99.4 % | 10.64 | 24,255 | 47.0 % |
| 2021 | 373,119 | 1.107 | 16.91 | 5,878 | 98.8 % | 8.08 | 24,278 | 19.2 % |
| 2022 | 372,704 | 1.107 | 23.81 | 5,828 | 100.0 % | 11.08 | 24,159 | 50.7 % |
| 2023 | 371,212 | 1.070 | 17.95 | 5,773 | 99.5 % | 8.45 | 24,077 | 25.2 % |
| 2024 | 373,200 | 1.112 | 13.89 | 5,859 | 82.8 % | 6.37 | 24,261 | 8.3 % |
| 2025 | 370,873 | 1.104 | 16.68 | 5,816 | 99.5 % | 7.96 | 24,110 | 17.0 % |
| 2026 (partial) | 266,684 | 1.114 | 15.01 | 4,222 | 86.2 % | 7.03 | 17,375 | 14.3 % |

### 10 largest gaps > 1 day (raw series)

| from (server) | to (server) | from (UTC) | to (UTC) | hours |
|---|---|---|---|---|
| 2017-12-22 23:59 | 2017-12-26 06:00 | 2017-12-22 21:59 | 2017-12-26 04:00 | 78.02 |
| 2015-12-24 18:59 | 2015-12-28 00:05 | 2015-12-24 16:59 | 2015-12-27 22:05 | 77.1 |
| 2015-12-31 20:00 | 2016-01-04 00:00 | 2015-12-31 18:00 | 2016-01-03 22:00 | 76.0 |
| 2020-12-24 20:59 | 2020-12-28 00:04 | 2020-12-24 18:59 | 2020-12-27 22:04 | 75.08 |
| 2020-12-31 23:00 | 2021-01-04 00:02 | 2020-12-31 21:00 | 2021-01-03 22:02 | 73.03 |
| 2017-12-29 23:59 | 2018-01-02 00:01 | 2017-12-29 21:59 | 2018-01-01 22:01 | 72.03 |
| 2023-12-29 23:58 | 2024-01-02 00:00 | 2023-12-29 21:58 | 2024-01-01 22:00 | 72.03 |
| 2022-12-23 23:55 | 2022-12-26 09:03 | 2022-12-23 21:55 | 2022-12-26 07:03 | 57.13 |
| 2011-12-23 22:59 | 2011-12-26 08:00 | 2011-12-23 20:59 | 2011-12-26 06:00 | 57.02 |
| 2022-12-30 23:55 | 2023-01-02 07:02 | 2022-12-30 21:55 | 2023-01-02 05:02 | 55.12 |

---

## 6. USDJPY — full detail

### Coverage and data quality

| item | value |
|---|---|
| first bar (server) | 2010-01-04 00:00 |
| first bar (UTC) | 2010-01-03 22:00 |
| last bar (server) | 2026-09-18 16:50 |
| last bar (UTC) | 2026-09-18 13:50 |
| M1 rows total | 6,200,596 |
| suspect rows total | 1.1105 % |
| timestamps strictly increasing | true (0 duplicate/backwards) |
| gaps > 1 day (raw / non-suspect) | 883 / 885 |
| cache SHA256 | `57F96E5CDBE4FA8ED0B1608BA9A66CA7091E8E441B8F2A3D840919B0A7A2813E` |
| clock source | `03. EA Developer/EA_VolmanPA/research/lab/vpa_random_baseline.py:60` |

### Per-year M1 counts, suspect % and ATR14 (pips)

`c_rt` used for the share columns = 1.4 pips (threshold 14.0 pips). Overall medians: **H1 15.81 p** (n=95,349), **M15 7.35 p** (n=400,378). Overall shares ATR >= 10*c_rt: H1 59.8 %, M15 10.4 %.

| Year | M1 bars | suspect % | H1 med | H1 n | H1 share >= 10*c_rt | M15 med | M15 n | M15 share >= 10*c_rt |
|---|---|---|---|---|---|---|---|---|
| 2010 | 367,049 | 1.101 | 16.94 | 5,006 | 81.9 % | 7.72 | 22,778 | 4.3 % |
| 2011 | 368,497 | 1.131 | 12.19 | 5,105 | 31.5 % | 5.66 | 23,144 | 1.8 % |
| 2012 | 369,645 | 1.133 | 10.01 | 5,724 | 15.2 % | 4.82 | 23,882 | 0.1 % |
| 2013 | 368,682 | 1.144 | 19.00 | 5,796 | 83.6 % | 8.79 | 23,969 | 10.8 % |
| 2014 | 367,840 | 1.132 | 12.83 | 5,465 | 43.2 % | 5.92 | 23,465 | 5.3 % |
| 2015 | 370,855 | 1.105 | 16.43 | 5,752 | 67.7 % | 7.49 | 24,001 | 7.4 % |
| 2016 | 373,328 | 1.129 | 21.40 | 5,826 | 95.0 % | 10.03 | 24,209 | 16.0 % |
| 2017 | 370,562 | 1.018 | 16.66 | 5,765 | 78.9 % | 7.79 | 24,067 | 6.0 % |
| 2018 | 371,938 | 1.123 | 13.24 | 5,880 | 41.6 % | 6.33 | 24,209 | 1.0 % |
| 2019 | 371,473 | 1.115 | 10.42 | 5,850 | 15.3 % | 4.84 | 24,173 | 0.9 % |
| 2020 | 372,985 | 1.111 | 11.16 | 5,882 | 26.2 % | 5.31 | 24,285 | 7.1 % |
| 2021 | 373,116 | 1.102 | 10.54 | 5,884 | 11.7 % | 4.92 | 24,291 | 0.4 % |
| 2022 | 372,697 | 1.106 | 23.42 | 5,826 | 83.8 % | 10.78 | 24,168 | 26.3 % |
| 2023 | 371,140 | 1.063 | 22.88 | 5,758 | 91.0 % | 10.43 | 24,061 | 22.6 % |
| 2024 | 373,134 | 1.149 | 23.35 | 5,816 | 85.3 % | 10.64 | 24,208 | 28.5 % |
| 2025 | 370,862 | 1.103 | 24.20 | 5,799 | 99.1 % | 11.31 | 24,094 | 26.4 % |
| 2026 (partial) | 266,793 | 1.114 | 17.46 | 4,215 | 67.7 % | 8.11 | 17,374 | 12.1 % |

### 10 largest gaps > 1 day (raw series)

| from (server) | to (server) | from (UTC) | to (UTC) | hours |
|---|---|---|---|---|
| 2017-12-22 23:59 | 2017-12-26 06:00 | 2017-12-22 21:59 | 2017-12-26 04:00 | 78.02 |
| 2015-12-24 18:59 | 2015-12-28 00:04 | 2015-12-24 16:59 | 2015-12-27 22:04 | 77.08 |
| 2015-12-31 20:00 | 2016-01-04 00:00 | 2015-12-31 18:00 | 2016-01-03 22:00 | 76.0 |
| 2020-12-24 20:59 | 2020-12-28 00:03 | 2020-12-24 18:59 | 2020-12-27 22:03 | 75.07 |
| 2020-12-31 23:00 | 2021-01-04 00:02 | 2020-12-31 21:00 | 2021-01-03 22:02 | 73.03 |
| 2017-12-29 23:59 | 2018-01-02 00:01 | 2017-12-29 21:59 | 2018-01-01 22:01 | 72.03 |
| 2023-12-29 23:58 | 2024-01-02 00:00 | 2023-12-29 21:58 | 2024-01-01 22:00 | 72.03 |
| 2022-12-23 23:55 | 2022-12-26 09:04 | 2022-12-23 21:55 | 2022-12-26 07:04 | 57.15 |
| 2011-12-23 23:00 | 2011-12-26 08:00 | 2011-12-23 21:00 | 2011-12-26 06:00 | 57.0 |
| 2022-12-30 23:55 | 2023-01-02 07:00 | 2022-12-30 21:55 | 2023-01-02 05:00 | 55.08 |

---

## 7. AUDUSD — full detail

### Coverage and data quality

| item | value |
|---|---|
| first bar (server) | 2010-01-04 00:00 |
| first bar (UTC) | 2010-01-03 22:00 |
| last bar (server) | 2026-09-18 08:06 |
| last bar (UTC) | 2026-09-18 05:06 |
| M1 rows total | 6,199,005 |
| suspect rows total | 1.1080 % |
| timestamps strictly increasing | true (0 duplicate/backwards) |
| gaps > 1 day (raw / non-suspect) | 884 / 885 |
| cache SHA256 | `3A3E18E3758B65BF216F9BF10A4B19DFEA5E40A7674F74FA4EBDAFFFF09B9FFD` |
| clock source | `03. EA Developer/EA_VolmanPA/research/lab/vpa_random_baseline.py:60` |

### Per-year M1 counts, suspect % and ATR14 (pips)

`c_rt` used for the share columns = 1.4 pips (threshold 14.0 pips). Overall medians: **H1 13.72 p** (n=95,056), **M15 6.56 p** (n=399,807). Overall shares ATR >= 10*c_rt: H1 47.9 %, M15 4.8 %.

| Year | M1 bars | suspect % | H1 med | H1 n | H1 share >= 10*c_rt | M15 med | M15 n | M15 share >= 10*c_rt |
|---|---|---|---|---|---|---|---|---|
| 2010 | 366,412 | 1.123 | 25.40 | 4,676 | 99.9 % | 11.41 | 22,204 | 23.6 % |
| 2011 | 368,627 | 1.142 | 25.84 | 5,135 | 99.2 % | 11.88 | 23,210 | 31.9 % |
| 2012 | 369,891 | 1.133 | 17.95 | 5,785 | 80.5 % | 8.39 | 24,004 | 3.0 % |
| 2013 | 368,688 | 1.136 | 16.41 | 5,826 | 75.4 % | 7.82 | 23,999 | 5.6 % |
| 2014 | 368,069 | 1.135 | 13.84 | 5,569 | 48.8 % | 6.41 | 23,636 | 1.0 % |
| 2015 | 370,905 | 1.118 | 17.33 | 5,724 | 83.8 % | 8.09 | 23,992 | 3.2 % |
| 2016 | 373,062 | 1.111 | 15.73 | 5,808 | 69.8 % | 7.44 | 24,138 | 1.6 % |
| 2017 | 370,302 | 0.969 | 11.62 | 5,759 | 18.6 % | 5.46 | 24,014 | 0.1 % |
| 2018 | 371,906 | 1.122 | 11.80 | 5,846 | 17.5 % | 5.61 | 24,173 | 0.1 % |
| 2019 | 371,452 | 1.117 | 8.47 | 5,840 | 2.3 % | 4.03 | 24,157 | 0.1 % |
| 2020 | 372,905 | 1.125 | 13.97 | 5,840 | 49.7 % | 6.67 | 24,226 | 5.8 % |
| 2021 | 373,048 | 1.101 | 12.11 | 5,854 | 24.1 % | 5.78 | 24,251 | 0.3 % |
| 2022 | 372,314 | 1.101 | 16.80 | 5,792 | 80.8 % | 7.86 | 24,091 | 2.7 % |
| 2023 | 371,131 | 1.080 | 13.02 | 5,739 | 35.5 % | 6.07 | 24,037 | 0.6 % |
| 2024 | 373,168 | 1.103 | 9.98 | 5,848 | 7.0 % | 4.63 | 24,249 | 0.2 % |
| 2025 | 370,839 | 1.104 | 10.18 | 5,809 | 10.3 % | 4.83 | 24,088 | 1.6 % |
| 2026 (partial) | 266,286 | 1.121 | 10.27 | 4,206 | 22.2 % | 4.96 | 17,338 | 0.8 % |

### 10 largest gaps > 1 day (raw series)

| from (server) | to (server) | from (UTC) | to (UTC) | hours |
|---|---|---|---|---|
| 2017-12-22 23:59 | 2017-12-26 06:00 | 2017-12-22 21:59 | 2017-12-26 04:00 | 78.02 |
| 2015-12-24 18:59 | 2015-12-28 00:04 | 2015-12-24 16:59 | 2015-12-27 22:04 | 77.08 |
| 2015-12-31 20:00 | 2016-01-04 00:00 | 2015-12-31 18:00 | 2016-01-03 22:00 | 76.0 |
| 2020-12-24 20:59 | 2020-12-28 00:03 | 2020-12-24 18:59 | 2020-12-27 22:03 | 75.07 |
| 2020-12-31 23:00 | 2021-01-04 00:02 | 2020-12-31 21:00 | 2021-01-03 22:02 | 73.03 |
| 2017-12-29 23:59 | 2018-01-02 00:03 | 2017-12-29 21:59 | 2018-01-01 22:03 | 72.07 |
| 2023-12-29 23:58 | 2024-01-02 00:00 | 2023-12-29 21:58 | 2024-01-01 22:00 | 72.03 |
| 2022-12-23 23:55 | 2022-12-26 09:03 | 2022-12-23 21:55 | 2022-12-26 07:03 | 57.13 |
| 2011-12-23 22:59 | 2011-12-26 08:01 | 2011-12-23 20:59 | 2011-12-26 06:01 | 57.03 |
| 2022-12-30 23:55 | 2023-01-02 07:06 | 2022-12-30 21:55 | 2023-01-02 05:06 | 55.18 |

---

## 8. USDCAD — full detail

### Coverage and data quality

| item | value |
|---|---|
| first bar (server) | 2010-01-04 00:00 |
| first bar (UTC) | 2010-01-03 22:00 |
| last bar (server) | 2026-11-23 08:57 |
| last bar (UTC) | 2026-11-23 06:57 |
| M1 rows total | 6,195,950 |
| suspect rows total | 1.1003 % |
| timestamps strictly increasing | true (0 duplicate/backwards) |
| gaps > 1 day (raw / non-suspect) | 885 / 885 |
| cache SHA256 | `6FFCE5218B4E8EBB65A4A336FDF1CB5B44C70F4EBC2E67FD7217085F816DD851` |
| clock source | `03. EA Developer/EA_VolmanPA/research/lab/vpa_random_baseline.py:60` |

### Per-year M1 counts, suspect % and ATR14 (pips)

`c_rt` used for the share columns = 1.4 pips (threshold 14.0 pips). Overall medians: **H1 15.25 p** (n=94,423), **M15 7.05 p** (n=398,626). Overall shares ATR >= 10*c_rt: H1 59.6 %, M15 6.5 %.

| Year | M1 bars | suspect % | H1 med | H1 n | H1 share >= 10*c_rt | M15 med | M15 n | M15 share >= 10*c_rt |
|---|---|---|---|---|---|---|---|---|
| 2010 | 366,783 | 1.117 | 22.32 | 4,895 | 98.4 % | 9.91 | 22,627 | 17.1 % |
| 2011 | 368,043 | 1.132 | 18.87 | 4,933 | 88.5 % | 8.69 | 22,872 | 10.5 % |
| 2012 | 369,762 | 1.126 | 12.70 | 5,743 | 33.5 % | 6.07 | 23,938 | 0.2 % |
| 2013 | 368,586 | 1.127 | 11.04 | 5,775 | 20.5 % | 5.27 | 23,935 | 0.7 % |
| 2014 | 366,904 | 1.121 | 13.26 | 5,105 | 42.7 % | 5.70 | 22,883 | 1.1 % |
| 2015 | 370,550 | 1.103 | 20.80 | 5,641 | 97.5 % | 9.28 | 23,815 | 16.1 % |
| 2016 | 372,771 | 1.099 | 22.16 | 5,777 | 96.5 % | 10.13 | 24,045 | 21.4 % |
| 2017 | 369,719 | 1.022 | 16.35 | 5,607 | 78.0 % | 7.35 | 23,761 | 3.8 % |
| 2018 | 371,902 | 1.119 | 15.88 | 5,869 | 73.2 % | 7.25 | 24,187 | 3.4 % |
| 2019 | 371,422 | 1.110 | 11.70 | 5,847 | 22.1 % | 5.28 | 24,160 | 0.4 % |
| 2020 | 372,934 | 1.109 | 16.43 | 5,880 | 69.8 % | 7.98 | 24,274 | 13.1 % |
| 2021 | 372,982 | 1.090 | 15.17 | 5,870 | 65.4 % | 7.11 | 24,258 | 2.7 % |
| 2022 | 372,276 | 1.069 | 19.26 | 5,814 | 93.6 % | 9.05 | 24,099 | 11.5 % |
| 2023 | 371,000 | 1.056 | 14.84 | 5,770 | 62.2 % | 6.80 | 24,054 | 2.6 % |
| 2024 | 373,179 | 1.101 | 11.24 | 5,868 | 18.0 % | 5.07 | 24,269 | 0.4 % |
| 2025 | 370,853 | 1.096 | 12.67 | 5,802 | 37.0 % | 5.97 | 24,090 | 4.3 % |
| 2026 (partial) | 266,284 | 1.110 | 10.87 | 4,227 | 14.9 % | 5.20 | 17,359 | 0.5 % |

### 10 largest gaps > 1 day (raw series)

| from (server) | to (server) | from (UTC) | to (UTC) | hours |
|---|---|---|---|---|
| 2026-09-18 08:08 | 2026-11-23 08:57 | 2026-09-18 05:08 | 2026-11-23 06:57 | 1584.83 |
| 2017-12-22 23:59 | 2017-12-26 06:00 | 2017-12-22 21:59 | 2017-12-26 04:00 | 78.02 |
| 2015-12-24 18:59 | 2015-12-28 00:05 | 2015-12-24 16:59 | 2015-12-27 22:05 | 77.1 |
| 2015-12-31 20:00 | 2016-01-04 00:00 | 2015-12-31 18:00 | 2016-01-03 22:00 | 76.0 |
| 2020-12-24 20:59 | 2020-12-28 00:03 | 2020-12-24 18:59 | 2020-12-27 22:03 | 75.07 |
| 2020-12-31 23:00 | 2021-01-04 00:03 | 2020-12-31 21:00 | 2021-01-03 22:03 | 73.05 |
| 2017-12-29 23:59 | 2018-01-02 00:01 | 2017-12-29 21:59 | 2018-01-01 22:01 | 72.03 |
| 2023-12-29 23:58 | 2024-01-02 00:00 | 2023-12-29 21:58 | 2024-01-01 22:00 | 72.03 |
| 2022-12-23 23:54 | 2022-12-26 09:03 | 2022-12-23 21:54 | 2022-12-26 07:03 | 57.15 |
| 2011-12-23 22:59 | 2011-12-26 08:00 | 2011-12-23 20:59 | 2011-12-26 06:00 | 57.02 |

---

## 9. USDCHF — full detail

### Coverage and data quality

| item | value |
|---|---|
| first bar (server) | 2010-01-04 00:00 |
| first bar (UTC) | 2010-01-03 22:00 |
| last bar (server) | 2026-09-18 16:50 |
| last bar (UTC) | 2026-09-18 13:50 |
| M1 rows total | 6,193,336 |
| suspect rows total | 1.0966 % |
| timestamps strictly increasing | true (0 duplicate/backwards) |
| gaps > 1 day (raw / non-suspect) | 884 / 885 |
| cache SHA256 | `336277814A71317F21B3AB15E85B00C29873A4750E22A2E415A7093BE5EE0436` |
| clock source | `03. EA Developer/EA_VolmanPA/research/lab/vpa_random_baseline.py:60` |

### Per-year M1 counts, suspect % and ATR14 (pips)

`c_rt` used for the share columns = 1.1 pips (threshold 11.0 pips). Overall medians: **H1 12.80 p** (n=94,084), **M15 6.11 p** (n=398,136). Overall shares ATR >= 10*c_rt: H1 67.1 %, M15 10.8 %.

| Year | M1 bars | suspect % | H1 med | H1 n | H1 share >= 10*c_rt | M15 med | M15 n | M15 share >= 10*c_rt |
|---|---|---|---|---|---|---|---|---|
| 2010 | 367,657 | 1.124 | 22.71 | 5,094 | 100.0 % | 10.43 | 23,010 | 43.1 % |
| 2011 | 368,597 | 1.143 | 20.47 | 5,186 | 99.8 % | 9.58 | 23,255 | 35.3 % |
| 2012 | 369,821 | 1.133 | 13.99 | 5,748 | 88.8 % | 6.73 | 23,951 | 6.6 % |
| 2013 | 368,564 | 1.135 | 13.77 | 5,754 | 82.7 % | 6.45 | 23,905 | 9.1 % |
| 2014 | 367,595 | 1.123 | 10.49 | 5,373 | 44.6 % | 4.56 | 23,312 | 2.8 % |
| 2015 | 367,681 | 1.111 | 20.16 | 5,171 | 100.0 % | 9.23 | 22,962 | 33.4 % |
| 2016 | 371,396 | 1.065 | 14.81 | 5,422 | 89.9 % | 6.85 | 23,462 | 11.5 % |
| 2017 | 369,805 | 0.987 | 12.99 | 5,521 | 80.2 % | 6.13 | 23,656 | 4.3 % |
| 2018 | 371,799 | 1.127 | 11.50 | 5,847 | 58.1 % | 5.62 | 24,157 | 1.6 % |
| 2019 | 371,391 | 1.110 | 9.40 | 5,819 | 28.1 % | 4.46 | 24,135 | 0.6 % |
| 2020 | 372,876 | 1.105 | 11.31 | 5,856 | 53.7 % | 5.47 | 24,251 | 6.7 % |
| 2021 | 372,895 | 1.083 | 10.29 | 5,874 | 37.1 % | 4.90 | 24,251 | 0.4 % |
| 2022 | 371,724 | 1.037 | 15.62 | 5,791 | 88.8 % | 7.30 | 24,045 | 14.8 % |
| 2023 | 370,999 | 1.054 | 12.59 | 5,770 | 71.6 % | 5.88 | 24,072 | 5.1 % |
| 2024 | 372,979 | 1.099 | 10.48 | 5,838 | 42.2 % | 4.83 | 24,237 | 2.2 % |
| 2025 | 370,774 | 1.098 | 10.75 | 5,795 | 46.5 % | 5.20 | 24,090 | 5.2 % |
| 2026 (partial) | 266,783 | 1.114 | 9.77 | 4,225 | 31.6 % | 4.65 | 17,385 | 1.0 % |

### 10 largest gaps > 1 day (raw series)

| from (server) | to (server) | from (UTC) | to (UTC) | hours |
|---|---|---|---|---|
| 2017-12-22 23:59 | 2017-12-26 06:00 | 2017-12-22 21:59 | 2017-12-26 04:00 | 78.02 |
| 2015-12-24 18:59 | 2015-12-28 00:05 | 2015-12-24 16:59 | 2015-12-27 22:05 | 77.1 |
| 2015-12-31 20:00 | 2016-01-04 00:00 | 2015-12-31 18:00 | 2016-01-03 22:00 | 76.0 |
| 2015-01-15 20:06 | 2015-01-19 00:00 | 2015-01-15 18:06 | 2015-01-18 22:00 | 75.9 |
| 2020-12-24 20:59 | 2020-12-28 00:03 | 2020-12-24 18:59 | 2020-12-27 22:03 | 75.07 |
| 2020-12-31 23:00 | 2021-01-04 00:02 | 2020-12-31 21:00 | 2021-01-03 22:02 | 73.03 |
| 2017-12-29 23:59 | 2018-01-02 00:05 | 2017-12-29 21:59 | 2018-01-01 22:05 | 72.1 |
| 2023-12-29 23:58 | 2024-01-02 00:00 | 2023-12-29 21:58 | 2024-01-01 22:00 | 72.03 |
| 2022-12-23 23:55 | 2022-12-26 09:03 | 2022-12-23 21:55 | 2022-12-26 07:03 | 57.13 |
| 2011-12-23 22:59 | 2011-12-26 08:00 | 2011-12-23 20:59 | 2011-12-26 06:00 | 57.02 |

---

## 10. NZDUSD — full detail

### Coverage and data quality

| item | value |
|---|---|
| first bar (server) | 2010-01-04 00:00 |
| first bar (UTC) | 2010-01-03 22:00 |
| last bar (server) | 2026-09-18 08:07 |
| last bar (UTC) | 2026-09-18 05:07 |
| M1 rows total | 6,192,049 |
| suspect rows total | 1.1050 % |
| timestamps strictly increasing | true (0 duplicate/backwards) |
| gaps > 1 day (raw / non-suspect) | 884 / 885 |
| cache SHA256 | `59AE4E15D2C81BC785BD0EA533D0CEA35FF0F0C4E00FC98AE5F264438EC82788` |
| clock source | `03. EA Developer/EA_VolmanPA/research/lab/vpa_random_baseline.py:60` |

### Per-year M1 counts, suspect % and ATR14 (pips)

`c_rt` used for the share columns = 1.4 pips (threshold 14.0 pips). Overall medians: **H1 13.13 p** (n=93,436), **M15 6.29 p** (n=396,607). Overall shares ATR >= 10*c_rt: H1 43.6 %, M15 2.4 %.

| Year | M1 bars | suspect % | H1 med | H1 n | H1 share >= 10*c_rt | M15 med | M15 n | M15 share >= 10*c_rt |
|---|---|---|---|---|---|---|---|---|
| 2010 | 361,240 | 1.080 | 22.97 | 3,709 | 99.5 % | 10.01 | 20,033 | 9.9 % |
| 2011 | 367,501 | 1.136 | 22.02 | 4,813 | 98.3 % | 10.03 | 22,654 | 14.3 % |
| 2012 | 369,891 | 1.137 | 15.88 | 5,784 | 71.3 % | 7.66 | 24,006 | 0.4 % |
| 2013 | 368,670 | 1.138 | 17.11 | 5,815 | 84.7 % | 8.18 | 23,988 | 3.6 % |
| 2014 | 368,151 | 1.129 | 13.48 | 5,600 | 45.5 % | 6.50 | 23,697 | 1.6 % |
| 2015 | 370,593 | 1.123 | 17.51 | 5,616 | 85.0 % | 8.14 | 23,811 | 3.9 % |
| 2016 | 372,899 | 1.111 | 15.83 | 5,750 | 75.2 % | 7.50 | 24,051 | 1.7 % |
| 2017 | 370,338 | 0.993 | 12.09 | 5,707 | 24.7 % | 5.73 | 23,956 | 0.2 % |
| 2018 | 371,833 | 1.120 | 10.83 | 5,835 | 10.5 % | 5.21 | 24,152 | 0.1 % |
| 2019 | 371,412 | 1.119 | 8.77 | 5,815 | 1.8 % | 4.12 | 24,128 | 0.1 % |
| 2020 | 372,888 | 1.120 | 12.50 | 5,836 | 35.2 % | 5.95 | 24,230 | 4.3 % |
| 2021 | 372,914 | 1.095 | 12.18 | 5,828 | 23.9 % | 5.75 | 24,203 | 0.2 % |
| 2022 | 372,267 | 1.087 | 14.99 | 5,775 | 62.5 % | 7.00 | 24,034 | 1.6 % |
| 2023 | 371,221 | 1.075 | 12.29 | 5,750 | 25.0 % | 5.72 | 24,043 | 0.3 % |
| 2024 | 373,135 | 1.099 | 9.28 | 5,829 | 3.6 % | 4.31 | 24,229 | 0.0 % |
| 2025 | 370,825 | 1.105 | 9.49 | 5,783 | 7.5 % | 4.44 | 24,068 | 0.5 % |
| 2026 (partial) | 266,271 | 1.125 | 9.20 | 4,191 | 7.8 % | 4.43 | 17,324 | 0.1 % |

### 10 largest gaps > 1 day (raw series)

| from (server) | to (server) | from (UTC) | to (UTC) | hours |
|---|---|---|---|---|
| 2017-12-22 23:59 | 2017-12-26 06:00 | 2017-12-22 21:59 | 2017-12-26 04:00 | 78.02 |
| 2015-12-24 18:59 | 2015-12-28 00:04 | 2015-12-24 16:59 | 2015-12-27 22:04 | 77.08 |
| 2015-12-31 20:00 | 2016-01-04 00:00 | 2015-12-31 18:00 | 2016-01-03 22:00 | 76.0 |
| 2020-12-24 20:59 | 2020-12-28 00:03 | 2020-12-24 18:59 | 2020-12-27 22:03 | 75.07 |
| 2020-12-31 23:00 | 2021-01-04 00:02 | 2020-12-31 21:00 | 2021-01-03 22:02 | 73.03 |
| 2017-12-29 23:59 | 2018-01-02 00:01 | 2017-12-29 21:59 | 2018-01-01 22:01 | 72.03 |
| 2023-12-29 23:58 | 2024-01-02 00:00 | 2023-12-29 21:58 | 2024-01-01 22:00 | 72.03 |
| 2022-12-23 23:55 | 2022-12-26 09:03 | 2022-12-23 21:55 | 2022-12-26 07:03 | 57.13 |
| 2011-12-23 22:59 | 2011-12-26 08:00 | 2011-12-23 20:59 | 2011-12-26 06:00 | 57.02 |
| 2022-12-30 23:55 | 2023-01-02 07:09 | 2022-12-30 21:55 | 2023-01-02 05:09 | 55.23 |

---

## 11. Notes, assumptions and caveats

- `ASSUMPTION:` ATR14 uses complete buckets only; incomplete hours (holidays, the
  suspect 00:00 roll hour, feed gaps) produce no bar at all rather than a patched one.
  Cadence of signals on H1/M15 must therefore tolerate missing buckets.
- `ASSUMPTION:` the share columns for AUDUSD/USDCAD/NZDUSD use the 1.4 p `proxy` c_rt
  from COSTS.md; if the Lead adopts a different c_rt, the share can be re-derived from
  the per-year ATR percentiles stored in each JSON (`p10,p25,median,p75,p90`).
- The 2010-2026 window includes the 2015-01-15 CHF de-peg and the 2020 COVID shock;
  per-year tables keep them visible instead of averaging them away.
- 2026 is partial (cache ends 2026-09-18); do not compare its counts with full years.
- Weekend gaps are the bulk of the "gaps > 1 day" count (roughly 52/year plus holidays);
  the largest gaps are the Christmas/New-Year breaks (see per-symbol tables).
- This inventory is measurement only; no economic claim is made here.

---

## 12. Verification (independent cross-check)

`PA_Pro/docs/_data_inventory_verify.py` (run 2026-09-20 under `pa_slots`) recomputed
EURUSD ATR14(H1) through a different pipeline (pandas `resample("1h")` + independently
written Wilder loop) and compared the clock modules:

```
clock compare n=102 equal=True offsets_seen=[2, 3]
buckets: verify=95400 json_buckets=95400 json_atr_n=95387
overall median: verify=15.403856 json=15.403856 diff=0.00e+00
overall share>=10p: verify=0.879145 json=0.879100
  2010: verify=29.012682 json=29.012682 diff=0.00e+00
  2019: verify=9.813440 json=9.813440 diff=0.00e+00
  2024: verify=10.421306 json=10.421306 diff=0.00e+00
  2026: verify=11.353843 json=11.353843 diff=0.00e+00
  2019 share>=10p: verify=0.474718 json=0.474700
```

- Clock: `pa_clock.server_offset_hours` == the Volman
  `eu_server_offset_hours` on 102 DST-boundary timestamps (2010-2026), so the
  scan's server/UTC columns are consistent with the now-existing PA-PRO clock module.
- ATR medians match exactly; the small share deltas (0.879145 vs 0.879100) are the
  JSON's 4-decimal rounding only.
- The scan JSONs record `clock_source` = the Volman file because `PA_Pro/lib/pa_clock.py`
  did not exist yet at scan time; re-running the scan now would use `pa_clock.py`
  (same semantics).
