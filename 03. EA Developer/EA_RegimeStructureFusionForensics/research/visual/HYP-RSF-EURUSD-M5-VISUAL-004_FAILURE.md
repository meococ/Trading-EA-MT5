# HYP-RSF-EURUSD-M5-VISUAL-004 — Failure Packet

Status: `KILLED_ENGINEERING`

VISUAL-004 was stopped after native MT5 evidence made full completion economically
and operationally unnecessary. The partial run `20260807_011841` reached
59,087,274 ticks and 450 final closes. Its VisualShots sidecar contains 24 OPEN /
CLOSE requests for 12 frozen positions. Every `ChartScreenShot` request returned
`true` with MQL error `0`, yet no referenced PNG existed under the tester agent,
portable terminal, workspace, or user MetaQuotes data roots after all files closed.

The live chart also failed presentation acceptance:

- QQE rendered only the white trend line; the gray/cyan/magenta histogram was absent.
- TB SMC retained overlapping historical zones that obscured price behavior.
- The M5 price chart and trade markers themselves were genuine MT5 Visual Mode.

Therefore request acceptance is no longer treated as screenshot evidence. VISUAL-005
must verify an actual readable file with positive size, use an explicit QQE color-index
count, and restrict display-only TB retention to one cell and one void. This failure
does not change, rescue, or re-score the already killed parent strategy.
