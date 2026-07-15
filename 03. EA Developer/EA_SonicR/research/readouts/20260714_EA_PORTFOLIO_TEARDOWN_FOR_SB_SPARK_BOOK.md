# Tear-down — legacy EA_Portfolio for SB+Spark book lane

Date: 2026-07-14  
Owner mandate: iterate / teardown-rebuild OK  
Hypothesis: `HYP-SB-SPARK-BOOK-001`

## Decision

`03. EA Developer/EA_Portfolio/` (v1.0, 2026-04-05) is **not** the research
scaffold for the near-GOAL SB+Spark book.

## Why teardown (not reuse)

| Module in legacy portfolio | Current shelf status |
|---|---|
| Cobra / CBR XAUUSD | Outside Phase-0 SB+Spark universe; not this lane |
| ITSM | Parked PF 1.16; offline Spark+ITSM and SB+Spark+ITSM **FAIL** |
| LondonNY / LNY | Closed / not SB+Spark |
| InsideBar | **Killed** |
| SilverBullet | Valid sleeve, but wired inside contaminated multi-sleeve host |

Offline option matrix V1 killed/parked every expansion that adds ITSM / London /
NY / PDH into the SB+Spark book (pooled PF dilutes below 1.30 or cadence breaks).

Reusing the legacy host would re-introduce killed sleeves by default toggles and
mix risk budgets that were never frozen for `HYP-SB-SPARK-BOOK-001`.

## Replacement scaffold (this campaign)

1. **Dual-instance compose** — keep `EA_SilverBullet` + `EA_M15SparkAsian` as
   separate EX5; offline join on exact run IDs (capital-normalized).
2. **Do not compile** `EA_Portfolio` for this hyp.
3. A future clean `EA_SBSparkBook` may be built only after:
   - Spark Deposit=100000 capital twin Model 0 lands,
   - a priori weight/overlap options remain survivors,
   - Owner accepts research-scaffold compile (still not Real-confirmed).

## Integrity

- No files deleted from `EA_Portfolio/` (evidence preservation).
- Tear-down = **lane ban + do-not-compile**, not destructive cleanup.
- Phase 0 contamination on `HYP-PORTFOLIO-COMPOSE-001` remains uncleared;
  `HYP-SB-SPARK-BOOK-001` is the clean child path.
