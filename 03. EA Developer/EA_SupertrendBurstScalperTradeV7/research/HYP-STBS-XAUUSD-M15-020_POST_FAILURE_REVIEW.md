# HYP-STBS-XAUUSD-M15-020 — Independent Post-Failure Review

## Verdict

`PASS_KILL_ENGINEERING_LIFECYCLE_CLOSE_LOG_AND_JOURNAL_TRUNCATION_NO_ECONOMIC_VERDICT`

The independent review reconciled the sole attempt and agrees that HYP020 must be terminalized without an economic conclusion.

## Reconciled facts

- Attempt start: `8FF8748BB29E0C54452FE3AF573DF3C731C793BC114AD85178FACEF924A93B96`
- Attempt terminal: `71907357A1EFAD222EE92E2CC9541AAD030629ECBC4630F4E2B972D5364561B1`
- Run manifest: `81D57111C854DA6207B6FF08467DC15EE00152C91C7DF8331143D7E649646E8F`
- Report: `7D504EE9519F11532D1F8C86FFEC2F8DE5DC75A3EBA7460F36DA448767AE9D10`
- Source snapshot: `B49D1CA7868B723C10B12A23D2C07CA1DF5F2A0BB86B0860C05FD34CE0F03750`
- Run EX5: `58D7C891D2E910C78CC92C0C1DCEE6D6495C2924C160743B6CF6DCD5990EC878`
- Run config: `F82202B251A14D4028671D7C071DAD23136F3D53A056A82F1C4C61A6E33A0893`
- Lifecycle CSV: `B775B9F4B0FBFA8A9AC6BC5B0F6F9D193B6BFE16417D38F826AAA0CCD547B558`
- RunMeta: `D8996FF9F968BF5E1296FA4E78EC1FE4FCA064F5D641C478F0FB5A7A52231A36`

The tester opened one `0.95`-lot SHORT at `1312.23` and closed it at `1313.86` by SL. During the close callback, the EA observed transient zero deal fields after mutable History selection and raised `lifecycle_deal_logging_failed`; the lifecycle sidecar therefore contains OPEN only and RunMeta is `runtime_failed=true`. Signal processing stopped after the first event.

Separately, the agent log contains 6,011 `STBS_MARGIN_ACTUAL` rows for the one open position. The combined journal collector reached its frozen one-MiB cap and emitted `truncated=true`, so the exported journal does not contain the terminal summary.

## Scope

The one loss, PF `0`, and any derived analysis cache are inadmissible because lifecycle correctness and journal completeness failed before cost/unified validation. This is not evidence against the Supertrend signal and cannot justify parameter or filter changes.

## Approved next lane

Fresh HYP021/V8 may preserve all economic choices and change only lifecycle/evidence transport:

1. queue deal notifications and consume stable history on a later tick/deinit;
2. capture every deal field before any history reselection;
3. replay deals ordered by `(DEAL_TIME_MSC, ticket)` in OPEN then CLOSE passes;
4. retry transient history unavailability but fail closed if unresolved;
5. emit reason-coded lifecycle rejects;
6. bound normal-path journal volume while keeping the lifecycle CSV and RunMeta authoritative;
7. compile, non-repaint audit, focused tests, preregistration and independent pre-run review before one fresh Model-0 attempt.

No optimization, OOS, holdout, promotion, paper or live authority is granted.
