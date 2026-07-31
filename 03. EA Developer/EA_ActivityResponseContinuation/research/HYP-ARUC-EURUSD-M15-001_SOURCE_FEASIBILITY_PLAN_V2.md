# HYP-ARUC-EURUSD-M15-001 — Source Feasibility Plan V2

Status: `FROZEN_PRE_RUN_ENGINEERING_AMENDMENT`

## Supersession and attempt state

This V2 plan supersedes only the exact V1 plan at
`03. EA Developer/EA_ActivityResponseContinuation/research/HYP-ARUC-EURUSD-M15-001_SOURCE_FEASIBILITY_PLAN.md`
with SHA256
`BAA96FF852611996ACC1074BF9955C9F570D4593C86CF66753579C3B3480F1B4`.
V1 registry row 301 and the V1 source-run packet remain immutable audit
history; neither may authorize this V2 builder.

The amendment is pre-outcome and pre-execution. No source attempt started,
`source_feasibility_attempts_consumed=0`, no DESIGN shard or post-entry price
was opened, no outcome was emitted and the source sentinel remains `None`.
The hypothesis, data contract, causal features, three arms, Stage-0 gates,
economics prohibitions and all other research terms frozen by V1 remain
unchanged unless this amendment explicitly replaces an engineering preflight
rule below.

## Preflight finding

The canonical registry validator accepts the production registry as 301 rows
and 101 hypotheses. Historical append-only rows legitimately contain JSON
whitespace that is not compact/sorted canonical serialization. Requiring every
historical raw line to equal the builder's canonical serializer is therefore
an invalid local preflight condition, not a registry or market failure.

## Registry snapshot contract

The builder must use a registry-only JSONL parser. It requires non-empty bytes,
exact terminal LF framing for every row, strict UTF-8, no blank row, no
duplicate key, no non-finite number and a JSON object at every row root. It
does not require historical rows to use canonical whitespace or key ordering.
Manifest and receipt parsing remains canonical and unchanged.

The packet-selected latest ARUC row remains bound to its exact raw-line SHA256.
The selected row itself must use the builder's canonical serialization. Its
identity, state, null source/model fields, empty run IDs, plan binding, literal
Boolean authorities, data bindings and exact validation-object whitelist all
remain fail-closed.

## Canonical registry validation bindings

Before any DESIGN receipt, manifest or shard is opened, the immutable in-memory
registry snapshot must return no errors from the hash-bound canonical validator
and schema below. The builder executes the validator in-process and supplies
immutable byte adapters for both registry and schema; no subprocess or mutable
temporary file is permitted. Any hash mismatch, load error, malformed validator
result or reported validation error fails closed.

- Validator path: `04. Memory/research/validate_candidate_registry.py`
- Validator SHA256: `B04B379E11F556A0CF3E6C3264768176310FF01CF360CC3B92464C51A2996DD0`
- Schema path: `04. Memory/research/CANDIDATE_REGISTRY.schema.json`
- Schema SHA256: `96C80D3C46A105A9754CA1325F3DD6C160D92A9D5800ECBC402DE0F40C612F5C`

The V2 run packet is exactly
`03. EA Developer/EA_ActivityResponseContinuation/research/HYP-ARUC-EURUSD-M15-001_SOURCE_RUN_PACKET_V2.json`
with schema `aruc_001_source_feasibility_run_packet.v2`. It must bind both
validator and schema paths and hashes in addition to all unchanged V1 packet
fields. A V1 packet cannot authorize the V2 source.

The future latest registry validation object must use the exact V2 whitelist:
the two intended literal-true source-feasibility fields, every literal-false
sealed-capability field, the six V1 attempt/data-binding fields, plus exact
`registry_validator_path`, `registry_validator_sha256`,
`registry_schema_path` and `registry_schema_sha256` bindings. No additional
validation key is permitted regardless of name or value.

## Disarm and permissions

`REVIEWED_RUN_PACKET_SHA256` remains `None` in reviewed source. A later real
DESIGN read still requires an explicit run switch, a separately reviewed exact
V2 packet SHA armed into the sentinel, an exact latest registry row, clean
canonical registry validation and all existing file/data/clock bindings.
Validation/holdout/private/sealed, outcome/economics, network/paid,
MT5/MQL5, optimization, promotion/live and registry mutation remain forbidden.
