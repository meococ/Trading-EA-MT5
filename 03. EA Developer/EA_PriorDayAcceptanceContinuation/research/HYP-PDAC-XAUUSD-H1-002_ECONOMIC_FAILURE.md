# HYP-PDAC-XAUUSD-H1-002 economic failure

Verdict: `KILL_BASE_PF_AND_EXPECTANCY_FAIL`

## Frozen object

- Native FivePercent XAUUSD H1 prior-day first two-close acceptance.
- Friday entries allowed only before 20:00 UTC; no weekend hold.
- Exact next-H1 entry, structural stop 0.25 of the prior-day range inside the
  broken boundary, 1.50R target, eight-H1-bar time exit and 0.25% equity risk.
- One untuned Model-0 baseline over `[2018-01-01, 2023-01-01)`.

## Engineering evidence

- Run: `02. AlphaFactory/runs/EA_PriorDayAcceptanceContinuation/20260811_105343`.
- HQ `99%`; fixed-window DQ PASS; journal `3,654,120` bytes and non-truncated.
- Duplicate summaries agree: `runtime_failed=false`, closed bars `26,575`, raw
  signals `558`, LONG `309`, SHORT `249`, entries `546`, order rejects `0`,
  EA-requested closes `326`, clock rejects `1,143`, invalid inputs `0`.
- Source SHA256:
  `16DD0E4879DDBF2D479C52DBBA5167630D85A868B50A7670B195DCDC2711BD1D`.
- Run EX5 SHA256:
  `513DED52C5B9BCC050C739A53580FC216950A570DD29BB51B8EEDEC2C5A003C4`.
- Run manifest SHA256:
  `753403FA8E6C7CC4E7405C5CB882EB9B3FA81630F80C7473B90CA49A302B96F9`.
- Report SHA256:
  `651BC42660FDDCF14E755C579BCFF522252093DA8AD840E277B22D6954617710`.
- Journal SHA256:
  `32D999B2A5C357B454405B210A1291F00D01A8C23A0D13FD65AE26E38BC69CF1`.
- Enhanced-summary SHA256:
  `2E06A40E8AB869ECB0D839875187E3F36F71B276FA5240661D7D1D669BABC534`.

## Economic result

- Completed trades: `546`; cadence `2.093100/week` — PASS.
- Profit factor after the baseline broker report costs: `0.8335757847` — FAIL.
- Net profit: `-$7,943.06`.
- Expectancy: `-$14.5477/trade` — FAIL.
- Win rate: `43.0403%`; average win `$169.30`; average loss `-$153.47`.
- Max relative drawdown: `7.8109%` — PASS.

The baseline passes cadence and drawdown but has no positive post-report-cost
edge. Cost stress, optimization, WFA, validation and holdout remain unopened.

## Failure radius and forbidden rescue

This kills only the exact HYP002 prior-day two-close acceptance continuation
mapping above on FivePercent XAUUSD H1 for 2018–2022. It does not reject every
daily range or multi-day acceptance strategy.

Do not rescue this ID using the analyzer's favorable Thursday/Europe subsets,
session/hour/weekday or direction deletion, range/close thresholds, stop/target/
hold/risk changes, or another execution child. A next loop must select a
materially different market mechanism and begin with an outcome-blind density
gate when cheaply measurable.
