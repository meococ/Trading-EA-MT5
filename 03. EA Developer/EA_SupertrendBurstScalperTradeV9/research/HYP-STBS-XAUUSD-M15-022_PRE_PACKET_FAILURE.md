# HYP-STBS-XAUUSD-M15-022 — Pre-packet governance failure

## Verdict

`KILL_PRE_PACKET_BUILDER_SELF_HASH_AUTHORITY_CYCLE_NO_MT5_NO_ECONOMICS`

The valid initial HYP022 registry row has raw-row SHA-256 `2E27EFC91BF481F9D8C4F3837E8A128D1E9E08C0F0771AD8DC3181842AA7EE1`. It bound task-packet builder SHA-256 `EC49A7496CBCC947C3170D832DC87AF16775EB3329E2F5CF969426309DCF54C9`, whose frozen `EXPECTED_REGISTRY_ROW_SHA256` remained the literal placeholder `PENDING_HYP022_INITIAL_ROW_SHA256`.

Replacing that placeholder with the row hash necessarily changes the builder hash already bound by the same row. Appending a second `screened` row to bind a semantic builder is not legal under the current append-only transition contract and was rejected by the validator. The rejected unvalidated line was removed immediately; the authoritative registry was restored and validates at 861 rows.

The builder was hardened to semantic latest-row/self-SHA validation at SHA-256 `E49E0C9C6285CCBA76A617F14B6AAA1A89D97D4D4C3919AFC9407D06042E5B83`, but those bytes are not authorized by the existing HYP022 row. They must not be used under HYP022.

No task packet was created. `STBS022-MODEL0-TRAIN-001` was never claimed. No Alpha compile/backtest, MT5 launch, source-data access, order, deal, outcome, return, PF, cost artifact or economic validation occurred. The failure radius is only HYP022 pre-packet authority construction; it says nothing about the V9 formula or market edge.

The integrity-preserving continuation is a fresh hypothesis/EA identity whose corrected semantic builder is finalized before its first authority row. Editing the accepted HYP022 row in place, injecting a runtime hash, or broadening the registry validator is forbidden.
