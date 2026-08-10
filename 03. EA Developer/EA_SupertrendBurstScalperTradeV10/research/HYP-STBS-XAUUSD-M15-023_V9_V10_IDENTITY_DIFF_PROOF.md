# HYP-STBS-XAUUSD-M15-023 — V9 to V10 identity-only diff proof

## Identities

- Parent V9 source SHA-256: `9B82946CF17A876B547E7227F7FA131183C2383D38BF639574001CAB03DF8D82`
- Child V10 source SHA-256: `4B481CE867DB8A9F9E02AB218FEA50C88FD37A48B8ECB92E2048418DB7F7769B`
- Parent HYP022 terminal raw-row SHA-256: `91A68A5C36EA19F62F12896C4F96A05426D62C13DBCD8EF3F4F8DBB34F56409E`
- Parent verdict: `KILL_GOVERNANCE_PRE_PACKET_BUILDER_SELF_HASH_AUTHORITY_CYCLE_NO_ATTEMPT_NO_ECONOMIC_VERDICT`

## Exact executable diff

The only MQL changes are:

1. version `9.00` to `10.00`;
2. hypothesis `HYP-STBS-XAUUSD-M15-022` to `HYP-STBS-XAUUSD-M15-023` in the input default and OnInit guard;
3. variant tag `...V9...` to `...V10...` in the input default and OnInit guard;
4. magic `5604122` to `5604123` in the input default and OnInit guard;
5. EA name `EA_SupertrendBurstScalperTradeV9` to `EA_SupertrendBurstScalperTradeV10`.

All signal, Supertrend, ATR, closed-bar/exact-next clocks, 0.25% requested risk, 20-point adverse-fill envelope, full 4.4/lot charge reserve, requested/worst/SL margin stress, 1R/1.5R geometry, eight-bar hold, Friday/weekend controls, order FSM, lifecycle replay, runtime margin backstop, journal and telemetry behavior are byte-identical after normalizing those five identity tokens.

HYP023 is not an economic rescue and changes no threshold based on HYP021/HYP022 outcomes. It exists only because HYP022 never produced a packet or attempt and its initial authority bound an unusable self-referential builder.
