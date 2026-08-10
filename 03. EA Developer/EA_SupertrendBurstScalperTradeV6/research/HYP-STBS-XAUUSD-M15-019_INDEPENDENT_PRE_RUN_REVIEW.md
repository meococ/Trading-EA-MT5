# HYP-STBS-XAUUSD-M15-019 independent pre-run review

Verdict: `PASS_PRE_ECONOMIC_SOURCE_PACKAGE`

Scope: static source, compile, non-repaint, bounded-diff, lifecycle and frozen research-cost review only. No MT5 trade run, report outcome, PF, return, validation, holdout or promotion evidence was opened by this review.

## Evidence reviewed

- V6 source SHA256: `067633008AC0B88E56B15825DFA5226822D25C2B6E49AAC62AFFA6732D89F477`.
- Parent V5 source SHA256: `3822EED82C8D484CE8010A496767271DED20528158D68509B46EF934B043D918`.
- Preregistration SHA256: `BA98ACC7B5F1A204AD366A4DDCB0588A0214D0FA6B0272D2AA90946474806A5E`.
- Bounded V5/V6 diff proof SHA256: `1504468D6E788831C547E15E1FF2B459A09D9866A3ABEACA7DEE74CE8FC5496C`.
- Source-contract test SHA256: `5050EA379E3881B36A61B95174028C1BEE3433E723AFC512D0EEE44E164D94A9`; focused result: 5 passed.
- EX5 SHA256: `D0046A1F79B83CC7E607256A3F17AA079321961FF17380E23409E3A2D93B1EB7`.
- Compile log SHA256: `9F43EF7D79F0A3E06BD3B4CAC3314821CB0428188FA40D22F85407BC75C11652`; exact result: 0 errors, 0 warnings.
- Non-repaint manifest SHA256: `F5B369B693F4F2E4BED04B4E89B972DDC235D57E3F2693EF1F8D20166C5FEEB9`.
- Non-repaint audit SHA256: `8C95D7325C17571FAE3F7CC5FEE11C8069D5CAB428945B6BAA0041127ACFB19E`; verdict PASS, with only the declared non-decision `CopyTime` provenance read.
- EA contract SHA256: `891E6636F45B263F6163F5E703C9E87B912846B114CE25D5E45517871FD28057`.
- Research-cost manifest SHA256: `D822F04B6C7E92F8242BD66037CF28D6E7DCCD121FE6E46B98427D5FF22AC4B6`.
- Parent HYP018 terminal raw-row SHA256: `6DB679E3FDE7D7D0D11A4C942C4E89B986ECAFD96C5877353A367266DA044A41`.

## Findings

The mechanical normalization test proves that the only V5-to-V6 source changes are version/name, hypothesis/variant/magic, telemetry default and the OnInit trade-mode guard. The Supertrend signal, M15 ATR and geometry, risk sizing, account-safe margin search, restart persistence, explicit execution FSM, partial-fill handling, exits and frozen design-window gate reproduce V5.

Trade mode is fail-closed to HYP019, magic `5604119`, `InpAuditOnly=false`, telemetry enabled and the preregistered risk/session inputs. Lifecycle-v3 reloads and de-duplicates prior deals/positions/stop-outs, replays OPEN before CLOSE, identifies the final cumulative close, and fails runtime on stop-out or unbalanced opened/final-closed positions.

The cost manifest coherently binds the B326 data fingerprint, 100,000 USD account fingerprint, lifecycle-v3 HYP019/magic identity and the inclusive 2018-01-02 through 2022-12-30 scoring window. It is explicitly `RESEARCH_PROXY` and cannot promote or deploy the EA.

## Mandatory execution boundary

Authorize exactly one `STBS019-MODEL0-TRAIN-001` attempt. The durable claim must precede AlphaFactory execution and same-ID retry is forbidden. The exact invocation is XAUUSD M15, Model 0, 2005-01-01 through 2023-01-01 preload, 100,000 USD, 1:100, timeout 900, nonvisual and lifecycle-v3 trade-only telemetry. The CLI spread argument is omitted while the bound semantic spread remains `current`.

Engineering gates precede economics: exactly one new run; run-local source/EX5/config/compile identity; 0 errors and 0 warnings; HQ greater than 97; exact B326 and account fingerprints; unique RunMeta with `audit_only=false` and `runtime_failed=false`; lifecycle row count and every owned report deal/position reconciled; zero orphan/pending exposure, stop-out or emergency exit; and no trade outside the frozen economic window.

Only after all engineering gates pass may captured immutable bytes feed the verified research-cost builder and deterministic unified validation. Optimization, OOS, validation, holdout, paper, live and promotion permissions remain false.
