# Draft vendor inquiry - CLSMarketData FX Spot Flow

Date prepared: 2026-08-13

Status: `DRAFT_ONLY_NOT_SENT`

Revision: `R2_PRE_CONTACT_OFFICIAL_SOURCE_REFRESH`

Recipient currently published by CLS: `enquiries@cls-group.com`

Recipient verification: the current 2026 CLSMarketData overview and publication
page both publish `enquiries@cls-group.com`. The older
`data@cls-services.com` address is not used for this draft.

Subject: CLS FX Spot Flow historical and dynamic data for internal quantitative research

## Ready-to-send draft

Hello CLSMarketData team,

I am evaluating CLS FX Spot Flow for internal quantitative research and a local
MetaTrader 5 execution process. I am not requesting a trial or activating a
subscription at this stage. Please provide written answers and a quote for the
smallest product configuration that covers the following requirements:

1. Confirm the earliest available date for FX Spot Flow and the exact USD-major
   currency-pair list included in the proposed subscription.
2. Confirm the exact signed fields for the fund segment: does the product provide
   funds-only bought and sold volume, funds-versus-banks directional flow, or
   both? Please provide the data dictionary and quote/sign convention for every
   pair, including USD-base pairs such as USDJPY, USDCAD and USDCHF.
3. Confirm historical versus dynamic schema, taxonomy and methodology identity,
   plus revision and late-match policy. State the exact timestamp field and
   timezone defining each daily, hourly and dynamic observation: trade
   execution time, CLS submit time, match time or settlement date. Confirm
   whether the historical daily series from its first date is a DST-aware
   24-hour window ending 16:00 America/New_York on that same timestamp and is
   identical to the live/dynamic feed.
4. CLS's current overview says the dynamic window is updated every ten minutes,
   with average delivery of 15-30 minutes and possible longer delays. For a
   24-hour window ending 16:00 New York, can the feed provide a machine-readable
   completeness/received-by state by 16:30? What contractual SLA, holiday and
   incident status apply, and how are late or incomplete records marked? If
   16:30 is not supportable, what is the earliest documented final cut? Does the
   later daily historical file preserve exactly what was available at that cut,
   or is it revised?
5. Confirm REST API and CSV delivery terms, request limits, authentication,
   historical bulk-download support, and whether downloaded 2012-current raw
   data plus internally derived signals and audit hashes may be retained after
   cancellation for internal research/audit.
6. Confirm that an internal local adapter may transform the licensed data into
   hash-bound files consumed by a single MT5 process for internal quantitative
   research and, only if later validated, internal trading, without external
   redistribution. Please quote the lowest historical-plus-dynamic
   configuration, including quote currency, taxes, setup and recurring fees,
   minimum term, seats, API/CSV entitlements and any usage or overage charge.

Please do not activate a trial or subscription in response to this inquiry.

Thank you.

## Controls

- This draft has not been sent.
- Sending it is an external action and requires explicit Owner authorization.
- The current public source supports only product capability and contact-route
  verification. It does not establish price, licence rights, SLA, schema or
  source-intake PASS.
- A reply or quote does not authorize purchase, API access, hypothesis creation,
  price-outcome access, code, MT5 backtest, paper trading or live trading.
