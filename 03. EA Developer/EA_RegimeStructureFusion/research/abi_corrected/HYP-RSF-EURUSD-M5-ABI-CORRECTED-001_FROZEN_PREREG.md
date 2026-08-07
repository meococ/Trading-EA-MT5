# HYP-RSF-EURUSD-M5-ABI-CORRECTED-001 Frozen Preregistration

Frozen before reading any economic output from the corrected QQE implementation.

## Purpose

Measure the same-bar Cell16 decision logic after fixing the QQE `iCustom`
positional ABI. This is a control, not a parameter rescue and not a candidate
for promotion. Its only purpose is to separate the effect of the implementation
bug from the economic weakness of the strategy mechanism.

## Immutable identity

- Parent: terminal `HYP-RSF-EURUSD-M5-BLOCK1-001`, Cell16.
- EA source SHA-256: `F467D953809029E96FE4A8382ED79AC6DC81F10C242FC5C8F2FD112DBA215859`.
- Compile checkpoint: MetaEditor `0 errors`; EX5 size 95,440 bytes.
- AIRD source SHA-256: `C432AEF3BF7EC93EC8A64BD2806C115E71F822B2DCB438DAC22590FB978EB475`.
- VRC source SHA-256: `EB81B1426CBDAF3143F553388A213E2BB5A3E33E05433991918CC5977273A087`.
- MBB source SHA-256: `AC5DB6E1DDA825F6A3535E9AB1E4C9956086C7AF590E2672C71CF03D8F4E54FE`.
- TB SMC source SHA-256: `489B6E6B74C4FCA6624B510DC9FF38FDBBDA0584C007B8FFEE3D8339D1CB879E`.
- QQE source SHA-256: `86876D352762F6C107BC4AC886C04E901C9345C68A5C7E68C73A33696F13053F`.
- The only intended decision-path delta from the terminal parent is the QQE
  handle signature: the three MQL input-group strings are supplied in their
  actual positional slots. No threshold or trading parameter is changed.

## Frozen test contract

- Symbol/timeframe: EURUSD M5; M15 AIRD/VRC context.
- Development window: 2018-01-01 through 2022-12-31.
- Tester: Model 0 / every tick; execution mode 0; delay 0.
- Account: 100,000 USD, leverage 1:100.
- Sessions: London plus London/New York overlap (`InpManualSessionMask=6`),
  resolved by the EET/EEST broker-clock profile.
- Modes: range, trend and breakout (`InpManualModeMask=7`).
- Decision stack: AIRD/VRC + MBB + TB SMC + QQE all enabled.
- Risk, stops, reward/risk, cooldown, max-hold and protection controls remain at
  source defaults.
- Cost evidence: tester current-spread request plus report commission/swap. This does
  not constitute dynamic-slippage validation.
- Required telemetry: lifecycle-v3 trade log plus RunMeta.

Exact overrides:

`InpEnableTelemetry=true;InpExpectedSymbol=EURUSD;InpHypothesisId=HYP-RSF-EURUSD-M5-ABI-CORRECTED-001;InpMagic=5867311;InpManualModeMask=7;InpManualSessionMask=6;InpProfileMode=1;InpResearchAutoMode=true;InpUseContextRouter=true;InpUseQqeTiming=true;InpUseTbStructure=true;InpVariantTag=ABI_CORRECTED_SAME_BAR_CONTROL`

## Evaluation and stop rule

Report whole-window net profit, PF, trade count, trades/week, drawdown, win rate,
mean net R and route-level PF. Reconcile exactly one final close per position.

- The run counts as one family economic trial.
- Do not search parameters, hours, directions, weekdays or subsets.
- Do not read 2023-2025.
- If PF is below 1.30 or expectancy is non-positive, mark this same-bar control
  terminal and proceed only under the preregistered new temporal mechanism.
- Even if PF exceeds 1.30, this control cannot become promotion-ready because
  dynamic slippage, CPCV/DSR, WFA and untouched validation are absent.
