# PA-PRO — COSTS (sub-agent B, Round 00)

Status: `DONE`. Charter: `PA_PRO_CHARTER.md` §3/§6/§8 (SHA256
`3C57536848A4AA6113950D06D50331B8C664E18B79D34E08DEF2F1019BC5DC2C`, verified 2026-09-20).
ATR/share numbers come from `PA_Pro/docs/_data_inventory/<SYM>.json` (see
`DATA_INVENTORY.md` for the method); this file adds the cost model and the
cost-geometry feasibility tables. Renderer: `PA_Pro/docs/_costs_render.py`.

**`c_rt` is `RESEARCH_PROXY` (conservative)** — see §7. Every number carries a
file:line provenance; nothing here is a live-broker measurement.

---

## 1. c_rt p90 per symbol (all-in round-turn, pips)

`c_rt = spread_p90 + slippage_p90_rt + commission_bound` (`COST_FEASIBILITY.md:58-63`).
Commission bound = 0.7 pip = $7.00/lot round-turn, an **assumed conservative bound**
(`COST_FEASIBILITY.md:21`, `EA_LiquiditySweep/research/evidence/COST_SOURCE_MANIFEST.json:39-49`;
broker-observed commission is 0.00 on the governed run — `04. Memory/research/20260916_COST_PLANE_AUDIT.md:27-31`).

| Symbol | c_rt p90 (pips) | status | provenance |
|---|---|---|---|
| EURUSD | **1.0** | measured | `EA_VolmanPA/PLAN/COST_FEASIBILITY.md:75`; `vpa_random_baseline.py:41` |
| GBPUSD | **1.1** | measured | `EA_VolmanPA/PLAN/COST_FEASIBILITY.md:76`; `vpa_random_baseline.py:41` |
| USDJPY | **1.4** | measured | `EA_VolmanPA/PLAN/COST_FEASIBILITY.md:77`; `vpa_random_baseline.py:41` |
| AUDUSD | **1.4** | proxy | no measured c_rt in repo — `proxy` per `PA_PRO_CHARTER.md:96-98`; supporting: `04. Memory/research/20260919_LAB_FALSIFICATION_MAP_AND_COST_REFRAME.md:376` (Dukascopy AUDUSD RT spread ~1 p) |
| USDCAD | **1.4** | proxy | no measured c_rt in repo — `proxy` per `PA_PRO_CHARTER.md:96-98`; `COST_FEASIBILITY.md:79` (NOT MEASURED) |
| USDCHF | **1.1** | measured | `EA_VolmanPA/PLAN/COST_FEASIBILITY.md:78`; `vpa_random_baseline.py:41` |
| NZDUSD | **1.4** | proxy | no measured c_rt in repo — `proxy` per `PA_PRO_CHARTER.md:96-98`; `COST_FEASIBILITY.md:81` (NOT MEASURED) |

---

## 2. Cost tiers and semantics (charter §6)

Tiers multiply **`c_rt`**; the implementation shifts the fill **against the trader** by
`tier x c_rt` at entry (the round-turn cost is charged once per trade, as an adverse price
shift; `EA_VolmanPA/research/lab/vpa_random_baseline.py:10-11`). The referee reports every
metric per tier (charter §6, `PA_PRO_CHARTER.md:156-160`).

| tier | multiplier | semantics |
|---|---|---|
| gross | 0.0 | sanity only, no cost; never a promotion basis |
| x1 | 1.0 | baseline `c_rt` p90 (research proxy) |
| x1.5 | 1.5 | stress |
| x2 | 2.0 | stress ceiling; SCREEN gate requires PF x2 >= 1.00 (`PA_PRO_CHARTER.md:195`) |

Minimum stop = `10 x c_rt x tier` (charter §3 geometry guard, `PA_PRO_CHARTER.md:100`;
x1 is the hard guard, `PA_PRO_CHARTER.md:202`):

| Symbol | x1 min stop | x1.5 min stop | x2 min stop |
|---|---|---|---|
| EURUSD | 10.0 p | 15.0 p | 20.0 p |
| GBPUSD | 11.0 p | 16.5 p | 22.0 p |
| USDJPY | 14.0 p | 21.0 p | 28.0 p |
| AUDUSD | 14.0 p | 21.0 p | 28.0 p |
| USDCAD | 14.0 p | 21.0 p | 28.0 p |
| USDCHF | 11.0 p | 16.5 p | 22.0 p |
| NZDUSD | 14.0 p | 21.0 p | 28.0 p |

---

## 3. Feasibility arithmetic (stated formula)

For symbol `s`, year `y`:

- `min_stop_x1(s) = 10 x c_rt(s)` (pips), the charter §3 geometry guard at x1.
- `ratio_H1(s,y) = min_stop_x1(s) / median(ATR14_H1(s,y))` — how many times the typical
  H1 bar's ATR the guard costs. `ratio < 1` means a 1xATR14(H1) stop is wide enough at x1;
  `ratio > 1` means a structural H1 stop has to exceed the typical H1 ATR.
- `share_H1(s,y) = mean(ATR14_H1(s,y) >= min_stop_x1(s))` — the fraction of complete H1
  bars in the year whose ATR14 alone already covers the guard. Equivalently: the share of
  H1 bars on which a 1xATR14(H1) stop is admissible at x1.
- M15 columns use the same min stop against `median(ATR14_M15)`.

Caveat: `share_H1` is the share of **bars**, not of signals; setups can (and should)
select wide-ATR bars, so this is a floor on feasibility, not a forecast.

---

## 4. Feasibility per symbol — overall (2010-2026, complete bars only)

| Symbol | c_rt x1 | min stop x1 | ATR14 H1 med | ratio H1 | share H1 >= guard | ATR14 M15 med | ratio M15 |
|---|---|---|---|---|---|---|---|
| EURUSD | 1.0 | 10.0 p | 15.40 p | 0.65 | 87.9 % | 7.23 p | 1.38 |
| GBPUSD | 1.1 | 11.0 p | 19.40 p | 0.57 | 97.2 % | 9.18 p | 1.20 |
| USDJPY | 1.4 | 14.0 p | 15.81 p | 0.89 | 59.8 % | 7.35 p | 1.91 |
| AUDUSD | 1.4 | 14.0 p | 13.72 p | 1.02 | 47.9 % | 6.56 p | 2.13 |
| USDCAD | 1.4 | 14.0 p | 15.25 p | 0.92 | 59.6 % | 7.05 p | 1.99 |
| USDCHF | 1.1 | 11.0 p | 12.80 p | 0.86 | 67.1 % | 6.11 p | 1.80 |
| NZDUSD | 1.4 | 14.0 p | 13.13 p | 1.07 | 43.6 % | 6.29 p | 2.22 |

---

## 5. Feasibility per symbol and per year

Share column = fraction of complete H1 bars in that year with `ATR14(H1) >= 10 x c_rt(x1)`; `c_rt` is the symbol's x1 value (constant across years in this research plane). 2026 is partial (cache ends 2026-09-18).

### EURUSD (c_rt x1 = 1.0 p, min stop = 10.0 p)

| Year | H1 med | ratio H1 | share H1 >= guard | H1 n | M15 med | ratio M15 |
|---|---|---|---|---|---|---|
| 2010 | 29.01 p | 0.34 | 100.0 % | 4,937 | 12.99 p | 0.77 |
| 2011 | 29.74 p | 0.34 | 99.8 % | 5,267 | 13.64 p | 0.73 |
| 2012 | 19.26 p | 0.52 | 100.0 % | 5,781 | 9.01 p | 1.11 |
| 2013 | 17.23 p | 0.58 | 99.3 % | 5,802 | 7.79 p | 1.28 |
| 2014 | 13.49 p | 0.74 | 83.8 % | 5,319 | 5.88 p | 1.70 |
| 2015 | 22.02 p | 0.45 | 99.9 % | 5,686 | 9.94 p | 1.01 |
| 2016 | 15.79 p | 0.63 | 96.8 % | 5,858 | 7.35 p | 1.36 |
| 2017 | 14.24 p | 0.70 | 94.8 % | 5,720 | 6.57 p | 1.52 |
| 2018 | 15.40 p | 0.65 | 99.2 % | 5,872 | 7.46 p | 1.34 |
| 2019 | 9.81 p | 1.02 | 47.5 % | 5,854 | 4.58 p | 2.18 |
| 2020 | 14.82 p | 0.67 | 86.0 % | 5,887 | 6.89 p | 1.45 |
| 2021 | 11.51 p | 0.87 | 74.7 % | 5,883 | 5.43 p | 1.84 |
| 2022 | 19.11 p | 0.52 | 99.7 % | 5,827 | 8.69 p | 1.15 |
| 2023 | 13.65 p | 0.73 | 95.2 % | 5,769 | 6.26 p | 1.60 |
| 2024 | 10.42 p | 0.96 | 55.5 % | 5,866 | 4.81 p | 2.08 |
| 2025 | 14.57 p | 0.69 | 93.0 % | 5,812 | 6.88 p | 1.45 |
| 2026 (partial) | 11.35 p | 0.88 | 67.9 % | 4,247 | 5.45 p | 1.83 |

### GBPUSD (c_rt x1 = 1.1 p, min stop = 11.0 p)

| Year | H1 med | ratio H1 | share H1 >= guard | H1 n | M15 med | ratio M15 |
|---|---|---|---|---|---|---|
| 2010 | 31.55 p | 0.35 | 100.0 % | 5,054 | 14.72 p | 0.75 |
| 2011 | 27.40 p | 0.40 | 100.0 % | 5,263 | 12.99 p | 0.85 |
| 2012 | 18.18 p | 0.61 | 98.9 % | 5,812 | 8.57 p | 1.28 |
| 2013 | 19.21 p | 0.57 | 100.0 % | 5,837 | 8.89 p | 1.24 |
| 2014 | 16.34 p | 0.67 | 90.5 % | 5,544 | 7.31 p | 1.50 |
| 2015 | 21.63 p | 0.51 | 100.0 % | 5,741 | 10.09 p | 1.09 |
| 2016 | 24.83 p | 0.44 | 100.0 % | 5,786 | 11.92 p | 0.92 |
| 2017 | 18.40 p | 0.60 | 99.0 % | 5,701 | 8.72 p | 1.26 |
| 2018 | 19.03 p | 0.58 | 100.0 % | 5,863 | 9.13 p | 1.20 |
| 2019 | 16.99 p | 0.65 | 95.6 % | 5,836 | 8.15 p | 1.35 |
| 2020 | 22.44 p | 0.49 | 99.4 % | 5,853 | 10.64 p | 1.03 |
| 2021 | 16.91 p | 0.65 | 98.8 % | 5,878 | 8.08 p | 1.36 |
| 2022 | 23.81 p | 0.46 | 100.0 % | 5,828 | 11.08 p | 0.99 |
| 2023 | 17.95 p | 0.61 | 99.5 % | 5,773 | 8.45 p | 1.30 |
| 2024 | 13.89 p | 0.79 | 82.8 % | 5,859 | 6.37 p | 1.73 |
| 2025 | 16.68 p | 0.66 | 99.5 % | 5,816 | 7.96 p | 1.38 |
| 2026 (partial) | 15.01 p | 0.73 | 86.2 % | 4,222 | 7.03 p | 1.56 |

### USDJPY (c_rt x1 = 1.4 p, min stop = 14.0 p)

| Year | H1 med | ratio H1 | share H1 >= guard | H1 n | M15 med | ratio M15 |
|---|---|---|---|---|---|---|
| 2010 | 16.94 p | 0.83 | 81.9 % | 5,006 | 7.72 p | 1.81 |
| 2011 | 12.19 p | 1.15 | 31.5 % | 5,105 | 5.66 p | 2.47 |
| 2012 | 10.01 p | 1.40 | 15.2 % | 5,724 | 4.82 p | 2.91 |
| 2013 | 19.00 p | 0.74 | 83.6 % | 5,796 | 8.79 p | 1.59 |
| 2014 | 12.83 p | 1.09 | 43.2 % | 5,465 | 5.92 p | 2.36 |
| 2015 | 16.43 p | 0.85 | 67.7 % | 5,752 | 7.49 p | 1.87 |
| 2016 | 21.40 p | 0.65 | 95.0 % | 5,826 | 10.03 p | 1.40 |
| 2017 | 16.66 p | 0.84 | 78.9 % | 5,765 | 7.79 p | 1.80 |
| 2018 | 13.24 p | 1.06 | 41.6 % | 5,880 | 6.33 p | 2.21 |
| 2019 | 10.42 p | 1.34 | 15.3 % | 5,850 | 4.84 p | 2.89 |
| 2020 | 11.16 p | 1.25 | 26.2 % | 5,882 | 5.31 p | 2.64 |
| 2021 | 10.54 p | 1.33 | 11.7 % | 5,884 | 4.92 p | 2.85 |
| 2022 | 23.42 p | 0.60 | 83.8 % | 5,826 | 10.78 p | 1.30 |
| 2023 | 22.88 p | 0.61 | 91.0 % | 5,758 | 10.43 p | 1.34 |
| 2024 | 23.35 p | 0.60 | 85.3 % | 5,816 | 10.64 p | 1.32 |
| 2025 | 24.20 p | 0.58 | 99.1 % | 5,799 | 11.31 p | 1.24 |
| 2026 (partial) | 17.46 p | 0.80 | 67.7 % | 4,215 | 8.11 p | 1.73 |

### AUDUSD (c_rt x1 = 1.4 p, min stop = 14.0 p)

| Year | H1 med | ratio H1 | share H1 >= guard | H1 n | M15 med | ratio M15 |
|---|---|---|---|---|---|---|
| 2010 | 25.40 p | 0.55 | 99.9 % | 4,676 | 11.41 p | 1.23 |
| 2011 | 25.84 p | 0.54 | 99.2 % | 5,135 | 11.88 p | 1.18 |
| 2012 | 17.95 p | 0.78 | 80.5 % | 5,785 | 8.39 p | 1.67 |
| 2013 | 16.41 p | 0.85 | 75.4 % | 5,826 | 7.82 p | 1.79 |
| 2014 | 13.84 p | 1.01 | 48.8 % | 5,569 | 6.41 p | 2.18 |
| 2015 | 17.33 p | 0.81 | 83.8 % | 5,724 | 8.09 p | 1.73 |
| 2016 | 15.73 p | 0.89 | 69.8 % | 5,808 | 7.44 p | 1.88 |
| 2017 | 11.62 p | 1.20 | 18.6 % | 5,759 | 5.46 p | 2.56 |
| 2018 | 11.80 p | 1.19 | 17.5 % | 5,846 | 5.61 p | 2.50 |
| 2019 | 8.47 p | 1.65 | 2.3 % | 5,840 | 4.03 p | 3.48 |
| 2020 | 13.97 p | 1.00 | 49.7 % | 5,840 | 6.67 p | 2.10 |
| 2021 | 12.11 p | 1.16 | 24.1 % | 5,854 | 5.78 p | 2.42 |
| 2022 | 16.80 p | 0.83 | 80.8 % | 5,792 | 7.86 p | 1.78 |
| 2023 | 13.02 p | 1.07 | 35.5 % | 5,739 | 6.07 p | 2.31 |
| 2024 | 9.98 p | 1.40 | 7.0 % | 5,848 | 4.63 p | 3.02 |
| 2025 | 10.18 p | 1.37 | 10.3 % | 5,809 | 4.83 p | 2.90 |
| 2026 (partial) | 10.27 p | 1.36 | 22.2 % | 4,206 | 4.96 p | 2.82 |

### USDCAD (c_rt x1 = 1.4 p, min stop = 14.0 p)

| Year | H1 med | ratio H1 | share H1 >= guard | H1 n | M15 med | ratio M15 |
|---|---|---|---|---|---|---|
| 2010 | 22.32 p | 0.63 | 98.4 % | 4,895 | 9.91 p | 1.41 |
| 2011 | 18.87 p | 0.74 | 88.5 % | 4,933 | 8.69 p | 1.61 |
| 2012 | 12.70 p | 1.10 | 33.5 % | 5,743 | 6.07 p | 2.31 |
| 2013 | 11.04 p | 1.27 | 20.5 % | 5,775 | 5.27 p | 2.66 |
| 2014 | 13.26 p | 1.06 | 42.7 % | 5,105 | 5.70 p | 2.46 |
| 2015 | 20.80 p | 0.67 | 97.5 % | 5,641 | 9.28 p | 1.51 |
| 2016 | 22.16 p | 0.63 | 96.5 % | 5,777 | 10.13 p | 1.38 |
| 2017 | 16.35 p | 0.86 | 78.0 % | 5,607 | 7.35 p | 1.91 |
| 2018 | 15.88 p | 0.88 | 73.2 % | 5,869 | 7.25 p | 1.93 |
| 2019 | 11.70 p | 1.20 | 22.1 % | 5,847 | 5.28 p | 2.65 |
| 2020 | 16.43 p | 0.85 | 69.8 % | 5,880 | 7.98 p | 1.75 |
| 2021 | 15.17 p | 0.92 | 65.4 % | 5,870 | 7.11 p | 1.97 |
| 2022 | 19.26 p | 0.73 | 93.6 % | 5,814 | 9.05 p | 1.55 |
| 2023 | 14.84 p | 0.94 | 62.2 % | 5,770 | 6.80 p | 2.06 |
| 2024 | 11.24 p | 1.25 | 18.0 % | 5,868 | 5.07 p | 2.76 |
| 2025 | 12.67 p | 1.10 | 37.0 % | 5,802 | 5.97 p | 2.34 |
| 2026 (partial) | 10.87 p | 1.29 | 14.9 % | 4,227 | 5.20 p | 2.69 |

### USDCHF (c_rt x1 = 1.1 p, min stop = 11.0 p)

| Year | H1 med | ratio H1 | share H1 >= guard | H1 n | M15 med | ratio M15 |
|---|---|---|---|---|---|---|
| 2010 | 22.71 p | 0.48 | 100.0 % | 5,094 | 10.43 p | 1.06 |
| 2011 | 20.47 p | 0.54 | 99.8 % | 5,186 | 9.58 p | 1.15 |
| 2012 | 13.99 p | 0.79 | 88.8 % | 5,748 | 6.73 p | 1.63 |
| 2013 | 13.77 p | 0.80 | 82.7 % | 5,754 | 6.45 p | 1.71 |
| 2014 | 10.49 p | 1.05 | 44.6 % | 5,373 | 4.56 p | 2.41 |
| 2015 | 20.16 p | 0.55 | 100.0 % | 5,171 | 9.23 p | 1.19 |
| 2016 | 14.81 p | 0.74 | 89.9 % | 5,422 | 6.85 p | 1.60 |
| 2017 | 12.99 p | 0.85 | 80.2 % | 5,521 | 6.13 p | 1.80 |
| 2018 | 11.50 p | 0.96 | 58.1 % | 5,847 | 5.62 p | 1.96 |
| 2019 | 9.40 p | 1.17 | 28.1 % | 5,819 | 4.46 p | 2.47 |
| 2020 | 11.31 p | 0.97 | 53.7 % | 5,856 | 5.47 p | 2.01 |
| 2021 | 10.29 p | 1.07 | 37.1 % | 5,874 | 4.90 p | 2.24 |
| 2022 | 15.62 p | 0.70 | 88.8 % | 5,791 | 7.30 p | 1.51 |
| 2023 | 12.59 p | 0.87 | 71.6 % | 5,770 | 5.88 p | 1.87 |
| 2024 | 10.48 p | 1.05 | 42.2 % | 5,838 | 4.83 p | 2.28 |
| 2025 | 10.75 p | 1.02 | 46.5 % | 5,795 | 5.20 p | 2.12 |
| 2026 (partial) | 9.77 p | 1.13 | 31.6 % | 4,225 | 4.65 p | 2.37 |

### NZDUSD (c_rt x1 = 1.4 p, min stop = 14.0 p)

| Year | H1 med | ratio H1 | share H1 >= guard | H1 n | M15 med | ratio M15 |
|---|---|---|---|---|---|---|
| 2010 | 22.97 p | 0.61 | 99.5 % | 3,709 | 10.01 p | 1.40 |
| 2011 | 22.02 p | 0.64 | 98.3 % | 4,813 | 10.03 p | 1.40 |
| 2012 | 15.88 p | 0.88 | 71.3 % | 5,784 | 7.66 p | 1.83 |
| 2013 | 17.11 p | 0.82 | 84.7 % | 5,815 | 8.18 p | 1.71 |
| 2014 | 13.48 p | 1.04 | 45.5 % | 5,600 | 6.50 p | 2.16 |
| 2015 | 17.51 p | 0.80 | 85.0 % | 5,616 | 8.14 p | 1.72 |
| 2016 | 15.83 p | 0.88 | 75.2 % | 5,750 | 7.50 p | 1.87 |
| 2017 | 12.09 p | 1.16 | 24.7 % | 5,707 | 5.73 p | 2.44 |
| 2018 | 10.83 p | 1.29 | 10.5 % | 5,835 | 5.21 p | 2.69 |
| 2019 | 8.77 p | 1.60 | 1.8 % | 5,815 | 4.12 p | 3.39 |
| 2020 | 12.50 p | 1.12 | 35.2 % | 5,836 | 5.95 p | 2.35 |
| 2021 | 12.18 p | 1.15 | 23.9 % | 5,828 | 5.75 p | 2.44 |
| 2022 | 14.99 p | 0.93 | 62.5 % | 5,775 | 7.00 p | 2.00 |
| 2023 | 12.29 p | 1.14 | 25.0 % | 5,750 | 5.72 p | 2.45 |
| 2024 | 9.28 p | 1.51 | 3.6 % | 5,829 | 4.31 p | 3.25 |
| 2025 | 9.49 p | 1.47 | 7.5 % | 5,783 | 4.44 p | 3.15 |
| 2026 (partial) | 9.20 p | 1.52 | 7.8 % | 4,191 | 4.43 p | 3.16 |

---

## 6. Cost-evidence search for AUDUSD / USDCAD / NZDUSD (what was searched, what was found)

Searched (all READ-ONLY, 2026-09-20):

1. `03. EA Developer/*/research/evidence/*spread*evidence*.json` — found only EURUSD
   (`EA_LiquiditySweep`), GBPUSD + USDJPY (`EA_SessionDrive`), USDCHF (`EA_BoundaryEdge`,
   `EA_RollReversion`), USDJPY (`EA_WeekGap`, `EA_SessionMomentum`), XAUUSD
   (`EA_LiquiditySweep`). **No AUDUSD / USDCAD / NZDUSD spread evidence file exists.**
2. `03. EA Developer/*/research/evidence/*slippage*evidence*.json` — same symbol set as
   above (EURUSD, GBPUSD, USDJPY, USDCHF, XAUUSD). **No AUDUSD / USDCAD / NZDUSD slippage
   evidence file exists.**
3. `**/COST_SOURCE_MANIFEST.json` — 6 manifests exist (EA_BoundaryEdge, EA_LiquiditySweep,
   EA_RollReversion, EA_SessionDrive, EA_SessionMomentum, EA_WeekGap); all are for
   USDCHF/USDJPY/EURUSD/GBPUSD/XAUUSD. The per-symbol `_dataacq` manifests
   (`02. AlphaFactory/runs/_dataacq/<SYM>/cost_source_manifest.json`) carry
   `cost_provenance: UNVERIFIED`, `commission: unknown_not_zero`, `slippage:
   unknown_not_zero`, `note: "Data acquisition; no economics."` — not usable as cost
   evidence.
4. `02. AlphaFactory/lab/*` — `labels.py:23-38` defines the v4 per-event cost
   (`spread_cost_arr` = recorded feed spread in pips + 0.7 commission). `results_log.csv`
   has `cost_rt` for the three symbols (11,460 cells each): min 1.0 / median 1.0 / max
   ~4.0–5.2 p. This is **recorded feed spread on event masks, not an all-in p90**, and the
   recorded `sp` field is known corrupt in bursts (`data_plane.py:8-11`, and the
   2026-09-20 GATE-B correction in `04. Memory/research/20260919_...md:244-263`); it is
   cited as supporting context only.
5. `02. AlphaFactory/tools/*cost*` — `measure_cost_evidence.py`,
   `build_research_cost_proxy_evidence.py`, `build_verified_cost_artifact.py`,
   `research_cost_stress.py` and the MTS cost overlays: tooling only; their outputs for
   these symbols are the `_dataacq` UNVERIFIED manifests (3).
6. `04. Memory/research/2026091*COST*.md` — `20260916_COST_PLANE_AUDIT.md` (commission
   bound, demo vs deploy planes) and `20260919_LAB_FALSIFICATION_MAP_AND_COST_REFRAME.md`
   (two cost planes; AUDUSD Dukascopy measurements). The 2026-09-18 day-boundary doc
   reports MQ-Demo tick spreads at 00:00-02:00 server of p50 0.1-0.2 p / p90 0.2-0.3 p
   across the seven majors (`04. Memory/research/20260918_DAY_BOUNDARY_MARKET_PHYSICS.md:77-78`),
   i.e. the same order as the four measured majors — again window-specific and
   spread-only.

Found for AUDUSD: real measured spread on the **Dukascopy** tick plane — "normal ~1.0 p",
week-open first 10 min median 15.6 p / p90 17.3 p
(`04. Memory/research/20260919_LAB_FALSIFICATION_MAP_AND_COST_REFRAME.md:189-190`) and
"Dukascopy AUDUSD RT spread ~1 pip" (`...:376`). This is spread-only, another venue, and
~110 days in 2026 — **not** an all-in research-plane `c_rt`.

Found for USDCAD / NZDUSD: nothing measured. `COST_FEASIBILITY.md:79-81` lists both as
**NOT MEASURED** and `COST_FEASIBILITY.md:271-276` names measuring them as required work
before an economic run.

**Decision (per the task rule):** no sufficient all-in measured `c_rt` exists for the
three symbols, so all three use **1.4 pips, marked `proxy`**, per
`PA_PRO_CHARTER.md:96-98`. The 1.4 p proxy is conservative in the direction of the
program: for AUDUSD it is above the measured Dukascopy spread-alone (~1.0 p) and above
the recorded-feed median; it equals the USDJPY measured value, the widest measured major.

---

## 7. Provenance, assumptions, and caveats

- **`RESEARCH_PROXY` (conservative).** Every manifest in the repo is
  `evidence_tier: RESEARCH_PROXY`, `promotion_eligible: false`
  (`EA_LiquiditySweep/research/evidence/COST_SOURCE_MANIFEST.json:3-9`);
  `COST_FEASIBILITY.md:302-310` (§8) states the p90 construction is the conservative bound
  for the research plane. Live/deploy costs can be lower (deploy plane EURUSD 0.0-0.1 p
  all-day, USDCHF 0.1-0.2 p — `04. Memory/research/20260919_LAB_FALSIFICATION_MAP_AND_COST_REFRAME.md:16-19`),
  but promotion requires the measured venue, not this proxy.
- `ASSUMPTION:` the 3-4 day MQ-Demo tick samples (2026-09-08/11) represent the 2010-2026
  distribution (`COST_FEASIBILITY.md:304-305`).
- `ASSUMPTION:` x1.5/x2 tiers apply the same `c_rt` multiplied, as an adverse shift at
  fill (charter §6); no separate measurement exists for stressed fills.
- Exact per-year shares are computed for x1 only. For x1.5/x2 thresholds, the JSON
  per-year ATR percentiles (`p10,p25,median,p75,p90` in
  `_data_inventory/<SYM>.json`) allow interpolation, but the exact share is `NOT RUN`.
- The cost-geometry guard is a necessary condition, not a promise: a stop can be wide and
  the setup still lose; and the guard says nothing about target geometry (`b`).
- `c_rt` for AUDUSD/USDCAD/NZDUSD must be re-derived from measured evidence before any
  promotion decision on those symbols (per charter §3).
