# HYP-RSF-EURUSD-M5-STATE-TRANSITION-013 - result

## Verdict

`KILL_NO_STABLE_TRANSITION_EDGE`

Changing the decision clock from simultaneous indicator levels to indicator
transitions improves the best discovery result, but the five-indicator event
surface still has negative expectancy after observed costs. The sealed
2023-and-later validation period was not opened.

## Frozen object tested

The test reused the bound 2018-2022 EURUSD M5 census from AlphaFactory run
`20260808_004517`. It evaluated the preregistered union of AIRD regime changes,
VRC regime changes, MBB releases/signals, TB SMC structure-state changes and QQE
state/zero crossings. Models received levels, 1/3-bar deltas and causal event
ages. No family, direction, year or session was removed after seeing outcomes.

Event counts were AIRD 4,354; VRC 28,386; MBB 45,283; TB 318,377; QQE 82,318;
union 334,457. The high TB count shows that its cell/void side changes act more
like a dense structural state stream than a sparse entry trigger.

## Discovery result

Six cells were evaluated: Ridge and shallow HistGradientBoosting at 3, 6 and
12 M5 bars. There were 24 expanding-year model fits and 72 train-threshold/test
fold evaluations. Every trade paid the observed spread times
`1.5 + 0.15 * (1 + VRC volatility percentile / 100)`.

No cell survived. The best cell was Ridge/6 bars:

- 778 primary-threshold trades across 2019-2022;
- cadence valid in all four yearly folds;
- pooled PF 0.820672;
- median yearly PF 0.892581;
- pooled net -114.892904 normalized ATR-R;
- adjacent cadence thresholds PF 0.798925 and 0.777095.

This is better than STATE-MODEL-012 but remains clearly below break-even and
fails both the primary PF and adjacent-threshold stability gates. It is not a
near miss that may be rescued by session or direction mining.

## Failure radius

This terminal decision applies to the exact EURUSD M5 five-indicator transition
union and its six frozen directional-return cells. It does not establish that
the indicators are useless on another symbol/timeframe, or for a different
causal target such as volatility expansion. Any such test requires a fresh ID,
fresh preregistration and pair-specific costs; it may not use 2023+ data.

## Bound artifacts

- Parent census SHA256: `2E24166F486D7073C4E98C452290372E4604D2C566BAD822F4FDC38E0E46D2BB`
- Discovery results SHA256: `CBF43C04338BD2EDF9E49E6C4064BCD8CAB65B6D4204B6B6435BF649ACAC82FC`
- Walk-forward folds SHA256: `78F3BC8AAF4F92C807EFB12A8ACA8D8447085569D6CACEAEDC0F919F28FACBDE`
- Feature diagnostics SHA256: `0E6BE4C1CAF5D878CF452A280E7FCB95A176B355F66BF23489518B760D362064`

