# Frozen prereg — HYP-CBWR-XAUUSD-M15-002

Status: FROZEN engineering successor before its compile and first outcome-bearing run.

Parent: `HYP-CBWR-XAUUSD-M15-001`, invalid after report creation because its journal D0 proof used noncanonical `m15_*` field names. The parent report is preserved but its P&L and trade metrics remain unread for selection.

## Invariant market and trading surface

HYP002 is signal-, execution-, management-, risk-, cost- and window-identical to the parent prereg:

- XAUUSD M15 Model 0 design `[2018-01-01,2022-01-01)`.
- Signal bar shift 1; swing extrema shifts 2..9.
- Directional wick/range >=0.60, body/range <=0.35, close in directional half, swing tolerance 0.15 ATR14.
- ATR14 / prior-50 ATR mean in `[0.70,2.20]`.
- Next-bar first-tick entry; max spread 55 points.
- Structural stop outside wick by 0.25 ATR, entry risk clamped to 1.20..2.80 ATR, TP 1.60R, BE 0.90R plus entry spread, time stop 12 bars.
- Risk 0.60% equity; 1.50% daily and 3.50% weekly entry halts; daily 21:50 and Friday 20:00 server flat.
- Primary `SWING8_PRIMARY/InpRequireSwing=true`. No-swing matched control remains locked until the primary passes the design advance gate.

## Only authorized changes

- Hypothesis identity `...001 -> ...002`.
- Magic `5604701 -> 5604702`.
- Telemetry prefix `CBWR001 -> CBWR002`.
- `EmitSeriesProof` now emits the AlphaFactory canonical M5/M1 D0 series fields and one M5 `CopyTime` proof. This changes no signal or order decision.

## Acceptance, cost and stopping rules

All acceptance/kill, cost status, forbidden post-result edits and locked OOS rules are inherited exactly from the parent prereg. Immediate design kill remains: PF `<1.00`, expectancy `<=0`, no trades/runtime failure or Max DD `>12%`. Advance requires N `>=300`, PF `>=1.15`, positive expectancy, DD `<=12%`, acceptable concentration and reconciled telemetry/report counts. Goal/DONE thresholds are unchanged and stricter.

No live trading, optimization, OOS, parameter change or matched-control execution is authorized by this prereg alone.
