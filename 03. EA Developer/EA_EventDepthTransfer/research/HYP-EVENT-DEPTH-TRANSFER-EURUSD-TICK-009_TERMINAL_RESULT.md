# Event Depth Transfer HYP008/HYP009 terminal result

Verdict: `KILL_FROZEN_MAPPING`  
Economic-valid: `false`  
Validation/OOS/paper/promotion/live: `not authorized`

## Evidence order

HYP008 PRIMARY completed before the HYP009 preregistration timestamp. The HYP009
claim that it was frozen before HYP008 outcomes is therefore false. HYP009 adds a
read-only D0 series proof but does not introduce a new mechanism, signal, timing,
cost model or economic mapping. Its PRIMARY/REVERSE pair can confirm the terminal
result, but cannot reset outcome blindness or rescue the mapping.

Both roles are engineering-valid: 329/329 events accounted, 317 closed trades,
11 frozen zero-source events, one entry rejection, zero exit rejects, maximum one
position, runtime failure false, and exact PRIMARY/REVERSE identity/tick/sign
pairing. Strategy Tester History Quality is 100%.

## Frozen economic readout

| Gate | PRIMARY result | Verdict |
|---|---:|---|
| Completed trades | 317 | PASS |
| Cadence | 3.04/week | PASS |
| Base PF | 0.9147255003 | FAIL vs 1.30 |
| Base expectancy | -USD 1.3107/trade | FAIL |
| Base net | -USD 415.50 | FAIL |
| 1.5x cost PF | 0.7101184644 | FAIL vs 1.25 |
| 2x cost PF | 0.5582010582 | FAIL vs 1.00 |
| 2x expectancy | -USD 8.9558/trade | FAIL |
| 2019 / 2020 base net | -USD 583.50 / +USD 168.00 | FAIL both-positive |
| Base equity DD | 1.3909% | PASS vs 8% |
| Top 5% positive-profit share | 37.9291% | FAIL vs 30% |
| REVERSE base PF | 0.3846420885 | inferior, but not a rescue |

REVERSE is also strongly negative: base net `-USD 4,431.50`, expectancy
`-USD 13.9795/trade`, and both DESIGN years lose.

The five reduced-quality source cells cannot rescue the result. Excluding them
diagnostically leaves PRIMARY base PF `0.9206184497`, still terminal.

## Terminal rule

Do not add session/day/hour filters, thresholds, score magnitude, direction
selection, SL/TP, alternate hold, sizing changes or another data-proof successor.
Do not rerun PRIMARY or REVERSE. The exact CME 6E depth-transfer/T+60/T+120 family
is closed at this mapping. Continue the overall EA goal only through a materially
different information set or mechanism.
