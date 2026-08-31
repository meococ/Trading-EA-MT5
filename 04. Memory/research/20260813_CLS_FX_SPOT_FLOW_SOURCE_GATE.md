# CLS FX Spot Flow source and mechanism gate

Date: 2026-08-13

Source-object ID: `CLS-FXSPOTFLOW-FUND-G10CS-DAILY`

Source verdict: `PASS_SOURCE_METADATA_BUT_HOLD_COST_CONTRACT`

Hypothesis state: `NOT_AUTHORIZED`

Overall EA goal: `ACTIVE / UNMET`

## Frozen pre-outcome object

- Input is CLSMarketData FX Spot Flow for the fund counterparty segment, not
  broker OHLC, tick volume, retail sentiment, CFTC positioning or rates.
- Proposed target is one multi-symbol Forex EA operating a USD-major basket.
- For each pair, use matched fund buy-minus-sell spot volume over the 24 hours
  ending 16:00 New York, only when every required record was received by 16:30.
- Normalize quote orientation into foreign-currency buying pressure versus USD.
  Standardize each pair by the trailing 60 business-day flow standard deviation
  using past data only.
- At the first fully closed H1 bar at or after 17:00 New York, long the strongest
  standardized flow and short the weakest with equal risk. Rebalance daily; do
  not open Friday and flatten Friday 16:00 New York.
- No price-derived signal, threshold, session selector, direction filter, stop/
  target choice or outcome-selected pair is part of this source object.
- No API key, signup, vendor contact, trial, quote request, purchase, payload,
  target return, PF, code, registry row, MT5 launch or backtest was opened.

## Official source capability

Current CLS materials inspected:

- https://www.cls-group.com/products/data/clsmarketdata/fx-flow/
  confirms that FX Flow is an active product derived from executed trade data,
  provides direction of trade and aggregate price-taker/market-maker activity,
  and is intended for directional and alpha-generation analysis.
- https://www.cls-group.com/media/djwj5lsd/clsmarketdata2-_-cls-group.pdf
  is the current 2026 overview. It states that FX Spot Flow daily/hourly history
  begins 2012-09-03 and dynamic history begins 2022-07-10. The dynamic window is
  every ten minutes with average 15-30-minute delivery and possible longer
  delays.
- The same 2026 overview states that data can be accessed by REST API or CSV
  through CLS Direct. It identifies aggregate relationships including funds and
  banks, NBFIs and banks, corporates and banks, and provides purchased/sold
  volume plus trade counts.
- https://www.cls-group.com/publications/clsmarketdata/ and the 2026 overview
  publish the current product inquiry address `enquiries@cls-group.com`.
- The product has ample theoretical cadence. One cross-sectional decision per
  non-Friday business day from 2018-latest is far above 150 independent dates.

These facts establish that a real historical-plus-live commercial source exists
and that it is materially different from the exhausted local price-only shelf.
They do not establish subscription affordability or a lawful research licence.

## Mechanism and evidence gate

- Menkhoff, Sarno, Schmeling and Schrimpf, *Information Flows in Foreign
  Exchange Markets: Dissecting Customer Currency Trades*, Journal of Finance
  71 (2016), BIS Working Paper 405:
  https://www.bis.org/publ/work405.pdf
  uses more than ten years of daily customer flows, standardizes with a trailing
  60-day window, and forms dollar-neutral portfolios from lagged flow. Positive
  investment-manager buying pressure predicts next-day appreciation; individual
  investor flow has the opposite sign.
- Cuemacro/CLS, *Seeking the cues in macro markets*:
  https://www.cls-group.com/media/addcji41/20190510-cuemacro-going-with-the-fx-flow.pdf
  directly studies CLS fund flow. It uses a continuation sign, trailing
  standardization and a daily lag-controlled implementation. The daily basket
  was positive in the short April-October 2018 OOS shown in the paper; the
  hourly version was slightly negative OOS.
- The two sources agree at the mechanism-class level: follow lagged institutional
  investment-manager/fund flow at a daily horizon. This differs from closed D1
  time-series momentum and carry because the signed input is executed customer
  flow rather than prior price or interest differentials.

Evidence limitations remain material:

- Menkhoff uses one dealer's customer tape and LT/ST manager taxonomy, not the
  CLS funds-and-banks field.
- The Cuemacro OOS is only seven months, and its publication is a vendor-hosted
  research paper rather than an independent long live record.
- Class-level sign agreement cannot substitute for exact CLS field identity,
  historical/live revision parity or a fresh Model-0 on acquired data.

## Contract and implementation HOLD

The public documents do not prove:

1. the current price or smallest legal historical-plus-live subscription;
2. the exact pair list for the FX Spot Flow tier offered to this Owner;
3. whether the signed field is funds-only net buy-minus-sell or funds-versus-
   banks flow, and the quote sign for every USD-base versus USD-quote pair;
4. whether a timestamped received-by snapshot exists and a later historical
   daily file is byte/field-equivalent to what was known by 16:30 New York;
5. revision, late-trade removal and methodology-version semantics;
6. completeness SLA for the 16:30 cut and fail-closed status fields;
7. the right to retain the 2012-latest history after cancellation and feed it
   through a local adapter into one MT5 EA for internal research/trading.

The REST/CSV-to-MT5 path is feasible in engineering terms but is not native MT5.
It would require a separately reviewed local ingestor that writes immutable,
hash-bound snapshots for MQL5 consumption. No such adapter is authorized before
the source contract and Owner spend gate pass.

## Verdict and next gate

`CLS-FXSPOTFLOW-FUND-G10CS-DAILY` is the first object in this pass that survives
mechanism novelty, sign/horizon and theoretical sample gates. It is not an EA
candidate yet and has no economic verdict.

Controls:

- `source_metadata_pass=true`
- `owner_cost_review_required=true`
- `vendor_contact_authorized=false`
- `purchase_authorized=false`
- `hypothesis_authorized=false`
- `outcomes_authorized=false`
- `code_authorized=false`
- `mt5_authorized=false`
- `live_allowed=false`

Next safe action is Owner authorization to send the six exact questions in
`04. Memory/research/20260813_CLS_FX_SPOT_FLOW_VENDOR_INQUIRY.md` and obtain a
written quote. No signup, trial, payload or price outcome may be opened first.
Any later reply or sample must pass the frozen fifteen-gate contract in
`04. Memory/research/20260813_CLS_FX_SPOT_FLOW_INTAKE_CONTRACT.md` before a
hypothesis ID can be drafted.

Pre-contact refresh: the current recipient was corrected to
`enquiries@cls-group.com`. Grok Build identified, and Lead independently
accepted against intake gate 6, a missing observation-clock question. The R2
draft now requires exact execution/submit/match/settlement timestamp semantics,
timezone, DST-aware 16:00 America/New_York window identity and historical/live
parity. No contact has occurred.
