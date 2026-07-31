# DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002 — COLLECTION PLAN V2

Status: `FROZEN_IDEA_AMENDMENT_PRE_DECODE_PRE_OUTCOME`

This create-new V2 supersedes V1 SHA256
`A8A768D529A4569BDD508BFA0722BFA1ACEF25C3098A91FF78B98EA209E3510F`.
Every V1 clause remains binding except where V2 explicitly replaces or narrows
it below. V2 is frozen while HYP-006 remains in registry state `idea`; no source
content, price row, strategy outcome or performance metric has been opened.

## 1. Metadata-only date selection is a separate capability

The source builder must never receive the full HYP-002 Stage-0 feature
projection. Before any selected DESIGN shard content is opened, a trusted
metadata-only projector must:

1. verify the HYP-002 Stage-0 ledger and receipt SHAs frozen in V1;
2. read only eligibility metadata needed to produce the sorted unique tuple of
   exactly `1,297` DESIGN opportunity dates;
3. prove the tuple SHA256 is exactly
   `4F30B5E09C8C21C3FCB63F4D5A016EB514D689710589077427464B92CD99A06A`;
4. emit a canonical create-new selection manifest with exactly 1,297 rows and
   no direction, M252, M6, alignment, arm, ATR, OHLC, return, cost or gate field.

After generic custody publishes the public DESIGN H1 vault, the supervisor may
parse its public receipt and manifest as metadata only. It must map every
required date to exactly one canonical public shard path/hash/bytes record and
freeze that mapping before any selected shard content-open. A missing or
duplicate required date fails before any selected shard open.

The public vault may contain dates outside the 1,297-date selection. The exact
H1 extra-date count is `public_design_date_count - 1297` and must be recorded
from metadata; it is not assumed from HYP-004's M1 count. Every unselected
public shard has builder payload-read count exactly `0`. The filtered source
capability exposes `design_dates()` equal to the exact 1,297-date tuple and may
open each selected shard at most once, only after the durable attempt marker.

The sealed source child receives only:

- the exact date tuple and canonical selection-manifest bytes;
- selected public DESIGN shard bytes;
- public custody receipt/manifest bytes needed for provenance;
- source-builder contract metadata.

It receives no Stage-0 direction, ATR, eligibility, arm or strategy field and
no parent path-enumeration capability. The separate future economic evaluator
may receive the full accepted feature projection only after independent source
PASS and under a create-new economic packet. Source construction cannot compute
or emit a trade, return, PnL or gate.

This replaces V1 wording that allowed the source builder to receive the full
Stage-0 projection and full public DESIGN capability simultaneously.

## 2. Exact source-read ordering

Before the durable attempt marker, verify only non-content bindings and expected
source facts: canonical plans/registry/packet, expected whole SHA/bytes/footer
length/start/SHA, source path `lstat`/size/identity, root manifest and clock,
tool/test hashes, review-base/runtime supervisor identities, and fresh evidence,
stage and output paths. Expected footer values are packet bindings at this stage;
the source file must not be opened to re-verify them.

After exclusive marker write, file flush, directory flush and exact readback,
the generic custodian performs the first-and-only raw H1 source-content read.
During that same controlled read it must recompute and verify:

- whole-file SHA256 and bytes;
- footer length, start and exact footer-range SHA256;
- exact Arrow schema and BID/clock invariants;
- all 71,785 rows and exact-once split reconciliation.

Any mismatch is an attempt-consuming engineering failure. Later selected public
DESIGN shard reads are capability reads of newly published custody artifacts,
not a second raw-monolith read. The terminal receipt separately reports raw
source opens, selected shard opens and unselected shard opens.

## 3. V2 tests and prohibitions

Red-first tests must prove a synthetic public capability with required dates
plus extras is narrowed before payload extraction; all required dates open once,
all extras open zero times, and the worker payload has exactly the required keys.
Also test missing/duplicate selection rows, injected extra payload keys, feature
field leakage, pre-marker raw open, second raw open, selected hash drift and
unselected shards rigged to raise if touched.

All V1 path/source/parent/M1/VALIDATION/HOLDOUT/network/subprocess prohibitions
remain unchanged. Source PASS remains engineering-only and cannot authorize
economics or trading.

