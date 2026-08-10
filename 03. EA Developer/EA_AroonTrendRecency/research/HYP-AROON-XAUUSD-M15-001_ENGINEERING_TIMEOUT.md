# HYP-AROON-XAUUSD-M15-001 — Engineering Timeout

Verdict: `PARK_ENGINEERING_TIMEOUT_BEFORE_SOURCE_REPORT_NO_ECONOMIC_VERDICT`

The sole source-feasibility attempt was claimed at `2026-08-10T03:10:03.585158Z` and the external shell terminated the analyzer with exit code `124` after approximately 124 seconds.

Immutable evidence:

- attempt ID: `AROON001-SOURCE-ATTEMPT-001`
- attempt-started SHA256: `E2F0D692D0A0602E8C04200205C1ACAEBCB2900FAFD738253D275A3CD38AFE7E`
- authorized analyzer SHA256: `6E2383CE15074890905AFC6AAF2E6D0D9893FBDE8B414850F28F12A08F100CF0`
- authorized registry row SHA256: `4914132842B5DA8F0734A61A75B1B6EEBBF3141C8F644C4BF57DD436B47694D6`
- registry snapshot SHA256: `245199A6704C21CD7F67745779B3EA668F6A85CD694E5451B6B90F010A36B2DF`

The evidence root contains only `attempt_started.json`. No source report, event ledger, receipt or terminal was created. The source may have been opened after the claim, but access stage is not durably known; therefore `source_opened` is recorded as unknown and `source_scan_completed=false`.

No source gate, event count, cadence, trade, return, PnL, profit factor, validation or holdout result exists. This failure says only that the row-by-row aggregation implementation did not finish inside the execution budget.

Same-ID retry is forbidden. A fresh child may change only aggregation implementation performance while preserving the complete-triplet contract, Aroon formula, signal, source, windows and gates.
