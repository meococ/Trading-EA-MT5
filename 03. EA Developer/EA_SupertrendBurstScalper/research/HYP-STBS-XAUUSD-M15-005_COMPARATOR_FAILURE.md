# HYP-STBS-XAUUSD-M15-005 — Comparator failure

Status: `KILL_EXACT_GEOMETRY_FROM_ROUNDED_ATR_TELEMETRY`

Attempt: `STBS005-COMPARATOR-001` (consumed; no retry)

## Evidence

- Screened authority raw SHA256: `2A06DAC8C758D95C870C85775A9496D0759FE972BC2ECD8E448F2671BC332444`.
- Attempt start SHA256: `B43F8B50DB8E9BADB4F6B7C6814FD91BAA7702B2458C9B5DD756B2C708E83EAA`.
- Failed terminal SHA256: `D0DA049862B26BAD9897798FF344B6944BCFADD970FF532D66AEB04B42356DF2`.
- The evidence root contains only the start and failed terminal. No comparator report or success receipt exists.

## Exact failure

The exact heading predicate and empty Orders structure passed. HYP005 reached journal/oracle comparison and stopped at unique signal index 10 because its reconstructed stop and target differed from the printed telemetry.

The event is SHORT with printed ATR `2.04000000`, entry `1337.68000000`, SL `1339.73000000`, and TP `1334.60000000`. The MQL source calculates geometry from the full unrounded ATR double, then applies `MathCeil`/`MathFloor`; the journal prints ATR with only eight decimal places. Reconstructing exact tick-boundary behavior from that rounded ATR is therefore not identifiable. The run manifest proves XAUUSD digits `2` and point `0.01`, but does not persist the runtime `SYMBOL_TRADE_TICK_SIZE`.

Read-only reconciliation of all 683 executable records found zero nonfinite/nonpositive values, zero wrong-sided entries/stops/targets, and zero point-alignment failures. `risk_distance - printed_ATR` lay within numerical tolerance of `[0, 0.01]`; `reward_distance - 1.5*risk_distance` also lay within numerical tolerance of `[0, 0.01]`. This supports only point-bounded observable telemetry consistency, not exact reconstruction of the unprinted raw double or runtime tick-size value.

## Verdict boundary

This kills only HYP005's claim that exact 1-ATR/1.5R prices can be reconstructed from eight-decimal ATR telemetry with an assumed `0.01` tick size. It does not reject the hash-bound source formula, signal/clock/oracle mapping, point-bounded geometry readiness, data quality, zero-order fact or any market/economic property.

HYP005 opened no AlphaFactory call, compile, MT5 launch, source acquisition, order, outcome, performance or economics. A fresh comparator-only child may narrow the geometry verdict to explicitly point-bounded observable consistency, retain every other frozen check, and must not claim exact raw-double parity, runtime tick-size parity or position-sizing parity.
