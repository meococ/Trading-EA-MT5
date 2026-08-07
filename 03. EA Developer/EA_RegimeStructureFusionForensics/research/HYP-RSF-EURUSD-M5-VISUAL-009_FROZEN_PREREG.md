# HYP-RSF-EURUSD-M5-VISUAL-009 — Grouped iCustom ABI Parity Smoke

Status: `PREREGISTERED_DIAGNOSTIC_ONLY`

## Frozen delta

VISUAL-008 isolated a positional ABI defect: `input group` declarations consume
positions in MQL5 `iCustom` calls.  QQE group placeholders were omitted, so the
indicator received shifted values and Secondary threshold became `50`.

This follow-up changes only custom-indicator transport fidelity:

1. Parent and visual QQE calls bind the `Primary QQE Settings`,
   `Secondary QQE Settings`, and `Bollinger Bands Settings` group positions.
2. Display-only MBB and TB calls bind every group position that precedes a
   customized display or alert input.
3. The existing closed-bar QQE buffer probe is retained unchanged.

Indicator formulas, source buffers, trading thresholds, risk, sessions and
entry/exit code do not change.  Correcting the parent QQE transport means future
economic testing requires a fresh strategy hypothesis; no old result may be
reclassified or rescued.

## Frozen execution

- EA: `EA_RegimeStructureFusionForensics`
- symbol/timeframe: `EURUSD M5`
- interval: `2019.06.03` through `2019.06.05`
- Model 0; no artificial delay; current spread
- deposit/leverage: `100000 USD`, `1:100`
- Visual Mode required
- smoke timestamp: `1559642100`
- native target: `NATIVE_MT5_VISUAL009_EURUSD_M5.png`

## Acceptance and stop rule

Pass requires zero-error compile, completed wrapper-safe RunMeta, current-run
native PNG import, and direct inspection of the real tester window.  QQE short
name must show the intended sequence `6 5 3 3 close 6 5 1.61 3 close 50 0.35`.
The probe mask must equal `255`; whenever absolute Secondary RSI exceeds `3`,
the main histogram must equal Secondary RSI and exactly one neutral/up/down
mirror must carry that value.  Visible chart columns must agree with the probe.

Any mismatch kills this ID.  This diagnostic authorizes no economic claim,
optimization, validation, holdout access or promotion.
