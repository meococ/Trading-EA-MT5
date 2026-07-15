# Deep Research V6 Coordinator Audit — 2026-07-13

Status: `NO_LEGAL_CANDIDATE_CONFIRMED / FRONTIER_STOP / NO_EA_BUILD`

## Binding

- ChatGPT conversation:
  `https://chatgpt.com/c/6a54f339-93c0-83ec-b966-d022564ca116`
- Report title: `Deep Research V6 Strategy`
- Failure packet:
  `03. EA Developer/EA_SonicR/research/20260713_NEW_STRATEGY_DEEP_RESEARCH_FAILURE_PACKET_V6.md`
- Submission receipt:
  `03. EA Developer/EA_SonicR/research/preflight/20260713_NEW_STRATEGY_DEEP_RESEARCH_SUBMISSION_V6.json`
- Result receipt:
  `03. EA Developer/EA_SonicR/research/preflight/20260713_NEW_STRATEGY_DEEP_RESEARCH_RESULT_V6.json`
- UI contract was valid before submission: `GPT-5.6 Sol`, `Pro`, and
  `Nghiên cứu sâu` were read back before the plan was started.

## Model result

V6 returned `NO LEGAL CANDIDATE`. It found three mechanism families near the
allowed surface, but none can be tested without changing the causal variable,
the allowed execution horizon, or both:

1. order-flow assimilation after public news;
2. triangular-parity or stale-quote convergence;
3. liquidity-shock or spread-based directional trading.

This is a legal no-candidate answer under the V6 packet. It does not authorize
an approximate price-action implementation, a second-order proxy, an offline
probe, a registry row, a preregistration, MQL5 source, compile, or backtest.

## Source audit

| Near-miss family | What the cited evidence actually observes | MT5/contract mismatch | Coordinator disposition |
|---|---|---|---|
| News order-flow assimilation | Signed buyer- versus seller-initiated transactions, end-user or informed flow, and post-news price discovery | The current retail surface has quotes, ticks, spread and tick volume, but no signed transaction flow or participant classification. `sign(Δmid)` would reuse price as both proxy and target. | `REJECT_PROXY_MISMATCH` |
| Triangular parity / stale quotes | Tick-frequency multi-venue quotes and short-lived no-arbitrage violations | The effect is explicitly short-lived and can be missed by lower-frequency observations. M5–H1 closed-bar decisions erase the latency state the mechanism needs. | `REJECT_TIMESCALE_MISMATCH` |
| Liquidity shock / spread direction | CLS trading volume, dealer-intermediation capacity, quote submission, or other institutional liquidity states | A retail spread/tick-volume reduction does not reconstruct those states. Published low-frequency spread estimators can be materially volatility-biased. | `REJECT_UNOBSERVABLE_CAUSAL_STATE` |

Primary and institutional sources checked:

- MQL5 timeseries API surface (`CopyRates`, tick/real volume, spread, ticks):
  `https://www.mql5.com/en/docs/series`.
- ECB Working Paper 424, signed order flow and transaction-level interdealer
  data: `https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp424.pdf`.
- *Jumps and cojumps in foreign exchange markets*, including signed order flow,
  informed trading, and the absence of reversal after news jumps:
  `https://www.sciencedirect.com/science/article/abs/pii/S0378426617302212`.
- *Liquidity in the global currency market*, using CLS intraday volume and
  triangular violations:
  `https://www.sciencedirect.com/science/article/pii/S0304405X22001891`.
- *Constrained liquidity provision in currency markets*, using globally
  representative trading volume and dealer-intermediation constraints:
  `https://www.sciencedirect.com/science/article/pii/S0304405X25000364`.
- Review of Finance / RFS evidence on volatility-induced bias in popular
  low-frequency effective-spread measures:
  `https://academic.oup.com/rfs/article/36/10/4190/7127916`.
- BIS Working Paper 1094 on fragmented FX execution, HFT, and high-frequency
  cross-asset structure: `https://www.bis.org/publ/work1094.pdf`.
- Tick-frequency FX triangular arbitrage evidence and the loss of short-lived
  opportunities at lower sampling frequencies:
  `https://papers.ssrn.com/sol3/papers.cfm?abstract_id=887442`.

These sources support the existence of market mechanisms. They do not support
a causal, deployable M5–H1 retail rule under the current data and execution
contract. The news-jump paper also reports no jump-return reversal after news,
which blocks a clean price-only fade interpretation; reducing the result to
post-event momentum would be another generic event/price wrapper, not the
observed order-flow mechanism.

## Local de-dup and failure cross-check

- `STRATEGY_LOG.md:3216` already invalidates pure tick-volume order flow because
  MT4/MT5 data are not faithful to real flow.
- `STRATEGY_LOG.md:3218` already invalidates spread compression as a signal
  because correlation is not causation.
- `S624 / EA_FlowType` produced PF `0.94` on XAUUSD and explicitly concluded
  that retail CFD M1 aggregation is not institutional order flow.
- `S625 / EA_FlowType` produced PF `1.04` on USDJPY with recent decay to PF
  `0.78`; the same flow-proxy lesson applied.
- No exact triangular-arbitrage candidate exists in the registry. Adjacent
  low-frequency convergence/lead-lag attempts are already dead: `S619`
  cross-asset catch-up PF `0.86`, and `S621` COMEX-LBMA convergence PF `1.04`.

Therefore V6 did not surface a de-duplicated, observable, causally faithful
candidate that deserves the cheap-probe ceremony.

## Coordinator verdict

`NO_LEGAL_CANDIDATE_CONFIRMED / STOP_UNCHANGED_FRONTIER`

- Do not create a candidate-registry row or hypothesis ID.
- Do not write or freeze a preregistration.
- Do not create another proxy probe from price direction, tick direction, tick
  volume, spread compression, event clock, or an M5–H1 parity wrapper.
- Do not write an EA, compile MetaEditor, run Strategy Tester, optimize, or
  deploy.
- Do not automatically start V7 under the unchanged blocker. Re-prompting for
  cosmetic variants would violate the failure-loop stop rule.

The frontier may reopen only after a real external-state change supplies at
least one of:

1. lawful, timestamped signed transactions, participant/dealer flow, or
   venue/order-book depth that observes the claimed causal state;
2. an explicit Owner scope expansion to sub-second/tick execution together
   with venue/broker latency, synchronization, full cost, and slippage proof;
3. a genuinely independent exogenous data surface with reconstructable
   historical timing and lawful reuse rights.

Until then there is no evidence-backed strategy goal to set and no EA to build.
