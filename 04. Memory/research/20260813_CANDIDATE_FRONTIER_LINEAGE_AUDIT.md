# Candidate registry lineage-aware frontier audit

Date: 2026-08-13

## Question

Does the current append-only candidate registry contain any lawful open
economic, source-only or collection-only frontier object that can be continued
without reopening a terminal family, inspecting target outcomes or inventing a
new mechanism?

## Exact inputs and guard implementation

- Registry: `04. Memory/research/CANDIDATE_REGISTRY.jsonl`
- Registry SHA256:
  `2043351DDB09F826187D4A55690646DC946415062531063774A721C334F26391`
- Auditor: `04. Memory/research/audit_candidate_frontier.py`
- Auditor SHA256:
  `F10B9D8F357DD20224E5FD6998B63FAA15127F2E0A16DDB929155C63E3ADF279`
- Tests: `04. Memory/research/tests/test_audit_candidate_frontier.py`
- Tests SHA256:
  `21F1F26ABDA2DD60A1EABCC6618B100118C4B58CAF9AA6AA05F447175740E1ED`
- Explicit lineage overrides:
  `04. Memory/research/CANDIDATE_LINEAGE_OVERRIDES.json`
- Overrides SHA256:
  `5B6530D9B5B762C1C85838C8BC3881832AE5B4E4E1276E673FB1F8845DF31A1F`

## Method

1. Parse all append rows and use the last append row for each hypothesis ID.
2. Build explicit child edges from hypothesis IDs cited in `parent_candidate`.
3. Apply only hash-bound manual edges supported by a local authority receipt.
4. Classify only graph leaves. `parked`, `killed` and `rejected` are terminal.
5. Do not treat one truthy field as economic authority. An open economic leaf
   requires the coherent last-row trio:
   `economics_authorized=true`, `performance_metrics_authorized=true`, and one
   of `model0_authorized`, `model0_performance_authorized` or
   `mt5_train_run_authorized` true.
6. Any registry hash or override authority-receipt hash drift fails closed.

No prices, outcomes, return fields, reports or EA performance metrics are read.

## Explicit stale-parent correction

The append-only registry does not encode the T2 data-epoch succession as an
exact hypothesis-parent edge. One override binds
`HYP-PTR-T2-DATA-EPOCH-D0-M5-001` to terminal
`HYP-PTR-T2-DATA-EPOCH-D0-M5-005`. This is not inferred from numeric naming.
It is supported by the hash-bound receipt
`20260813_UNRUN_EA_SHELF_DATABASE_AUDIT.md`, which states that HYP001 is an old
collection-only receipt superseded by HYP002 through HYP005.

## Local result

```text
rows=978
hypotheses=390
ea_names=99
graph_leaves=137
applied_lineage_override_count=1
terminal_frontier_count=137
open_economic=[]
source_only=[]
collection_only=[]
stale_nonterminal=[]
verdict=NO_OPEN_ECONOMIC_CANDIDATE
```

Validation:

- `pytest`: `9 passed`
- Python bytecode compilation: PASS
- Override JSON parse: PASS

## Grok Build red-team

The first bytes-based review returned `FRONTIER_GUARD_FAIL` because numeric
namespace heads were selected in first-seen dictionary order rather than by
last append. Lead removed numeric namespace suppression completely rather than
applying only the minimum ordering fix. The revised implementation uses the
single explicit, registry-and-receipt hash-bound override above and requires a
coherent economic authority trio. Grok's second bytes-based review returned:

`FRONTIER_GUARD_PASS`

Grok is advisory; the local artifact and tests are authoritative.

## Lead verdict

`NO_PARKED_REVIVAL_CURRENT_REGISTRY`

There is no current registry leaf authorized for economic work, source-only
work or collection-only work. This closes the stale-parked-state ambiguity and
prevents an old parent row from being mistaken for an active candidate.

This verdict does **not** close the overall EA goal, does not claim that a
profitable EA is impossible and does not prohibit a materially new,
pre-registered source/mechanism. CLS R2 remains a separate external metadata
gate requiring Owner contact authority.
