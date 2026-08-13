# HYP-CBWR-XAUUSD-M15-003 — terminal baseline result

Verdict: `KILL_DESIGN_EDGE_AND_RISK_FAILURE_NO_CONTROL_NO_OOS`.

## Evidence identity

- Run: `02. AlphaFactory/runs/EA_WickReject_XAU_M15_V1/20260812_004435/`
- Source SHA256: `015C6FA93A7768C85D5DD4703E50D3D5AC67B3A7DCBED71E73735B0CDCF3DC85`
- Executed EX5 SHA256: `6127959EA0B8D348BF767A536C577BBEB2753B8337A824ABDF13B96E3325061A`
- Report SHA256: `6A264270E74DBAC251847757C7399DFCCB20F264FD8B31DD4F4C0A896FF95DE2`
- Receipt SHA256: `16668AEB00810BF207A81C144FF45B286B50FF783D1EE3867FC4F8C2B1276E49`
- Compile: 0 errors, 0 warnings; non-repaint PASS; History Quality 99%; coverage class `FULL_2018_PLUS`.

## Economic result

The requested design range was 2018-01-01 to 2022-01-01, but MT5 stopped at 2018-01-22 because a margin stop-out occurred after 1% of the testing interval. This is part of the terminal risk verdict, not a full-window edge estimate.

| Metric | Result |
|---|---:|
| Trades | 29 |
| Net profit | -$10,427.11 |
| Profit factor | 0.125957 |
| Win rate | 20.6897% |
| Expectancy | -$359.56/trade |
| Max drawdown | 9.9966% |
| Max loss streak | 10 |

The one nonduplicated journal stream contains 56 qualified signals, 29 entries and 28 instrumented exits before the final forced close: 23 SL, 4 time-stop and 1 TP. The 28 logged exits lost `-$9,513.24` in price P&L before `-$142.27` commission and `-$206.71` swap. Therefore friction is not the primary cause; the entry object is gross-negative in the observed path.

All broad sessions fail: Asia PF 0.00, Europe PF 0.27, New York PF 0.06. The hour chart contains two apparent PF=1000 bars with only one trade each; these are sparse artifacts and are forbidden as post-hoc filters.

## Chart/log diagnosis

- `analysis/analysis_charts.png` shows an almost monotonic equity decline and drawdown expansion; there is no recovery regime.
- Rejection bars frequently continued through the wick rather than mean-reverting. The realized win rate is far below the approximate 38.5% break-even win rate for a clean 1.6R target, even before costs and BE/time-stop distortions.
- Risk locks skipped 24 of 56 qualified signals, but removing them is forbidden and would expose an already gross-negative signal more often.
- The final margin stop-out means the sizing/margin envelope is not safe for this symbol/account even at the preregistered 0.60% stop-risk calculation.

## Stopping decision

The primary fails immediate prereg gates PF `<1.00`, expectancy `<=0`, and runtime/risk completion. No matched no-swing control, OOS, cross-symbol transfer, cost stress, validation, optimization or parameter revision is authorized.

Exact failure radius: XAUUSD M15 closed-bar directional wick >=0.60, body <=0.35, directional-half close, prior 8-bar swing tolerance 0.15 ATR14, ATR ratio `[0.70,2.20]`, next-bar market entry, structural 1.20..2.80 ATR stop, 1.60R target, 0.90R BE and 12-bar time stop under the frozen risk/flat rules. This does not kill all rejection, reversal or price-action systems by name.
