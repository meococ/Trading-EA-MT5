# HYP-STBS-XAUUSD-M15-008 — Model0 timeout failure

Status: `FAIL_ENGINEERING_TIMEOUT_NO_ECONOMIC_READOUT`

## Exact attempt

- Attempt: `STBS008-MODEL0-TRAIN-001`
- Attempt start SHA256: `B095C136EEACEE67584BD3C83F3B529AC2C12F813EE2FA9623D43BE5241F3BE0`
- Attempt terminal SHA256: `1E897BAD80927339A051A1B97BE2AEFA4B3E88A3C20E7CC9850D314976BD3F80`
- Alpha stdout SHA256: `F5457D01F31F8E0BFC7C4229B47AC8D87725AA093ED654AA497DB1ED5B12ACB9`
- Alpha stderr SHA256: `92B199FE6A663BE3F04D515E8EE8B4458507630083B269F91F342596DA2716B0`
- Run directory: `02. AlphaFactory/runs/EA_SupertrendBurstScalperTrade/20260809_153656`
- Run-scoped source SHA256: `2E0501CC0C19A8FD8418242A0EC64D725EBC14425AD7A1718F9FEB444B977E32`
- Run-scoped EX5 SHA256: `7FF08B11523DE136DB961F1466FDE27BD5314ABB0B8162A775DDD5D685611848`
- Run-scoped config SHA256: `77700AD8D6F830DA9713902423258F283296B03852F70DDC1913A4EB281B0A25`
- Tester-agent log SHA256 at collection: `A6CE806EB760E1F487C20F415EDE71ACA4DCE8B08289A38AE54EE520E0E137D2`
- Exact 36-line run slice: `research/evidence/HYP-STBS-XAUUSD-M15-008/STBS008-MODEL0-TRAIN-001/tester_journal_exact_slice.log`, SHA256 `2C77B2057C21F2A1D0A286C740F9AEE3236D082151CD106E9F6900024EE6A638`
- Reversible original compile-log archive: `research/evidence/HYP-STBS-XAUUSD-M15-008/STBS008-MODEL0-TRAIN-001/compile_log_original_utf16le.b64`; decoding produces exactly 3,164 bytes with SHA256 `5FA42A36372DA0F591CF145F5AD9DF379824185FA6653355BAC4E294B024CCAB`

The sole attempt started the exact sealed source on `XAUUSD/M15`, `Model=0`, `2005.01.01–2023.01.01`, compiled a fresh non-empty EX5, and initialized successfully. AlphaFactory then returned exit code 1 at `2026-08-09T09:07:02Z` with `Backtest failed: timeout after 1800s`.

## Run-local evidence

The exact tester-log segment is 36 lines. Its decisive records are:

```text
15:36:59.919 expert file added: .../20260809_153656/EA_SupertrendBurstScalperTrade.ex5
15:37:00.080 testing ... from 2005.01.01 00:00 to 2023.01.01 00:00 started
15:37:00.116 DATA_EPOCH_D0_SERIES_PROOF ... m5_first_epoch=1086938100 ... m1_server_first_epoch=1086938100 ...
15:37:00.120 STBS_INIT|hypothesis=HYP-STBS-XAUUSD-M15-007|audit=false|h1_last=2004.12.30 18:00:00|state=UP|exec_state=0
16:07:02.031 prepare for shutdown
16:07:02.033 test .../20260809_153656/... thread finished
```

Within that exact segment:

- `STBS_SIGNAL=0`
- `STBS_REQUEST_RESULT=0`
- `STBS_DEAL=0`
- `STBS_SUMMARY=0`
- `STBS_FATAL=0`
- trade/order/deal records attributable to this run: `0`

No `run_manifest.json` or report file was produced. The last logged simulated timestamp is the 2005 initialization record and no DESIGN event was observed; the log does not prove the tester's unlogged internal progress timestamp. The orphaned local `metatester64.exe` process from this timed-out run was identified by exact executable path/PID and stopped after AlphaFactory had already written the failure terminal; it was then verified absent.

## Failure radius

This result closes only the exact HYP008 execution attempt under the preregistered 1,800-second runtime budget. It establishes that the trade-enabled source is too slow under full `2005–2023` Model0 every-tick generation to produce a complete baseline within that budget.

It does **not** establish low PF, negative expectancy, bad cadence, bad risk, or lack of market edge. No outcome/economic result exists and no HYP008 retry is authorized.

## Technical diagnosis and next lane

The audit-only parent processed the same `2005–2023` clock in about 71 seconds. The trade-enabled source calls execution reconciliation and persistent-intent handling on every synthetic tick even while flat and before the design window. A fresh engineering child may preserve the exact indicator, signal, ATR, risk, exit and economic contracts while adding a fail-closed flat-state lifecycle fast path and a separately frozen runtime budget. Merely relaunching HYP008 or interpreting the timeout as an economic result is forbidden.
