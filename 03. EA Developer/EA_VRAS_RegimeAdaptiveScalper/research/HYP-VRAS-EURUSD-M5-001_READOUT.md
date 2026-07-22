# HYP-VRAS-EURUSD-M5-001 - invalid engineering readout

## Verdict

`INVALID_ENGINEERING_RUN_NO_ECONOMIC_VERDICT`.

The bound Model-0 run `20260722_102241` completed at 100% history quality on
298,267 M5 bars and 79,411,093 ticks, but opened zero trades. Profit factor,
win rate and expectancy are therefore undefined.

## Evidence and failure radius

- Signal engine produced 2,546 entry attempts.
- 1,052 were rejected by session/news/spread/daily guards.
- 1,016 were rejected by the frozen K=8 cost-distance gate.
- 478 reached `OrderCheck()` and were all rejected by EA logic.
- Root cause: HYP-001 compared `MqlTradeCheckResult.retcode` with
  `TRADE_RETCODE_DONE/PLACED`. A successful `OrderCheck()` returns boolean
  `true` and normally leaves check retcode at zero; DONE/PLACED belong to the
  subsequent `OrderSend()` result.

The same incorrect check also prevented safety/time exits. This is a mechanical
execution defect, not evidence for or against the VRAS market hypothesis.
HYP-001 is terminal and must not be rerun. HYP-002 may correct only this API
usage while preserving the exact signal, risk, session, cost and data surface.

## Bound artifacts

- Run: `02. AlphaFactory/runs/EA_VRAS_RegimeAdaptiveScalper/20260722_102241`
- Report SHA256: `0CBD172CEC0D1AE46EFDBECFEA8D9CD1B4C55B6592086CFA6FBEB1C4BDC1A948`
- Source SHA256: `ED9DC425E766F0083EDBBD9634B8381C6D8BA23FF1AA4B673A70E3D3EC2D8889`
- Decision telemetry SHA256:
  `EE134DC0FFDF011C26B2C163C3BCC4F37802DCF74B971BC980B9994C8B0C961F`

Cost/news provenance remains diagnostic-only and promotion is prohibited.
