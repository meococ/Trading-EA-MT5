# HYP-GC-OFI-INNOV-XAU-M5-001 — frozen Q1-2019 source pilot

Status: `FREE_METADATA_REQUOTE_ONLY` until a fresh receipt proves the aggregate
paid estimate is strictly below USD 10.00.  No XAUUSD outcome, return, EA,
MQL5, MT5 run or economic metric is authorized by this plan.

## Causal object

The source object is the count-sign innovation estimator frozen in
`04. Memory/research/20260811_GC_SIGNED_FLOW_MECHANISM_SCREEN.md` draft v2:
raw-contract GC aggressor signs, a causal asymmetric one-lag Markov expectation,
completed five-minute innovation bins, a frozen expanding prior-session scale,
and a direction-neutral paired raw-flow null.  The exact reference math remains
`04. Memory/research/gc_signed_flow_estimator_reference.py`; no estimator
constant may change from this source pilot.

## Exact source request

- Hypothesis: `HYP-GC-OFI-INNOV-XAU-M5-001`.
- Quote/pilot ID: `GCOFI001-Q1-2019-SOURCE-PILOT-001`.
- Dataset: `GLBX.MDP3`.
- Symbol: continuous `GC.v.0`; `stype_in=continuous` and paid payloads must use
  `stype_out=instrument_id`.
- UTC half-open window: `[2019-01-01T00:00:00Z, 2019-04-01T00:00:00Z)`.
- Required schemas: `tbbo`, `definition`, and `status`, each quoted and acquired
  as a separate DBNv3 Zstandard payload.
- Runtime: the hash-bound Python 3.12.10 / Databento 0.55.1 / databento-dbn
  0.35.0 runtime already recorded by
  `HYP-EVENT-AGGFLOW-EURUSD-TICK-005_DBV3_RUNTIME_RECEIPT.json`.
- Cost mode: `historical-streaming`.

The three live estimates are summed before any paid call.  Paid access is
fail-closed unless every quote is finite and nonnegative, every billable-size
query is positive, and the aggregate estimate is **strictly below USD 10.00**.
The Owner's standing authority is the message: “Đồng ý chi tối đa USD 0.01 cho
duy nhất pilot EVT0001 và mọi thứ không cần hỏi lại nếu dưới 10u”.  This plan
uses only the second clause; it does not alter or retry EVT0001.

## One-shot acquisition boundary

This plan first authorizes only three free `metadata.get_cost` and three free
`metadata.get_billable_size` calls.  A separate hash-bound paid-acquisition
tool/receipt must be frozen after the live quote and before any
`timeseries.get_range` call.

For the later paid step, each schema receives at most one remote call.  Write an
in-flight manifest before each call.  A transport or decode failure stops the
campaign; there is no automatic or same-ID remote retry.  Raw bytes, size,
SHA-256, DBN version, dataset, schema, record count and source clock are bound
before semantic inspection.

## Source-only gates

The pilot may inspect only source integrity and the fields required to verify:

1. DBNv3/dataset/schema identity and deterministic replay;
2. raw-instrument mapping and visible front-roll boundaries;
3. complete trading-status/session delimitation for the accepted TBBO rows;
4. nondecreasing `(ts_event, sequence)` with no duplicate/correction ambiguity;
5. at least 99% of trade count and contract volume classified directly as
   aggressor `A` or `B` (all `N` rows are counted and excluded);
6. usable pre-trade/post-trade BBO, no locked/crossed/stale bin, and exact
   five-minute UTC aggregation; and
7. deterministic equality with the frozen estimator reference on fixtures and
   replay.

Any failed source gate kills this exact pilot.  Do not lower 99%, exclude a
date/session/contract, change schema, impute `N`, infer side from price, relax
status/roll rules, or inspect XAUUSD to rescue it.  A PASS permits only a fresh
multi-year counts-only cadence plan; it is not edge evidence.

