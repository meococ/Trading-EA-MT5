# Frozen prereg — HYP-CBWR-XAUUSD-M15-003

Status: FROZEN engineering successor before compile and outcome-bearing execution.

Parents: HYP001 failed the evidence adapter after report creation; HYP002 then failed OnInit with zero bars/trades because the strict EA received only a partial override surface. Neither parent report was used for economic selection.

## Trading object is unchanged

The full market, signal, execution, management, risk, cost, design-window, control and stopping contract is inherited exactly from HYP001/HYP002:

- XAUUSD M15 Model 0 design `[2018-01-01,2022-01-01)`.
- Closed signal bar shift 1; prior swing shifts 2..9.
- Wick >=0.60, body <=0.35, directional-half close, 0.15 ATR swing tolerance.
- ATR14 / prior-50 ATR mean `[0.70,2.20]`.
- Next-bar market entry, 55-point spread cap.
- Structural stop buffer 0.25 ATR, risk clamp 1.20..2.80 ATR, target 1.60R, BE 0.90R plus entry spread, time stop 12 bars.
- 0.60% equity risk; daily/weekly entry locks 1.50%/3.50%; server flat 21:50 daily and Friday 20:00.
- Primary variant `SWING8_PRIMARY`; matched no-swing control remains locked.

## Only authorized HYP003 changes

- Identity `...002 -> ...003`, magic `5604702 -> 5604703`, prefix `CBWR002 -> CBWR003`.
- The execution task/receipt/CLI now supplies every frozen input explicitly except reserved `InpEnableTelemetry`, whose compiled default remains `true` under telemetry profile `none`.
- No formula, bar index, threshold, clock, order geometry or risk behavior changes.

Immediate design kill and advance gates remain exactly those in HYP001: kill on PF `<1.00`, expectancy `<=0`, no valid trades/runtime failure or DD `>12%`; advance only with N `>=300`, PF `>=1.15`, positive expectancy, DD `<=12%`, acceptable concentration and reconciled counts. Goal/DONE remains PF `>1.30` plus cost stress, holdout, WFA/DSR/Monte Carlo and recovery gates.

No optimization, OOS, matched control, promotion or live action is authorized by this prereg alone.
