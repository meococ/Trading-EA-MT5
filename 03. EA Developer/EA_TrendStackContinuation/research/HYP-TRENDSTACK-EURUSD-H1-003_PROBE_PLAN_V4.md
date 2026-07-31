# HYP-TRENDSTACK-EURUSD-H1-003 — PROBE PLAN V4

Status: `FROZEN_PRE_OUTCOME_REGISTRY_AUTHORITY_AMENDMENT`

## 1. Bound authority

This create-new amendment must be read with and does not modify the market,
data, attempt, execution, or economic contracts frozen in:

- V1 SHA256
  `6A2165CDCE80AD4B04036832C1685746B3828452A8223F35B448DC0568091475`;
- V2 SHA256
  `13BCD3AEB5AB08EC060EAF5107A384FEE8A2CAF581506B50C5F0D8C5A5830840`;
- V3 SHA256
  `1323330E76ED3671D5B57A367A4A84A6944B01634A4E90EC1B53128DFBB68649`;
- collection plan SHA256
  `673D285C8C46D81C2D21ED0BD1E46D12A0EB12CD7DF874074909EF1FA5D2BF2B`.

V4 resolves only the impossible request for a later pre-source registry state
transition. No price row or outcome existed when V4 was frozen.

## 2. Existing registry row is the conditional authority

The sole HYP-003 registry authority is existing row index `273` in
`04. Memory/research/CANDIDATE_REGISTRY.jsonl`, whose exact UTF-8 row bytes
without the line terminator have SHA256:

`63EB8F7A618DCF9179D6BE558F91E264146BA5B4629A73FBB911AD8F4B5B5920`

That row is state `probe`. Its reason conditionally authorizes exactly one
outcome-blind custody and DESIGN source-completeness attempt only after
independent review and a create-new hash-bound run packet. Its standing field
`source_run_authorized=false` remains correct: the registry row alone grants no
general, repeatable, direct, or already-armed production authority.

There is no legal or necessary pre-source registry append. The active validator
forbids `probe -> probe`; `probe -> screened` would require Model 0 and a
canonical EA source, both explicitly unauthorized in this source-only lane.
Creating a new hypothesis ID would launder the same mechanism and data contract.
Changing the global registry state machine for one source attempt is out of
scope.

V4 therefore supersedes only the V2/V3 clauses that require a later registry
transition or post-authorization row before source open. Row 273 plus the
current Owner scope, V1–V4, and the independently reviewed one-shot packet are
the complete authority conjunction.

## 3. Packet and runtime bindings

The final canonical packet must add:

- V4 path and exact SHA256;
- `registry_row_index=273`;
- `registry_row_sha256` equal to the exact row digest above.

It must retain the active registry absolute path and whole-file SHA256 observed
immediately before packet creation. The supervisor must verify, before any raw
source open or attempt marker, that:

1. row 273 exact bytes match the frozen row digest;
2. row 273 is the latest HYP-003 row and preserves state `probe`, the V1
   preregistration binding, conditional one-attempt reason, and all false
   economic/Model-0/promotion/validation/holdout flags;
3. the whole registry exact bytes match the packet whole-file SHA;
4. no later HYP-003 row exists.

Unrelated registry rows appended before packet creation are permitted only when
the packet binds the resulting whole-file SHA and row 273 remains the latest
HYP-003 row. Any registry change after packet review invalidates that packet and
must fail before marker/source open.

Replace the generic packet flag `source_run_authorized` with the narrower exact
boolean:

`one_shot_custody_source_attempt_authorized=true`

This flag is valid only for the single packet-bound `source_attempt_id`, exact
durable marker, deterministic custody/DESIGN stages, frozen local raw source,
and source-completeness verdict. It grants no retry, alternate source, repair,
economics, performance metric, MT5, EA, Model 0, validation outcome, holdout,
promotion, paper, live, or deploy authority. All other outcome flags stay false.

## 4. Mandatory synthetic proof

Before packet review, tests must prove:

- exact row-index/hash/latest-HYP-003 validation passes for the frozen row;
- wrong row index/hash, changed row bytes, or any later HYP-003 row fails before
  marker creation and produces zero raw-source opens;
- unrelated appended rows pass only when the packet whole-file SHA matches;
- old `source_run_authorized`, missing one-shot flag, non-boolean values, or any
  extra field fail closed;
- production guard remains `None` and all tests remain synthetic.

Production remains `BLOCKED_REGISTRY_PACKET_REVIEW` until V4 is hash-bound in
the final reviewed supervisor/test package and canonical one-shot packet.
