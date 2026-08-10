# HYP-STBS-XAUUSD-M15-015 — terminal engineering failure

## Verdict

`KILL_JOURNAL_TRUNCATED_AND_DEPOSIT_MARGIN_CONTRACT_INVALID_NO_ECONOMIC_VERDICT`

The sole `STBS015-MODEL0-AUDIT-001` attempt is consumed. AlphaFactory compiled the frozen V4 source, launched MT5 and created run `20260809_233033`, but rejected the run before any accepted performance analysis because the tester journal was truncated at the fixed one-MiB collection boundary.

This is not a low-PF result. HYP015 authorized zero trades and no performance metrics. The report contains no order rows and only the tester-start funding balance deal.

## Exact evidence

- screened authority raw row: `E65477328CC81051D1F183A8336F57961D2AB28C0BB8EC01228689530C3C5BD7`
- attempt start: `B247AF50A24659F3024228E1FC5243790CB0361024C5FC747E92417F6527FF97`
- failed terminal: `1E4C0180BE333E1CBCB7C2156AF78BD6BF67931341BF369F62BE96484086CB88`
- task packet: `F476DCF6D67369184369C8664F533820FA055D3E8D8BDFEE2604B52104672BAA`
- contract receipt: `E164FE998F4C1A92DE2661F018A5F2D24B6243A331BA7AA0C15A4FA84CDD1DC7`
- Alpha stdout/stderr: `90FF8F395AFD6D8D487031B878B24B7E934BC2673294597D21F041F6428DCCD6` / `CC7F16C048DB6F2A4D3F4A00AAD0F133503EB7E566714391F3BF3D3E2DB75DE6`
- run manifest: `40EB0F78C32AAAEF6521FC9685F7DCE61D29520FCFF7F246EF705CC19C646F08`
- report: `6BBCC900C6F8C198A604C5EC17D5341DBCC99C0FC4FEC9A4E660690F6D9168D8`
- truncated journal: `1D2A55F682B646D919551E7F9E536095E2223D3A96A1360EA4228F4E808F5781`
- run compile EX5/log: `4AB3DA39BC82DAFC1ADACA8082B0E7F7D760BA843DA79AD7AB251890CA7EB43E` / `332125A629C31E083DBC810471389BEAA5F365966BE2E86C0E855F419F8B5AF1`, compile result 0 errors and 0 warnings.

The manifest records `files_read=2`, `bytes_read=1048576`, and `truncated=true`. The captured UTF-8 delta is 524,289 bytes and ends during January 2019, so it has no final `STBS_SUMMARY` and cannot prove the frozen full-window counts.

## Second independent blocker exposed before outcome

The truncated evidence contains 161 `STBS_SIGNAL` rows and 1,498 `STBS_MARGIN_CHECK` rows. Every captured exact signal has `margin_ready=false`. The run was frozen with a USD 10,000 deposit while the FivePercent account contract is money-mode margin call USD 92,000 and stop-out USD 90,000. The V4 contract additionally required projected free margin above 1.25 times that threshold, making every positive volume impossible.

Therefore merely increasing the journal budget or suppressing logging would still fail the margin-readiness gate. A fresh child must use the already-established USD 100,000 account class and an account-compatible downward-only volume cap. It may reduce audit-only logging, but it must preserve Supertrend, ATR, entry, SL, TP, holding, Friday and maximum-risk rules.

## Scope

Killed only: HYP015 outer audit invocation with V4, USD 10,000 deposit, the exact V4 money-mode margin threshold and the fixed journal capture. No market edge, PF, expectancy, cost robustness, validation, holdout or deployment conclusion is authorized.

