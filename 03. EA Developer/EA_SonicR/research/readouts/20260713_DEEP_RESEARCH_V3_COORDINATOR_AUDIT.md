# Deep Research V3 Coordinator Audit — 2026-07-13

Status: `NO_LEGAL_CANDIDATE / FRONTIER_EXHAUSTED_UNDER_CURRENT_CONTRACT`

## Binding

- ChatGPT conversation:
  `https://chatgpt.com/c/6a53cb1b-0310-83ec-b440-2af58d4d8389`
- Failure packet:
  `03. EA Developer/EA_SonicR/research/20260713_NEW_STRATEGY_DEEP_RESEARCH_FAILURE_PACKET_V3.md`
- Submission receipt:
  `03. EA Developer/EA_SonicR/research/preflight/20260713_NEW_STRATEGY_DEEP_RESEARCH_SUBMISSION_V3.json`
- UI contract was valid before submission: `GPT-5.6 Sol`, `Pro`, and
  `Nghiên cứu sâu` were all read back in the in-app Browser.

## Model result

The V3 report returned `NO LEGAL CANDIDATE`. It found only two theoretically
independent public-information frontiers after applying the locked family
boundary:

1. official macro-announcement surprise;
2. official-sector action or communication, including intervention.

Neither frontier survived the data-and-cost gate. The causal state for the
first is the surprise relative to a reconstructable real-time expectation, not
the release clock or post-release OHLC pattern. The second needs precise,
sufficiently dense action/communication timestamps and sometimes confidential
intervention data. Both also need executable tick bid/ask, full commission, and
independent slippage evidence around event windows. The current workspace does
not have those inputs.

The report correctly distinguished mechanism evidence from proof of a retail
rule after broker costs and granted no exact rules, probe, hypothesis ID,
preregistration, code, compile, backtest, or promotion authority.

## Primary-source boundary

The model cited primary or institutional sources that support the existence of
the mechanisms, not their deployable profitability:

- Andersen, Bollerslev, Diebold, and Vega, *Micro Effects of Macro
  Announcements: Real-Time Price Discovery in Foreign Exchange*:
  `https://econ.duke.edu/~boller/Published_Papers/aer_03.pdf`.
- Federal Reserve, *The High-Frequency Effects of U.S. Macroeconomic Data
  Releases on Prices and Trading Activity in the Global Interdealer Foreign
  Exchange Market*:
  `https://www.federalreserve.gov/pubs/ifdp/2004/823/ifdp823.htm`.
- BIS Working Paper 462, *The effects of intraday foreign exchange market
  operations in Latin America*:
  `https://www.bis.org/publ/work462.pdf`.
- New York Fed, *Foreign Exchange Operations*:
  `https://www.newyorkfed.org/markets/international-market-operations/foreign-exchange-operations`.

These sources do not provide a frozen M5/M15 retail rule that meets the local
cadence, net-cost, robustness, and reproducibility contract.

## Local catalog cross-check

The local catalog makes the no-candidate verdict stronger than the model's
data-only boundary:

- The standalone pre-announcement drift probe used 199 seeded high-importance
  events per window family on USDJPY M5. Gross mean return was only 0.12–0.60
  bps and every window became negative after a conservative 2 bps haircut.
- The GBPUSD M5 follow-up had the same failure shape: gross mean return -0.34
  to +0.94 bps and every window negative after the same haircut.
- `S703 / EA_NewsMomentum` tested post-event continuation on USDJPY M15,
  2019-01-01 through 2026-03-29. The selective configurations produced only
  43–47 trades in seven years (PF 1.2119–1.3432), while lowering the threshold
  to reach 138 trades collapsed PF to 0.7563 and net to -857.63.

Therefore a pure event-clock or post-event price-action implementation is not
only a prohibited timing/technical reduction; adjacent local formulations are
already cost- or cadence-invalidated. A surprise-based implementation remains
conceptually different, but it is unobservable under the current public-data
contract and may not be approximated with `actual - previous`, time, symbol,
side, threshold, filter, target, stop, or hold variations.

## Coordinator verdict

`NO_LEGAL_CANDIDATE / STOP_RESEARCH_FRONTIER`

- Do not append a candidate registry row.
- Do not create or freeze a preregistration.
- Do not write a probe/analyzer, EA source, or include.
- Do not compile or backtest a new EA from V3.
- Do not continue prompting for cosmetic variants under the unchanged data
  boundary.

Research may reopen only after a genuine external-state change supplies at
least one of the following:

1. a timestamped, historically reconstructable real-time expectations dataset
   joined to official releases;
2. exact and sufficiently dense official intervention/action timestamps;
3. executable tick bid/ask, complete per-symbol commission, and independent
   event-window slippage for the target broker;
4. an Owner-approved contract expansion for dealer/customer order flow or
   market depth.

