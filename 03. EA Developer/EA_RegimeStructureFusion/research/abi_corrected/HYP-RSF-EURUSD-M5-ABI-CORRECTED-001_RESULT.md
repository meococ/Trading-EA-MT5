# HYP-RSF-EURUSD-M5-ABI-CORRECTED-001 — terminal result

## Verdict

`KILL_SAME_BAR_FUSION_NEGATIVE_EXPECTANCY`

Correcting the QQE positional `input group` ABI improved the parent control, but it did not create a positive edge. The same-bar decision mechanism is terminal and must not be rescued by weekday, hour, direction, route, or threshold filtering under this hypothesis ID.

## Immutable run

- AlphaFactory run: `02. AlphaFactory/runs/EA_RegimeStructureFusion/20260807_042332`
- Window/model: EURUSD M5, 2018-01-01 through 2022-12-31, Model 0
- Source SHA256: `F467D953809029E96FE4A8382ED79AC6DC81F10C242FC5C8F2FD112DBA215859`
- Report SHA256: `92399653BC825F3036FD51665AABF9E75FC8DC112625BF551CB3ADF4E67860A7`
- EX5 SHA256: `5D15F59F8229BCAEA0CB39EF87E27184B82BED973DD3B3D5E4B661BCDE51CF4B`
- Data fingerprint: `C86447BB9D3C637FEF2FF810C8A1D3AE08D27B27B990966A07E6E476F2F3C7D3`
- Compile: 0 errors; non-repaint audit: PASS
- Five indicator dependencies are source-hash-bound in the run manifest.

## Economic result

| Metric | Result | Gate |
|---|---:|---:|
| Trades | 720 | 2–5/week target |
| Net | -5,238.92 USD | > 0 |
| Profit factor | 0.8516 | >= 1.30 |
| Win rate | 41.4% | diagnostic only |
| Expectancy | -7.28 USD/trade | > 0 |
| Max drawdown | 5.51% | <= 8% |

The loss is broad: 2018–2021 are negative and 2022 remains slightly negative (PF 0.986). Europe PF is 0.89 and New York PF is 0.75. Friday and isolated routes are not eligible rescue evidence because they were observed after the full-window result.

## Route attribution

| Route | Trades | Net USD | PF |
|---|---:|---:|---:|
| BREAKOUT_LONG | 107 | -402.42 | 0.912 |
| BREAKOUT_SHORT | 118 | -47.05 | 0.989 |
| RANGE_LONG | 18 | -528.59 | 0.360 |
| RANGE_SHORT | 33 | +471.10 | 1.340 |
| TREND_LONG | 212 | -5,135.90 | 0.603 |
| TREND_SHORT | 232 | +403.94 | 1.036 |

These route values explain the failure radius; they do not authorize disabling losing routes under the same ID.

## Harness note

The MT5 report and lifecycle sidecars completed successfully. The outer research loop then stopped while building the report-bound cost artifact because the supplied research-proxy spread CSV contains rows outside the run window. No cost-stress or promotion claim is made. Since raw PF is already below 1, that post-report failure cannot reverse the kill decision.

## Authorized successor boundary

A fresh hypothesis may test temporal sequencing because native losing-trade charts showed repeated entries on the setup/extension bar without a later structural reclaim or sufficient runway. It must preserve both directions, the session profile, risk size, stops, target RR, and indicator parameters during its first attribution run.
