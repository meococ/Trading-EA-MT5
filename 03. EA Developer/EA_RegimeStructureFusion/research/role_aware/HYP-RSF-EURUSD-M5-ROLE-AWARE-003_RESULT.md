# HYP-RSF-EURUSD-M5-ROLE-AWARE-003 — terminal result

Status: `KILLED_NEGATIVE_EXPECTANCY`

## Frozen test

- EURUSD M5, 2018-01-01 through 2022-12-31, Model 0, 100% history quality.
- Run: `02. AlphaFactory/runs/EA_RegimeStructureFusion/20260807_064845`.
- Exactly one economic trial; no optimization, validation, holdout or route deletion.
- Mechanism: AIRD state/ambiguity, VRC volatility permission, TB direction and
  stored level, MBB location/objective, and QQE only after a later price event.

## Economic result

| Metric | Value |
|---|---:|
| Trades | 89 |
| Profit factor | 0.6791 |
| Net profit | -3,093.87 USD |
| Max drawdown | 3.653% |
| Win rate | 37.1% |
| Expectancy | -34.76 USD/trade |
| Mean achieved R | -0.1834R |

Raw PF is below 1.0, therefore the frozen immediate-kill rule applies before
cost stress, parameter search, validation or holdout access.

## Causal funnel

- 1,728 role-aware setups armed; 89 confirmed (5.2%).
- 1,219 arms expired (70.5%), 420 cancelled, and 95 breakout retests occurred.
- AIRD ambiguity rejected 10,379 candidate states.
- Trend supplied 1,492 of 1,728 setup events and 77 of 89 executed trades.
- Range supplied 90 setup events but zero executions. The causal range route did
  not become an economic engine.

## Route and stability diagnosis

| Route | Trades | Net USD | PF | Win rate |
|---|---:|---:|---:|---:|
| Trend long | 44 | -1,789.39 | 0.6356 | 36.4% |
| Trend short | 33 | -1,245.07 | 0.6505 | 36.4% |
| Breakout long | 6 | -227.84 | 0.6813 | 33.3% |
| Breakout short | 6 | +168.43 | 1.3716 | 50.0% |

The six-trade breakout-short slice is descriptive only and cannot be selected
post hoc. Year PFs were 0.716, 0.443, 1.130, 0.292 and 1.239 for 2018–2022.
The mechanism therefore alternated between regimes rather than maintaining a
stable edge. Europe PF 0.66 and New York PF 0.71 both failed; timezone pruning
would be result-mining, not pair-specific optimization.

## Failure radius

The role-aware ordering fixed the semantic defect found on the seven native
MT5 loser charts, but it did not create independent predictive information.
The trend route still asks lagged price transforms to forecast continuation,
then pays approximately one full risk unit when continuation fails. With a
1.50R target the break-even win rate before costs is about 40%; observed trend
win rate was 36.4% in both directions.

This failure invalidates threshold rescue, session deletion, direction deletion
and selection of favorable years under this ID. A successor must change the
economic event being traded. The admissible direction is a fresh structural
liquidity-event hypothesis where TB sweep/reclaim and displacement are the
primary causal event; AIRD/VRC may veto hostile state, MBB defines location and
objective, and QQE cannot delay entry until a zero-cross consensus.

## Evidence hashes

- Source: `B1E0B19A7985B664A09C198610AA6696ECC699ABAF9DF16D9604AB06F936784E`
- Contract receipt: `DF70D666B09FD56E95A17AA05613AAD8C146ED0A794B3089F5156155226B56BF`
- Run manifest: `9085618E4B85D5539B7A90C5D9B70C5107814EE22DF23BBB3822048E012F2797`
- Report: `39EBFC36380B5A9B7E4FD8BA684A0F84F870F53F2D94AA899F646C567124876F`
- Lifecycle: `2CE1C5BE27321820D5A59F7D0C89DB90C3D354CB47C6AA07D4979D8C03E0A64A`
- Run meta: `C1B61F84AFEC64D90ECF1CFBFCE55E55FDF746C8DDD23C7FF8CD4721E7B8457F`

Engineering-valid: yes. Economic-valid: no. Promotion-ready: no.
