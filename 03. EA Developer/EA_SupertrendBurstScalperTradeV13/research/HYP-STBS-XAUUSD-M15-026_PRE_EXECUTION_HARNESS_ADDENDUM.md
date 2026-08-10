# HYP026 pre-execution harness addendum

Status: FROZEN BEFORE HYP026 PROBE OR PACKET BUILD

This addendum repairs only the post-claim self-rejection that terminalized HYP025 and closes the launch claim before bound-artifact reads. It does not change the inherited V12 strategy logic, numeric inputs, data, costs, risk, acceptance gates or four-MiB journal contract.

## Outer and inner identities

- Outer registry, task, receipt, attempt and Alpha run-manifest identity: `HYP-STBS-XAUUSD-M15-026`.
- Inner MQL5 override, lifecycle and RunMeta identity: `HYP-STBS-XAUUSD-M15-026`.
- EA/source: identity-only clone `EA_SupertrendBurstScalperTradeV13`, SHA-256 `F60A9469D1A6FE2D62F5E83DECB953862C68AF9E3D154EA0AE488C072B4A4DA4`.
- Magic and variant are `5604126` and `STBS_H1_FLIP_M15_BURST_TRADE_V13_POSTCLAIM_RECONCILE`.

All identity surfaces must equal HYP026: Alpha invocation, exact MQL5 override, RunMeta, lifecycle sidecars, task packet, contract receipt, run manifest and attempt chain. The generic verified-cost builder is intentionally unchanged and must reject any outer/inner identity divergence.

## Two-stage authority

1. The initial HYP026 row is `state=probe`, authority `PACKET_BUILD_ONLY_NO_EXECUTION_NO_ECONOMICS`.
2. It authorizes only `STBS026-PACKET-BUILD-001`; every compile, MT5, trade, outcome, performance, economics, validation, holdout and deployment permission is false.
3. The builder creates and fsyncs an exclusive start before reading frozen inputs, writes the task packet exclusively, and emits a COMPLETE or FAILED terminal. Same-ID retry is false.
4. Only a reviewed ordinary `probe -> screened` successor may bind packet/start/terminal, this exact addendum path/SHA and authorize `STBS026-MODEL0-TRAIN-001`.
5. On `-Execute`, the runner may inspect only screened-registry metadata before creating and fsyncing the durable Model0 claim. It must read/hash this addendum, packet, source, prereg and all other bound controls only after that claim; any later failure writes the irrevocable FAILED terminal. The exact non-executing dry-run remains fully validating and must be green before `-Execute`.

## Frozen execution contract

Symbol `XAUUSD`, chart `M15`, preload `2005.01.01` to `2023.01.01`, Model0, execution mode 0, delay 0, timeout 900, deposit 100000, leverage 100, current spread semantic with CLI spread omitted, lifecycle-v3 trade-only telemetry, four-MiB raw journal cap, and the inclusive economic window `2018.01.02` to `2022.12.30` are unchanged.

No optimization, validation, OOS, holdout, paper, live or market-edge authority is created here.
