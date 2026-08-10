# HYP-ST-XAUUSD-H1-009 - post-terminal read disclosure

Status: `APPEND_ONLY_CORRECTION`

The frozen HYP009 failure report states that the oracle was not opened by the
failed comparator invocation. That wording was too broad. The inherited
pre-claim authority validator hash-read the HYP003 oracle file, start, report,
receipt and terminal before reaching the missing MQL source binding and raising
`ValueError: mql_source binding mismatch`.

Those files were not decoded, parsed or compared. The MQL audit CSV was not
read by the parity engine, no comparator claim/root was created, and no source
row, outcome, trade, return, PF or economic metric was evaluated. This addendum
does not modify the sealed failure report or HYP009 registry rows; HYP010 must
bind it explicitly and uses claim-before-artifact-read ordering.
