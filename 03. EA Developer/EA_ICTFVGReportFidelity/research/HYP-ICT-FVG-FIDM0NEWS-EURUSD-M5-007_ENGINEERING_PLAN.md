# HYP-ICT-FVG-FIDM0NEWS-EURUSD-M5-007 - frozen news-calendar runtime repair

Status: **FROZEN BEFORE SOURCE/INCLUDE REPAIR OR ANY VALID TESTER OUTCOME**

## Parent preflight evidence

- Parent: `HYP-ICT-FVG-FIDM0-EURUSD-M5-006`.
- Parent control attempt: AlphaFactory run `20260719_003953`.
- The attempt is not a valid strategy outcome: MT5 stopped in `OnInit` with
  `Historical news guard calendar failed validation; fail closed.` It produced
  history quality `n/a`, zero bars, zero ticks, no RunMeta and no lifecycle
  sidecar. No signal, trade or economic outcome was evaluated.
- Root cause frozen before repair: the raw/CSV corpus contains 1,282 distinct
  event IDs but only 869 distinct UTC timestamps because several legitimate
  high-impact events can share one release time. The EA time-only calendar
  stores all 1,282 timestamps while `NewsCalendarValid()` correctly requires a
  strictly increasing array for binary search.

## Legal engineering delta

- Preserve the raw evidence and CSV at 1,282 events and their existing hashes.
- In `build_news_calendar_artifacts.py`, generate the MQL5 time-only array from
  sorted unique UTC epochs. The expected generated count is 869, with 413
  same-time event rows collapsed only in the execution lookup array.
- Add build-audit metrics for event rows, unique calendar timestamps and
  collapsed same-time rows. The audit remains source rank `C`, diagnostic-only
  and `promotion_eligible=false`.
- Change canonical EA source only for embedded hypothesis identity/version;
  signal, risk, execution, sessions, news-window behavior and parameters stay
  unchanged.
- Update the receipt builder identity to this child. CONTROL and CHALLENGER
  preset files and their hashes remain unchanged.

## Verification and execution contract

- Red-first tests must prove the old generated include has duplicate adjacent
  timestamps and that the repaired builder emits a strictly increasing 869-row
  lookup array while retaining 1,282 CSV event rows.
- Rebuild the include/audit, run all package tests, compile 0/0, rerun the
  exact-source non-repaint audit and issue a new source/binary receipt.
- Then run exactly one sequential Model-0 pair on EURUSD M5, 2019.01.01 through
  2022.12.31, deposit 100000: control `InpSignalMode=0`, then challenger
  `InpSignalMode=1`. No optimization, parameter change, rerun or 2023+ access.
- Diagnostic costs remain 1.5/2.25/3.0 pip round trip. Historical spread,
  commission-lifecycle and direction-aware slippage provenance remain failed;
  every result remains `promotion_eligible=false`.
- Challenger gates remain: at least 300 trades; 2.0-5.0 trades per elapsed
  week; PF at 1.5 pip >=1.60; PF at 2.25 pip >=1.25; PF at 3.0 pip >=1.00;
  max drawdown <=8%.

The invalid parent run cannot be used as a matched control or performance
observation. A valid child control must complete with real ticks and both
lifecycle-v3 sidecars before the challenger is allowed to start.
