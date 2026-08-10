# HYP-APC-XAUUSD-M15-002 — Engineering/source result

Verdict: `KILL_ENGINEERING_DQ_AND_SOURCE_UNDERFREQUENCY_NO_ECONOMIC_VERDICT`

The sole frozen Model-0 TRAIN attempt completed compilation and produced an MT5 report, but AlphaFactory rejected it before economic acceptance because Strategy Tester History Quality was exactly `97`, while the frozen gate is strictly `>97`.

The engineering revision itself worked as intended:

- D0 M5/M1 availability proof completed.
- Flat completed bars no longer caused a runtime fatal.
- `runtime_failed=false` and no `APC_FATAL` condition was accepted by the earlier reconciled run readout.
- Closed-bar source counts were `raw=103`, `LONG=44`, `SHORT=59`, with `102` accepted entries and one entry rejection.
- Over the frozen `[2010-01-04, 2018-01-01)` window (`417` elapsed calendar weeks), raw cadence was only `0.2470/week`; accepted-entry cadence was `0.2446/week`.

The exact mechanism is therefore far below the required `2–5` executed trades/week even before an admissible economic readout. No PF, PnL, return, optimization, validation or holdout result from this run is admitted or used.

## Immutable run identity

- Run: `02. AlphaFactory/runs/EA_ATRImpulsePullbackContinuation/20260810_200253`
- Source SHA256: `749D403F7FD5713368351FC82AC6E085C12A1D2FE79A88D34A326524C8490C78`
- Prereg SHA256: `3264934750220A26704B979452D2B3CCA06B45150E2869F6BF64B3373EAEBEAE`
- Task SHA256: `B427A535556158104DC9806A14A9417269ED856CD1FDB539DA50E6603D43CCB3`
- Contract receipt SHA256: `E74A4634E617AE6D3D618EAAADF64DE1BCF8D5E93EB4F0A92D04702C98F18D10`
- Run manifest SHA256: `6B28C2FB643C1D33597E86A02E23E0D79B9409302E2086D4A8DCF9EFC36DAE56`
- Tester journal SHA256: `78ABEC61D7766E53352B1A91115EB74D5713CD372A20F186E2C6C5858A621142`
- Report SHA256: `EC4A132DA2F17D1144F9A4F82E6FD8460D0305B852BE50538252E82DA422EFFB`

## Failure radius

This kills only the exact XAUUSD M15 ATR14/EMA50/ADX14 three-bar impulse–pullback–release mechanism and its flat-safe D0 engineering child. It is an engineering-DQ plus structural source-cadence conclusion, not an economic no-edge claim.

No APC003, session/direction filter, relaxed HQ threshold, altered impulse threshold, cooldown deletion, timeframe rescue, or report-derived stop/target change is authorized. The next baseline must use a materially different market mechanism.
