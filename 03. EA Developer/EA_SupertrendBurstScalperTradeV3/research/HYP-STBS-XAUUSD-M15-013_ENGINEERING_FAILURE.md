# HYP-STBS-XAUUSD-M15-013 engineering failure

Verdict: `KILL_ENGINEERING_PRE_COST_DATA_IDENTITY_AND_BROKER_STOPOUT_NO_ECONOMIC_VERDICT`

The sole authorized attempt `STBS013-MODEL0-TRAIN-001` is consumed. The run compiled with zero errors and MT5 produced a report, but it is not economic evidence and its displayed `PF=0.00, N=1` must not be used.

Two independent engineering failures occurred:

1. The run manifest emitted base `data_fingerprint=077437E0038B40FEDB8AC611CAFE410B2FF8D0A90A742F0C52336F728D8C0BF4`, while the frozen packet required `B326D511C805C7998DF1C2FC540770B6EC3054D0D4BCBB41A5A4E3C2E4239D25`. The research loop stopped before verified-cost construction and unified economic validation.
2. The only position was a 0.15-lot SHORT opened at 2018-01-03 05:00 server time. The tester immediately emitted `position stop out triggered at 1269.75$` on the next M15 bar, closed the broker position, and stopped 72% before the requested horizon. Lifecycle telemetry contains one OPEN and zero CLOSE rows; RunMeta incorrectly reports `runtime_failed=false` with `exec_state=OPEN` at deinitialization.

The run therefore proves neither low PF nor no edge. It exposes an execution-safety defect: `OrderCalcMargin <= free margin` and `OrderCheck retcode=0` are insufficient for this broker's high stop-out level. A legal fresh child must preserve the frozen signal, ATR, stop, target and maximum 0.25% risk, but add descending step-wise volume selection using projected margin/free/margin-level, broker stop-out mode/levels and predeclared headroom. A minimum lot that cannot satisfy the contract must be skipped. It must also detect stop-out deals, reconcile forced closes at deinit, mark runtime failure, and bind the observed data fingerprint without reading economic outcomes for tuning.

## Bound evidence

- attempt start: `02. AlphaFactory/runtime/model0_economic_attempts/HYP-STBS-XAUUSD-M15-013/STBS013-MODEL0-TRAIN-001/attempt_started.json`, SHA256 `FE35004BF0F88EB2F2E470EE9885CC996179BE76671CD61473BD745C66951FBB`
- attempt terminal: `02. AlphaFactory/runtime/model0_economic_attempts/HYP-STBS-XAUUSD-M15-013/STBS013-MODEL0-TRAIN-001/attempt_terminal.json`, SHA256 `A31F6B9B8DE89311C60AC8462F719B2564BA41225CB1E064F74755DEBB115004`
- run manifest: `02. AlphaFactory/runs/EA_SupertrendBurstScalperTradeV3/20260809_212445/run_manifest.json`, SHA256 `ED17A648C584E2147F8117DCB4C1CDAFD36A8C7D28C93BAD7EA8E7A183BD4E8D`
- report: `02. AlphaFactory/runs/EA_SupertrendBurstScalperTradeV3/20260809_212445/report.html`, SHA256 `6709BE640B22FEFFC62C8CCAB1BAA43BA1E467EBCFDA556443CC9B4F5A5A56FE`
- tester journal delta: `02. AlphaFactory/runs/EA_SupertrendBurstScalperTradeV3/20260809_212445/logs/tester_journal_delta.log`, SHA256 `4123C1C0FE174CA12FFECCCA046C14347B64AF9E74AF61E02EDEA759CBA9EDDE`
- RunMeta: `02. AlphaFactory/runs/EA_SupertrendBurstScalperTradeV3/20260809_212445/logs/XAUUSD_RunMeta_HYP-STBS-XAUUSD-M15-013_339609125.json`, SHA256 `06C08A3CFBF13277B38FE0583B1D25CD5FAB86A59E4431B67CE09B3641EF4B10`
- lifecycle CSV: `02. AlphaFactory/runs/EA_SupertrendBurstScalperTradeV3/20260809_212445/logs/XAUUSD_LifecycleTrades_HYP-STBS-XAUUSD-M15-013_339609125.csv`, SHA256 `3C98A4381C34EB724EB40DE86518D25662EABA035DAC3B06D5883A9FFD016569`
- inadmissible enhanced summary: `02. AlphaFactory/runs/EA_SupertrendBurstScalperTradeV3/20260809_212445/analysis/enhanced_summary.json`, SHA256 `5A8EF30557EE31BEFEF7639BF865D3B4AC734963136FA87592FCB2B809138AC9`

No verified cost artifact, unified baseline verdict, optimization, validation, OOS, holdout, paper or live stage was opened.
