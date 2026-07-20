# HYP-ICT-FVG-FIDNEWS-EURUSD-M5-002 — build readout

Verdict: **PARKED_PRE_MODEL0_COST_PROVENANCE_FAILED**

## What is implemented

- Ordered EURUSD M5 report-fidelity FSM: sweep/reclaim, displacement plus
  strict FVG, fresh OB/FVG overlap, closed-M15 MSS, first 50-70% retest,
  rejection and closed-M15 ADX >25.
- Fixed prop/risk controls: 0.25% risk, 1.5% daily stop, 8% account drawdown,
  two trades/day, two-loss cooldown, 2R target, +1R/+0.5R stop tightening and
  22:00 UTC flattening.
- Hash-bound high-impact news guard: 1,282 timed EUR/USD events over 209
  consecutive weekly pages, UTC-converted, binary-search blackout +/-30
  minutes, fail closed outside 2019-2022.
- Lifecycle-v3 telemetry with news source SHA and rejection counts.

## Verification

- Contract/data tests: **13/13 PASS**.
- AlphaFactory compile: **0 errors, 0 warnings**, EX5 70,080 bytes.
- Main source SHA-256:
  `8BABF2EEE803638E0832D2B6DAFBFA2E6FE6F3E88C24307CFCAE8D0E6D927BE3`.
- EX5 SHA-256:
  `B1603F15D5AFA111ED41AEC7B1BAC73FB70C8F1E27F068EF4DF8100232D27A92`.
- Receipt:
  `research/evidence/20260718_SOURCE_BINARY_RECEIPT_V3.json`.
- Non-repaint audit:
  `research/evidence/20260718_NONREPAINT_AUDIT_V3.json`.
- Registry validator: `CANDIDATE_REGISTRY_OK rows=77 hypotheses=30`.

No Strategy Tester outcome, PF, expectancy, drawdown, cadence or trade ledger
was opened for this child. The 2023+ holdout remained sealed.

## Why Model 0 stopped

The read-only FivePercent EURUSD export returned 1,491,312 M1 rows, but 366,196
rows (24.5552909%) report zero spread. The exported spread column is therefore
not acceptable cost evidence. There are also no >=30 verified same-symbol
commission lifecycles and no >=100 direction-aware slippage observations.

AlphaFactory requires verified historical spread even for an explicitly
non-promotable research proxy, and permits that proxy only for a control
bootstrap—not the frozen control/challenger comparison. Bypassing this would
make the economic result invalid, so the run stopped before outcome.

## Honest strategy conclusion

Architecture fidelity is materially stronger than the old unordered
`EA_FVGConfluence`, which remains terminal killed. Economic edge, cadence and
superiority versus similar EAs or professional traders remain **UNTESTED** for
this exact build. The source-C news calendar and compile success do not imply
profitability.

## Reopen condition

A new child hypothesis—not either terminal ID—may be opened only after binding:

1. same-broker historical EURUSD spread with a passing zero/missing-value audit;
2. >=30 verified round-turn commission lifecycles or an authoritative broker contract;
3. >=100 direction-aware slippage/fill observations;
4. a fresh source/include/EX5 receipt and frozen task packets for both arms.
