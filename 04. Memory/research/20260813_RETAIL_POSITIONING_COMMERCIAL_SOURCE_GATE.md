# Retail positioning commercial source gate

Date: 2026-08-13

Object verdict: `KILL_RETAIL_POSITIONING_EURUSD_H1_H4_4H20H`

Overall EA goal: `ACTIVE / UNMET`

## Frozen scope

- Exactly one mechanism was audited without target outcomes: aggregate retail
  EURUSD positioning/order flow, traded contrarian from a closed H1/H4 bar with
  a fixed holding horizon inside 4-20 hours.
- Required source contract: retainable point-in-time history from 2018-latest,
  an accessible live feed with the identical field definition, documented
  timestamp/publication-lag/revision semantics, and at least 150 independent
  non-overlapping decisions before filters.
- Required evidence contract: two peer-reviewed or primary studies supporting
  the same action sign and approximately the same 4-20-hour or daily horizon.
- No signup, account opening, trial, purchase, authenticated API call, source
  payload, EURUSD return, PF, code, registry row, MT5 run or backtest occurred.

## Evidence gate

- Kaourma, Milidonis, Nishiotis and Panayides, *News and intraday retail
  investor order flow in foreign exchange markets*, Journal of International
  Financial Markets, Institutions and Money 101 (2025),
  https://doi.org/10.1016/j.intfin.2025.102146, studies proprietary minute and
  five-minute EURUSD retail flow. It reports return-contrarian retail behavior
  and positive simple crossover results for holding periods of 4-20 hours.
- That is a useful mechanism lead, but its proprietary field is not shown to be
  identical to OANDA position buckets or IG percent-long snapshots. The study
  also says the retail response is mainly driven by lagged returns. A public
  fade of the displayed retail book can therefore collapse into ordinary price
  momentum unless the independent flow contribution is separately identified.
- The inspected primary literature did not provide a second same-field,
  same-sign, same-horizon result that fixes `fade aggregate retail positioning`
  as distinct from following lagged EURUSD returns. Institutional/interdealer
  customer-flow findings are a different population and often a continuation
  rather than a fade sign.

## Source gate

- OANDA Forex Labs v1 documentation for `orderbook_data` documents snapshots
  and, depending on period, a bounded historical window. The already-verified
  local source record corrects the false claim that only 24 hours exist: the
  one-hour period can expose 20-minute snapshots with up to one year of
  history. That is still not a documented 2018-latest PIT tape.
- OANDA REST-v20 documentation advertises price history from 2005, but that is
  price history, not aggregate customer positioning history. Its account
  position endpoints expose only the authenticated user's own positions.
- IG's official REST reference exposes current client-sentiment endpoints, but
  no inspected official endpoint provides retainable 2018-latest sentiment
  history with a matching live/historical schema, publication lag and revision
  contract.
- The proposed object also mixes a stock (`percent long`, position-book
  buckets) with a flow (signed new transactions). Those are not interchangeable
  fields and cannot inherit the proprietary paper's sign without proof.
- No official commercial SKU, price or retention licence for the exact
  historical-plus-live 2018-latest object was found. There is therefore nothing
  admissible to escalate for Owner spending review.

## Grok cross-check and correction

Grok Build returned `KILL_OBJECT` for the same evidence/data-identity reasons.
It also stated that OANDA history was limited to 24 hours. Lead rejected that
detail against the newer local source audit: the correct bounded maximum is up
to one year for the documented one-hour period with 20-minute snapshots. This
correction does not change the terminal verdict because the frozen contract
requires 2018-latest history and live/history identity.

## Verdict and controls

The exact EURUSD H1/H4 retail-positioning contrarian object is terminal before
outcomes. The fatal conditions are both source identity and mechanism identity:

1. no official retainable 2018-latest PIT history of the same field delivered
   live; and
2. no two-source evidence lock separating fade-retail-flow alpha from a renamed
   lagged-price momentum rule at the frozen horizon.

Controls:

- `purchase_authorized=false`
- `hypothesis_authorized=false`
- `economics_authorized=false`
- `live_allowed=false`
- Do not scrape the current IG/OANDA UI, forward-fill a short snapshot window,
  mix stock and flow fields, or use the 2025 paper to authorize an OHLC momentum
  backtest under a retail-sentiment label.
- This is a scoped object kill. It is not evidence that the overall EA goal or
  every commercial information source is infeasible.
