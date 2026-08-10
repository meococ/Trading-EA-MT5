# HYP-STBS-XAUUSD-M15-005 — Independent post-failure review

Status: `PASS_KILL_EXACT_GEOMETRY_FROM_ROUNDED_ATR_TELEMETRY`

## Evidence and verdict

- Screened authority raw SHA256: `2A06DAC8C758D95C870C85775A9496D0759FE972BC2ECD8E448F2671BC332444`.
- Attempt start SHA256: `B43F8B50DB8E9BADB4F6B7C6814FD91BAA7702B2458C9B5DD756B2C708E83EAA`.
- Failed terminal SHA256: `D0DA049862B26BAD9897798FF344B6944BCFADD970FF532D66AEB04B42356DF2`.
- No comparator report or success receipt exists.

The exact kill is warranted. HYP005 attempted to reconstruct exact stop/target geometry from ATR printed to eight decimals while the MQL source uses the unrounded ATR double and runtime `SYMBOL_TRADE_TICK_SIZE`. The run proves digits `2` and point `0.01`, but does not persist runtime tick size. Exact raw-double/tick-size parity is therefore unidentifiable from these artifacts.

This failure radius is comparator observability only. It does not disprove `BuildEntryPlan`, signal/clock/oracle logic, the remaining comparator gates, or any market/economic property. HYP005 opened no AlphaFactory call, compile, MT5 launch, order, outcome, performance or economics.

## Legal next revision

A fresh HYP006 comparator-only child is legal after HYP005 becomes terminal. It may replace only the overclaimed exact geometry reconstruction with this preregistered observable contract across all 683 executable signals:

- `risk = abs(entry - stop)` and `reward = abs(target - entry)`.
- ATR, entry, stop, target and volume are finite and positive; stop/target are strictly direction-sided.
- Entry, stop and target align to the bound point `0.01`.
- With fixed `tol = 0.5e-8 + 1e-9`, require `-tol <= risk - printed_ATR <= 0.01 + tol`.
- Require `-tol <= reward - 1.5*risk <= 0.01 + tol`.
- Re-run every inherited HYP005/HYP004 gate and deterministic replay under a fresh HYP006 schema/verdict.

The final report must explicitly set `point_bounded_telemetry_consistency=true`, `exact_raw_double_geometry_proven=false`, `runtime_tick_size_proven=false`, and `exact_position_sizing_proven=false`. No compile, MT5, performance or economic authority may be opened.
