# HYP016 V4 to V5 bounded-diff proof

- Parent V4 source SHA-256: `028D0AADB49856F58B167390E93300CD12AD90993F13FE7D5012DE6FFB8FC726`
- Child V5 source SHA-256: `3822EED82C8D484CE8010A496767271DED20528158D68509B46EF934B043D918`

The focused source test extracts balanced MQL function bodies and requires exact byte equality for:

- `RebuildFrozenSupertrend`
- `BuildEntryGeometry`
- `ProcessNewClosedH1Bars`
- `SubmitEntry`
- `ManageLifecycle`

These cover the frozen Supertrend state, closed-H1 scheduling, M15 ATR/SL/TP geometry, entry request path, eight-bar/Friday lifecycle and reverse/exit scheduling. The test also requires direct audit guards before every `OrderSend` gateway.

The only intentional non-identity regions are:

- source/package/hypothesis/magic/variant identity;
- money-mode margin admission in `EvaluateMarginCandidate`;
- the same money-mode threshold in `EvaluateActualMargin`;
- added `required_free_margin` evidence in `EntryPlan`;
- audit-only suppression of per-candidate margin/reject logs;
- compact audit-only signal telemetry.

Percent-mode logic, risk percentage, Supertrend/ATR parameters, stop, target, maximum hold, session rules and all order/lifecycle functions remain unchanged. The test file is `research/tests/test_stbs016_account_safe_audit_contract.py` and must pass before authority.

