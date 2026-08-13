# HYP009 DESIGN Model-0 result

Verdict: **KILL_FROZEN_MAPPING**. Engineering is valid; economics are not.
Validation, holdout, optimization and deployment remain closed.

## Bound runs

- PRIMARY: AlphaFactory `20260813_104643`, EURUSD M1, Model 0,
  `[2019.01.01, 2021.01.01)`, exact frozen sign.
- REVERSE: AlphaFactory `20260813_104719`, identical contract with sign only reversed.
- Strategy Tester History Quality: 100% for both runs.
- Journal coverage: EURUSD synchronized from 1971-01-04 through 2026-08-05;
  one distinct valid D0 proof per run; journal not truncated.
- Runtime: zero init/runtime failures; 329/329 events accounted in each role.

## Frozen economic readout

| Arm | Trades | Net USD | PF | Expectancy/trade USD | Max DD |
|---|---:|---:|---:|---:|---:|
| PRIMARY base | 317 | -415.50 | 0.9147 | -1.3107 | 1.3909% |
| PRIMARY cost x1.5 | 317 | -1,627.25 | 0.7101 | -5.1333 | 2.1948% |
| PRIMARY cost x2 | 317 | -2,839.00 | 0.5582 | -8.9558 | 3.0869% |
| REVERSE base | 317 | -4,431.50 | 0.3846 | -13.9795 | 4.4668% |
| REVERSE cost x1.5 | 317 | -5,643.25 | 0.3005 | -17.8021 | 5.6484% |
| REVERSE cost x2 | 317 | -6,855.00 | 0.2377 | -21.6246 | 6.8550% |

PRIMARY years were 2019 `-$583.50` and 2020 `+$168.00`. The top 16 trades
contributed 37.93% of positive gross profit, above the frozen 30% cap. Removing the
five predeclared reduced-quality source cells remains losing (PF 0.9206) and is
diagnostic only.

The mechanism has directional information before complete cost: PRIMARY raw-mid
total was `+$2,008`, while REVERSE was exactly `-$2,008`. Execution cost was
`$2,423.50` in each role, erasing the gross signal. This is not a deployable edge:
cost x1.5 and x2 deteriorate sharply, and 2019 is negative.

## Native chart and log interpretation

- PRIMARY balance peaked early near EVT0020, fell to its worst cumulative point at
  EVT0223 (`-$1,242` from start in the cost ledger), then recovered `$826.50` but
  still ended below start. This is regime-fragile recovery, not stable compounding.
- REVERSE peaked only `$37` near EVT0005 and then decayed almost monotonically to its
  terminal loss. This confirms the frozen primary polarity is better, but insufficient.
- PRIMARY win rate was 42.90%; average winner `$32.77`, average loser `-$27.22`.
  Entry spread median was 0.2 pip and p95 0.8 pip; 102/317 trades incurred nonzero
  adverse dynamic-spread cost. One event, EVT0210, was an entry rejection in both
  roles and was accounted identically.
- Native balance evidence:
  `primary_native_balance.png` SHA-256
  `8EB817C80A2B83CEA9E3FC1121477CD0C71B76A2988F811608B0DECCEF300CF2`;
  `reverse_native_balance.png` SHA-256
  `2AE03C068D6F6B91CC02DF1A4199D90318E314347E166DF6D22C940999A64F00`.

## Failed gates and failure radius

Failed: base PF, base expectancy, x1.5 PF, x2 PF, x2 expectancy, both-years-positive,
and top-5% concentration. Passed: sample/cadence, drawdown and reverse inferiority.

Terminal failure radius is the exact HYP007 depth sign with T+60 entry and T+120
exit. It cannot be rescued by score threshold, event/session/day/direction filter,
cell exclusion, alternate timing/hold, SL/TP, trailing, sizing or renamed/recombined
variants. The only lawful next loop is a materially independent information mechanism.

Frozen analyzer: `economic_analysis.json`, SHA-256
`371A20E358A5AEDE0A0D348CEF68D111425BE71E518A354CD8C26BB20D831625`.

