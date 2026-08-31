# FXCM Pro Trade Tape source gate - 2026-08-13

## Status

- Verdict: `PASS_SOURCE_METADATA_BUT_HOLD_COST_CONTRACT`
- Object ID: `FXCM-PRO-TRADETAPE-RETAIL-TXN`
- Authority: source object only; no hypothesis ID, signal sign, horizon, EA,
  backtest or economic verdict is authorized.
- Scope: Forex/XAUUSD only. No signup, authenticated API, sample download,
  vendor contact, trial or purchase occurred.

## Why this is not the killed retail-positioning object

The inspected product is an anonymized, order-by-order tape of executed retail
transactions. Its documented fields are timestamp, symbol, signed long/short
quantity and transaction rate. That is materially different from a periodically
published stock such as percent-long, position buckets or aggregate client
sentiment. It must not inherit the sign, horizon or terminal verdict of
`KILL_RETAIL_POSITIONING_EURUSD_H1_H4_4H20H`.

This distinctness is a data-object verdict only. No evidence currently fixes
whether the tape should be followed, faded or transformed at any closed-bar
horizon.

## Official metadata that passed

Current FXCM Pro material states:

- the tape contains millisecond-timestamped retail trading transactions;
- order-flow history is available from 2017;
- it is offered across FX and CFD instruments;
- fields include `DateTime (EST)`, `Symbol`, `Quantity (Volume long or short)`
  and `Rate (Price)`;
- live delivery uses FIX 4.4 and updates order by order;
- a one-month anonymized CSV sample and a product sheet exist; and
- the page is intended for institutional/professional clients.

Official FXCM GitHub material separately publishes a one-month sample endpoint
and describes `DateTime (UTC)`, `Symbol`, `Quantity` and `Rate`. It says scope
may vary by product and the sample is for personal use under the FXCM EULA.

The official 26 February 2018 product sheet was then inspected as text and as
three rendered pages. For that documented vintage it resolves:

- `Quantity` is bought volume when positive and sold volume when negative;
- FIX tag 54 `Side` is `1=Buy`, `2=Sell`;
- `DateTime` and tag 60 `TransactTime` are execution time in UTC;
- the live schema lists tags 31, 32, 55, 60, 75, 570, 571, 54, 37, 1, 487,
  167, 15, 453 and 448;
- tag 487 defaults to `0` for new trades only; and
- its named samples cover July-December 2017 (sales) and January 2018
  (GitHub), establishing a 2017 lower bound for that vintage.

The PDF SHA256 is
`1F6C2496C601A78B686D4174E77238807698824E0AD0D1D21B5A4F25E3F457A9`.
This is schema evidence, not evidence that the current 2026 product still uses
the identical fields, clock, population or lifecycle policy.

Sources inspected:

- <https://www.fxcm.com/pro/market-data/trade-tape/>
- <https://www.fxcm.com/pro/market-data/>
- <https://github.com/fxcm/MarketData>
- <https://github.com/fxcm/MarketData/tree/master/Order%20Flow>
- <https://github.com/fxcm/MarketData/blob/master/Order%20Flow/Product%20Sheet%20-%20Orders%2002-26-18%20(no%20URL).pdf>

## Holds that prevent a hypothesis or build

1. The 2018 sheet documents bought-positive/sold-negative quantity and FIX Side
   1/2, but current fixtures have not proven that the 2026 product preserves
   this encoding.
2. `EST` on the current Pro page conflicts with UTC execution time in the 2018
   sheet and GitHub sample; current event time, received time and DST behavior
   are not bound.
3. The 2018 sheet and current Pro page support a 2017 lower bound/start, while
   another localized FXCM page has stated 2012. The current canonical start and
   whether 2012 names another product remain unconfirmed.
4. Historical CSV and live FIX identity is not proven for schema, population,
   version, cancels, partial fills or corrections.
5. `all FX and CFD instruments` does not name EURUSD and XAUUSD in a binding
   pair list for both historical and live products.
6. The exact population is one broker's retail transactions; coverage changes,
   regional mix and methodology/version history are undisclosed.
7. Price, minimum term, eligibility, retention after cancellation and written
   internal-use rights for a local MT5 ingest process are not public.
8. Two primary/peer-reviewed studies now support the broad fade-individual-
   investor-flow sign at intraday/daily horizons. They do not authorize a new
   FXCM child: the exact 3-hour/daily crossover and 20-hour hold duplicate the
   terminal retail-fade family, select published result cells and still lack
   current FXCM population identity. Vendor availability is not economic
   evidence.

The first fatal uncertainty is current-version identity: the 2018 sheet fixes
its own sign and UTC execution clock, but the current Pro page says EST and
does not prove that today's historical CSV/live FIX is the same schema,
population and lifecycle. A backtest cannot inherit an old schema silently.

## Exact vendor questions, not yet sent

1. Does the current product begin in 2017 as the 2018 sheet/current Pro page
   imply, or does the 2012 statement describe another product?
2. Are EURUSD and XAUUSD present in both the historical CSV and live FIX 4.4
   products for the full licensed period?
3. Does the current product retain the 2018 convention `Quantity > 0 = bought`,
   `Quantity < 0 = sold` and FIX Side `1=Buy`, `2=Sell`? Please provide at
   least five dated fixtures containing both sides.
4. Does the current product still use execution time in UTC as the product
   sheet states, or is the current Pro page's EST field authoritative? Please
   distinguish event time from received/publication time and specify DST.
5. Does current live FIX still use the 2018 tag list and tag 487 default, or is
   there a dated successor schema? Are current CSV and FIX the identical
   transaction population and methodology version?
6. What do current tags 487 and 570 mean operationally, and how are cancels,
   corrections, partial fills, duplicates and late records represented? Is
   revision/as-of history retained?
7. What is the written price, currency, minimum term and eligibility, and may a
   customer retain the licensed history and feed it into a local MT5 process
   for internal research/trading after cancellation?
8. Which agreement governs the paid feed: the personal-use sample EULA or the
   professional market-data terms?

## Decision

The source is not killed and the overall EA goal is not infeasible. It survives
as a second commercial source object beside CLS FX Spot Flow. It remains behind
a cost/contract and field-identity hold. Owner authorization is required before
sending the prepared inquiry; a reply and written quote would still unlock only
an outcome-blind source-intake gate, not an EA or profitability claim.

The exact paper-clone child
`FXCM-RETAILTXN-EURUSD-M5-3H24H-FADE-20H` is separately killed as
`KILL_DUPLICATE_TERMINAL_FAMILY`. This does not kill the vendor source object,
but it removes the current reason to request acquisition for that mechanism.

Prepared controls:

- unsent inquiry:
  `04. Memory/research/20260813_FXCM_TRADE_TAPE_VENDOR_INQUIRY.md`;
- frozen pre-outcome intake contract:
  `04. Memory/research/20260813_FXCM_TRADE_TAPE_INTAKE_CONTRACT.md`.
- mechanism reconciliation:
  `04. Memory/research/20260813_FXCM_RETAIL_FLOW_MECHANISM_RECONCILIATION.md`.

Grok Build independently returned the same
`PASS_SOURCE_METADATA_BUT_HOLD_COST_CONTRACT` verdict. Local official-source
review is controlling.
