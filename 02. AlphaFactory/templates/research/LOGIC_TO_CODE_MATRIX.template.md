# Logic-to-code matrix — HYP-REPLACE-ME

Freeze this matrix before the meaningful run. One row is one trader decision
or safety invariant. A row is complete only when the exact source location,
closed-bar information set, telemetry field and verification are all bound.

| ID | Trader observation / intent | Quantified rule | Role (`context|qualification|trigger|invalidation|management|risk`) | Source symbol / location | Decision-time data and bar index | Telemetry proof | Test / parity proof | Status |
|---|---|---|---|---|---|---|---|---|
| L01 | REPLACE | REPLACE | REPLACE | REPLACE | REPLACE | REPLACE | REPLACE | `VERIFIED|PROXY|MISSING` |

## State machine and sequencing

Describe the ordered transition chain, timeouts, resets, duplicate suppression
and the exact event that authorizes entry. Context must not silently become the
trigger.

## Stop, target and execution geometry

Bind price side, tick size, broker stop/freeze levels, spread/slippage model,
volume sizing, partial fill behavior, break-even/partial exits and restart
reconciliation.

## Known gaps before outcome

List every material ambiguity. `unresolved_material_ambiguities` in the delivery
packet must be zero before a completion claim; otherwise open a plan amendment
before reading the run outcome.
