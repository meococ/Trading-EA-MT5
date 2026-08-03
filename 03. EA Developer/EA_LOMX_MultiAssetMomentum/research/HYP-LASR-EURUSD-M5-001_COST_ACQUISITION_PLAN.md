# HYP-LASR-EURUSD-M5-001 - Frozen Cost Acquisition Plan

Status: `FROZEN_OUTCOME_BLIND_COST_BUILD_ONLY`

No HYP-LASR-EURUSD-M5-001 performance run or outcome exists when this plan is
frozen. It authorizes deterministic cost-evidence construction only.

## Identity and immutable inputs

- Symbol/timeframe: `EURUSD M5`
- Design universe: `2016.01.04` through `2024.12.31`
- Training-control cost window: `2016.01.04` through `2022.12.30`
- Broker/server: `Five Percent Online Ltd` / `FivePercentOnline-Real`
- Geometry: digits `5`, point `0.00001`, pip size `0.0001`
- Raw-tick M5 spread source:
  `research/evidence/HYP-LASR-EURUSD-M5-001/COST_SOURCE/EURUSD_M5_RAW_TICK_SPREAD_SOURCE.csv`
- Raw-tick source SHA-256:
  `A1C0983889C439984C6B3F4A4D93B3D888DDE0643D99AA1E71B9E57A06E115D3`
- Coverage receipt SHA-256:
  `034728C2B5BAD520E8DAA41B2CEB0E03A51122D724ECF27885BF50AA178F6574`
- Coverage: `521799 / 521865 = 0.9998735305107643`
- Quote root: `02. AlphaFactory/evidence/execution/FivePercentOnline-Real`
- Tester commission source:
  `02. AlphaFactory/runs/EA_LondonNY/20260702_224423/logs/EURUSD_20260403_PX6_Trades_20210101_000000_141232468.csv`
- Tester commission source SHA-256:
  `A0B0D213FA4DF8E8A4751FD9686E1F7B453DF39CFCCFAB971503A476279C2C7F`
- Builder SHA-256:
  `A62B423F8E10A386A924BED6E8F6A2FC1587311EC2BA4E1210CEA3BADC189207`

## Frozen construction

- Quote-latency proxy: symmetric 1000 ms adverse executable-quote movement,
  maximum quote wait 500 ms.
- Commission statistic: maximum complete same-symbol Strategy Tester lifecycle
  cost per lot; at least 30 lifecycles required by the builder.
- Historical spread: first valid raw BID/ASK tick inside each synchronized M5
  bar, exact 2016-2022 training-control window.
- Outputs live under
  `research/evidence/HYP-LASR-EURUSD-M5-001/COST_SOURCE/`.

## Restrictions

The quote latency is not an observed fill and the commission source is a tester
simulation. Therefore the result is a research proxy only:
`promotion_eligible=false`, even if a later economic control passes. No PnL,
PF, cadence, optimizer, validation, holdout, paper, or live access is authorized
by this plan.
