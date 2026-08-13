# HYP-EHPR-EURUSD-M15-002 — source-feasibility result

Attempt: `EHPR002-SOURCE-ATTEMPT-001`

Verdict: `PASS_SOURCE_FEASIBILITY_MAY_DRAFT_MQL5_BASELINE`

This verdict is limited to deterministic, outcome-blind event population. It is not engineering-valid MQL5, economic-valid, promotion-ready, or evidence of market edge.

## Frozen-gate readout

| Measure | Result |
|---|---:|
| M5 rows read in authorized source/prehistory window | 446,636 |
| Unique alignable M15 buckets | 148,975 |
| Complete derived M15 bars | 148,746 |
| Derived M15 coverage | 99.8463% |
| DESIGN bars | 124,011 |
| Usable DESIGN bars | 120,991 |
| Usable coverage | 97.5647% |
| Raw phase-cross events | 21,680 |
| Executable exact-next events | 21,618 |
| Exact-next coverage | 99.7140% |
| Event cadence | 82.9638/week |
| LONG / SHORT | 10,809 / 10,809 |
| Maximum year share | 20.7235% |
| Unexpected gap resets | 89 |
| Direction conflicts | 0 |

Each frozen source gate passed. The exact ledger has 21,506 direction changes and 111 same-direction adjacencies across 21,617 adjacent pairs; it is 99.49% alternating, not perfectly alternating.

## Evidence bindings

- Report: `research/evidence/HYP-EHPR-EURUSD-M15-002/EHPR002-SOURCE-ATTEMPT-001/ehpr_002_source_report.json` — SHA-256 `542D6C33AF9A610C65AB7033C097A6187705BDB4EBC4B1D82DC6529642BF19EE`
- Event ledger: `research/evidence/HYP-EHPR-EURUSD-M15-002/EHPR002-SOURCE-ATTEMPT-001/ehpr_002_event_ledger.jsonl` — SHA-256 `75EBCADA6ABD60605ACC9CC53F75C75297B0719AFBA6976E0332BE30773B7EBE`
- Receipt: `research/evidence/HYP-EHPR-EURUSD-M15-002/EHPR002-SOURCE-ATTEMPT-001/source_feasibility_receipt.json` — SHA-256 `FC8267DE3789A28B27AD8A57AD1136826797CE58BE0C1A86EA659C81A4B63C94`
- Terminal receipt: `research/evidence/HYP-EHPR-EURUSD-M15-002/EHPR002-SOURCE-ATTEMPT-001/attempt_terminal.json` — SHA-256 `6201592105CE243F5214E38C8868F0D3FA2B690F2202C315D6D08860DAE61E2A`

## Outcome boundary

The receipt reports zero post-event OHLC rows, returns, trades, PnL, profit factor, validation rows, holdout rows, MQL5 builds, and MT5 runs. Those counters remain authoritative.
