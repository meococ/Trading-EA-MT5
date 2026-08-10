# HYP-ST-XAUUSD-H1-009 - pre-collection review packet

Status: `PASS_PRE_COLLECTION`

HYP009 is a fresh artifact-recovery child of terminal HYP008. It does not run
MT5, AlphaFactory, MetaEditor or any economics. It may claim once, copy the
exact completed HYP008 parity CSV and compile log into its fresh evidence root,
normalize the two identical manifest-bound current summaries into one line,
then run one correctness-only full-bar comparator.

Frozen implementation hashes:

- prereg: `E88D5B6B7B354B7ADB7F053331E5A31A8F98B68E8F7580847CC87168666BA827`
- recovery contract: `40CB06A789EE662FB1217EBCF7C89A8C9835E76D036C487630F3456DF7FA775E`
- collector: `8BC9B55070779E0B9B8E8834F95DD6F58512B25EB2976A1CBED8A30B8319EF2D`
- comparator wrapper: `A68CB44C72BAC8BB73BC151C21150E9968826764BFD6EB3580640CBBA7E067E1`
- recovery tests: `25AB4956A80F7DC452B3A4DC2C2790802139223F2C3DA69AD2F09D907AA36818`
- frozen comparator dependency: `0DA75EED50E420209A0A70E48E21FE46D93F21B17D100CA27BF9F0D7DA9BD367`
- legacy parity tests: `22F0F1F25F0886402B2EF098017EFCC1D6C01111C5142E90E5752BDD4B27C590`

Frozen HYP008 artifact hashes are enumerated in the recovery contract. HYP008
is terminal `KILL_EXACT_ARTIFACT_COLLECTOR_JOURNAL_SELECTION`; its MT5 run
remains valid but parity is not yet proven. The HYP009 evidence root and both
new attempt IDs are absent.

Verification: Python compilation PASS; recovery plus existing parity/DQ suite
`72 passed`; candidate registry `802 rows / 311 hypotheses` PASS.

Review must verify claim-before-read, automatic failure terminal, no global
tester-log scan, exact current-summary normalization, source/destination hash
reconciliation, fresh evidence-root-only writes, inherited HYP008 run identity,
HYP003 oracle comparison, one-shot authority and the zero-economic boundary.

The collector snapshots each mutable common CSV/compile-log source once,
verifies stat stability around that read, validates the recovered bytes, and
never writes into the Alpha run directory. The comparator uses its own
fail-closed execute/receipt path; it does not delegate receipt construction to
the frozen HYP008 base and therefore never references the absent Alpha-run
compile-log extension.

Independent verdict: `PASS`. No fatal blocker remains. Both tools fail closed
on compile, research-access, retry and registry-mutation authority drift; the
canonical-root, latest-authority-row, captured-source, HYP008-run and HYP003-
oracle bindings remain intact. Review was static only and opened no evidence.
