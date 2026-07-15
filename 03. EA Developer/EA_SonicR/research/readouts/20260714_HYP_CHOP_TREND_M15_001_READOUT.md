# Readout — HYP-CHOP-TREND-M15-001 / EA_M15ChopTrend

Date: 2026-07-14 UTC+7  
State: `killed` (Model 0 screen; PF weak; cadence high-side OK; GOAL fail)

## Run

| Field | Value |
|---|---|
| run_id | `20260714_001121` (byte-identical twin `20260714_000557`; same report SHA256 `EDBC9489…F0D2FA`) |
| EA | `EA_M15ChopTrend` |
| Symbol / TF | USDJPY M15 |
| Window | 2021.01.01 – 2025.12.31 |
| Model | 0 |
| Deposit / leverage | 10000 / 100 |
| Spread | tester `current` (not broker-verified cost) |
| History quality | 99% |
| Bars / ticks | 124212 / 123918541 |
| Compile | SUCCESS (0 errors; EX5 present) |
| Receipt SHA256 | `720387C2E06A5E12E1996A7D6CDE449B0D01BC9C1619159DBBC0BA091C1F4E96` |

## Metrics (tester report)

| Metric | Value |
|---|---|
| Profit factor (`Hệ số lợi nhuận`) | **1.08** |
| Total trades (`Tổng số giao dịch`) | **1401** |
| Net profit (`Tổng lợi nhuận ròng`) | **3399.51** |
| Expectancy (`Mức lợi nhuận mong muốn`) | 2.43 |
| Max equity DD | 25.94% |
| Win rate | 42.40% |
| Elapsed calendar weeks | 1825/7 ≈ **260.71** |
| Trades/week (elapsed) | 1401 / 260.71 ≈ **5.37** |

## Verdict

- **Cadence:** 5.37/week is inside prereg band `[1.5, 6.0]` and at/above GOAL upper edge (2–5). Density is not the blocker.
- **Edge:** PF **1.08** is far below GOAL PF>1.30. Scratch-to-weak expectancy after tester friction only.
- **Kill:** close hypothesis. Matches prior ChopRegime-family caution (S629 baseline ~PF 1.12 without day mining). Do **not** mine CI/EMA thresholds, hours, or day filters from this readout.
- **Cost honesty:** missing/zero broker commission/slippage provenance; do not treat this PF as verified after-cost.
- **Ceremony:** `alpha.ps1` closeout threw known `includes_sha256` mismatch after report ready (same class as VOLEXP/TickVol). Artifacts kept under `02. AlphaFactory/runs/EA_M15ChopTrend/20260714_001121/`.

## Independence note

Owner unlimited-GOAL queue ordered empirical Model 0 despite prior twin-fail-closed memo. Screen confirms weak CI+EMA trend edge on USDJPY M15 2021–2025. Not a rescue of TickVol / HourOpen / VolExpansion / carry / fix / Sonic.

## Next (single proposed ID)

1. Close `HYP-CHOP-TREND-M15-001` as killed.
2. Scaffold only (no Model 0 yet): **`HYP-INSIDEBAR-M15-001` / `EA_M15InsideBreak`** — seed `S226/S232 EA_InsideBar` (PF ~1.32–1.65). Path: `03. EA Developer/EA_M15InsideBreak/`.
