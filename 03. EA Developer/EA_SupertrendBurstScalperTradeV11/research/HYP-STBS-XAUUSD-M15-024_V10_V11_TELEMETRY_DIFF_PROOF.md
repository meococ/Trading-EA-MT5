# HYP024 V10 to V11 bounded-diff proof

Parent terminal row SHA256: `2CA6AD8D565F0670E18DFBD58EA17CEE93372B18D1F06C27216288E49D6FA6B3`

Parent V10 source SHA256: `4B481CE867DB8A9F9E02AB218FEA50C88FD37A48B8ECB92E2048418DB7F7769B`

Child V11 source SHA256: `7CC7A9D7C30216A1669D84AEEA867E32EA15F2E9E8C195D171BD574A4D2EB0BC`

The complete source diff is limited to:

1. EA version, description, package name, hypothesis ID, variant tag and magic identity.
2. Deletion of the three-line nondecision `STBS_MARGIN_STRESS_UNSAFE` `PrintFormat` block after the `safe` result is computed inside `EvaluateMarginCandidate`.

The deletion does not alter any variable, computation, branch, loop condition, loop iteration, return value or persisted `EntryPlan` field. The frozen source contract test normalizes the identity changes, deletes that exact one block from V10 in memory, and requires byte-for-byte equality with V11.

Unchanged surfaces include Supertrend state, signal timestamps, M15 ATR, geometry, risk sizing, adverse-fill envelope, commission reserve, margin and stopout calculations, selected volume, order requests, SL/TP, execution FSM, lifecycle replay, exits, daily/account locks, costs, economic window and all acceptance thresholds.

The separate four-MiB journal cap is a harness contract change in AlphaFactory and the HYP024 packet/runner, not MQL trading logic. The cap remains fail-closed on truncation and does not authorize any additional outcome, optimization or promotion access.
