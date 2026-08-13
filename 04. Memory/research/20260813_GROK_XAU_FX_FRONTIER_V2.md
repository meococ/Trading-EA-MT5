# Grok XAU/FX frontier V2 - local audit (2026-08-13)

## Scope and verdict

The existing Grok session was invoked with the exact
`/deep-research-trading-meta5` skill for one additional outcome-blind frontier
pass. It was required to return one materially new XAUUSD or liquid-FX M5/M15
information object that passed de-duplication, fixed-sign, 5-30 minute horizon,
2018-current PIT historical/live identity, sample-size and one-shot sub-USD-10
source gates, or return no candidate. No target outcome, code or backtest was
authorized.

Grok returned `NO_CANDIDATE_XAU_FX_FRONTIER_V2`. Lead accepts the conclusion
only after the following local primary-source audit; Grok's word
"exhaustive" is not evidence.

## Local source audit

1. **COMEX gold registered/eligible stocks**
   - CME publishes daily Gold Stocks reports and an official historical
     registrar surface. Therefore Grok's assertion that free 2018-current
     machine-readable history is incomplete was not independently established
     and is not used as a kill gate.
   - The remaining fatal gate is mechanism evidence: neither Grok nor the local
     audit found two inspectable primary sources establishing a mechanically
     fixed, post-publication 5-30 minute XAUUSD sign after realistic retail
     costs. A daily inventory level alone does not choose a scalp side.
   - Official sources:
     <https://www.cmegroup.com/solutions/clearing/operations-and-deliveries/nymex-delivery-notices.html>
     and
     <https://www.cmegroup.com/clearing/operations-and-deliveries/registrar-reports.html>.

2. **LBMA clearing volumes**
   - LBMA describes the public series as the latest **monthly** figures for net
     transfers settled through LPMCL. It is not a decision-time M5/M15 flow
     tape and does not provide a mechanically fixed 5-30 minute side.
   - Official source: <https://www.lbma.org.uk/prices-and-data/clearing-data>.

3. **CME FX Link**
   - CME defines FX Link as the tradeable differential between OTC spot and FX
     futures and states that market data are available through commercial
     platforms. This is economically the already-reviewed spot/futures basis
     object, not a materially new causal field. The official page does not
     establish a useful one-shot historical/live-identical purchase below USD
     10.
   - Official source: <https://www.cmegroup.com/trading/fx/fx-link.html>.

4. **New York Fed primary-dealer statistics**
   - The official tool is updated Thursdays with the previous week's
     statistics. Positions, transactions and financing are therefore too stale
     and aggregated for a decision-time M5/M15 scalp, even though long history
     and machine-readable exports exist.
   - Official source:
     <https://www.newyorkfed.org/markets/counterparties/primary-dealers-statistics>.

## Lead verdict and authority boundary

`NO_CANDIDATE_XAU_FX_FRONTIER_V2_LOCAL_CONFIRMED`.

This is a source/sign/horizon frontier verdict, not a universal market no-edge
claim. It opens no hypothesis ID, source spend, target outcome, economic run,
MQL5 file, MT5 test, optimization, paper trade or live trade. Reopening requires
a materially different information object with its own primary-source evidence
and frozen source/cost/outcome contract; a renamed member of the classes above
is not sufficient.

