# HYP-VRAS-EURUSD-M5-006 — Probe Plan

1. Red-first static contract tests must fail before the new MQL5 source exists.
2. Implement one package containing both frozen arms behind `InpUseVolatilityNormalizedStop`.
3. Require tests, warning-free compile, closed-bar/non-repaint audit, canonical contract validation, and SHA-bound screened registry state.
4. Run control then challenger once, serially, in Model 0 on the frozen window.
5. Reconcile MT5 report net P/L to complete lifecycle-v3 deals. Missing SL/TP deal logging invalidates the economics.
6. Compare absolute and relative frozen gates. Robustness/WFA/Monte Carlo are permitted only after valid base economics exist; they cannot rescue a failed base or relative gate.
7. Produce a delivery verdict of pass, killed, or blocked. Never promote or trade live from this diagnostic pair.

