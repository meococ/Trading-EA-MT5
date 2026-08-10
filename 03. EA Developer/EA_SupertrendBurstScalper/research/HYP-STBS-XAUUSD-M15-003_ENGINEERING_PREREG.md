# HYP-STBS-XAUUSD-M15-003 — Frozen MT5 audit-governance revision

Preregistered at: `2026-08-09T05:05:56Z`  
Availability as-of: `2026-08-09T05:05:00Z`

## Question and scope

Can the unchanged, hard audit-only Supertrend Burst Scalper implementation complete its one-shot Model-0 signal/ATR/geometry correctness audit when the required post-packet review path is reserved before packet sealing?

This is a fresh governance child of terminal `HYP-STBS-XAUUSD-M15-002`, which failed before compile/MT5 solely because a new untracked review path changed AlphaFactory's sealed Git-status path set. HYP003 does not revise the indicator, signal, ATR, geometry, symbol, timeframe, data window, costs or economic thesis.

## Frozen identities

- Outer hypothesis: `HYP-STBS-XAUUSD-M15-003`.
- Inner MQL5 journal/implementation identity: `HYP-STBS-XAUUSD-M15-001`.
- Parent indicator-parity object: terminal `HYP-ST-XAUUSD-H1-012`.
- Source: `03. EA Developer/EA_SupertrendBurstScalper/EA_SupertrendBurstScalper.mq5`, SHA256 `B7D0092655A602C6619DD277848168F2B926C4F5ADB1311F4DB303AAC771757D`.
- Failed governance parent terminal raw row: `HYP-STBS-XAUUSD-M15-002`, SHA256 `A626D682AC44ADDA7D876DB4185BD6793A36A6A833425F66F775DC2CBAC32674`.
- Exact HYP002 verdict: `KILL_PRE_ALPHA_GIT_STATUS_PATHSET_DRIFT_NO_COMPILE_NO_MT5`.

## Frozen run contract

- EA/symbol/chart: `EA_SupertrendBurstScalper`, `XAUUSD`, native `M15`.
- AlphaFactory invocation window: `2005.01.01` through `2023.01.01`, Model `0`, execution mode `0`, delay `0`, deposit `10000`, leverage `100`, current spread token, telemetry profile `none`, telemetry tier `off`.
- Sole override: `InpAuditOnly=true`.
- Prehistory advances the exact H1 Supertrend state from the broker-native inception; only DESIGN `[2018-01-01, 2023-01-01)` events are emitted/scored.
- Expected frozen parent identities: raw `690`, executable `683`, exact-next gaps `7`, LONG `339`, SHORT `344`.
- Audit-only source must produce zero entry requests, close requests, deals, orders, trades, outcome reads, returns and economics.

Fresh outer attempts are exactly `STBS003-PACKET-BUILD-001` and `STBS003-MT5-AUDIT-001`, each limit one with no same-ID retry. Packet build is authorized only by a reviewed `probe` row. MT5 is authorized only by a later independently reviewed `screened` row after packet completion.

## Reserved mutable control path

Before packet sealing, this exact path must already exist once in `git status --short --untracked-files=all`:

`03. EA Developer/EA_SupertrendBurstScalper/research/HYP-STBS-XAUUSD-M15-003_POST_PACKET_REVIEW.md`

Its initial content must state only `RESERVED_NON_AUTHORITATIVE_PLACEHOLDER`. The packet receipt records the path/status-line reservation under `reserved_mutable_control_paths`, never the placeholder SHA as immutable evidence or a review. After packet completion, only bytes at this same path may change. Add/delete/rename of any workspace path invalidates the lane.

The final screened row must bind the final review path/SHA/status. After its durable MT5 claim, the launcher must hash that file, require `PASS_SCREENED_AUTHORITY`, reject the placeholder marker, reconcile the reservation contract and then allow AlphaFactory's independent live Git identity gate.

## Acceptance and hard gates

- Registry validator PASS at probe and screened transitions.
- Exact HYP002 terminal metrics/artifact hashes and actual file bytes.
- Packet claim before bound reads; packet attempt terminal on success/failure.
- Reserved path occurs exactly once in the sealed status list; it is absent from immutable receipt evidence.
- Final review hash/semantics validated only after MT5 claim.
- Full chronology: probe authority <= packet start <= receipt generation <= packet terminal <= screened authority <= MT5 claim.
- Alpha compile `0 errors / 0 warnings`; History Quality `>97%`; exact journal/run-snapshot/source/config/EX5 bindings.
- Raw/executable/gap/direction and ATR/geometry counts reconcile exactly; zero fatal/trade/outcome records.

Every trade, outcome, performance, economic, optimization, validation, holdout, visual, network, paid-request, promotion, paper and live permission remains false. A correctness PASS authorizes only a separately preregistered fresh economic child; it does not claim market edge.
