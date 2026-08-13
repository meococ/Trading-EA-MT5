# Post-EventDepth options and macro source frontier

- Recorded at UTC: `2026-08-13T04:07:08Z`
- Scope: XAUUSD or the seven FX majors; MT5 execution; no BTC; no Git.
- Status: `NO_CANDIDATE_THIS_PASS`
- Authority: source/formula review only. No target return, PnL, PF, payload
  purchase, code, compile, MT5 run, validation, paper or live authority.
- Grok Build session:
  `https://grok.com/c/04527241-cd90-4e7f-a3e2-ea182ddbe4c8?rid=c04241ec-b073-4ecd-9c55-7ffa1fe84ac0`

## 1. CME EUR/USD listed-option trade flow

Grok initially proposed `GLBX.MDP3` `trades + definition` for EUU options and
the raw rule `s * size`, where option type and aggressor side supplied the
sign. Lead rejected that mapping against the earlier frozen local guard.

Final Grok verdict: `REVOKE_OPTIONS_FLOW_CANDIDATE`.

Fatal boundary:

- documented trade `side` is aggressor side, not customer/dealer or
  opening/closing identity;
- an outright C/P print cannot be proven not to be one leg of a package;
- `trades` and `definition` expose no point-in-time option delta;
- strike and expiry alone cannot produce delta without an underlying price,
  volatility and rates;
- therefore raw call/put contract counts are not dealer delta and do not give a
  mechanically valid EURUSD side.

No metadata cost call or payload request was made.

## 2. CME EUR/USD CVOL skew

Object reviewed: official CME/CBA EOD family `EUVL`, `EUUP`, `EUDN`, `EUSK`,
`EUAM`, `EUCV`.

Final Grok verdict: `NO_CVOL_CANDIDATE`.

Lead correction after the Grok verdict: primary CME research publishes a fixed
directional interpretation for skew ratio `EUUP / EUDN`: above `1.0` and rising
is bullish sentiment; below `1.0` and falling is bearish. CME's separate
2007-2023 study says EURUSD tended, to a lesser extent, to follow that direction
over the subsequent three months. Absence of a mechanical sign is therefore not
the final kill reason.

Fatal boundaries:

- documented horizon is 30-day option expectation / three-month research, not a
  proven next-session Friday-flat holding rule;
- EOD benchmark and 15-second live stream are different calculation surfaces;
- November-2020 launch/backfill does not prove contemporaneous 2018-latest identity;
- August-2026 CME benchmark fee list prices delayed EOD internal
  display/non-display Data License at USD 2,000 per Licensee Group, far above
  standing sub-USD-10 authority. Zero-dollar distribution/device rows do not
  authorize EA internal non-display use.

Primary documentation:

- `https://www.cmegroup.com/market-data/cme-group-benchmark-administration/files/cvol-methodology.pdf`
- `https://www.cmegroup.com/market-data/cme-group-benchmark-administration/cme-group-volatility-indexes-faq.html`
- `https://www.cmegroup.com/datamine/quick-guide-custom-select.html`
- `https://www.cmegroup.com/insights/economic-research/2025/cvol-skew-ratio-can-options-offer-useful-insights-on-market-direction.html?source=rss`
- `https://www.cmegroup.com/insights/economic-research/2023/is-cvol-skew-a-leading-indicator-of-price-trends-in-commodities-bonds-and-currency-markets.html`
- `https://www.cmegroup.com/market-data/files/benchmark-data-fee-list.pdf`

No order, download or source spend was made.

## 3. Official macro valuation (PPP / REER)

Local de-dup found no prior PPP/REER EA lineage, but source novelty did not pass
the deliverable contract.

Final Grok verdict: `NO_MACRO_VALUATION_CANDIDATE`.

Fatal boundaries:

- OECD PPP is annual and revised; 2018-latest provides only about eight
  independent prints;
- ECB/BIS REER is a basket and monthly/slow, not a threshold-free bilateral
  EURUSD side;
- PPP/REER mean reversion is a multi-month or multi-year mechanism, while the
  Owner contract requires Friday-flat/no-weekend positions;
- cloning one monthly or annual print into many D1 entries would create a false
  sample size;
- original-print vintage identity for every 2018-latest row is not established.

No series payload or target price was downloaded.

## 4. COMEX registered/eligible stocks check

The official daily report exists, but the current failure catalog already
records the first fatal boundary: registered/eligible inventory and delivery
notices do not mechanically choose a post-release XAUUSD side. This lane was
not reopened or sent to an outcome scan.

## Decision

Options-flow, CVOL-skew and PPP/REER are terminal only for the exact source/sign/
horizon contracts above. They are not a global no-edge finding. No market
mechanism is active after this pass. A successor must introduce an information
object with all of: direct mechanical sign, point-in-time/revision semantics,
historical/live identity, enough independent observations, horizon compatible
with Friday-flat execution and a quote inside existing Owner authority. Do not
manufacture a candidate by retiming, thresholding, reweighting or repeating one
slow source print across many bars.
