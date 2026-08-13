# HYP008 engineering failure receipt

- Attempt: `EVENTDEPTHTRANSFER008-MODEL0-PRIMARY-001`
- AlphaFactory run directory: `02. AlphaFactory/runs/EA_EventDepthTransfer/20260813_104115`
- Tester reached report-ready state, but the mandatory data-quality gate failed:
  `MT5 journal delta requires one distinct D0 series proof for 'EURUSD'; found 0.`
- Journal evidence: two exact-symbol history synchronization lines and zero
  `DATA_EPOCH_D0_SERIES_PROOF` records.
- Frozen report SHA-256: `1E73029FDCD2EC0157C4EBC27561AA59B9957C6C49CDD0174428C1913AF0E607`.
- Frozen trade ledger SHA-256: `BE4A998D1580B295BF52602B0B094712C4F3634EBDF98D01A9C0AA588B318E0E`.
- Frozen run-meta SHA-256: `53E0D07B68DFB7217D497EC35AEF4036739B368BA6311FD5F93F0B61ED0BBE48`.
- Frozen journal SHA-256: `30EE4A7DEF73E3480812658968FF71F22021FC1885CA4D59EF5725EC472CA5F3`.

No report, ledger PnL, return, PF, drawdown or trade outcome was inspected. The
artifacts are hash-preserved but economically inadmissible. HYP008 consumed its one
PRIMARY attempt; REVERSE was not run. A successor may add only the missing canonical
D0 proof while keeping source table, signal, timing, sizing, cost and gates unchanged.

