# Payment Park Closeout — HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002

Status: `PARK_DESIGN_SOURCE_PAYMENT_AUTHORITY_UNMET`

The strategy remains economically untested. This is a design-source payment
authority park, not a no-edge verdict and not a completed EA.

## Frozen design contract

- Parent `HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001` remains parked and unchanged.
- This successor keeps the same untested mechanism and economic gates, but
  narrows acquisition to 329 design clocks from 2019–2020.
- Exact segments per clock: PRE `[T-60s,T-15s)` and LATE `[T+45s,T+60s)`.
- Frozen design request count: 658; total requested duration: 19,740 seconds.
- Validation source for 2021–2022 and all EURUSD price outcomes remain sealed.
- Canonical preregistration SHA-256:
  `62A3AB66C64083D9967D91A0D634DEF29641AE7F3A05D3C59CBC153AAF4B3CBF`.

## Preserved free-quote evidence

- Immutable quote plan ID:
  `DEDDE7F292738C16A200C59903F7839C85B728818805AA09D46D3E7F188E0C16`.
- Estimated source cost: USD 3.141317501659.
- Estimated billable size: 6,745,927,968 bytes (6.282635 GiB).
- Coverage: 658/658 frozen PRE/LATE request identities.
- Free calls: 658 `metadata.get_cost` and 658
  `metadata.get_billable_size` attempts.
- Forbidden calls: zero dataset-range, symbology, time-series, batch and paid
  requests.
- Raw source state: zero DBN files and no download manifest.
- Immutable evidence manifest:
  `02. AlphaFactory/data/databento/cme_6e_event_clob_design_segments/evidence/FREE_QUOTE_DEDDE7F2/manifest.json`,
  SHA-256 `9C9AFE1898BB6A9155D693F44DB704C5B8984775A593BE3213411BBDC1AFB5E5`.
- The first free-quote attempt failed closed on an empty HTTP 500 response. Its
  sanitized failure artifact remains bound at SHA-256
  `6B3863373881624467A720AC05E6708D0D8C07E851C6B66B3831E2429F473930`;
  no remote outcome or paid call was opened by that failure.

## Current V12 guard

- Canonical registry: 271 rows / 90 hypotheses PASS, SHA-256
  `8621EDAFE31CF963C2C246DD5E52DC3F11E19DC8467F72E65A914942E45933CC`.
- HYP-002 history is the exact `idea -> probe -> parked` three-row sequence;
  latest row SHA-256
  `AAE0F493502C13EB8C75C9105C83C6B6F325043D59BBB120075063401C907C45`.
- V12 task packet SHA-256:
  `81D2A9DD4016F29D2A4BDFC041633D179D4623C743F65773E1FDC70B22F450CC`.
- Acquisition tool SHA-256:
  `7D2508BD72F6DBACC097378FEA5192E50FA639FB01F6F0332C28E1262A81B620`.
- Focused test file SHA-256:
  `B5A03BE2B260A0343206F0100EDAC800F7C96CF003A789E29DC30B1D5466ACC7`.
- Parent and independent reviewer runs: 104/104 PASS.
- Active V12 plan is offline only, ID
  `093ADD4AE4DCFEEA63558E0C23F3E246BE5889B9BB0D2DEB6B8D6D4B741446C1`,
  SHA-256 `96B74679902A85E4B58F5C6D43CBE0D6E27AA388CD1EA93E5EFBD91069602C2A`.
- Both CLI and direct production entry points reject design quote/download at
  the parked authority guard before API-key/client creation, registry validator,
  metadata access, target-root mutation, lock creation or time-series access.

The active quote receipt and storage assessment remain duplicate convenience
copies. Their hashes match the immutable evidence children; they do not grant
authority and are not raw market data.

## Reopen condition

The Owner must explicitly approve a positive USD ceiling. Recommended ceiling:
**USD 3.50**, about 11.4% above the final free quote, bound to exact plan
`DEDDE7F2...0C16`. A future authority amendment must require a fresh live
re-quote. If that re-quote exceeds USD 3.50, the workflow must stop before the
first paid call.

After authorized source acquisition, `.mq5` remains forbidden until Stage 0B–D
source coverage/cadence and both frozen economic splits survive. There is still
no price outcome, PnL, PF, expectancy, chart, compile, Model 0, promotion, paper
or live claim. The Owner goal remains active and UNMET.
