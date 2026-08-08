# HYP-RSF-USDJPY-M15-STATE-MODEL-015 - result

## Verdict

`KILL_NO_STABLE_DISCOVERY_EDGE`

Native M15 calculation reduced USDJPY spread/ATR pressure but did not preserve
the gross directional signal. The fixed-horizon five-indicator state-regression
family is therefore closed on both tested M5 and M15 resolutions. No 2023+
validation was opened.

## Census evidence

- AlphaFactory run `20260808_012351`, Model 0, USDJPY M15.
- History quality 100%; 124,360 bars; 110,725,834 ticks.
- 124,359 census rows, 58 columns, zero duplicate timestamps, missing cells or
  non-finite cells.
- Indicator-ready 124,360/124,360; entries/final closes 0/0.
- The economic analyzer's terminal `No trades found in report` occurred after
  the valid zero-trade artifacts were copied; no census rerun was performed.

Median observed spread/TB-ATR fell from 0.0769 on M5 to 0.0426 on M15; P90 fell
from 0.3548 to 0.1818. This confirms the timeframe change did reduce relative
friction as designed.

## Preregistered discovery

All six Ridge/shallow-HGB x 2/4/8-M15-bar cells and 72 train-threshold fold
evaluations ran. No cell survived. Best was Ridge/8 bars:

- 891 primary-threshold trades;
- cadence valid in three folds;
- gross PF 1.033297, gross +24.109663R;
- dynamic cost 135.531433R;
- net PF 0.862252, net -111.421770R;
- median yearly PF 0.830086;
- adjacent cadence PF 0.790278 and 0.908616.

Years 2019, 2020 and 2021 were net negative; only 2022 was positive. Unlike M5,
M15 already lacks meaningful gross edge before costs. Lower friction alone
cannot rescue it.

## Decision

No more fixed-horizon state regression, timeframe hopping, session mining or
feature deletion. The next legal object must change the target. A separately
preregistered first-hit barrier acceptance model may use the same discovery
census because it asks whether a direction reaches a causal price barrier
before invalidation, rather than predicting a terminal close. That target is
not evaluated here.

## Bound artifacts

- Census SHA256: `1FFA026BF50C431C87EC9EC9CE5DD7D17ABB26DBDB179680B8E75C5421642D2A`
- RunMeta SHA256: `41F34D8C7890EB034E1F61DDD20BA8578995A7E9EB7DCF6223E3D573337F7099`
- Report SHA256: `1A100CFB9676BD6C4F19539CAA0E5EDEAFD04016AA2F05F1009A7EB7E8C3AA84`
- Run manifest SHA256: `0D04DD3432039AB7608FBCBFB305833100E8E0B4276C9B66753B95833BB28D14`
- Results SHA256: `87F4A8C6C2DD8EDB8898BAD504A469199F69C3621BC88943897512CD2EA4CF63`
- Walk-forward folds SHA256: `AF846CFFD1F0C5B357E9774CFF5F9662FF8EFBA01CDF7A320622F92074377915`
- Feature diagnostics SHA256: `CCC0C7321966D525605F82D9EEFCB72A94580577CBCB9AF220CCDD6D988668E8`
- Failure diagnostic SHA256: `ED26FC5AF807745D574B805265FA2D1B134C697773990C439D806E8D484B678A`

