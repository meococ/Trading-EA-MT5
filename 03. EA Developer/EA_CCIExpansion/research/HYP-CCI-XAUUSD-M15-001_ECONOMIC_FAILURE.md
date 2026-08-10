# HYP-CCI-XAUUSD-M15-001 — economic baseline failure

Verdict: `KILL_BASE_PF_EXPECTANCY_AND_YEAR_CONCENTRATION_FAIL`.

## Evidence integrity

- Sole run: `02. AlphaFactory/runs/EA_CCIExpansion/20260810_222415`.
- Source SHA256: `D08999121732CA3B42BBE4125A3FD7D089734364E56D6F3F1F9D6F3A8780EE65`.
- Run manifest SHA256: `517489F42AEA1EF84189892FAE2DD2FD6F88DE558DB8A2B1646E6686AD53EA3D`.
- Report SHA256: `16045269BBCFC0D745E81EBDBEE400A8E1F6479717B97E1FE44006B34CC1EC50`.
- Tester journal SHA256: `70F27C996B9514F12FE57552F4E293EA5B877AB0F36D95F0529646C43FF4B12F`.
- History Quality 99%; full fixed-window DQ gate passed. Journal raw bytes `2,193,630` from three sources, `truncated=false`.
- Two duplicate journal summaries are identical: closed bars 117,789; raw signals 11,109; long 5,604; short 5,505; entries 589; clock rejects 82; invalid 0; `runtime_failed=false`. No fatal marker.

## Frozen baseline result

- 589 completed positions: 338 BUY and 251 SELL.
- Gross winning P/L `$12,704.49`; gross losing P/L `$19,709.97`; report commission `-$518.95`; swap `$0.00`.
- Profit factor `0.6445717573`; net `-$7,005.48`; expectancy `-$11.893854` per position; win rate `39.8981%`.
- Equity drawdown `7.0193%`.
- Cadence `589 / 260.857143 = 2.25794` positions/week passes the 2–5/week gate.
- Entry years: 2018 `258`, 2019 `258`, 2020 `73`, 2021 `0`, 2022 `0`; max-year share `43.8031%` fails the 30% gate.

## Failure radius

The exact native CCI20 typical-price expansion through `+100/-100`, five-bar plus `0.20*ATR14` stop, `1.50R` target, 12-bar exit and one-entry/day mapping has no positive TRAIN expectancy after tester spread and commission. The frozen peak-drawdown lock stopped later entries; removing it after seeing the outcomes would be a post-hoc rescue and is forbidden.

Do not reuse this result to select session, hour, weekday, direction, CCI threshold/period, price type, stop/target/hold, daily cap or drawdown-lock changes. Do not run cost stress, optimization, validation, OOS or holdout for CCI001. A successor must preregister a materially different market mechanism before outcomes.
