# HYP-RSF-EURUSD-M5-VISUAL-008 — Native QQE Buffer Probe

Status: `PREREGISTERED_DIAGNOSTIC_ONLY`

## Frozen delta

VISUAL-007 proved that AlphaFactory can import a genuine MT5 Visual Mode PNG,
but lifecycle finalization failed because the included parent engine wrote its
own EA name into RunMeta.  The frame also showed only the QQE trend line.  The
tester `.set` files contain the intended QQE defaults, so parameter staleness is
not accepted as a diagnosis without direct buffer evidence.

This follow-up changes telemetry only:

1. RunMeta derives `ea_name` from `MQLInfoString(MQL_PROGRAM_NAME)` so a wrapper
   and its included parent cannot disagree about the running program identity.
2. Every visual-shot row records the closed-bar values from the exact QQE
   display handle for buffers `0`, `2`, `3`, `4`, `8`, `10`, `11`, and `12`,
   plus a success bit mask.  This distinguishes calculation, warm-up and native
   renderer failures without changing any decision buffer.
3. All twelve QQE inputs are explicit in the task packet to remove tester-profile
   ambiguity.

No entry, exit, risk, session, mode, indicator threshold or parent decision
handle may change.

## Frozen execution

- EA: `EA_RegimeStructureFusionForensics`
- symbol/timeframe: `EURUSD M5`
- interval: `2019.06.03` through `2019.06.05`
- Model 0; no artificial delay; current spread
- deposit/leverage: `100000 USD`, `1:100`
- Visual Mode required
- smoke timestamp: `1559642100`
- native target: `NATIVE_MT5_VISUAL008_EURUSD_M5.png`

## Acceptance and stop rule

Pass requires a zero-error compile, a completed manifest whose RunMeta identity
matches the forensic EA, SHA-256-bound import of the current-run native PNG, and
at least one VisualShots row with a nonzero QQE probe mask.  The frame must be
inspected directly.  Visible histogram columns pass the display lane.  If the
probe contains nonzero histogram/mirror values but no columns are visible, the
result is classified as a native ChartIndicatorAdd rendering defect.  If the
probe values themselves are zero while primary/secondary RSI is live, the next
repair must remain inside QQE calculation/display mapping.

Any failed requirement kills this ID.  This diagnostic authorizes no economic
claim, parameter optimization, validation, holdout access or promotion.
