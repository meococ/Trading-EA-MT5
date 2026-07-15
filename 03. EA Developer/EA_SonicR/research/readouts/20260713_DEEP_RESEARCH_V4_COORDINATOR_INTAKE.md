# Deep Research V4 Coordinator Intake — 2026-07-13

Status: `DATA_ACQUISITION_ONLY / NO STRATEGY PROBE / NO EA BUILD`

## Binding

- ChatGPT conversation:
  `https://chatgpt.com/c/6a53ce89-fba4-83ec-9d44-f2edcedeb01d`
- Research verdict:
  `DATA ACQUISITION REQUIRED BEFORE RESEARCH CAN CONTINUE`
- Codex goal thread:
  `019f571c-42a0-7ed1-8e02-5bf6f2a43669`

## Intake interpretation

V4 did not produce a legal entry system or an offline-probe candidate. It
identified three conceptual data surfaces:

1. `QFSI` — quote-firmness/execution-stress state derived from broker quote
   ticks. It remains blocked by incomplete historical cost and fill/slippage
   evidence. It is an execution-feasibility research surface, not permission to
   filter or rescue an existing entry.
2. `GVBCI` — XAUUSD spot versus COMEX GC basis state. It requires synchronized
   historical GC L1/trades, contract and roll metadata, and strict stale-quote
   handling. It becomes an already-closed lead-lag family if reduced to
   “futures moves first, spot catches up.”
3. `SCFIS` — segmented customer-flow state. It is not legal with current data
   and may not be replaced by aggregate tick-volume proxies.

No research claim in the model report overrides local catalog de-duplication,
cost provenance, or the frozen preregistration doctrine.

## Active goal

Build and validate a data-acquisition-only foundation for the V4 frontier:

- prioritize an inventory of EURUSD, GBPUSD, and XAUUSD broker tick, bid/ask,
  commission, and fill/slippage coverage;
- define a no-live-trading capture contract and hash-bound schemas;
- implement or document coverage, timestamp, and synchronization validators;
- assess lawful and affordable COMEX GC L1/trades plus roll metadata only after
  the cheaper broker-data lane is understood;
- issue a coordinator `GO_FOR_PREREG_DESIGN` or `STOP_DATA_FRONTIER` readout.

## Hard stop rules

- No hypothesis ID or registry row from V4 yet.
- No preregistration, indicator implementation in an EA, compile, or MT5
  backtest.
- No live trading or account attachment.
- QFSI stops if broker cost/fill evidence cannot be made sufficiently complete.
- GVBCI stops if synchronized GC data and roll metadata cannot be acquired with
  reproducible timestamps and acceptable rights/cost.
- SCFIS remains excluded without lawful segmented customer-flow data.

