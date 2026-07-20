# MT5 PLAN - HYP-LSS-OB-REPL-MT5-EURUSD-M15-002

Status: FROZEN 2026-07-18 before source creation, compile, or MT5 Strategy
Tester outcome for this child.

## 1. Owner override and scope

- Owner correction in the active task: `phải backtest bằng mt5`.
- Parent `HYP-LSS-OB-REPL-EURUSD-M15-001` remains terminal at the offline
  cadence frontier. It is not reopened or relabeled.
- This child changes delivery routing only: implement the same frozen rules as
  a canonical MQL5 EA and run two real MT5 Strategy Tester Model-0 variants.
- Purpose: implementation/fidelity plus diagnostic economic readout. This is
  not a post-hoc strategy rescue, optimization, promotion, or live authority.

## 2. Bound identity

- Source report SHA256:
  `8F3EE339C52B7271CC9382DE21379E8C35C0D1646CEF133D1050D083FEC19223`.
- Parent prereg SHA256:
  `7F051DE01B89E6A41A01B0C7EC023ED7435AF74420EA2E6D89AB9348279C26BD`.
- Parent density SHA256:
  `70447FB1D97AFDF4EDBCF8E630D334A51D3655AE9124D7BE4CC58D315390963D`.
- Parent native-MT5 parity SHA256:
  `4E916DE8AE800262CFF9C98D0DF38030D786D7BE9B929BAFE6E34A5397054694`.
- Requirement matrix SHA256:
  `9EE82A981FB536E35F5F6737A7ADE8D6146AD3CE5CD377B1A1849A48C924E9E8`.
- FivePercent EURUSD M1 SHA256:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- News CSV SHA256:
  `80B9DE46517B42F8B1D9A3ACCEFA6CC6D3DCB4DD06CAE357F16DE46228C64307`.

## 3. Frozen strategy surface

- EURUSD M15 decisions; closed bars only.
- H1 latest strength-2 confirmed pivot break supplies persistent BOS bias.
- H4 uses UTC-anchored custom aggregation from closed M15 bars; latest
  confirmed high/low must bracket price. Long <=50% midpoint; short >=50%.
- M15 sweep of the latest confirmed strength-2 pivot from the preceding 20
  bars, with wick through and close back inside.
- Within the next 3 M15 bars, directional body >=1.8 x closed `iATR(14)` and a
  strict three-bar FVG.
- Last opposite candle before displacement is the OB; body must overlap FVG.
  Stop uses the farther adverse sweep/OB wick plus 1.5 pip.
- Stop distance must be 8-12 pip. TP=2R. No partial, break-even, trailing,
  optimization, or parameter amendment.
- Challenger: first overlap retest within 12 bars and same UTC session;
  directional engulfing OR body/range >=0.60 with directional outer-25% close.
- Control: same context/sweep/displacement/OB/stop/risk/common guards, enters
  on the first quote after displacement close without waiting for retest.
- Closed M15 `iADX(14)>25`; UTC sessions `[07:00,10:00)` and `[13:00,16:00)`.
- Hash-bound EUR/USD high-impact news blackout is inclusive +/-30 minutes.
- Risk 0.25% equity/trade; one owned position; <=2 trades/day; daily stop
  -1.5%; peak-equity stop -8%; cooldown 120 minutes after 2 consecutive losses;
  spread <=1.8 pip; flatten at 21:45 UTC.

## 4. Fixed MT5 runs

- EA: `EA_LSSOBPropScalper`.
- Symbol/timeframe: `EURUSD`, `M15`.
- Window: `2019.01.03` through `2022.12.31`; 2023+ remains unopened.
- Model: `0` only.
- Deposit: 100,000 USD; leverage 1:100.
- Trial family N=2 only:
  - control: `InpSignalMode=0`;
  - challenger: `InpSignalMode=1`.
- All other inputs identical. No rerun with changed signal/time/session/RR/asset.

## 5. Evidence and interpretation

- Required: package tests, compile 0 errors/0 warnings, fresh EX5, exact-source
  non-repaint PASS, source/binary receipt, two MT5 reports/run manifests,
  lifecycle-v3 sidecars, report analysis and `validate-full` attempt.
- Costs are explicitly unverified: FivePercent historical spread provenance is
  failed and commission/direction-aware slippage are absent. Tester/current
  spread is a diagnostic simulation, never evidence that real cost is zero.
- Zero trades is a valid MT5 backtest outcome and must be reported as zero
  trades; PF/WR/expectancy are undefined, not fabricated.
- Any failure of cadence/economics/stability keeps terminal KILL. A numerical
  pass still cannot exceed `PARKED_DIAGNOSTIC_SURVIVOR` because cost/news and
  producer-validation promotion boundaries remain unresolved.
