# HYP-CME6E-OPT-PIN-EURUSD-M15-001 - source-contract kill

Status: `KILL_SOURCE_CONTRACT_INVALID`

This exact mapping is terminal before statistics acquisition, target-price
access, MQL5, MT5, or economics.

## Why it is terminal

The R2 definition discovery selected the latest eligible definition over the
whole 2018-2022 archive and only then derived each expiry decision.  A direct
outcome-blind audit of all 60 acquired definition payloads found:

- 3,844,956 relevant call/put definition rows;
- 62,302 relevant raw symbols before the R2 eligibility projection;
- 756 expiration-revised raw symbols;
- 27,294 raw symbols whose latest selected definition had `ts_recv` or
  `ts_event` at or after its derived `expiration - 15 minutes` decision;
- zero delete actions in the relevant audited rows.

Example: the R2 latest-state rule can select a definition snapshot received on
2018-01-05 for a contract expiring on 2018-01-03.  That state was not knowable
at the decision and therefore violates the frozen point-in-time contract.

The second defect is independent.  The frozen source plan converted a missing
normalized `statistics` open-interest record into zero.  CME documents zero OI
in its Security Definition field, but the acquired normalized Databento
definition schema does not expose that field.  Databento's statistics contract
represents published venue statistics and can carry an explicit zero.  A
missing normalized record therefore cannot be proven to be zero by these
payloads.  The two pilots' published-only and zero-completed maxima matching is
not a discriminating test because adding zero-valued rows cannot displace an
already-positive maximum.

## Frozen consequences

- The USD 0.364300683141 statistics quote is not an acquisition authority for
  this killed mapping.
- No statistics payload, futures reference, EURUSD target, trade direction,
  return, or PnL was opened for this kill.
- The six 12:00 Chicago holiday/early-close expiries remain correctly excluded
  by the predeclared clock gate.  They are not the kill reason.
- The already-paid USD 4.65386341884732 definition payload remains a reusable,
  hash-bound source artifact; reusing it cannot revive this exact mapping.

Any continuation must use a new hypothesis ID, select definitions with an
explicit `ts_event < decision` and `ts_recv < decision` argmax, and treat
missing normalized OI as unknown unless a separately bound source proves the
zero value.

