# HYP-TRENDSTACK-EURUSD-H1-003 — PROBE PLAN V3

Status: `FROZEN_PRE_OUTCOME_AUTHORITY_AMENDMENT`

## 1. Authority and scope

This create-new amendment is subordinate to and must be read with:

- `HYP-TRENDSTACK-EURUSD-H1-003_PROBE_PLAN.md`, SHA256
  `6A2165CDCE80AD4B04036832C1685746B3828452A8223F35B448DC0568091475`;
- `HYP-TRENDSTACK-EURUSD-H1-003_PROBE_PLAN_V2.md`, SHA256
  `13BCD3AEB5AB08EC060EAF5107A384FEE8A2CAF581506B50C5F0D8C5A5830840`;
- `DATASET-FIVEPERCENT-EURUSD-M1-SPLITVAULT-001_PLAN.md`, SHA256
  `673D285C8C46D81C2D21ED0BD1E46D12A0EB12CD7DF874074909EF1FA5D2BF2B`.

V1 remains the registry-bound preregistration. V2 remains authoritative for
the frozen trading semantics, twelve economic gates, source boundary, and
single-attempt policy. V3 changes no signal, parameter, date, cost, arm, gate,
data row, or economic authority. V3 only resolves four pre-outcome P0 defects:

1. the impossible packet-SHA versus exact supervisor-SHA self-reference;
2. non-source binding drift being checked after a production source open;
3. absence of a durable one-attempt consumption record;
4. `source_attempt_id` not binding the production staging paths.

No production source open is authorized until this V3 SHA, the final reviewed
tools/tests, and the post-authorization registry whole-file SHA are bound by a
create-new canonical source run packet and independently reviewed.

## 2. Non-circular supervisor authority

The source run packet field is `supervisor_review_base_sha256`, not an exact
hash of the temporarily armed runtime file. It is the SHA256 of the exact final
reviewed supervisor bytes while the sole authority line is exactly:

`REVIEWED_RUN_PACKET_SHA256: str | None = None`

After independent packet review, production arming may change exactly that one
complete line so its string value equals the reviewed packet SHA256. Runtime
must read its own exact bytes, require exactly one syntactically exact authority
line, require the line value to equal the packet SHA, normalize only that line
back to the exact `None` sentinel above, and require the normalized digest to
equal `supervisor_review_base_sha256`. Any other byte, duplicate line, comment,
whitespace, type, path, or value drift fails before the raw source is opened.

The exact armed runtime supervisor SHA256 is excluded from the packet to avoid
self-reference. It must be recomputed from exact runtime bytes and bound into
the durable attempt-start and terminal evidence together with the packet SHA
and review-base SHA. After the single source attempt terminates, the authority
line must be restored to `None`; restoration does not authorize a retry.

An unsigned sidecar, environment value, CLI value, or caller-supplied digest is
not an authority root for this run.

## 3. Verify-before-open order

Packet bytes, schema, IDs, flags, canonical form, paths, output nonexistence,
source identity/size, and every non-source plan/registry/manifest/clock/parent/
tool/test binding must be verified before the consumption marker is created.
The raw parquet content must not be opened by the generic binding loop.

Only after all non-source bindings and the armed supervisor review-base check
pass may the supervisor create and verify the attempt-start evidence. The next
source operation is the custodian's single stable read of the raw parquet. The
custodian must compute SHA256, bytes, footer SHA, and decode from those already
verified bytes. It may re-stat the immutable source identity after decoding but
must not reopen the raw parquet. A source content/hash/footer/schema/identity
failure is an engineering-invalid consumed attempt, not a market verdict.

## 4. Durable single-attempt consumption

The packet binds one strict ID of the existing V2 form:

`HYP003-SOURCE-ATTEMPT-<16 uppercase hexadecimal characters>`

It also binds exact create-new absolute paths for:

- `attempt_evidence_root`;
- `custody_stage_path`;
- `design_stage_path`.

All three paths must be deterministic functions of the exact
`source_attempt_id` and their fixed role under the canonical HYP-003 evidence/
data parents. They must be absent during packet validation. No wildcard,
prefix lookup, random production staging token, alternate sibling, or earlier
attempt capability is legal.

Immediately before the first raw-source open, the supervisor must create the
exact evidence root and create-new canonical one-line `attempt_started.json`,
flush and stable-read it, and recheck its file and parent identities. The marker
binds at minimum:

- schema, HYP-003 ID, source attempt ID, and `ATTEMPT_CONSUMED` verdict;
- packet path/SHA and V1/V2/V3 plan SHAs;
- registry path/SHA;
- supervisor review-base SHA and exact armed runtime SHA;
- source path/SHA/bytes/footer SHA plus pre-open identity;
- exact split-vault/DESIGN output roots and custody/DESIGN staging paths;
- all four reviewed tool and test SHAs.

Successful creation and readback of this marker is the conservative attempt
consumption event. If the following source open fails, the attempt is still
consumed. Existing evidence root/marker, staging path, output root, or same
attempt ID must fail closed and can never be deleted, overwritten, resumed, or
retried under HYP-003.

## 5. Deterministic staging and evidence closure

The generic custodian and contained DESIGN worker receive the exact
`source_attempt_id` and only their exact packet-bound staging path. Custody and
DESIGN public/private receipts must bind the same ID and their exact stage role.
Atomic publication may rename only the bound stage to its packet-bound output.
No stage implementation may select a random production name.

After the marker is consumed:

- any exception must make a best-effort create-new canonical
  `attempt_terminal.json` with verdict
  `SOURCE_ATTEMPT_FAILED_ENGINEERING_NO_MARKET_VERDICT`;
- a fully independently validated tree must create the same file with verdict
  `SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET`;
- terminal evidence binds the attempt-start SHA, packet SHA, review-base SHA,
  armed runtime SHA, source attempt ID, final public receipt/manifest/tree
  hashes when available, and no performance metric;
- failure to write terminal evidence does not restore authority: the durable
  start marker still proves the attempt was consumed and HYP-003 must park.

The returned supervisor result must repeat the exact attempt ID, packet SHA,
review-base SHA, armed runtime SHA, attempt-start SHA, terminal-evidence SHA,
and source verdict. It must not contain economics, validation-period outcomes,
holdout outcomes, or trading metrics.

## 6. Run-packet delta from V2

The one-line canonical packet keeps every V2 field and invariant except:

- replace `supervisor_tool_sha256` with
  `supervisor_review_base_sha256`;
- add this V3 path/SHA;
- add exact `attempt_evidence_root`, `custody_stage_path`, and
  `design_stage_path`.

The registry whole-file SHA is computed only after the legal authorization
transition binds this V3 and the final review-base tool/test hashes. All outcome
flags remain false except `source_run_authorized=true`. Model 0, economics,
MT5, network, trading mutation, validation, and holdout remain unauthorized.

## 7. Mandatory pre-production tests

The final source package must pass synthetic tests proving:

1. exact authority-line normalization succeeds only for the reviewed base and
   reviewed packet SHA; every other one-byte/line/value change fails;
2. drift/replacement of each non-source binding produces zero raw-source opens
   and no attempt marker;
3. marker creation/readback occurs before the only raw-source open;
4. crash after marker but before open, crash during/after open, existing marker,
   alternate attempt ID, and reused staging/output all prevent same-ID retry;
5. custody and DESIGN stages are exact deterministic packet paths and all
   receipts carry the same source attempt ID and role;
6. the raw parquet is stable-read once, decoded from verified bytes, and never
   reopened by supervisor or custodian;
7. success/failure terminal evidence and returned hashes reconcile exactly;
8. the production guard remains `None` in the reviewed base, and no production
   source/output/MT5/economic operation occurs during tests.

Production remains `BLOCKED_AUTHORITY_ENGINEERING` until these tests, the full
package regression, independent packet review, and the legal registry
transition all pass.
