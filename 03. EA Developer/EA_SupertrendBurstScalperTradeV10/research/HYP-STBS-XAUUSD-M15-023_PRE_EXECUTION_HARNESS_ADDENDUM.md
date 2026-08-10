# HYP023 pre-execution harness addendum

Status: FROZEN BEFORE PACKET BUILD

This addendum narrows the HYP023 control plane without changing strategy, risk, cost, data, or acceptance logic.

## Two-stage authority

1. The initial registry row is `state=probe` with authority `PACKET_BUILD_ONLY_NO_EXECUTION_NO_ECONOMICS`.
2. It authorizes only `STBS023-PACKET-BUILD-001` and binds the exact task-packet builder bytes.
3. The builder must claim exclusively and fsync `attempt_started.json` before reading registry or frozen artifacts. It opens the packet with `xb`, writes a terminal on completion/failure, and cannot reuse the same ID.
4. Only an independently reviewed, ordinary `probe -> screened` successor may bind the completed packet/start/terminal and authorize `STBS023-MODEL0-TRAIN-001`.

## Packet-only fail-closed surface

The probe has empty `run_ids`; packet consumed zero; MT5/run-compile attempts consumed zero; model runs, launches, orders, trades, returns and performance trials zero; economics, research validation and holdout unopened. All MT5, compile, trade, collection/comparator, outcome, performance, economics, optimization, validation, holdout, promotion, paper/live, retry, and registry-mutation permissions are explicitly false.

## Frozen package

- Source SHA-256: `4B481CE867DB8A9F9E02AB218FEA50C88FD37A48B8ECB92E2048418DB7F7769B`
- EX5 SHA-256: `4A1639156AB77A8A82CF59A5A65693BFBA751AB9574E6BC4981E70E0BB10AD64`
- Compile log SHA-256: `7A42C5F208DCDD3481009D78ECB34BA34A4C54C032D86A8C02FA98495BB92692`
- Preregistration SHA-256: `24D607EA281C80359C57988E1680DE83BCBAEDD9AC3AE82A5F4226083F04DD26`
- Packet builder SHA-256: `47C12BD3D7E8527C17ED1EEBC1FF41C02C6E3D64DDFF7C1E767FACACDB6F2539`
- Model0 runner SHA-256: `95D211A6CEC5915C3B47B304B932C4F3665F0ECC5048C8A92ED15C10D41FABA5`
- Runner/builder test SHA-256: `0083D488D0E86177BAAC3B430BB0C9034CD5A395EA4AEA7C4790C55BB0DA6EC6`
- `.gitignore` SHA-256: `AB52FF98D7479D29EFA5C324622C77E9929E42939B5C3738C8FFDBB6B6C0B85C`

No optimization, OOS, holdout, Monte Carlo, paper, live, or promotion authority is created here.
