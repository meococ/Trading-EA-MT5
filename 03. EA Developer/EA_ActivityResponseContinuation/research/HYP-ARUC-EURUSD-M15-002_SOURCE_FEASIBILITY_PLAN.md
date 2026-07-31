# HYP-ARUC-EURUSD-M15-002 — Source Feasibility Plan

Status: `FROZEN_FRESH_CHILD_PRE_RUN`

## Identity and reason for the child

- Hypothesis: `HYP-ARUC-EURUSD-M15-002`
- Parent candidate: `HYP-ARUC-EURUSD-M15-001`
- Attempt: `ARUC002-SOURCE-ATTEMPT-001`, limit exactly one.
- Family: `activity-response-underreaction-continuation`.
- Symbol/timeframe: FivePercent `EURUSD`, M15 decisions, H1 BID volatility.

The parent `-001` authority became terminal before any source execution because
its proposed V2 preregistration path was incompatible with the canonical
append-only registry rule that freezes preregistration after entry to `probe`.
The parent consumed zero source-feasibility attempts, opened zero DESIGN shards,
read zero post-entry OHLC rows and emitted zero outcomes. This fresh child exists
only to repair registry/run authority without rewriting parent history.

No market thesis, threshold, date, symbol, timeframe, dataset, source hash,
feature definition, control arm, Stage-0 gate or prohibition changed from the
frozen parent contract. This is not a post-hoc market rescue and provides no
economic authority.

## Unchanged public DESIGN contract

Only the identical ordered public DESIGN date sequence from `2016-01-04`
through `2020-12-31` is permitted: 1,555 manifest dates, comprising 1,298
Monday-Friday decision dates and 257 Sunday history dates, with no Saturdays.
Sunday rows are causal history only and never enter decision slots or formation
denominators.

M1 remains exactly 1,859,820 DESIGN rows from
`02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002`; H1 BID remains exactly
31,057 DESIGN rows backed by 71,785 raw-source rows from
`02. AlphaFactory/data/fivepercent/EURUSD/h1_splitvault_002`. All receipt,
manifest, immutable-source, schema, one-row-group, SHA, byte-count, timestamp,
timezone and public-path checks remain unchanged from `-001`.

The causal feature contract, PRIMARY/PRICE_ONLY/SHIFTED_TICKS arms, closed-bar
timing, timestamp-only horizon mapping and outcome blindness are identical to
the parent. Stage-0 still requires cadence 2-5 per elapsed calendar week, at
least 25% each LONG and SHORT, no year over 30%, formation and source-executable
horizon ratios at least 0.99, median `1.50 pip / SL_pips <= 0.25`, and at least
20 PRIMARY signals per side. Only PRIMARY feeds those gates.

## Canonical generic source-only authority

The exact latest canonical `-002` registry row is the sole frozen run packet;
there is no separate JSON packet. A future execution requires all of the
following before any DESIGN receipt, manifest or shard is opened:

1. explicit run switch and exact non-`None` `REVIEWED_REGISTRY_ROW_SHA256`;
2. the disarmed builder base obtained by normalizing that single sentinel;
3. strict registry JSONL content parsing while tolerating legitimate historical
   whitespace/key ordering;
4. the exact selected raw-line SHA equals the sentinel, the selected row is the
   latest `-002` row and uses compact sorted canonical serialization;
5. the immutable registry snapshot returns no errors from the hash-bound
   canonical validator and schema;
6. exact identity, parent, plan, review, implementation, data, clock,
   permissions and zero-runtime metric bindings in that row.

Canonical dependencies:

- `04. Memory/research/validate_candidate_registry.py` — SHA256
  `B04B379E11F556A0CF3E6C3264768176310FF01CF360CC3B92464C51A2996DD0`
- `04. Memory/research/CANDIDATE_REGISTRY.schema.json` — SHA256
  `96C80D3C46A105A9754CA1325F3DD6C160D92A9D5800ECBC402DE0F40C612F5C`

The validation object uses an absolute whitelist. It requires literal
`source_run_authorized=true`, `source_feasibility_only=true`,
`source_build_authorized=false`, `source_feasibility_attempt_limit=1`, the exact
attempt/evidence root, exact `probe_status`, all three independent review
statuses `PASS`, reviewed builder/test and independent receipt bindings, all
canonical source-only false fields, all retained sealed false fields, and exact
clock/dataset/validator/schema bindings. No extra validation key is permitted.

The root `metrics` object must equal the canonical zero-runtime contract:
attempts/runs/post-entry rows/outcomes/returns/trades/performance trials/model
runs/MT5 launches/MQL5 files/paid requests/network calls are zero;
`economics_executed`, validation-opened and holdout-opened are literal false.

The independent review receipt is parent-owned and must use exact schema
`aruc_002_source_implementation_review_receipt.v1`, bind this plan and the
reviewed builder/test hashes, record `review_status=PASS`, authorize only the
source-feasibility run and keep performance/economics and MT5/MQL5 false.

## Prohibitions and completion boundary

The reviewed builder sentinel remains exactly `None`; this build task does not
append a registry row, create a receipt, arm the sentinel or run the source.
Validation/holdout/private/sealed access, post-entry prices, returns, PnL, PF,
DSR, optimization, economics, network/paid, MT5/MQL5, promotion/live and
registry mutation remain forbidden.

A future terminal successor must consume at most this single attempt, switch
`source_run_authorized` to literal false and add only the canonical completion
bindings. Source-feasibility PASS may authorize only drafting a separate future
economics preregistration; it never authorizes economics automatically.
