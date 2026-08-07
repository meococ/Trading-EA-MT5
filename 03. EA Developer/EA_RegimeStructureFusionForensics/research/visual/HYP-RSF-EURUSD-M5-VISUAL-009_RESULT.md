# HYP-RSF-EURUSD-M5-VISUAL-009 — Result

Status: `PASS_ENGINEERING_VISUAL_PARITY`

- Compile: zero errors.
- AlphaFactory run: `20260807_030104`, completed.
- RunMeta EA identity: `EA_RegimeStructureFusionForensics`, matching manifest.
- Native chart: `NATIVE_MT5_VISUAL009_EURUSD_M5.png`, `603987` bytes,
  SHA-256 `27EBD369D9A83C2E8FF55D7FD0C5E61A007807D1A63E0439DD22BB6BE3351429`.
- Actual MT5 pane header: `QQE MOD 6 5 3 3 close 6 5 1.61 3 close 50 0.35`.
- Visual probe at the frozen smoke bar:
  - mask `255`
  - histogram `18.22055384`
  - trend line `11.67566631`
  - primary RSI `18.22055384`
  - secondary RSI `18.22055384`
  - state `+1`
  - neutral/up/down mirrors `0 / 18.22055384 / 0`
- Native cyan/gray/magenta columns agree with the direct display-handle data.

Verdict: grouped `iCustom` ABI alignment is engineering-valid.  This smoke is
diagnostic only; its single trade and P/L have no economic authority.  The
corrected QQE transport changes the tested implementation, so any new strategy
evaluation must use a fresh hypothesis ID and must not relabel or rescue the
terminal Cell-16 result.
