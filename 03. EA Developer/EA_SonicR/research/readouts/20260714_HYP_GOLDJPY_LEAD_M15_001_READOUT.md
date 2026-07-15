# Readout — HYP-GOLDJPY-LEAD-M15-001 / EA_M15GoldJPYLead

Date: 2026-07-14 ICT  
State: `killed` (Model 0 screen; PF below 1.00; cadence OK; GOAL fail)  
Process: `GPT_DEEP_RESEARCH_WAIVED / LOCAL_SELF_RESEARCH_ONLY`

## Run

| Field | Value |
|---|---|
| run_id | `20260714_001343` |
| EA | `EA_M15GoldJPYLead` |
| Symbol / TF | USDJPY M15 (gold context `XAUUSD`) |
| Window | 2021.01.01 – 2025.12.31 |
| Model | 0 |
| Deposit / leverage | 10000 / 100 |
| Spread | tester `current` (not broker-verified cost) |
| History quality | 99% |
| Bars / ticks | 124212 / 123918541 |

## Metrics (tester report)

| Metric | Value |
|---|---|
| Profit factor (`Hệ số lợi nhuận`) | **0.97** |
| Total trades (`Tổng số giao dịch`) | **931** |
| Net profit (`Tổng lợi nhuận ròng`) | **-710.49** |
| Expected payoff | **-0.76** |
| Max equity DD (relative) | 16.85% |
| Elapsed calendar weeks | 1825/7 ≈ **260.71** |
| Trades/week (elapsed) | 931 / 260.71 ≈ **3.57** |

## Verdict

- **Cadence:** inside/near GOAL band (3.57/week ≥ 1.5; within 2–5).
- **Edge:** PF 0.97 and negative expectancy — fails GOAL PF>1.30 and screen floor PF≥1.00.
- **Kill:** close hypothesis. Do **not** mine gold ATR thresh, hours, Mon+Thu-only, skip-h16, or add CI from this readout.
- **Cost honesty:** missing/zero broker commission/slippage provenance; do not treat this PF as verified after-cost.
- **Ceremony:** `alpha.ps1` closeout threw known `includes_sha256` mismatch after report ready (same class as VOLEXP/HourOpen). Artifacts kept under `02. AlphaFactory/runs/EA_M15GoldJPYLead/20260714_001343/`. Compile **0 errors** / EX5 present.

## Independence note

Near-miss seed was `S673 / EA_GoldJPYInverse` (PF~1.26). Transfer used Mon–Thu NY `[15,18)` a priori, no CI, no S676 hour mining. Independent of killed ChopRegime/ChopTrend, HourOpenBreak, VolExpansion, TickVolImpulse, carry/COT/bond.

## ChopTrend check

`HYP-CHOP-TREND-M15-001` remains **FAIL_CLOSED** twin of ChopRegime `KILL_FAMILY` — do not rescue. (A parallel agent may have attempted Model 0; intake denial still stands.)

## Next (single proposed ID)

1. Close `HYP-GOLDJPY-LEAD-M15-001` as killed.
2. Next independent screen meeting local near-miss filter (PF>1.15 and ~≥1.5 trades/week, unlocked):
   **`HYP-SPARK-ASIAN-M15-001` / `EA_M15AsianRangeBreak`** — seed `S111 / EA_Spark` USDJPY M15 (PF ~1.26, ~71/yr ≈ 1.37/week). Not InsideBar (cadence ~0.3/week fails dual filter). Not GoldJPY/Chop/HourOpen/VolExp/TickVol rescue.
