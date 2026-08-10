# HYP-KVO-EURUSD-M15-002 — ENGINEERING FAILURE

- Verdict: `KILL_ENGINEERING_RUNTIME_FAIL_AND_POST_REPORT_COLLECTION_RACE_NO_ECONOMIC_VERDICT`
- Run identity: `EA_KlingerPullback/20260810_203959`
- Frozen source SHA256: `F9A0EA48EC8EF0CCA95D4AF258E54DC90675EA733166EB8EAFE31EB8996AAFEF`
- Run EX5 SHA256: `C7F69311878A5C0A6F05257D939D9C0AF1B48BC07BF6F8F1D793002926C12E2F`
- Config SHA256: `72243D122CE8A71065FCA07C501C9FFC62118283863977D415156A1B850882C0`
- Raw tester report SHA256: `9975BC92BEF1013EA166891476308659300C12DAE6EDA3E86F68742679819DCB`
- Tester agent log SHA256 at review: `13E7F1BEC5E4E33CB80D4732E5A3749C050652C71124B0212AFFF4D2123A4689`

## Exact failure radius

MT5 completed the Model-0 test and wrote the native report, but the EA terminal summary was not engineering-valid:

- `closed_bars=197804`
- `raw=9524`, `long=4798`, `short=4726`
- `entries=31`, `rejects=9482`, `closes=1`, `clock_rejects=11`, `invalid=0`
- `runtime_failed=true`

The first runtime failure was an entry request rejected with `TRADE_RETCODE_MARKET_CLOSED` at 2010-02-16 00:00. The implementation marked every rejected `OrderSend` as a fatal runtime error, so all later signals were blocked. This is an execution-state defect, not evidence about the market edge.

Separately, after the report appeared and `/ShutdownTerminal` exited normally, AlphaFactory attempted to stop the original PID. Its identity had already disappeared or been reused, so the old cleanup path raised `process identity changed` before collecting the run manifest and report into the run directory.

No PF, expectancy, return, validation, OOS, holdout, optimization, or deployment conclusion is admissible from this attempt. Same-ID retry is forbidden. A fresh child may preserve the frozen KVO signal/risk thesis while changing only rejected-entry reconciliation and using the independently fixed post-report PID cleanup.
