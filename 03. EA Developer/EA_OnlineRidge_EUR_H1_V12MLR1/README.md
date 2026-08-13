# EA_OnlineRidge_EUR_H1_V12MLR1

Active `HYP-ORLS-EURUSD-H1-002`: runtime-only fresh identity for the frozen V12-ML EURUSD H1 online RLS design. The sole implementation delta from terminal engineering-invalid HYP001 is `CopyRates need=26` so the ATR24 loop can safely read indices 0..25. No economic logic changed.

DESIGN `[2018-01-01, 2022-01-01)` is authorized. Validation 2022-2023 and holdout 2024-current remain unopened.

DESIGN run `20260812_032000` completed at HQ100 with 1,704 trades, PF `0.924678`, net `-$7,041.14`, DD `9.6378%`. Verdict: `KILL_DESIGN_NEGATIVE_EDGE_OVERTRADING_NO_VALIDATION`. The 2022-2023 validation and 2024-current holdout remain unopened.
