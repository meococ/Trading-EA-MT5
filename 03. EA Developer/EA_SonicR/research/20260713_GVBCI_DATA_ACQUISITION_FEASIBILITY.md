# GVBCI Data Acquisition Feasibility — 2026-07-13

Status: `GO_FOR_COST_QUOTE_ONLY / NO PURCHASE / NO DOWNLOAD`

## Minimum technical surface

GVBCI is not a generic futures-leads-spot rule. A legal data surface must
preserve the COMEX GC contract identity and basis state. The minimum request is:

- CME Globex MDP 3.0 (`GLBX.MDP3`);
- `GC.FUT` parent symbology, filtered to outright futures;
- point-in-time instrument definitions and expirations;
- one-second BBO for the full research window;
- trades for activity/roll evidence;
- a one-month MBP-1 pilot before considering every-update L1 for five years.

The frozen quote-only request is:
`03. EA Developer/EA_SonicR/research/preflight/v4_data/20260713_GVBCI_DATABENTO_QUOTE_REQUEST_V1.json`.

Databento documents that parent symbology `[ROOT].FUT` returns the product
family and that `instrument_class` separates outright futures from spreads:
`https://databento.com/docs/standards-and-conventions/symbology`.
Its definitions are point-in-time, while MBP-1 provides every top-of-book
update with `ts_event`, `ts_recv`, and venue sequence numbers:
`https://databento.com/docs/schemas-and-data-formats/mbp-1`.

## Lawful-use assessment

CME classifies quantitative research, strategy development, signal processing,
and time-series analysis as Category C-2 non-display use. Licensing and fees
depend on the declared application and usage:
`https://www.cmegroup.com/market-data/distributor/files/cme-group-data-licensing-policy-guidelines-and-non-display-licensing-faq-october-2024.pdf`.

CME DataMine is a lawful direct route, but ordering requires a use declaration,
license review, agreement acceptance, and payment setup. CME's ordering guide
explicitly includes non-viewable/non-display applications:
`https://www.cmegroup.com/tools-information/webhelp/data-services-portal/Content/Ordering-CME-Datamine-Products.html`.

Databento is also a licensed distribution route, but publisher restrictions
still apply. The exact research-use classification must be confirmed in its
License Manager before any download. No data may be redistributed from this
workspace.

## Affordability assessment

Databento's historical service supports pay-as-you-go requests with no
subscription requirement, an exact estimator, and programmatic cost queries.
Its current pricing page also advertises USD 125 of new-user historical-data
credits. The same page illustrates that USD 125 covers roughly 12 months of
MBP-1 or 16 months of trades for one CME product in its ES example, but that is
not an exact GC quote and must not be extrapolated as a purchase price:
`https://databento.com/pricing/`.

Therefore:

- `bbo-1s + definition + trades` is the cost-first five-year quote;
- MBP-1 is restricted to a one-month fidelity pilot initially;
- affordability remains `UNRESOLVED` until the provider returns an exact
  estimate for the frozen request;
- no Standard subscription is required merely to obtain a usage-based
  historical estimate;
- no purchase, API request that incurs data charges, or download is authorized
  without Owner approval.

## Timestamp and roll risks

- Use `ts_event` as the futures event clock and retain `ts_recv` and sequence.
- Do not use a vendor continuous series as the only source. Preserve raw
  contracts and point-in-time definitions so the roll rule can be audited.
- Do not choose the roll retrospectively from the best PnL. A separate prereg
  must freeze the roll rule using only decision-time activity/expiry data.
- No carry-forward is allowed at a decision bar. Spot and futures observations
  must both meet a frozen staleness bound.
- If the proposed rule becomes “COMEX moves first, XAUUSD catches up,” it is a
  duplicate of the closed lead-lag family and must be killed.

## Verdict

`GO_FOR_COST_QUOTE_ONLY`

The technically preferred first route is a Databento exact cost estimate for
the frozen request because it exposes the required definitions, BBO/trade
schemas, and timestamps through one historical API. CME DataMine remains the
direct fallback. Neither route is currently proven affordable, licensed for
this exact user/application, or locally available, so GVBCI remains blocked
from preregistration and probing.

