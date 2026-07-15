# Execution Data Acquisition Contract V1 — 2026-07-13

Status: `ACTIVE / DATA-ONLY / NO LIVE TRADING`

## Scope and authority

This contract is the capture and validation boundary for the Deep Research V4
QFSI/GVBCI data lane. It does not authorize a strategy hypothesis, candidate
registry row, preregistration, indicator integration, EA decision change,
compile, MT5 backtest, or deployment.

The canonical QFSI target broker/server is `FivePercentOnline-Real`. Evidence
from `MetaQuotes-Demo`, tester-generated ticks, a different broker, or a
different symbol namespace cannot be mixed with this lane.

## Safety contract

- All local collectors and probes are read-only.
- They may read terminal/account metadata, symbol metadata, quote history, and
  existing account history.
- They must not place, modify, or close an order or position.
- No account login, ticket, or raw trade row is written to a probe receipt.
- No cron/scheduled capture is authorized. A future passive capture must be
  started explicitly and stopped explicitly.
- Existing legitimate broker fills or broker-provided reports may be imported.
  The research lane must not manufacture trades to satisfy a sample gate.

Tool:
`02. AlphaFactory/tools/execution_data_foundation.py`

Machine schema:
`02. AlphaFactory/schemas/execution_data_capture_manifest.v1.schema.json`

## Hash-bound bundle

Each evidence bundle uses schema
`alphafactory_execution_data_capture.v1`. Every `AVAILABLE` data artifact must
bind its relative path, SHA-256, and exact row count. The manifest binds:

- expected and observed server;
- hashed server and account fingerprints;
- account currency and terminal build;
- symbol geometry;
- research gate thresholds;
- quote, heartbeat, commission, and slippage artifacts;
- the zero-order/no-live safety declaration.

Changing any raw file invalidates the manifest until its hash and row count are
recomputed. A self-attested aggregate is not evidence.

## CSV contracts

### Quote ticks

Required columns:

```text
time_msc,time_utc,symbol,bid,ask,last,volume_real,flags
```

Rules:

- `time_msc` is non-decreasing UTC epoch milliseconds.
- `time_utc` must represent the same instant and include a timezone.
- `bid > 0`, `ask > 0`, and `ask >= bid`.
- Missing bid/ask rows are invalid; they are not zero-spread observations.
- QFSI-eligible completeness requires `PASSIVE_HEARTBEAT` or venue sequence
  numbers. An MT5 `copy_ticks_range` history export without an independent
  continuity record is `BROKER_HISTORY_UNVERIFIED`: useful for discovery, not
  sufficient for QFSI preregistration.

### Collector heartbeats

Required columns:

```text
time_msc,time_utc,connected,server_fingerprint,terminal_build
```

The heartbeat proves that a silent quote interval was observed while the
collector remained connected rather than being a missing-data interval. The
frozen gate requires at least 90 elapsed calendar days, connected ratio at
least 95%, and no heartbeat gap above 60 seconds.

### Commission lifecycles

Required columns:

```text
position_id,symbol,account_currency,round_turn_account_per_lot,conversion_method,open_time_utc,close_time_utc,source
```

The gate is at least 30 independent, fully closed same-symbol lifecycles.
`conversion_method` must equal `per_trade_contemporaneous`. A current FX
conversion or tick-value snapshot may not be applied retroactively.

### Side-referenced slippage fills

Required columns:

```text
fill_id,symbol,side,reference_side,reference_time_msc,request_time_msc,fill_time_msc,reference_price,fill_price,pip_size,source
```

Rules:

- BUY uses the independent pre-send ASK; SELL uses the independent pre-send
  BID.
- `reference_time_msc <= request_time_msc <= fill_time_msc`.
- The pre-send quote may be at most 1,000 ms old at request time.
- The gate is 100 fills per symbol, including at least 30 buys and 30 sells.
- Tester fill summaries, order request price under Market Execution, and a
  reference copied from the fill itself are not independent evidence.
- The collector does not send orders. This file can only be assembled from
  existing legitimate broker fills joined to an independently logged pre-send
  quote source or from an explicit broker execution report with equivalent
  fields.

## QFSI gate

The validator can return `GO_FOR_PREREG_DESIGN` only when all three symbols
`EURUSD`, `GBPUSD`, and `XAUUSD` pass, on the exact target server:

1. at least 90 elapsed days of timestamp-valid quote ticks;
2. at least 1,000 quote rows per elapsed day as a minimal corruption/emptiness
   guard, not as proof of market activity;
3. passive-heartbeat or venue-sequence completeness proof;
4. connected heartbeat ratio at least 95% and maximum gap at most 60 seconds;
5. at least 30 commission lifecycles per symbol;
6. at least 100 independent side-referenced slippage fills per symbol, with
   at least 30 buys and 30 sells;
7. exact hashes, row counts, server identity, and zero-order safety fields.

Passing this data gate authorizes only coordinator review and possible prereg
design. It never authorizes an EA edit, compile, backtest, or live trading.

## Operating commands

Read-only terminal probe:

```powershell
python "02. AlphaFactory/tools/execution_data_foundation.py" probe-mt5 `
  --expected-server "FivePercentOnline-Real" `
  --symbols EURUSD GBPUSD XAUUSD `
  --sample-hours 1 `
  --out "03. EA Developer/EA_SonicR/research/preflight/v4_data/mt5_probe.json"
```

Validate a completed hash-bound bundle:

```powershell
python "02. AlphaFactory/tools/execution_data_foundation.py" validate `
  --manifest "<bundle>.manifest.json" `
  --out "<bundle>.validation.json"
```

Inventory the lane without reading tester proxies as broker evidence:

```powershell
python "02. AlphaFactory/tools/execution_data_foundation.py" inventory `
  --expected-server "FivePercentOnline-Real" `
  --probe "<probe.json>" `
  --evidence-root "02. AlphaFactory/evidence/execution" `
  --prior-audit "03. EA Developer/EA_SonicR/research/20260711_BROKER_COST_PROVENANCE_AUDIT.md" `
  --out "<inventory.json>"
```

## Stop rules

- Server mismatch: stop capture and quarantine the receipt as non-evidence.
- No passive heartbeat/sequence proof: historical quote data stays discovery
  only.
- Any missing, altered, or unhashable source: fail closed.
- Any post-request/future slippage reference: fail closed as lookahead.
- Insufficient commission or slippage sample: remain `STOP_DATA_FRONTIER`.
- Tester `slippage_summary.json` files never satisfy the broker-cost gate.

