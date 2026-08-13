# FXCM retail-flow mechanism reconciliation - 2026-08-13

## Status

- Source object: `FXCM-PRO-TRADETAPE-RETAIL-TXN`
- Source verdict: `PASS_SOURCE_METADATA_BUT_HOLD_COST_CONTRACT`
- Tested mechanism child:
  `FXCM-RETAILTXN-EURUSD-M5-3H24H-FADE-20H`
- Child verdict: `KILL_DUPLICATE_TERMINAL_FAMILY`
- No hypothesis ID, source sample, target price, PF, code, MT5 run, vendor
  contact, trial or purchase was opened.

## Primary evidence now established

Kaourma, Milidonis, Nishiotis and Panayides (JIFMIM 2025) use EURUSD retail
aggressive-order activity at five-minute frequency. Their field is:

`OrderFlow_t = DeltaLongOpenInterest_t - DeltaShortOpenInterest_t`.

They trade against retail flow: short when the 3-hour flow moving average
crosses above the daily moving average and long on the reverse cross. Signals
are non-overlapping and evaluated at fixed 4, 8, 16 and 20-hour horizons. The
paper reports both IS and OOS, but the proprietary anonymous-broker sample is
only July 2014-April 2016 and the strategy is explicitly a published grid, not
a new preregistration for FXCM.

Menkhoff, Sarno, Schmeling and Schrimpf (Journal of Finance 2016; BIS Working
Paper 405) use daily customer-initiated order flow from one dealer over
2001-2011. Portfolios that mimic individual-investor buying pressure have a
negative next-day spread of about 14% annualized and a Sharpe ratio of -1.55.
The paper's longer-horizon table shows the individual-investor negative effect
is strongest at short horizons and decays. The main result and longer-horizon
table were visually checked in the rendered PDF as well as extracted as text.

Sources:

- <https://doi.org/10.1016/j.intfin.2025.102146>
- <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3796753>
- <https://www.bis.org/publ/work405.pdf>

BIS PDF SHA256:
`FC0795A2F05B8024D0B3499358E18886043B21F5B91FAED4CFA678C4F17FD860`.

## Field-algebra correction

Grok initially claimed that signed FXCM executions could not equal the paper's
change in net open interest because openings and closures were mixed. Lead
rejected that claim. For customer-side quantity `Q`:

| Transaction | Signed execution | `DeltaLong - DeltaShort` |
|---|---:|---:|
| open long | `+Q` buy | `+Q` |
| close long | `-Q` sell | `-Q` |
| open short | `-Q` sell | `-Q` |
| close short | `+Q` buy | `+Q` |

Therefore signed customer executions are algebraically identical to the change
in net position. Passive versus aggressive orders change population selection,
not that identity. The 2018 product sheet's bought-positive/sold-negative field
is a valid conditional prior.

Grok accepted the correction as `PASS_CONDITIONAL_2018`. The remaining field
holds are current-version customer-side identity, passive/aggressive population
share, contract units, corrections/duplicates and historical/live parity.

## Why the exact child is still killed

The prior terminal object already froze fade-retail EURUSD at a 4-20-hour
horizon and prohibited rescue by vendor, threshold, crossover, timeframe or
hold-time substitution. The proposed child changes H1/H4 snapshots to M5 signed
transactions but copies the published 3-hour/daily crossover and selects 20
hours from the paper's reported 4/8/16/20 grid. That is a vendor/timeframe
rescue and a published-recipe clone, not a materially fresh mechanism.

The literature correction strengthens the retail-fade class; it does not erase
the prior terminal-family boundary. It also cannot distinguish a flow signal
from ordinary lagged-price momentum, because the 2025 paper finds retail flow is
mainly driven by lagged returns. A future materially new flow object would need
a frozen price-only control before target outcomes and would be killed, not
retuned, if flow adds no independent information.

## Decision

- `hypothesis_authorized=false`
- `build_allowed=false`
- `economics_authorized=false`
- `live_allowed=false`
- Do not code, backtest, alter the SMA windows/hold, change vendor or reopen the
  child.
- The FXCM source object itself remains alive only for contract/identity review.
  Its existence must not be presented as an EA candidate or economic edge.
