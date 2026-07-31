# PROBE PLAN V2 — HYP-TRENDSTACK-EURUSD-H1-003

Status: **FROZEN before any production source-row access, custody decode,
HYP-003 DESIGN price access, outcome, PnL, or economic metric** on 2026-07-28.

This is a pre-outcome authority amendment to:

- `HYP-TRENDSTACK-EURUSD-H1-003_PROBE_PLAN.md`, SHA256
  `6A2165CDCE80AD4B04036832C1685746B3828452A8223F35B448DC0568091475`;
- `DATASET-FIVEPERCENT-EURUSD-M1-SPLITVAULT-001_PLAN.md`, SHA256
  `673D285C8C46D81C2D21ED0BD1E46D12A0EB12CD7DF874074909EF1FA5D2BF2B`.

V1 remains the registry-bound preregistration. V2 does not change the market
mechanism, feature definitions, opportunity set, source identity, costs,
trial budget, or economic thresholds. It closes the production source-run,
execution-semantics, capability, attempt, and diagnostic-authority gaps found
by independent review. A later registry transition and reviewed run packet
must bind this exact V2 file SHA before any production source open.

## 1. Immutable parent execution contract

The conditional DESIGN evaluator must reproduce, without interpretation:

- `HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_PLAN.md`, SHA256
  `06AB038A59A9CEEF3E47734E892CCC04A98F43D6E82B9373A2C8680EBB6DA0A9`;
- `HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_PLAN_V2.md`, SHA256
  `3E31F1229C1BD4DBAB05D977E9F9FB5BB553EE65F097BB0B43B787AC9A1EC4C6`.

Exact one-day semantics are frozen here as well:

- entry is the `12:01 UTC` M1 bid open;
- LONG stop is `entry - ATR20`; SHORT stop is `entry + ATR20`;
- stop is active on M1 bars `12:01` through `17:59` inclusive;
- on the entry bar, low/high touching the stop exits at the exact stop;
- on later bars, an adverse open at/beyond the stop exits at that bar open;
  otherwise a high/low touch exits at the exact stop;
- if no prior stop exit occurs, exit at the `18:00 UTC` M1 bid open; an 18:00
  open beyond the stop is still `TIME_EXIT_1800` at that open;
- there is one barrier and no take profit, so no SL-vs-TP intrabar tie exists;
- any missing minute or join identity is `INVALID_ENGINEERING`; no opportunity
  may be dropped;
- `gross_R = direction * (exit_bid - entry_bid) / ATR20`;
- `stop_pips = ATR20 / 0.0001`;
- `net_R = gross_R - round_trip_cost_pips / stop_pips`.

The full frozen DESIGN decision set is exactly 1,297 dates and the four arms
remain exactly four economic trials. Source/custody/tool failures are not
economic trials.

## 2. Exact DESIGN economic gates

No DESIGN economics is authorized by this V2 or by the source run. If a later
separate economic packet is authorized after source acceptance, the exact
twelve gates are:

1. completed cadence `2.0..5.0` per `260.571428571` elapsed calendar weeks;
2. PF at 1.50 pips `> 1.30`;
3. PF at 2.25 pips `>= 1.25`;
4. PF at 3.00 pips `>= 1.00`;
5. mean net R at 1.50 pips `>= 0.08`;
6. total net R at 1.50 pips `> 0`;
7. at least `4/5` DESIGN years positive at 1.50 pips;
8. DSR at 1.50 pips `>= 0.95` across exactly four arm trials;
9. STACK PF delta versus the better standalone PF `>= 0.15`;
10. STACK mean-R delta versus the better standalone mean R `>= 0.05`;
11. STACK PF delta versus DISAGREE `>= 0.15`;
12. STACK mean-R delta versus DISAGREE `>= 0.05`.

The better standalone control is the separate maximum of M252 and M6 for each
metric. DSR uses canonical `dsr.py`, per-trade 1.50-pip returns, sample variance
across four arm Sharpe ratios, `n_trials=4`, challenger skew, and non-excess
kurtosis.

The registry `acceptance_contract.max_drawdown_pct=6` and
`max_monte_carlo_p95_dd_pct=6` fields are **dormant, non-authoritative
diagnostics in this M1 proxy phase**. Drawdown and Monte Carlo cannot pass,
kill, promote, or rescue HYP-003 here. They become gates only under a future
separately frozen Model-0/robustness contract after DESIGN and validation both
survive. No risk-normalization inference is permitted in this phase.

## 3. Full-corpus grid semantics

The generic custodian must preserve the input exactly. For the complete FX
corpus:

- every `time_utc` is minute-aligned with zero seconds and sub-second part;
- timestamps are globally unique and strictly increasing;
- one-minute adjacency is **not** required across market/session/weekend gaps;
- no observed gap may be filled, dropped, deduplicated, resampled, or used to
  tune a trading rule.

Only the HYP-003 frozen DESIGN windows require exact adjacency: every one of
the 1,297 dates must contain all 360 consecutive M1 opens from `12:01` through
`18:00` inclusive, for exactly 466,920 rows. The known 2016-03-11 gap receives
no exception.

## 4. One reviewed source pipeline and attempt semantics

There is one serial, outcome-blind production source pipeline:

1. generic custodian verifies and decodes the immutable raw corpus once;
2. only after custody PASS, the DESIGN child receives public DESIGN bytes,
   public manifest/receipt, and a physical DESIGN-only Stage-0 projection;
3. the builder may publish only `PENDING_INDEPENDENT_VALIDATION`;
4. an independently hash-bound validator reopens and rehashes the complete
   published DESIGN tree and alone may emit
   `SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET`.

The source pipeline is a single authorized attempt identified by one exact
`source_attempt_id` in the run packet. The supervisor must pre-create and bind
one exact child attempt path. No wildcard/prefix capability to earlier attempts
is legal. Starting the first production source open consumes the attempt. Any
crash, identity drift, capability denial, content/schema failure, output race,
validation failure, or partial publication parks HYP-003 engineering-invalid;
there is no same-ID retry, resume, fill, repair run, alternate source, or output
reuse after the production open.

Synthetic tests and reviewed-packet validation do not consume the attempt
because they cannot open the production source.

## 5. Required run-packet bindings before production open

Production remains impossible while
`splitvault_001_supervisor.REVIEWED_RUN_PACKET_SHA256 is None`.

The create-new canonical source run packet must be one-line canonical JSON with
no extra field and must bind at minimum:

- schema, collection ID, HYP-003 ID, verdict, and exact `source_attempt_id`;
- V1 plan path/SHA, this V2 path/SHA, and collection plan path/SHA;
- active registry path and whole-file SHA after the legal authorization row;
- raw source path/SHA/bytes/footer SHA and root manifest path/SHA;
- clock tool path/SHA;
- parent Stage-0 ledger/receipt paths and SHAs;
- frozen DESIGN date-set SHA;
- final reviewed custodian, supervisor, builder, validator paths and SHAs;
- all four final test paths and SHAs;
- exact create-new split-vault and DESIGN-source output roots;
- `source_run_authorized=true`;
- `performance_metrics_authorized=false`;
- `trading_mutation=false`;
- `network_allowed=false`;
- `subprocess_allowed=false` for the contained worker;
- `model0_authorized=false`.

The supervisor may use subprocess only as the containment mechanism for the
reviewed worker; the worker itself receives no subprocess or network authority.
The packet SHA must be independently reviewed and then hard-bound into the
supervisor before production. The bound supervisor source SHA must in turn be
recomputed and included in the run evidence. Any packet/path/file/hash/type/
flag drift fails before the raw source is opened.

## 6. Capability and evidence invariants

- The DESIGN capability contains DESIGN bytes and public custody evidence only;
  it contains no raw/vault/private/validation/holdout/quarantine path.
- Worker audit/filesystem policy is installed before third-party import and
  permits read-only trusted imports plus the exact output/attempt capability;
  it denies source-parent/future/private enumeration and all worker network,
  system, exec, spawn, and subprocess events.
- Reviewed tool bytes are executed from the exact verified bytes, not reopened
  pathnames.
- Late output collision/reparse never receives a sealed attempt; failed
  attempts remain in a trusted sibling location.
- Supervisor binds the exact builder-returned PENDING receipt and deterministic
  tree digest. Validator authority binds root/directory/file identities, parent
  ledger/receipt, projector/builder, custody receipt/manifest, per-day custody
  hashes, and final re-inventory equality immediately before READY.
- Directory identity is the exact six-integer tuple
  `(dev, ino, mode, mtime_ns, ctime_ns, attributes)` across supervisor,
  builder, and validator.
- Public evidence distinguishes infrastructure decode from research access:
  `custodian_full_corpus_decoded=true`,
  `research_validation_opened=false`,
  `research_holdout_opened=false`,
  `economics_opened=false`, and `performance_trials_executed=0`.

## 7. Failure routing and remaining authority

- Source/custody/capability/completeness/validation failure:
  `PARK_ENGINEERING_INVALID_SOURCE_OR_SEAL_NO_MARKET_VERDICT`.
- Source PASS: `SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET`; economics
  remain unopened until a separate pre-outcome packet and authority transition.
- DESIGN economic failure after later authorization: `KILL`; validation remains
  unopened.
- DESIGN survivor: validation still requires a separate frozen plan and
  transition.
- No source result authorizes EA source, MQL5 compile, Model 0, promotion,
  robustness, paper, live, or deployment.

