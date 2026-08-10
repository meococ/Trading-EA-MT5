# HYP-STBS-XAUUSD-M15-003 — Post-MT5 validator contract failure

Recorded at: `2026-08-09T05:47:04Z`  
Verdict: `KILL_POST_MT5_VALIDATOR_BOM_AND_CLOCK_AXIS_CONTRACT_NO_ECONOMICS`

## Exact failure radius

The sole `STBS003-MT5-AUDIT-001` attempt passed its registry, packet, reservation and bound-file gates. AlphaFactory compiled the unchanged hard audit-only EA, started MT5, produced the report and verified zero-trade data collection. The frozen validator then failed while reading `analysis/enhanced_summary.json` with plain UTF-8 because the file begins with one UTF-8 BOM. No HYP003 success receipt exists and same-ID retry is forbidden.

The first failure masked a second comparator-contract defect. The frozen journal comparator compared MQL runtime numeric epochs to the oracle's server-axis `source_epoch`. Across the 690 unique events, that produces expected broker-offset differences: `-7200` seconds for 269 rows and `-10800` seconds for 421 rows. This is not a signal-time divergence. Exact dual-axis reconciliation gives zero mismatches:

- MQL numeric `source_epoch` equals Unix epoch of oracle `time_utc`: `690/690`.
- MQL numeric `decision_epoch` equals Unix epoch of the full oracle row referenced by `next_source_epoch`: `690/690`.
- Printed source and decision timestamps equal the oracle server-axis `source_epoch` and `next_source_epoch`: `690/690` each.
- Direction and exact-next classification mismatch count: `0`.

## Run evidence

Outer screened authority raw SHA256: `8ECC30240CBD3DC8F66CB89EFF4771CC97980645753A08A3E4C07476EC7B15DD`.

Attempt root `03. EA Developer/EA_SupertrendBurstScalper/research/evidence/HYP-STBS-XAUUSD-M15-003/STBS003-MT5-AUDIT-001`:

- `attempt_started.json`: `9FCEBA75ED34EC3E7C3A290ACD37F8B74098E2034328E6AECEBA987A4177BC03`.
- `attempt_terminal.json`: `BD0A8C6FCF38982F270DE2E3045E54B038880C629217BE41CBA46D0CB5FE6495`.
- `alpha_stdout.log`: `2C957E7CF213CDAA2DDBFD571B188EF302620814EF9D9F3F38D2DDAA72ED956A`.
- `alpha_stderr.log`: empty, SHA256 `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`.

Canonical Alpha run: `02. AlphaFactory/runs/EA_SupertrendBurstScalper/20260809_123517`.

- `run_manifest.json`: `3356D5AEC1A7802029B8D0F8A60D8397E1AF56505C92946B82476D099C5BEFA4`.
- `report.html`: `2CB5425C5827DEC6D81B58BF0DB785B58DD2CCFC169B990AAB3F761FE4D5A591`.
- `logs/tester_journal_delta.log`: `3D55018CB8E6FACA8E9D397BB642576905DFD970149B9F25F62D20D4BBC35E49`.
- `analysis/enhanced_summary.json`: `B42E837D0CD2B2A09CEC0996110F856EA5F0186C0FA8FB415D4F12EE78A769D0`.
- `snapshot/source/EA_SupertrendBurstScalper.mq5`: `B7D0092655A602C6619DD277848168F2B926C4F5ADB1311F4DB303AAC771757D`.
- `snapshot/build/EA_SupertrendBurstScalper.ex5`: `9FFB9894FAD88C754853302B5AE21863A3999622BDEF3C1A2034F152069AE70D`.
- `snapshot/config/config.ini`: `C61B92A196890A7C4144498B8F4F3CA4B5102D6184F4EFD2CDB1A13EA520EEDC`.
- `config/overrides.txt`: `4C1A8DD80B5ECA77D15A13E312BE2DEE7B2C0DF8DB50F773E906C62EFF84E1C4`.

The manifest binds HYP003, XAUUSD M15, Model 0, `2005.01.01` through `2023.01.01`, sole override `InpAuditOnly=true`, telemetry `none/off`, exact receipt/source/EX5/config/report hashes, HQ `98`, full coverage, non-truncated journal and passing M5 `CopyTime` proof. The report Orders section is exactly empty. Alpha stdout records compile success with a 33,830-byte EX5 and zero compile errors; there is no run-local compile log, so this object makes no independent zero-warning claim.

## Signal-only reconciliation

The journal contains 1,380 physical signal records as two identical copies of each of 690 unique events and two identical summaries. Counts reconcile exactly: raw `690`, executable `683`, gaps `7`, LONG `339`, SHORT `344`, ATR-ready `683`, geometry-ready `683`, entries `0`, closes `0`, fatal/trade records `0`. The BOM-tolerant zero-trade summary is semantically valid and has `n_trades=0`, `performance_metrics_authorized=false`; report orders are empty.

This evidence is engineering/data-collection only. No returns, PF, expectancy, costed economics, optimization, validation, holdout, paper or live claim was opened. A fresh comparator-only child may reuse these exact hash-locked artifacts without another MT5 run.
