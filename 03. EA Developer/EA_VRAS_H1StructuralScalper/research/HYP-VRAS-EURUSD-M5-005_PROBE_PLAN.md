# HYP-VRAS-EURUSD-M5-005 — Probe Plan

- **Target**: Validate H1 Structural Scalper EA on EURUSD M5 (2019.01.01 -- 2022.12.31).
- **Execution Mode**: Model 0 Matched Pair (Control vs Challenger) via MT5 Strategy Tester.
- **Data Quality**: FivePercent EURUSD M5, 100% history quality.
- **Outputs Required**:
  - Tester HTML / XML report.
  - Lifecycle v3 reconciliation log (`$0 gap`).
  - Decision Telemetry CSV with 9/9 entry parity.
  - Verification against frozen gates (N >= 350, Cadence 2-5/week, PF >= 1.30, Max DD <= 6%).
