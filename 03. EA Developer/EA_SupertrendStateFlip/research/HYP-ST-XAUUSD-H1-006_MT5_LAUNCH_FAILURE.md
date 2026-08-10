# HYP-ST-XAUUSD-H1-006 — terminal telemetry-contract failure

Verdict: `KILL_ENGINEERING_INVOCATION_ADAPTER_TELEMETRY_OVERRIDE_NO_MT5`

The sole `ST006-MT5-001` attempt was claimed and reached AlphaFactory after the
spread-token correction. AlphaFactory then rejected the explicit
`InpEnableTelemetry=false` override because this EA declares telemetry profile
`none`. The source already defaults that input to `false`, and `OnInit` fails
closed if it is ever true, so the override is redundant and illegal at the
AlphaFactory adapter boundary.

Evidence SHA-256:

- attempt start: `0DCE9AA039ED87A0CFE63625791993CEDB9F11C45456F957196FFB533CF3EBD5`
- stdout: `4CA1A19F2624B3A91FEC72AFC84F2780AF40D4386128FD44E500E5ED30106D41`
- stderr: `BFD978E60FCF31630104F1135BECD2E7B96D96815A51E8409AD0DDFFC540AE09`
- terminal: `4F02438076604668CD968A853F6963C71CD6918A90A3A4B4DE3B00F16E29D664`

No run directory, terminal process, history access, common CSV, report, order,
deal, outcome or economic metric was produced. Same-ID retry is forbidden. The
failure radius is only the redundant telemetry override in the outer execution
contract; it does not invalidate the spread fix, MQL source, EX5, oracle,
Supertrend formula or parity thesis.

