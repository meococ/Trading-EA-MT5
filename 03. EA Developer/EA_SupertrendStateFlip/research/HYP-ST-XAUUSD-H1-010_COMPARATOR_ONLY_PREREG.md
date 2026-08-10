# HYP-ST-XAUUSD-H1-010 - sealed comparator-only preregistration

Status: `FROZEN_PRE_AUTHORITY`

## Thesis and exact scope

HYP010 is a fresh correctness-only child of terminal HYP009. It does not alter
the Supertrend10x3 formula, MQL source, compiled EX5, HYP008 MT5 run, HYP003
oracle, or recovered audit rows. Its sole job is to execute the full-bar parity
comparison that HYP009 never claimed because its registry authority omitted one
duplicate source-binding field.

Identity chain is frozen as:

- outer authority: `HYP-ST-XAUUSD-H1-010`;
- sealed collection: `HYP-ST-XAUUSD-H1-009` /
  `ST009-ARTIFACT-COLLECT-001`;
- MT5 run: `HYP-ST-XAUUSD-H1-008`;
- parity target/oracle: `HYP-ST-XAUUSD-H1-003`;
- sole comparator attempt: `ST010-COMPARATOR-001`.

## Inputs and provenance

Only the sealed HYP009 collection root may supply the MQL audit CSV, normalized
summary and compile log. The comparator may also read the hash-bound HYP008 run
manifest/report/source/EX5, HYP003 oracle chain, HYP008 non-repaint packet, this
preregistration, tests and current registry. It may not read the mutable
FILE_COMMON source or canonical compile log.

`--mql-source` is frozen to the HYP008 run-local source snapshot, not the
mutable canonical source path, because the sealed HYP009 receipt binds that
exact path. Its bytes must still equal canonical reviewed source SHA256
`580E2F6713ABA77597528127249CF5BBE0F2826FFF20AE10B36B73402B4A03AF`.

The collection receipt must bind historical HYP009 authority-row SHA256
`3BAD69ED145D3133AA806792DAD836243F08B9264C2BBB44627F9ACB99882A70`.
The current registry must contain that exact historical row and separately end
HYP009 at terminal row SHA256
`75120889128610339D5DCE0A0F11B471E3D38F3597C728BC8DB5085C5DB0B70D`.
The terminal row must bind the same collection receipt/terminal and record
collection consumed once, comparator consumed zero.

## Frozen comparator behavior

The wrapper hash-loads the reviewed HYP009 comparator engine and changes only
the outer authority, attempt ID/root and the historical-row lineage validator.
The inherited receipt/terminal schema and filenames retain their `st009` labels
for engine compatibility, but their embedded outer authority and attempt must
be HYP010 / ST010.

The comparator must causally match all 29,460 H1 design rows and exact state,
ATR, bands, event timestamps and directions against the HYP003 oracle. Expected
source counters remain raw 690, executable 683, gaps 7, LONG 339, SHORT 344.
Any row mismatch, missing row, extra row, non-repaint drift, run-contract drift,
receipt drift, authority drift or replay mismatch fails the sole attempt.

## Authority boundary

No artifact collection, MT5, AlphaFactory, MetaEditor, MQL compilation, trade
API, orders, deals, outcome prices, returns, PF, optimization, validation,
holdout, paper, promotion or live work is authorized. A parity PASS is only an
`engineering-valid` result. Economics require a separately preregistered child
with real trade logic, exits, risk and frozen costs.

The attempt is durable and one-shot. Claim occurs before oracle/audit reads;
success or failure writes a terminal. Same-ID retry and registry mutation by the
comparator are forbidden.

Pre-claim validation is limited to registry metadata, IDs, exact paths and the
executing wrapper/dependency code hashes. The first post-claim hook hashes every
authority-bound oracle, audit, source, non-repaint, receipt and test artifact;
only after that hook passes may oracle parsing or row comparison begin.

The append-only HYP009 read-scope correction is an explicit dependency:
`03. EA Developer/EA_SupertrendStateFlip/research/HYP-ST-XAUUSD-H1-009_POST_TERMINAL_READ_DISCLOSURE.md`,
SHA256 `C85948D1CBF333A3F57517D9E4D8CDA20F17947759CE20113D22239F1FCB1CFA`.
Authority must bind the exact path/hash as metadata before claim; the post-claim
artifact validator must hash-check the file before oracle parsing.
