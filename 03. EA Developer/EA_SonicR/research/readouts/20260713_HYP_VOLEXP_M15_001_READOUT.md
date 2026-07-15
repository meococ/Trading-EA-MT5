# Readout — HYP-VOLEXP-M15-001 / EA_M15VolExpansion

Date: 2026-07-13 / 2026-07-14 UTC+7  
State: `killed` (Model 0 screen; PF near-breakeven; cadence OK; GOAL fail)

## Run

| Field | Value |
|---|---|
| run_id | `20260714_000211` |
| EA | `EA_M15VolExpansion` |
| Symbol / TF | USDJPY M15 |
| Window | 2021.01.01 – 2025.12.31 |
| Model | 0 |
| Deposit / leverage | 10000 / 100 |
| Spread | tester `current` (not broker-verified cost) |
| History quality | 99% |
| Bars / ticks | 124212 / 123918541 |

## Metrics (tester report)

| Metric | Value |
|---|---|
| Profit factor (`Hệ số lợi nhuận`) | **1.01** |
| Total trades (`Tổng số giao dịch`) | **741** |
| Net profit (`Tổng lợi nhuận ròng`) | **126.50** |
| Max equity DD | 14.36% |
| Win rate | 40.76% |
| Elapsed calendar weeks | 1825/7 ≈ **260.71** |
| Trades/week (elapsed) | 741 / 260.71 ≈ **2.84** |

## Verdict

- **Cadence:** inside GOAL band 2–5/week (2.84). Density is viable.
- **Edge:** PF 1.01 is only scratch expectancy after tester friction — far below GOAL PF>1.30. Not a research-pass survivor.
- **Kill:** close hypothesis. Do **not** mine RV thresholds, hours, or day filters from this readout.
- **Cost honesty:** missing/zero broker commission/slippage provenance; do not treat this PF as verified after-cost.
- **Ceremony:** `alpha.ps1` closeout threw the known `includes_sha256` mismatch after report ready (same class as cadence-book `20260713_234653`). Artifacts under `02. AlphaFactory/runs/EA_M15VolExpansion/20260714_000211/` remain usable for screen readout. Compile earlier proved **0 errors** / EX5 present.

## Independence note

Near-miss seed was `S639 / EA_VolCluster` (PF~1.21). Independent of killed hour-open-break, carry/COT, fix/session, and Sonic Classic. Transfer preserved cadence but did not deliver GOAL edge.

## Next (single proposed ID)

1. Close `HYP-VOLEXP-M15-001` as killed.
2. Next independent screen if ChopTrend is already the active lane:
   **`HYP-INSIDEBAR-M15-001` / `EA_M15InsideBreak`** — seed `S226/S232 EA_InsideBar`
   (PF ~1.32–1.65). Otherwise continue coordinator queue `HYP-CHOP-TREND-M15-001`.
   Not hour-open, not vol-expansion, not tick-vol, not carry/fix/Sonic.
