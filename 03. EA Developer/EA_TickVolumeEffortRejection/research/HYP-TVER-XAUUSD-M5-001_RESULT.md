# HYP-TVER-XAUUSD-M5-001 — Source Feasibility Result

Date: 2026-08-09  
Attempt: `TVER001-SOURCE-ATTEMPT-001`  
Verdict: `PARK_SOURCE_FEASIBILITY_EXACT_TVER_MAPPING`

## Result

The sole frozen outcome-blind attempt completed and its deterministic replay matched byte-for-byte. It materialized only XAUUSD M5 bars in the UTC design window 2018–2022 and emitted no future-price or economic field.

| Gate | Result | Pass |
|---|---:|:---:|
| Design rows | 351,303 | yes |
| Feature coverage | 99.8941% | yes |
| Exact-next-M5 coverage | 99.6330% | yes |
| Candidates | 141 (minimum 500) | no |
| Cadence | 0.540526/week (required 2–5) | no |
| LONG / SHORT | 79 / 62; 56.03% / 43.97% | yes |
| Maximum year share | 34.04% (maximum 30%) | no |
| Every-year cadence | 0.249–0.921/week (minimum 1.25) | no |

The funnel contained 13,154 high-effort bars, 374 low-progress bars and 141 final completed-bar rejection candidates. Data quality and direction balance are adequate, but the exact conjunction is too sparse and unstable by year to justify implementation.

## Decision

Do not relax RV10, ATR, wick, close-location, cadence or year gates; do not add a session/direction filter; do not rerun this ID; do not build its MQL5 indicator/EA and do not open economics, validation or holdout.

Failure radius is only the exact FivePercent XAUUSD M5 2018–2022 `RV10 >= 2.00`, range/prior-ATR14 `<= 0.80`, symmetric wick-rejection mapping. No economic edge was evaluated.

Canonical evidence is under `research/evidence/HYP-TVER-XAUUSD-M5-001/TVER001-SOURCE-ATTEMPT-001/`. Independent post-failure review is `PASS_PARK`.

