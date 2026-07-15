# V4 Data Foundation Coordinator Readout — 2026-07-13

Status: `FOUNDATION_READY / DATA_NOT_READY / NO STRATEGY AUTHORITY`

## Objective audit

| Requirement | Evidence | Verdict |
|---|---|---|
| Audit existing EURUSD/GBPUSD/XAUUSD broker quote/cost evidence | Current read-only probe, prior FivePercentOnline audit, and local evidence inventory | `COMPLETE` |
| No-live-trading capture contract | `04. Project Control/ai/data_contracts/20260713_EXECUTION_DATA_ACQUISITION_CONTRACT_V1.md` | `COMPLETE` |
| Hash-bound schema | `02. AlphaFactory/schemas/execution_data_capture_manifest.v1.schema.json` | `COMPLETE` |
| Read-only collector/probe and inventory/validator | `02. AlphaFactory/tools/execution_data_foundation.py` | `COMPLETE` |
| Coverage/timestamp/cost/synchronization gates | Schema, validator, and focused tests | `COMPLETE` |
| Lawful/affordable COMEX GC assessment | `20260713_GVBCI_DATA_ACQUISITION_FEASIBILITY.md` and frozen quote-only request | `COMPLETE; PRICE UNRESOLVED` |
| Coordinator GO/NO-GO | This readout | `COMPLETE` |

## Current broker-data inventory

The canonical target remains `FivePercentOnline-Real`. The current read-only
MT5 probe observed `MetaQuotes-Demo`, so its quote history is non-evidence for
the target lane. The probe still proved that the collector surface is working:

| Symbol | Latest closed-market one-hour history sample | Target evidence? |
|---|---:|---|
| EURUSD | 8,157 ticks | No — wrong server and continuity unproven |
| GBPUSD | 13,927 ticks | No — wrong server and continuity unproven |
| XAUUSD | 14,577 ticks | No — wrong server and continuity unproven |

Probe:
`03. EA Developer/EA_SonicR/research/preflight/v4_data/20260713_MT5_READONLY_PROBE_V1.json`.

Inventory:
`03. EA Developer/EA_SonicR/research/preflight/v4_data/20260713_EXECUTION_DATA_INVENTORY_V1.json`.

The execution evidence root currently contains:

- 0 capture manifests;
- 0 eligible validated bundles;
- 0 raw quote/commission/slippage files named as execution evidence;
- 69 tester `slippage_summary.json` files, all explicitly ineligible as broker
  execution evidence.

The prior `FivePercentOnline-Real` audit remains authoritative for the only
connected-target snapshot:

- 2024–2025 non-zero M15 spread coverage was only about 4%;
- EURUSD had two commission lifecycles; GBPUSD and USDJPY had none;
- every symbol had zero independent side-referenced slippage samples;
- XAUUSD was not included in that audit and has no current target-broker bundle.

## Delivered contract and tooling

The machine schema freezes the minimum data gate:

- 90 elapsed calendar days of quote/heartbeat evidence;
- at least 1,000 quote rows per elapsed day as an emptiness/corruption guard;
- at least 95% connected heartbeat ratio and maximum 60-second heartbeat gap;
- 30 same-symbol commission lifecycles;
- 100 side-referenced slippage fills per symbol, including 30 buys and 30
  sells;
- pre-send ASK for buys and BID for sells, no more than 1,000 ms old;
- exact server identity, SHA-256, row counts, timestamps, and zero-order safety.

`execution_data_foundation.py` provides:

1. `probe-mt5` — read-only terminal/server/symbol/quote-history probe with
   account fingerprinting and no raw account ID;
2. `validate` — JSON-Schema, file-hash, row-count, timestamp, symbol, quote,
   commission, slippage, sample-size, and lookahead validation;
3. `inventory` — separates eligible broker bundles from tester proxies and
   emits the coordinator data verdict.

Focused verification:

```text
python -m pytest -q tests/test_execution_data_foundation.py tests/test_verified_cost_builder.py
11 passed
```

Tests prove fail-closed behavior for altered hashes, relaxed research gates,
post-request/future slippage references, short/insufficient data, and the
absence of mutating MT5 trade-call surfaces.

## GVBCI acquisition assessment

Local COMEX GC L1/trade/definition data is absent. The data route is technically
feasible but neither licensed nor priced for this exact application yet.

Coordinator priority:

1. request an exact Databento usage-based historical estimate for the frozen
   `GLBX.MDP3 / GC.FUT` request;
2. price five years of `definition + bbo-1s + trades` first;
3. price only one month of MBP-1 as a timestamp/sequence fidelity pilot;
4. confirm CME Category C-2 internal non-display research licensing in the
   provider License Manager;
5. do not buy or download without Owner approval.

Databento's public pricing is usage-based with no subscription required for a
historical estimate and advertises USD 125 of new-user credits, but it does not
provide an exact GC five-year quote on the public page. Affordability therefore
remains `UNRESOLVED`, not assumed.

## Coordinator verdict

### QFSI

`STOP_DATA_FRONTIER`

Reason: wrong currently connected server and zero eligible hash-bound
quote/heartbeat/commission/slippage bundles. Historical MT5 ticks without a
continuity proof stay discovery-only.

### GVBCI

`GO_FOR_COST_QUOTE_ONLY`

Reason: the lawful technical path is specified, but no local data, license
confirmation, exact price, purchase approval, or synchronized spot/futures
dataset exists.

### SCFIS

`EXCLUDED`

Reason: no lawful segmented customer-flow feed exists, and aggregate tick
volume is not an acceptable proxy.

## Authorization

- Hypothesis ID or registry row: `NO`
- Preregistration: `NO`
- EA decision-logic or indicator implementation: `NO`
- Compile or MT5 backtest: `NO`
- Live trading or order generation: `NO`
- Re-run read-only target-server probe after the Owner logs into the target
  broker: `YES`
- Obtain a no-purchase vendor cost estimate after credentials/license access
  exists: `YES`

The foundation goal is technically complete, but the data frontier itself is
not open. A future goal must be triggered by a real external-state change:
target-broker access for QFSI or an Owner-approved vendor quote/license step for
GVBCI.

