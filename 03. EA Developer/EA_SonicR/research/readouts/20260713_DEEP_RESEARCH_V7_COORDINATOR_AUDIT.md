# Deep Research V7 Coordinator Audit — 2026-07-13

Status: `NO_LEGAL_H4_D1_CANDIDATE_CONFIRMED / FRONTIER_STOP / NO_EA_BUILD`

## Binding

- ChatGPT conversation:
  `https://chatgpt.com/c/6a55088f-89b4-83ec-97b2-54a3a185ccb5`
- Report title: `Deep Research V7 FX`
- Model headline: `NO LEGAL H4/D1 CANDIDATE`
- Scope packet:
  `03. EA Developer/EA_SonicR/research/20260713_NEW_STRATEGY_DEEP_RESEARCH_SCOPE_EXPANSION_V7.md`
- Submission receipt:
  `03. EA Developer/EA_SonicR/research/preflight/20260713_NEW_STRATEGY_DEEP_RESEARCH_SUBMISSION_V7.json`
- Pre-result local de-dup baseline:
  `03. EA Developer/EA_SonicR/research/readouts/20260713_V7_H4_D1_LOCAL_DEDUP_BASELINE.md`
- Result receipt:
  `03. EA Developer/EA_SonicR/research/preflight/20260713_NEW_STRATEGY_DEEP_RESEARCH_RESULT_V7.json`

## Model result

V7 found no independent H4/D1 mechanism that simultaneously preserves the
primary-source causal variable, maps to the allowed retail MT5 surface, avoids
the frozen V2–V6/local families, and has a structural path to the pooled
2–5-trades-per-week target.

The strongest medium-horizon FX families were:

1. signed interdealer/customer order-flow information assimilation;
2. carry/funding and global-volatility risk;
3. FX liquidity state and liquidity risk;
4. portfolio rebalancing/equity-hedging flow;
5. price-only momentum or reversal.

Families 1–4 require causal state variables outside the V7 data contract.
Family 5 is observable but explicitly duplicates frozen momentum, reversal,
trend, rank, and path-dependence families. Slowing the decision horizon from
M5–H1 to H4/D1 does not repair either problem.

## Primary-source audit

| Family | What the source actually uses or establishes | V7 transfer verdict |
|---|---|---|
| Order flow | Evans and Lyons define order flow as net buyer- versus seller-initiated signed trades and aggregate dealer activity to daily frequency. BIS Working Paper 405 builds predictive portfolios from lagged total and disaggregated customer flows. | `REJECT_UNOBSERVABLE_CAUSAL_STATE`: retail quote ticks, tick counts, OHLC, and spread are not signed dealer/customer flow. |
| Carry / global volatility | Menkhoff et al. study currency excess returns from borrowing low-interest currencies and investing in high-interest currencies, and relate that cross-section to global FX volatility innovations. | `REJECT_MISSING_POINT_IN_TIME_CARRY_INPUT`: spot OHLC alone does not reconstruct historical interest differentials, forwards, funding, or positioning. |
| FX liquidity | Mancini, Ranaldo, and Wrampelmeyer measure systematic FX liquidity and show commonality, illiquidity cost, and a relation between liquidity risk and carry returns. | `REJECT_STATE_NOT_DIRECTION`: even a legal liquidity-state measure does not supply an independent directional entry for the three spot pairs without adding a frozen carry/momentum/reversal wrapper. |
| Portfolio rebalancing | The ECB uncovered-return-parity work models FX expectations jointly with equity/bond return differentials and other external instruments. | `REJECT_EXTERNAL_SERIES_REQUIRED`: the V7 surface contains no point-in-time equity, bond, capital-flow, or hedging-pressure series. |
| Currency momentum | Menkhoff et al. document cross-sectional currency momentum using spot and one-month forward data over a broad currency set, and show sensitivity to transaction costs. | `REJECT_DUPLICATE_FAMILY`: this is return continuation/ranking, not a new independent H4/D1 mechanism under the frozen boundary. |

Sources audited:

- Evans and Lyons, *Order Flow and Exchange Rate Dynamics*:
  `https://www.nber.org/system/files/working_papers/w7317/w7317.pdf`.
- BIS Working Paper 405, *Information flows in foreign exchange markets:
  dissecting customer currency trades*:
  `https://www.bis.org/publ/work405.pdf`.
- Menkhoff et al., *Carry Trades and Global Foreign Exchange Volatility*:
  `https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2012.01728.x`.
- Mancini, Ranaldo, and Wrampelmeyer, *Liquidity in the Foreign Exchange
  Market: Measurement, Commonality, and Risk Premiums*:
  `https://onlinelibrary.wiley.com/doi/10.1111/jofi.12053`.
- ECB Working Paper 812, *The uncovered return parity condition*:
  `https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp812.pdf`.
- Menkhoff et al., *Currency momentum strategies*:
  `https://www.sciencedirect.com/science/article/abs/pii/S0304405X12001353`.
- Official MQL5 `MqlRates` and `CopyTicksRange` documentation:
  `https://www.mql5.com/en/docs/constants/structures/mqlrates` and
  `https://www.mql5.com/en/docs/series/copyticksrange`.

The MQL5 surface can provide bar OHLC, tick volume, spread, and historical tick
records. This is sufficient for closed-bar implementation hygiene and Bid/Ask
outcome reconstruction. It is not evidence that a retail feed contains the
signed, participant-classified, funding, positioning, or cross-market state
used by the papers above.

## Local de-dup cross-check

The pre-result baseline already closed the observable price-only reductions:

- `S693 / EA_H4Ribbon`: H4 EMA pullback trend, PF `0.87`;
- `S694 / EA_D1InsideDay`: daily compression breakout, PF `0.83` and only 20
  trades; `S695` produced one trade;
- `S548 / EA_ACF`: serial-dependence regime switching, PF `0.88`, DD `100%`;
- `S618`: multi-pair consensus, PF `1.02`;
- `S619`: cross-asset catch-up, PF `0.86`;
- `S670`: cross-pair divergence, PF `0.95`;
- `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`: the existing common-USD/ranking
  architecture remains `IDEA / COST-DATA BLOCKED` and cannot be renamed at H4.

V7 therefore returned neither a de-duplicated legal candidate nor an exact
mechanism-matched probe worth implementing.

## Coordinator verdict

`NO_LEGAL_H4_D1_CANDIDATE_CONFIRMED / STOP_UNCHANGED_FRONTIER`

- Do not append a candidate-registry row.
- Do not freeze a preregistration.
- Do not implement an analyzer or cheap probe.
- Do not write or edit MQL5 strategy code.
- Do not compile, run Strategy Tester, optimize, or deploy.
- Do not automatically launch V8 with the same price/tick-volume/spread data
  contract. It would only request a renamed duplicate.

Research may reopen only after an explicit Owner data-contract expansion that
supplies at least one lawful, timestamped, historically reconstructable causal
surface:

1. signed dealer/customer flow with participant meaning;
2. interest-rate/forward/funding/positioning data suitable for true carry;
3. external equity/bond/capital-flow or hedging-pressure data;
4. a separately justified cross-market dataset with synchronized timestamps,
   license, provenance, and realistic execution-cost coverage.

Until such a surface exists, there is no evidence-backed probe or EA target to
develop from V7.
