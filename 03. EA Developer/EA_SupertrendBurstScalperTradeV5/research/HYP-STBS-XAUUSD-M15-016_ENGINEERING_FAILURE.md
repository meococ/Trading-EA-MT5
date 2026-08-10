# HYP-STBS-XAUUSD-M15-016 — pre-compile receipt override failure

## Verdict

`KILL_HARNESS_UNNORMALIZED_OVERRIDE_RECEIPT_PRECOMPILE_NO_MT5_NO_ECONOMIC_VERDICT`

The sole `STBS016-MODEL0-AUDIT-001` attempt is consumed. AlphaFactory rejected the execution receipt before compile, MT5 launch, source-data access, report creation, orders, deals, returns or economic analysis.

## Exact failure

The runner passed a semantically valid but non-canonical override string. The receipt bound that original order, while `Resolve-TelemetryTierOverrides` for telemetry profile `none` normalizes the override map by sorting keys before AlphaFactory compares the invocation to the receipt.

The only ordering difference is inside the account-risk inputs: the runner placed `InpPercentStopoutHeadroomFactor` before the two `InpMoney*` keys; AlphaFactory's canonical order places the `InpMoney*` keys first. The values, MQL source and intended tester contract were not changed.

AlphaFactory stopped with:

`Contract receipt binding 'overrides' does not match the alpha invocation.`

Run-directory delta was exactly `0 -> 0`. The canonical EX5 and compile log remained byte-identical to the reviewed static artifacts.

## Bound evidence

- authorized registry row: `852EBE8283E03C4DB72FC9959C0466A37BC0793292E061C1FD30E447FAF82BAF`
- attempt start: `4A697136DD7A241D99430665B1FA65F7A94540419C5457E2BB19A1AE76D4A5F8`
- task packet: `AD75263E27AE0272D0866FF108413E7C6367BE9201906063FEB35274B7F376B7`
- contract receipt: `7B32BEA632907C302B9CE57CE89EA179A1B4A93C5AFB58D285E9EF4DFBEAAA2F`
- Alpha stdout: `AB5FB3E3F4AB7E0CF3AF72DC92686E62AA3848AC4DAEA2BB9A2427053E7C9117`
- Alpha stderr: `A264A3664CC01B6EA28E246E6DCB173B7862A95474A90B416DE4AF8BED9E1FC4`
- attempt terminal: `140B4F53906C54C894CDB45C16668D8EE8C0377E2E3FD455D7918D5C11807DD4`
- reviewed/run-captured EX5: `691D215558F56DEDAB37EA142955243B0A22F0A51E6435E8D86CBEF4E3603968`
- reviewed/run-captured compile log: `5A7C3A3C7D5FE286E88A76CC72D33C3470B2115B8997C347D8EE5AD61100B53B`

## Failure radius

This kills only the HYP016 outer receipt/invocation mapping. It says nothing about Supertrend signal correctness, account-safe margin readiness, trade expectancy, PF, robustness or deployability.

A continuation, if independently ratified, must use a fresh outer hypothesis and attempt ID, keep the exact V5 MQL/inner HYP016 identity unchanged, bind the terminal HYP016 row and failure evidence, and freeze the same override values in AlphaFactory's canonical sorted order before its sole run.
