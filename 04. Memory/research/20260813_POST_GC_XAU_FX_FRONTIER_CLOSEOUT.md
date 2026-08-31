# Post-GC XAU/FX frontier closeout - 2026-08-13

## Scope

This note records the outcome-blind frontier work immediately after the
terminal source-integrity verdict for `HYP-GC-OFI-INNOV-XAU-M5-003`. Grok deep
research was advisory; local source, de-duplication and authorization rules
remain authoritative. No target-price outcome, economic metric, MQL5 source,
MT5 run, optimization, paper trade or live trade was opened in this pass.

## Terminal source result carried forward

`HYP-GC-OFI-INNOV-XAU-M5-003` is terminal as
`KILL_SOURCE_INTEGRITY_HYP003`. The exact Q1-2019 source failed four frozen
conditions: 49,989 duplicate `(ts_event, sequence)` keys, 5,323 records with
fatal quality flags, A/B aggressor volume share 0.9860960694566356 below 0.99,
and 12 conflicting definition records. It may not be rescued by dropping
duplicates, ignoring flags or lowering coverage.

## Fresh frontier objects reviewed

1. **CME 6E versus OTC EURUSD completed-M5 basis catch-up**
   - Verdict: `KILL_6E_SPOT_BASIS_FRONTIER`.
   - Price-discovery evidence does not establish a fixed retail-tradable
     15-30 minute catch-up direction after both legs are already closed. The
     mapping also collapses into closed laggard/residual families.

2. **CME 6E MBO order-ID queue persistence/cancellation**
   - Verdict: `KILL_6E_MBO_ORDER_ID_FRONTIER`.
   - Order identity improves measurement but does not fix the continuation
     versus fade sign over the required horizon. The directly relevant effects
     are one-tick/sub-second, and a useful sequence-complete Q1 pilot was not
     shown to fit the standing sub-USD-10 source authority.

3. **General adversarial XAU/FX source frontier**
   - Verdict: `NO_CANDIDATE_XAU_FX_FRONTIER`.
   - The best reviewed objects were CFTC positioning, LBMA Gold Price and CME
     final settlement/delivery. They fail on horizon/cadence, lawful PIT source
     identity, or overlap with already closed settlement/fix residual logic.

4. **Cross-sectional common-USD aggressor flow from seven CME FX futures**
   - Verdict: `KILL_COMMON_USD_FUTURES_FLOW_FRONTIER`.
   - Averaging signed aggressor flow across 6E/6B/6J/6C/6A/6S/6N does not create
     a new causal field. It retimes and combines the same scheduled-event
     first-wave flow primitive already terminal in HYP013; the literature also
     does not prove persistence from +5 to +20 minutes after retail cost.

5. **EIA WPSR: CME CL aggressor flow to USDCAD**
   - Verdict: `KILL_CL_FLOW_USDCAD_FRONTIER`.
   - The long-run oil/CAD terms-of-trade mechanism does not establish the
     required sign from CL aggressor flow in `[0,+5m)` to USDCAD direction in
     `+5m` to `+20m`. EIA/oil microstructure studies stop at the oil market or
     use much longer FX horizons; the scalping-horizon sign is unproven and
     regime-dependent.

6. **Continuous non-event 6E signed-volume innovation to EURUSD**
   - Verdict: `KILL_CONTINUOUS_6E_FLOW_FRONTIER`.
   - The same-UTC-slot median/MAD transform is not an exact event-flow HYP013
     retiming, but it remains the same single-future aggressor-flow primitive
     in the continuation direction. Primary evidence supports contemporaneous
     impact or at most the next few minutes, not a reliable continuation from
     a completed M5 bar through the following 15 minutes after retail cost.
   - Trades/BBO capability and a possible sub-USD-10 narrow pilot were not the
     binding constraint. Because the same-sign, same-horizon evidence gate
     failed, no quote or purchase was authorized.

7. **Publicly disseminated CME 6E block trades to EURUSD**
   - Verdict: `KILL_6E_BLOCK_FRONTIER`.
   - CME blocks are privately negotiated bilateral trades. The public record
     has contract, price, quantity and time but no buyer/seller initiator or
     aggressor polarity. Price-versus-BBO cannot repair the sign because the
     displayed book may move during negotiation/reporting delay.

8. **CME 6E multi-level trade-through sweep reversal**
   - Verdict: `KILL_6E_SWEEP_REVERSAL_FRONTIER`.
   - Primary evidence does not support fading an observed sweep after its M5
     bar closes for the next 5-30 minutes. Book resiliency is mainly sub-minute
     to a few minutes; FX aggressor flow at longer immediate horizons more
     often represents permanent impact. Trades alone also cannot prove an
     uninterrupted multi-level sweep without contemporaneous depth or MBO.

9. **EBS Spot EURUSD primary-CLOB flow/resiliency**
   - Verdict: `KILL_EBS_SPOT_FRONTIER`.
   - CME DataMine EBS tick/Level 1/Level 2 Price and Deal histories require a
     formal Information License Agreement. CME publishes no verifiable
     sub-USD-10 one-shot quote for a useful historical/live-identical tape;
     the documented route is licensing/data-sales access. Sales contact or
      academic restricted access is not a quote.

10. **Fresh residual exchange/regulator source sweep V2**
    - Verdict: `NO_CANDIDATE_XAU_FX_FRONTIER_V2_LOCAL_CONFIRMED`.
    - The residual classes were COMEX gold warehouse stocks, LBMA clearing
      volume, CME FX Link and New York Fed primary-dealer statistics. Local
      primary-source review rejected Grok's unsupported claim that official
      COMEX history is necessarily incomplete, but none of the four classes
      passes fixed 5-30 minute sign, M5/M15 cadence, source-cost and de-dup gates
      together. Detailed audit:
      `04. Memory/research/20260813_GROK_XAU_FX_FRONTIER_V2.md`.

## Local primary-source verification

Lead did not promote Grok text into source authority. The following official
sources were checked independently:

- CME's FX block guide states that blocks are privately negotiated away from
  the competitive venue and that FX blocks are reported within 15 minutes:
  <https://www.cmegroup.com/education/articles-and-reports/fx-futures-and-option-block-reference-guide>.
- CME's Rule 526 advisory lists the information supplied privately to the
  Exchange. The conclusion that a public observer lacks initiator polarity is
  an inference from the public tape contract, not a claim that CME lacks the
  clearing-party records:
  <https://www.cmegroup.com/rulebook/files/cme-group-Rule-526.pdf>.
- CME's EBS Spot FX catalog documents real-time/historical delivery, one-second
  tick/Level-1 slices, 100-millisecond Level-2 slices and the required ILA:
  <https://www.cmegroup.com/market-data/browse-data/catalog/ebs-spot-fx.html>.
- The Federal Reserve EBS study documents high-frequency contemporaneous
  order-flow/return association, not the exact post-completed-M5 5-30 minute
  trading claim required here:
  <https://www.federalreserve.gov/econres/ifdp/order-flow-and-exchange-rate-dynamics-in-electronic-brokerage-system-data.htm>.
- CME publishes daily COMEX Gold Stocks reports and an official historical
  registrar page. This disproves neither a mechanism nor an edge; the V2 object
  failed because no fixed post-publication 5-30 minute XAUUSD sign was supported:
  <https://www.cmegroup.com/solutions/clearing/operations-and-deliveries/nymex-delivery-notices.html>.
- LBMA's public clearing series is monthly net-settlement data, not an M5/M15
  directional tape: <https://www.lbma.org.uk/prices-and-data/clearing-data>.
- CME defines FX Link as a spot/futures differential, which places it inside the
  already-reviewed basis family: <https://www.cmegroup.com/trading/fx/fx-link.html>.
- New York Fed primary-dealer statistics are released Thursdays for the prior
  week, not at a scalping decision clock:
  <https://www.newyorkfed.org/markets/counterparties/primary-dealers-statistics>.

## Database-first paid-cell audit

A latest-row registry scan for active-scope XAU/FX candidates with an existing
source estimate below USD 10 and no economic readout found only stale parent
states:

- `HYP-GC-OFI-INNOV-XAU-M5-002` is superseded by the terminal HYP003 source
  verdict;
- `HYP-EURFXOFI-EURUSD-M1-001`, `004` and `005` are superseded by the completed
  USD 2.117540538299 HYP006 acquisition and terminal 001..016/economic campaign.

Therefore no existing lawful sub-USD-10 source cell remains open for purchase.
The standing Owner authority was not consumed by this audit.

Machine-readable successor audit:
`04. Memory/research/20260813_POST_GC_XAU_FX_SUCCESSOR_CHAIN_AUDIT.json`
(`SHA256 D0631E3F2D5E6C81B39983047EE3371D6F32459C03E40C74DD23BC101C7AE2AE`).
It binds the registry snapshot, latest row/state, direct and terminal successor,
and closure reason for every source cell considered above.

## Authorization and economics boundary

- Source purchases made by this frontier pass: `USD 0.00`.
- New hypothesis IDs opened: `0`.
- Target outcomes inspected: `0`.
- Economic runs, MQL5 builds and MT5 backtests: `0`.
- Edge claim: `false`.

The goal remains `ACTIVE/UNMET`. A next attempt must use a materially different
information object, a fixed causal sign, exact PIT/historical-live source
identity, and a preregistered source/cost/outcome contract before any target
readout.
