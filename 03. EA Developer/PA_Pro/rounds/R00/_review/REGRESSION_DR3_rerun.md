# R00 — MANDATORY REGRESSION: frozen DR3 through the PA-PRO referee

- Round: R00 · family `REGRESSION_DR3` (legacy flats) + `REGRESSION_DR3_CORRECTED` (x1 only)
- Split: DESIGN 2016-01-01..2021-12-31 (frozen loaders, READ-ONLY) · EURUSD M5 · cost tiers gross/x1/x1.5/x2
- Frozen detector records: 91734 · accepted (executable): 4331 · matched subset: 4216 · random entries: 84320 · matcher parity vs frozen module: PASS (bit-identical)
- Engine: `pa_fill.simulate` (legacy_flats=True reproduces `vpa_econ1_sim.py:53-160`); metrics: `pa_metrics.compute`; ledger: `pa_ledger.append` (one line per tier and component).

## 1. Verdict table — ours vs ECON-1 (x1 primary)

| metric | ECON-1 target | ours (legacy x1) | match |
|---|---|---|---|
| N fills | 2436 | 2436 | YES |
| WR | 0.3017 | 0.301724 | YES |
| PF | 0.795 | 0.795195 | YES |
| b | 1.839 | 1.83923 | YES |
| exp R | -0.1385 | -0.138542 | YES |
| total R | -337.5 | -337.487 | YES |
| max DD % | 84.19 | 84.1919 | YES |
| exit mix TP/SL/DAILY/FRIDAY/MIDNIGHT/DATA_END | 617/1618/139/61/1/0 | 617/1618/139/61/1/0 | YES |
| status counts | {"CANCELLED": 165, "EXPIRED": 1708, "FILLED": 2436, "VETO_FRIDAY": 22} | {"CANCELLED": 165, "EXPIRED": 1708, "FILLED": 2436, "VETO_FRIDAY": 22} | YES |

Full table (all tiers), ours:

```
tier        N      WR     PF      b     expR      Rtot  maxDD% |     rN     rWR    rPF  lift pp               CI
gross    2436 0.3498  0.992  1.842  -0.0051    -12.37   38.96 |  42257 0.3456  0.971    +0.44 [-1.49,+2.41]
x1       2436 0.3017  0.795  1.839  -0.1385   -337.49   84.19 |  42257 0.2994  0.783    +0.24 [-1.61,+2.14]
x1.5     2436 0.2837  0.720  1.819  -0.1950   -474.90   91.81 |  42257 0.2758  0.695    +0.83 [-0.98,+2.70]
x2       2436 0.2697  0.667  1.807  -0.2373   -578.05   95.03 |  42257 0.2552  0.625    +1.49 [-0.29,+3.34]
```

ECON-1 x1 reference: N=2436 WR 30.17% PF 0.795 b 1.839 exp -0.1385 R -337.5 maxDD 84.19%.

Matched random (ours):

| tier | N | WR | PF | b | exp R |
|---|---|---|---|---|---|
| gross | 42257 | 0.3456 | 0.971 | 1.8375 | -0.0182 |
| x1 | 42257 | 0.2994 | 0.783 | 1.8316 | -0.1479 |
| x1.5 | 42257 | 0.2758 | 0.695 | 1.8248 | -0.2152 |
| x2 | 42257 | 0.2552 | 0.625 | 1.8219 | -0.2733 |

Target random x1: N 42257, WR 29.94%, PF 0.783, b 1.832, lift +0.24pp CI [-1.61, +2.14].

## 2. Per-year (legacy x1) vs ECON-1 §4

| year | target N | ours N | target WR | ours WR | target PF | ours PF | target R | ours R |
|---|---|---|---|---|---|---|---|---|
| 2016 | 408 | 408 | 0.294 | 0.2941 | 0.802 | 0.802 | -56.5 | -56.4 |
| 2017 | 422 | 422 | 0.287 | 0.2867 | 0.757 | 0.757 | -71.0 | -71.0 |
| 2018 | 444 | 444 | 0.331 | 0.3311 | 0.956 | 0.956 | -12.9 | -12.9 |
| 2019 | 378 | 378 | 0.320 | 0.3201 | 0.840 | 0.840 | -39.0 | -39.0 |
| 2020 | 375 | 375 | 0.261 | 0.2613 | 0.617 | 0.617 | -101.8 | -101.8 |
| 2021 | 409 | 409 | 0.313 | 0.3130 | 0.791 | 0.791 | -56.4 | -56.4 |

## 3. Flats policy: legacy quirk vs corrected (x1)

| policy | strategy N/WR/PF/R | FRIDAY exits | status VETO | random N/WR/PF | lift pp (CI) |
|---|---|---|---|---|---|
| legacy (dow==4 = Thursday) | 2436/0.3017/0.795/-337.5 | 61 | {"CANCELLED": 165, "EXPIRED": 1708, "FILLED": 2436, "VETO_FRIDAY": 22} | 42257/0.2994/0.783 | +0.24 [-1.61,+2.14] |
| corrected (real Friday 20:00) | 2440/0.3082/0.815/-303.4 | 61 | {"CANCELLED": 165, "EXPIRED": 1708, "FILLED": 2440, "VETO_FRIDAY": 18} | 42313/0.3007/0.788 | +0.76 [-1.10,+2.67] |

## 4. DIFFERENCES (every semantic difference, explained and quantified)

1. **Friday policy.** `legacy_flats=True` reproduces the frozen quirk: the weekday formula `((t//86400)+4)%7` is Sunday=0, so `dow == 4` fires on **Thursday** 20:00 server (ECON1_RESULTS §6.2). The referee's default (`legacy_flats=False`) uses the correct calendar (Monday=0), plus a Saturday/Sunday veto/flat. Table §3 quantifies the difference at x1; the regression acceptance table uses the LEGACY policy so it is bit-comparable with ECON-1.
2. **PF when the gross loss is 0.** The frozen `vpa_econ1_sim.metrics` returns `float('inf')`; `pa_metrics` returns `None` (charter section 6). No tier in this regression has a zero gross loss (all PF finite), so the difference does not bite here.
3. **Exit-mix labels.** The frozen engine has no WEEKEND reason; the corrected policy adds one (never reached while the daily 22:00 flat is active). Legacy exits are labelled identically (DAILY before FRIDAY, MIDNIGHT last).
4. **Metrics addition.** `t of mean R`, per-symbol, split-half, trades/week, top-5% share, largest-year share are new referee fields with no ECON-1 counterpart; they do not change the reproduction.
5. **Random rows with an out-of-session signal bar** contribute no matched rows (frozen G3 rule) — reproduced; the lift uses the matched subset (4216/4331).
6. **Costs.** The engine applies `c_rt(symbol) * tier` pips as an adverse fill shift; EURUSD c_rt(x1)=1.0 pip (COST_FEASIBILITY.md:75), identical to the frozen default `cost_rt_pips=1.0`. gross=0.0, x1.5=1.5, x2=2.0.
7. **Rounding.** No numeric rounding is applied inside the engine (raw float64 compares); the table shows metrics rounded for display only. `lift_pp`/CI are rounded to 2 decimals like the frozen run.

## 5. Ledger

- legacy trials: T000011, T000012, T000013, T000014, T000015, T000016, T000017, T000018
- corrected trials: T000019, T000020
- `pa_ledger.verify()` PASS (the script prints the verified chain).
