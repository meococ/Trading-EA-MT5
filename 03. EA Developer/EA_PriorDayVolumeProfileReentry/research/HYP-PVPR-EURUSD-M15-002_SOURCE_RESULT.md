# HYP-PVPR-EURUSD-M15-002 — source result

Verdict: `SCREENED_SOURCE_PASS_MQL5_BUILD_AUTHORIZED`.

- Native FivePercent EURUSD M1, no paid data and no outcomes.
- 2,606,633 design M1 rows; 1,442/1,460 eligible prior-day profiles valid.
- 945 executable signals: 457 LONG / 488 SHORT.
- Exact-next coverage 100%; pooled cadence 2.5900548/week.
- Annual cadence 2.4356–2.7233/week; max-year share 15.03%.
- All source gates passed. Independent read-only review replayed every ledger row
  and returned `PASS_MQL5_BUILD_AUTHORIZED`.

HYP001's earlier float-boundary PASS is invalid and is not used. HYP002 fixes
only the numeric representation with five-digit integer broker points; exact
open equality with VAL/VAH never emits. PF, returns and economic edge remain
unopened until the sole untuned Model-0 baseline.
