# HYP-ST-XAUUSD-H1-009 - comparator authority-binding failure

Status: `KILL_EXACT_COMPARATOR_AUTHORITY_BINDING`

Timestamp: `2026-08-09T00:21:46Z`

## What completed

- `ST009-ARTIFACT-COLLECT-001` completed and sealed the existing HYP008
  artifacts without rerunning MT5 or compilation.
- Recovery receipt SHA256:
  `398194E68C53E7C78BD7963EAD4AB9A64B4ABC889CF9510EAF1E73A84C41E434`.
- Recovery terminal SHA256:
  `838D2A803CDA6F071DF057F2DC3E973CFCB12FCB46179AC4DA995AD146B6BD72`.
- Recovered CSV stayed byte-identical at
  `C404DDE7922C757CC0B1B3D7E3AF8F48C7A4E0F219716314A138D1AC4AB61DD3`;
  counters remain rows 29,460, raw 690, executable 683, gaps 7, LONG 339,
  SHORT 344.

## Exact failure

The first comparator invocation stopped in `validate_registry_authority()`
before the durable comparator claim. The HYP009 authority row bound the
canonical source through top-level `source_hash`, but omitted the duplicate
fail-close field `validation.reviewed_mql_source_sha256` required by the frozen
comparator. The exact exception was:

`ValueError: mql_source binding mismatch`

The canonical source hash is correct:
`580E2F6713ABA77597528127249CF5BBE0F2826FFF20AE10B36B73402B4A03AF`.
The failure is only the missing validation-field binding.

## Evidence boundary

- Comparator evidence root `ST009-COMPARATOR-001` was not created.
- Comparator claim/receipt/terminal do not exist; comparator attempts consumed
  is zero.
- Oracle, recovered CSV and per-bar parity calculation were not opened by the
  comparator invocation.
- No MT5, AlphaFactory, MetaEditor, orders, trades, outcomes, returns, PF,
  optimization, validation, holdout, paper or live execution occurred.
- Registry remained SHA256
  `990F949A249AB628D1979845FB008A919ED2833C0FDA4DD166C19CA922BBFA55`
  with 803 rows at failure discovery.

## Verdict and next legal lane

Do not amend the sealed HYP009 authority row or weaken its comparator. The
HYP009 collection receipt binds the exact original authority-row SHA, so a
same-ID authority append would invalidate that latest-row invariant. Terminally
close HYP009 with collection consumed once and comparator unconsumed.

Open a fresh comparator-only child `HYP-ST-XAUUSD-H1-010` that explicitly binds
the MQL source in its validation authority and consumes the already sealed
HYP009 collection receipt/terminal. It must use a fresh comparator ID/evidence
root, cannot repeat collection or MT5, and keeps every economic/outcome/trading
permission false.
