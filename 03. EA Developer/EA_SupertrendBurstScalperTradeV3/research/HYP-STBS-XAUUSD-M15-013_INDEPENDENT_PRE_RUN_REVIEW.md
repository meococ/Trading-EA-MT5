# HYP-STBS-XAUUSD-M15-013 independent pre-run review

Status: `PASS_PRE_RUN`

Reviewed at: `2026-08-09T13:27:20Z`

## Scope

Static, outcome-blind review of the sole untuned Model-0 TRAIN baseline package. No MT5 baseline, report, lifecycle outcome, PF, return, optimization, OOS, holdout, paper or live result was opened for HYP013.

## Frozen identities

- Prereg SHA256: `EF3DB79293438056A1634723E5F2DAE7183E093EF33A6F84CC6E061AC4AFE1CA`.
- MQL5 source SHA256: `8E1DEA824FC0BC1699FC618AC71F2C8D7848556215699FFF432DA1BF9EEFF3B0`.
- EX5 SHA256: `8330D957AC11B04A0E3EA46482C67E97253C945BAEAA60AC9DE720C5372BDBA7`.
- Compile-log SHA256: `DBB242DB21626640C72FC6A14982F39B450EDA6CEDE2AEE2D11A40947A431CD4`; compile result is 0 errors and 0 warnings.
- Capability-contract SHA256: `891E6636F45B263F6163F5E703C9E87B912846B114CE25D5E45517871FD28057`.
- Static non-repaint manifest/audit SHA256: `BB4D50443DF5E823CB67DE2DD5E010D6B687BE2D447D25C89C203705377DF553` / `69D1DE724BE08DD2BD776543AD9D0368DBEA788577884E1B26BFA83E2B56B86C`; audit status PASS with zero findings.
- Source/telemetry contract-test SHA256: `6839FAEB9179D676C955F741D12CAF57E0C26F6AE7B9024DA845921C230200B3`.
- Cost-source manifest SHA256: `77A7D738AD945AB869CC1682110FF64C1DC3D8827039F68F937392A793C7CAF8`.
- Research loop / verified-cost builder / unified validator / cost test SHA256: `2E89E9C654B301C7BDB22AF344BA7BEFD4C8B7459AE7BE6EFF9A36118E7D61DE` / `617AF7E526E7D30DBB7C6BBEF7B6DB3740552ABA31BFBFB0F6C42A4C1F8BB3AD` / `E9C26801D020298AE6BADD1737ECE5B77778EA34951B99EB3A0B81F47D5E9DE2` / `40F1461086A95AD3CB2FF50D15A2F1FD5B848525DCD13FC1EFDD39499CDC177E`.

## Review verdict

The package is ready for exactly one `STBS013-MODEL0-TRAIN-001` control run. The recursive H1 Supertrend state may use the frozen 2005-2023 tester preload, while every economic deal must lie inside the inclusive 2018-01-02 through 2022-12-30 scoring window. Cadence uses the inclusive-day denominator. Canonical cost rebuilding is fail-closed on exact report/lifecycle joins and the sole manifest-bound RunMeta, including HYP013 identity, audit disabled, promotion disabled, `diagnostic.runtime_failed=false`, and exact lifecycle-row reconciliation.

The separate baseline verdict is allowed to return only PASS, FAIL or BLOCKED under the preregistered gates. PASS may open a fresh robustness/OOS lane. FAIL parks only this exact mechanism and requires a materially new hypothesis. BLOCKED is engineering evidence only. No result-mined filter, parameter change, optimization or same-ID retry is authorized.

The cost tier remains `RESEARCH_PROXY`; therefore even a baseline PASS is economic research evidence, not promotion, paper or live authorization.
