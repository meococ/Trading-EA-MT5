# HYP-ICT-FVG-FIDSAFE-EURUSD-M5-004 - final engineering readout

Verdict: **PARKED_PRE_MODEL0_COST_PROVENANCE_FAILED**

## Final build

The ordered ICT/FVG signal and the 1,282-event news guard are unchanged. The
final execution layer preserves cross-day loss streaks, rebuilds lifecycle P&L
by exact position ID, stores the 64-bit ID losslessly, validates actual server
retcodes, counts only actual first entry deals, blocks duplicate pending sends,
uses volume-weighted fill risk and retries emergency closes after restart.

The final fail-safe removes the last approximate recovery path: if persisted
position ID, original stop or planned money-risk budget cannot be bound exactly
after restart, the EA closes the owned position. It never infers initial risk
from TP, a breakeven stop or current equity.

## Evidence

- Source SHA-256:
  `B3367A3D70C26805931473B3F7185A00337231E05A3C3E9DF1A51BDF35D8630E`.
- AlphaFactory compile: **0 errors / 0 warnings**.
- EX5: 76,422 bytes, SHA-256
  `61C8CEB871DC4BE66526CD002DA30F40B103C2B1C15D0723BA4C9A1F2785D4F9`.
- Package tests: **19/19 PASS**, including complete receipt binding.
- Exact-source non-repaint audit V7: **PASS**, zero findings.
- Source/binary receipt V5: SHA-256
  `9BCC5CF3A7A271E46FE650D1CC4CC1BF5FA61F0A35B0A649F84AE96FC56F9618`.

## Economic boundary

No Strategy Tester outcome, trade ledger, PF, expectancy, cadence, drawdown or
holdout data was opened. FivePercent historical spread provenance still fails
because 366,196 of 1,491,312 M1 rows are zero, while verified commission and
direction-aware slippage remain absent. Therefore `model0_authorized=false`,
`promotion_eligible=false`, and the economic verdict is **UNTESTED**.

Verified same-broker spread, at least 30 commission-bearing completed
lifecycles and at least 100 direction-aware fill/slippage observations are the
remaining external unlock. Any future economics requires a fresh child ID.
