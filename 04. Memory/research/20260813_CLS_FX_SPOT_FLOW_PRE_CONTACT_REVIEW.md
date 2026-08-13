# CLS FX Spot Flow pre-contact review

Date: 2026-08-13

State: `PRE_CONTACT_REVISED_READY_OWNER_AUTHORITY_REQUIRED`

Source object: `CLS-FXSPOTFLOW-FUND-G10CS-DAILY`

External action: `NOT_PERFORMED`

## Official-source refresh

Current CLS materials were checked before any contact:

- https://www.cls-group.com/products/data/clsmarketdata/fx-flow/
  confirms that FX Flow remains an active commercial product, describes
  aggregate direction, aggressor and market-participant flow, and provides an
  official contact form.
- https://www.cls-group.com/media/djwj5lsd/clsmarketdata2-_-cls-group.pdf
  is the current 2026 overview. It states that FX Spot Flow is predominantly
  updated daily with hourly aggregation and is also available in a dynamic
  window every ten minutes. Average delivery is 15-30 minutes and longer delays
  can occur. Daily/hourly history begins 2012-09-03; dynamic history begins
  2022-07-10. Delivery is REST API or CSV through CLS Direct.
- https://www.cls-group.com/publications/clsmarketdata/
  and the current overview publish `enquiries@cls-group.com`. The older
  `data@cls-services.com` address appears only in older material and is not the
  selected route.

## Inquiry review

The six-question draft was revised before sending to:

1. use the current published recipient;
2. treat the 16:30 cut as an unanswered contractual requirement, not a public
   fact;
3. ask for machine-readable completeness plus holiday/incident status and the
   earliest supported final cut if 16:30 is unavailable;
4. separate raw-data retention from retention of derived signals/audit hashes;
5. request both internal research and conditional future internal-trading
   rights for one MT5 process;
6. require quote currency, taxes, setup/recurring fees, minimum term, seats,
   entitlements and overage charges in writing.

The revised draft remains outcome-blind and asks for no trial, credential,
sample payload or subscription activation.

## Grok Build red-team and Lead adjudication

Grok Build returned `REVISE_PRE_CONTACT`: the first draft did not force CLS to
identify whether its observation clock is trade execution, CLS submission,
matching or settlement date, nor prove that the historical daily object is the
same DST-aware 24-hour window ending 16:00 America/New_York as the dynamic feed.

Lead accepted this finding against frozen intake gate 6. Question 3 now locks
the exact timestamp field, timezone, window definition and historical/dynamic
identity. This is a source-clock correction before contact, not a signal,
horizon or outcome change. No other Grok suggestion was adopted.

After the exact R2 wording was applied, Grok Build returned
`PRE_CONTACT_PASS`. This is advisory corroboration; Lead's PASS remains based
on the local frozen intake contract and current official CLS materials.

## Verdict

`pre_contact_review_pass=true_after_r2_clock_revision`

`vendor_contact_authorized=false`

`purchase_authorized=false`

`hypothesis_authorized=false`

`outcomes_authorized=false`

`code_authorized=false`

`mt5_authorized=false`

The only next external action is Owner authorization to send the exact revised
draft in `20260813_CLS_FX_SPOT_FLOW_VENDOR_INQUIRY.md`. A response remains
metadata and must pass the frozen fifteen-gate intake contract before any new
hypothesis is opened.
