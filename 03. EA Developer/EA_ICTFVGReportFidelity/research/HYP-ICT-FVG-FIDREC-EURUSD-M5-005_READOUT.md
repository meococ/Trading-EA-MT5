# HYP-ICT-FVG-FIDREC-EURUSD-M5-005 - final engineering readout

Verdict: **PARKED_PRE_MODEL0_COST_PROVENANCE_FAILED**

## Final implementation

The ordered report-fidelity signal, sessions, thresholds, news guard and trade
geometry are unchanged. The completed execution layer now:

- preserves cross-day loss streaks and peak-equity state;
- binds original risk to a losslessly persisted 64-bit position ID;
- rebuilds full lifecycle net P&L from broker deal history;
- classifies every lifecycle idempotently with a persisted last-classified ID;
- replays a missed offline SL/TP close using the actual final-deal timestamp;
- recounts unique actual entry position IDs for the current UTC day;
- validates server retcodes, blocks duplicate pending sends and counts only the
  first actual entry deal;
- retries excess-fill-risk emergency closes after restart; and
- fails closed when position/risk or missed-close history cannot be proven.

## Evidence

- Source: 52,368 bytes; SHA-256
  `C6A05F4124029A38A7FC80B83D8697B6B58E87CF3FAEDD9FD53BE43DA87522E2`.
- AlphaFactory compile: **0 errors / 0 warnings**.
- EX5: 76,798 bytes; SHA-256
  `EEC0E1435C42BAF1C53A1677451107488CDB2D20717BE2C6020F54BB4535728E`.
- Package tests: **20/20 PASS**, including exact receipt binding and offline
  reconciliation invariants.
- Exact-source non-repaint V8: **PASS**, zero findings.
- Receipt V6 SHA-256:
  `FBA629D8EC472DD592D6CB07FDD929E91F1AA39BDBD8B4EDAC59AD482705569E`.

## Economic boundary

No Strategy Tester outcome, trade ledger, PF, expectancy, cadence, drawdown or
holdout was opened. The same-broker cost gate remains failed: 366,196 of
1,491,312 historical M1 spread rows are zero, and verified commission plus
direction-aware slippage are absent. The strategy's economic verdict remains
**UNTESTED**; `model0_authorized=false`, `promotion_eligible=false`.

Verified same-broker spread, at least 30 commission-bearing completed
lifecycles and at least 100 direction-aware fill/slippage observations are the
remaining external unlock. Any later economics requires a fresh child ID.
