# Sonic R post-ITSM source frontier closeout — 2026-08-12

Status: `NO_CANDIDATE_THIS_BOUNDED_FRONTIER_GOAL_REMAINS_ACTIVE`.

This checkpoint is pre-hypothesis and outcome-blind. Git is outside the active
goal path by Owner instruction. No new paid request, source payload, EURUSD
outcome, MQL5 build or MT5 run was opened by the work below.

## 1. CME 6E MBP-1 trades plus BBO

The existing `HYP-EVENT-L1-REPLEN-EURUSD-TICK-002` pilot remains valid source
semantics evidence: one exact `[T,T+120s)` payload contained 11,723 records,
2,163 trades, 9,401 BBO-size updates and 6,686 unchanged-price size updates.
It does not identify MBO queues, customers, dealers, icebergs or true refill.

The combined trades+BBO successor was rejected before a hypothesis ID:

- a 60-second signed-trade sum is a retimed HYP013 object;
- using signed flow to select BBO states is a post-hoc HYP013 filter;
- aggregate BBO-size changes cannot identify refill versus new limit orders or
  cancel/replace activity;
- the same observable state supports continuation and contrarian stories with
  equal ex-ante status.

Bounded Grok review returned `NO_CANDIDATE`. Lead verdict agrees. Do not buy the
quoted USD 1.191255122426 full-DESIGN MBP-1 corpus for this object.

A final, narrower closed-M5 draft matched aggressive executions at the current
best price to later same-price displayed-size increases and used
`min(executed, size_increases)` as an absorption proxy. It also failed before
counts or outcome access:

- TBBO cannot attribute a size increase to the liquidity just executed; the
  update may be a different order, cancel/replace, queue churn or receive-order
  ambiguity;
- bid/ask absorption still supports both fade and continuation stories, so its
  sign is not mechanically unique;
- the proxy becomes either a transform of HYP013 signed flow or a hidden gate
  on it, and `[T,T+300s)` to a `T+900s` exit exceeds the seconds-scale lifetime
  of the claimed queue mechanism.

Grok returned `NO_CANDIDATE`; Lead agrees. Do not mint an ID, run a counts-only
gate or decode EURUSD for this TBBO transform. True MBO/order identity is the
only lawful source-level reopen for an absorption/refill object.

## 2. USD-event CME 2-Year Treasury repricing

The clean 2019-2020 clock file contains 319 clusters: 234 USD-only and 85
EUR-only. The USD-only raw cadence is 2.2408/week, so cadence alone did not kill
the draft.

The draft compared a pre-release ZT midpoint with the last valid midpoint in
the minute before the closed `T+5m` decision. It was rejected before source
quote because:

- `ZT price down -> US yield up -> SELL EURUSD` is only one channel; risk-off,
  dollar-smile, EUR relative-rate and basis states can imply the opposite FX
  response from the same ZT move;
- the information object is event-conditioned cross-asset price momentum, not
  a new non-price source;
- by `T+5m` both ZT and EURUSD have absorbed the scheduled jump, leaving a
  post-jump continuation claim already adjacent to terminal price-momentum
  families;
- historical and live ZT BBO require a CME data path outside the FivePercent
  MT5 tape, so zero-cost train/serve identity is absent.

Bounded Grok review returned `NO_CANDIDATE`. No ZT metadata or payload call was
made.

## 3. CME 6E option trade flow

The option-pin definition fixed-point evidence is reusable only for PIT
identity; the normalized-OI hypothesis remains terminal. A fresh draft proposed
call/put plus aggressor-side contract flow over `[T,T+5m)`.

The draft was rejected before source quote because:

- aggressor side is not customer/dealer identity and does not reveal opening
  versus closing, hedge, conversion/reversal or multi-leg intent;
- one OTM weekly contract and one ITM quarterly contract do not carry equal
  delta, so raw contract-count aggregation is not the dealer-hedging object in
  the market story;
- adding a delta model, moneyness/expiry filter or outcome-selected weighting
  would be a new tuned rescue;
- without those missing fields the object is a 6E signed-flow cousin with a
  15-second to 5-minute retime, not a materially independent mechanism.

Bounded Grok review returned `NO_CANDIDATE`. No option-trades metadata or
payload call was made.

## 4. Relative-rate two-leg frontier

A synchronized USD-versus-EUR front-end-rate repricing object remains more
mechanically relevant than the rejected one-leg ZT draft, but the required
2019-2020 intraday source is not available on the lawful zero-cost surface:

- CME states that its EUR short-term-rate futures first traded on 2022-10-31,
  so the CME-only EUR leg cannot cover the 2019-2020 DESIGN period;
- ICE lists Three Month Euribor futures, while its developer data products are
  commercial historical/realtime feeds rather than a verified free individual
  train/serve path;
- Eurex labels static reference data free but lists intraday files as fee-based.

Official references:

- https://investor.cmegroup.com/news-releases/news-release-details/cme-group-announces-first-day-trading-eustr-futures
- https://www.ice.com/products/38527986/three-month-euribor-futures
- https://developer.ice.com/fixed-income-data-services/catalog/ice-futures-europe
- https://www.eurex.com/ex-en/data/trading-files

Do not replace the absent EUR leg with ZT-only, daily settlement, a different
post-event hold or an event-name subset. A paid/cross-vendor source contract
requires separate exact authority and still must prove live MT5 serve identity.

The older recommended `USD 17.00` ceiling is not a quote for this two-leg
relative-rate frontier. It covered a different, never-submitted Databento plan
for 38 CME 6E option parents plus `6E.FUT`: definition USD
`4.575774885714`, statistics USD `11.450830161572`, total USD
`16.026605047286`. No request, batch, download or charge occurred. That plan
must not be revived: the later normalized-OI option-pin lineage is terminal
because the sole authorized source mapping left `291/291` decision clocks with
unknown normalized OI.

## 5. Catalog guard

`EA_MultiAssetTSMOMD1V6/20260812_113422` appears in the runs catalog near PF
1.40, but the authoritative hypothesis artifact records native PF
`0.4853467684`, net `-$7,708.23`, `0/4` profitable years and one failed
transition. Its exact V6 weekly TSMOM identity is terminal. The catalog row is
discovery metadata only and cannot revive the run.

## 6. Final Build-mode source-frontier pass

After the local calendar, Treasury-auction, SOFR/EFFR, MBO, Kalshi and existing
Databento families were de-duplicated, the active Grok Build session received a
bounded pre-source packet. It was forbidden to write code, inspect target-price
outcomes, buy data or claim an edge. It returned `NO_CANDIDATE` after examining
the strongest remaining objects:

- an official-clock residual after the first closed M5 fails the required
  post-decision horizon: the supported FX reaction is contemporaneous/seconds,
  while a deterministic 5-30 minute continuation-versus-fade sign is not
  established and the clock overlaps the terminal event-flow/event-OCO radius;
- CFTC COT/TFF positioning is a weekly object with about one release per week,
  not a closed-M5/M15 information arrival for a 5-30 minute scalp;
- ZT/6E/ES post-print mid changes are forbidden cross-asset price momentum and
  their FX sign is not unique across rate, risk-off and basis channels; the
  required live CME feed is also outside the MT5-only tape.

Lead review agrees with the pre-hypothesis verdict. This pass authorizes no
hypothesis ID, metadata purchase, counts run, outcome read, MQL5 or MT5 run.
It also closes any attempt to revive scheduled release clocks without a new
PIT value object and exact post-closed-bar directional evidence.

Independent source check:

- Andersen et al. document announcement-surprise conditional-mean jumps, but
  do not establish a tradable residual beginning after the first closed M5:
  https://pubs.aeaweb.org/doi/10.1257/000282803321455151
- Evans and Speight report that EUR exchange-rate return reaction occurs within
  the first five minutes with very little reaction in the following 15 minutes:
  https://orca.cardiff.ac.uk/id/eprint/77683/
- CFTC states that COT is normally released Friday at 15:30 Eastern using the
  preceding Tuesday's positions, confirming that it is a delayed weekly object:
  https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm

## Verdict boundary

- Engineering-valid source semantics exist for the old L1 pilot only.
- None of the four new drafts is economic-valid because none lawfully opened
  an outcome.
- No object is promotion-ready, paper-ready or live-ready.
- The goal remains active. The next hypothesis requires a genuinely different
  PIT/live-serveable information object; absence of such an object is not
  permission to manufacture one from renamed price, flow, timing or filters.
