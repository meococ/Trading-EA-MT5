# HYP-STBS-XAUUSD-M15-018 — independent pre-comparator review

Status: `PASS_PRE_AUTHORITY`

Reviewed read-only after the initial FAIL and the complete hardening revision.
No comparator execution, MT5 run, compilation, source-data read, order, outcome,
PF or economics was authorized by this review.

## Frozen package

- preregistration SHA256: `3C25D7037E080AF560BAFC4615B37C82C8E0F8B80DB5F2F467725C21E18B3EE7`;
- comparator SHA256: `04222C5F8FB3D60A4F21AE517C2484332290108456DA49C61BE9838AEC7AB7FA`;
- test SHA256: `04A7F8F26A0B9C762D83C73F10E0A135BB4762CBEDF345AA66F3EB60A2111818`;
- focused test result: 73 passed;
- `STBS018-COMPARATOR-001` evidence root absent at review.

## Verdict

`PASS_PRE_AUTHORITY`

The durable claim precedes registry and artifact reads. Registry parsing uses
one strict duplicate-rejecting byte buffer and captures the full snapshot plus
exact raw authority rows. Required permissions and zero counters are exhaustive
and omission-fail-closed. Comparator/prereg/test, HYP017/HYP013 lineage, every
run input and the run compile log are captured, receipt-bound and final-rehashed;
the failure terminal inventories all created attempt artifacts.

Canonical run paths, exact inventory set, journal-only sidecar allowlist,
unique 0-error/0-warning compile result, pre-outcome HYP013 fingerprint lineage,
manifest/data-quality/series proof, reason-1 duplicate journal normalization,
zero-order report shape and deterministic replay are all fail-closed.

This PASS authorizes only one comparator attempt. A successful result may state
`PASS_ENGINEERING_ZERO_TRADE_MODEL0_AUDIT`; it cannot state or imply an economic
edge, PF, robustness, promotion or deployment readiness.
