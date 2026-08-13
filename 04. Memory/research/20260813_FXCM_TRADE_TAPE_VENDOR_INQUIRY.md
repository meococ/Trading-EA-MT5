# FXCM Pro Trade Tape vendor inquiry - draft only

Status: `DRAFT_ONLY_NOT_SENT`

Intended recipient: `data@fxcmpro.com`

Subject: FXCM Pro Trade Tape historical/live data contract questions

Hello FXCM Pro Market Data team,

We are evaluating the FXCM Trade Tape for internal quantitative research and a
local MetaTrader 5 ingestion process. Before any trial, activation or purchase,
please provide written answers and a firm quote for the following:

1. Does the current product begin in 2017 as the 2018 product sheet and current
   Pro page imply, or does the published 2012 statement describe another
   product?
2. Are EURUSD and XAUUSD available in both historical CSV and live FIX 4.4 for
   the full licensed period?
3. Does the current product retain the 2018 product-sheet convention
   `Quantity > 0 = bought`, `Quantity < 0 = sold`, and FIX Side `1=Buy`,
   `2=Sell`? Please provide at least five dated fixtures containing both sides.
4. Does the current product still use execution time in UTC, or is the current
   Pro page's EST field authoritative? Please distinguish event time from
   received/publication time and specify daylight-saving handling.
5. Does current live FIX still use the 2018 tag list and tag 487 default, or is
   there a dated successor schema? Are current CSV and FIX generated from the
   identical transaction population and methodology version?
6. What do current tags 487 and 570 mean operationally, and how are cancels,
   corrections, partial fills, duplicates and late records represented? Is
   revision/as-of history retained?
7. Please quote the price, currency, minimum term and customer eligibility, and
   confirm in writing whether the licensed history may be retained and used by
   a local MT5 process for internal research/trading after cancellation.
8. Which agreement governs the paid feed: the personal-use sample EULA or the
   professional market-data terms?

Please do not activate a trial, create credentials or start a subscription in
response to this inquiry.

Regards,

[Owner name]
