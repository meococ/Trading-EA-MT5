# HYP-GLDFLOW-XAU-M15-002 — Readout

Verdict: **KILL_AT_OFFLINE_PROBE**  
Build authority: **DENIED**  
Holdout/live authority: **NONE**

## Frozen train result

The deterministic official-basket reconstruction produced 1,005 usable
2021-2024 flow rows and 512 non-zero 2022-2024 creation/redemption events. All
512 events bound to the strictly next US trading day and produced a trade:
`3.2731` trades per elapsed calendar week, 208 long and 304 short.

| Measure | Matched momentum control | SPDR flow challenger |
|---|---:|---:|
| Trades / elapsed week | 512 / 3.2731 | 512 / 3.2731 |
| Gross PF | not a frozen control gate | 0.8618 |
| Gross net R | not a frozen control gate | -44.4045 |
| PF x1 / net R | 0.6039 / -157.5505 | 0.5565 / -180.4195 |
| PF x1.5 | 0.4879 | 0.4476 |
| PF x2 | 0.3924 | 0.3576 |
| Expectancy x1 | -0.3077R | -0.3524R |
| DD at 0.25% risk | 40.6463% | 48.5620% |
| Positive years | 0/3 | 0/3 |

Only 4 of 13 preregistered gates passed: minimum/maximum cadence plus long and
short counts. PF, net, expectancy, both stress gates, DD, year stability, PF
margin and net margin versus control all failed. The challenger lost before
cost and became worse after the frozen 82-point proxy, so missing commission or
slippage cannot rescue the conclusion.

## Interpretation

Lagged daily GLD primary creations/redemptions contain no usable next-US-
session directional edge under the frozen 1.5 ATR / 1.5R / four-hour contract.
They underperformed a weak matched momentum control. Do not reverse direction,
mine flow magnitude, smooth/z-score the series, veto years/days/hours, change
RR/hold/session, or open 2025+ under this family.

## Integrity and storage

- workbook SHA256:
  `8E7F1DA21C7169D1950F865731817E191E897E650454F9FA37AE5AD1CBD08C38`
- prereg SHA256:
  `2AC737A8AF279242866B900D7F96801ABDA11C0FBEB05B39CE04409053FAD86A`
- probe script SHA256:
  `86256DE626E090DE39191AED15E6AB9C72319060ACA9971CAD12410D4E33288E`
- probe result:
  `research/evidence/20260716_HYP_GLDFLOW_XAU_M15_002_PROBE.json`
- probe result SHA256:
  `0417DFE0DE8862E1F322996E8558087CBEADAAA2A1B79AA89F5A1E5531E0A866`
- `holdout_payload_cells_accessed=0`; XAU frame ends in 2024.
- portable terminal and data path were on `D:`; `FILE_COMMON` was not used.
- all four protected C roots were count/byte/metadata-identical before/after;
  terminal process count at closeout was zero.

No `.mq5`, EX5, compile, Strategy Tester run or live action was created because
the legally prior probe killed build authority.
