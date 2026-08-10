# HYP-STBS-XAUUSD-M15-020 — Engineering Failure

## Verdict

`KILL_ENGINEERING_LIFECYCLE_CLOSE_LOGGING_FAILED_AND_JOURNAL_TRUNCATED_NO_ECONOMIC_VERDICT`

The sole authorized Model-0 TRAIN attempt is consumed. The run produced a tester report, but it failed the frozen engineering/evidence gates before cost or economic acceptance. The observed one-trade PF/return is inadmissible and must not be used to accept, reject, tune, or filter the strategy.

## Frozen attempt

- Attempt: `STBS020-MODEL0-TRAIN-001`
- Alpha run: `20260810_013139`
- Source SHA-256: `B49D1CA7868B723C10B12A23D2C07CA1DF5F2A0BB86B0860C05FD34CE0F03750`
- Attempt start SHA-256: `8FF8748BB29E0C54452FE3AF573DF3C731C793BC114AD85178FACEF924A93B96`
- Attempt terminal SHA-256: `71907357A1EFAD222EE92E2CC9541AAD030629ECBC4630F4E2B972D5364561B1`
- Run manifest SHA-256: `81D57111C854DA6207B6FF08467DC15EE00152C91C7DF8331143D7E649646E8F`
- Tester report SHA-256: `7D504EE9519F11532D1F8C86FFEC2F8DE5DC75A3EBA7460F36DA448767AE9D10`
- Exported journal SHA-256: `BA816D419CC4398473D820A2317846B2260592838CF59CB128281B6CB491A52C`
- Lifecycle CSV SHA-256: `B775B9F4B0FBFA8A9AC6BC5B0F6F9D193B6BFE16417D38F826AAA0CCD547B558`
- RunMeta SHA-256: `D8996FF9F968BF5E1296FA4E78EC1FE4FCA064F5D641C478F0FB5A7A52231A36`
- Run EX5 SHA-256: `58D7C891D2E910C78CC92C0C1DCEE6D6495C2924C160743B6CF6DCD5990EC878`
- Run config SHA-256: `F82202B251A14D4028671D7C071DAD23136F3D53A056A82F1C4C61A6E33A0893`

## Exact failure evidence

1. AlphaFactory stopped after the report became ready because `data_quality_journal_delta.truncated=true`. The raw journal read reached the frozen `1,048,576`-byte cap; the exported UTF-8 journal is exactly `524,289` bytes and contains no terminal `STBS_SUMMARY`.
2. The journal flood is caused by `STBS_MARGIN_ACTUAL` being emitted on every position-management reconciliation. The truncated export contains 1,908 such records and stops at `2018.01.03 05:07:14`, while the tester continued through 2022.
3. The complete native agent log records the independent runtime failure at `2018.01.03 05:34:29`: `STBS_FATAL|runtime|lifecycle_deal_logging_failed` for closing deal `3`, reason `DEAL_REASON_SL`.
4. The complete native agent log ends with `STBS_FATAL|lifecycle_unbalanced|positions_opened=1|positions_final_closed=0` and `STBS_SUMMARY ... raw=1 ... entries=1 ... closes=1 ... failed=true`.
5. RunMeta independently agrees: `runtime_failed=true`, one opened position, zero final lifecycle closes. The lifecycle CSV contains only the opening SELL row.
6. The tester report contains one SELL opened at `2018.01.03 05:00:00` and closed by SL at `05:34:29`. Although the report parser can calculate one losing trade, this outcome was generated after the lifecycle contract failed and is not economic evidence.

## Failure radius

This kills only the exact V7 trade-enabled implementation/evidence mapping in which:

- actual-margin telemetry is printed per tick/reconciliation and exhausts the journal cap; and
- close-deal lifecycle logging is attempted inside the trade-transaction callback and fails before a durable final-close row is recorded.

It does not establish that the frozen H1 Supertrend flip signal lacks edge, and it does not authorize any parameter, session, direction, stop, target, sizing, or cost change.

## Lawful next revision

A fresh source identity may change only the evidence/lifecycle implementation:

- preserve signal, ATR14, entry geometry, 1R stop, 1.5R target, eight-bar hold, account-safe sizing and all economic thresholds;
- emit actual-margin telemetry once per owned position plus any unsafe/fatal transition, not every tick;
- defer deal logging out of `OnTradeTransaction`, replay stable account history on the next tick and on deinitialization, and make the replay ownership/volume calculation self-contained;
- add stage-specific lifecycle failure diagnostics and regression fixtures for delayed close visibility, SL close, partial closes, callback reordering and final replay balance;
- compile, rerun non-repaint/static tests, preregister a fresh one-shot baseline, and keep economics closed until lifecycle and journal completeness pass.

Same-ID retry of HYP020 is forbidden.
