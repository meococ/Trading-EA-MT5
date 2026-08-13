# HYP-NYOD-XAUUSD-M15-001 economic failure

Verdict: `KILL_BASE_PF_EXPECTANCY_AND_CADENCE_FAIL`

## Frozen object tested

- Native FivePercent `XAUUSD M15`, design window `[2018-01-01, 2023-01-01)`.
- One New York 08:15 opening-drive continuation event per day at most.
- Prior ATR14 and prior two-hour range; strict expansion/body/close-location gates.
- Exact 08:30 next-bar entry, drive-extreme plus 0.15 ATR stop, 1.50R target,
  six-bar maximum hold and 0.25% equity risk.
- Untuned Model-0 baseline with current broker spread and commission.

## Engineering evidence

- Run: `02. AlphaFactory/runs/EA_NYOpeningDriveContinuation/20260811_102221`.
- History quality: `99%`; bars: `117,790`; ticks: `135,208,676`.
- Journal was non-truncated and the fixed-window data-quality gate passed.
- EA summary: `runtime_failed=false`, raw signals `185` (`92 LONG`, `93 SHORT`),
  accepted entries `153`, clock rejects `1,304`, invalid events `0`.
- Source SHA256: `183C5B17CCC147C72FA51E183B2EB0D6E717F69B2A9AE2BE8D0CA6F74232878A`.
- Run EX5 SHA256: `73D40589AB15D67D9FCA0C4D585CB0714F26F72170E0601DD2F2471480A69C32`.
- Run manifest SHA256: `4AA1347BDA59FC99C7244099211A520EA8EE797FC857CFB2FCFCA38316ED037D`.
- Report SHA256: `14F2715B1AD878AAEBCC8DC9F2D47F707A89591926561A265CD5C13A436D9728`.
- Journal SHA256: `DD346F931D86E614689E36D5CB54C4E9AF68FAD857F1B8C9FA268B8C56EF4464`.
- Enhanced-summary SHA256: `59BFB0898F575DF02E4622F234A11DEA066B4C03ACF06A40AB6A2BAAFBB0CDE4`.

## Economic result

- Completed trades: `153`.
- Profit factor after the baseline broker-cost model: `0.7016232424`.
- Net profit: `-$5,976.57`.
- Expectancy: `-$39.0625` per trade.
- Win rate: `37.9085%`; average win `$242.31`; average loss `-$210.85`.
- Max relative drawdown: `6.5172%`.
- Cadence: `153 / (1826 / 7) = 0.5865` trades/week.

PF, expectancy and cadence fail by wide margins. The drawdown gate passing does
not compensate for the absence of edge or the sparse event clock. Cost stress,
optimization, validation and holdout remain unopened because the x1 baseline is
already terminal.

## Exact failure radius

This verdict kills only the frozen New York 08:15 opening-drive continuation
mapping above on FivePercent XAUUSD M15 for 2018-2022. It is not a claim that
all opening-range, all continuation or all XAUUSD strategies lack edge.

No rescue is permitted through hour/DST shifts, weekday or direction selection,
ATR/range/body/close thresholds, stop/target/hold/risk changes, or alternative
session definitions after reading this result. Any new work must be a materially
different market mechanism under a fresh preregistration.
