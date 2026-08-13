# Zero-cost official XAU/FX source frontier re-audit - 2026-08-13

## Scope and evidence boundary

- Outcome-blind search for one new official, free, retainable 2018-latest
  information object for XAUUSD or seven liquid FX majors on H1/H4/D1.
- Admission required a historical/live PIT contract, a documented mechanical
  target sign, a post-publication Friday-flat horizon and enough independent
  DESIGN/validation/holdout events.
- Price/indicator/session, CFTC/CME positioning and market data, central-bank
  liquidity, GDT, TFX, SGE/LBMA/GLD, SDR, news/sentiment and paid/vendor
  lineages were excluded because their exact local families are terminal.
- Grok Build searched official publishers only. Lead independently checked the
  nearest misses below. No payload, target price, outcome, code, MT5 run,
  subscription or purchase was opened.

## Nearest misses

### RBA Index of Commodity Prices

- Official archive and current releases:
  https://www.rba.gov.au/statistics/frequency/commodity-prices/index.html
- Official frequency and clock:
  https://www.rba.gov.au/statistics/tables/frequency-statistical-releases.html
- RBA publishes the monthly index on the first business day at 4:30 pm. The
  release uses preliminary estimates for recent bulk-commodity export prices,
  market/spot prices and periodically updated weights/rebases.
- The clock is usable, but the object aggregates commodity prices already
  traded before publication and is explicitly preliminary/reweighted. RBA
  defines no new post-print AUDUSD sign or H4/D1 Friday-flat horizon. Treating
  a positive index change as BUY AUDUSD would be external price momentum, not
  a mechanical publication shock.

### Bank of Canada Commodity Price Index

- Official data and methodology:
  https://www.bankofcanada.ca/rates/price-indexes/bcpi/
- BCPI is a chain Fisher index of spot or transaction prices in USD. Some
  inputs arrive weeks or months late; the latest observation is repeated until
  actual data arrive, and the series is revised. Component sources and weights
  have also been changed retroactively.
- Free weekly/monthly files do not preserve an original-print vintage chain.
  The field is a revised aggregation of already-public commodity prices and
  does not mechanically create a new USDCAD H1/H4/D1 shock.

### Japan Ministry of Finance intervention operations

- Official monthly/quarterly history:
  https://www.mof.go.jp/english/policy/international_policy/reference/feio/quarter/index.html
- Yen bought/sold is a near-mechanical USDJPY direction, but publication occurs
  after the intervention operations and therefore after their direct market
  impact. The small number of intervention days since 2018 cannot support
  independent DESIGN, validation and holdout samples. A later entry cannot
  repair stale information or sample insufficiency.

### Japan Ministry of Finance international securities transactions

- Official weekly/monthly history:
  https://www.mof.go.jp/english/policy/international_policy/reference/itn_transactions_in_securities/index.htm
- Official release schedule:
  https://www.mof.go.jp/english/policy/international_policy/reference/itn_transactions_in_securities/schedule.htm
- The weekly series has an explicit 8:50 am JST release schedule and data from
  2005. Transactions are recorded on execution date and describe the preceding
  week.
- A resident purchase of foreign securities does not uniquely prove a same-
  amount spot-JPY sale: purchases can be funded from foreign balances or FX-
  hedged, while the aggregate mixes security and investor types. The operation
  precedes publication and MoF specifies no post-print USDJPY direction or
  Friday-flat horizon.

### United States Mint bullion sales

- Official sales surface:
  https://www.usmint.gov/about/production-sales-figures/bullion-sales
- Totals are updated monthly and the page warns that published reports may not
  reflect later updates. No deterministic first-public HH:MM/vintage chain or
  mechanical global XAUUSD direction is defined. Domestic coin sales are not
  the global marginal gold-flow identity.

## Verdict

`NO_EXACT_ZERO_COST_OFFICIAL_CANDIDATE`

No inspected source combines an exact free PIT tape, unique target sign,
post-publication causal horizon and adequate independent sample. A conservative
later entry can cure clock uncertainty only; it cannot cure information already
acted on, revised price aggregates, FX hedging ambiguity or sparse events.

Do not download these sources, infer an AUD/CAD/JPY/XAU sign from target returns,
or reopen excluded families. This is a scoped source-frontier result, not a
global no-edge claim. The goal remains `ACTIVE / UNMET`; the next zero-cost
action is to audit prospective first-public collection rather than manufacture
another retrospective candidate.
