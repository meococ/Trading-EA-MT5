# HYP-STBS-XAUUSD-M15-004 — Existing-run comparator revision

Preregistered at: `2026-08-09T05:50:00Z`

## Question and legal scope

Can a fresh one-shot comparator validate the already completed, exact hash-locked HYP003 Model-0 audit run when JSON permits at most one leading UTF-8 BOM and runtime numeric epochs are compared to oracle UTC while printed timestamps are compared to oracle server time?

HYP004 is a comparator-only engineering child of terminal `HYP-STBS-XAUUSD-M15-003`. It performs no compile, AlphaFactory invocation, MT5 launch, source-data acquisition, order, outcome, performance or economic analysis. It reuses only the exact HYP003 attempt and canonical Alpha run artifacts frozen below. No HYP003 same-ID retry is permitted.

## Frozen identities and inputs

- Hypothesis: `HYP-STBS-XAUUSD-M15-004`.
- Attempt: `STBS004-COMPARATOR-001`, limit one, no retry.
- Parent indicator-parity object: `HYP-ST-XAUUSD-H1-012`.
- Terminal HYP003 raw registry row SHA256: `F7813C1663BA9E14C28CB90227422A612A776743F1634DC1D25C0FE00F97D593`.
- Screened HYP003 authority raw SHA256: `8ECC30240CBD3DC8F66CB89EFF4771CC97980645753A08A3E4C07476EC7B15DD`.
- Packet receipt `03. EA Developer/EA_SupertrendBurstScalper/research/preflight/HYP-STBS-XAUUSD-M15-003/V1/contract_receipt.control.json`, SHA256 `9355A3960D7DBEBD33EE9CF9B86BA8748F45B53C3CC6E2EA0EA76961C64A11D2`.
- Attempt root `03. EA Developer/EA_SupertrendBurstScalper/research/evidence/HYP-STBS-XAUUSD-M15-003/STBS003-MT5-AUDIT-001`:
  - `attempt_started.json`: `9FCEBA75ED34EC3E7C3A290ACD37F8B74098E2034328E6AECEBA987A4177BC03`.
  - `attempt_terminal.json`: `BD0A8C6FCF38982F270DE2E3045E54B038880C629217BE41CBA46D0CB5FE6495`.
  - `alpha_stdout.log`: `2C957E7CF213CDAA2DDBFD571B188EF302620814EF9D9F3F38D2DDAA72ED956A`.
  - `alpha_stderr.log`: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`.
- Failure document `03. EA Developer/EA_SupertrendBurstScalper/research/HYP-STBS-XAUUSD-M15-003_POST_MT5_VALIDATOR_FAILURE.md`, SHA256 `B55AA6972FC19DD8C665E5A525C9F4122C0DCBA14FBBFCA5317925E2ADE4C0B8`.
- Independent failure review `03. EA Developer/EA_SupertrendBurstScalper/research/HYP-STBS-XAUUSD-M15-003_POST_FAILURE_REVIEW.md`, SHA256 `C6419755734EA30BBF1C31A5F78EF378C8BC445CB11E5961C9C15DD2A59DED80`.
- Oracle `03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-003/ST003-ORACLE-001/st003_source_parity_oracle.jsonl`, SHA256 `63E93022794C6DD50EBFB4464DD521D4B1757C5797B158121467F18FF2F13096`.
- Canonical run: `02. AlphaFactory/runs/EA_SupertrendBurstScalper/20260809_123517`.
- Manifest SHA256: `3356D5AEC1A7802029B8D0F8A60D8397E1AF56505C92946B82476D099C5BEFA4` at both `run_manifest.json` and `config/run_manifest.json`.
- Report SHA256: `2CB5425C5827DEC6D81B58BF0DB785B58DD2CCFC169B990AAB3F761FE4D5A591` at both `report.html` and `build/report.html`.
- Journal SHA256: `3D55018CB8E6FACA8E9D397BB642576905DFD970149B9F25F62D20D4BBC35E49` at `logs/tester_journal_delta.log`.
- Summary SHA256: `B42E837D0CD2B2A09CEC0996110F856EA5F0186C0FA8FB415D4F12EE78A769D0` at `analysis/enhanced_summary.json`.
- Source snapshot SHA256: `B7D0092655A602C6619DD277848168F2B926C4F5ADB1311F4DB303AAC771757D` at `snapshot/source/EA_SupertrendBurstScalper.mq5`.
- EX5 snapshot SHA256: `9FFB9894FAD88C754853302B5AE21863A3999622BDEF3C1A2034F152069AE70D` at `snapshot/build/EA_SupertrendBurstScalper.ex5`.
- Config SHA256: `C61B92A196890A7C4144498B8F4F3CA4B5102D6184F4EFD2CDB1A13EA520EEDC` at `config.ini`, `config/config.ini`, and `snapshot/config/config.ini`.
- Overrides SHA256: `4C1A8DD80B5ECA77D15A13E312BE2DEE7B2C0DF8DB50F773E906C62EFF84E1C4` at `overrides.txt` and `config/overrides.txt`.

Every canonical and duplicate run-local path is hash-locked before comparison. Each unique input path is opened exactly once after the durable comparator claim; hashing and parsing use the same captured bytes.

## Frozen parser and clock contract

- JSON artifacts accept zero or one leading byte sequence `EF BB BF`; double/interior BOM, invalid UTF-8, duplicate semantic keys where checked, or malformed JSON fail.
- Journal and oracle text are strict UTF-8 and have no BOM.
- The journal must contain exactly two identical physical copies of every signal and exactly two identical summaries: 1,380 physical signals, 690 unique, raw 690, executable 683, gaps 7, LONG 339, SHORT 344, ATR-ready 683, geometry-ready 683, entries/entry rejects/closes zero, failed false, and no fatal/entry/close/deal record.
- For every raw event, MQL numeric source epoch equals Unix epoch of oracle `time_utc`.
- MQL numeric decision epoch equals Unix epoch of the full oracle row referenced by that event's `next_source_epoch`.
- Printed source and decision strings equal UTC formatting of the oracle server-axis `source_epoch` and `next_source_epoch` respectively.
- Direction, exact-next and gap consumption are exact. Executable geometry reconstructs the inherited direct-MQL5 plan: LONG stop is tick-size floor of `entry - 1.00*ATR`, SHORT stop is tick-size ceiling of `entry + 1.00*ATR`; target is the outward tick-size normalization of `entry +/- 1.50*normalized_stop_risk`. Logged stop/target must match these reconstructed prices within half a point. Volume is proven only positive/readiness-valid; exact 0.25% sizing is not claimed by this comparator.
- Report Orders section is structurally empty; summary is zero-trade/data-acquisition-only; HQ is greater than 97 and the exact manifest/DQ/series-proof contract passes.

The comparison is replayed twice over the same captured byte map and must produce byte-identical report output.

## Verdict boundary

PASS may state only `ENGINEERING_VALID_STBS_MODEL0_SIGNAL_ATR_GEOMETRY_AUDIT_PASS`. It does not establish profitability, PF, expectancy, cost realism, robustness or deployment readiness. Every MT5, compile, trade, outcome, performance, economic, optimization, validation, holdout, promotion, paper and live authority remains false.
